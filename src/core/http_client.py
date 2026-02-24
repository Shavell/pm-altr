"""HTTP client with full metrics, proxy, SSL, redirect support."""
from __future__ import annotations
import os
import time
from dataclasses import dataclass, field
from typing import Optional
import requests
from requests.auth import HTTPBasicAuth


@dataclass
class RequestConfig:
    method: str = "GET"
    url: str = ""
    headers: dict = field(default_factory=dict)
    params: dict = field(default_factory=dict)
    body_type: str = "none"          # none | json | form-data | x-www-form-urlencoded | text
    body_json: str = ""
    body_form: dict = field(default_factory=dict)
    body_text: str = ""
    auth_type: str = "none"          # none | basic | bearer
    auth_username: str = ""
    auth_password: str = ""
    auth_token: str = ""
    ssl_verify: bool = True
    follow_redirects: bool = True
    timeout: int = 30
    proxy_enabled: bool = False
    proxy_use_system: bool = False
    proxy_http: str = ""
    proxy_https: str = ""
    proxy_username: str = ""
    proxy_password: str = ""
    proxy_no_proxy: str = ""


@dataclass
class ResponseData:
    status_code: int = 0
    reason: str = ""
    response_time_ms: float = 0.0
    response_size_bytes: int = 0
    headers: dict = field(default_factory=dict)
    body: str = ""
    body_bytes: bytes = field(default_factory=bytes)
    content_type: str = ""
    error: Optional[str] = None
    redirect_history: list = field(default_factory=list)


class HttpClient:
    def send(self, config: RequestConfig) -> ResponseData:
        proxies = None
        old_no_proxy = os.environ.get("NO_PROXY")
        if config.proxy_enabled:
            if config.proxy_no_proxy:
                os.environ["NO_PROXY"] = config.proxy_no_proxy
            if config.proxy_use_system:
                # Let requests read HTTP_PROXY / HTTPS_PROXY / NO_PROXY from env
                proxies = None
            elif config.proxy_http or config.proxy_https:
                def _inject_auth(url: str) -> str:
                    if config.proxy_username and "@" not in url:
                        from urllib.parse import urlparse, urlunparse
                        p = urlparse(url)
                        netloc = f"{config.proxy_username}:{config.proxy_password}@{p.hostname}"
                        if p.port:
                            netloc += f":{p.port}"
                        url = urlunparse(p._replace(netloc=netloc))
                    return url

                proxies = {}
                if config.proxy_http:
                    proxies["http"] = _inject_auth(config.proxy_http)
                if config.proxy_https:
                    proxies["https"] = _inject_auth(config.proxy_https)
        else:
            # Proxy explicitly disabled — bypass env vars
            proxies = {"http": None, "https": None}

        auth = None
        if config.auth_type == "basic":
            auth = HTTPBasicAuth(config.auth_username, config.auth_password)

        headers = dict(config.headers)
        if config.auth_type == "bearer" and config.auth_token:
            headers["Authorization"] = f"Bearer {config.auth_token}"

        kwargs: dict = {
            "headers": headers,
            "params": config.params or None,
            "verify": config.ssl_verify,
            "allow_redirects": config.follow_redirects,
            "timeout": config.timeout,
            "proxies": proxies,
            "auth": auth,
        }

        if config.body_type == "json":
            kwargs["data"] = config.body_json.encode("utf-8") if config.body_json else None
            if "Content-Type" not in headers:
                headers["Content-Type"] = "application/json"
        elif config.body_type == "form-data":
            kwargs["files"] = {k: (None, v) for k, v in config.body_form.items()}
        elif config.body_type == "x-www-form-urlencoded":
            kwargs["data"] = config.body_form
        elif config.body_type == "text":
            kwargs["data"] = config.body_text.encode("utf-8") if config.body_text else None
            if "Content-Type" not in headers:
                headers["Content-Type"] = "text/plain"

        result = ResponseData()
        try:
            t0 = time.perf_counter()
            resp = requests.request(config.method, config.url, **kwargs)
            elapsed = (time.perf_counter() - t0) * 1000

            result.status_code = resp.status_code
            result.reason = resp.reason or ""
            result.response_time_ms = round(elapsed, 2)
            result.response_size_bytes = len(resp.content)
            result.headers = dict(resp.headers)
            result.body_bytes = resp.content
            result.content_type = resp.headers.get("Content-Type", "")
            result.redirect_history = [r.url for r in resp.history]
            try:
                result.body = resp.text
            except Exception:
                result.body = repr(resp.content)
        except requests.exceptions.SSLError as e:
            result.error = f"SSL Error: {e}"
        except requests.exceptions.ProxyError as e:
            result.error = f"Proxy Error: {e}"
        except requests.exceptions.ConnectionError as e:
            result.error = f"Connection Error: {e}"
        except requests.exceptions.Timeout as e:
            result.error = f"Timeout: {e}"
        except Exception as e:
            result.error = str(e)
        finally:
            # Restore original NO_PROXY env
            if old_no_proxy is None:
                os.environ.pop("NO_PROXY", None)
            else:
                os.environ["NO_PROXY"] = old_no_proxy
        return result
