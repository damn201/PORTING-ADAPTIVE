"""Konstanta dan pengaturan Uncharted PC Installer (stdlib saja)."""

import json
import os
import platform
from pathlib import Path

APP_DIR_NAME = "UnchartedPCInstaller"

# --- Port native yang dipakai (Supermedo/uncharted_pc) ---
PORT_REPO = "Supermedo/uncharted_pc"
PORT_TAG = "v0.3.15"
PORT_ASSET = "uncharted-windows.zip"
PORT_URL = (
    f"https://github.com/{PORT_REPO}/releases/download/{PORT_TAG}/{PORT_ASSET}"
)
PORT_RELEASE_API = (
    f"https://api.github.com/repos/{PORT_REPO}/releases/tags/{PORT_TAG}"
)
PORT_LICENSE = "GPL v2 atau lebih baru"
LAUNCHER_EXE = "Uncharted.exe"

# Ukuran aset yang terverifikasi (26 Nov 2026): 122.970.173 byte = 117,3 MB.
PORT_ASSET_SIZE = 122970173

# --- Port cadangan (fallback): BilalReloaded ---
# Dipakai OTOMATIS bila unduhan port utama gagal. Terverifikasi 26 Nov 2026
# lewat GitHub API + README repo: rilis v0.8.6 (14 Nov 2026), 873 bintang,
# aset Uncharted-windows.zip 121.477.657 byte = 115,9 MB, launcher
# "Uncharted Launcher.exe". Lisensi tidak tercantum di GitHub.
FALLBACK_REPO = "bc160201983/Uncharted-The-Nathan-Drake-Collection-PC-port"
FALLBACK_TAG = "v0.8.6"
FALLBACK_ASSET = "Uncharted-windows.zip"
FALLBACK_URL = (
    f"https://github.com/{FALLBACK_REPO}/releases/download/"
    f"{FALLBACK_TAG}/{FALLBACK_ASSET}"
)
FALLBACK_RELEASE_API = (
    f"https://api.github.com/repos/{FALLBACK_REPO}/releases/tags/{FALLBACK_TAG}"
)
FALLBACK_LAUNCHER_EXE = "Uncharted Launcher.exe"
FALLBACK_ASSET_SIZE = 121477657

# Semua nama launcher yang dikenali (port utama dulu, lalu fallback).
LAUNCHER_NAMES = (LAUNCHER_EXE, FALLBACK_LAUNCHER_EXE)

# --- Folder game yang valid (dump PS4 Nathan Drake Collection) ---
# Wajib ada di folder game. Perbandingan nama tidak membedakan huruf
# besar/kecil karena dump PS4 di Windows bersifat case-insensitive.
REQUIRED_GAME_FILES = ("eboot.bin", "sce_sys", "u1data", "u2data", "u3data")
# Idealnya juga ada (hanya peringatan bila tidak ada, bukan kegagalan).
RECOMMENDED_GAME_FILES = ("big2-ps4_Shipping.elf", "big3-ps4_Shipping.elf")

# --- Syarat minimum PC (dari README port) ---
MIN_WINDOWS_BUILD = 18362  # Windows 10 versi 1903
MIN_RAM_GB = 8
MIN_VRAM_GB = 6
MIN_DISK_GB = 50  # port 117 MB + game ~44 GB
REQUIRED_CPU_FLAGS = ("avx", "f16c", "bmi1", "movbe", "lzcnt")

USER_AGENT = "UnchartedPCInstaller/1.1 (+https://github.com/Supermedo/uncharted_pc)"

# Validasi folder game: cari file wajib sampai sedalam ini (0 = folder itu
# sendiri, 1 = subfolder, 2 = subfolder dari subfolder). Pengguna sering
# memilih folder induk yang berisi subfolder game.
GAME_SEARCH_MAX_DEPTH = 2


def platform_id() -> str:
    """'windows' | 'macos' | 'linux' | 'unknown'."""
    system = platform.system().lower()
    if system == "windows":
        return "windows"
    if system == "darwin":
        return "macos"
    if system == "linux":
        return "linux"
    return "unknown"


def is_frozen() -> bool:
    """True saat berjalan sebagai binary hasil PyInstaller."""
    import sys

    return bool(getattr(sys, "frozen", False))


def app_dir() -> Path:
    """Folder data Uncharted PC Installer milik pengguna (dibuat bila belum ada)."""
    pid = platform_id()
    if pid == "windows":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    elif pid == "macos":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    folder = base / APP_DIR_NAME
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def downloads_dir() -> Path:
    folder = app_dir() / "downloads"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def settings_path() -> Path:
    return app_dir() / "settings.json"


def default_settings() -> dict:
    return {
        "install_dir": "",
        "game_folder": "",
        "game_validated": False,
        "port_version": "",
        "port_exe": "",
    }


def load_settings() -> dict:
    settings = default_settings()
    try:
        data = json.loads(settings_path().read_text(encoding="utf-8"))
        if isinstance(data, dict):
            settings.update(data)
    except (OSError, ValueError):
        pass
    return settings


def save_settings(settings: dict) -> None:
    settings_path().write_text(
        json.dumps(settings, indent=2, ensure_ascii=False), encoding="utf-8"
    )
