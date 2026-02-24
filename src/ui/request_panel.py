"""Request builder panel: URL, method, params, headers, body, auth, toggles."""
from __future__ import annotations
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QComboBox, QPushButton, QCheckBox,
    QTabWidget, QTableWidget, QTableWidgetItem,
    QHeaderView, QTextEdit, QStackedWidget,
    QFormLayout,
)
from src.core.http_client import RequestConfig
from src.core.curl_parser import CurlRequest


HTTP_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"]


class _KeyValueTable(QWidget):
    """Editable key-value table with Add / Remove rows."""
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["", "Key", "Value"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.setColumnWidth(0, 24)
        layout.addWidget(self.table)

        btn_row = QHBoxLayout()
        add_btn = QPushButton("+ Add Row")
        add_btn.clicked.connect(self.add_row)
        btn_row.addWidget(add_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

    def add_row(self, key: str = "", value: str = ""):
        row = self.table.rowCount()
        self.table.insertRow(row)
        chk = QCheckBox()
        chk.setChecked(True)
        chk_widget = QWidget()
        chk_layout = QHBoxLayout(chk_widget)
        chk_layout.addWidget(chk)
        chk_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        chk_layout.setContentsMargins(0, 0, 0, 0)
        self.table.setCellWidget(row, 0, chk_widget)
        self.table.setItem(row, 1, QTableWidgetItem(key))
        self.table.setItem(row, 2, QTableWidgetItem(value))

    def get_dict(self) -> dict:
        result = {}
        for row in range(self.table.rowCount()):
            chk_widget = self.table.cellWidget(row, 0)
            if chk_widget:
                chk = chk_widget.findChild(QCheckBox)
                if chk and not chk.isChecked():
                    continue
            k_item = self.table.item(row, 1)
            v_item = self.table.item(row, 2)
            k = k_item.text().strip() if k_item else ""
            v = v_item.text().strip() if v_item else ""
            if k:
                result[k] = v
        return result

    def set_dict(self, d: dict):
        self.table.setRowCount(0)
        for k, v in d.items():
            self.add_row(str(k), str(v))

    def clear(self):
        self.table.setRowCount(0)


class RequestPanel(QWidget):
    proxy_settings_requested = pyqtSignal()
    import_curl_requested = pyqtSignal()
    export_curl_requested = pyqtSignal()
    save_to_collection_requested = pyqtSignal()

    def __init__(self, settings: dict, parent=None):
        super().__init__(parent)
        self._settings = settings
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # URL bar row
        url_row = QHBoxLayout()
        self.method_combo = QComboBox()
        self.method_combo.addItems(HTTP_METHODS)
        self.method_combo.setMinimumWidth(90)
        url_row.addWidget(self.method_combo)

        self.url_edit = QLineEdit()
        self.url_edit.setPlaceholderText("https://example.com/api/endpoint")
        url_row.addWidget(self.url_edit)

        self.send_btn = QPushButton("Send")
        self.send_btn.setMinimumWidth(80)
        self.send_btn.setStyleSheet("background:#2980b9;color:white;font-weight:bold;border-radius:4px;padding:4px 12px;")
        url_row.addWidget(self.send_btn)
        layout.addLayout(url_row)

        # Toggles + cURL buttons row
        toggle_row = QHBoxLayout()
        self.ssl_check = QCheckBox("SSL Verify")
        self.ssl_check.setChecked(self._settings.get("ssl_verify", True))
        self.redirect_check = QCheckBox("Follow Redirects")
        self.redirect_check.setChecked(self._settings.get("follow_redirects", True))
        self.proxy_check = QCheckBox("Use Proxy")
        self.proxy_check.setChecked(self._settings.get("proxy_enabled", False))
        self.proxy_check.toggled.connect(self._on_proxy_toggled)
        toggle_row.addWidget(self.ssl_check)
        toggle_row.addWidget(self.redirect_check)
        toggle_row.addWidget(self.proxy_check)
        toggle_row.addStretch()

        import_btn = QPushButton("📥 Import cURL")
        import_btn.clicked.connect(self.import_curl_requested.emit)
        export_btn = QPushButton("📤 Export cURL")
        export_btn.clicked.connect(self.export_curl_requested.emit)
        save_col_btn = QPushButton("💾 Save to Collection")
        save_col_btn.clicked.connect(self.save_to_collection_requested.emit)
        toggle_row.addWidget(import_btn)
        toggle_row.addWidget(export_btn)
        toggle_row.addWidget(save_col_btn)
        layout.addLayout(toggle_row)

        # Sub-tabs: Params / Headers / Body / Auth
        self.sub_tabs = QTabWidget()
        self.sub_tabs.setDocumentMode(True)

        # Params
        self.params_table = _KeyValueTable()
        self.sub_tabs.addTab(self.params_table, "Params")

        # Headers
        self.headers_table = _KeyValueTable()
        self.sub_tabs.addTab(self.headers_table, "Headers")

        # Body
        body_widget = QWidget()
        body_layout = QVBoxLayout(body_widget)
        body_layout.setContentsMargins(0, 4, 0, 0)
        body_type_row = QHBoxLayout()
        body_type_row.addWidget(QLabel("Content Type:"))
        self.body_type_combo = QComboBox()
        self.body_type_combo.addItems(["none", "json", "form-data", "x-www-form-urlencoded", "text"])
        self.body_type_combo.currentTextChanged.connect(self._on_body_type_change)
        body_type_row.addWidget(self.body_type_combo)
        body_type_row.addStretch()
        body_layout.addLayout(body_type_row)

        self.body_stack = QStackedWidget()

        # none
        none_placeholder = QLabel("No body for this request.")
        none_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.body_stack.addWidget(none_placeholder)  # index 0

        # json / text — shared text editor
        self.body_text_edit = QTextEdit()
        self.body_text_edit.setFont(QFont("Menlo, Consolas, monospace", 11))
        self.body_text_edit.setPlaceholderText('{"key": "value"}')
        self.body_stack.addWidget(self.body_text_edit)  # index 1

        # form-data
        self.body_form_table = _KeyValueTable()
        self.body_stack.addWidget(self.body_form_table)  # index 2

        # x-www-form-urlencoded
        self.body_urlenc_table = _KeyValueTable()
        self.body_stack.addWidget(self.body_urlenc_table)  # index 3

        # text/plain (reuse body_text_edit via a second slot)
        plain_placeholder = QLabel("")  # won't be used; handled in get_config
        self.body_stack.addWidget(plain_placeholder)  # index 4

        body_layout.addWidget(self.body_stack)
        self.sub_tabs.addTab(body_widget, "Body")

        # Auth
        auth_widget = QWidget()
        auth_layout = QVBoxLayout(auth_widget)
        auth_layout.setContentsMargins(4, 4, 4, 4)
        auth_type_row = QHBoxLayout()
        auth_type_row.addWidget(QLabel("Auth Type:"))
        self.auth_type_combo = QComboBox()
        self.auth_type_combo.addItems(["none", "basic", "bearer"])
        self.auth_type_combo.currentTextChanged.connect(self._on_auth_type_change)
        auth_type_row.addWidget(self.auth_type_combo)
        auth_type_row.addStretch()
        auth_layout.addLayout(auth_type_row)

        self.auth_stack = QStackedWidget()
        no_auth = QLabel("No authentication.")
        no_auth.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.auth_stack.addWidget(no_auth)  # 0

        basic_widget = QWidget()
        basic_form = QFormLayout(basic_widget)
        self.basic_user = QLineEdit()
        self.basic_user.setPlaceholderText("username")
        self.basic_pass = QLineEdit()
        self.basic_pass.setEchoMode(QLineEdit.EchoMode.Password)
        self.basic_pass.setPlaceholderText("password")
        basic_form.addRow("Username:", self.basic_user)
        basic_form.addRow("Password:", self.basic_pass)
        self.auth_stack.addWidget(basic_widget)  # 1

        bearer_widget = QWidget()
        bearer_form = QFormLayout(bearer_widget)
        self.bearer_token = QLineEdit()
        self.bearer_token.setPlaceholderText("token")
        bearer_form.addRow("Token:", self.bearer_token)
        self.auth_stack.addWidget(bearer_widget)  # 2

        auth_layout.addWidget(self.auth_stack)
        auth_layout.addStretch()
        self.sub_tabs.addTab(auth_widget, "Auth")

        layout.addWidget(self.sub_tabs)

    # --- signal handlers ---
    def _on_proxy_toggled(self, checked: bool):
        if checked:
            host = self._settings.get("proxy_host", "").strip()
            if not host:
                # No proxy configured yet — open settings dialog
                self.proxy_settings_requested.emit()
                # Re-check: if still no proxy, uncheck
                if not self._settings.get("proxy_host", "").strip():
                    self.proxy_check.setChecked(False)

    def _on_body_type_change(self, t: str):
        idx_map = {"none": 0, "json": 1, "form-data": 2, "x-www-form-urlencoded": 3, "text": 1}
        self.body_stack.setCurrentIndex(idx_map.get(t, 0))
        if t == "json":
            self.body_text_edit.setPlaceholderText('{"key": "value"}')
        elif t == "text":
            self.body_text_edit.setPlaceholderText("Plain text body…")

    def _on_auth_type_change(self, t: str):
        idx_map = {"none": 0, "basic": 1, "bearer": 2}
        self.auth_stack.setCurrentIndex(idx_map.get(t, 0))

    # --- public API ---
    def get_config(self) -> RequestConfig:
        s = self._settings
        cfg = RequestConfig(
            method=self.method_combo.currentText(),
            url=self.url_edit.text().strip(),
            headers=self.headers_table.get_dict(),
            params=self.params_table.get_dict(),
            body_type=self.body_type_combo.currentText(),
            ssl_verify=self.ssl_check.isChecked(),
            follow_redirects=self.redirect_check.isChecked(),
            proxy_enabled=self.proxy_check.isChecked(),
            proxy_use_system=s.get("proxy_use_system", False),
            proxy_http=s.get("proxy_http", ""),
            proxy_https=s.get("proxy_https", ""),
            proxy_username=s.get("proxy_username", ""),
            proxy_password=s.get("proxy_password", ""),
            proxy_no_proxy=s.get("proxy_no_proxy", ""),
            auth_type=self.auth_type_combo.currentText(),
            auth_username=self.basic_user.text(),
            auth_password=self.basic_pass.text(),
            auth_token=self.bearer_token.text(),
        )
        bt = cfg.body_type
        if bt in ("json", "text"):
            cfg.body_json = self.body_text_edit.toPlainText()
            cfg.body_text = cfg.body_json
        elif bt == "form-data":
            cfg.body_form = self.body_form_table.get_dict()
        elif bt == "x-www-form-urlencoded":
            cfg.body_form = self.body_urlenc_table.get_dict()
        return cfg

    def load_from_curl(self, curl_req: CurlRequest):
        self.method_combo.setCurrentText(curl_req.method)
        self.url_edit.setText(curl_req.url)
        self.headers_table.set_dict(curl_req.headers)
        self.params_table.set_dict(curl_req.params)
        self.ssl_check.setChecked(curl_req.ssl_verify)
        self.redirect_check.setChecked(curl_req.follow_redirects)
        if curl_req.body:
            self.body_type_combo.setCurrentText(curl_req.body_type or "text")
            self.body_text_edit.setPlainText(curl_req.body)
        if curl_req.auth_type != "none":
            self.auth_type_combo.setCurrentText(curl_req.auth_type)
            self.basic_user.setText(curl_req.auth_username)
            self.basic_pass.setText(curl_req.auth_password)

    def load_from_history(self, entry):
        import json as _json
        self.method_combo.setCurrentText(entry.method)
        self.url_edit.setText(entry.url)
        try:
            self.headers_table.set_dict(_json.loads(entry.request_headers or "{}"))
        except Exception:
            pass
        try:
            self.params_table.set_dict(_json.loads(entry.request_params or "{}"))
        except Exception:
            pass
        if entry.request_body:
            self.body_type_combo.setCurrentText(entry.request_body_type or "text")
            self.body_text_edit.setPlainText(entry.request_body)

    def get_tab_state(self) -> dict:
        """Serialize current tab state to a dict for persistence."""
        return {
            "method": self.method_combo.currentText(),
            "url": self.url_edit.text(),
            "headers": self.headers_table.get_dict(),
            "params": self.params_table.get_dict(),
            "body_type": self.body_type_combo.currentText(),
            "body_text": self.body_text_edit.toPlainText(),
            "body_form": self.body_form_table.get_dict(),
            "body_urlenc": self.body_urlenc_table.get_dict(),
            "auth_type": self.auth_type_combo.currentText(),
            "auth_username": self.basic_user.text(),
            "auth_token": self.bearer_token.text(),
        }

    def load_tab_state(self, state: dict):
        """Restore tab state from a dict."""
        self.method_combo.setCurrentText(state.get("method", "GET"))
        self.url_edit.setText(state.get("url", ""))
        self.headers_table.set_dict(state.get("headers", {}))
        self.params_table.set_dict(state.get("params", {}))
        self.body_type_combo.setCurrentText(state.get("body_type", "none"))
        self.body_text_edit.setPlainText(state.get("body_text", ""))
        self.body_form_table.set_dict(state.get("body_form", {}))
        self.body_urlenc_table.set_dict(state.get("body_urlenc", {}))
        self.auth_type_combo.setCurrentText(state.get("auth_type", "none"))
        self.basic_user.setText(state.get("auth_username", ""))
        self.bearer_token.setText(state.get("auth_token", ""))
