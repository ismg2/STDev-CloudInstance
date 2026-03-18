"""Authentication module for STEdgeAI Developer Cloud.

Handles Bearer token management:
- Reads cached token from ~/.stmai_token
- Refreshes expired tokens automatically
- Falls back to interactive login if no token exists
- Supports environment variables stmai_username / stmai_password
"""

import json
import os
import re
import time
import getpass

import requests

from config import TOKEN_FILE, SSO_URL, SSO_CLIENT_ID, SSO_CALLBACK_URL, ENDPOINTS, BASE_URL


def _get_ssl_verify():
    """Check if SSL verification should be disabled (proxy environments)."""
    return os.environ.get("STEDGEAI_SSL_VERIFY", "1") != "0"


def _get_session():
    """Create a requests session with appropriate headers."""
    session = requests.Session()
    session.verify = _get_ssl_verify()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0"
    })
    # Support HTTP_PROXY / HTTPS_PROXY from environment
    http_proxy = os.environ.get("HTTP_PROXY") or os.environ.get("http_proxy")
    https_proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
    if http_proxy or https_proxy:
        session.proxies = {}
        if http_proxy:
            session.proxies["http"] = http_proxy
        if https_proxy:
            session.proxies["https"] = https_proxy
    return session


def _load_cached_token():
    """Load token from cache file if it exists."""
    if not os.path.exists(TOKEN_FILE):
        return None
    try:
        with open(TOKEN_FILE, "r") as f:
            data = json.load(f)
        if "access_token" in data:
            return data
    except (json.JSONDecodeError, IOError):
        pass
    return None


def _save_token(token_data):
    """Save token data to cache file."""
    with open(TOKEN_FILE, "w") as f:
        json.dump(token_data, f)
    os.chmod(TOKEN_FILE, 0o600)


def _is_token_expired(token_data):
    """Check if the token has expired."""
    expires_at = token_data.get("expires_at", 0)
    return time.time() >= expires_at


def _refresh_token(token_data):
    """Refresh an expired access token using the refresh token."""
    refresh_tok = token_data.get("refresh_token")
    if not refresh_tok:
        return None
    session = _get_session()
    try:
        resp = session.post(
            ENDPOINTS["login_refresh"],
            json={"refresh_token": refresh_tok},
            timeout=30,
        )
        if resp.status_code == 200:
            new_data = resp.json()
            new_data.setdefault("expires_at", time.time() + 3600)
            _save_token(new_data)
            return new_data
    except requests.RequestException:
        pass
    return None


def _login_interactive(username=None, password=None):
    """Perform OAuth2 SSO login to obtain a new token.

    Uses the same flow as the official ST tools:
    1. Initiate OAuth2 authorization request
    2. Submit credentials to CAS login
    3. Follow redirects to obtain authorization code
    4. Exchange code for tokens
    """
    if not username:
        username = os.environ.get("stmai_username") or input("ST Username (email): ").strip()
    if not password:
        password = os.environ.get("stmai_password") or getpass.getpass("ST Password: ")

    session = _get_session()
    session.max_redirects = 30

    # Step 1: Initiate OAuth2 authorization
    auth_params = {
        "response_type": "code",
        "client_id": SSO_CLIENT_ID,
        "redirect_uri": SSO_CALLBACK_URL,
        "scope": "openid",
    }
    try:
        resp = session.get(f"{SSO_URL}/as/authorization.oauth2", params=auth_params,
                           allow_redirects=True, timeout=30)
    except requests.RequestException as e:
        raise ConnectionError(f"Impossible de contacter le serveur SSO: {e}")

    # Step 2: Extract login form and submit credentials
    # Look for the CAS login form action URL and login ticket
    action_match = re.search(r'action="([^"]+)"', resp.text)
    lt_match = re.search(r'name="lt" value="([^"]+)"', resp.text)

    if not action_match:
        raise RuntimeError("Impossible de trouver le formulaire de login SSO.")

    login_url = action_match.group(1)
    if not login_url.startswith("http"):
        login_url = f"{SSO_URL}{login_url}"

    form_data = {
        "username": username,
        "password": password,
        "submit": "Sign In",
    }
    if lt_match:
        form_data["lt"] = lt_match.group(1)

    try:
        resp = session.post(login_url, data=form_data, allow_redirects=True, timeout=30)
    except requests.RequestException as e:
        raise ConnectionError(f"Erreur lors de la soumission des credentials: {e}")

    # Check for wrong password
    if "Invalid credentials" in resp.text or "mot de passe" in resp.text.lower():
        raise PermissionError("Identifiants invalides. Verifiez votre username/password.")

    # Step 3: Extract authorization code from redirect
    code = None
    if "code=" in resp.url:
        code_match = re.search(r'code=([^&]+)', resp.url)
        if code_match:
            code = code_match.group(1)

    if not code:
        # Check history for the code in redirects
        for r in resp.history:
            if "code=" in r.headers.get("Location", ""):
                code_match = re.search(r'code=([^&]+)', r.headers["Location"])
                if code_match:
                    code = code_match.group(1)
                    break

    if not code:
        raise RuntimeError("Impossible d'obtenir le code d'autorisation. Login echoue.")

    # Step 4: Exchange code for token
    try:
        resp = session.post(
            ENDPOINTS["login_callback"],
            json={"code": code},
            timeout=30,
        )
        if resp.status_code != 200:
            raise RuntimeError(f"Echange de code echoue (HTTP {resp.status_code})")
        token_data = resp.json()
        token_data.setdefault("expires_at", time.time() + 3600)
        _save_token(token_data)
        return token_data
    except requests.RequestException as e:
        raise ConnectionError(f"Erreur lors de l'echange de token: {e}")


def get_bearer_token():
    """Get a valid Bearer token, refreshing or logging in as needed.

    Returns:
        str: A valid access token ready for Authorization header.
    """
    # Try cached token first
    token_data = _load_cached_token()
    if token_data:
        if not _is_token_expired(token_data):
            print("[Auth] Token Bearer valide trouve en cache.")
            return token_data["access_token"]
        # Try refresh
        print("[Auth] Token expire, tentative de refresh...")
        refreshed = _refresh_token(token_data)
        if refreshed:
            print("[Auth] Token rafraichi avec succes.")
            return refreshed["access_token"]
        print("[Auth] Refresh echoue, login interactif necessaire.")

    # Interactive login
    print("[Auth] Aucun token valide. Connexion au ST Edge AI Developer Cloud...")
    print("       Vous avez besoin d'un compte myST (https://my.st.com)")
    token_data = _login_interactive()
    print("[Auth] Connexion reussie!")
    return token_data["access_token"]


def get_auth_headers():
    """Get HTTP headers with Bearer authentication.

    Returns:
        dict: Headers dict with Authorization Bearer token.
    """
    token = get_bearer_token()
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
