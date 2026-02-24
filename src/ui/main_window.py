"""Main application window with tab management."""
from __future__ import annotations
import json
from pathlib import Path
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QAction, QCloseEvent
from PyQt6.QtWidgets import (
    QMainWindow, QTabWidget, QWidget, QSplitter,
    QVBoxLayout, QDockWidget, QInputDialog,
    QMessageBox, QApplication, QMenu,
)

from src.core.http_client import HttpClient, RequestConfig, ResponseData
from src.core.curl_parser import parse_curl, export_curl, CurlRequest
from src.core.history_manager import HistoryManager, HistoryEntry
from src.core.collection_manager import CollectionManager, CollectionRequest
from src.core.settings_store import load_settings
from src.ui.request_panel import RequestPanel
from src.ui.response_panel import ResponsePanel
from src.ui.network_debug_panel import NetworkDebugPanel
from src.ui.history_panel import HistoryPanel
from src.ui.collection_panel import CollectionPanel
from src.ui.settings_dialog import SettingsDialog

_TABS_PATH = Path.home() / ".pm-altr" / "tabs.json"


class _SendWorker(QThread):
    finished = pyqtSignal(object)

    def __init__(self, client: HttpClient, config: RequestConfig):
        super().__init__()
        self._client = client
        self._config = config

    def run(self):
        result = self._client.send(self._config)
        self.finished.emit(result)


class RequestTab(QWidget):
    """A single request/response tab."""

    history_saved = pyqtSignal()
    proxy_settings_requested = pyqtSignal()
    import_curl_requested = pyqtSignal()
    export_curl_requested = pyqtSignal()
    save_to_collection_requested = pyqtSignal()

    def __init__(self, settings: dict, history_mgr: HistoryManager, parent=None):
        super().__init__(parent)
        self._settings = settings
        self._history_mgr = history_mgr
        self._client = HttpClient()
        self._worker = None
        self._last_url = ""
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        splitter = QSplitter(Qt.Orientation.Vertical)

        # Top: request panel + debug panel side by side
        top_splitter = QSplitter(Qt.Orientation.Horizontal)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)

        self.request_panel = RequestPanel(self._settings)
        self.request_panel.send_btn.clicked.connect(self._send)
        self.request_panel.proxy_settings_requested.connect(self.proxy_settings_requested.emit)
        self.request_panel.import_curl_requested.connect(self.import_curl_requested.emit)
        self.request_panel.export_curl_requested.connect(self.export_curl_requested.emit)
        self.request_panel.save_to_collection_requested.connect(
            self.save_to_collection_requested.emit
        )
        left_layout.addWidget(self.request_panel)

        top_splitter.addWidget(left)

        self.debug_panel = NetworkDebugPanel()
        top_splitter.addWidget(self.debug_panel)
        top_splitter.setSizes([700, 300])

        splitter.addWidget(top_splitter)

        self.response_panel = ResponsePanel()
        splitter.addWidget(self.response_panel)
        splitter.setSizes([400, 300])

        layout.addWidget(splitter)

    def _send(self):
        config = self.request_panel.get_config()
        if not config.url:
            QMessageBox.warning(self, "Missing URL", "Please enter a URL.")
            return
        self._last_url = config.url
        proxy_addr = config.proxy_http or config.proxy_https or ""
        self.debug_panel.set_url(config.url, config.proxy_enabled, proxy_addr)
        self.request_panel.send_btn.setText("Sending…")
        self.request_panel.send_btn.setEnabled(False)
        self.response_panel.clear()
        self._worker = _SendWorker(self._client, config)
        self._worker.finished.connect(self._on_response)
        self._worker.start()

    def _on_response(self, data: ResponseData):
        self.request_panel.send_btn.setText("Send")
        self.request_panel.send_btn.setEnabled(True)
        if data.error:
            QMessageBox.critical(self, "Request Error", data.error)
            return
        self.response_panel.show_response(data)
        # Auto-run diagnostics
        self.debug_panel._run()
        # Save to history
        cfg = self.request_panel.get_config()
        entry = HistoryEntry(
            method=cfg.method,
            url=cfg.url,
            request_headers=json.dumps(cfg.headers),
            request_params=json.dumps(cfg.params),
            request_body=cfg.body_json or cfg.body_text or json.dumps(cfg.body_form),
            request_body_type=cfg.body_type,
            response_status=data.status_code,
            response_time_ms=data.response_time_ms,
            response_size_bytes=data.response_size_bytes,
            response_headers=json.dumps(data.headers),
            response_body=data.body[:10000],
        )
        self._history_mgr.save(entry)
        self.history_saved.emit()

    def load_from_curl(self, curl_req: CurlRequest):
        self.request_panel.load_from_curl(curl_req)

    def load_from_history(self, entry: HistoryEntry):
        self.request_panel.load_from_history(entry)

    def get_curl(self) -> str:
        cfg = self.request_panel.get_config()
        body = cfg.body_json or cfg.body_text or ""
        return export_curl(cfg.method, cfg.url, cfg.headers, cfg.params, body, cfg.body_type)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PM-ALTR — HTTP Client")
        self.resize(1280, 800)
        self._settings: dict = load_settings()
        self._history_mgr = HistoryManager()
        self._collection_mgr = CollectionManager()
        self._adding_tab = False
        self._build_ui()
        self._build_menu()
        self._restore_tabs()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)

        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.setMovable(True)
        self.tabs.tabCloseRequested.connect(self._close_tab)
        self.tabs.currentChanged.connect(self._on_current_changed)

        # Insert a permanent "+" tab as the first tab (always index 0)
        self.tabs.addTab(QWidget(), "+")
        # Disable close button on the "+" tab
        self.tabs.tabBar().setTabButton(0, self.tabs.tabBar().ButtonPosition.RightSide, None)
        self.tabs.tabBar().setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tabs.tabBar().customContextMenuRequested.connect(self._tab_context_menu)

        layout.addWidget(self.tabs)

        # History dock — non-closable, always visible
        self._history_panel = HistoryPanel(self._history_mgr)
        self._history_panel.entry_selected.connect(self._load_history_entry)
        history_dock = QDockWidget("History", self)
        history_dock.setWidget(self._history_panel)
        history_dock.setMinimumWidth(280)
        history_dock.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable
            | QDockWidget.DockWidgetFeature.DockWidgetFloatable
        )
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, history_dock)
        self._history_dock = history_dock

        # Collection dock
        self._collection_panel = CollectionPanel(self._collection_mgr)
        self._collection_panel.request_selected.connect(self._load_collection_request)
        collection_dock = QDockWidget("Collections", self)
        collection_dock.setWidget(self._collection_panel)
        collection_dock.setMinimumWidth(280)
        collection_dock.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable
            | QDockWidget.DockWidgetFeature.DockWidgetFloatable
        )
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, collection_dock)
        self._collection_dock = collection_dock
        self.tabifyDockWidget(history_dock, collection_dock)

    def _build_menu(self):
        mb = self.menuBar()

        # File menu
        file_menu = mb.addMenu("File")
        new_tab_action = QAction("New Tab", self)
        new_tab_action.setShortcut("Ctrl+T")
        new_tab_action.triggered.connect(self._new_tab)
        file_menu.addAction(new_tab_action)
        file_menu.addSeparator()
        settings_action = QAction("Settings…", self)
        settings_action.setShortcut("Ctrl+,")
        settings_action.triggered.connect(self._open_settings)
        file_menu.addAction(settings_action)

        # cURL menu
        curl_menu = mb.addMenu("cURL")
        import_action = QAction("Import cURL…", self)
        import_action.setShortcut("Ctrl+I")
        import_action.triggered.connect(self._import_curl)
        curl_menu.addAction(import_action)
        export_action = QAction("Export cURL (copy)", self)
        export_action.setShortcut("Ctrl+E")
        export_action.triggered.connect(self._export_curl)
        curl_menu.addAction(export_action)

        # View menu
        view_menu = mb.addMenu("View")
        toggle_history = QAction("Toggle History", self)
        toggle_history.setShortcut("Ctrl+H")
        toggle_history.triggered.connect(lambda: self._history_dock.setVisible(
            not self._history_dock.isVisible()))
        view_menu.addAction(toggle_history)
        toggle_collections = QAction("Toggle Collections", self)
        toggle_collections.setShortcut("Ctrl+L")
        toggle_collections.triggered.connect(lambda: self._collection_dock.setVisible(
            not self._collection_dock.isVisible()))
        view_menu.addAction(toggle_collections)

    def _on_current_changed(self, index: int):
        if index == 0 and not self._adding_tab and hasattr(self, '_history_panel'):
            self._adding_tab = True
            self._new_tab()
            self._adding_tab = False

    def _new_tab(self, title: str = "New Request"):
        tab = RequestTab(self._settings, self._history_mgr)
        tab.history_saved.connect(self._history_panel.refresh)
        tab.proxy_settings_requested.connect(self._open_settings)
        tab.import_curl_requested.connect(self._import_curl)
        tab.export_curl_requested.connect(self._export_curl)
        tab.save_to_collection_requested.connect(self._save_to_collection)
        idx = self.tabs.addTab(tab, title)
        self.tabs.setCurrentIndex(idx)
        return tab

    def _close_tab(self, index: int):
        # Protect the "+" tab (index 0)
        if index == 0:
            return
        self.tabs.removeTab(index)
        # If no real tabs left, open a fresh one
        if self.tabs.count() <= 1:
            self._new_tab()

    def _tab_context_menu(self, pos):
        index = self.tabs.tabBar().tabAt(pos)
        if index <= 0:
            return
        menu = QMenu(self)
        menu.addAction("Close", lambda: self._close_tab(index))
        menu.addAction("Close Others", lambda: self._close_other_tabs(index))
        menu.addAction("Close All", self._close_all_tabs)
        menu.exec(self.tabs.tabBar().mapToGlobal(pos))

    def _close_other_tabs(self, keep_index: int):
        i = self.tabs.count() - 1
        while i > 0:
            if i != keep_index:
                self.tabs.removeTab(i)
                if keep_index > i:
                    keep_index -= 1
            i -= 1

    def _close_all_tabs(self):
        while self.tabs.count() > 1:
            self.tabs.removeTab(self.tabs.count() - 1)
        self._new_tab()

    def _current_tab(self) -> RequestTab | None:
        w = self.tabs.currentWidget()
        return w if isinstance(w, RequestTab) else None

    def _import_curl(self):
        text, ok = QInputDialog.getMultiLineText(
            self, "Import cURL", "Paste your cURL command:"
        )
        if ok and text.strip():
            curl_req = parse_curl(text.strip())
            if curl_req:
                tab = self._new_tab(curl_req.url[:40] or "Imported")
                tab.load_from_curl(curl_req)
            else:
                QMessageBox.warning(self, "Parse Error", "Could not parse the cURL command.")

    def _export_curl(self):
        tab = self._current_tab()
        if tab:
            url = tab.request_panel.url_edit.text().strip()
            if not url:
                QMessageBox.warning(self, "Export Error", "Please enter a URL first.")
                return
            curl_str = tab.get_curl()
            QApplication.clipboard().setText(curl_str)
            QMessageBox.information(self, "Exported", "cURL command copied to clipboard.")

    def _open_settings(self):
        dlg = SettingsDialog(self._settings, self)
        if dlg.exec():
            # Settings already saved to disk inside dialog._accept()
            # Refresh toggles in all tabs
            for i in range(self.tabs.count()):
                tab = self.tabs.widget(i)
                if isinstance(tab, RequestTab):
                    rp = tab.request_panel
                    rp.ssl_check.setChecked(self._settings.get("ssl_verify", True))
                    rp.redirect_check.setChecked(self._settings.get("follow_redirects", True))
                    rp.proxy_check.setChecked(self._settings.get("proxy_enabled", False))

    def _load_history_entry(self, entry: HistoryEntry):
        tab = self._new_tab(entry.url[:40] or entry.method)
        tab.load_from_history(entry)
        # Refresh history panel after new sends
        self._history_panel.refresh()

    # --- Tab state persistence ---

    def _save_tabs(self):
        tabs_data = []
        for i in range(1, self.tabs.count()):  # skip index 0 ("+" tab)
            tab = self.tabs.widget(i)
            if isinstance(tab, RequestTab):
                tabs_data.append({
                    "title": self.tabs.tabText(i),
                    "state": tab.request_panel.get_tab_state(),
                })
        active = max(self.tabs.currentIndex() - 1, 0)  # offset for "+" tab
        payload = {"tabs": tabs_data, "active": active}
        _TABS_PATH.parent.mkdir(parents=True, exist_ok=True)
        _TABS_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    def _restore_tabs(self):
        if _TABS_PATH.exists():
            try:
                payload = json.loads(_TABS_PATH.read_text(encoding="utf-8"))
                tabs_data = payload.get("tabs", [])
                active = payload.get("active", 0)
                for td in tabs_data:
                    title = td.get("title", "Restored")
                    tab = self._new_tab(title)
                    tab.request_panel.load_tab_state(td.get("state", {}))
                if self.tabs.count() > 1:  # has real tabs beyond "+"
                    self.tabs.setCurrentIndex(min(active + 1, self.tabs.count() - 1))
                    return
            except Exception:
                pass
        # Fallback: open a blank tab
        self._new_tab()

    # --- Collection helpers ---

    def _save_to_collection(self):
        tab = self.tabs.currentWidget()
        if isinstance(tab, RequestTab):
            state = tab.request_panel.get_tab_state()
            self._collection_panel.save_current_request(state)

    def _load_collection_request(self, req: CollectionRequest):
        tab = self._new_tab(req.name or req.url[:30])
        state = {
            "method": req.method,
            "url": req.url,
            "headers": json.loads(req.headers) if req.headers else {},
            "params": json.loads(req.params) if req.params else {},
            "body_type": req.body_type or "none",
            "body_text": req.body or "",
            "auth_type": req.auth_type or "none",
            "auth_username": req.auth_username or "",
            "auth_token": req.auth_token or "",
        }
        tab.request_panel.load_tab_state(state)

    def closeEvent(self, event: QCloseEvent):
        self._save_tabs()
        super().closeEvent(event)
