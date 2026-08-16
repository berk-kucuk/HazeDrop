"""Colour palette, Qt palette and application stylesheet.

Two rules keep this file out of trouble:

1. The global ``QWidget`` rule never sets ``background-color``. Doing so makes
   every checkbox, container and layout helper paint an opaque rectangle over
   whatever surface it sits on. Backgrounds are declared per-surface instead,
   and those widgets opt in via :func:`styled` (Qt only honours a stylesheet
   background on a plain ``QWidget`` when ``WA_StyledBackground`` is set).
2. Nothing relies on the default palette for contrast. ``QApplication`` gets an
   explicit dark palette so native pieces — menus, tooltips, dialogs, the tray
   menu — match the rest of the app.
"""

from __future__ import annotations

import os
import tempfile

from PyQt6.QtCore import QPointF, Qt
from PyQt6.QtGui import QColor, QImage, QPainter, QPalette, QPen
from PyQt6.QtWidgets import QWidget

# ── Palette ───────────────────────────────────────────────────────────────
#
# Surfaces climb in 6–8 point steps so adjacent layers stay distinguishable
# without ever leaving the near-black identity.

COLORS: dict[str, str] = {
    "bg":            "#08080a",  # window
    "bg_panel":      "#0b0b0e",  # content area
    "bg_card":       "#121216",  # grouped block
    "bg_elevated":   "#17171c",  # inputs
    "bg_hover":      "#1f1f26",
    "border":        "#24242b",
    "border_focus":  "#33333d",
    "border_active": "#4a4a57",

    "accent":        "#ffffff",
    "accent_dim":    "#9a9aa6",

    # Text. text_dim is deliberately far brighter than it used to be: at
    # #555555 on #0b0b0e the field labels sat at ~2:1 contrast, well under the
    # 4.5:1 needed to actually read them.
    "text":          "#f2f2f5",
    "text_dim":      "#a0a0ac",
    "text_faint":    "#6b6b78",
    "text_muted":    "#55555f",

    "success":       "#34d399",
    "warning":       "#fbbf24",
    "error":         "#f87171",
    "panic":         "#ff453a",
}

FONT_STACK = '"Inter", "SF Pro Text", "Segoe UI", "Noto Sans", system-ui, sans-serif'
MONO_STACK = '"JetBrains Mono", "Fira Code", "Cascadia Code", "DejaVu Sans Mono", monospace'


def _checkmark_url() -> str:
    """Render the tick used by ``QCheckBox::indicator:checked``.

    Qt stylesheets can only reference an image by URL and the project has no
    compiled ``.qrc``, so the glyph is drawn once into the cache directory.
    ``QImage`` (unlike ``QPixmap``) paints fine before ``QApplication`` exists,
    which matters because this module is imported first.
    """
    path = os.path.join(tempfile.gettempdir(), "hazedrop-check-15.png")
    if not os.path.exists(path):
        try:
            img = QImage(30, 30, QImage.Format.Format_ARGB32_Premultiplied)
            img.fill(Qt.GlobalColor.transparent)
            painter = QPainter(img)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            pen = QPen(QColor("#000000"), 4.0)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)
            painter.drawPolyline(
                QPointF(7, 15.5), QPointF(12.5, 21), QPointF(23, 9)
            )
            painter.end()
            img.save(path, "PNG")
        except Exception:
            return ""
    return path.replace("\\", "/")


def _arrow_url(direction: str, color: str) -> str:
    """Render a chevron for spin-box / combo-box arrows.

    The usual CSS "zero-size box with coloured borders" triangle trick does
    nothing in Qt stylesheets — ``::up-arrow`` only honours ``image``, which is
    why those controls used to show grey blocks.
    """
    name = f"hazedrop-arrow-{direction}-{color.lstrip('#')}.png"
    path = os.path.join(tempfile.gettempdir(), name)
    if not os.path.exists(path):
        try:
            img = QImage(20, 20, QImage.Format.Format_ARGB32_Premultiplied)
            img.fill(Qt.GlobalColor.transparent)
            painter = QPainter(img)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            pen = QPen(QColor(color), 2.2)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)
            if direction == "up":
                points = (QPointF(5, 12.5), QPointF(10, 7.5), QPointF(15, 12.5))
            else:
                points = (QPointF(5, 7.5), QPointF(10, 12.5), QPointF(15, 7.5))
            painter.drawPolyline(*points)
            painter.end()
            img.save(path, "PNG")
        except Exception:
            return ""
    return path.replace("\\", "/")


def _image(url: str) -> str:
    return f"url({url})" if url else "none"


_CHECK_IMAGE = _image(_checkmark_url())
_ARROW_UP = _image(_arrow_url("up", COLORS["text_dim"]))
_ARROW_DOWN = _image(_arrow_url("down", COLORS["text_dim"]))
_ARROW_DOWN_DIM = _image(_arrow_url("down", COLORS["text_muted"]))
_ARROW_UP_DIM = _image(_arrow_url("up", COLORS["text_muted"]))


def styled(widget: QWidget) -> QWidget:
    """Let a plain ``QWidget`` paint its stylesheet background. Returns it."""
    widget.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
    return widget


def build_palette() -> QPalette:
    """Dark palette so native popups (menus, tooltips) are not blinding."""
    c = COLORS
    p = QPalette()
    role = QPalette.ColorRole
    group = QPalette.ColorGroup

    p.setColor(role.Window, QColor(c["bg"]))
    p.setColor(role.WindowText, QColor(c["text"]))
    p.setColor(role.Base, QColor(c["bg_elevated"]))
    p.setColor(role.AlternateBase, QColor(c["bg_card"]))
    p.setColor(role.Text, QColor(c["text"]))
    p.setColor(role.PlaceholderText, QColor(c["text_muted"]))
    p.setColor(role.Button, QColor(c["bg_elevated"]))
    p.setColor(role.ButtonText, QColor(c["text"]))
    p.setColor(role.ToolTipBase, QColor(c["bg_card"]))
    p.setColor(role.ToolTipText, QColor(c["text"]))
    p.setColor(role.Highlight, QColor(c["border_focus"]))
    p.setColor(role.HighlightedText, QColor(c["text"]))
    p.setColor(role.Link, QColor(c["accent"]))

    for r in (role.WindowText, role.Text, role.ButtonText):
        p.setColor(group.Disabled, r, QColor(c["text_muted"]))
    return p


STYLESHEET = f"""
/* ── Base ────────────────────────────────────────────────────────────────
   No background-color here on purpose — see the module docstring. */
QWidget {{
    color: {COLORS["text"]};
    font-family: {FONT_STACK};
    font-size: 13px;
    outline: none;
    selection-background-color: {COLORS["border_focus"]};
    selection-color: {COLORS["text"]};
}}

/* ── Surfaces ──────────────────────────────────────────────────────────── */
QWidget#root {{
    background-color: {COLORS["bg"]};
    border: 1px solid {COLORS["border"]};
    border-radius: 0px;
}}

QWidget#sidebar {{
    background-color: {COLORS["bg"]};
    border-right: 1px solid {COLORS["border"]};
}}

QWidget#titleBar {{
    background-color: {COLORS["bg"]};
    border-bottom: 1px solid {COLORS["border"]};
}}

QWidget#panel {{
    background-color: {COLORS["bg_panel"]};
}}

QWidget#footerBar {{
    background-color: {COLORS["bg_panel"]};
    border-top: 1px solid {COLORS["border"]};
}}

QFrame#card {{
    background-color: {COLORS["bg_card"]};
    border: 1px solid {COLORS["border"]};
    border-radius: 8px;
}}

QFrame#hsep {{
    background-color: {COLORS["border"]};
    border: none;
    max-height: 1px;
    min-height: 1px;
}}

QScrollArea {{
    background: transparent;
    border: none;
}}

QScrollArea > QWidget > QWidget {{
    background: transparent;
}}

/* ── Labels ──────────────────────────────────────────────────────────── */
QLabel {{
    background: transparent;
}}

QLabel#section_title {{
    color: {COLORS["text"]};
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 1.8px;
}}

QLabel#field_label {{
    color: {COLORS["text_dim"]};
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.6px;
}}

QLabel#help_text {{
    color: {COLORS["text_faint"]};
    font-size: 11px;
}}

QLabel#muted {{
    color: {COLORS["text_faint"]};
    font-size: 11px;
}}

QLabel#value_label {{
    color: {COLORS["text"]};
    font-size: 12px;
}}

QLabel#mono {{
    color: {COLORS["text"]};
    font-family: {MONO_STACK};
    font-size: 12px;
}}

QLabel#status_idle   {{ color: {COLORS["text_dim"]};  font-size: 12px; }}
QLabel#status_active {{ color: {COLORS["text"]};      font-size: 12px; }}
QLabel#status_success{{ color: {COLORS["success"]};   font-size: 12px; }}
QLabel#status_error  {{ color: {COLORS["error"]};     font-size: 12px; }}

QLabel#inline_error {{
    color: {COLORS["error"]};
    font-size: 11px;
}}

/* ── Inputs ──────────────────────────────────────────────────────────── */
QLineEdit, QPlainTextEdit, QSpinBox, QComboBox {{
    background-color: {COLORS["bg_elevated"]};
    color: {COLORS["text"]};
    border: 1px solid {COLORS["border"]};
    border-radius: 6px;
    padding: 8px 11px;
    font-size: 13px;
    selection-background-color: {COLORS["border_active"]};
}}

QLineEdit {{ min-height: 20px; }}
QSpinBox  {{ min-height: 20px; }}
QComboBox {{ min-height: 20px; }}

QLineEdit:hover, QPlainTextEdit:hover, QSpinBox:hover, QComboBox:hover {{
    border-color: {COLORS["border_focus"]};
}}

QLineEdit:focus, QPlainTextEdit:focus, QSpinBox:focus, QComboBox:focus {{
    border-color: {COLORS["border_active"]};
    background-color: {COLORS["bg_hover"]};
}}

QLineEdit:disabled, QPlainTextEdit:disabled, QSpinBox:disabled {{
    color: {COLORS["text_muted"]};
    background-color: {COLORS["bg_card"]};
    border-color: {COLORS["border"]};
}}

/* Qt spells this differently from CSS — ::placeholder does nothing here. */
QLineEdit, QPlainTextEdit {{
    placeholder-text-color: {COLORS["text_muted"]};
}}

QLineEdit#url_field {{
    font-family: {MONO_STACK};
    font-size: 12px;
    color: {COLORS["text"]};
    background-color: {COLORS["bg_elevated"]};
}}

QLineEdit[state="valid"]   {{ border-color: #1f6b45; }}
QLineEdit[state="invalid"] {{ border-color: #7a2f2f; }}

QPlainTextEdit {{
    font-family: {MONO_STACK};
}}

QPlainTextEdit#bridges {{
    font-size: 12px;
}}

/* ── Buttons ─────────────────────────────────────────────────────────── */
QPushButton {{
    background-color: {COLORS["bg_elevated"]};
    color: {COLORS["text"]};
    border: 1px solid {COLORS["border"]};
    border-radius: 6px;
    padding: 8px 16px;
    font-size: 12px;
    font-weight: 500;
}}

QPushButton:hover {{
    background-color: {COLORS["bg_hover"]};
    border-color: {COLORS["border_focus"]};
}}

QPushButton:pressed {{
    background-color: {COLORS["border"]};
}}

QPushButton:disabled {{
    color: {COLORS["text_muted"]};
    background-color: {COLORS["bg_card"]};
    border-color: {COLORS["border"]};
}}

QPushButton#primary {{
    background-color: {COLORS["accent"]};
    color: #000000;
    border: 1px solid {COLORS["accent"]};
    border-radius: 6px;
    padding: 11px 26px;
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 1.4px;
    min-height: 20px;
}}

QPushButton#primary:hover    {{ background-color: #e6e6e9; border-color: #e6e6e9; }}
QPushButton#primary:pressed  {{ background-color: #c9c9cf; border-color: #c9c9cf; }}
QPushButton#primary:disabled {{
    background-color: {COLORS["bg_elevated"]};
    color: {COLORS["text_muted"]};
    border-color: {COLORS["border"]};
}}

QPushButton#stop {{
    background-color: transparent;
    color: {COLORS["error"]};
    border: 1px solid #4a2020;
    border-radius: 6px;
    padding: 10px 26px;
    font-size: 12px;
    font-weight: 600;
    letter-spacing: 1.2px;
}}

QPushButton#stop:hover {{
    background-color: #241012;
    border-color: {COLORS["error"]};
}}

QPushButton#ghost {{
    background-color: transparent;
    color: {COLORS["text_dim"]};
    border: 1px solid {COLORS["border"]};
    border-radius: 6px;
    padding: 8px 14px;
    font-size: 12px;
    font-weight: 500;
}}

QPushButton#ghost:hover {{
    background-color: {COLORS["bg_elevated"]};
    border-color: {COLORS["border_focus"]};
    color: {COLORS["text"]};
}}

QPushButton#ghost:checked {{
    background-color: {COLORS["bg_hover"]};
    border-color: {COLORS["border_active"]};
    color: {COLORS["text"]};
}}

QPushButton#ghost:disabled {{
    color: {COLORS["text_muted"]};
    border-color: {COLORS["border"]};
}}

/* ── Sidebar navigation ──────────────────────────────────────────────── */
QPushButton#nav_btn, QPushButton#nav_btn_active {{
    border: none;
    border-left: 2px solid transparent;
    border-radius: 0px;
    border-top-right-radius: 6px;
    border-bottom-right-radius: 6px;
    padding: 10px 2px;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.4px;
    text-align: center;
}}

QPushButton#nav_btn {{
    background-color: transparent;
    color: {COLORS["text_faint"]};
}}

QPushButton#nav_btn:hover {{
    background-color: {COLORS["bg_card"]};
    color: {COLORS["text_dim"]};
    border-left-color: {COLORS["border_focus"]};
}}

QPushButton#nav_btn_active {{
    background-color: {COLORS["bg_card"]};
    color: {COLORS["text"]};
    border-left: 2px solid {COLORS["accent"]};
}}

/* ── Title bar controls ──────────────────────────────────────────────── */
QPushButton#winBtn, QPushButton#winBtnClose {{
    background: transparent;
    color: {COLORS["text_faint"]};
    border: none;
    border-radius: 5px;
    font-size: 14px;
    font-weight: 400;
    padding: 0px;
}}

QPushButton#winBtn:hover {{
    color: {COLORS["text"]};
    background-color: {COLORS["bg_hover"]};
}}

QPushButton#winBtnClose:hover {{
    color: #ffffff;
    background-color: #c0392b;
}}

QPushButton#protocolBadge, QPushButton#protocolBadgeActive {{
    border-radius: 4px;
    padding: 4px 9px;
    font-size: 9px;
    font-weight: 700;
    letter-spacing: 1.2px;
}}

QPushButton#protocolBadge {{
    background-color: {COLORS["bg_card"]};
    color: {COLORS["text_faint"]};
    border: 1px solid {COLORS["border"]};
}}

QPushButton#protocolBadgeActive {{
    background-color: #0d2a1c;
    color: {COLORS["success"]};
    border: 1px solid #1c5138;
}}

QPushButton#panicBtn {{
    background-color: #1a0708;
    color: {COLORS["panic"]};
    border: 1px solid #4a1416;
    border-radius: 4px;
    padding: 4px 11px;
    font-size: 9px;
    font-weight: 700;
    letter-spacing: 1.4px;
}}

QPushButton#panicBtn:hover {{
    background-color: {COLORS["panic"]};
    color: #000000;
    border-color: {COLORS["panic"]};
}}

/* ── Check boxes ─────────────────────────────────────────────────────── */
QCheckBox {{
    background: transparent;
    color: {COLORS["text_dim"]};
    spacing: 9px;
    font-size: 12px;
    padding: 2px 0px;
}}

QCheckBox:hover    {{ color: {COLORS["text"]}; }}
QCheckBox:disabled {{ color: {COLORS["text_muted"]}; }}

QCheckBox::indicator {{
    width: 15px;
    height: 15px;
    border: 1px solid {COLORS["border_focus"]};
    border-radius: 4px;
    background-color: {COLORS["bg_elevated"]};
}}

QCheckBox::indicator:hover {{
    border-color: {COLORS["border_active"]};
}}

QCheckBox::indicator:checked {{
    background-color: {COLORS["accent"]};
    border-color: {COLORS["accent"]};
    image: {_CHECK_IMAGE};
}}

/* ── Spin box ────────────────────────────────────────────────────────── */
QSpinBox {{
    padding-right: 20px;
}}

QSpinBox::up-button, QSpinBox::down-button {{
    subcontrol-origin: border;
    background: transparent;
    border: none;
    width: 18px;
}}

QSpinBox::up-button   {{ subcontrol-position: top right;    margin: 3px 3px 0px 0px; }}
QSpinBox::down-button {{ subcontrol-position: bottom right; margin: 0px 3px 3px 0px; }}

QSpinBox::up-button:hover, QSpinBox::down-button:hover {{
    background-color: {COLORS["bg_hover"]};
    border-radius: 3px;
}}

QSpinBox::up-arrow {{
    image: {_ARROW_UP};
    width: 14px;
    height: 14px;
}}

QSpinBox::down-arrow {{
    image: {_ARROW_DOWN};
    width: 14px;
    height: 14px;
}}

QSpinBox::up-arrow:disabled, QSpinBox::up-arrow:off {{
    image: {_ARROW_UP_DIM};
}}

QSpinBox::down-arrow:disabled, QSpinBox::down-arrow:off {{
    image: {_ARROW_DOWN_DIM};
}}

/* ── Combo box ───────────────────────────────────────────────────────── */
QComboBox::drop-down {{
    subcontrol-origin: padding;
    subcontrol-position: center right;
    border: none;
    width: 26px;
}}

QComboBox::down-arrow {{
    image: {_ARROW_DOWN};
    width: 16px;
    height: 16px;
    margin-right: 8px;
}}

QComboBox QAbstractItemView {{
    background-color: {COLORS["bg_card"]};
    color: {COLORS["text"]};
    border: 1px solid {COLORS["border_focus"]};
    border-radius: 6px;
    padding: 4px;
    outline: none;
    selection-background-color: {COLORS["bg_hover"]};
    selection-color: {COLORS["text"]};
}}

/* ── Progress ────────────────────────────────────────────────────────── */
QProgressBar {{
    background-color: {COLORS["bg_elevated"]};
    border: none;
    border-radius: 3px;
    min-height: 6px;
    max-height: 6px;
    text-align: center;
    color: transparent;
}}

QProgressBar::chunk {{
    background-color: {COLORS["accent"]};
    border-radius: 3px;
}}

/* ── Menus & tooltips (tray menu, context menus) ─────────────────────── */
QMenu {{
    background-color: {COLORS["bg_card"]};
    color: {COLORS["text"]};
    border: 1px solid {COLORS["border_focus"]};
    border-radius: 8px;
    padding: 6px;
}}

QMenu::item {{
    padding: 7px 22px 7px 14px;
    border-radius: 5px;
}}

QMenu::item:selected {{
    background-color: {COLORS["bg_hover"]};
}}

QMenu::separator {{
    height: 1px;
    background-color: {COLORS["border"]};
    margin: 5px 8px;
}}

QToolTip {{
    background-color: {COLORS["bg_card"]};
    color: {COLORS["text"]};
    border: 1px solid {COLORS["border_focus"]};
    border-radius: 6px;
    padding: 6px 9px;
    font-size: 12px;
}}

/* ── Scroll bars ─────────────────────────────────────────────────────── */
QScrollBar:vertical {{
    background: transparent;
    width: 10px;
    margin: 2px 2px 2px 0px;
}}

QScrollBar::handle:vertical {{
    background: {COLORS["border_focus"]};
    border-radius: 3px;
    min-height: 32px;
}}

QScrollBar::handle:vertical:hover {{
    background: {COLORS["border_active"]};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}

QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: transparent;
}}

QScrollBar:horizontal {{
    background: transparent;
    height: 10px;
    margin: 0px 2px 2px 2px;
}}

QScrollBar::handle:horizontal {{
    background: {COLORS["border_focus"]};
    border-radius: 3px;
    min-width: 32px;
}}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0px;
}}

QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
    background: transparent;
}}

/* ── Dialogs ─────────────────────────────────────────────────────────── */
QMessageBox {{
    background-color: {COLORS["bg_card"]};
}}

QMessageBox QLabel {{
    color: {COLORS["text"]};
}}
"""
