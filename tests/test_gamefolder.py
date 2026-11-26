"""Unit test validasi folder game (dump PS4 Nathan Drake Collection)."""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from uncharted_installer.config import REQUIRED_GAME_FILES  # noqa: E402
from uncharted_installer.port import validate_game_folder  # noqa: E402

COMPLETE = [
    "eboot.bin", "sce_sys", "u1data", "u2data", "u3data",
    "big2-ps4_Shipping.elf", "big3-ps4_Shipping.elf",
]


def make_folder(root: Path, names: list[str]) -> Path:
    folder = root / "CUSA02343"
    folder.mkdir(parents=True, exist_ok=True)
    for name in names:
        path = folder / name
        if name in ("sce_sys", "u1data", "u2data", "u3data"):
            path.mkdir(exist_ok=True)
        else:
            path.write_bytes(b"\x00" * 16)
    return folder


class TestValidateGameFolder(unittest.TestCase):
    def test_folder_lengkap_lolos(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = make_folder(Path(tmp), COMPLETE)
            hasil = validate_game_folder(folder)
            self.assertTrue(hasil["valid"])
            self.assertEqual(hasil["missing_required"], [])
            self.assertEqual(hasil["missing_recommended"], [])

    def test_folder_kosong_gagal_dengan_daftar_hilang(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "kosong"
            folder.mkdir()
            hasil = validate_game_folder(folder)
            self.assertFalse(hasil["valid"])
            self.assertEqual(
                set(hasil["missing_required"]), set(REQUIRED_GAME_FILES)
            )

    def test_folder_tanpa_sce_sys_gagal(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = make_folder(
                Path(tmp), ["eboot.bin", "u1data", "u2data", "u3data"]
            )
            hasil = validate_game_folder(folder)
            self.assertFalse(hasil["valid"])
            self.assertIn("sce_sys", hasil["missing_required"])

    def test_folder_tanpa_file_elf_hanya_peringatan(self):
        """File .elf yang hilang tidak membuat folder tidak valid."""
        with tempfile.TemporaryDirectory() as tmp:
            folder = make_folder(
                Path(tmp),
                ["eboot.bin", "sce_sys", "u1data", "u2data", "u3data"],
            )
            hasil = validate_game_folder(folder)
            self.assertTrue(hasil["valid"])
            self.assertEqual(
                set(hasil["missing_recommended"]),
                {"big2-ps4_Shipping.elf", "big3-ps4_Shipping.elf"},
            )

    def test_folder_tidak_ada_gagal(self):
        with tempfile.TemporaryDirectory() as tmp:
            hasil = validate_game_folder(Path(tmp) / "tidak-ada")
            self.assertFalse(hasil["valid"])
            self.assertEqual(
                set(hasil["missing_required"]), set(REQUIRED_GAME_FILES)
            )

    def test_folder_induk_dengan_subfolder_game_lolos(self):
        """Pengguna memilih folder induk berisi subfolder game."""
        with tempfile.TemporaryDirectory() as tmp:
            induk = Path(tmp) / "induk"
            make_folder(induk, COMPLETE)
            hasil = validate_game_folder(induk)
            self.assertTrue(hasil["valid"])
            self.assertEqual(hasil["missing_required"], [])
            self.assertIn("eboot.bin", hasil["found_at"])

    def test_game_dua_level_ke_dalam_lolos(self):
        with tempfile.TemporaryDirectory() as tmp:
            dalam = Path(tmp) / "a" / "b"
            make_folder(dalam, COMPLETE)
            hasil = validate_game_folder(Path(tmp) / "a")
            self.assertTrue(hasil["valid"])

    def test_game_tiga_level_ke_dalam_tidak_ditemukan(self):
        with tempfile.TemporaryDirectory() as tmp:
            dalam = Path(tmp) / "x" / "y" / "z"
            make_folder(dalam, COMPLETE)
            hasil = validate_game_folder(Path(tmp) / "x")
            self.assertFalse(hasil["valid"])
            self.assertEqual(
                set(hasil["missing_required"]), set(REQUIRED_GAME_FILES)
            )


if __name__ == "__main__":
    unittest.main()
