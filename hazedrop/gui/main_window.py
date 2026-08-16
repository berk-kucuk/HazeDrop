from __future__ import annotations

import asyncio
import base64
import sys

from PyQt6.QtCore import QByteArray, Qt
from PyQt6.QtGui import QCloseEvent, QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QApplication, QHBoxLayout, QLabel, QPushButton, QSizePolicy,
    QStackedWidget, QVBoxLayout, QWidget,
)

from hazedrop.core.settings import load_settings, save_settings
from hazedrop.core.tor_manager import TorManager
from hazedrop.gui.receive_panel import ReceivePanel
from hazedrop.gui.send_panel import SendPanel
from hazedrop.gui.settings_panel import SettingsPanel
from hazedrop.gui.theme import COLORS, STYLESHEET, build_palette
from hazedrop.gui.title_bar import TitleBar
from hazedrop.gui.tray import HazeTray
from hazedrop.i18n import set_language, t
from hazedrop.secure.memory import panic

_NAV_ICONS = ("↑", "↓", "⚙")
_NAV_KEYS = ("nav_send", "nav_recv", "nav_conf")

#: Grab zone around a frameless window. The root layout reserves this much so
#: the edge is not covered by a child widget that would swallow the press.
_RESIZE_MARGIN = 5

_MIN_WIDTH = 680
_MIN_HEIGHT = 520


class NavButton(QPushButton):
    def __init__(self, arrow: str, label: str, active: bool = False, parent=None) -> None:
        super().__init__(f"{arrow}\n{label}", parent)
        self._arrow = arrow
        self.setObjectName("nav_btn_active" if active else "nav_btn")
        self.setCheckable(True)
        self.setChecked(active)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedWidth(70)
        self.setMinimumHeight(56)

    def set_label(self, label: str) -> None:
        self.setText(f"{self._arrow}\n{label}")

    def set_active(self, active: bool) -> None:
        self.setChecked(active)
        self.setObjectName("nav_btn_active" if active else "nav_btn")
        self.style().unpolish(self)
        self.style().polish(self)


class MainWindow(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self._tor = TorManager()
        self._resize_edges: Qt.Edge | None = None
        self._setup_window()
        self._build_ui()
        self._install_shortcuts()
        self._tray = HazeTray(self)
        self._tray.show()
        self._send_panel.set_tray(self._tray)
        self._recv_panel.set_tray(self._tray)

    # ── Window chrome ─────────────────────────────────────────────

    def _setup_window(self) -> None:
        self.setObjectName("root")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window)
        self.setWindowTitle("HazeDrop")
        self.setMinimumSize(_MIN_WIDTH, _MIN_HEIGHT)
        # Needed for the edge-hover cursor feedback below.
        self.setMouseTracking(True)
        self._restore_geometry()

    def _restore_geometry(self) -> None:
        saved = load_settings().window_geometry
        if saved:
            try:
                if self.restoreGeometry(QByteArray(base64.b64decode(saved))):
                    return
            except Exception:
                pass
        self.resize(880, 640)
        screen = QApplication.primaryScreen()
        if screen is not None:
            frame = self.frameGeometry()
            frame.moveCenter(screen.availableGeometry().center())
            self.move(frame.topLeft())

    def _persist_geometry(self) -> None:
        try:
            settings = load_settings()
            settings.window_geometry = base64.b64encode(
                bytes(self.saveGeometry())
            ).decode("ascii")
            save_settings(settings)
        except Exception:
            pass

    # ── UI ────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(*(_RESIZE_MARGIN,) * 4)
        root.setSpacing(0)
        self._root_layout = root

        self._title_bar = TitleBar(self)
        self._title_bar.panic_triggered.connect(self._on_panic)
        self._title_bar.renew_circuit.connect(self._on_renew)
        root.addWidget(self._title_bar)

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        root.addLayout(body, 1)

        body.addWidget(self._build_sidebar())

        self._stack = QStackedWidget()
        self._stack.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._send_panel = SendPanel(self._tor, self)
        self._recv_panel = ReceivePanel(self._tor, self)
        self._settings_panel = SettingsPanel(self)

        self._send_panel.tor_status_changed.connect(self._title_bar.set_tor_status)
        self._recv_panel.tor_status_changed.connect(self._title_bar.set_tor_status)
        self._settings_panel.settings_changed.connect(self._on_settings_changed)

        # Both panels drive the same TorManager, so STOP on one must not tear
        # down a transfer running in the other.
        self._send_panel.tor_needed_elsewhere = lambda: self._recv_panel.is_busy

        for panel in (self._send_panel, self._recv_panel, self._settings_panel):
            self._stack.addWidget(panel)
        body.addWidget(self._stack, 1)

    def _build_sidebar(self) -> QWidget:
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        sidebar.setFixedWidth(78)

        lay = QVBoxLayout(sidebar)
        lay.setContentsMargins(4, 14, 4, 10)
        lay.setSpacing(4)

        self._nav_btns: list[NavButton] = []
        for i, (arrow, key) in enumerate(zip(_NAV_ICONS, _NAV_KEYS)):
            btn = NavButton(arrow, t(key), active=(i == 0))
            btn.setToolTip(f"{t(key)}  ·  Ctrl+{i + 1}")
            btn.clicked.connect(lambda _checked=False, idx=i: self._switch(idx))
            lay.addWidget(btn, 0, Qt.AlignmentFlag.AlignHCenter)
            self._nav_btns.append(btn)

        lay.addStretch(1)

        from hazedrop import __version__
        ver = QLabel(f"v{__version__}")
        ver.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ver.setStyleSheet(
            f"color: {COLORS['text_muted']}; font-size: 9px;"
            f"letter-spacing: 0.5px; background: transparent;"
        )
        lay.addWidget(ver)
        return sidebar

    def _install_shortcuts(self) -> None:
        for i in range(3):
            QShortcut(QKeySequence(f"Ctrl+{i + 1}"), self,
                      activated=lambda idx=i: self._switch(idx))
        # Documented in the README but never actually wired up before.
        QShortcut(QKeySequence("Ctrl+\\"), self, activated=self._on_panic)
        QShortcut(QKeySequence("Ctrl+W"), self, activated=self.close)

    def _switch(self, index: int) -> None:
        self._stack.setCurrentIndex(index)
        for i, btn in enumerate(self._nav_btns):
            btn.set_active(i == index)

    # ── Frameless resizing ────────────────────────────────────────

    def _edges_at(self, pos) -> Qt.Edge | None:
        margin = _RESIZE_MARGIN
        x, y, w, h = pos.x(), pos.y(), self.width(), self.height()
        edges: Qt.Edge | None = None

        def add(edge: Qt.Edge) -> None:
            nonlocal edges
            edges = edge if edges is None else edges | edge

        if x <= margin:
            add(Qt.Edge.LeftEdge)
        elif x >= w - margin:
            add(Qt.Edge.RightEdge)
        if y <= margin:
            add(Qt.Edge.TopEdge)
        elif y >= h - margin:
            add(Qt.Edge.BottomEdge)
        return edges

    @staticmethod
    def _cursor_for(edges: Qt.Edge | None) -> Qt.CursorShape:
        if edges is None:
            return Qt.CursorShape.ArrowCursor
        left = bool(edges & Qt.Edge.LeftEdge)
        right = bool(edges & Qt.Edge.RightEdge)
        top = bool(edges & Qt.Edge.TopEdge)
        bottom = bool(edges & Qt.Edge.BottomEdge)
        if (top and left) or (bottom and right):
            return Qt.CursorShape.SizeFDiagCursor
        if (top and right) or (bottom and left):
            return Qt.CursorShape.SizeBDiagCursor
        if left or right:
            return Qt.CursorShape.SizeHorCursor
        return Qt.CursorShape.SizeVerCursor

    def mouseMoveEvent(self, event) -> None:  # noqa: N802 - Qt naming
        if not self.isMaximized():
            self.setCursor(self._cursor_for(self._edges_at(event.position().toPoint())))
        super().mouseMoveEvent(event)

    def mousePressEvent(self, event) -> None:  # noqa: N802 - Qt naming
        if event.button() == Qt.MouseButton.LeftButton and not self.isMaximized():
            edges = self._edges_at(event.position().toPoint())
            handle = self.windowHandle()
            if edges is not None and handle is not None:
                handle.startSystemResize(edges)
                event.accept()
                return
        super().mousePressEvent(event)

    def leaveEvent(self, event) -> None:  # noqa: N802 - Qt naming
        self.unsetCursor()
        super().leaveEvent(event)

    def changeEvent(self, event) -> None:  # noqa: N802 - Qt naming
        super().changeEvent(event)
        if event.type() == event.Type.WindowStateChange:
            # A maximized window sits flush against the screen edge, so the
            # grab margin only gets in the way there.
            margin = 0 if self.isMaximized() else _RESIZE_MARGIN
            self._root_layout.setContentsMargins(*(margin,) * 4)
            self._title_bar.sync_maximize_state()

    # ── i18n ──────────────────────────────────────────────────────

    def retranslate_all(self) -> None:
        for i, key in enumerate(_NAV_KEYS):
            self._nav_btns[i].set_label(t(key))
            self._nav_btns[i].setToolTip(f"{t(key)}  ·  Ctrl+{i + 1}")
        self._title_bar.retranslate()
        self._send_panel.retranslate()
        self._recv_panel.retranslate()
        self._settings_panel.retranslate()
        self._tray.retranslate()

    def _on_settings_changed(self) -> None:
        self.retranslate_all()
        self._recv_panel.reload_defaults()
        self._send_panel.reload_defaults()

    # ── Lifecycle ─────────────────────────────────────────────────

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802 - Qt naming
        self._persist_geometry()
        if load_settings().minimize_to_tray:
            self.hide()
            event.ignore()
        else:
            event.accept()
            QApplication.quit()

    def _on_panic(self) -> None:
        keys = []
        if self._send_panel.active_key is not None:
            keys.append(self._send_panel.active_key)
        panic(keys)

    def _on_renew(self) -> None:
        asyncio.ensure_future(self._tor.renew_circuit())


#: Name of the local socket used to detect an already-running instance.
_SINGLE_INSTANCE_KEY = "hazedrop-gui-singleton"


def launch_gui() -> None:
    import qasync
    from PyQt6.QtNetwork import QLocalServer, QLocalSocket

    from hazedrop.gui.tray import load_app_icon

    settings = load_settings()
    set_language(settings.language)

    app = QApplication(sys.argv)
    app.setApplicationName("HazeDrop")
    app.setApplicationDisplayName("HazeDrop")
    app.setDesktopFileName("hazedrop")
    app.setStyle("Fusion")           # predictable base for the stylesheet
    app.setPalette(build_palette())  # keeps native popups dark
    app.setStyleSheet(STYLESHEET)
    app.setWindowIcon(load_app_icon())
    app.setQuitOnLastWindowClosed(False)  # the tray keeps the app alive

    # ── Single instance ──────────────────────────────────────────
    # Closing the window minimizes to the tray rather than quitting, so a
    # second launch (desktop icon, launcher, `hazedrop` in a new terminal)
    # used to start an entirely new process — its own tray icon and its own
    # window — while the first kept running hidden. Detect that here and
    # just raise the existing window instead of starting a duplicate.
    probe = QLocalSocket()
    probe.connectToServer(_SINGLE_INSTANCE_KEY)
    already_running = probe.waitForConnected(200)
    probe.close()
    if already_running:
        return

    # No peer answered — either we're first, or a previous instance crashed
    # and left its socket file behind. removeServer() clears the stale file
    # before we claim the name.
    QLocalServer.removeServer(_SINGLE_INSTANCE_KEY)
    server = QLocalServer()
    server.listen(_SINGLE_INSTANCE_KEY)

    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)

    with loop:
        window = MainWindow()
        window.setWindowIcon(load_app_icon())
        window.show()

        def _on_relaunch() -> None:
            conn = server.nextPendingConnection()
            if conn is not None:
                conn.disconnectFromServer()
            window.showNormal()
            window.raise_()
            window.activateWindow()

        server.newConnection.connect(_on_relaunch)

        loop.run_forever()
