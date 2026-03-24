"""Authentication module for STEdgeAI Developer Cloud.

Implements the exact OAuth2/SSO login flow used by ST's official tools.
Source reference: STMicroelectronics/stm32ai-modelzoo-services login_service.py

Flow:
  1. GET  {SSO_URL}/as/authorization.oauth2  ΓåÆ HTML login page
  2. POST {login_url} with username, password, lt, _eventId=Login ΓåÆ redirects
  3. Follow redirects until reaching {CALLBACK_URL}?code=...
  4. POST {USER_SERVICE_URL}/login/callback with redirect_url + code ΓåÆ tokens
  5. Tokens saved to ~/.stmai_token as JSON

Token refresh:
  POST {USER_SERVICE_URL}/login/refresh with refresh_token
"""

import getpass
import html
import json
import os
import re
import time
from json import JSONDecodeError
from pathlib import Path
from urllib.parse import parse_qs, urljoin, urlparse

import requests

from app.config import (
    SSO_URL, CLIENT_ID, CALLBACK_URL,
    USER_SERVICE_URL, TOKEN_FILE,
    SSL_VERIFY,
)

LOGIN_CALLBACK_ROUTE = f"{USER_SERVICE_URL}/login/callback"
LOGIN_REFRESH_ROUTE  = f"{USER_SERVICE_URL}/login/refresh"


def _get_ssl_verify():
    """Return SSL verify flag (can be disabled via NO_SSL_VERIFY env var)."""
    return SSL_VERIFY


def _get_proxy():
    """Read proxy settings from environment variables."""
    config = {}
    for key in ("http_proxy", "HTTP_PROXY", "https_proxy", "HTTPS_PROXY"):
        val = os.environ.get(key)
        if val:
            proto = "http" if "http_proxy" in key.lower() else "https"
            config[proto] = val
    return config or None


def _make_session():
    """Create a requests.Session configured for ST SSO."""
    s = requests.Session()
    s.verify  = _get_ssl_verify()
    s.proxies = _get_proxy() or {}
    s.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv59.0) Gecko/20100101",
    })
    return s


# ---------------------------------------------------------------------------
# Token file helpers
# ---------------------------------------------------------------------------

def _read_token():
    """Load token dict from ~/.stmai_token. Returns None if missing/invalid."""
    path = Path(TOKEN_FILE)
    if not path.exists():
        return None
    try:
        with open(path, "r") as f:
            return json.load(f)
    except (JSONDecodeError, OSError):
        return None


def _save_token(token: dict):
    """Persist token dict to ~/.stmai_token (mode 600)."""
    path = Path(TOKEN_FILE)
    with open(path, "w") as f:
        json.dump(token, f)
    os.chmod(path, 0o600)


def _is_expired(token: dict) -> bool:
    """Return True if token has expired."""
    expires_at = token.get("expires_at")
    if expires_at is None:
        return True
    return time.time() >= float(expires_at)


# ---------------------------------------------------------------------------
# Refresh
# ---------------------------------------------------------------------------

def _refresh(token: dict):
    """Try to refresh an expired token. Returns new token dict or None."""
    refresh_tok = token.get("refresh_token")
    if not refresh_tok:
        return None
    s = _make_session()
    try:
        resp = s.post(
            LOGIN_REFRESH_ROUTE,
            data={"refresh_token": refresh_tok},
            timeout=30,
        )
        if resp.status_code == 200:
            new_token = {**token, **resp.json()}
            _save_token(new_token)
            return new_token
    except requests.RequestException:
        pass
    return None


# ---------------------------------------------------------------------------
# Interactive login (exact ST flow)
# ---------------------------------------------------------------------------

def _login(username: str, password: str) -> dict:
    """Perform full OAuth2 SSO login and return the token dict.

    Mirrors the exact flow in ST's login_service._login().
    """
    s = _make_session()

    # Step 1 ΓÇô Initiate OAuth2 authorization request
    resp = s.get(
        url=f"{SSO_URL}/as/authorization.oauth2",
        params={
            "response_type": "code",
            "client_id": CLIENT_ID,
            "scope": "openid",
            "redirect_uri": CALLBACK_URL,
            "response_mode": "query",
        },
        allow_redirects=True,
        timeout=30,
    )
    page = resp.text

    # Step 2 ΓÇô Parse the CAS login form
    form_match = re.search(r'<form\s+.*?\s+action="(.*?)"', page, re.DOTALL)
    if not form_match:
        raise RuntimeError("Impossible de trouver le formulaire de login ST SSO.")
    form_action = html.unescape(form_match.group(1))

    lt_match = re.search(r'(<input.*?name="lt".*?/>)', page)
    if not lt_match:
        raise RuntimeError("Impossible de trouver le token 'lt' dans la page SSO.")
    lt_value = html.unescape(
        re.search(r'value="(.*?)"', lt_match.group(1)).group(1)
    )

    # Reconstruct absolute login URL
    parsed = urlparse(resp.url)
    login_url = urljoin(parsed.scheme + "://" + parsed.netloc, form_action)

    # Step 3 ΓÇô Submit credentials
    resp = s.post(
        url=login_url,
        data={
            "username": username,
            "password": password,
            "_eventId": "Login",
            "lt": lt_value,
        },
        allow_redirects=False,
        timeout=30,
    )

    # Check for wrong password / blocked account
    if resp.status_code == 200:
        if re.search(r"You have provided the wrong password", resp.text):
            raise PermissionError("Identifiants invalides (mauvais mot de passe).")
        if re.search(r"You have exceeded 5 login attempts", resp.text):
            raise PermissionError("Compte bloque apres 5 tentatives echouees.")

    # Step 4 ΓÇô Follow redirects until we reach our callback URL
    redirect = resp.headers.get("Location", "")
    is_ready = False
    while not is_ready:
        resp = s.get(url=redirect, allow_redirects=False, timeout=30)
        if resp.status_code == 302:
            redirect = resp.headers.get("Location", "")
            is_ready = redirect.startswith(CALLBACK_URL)
        else:
            is_ready = True

    # Step 5 ΓÇô Extract authorization code from callback URL
    query  = urlparse(redirect).query
    params = parse_qs(query)
    if "code" not in params:
        raise RuntimeError("Code d'autorisation absent de la URL de callback.")
    auth_code = params["code"][0]

    # Step 6 ΓÇô Exchange code for tokens
    resp = s.post(
        url=LOGIN_CALLBACK_ROUTE,
        data={
            "redirect_url": CALLBACK_URL,
            "code": auth_code,
        },
        allow_redirects=False,
        timeout=30,
    )
    assert resp.status_code == 200, f"Callback echoue HTTP {resp.status_code}"

    token = resp.json()
    if not token.get("access_token"):
        raise RuntimeError("Le serveur n'a pas retourne de access_token.")

    _save_token(token)
    return token


def _login_with_retry(username: str, password: str, retries: int = 5) -> dict:
    """Retry login up to `retries` times with 5s delay between attempts."""
    for attempt in range(retries):
        try:
            return _login(username, password)
        except PermissionError:
            raise  # Don't retry bad credentials
        except Exception as e:
            if attempt < retries - 1:
                print(f"  [Auth] Tentative {attempt + 1}/{retries} echouee, retry dans 5s... ({e})")
                time.sleep(5)
            else:
                raise


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_bearer_token() -> str:
    """Return a valid Bearer access token, refreshing or logging in as needed.

    Priority:
      1. Cached non-expired token  ΓåÆ return as-is
      2. Cached expired token      ΓåÆ try refresh
      3. No token / refresh failed ΓåÆ interactive login
    """
    token = _read_token()

    if token:
        if not _is_expired(token):
            print("[Auth] Token Bearer valide (cache).")
            return token["access_token"]
        print("[Auth] Token expire, tentative de refresh...")
        refreshed = _refresh(token)
        if refreshed:
            print("[Auth] Token rafraichi avec succes.")
            return refreshed["access_token"]
        print("[Auth] Refresh echoue, login interactif requis.")

    # Interactive login
    print("\n[Auth] Connexion au ST Edge AI Developer Cloud (compte myST requis)")
    print("       https://my.st.com  |  Vos credentials ne sont jamais stockes en clair.")
    print()
    username = os.environ.get("stmai_username") or input("  Email (username myST) : ").strip()
    password = os.environ.get("stmai_password") or getpass.getpass("  Mot de passe        : ")

    token = _login_with_retry(username, password)
    print("[Auth] Connexion reussie!")
    return token["access_token"]


def get_auth_headers() -> dict:
    """Return HTTP headers dict with Authorization Bearer token."""
    return {
        "Authorization": f"Bearer {get_bearer_token()}",
        "Accept": "application/json",
    }
