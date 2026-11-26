"""Unit test port: pencarian launcher (dua nama) dan retry unduhan."""

import io
import sys
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from uncharted_installer.config import (  # noqa: E402
    FALLBACK_LAUNCHER_EXE,
    LAUNCHER_EXE,
)
from uncharted_installer.port import download_port, find_launcher  # noqa: E402


class _FakeResponse:
    """Tiruan objek respons urllib: context manager + headers + read()."""

    def __init__(self, data: bytes):
        self._buf = io.BytesIO(data)
        self.headers = {"Content-Length": str(len(data))}

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def read(self, size=-1):
        return self._buf.read(size)


class TestFindLauncher(unittest.TestCase):
    def test_mengenali_uncharted_exe(self):
        with tempfile.TemporaryDirectory() as tmp:
            exe = Path(tmp) / LAUNCHER_EXE
            exe.write_bytes(b"MZ")
            self.assertEqual(find_launcher(tmp), exe)

    def test_mengenali_uncharted_launcher_exe_bilal(self):
        with tempfile.TemporaryDirectory() as tmp:
            exe = Path(tmp) / FALLBACK_LAUNCHER_EXE
            exe.write_bytes(b"MZ")
            self.assertEqual(find_launcher(tmp), exe)

    def test_mengenali_launcher_di_subfolder(self):
        with tempfile.TemporaryDirectory() as tmp:
            sub = Path(tmp) / "bin"
            sub.mkdir()
            exe = sub / FALLBACK_LAUNCHER_EXE
            exe.write_bytes(b"MZ")
            self.assertEqual(find_launcher(tmp), exe)

    def test_supermedo_didahulukan_bila_keduanya_ada(self):
        with tempfile.TemporaryDirectory() as tmp:
            utama = Path(tmp) / LAUNCHER_EXE
            utama.write_bytes(b"MZ")
            cadangan = Path(tmp) / FALLBACK_LAUNCHER_EXE
            cadangan.write_bytes(b"MZ")
            self.assertEqual(find_launcher(tmp), utama)

    def test_tidak_ada_launcher_mengembalikan_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(find_launcher(tmp))
            self.assertIsNone(find_launcher(Path(tmp) / "tidak-ada"))


class TestDownloadRetry(unittest.TestCase):
    def test_retry_dua_kali_gagal_lalu_berhasil(self):
        data = b"isi-zip-tiruan"
        calls = {"n": 0}

        def fake_urlopen(req, timeout=None):
            calls["n"] += 1
            if calls["n"] <= 2:
                raise urllib.error.URLError("koneksi putus (tiruan)")
            return _FakeResponse(data)

        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "port.zip"
            with mock.patch(
                "uncharted_installer.port.urllib.request.urlopen",
                side_effect=fake_urlopen,
            ), mock.patch(
                "uncharted_installer.port.time.sleep", return_value=None
            ):
                result = download_port(
                    "https://example.invalid/port.zip",
                    dest=dest,
                    expected_size=len(data),
                    retries=3,
                )
            self.assertEqual(result, dest)
            self.assertEqual(dest.read_bytes(), data)
            self.assertEqual(calls["n"], 3)

    def test_gagal_setelah_3_kali_percobaan(self):
        calls = {"n": 0}

        def fake_urlopen(req, timeout=None):
            calls["n"] += 1
            raise urllib.error.URLError("koneksi putus (tiruan)")

        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "port.zip"
            with mock.patch(
                "uncharted_installer.port.urllib.request.urlopen",
                side_effect=fake_urlopen,
            ), mock.patch(
                "uncharted_installer.port.time.sleep", return_value=None
            ):
                with self.assertRaises(RuntimeError) as ctx:
                    download_port(
                        "https://example.invalid/port.zip",
                        dest=dest,
                        expected_size=10,
                        retries=3,
                    )
            self.assertIn("3 kali percobaan", str(ctx.exception))
            self.assertEqual(calls["n"], 3)
            self.assertFalse(dest.exists())  # file sebagian dihapus

    def test_ukuran_tidak_cocok_ditolak(self):
        data = b"terlalu-pendek"
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "port.zip"
            with mock.patch(
                "uncharted_installer.port.urllib.request.urlopen",
                return_value=_FakeResponse(data),
            ), mock.patch(
                "uncharted_installer.port.time.sleep", return_value=None
            ):
                with self.assertRaises(RuntimeError) as ctx:
                    download_port(
                        "https://example.invalid/port.zip",
                        dest=dest,
                        expected_size=99999,
                        retries=3,
                    )
            self.assertIn("Ukuran file tidak cocok", str(ctx.exception))
            self.assertFalse(dest.exists())


if __name__ == "__main__":
    unittest.main()
