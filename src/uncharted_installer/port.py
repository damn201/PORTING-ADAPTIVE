"""Manajemen port Uncharted PC: unduh, pasang, verifikasi, dan validasi
folder game.

Port utama: Supermedo/uncharted_pc v0.3.15 (GPL v2+).
Aset: uncharted-windows.zip (117,3 MB), berisi launcher Uncharted.exe.
Port cadangan (fallback otomatis bila unduhan utama gagal):
BilalReloaded v0.8.6, aset Uncharted-windows.zip (115,9 MB),
launcher "Uncharted Launcher.exe".
Cara pakai portnya (dari README port): ekstrak zip, jalankan launcher,
pilih folder game, pilih game, tekan PLAY. Port akan meminta folder game
sendiri saat pertama main.

Alur normal TIDAK PERNAH memakai GitHub API — unduhan memakai URL
hardcoded di config. API hanya dipakai release_info() untuk --self-test.

Modul ini TIDAK menyertakan file game apa pun — pengguna wajib memakai dump
PS4 "Uncharted: The Nathan Drake Collection" miliknya sendiri.
"""

import json
import os
import shutil
import subprocess
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

from .config import (
    FALLBACK_ASSET,
    FALLBACK_ASSET_SIZE,
    FALLBACK_LAUNCHER_EXE,
    FALLBACK_RELEASE_API,
    FALLBACK_TAG,
    FALLBACK_URL,
    GAME_SEARCH_MAX_DEPTH,
    LAUNCHER_EXE,
    LAUNCHER_NAMES,
    PORT_ASSET,
    PORT_ASSET_SIZE,
    PORT_RELEASE_API,
    PORT_TAG,
    PORT_URL,
    RECOMMENDED_GAME_FILES,
    REQUIRED_GAME_FILES,
    USER_AGENT,
    downloads_dir,
    load_settings,
    save_settings,
)

# Percobaan unduh ulang bila koneksi gagal/terputus.
DOWNLOAD_MAX_ATTEMPTS = 3
DOWNLOAD_RETRY_DELAY_SECONDS = 5


def _github_json(url: str, timeout: int = 30) -> dict:
    req = urllib.request.Request(
        url, headers={"User-Agent": USER_AGENT, "Accept": "application/vnd.github+json"}
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def release_info(
    api_url: str = PORT_RELEASE_API,
    asset_name: str = PORT_ASSET,
    timeout: int = 30,
) -> dict:
    """Ambil info rilis port dari GitHub API (HANYA untuk --self-test).

    Mengembalikan {"tag", "asset_name", "asset_url", "asset_size"}.
    Bisa gagal (mis. rate-limit 403) — pemanggil harus menolerirnya.
    """
    data = _github_json(api_url, timeout=timeout)
    assets = [
        {
            "name": a["name"],
            "url": a["browser_download_url"],
            "size": a.get("size", 0),
        }
        for a in data.get("assets", [])
    ]
    for asset in assets:
        if asset["name"] == asset_name:
            return {
                "tag": data.get("tag_name", ""),
                "asset_name": asset["name"],
                "asset_url": asset["url"],
                "asset_size": asset["size"],
            }
    raise RuntimeError(
        f"Aset {asset_name} tidak ditemukan di rilis {data.get('tag_name', '?')}."
    )


def release_info_fallback(timeout: int = 30) -> dict:
    """Info rilis port cadangan BilalReloaded (HANYA untuk --self-test)."""
    return release_info(
        api_url=FALLBACK_RELEASE_API, asset_name=FALLBACK_ASSET, timeout=timeout
    )


def _download_once(
    url: str,
    dest: Path,
    progress_cb=None,
    expected_size: int = 0,
    timeout: int = 900,
) -> Path:
    """Satu kali percobaan unduh. Menghapus file sebagian bila gagal."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            total = int(resp.headers.get("Content-Length") or 0)
            downloaded = 0
            with open(dest, "wb") as fh:
                while True:
                    chunk = resp.read(1024 * 256)
                    if not chunk:
                        break
                    fh.write(chunk)
                    downloaded += len(chunk)
                    if progress_cb:
                        progress_cb(downloaded, total)
    except Exception:
        try:
            if dest.is_file():
                dest.unlink()
        except OSError:
            pass
        raise
    if expected_size and dest.stat().st_size != expected_size:
        actual_size = dest.stat().st_size
        try:
            dest.unlink()
        except OSError:
            pass
        raise RuntimeError(
            f"Ukuran file tidak cocok: {actual_size} byte, "
            f"diharapkan {expected_size} byte. Unduhan mungkin rusak."
        )
    return dest


def download_port(
    url: str = PORT_URL,
    dest: Path | None = None,
    progress_cb=None,
    expected_size: int = PORT_ASSET_SIZE,
    timeout: int = 900,
    retries: int = DOWNLOAD_MAX_ATTEMPTS,
) -> Path:
    """Unduh zip port dengan laporan progres (downloaded_bytes, total_bytes).

    Mencoba ulang sampai `retries` kali bila koneksi gagal/terputus.
    Memverifikasi ukuran file hasil unduhan bila expected_size diberikan.
    Tidak pernah memakai GitHub API — URL sudah hardcoded di config.
    """
    dest = dest or (downloads_dir() / PORT_ASSET)
    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            return _download_once(
                url, dest,
                progress_cb=progress_cb,
                expected_size=expected_size,
                timeout=timeout,
            )
        except Exception as exc:  # noqa: BLE001 - coba lagi / laporkan di akhir
            last_error = exc
            if attempt < retries:
                time.sleep(DOWNLOAD_RETRY_DELAY_SECONDS)
    raise RuntimeError(
        f"Unduhan gagal setelah {retries} kali percobaan: {last_error}. "
        "Periksa koneksi internet, lalu coba lagi."
    )


def extract_port(zip_path: Path, install_dir: Path) -> Path:
    """Ekstrak zip port ke folder install. Mengembalikan folder install."""
    zip_path = Path(zip_path)
    install_dir = Path(install_dir)
    if not zip_path.is_file():
        raise RuntimeError(f"File zip tidak ditemukan: {zip_path}")
    if not zipfile.is_zipfile(zip_path):
        raise RuntimeError(f"File bukan zip yang valid: {zip_path}")
    install_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(path=install_dir)
    return install_dir


def find_launcher(install_dir: Path | str) -> Path | None:
    """Cari launcher port di folder install (termasuk subfolder).

    Mengenali kedua nama: "Uncharted.exe" (Supermedo) dan
    "Uncharted Launcher.exe" (BilalReloaded). Port utama didahulukan.
    Perbandingan nama tidak membedakan huruf besar/kecil.
    """
    root = Path(install_dir)
    if not root.is_dir():
        return None
    for name in LAUNCHER_NAMES:
        target = name.lower()
        direct = root / name
        if direct.is_file():
            return direct
        for candidate in root.rglob("*"):
            if candidate.is_file() and candidate.name.lower() == target:
                return candidate
    return None


def verify_port(install_dir: Path | str) -> Path | None:
    """Path launcher bila port sudah terpasang, None bila belum."""
    return find_launcher(install_dir)


def _save_port_settings(install_dir: Path, exe: Path, version: str) -> None:
    settings = load_settings()
    settings["install_dir"] = str(install_dir)
    settings["port_version"] = version
    settings["port_exe"] = str(exe)
    save_settings(settings)


def install_port(
    install_dir: Path | str,
    progress_cb=None,
    log=None,
) -> Path:
    """Unduh + ekstrak port ke folder install. Mengembalikan path launcher.

    Bisa dilanjutkan (resumable): bila launcher sudah ada, langsung
    dikembalikan tanpa mengunduh lagi. Mencoba port utama (Supermedo)
    dulu; bila gagal, otomatis beralih ke port cadangan (BilalReloaded).
    `log` (bila diberikan) dipanggil dengan pesan Bahasa Indonesia.
    Menyimpan install_dir dan versi port ke settings.
    """
    install_dir = Path(install_dir)
    existing = find_launcher(install_dir)
    if existing is not None:
        if log:
            log(f"Port sudah terpasang, unduhan dilewati: {existing.name}.")
        _save_port_settings(install_dir, existing, load_settings().get("port_version") or "")
        return existing

    def _try_one(label: str, url: str, asset: str, size: int, tag: str) -> Path:
        if log:
            log(f"Mengunduh port {label} ({tag})...")
        zip_path = download_port(
            url,
            dest=downloads_dir() / asset,
            progress_cb=progress_cb,
            expected_size=size,
        )
        if log:
            log(f"Unduhan {label} selesai. Mengekstrak...")
        extract_port(zip_path, install_dir)
        exe = find_launcher(install_dir)
        if exe is None:
            raise RuntimeError(
                f"Port {label} berhasil diunduh dan diekstrak, tetapi "
                "launcher tidak ditemukan di folder install."
            )
        _save_port_settings(install_dir, exe, tag)
        return exe

    errors: list[str] = []
    try:
        return _try_one("Supermedo", PORT_URL, PORT_ASSET, PORT_ASSET_SIZE, PORT_TAG)
    except Exception as exc:  # noqa: BLE001 - lanjut ke fallback
        errors.append(f"Supermedo ({PORT_TAG}): {exc}")
        if log:
            log(f"Unduhan port Supermedo gagal: {exc}")
            log("Mencoba port cadangan (BilalReloaded)...")
    try:
        return _try_one(
            "BilalReloaded", FALLBACK_URL, FALLBACK_ASSET,
            FALLBACK_ASSET_SIZE, FALLBACK_TAG,
        )
    except Exception as exc:  # noqa: BLE001 - kedua port gagal
        errors.append(f"BilalReloaded ({FALLBACK_TAG}): {exc}")
    raise RuntimeError(
        "Kedua port gagal diunduh:\n- " + "\n- ".join(errors) +
        "\nPeriksa koneksi internet, lalu tekan MAIN lagi."
    )


def validate_game_folder(
    folder: Path | str,
    max_depth: int = GAME_SEARCH_MAX_DEPTH,
) -> dict:
    """Validasi folder game (dump PS4 Nathan Drake Collection).

    Mencari file/folder wajib secara REKURSIF sampai `max_depth` level ke
    dalam (0 = folder itu sendiri), karena pengguna sering memilih folder
    induk yang berisi subfolder game. Perbandingan nama tidak membedakan
    huruf besar/kecil.

    Mengembalikan:
      {"valid": bool,
       "missing_required": [nama yang hilang],
       "missing_recommended": [nama yang idealnya ada],
       "found_at": {nama: path relatif tempat ditemukan},
       "detail": str}
    "valid" di sini hanya berarti "file lengkap ditemukan" — bila tidak
    valid, ini HANYA peringatan: aplikasi tetap meluncurkan port dan
    membiarkan GUI port-nya sendiri yang meminta folder game.
    """
    root = Path(folder)
    empty = {
        "valid": False,
        "missing_required": list(REQUIRED_GAME_FILES),
        "missing_recommended": list(RECOMMENDED_GAME_FILES),
        "found_at": {},
        "detail": f"Folder tidak ditemukan: {root}",
    }
    if not root.is_dir():
        return empty
    # Kumpulkan nama (huruf kecil) -> path relatif, sampai max_depth.
    found: dict[str, str] = {}
    try:
        for dirpath, dirnames, filenames in os.walk(root):
            rel_dir = Path(dirpath).relative_to(root)
            depth = 0 if str(rel_dir) == "." else len(rel_dir.parts)
            if depth > max_depth:
                dirnames[:] = []
                continue
            for name in list(dirnames) + list(filenames):
                key = name.lower()
                if key not in found:
                    found[key] = str(rel_dir / name) if depth else name
            if depth >= max_depth:
                dirnames[:] = []
    except OSError as exc:
        result = dict(empty)
        result["detail"] = f"Tidak bisa membaca folder game: {exc}"
        return result

    missing_required = [f for f in REQUIRED_GAME_FILES if f.lower() not in found]
    missing_recommended = [
        f for f in RECOMMENDED_GAME_FILES if f.lower() not in found
    ]
    found_at = {
        f: found[f.lower()] for f in REQUIRED_GAME_FILES + RECOMMENDED_GAME_FILES
        if f.lower() in found
    }
    valid = not missing_required
    if valid:
        nested = {f for f in found_at.values() if os.sep in f}
        where = (
            f" File ditemukan di subfolder ({', '.join(sorted(nested))})."
            if nested else ""
        )
        if not missing_recommended:
            detail = (
                "Folder game lengkap: eboot.bin, sce_sys, u1data, u2data, "
                f"u3data, dan file .elf ada.{where}"
            )
        else:
            detail = (
                "Folder game lengkap untuk dimainkan, tetapi file berikut "
                f"tidak ada (disarankan, bukan wajib): "
                f"{', '.join(missing_recommended)}.{where}"
            )
    else:
        detail = (
            "Folder game ini belum lengkap — file/folder wajib yang hilang: "
            f"{', '.join(missing_required)}. Ini hanya peringatan: aplikasi "
            "tetap akan membuka port, dan port akan meminta kamu memilih "
            "folder game yang benar saat pertama main. Pastikan itu adalah "
            "dump PS4 'Uncharted: The Nathan Drake Collection' "
            "(mis. CUSA02343 / CUSA02320 / CUSA02344) lengkap dengan "
            "update 1.02."
        )
    return {
        "valid": valid,
        "missing_required": missing_required,
        "missing_recommended": missing_recommended,
        "found_at": found_at,
        "detail": detail,
    }


def launch_port(install_dir: Path | str) -> tuple[bool, str]:
    """Jalankan launcher port dari folder install (GUI port akan terbuka)."""
    exe = find_launcher(install_dir)
    if exe is None:
        return False, (
            "Port belum terpasang. Tekan MAIN lagi — aplikasi akan "
            "mengunduh dan memasang port dulu."
        )
    try:
        subprocess.Popen(
            [str(exe)],
            cwd=str(Path(exe).parent),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except OSError as exc:
        return False, f"Tidak bisa menjalankan {exe.name}: {exc}"
    return True, (
        f"{exe.name} dibuka. Di dalam port: pilih folder game, "
        "pilih game (Uncharted 1 / 2 / 3), lalu tekan PLAY."
    )


def open_folder(path: Path | str) -> tuple[bool, str]:
    """Buka folder di File Explorer (Windows) / file manager lainnya."""
    import platform
    import sys

    target = Path(path)
    if not target.is_dir():
        return False, f"Folder tidak ditemukan: {target}"
    try:
        system = platform.system()
        if system == "Windows":
            subprocess.Popen(["explorer", str(target)])
        elif system == "Darwin":
            subprocess.Popen(["open", str(target)])
        else:
            subprocess.Popen(["xdg-open", str(target)])
    except OSError as exc:
        return False, f"Tidak bisa membuka folder: {exc}"
    return True, f"Membuka folder: {target}"
