"""History dock widget."""
from __future__ import annotations
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QListWidget, QListWidgetItem, QLineEdit, QLabel, QMessageBox,
)
from src.core.history_manager import HistoryEntry, HistoryManager


class HistoryPanel(QWidget):
    entry_selected = pyqtSignal(object)  # emits HistoryEntry

    def __init__(self, manager: HistoryManager, parent=None):
        super().__init__(parent)
        self._mgr = manager
        self._entries: list[HistoryEntry] = []
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        layout.addWidget(QLabel("Request History"))

        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search…")
        self.search_box.textChanged.connect(self._search)
        layout.addWidget(self.search_box)

        self.list_widget = QListWidget()
        self.list_widget.itemDoubleClicked.connect(self._on_double_click)
        layout.addWidget(self.list_widget)

        btn_row = QHBoxLayout()
        refresh_btn = QPushButton("↻ Refresh")
        refresh_btn.clicked.connect(self.refresh)
        clear_btn = QPushButton("🗑 Clear All")
        clear_btn.clicked.connect(self._clear_all)
        btn_row.addWidget(refresh_btn)
        btn_row.addWidget(clear_btn)
        layout.addLayout(btn_row)

    def refresh(self):
        self._entries = self._mgr.get_all()
        self._populate(self._entries)

    def _search(self, text: str):
        if text.strip():
            entries = self._mgr.search(text.strip())
        else:
            entries = self._entries
        self._populate(entries)

    def _populate(self, entries: list[HistoryEntry]):
        self.list_widget.clear()
        for e in entries:
            ts = e.timestamp[:19] if e.timestamp else "?"
            label = f"[{e.method}] {e.url}  —  {e.response_status}  ({ts})"
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, e)
            self.list_widget.addItem(item)

    def _on_double_click(self, item: QListWidgetItem):
        entry: HistoryEntry = item.data(Qt.ItemDataRole.UserRole)
        if entry:
            self.entry_selected.emit(entry)

    def _clear_all(self):
        if QMessageBox.question(self, "Clear History", "Delete all history entries?",
                                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                                ) == QMessageBox.StandardButton.Yes:
            self._mgr.clear()
            self.refresh()
