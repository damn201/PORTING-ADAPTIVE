"""Cek sistem: apakah PC ini memenuhi syarat minimum port Uncharted PC.

Syarat minimum (dari README port Supermedo/uncharted_pc):
  - Windows 10 (1903+) atau Windows 11 64-bit
  - CPU Intel Core generasi ke-3+ / AMD Ryzen / AMD FX
    (butuh instruksi AVX, F16C, BMI1, MOVBE, LZCNT)
  - GPU dengan Vulkan 1.3 + driver terbaru, VRAM 6 GB direkomendasikan
    (kartu 4 GB bisa crash)
  - RAM bebas ~8 GB
  - Ruang disk: port 117 MB + game ~44 GB (cek minimal 50 GB kosong)

Setiap cek mengembalikan dict:
  {"id", "name", "status", "detail", "tip"}
dengan status "ok" | "gagal" | "tidak diketahui".

Semua cek dirancang gagal dengan anggun di Linux/Wine — tidak pernah crash,
melainkan melaporkan "tidak dapat diperiksa di sini".
"""

import ctypes
import os
import platform
import re
import shutil
import subprocess
import sys
from pathlib import Path

from .config import (
    MIN_DISK_GB,
    MIN_RAM_GB,
    MIN_VRAM_GB,
    MIN_WINDOWS_BUILD,
    REQUIRED_CPU_FLAGS,
)

# Status
OK = "ok"
FAIL = "gagal"
UNKNOWN = "tidak diketahui"


def _check(check_id: str, name: str, status: str, detail: str, tip: str = "") -> dict:
    return {
        "id": check_id,
        "name": name,
        "status": status,
        "detail": detail,
        "tip": tip,
    }


# ---------------------------------------------------------------------------
# OS
# ---------------------------------------------------------------------------

def _os_check() -> dict:
    if platform.system() != "Windows":
        return _check(
            "os",
            "Sistem operasi",
            UNKNOWN,
            f"Tidak dapat diperiksa di sini ({platform.system()} — bukan Windows).",
            "Port ini hanya berjalan di Windows 10 (1903+) atau Windows 11 64-bit.",
        )
    try:
        ver = sys.getwindowsversion()
        build = ver.build
        edition = "Windows 11" if build >= 22000 else "Windows 10"
        is_64bit = platform.machine().lower() in ("amd64", "x86_64", "arm64")
        if build >= MIN_WINDOWS_BUILD and is_64bit:
            return _check(
                "os",
                "Sistem operasi",
                OK,
                f"{edition} build {build} 64-bit.",
            )
        if build < MIN_WINDOWS_BUILD:
            return _check(
                "os",
                "Sistem operasi",
                FAIL,
                f"{edition} build {build} — terlalu lama.",
                "Butuh Windows 10 versi 1903 (build 18362) atau lebih baru.",
            )
        return _check(
            "os",
            "Sistem operasi",
            FAIL,
            "Windows 32-bit terdeteksi.",
            "Port ini butuh Windows 64-bit.",
        )
    except (OSError, AttributeError):
        return _check(
            "os",
            "Sistem operasi",
            UNKNOWN,
            "Versi Windows tidak dapat dibaca.",
            "Pastikan memakai Windows 10 (1903+) atau Windows 11 64-bit.",
        )


# ---------------------------------------------------------------------------
# CPU
# ---------------------------------------------------------------------------

def _cpu_flags_from_py_cpuinfo() -> dict | None:
    """Baca flag CPU lewat py-cpuinfo; None bila paket tidak tersedia."""
    try:
        import cpuinfo
    except ImportError:
        return None
    try:
        flags = {f.lower() for f in cpuinfo.get_cpu_info().get("flags", [])}
    except Exception:  # noqa: BLE001 - py-cpuinfo gagal di CPU tak dikenal
        return None
    return {flag: flag in flags for flag in REQUIRED_CPU_FLAGS}


def _cpu_flags_from_proc() -> dict | None:
    """Baca flag CPU dari /proc/cpuinfo (Linux)."""
    try:
        text = Path("/proc/cpuinfo").read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    match = re.search(r"^flags\s*:\s*(.+)$", text, re.MULTILINE)
    if not match:
        return None
    flags = set(match.group(1).split())
    return {flag: flag in flags for flag in REQUIRED_CPU_FLAGS}


def _cpu_name() -> str:
    if platform.system() == "Linux":
        try:
            text = Path("/proc/cpuinfo").read_text(encoding="utf-8", errors="replace")
            match = re.search(r"model name\s*:\s*(.+)", text)
            if match:
                return match.group(1).strip()
        except OSError:
            pass
    if platform.system() == "Windows":
        try:
            out = subprocess.run(
                ["wmic", "cpu", "get", "name"],
                capture_output=True, text=True, timeout=15,
            )
            lines = [ln.strip() for ln in out.stdout.splitlines() if ln.strip()]
            if len(lines) > 1:
                return lines[1]
        except (OSError, subprocess.SubprocessError):
            pass
    return platform.processor() or "Tidak diketahui"


def _cpu_check() -> dict:
    flags = _cpu_flags_from_py_cpuinfo()
    if flags is None:
        flags = _cpu_flags_from_proc()
    name = _cpu_name()
    if flags is None:
        return _check(
            "cpu",
            "CPU (instruksi AVX, F16C, BMI1, MOVBE, LZCNT)",
            UNKNOWN,
            f"Tidak dapat diperiksa di sini. CPU: {name}.",
            "Di Windows, pasang py-cpuinfo agar instruksi CPU bisa diperiksa. "
            "Butuh CPU Intel Core gen ke-3+ / AMD Ryzen / AMD FX.",
        )
    missing = [flag for flag, ok in flags.items() if not ok]
    if not missing:
        return _check(
            "cpu",
            "CPU (instruksi AVX, F16C, BMI1, MOVBE, LZCNT)",
            OK,
            f"Semua instruksi tersedia. CPU: {name}.",
        )
    return _check(
        "cpu",
        "CPU (instruksi AVX, F16C, BMI1, MOVBE, LZCNT)",
        FAIL,
        f"Instruksi tidak tersedia: {', '.join(missing).upper()}. CPU: {name}.",
        "Port ini butuh AVX, F16C, BMI1, MOVBE, dan LZCNT. "
        "CPU yang terlalu lama tidak bisa menjalankan gamenya.",
    )


# ---------------------------------------------------------------------------
# RAM
# ---------------------------------------------------------------------------

def _ram_gb() -> float | None:
    if platform.system() == "Windows":
        try:
            class MemoryStatus(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]

            status = MemoryStatus()
            status.dwLength = ctypes.sizeof(status)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status))
            return status.ullTotalPhys / 1024 ** 3
        except (OSError, AttributeError):
            return None
    if platform.system() == "Linux":
        try:
            text = Path("/proc/meminfo").read_text(encoding="utf-8")
            match = re.search(r"MemTotal:\s*(\d+)\s*kB", text)
            if match:
                return int(match.group(1)) / 1024 / 1024
        except OSError:
            return None
    if platform.system() == "Darwin":
        try:
            out = subprocess.run(
                ["sysctl", "-n", "hw.memsize"],
                capture_output=True, text=True, timeout=10,
            )
            return int(out.stdout.strip()) / 1024 ** 3
        except (OSError, ValueError, subprocess.SubprocessError):
            return None
    return None


def _ram_check() -> dict:
    ram = _ram_gb()
    if ram is None:
        return _check(
            "ram",
            "RAM",
            UNKNOWN,
            "RAM tidak dapat diperiksa di sini.",
            f"Disarankan RAM {MIN_RAM_GB} GB atau lebih.",
        )
    if ram >= MIN_RAM_GB:
        return _check("ram", "RAM", OK, f"{ram:.1f} GB terpasang.")
    return _check(
        "ram",
        "RAM",
        FAIL,
        f"{ram:.1f} GB terpasang — di bawah rekomendasi.",
        f"Disarankan RAM {MIN_RAM_GB} GB atau lebih agar game berjalan lancar.",
    )


# ---------------------------------------------------------------------------
# GPU + Vulkan
# ---------------------------------------------------------------------------

def _gpu_info() -> tuple[str, float | None]:
    """(nama GPU, VRAM dalam GB atau None bila tidak diketahui).

    Gagal membaca = ("Tidak diketahui", None), bukan exception.
    """
    if platform.system() == "Windows":
        try:
            out = subprocess.run(
                ["wmic", "path", "win32_VideoController",
                 "get", "name,AdapterRAM"],
                capture_output=True, text=True, timeout=20,
            )
            best_name, best_vram = "", None
            for line in out.stdout.splitlines():
                line = line.strip()
                if not line or line.lower().startswith("adapterram"):
                    continue
                parts = line.split(None, 1)
                try:
                    vram_bytes = int(parts[0])
                    vram_gb = vram_bytes / 1024 ** 3
                except (ValueError, IndexError):
                    vram_gb = None
                name = parts[1].strip() if len(parts) > 1 else ""
                if best_vram is None or (vram_gb or 0) > best_vram:
                    best_name, best_vram = name, vram_gb
            if best_name:
                return best_name, best_vram
        except (OSError, subprocess.SubprocessError):
            pass
        return "Tidak diketahui", None
    if platform.system() == "Linux":
        try:
            out = subprocess.run(["lspci"], capture_output=True, text=True, timeout=20)
            for line in out.stdout.splitlines():
                if "VGA" in line or "3D controller" in line:
                    return line.split(":", 2)[-1].strip(), None
        except (OSError, subprocess.SubprocessError):
            pass
        return "Tidak diketahui", None
    return "Tidak diketahui", None


def _gpu_check() -> dict:
    name, vram = _gpu_info()
    if vram is None:
        return _check(
            "gpu",
            "GPU / VRAM",
            UNKNOWN,
            f"GPU: {name}. VRAM tidak dapat diperiksa di sini.",
            f"Disarankan GPU dengan VRAM {MIN_VRAM_GB} GB. "
            "Kartu 4 GB bisa crash saat memainkan game.",
        )
    if vram >= MIN_VRAM_GB:
        return _check(
            "gpu",
            "GPU / VRAM",
            OK,
            f"{name} — VRAM {vram:.1f} GB.",
        )
    return _check(
        "gpu",
        "GPU / VRAM",
        FAIL,
        f"{name} — VRAM {vram:.1f} GB, di bawah rekomendasi.",
        f"Disarankan VRAM {MIN_VRAM_GB} GB. Kartu 4 GB bisa crash.",
    )


def _vulkan_check() -> dict:
    if platform.system() == "Windows":
        system_root = Path(os.environ.get("SystemRoot", r"C:\Windows"))
        dll = system_root / "System32" / "vulkan-1.dll"
        if dll.is_file():
            return _check(
                "vulkan",
                "Vulkan 1.3",
                OK,
                "vulkan-1.dll ditemukan di System32.",
            )
        return _check(
            "vulkan",
            "Vulkan 1.3",
            FAIL,
            "vulkan-1.dll tidak ditemukan di System32.",
            "Pasang driver GPU terbaru dari situs resmi NVIDIA / AMD / Intel — "
            "driver terbaru sudah menyertakan Vulkan 1.3.",
        )
    return _check(
        "vulkan",
        "Vulkan 1.3",
        UNKNOWN,
        "Tidak dapat diperiksa di sini (bukan Windows).",
        "Di Windows, pastikan driver GPU terbaru terpasang (Vulkan 1.3).",
    )


# ---------------------------------------------------------------------------
# Disk
# ---------------------------------------------------------------------------

def _disk_check(path: str | Path | None) -> dict:
    target = Path(path) if path else Path.home()
    if not target.exists():
        target = Path.home()
    try:
        free_gb = shutil.disk_usage(target).free / 1024 ** 3
    except OSError:
        return _check(
            "disk",
            "Ruang disk kosong",
            UNKNOWN,
            f"Tidak dapat memeriksa disk di {target}.",
            f"Siapkan minimal {MIN_DISK_GB} GB kosong (port 117 MB + game ~44 GB).",
        )
    if free_gb >= MIN_DISK_GB:
        return _check(
            "disk",
            "Ruang disk kosong",
            OK,
            f"{free_gb:.1f} GB kosong di {target}.",
        )
    return _check(
        "disk",
        "Ruang disk kosong",
        FAIL,
        f"Hanya {free_gb:.1f} GB kosong di {target}.",
        f"Siapkan minimal {MIN_DISK_GB} GB kosong — game saja ~44 GB. "
        "Kosongkan disk atau pilih drive lain untuk folder install.",
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def run_checks(install_dir: str | Path | None = None) -> list[dict]:
    """Jalankan semua cek sistem. Tidak pernah melempar exception."""
    checks = []
    for fn in (_os_check, _cpu_check, _ram_check, _gpu_check, _vulkan_check):
        try:
            checks.append(fn())
        except Exception as exc:  # noqa: BLE001 - satu cek gagal, lainnya tetap jalan
            checks.append(_check(
                getattr(fn, "__name__", "cek"),
                "Cek sistem",
                UNKNOWN,
                f"Tidak dapat diperiksa di sini ({exc}).",
            ))
    try:
        checks.append(_disk_check(install_dir))
    except Exception as exc:  # noqa: BLE001
        checks.append(_check(
            "disk", "Ruang disk kosong", UNKNOWN,
            f"Tidak dapat diperiksa di sini ({exc}).",
        ))
    return checks


def summarize(checks: list[dict]) -> tuple[int, int, int]:
    """(jumlah lolos, jumlah gagal, jumlah tidak diketahui)."""
    ok = sum(1 for c in checks if c["status"] == OK)
    failed = sum(1 for c in checks if c["status"] == FAIL)
    unknown = sum(1 for c in checks if c["status"] == UNKNOWN)
    return ok, failed, unknown
