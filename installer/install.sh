#!/usr/bin/env bash
# ══════════════════════════════════════════════════════════════════════════════
#  HazeDrop Installer
#  Supports: Arch · Debian/Ubuntu · Fedora/RHEL · openSUSE · Void · Alpine
#            Gentoo · macOS (Homebrew)
#  Usage:  bash install.sh [--uninstall] [--no-deps] [--system]
# ══════════════════════════════════════════════════════════════════════════════
set -euo pipefail

# ── App metadata ───────────────────────────────────────────────────────────
APP_NAME="hazedrop"
APP_VERSION="1.0.0"

# ── Default paths (user install) ───────────────────────────────────────────
USER_INSTALL_BASE="$HOME/.local/share/hazedrop"
USER_BIN_DIR="$HOME/.local/bin"
USER_DESKTOP_DIR="$HOME/.local/share/applications"
USER_PIXMAP_DIR="$HOME/.local/share/pixmaps"

# ── System paths ───────────────────────────────────────────────────────────
SYS_INSTALL_BASE="/opt/hazedrop"
SYS_BIN_DIR="/usr/local/bin"
SYS_DESKTOP_DIR="/usr/share/applications"
SYS_PIXMAP_DIR="/usr/share/pixmaps"

# ── Parse arguments ────────────────────────────────────────────────────────
OPT_UNINSTALL=false
OPT_NO_DEPS=false
OPT_SYSTEM=false

for arg in "$@"; do
    case "$arg" in
        --uninstall|-u) OPT_UNINSTALL=true ;;
        --no-deps)      OPT_NO_DEPS=true   ;;
        --system)       OPT_SYSTEM=true    ;;
        --help|-h)
            cat <<HELP
Usage: bash install.sh [OPTIONS]

Options:
  --uninstall    Remove HazeDrop and all installed files
  --no-deps      Skip automatic system package installation
  --system       Install system-wide to /opt/hazedrop (requires sudo)
  --help         Show this message

Examples:
  bash install.sh                 # User install (~/.local)
  bash install.sh --system        # System-wide install (/opt)
  bash install.sh --uninstall     # Remove user install
  bash install.sh --no-deps       # Skip apt/pacman/dnf step
HELP
            exit 0
            ;;
        *)
            echo "Unknown option: $arg  (try --help)"
            exit 1
            ;;
    esac
done

# ── Resolve active install paths ───────────────────────────────────────────
if $OPT_SYSTEM; then
    INSTALL_BASE="$SYS_INSTALL_BASE"
    BIN_DIR="$SYS_BIN_DIR"
    DESKTOP_DIR="$SYS_DESKTOP_DIR"
    PIXMAP_DIR="$SYS_PIXMAP_DIR"
    NEED_SUDO=true
else
    INSTALL_BASE="$USER_INSTALL_BASE"
    BIN_DIR="$USER_BIN_DIR"
    DESKTOP_DIR="$USER_DESKTOP_DIR"
    PIXMAP_DIR="$USER_PIXMAP_DIR"
    NEED_SUDO=false
fi

VENV_DIR="$INSTALL_BASE/venv"
LAUNCHER="$BIN_DIR/hazedrop"
DESKTOP_FILE="$DESKTOP_DIR/hazedrop.desktop"
ICON_DEST="$PIXMAP_DIR/hazedrop.png"

# Helper: run with sudo only when needed
_run() {
    if $NEED_SUDO; then sudo "$@"; else "$@"; fi
}

# ── Colors ─────────────────────────────────────────────────────────────────
if [[ -t 1 ]]; then
    R='\033[0;31m' G='\033[0;32m' Y='\033[1;33m'
    C='\033[0;36m' B='\033[1m'   D='\033[2m'   N='\033[0m'
else
    R='' G='' Y='' C='' B='' D='' N=''
fi

_info()    { echo -e "  ${C}◈${N}  $*"; }
_ok()      { echo -e "  ${G}✓${N}  $*"; }
_warn()    { echo -e "  ${Y}!${N}  $*"; }
_err()     { echo -e "  ${R}✕${N}  $*" >&2; }
_die()     { _err "$*"; exit 1; }
_section() { echo -e "\n${B}$*${N}"; }

# ── Find project root ──────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -f "$SCRIPT_DIR/pyproject.toml" ]]; then
    PROJECT_ROOT="$SCRIPT_DIR"
elif [[ -f "$SCRIPT_DIR/../pyproject.toml" ]]; then
    PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
else
    _die "Cannot find pyproject.toml. Run from the project root or installer/ directory."
fi

LOGO_SRC="$PROJECT_ROOT/hazedrop/assets/logo.png"

# ══════════════════════════════════════════════════════════════════════════════
#  UNINSTALL
# ══════════════════════════════════════════════════════════════════════════════
if $OPT_UNINSTALL; then
    _section "◈  HazeDrop — Uninstall"
    echo ""
    removed=0

    for path in "$INSTALL_BASE" "$USER_INSTALL_BASE" "$SYS_INSTALL_BASE"; do
        if [[ -d "$path" ]]; then
            _run rm -rf "$path"
            _ok "Removed $path"
            removed=1
        fi
    done

    for path in "$LAUNCHER" "$USER_BIN_DIR/hazedrop" "$SYS_BIN_DIR/hazedrop"; do
        if [[ -f "$path" ]]; then
            _run rm -f "$path"
            _ok "Removed $path"
            removed=1
        fi
    done

    for path in "$DESKTOP_FILE" \
                "$USER_DESKTOP_DIR/hazedrop.desktop" \
                "$SYS_DESKTOP_DIR/hazedrop.desktop"; do
        if [[ -f "$path" ]]; then
            _run rm -f "$path"
            _ok "Removed $path"
            removed=1
        fi
    done

    for path in "$ICON_DEST" \
                "$USER_PIXMAP_DIR/hazedrop.png" \
                "$SYS_PIXMAP_DIR/hazedrop.png"; do
        if [[ -f "$path" ]]; then
            _run rm -f "$path"
            _ok "Removed icon $path"
            removed=1
        fi
    done

    # Refresh desktop/icon caches
    command -v update-desktop-database &>/dev/null && \
        update-desktop-database "$USER_DESKTOP_DIR" 2>/dev/null || true
    command -v xdg-desktop-menu &>/dev/null && \
        xdg-desktop-menu forceupdate 2>/dev/null || true

    echo ""
    if [[ $removed -eq 1 ]]; then
        _ok "Uninstall complete."
    else
        _warn "Nothing to uninstall — HazeDrop was not found."
    fi
    exit 0
fi

# ══════════════════════════════════════════════════════════════════════════════
#  INSTALL
# ══════════════════════════════════════════════════════════════════════════════
echo ""
echo -e "${B}  ◈  HazeDrop ${APP_VERSION} — Installer${N}"
echo -e "${D}  Anonymous encrypted file transfer over Tor${N}"
echo ""

# ── Detect OS and package manager ─────────────────────────────────────────
_detect_os() {
    if [[ -f /etc/os-release ]]; then
        # shellcheck source=/dev/null
        source /etc/os-release
        echo "${ID:-unknown}"
    elif [[ "$(uname -s 2>/dev/null)" == "Darwin" ]]; then
        echo "macos"
    else
        echo "unknown"
    fi
}

_detect_pm() {
    for pm in pacman apt-get dnf yum zypper xbps-install emerge apk brew; do
        command -v "$pm" &>/dev/null && { echo "$pm"; return; }
    done
    echo "unknown"
}

OS_ID="$(_detect_os)"
PKG_MGR="$(_detect_pm)"
_info "OS: ${OS_ID}   Package manager: ${PKG_MGR}"

# ── Existing install check ─────────────────────────────────────────────────
if [[ -x "$VENV_DIR/bin/hazedrop" ]]; then
    _warn "HazeDrop is already installed at $INSTALL_BASE"
    printf "     Update existing installation? [y/N] "
    read -r reply
    [[ "${reply,,}" == "y" ]] || { echo "Aborted."; exit 0; }
fi

# ── [1/4] System dependencies ─────────────────────────────────────────────
_section "  [1/4] System dependencies"

if $OPT_NO_DEPS; then
    _info "Skipping (--no-deps)"
else
    _install_pkgs() {
        case "$PKG_MGR" in
            pacman)
                _info "Installing via pacman..."
                sudo pacman -Sy --needed --noconfirm \
                    python tor python-pip
                ;;
            apt-get)
                _info "Installing via apt-get..."
                sudo apt-get update -qq
                sudo DEBIAN_FRONTEND=noninteractive apt-get install -y \
                    --no-install-recommends \
                    python3 python3-pip python3-venv tor \
                    libgl1 libglib2.0-0 libdbus-1-3
                ;;
            dnf)
                _info "Installing via dnf..."
                sudo dnf install -y \
                    python3 python3-pip tor \
                    mesa-libGL dbus-libs
                ;;
            yum)
                _info "Installing via yum..."
                sudo yum install -y python3 python3-pip tor
                ;;
            zypper)
                _info "Installing via zypper..."
                sudo zypper install -y \
                    python3 python3-pip tor libGL1 libglib-2_0-0
                ;;
            xbps-install)
                _info "Installing via xbps..."
                sudo xbps-install -Sy python3 python3-pip tor
                ;;
            apk)
                _info "Installing via apk..."
                sudo apk add --no-cache python3 py3-pip tor
                ;;
            brew)
                _info "Installing via Homebrew..."
                brew install python@3.12 tor
                ;;
            emerge)
                _info "Installing via emerge..."
                sudo emerge --ask=n dev-python/pip net-vpn/tor
                ;;
            *)
                _warn "Unknown package manager."
                _warn "Ensure python3 (≥3.11), pip, venv and tor are installed."
                ;;
        esac
    }

    if ! _install_pkgs; then
        _warn "Dependency installation encountered errors — continuing anyway."
        _warn "If pip or tor are missing, install them manually and re-run."
    fi
fi

# ── [2/4] Python & venv ────────────────────────────────────────────────────
_section "  [2/4] Python environment"

PYTHON_CMD=""
for cmd in python3.13 python3.12 python3.11 python3 python; do
    if command -v "$cmd" &>/dev/null; then
        is_new=$("$cmd" -c "import sys; print(sys.version_info>=(3,11))" 2>/dev/null || echo "False")
        if [[ "$is_new" == "True" ]]; then
            PYTHON_CMD="$cmd"; break
        fi
    fi
done
[[ -n "$PYTHON_CMD" ]] || _die "Python 3.11 or newer is required but not found."

PY_VER=$("$PYTHON_CMD" -c "import sys; v=sys.version_info; print(f'{v.major}.{v.minor}.{v.micro}')")
_ok "Python: $PYTHON_CMD  ($PY_VER)"

if command -v tor &>/dev/null; then
    TOR_VER=$(tor --version 2>/dev/null | head -1 | grep -oP '\d+\.\d+\.\d+(\.\d+)?' || echo "?")
    _ok "Tor: $TOR_VER"
else
    _warn "Tor binary not found — install tor and ensure it is in PATH."
fi

_info "Creating virtual environment: $VENV_DIR"
_run mkdir -p "$INSTALL_BASE"
"$PYTHON_CMD" -m venv "$VENV_DIR"
_ok "Virtual environment ready"

_info "Installing HazeDrop..."
"$VENV_DIR/bin/pip" install --quiet --upgrade pip
"$VENV_DIR/bin/pip" install --quiet "$PROJECT_ROOT"
INSTALLED_VER=$("$VENV_DIR/bin/python" -c "import hazedrop; print(hazedrop.__version__)" 2>/dev/null || echo "$APP_VERSION")
_ok "HazeDrop $INSTALLED_VER installed"

# ── [3/4] Launcher, icon, .desktop ────────────────────────────────────────
_section "  [3/4] Desktop integration"

# Launcher
_run mkdir -p "$BIN_DIR"
_run tee "$LAUNCHER" > /dev/null <<LAUNCHER_CONTENT
#!/usr/bin/env bash
# HazeDrop launcher — generated by install.sh
exec "${VENV_DIR}/bin/hazedrop" "\$@"
LAUNCHER_CONTENT
_run chmod +x "$LAUNCHER"
_ok "Launcher: $LAUNCHER"

# Icon
_run mkdir -p "$PIXMAP_DIR"
ICON_PATH="$ICON_DEST"
if [[ -f "$LOGO_SRC" ]]; then
    _run cp "$LOGO_SRC" "$ICON_DEST"
    _ok "Icon: $ICON_DEST"
else
    # Try from installed package
    INSTALLED_LOGO=$(find "$VENV_DIR" -name "logo.png" 2>/dev/null | head -1 || true)
    if [[ -n "$INSTALLED_LOGO" ]]; then
        _run cp "$INSTALLED_LOGO" "$ICON_DEST"
        _ok "Icon: $ICON_DEST"
    else
        _warn "Logo not found — using fallback icon name."
        ICON_PATH="network-transmit-receive"
    fi
fi

# .desktop
_run mkdir -p "$DESKTOP_DIR"
_run tee "$DESKTOP_FILE" > /dev/null <<DESKTOP_CONTENT
[Desktop Entry]
Version=1.0
Type=Application
Name=HazeDrop
GenericName=Anonymous File Transfer
Comment=Anonymous encrypted file transfer over Tor — Haze Protocol v2
Exec=${LAUNCHER} %u
Icon=${ICON_PATH}
Terminal=false
Categories=Network;Security;FileTransfer;
Keywords=tor;anonymous;secure;encrypt;onion;privacy;
StartupNotify=true
StartupWMClass=hazedrop
DESKTOP_CONTENT
_ok ".desktop: $DESKTOP_FILE"

# Refresh caches
command -v update-desktop-database &>/dev/null && \
    update-desktop-database "$DESKTOP_DIR" 2>/dev/null || true
command -v gtk-update-icon-cache &>/dev/null && [[ -d "$HOME/.local/share/icons" ]] && \
    gtk-update-icon-cache -f "$HOME/.local/share/icons" 2>/dev/null || true
command -v xdg-desktop-menu &>/dev/null && \
    xdg-desktop-menu forceupdate 2>/dev/null || true

# ── [4/4] Summary ──────────────────────────────────────────────────────────
_section "  [4/4] Complete"
echo ""
_ok "HazeDrop $INSTALLED_VER installed successfully!"
echo ""

# PATH warning
if ! echo ":$PATH:" | grep -q ":$BIN_DIR:"; then
    _warn "$BIN_DIR is not in your PATH."
    echo -e "     Add to your ${B}~/.bashrc${N} or ${B}~/.zshrc${N}:"
    echo -e "     ${D}export PATH=\"\$HOME/.local/bin:\$PATH\"${N}"
    echo ""
fi

echo -e "  ${B}hazedrop${N}               Launch GUI"
echo -e "  ${B}hazedrop --cli${N}          Interactive TUI"
echo -e "  ${B}hazedrop send FILE${N}      Send a file"
echo -e "  ${B}hazedrop receive URL${N}    Receive a file"
echo ""
echo -e "  Uninstall:  ${B}bash installer/install.sh --uninstall${N}"
echo ""
