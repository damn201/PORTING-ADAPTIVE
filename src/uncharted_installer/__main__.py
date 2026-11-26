"""Entry point Uncharted PC Installer.

Penggunaan:
  python -m uncharted_installer            # buka GUI
  python -m uncharted_installer --version  # tampilkan versi
  python -m uncharted_installer --self-test  # cek non-GUI (untuk pengujian)
"""

import argparse
import sys
import tempfile
from pathlib import Path


def _make_mock_game_folder(root: Path, files: list[str]) -> Path:
    """Bangun folder game tiruan berisi file/folder sesuai daftar."""
    folder = root / "CUSA02343"
    folder.mkdir(parents=True, exist_ok=True)
    for name in files:
        path = folder / name
        if name in ("sce_sys", "u1data", "u2data", "u3data"):
            path.mkdir(exist_ok=True)
            (path / ".keep").write_bytes(b"")
        else:
            path.write_bytes(b"\x00" * 16)
    return folder


def self_test() -> int:
    """Tes mandiri tanpa GUI; kembalikan 0 bila semua lolos."""
    from uncharted_installer import __version__
    from uncharted_installer.config import (
        FALLBACK_ASSET,
        FALLBACK_ASSET_SIZE,
        FALLBACK_TAG,
        PORT_ASSET,
        PORT_ASSET_SIZE,
        PORT_TAG,
        REQUIRED_GAME_FILES,
        app_dir,
        platform_id,
    )
    from uncharted_installer.port import (
        release_info,
        release_info_fallback,
        validate_game_folder,
    )
    from uncharted_installer.syscheck import run_checks, summarize

    failures = []
    warnings = []

    print(f"Uncharted PC Installer v{__version__} — self-test")
    print(f"platform: {platform_id()} | python: {sys.version.split()[0]}")

    try:
        folder = app_dir()
        print(f"app_dir: {folder} (ok)")
    except Exception as exc:  # noqa: BLE001
        failures.append(f"app_dir: {exc}")

    # GitHub API HANYA untuk self-test dan bisa rate-limit (403) — kegagalan
    # API di sini dilaporkan sebagai "tidak dapat diperiksa", BUKAN gagal.
    try:
        info = release_info()
        assert info["tag"] == PORT_TAG, info
        assert info["asset_name"] == PORT_ASSET, info
        assert info["asset_size"] == PORT_ASSET_SIZE, info
        print(
            f"rilis port: {info['tag']} | aset: {info['asset_name']} "
            f"({info['asset_size'] / 1024 / 1024:.1f} MB) (ok)"
        )
    except Exception as exc:  # noqa: BLE001
        warnings.append(f"rilis port (GitHub API): {exc}")
        print(f"rilis port: tidak dapat diperiksa (GitHub API: {exc})")

    try:
        info = release_info_fallback()
        assert info["tag"] == FALLBACK_TAG, info
        assert info["asset_name"] == FALLBACK_ASSET, info
        assert info["asset_size"] == FALLBACK_ASSET_SIZE, info
        print(
            f"rilis port cadangan: {info['tag']} | aset: {info['asset_name']} "
            f"({info['asset_size'] / 1024 / 1024:.1f} MB) (ok)"
        )
    except Exception as exc:  # noqa: BLE001
        warnings.append(f"rilis port cadangan (GitHub API): {exc}")
        print(f"rilis port cadangan: tidak dapat diperiksa (GitHub API: {exc})")

    try:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            lengkap = _make_mock_game_folder(
                root / "lengkap",
                ["eboot.bin", "sce_sys", "u1data", "u2data", "u3data",
                 "big2-ps4_Shipping.elf", "big3-ps4_Shipping.elf"],
            )
            hasil = validate_game_folder(lengkap)
            assert hasil["valid"] is True, hasil
            assert not hasil["missing_required"], hasil
            print("validasi folder game: folder lengkap lolos (ok)")

            kosong = root / "kosong"
            kosong.mkdir()
            hasil = validate_game_folder(kosong)
            assert hasil["valid"] is False, hasil
            assert set(hasil["missing_required"]) == set(REQUIRED_GAME_FILES), hasil
            print(
                "validasi folder game: folder kosong gagal dengan daftar "
                f"file hilang ({len(hasil['missing_required'])} item) (ok)"
            )

            tanpa_sce = _make_mock_game_folder(
                root / "tanpa_sce",
                ["eboot.bin", "u1data", "u2data", "u3data"],
            )
            hasil = validate_game_folder(tanpa_sce)
            assert hasil["valid"] is False, hasil
            assert "sce_sys" in hasil["missing_required"], hasil
            print("validasi folder game: folder tanpa sce_sys gagal (ok)")

            # Folder induk yang berisi subfolder game (kasus umum pengguna).
            induk = root / "induk" / "CUSA02343"
            induk.mkdir(parents=True, exist_ok=True)
            for name in ["eboot.bin", "sce_sys", "u1data", "u2data", "u3data"]:
                path = induk / name
                if name in ("sce_sys", "u1data", "u2data", "u3data"):
                    path.mkdir(exist_ok=True)
                else:
                    path.write_bytes(b"\x00" * 16)
            hasil = validate_game_folder(root / "induk")
            assert hasil["valid"] is True, hasil
            assert not hasil["missing_required"], hasil
            print(
                "validasi folder game: folder induk dengan subfolder game "
                "lolos (pencarian rekursif) (ok)"
            )

            # Game 2 level ke dalam masih ditemukan; 3 level tidak.
            dalam2 = root / "a" / "b" / "CUSA02343"
            dalam2.mkdir(parents=True, exist_ok=True)
            for name in ["eboot.bin", "sce_sys", "u1data", "u2data", "u3data"]:
                path = dalam2 / name
                if name in ("sce_sys", "u1data", "u2data", "u3data"):
                    path.mkdir(exist_ok=True)
                else:
                    path.write_bytes(b"\x00" * 16)
            hasil = validate_game_folder(root / "a")
            assert hasil["valid"] is True, hasil
            print("validasi folder game: game 2 level ke dalam lolos (ok)")
            dalam3 = root / "x" / "y" / "z" / "CUSA02343"
            dalam3.mkdir(parents=True, exist_ok=True)
            for name in ["eboot.bin", "sce_sys", "u1data", "u2data", "u3data"]:
                path = dalam3 / name
                if name in ("sce_sys", "u1data", "u2data", "u3data"):
                    path.mkdir(exist_ok=True)
                else:
                    path.write_bytes(b"\x00" * 16)
            hasil = validate_game_folder(root / "x")
            assert hasil["valid"] is False, hasil
            print("validasi folder game: game 3 level ke dalam tidak ditemukan (ok)")
    except Exception as exc:  # noqa: BLE001
        failures.append(f"validasi folder game: {exc}")

    try:
        checks = run_checks()
        ok, gagal, tidak_diketahui = summarize(checks)
        for check in checks:
            print(f"  syscheck [{check['status']}] {check['name']}: {check['detail']}")
        print(
            f"syscheck: {len(checks)} cek jalan tanpa crash "
            f"({ok} lolos, {gagal} gagal, {tidak_diketahui} tidak diketahui) (ok)"
        )
    except Exception as exc:  # noqa: BLE001
        failures.append(f"syscheck: {exc}")

    try:
        import tkinter  # noqa: F401
        print("tkinter: ok")
    except Exception as exc:  # noqa: BLE001
        failures.append(f"tkinter: {exc}")

    if failures:
        print("\nSELF-TEST GAGAL:")
        for failure in failures:
            print(f"  - {failure}")
        return 1
    if warnings:
        print("\nPeringatan (bukan kegagalan):")
        for warning in warnings:
            print(f"  - {warning}")
    print("\nSELF-TEST OK")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="uncharted_installer",
        description="Uncharted PC Installer — port native Uncharted untuk Windows",
    )
    parser.add_argument("--version", action="store_true", help="tampilkan versi")
    parser.add_argument("--self-test", action="store_true", help="tes mandiri tanpa GUI")
    args = parser.parse_args(argv)
    if args.version:
        from uncharted_installer import __version__
        print(f"Uncharted PC Installer {__version__}")
        return 0
    if args.self_test:
        return self_test()
    from uncharted_installer.app import run
    run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
