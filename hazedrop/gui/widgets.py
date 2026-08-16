"""Reusable widgets and layout helpers.

The recurring theme here is *not letting content dictate window width*. Every
widget that can receive arbitrary text — file names, onion URLs, error
messages — either elides or wraps, and reports a small horizontal size hint so
a 200-character path can never push the layout past the viewport.
"""

from __future__ import annotations

from PyQt6.QtCore import QSize, Qt, QTimer
from PyQt6.QtGui import QFontMetrics
from PyQt6.QtWidgets import (
    QCheckBox, QFrame, QHBoxLayout, QLabel, QLayout, QPushButton,
    QSizePolicy, QVBoxLayout, QWidget,
)

from hazedrop.gui.theme import COLORS, styled


# ── Layout helpers ────────────────────────────────────────────────────────

def h_sep() -> QFrame:
    """A 1px rule. Uses an object name rather than the fragile
    ``QFrame[frameShape="4"]`` attribute selector the old theme relied on."""
    sep = QFrame()
    sep.setObjectName("hsep")
    sep.setFrameShape(QFrame.Shape.NoFrame)
    sep.setFixedHeight(1)
    sep.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
    return sep


def section_title(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setObjectName("section_title")
    return lbl


def field_label(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setObjectName("field_label")
    return lbl


def help_text(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setObjectName("help_text")
    lbl.setWordWrap(True)
    return lbl


class Card(QFrame):
    """Rounded, bordered container used to group related controls."""

    def __init__(self, spacing: int = 12, margins: tuple[int, int, int, int] = (16, 14, 16, 14),
                 parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("card")
        self.setFrameShape(QFrame.Shape.NoFrame)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(*margins)
        lay.setSpacing(spacing)
        lay.setSizeConstraint(QLayout.SizeConstraint.SetMinimumSize)
        self._lay = lay

    def body(self) -> QVBoxLayout:
        return self._lay

    def add(self, item) -> None:
        if isinstance(item, QWidget):
            self._lay.addWidget(item)
        else:
            self._lay.addLayout(item)


def row(*items, spacing: int = 8, stretch_last: bool = False) -> QHBoxLayout:
    """Horizontal row; pass ``(widget, stretch)`` tuples to weight children."""
    lay = QHBoxLayout()
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(spacing)
    for item in items:
        widget, factor = item if isinstance(item, tuple) else (item, 0)
        if widget is None:
            lay.addStretch(factor or 1)
        elif isinstance(widget, QWidget):
            lay.addWidget(widget, factor)
        else:
            lay.addLayout(widget, factor)
    if stretch_last:
        lay.addStretch()
    return lay


# ── Text-safe labels ──────────────────────────────────────────────────────

class ElidedLabel(QLabel):
    """A label that shortens its text with ``…`` instead of widening.

    ``QLabel`` normally reports the full string as its minimum width, which is
    how a long file name used to shove the entire send panel off screen.
    """

    def __init__(self, text: str = "", mode: Qt.TextElideMode = Qt.TextElideMode.ElideMiddle,
                 parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._full = text
        self._mode = mode
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.setText(text)

    def setText(self, text: str) -> None:  # noqa: N802 - Qt naming
        self._full = text or ""
        self.setToolTip(self._full if self._full else "")
        self._apply()

    def fullText(self) -> str:  # noqa: N802 - Qt naming
        return self._full

    def minimumSizeHint(self) -> QSize:  # noqa: N802 - Qt naming
        hint = super().minimumSizeHint()
        return QSize(min(hint.width(), 48), hint.height())

    def resizeEvent(self, event) -> None:  # noqa: N802 - Qt naming
        super().resizeEvent(event)
        self._apply()

    def _apply(self) -> None:
        width = max(self.width() - 2, 24)
        metrics = QFontMetrics(self.font())
        super().setText(metrics.elidedText(self._full, self._mode, width))


class WrapLabel(QLabel):
    """Word-wrapping label that does not inflate the layout's minimum width."""

    def __init__(self, text: str = "", parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self.setWordWrap(True)
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Minimum)

    def minimumSizeHint(self) -> QSize:  # noqa: N802 - Qt naming
        return QSize(48, super().minimumSizeHint().height())


# ── Buttons ───────────────────────────────────────────────────────────────

def _text_width(button: QPushButton, *candidates: str) -> int:
    """Widest rendering of the given labels, so a button sized for one
    language does not clip in another."""
    metrics = QFontMetrics(button.font())
    return max((metrics.horizontalAdvance(c) for c in candidates if c), default=0)


def fit_button(button: QPushButton, *labels: str, padding: int = 26) -> QPushButton:
    """Size a small button to its *widest* possible label.

    Replaces the hard-coded ``setFixedWidth(52)`` calls that clipped Turkish
    strings such as "göster" into "jöster".
    """
    button.setMinimumWidth(_text_width(button, *labels) + padding)
    button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
    return button


class SpinnerButton(QPushButton):
    """Push button that can show a braille spinner plus a status label.

    Width is latched while spinning so the button does not jitter as the
    label changes between "STARTING TOR" and "BOOTSTRAPPING 45%".
    """

    _FRAMES = ("⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏")

    def __init__(self, text: str = "", parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self._base_text = text
        self._spin_label = ""
        self._spin_frame = 0
        self._spin_timer = QTimer(self)
        self._spin_timer.timeout.connect(self._tick)

    @property
    def is_spinning(self) -> bool:
        return self._spin_timer.isActive()

    def start_spin(self, label: str) -> None:
        self._spin_label = label
        self._spin_frame = 0
        self._refresh()
        self._spin_timer.start(90)

    def set_spin_label(self, label: str) -> None:
        self._spin_label = label
        if self._spin_timer.isActive():
            self._refresh()

    def stop_spin(self, text: str | None = None) -> None:
        self._spin_timer.stop()
        self._base_text = text if text is not None else self._base_text
        self.setText(self._base_text)

    def _tick(self) -> None:
        self._spin_frame = (self._spin_frame + 1) % len(self._FRAMES)
        self._refresh()

    def _refresh(self) -> None:
        self.setText(f"{self._FRAMES[self._spin_frame]}  {self._spin_label}")


class StatusRow(QWidget):
    """Coloured dot + status text, with an optional pulse while active."""

    def __init__(self, text: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._pulse = QTimer(self)
        self._pulse.setInterval(600)
        self._pulse.timeout.connect(self._on_pulse)
        self._pulse_on = False

        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)

        self._dot = QLabel("●")
        self._dot.setFixedWidth(10)
        self._dot.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignHCenter)
        lay.addWidget(self._dot, 0, Qt.AlignmentFlag.AlignVCenter)

        self._label = ElidedLabel(text, Qt.TextElideMode.ElideRight)
        self._label.setObjectName("status_idle")
        lay.addWidget(self._label, 1)

        self._set_dot(COLORS["text_muted"])

    def text(self) -> str:
        return self._label.fullText()

    def set_status(self, text: str, style: str = "idle") -> None:
        self._label.setText(text)
        self._label.setObjectName(f"status_{style}")
        self._label.style().unpolish(self._label)
        self._label.style().polish(self._label)

        color = {
            "idle":    COLORS["text_muted"],
            "active":  COLORS["accent"],
            "success": COLORS["success"],
            "error":   COLORS["error"],
        }.get(style, COLORS["text_muted"])

        if style == "active":
            if not self._pulse.isActive():
                self._pulse_on = True
                self._pulse.start()
        else:
            self._pulse.stop()
        self._set_dot(color)

    def stop(self) -> None:
        self._pulse.stop()

    def style_name(self) -> str:
        return self._label.objectName().removeprefix("status_")

    def _on_pulse(self) -> None:
        self._pulse_on = not self._pulse_on
        self._set_dot(COLORS["accent"] if self._pulse_on else COLORS["text_faint"])

    def _set_dot(self, color: str) -> None:
        self._dot.setStyleSheet(f"color: {color}; font-size: 9px; background: transparent;")


# ── Compatibility ─────────────────────────────────────────────────────────

def on_toggle(check: QCheckBox, slot) -> None:
    """Connect a checkbox to ``slot(bool)``.

    ``stateChanged`` is deprecated from Qt 6.7 on; ``checkStateChanged`` hands
    back a ``Qt.CheckState`` rather than an int, so normalise both to a bool.
    """
    if hasattr(check, "checkStateChanged"):
        check.checkStateChanged.connect(
            lambda state: slot(state == Qt.CheckState.Checked)
        )
    else:  # pragma: no cover - Qt < 6.7
        check.stateChanged.connect(lambda state: slot(bool(state)))


__all__ = [
    "Card", "ElidedLabel", "SpinnerButton", "StatusRow", "WrapLabel",
    "field_label", "fit_button", "h_sep", "help_text", "on_toggle", "row",
    "section_title", "styled",
]
