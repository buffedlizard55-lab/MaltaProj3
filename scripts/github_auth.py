"""Authenticate requests to the GitHub API, and nothing else.

Measured on 2026-10-15 from a GitHub-hosted runner (run 38824422956): unauthenticated calls to
api.github.com were answered HTTP 403 with `x-ratelimit-remaining: 0` of 60 on three tries in a row, because that
quota is shared by every job leaving the same runner addresses; the workflow's own GITHUB_TOKEN got HTTP 200 with a
limit of 5000 per hour (GitHub documents 60 per hour per IP address for unauthenticated requests and a separate
per-repository budget for GITHUB_TOKEN). Both collectors read Valve's public standings through that API, so an exhausted shared quota
silently removed every model estimate and the saved ratings evidence.

The token is attached to https://api.github.com only. It is never sent to another host, never written to a request
manifest or evidence file, and requests drops it on a cross-host redirect.
"""
from __future__ import annotations

import os
from urllib.parse import urlparse

API_HOST = 'api.github.com'


def auth_headers(url: str, environ=None) -> dict:
    env = os.environ if environ is None else environ
    token = env.get('GITHUB_TOKEN') or env.get('GH_TOKEN')
    parsed = urlparse(url)
    if token and parsed.scheme == 'https' and (parsed.hostname or '').lower() == API_HOST:
        return {'Authorization': 'Bearer ' + token, 'X-GitHub-Api-Version': '2022-11-28'}
    return {}
