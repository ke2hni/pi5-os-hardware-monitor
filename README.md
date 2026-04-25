# 🚀 Pi 5 OS Hardware Monitor

A native Raspberry Pi OS desktop hardware monitor for **Raspberry Pi 5**.

Built with **Python + GTK 3**. Simple desktop app:
- ❌ No background service
- ❌ No logging/history
- ✅ Lightweight & real-time

---

## 📦 Install

```bash
sudo apt update
sudo apt install -y git
git clone https://github.com/ke2hni/pi5-os-hardware-monitor.git
cd pi5-os-hardware-monitor
sudo ./install.sh
```

Launch from menu or:

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

## 🧠 What it monitors

- 📊 Overview — temps, fan, power, system
- ⚡ Power — voltage, throttling, clocks
- 💾 Storage — SD, USB, NVMe
- 🚀 NVMe — SMART + PCIe
- 🖥️ System — OS, CPU, memory

---

## 🎯 Design Goals

- Pi 5 only
- No daemon
- Active tab refresh only
- Low CPU usage
- Clean UI

---

## 🌡️ Temperature Colors

| Color | Meaning |
|------|--------|
| 🔵 Blue | Cool |
| 🟢 Green | Normal |
| 🟡 Amber | Warm |
| 🔴 Red | Hot |

---

## 🛠️ Customization

```python
TEMP_COLORS = {
    "cool": "#4A90E2",
    "normal": "#4CAF50",
    "warm": "#FFC107",
    "hot": "#F44336",
}
```

---

## ⚠️ Notes

- Works on Pi OS Desktop only
- NVMe tab appears only if detected
