#!/usr/bin/env bash
set -Eeuo pipefail
APP_ID="pi5-os-hardware-monitor"
INSTALL_DIR="/opt/${APP_ID}"
BIN_PATH="/usr/local/bin/${APP_ID}"
DESKTOP_PATH="/usr/share/applications/${APP_ID}.desktop"
SUDOERS_PATH="/etc/sudoers.d/${APP_ID}"

if [[ "${EUID}" -ne 0 ]]; then
    echo "Run with sudo: sudo ./uninstall.sh" >&2
    exit 1
fi

rm -f "${BIN_PATH}" "${DESKTOP_PATH}" "${SUDOERS_PATH}"
rm -rf "${INSTALL_DIR}"
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database /usr/share/applications >/dev/null 2>&1 || true
fi

echo "Pi 5 OS Hardware Monitor removed. The pi-hardware-monitor group is left in place intentionally."
