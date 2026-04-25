#!/usr/bin/env bash
set -Eeuo pipefail

APP_NAME="Pi 5 OS Hardware Monitor"
APP_ID="pi5-os-hardware-monitor"
INSTALL_DIR="/opt/${APP_ID}"
BIN_PATH="/usr/local/bin/${APP_ID}"
DESKTOP_PATH="/usr/share/applications/${APP_ID}.desktop"
SUDOERS_PATH="/etc/sudoers.d/${APP_ID}"
REQUIRED_GROUP="pi-hardware-monitor"
MIN_PYTHON_MAJOR=3
MIN_PYTHON_MINOR=9

log() { printf '[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*"; }
warn() { printf '[%s] WARNING: %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*" >&2; }
fail() { printf '[%s] ERROR: %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*" >&2; exit 1; }

SUDO_USER_NAME="${SUDO_USER:-}"
if [[ -z "${SUDO_USER_NAME}" || "${SUDO_USER_NAME}" == "root" ]]; then
    SUDO_USER_NAME="$(logname 2>/dev/null || true)"
fi

if [[ "${EUID}" -ne 0 ]]; then
    fail "Run this installer with sudo: sudo ./install.sh"
fi

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_SOURCE="${PROJECT_ROOT}/app.py"
[[ -f "${APP_SOURCE}" ]] || fail "app.py was not found beside install.sh"

is_pi5() {
    local model
    model="$(tr -d '\0' </proc/device-tree/model 2>/dev/null || true)"
    [[ "${model}" == *"Raspberry Pi 5"* ]]
}

if ! is_pi5; then
    fail "This app is for Raspberry Pi 5 hardware only. Detected: $(tr -d '\0' </proc/device-tree/model 2>/dev/null || echo 'Unknown')"
fi

check_python_version() {
    python3 - <<PY
import sys
major, minor = sys.version_info[:2]
raise SystemExit(0 if (major, minor) >= (${MIN_PYTHON_MAJOR}, ${MIN_PYTHON_MINOR}) else 1)
PY
}

ensure_apt_metadata() {
    log "Refreshing APT package metadata"
    apt-get update
}

install_dependencies() {
    local packages=(
        python3
        python3-gi
        gir1.2-gtk-3.0
        libraspberrypi-bin
        nvme-cli
        smartmontools
        pciutils
        util-linux
        coreutils
        procps
        iproute2
    )

    log "Installing/upgrading required packages when needed"
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends "${packages[@]}"

    check_python_version || fail "Python ${MIN_PYTHON_MAJOR}.${MIN_PYTHON_MINOR}+ is required"
}

install_application() {
    log "Installing ${APP_NAME} to ${INSTALL_DIR}"
    install -d -m 0755 "${INSTALL_DIR}"
    install -m 0755 "${APP_SOURCE}" "${INSTALL_DIR}/app.py"

    cat > "${BIN_PATH}" <<WRAPPER
#!/usr/bin/env bash
exec python3 "${INSTALL_DIR}/app.py" "\$@"
WRAPPER
    chmod 0755 "${BIN_PATH}"
}

configure_permissions() {
    log "Configuring limited passwordless hardware commands"

    if ! getent group "${REQUIRED_GROUP}" >/dev/null; then
        groupadd --system "${REQUIRED_GROUP}"
    fi

    if [[ -n "${SUDO_USER_NAME}" ]] && id "${SUDO_USER_NAME}" >/dev/null 2>&1; then
        usermod -aG "${REQUIRED_GROUP}" "${SUDO_USER_NAME}"
    fi

    local nvme_path smartctl_path
    nvme_path="$(command -v nvme || true)"
    smartctl_path="$(command -v smartctl || true)"

    [[ -n "${nvme_path}" ]] || fail "nvme command not found after dependency install"
    [[ -n "${smartctl_path}" ]] || warn "smartctl command not found; NVMe SMART fallback may be limited"

    {
        echo "# ${APP_NAME}: allow only required hardware read commands without a password"
        echo "%${REQUIRED_GROUP} ALL=(root) NOPASSWD: ${nvme_path}"
        if [[ -n "${smartctl_path}" ]]; then
            echo "%${REQUIRED_GROUP} ALL=(root) NOPASSWD: ${smartctl_path}"
        fi
    } > "${SUDOERS_PATH}"

    chmod 0440 "${SUDOERS_PATH}"
    visudo -cf "${SUDOERS_PATH}" >/dev/null || {
        rm -f "${SUDOERS_PATH}"
        fail "sudoers validation failed; removed ${SUDOERS_PATH}"
    }
}

install_desktop_launcher() {
    log "Installing desktop launcher"
    cat > "${DESKTOP_PATH}" <<DESKTOP
[Desktop Entry]
Type=Application
Name=${APP_NAME}
Comment=Raspberry Pi 5 desktop hardware monitor
Exec=${BIN_PATH}
Terminal=false
Categories=System;Monitor;GTK;
StartupNotify=true
DESKTOP
    chmod 0644 "${DESKTOP_PATH}"

    if command -v update-desktop-database >/dev/null 2>&1; then
        update-desktop-database /usr/share/applications >/dev/null 2>&1 || true
    fi
}

validate_install() {
    log "Validating install"
    command -v python3 >/dev/null || fail "python3 missing"
    command -v vcgencmd >/dev/null || fail "vcgencmd missing"
    command -v nvme >/dev/null || fail "nvme-cli missing"
    python3 -m py_compile "${INSTALL_DIR}/app.py"

    if [[ -n "${SUDO_USER_NAME}" ]] && id "${SUDO_USER_NAME}" >/dev/null 2>&1; then
        log "User ${SUDO_USER_NAME} was added to ${REQUIRED_GROUP}. Log out/in if sudo-free NVMe access does not work immediately."
    fi
}

main() {
    ensure_apt_metadata
    install_dependencies
    install_application
    configure_permissions
    install_desktop_launcher
    validate_install
    log "Install complete. Launch from the menu or run: ${BIN_PATH}"
}

main "$@"
