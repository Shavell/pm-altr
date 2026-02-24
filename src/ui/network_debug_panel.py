"""Network diagnostics panel widget."""
from __future__ import annotations
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton,
    QLabel, QTextEdit,
)
from src.core.network_diagnostics import DiagnosticsResult, run_diagnostics


class _DiagWorker(QThread):
    finished = pyqtSignal(object)

    def __init__(self, url: str, proxy_used: bool, proxy_address: str):
        super().__init__()
        self._url = url
        self._proxy_used = proxy_used
        self._proxy_address = proxy_address

    def run(self):
        result = run_diagnostics(self._url, self._proxy_used, self._proxy_address)
        self.finished.emit(result)


class NetworkDebugPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._url = ""
        self._proxy_used = False
        self._proxy_address = ""
        self._build_ui()
        self._worker = None

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        header = QLabel("Network Diagnostics")
        header.setStyleSheet("font-weight:bold;")
        layout.addWidget(header)

        self.output = QTextEdit()
        self.output.setReadOnly(True)
        self.output.setFontFamily("Menlo, Consolas, monospace")
        layout.addWidget(self.output)

    def set_url(self, url: str, proxy_used: bool = False, proxy_address: str = ""):
        self._url = url
        self._proxy_used = proxy_used
        self._proxy_address = proxy_address

    def _run(self):
        if not self._url:
            self.output.setPlainText("No URL set.")
            return
        self.output.setPlainText("Running diagnostics…")
        self._worker = _DiagWorker(self._url, self._proxy_used, self._proxy_address)
        self._worker.finished.connect(self._on_result)
        self._worker.start()

    def _on_result(self, result: DiagnosticsResult):
        proxy_line = (
            f"✅ Yes — {result.proxy_address}" if result.proxy_used
            else "❌ No (direct connection)"
        )
        tcp_line = (
            f"{result.tcp_connect_ms} ms  →  connected to {result.connected_ip}"
            if result.tcp_connect_ms >= 0
            else "FAILED"
        )

        lines = [
            "─── DNS Resolution ───────────────────────",
            f"Hostname       : {result.hostname}",
            f"Resolved IPs   : {', '.join(result.resolved_ips) or 'N/A'}",
            f"DNS Lookup     : {result.dns_time_ms} ms",
            "",
            "─── Connection ───────────────────────────",
            f"Target port    : {result.tcp_port}",
            f"TCP connect    : {tcp_line}",
            "",
            "─── Proxy ────────────────────────────────",
            f"Proxy used     : {proxy_line}",
        ]
        if result.error:
            lines += ["", f"⚠ Errors:\n{result.error}"]
        self.output.setPlainText("\n".join(lines))
