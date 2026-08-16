from __future__ import annotations

import os

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox, QComboBox, QFileDialog, QFrame, QHBoxLayout, QLabel, QLineEdit,
    QPlainTextEdit, QPushButton, QScrollArea, QSpinBox, QVBoxLayout, QWidget,
)

from hazedrop.core.duration import parse_duration
from hazedrop.core.history import clear_history
from hazedrop.core.settings import Settings, load_settings, save_settings
from hazedrop.gui.widgets import (
    Card, ElidedLabel, field_label, fit_button, help_text, on_toggle, row,
    section_title,
)
from hazedrop.i18n import LANGUAGE_OPTIONS, set_language, t


class SettingsPanel(QWidget):
    settings_changed = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("panel")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._settings: Settings = load_settings()
        self._build_ui()
        self._populate()

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

        self._title_lbl = section_title(t("settings_title"))
        layout.addWidget(self._title_lbl)

        layout.addWidget(self._build_general_card())
        layout.addWidget(self._build_transfer_card())
        layout.addWidget(self._build_history_card())
        layout.addWidget(self._build_bridges_card())
        layout.addWidget(self._build_language_card())
        layout.addStretch(1)

        scroll.setWidget(content)
        outer.addWidget(scroll, 1)
        outer.addWidget(self._build_footer())

    def _build_general_card(self) -> Card:
        card = Card()
        self._general_lbl = section_title(t("general_section"))
        card.add(self._general_lbl)

        self._dl_dir_lbl = field_label(t("dl_dir_label"))
        card.add(self._dl_dir_lbl)

        self._dl_dir_input = QLineEdit()
        self._dl_dir_input.setPlaceholderText(os.path.expanduser("~/Downloads"))

        self._browse_btn = QPushButton(t("browse_btn"))
        self._browse_btn.setObjectName("ghost")
        self._browse_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        fit_button(self._browse_btn, t("browse_btn"))
        self._browse_btn.clicked.connect(self._browse_dir)

        card.add(row((self._dl_dir_input, 1), self._browse_btn, spacing=6))

        self._minimize_check = QCheckBox(t("minimize_tray_check"))
        self._minimize_check.setCursor(Qt.CursorShape.PointingHandCursor)
        card.add(self._minimize_check)
        return card

    def _build_transfer_card(self) -> Card:
        card = Card()
        self._transfer_lbl = section_title(t("transfer_section"))
        card.add(self._transfer_lbl)

        self._max_dl_lbl = field_label(t("max_dl_label"))
        self._max_dl_spin = QSpinBox()
        self._max_dl_spin.setRange(0, 999)
        self._max_dl_spin.setFixedWidth(96)
        self._max_dl_spin.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self._max_dl_spin.setSpecialValueText(t("unlimited"))
        card.add(row((self._max_dl_lbl, 1), self._max_dl_spin, spacing=10))

        self._max_dl_help = help_text(t("max_dl_help"))
        card.add(self._max_dl_help)

        self._expire_lbl = field_label(t("default_expire_label"))
        self._expire_input = QLineEdit()
        self._expire_input.setPlaceholderText(t("expire_hint"))
        self._expire_input.setFixedWidth(140)
        self._expire_input.textChanged.connect(self._validate_expire)
        card.add(row((self._expire_lbl, 1), self._expire_input, spacing=10))

        self._expire_error = QLabel("")
        self._expire_error.setObjectName("inline_error")
        self._expire_error.setVisible(False)
        card.add(self._expire_error)
        return card

    def _build_history_card(self) -> Card:
        card = Card()
        self._history_lbl = section_title(t("history_section"))
        card.add(self._history_lbl)

        self._history_check = QCheckBox(t("history_check"))
        self._history_check.setCursor(Qt.CursorShape.PointingHandCursor)
        on_toggle(self._history_check, self._on_history_toggled)
        card.add(self._history_check)

        self._ttl_lbl = field_label(t("history_ttl_label"))
        self._ttl_spin = QSpinBox()
        self._ttl_spin.setRange(1, 365)
        self._ttl_spin.setFixedWidth(96)
        self._ttl_spin.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        card.add(row((self._ttl_lbl, 1), self._ttl_spin, spacing=10))

        self._clear_btn = QPushButton(t("clear_history_btn"))
        self._clear_btn.setObjectName("ghost")
        self._clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._clear_btn.clicked.connect(self._on_clear_history)
        card.add(row(self._clear_btn, None))
        return card

    def _build_bridges_card(self) -> Card:
        card = Card()
        self._bridges_lbl = section_title(t("bridges_section"))
        card.add(self._bridges_lbl)

        self._bridges_check = QCheckBox(t("use_bridges_check"))
        self._bridges_check.setCursor(Qt.CursorShape.PointingHandCursor)
        on_toggle(self._bridges_check, self._on_bridges_toggled)
        card.add(self._bridges_check)

        self._bridges_help = help_text(t("bridges_help"))
        card.add(self._bridges_help)

        self._bridge_lines_lbl = field_label(t("bridge_lines_label"))
        card.add(self._bridge_lines_lbl)

        self._bridges_input = QPlainTextEdit()
        self._bridges_input.setObjectName("bridges")
        self._bridges_input.setFixedHeight(110)
        self._bridges_input.setPlaceholderText(t("bridge_placeholder"))
        self._bridges_input.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self._bridges_input.setEnabled(False)
        card.add(self._bridges_input)
        return card

    def _build_language_card(self) -> Card:
        card = Card()
        self._language_lbl = section_title(t("language_section"))
        card.add(self._language_lbl)

        self._language_field_lbl = field_label(t("language_label"))
        self._lang_combo = QComboBox()
        self._lang_combo.setCursor(Qt.CursorShape.PointingHandCursor)
        self._lang_combo.setFixedWidth(180)
        for code, name in LANGUAGE_OPTIONS.items():
            self._lang_combo.addItem(name, code)
        card.add(row((self._language_field_lbl, 1), self._lang_combo, spacing=10))

        self._language_help = help_text(t("language_help"))
        card.add(self._language_help)
        return card

    def _build_footer(self) -> QWidget:
        footer = QWidget()
        footer.setObjectName("footerBar")
        footer.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        lay = QHBoxLayout(footer)
        lay.setContentsMargins(28, 14, 28, 14)
        lay.setSpacing(12)

        self._save_status = ElidedLabel("", Qt.TextElideMode.ElideRight)
        self._save_status.setObjectName("help_text")
        lay.addWidget(self._save_status, 1)

        self._save_btn = QPushButton(t("save_btn"))
        self._save_btn.setObjectName("primary")
        self._save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._save_btn.setMinimumWidth(150)
        self._save_btn.clicked.connect(self._on_save)
        lay.addWidget(self._save_btn, 0)
        return footer

    # ── Population ────────────────────────────────────────────────

    def _populate(self) -> None:
        s = self._settings
        self._dl_dir_input.setText(s.download_dir)
        self._minimize_check.setChecked(s.minimize_to_tray)
        self._max_dl_spin.setValue(s.max_downloads)
        self._expire_input.setText(s.default_expire)
        self._history_check.setChecked(s.history_enabled)
        self._ttl_spin.setValue(s.history_ttl_days)
        self._ttl_spin.setEnabled(s.history_enabled)
        self._clear_btn.setEnabled(s.history_enabled)
        self._bridges_check.setChecked(s.use_bridges)
        self._bridges_input.setPlainText("\n".join(s.tor_bridges))
        self._bridges_input.setEnabled(s.use_bridges)
        for i in range(self._lang_combo.count()):
            if self._lang_combo.itemData(i) == s.language:
                self._lang_combo.setCurrentIndex(i)
                break

    # ── i18n ──────────────────────────────────────────────────────

    def retranslate(self) -> None:
        self._title_lbl.setText(t("settings_title"))
        self._general_lbl.setText(t("general_section"))
        self._dl_dir_lbl.setText(t("dl_dir_label"))
        self._browse_btn.setText(t("browse_btn"))
        fit_button(self._browse_btn, t("browse_btn"))
        self._minimize_check.setText(t("minimize_tray_check"))
        self._transfer_lbl.setText(t("transfer_section"))
        self._max_dl_lbl.setText(t("max_dl_label"))
        self._max_dl_spin.setSpecialValueText(t("unlimited"))
        self._max_dl_help.setText(t("max_dl_help"))
        self._expire_lbl.setText(t("default_expire_label"))
        self._expire_input.setPlaceholderText(t("expire_hint"))
        self._history_lbl.setText(t("history_section"))
        self._history_check.setText(t("history_check"))
        self._ttl_lbl.setText(t("history_ttl_label"))
        self._clear_btn.setText(t("clear_history_btn"))
        self._bridges_lbl.setText(t("bridges_section"))
        self._bridges_check.setText(t("use_bridges_check"))
        self._bridges_help.setText(t("bridges_help"))
        self._bridge_lines_lbl.setText(t("bridge_lines_label"))
        self._bridges_input.setPlaceholderText(t("bridge_placeholder"))
        self._language_lbl.setText(t("language_section"))
        self._language_field_lbl.setText(t("language_label"))
        self._language_help.setText(t("language_help"))
        self._save_btn.setText(t("save_btn"))
        self._validate_expire()

    # ── Slots ─────────────────────────────────────────────────────

    def _browse_dir(self) -> None:
        path = QFileDialog.getExistingDirectory(
            self, t("dl_dir_label"), self._dl_dir_input.text()
        )
        if path:
            self._dl_dir_input.setText(path)

    def _on_bridges_toggled(self, checked: bool) -> None:
        self._bridges_input.setEnabled(checked)

    def _on_history_toggled(self, checked: bool) -> None:
        self._ttl_spin.setEnabled(checked)
        self._clear_btn.setEnabled(checked)

    def _on_clear_history(self) -> None:
        clear_history()
        self._flash(t("history_cleared"))

    def _validate_expire(self) -> bool:
        text = self._expire_input.text().strip()
        valid = True
        if text:
            try:
                parse_duration(text)
            except ValueError:
                valid = False
        self._expire_error.setText("" if valid else t("expire_invalid"))
        self._expire_error.setVisible(not valid)
        self._expire_input.setProperty("state", "" if valid else "invalid")
        self._expire_input.style().unpolish(self._expire_input)
        self._expire_input.style().polish(self._expire_input)
        return valid

    def _flash(self, message: str) -> None:
        self._save_status.setText(message)
        QTimer.singleShot(2600, lambda: self._save_status.setText(""))

    def _on_save(self) -> None:
        if not self._validate_expire():
            self._flash(t("expire_invalid"))
            return

        s = self._settings
        s.download_dir = self._dl_dir_input.text().strip() or os.path.expanduser("~/Downloads")
        s.minimize_to_tray = self._minimize_check.isChecked()
        s.max_downloads = self._max_dl_spin.value()
        s.default_expire = self._expire_input.text().strip()
        s.history_enabled = self._history_check.isChecked()
        s.history_ttl_days = self._ttl_spin.value()
        s.use_bridges = self._bridges_check.isChecked()
        s.tor_bridges = [
            line.strip()
            for line in self._bridges_input.toPlainText().splitlines()
            if line.strip()
        ]

        new_lang = self._lang_combo.currentData()
        lang_changed = new_lang != s.language
        s.language = new_lang

        save_settings(s)

        if lang_changed:
            # Applied live via retranslate(); no restart needed any more.
            set_language(new_lang)

        self.settings_changed.emit()
        self._flash(t("settings_saved"))
