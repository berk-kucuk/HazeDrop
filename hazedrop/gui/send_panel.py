from __future__ import annotations

import asyncio
import os
import random
import tempfile
from collections.abc import Callable

import qasync
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QImage, QPixmap
from PyQt6.QtWidgets import (
    QApplication, QButtonGroup, QCheckBox, QFileDialog, QFrame, QHBoxLayout,
    QLabel, QLineEdit, QPlainTextEdit, QProgressBar, QPushButton, QScrollArea,
    QSizePolicy, QSpinBox, QVBoxLayout, QWidget,
)

from hazedrop.core.crypto import compute_file_hash
from hazedrop.core.duration import parse_duration
from hazedrop.core.settings import load_settings
from hazedrop.gui.theme import COLORS
from hazedrop.gui.widgets import (
    Card, ElidedLabel, SpinnerButton, StatusRow, field_label, fit_button,
    h_sep, help_text, on_toggle, row, section_title,
)
from hazedrop.i18n import t

#: QProgressBar is backed by a 32-bit int, so byte counts from a >2 GiB
#: transfer overflow it. Everything is reported against a fixed scale instead.
_PROGRESS_SCALE = 1000


def _human_size(num_bytes: float) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if num_bytes < 1024 or unit == "TB":
            precision = 0 if unit == "B" else 1
            return f"{num_bytes:.{precision}f} {unit}"
        num_bytes /= 1024
    return f"{num_bytes:.1f} TB"


class DropZone(QFrame):
    """File drop target.

    Subclasses ``QFrame`` (not a bare ``QWidget``) so the stylesheet border and
    background are actually painted — the previous version set a stylesheet on
    a plain widget, which Qt silently ignores, leaving an invisible drop area.
    """

    file_selected = pyqtSignal(str)

    _BASE = "border-radius: 8px;"
    _IDLE = (
        f"{_BASE} background-color: {COLORS['bg_card']};"
        f"border: 1px dashed {COLORS['border_focus']};"
    )
    _HOVER = (
        f"{_BASE} background-color: {COLORS['bg_hover']};"
        f"border: 1px dashed {COLORS['border_active']};"
    )
    _LOADED = (
        f"{_BASE} background-color: {COLORS['bg_hover']};"
        f"border: 1px solid {COLORS['border_active']};"
    )

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("dropZone")
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setAcceptDrops(True)
        self.setMinimumHeight(104)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(self._IDLE)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 12, 18, 12)
        lay.setSpacing(5)
        # Vertical stretches rather than setAlignment(AlignCenter): an aligned
        # layout hands each child only its size hint, which collapses the
        # elided label to "c…z" instead of letting it use the full width.
        lay.addStretch(1)

        self._icon = QLabel("↑")
        self._icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._icon.setStyleSheet(
            f"color: {COLORS['text_faint']}; font-size: 20px;"
            f"border: none; background: transparent;"
        )
        lay.addWidget(self._icon)

        # Elided so a long path shortens instead of stretching the panel.
        self._primary = ElidedLabel(t("drop_hint_line1"))
        self._primary.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._primary.setStyleSheet(
            f"color: {COLORS['text_dim']}; font-size: 12px; font-weight: 500;"
            f"border: none; background: transparent;"
        )
        lay.addWidget(self._primary)

        self._secondary = QLabel(t("drop_hint_line2"))
        self._secondary.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._secondary.setStyleSheet(
            f"color: {COLORS['text_muted']}; font-size: 11px;"
            f"border: none; background: transparent;"
        )
        lay.addWidget(self._secondary)
        lay.addStretch(1)

        self._file_loaded = False

    # ── Content ───────────────────────────────────────────────────

    def set_file(self, name: str, size_bytes: float) -> None:
        self._file_loaded = True
        self._icon.setText("◆")
        self._icon.setStyleSheet(
            f"color: {COLORS['accent']}; font-size: 15px;"
            f"border: none; background: transparent;"
        )
        self._primary.setText(name)
        self._primary.setStyleSheet(
            f"color: {COLORS['text']}; font-size: 13px; font-weight: 600;"
            f"border: none; background: transparent;"
        )
        self._secondary.setText(_human_size(size_bytes))
        self._secondary.setStyleSheet(
            f"color: {COLORS['text_dim']}; font-size: 11px;"
            f"border: none; background: transparent;"
        )
        self.setStyleSheet(self._LOADED)

    def clear_file(self) -> None:
        self._file_loaded = False
        self._icon.setText("↑")
        self._icon.setStyleSheet(
            f"color: {COLORS['text_faint']}; font-size: 20px;"
            f"border: none; background: transparent;"
        )
        self._primary.setStyleSheet(
            f"color: {COLORS['text_dim']}; font-size: 12px; font-weight: 500;"
            f"border: none; background: transparent;"
        )
        self._secondary.setStyleSheet(
            f"color: {COLORS['text_muted']}; font-size: 11px;"
            f"border: none; background: transparent;"
        )
        self.setStyleSheet(self._IDLE)
        self.retranslate()

    def retranslate(self) -> None:
        if not self._file_loaded:
            self._primary.setText(t("drop_hint_line1"))
            self._secondary.setText(t("drop_hint_line2"))

    # ── Interaction ───────────────────────────────────────────────

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802 - Qt naming
        # Left button only; the old handler opened a dialog on right-click too.
        if event.button() == Qt.MouseButton.LeftButton and self.rect().contains(
            event.position().toPoint()
        ):
            path, _ = QFileDialog.getOpenFileName(self, t("select_file_title"))
            if path:
                self.file_selected.emit(path)
        super().mouseReleaseEvent(event)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:  # noqa: N802
        if event.mimeData().hasUrls():
            self.setStyleSheet(self._HOVER)
            event.acceptProposedAction()

    def dragLeaveEvent(self, event) -> None:  # noqa: N802 - Qt naming
        self.setStyleSheet(self._LOADED if self._file_loaded else self._IDLE)

    def dropEvent(self, event: QDropEvent) -> None:  # noqa: N802 - Qt naming
        self.setStyleSheet(self._LOADED if self._file_loaded else self._IDLE)
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if os.path.isfile(path):
                self.file_selected.emit(path)
                event.acceptProposedAction()
                return


class SendPanel(QWidget):
    tor_status_changed = pyqtSignal(str, str)

    def __init__(self, tor_manager, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("panel")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        self._tor = tor_manager
        self._filepath: str | None = None
        self._session = None
        self._server = None
        self._text_mode = False
        self._temp_text_file: str | None = None
        self._temp_zip: str | None = None
        self._tray = None
        self._sharing = False
        #: Set by MainWindow so STOP does not tear down Tor mid-download.
        self.tor_needed_elsewhere: Callable[[], bool] | None = None

        settings = load_settings()
        self._default_max_downloads = settings.max_downloads
        self._default_expire = settings.default_expire

        self._build_ui()

    # ── Public API ────────────────────────────────────────────────

    def set_tray(self, tray) -> None:
        self._tray = tray

    @property
    def active_key(self):
        return self._session.key if self._session else None

    @property
    def is_busy(self) -> bool:
        return self._sharing or self._server is not None

    def reload_defaults(self) -> None:
        settings = load_settings()
        self._default_max_downloads = settings.max_downloads
        self._default_expire = settings.default_expire

    # ── UI ────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        content = QWidget()
        content.setObjectName("panel")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(28, 22, 28, 22)
        layout.setSpacing(16)

        layout.addLayout(self._build_header())
        layout.addWidget(self._build_source_card())
        layout.addWidget(self._build_security_card())
        layout.addWidget(self._build_options_card())
        layout.addWidget(self._build_active_card())
        layout.addStretch(1)

        scroll.setWidget(content)
        self._scroll = scroll
        outer.addWidget(scroll, 1)
        outer.addWidget(self._build_footer())

    def _reveal_active_card(self) -> None:
        """Show the result card and scroll it into view.

        Without this the share link appears below the fold and reads as
        "nothing happened".
        """
        self._active_card.setVisible(True)
        QTimer.singleShot(0, lambda: self._scroll.ensureWidgetVisible(self._active_card, 0, 24))

    def _build_header(self) -> QHBoxLayout:
        self._title_lbl = section_title(t("send_title"))

        # A two-button segmented control replaces the 52px button whose label
        # ("Metin") did not fit.
        self._file_mode_btn = QPushButton(t("mode_file"))
        self._text_mode_btn = QPushButton(t("mode_text"))
        self._mode_group = QButtonGroup(self)
        for i, btn in enumerate((self._file_mode_btn, self._text_mode_btn)):
            btn.setObjectName("ghost")
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            # Both segments get the width of the widest label so the control
            # does not jump when the language changes.
            fit_button(btn, t("mode_file"), t("mode_text"))
            self._mode_group.addButton(btn, i)
        self._file_mode_btn.setChecked(True)
        self._mode_group.setExclusive(True)
        self._mode_group.idClicked.connect(lambda idx: self._set_text_mode(idx == 1))

        return row(self._title_lbl, None,
                   self._file_mode_btn, self._text_mode_btn, spacing=6)

    def _build_source_card(self) -> Card:
        card = Card()

        self._drop_zone = DropZone()
        self._drop_zone.file_selected.connect(self._on_file_selected)
        card.add(self._drop_zone)

        self._text_input = QPlainTextEdit()
        self._text_input.setFixedHeight(126)
        self._text_input.setPlaceholderText(t("text_placeholder"))
        self._text_input.setVisible(False)
        self._text_input.textChanged.connect(self._refresh_share_enabled)
        card.add(self._text_input)

        self._folder_btn = QPushButton(t("select_folder_btn"))
        self._folder_btn.setObjectName("ghost")
        self._folder_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._folder_btn.clicked.connect(self._on_select_folder)

        self._clear_btn = QPushButton(t("clear_btn"))
        self._clear_btn.setObjectName("ghost")
        self._clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._clear_btn.setVisible(False)
        self._clear_btn.clicked.connect(self._on_clear_file)

        self._source_actions = row(self._folder_btn, self._clear_btn, None, spacing=8)
        card.add(self._source_actions)
        return card

    def _build_security_card(self) -> Card:
        card = Card()
        self._security_lbl = section_title(t("security_title"))
        card.add(self._security_lbl)

        self._no_pw_check = QCheckBox(t("keyless_check"))
        self._no_pw_check.setChecked(True)
        self._no_pw_check.setCursor(Qt.CursorShape.PointingHandCursor)
        on_toggle(self._no_pw_check, self._on_no_pw_toggled)
        card.add(self._no_pw_check)

        self._keyless_help = help_text(t("keyless_help"))
        card.add(self._keyless_help)

        self._pw_field_lbl = field_label(t("pw_label"))
        card.add(self._pw_field_lbl)

        self._password_input = QLineEdit()
        self._password_input.setPlaceholderText(t("pw_placeholder"))
        self._password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self._password_input.setEnabled(False)

        self._pw_toggle = QPushButton(t("pw_show"))
        self._pw_toggle.setObjectName("ghost")
        self._pw_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self._pw_toggle.setEnabled(False)
        # Sized for the widest label in any language, so "göster" is not
        # clipped to "jöster" the way a hard-coded 52px was.
        fit_button(self._pw_toggle, t("pw_show"), t("pw_hide"))
        self._pw_toggle.clicked.connect(self._toggle_pw)

        card.add(row((self._password_input, 1), self._pw_toggle, spacing=6))
        return card

    def _build_options_card(self) -> Card:
        card = Card()
        self._options_lbl = section_title(t("options_title"))
        card.add(self._options_lbl)

        self._limit_check = QCheckBox(t("limit_check"))
        self._limit_check.setChecked(self._default_max_downloads > 0)
        self._limit_check.setCursor(Qt.CursorShape.PointingHandCursor)
        on_toggle(self._limit_check, self._on_limit_toggled)

        self._max_dl_spin = QSpinBox()
        self._max_dl_spin.setRange(1, 999)
        self._max_dl_spin.setValue(max(1, self._default_max_downloads))
        self._max_dl_spin.setEnabled(self._default_max_downloads > 0)
        self._max_dl_spin.setFixedWidth(88)
        self._max_dl_spin.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        card.add(row((self._limit_check, 1), self._max_dl_spin, spacing=10))

        self._expire_check = QCheckBox(t("expire_check"))
        self._expire_check.setCursor(Qt.CursorShape.PointingHandCursor)
        self._expire_check.setChecked(bool(self._default_expire))
        on_toggle(self._expire_check, self._on_expire_toggled)

        self._expire_input = QLineEdit()
        self._expire_input.setPlaceholderText(t("expire_placeholder"))
        self._expire_input.setEnabled(bool(self._default_expire))
        self._expire_input.setFixedWidth(140)
        self._expire_input.setText(self._default_expire)
        self._expire_input.textChanged.connect(self._validate_expire)

        card.add(row((self._expire_check, 1), self._expire_input, spacing=10))

        self._expire_error = QLabel("")
        self._expire_error.setObjectName("inline_error")
        self._expire_error.setVisible(False)
        card.add(self._expire_error)
        return card

    def _build_active_card(self) -> Card:
        card = Card(spacing=13)
        self._active_card = card
        card.setVisible(False)

        self._share_link_lbl = section_title(t("share_link_title"))
        card.add(self._share_link_lbl)

        # Read-only QLineEdit rather than a QLabel: an onion URL is one long
        # unbreakable token, which word-wrap cannot handle — it just overflowed.
        self._url_field = QLineEdit()
        self._url_field.setObjectName("url_field")
        self._url_field.setReadOnly(True)
        self._url_field.setCursorPosition(0)
        card.add(self._url_field)

        self._copy_btn = QPushButton(t("copy_link_btn"))
        self._copy_btn.setObjectName("ghost")
        self._copy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        fit_button(self._copy_btn, t("copy_link_btn"), t("copied_btn"))
        self._copy_btn.clicked.connect(self._on_copy_url)

        self._qr_btn = QPushButton(t("qr_btn"))
        self._qr_btn.setObjectName("ghost")
        self._qr_btn.setCheckable(True)
        self._qr_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        fit_button(self._qr_btn, t("qr_btn"))
        self._qr_btn.toggled.connect(self._toggle_qr)

        card.add(row(self._copy_btn, self._qr_btn, None, spacing=8))

        self._qr_label = QLabel()
        self._qr_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._qr_label.setVisible(False)
        self._qr_label.setStyleSheet(
            f"background: {COLORS['bg_elevated']}; border: 1px solid {COLORS['border']};"
            f"border-radius: 6px; padding: 14px;"
        )
        card.add(self._qr_label)

        card.add(h_sep())

        self._status_row = StatusRow(t("status_waiting"))
        card.add(self._status_row)

        self._progress = QProgressBar()
        self._progress.setRange(0, _PROGRESS_SCALE)
        self._progress.setVisible(False)
        card.add(self._progress)

        self._stop_btn = QPushButton(t("stop_btn"))
        self._stop_btn.setObjectName("stop")
        self._stop_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._stop_btn.clicked.connect(self._on_stop_clicked)
        card.add(row(self._stop_btn, None))
        return card

    def _build_footer(self) -> QWidget:
        footer = QWidget()
        footer.setObjectName("footerBar")
        footer.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        lay = QHBoxLayout(footer)
        lay.setContentsMargins(28, 14, 28, 14)
        lay.setSpacing(12)

        self._footer_hint = ElidedLabel(t("footer_hint_pick"), Qt.TextElideMode.ElideRight)
        self._footer_hint.setObjectName("help_text")
        lay.addWidget(self._footer_hint, 1)

        # Lives outside the scroll area: the old layout pushed SHARE below the
        # fold at the default window height, where it looked simply missing.
        self._share_btn = SpinnerButton(t("share_btn"))
        self._share_btn.setObjectName("primary")
        self._share_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._share_btn.setMinimumWidth(150)
        self._share_btn.setEnabled(False)
        self._share_btn.clicked.connect(self._on_share_clicked)
        lay.addWidget(self._share_btn, 0)
        return footer

    # ── i18n ──────────────────────────────────────────────────────

    def retranslate(self) -> None:
        self._title_lbl.setText(t("send_title"))
        self._file_mode_btn.setText(t("mode_file"))
        self._text_mode_btn.setText(t("mode_text"))
        fit_button(self._file_mode_btn, t("mode_file"), t("mode_text"))
        fit_button(self._text_mode_btn, t("mode_file"), t("mode_text"))
        self._drop_zone.retranslate()
        self._text_input.setPlaceholderText(t("text_placeholder"))
        self._folder_btn.setText(t("select_folder_btn"))
        self._clear_btn.setText(t("clear_btn"))
        self._security_lbl.setText(t("security_title"))
        self._no_pw_check.setText(t("keyless_check"))
        self._keyless_help.setText(t("keyless_help"))
        self._pw_field_lbl.setText(t("pw_label"))
        self._password_input.setPlaceholderText(t("pw_placeholder"))
        hidden = self._password_input.echoMode() == QLineEdit.EchoMode.Password
        self._pw_toggle.setText(t("pw_show") if hidden else t("pw_hide"))
        fit_button(self._pw_toggle, t("pw_show"), t("pw_hide"))
        self._options_lbl.setText(t("options_title"))
        self._limit_check.setText(t("limit_check"))
        self._expire_check.setText(t("expire_check"))
        self._expire_input.setPlaceholderText(t("expire_placeholder"))
        self._share_link_lbl.setText(t("share_link_title"))
        self._copy_btn.setText(t("copy_link_btn"))
        fit_button(self._copy_btn, t("copy_link_btn"), t("copied_btn"))
        self._qr_btn.setText(t("qr_btn"))
        self._stop_btn.setText(t("stop_btn"))
        if not self._share_btn.is_spinning:
            self._share_btn.stop_spin(t("share_btn"))
        if self._status_row.style_name() == "idle":
            self._status_row.set_status(t("status_waiting"), "idle")
        self._validate_expire()
        self._refresh_share_enabled()

    # ── State ─────────────────────────────────────────────────────

    def _refresh_share_enabled(self) -> None:
        if self._sharing or self._server is not None:
            self._share_btn.setEnabled(False)
            return

        if self._text_mode:
            ready = bool(self._text_input.toPlainText().strip())
            hint = t("footer_hint_ready") if ready else t("footer_hint_text")
        else:
            ready = bool(self._filepath)
            hint = t("footer_hint_ready") if ready else t("footer_hint_pick")

        if ready and not self._expire_ok():
            ready = False
            hint = t("expire_invalid")

        self._share_btn.setEnabled(ready)
        self._footer_hint.setText(hint)

    def _expire_ok(self) -> bool:
        if not self._expire_check.isChecked():
            return True
        try:
            return parse_duration(self._expire_input.text()) is not None
        except ValueError:
            return False

    def _validate_expire(self) -> None:
        text = self._expire_input.text().strip()
        invalid = self._expire_check.isChecked() and bool(text) and not self._expire_ok()
        self._expire_error.setText(t("expire_invalid") if invalid else "")
        self._expire_error.setVisible(invalid)
        self._expire_input.setProperty("state", "invalid" if invalid else "")
        self._expire_input.style().unpolish(self._expire_input)
        self._expire_input.style().polish(self._expire_input)
        self._refresh_share_enabled()

    def _set_text_mode(self, enabled: bool) -> None:
        self._text_mode = enabled
        self._drop_zone.setVisible(not enabled)
        for i in range(self._source_actions.count()):
            widget = self._source_actions.itemAt(i).widget()
            if widget is not None:
                widget.setVisible(not enabled and (widget is not self._clear_btn
                                                   or bool(self._filepath)))
        self._text_input.setVisible(enabled)
        self._refresh_share_enabled()

    # ── Slots ─────────────────────────────────────────────────────

    def _on_file_selected(self, path: str) -> None:
        try:
            size = os.path.getsize(path)
        except OSError as exc:
            self._show_transient_error(str(exc))
            return
        self._filepath = path
        self._drop_zone.set_file(os.path.basename(path), size)
        self._clear_btn.setVisible(True)
        self._refresh_share_enabled()

    def _on_clear_file(self) -> None:
        self._filepath = None
        self._cleanup_temps()
        self._drop_zone.clear_file()
        self._clear_btn.setVisible(False)
        self._refresh_share_enabled()

    def _on_select_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, t("select_folder_btn"))
        if not folder:
            return
        import zipfile

        fd, zip_path = tempfile.mkstemp(suffix=".zip", prefix="hazedrop_")
        os.close(fd)
        try:
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                for root_dir, _dirs, files in os.walk(folder):
                    for fname in files:
                        fpath = os.path.join(root_dir, fname)
                        arcname = os.path.relpath(fpath, os.path.dirname(folder))
                        zf.write(fpath, arcname)
        except Exception as exc:
            try:
                os.unlink(zip_path)
            except OSError:
                pass
            self._show_transient_error(t("zip_failed", exc))
            return

        self._cleanup_temps()
        self._temp_zip = zip_path
        self._filepath = zip_path
        self._drop_zone.set_file(os.path.basename(folder) + ".zip",
                                 os.path.getsize(zip_path))
        self._clear_btn.setVisible(True)
        self._refresh_share_enabled()

    def _show_transient_error(self, message: str) -> None:
        self._reveal_active_card()
        self._status_row.set_status(message, "error")

    def _on_limit_toggled(self, checked: bool) -> None:
        self._max_dl_spin.setEnabled(checked)

    def _on_expire_toggled(self, checked: bool) -> None:
        self._expire_input.setEnabled(checked)
        self._validate_expire()

    def _on_no_pw_toggled(self, checked: bool) -> None:
        self._password_input.setEnabled(not checked)
        self._pw_toggle.setEnabled(not checked)
        self._pw_field_lbl.setEnabled(not checked)

    def _toggle_pw(self) -> None:
        hidden = self._password_input.echoMode() == QLineEdit.EchoMode.Password
        self._password_input.setEchoMode(
            QLineEdit.EchoMode.Normal if hidden else QLineEdit.EchoMode.Password
        )
        self._pw_toggle.setText(t("pw_hide") if hidden else t("pw_show"))

    def _toggle_qr(self, visible: bool) -> None:
        self._qr_label.setVisible(visible)
        if visible and self._qr_label.pixmap().isNull():
            url = self._url_field.text()
            if url:
                self._qr_label.setPixmap(self._generate_qr(url))

    def _generate_qr(self, url: str) -> QPixmap:
        import qrcode

        qr = qrcode.QRCode(box_size=5, border=2,
                           error_correction=qrcode.constants.ERROR_CORRECT_L)
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="white",
                            back_color=COLORS["bg_elevated"]).convert("RGBA")
        data = img.tobytes("raw", "RGBA")
        qimage = QImage(data, img.width, img.height, QImage.Format.Format_RGBA8888)
        return QPixmap.fromImage(qimage.copy())

    def _on_copy_url(self) -> None:
        url = self._url_field.text()
        if not url:
            return
        QApplication.clipboard().setText(url)
        self._copy_btn.setText(t("copied_btn"))
        QTimer.singleShot(1800, lambda: self._copy_btn.setText(t("copy_link_btn")))

    # ── Share flow ────────────────────────────────────────────────

    @qasync.asyncSlot()
    async def _on_share_clicked(self) -> None:
        from hazedrop.core.crypto import (
            build_share_url, derive_key, generate_key, generate_salt,
        )
        from hazedrop.core.history import add_entry
        from hazedrop.core.server import TorDropServer
        from hazedrop.core.session import DropSession

        settings = load_settings()

        # Validate before touching Tor. parse_duration used to run unguarded
        # and a typo such as "10mn" raised straight out of the slot.
        try:
            expire_seconds = (
                parse_duration(self._expire_input.text())
                if self._expire_check.isChecked() else None
            )
        except ValueError:
            self._validate_expire()
            self._show_transient_error(t("expire_invalid"))
            return

        if self._text_mode:
            text = self._text_input.toPlainText()
            if not text.strip():
                self._show_transient_error(t("text_empty"))
                return
            tmp_dir = tempfile.mkdtemp(prefix="hazedrop_")
            filepath = os.path.join(tmp_dir, "snippet.txt")
            with open(filepath, "w", encoding="utf-8") as fh:
                fh.write(text)
            self._temp_text_file = filepath
        else:
            if not self._filepath or not os.path.exists(self._filepath):
                self._show_transient_error(t("file_missing"))
                return
            filepath = self._filepath

        password = None if self._no_pw_check.isChecked() else (self._password_input.text() or None)
        max_downloads = self._max_dl_spin.value() if self._limit_check.isChecked() else 0

        salt = generate_salt() if password else None
        key = derive_key(password, salt) if password else generate_key()

        self._sharing = True
        self._share_btn.setEnabled(False)
        self._share_btn.start_spin(t("spin_starting_tor"))
        self._footer_hint.setText(t("footer_hint_starting"))
        self.tor_status_changed.emit("starting", "")

        loop = asyncio.get_running_loop()
        fname = os.path.basename(filepath)

        try:
            file_hash = await loop.run_in_executor(None, compute_file_hash, filepath)

            self._session = DropSession(
                filepath=filepath,
                filename=fname,
                filesize=os.path.getsize(filepath),
                password=password,
                once=(max_downloads == 1),
                expire_seconds=expire_seconds,
                salt=salt,
                key=key,
                file_hash=file_hash,
                max_downloads=max_downloads,
            )

            def _progress(msg: str) -> None:
                for part in msg.split():
                    if part.endswith("%"):
                        self._share_btn.set_spin_label(t("spin_bootstrapping", part))
                        self.tor_status_changed.emit("starting", part)

            await self._tor.start(
                on_progress=_progress,
                bridges=settings.tor_bridges if settings.use_bridges else None,
                use_bridges=settings.use_bridges,
            )
            self.tor_status_changed.emit("active", "")
            self._share_btn.set_spin_label(t("spin_publishing"))

            local_port = random.randint(50000, 59999)

            def _on_start() -> None:
                self._status_row.set_status(t("status_downloading"), "active")
                self._progress.setRange(0, 0)  # indeterminate until first byte
                self._progress.setVisible(True)
                if self._tray:
                    self._tray.notify("HazeDrop", t("notify_dl_started", fname))

            def _on_complete() -> None:
                self._status_row.set_status(t("status_complete"), "success")
                self._progress.setVisible(False)
                if self._tray:
                    self._tray.notify("HazeDrop", t("notify_dl_complete", fname))

            self._server = TorDropServer(
                self._session, local_port,
                on_download_start=_on_start,
                on_download_complete=_on_complete,
            )
            await self._server.start()

            onion = await loop.run_in_executor(
                None, self._tor.create_hidden_service, local_port
            )
            self._session.onion_address = onion

            share_url = build_share_url(
                onion, key, self._session.is_password_protected, file_hash
            )

            self._share_btn.stop_spin(t("share_btn"))
            self._url_field.setText(share_url)
            self._url_field.setCursorPosition(0)
            self._url_field.setToolTip(share_url)
            self._reveal_active_card()
            self._status_row.set_status(t("status_waiting"), "idle")
            self._footer_hint.setText(t("footer_hint_live"))

            if settings.history_enabled:
                add_entry("send", fname, os.path.getsize(filepath), onion,
                          "active", ttl_days=settings.history_ttl_days)

        except Exception as exc:  # noqa: BLE001 - surfaced in the UI
            self.tor_status_changed.emit("error", "")
            self._share_btn.stop_spin(t("share_btn"))
            self._url_field.clear()
            self._reveal_active_card()
            self._status_row.set_status(t("status_error_prefix", exc), "error")
            self._footer_hint.setText(t("footer_hint_failed"))
            if self._server is not None:
                try:
                    await self._server.stop()
                except Exception:
                    pass
                self._server = None
            if self._session is not None:
                self._session.zero_key()
                self._session = None
            self._cleanup_temps()
        finally:
            self._sharing = False
            self._refresh_share_enabled()

    @qasync.asyncSlot()
    async def _on_stop_clicked(self) -> None:
        self._status_row.stop()
        if self._session is not None:
            self._session.zero_key()
            self._session = None
        if self._server is not None:
            await self._server.stop()
            self._server = None

        # The receive panel shares this TorManager; stopping it mid-download
        # would kill that transfer too.
        if not (self.tor_needed_elsewhere and self.tor_needed_elsewhere()):
            await self._tor.stop()
            self.tor_status_changed.emit("idle", "")

        self._active_card.setVisible(False)
        self._qr_btn.setChecked(False)
        self._qr_label.setVisible(False)
        self._qr_label.setPixmap(QPixmap())
        self._url_field.clear()
        self._progress.setVisible(False)
        self._share_btn.stop_spin(t("share_btn"))
        self._cleanup_temps()
        self._refresh_share_enabled()

    # ── Cleanup ───────────────────────────────────────────────────

    def _cleanup_temps(self) -> None:
        if self._temp_text_file:
            try:
                if os.path.exists(self._temp_text_file):
                    os.unlink(self._temp_text_file)
                tmp_dir = os.path.dirname(self._temp_text_file)
                if os.path.isdir(tmp_dir) and not os.listdir(tmp_dir):
                    os.rmdir(tmp_dir)
            except OSError:
                pass
            self._temp_text_file = None

        if self._temp_zip:
            try:
                if os.path.exists(self._temp_zip):
                    os.unlink(self._temp_zip)
            except OSError:
                pass
            if self._filepath == self._temp_zip:
                self._filepath = None
            self._temp_zip = None

    def panic(self) -> None:
        if self._session is not None:
            self._session.zero_key()
