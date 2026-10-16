# adb-qr

A lightweight, crash-free, cross-platform Python CLI tool to pair and connect Android 11+ Wireless Debugging using a terminal QR code.

No need to launch bulky Android Studio or manually type dynamic IP addresses, random ports, and 6-digit pairing codes.

## Why this exists?

Existing Node.js alternatives (like `adb-wifi`) often crash with `TypeError: Cannot read properties of null` when encountering non-standard mDNS packets on local networks. `adb-qr` is written in Python using `zeroconf` with strict packet validation, IPv4 prioritization, and automatic `pair` + `connect` chaining.

## Prerequisites

- **Python 3.8+**
- **`adb`** (Android Platform Tools) installed and available in your system `PATH`.
- PC and Android device connected to the **same Wi-Fi network**.

## Installation

### Option 1: Install as a global CLI command (Recommended)

 works on Linux, macOS, and Windows:

```bash
git clone [https://github.com/galooha/adb_qr.git]
cd adb_qr
pip install .