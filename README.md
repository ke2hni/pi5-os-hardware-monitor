# 🚀 Pi 5 OS Hardware Monitor

![Platform](https://img.shields.io/badge/Platform-Raspberry%20Pi%205-blue)
![OS](https://img.shields.io/badge/OS-Raspberry%20Pi%20OS-green)
![Language](https://img.shields.io/badge/Python-3.x-yellow)
![License](https://img.shields.io/badge/License-MIT-lightgrey)

A **native Raspberry Pi OS desktop hardware monitor** built specifically for **Raspberry Pi 5**.

⚡ Fast • 🧼 Clean UI • 🪶 Lightweight • 🔍 Real-time

---

## 📸 Overview

- 📊 Live system stats (no delays)
- 🌡️ Smart temperature color indicators
- ⚡ Power & throttling insights
- 💾 Storage + NVMe monitoring
- 🖥️ Clean GTK desktop interface

---

## 📦 Install (Fresh System Ready)

```bash
sudo apt update
sudo apt install -y git
git clone https://github.com/ke2hni/pi5-os-hardware-monitor.git
cd pi5-os-hardware-monitor
sudo ./install.sh
```

Launch:

```bash
pi5-os-hardware-monitor
```

---

## 🔄 Upgrade

```bash
cd ~/pi5-os-hardware-monitor
git reset --hard
git pull
sudo ./install.sh
```

---

## 🗑️ Uninstall

```bash
cd ~/pi5-os-hardware-monitor
sudo ./uninstall.sh
```

---

## 🧠 Features

### 📊 Overview Tab
- CPU / I/O / Power chip temps
- Fan RPM + power level
- System summary
- Network identity

### ⚡ Power Tab
- Input voltage & limits
- Throttling status
- Clock speeds
- Power diagnostics

### 💾 Storage Tab
- Boot device detection
- SD card info
- USB storage
- NVMe presence

### 🚀 NVMe Tab (Auto)
- SMART data
- Drive health
- PCIe link speed/width
- Firmware + usage stats

### 🖥️ System Tab
- OS / Kernel
- CPU / Memory / Load
- Uptime
- Process count

---

## 🌡️ Temperature Color System

| Color | Meaning |
|------|--------|
| 🔵 Blue | Cool |
| 🟢 Green | Normal |
| 🟡 Amber | Warm |
| 🔴 Red | Hot |

✔ Sensor-specific thresholds  
✔ Works in light & dark themes  
✔ Updates in real time  

---

## 🛠️ Customization

### Colors
```python
TEMP_COLORS = {
    "cool": "#4A90E2",
    "normal": "#4CAF50",
    "warm": "#FFC107",
    "hot": "#F44336",
}
```

### Thresholds
```python
TEMP_THRESHOLDS = {
    "CPU Temp": {"cool": 45, "warm": 65, "hot": 80},
    "I/O Temp": {"cool": 40, "warm": 60, "hot": 75},
    "Power Chip Temp": {"cool": 45, "warm": 65, "hot": 80},
    "SMART Temp": {"cool": 40, "warm": 55, "hot": 70},
}
```

---

## 🔐 Permissions

Installer configures secure hardware access:

- `nvme`
- `smartctl`

Via:
```bash
/etc/sudoers.d/pi5-os-hardware-monitor
```

---

## ⚙️ Dependencies

Installed automatically:
- python3
- GTK3 bindings
- nvme-cli
- smartmontools
- pciutils
- util-linux
- procps

---

## 🧩 Design Philosophy

- ✔ Pi 5 only (no legacy clutter)
- ✔ No background services
- ✔ No telemetry/logging
- ✔ Minimal CPU usage
- ✔ Clean, readable UI

---

## ⚠️ Notes

- NVMe tab appears only when detected
- Designed for Raspberry Pi OS Desktop
- Not compatible with Pi 4 or headless setups

---

## 🧪 Development

Run locally:

```bash
python3 app.py
```

Check syntax:

```bash
python3 -m py_compile app.py
```

---

## 📜 License

MIT License

---

## ⭐ Support

If this project helped you:

⭐ Star the repo  
🐛 Report issues  
💡 Suggest improvements  

<img width="1920" height="1080" alt="Screenshot 2026-04-25 171921" src="https://github.com/user-attachments/assets/0553d9f7-c637-465d-9334-109ad74f432a" />
<img width="1920" height="1080" alt="Screenshot 2026-04-25 171932" src="https://github.com/user-attachments/assets/4f0e9a2f-960d-4d7f-b3f6-971c0694cc90" />
<img width="1920" height="1080" alt="Screenshot 2026-04-25 171938" src="https://github.com/user-attachments/assets/bc5b1105-df19-4e66-a4ba-4e753e1f14b7" />
<img width="1920" height="1080" alt="Screenshot 2026-04-25 171944" src="https://github.com/user-attachments/assets/851ac652-eb7e-4c48-874e-834eb4c38d4b" />
<img width="1920" height="1080" alt="Screenshot 2026-04-25 171950" src="https://github.com/user-attachments/assets/b5bd6cfe-3b2d-462c-ba75-0fb2eae4d9bf" />
