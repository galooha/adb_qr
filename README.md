# adb-qr

A lightweight, crash-free Python CLI tool to pair and connect Android 11+ Wireless Debugging using a terminal QR code.

No need to launch bulky Android Studio or manually type dynamic IP addresses, random ports, and 6-digit pairing codes.

## Why this exists?

Existing Node.js alternatives (like `adb-wifi`) often crash with `TypeError: Cannot read properties of null` when encountering non-standard mDNS packets on local networks. `adb-qr` is written in Python using `zeroconf` with strict packet validation, zero bloat, and automatic `pair` + `connect` chaining.

## Prerequisites

- **Python 3.10+**
- **`adb`** (Android Platform Tools) installed and available in your system `PATH`.
- PC and Android device connected to the **same Wi-Fi network**.

## Installation

1. Clone this repository:
   ```bash
   git clone [https://github.com/](https://github.com/)<your-username>/adb-qr.git
   cd adb-qr
