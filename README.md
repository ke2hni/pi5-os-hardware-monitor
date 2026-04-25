# Pi 5 OS Hardware Monitor

A native Raspberry Pi OS desktop hardware monitor for **Raspberry Pi 5**.

Built with **Python + GTK 3**. It is a simple desktop app: no background service, no logging, and no history collector.

## Install

```bash
git clone https://github.com/ke2hni/pi5-os-hardware-monitor.git
cd pi5-os-hardware-monitor
sudo ./install.sh
```

Then launch it from the Raspberry Pi OS menu or run:

```bash
pi5-os-hardware-monitor
```

If NVMe SMART data does not appear immediately after install, log out and back in once so your desktop session picks up the new `pi-hardware-monitor` group membership.

## Upgrade
The reset step makes sure any local installer/runtime files are restored to the official GitHub version before upgrading.

```bash

cd ~/pi5-os-hardware-monitor
git reset --hard
git pull
sudo ./install.sh

```

The installer is safe to re-run. It refreshes package metadata, installs missing dependencies, upgrades required packages when apt has newer compatible versions, refreshes the app file, and revalidates the sudoers rule.

## Uninstall

```bash
cd pi5-os-hardware-monitor
sudo ./uninstall.sh
```

The uninstall script removes the app files, launcher, and sudoers rule. It intentionally leaves the `pi-hardware-monitor` group in place.

## What it monitors

Tabs:

- **Overview** — CPU temperature, I/O temperature, power chip temperature, fan RPM, power state, system summary, and network identity
- **Power** — input voltage, negotiated current limit, USB current mode, voltage rails, clocks, ring oscillator, core rail power, and decoded raw throttle status
- **Storage** — boot device, root device, NVMe presence, fan presence, storage devices, SD card identity, and external USB storage
- **NVMe** — shown only when an NVMe device is detected; includes temperature, manufacturer, model, capacity, health, firmware, life used, power-on hours, unsafe shutdowns, media errors, mountpoint, and PCIe link status
- **System** — OS version, kernel, architecture, hostname, firmware version, uptime, memory, swap, load, and process count

## Design goals

- Raspberry Pi 5 only
- Native Raspberry Pi OS desktop app
- No daemon or background service
- No logging/history storage
- Only the active tab refreshes
- NVMe tab loads lazily and uses a background thread
- Low CPU usage
- Readable two-column layout
- No forced oversized window

## Dependencies installed by `install.sh`

The installer uses apt and installs or upgrades the required runtime packages when needed:

- `python3`
- `python3-gi`
- `gir1.2-gtk-3.0`
- `libraspberrypi-bin`
- `nvme-cli`
- `smartmontools`
- `pciutils`
- `util-linux`
- `coreutils`
- `procps`
- `iproute2`

No Python virtual environment and no pip packages are required.

## Permissions

NVMe controller data can require root access on Raspberry Pi OS. The installer creates a limited sudoers rule at:

```text
/etc/sudoers.d/pi5-os-hardware-monitor
```

It creates/uses this group:

```text
pi-hardware-monitor
```

The sudoers rule allows only the needed hardware-read commands without a password:

```text
%pi-hardware-monitor ALL=(root) NOPASSWD: /usr/sbin/nvme
%pi-hardware-monitor ALL=(root) NOPASSWD: /usr/sbin/smartctl
```

The installer validates the sudoers file with `visudo -cf` before leaving it installed.

## Hardware support

Supported:

- Raspberry Pi 5 Model B
- Raspberry Pi OS desktop
- SD boot, USB storage, and NVMe storage
- Pi 5 fan telemetry when available
- Pi 5 power/throttle information via `vcgencmd`

Not supported:

- Raspberry Pi 4 or earlier
- Non-Raspberry Pi hardware
- Headless-only/non-desktop installs
- Historical graphs or stored samples

## 🌡️ Temperature Color Indicators

The monitor uses dynamic color-coded temperature values to make it easier to quickly identify system conditions at a glance.

Colors automatically adjust based on the sensor type and current temperature.

🎨 Color Meaning
Color	Meaning
🔵 Blue	Cool / Below normal operating range
🟢 Green	Normal operating temperature
🟡 Amber	Warm / Elevated temperature
🔴 Red	Hot / Attention recommended
⚙️ Sensor-Aware Thresholds

Each temperature sensor uses its own threshold ranges (not a fixed global scale):

CPU Temp → tuned for Pi 5 CPU behavior
I/O Temp (rp1_adc) → lower baseline device
Power Chip Temp (PMIC) → similar to CPU thermal profile
NVMe SMART Temp → storage-specific thermal limits

This ensures temperatures are evaluated correctly based on the hardware they represent.

🛠️ Customizing Colors

Color values are defined in:

TEMP_COLORS = {
    "cool": "#4A90E2",
    "normal": "#4CAF50",
    "warm": "#FFC107",
    "hot": "#F44336",
}

You can change these to any valid GTK/Pango color (hex recommended).

🔧 Customizing Temperature Thresholds

Thresholds are defined per sensor:

TEMP_THRESHOLDS = {
    "CPU Temp": {"cool": 45, "warm": 65, "hot": 80},
    "I/O Temp": {"cool": 40, "warm": 60, "hot": 75},
    "Power Chip Temp": {"cool": 45, "warm": 65, "hot": 80},
    "SMART Temp": {"cool": 40, "warm": 55, "hot": 70},
}
How it works:
Below cool → Blue
Between cool and warm → Green
Between warm and hot → Amber
Above hot → Red
💡 Notes
Colors are chosen to work in both light and dark themes
No background services are used — colors update live with the active tab
If a value cannot be parsed (missing or unavailable), no color is applied

## Development

Run directly from the repo:

```bash
python3 app.py
```

Syntax check:

```bash
python3 -m py_compile app.py
```

## Notes

The NVMe tab is hidden when no NVMe device is detected at startup. Reopen the app after adding/removing NVMe hardware.
