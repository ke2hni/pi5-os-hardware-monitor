#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Pi 5 OS Hardware Monitor
# Copyright (c) 2026 Jeff Milne - KE2HNI
#
# SPDX-License-Identifier: MIT
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the conditions of the MIT License.
#
# See the LICENSE file for the full license text.

import glob
import os
import re
import subprocess
import threading
import time

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib, Pango


APP_START_TIME = time.monotonic()
NA = "Not Available"

SD_VENDOR_NAMES = {
    "0X000000": "Generic",
    "0X000001": "Panasonic",
    "0X000002": "Kioxia",
    "0X000003": "SanDisk",
    "0X000005": "STMicro",
    "0X000006": "SanDisk",
    "0X000009": "ATP",
    "0X00000B": "Toshiba",
    "0X000012": "Patriot",
    "0X000013": "SanDisk",
    "0X000014": "Samsung",
    "0X00001B": "Kingston",
    "0X00001D": "ADATA",
    "0X000024": "Lexar",
    "0X000027": "Phison",
    "0X000028": "Lexar",
    "0X000031": "SiliconPower",
    "0X000041": "Kingston",
    "0X000045": "TeamGroup",
    "0X000056": "SanDian",
    "0X00005C": "Lexar",
    "0X00006F": "Netac",
    "0X000074": "Transcend",
    "0X000076": "PNY",
    "0X000082": "Sony",
    "0X000089": "Intel",
    "0X000090": "Strontium",
    "0X000092": "Verbatim",
    "0X00009B": "Patriot",
    "0X00009C": "Lexar",
    "0X00009F": "Kingston",
    "0X0000AD": "Longsys",
    "0X0000B6": "Delkin",
    "0X0000C4": "Kootion",
    "0X0000C9": "Kodak",
    "0X0000DF": "Lenovo",
    "0X0000F2": "MK",
    "0X0000FE": "Generic",
    "0X0000FF": "Lenovo",
}

NVME_PCI_VENDOR_NAMES = {
    "025e": "Solidigm",
    "101c": "Western Digital",
    "1042": "Micron",
    "106c": "Hynix Semiconductor",
    "1099": "Samsung",
    "1179": "Toshiba Corporation",
    "11ab": "Marvell",
    "126f": "Silicon Motion, Inc.",
    "144d": "Samsung",
    "1458": "Gigabyte",
    "1462": "MSI",
    "15b7": "Sandisk Corp",
    "17aa": "Lenovo",
    "196e": "PNY",
    "197b": "JMicron",
    "1987": "Phison",
    "1aed": "SanDisk",
    "1b1c": "Corsair",
    "1b96": "Western Digital",
    "1bb1": "Seagate Technology PLC",
    "1bcd": "Apacer Technology",
    "1c5c": "SK hynix",
    "1cc1": "ADATA",
    "1cfa": "Corsair Memory, Inc",
    "1d49": "Lenovo",
    "1d79": "Transcend",
    "1d97": "Longsys",
    "1dbe": "INNOGRIT Corporation",
    "1dee": "Biwin Storage",
    "1e0f": "KIOXIA Corporation",
    "1e4b": "Maxio",
    "1f31": "Nextorage",
    "1f40": "Netac",
    "2646": "Kingston",
    "7377": "Colorful",
    "8086": "Intel Corporation",
    "c0a9": "Micron/Crucial",
}

def format_sd_vendor_id(value):
    if value == NA or not value:
        return NA

    normalized = value.strip().upper()
    if normalized.startswith("0X"):
        hex_digits = normalized[2:]
    else:
        hex_digits = normalized

    try:
        vendor_id = f"0X{int(hex_digits, 16):06X}"
    except Exception:
        return normalized

    return SD_VENDOR_NAMES.get(vendor_id, f"Unknown ({vendor_id})")


def run_command(command, timeout=2):
    try:
        result = subprocess.run(
            command,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=timeout,
            check=False,
        )
        if result.returncode != 0:
            return NA
        output = result.stdout.strip()
        return output if output else NA
    except Exception:
        return NA




def run_command_first(commands, timeout=2):
    for command in commands:
        output = run_command(command, timeout=timeout)
        if output != NA:
            return output
    return NA

def read_file(path):
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as file:
            return file.read().strip()
    except Exception:
        return NA


def read_binary(path):
    try:
        with open(path, "rb") as file:
            return file.read()
    except Exception:
        return None


def read_dt_uint32(path):
    data = read_binary(path)
    if not data:
        return None
    try:
        return int.from_bytes(data[-4:], "big")
    except Exception:
        return None


def read_dt_bool(path):
    data = read_binary(path)
    if data is None:
        return None
    if len(data) == 0:
        return True
    try:
        return int.from_bytes(data[-4:], "big") != 0
    except Exception:
        return None


def yes_no(value):
    return "Yes" if value else "No"


def shorten(value, max_len=44):
    text = str(value)
    if len(text) <= max_len:
        return text
    return text[: max_len - 1] + "…"


def unescape_lsblk_path(value):
    if value in [NA, "Not Mounted"] or not value:
        return value
    return value.replace("\\x20", " ")


def c_to_f(temp_c):
    return temp_c * 9 / 5 + 32


def format_temp(temp_c):
    return f"{temp_c:.1f} °C / {c_to_f(temp_c):.1f} °F"


def parse_first_float(text):
    match = re.search(r"[-+]?\d+(?:\.\d+)?", text)
    if not match:
        return None
    try:
        return float(match.group(0))
    except Exception:
        return None


def parse_vcgencmd_adc_value(line):
    match = re.search(r"=\s*([-+]?\d+(?:\.\d+)?)(?:V|A)?", line)
    if match:
        try:
            return float(match.group(1))
        except Exception:
            return None

    match = re.search(r"volt\(([-+]?\d+(?:\.\d+)?)V\)", line)
    if match:
        try:
            return float(match.group(1))
        except Exception:
            return None

    return None


def get_cpu_temp():
    output = run_command(["vcgencmd", "measure_temp"])
    value = parse_first_float(output)
    if value is None:
        return NA
    return format_temp(value)


def get_clock_hz(name):
    output = run_command(["vcgencmd", "measure_clock", name])
    if output == NA or "=" not in output:
        return None
    try:
        return int(output.split("=", 1)[1])
    except Exception:
        return None


def format_clock(hz):
    if hz is None:
        return NA
    if hz >= 1_000_000_000:
        return f"{hz / 1_000_000_000:.2f} GHz"
    return f"{hz / 1_000_000:.0f} MHz"


def get_clock(name):
    return format_clock(get_clock_hz(name))


def get_voltage(name):
    output = run_command(["vcgencmd", "measure_volts", name])
    if output == NA:
        return output
    return output.replace("volt=", "")


def get_cpu_usage():
    stat1 = read_file("/proc/stat")
    time.sleep(0.2)
    stat2 = read_file("/proc/stat")
    try:
        cpu1 = list(map(int, stat1.splitlines()[0].split()[1:]))
        cpu2 = list(map(int, stat2.splitlines()[0].split()[1:]))
        idle1 = cpu1[3] + cpu1[4]
        idle2 = cpu2[3] + cpu2[4]
        total1 = sum(cpu1)
        total2 = sum(cpu2)
        total_delta = total2 - total1
        idle_delta = idle2 - idle1
        if total_delta == 0:
            return NA
        usage = 100 * (1 - idle_delta / total_delta)
        return f"{usage:.1f}%"
    except Exception:
        return NA


def get_memory_usage():
    meminfo = read_file("/proc/meminfo")
    try:
        values = {}
        for line in meminfo.splitlines():
            key, value = line.split(":", 1)
            values[key] = int(value.strip().split()[0])
        total = values["MemTotal"]
        available = values["MemAvailable"]
        used = total - available
        percent = used / total * 100
        return f"{used / 1024:.0f} MB / {total / 1024:.0f} MB ({percent:.0f}%)"
    except Exception:
        return NA


def get_total_ram():
    meminfo = read_file("/proc/meminfo")
    try:
        for line in meminfo.splitlines():
            if line.startswith("MemTotal:"):
                kb = int(line.split()[1])
                return f"{kb / 1024 / 1024:.1f} GiB"
    except Exception:
        pass
    return NA


def get_swap_usage():
    meminfo = read_file("/proc/meminfo")
    try:
        values = {}
        for line in meminfo.splitlines():
            key, value = line.split(":", 1)
            values[key] = int(value.strip().split()[0])
        total = values.get("SwapTotal", 0)
        free = values.get("SwapFree", 0)
        used = total - free
        if total == 0:
            return "Not configured"
        percent = used / total * 100
        return f"{used / 1024:.0f} MB / {total / 1024:.0f} MB ({percent:.0f}%)"
    except Exception:
        return NA


def get_load_average():
    output = read_file("/proc/loadavg")
    if output == NA:
        return output
    try:
        one, five, fifteen = output.split()[:3]
        return f"{one} / {five} / {fifteen}"
    except Exception:
        return NA


def get_uptime():
    try:
        seconds = int(float(read_file("/proc/uptime").split()[0]))
        days = seconds // 86400
        hours = (seconds % 86400) // 3600
        minutes = (seconds % 3600) // 60
        if days > 0:
            return f"{days}d {hours}h {minutes}m"
        return f"{hours}h {minutes}m"
    except Exception:
        return NA


def get_app_open_time():
    seconds = int(time.monotonic() - APP_START_TIME)
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    return f"{hours}h {minutes}m"


def get_model():
    model = read_file("/proc/device-tree/model")
    if model == NA:
        return model
    return model.replace("\x00", "")


def get_model_display():
    model = get_model()
    if model == NA:
        return model
    if " Model " in model:
        return model.replace(" Model ", "\nModel ", 1)
    return model


def get_os_version():
    os_release = read_file("/etc/os-release")
    try:
        for line in os_release.splitlines():
            if line.startswith("PRETTY_NAME="):
                return line.split("=", 1)[1].strip('"')
    except Exception:
        pass
    return NA


def get_kernel():
    return run_command(["uname", "-r"])


def get_hostname():
    return run_command(["hostname"])


def get_architecture():
    return run_command(["uname", "-m"])


def get_process_count():
    try:
        return str(len([name for name in os.listdir("/proc") if name.isdigit()]))
    except Exception:
        return NA


def get_firmware_version():
    output = run_command(["vcgencmd", "version"])
    if output == NA:
        return output
    lines = output.splitlines()
    return lines[0] if lines else NA


def find_hwmon_temp_by_name(possible_names):
    hwmon_root = "/sys/class/hwmon"
    try:
        for hwmon in sorted(os.listdir(hwmon_root)):
            hwmon_path = os.path.join(hwmon_root, hwmon)
            name = read_file(os.path.join(hwmon_path, "name"))
            if name in possible_names:
                temp_files = sorted(
                    file_name
                    for file_name in os.listdir(hwmon_path)
                    if file_name.startswith("temp") and file_name.endswith("_input")
                )
                for temp_file in temp_files:
                    value = read_file(os.path.join(hwmon_path, temp_file))
                    try:
                        return format_temp(int(value) / 1000)
                    except Exception:
                        continue
    except Exception:
        pass
    return NA


def get_io_temp():
    return find_hwmon_temp_by_name(["rp1_adc"])


def get_power_chip_temp():
    output = run_command(["vcgencmd", "measure_temp", "pmic"], timeout=2)
    value = parse_first_float(output)
    if value is not None:
        return format_temp(value)
    return find_hwmon_temp_by_name(["rpi_volt", "pmic"])


def get_fan_hwmon_path():
    hwmon_root = "/sys/class/hwmon"
    try:
        for hwmon in sorted(os.listdir(hwmon_root)):
            hwmon_path = os.path.join(hwmon_root, hwmon)
            fan_files = sorted(
                file_name
                for file_name in os.listdir(hwmon_path)
                if file_name.startswith("fan") and file_name.endswith("_input")
            )
            if fan_files:
                return hwmon_path, fan_files[0]
    except Exception:
        pass
    return None, None


def get_fan_rpm_value():
    hwmon_path, fan_file = get_fan_hwmon_path()
    if not hwmon_path or not fan_file:
        return None
    value = read_file(os.path.join(hwmon_path, fan_file))
    try:
        return int(value)
    except Exception:
        return None


def get_power_level():
    # Fan power level comes from the fan PWM value, not CPU/core voltage.
    rpm = get_fan_rpm_value()
    if rpm is None:
        return NA
    if rpm == 0:
        return "0% Idle"

    hwmon_path, _fan_file = get_fan_hwmon_path()
    if not hwmon_path:
        return NA

    try:
        pwm_files = sorted(
            file_name
            for file_name in os.listdir(hwmon_path)
            if re.fullmatch(r"pwm\d+", file_name)
        )
        for pwm_file in pwm_files:
            value = read_file(os.path.join(hwmon_path, pwm_file))
            try:
                pwm_value = int(value)
            except Exception:
                continue
            percent = max(0, min(100, round((pwm_value / 255) * 100)))
            return f"{percent}%"
    except Exception:
        pass

    return NA

def get_fan_info():
    rpm = get_fan_rpm_value()
    if rpm is None:
        return NA
    if rpm == 0:
        return "0 RPM Idle"
    return f"{rpm} RPM"


def get_fan_present():
    return "Yes" if get_fan_rpm_value() is not None else "No"

def get_throttled_raw():
    output = run_command(["vcgencmd", "get_throttled"])
    if output == NA:
        return None
    value = output.replace("throttled=", "").strip()
    try:
        return int(value, 16)
    except Exception:
        return None


def get_throttled_raw_text():
    raw = get_throttled_raw()
    return NA if raw is None else f"{raw:#x}"


def bit_status(bit_now, bit_past):
    raw = get_throttled_raw()
    if raw is None:
        return (NA, NA)
    return (yes_no(bool(raw & bit_now)), yes_no(bool(raw & bit_past)))


def get_power_health():
    raw = get_throttled_raw()
    if raw is None:
        return NA
    if raw == 0:
        return "Healthy\nNo power or thermal issues"
    issues = []
    if raw & ((1 << 0) | (1 << 16)):
        issues.append("Undervoltage")
    if raw & ((1 << 1) | (1 << 17)):
        issues.append("Frequency cap")
    if raw & ((1 << 2) | (1 << 18)):
        issues.append("Throttling")
    if raw & ((1 << 3) | (1 << 19)):
        issues.append("Temperature limit")
    return "Needs attention\n" + ", ".join(issues)


def get_throttled_status():
    raw = get_throttled_raw()
    if raw is None:
        return NA
    return "No throttling detected" if raw == 0 else get_power_health()


def get_current_undervoltage():
    return bit_status(1 << 0, 1 << 16)[0]


def get_boot_undervoltage():
    return bit_status(1 << 0, 1 << 16)[1]


def get_current_throttled():
    return bit_status(1 << 2, 1 << 18)[0]


def get_boot_throttled():
    return bit_status(1 << 2, 1 << 18)[1]


def get_current_freq_cap():
    return bit_status(1 << 1, 1 << 17)[0]


def get_boot_freq_cap():
    return bit_status(1 << 1, 1 << 17)[1]


def get_current_soft_temp_limit():
    return bit_status(1 << 3, 1 << 19)[0]


def get_boot_soft_temp_limit():
    return bit_status(1 << 3, 1 << 19)[1]


def get_input_voltage():
    output = run_command(["vcgencmd", "pmic_read_adc"], timeout=3)
    if output == NA:
        return output

    for line in output.splitlines():
        if "EXT5V_V" not in line:
            continue

        value = parse_vcgencmd_adc_value(line)
        if value is not None:
            return f"{value:.4f} V"

    return NA


def get_core_rail_power():
    output = run_command(["vcgencmd", "pmic_read_adc"], timeout=3)
    if output == NA:
        return output

    voltage = None
    current = None

    for line in output.splitlines():
        if "VDD_CORE_V" in line:
            voltage = parse_vcgencmd_adc_value(line)
        elif "VDD_CORE_A" in line:
            current = parse_vcgencmd_adc_value(line)

    if voltage is None or current is None:
        return NA

    return f"{voltage * current:.2f} W"


def get_negotiated_current_limit():
    current = read_dt_uint32("/proc/device-tree/chosen/power/max_current")
    if current is None:
        return NA
    return f"{current} mA"


def get_usb_current_limit_mode():
    high_limit = read_dt_bool("/proc/device-tree/chosen/power/usb_max_current_enable")
    if high_limit is None:
        output = run_command(["vcgencmd", "get_config", "usb_max_current_enable"])
        if output != NA and "=" in output:
            try:
                high_limit = int(output.split("=", 1)[1].strip()) != 0
            except Exception:
                high_limit = None
    if high_limit is None:
        return NA
    return "High" if high_limit else "Low"


def get_usb_over_current_at_boot():
    detected = read_dt_bool("/proc/device-tree/chosen/power/usb_over_current_detected")
    if detected is None:
        return NA
    return yes_no(detected)


def get_storage_summary():
    output = run_command(["lsblk", "-dn", "-o", "NAME,SIZE,TYPE,TRAN"])
    if output == NA:
        return output
    devices = []
    for line in output.splitlines():
        parts = line.split()
        if len(parts) >= 3 and parts[2] == "disk":
            name = parts[0]
            size = parts[1]
            transport = parts[3] if len(parts) >= 4 else "unknown"
            devices.append(f"{name} {size} {transport}")
    return "\n".join(devices) if devices else NA


def get_root_usage():
    output = run_command(["df", "-h", "/"])
    try:
        parts = output.splitlines()[1].split()
        return f"{parts[2]} / {parts[1]} ({parts[4]})"
    except Exception:
        return NA


def get_root_percent():
    output = run_command(["df", "-h", "/"])
    try:
        return output.splitlines()[1].split()[4]
    except Exception:
        return NA


def get_boot_usage():
    for path in ["/boot/firmware", "/boot"]:
        if os.path.ismount(path):
            output = run_command(["df", "-h", path])
            try:
                parts = output.splitlines()[1].split()
                return f"{parts[2]} / {parts[1]} ({parts[4]})"
            except Exception:
                continue
    return NA


def get_root_device():
    output = run_command(["findmnt", "-n", "-o", "SOURCE", "/"])
    return output if output else NA


def get_boot_device():
    root = get_root_device()
    if "nvme" in root:
        return "NVMe"
    if "mmcblk" in root:
        return "SD Card"
    if "sd" in root:
        return "USB / SATA"
    return "Other / Unknown" if root != NA else NA


def lsblk_value(device, column):
    output = run_command(["lsblk", "-dn", "-o", column, device])
    return output if output else NA


def nvme_sysfs_value(names):
    device = nvme_device()
    if not device:
        return NA

    block_name = os.path.basename(device)
    candidate_roots = [
        f"/sys/block/{block_name}/device",
        f"/sys/class/block/{block_name}/device",
    ]
    candidate_roots.extend(sorted(glob.glob("/sys/class/nvme/nvme*")))

    for root in candidate_roots:
        for name in names:
            value = read_file(os.path.join(root, name))
            if value != NA and value:
                return value

    return NA


def nvme_device():
    devices = sorted(glob.glob("/dev/nvme*n1"))
    return devices[0] if devices else None


def nvme_present():
    return nvme_device() is not None


def normalize_field_name(value):
    return re.sub(r"[^a-z0-9]+", "_", value.strip().lower()).strip("_")


def nvme_cli_line_value(output, keys):
    if output == NA:
        return NA

    normalized_keys = [normalize_field_name(key) for key in keys]

    for line in output.splitlines():
        if ":" not in line:
            continue

        key, value = line.split(":", 1)
        normalized_key = normalize_field_name(key)

        if normalized_key in normalized_keys:
            return value.strip()

    return NA


def clean_nvme_integer(value):
    if value == NA:
        return NA

    number = re.sub(r"[^0-9]", "", value.split("[")[0])
    return number if number else value


def format_bytes_decimal(value):
    if value == NA:
        return NA

    number = re.sub(r"[^0-9]", "", value)
    if not number:
        return NA

    try:
        size = int(number)
    except Exception:
        return NA

    if size <= 0:
        return NA

    units = ["B", "KB", "MB", "GB", "TB"]
    size_float = float(size)
    unit_index = 0

    while size_float >= 1000 and unit_index < len(units) - 1:
        size_float /= 1000
        unit_index += 1

    if unit_index == 0:
        return f"{int(size_float)} {units[unit_index]}"

    return f"{size_float:.1f} {units[unit_index]}"


def get_nvme_smart_log_full():
    device = nvme_device()
    if not device:
        return NA
    return run_command_first([
        ["nvme", "smart-log", device],
        ["sudo", "-n", "nvme", "smart-log", device],
    ], timeout=5)


def get_nvme_id_ctrl_full():
    device = nvme_device()
    if not device:
        return NA
    return run_command_first([
        ["nvme", "id-ctrl", device],
        ["sudo", "-n", "nvme", "id-ctrl", device],
    ], timeout=5)


def get_nvme_smart_full():
    device = nvme_device()
    if not device:
        return NA
    return run_command_first([
        ["smartctl", "-a", device],
        ["sudo", "-n", "smartctl", "-a", device],
    ], timeout=5)


def smart_line_value(smart, prefixes):
    if smart == NA:
        return NA
    for line in smart.splitlines():
        stripped = line.strip()
        lower = stripped.lower()
        for prefix in prefixes:
            if lower.startswith(prefix.lower()):
                return stripped.split(":", 1)[1].strip() if ":" in stripped else stripped
    return NA


def get_nvme_vendor_id_from_id_ctrl(field_name):
    id_ctrl = get_nvme_id_ctrl_full()
    value = nvme_cli_line_value(id_ctrl, [field_name])
    if value == NA:
        return NA

    match = re.search(r"(?:0x)?([0-9a-fA-F]{4})", value)
    if not match:
        return NA

    return match.group(1).lower()


def get_nvme_vendor_name_from_id_ctrl():
    for field_name in ["vid", "ssvid"]:
        vendor_id = get_nvme_vendor_id_from_id_ctrl(field_name)
        if vendor_id == NA:
            continue

        vendor_name = NVME_PCI_VENDOR_NAMES.get(vendor_id)
        if vendor_name:
            return vendor_name

    return NA


def get_nvme_drive_present():
    return yes_no(nvme_present())


def get_nvme_temp():
    device = nvme_device()
    if not device:
        return NA

    smart_log = get_nvme_smart_log_full()
    temperature = nvme_cli_line_value(smart_log, ["temperature"])

    if temperature != NA:
        kelvin_match = re.search(r"\(([-+]?\d+(?:\.\d+)?)\s*K\)", temperature)
        if kelvin_match:
            try:
                return format_temp(float(kelvin_match.group(1)) - 273.15)
            except Exception:
                pass

        celsius_match = re.search(r"\(([-+]?\d+(?:\.\d+)?)\s*C\)", temperature)
        if not celsius_match:
            celsius_match = re.search(r"([-+]?\d+(?:\.\d+)?)\s*C", temperature)

        if celsius_match:
            try:
                return format_temp(float(celsius_match.group(1)))
            except Exception:
                pass

        first_value = parse_first_float(temperature)
        if first_value is not None:
            if first_value > 200:
                return format_temp(first_value - 273.15)
            return format_temp(first_value)

    smart_output = get_nvme_smart_full()
    if smart_output != NA:
        for line in smart_output.splitlines():
            lower = line.lower().strip()
            if lower.startswith("temperature:") or lower.startswith("temperature "):
                value = parse_first_float(line)
                if value is not None:
                    return format_temp(value)

    return find_hwmon_temp_by_name(["nvme"])


def get_nvme_manufacturer():
    vendor_name = get_nvme_vendor_name_from_id_ctrl()
    if vendor_name != NA:
        return vendor_name

    model = get_nvme_model()
    if model == NA:
        return NA

    first = model.split()[0]
    known = {
        "TS": "Transcend",
        "SAMSUNG": "Samsung",
        "WD": "Western Digital",
        "WDC": "Western Digital",
        "KINGSTON": "Kingston",
        "CRUCIAL": "Crucial",
        "CT": "Crucial",
        "SK": "SK hynix",
        "INTEL": "Intel",
        "SOLIDIGM": "Solidigm",
    }

    upper = first.upper()
    for key, name in known.items():
        if upper.startswith(key):
            return name

    return first


def get_nvme_model():
    value = nvme_sysfs_value(["model", "model_number"])
    if value != NA:
        return shorten(value, 34)

    value = lsblk_value(nvme_device() or "", "MODEL")
    if value != NA:
        return shorten(value, 34)

    id_ctrl = get_nvme_id_ctrl_full()
    value = nvme_cli_line_value(id_ctrl, ["mn", "model_number", "model"])
    if value != NA:
        return shorten(value, 34)

    return shorten(smart_line_value(get_nvme_smart_full(), ["Model Number", "Device Model"]), 34)


def get_nvme_capacity():
    id_ctrl = get_nvme_id_ctrl_full()
    value = nvme_cli_line_value(id_ctrl, ["tnvmcap", "unvmcap"])
    formatted = format_bytes_decimal(value)
    if formatted != NA:
        return formatted

    size = lsblk_value(nvme_device() or "", "SIZE")
    if size != NA:
        return size

    value = smart_line_value(get_nvme_smart_full(), ["Namespace 1 Size/Capacity", "Total NVM Capacity"])
    return shorten(value, 34)


def get_nvme_health():
    smart_log = get_nvme_smart_log_full()
    critical = nvme_cli_line_value(smart_log, ["critical_warning", "critical warning"])

    if critical != NA:
        normalized = critical.strip().lower()
        if normalized in ["0", "0x0", "0x00", "0x00000000"]:
            return "Healthy"
        return f"Warning ({critical})"

    smart = get_nvme_smart_full()
    status = smart_line_value(smart, ["SMART overall-health self-assessment test result", "SMART Health Status"])
    critical = smart_line_value(smart, ["Critical Warning"])

    if status != NA:
        return status
    if critical != NA and critical.strip().lower().startswith("0x00"):
        return "Healthy"

    return NA


def get_nvme_firmware():
    value = nvme_sysfs_value(["firmware_rev", "firmware_revision"])
    if value != NA:
        return value

    id_ctrl = get_nvme_id_ctrl_full()
    value = nvme_cli_line_value(id_ctrl, ["fr", "firmware", "firmware_rev", "firmware_revision"])
    if value != NA:
        return value

    return smart_line_value(get_nvme_smart_full(), ["Firmware Version"])


def get_nvme_life_used():
    smart_log = get_nvme_smart_log_full()
    value = nvme_cli_line_value(smart_log, ["percentage_used", "percentage used"])
    if value != NA:
        return value

    return smart_line_value(get_nvme_smart_full(), ["Percentage Used"])


def get_nvme_power_on_hours():
    smart_log = get_nvme_smart_log_full()
    value = nvme_cli_line_value(smart_log, ["power_on_hours", "power on hours"])
    if value != NA:
        number = clean_nvme_integer(value)
        return f"{number} h" if number != NA else NA

    value = smart_line_value(get_nvme_smart_full(), ["Power On Hours"])
    if value == NA:
        return NA

    number = clean_nvme_integer(value)
    return f"{number} h" if number else value


def get_nvme_unsafe_shutdowns():
    smart_log = get_nvme_smart_log_full()
    value = nvme_cli_line_value(smart_log, ["unsafe_shutdowns", "unsafe shutdowns"])
    if value != NA:
        return clean_nvme_integer(value)

    value = smart_line_value(get_nvme_smart_full(), ["Unsafe Shutdowns"])
    return clean_nvme_integer(value) if value != NA else NA


def get_nvme_media_errors():
    smart_log = get_nvme_smart_log_full()
    value = nvme_cli_line_value(smart_log, [
        "media_errors", "media errors",
        "media_and_data_integrity_errors", "media and data integrity errors",
    ])
    if value != NA:
        return clean_nvme_integer(value)

    value = smart_line_value(get_nvme_smart_full(), ["Media and Data Integrity Errors", "Media Errors"])
    return clean_nvme_integer(value) if value != NA else NA


def get_nvme_mountpoint():
    device = nvme_device()
    if not device:
        return NA
    output = run_command(["lsblk", "-nr", "-o", "NAME,MOUNTPOINT", device])
    for line in output.splitlines():
        if "/" in line:
            parts = line.split(None, 1)
            if len(parts) == 2:
                return unescape_lsblk_path(parts[1])
    return "Not Mounted"


def get_nvme_pci_path():
    device = nvme_device()
    if not device:
        return None

    block_name = os.path.basename(device)
    path = os.path.realpath(f"/sys/block/{block_name}/device")

    while path and path != "/":
        if os.path.exists(os.path.join(path, "current_link_speed")):
            return path
        path = os.path.dirname(path)

    return None


def get_pcie_sysfs_value(name):
    pci_path = get_nvme_pci_path()
    if not pci_path:
        return NA

    value = read_file(os.path.join(pci_path, name))
    if value == NA or not value:
        return NA

    if name.endswith("_link_width") and not str(value).startswith("x"):
        return f"x{value}"

    return value


def get_pcie_link_value(pattern):
    device = nvme_device()
    if not device:
        return NA

    block_name = os.path.basename(device)
    pci_path = get_nvme_pci_path()
    pci_id = os.path.basename(pci_path) if pci_path else ""

    commands = [
        ["lspci", "-s", pci_id, "-vv"],
        ["sudo", "-n", "lspci", "-s", pci_id, "-vv"],
    ] if pci_id else [
        ["lspci", "-vv"],
        ["sudo", "-n", "lspci", "-vv"],
    ]

    output = run_command_first(commands, timeout=3)
    if output == NA:
        return NA

    for line in output.splitlines():
        if pattern in line:
            return line.strip()

    return NA


def extract_lnksta_speed():
    speed = get_pcie_sysfs_value("current_link_speed")
    width = get_pcie_sysfs_value("current_link_width")
    if speed != NA or width != NA:
        return (speed, width)

    line = get_pcie_link_value("LnkSta:")
    match = re.search(r"Speed\s+([^,]+),\s+Width\s+([^,\s]+)", line)
    return match.groups() if match else (NA, NA)


def extract_lnkcap_speed():
    speed = get_pcie_sysfs_value("max_link_speed")
    width = get_pcie_sysfs_value("max_link_width")
    if speed != NA or width != NA:
        return (speed, width)

    line = get_pcie_link_value("LnkCap:")
    match = re.search(r"Speed\s+([^,]+),\s+Width\s+([^,\s]+)", line)
    return match.groups() if match else (NA, NA)


def get_current_link_speed():
    return extract_lnksta_speed()[0]


def get_current_link_width():
    return extract_lnksta_speed()[1]


def get_max_link_speed():
    return extract_lnkcap_speed()[0]


def get_max_link_width():
    return extract_lnkcap_speed()[1]


def collect_nvme_data():
    if not nvme_present():
        return {
            "Present": "No",
            "SMART Temp": NA,
            "Manufacturer": NA,
            "Model": NA,
            "Capacity": NA,
            "Drive Health": NA,
            "Firmware": NA,
            "Life Used": NA,
            "Power-on Hours": NA,
            "Unsafe Shutdowns": NA,
            "Media Errors": NA,
            "Mounted At": NA,
            "Current Speed": NA,
            "Current Width": NA,
            "Max Speed": NA,
            "Max Width": NA,
        }

    return {
        "Present": "Yes",
        "SMART Temp": get_nvme_temp(),
        "Manufacturer": get_nvme_manufacturer(),
        "Model": get_nvme_model(),
        "Capacity": get_nvme_capacity(),
        "Drive Health": get_nvme_health(),
        "Firmware": get_nvme_firmware(),
        "Life Used": get_nvme_life_used(),
        "Power-on Hours": get_nvme_power_on_hours(),
        "Unsafe Shutdowns": get_nvme_unsafe_shutdowns(),
        "Media Errors": get_nvme_media_errors(),
        "Mounted At": get_nvme_mountpoint(),
        "Current Speed": get_current_link_speed(),
        "Current Width": get_current_link_width(),
        "Max Speed": get_max_link_speed(),
        "Max Width": get_max_link_width(),
    }


def get_sd_device():
    devices = sorted(glob.glob("/dev/mmcblk*"))
    disks = [d for d in devices if re.match(r"/dev/mmcblk\d+$", d)]
    return disks[0] if disks else None


def get_sd_present():
    return yes_no(get_sd_device() is not None)


def get_sd_capacity():
    device = get_sd_device()
    return lsblk_value(device, "SIZE") if device else NA


def get_sd_used():
    device = get_sd_device()
    if not device:
        return NA
    output = run_command(["lsblk", "-nr", "-o", "NAME,MOUNTPOINT", device])
    for line in output.splitlines():
        if "/" in line:
            mount = unescape_lsblk_path(line.split(None, 1)[1])
            df = run_command(["df", "-h", mount])
            try:
                return df.splitlines()[1].split()[4]
            except Exception:
                pass
    return "Not Mounted"


def get_sd_vendor():
    device = get_sd_device()
    if not device:
        return NA

    base = os.path.basename(device)
    value = read_file(f"/sys/block/{base}/device/manfid")

    if value == NA:
        value = read_file(f"/sys/block/{base}/device/oemid")

    return format_sd_vendor_id(value)


def get_sd_model():
    device = get_sd_device()
    if not device:
        return NA
    base = os.path.basename(device)
    value = read_file(f"/sys/block/{base}/device/name")
    return value if value != NA else NA


def get_sd_serial():
    device = get_sd_device()
    if not device:
        return NA
    base = os.path.basename(device)
    value = read_file(f"/sys/block/{base}/device/serial")
    return value if value != NA else NA


def get_sd_mountpoint():
    device = get_sd_device()
    if not device:
        return NA
    output = run_command(["lsblk", "-nr", "-o", "NAME,MOUNTPOINT", device])
    mounts = []
    for line in output.splitlines():
        parts = line.split(None, 1)
        if len(parts) == 2 and parts[1].startswith("/"):
            mounts.append(unescape_lsblk_path(parts[1]))
    return ", ".join(mounts) if mounts else "Not Mounted"


def get_usb_disk_lines():
    output = run_command(["lsblk", "-dn", "-o", "NAME,SIZE,TRAN,MODEL"])
    if output == NA:
        return []
    return [line for line in output.splitlines() if "usb" in line.lower()]


def get_usb_model():
    lines = get_usb_disk_lines()
    if not lines:
        return NA
    parts = lines[0].split(None, 3)
    return shorten(parts[3], 34) if len(parts) >= 4 else NA


def get_usb_capacity():
    lines = get_usb_disk_lines()
    if not lines:
        return NA
    parts = lines[0].split()
    return parts[1] if len(parts) >= 2 else NA


def get_usb_device_path():
    lines = get_usb_disk_lines()
    if not lines:
        return NA
    return "/dev/" + lines[0].split()[0]


def get_usb_mountpoint():
    device = get_usb_device_path()
    if device == NA:
        return NA
    output = run_command(["lsblk", "-nr", "-o", "NAME,MOUNTPOINT", device])
    for line in output.splitlines():
        parts = line.split(None, 1)
        if len(parts) == 2 and parts[1].startswith("/"):
            return unescape_lsblk_path(parts[1])
    return "Not Mounted"


def get_usb_free_space():
    mount = get_usb_mountpoint()
    if mount in [NA, "Not Mounted"]:
        return mount

    output = run_command(["df", "-h", mount])
    if output == NA:
        return NA

    try:
        lines = output.splitlines()
        if len(lines) < 2:
            return NA
        parts = lines[1].split()
        if len(parts) >= 4:
            return parts[3]
    except Exception:
        pass

    return NA


def get_network_ip():
    output = run_command(["hostname", "-I"])
    if output == NA or not output:
        return NA
    return output.split()[0]


def get_default_route():
    output = run_command(["ip", "route", "show", "default"])
    try:
        if not output or output == NA:
            return NA
        parts = output.split()
        gateway = parts[parts.index("via") + 1] if "via" in parts else "No gateway"
        interface = parts[parts.index("dev") + 1] if "dev" in parts else "unknown"
        return f"{interface} via {gateway}"
    except Exception:
        return NA


def get_primary_mac():
    output = run_command(["ip", "-o", "link", "show"])
    try:
        for line in output.splitlines():
            if "link/ether" in line and " lo: " not in line:
                parts = line.split()
                interface = parts[1].rstrip(":")
                mac = parts[parts.index("link/ether") + 1]
                return f"{interface}: {mac}"
    except Exception:
        pass
    return NA

def get_ring_oscillator():
    output = run_command(["vcgencmd", "read_ring_osc"], timeout=2)
    return output if output else NA

def apply_label_style(label, scale=1.0, bold=False):
    attributes = Pango.AttrList()
    if scale != 1.0:
        attributes.insert(Pango.attr_scale_new(scale))
    if bold:
        attributes.insert(Pango.attr_weight_new(Pango.Weight.BOLD))
    label.set_attributes(attributes)


TEMP_ROWS = {"CPU Temp", "I/O Temp", "Power Chip Temp", "SMART Temp"}


def temperature_color(value):
    match = re.search(r"([-+]?\d+(?:\.\d+)?)\s*°C", str(value))
    if not match:
        return None

    try:
        temp_c = float(match.group(1))
    except Exception:
        return None

    if temp_c >= 80:
        return "red"
    if temp_c >= 65:
        return "orange"
    if temp_c >= 55:
        return "goldenrod"
    return "green"



class ValueRow(Gtk.Box):
    def __init__(self, label):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        self.row_name = label
        self.set_margin_top(1)
        self.set_margin_bottom(1)

        self.label = Gtk.Label()
        self.label.set_halign(Gtk.Align.START)
        self.label.set_valign(Gtk.Align.START)
        self.label.set_width_chars(24)
        self.label.set_line_wrap(True)
        self.label.set_line_wrap_mode(Pango.WrapMode.WORD_CHAR)
        self.label.set_xalign(0.0)
        self.label.set_text(label)
        apply_label_style(self.label, scale=1.05, bold=True)

        self.value = Gtk.Label()
        self.value.set_halign(Gtk.Align.FILL)
        self.value.set_valign(Gtk.Align.START)
        self.value.set_hexpand(True)
        self.value.set_selectable(True)
        self.value.set_line_wrap(True)
        self.value.set_line_wrap_mode(Pango.WrapMode.WORD_CHAR)
        self.value.set_xalign(0.0)
        self.value.set_yalign(0.0)
        self.value.set_justify(Gtk.Justification.LEFT)
        self.value.set_max_width_chars(46)
        self.value.set_text("Loading...")
        apply_label_style(self.value, scale=1.05, bold=True)

        self.pack_start(self.label, False, False, 0)
        self.pack_start(self.value, True, True, 0)

    def set_value(self, value):
        text = str(value)
        color = temperature_color(text) if self.row_name in TEMP_ROWS else None

        if color:
            escaped_text = GLib.markup_escape_text(text)
            self.value.set_markup(f'<span foreground="{color}"><b>{escaped_text}</b></span>')
        else:
            self.value.set_text(text)
            apply_label_style(self.value, scale=1.05, bold=True)


class Section(Gtk.Frame):
    def __init__(self, title, description, rows):
        super().__init__()
        self.set_shadow_type(Gtk.ShadowType.ETCHED_IN)
        self.set_margin_bottom(5)

        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
        outer.set_border_width(6)

        title_label = Gtk.Label()
        title_label.set_text(title)
        apply_label_style(title_label, scale=1.15, bold=True)
        title_label.set_halign(Gtk.Align.START)
        outer.pack_start(title_label, False, False, 0)

        if description:
            desc = Gtk.Label(label=description)
            desc.set_halign(Gtk.Align.START)
            desc.set_line_wrap(True)
            desc.set_line_wrap_mode(Pango.WrapMode.WORD_CHAR)
            desc.set_xalign(0.0)
            outer.pack_start(desc, False, False, 0)

        self.rows = {}
        for row_name in rows:
            row = ValueRow(row_name)
            self.rows[row_name] = row
            outer.pack_start(row, False, False, 0)

        self.add(outer)

    def set_value(self, row_name, value):
        if row_name in self.rows:
            self.rows[row_name].set_value(value)


class PiHardwareMonitor(Gtk.Window):
    def __init__(self):
        super().__init__(title="Pi 5 OS Hardware Monitor v1.0")
        self.set_default_size(1240, 699)
        self.set_resizable(True)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.set_border_width(2)
        self.sections = {}
        self.page_ids = []
        self.active_page = "overview"
        self.nvme_scan_running = False
        self.nvme_scan_loaded = False

        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        title_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)

        header = Gtk.Label()
        header.set_text("Pi 5 OS Hardware Monitor v1.0 4/25/2026")
        apply_label_style(header, scale=1.35, bold=True)
        header.set_halign(Gtk.Align.START)
        subtitle = Gtk.Label(label="Raspberry Pi 5 desktop hardware monitor. No background service. Only the active tab refreshes.")
        subtitle.set_halign(Gtk.Align.START)
        title_box.pack_start(header, False, False, 0)
        title_box.pack_start(subtitle, False, False, 0)

        quit_button = Gtk.Button(label="Quit")
        quit_button.connect("clicked", self.on_quit_clicked)
        header_box.pack_start(title_box, True, True, 0)
        header_box.pack_start(quit_button, False, False, 0)

        self.notebook = Gtk.Notebook()
        self.notebook.set_tab_pos(Gtk.PositionType.TOP)
        self.notebook.set_scrollable(True)
        self.notebook.connect("switch-page", self.on_tab_switched)

        self.add_page("overview", "Overview", [[
            ("Thermal / Cooling", "Core temperature and fan telemetry", self.get_thermal_rows()),
            ("Power / Throttling", "Power, throttling, frequency cap, and temperature-limit status", [
                "Power Health", "Current Undervoltage", "Undervoltage Since Boot",
                "Current Throttled", "Throttled Since Boot", "Current Freq Cap",
                "Freq Cap Since Boot", "Current Soft Temp Limit", "Soft Temp Since Boot",
            ]),
        ], [
            ("System Summary", "Model, uptime, load, and memory", [
                "Pi Model", "CPU Frequency", "Total RAM", "Memory Usage", "Swap",
                "Uptime", "Load Average (1m/5m/15m)", "Root Filesystem Used", "Processes",
            ]),
            ("Network", "Current network identity", [
                "IP Address", "Default Route", "MAC Address", "Hostname",
            ]),
        ]])

        self.add_page("power", "Power", [[
            ("Power Supply", "Input voltage and negotiated power-supply status", [
                "Input Voltage", "Negotiated Current Limit", "USB Current Limit Mode", "USB Over-current at Boot",
            ]),
            ("Voltages", "Pi firmware voltage readings", [
                "Core Voltage", "SDRAM C", "SDRAM I", "SDRAM P",
            ]),
        ], [
            ("Clocks", "Current firmware-reported clock speeds", [
                "ARM Clock", "Core Clock", "eMMC Clock",
            ]),
            ("Advanced Power", "Extra Pi-specific power diagnostics", [
                "Power Chip Temp", "Power Level", "Core Rail Power", "Ring Oscillator", "Raw Status",
            ]),
        ]])

        self.add_page("storage", "Storage", [[
            ("Boot / Device Info", "Root device, storage type, and hardware presence", [
                "Boot Device", "Root Device", "NVMe Present", "Fan Present", "Storage Devices",
            ]),
            ("SD Card", "SD card presence and basic identity", [
                "Present", "Device", "Capacity", "Card Used", "Vendor", "Model", "Serial", "Mounted At",
            ]),
        ], [
            ("External USB Storage", "External USB storage when detected", [
                "Model", "Capacity", "Free Space", "Device Path", "Mounted At",
            ]),
        ]])

        if nvme_present():
            self.add_page("nvme", "NVMe", [[
                ("NVMe Drive", "Loads only after this tab is opened", [
                    "SMART Temp", "Manufacturer", "Model", "Capacity", "Drive Health",
                ]),
                ("PCIe / NVMe Link", "Current negotiated PCIe link status", [
                    "Current Speed", "Current Width", "Max Speed", "Max Width",
                ]),
            ], [
                ("NVMe Details", "SMART and firmware details", [
                    "Firmware", "Life Used", "Power-on Hours", "Unsafe Shutdowns", "Media Errors", "Mounted At",
                ]),
            ]])

        self.add_page("system", "System", [[
            ("System Details", "Model, OS, kernel, and runtime details", [
                "Pi Model", "OS Version", "Kernel", "Architecture", "Hostname",
                "Firmware Version", "System Uptime", "App Open Time",
            ]),
        ], [
            ("Performance", "CPU, memory, load, and process count", [
                "CPU Usage", "CPU Clock", "Core Clock", "Core Voltage",
                "Memory", "Swap", "Load Avg (1m/5m/15m)", "Processes",
            ]),
            ("Network", "Current network identity", [
                "IP Address", "Default Route", "MAC Address", "Hostname",
            ]),
        ]])

        main_box.pack_start(header_box, False, False, 0)
        main_box.pack_start(self.notebook, True, True, 0)
        self.add(main_box)

        GLib.idle_add(self.refresh_active_page_once)
        self.timeout_id = GLib.timeout_add_seconds(3, self.refresh_active_page)

    def add_page(self, page_id, tab_title, columns):
        grid = Gtk.Grid()
        grid.set_column_spacing(8)
        grid.set_row_spacing(4)
        grid.set_column_homogeneous(True)
        grid.set_margin_top(2)
        grid.set_margin_bottom(2)
        grid.set_margin_start(2)
        grid.set_margin_end(2)

        for col_index, sections in enumerate(columns):
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
            for title, desc, rows in sections:
                section = Section(title, desc, rows)
                self.sections[(page_id, title)] = section
                box.pack_start(section, False, False, 0)
            grid.attach(box, col_index, 0, 1, 1)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_min_content_height(1)
        scrolled.set_min_content_width(1)
        scrolled.set_overlay_scrolling(True)
        scrolled.add(grid)

        tab_label = Gtk.Label()
        tab_label.set_text(tab_title)
        apply_label_style(tab_label, scale=1.05, bold=True)
        self.page_ids.append(page_id)
        self.notebook.append_page(scrolled, tab_label)

    def stop_timers(self):
        timeout_id = getattr(self, "timeout_id", None)
        if timeout_id:
            try:
                GLib.source_remove(timeout_id)
            except Exception:
                pass
        self.timeout_id = None

    def on_quit_clicked(self, *args):
        self.destroy()

    def on_destroy(self, *args):
        self.stop_timers()
        Gtk.main_quit()

    def on_tab_switched(self, notebook, page, page_num):
        if page_num < 0 or page_num >= len(self.page_ids):
            return
        self.active_page = self.page_ids[page_num]
        GLib.idle_add(self.refresh_active_page_once)

    def refresh_active_page_once(self):
        self.refresh_active_page()
        return False

    def get_thermal_rows(self):
        return ["CPU Temp", "I/O Temp", "Power Chip Temp", "SMART Temp", "Fan RPM", "Power Level"]


    def set_row(self, page_id, section, row, value):
        key = (page_id, section)
        if key in self.sections:
            self.sections[key].set_value(row, value)

    def refresh_active_page(self):
        if self.active_page == "overview":
            self.update_overview_page()
        elif self.active_page == "power":
            self.update_power_page()
        elif self.active_page == "storage":
            self.update_storage_page()
        elif self.active_page == "nvme":
            self.start_nvme_scan_once()
        elif self.active_page == "system":
            self.update_system_page()
        return True

    def update_overview_page(self):
        page = "overview"
        self.set_row(page, "Thermal / Cooling", "CPU Temp", get_cpu_temp())
        self.set_row(page, "Thermal / Cooling", "I/O Temp", get_io_temp())
        self.set_row(page, "Thermal / Cooling", "Power Chip Temp", get_power_chip_temp())
        self.set_row(page, "Thermal / Cooling", "SMART Temp", get_nvme_temp())
        self.set_row(page, "Thermal / Cooling", "Fan RPM", get_fan_info())
        self.set_row(page, "Thermal / Cooling", "Power Level", get_power_level())
        self.set_row(page, "Power / Throttling", "Power Health", get_power_health())
        self.set_row(page, "Power / Throttling", "Current Undervoltage", get_current_undervoltage())
        self.set_row(page, "Power / Throttling", "Undervoltage Since Boot", get_boot_undervoltage())
        self.set_row(page, "Power / Throttling", "Current Throttled", get_current_throttled())
        self.set_row(page, "Power / Throttling", "Throttled Since Boot", get_boot_throttled())
        self.set_row(page, "Power / Throttling", "Current Freq Cap", get_current_freq_cap())
        self.set_row(page, "Power / Throttling", "Freq Cap Since Boot", get_boot_freq_cap())
        self.set_row(page, "Power / Throttling", "Current Soft Temp Limit", get_current_soft_temp_limit())
        self.set_row(page, "Power / Throttling", "Soft Temp Since Boot", get_boot_soft_temp_limit())

        self.set_row(page, "System Summary", "Pi Model", get_model_display())
        self.set_row(page, "System Summary", "CPU Frequency", get_clock("arm"))
        self.set_row(page, "System Summary", "Total RAM", get_total_ram())
        self.set_row(page, "System Summary", "Memory Usage", get_memory_usage())
        self.set_row(page, "System Summary", "Swap", get_swap_usage())
        self.set_row(page, "System Summary", "Uptime", get_uptime())
        self.set_row(page, "System Summary", "Load Average (1m/5m/15m)", get_load_average())
        self.set_row(page, "System Summary", "Root Filesystem Used", get_root_percent())
        self.set_row(page, "System Summary", "Processes", get_process_count())

        self.set_row(page, "Network", "IP Address", get_network_ip())
        self.set_row(page, "Network", "Default Route", get_default_route())
        self.set_row(page, "Network", "MAC Address", get_primary_mac())
        self.set_row(page, "Network", "Hostname", get_hostname())

    def get_throttled_raw_description(self):
        raw = get_throttled_raw()
        if raw is None:
            return NA

        if raw == 0:
            return "0x0 — Healthy System"

        issues = []

        if raw & (1 << 0):
            issues.append("Undervoltage NOW")
        if raw & (1 << 1):
            issues.append("Frequency cap NOW")
        if raw & (1 << 2):
            issues.append("Throttled NOW")
        if raw & (1 << 3):
            issues.append("Soft temp limit NOW")

        if raw & (1 << 16):
            issues.append("Undervoltage since boot")
        if raw & (1 << 17):
            issues.append("Frequency cap since boot")
        if raw & (1 << 18):
            issues.append("Throttled since boot")
        if raw & (1 << 19):
            issues.append("Soft temp limit since boot")

        if not issues:
            return f"{raw:#x} — Unknown status"

        return f"{raw:#x} — " + ", ".join(issues)

    def update_power_page(self):
        page = "power"
        self.set_row(page, "Power Supply", "Input Voltage", get_input_voltage())
        self.set_row(page, "Power Supply", "Negotiated Current Limit", get_negotiated_current_limit())
        self.set_row(page, "Power Supply", "USB Current Limit Mode", get_usb_current_limit_mode())
        self.set_row(page, "Power Supply", "USB Over-current at Boot", get_usb_over_current_at_boot())

        self.set_row(page, "Voltages", "Core Voltage", get_voltage("core"))
        self.set_row(page, "Voltages", "SDRAM C", get_voltage("sdram_c"))
        self.set_row(page, "Voltages", "SDRAM I", get_voltage("sdram_i"))
        self.set_row(page, "Voltages", "SDRAM P", get_voltage("sdram_p"))

        self.set_row(page, "Clocks", "ARM Clock", get_clock("arm"))
        self.set_row(page, "Clocks", "Core Clock", get_clock("core"))
        self.set_row(page, "Clocks", "eMMC Clock", get_clock("emmc"))

        self.set_row(page, "Advanced Power", "Power Chip Temp", get_power_chip_temp())
        self.set_row(page, "Advanced Power", "Power Level", get_power_level())
        self.set_row(page, "Advanced Power", "Core Rail Power", get_core_rail_power())
        self.set_row(page, "Advanced Power", "Ring Oscillator", get_ring_oscillator())
        self.set_row(page, "Advanced Power", "Raw Status", self.get_throttled_raw_description())

    def update_storage_page(self):
        page = "storage"
        self.set_row(page, "Boot / Device Info", "Boot Device", get_boot_device())
        self.set_row(page, "Boot / Device Info", "Root Device", get_root_device())
        self.set_row(page, "Boot / Device Info", "NVMe Present", get_nvme_drive_present())
        self.set_row(page, "Boot / Device Info", "Fan Present", get_fan_present())
        self.set_row(page, "Boot / Device Info", "Storage Devices", get_storage_summary())

        self.set_row(page, "SD Card", "Present", get_sd_present())
        self.set_row(page, "SD Card", "Device", get_sd_device() or NA)
        self.set_row(page, "SD Card", "Capacity", get_sd_capacity())
        self.set_row(page, "SD Card", "Card Used", get_sd_used())
        self.set_row(page, "SD Card", "Vendor", get_sd_vendor())
        self.set_row(page, "SD Card", "Model", get_sd_model())
        self.set_row(page, "SD Card", "Serial", get_sd_serial())
        self.set_row(page, "SD Card", "Mounted At", get_sd_mountpoint())

        self.set_row(page, "External USB Storage", "Model", get_usb_model())
        self.set_row(page, "External USB Storage", "Capacity", get_usb_capacity())
        self.set_row(page, "External USB Storage", "Free Space", get_usb_free_space())
        self.set_row(page, "External USB Storage", "Device Path", get_usb_device_path())
        self.set_row(page, "External USB Storage", "Mounted At", get_usb_mountpoint())


    def start_nvme_scan_once(self):
        if self.nvme_scan_running or self.nvme_scan_loaded:
            return False

        self.nvme_scan_running = True
        self.set_row("nvme", "NVMe Drive", "SMART Temp", "Scanning...")
        self.set_row("nvme", "NVMe Details", "Firmware", "Scanning...")
        self.set_row("nvme", "PCIe / NVMe Link", "Current Speed", "Scanning...")

        thread = threading.Thread(target=self.collect_nvme_data_in_background, daemon=True)
        thread.start()
        return False

    def collect_nvme_data_in_background(self):
        results = collect_nvme_data()
        GLib.idle_add(self.apply_nvme_results, results)

    def apply_nvme_results(self, results):
        for row in ["SMART Temp", "Manufacturer", "Model", "Capacity", "Drive Health"]:
            self.set_row("nvme", "NVMe Drive", row, results.get(row, NA))

        for row in ["Firmware", "Life Used", "Power-on Hours", "Unsafe Shutdowns", "Media Errors", "Mounted At"]:
            self.set_row("nvme", "NVMe Details", row, results.get(row, NA))

        for row in ["Current Speed", "Current Width", "Max Speed", "Max Width"]:
            self.set_row("nvme", "PCIe / NVMe Link", row, results.get(row, NA))

        self.nvme_scan_running = False
        self.nvme_scan_loaded = True
        return False

    def update_system_page(self):
        page = "system"
        self.set_row(page, "System Details", "Pi Model", get_model_display())
        self.set_row(page, "System Details", "OS Version", get_os_version())
        self.set_row(page, "System Details", "Kernel", get_kernel())
        self.set_row(page, "System Details", "Architecture", get_architecture())
        self.set_row(page, "System Details", "Hostname", get_hostname())
        self.set_row(page, "System Details", "Firmware Version", get_firmware_version())
        self.set_row(page, "System Details", "System Uptime", get_uptime())
        self.set_row(page, "System Details", "App Open Time", get_app_open_time())

        self.set_row(page, "Performance", "CPU Usage", get_cpu_usage())
        self.set_row(page, "Performance", "CPU Clock", get_clock("arm"))
        self.set_row(page, "Performance", "Core Clock", get_clock("core"))
        self.set_row(page, "Performance", "Core Voltage", get_voltage("core"))
        self.set_row(page, "Performance", "Memory", get_memory_usage())
        self.set_row(page, "Performance", "Swap", get_swap_usage())
        self.set_row(page, "Performance", "Load Avg (1m/5m/15m)", get_load_average())
        self.set_row(page, "Performance", "Processes", get_process_count())

        self.set_row(page, "Network", "IP Address", get_network_ip())
        self.set_row(page, "Network", "Default Route", get_default_route())
        self.set_row(page, "Network", "MAC Address", get_primary_mac())
        self.set_row(page, "Network", "Hostname", get_hostname())

def main():
    win = PiHardwareMonitor()
    win.connect("destroy", win.on_destroy)
    win.show_all()
    Gtk.main()


if __name__ == "__main__":
    main()
