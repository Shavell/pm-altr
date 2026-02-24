"""Settings dialog — proxy (host, port, auth, no_proxy, system proxy), SSL, redirect defaults."""
from __future__ import annotations
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGroupBox,
    QLineEdit, QCheckBox, QPushButton, QFormLayout,
)
from src.core.settings_store import save_settings


class SettingsDialog(QDialog):
    def __init__(self, settings: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setMinimumWidth(480)
        self._s = settings
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        # --- Proxy ---
        proxy_group = QGroupBox("Proxy")
        proxy_form = QFormLayout(proxy_group)

        self.proxy_enabled = QCheckBox("Enable proxy")
        self.proxy_enabled.setChecked(self._s.get("proxy_enabled", False))
        self.proxy_enabled.toggled.connect(self._toggle_proxy_fields)
        proxy_form.addRow(self.proxy_enabled)

        self.proxy_use_system = QCheckBox("Use system proxy (env vars)")
        self.proxy_use_system.setChecked(self._s.get("proxy_use_system", False))
        self.proxy_use_system.toggled.connect(self._toggle_proxy_fields)
        proxy_form.addRow(self.proxy_use_system)

        self.proxy_host = QLineEdit(self._s.get("proxy_host", ""))
        self.proxy_host.setPlaceholderText("127.0.0.1")
        proxy_form.addRow("Host:", self.proxy_host)

        self.proxy_port = QLineEdit(self._s.get("proxy_port", ""))
        self.proxy_port.setPlaceholderText("8080")
        self.proxy_port.setMaximumWidth(100)
        proxy_form.addRow("Port:", self.proxy_port)

        self.proxy_username = QLineEdit(self._s.get("proxy_username", ""))
        self.proxy_username.setPlaceholderText("(optional)")
        proxy_form.addRow("Username:", self.proxy_username)

        self.proxy_password = QLineEdit(self._s.get("proxy_password", ""))
        self.proxy_password.setPlaceholderText("(optional)")
        self.proxy_password.setEchoMode(QLineEdit.EchoMode.Password)
        proxy_form.addRow("Password:", self.proxy_password)

        self.proxy_no_proxy = QLineEdit(self._s.get("proxy_no_proxy", ""))
        self.proxy_no_proxy.setPlaceholderText("localhost,127.0.0.1,.internal.corp")
        proxy_form.addRow("No Proxy:", self.proxy_no_proxy)

        layout.addWidget(proxy_group)
        self._toggle_proxy_fields()

        # --- Defaults ---
        defaults_group = QGroupBox("Defaults")
        defaults_form = QFormLayout(defaults_group)
        self.ssl_verify = QCheckBox("Verify SSL certificates")
        self.ssl_verify.setChecked(self._s.get("ssl_verify", True))
        self.follow_redirects = QCheckBox("Follow redirects")
        self.follow_redirects.setChecked(self._s.get("follow_redirects", True))
        defaults_form.addRow(self.ssl_verify)
        defaults_form.addRow(self.follow_redirects)
        layout.addWidget(defaults_group)

        # --- Buttons ---
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        ok = QPushButton("OK")
        ok.setDefault(True)
        ok.clicked.connect(self._accept)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        btn_row.addWidget(cancel)
        btn_row.addWidget(ok)
        layout.addLayout(btn_row)

    def _toggle_proxy_fields(self):
        enabled = self.proxy_enabled.isChecked()
        use_sys = self.proxy_use_system.isChecked()
        # System proxy checkbox only visible when proxy enabled
        self.proxy_use_system.setEnabled(enabled)
        # Manual fields disabled when proxy off or when system proxy is on
        manual = enabled and not use_sys
        for w in (self.proxy_host, self.proxy_port, self.proxy_username, self.proxy_password):
            w.setEnabled(manual)
        # no_proxy is useful in both manual and system modes
        self.proxy_no_proxy.setEnabled(enabled)

    def _accept(self):
        self._s["proxy_enabled"] = self.proxy_enabled.isChecked()
        self._s["proxy_use_system"] = self.proxy_use_system.isChecked()
        self._s["proxy_host"] = self.proxy_host.text().strip()
        self._s["proxy_port"] = self.proxy_port.text().strip()
        self._s["proxy_username"] = self.proxy_username.text().strip()
        self._s["proxy_password"] = self.proxy_password.text()
        self._s["proxy_no_proxy"] = self.proxy_no_proxy.text().strip()
        self._s["ssl_verify"] = self.ssl_verify.isChecked()
        self._s["follow_redirects"] = self.follow_redirects.isChecked()
        # Rebuild proxy_http / proxy_https from parts
        from src.core.settings_store import proxy_url
        url = proxy_url(self._s)
        self._s["proxy_http"] = url
        self._s["proxy_https"] = url
        # Persist to disk
        save_settings(self._s)
        self.accept()

    def get_settings(self) -> dict:
        return self._s
