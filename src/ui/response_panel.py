"""Response panel: metrics bar, prettified body, headers, raw."""
from __future__ import annotations
import json
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QTabWidget, QTextEdit, QTableWidget, QTableWidgetItem,
    QHeaderView, QFrame,
)

try:
    from pygments import highlight
    from pygments.lexers import JsonLexer
    from pygments.formatters import HtmlFormatter
    _HAS_PYGMENTS = True
except ImportError:
    _HAS_PYGMENTS = False

from src.core.http_client import ResponseData


def _size_human(b: int) -> str:
    if b < 1024:
        return f"{b} B"
    elif b < 1024 * 1024:
        return f"{b / 1024:.1f} KB"
    else:
        return f"{b / 1024 / 1024:.1f} MB"


_STATUS_COLORS = {
    2: "#27ae60",
    3: "#f39c12",
    4: "#e74c3c",
    5: "#c0392b",
}


class ResponsePanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Metrics bar
        metrics_frame = QFrame()
        metrics_frame.setFrameShape(QFrame.Shape.StyledPanel)
        metrics_layout = QHBoxLayout(metrics_frame)
        metrics_layout.setContentsMargins(8, 4, 8, 4)

        self.status_label = QLabel("—")
        self.status_label.setFont(QFont("", 12, QFont.Weight.Bold))
        self.time_label = QLabel("—")
        self.size_label = QLabel("—")

        for lbl in (self.status_label, self.time_label, self.size_label):
            metrics_layout.addWidget(lbl)
            sep = QFrame()
            sep.setFrameShape(QFrame.Shape.VLine)
            sep.setFrameShadow(QFrame.Shadow.Sunken)
            metrics_layout.addWidget(sep)

        metrics_layout.addStretch()
        layout.addWidget(metrics_frame)

        # Tabs
        self.tabs = QTabWidget()
        self.body_view = QTextEdit()
        self.body_view.setReadOnly(True)
        self.body_view.setFont(QFont("Menlo, Consolas, monospace", 11))

        self.headers_table = QTableWidget()
        self.headers_table.setColumnCount(2)
        self.headers_table.setHorizontalHeaderLabels(["Header", "Value"])
        self.headers_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.headers_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        self.raw_view = QTextEdit()
        self.raw_view.setReadOnly(True)
        self.raw_view.setFont(QFont("Menlo, Consolas, monospace", 10))

        self.tabs.addTab(self.body_view, "Body")
        self.tabs.addTab(self.headers_table, "Headers")
        self.tabs.addTab(self.raw_view, "Raw")
        layout.addWidget(self.tabs)

    def clear(self):
        self.status_label.setText("—")
        self.time_label.setText("—")
        self.size_label.setText("—")
        self.body_view.clear()
        self.headers_table.setRowCount(0)
        self.raw_view.clear()

    def show_response(self, data: ResponseData):
        # Metrics
        color = _STATUS_COLORS.get(data.status_code // 100, "#888")
        self.status_label.setText(f"<span style='color:{color}'>{data.status_code} {data.reason}</span>")
        self.time_label.setText(f"⏱ {data.response_time_ms} ms")
        self.size_label.setText(f"📦 {_size_human(data.response_size_bytes)}")

        # Body
        body = data.body
        ct = data.content_type.lower()
        if "json" in ct or self._looks_json(body):
            body = self._prettify_json(body)
            if _HAS_PYGMENTS:
                self._render_html(self._pygments_json(body))
            else:
                self.body_view.setPlainText(body)
        else:
            self.body_view.setPlainText(body)

        # Headers
        self.headers_table.setRowCount(0)
        for k, v in data.headers.items():
            row = self.headers_table.rowCount()
            self.headers_table.insertRow(row)
            self.headers_table.setItem(row, 0, QTableWidgetItem(k))
            self.headers_table.setItem(row, 1, QTableWidgetItem(v))

        # Raw
        raw_lines = [f"HTTP/1.1 {data.status_code} {data.reason}"]
        for k, v in data.headers.items():
            raw_lines.append(f"{k}: {v}")
        raw_lines += ["", data.body]
        self.raw_view.setPlainText("\n".join(raw_lines))

    def _looks_json(self, s: str) -> bool:
        s = s.strip()
        return (s.startswith("{") and s.endswith("}")) or (s.startswith("[") and s.endswith("]"))

    def _prettify_json(self, s: str) -> str:
        try:
            return json.dumps(json.loads(s), indent=2, ensure_ascii=False)
        except Exception:
            return s

    def _pygments_json(self, s: str) -> str:
        formatter = HtmlFormatter(style="monokai", full=False, noclasses=True)
        return highlight(s, JsonLexer(), formatter)

    def _render_html(self, html: str):
        formatter = HtmlFormatter(style="monokai")
        bg = formatter.style.background_color or "#272822"
        full = f"""<html><body style='background:{bg};color:#f8f8f2;
            font-family:Menlo,Consolas,monospace;font-size:12px;'>{html}</body></html>"""
        self.body_view.setHtml(full)
