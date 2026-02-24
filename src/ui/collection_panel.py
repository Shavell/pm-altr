"""Collection browser panel with tree view."""
from __future__ import annotations
import json
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QTreeWidget, QTreeWidgetItem, QLabel, QInputDialog,
    QMessageBox, QMenu, QFileDialog,
)
from src.core.collection_manager import CollectionManager, CollectionRequest


class CollectionPanel(QWidget):
    request_selected = pyqtSignal(object)  # emits CollectionRequest

    def __init__(self, manager: CollectionManager, parent=None):
        super().__init__(parent)
        self._mgr = manager
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        layout.addWidget(QLabel("Collections"))

        btn_row = QHBoxLayout()
        new_btn = QPushButton("+ New")
        new_btn.clicked.connect(self._new_collection)
        import_btn = QPushButton("📥 Import")
        import_btn.clicked.connect(self._import_menu)
        export_btn = QPushButton("📤 Export")
        export_btn.clicked.connect(self._export_collection)
        btn_row.addWidget(new_btn)
        btn_row.addWidget(import_btn)
        btn_row.addWidget(export_btn)
        layout.addLayout(btn_row)

        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._context_menu)
        self.tree.itemDoubleClicked.connect(self._on_double_click)
        layout.addWidget(self.tree)

    def refresh(self):
        self.tree.clear()
        collections = self._mgr.get_collections()
        for col in collections:
            col_item = QTreeWidgetItem(self.tree)
            col_item.setText(0, f"📁 {col.name}")
            col_item.setData(0, Qt.ItemDataRole.UserRole, ("collection", col.id))
            col_item.setFlags(col_item.flags() | Qt.ItemFlag.ItemIsAutoTristate)

            reqs = self._mgr.get_requests(col.id)
            for req in reqs:
                req_item = QTreeWidgetItem(col_item)
                req_item.setText(0, f"[{req.method}] {req.name or req.url[:40]}")
                req_item.setData(0, Qt.ItemDataRole.UserRole, ("request", req))

    def _new_collection(self):
        name, ok = QInputDialog.getText(self, "New Collection", "Collection name:")
        if ok and name.strip():
            self._mgr.create_collection(name.strip())
            self.refresh()

    def _import_menu(self):
        menu = QMenu(self)
        menu.addAction("Import JSON Collection…", self._import_json)
        menu.addAction("Import OpenAPI Spec…", self._import_openapi)
        menu.exec(self.mapToGlobal(self.sender().pos()))

    def _import_json(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Import Collection", "", "JSON Files (*.json);;All Files (*)"
        )
        if path:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._mgr.import_collection(data)
                self.refresh()
            except Exception as e:
                QMessageBox.warning(self, "Import Error", str(e))

    def _import_openapi(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Import OpenAPI Spec", "",
            "YAML/JSON Files (*.yaml *.yml *.json);;All Files (*)"
        )
        if path:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
                # Try JSON first, then YAML
                try:
                    spec = json.loads(content)
                except json.JSONDecodeError:
                    try:
                        import yaml  # noqa: F811
                        spec = yaml.safe_load(content)
                    except ImportError:
                        QMessageBox.warning(
                            self, "YAML Support",
                            "Install PyYAML to import YAML specs:\npip install pyyaml"
                        )
                        return
                self._mgr.import_openapi(spec)
                self.refresh()
            except Exception as e:
                QMessageBox.warning(self, "Import Error", str(e))

    def _export_collection(self):
        item = self.tree.currentItem()
        if not item:
            QMessageBox.warning(self, "Export", "Select a collection first.")
            return
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data or data[0] != "collection":
            # Maybe a request item — get parent
            parent = item.parent()
            if parent:
                data = parent.data(0, Qt.ItemDataRole.UserRole)
        if not data or data[0] != "collection":
            QMessageBox.warning(self, "Export", "Select a collection first.")
            return
        cid = data[1]
        export_data = self._mgr.export_collection(cid)
        if not export_data:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Collection", f"{export_data['name']}.json",
            "JSON Files (*.json)"
        )
        if path:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            QMessageBox.information(self, "Exported", f"Saved to {path}")

    def _on_double_click(self, item: QTreeWidgetItem, column: int):
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if data and data[0] == "request":
            self.request_selected.emit(data[1])

    def _context_menu(self, pos):
        item = self.tree.itemAt(pos)
        if not item:
            return
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return
        menu = QMenu(self)
        if data[0] == "collection":
            cid = data[1]
            menu.addAction("Rename", lambda: self._rename_collection(cid))
            menu.addAction("Delete", lambda: self._delete_collection(cid))
        elif data[0] == "request":
            req = data[1]
            menu.addAction("Delete Request", lambda: self._delete_request(req.id))
        menu.exec(self.tree.viewport().mapToGlobal(pos))

    def _rename_collection(self, cid: int):
        name, ok = QInputDialog.getText(self, "Rename Collection", "New name:")
        if ok and name.strip():
            self._mgr.rename_collection(cid, name.strip())
            self.refresh()

    def _delete_collection(self, cid: int):
        if QMessageBox.question(
            self, "Delete Collection", "Delete this collection and all its requests?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        ) == QMessageBox.StandardButton.Yes:
            self._mgr.delete_collection(cid)
            self.refresh()

    def _delete_request(self, req_id: int):
        self._mgr.delete_request(req_id)
        self.refresh()

    def save_current_request(self, tab_state: dict):
        """Save current tab state into a collection via dialog."""
        collections = self._mgr.get_collections()
        if not collections:
            QMessageBox.information(
                self, "No Collections",
                "Create a collection first."
            )
            return
        names = [c.name for c in collections]
        name, ok = QInputDialog.getItem(
            self, "Save to Collection", "Choose collection:", names, 0, False
        )
        if not ok:
            return
        col = next(c for c in collections if c.name == name)
        req_name, ok2 = QInputDialog.getText(
            self, "Request Name", "Name for this request:",
            text=tab_state.get("url", "")[:50]
        )
        if not ok2:
            return
        req = CollectionRequest(
            name=req_name,
            method=tab_state.get("method", "GET"),
            url=tab_state.get("url", ""),
            headers=json.dumps(tab_state.get("headers", {})),
            params=json.dumps(tab_state.get("params", {})),
            body=tab_state.get("body_text", ""),
            body_type=tab_state.get("body_type", "none"),
            auth_type=tab_state.get("auth_type", "none"),
            auth_username=tab_state.get("auth_username", ""),
            auth_token=tab_state.get("auth_token", ""),
        )
        self._mgr.add_request(col.id, req)
        self.refresh()
