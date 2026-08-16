from __future__ import annotations

from typing import Literal

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QWidget

from hazedrop.i18n import t

Status = Literal["idle", "starting", "active", "error"]


class TitleBar(QWidget):
    panic_triggered = pyqtSignal()
    renew_circuit = pyqtSignal()

    def __init__(self, main_win: QWidget) -> None:
        super().__init__(main_win)
        self._win = main_win
        self.setObjectName("titleBar")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setFixedHeight(44)
        # Track state instead of re-deriving it from the visible label, which
        # is what made the old retranslate() guess (and get it wrong).
        self._status: Status = "idle"
        self._detail: str = ""
        self._build()

    def _build(self) -> None:
        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 0, 8, 0)
        lay.setSpacing(8)
        vc = Qt.AlignmentFlag.AlignVCenter

        name = QLabel("HAZEDROP")
        name.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        name.setStyleSheet(
            "font-size: 12px; font-weight: 800; color: #ffffff;"
            "letter-spacing: 3.5px; background: transparent;"
        )
        lay.addWidget(name, 0, vc)
        lay.addSpacing(6)

        self._badge = QPushButton(t("protocol_badge"))
        self._badge.setObjectName("protocolBadge")
        self._badge.setFlat(True)
        self._badge.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        # A status chip, not a control — do not offer a click affordance.
        self._badge.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        lay.addWidget(self._badge, 0, vc)

        lay.addStretch(1)

        self._renew_btn = QPushButton("⟳")
        self._renew_btn.setObjectName("winBtn")
        self._renew_btn.setFixedSize(28, 28)
        self._renew_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._renew_btn.setToolTip(t("renew_circuit_tip"))
        self._renew_btn.setVisible(False)
        self._renew_btn.clicked.connect(self.renew_circuit.emit)
        lay.addWidget(self._renew_btn, 0, vc)

        self._panic_btn = QPushButton(t("panic"))
        self._panic_btn.setObjectName("panicBtn")
        self._panic_btn.setFixedHeight(24)
        self._panic_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._panic_btn.setToolTip(t("panic_tip"))
        self._panic_btn.clicked.connect(self.panic_triggered.emit)
        lay.addWidget(self._panic_btn, 0, vc)

        lay.addSpacing(6)

        self._min_btn = self._win_button("−", "winBtn", self._win.showMinimized)
        lay.addWidget(self._min_btn, 0, vc)

        self._max_btn = self._win_button("□", "winBtn", self._toggle_maximized)
        lay.addWidget(self._max_btn, 0, vc)

        self._close_btn = self._win_button("✕", "winBtnClose", self._win.close)
        lay.addWidget(self._close_btn, 0, vc)

        self.retranslate()

    def _win_button(self, glyph: str, obj_name: str, callback) -> QPushButton:
        btn = QPushButton(glyph)
        btn.setObjectName(obj_name)
        btn.setFixedSize(28, 28)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        btn.clicked.connect(callback)
        return btn

    # ── Window controls ───────────────────────────────────────────

    def _toggle_maximized(self) -> None:
        if self._win.isMaximized():
            self._win.showNormal()
        else:
            self._win.showMaximized()
        self.sync_maximize_state()

    def sync_maximize_state(self) -> None:
        maximized = self._win.isMaximized()
        self._max_btn.setText("❐" if maximized else "□")
        self._max_btn.setToolTip(t("restore_tip") if maximized else t("maximize_tip"))

    # ── Drag ──────────────────────────────────────────────────────

    def mousePressEvent(self, event) -> None:  # noqa: N802 - Qt naming
        if event.button() == Qt.MouseButton.LeftButton:
            handle = self._win.windowHandle()
            if handle is not None:
                handle.startSystemMove()
        event.accept()

    def mouseDoubleClickEvent(self, event) -> None:  # noqa: N802 - Qt naming
        if event.button() == Qt.MouseButton.LeftButton:
            self._toggle_maximized()
        event.accept()

    # ── i18n ──────────────────────────────────────────────────────

    def retranslate(self) -> None:
        self._panic_btn.setText(t("panic"))
        self._panic_btn.setToolTip(t("panic_tip"))
        self._renew_btn.setToolTip(t("renew_circuit_tip"))
        self._min_btn.setToolTip(t("minimize_tip"))
        self._close_btn.setToolTip(t("close_tip"))
        self.sync_maximize_state()
        # Re-render the chip from the tracked state rather than parsing the
        # text that happens to be on screen.
        self.set_tor_status(self._status, self._detail)

    # ── Status ────────────────────────────────────────────────────

    def set_tor_status(self, status: Status, detail: str = "") -> None:
        self._status = status
        self._detail = detail

        if status == "active":
            obj, text = "protocolBadgeActive", t("protocol_badge")
        elif status == "starting":
            obj, text = "protocolBadge", (detail or t("protocol_connecting"))
        elif status == "error":
            obj, text = "protocolBadge", t("protocol_error")
        else:
            obj, text = "protocolBadge", t("protocol_badge")

        self._badge.setObjectName(obj)
        self._badge.setText(text)
        self._badge.setToolTip(t(f"tor_status_{status}"))
        self._renew_btn.setVisible(status == "active")
        self._badge.style().unpolish(self._badge)
        self._badge.style().polish(self._badge)
