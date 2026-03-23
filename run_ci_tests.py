#!/usr/bin/env python3
"""Minimal CI-style test runner for local and pipeline use."""

import sys
import unittest


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.discover("tests", pattern="test_*.py")
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
