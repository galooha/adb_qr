#!/usr/bin/env python3
"""
adb-qr: Pair and connect Android Wireless Debugging via terminal QR code.
"""

from __future__ import annotations

import argparse
import random
import shutil
import string
import subprocess
import sys
import threading
from typing import Dict, Tuple

import qrcode
from zeroconf import IPVersion, ServiceBrowser, ServiceListener, Zeroconf

__version__ = "0.1.0"

PAIRING_TYPE = "_adb-tls-pairing._tcp.local."
CONNECT_TYPE = "_adb-tls-connect._tcp.local."


class AdbQrListener(ServiceListener):
    """Listens for Android ADB mDNS broadcasts for pairing and connecting."""

    def __init__(
        self,
        session_name: str,
        password: str,
        done_event: threading.Event,
        connect_only: bool = False,
    ):
        self.session_name = session_name
        self.password = password
        self.done_event = done_event
        self.connect_only = connect_only
        self.paired_ip: str | None = None
        self.connect_candidates: Dict[str, int] = {}
        self.lock = threading.Lock()

    def update_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        # Handle port changes when Wireless Debugging is toggled on the phone
        self.add_service(zc, type_, name)

    def remove_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        pass

    def add_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        if self.done_event.is_set():
            return

        info = zc.get_service_info(type_, name)
        # Strict validation to prevent crashes on malformed local mDNS packets
        if not info or not info.addresses or not info.port:
            return

        # Prefer IPv4 to avoid link-local IPv6 routing issues with ADB
        addrs = info.parsed_addresses(IPVersion.V4Only) or info.parsed_addresses()
        if not addrs:
            return

        ip = addrs[0]
        port = info.port

        with self.lock:
            if self.done_event.is_set():
                return

            # Mode A: Connect-only mode (for already paired devices)
            if self.connect_only and type_ == CONNECT_TYPE:
                print(f"\n[+] Found active device at {ip}:{port}. Connecting...")
                self._connect_device(ip, port)
                self.done_event.set()
                return

            # Mode B - Phase 1: Capture the pairing broadcast after QR scan
            if type_ == PAIRING_TYPE and self.session_name in name:
                print(f"\n[+] Pairing request detected from {ip}:{port}. Pairing...")
                if self._pair_device(ip, port):
                    self.paired_ip = ip
                    # If the connect service was already discovered earlier, connect immediately
                    if ip in self.connect_candidates:
                        self._connect_device(ip, self.connect_candidates[ip])
                        self.done_event.set()
                    else:
                        print("[*] Waiting for connection port broadcast...")
                else:
                    self.done_event.set()

            # Mode B - Phase 2: Capture the connection port broadcast
            elif type_ == CONNECT_TYPE:
                self.connect_candidates[ip] = port
                if self.paired_ip == ip:
                    self._connect_device(ip, port)
                    self.done_event.set()

    def _pair_device(self, ip: str, port: int) -> bool:
        try:
            res = subprocess.run(
                ["adb", "pair", f"{ip}:{port}", self.password],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=15,
            )
            output = (res.stdout + res.stderr).strip()
            if res.returncode == 0 and "Successfully paired" in output:
                print(f"[✓] Paired successfully: {output}")
                return True
            print(f"[✗] Pairing failed: {output}", file=sys.stderr)
        except subprocess.TimeoutExpired:
            print(f"[✗] Timed out while pairing with {ip}:{port}", file=sys.stderr)
        return False

    def _connect_device(self, ip: str, port: int) -> None:
        print(f"[+] Connecting to {ip}:{port}...")
        try:
            res = subprocess.run(
                ["adb", "connect", f"{ip}:{port}"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=15,
            )
            output = (res.stdout + res.stderr).strip()
            if res.returncode == 0 and "connected to" in output.lower():
                print(f"[✓] {output}")
            else:
                print(f"[!] Connection output: {output}", file=sys.stderr)
        except subprocess.TimeoutExpired:
            print(f"[✗] Timed out while connecting to {ip}:{port}", file=sys.stderr)


def generate_credentials() -> Tuple[str, str]:
    session = "studio-" + "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
    password = "".join(random.choices(string.digits, k=6))
    return session, password


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Pair and connect Android Wireless Debugging via terminal QR code."
    )
    parser.add_argument(
        "-c", "--connect-only",
        action="store_true",
        help="Skip QR pairing and automatically connect to an already-paired device on the network",
    )
    parser.add_argument(
        "-t", "--timeout",
        type=int,
        default=120,
        help="Timeout in seconds to wait for device (default: 120)",
    )
    parser.add_argument(
        "--light",
        action="store_true",
        help="Invert QR code colors for light-themed terminals",
    )
    parser.add_argument(
        "-v", "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    return parser.parse_args()


def main() -> None:
    # Force UTF-8 output to prevent UnicodeEncodeError on Windows consoles (GBK/cp936)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")

    args = parse_args()

    if not shutil.which("adb"):
        print(
            "[✗] Error: 'adb' command not found in PATH. Please install Android Platform Tools.",
            file=sys.stderr,
        )
        sys.exit(1)

    session_name, password = generate_credentials()

    if args.connect_only:
        print("[*] Connect-only mode: Searching for already-paired Android devices on LAN...")
        print("[*] Make sure 'Wireless debugging' is turned ON on your phone.")
    else:
        qr_payload = f"WIFI:T:ADB;S:{session_name};P:{password};;"
        print("==========================================================")
        print(" 1. On your Android device, go to:")
        print("    Developer options -> Wireless debugging")
        print(" 2. Tap 'Pair device with QR code' and scan the code below")
        print("==========================================================\n")

        qr = qrcode.QRCode(border=2)
        qr.add_data(qr_payload)
        qr.make(fit=True)
        qr.print_ascii(invert=not args.light)

        print(f"\n[*] Listening for mDNS broadcasts (Session: {session_name} | PIN: {password})...")

    print("[*] Press Ctrl+C to cancel.")

    done_event = threading.Event()
    zc = Zeroconf()
    listener = AdbQrListener(
        session_name=session_name,
        password=password,
        done_event=done_event,
        connect_only=args.connect_only,
    )

    services = [CONNECT_TYPE] if args.connect_only else [PAIRING_TYPE, CONNECT_TYPE]
    ServiceBrowser(zc, services, listener)

    try:
        if not done_event.wait(timeout=args.timeout):
            print("\n[!] Timed out waiting for device.", file=sys.stderr)
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n[!] Cancelled by user.")
        sys.exit(130)
    finally:
        zc.close()


if __name__ == "__main__":
    main()