"""cURL import and export utilities."""
from __future__ import annotations
import re
import shlex
from dataclasses import dataclass, field
from typing import Optional
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse


@dataclass
class CurlRequest:
    method: str = "GET"
    url: str = ""
    headers: dict = field(default_factory=dict)
    params: dict = field(default_factory=dict)
    body: str = ""
    body_type: str = "none"
    auth_type: str = "none"
    auth_username: str = ""
    auth_password: str = ""
    ssl_verify: bool = True
    follow_redirects: bool = False
    cookies: dict = field(default_factory=dict)


def parse_curl(curl_string: str) -> Optional[CurlRequest]:
    """Parse a cURL command string into a CurlRequest object."""
    # Normalise line continuations and extra whitespace
    curl_string = curl_string.strip()
    curl_string = re.sub(r"\\\n\s*", " ", curl_string)

    try:
        tokens = shlex.split(curl_string)
    except ValueError:
        return None

    if not tokens or tokens[0].lower() not in ("curl", "curl.exe"):
        return None

    req = CurlRequest()
    i = 1
    while i < len(tokens):
        tok = tokens[i]

        if tok in ("-X", "--request") and i + 1 < len(tokens):
            req.method = tokens[i + 1].upper()
            i += 2

        elif tok in ("-H", "--header") and i + 1 < len(tokens):
            header = tokens[i + 1]
            if ":" in header:
                name, _, value = header.partition(":")
                req.headers[name.strip()] = value.strip()
            i += 2

        elif tok in ("-d", "--data", "--data-raw", "--data-ascii") and i + 1 < len(tokens):
            req.body = tokens[i + 1]
            req.body_type = "json" if _looks_like_json(req.body) else "text"
            if req.method == "GET":
                req.method = "POST"
            i += 2

        elif tok == "--data-urlencode" and i + 1 < len(tokens):
            req.body = tokens[i + 1]
            req.body_type = "x-www-form-urlencoded"
            if req.method == "GET":
                req.method = "POST"
            i += 2

        elif tok in ("-F", "--form") and i + 1 < len(tokens):
            req.body_type = "form-data"
            if req.method == "GET":
                req.method = "POST"
            i += 2

        elif tok in ("-u", "--user") and i + 1 < len(tokens):
            parts = tokens[i + 1].split(":", 1)
            req.auth_type = "basic"
            req.auth_username = parts[0]
            req.auth_password = parts[1] if len(parts) > 1 else ""
            i += 2

        elif tok in ("-b", "--cookie") and i + 1 < len(tokens):
            cookie_str = tokens[i + 1]
            for part in cookie_str.split(";"):
                part = part.strip()
                if "=" in part:
                    k, _, v = part.partition("=")
                    req.cookies[k.strip()] = v.strip()
            i += 2

        elif tok in ("-k", "--insecure"):
            req.ssl_verify = False
            i += 1

        elif tok in ("-L", "--location"):
            req.follow_redirects = True
            i += 1

        elif tok.startswith("http://") or tok.startswith("https://"):
            req.url = tok
            i += 1

        elif tok in ("--url",) and i + 1 < len(tokens):
            req.url = tokens[i + 1]
            i += 2

        else:
            i += 1

    # Extract query params from URL
    if req.url:
        parsed = urlparse(req.url)
        if parsed.query:
            for k, vals in parse_qs(parsed.query).items():
                req.params[k] = vals[0] if len(vals) == 1 else vals
            # Strip query string from url
            req.url = urlunparse(parsed._replace(query=""))

    # Detect Bearer token in Authorization header
    auth_header = req.headers.get("Authorization", req.headers.get("authorization", ""))
    if auth_header.lower().startswith("bearer "):
        req.auth_type = "bearer"
        # keep it in headers too

    return req


def export_curl(
    method: str,
    url: str,
    headers: dict,
    params: dict,
    body: str,
    body_type: str,
) -> str:
    """Serialize a request back to a cURL command."""
    segments = ["curl"]
    if method.upper() != "GET":
        segments.append(f"-X {method.upper()}")

    for k, v in headers.items():
        segments.append(f"-H {shlex.quote(f'{k}: {v}')}")

    if params:
        qs = urlencode(params)
        sep = "&" if "?" in url else "?"
        url = f"{url}{sep}{qs}"

    if body and body_type in ("json", "text"):
        segments.append(f"-d {shlex.quote(body)}")
    elif body_type == "x-www-form-urlencoded" and body:
        segments.append(f"--data-urlencode {shlex.quote(body)}")

    segments.append(shlex.quote(url))
    return " \\\n  ".join(segments)


def _looks_like_json(s: str) -> bool:
    s = s.strip()
    return (s.startswith("{") and s.endswith("}")) or (s.startswith("[") and s.endswith("]"))
