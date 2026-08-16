from __future__ import annotations

import os
import sys

from PyQt6.QtCore import QPoint, Qt
from PyQt6.QtGui import QColor, QIcon, QPainter, QPixmap, QPolygon
from PyQt6.QtWidgets import QApplication, QMenu, QSystemTrayIcon, QWidget

from hazedrop.assets import LOGO_PATH
from hazedrop.i18n import t

_ICON_SIZES = (16, 22, 24, 32, 48, 64, 128, 256)


def load_app_icon() -> QIcon:
    if os.path.exists(LOGO_PATH):
        source = QPixmap(LOGO_PATH)
        if not source.isNull():
            icon = QIcon()
            for size in _ICON_SIZES:
                icon.addPixmap(source.scaled(
                    size, size,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                ))
            return icon

    # Fallback: a white diamond, drawn at a few sizes so the tray does not
    # get a blurry upscale of a 32px bitmap.
    icon = QIcon()
    for size in (16, 32, 64):
        px = QPixmap(size, size)
        px.fill(QColor(0, 0, 0, 0))
        painter = QPainter(px)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QColor(255, 255, 255))
        painter.setPen(Qt.PenStyle.NoPen)
        edge = size - 1
        mid = size // 2
        painter.drawPolygon(QPolygon([
            QPoint(mid, 0), QPoint(edge, mid), QPoint(mid, edge), QPoint(0, mid),
        ]))
        painter.end()
        icon.addPixmap(px)
    return icon


# Kept as an alias: the old private name is referenced by packaging scripts.
_load_app_icon = load_app_icon


class HazeTray(QSystemTrayIcon):
    def __init__(self, window: QWidget, parent=None) -> None:
        super().__init__(parent)
        self._window = window
        self.setIcon(load_app_icon())
        self.setToolTip("HazeDrop")
        self._build_menu()
        self.activated.connect(self._on_activated)

    def _build_menu(self) -> None:
        menu = QMenu()
        self._show_action = menu.addAction(t("tray_show"))
        self._show_action.triggered.connect(self._show_window)
        self._hide_action = menu.addAction(t("tray_hide"))
        self._hide_action.triggered.connect(self._window.hide)
        menu.addSeparator()
        self._quit_action = menu.addAction(t("tray_quit"))
        self._quit_action.triggered.connect(self._quit)
        self._menu = menu
        self.setContextMenu(menu)

    def retranslate(self) -> None:
        self._show_action.setText(t("tray_show"))
        self._hide_action.setText(t("tray_hide"))
        self._quit_action.setText(t("tray_quit"))

    # ── Slots ─────────────────────────────────────────────────────

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            if self._window.isVisible() and not self._window.isMinimized():
                self._window.hide()
            else:
                self._show_window()

    def _show_window(self) -> None:
        self._window.showNormal()
        self._window.raise_()
        self._window.activateWindow()

    def _quit(self) -> None:
        self.hide()
        QApplication.quit()
        sys.exit(0)

    # ── Public API ────────────────────────────────────────────────

    def notify(self, title: str, msg: str) -> None:
        if QSystemTrayIcon.supportsMessages():
            self.showMessage(title, msg, load_app_icon(), 4000)
