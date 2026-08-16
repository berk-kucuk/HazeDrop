from __future__ import annotations

import os
import subprocess
import sys
import time

import qasync
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFileDialog, QFrame, QHBoxLayout, QLineEdit, QProgressBar,
    QPushButton, QScrollArea, QVBoxLayout, QWidget,
)

from hazedrop.core.settings import load_settings
from hazedrop.gui.widgets import (
    Card, ElidedLabel, SpinnerButton, StatusRow, field_label, fit_button,
    h_sep, help_text, row, section_title,
)
from hazedrop.i18n import t

#: See send_panel — QProgressBar cannot hold a >2 GiB byte count.
_PROGRESS_SCALE = 1000


def _human_size(num_bytes: float) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if num_bytes < 1024 or unit == "TB":
            precision = 0 if unit == "B" else 1
            return f"{num_bytes:.{precision}f} {unit}"
        num_bytes /= 1024
    return f"{num_bytes:.1f} TB"


def _format_eta(seconds: int) -> str:
    if seconds >= 3600:
        return f"{seconds // 3600}h {(seconds % 3600) // 60}m"
    if seconds >= 60:
        return f"{seconds // 60}m {seconds % 60}s"
    return f"{seconds}s"


class ReceivePanel(QWidget):
    tor_status_changed = pyqtSignal(str, str)

    def __init__(self, tor_manager, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("panel")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        self._tor = tor_manager
        self._saved_path: str | None = None
        self._dl_start: float = 0.0
        self._tray = None
        self._downloading = False
        self._build_ui()

    # ── Public API ────────────────────────────────────────────────

    def set_tray(self, tray) -> None:
        self._tray = tray

    @property
    def is_busy(self) -> bool:
        return self._downloading

    def reload_defaults(self) -> None:
        """Pick up a changed download directory, unless the user edited it."""
        settings = load_settings()
        if not self._output_input.isModified():
            self._output_input.setText(settings.download_dir)

    # ── UI ────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        content = QWidget()
        content.setObjectName("panel")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(28, 22, 28, 22)
        layout.setSpacing(16)

        self._title_lbl = section_title(t("recv_title"))
        layout.addWidget(self._title_lbl)

        layout.addWidget(self._build_source_card())
        layout.addWidget(self._build_dest_card())
        layout.addWidget(self._build_progress_card())
        layout.addStretch(1)

        scroll.setWidget(content)
        outer.addWidget(scroll, 1)
        outer.addWidget(self._build_footer())

    def _build_source_card(self) -> Card:
        card = Card()

        self._onion_lbl = field_label(t("onion_label"))
        card.add(self._onion_lbl)

        self._onion_input = QLineEdit()
        self._onion_input.setObjectName("url_field")
        self._onion_input.setPlaceholderText(t("onion_placeholder"))
        self._onion_input.setClearButtonEnabled(True)
        self._onion_input.textChanged.connect(self._on_url_changed)
        self._onion_input.returnPressed.connect(self._on_download_clicked)
        card.add(self._onion_input)

        self._onion_hint = help_text(t("onion_help"))
        card.add(self._onion_hint)

        self._pw_section = QWidget()
        pw_lay = QVBoxLayout(self._pw_section)
        pw_lay.setContentsMargins(0, 0, 0, 0)
        pw_lay.setSpacing(7)

        self._pw_lbl = field_label(t("pw_label"))
        pw_lay.addWidget(self._pw_lbl)

        self._password_input = QLineEdit()
        self._password_input.setPlaceholderText(t("pw_required_hint"))
        self._password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self._password_input.returnPressed.connect(self._on_download_clicked)

        self._pw_toggle = QPushButton(t("pw_show"))
        self._pw_toggle.setObjectName("ghost")
        self._pw_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        fit_button(self._pw_toggle, t("pw_show"), t("pw_hide"))
        self._pw_toggle.clicked.connect(self._toggle_pw)

        pw_lay.addLayout(row((self._password_input, 1), self._pw_toggle, spacing=6))
        card.add(self._pw_section)
        return card

    def _build_dest_card(self) -> Card:
        card = Card()

        self._save_to_lbl = field_label(t("save_to_label"))
        card.add(self._save_to_lbl)

        self._output_input = QLineEdit()
        self._output_input.setText(load_settings().download_dir)

        self._browse_btn = QPushButton(t("browse_btn"))
        self._browse_btn.setObjectName("ghost")
        self._browse_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        fit_button(self._browse_btn, t("browse_btn"))
        self._browse_btn.clicked.connect(self._browse_output)

        card.add(row((self._output_input, 1), self._browse_btn, spacing=6))
        return card

    def _build_progress_card(self) -> Card:
        card = Card(spacing=13)
        self._progress_card = card
        card.setVisible(False)

        self._file_info = ElidedLabel("", Qt.TextElideMode.ElideMiddle)
        self._file_info.setObjectName("value_label")
        card.add(self._file_info)

        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, _PROGRESS_SCALE)
        card.add(self._progress_bar)

        self._status_row = StatusRow("")
        card.add(self._status_row)

        card.add(h_sep())

        self._open_btn = QPushButton(t("open_folder_btn"))
        self._open_btn.setObjectName("ghost")
        self._open_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._open_btn.setVisible(False)
        self._open_btn.clicked.connect(self._open_folder)
        card.add(row(self._open_btn, None))
        return card

    def _build_footer(self) -> QWidget:
        footer = QWidget()
        footer.setObjectName("footerBar")
        footer.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        lay = QHBoxLayout(footer)
        lay.setContentsMargins(28, 14, 28, 14)
        lay.setSpacing(12)

        self._footer_hint = ElidedLabel(t("footer_hint_url"), Qt.TextElideMode.ElideRight)
        self._footer_hint.setObjectName("help_text")
        lay.addWidget(self._footer_hint, 1)

        self._download_btn = SpinnerButton(t("download_btn"))
        self._download_btn.setObjectName("primary")
        self._download_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._download_btn.setMinimumWidth(150)
        self._download_btn.setEnabled(False)
        self._download_btn.clicked.connect(self._on_download_clicked)
        lay.addWidget(self._download_btn, 0)
        return footer

    # ── i18n ──────────────────────────────────────────────────────

    def retranslate(self) -> None:
        self._title_lbl.setText(t("recv_title"))
        self._onion_lbl.setText(t("onion_label"))
        self._onion_input.setPlaceholderText(t("onion_placeholder"))
        self._onion_hint.setText(t("onion_help"))
        self._pw_lbl.setText(t("pw_label"))
        self._password_input.setPlaceholderText(t("pw_required_hint"))
        hidden = self._password_input.echoMode() == QLineEdit.EchoMode.Password
        self._pw_toggle.setText(t("pw_show") if hidden else t("pw_hide"))
        fit_button(self._pw_toggle, t("pw_show"), t("pw_hide"))
        self._save_to_lbl.setText(t("save_to_label"))
        self._browse_btn.setText(t("browse_btn"))
        fit_button(self._browse_btn, t("browse_btn"))
        self._open_btn.setText(t("open_folder_btn"))
        if not self._download_btn.is_spinning:
            self._download_btn.stop_spin(t("download_btn"))
        self._on_url_changed(self._onion_input.text())

    # ── Slots ─────────────────────────────────────────────────────

    def _toggle_pw(self) -> None:
        hidden = self._password_input.echoMode() == QLineEdit.EchoMode.Password
        self._password_input.setEchoMode(
            QLineEdit.EchoMode.Normal if hidden else QLineEdit.EchoMode.Password
        )
        self._pw_toggle.setText(t("pw_hide") if hidden else t("pw_show"))

    def _on_url_changed(self, text: str) -> None:
        text = text.strip()
        # A URL carrying a #key fragment is keyless; no password to ask for.
        self._pw_section.setVisible("#" not in text)

        if not text:
            state, hint = "", t("footer_hint_url")
        elif ".onion" in text:
            state, hint = "valid", t("footer_hint_ready_dl")
        else:
            state, hint = "invalid", t("onion_invalid")

        # A dynamic property keeps the theme in charge of the actual colours,
        # instead of an inline stylesheet fighting the global one.
        self._onion_input.setProperty("state", state)
        self._onion_input.style().unpolish(self._onion_input)
        self._onion_input.style().polish(self._onion_input)

        self._footer_hint.setText(hint)
        self._download_btn.setEnabled(bool(text) and ".onion" in text and not self._downloading)

    def _browse_output(self) -> None:
        path = QFileDialog.getExistingDirectory(
            self, t("save_to_label"), self._output_input.text()
        )
        if path:
            self._output_input.setText(path)
            self._output_input.setModified(True)

    @qasync.asyncSlot()
    async def _on_download_clicked(self) -> None:
        from hazedrop.core.history import add_entry
        from hazedrop.core.receiver import download_and_decrypt

        if self._downloading:
            return

        onion_url = self._onion_input.text().strip()
        if not onion_url:
            self._show_error(t("onion_required"))
            return

        settings = load_settings()
        password = self._password_input.text() or None
        output_dir = self._output_input.text().strip() or settings.download_dir

        try:
            os.makedirs(output_dir, exist_ok=True)
        except OSError as exc:
            self._show_error(t("output_dir_failed", exc))
            return

        self._downloading = True
        self._download_btn.setEnabled(False)
        self._progress_card.setVisible(True)
        self._progress_bar.setRange(0, 0)  # indeterminate until the first byte
        self._file_info.setText("")
        self._open_btn.setVisible(False)
        self._footer_hint.setText(t("footer_hint_downloading"))
        self._dl_start = time.monotonic()

        try:
            if not self._tor.is_running:
                self._download_btn.start_spin(t("spin_starting_tor"))
                self._status_row.set_status(t("status_starting_tor"), "active")
                self.tor_status_changed.emit("starting", "")

                def _on_tor_progress(msg: str) -> None:
                    for part in msg.split():
                        if part.endswith("%"):
                            self._download_btn.set_spin_label(t("spin_bootstrapping", part))
                            self._status_row.set_status(t("status_bootstrapping", part), "active")
                            self.tor_status_changed.emit("starting", part)

                await self._tor.start(
                    on_progress=_on_tor_progress,
                    bridges=settings.tor_bridges if settings.use_bridges else None,
                    use_bridges=settings.use_bridges,
                )
            self.tor_status_changed.emit("active", "")
        except Exception as exc:  # noqa: BLE001 - surfaced in the UI
            self.tor_status_changed.emit("error", "")
            self._finish_error(t("tor_failed", exc))
            return

        self._download_btn.start_spin(t("spin_connecting"))
        self._status_row.set_status(t("status_connecting_recv"), "active")

        def _on_progress(received: int, total: int) -> None:
            elapsed = time.monotonic() - self._dl_start
            speed = received / elapsed if elapsed > 0 else 0

            if total > 0:
                self._progress_bar.setRange(0, _PROGRESS_SCALE)
                self._progress_bar.setValue(
                    min(_PROGRESS_SCALE, int(received / total * _PROGRESS_SCALE))
                )
                base = (f"{t('status_downloading')}  "
                        f"{_human_size(received)} / {_human_size(total)}")
            else:
                base = f"{t('status_downloading')}  {_human_size(received)}"

            parts = [base]
            if speed > 0:
                parts.append(f"{_human_size(speed)}/s")
            if speed > 0 and total > received:
                parts.append(f"ETA {_format_eta(int((total - received) / speed))}")
            self._status_row.set_status("  ·  ".join(parts), "active")

        def _on_info(info: dict) -> None:
            name = info.get("filename", "")
            size = info.get("size", 0)
            self._file_info.setText(f"{name}  ·  {_human_size(size)}" if name else "")
            self._download_btn.set_spin_label(t("spin_downloading"))

        try:
            out = await download_and_decrypt(
                onion_address=onion_url,
                output_dir=output_dir,
                socks_port=self._tor.socks_port,
                password=password,
                on_progress=_on_progress,
                on_info=_on_info,
            )
            self._saved_path = out
            fname = os.path.basename(out)
            fsize = os.path.getsize(out) if os.path.exists(out) else 0

            self._progress_bar.setRange(0, _PROGRESS_SCALE)
            self._progress_bar.setValue(_PROGRESS_SCALE)
            self._status_row.set_status(t("saved_as", fname), "success")
            self._file_info.setText(f"{fname}  ·  {_human_size(fsize)}")
            self._open_btn.setVisible(True)
            self._footer_hint.setText(t("footer_hint_saved"))

            if self._tray:
                self._tray.notify("HazeDrop", t("notify_dl_complete_recv", fname))
            if settings.history_enabled:
                add_entry("receive", fname, fsize, onion_url, "completed",
                          ttl_days=settings.history_ttl_days)
        except (ConnectionError, TimeoutError, PermissionError, FileNotFoundError) as exc:
            self._finish_error(str(exc) or exc.__class__.__name__, log=settings.history_enabled,
                               url=onion_url, ttl=settings.history_ttl_days)
            return
        except Exception as exc:  # noqa: BLE001 - surfaced in the UI
            self._finish_error(t("status_error_prefix", exc), log=settings.history_enabled,
                               url=onion_url, ttl=settings.history_ttl_days)
            return
        finally:
            self._downloading = False
            self._download_btn.stop_spin(t("download_btn"))
            self._on_url_changed(self._onion_input.text())

    # ── Helpers ───────────────────────────────────────────────────

    def _show_error(self, message: str) -> None:
        self._progress_card.setVisible(True)
        self._progress_bar.setRange(0, _PROGRESS_SCALE)
        self._progress_bar.setValue(0)
        self._status_row.set_status(message, "error")

    def _finish_error(self, message: str, log: bool = False,
                      url: str = "", ttl: int = 7) -> None:
        self._downloading = False
        self._download_btn.stop_spin(t("download_btn"))
        self._show_error(message)
        self._footer_hint.setText(t("footer_hint_failed"))
        self._on_url_changed(self._onion_input.text())
        if log and url:
            from hazedrop.core.history import add_entry
            add_entry("receive", url, 0, url, "error", ttl_days=ttl)

    def _open_folder(self) -> None:
        if not self._saved_path:
            return
        folder = os.path.dirname(self._saved_path)
        try:
            if sys.platform == "darwin":
                subprocess.Popen(["open", folder])
            elif os.name == "nt":
                os.startfile(folder)  # type: ignore[attr-defined]
            else:
                subprocess.Popen(["xdg-open", folder])
        except Exception as exc:  # noqa: BLE001 - surfaced in the UI
            self._status_row.set_status(t("open_folder_failed", exc), "error")
