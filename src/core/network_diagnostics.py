"""Network diagnostics: DNS resolution and TCP connect info."""
from __future__ import annotations
import socket
import time
from dataclasses import dataclass, field
from typing import List, Optional
from urllib.parse import urlparse


@dataclass
class DiagnosticsResult:
    hostname: str = ""
    resolved_ips: List[str] = field(default_factory=list)
    dns_time_ms: float = 0.0
    tcp_connect_ms: float = 0.0
    tcp_port: int = 80
    connected_ip: str = ""
    proxy_used: bool = False
    proxy_address: str = ""
    error: Optional[str] = None


def run_diagnostics(url: str, proxy_used: bool = False, proxy_address: str = "") -> DiagnosticsResult:
    result = DiagnosticsResult(proxy_used=proxy_used, proxy_address=proxy_address)
    try:
        parsed = urlparse(url)
        hostname = parsed.hostname or url
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        result.hostname = hostname
        result.tcp_port = port

        # DNS resolution
        t0 = time.perf_counter()
        try:
            addr_infos = socket.getaddrinfo(hostname, port, proto=socket.IPPROTO_TCP)
            result.dns_time_ms = round((time.perf_counter() - t0) * 1000, 2)
            result.resolved_ips = list(dict.fromkeys(ai[4][0] for ai in addr_infos))
        except socket.gaierror as e:
            result.error = f"DNS resolution failed: {e}"
            return result

        # TCP connect timing (direct, not through proxy — shows actual server IP)
        if result.resolved_ips:
            connect_host = proxy_address.split("://")[-1].split(":")[0] if proxy_used and proxy_address else result.resolved_ips[0]
            connect_port = int(proxy_address.split(":")[-1]) if proxy_used and proxy_address and ":" in proxy_address else port
            try:
                t1 = time.perf_counter()
                sock = socket.create_connection((connect_host, connect_port), timeout=5)
                result.tcp_connect_ms = round((time.perf_counter() - t1) * 1000, 2)
                result.connected_ip = sock.getpeername()[0]
                sock.close()
            except Exception as e:
                result.tcp_connect_ms = -1
                result.error = f"TCP connect failed: {e}"

    except Exception as e:
        result.error = str(e)

    return result
