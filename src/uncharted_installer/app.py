"""Antarmuka grafis Uncharted PC Installer v1.1.0 (Tkinter, Bahasa Indonesia).

SATU LAYAR saja — tidak ada tab. Pengguna cukup:
  1. Pilih folder game (boleh kosong — port akan menanyakannya sendiri).
  2. Tentukan folder install.
  3. Tekan tombol besar "MAIN".
Semua langkah (cek sistem, unduh + ekstrak port, validasi folder game,
jalankan launcher) berjalan otomatis saat MAIN ditekan, dan bisa
dilanjutkan: langkah yang sudah selesai dilewati.

Operasi panjang berjalan di thread terpisah agar jendela tidak membeku;
progres dilaporkan lewat queue + after().
"""

import queue
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from . import __version__
from .config import (
    PORT_ASSET,
    PORT_TAG,
    load_settings,
    save_settings,
)
from .port import (
    find_launcher,
    install_port,
    launch_port,
    open_folder,
    validate_game_folder,
)
from .syscheck import FAIL, OK, UNKNOWN, run_checks, summarize


def _default_install_dir() -> str:
    if sys.platform == "win32":
        return r"C:\Games\UnchartedPC"
    return str(Path.home() / "UnchartedPC")


def _asset_path(name: str) -> Path | None:
    """Cari file aset (berfungsi saat dijalankan dari source maupun frozen)."""
    if getattr(sys, "frozen", False):
        base = Path(getattr(sys, "_MEIPASS", "."))
    else:
        base = Path(__file__).resolve().parents[2]
    candidate = base / "assets" / name
    return candidate if candidate.is_file() else None


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"Uncharted PC Installer v{__version__}")
        self.geometry("760x660")
        self.minsize(640, 580)
        icon = _asset_path("icon.png")
        if icon is not None:
            try:
                self._icon_photo = tk.PhotoImage(file=str(icon))
                self.iconphoto(True, self._icon_photo)
            except tk.TclError:
                pass

        self.settings = load_settings()
        self.queue: queue.Queue = queue.Queue()
        self._running = False

        self._build_widgets()
        self.after(100, self._poll_queue)

    # ------------------------------------------------------------------
    # Layout — satu layar
    # ------------------------------------------------------------------

    def _build_widgets(self):
        main = ttk.Frame(self, padding=12)
        main.pack(fill="both", expand=True)

        ttk.Label(
            main,
            text="Uncharted PC Installer",
            font=("TkDefaultFont", 16, "bold"),
        ).pack(anchor="w")
        ttk.Label(
            main,
            text="Port native Uncharted: The Nathan Drake Collection "
                 "(Uncharted 1, 2, 3) untuk Windows — BUKAN emulator.\n"
                 "Butuh dump PS4 Nathan Drake Collection milikmu sendiri. "
                 "Pilih folder game, tekan MAIN, langsung main.",
            wraplength=720,
            justify="left",
        ).pack(anchor="w", pady=(2, 10))

        # 1. Folder game
        ttk.Label(main, text="1. Folder Game", font=("TkDefaultFont", 11, "bold")).pack(anchor="w")
        row = ttk.Frame(main)
        row.pack(fill="x", pady=(2, 8))
        self.game_entry = ttk.Entry(row)
        self.game_entry.pack(side="left", fill="x", expand=True)
        self.game_entry.insert(0, self.settings.get("game_folder") or "")
        ttk.Button(
            row, text="Pilih Folder Game", command=self._pick_game_folder
        ).pack(side="left", padx=(6, 0))
        ttk.Label(
            main,
            text="Boleh dikosongkan — port akan meminta folder game sendiri "
                 "saat pertama main.",
            wraplength=720,
        ).pack(anchor="w", pady=(0, 8))

        # 2. Folder install
        ttk.Label(main, text="2. Folder Install", font=("TkDefaultFont", 11, "bold")).pack(anchor="w")
        row2 = ttk.Frame(main)
        row2.pack(fill="x", pady=(2, 8))
        self.install_entry = ttk.Entry(row2)
        self.install_entry.pack(side="left", fill="x", expand=True)
        self.install_entry.insert(
            0, self.settings.get("install_dir") or _default_install_dir()
        )
        ttk.Button(row2, text="Pilih...", command=self._pick_install_dir).pack(
            side="left", padx=(6, 0)
        )

        # Tombol MAIN
        self.play_btn = ttk.Button(
            main, text="▶  MAIN", command=self._start_main,
        )
        self.play_btn.pack(fill="x", pady=(4, 6))
        try:
            self.play_btn.configure(style="Big.TButton")
            style = ttk.Style(self)
            style.configure("Big.TButton", font=("TkDefaultFont", 14, "bold"))
        except tk.TclError:
            pass

        self.progress = ttk.Progressbar(main, length=400, mode="determinate")
        self.progress.pack(fill="x", pady=(0, 2))
        self.status_var = tk.StringVar(value="Siap. Pilih folder game, lalu tekan MAIN.")
        ttk.Label(main, textvariable=self.status_var, wraplength=720).pack(
            anchor="w", pady=(0, 6)
        )

        # Log besar
        ttk.Label(main, text="Log:").pack(anchor="w")
        log_frame = ttk.Frame(main)
        log_frame.pack(fill="both", expand=True)
        scrollbar = ttk.Scrollbar(log_frame)
        scrollbar.pack(side="right", fill="y")
        self.log_text = tk.Text(
            log_frame, height=14, wrap="word", state="disabled",
            yscrollcommand=scrollbar.set,
        )
        self.log_text.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.log_text.yview)

        # Tombol bawah
        bottom = ttk.Frame(main)
        bottom.pack(fill="x", pady=(8, 0))
        ttk.Button(bottom, text="Salin Log", command=self._copy_log).pack(
            side="left", padx=(0, 8)
        )
        ttk.Button(
            bottom, text="Buka Folder Install", command=self._open_install_folder
        ).pack(side="left")

    # ------------------------------------------------------------------
    # Log & queue
    # ------------------------------------------------------------------

    def log(self, message: str):
        self.log_text.configure(state="normal")
        self.log_text.insert("end", message + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _poll_queue(self):
        try:
            while True:
                kind, payload = self.queue.get_nowait()
                if kind == "log":
                    self.log(payload)
                elif kind == "status":
                    self.status_var.set(payload)
                elif kind == "progress":
                    downloaded, total = payload
                    if total:
                        self.progress["value"] = downloaded / total * 100
                elif kind == "progress_value":
                    self.progress["value"] = payload
                elif kind == "done":
                    self._running = False
                    self.play_btn.configure(state="normal")
                    self.status_var.set(payload)
        except queue.Empty:
            pass
        self.after(100, self._poll_queue)

    # ------------------------------------------------------------------
    # Pilihan folder
    # ------------------------------------------------------------------

    def _pick_game_folder(self):
        folder = filedialog.askdirectory(title="Pilih folder game (dump PS4 NDC)")
        if folder:
            self.game_entry.delete(0, "end")
            self.game_entry.insert(0, folder)
            self._save_settings()

    def _pick_install_dir(self):
        folder = filedialog.askdirectory(title="Pilih folder install port")
        if folder:
            self.install_entry.delete(0, "end")
            self.install_entry.insert(0, folder)
            self._save_settings()

    def _save_settings(self):
        self.settings["game_folder"] = self.game_entry.get().strip()
        self.settings["install_dir"] = self.install_entry.get().strip()
        save_settings(self.settings)

    def _copy_log(self):
        text = self.log_text.get("1.0", "end").strip()
        if not text:
            self.status_var.set("Log masih kosong — belum ada yang disalin.")
            return
        self.clipboard_clear()
        self.clipboard_append(text)
        self.status_var.set(
            "Log disalin ke clipboard. Tempelkan (Ctrl+V) bila diminta "
            "mengirim laporan error."
        )

    def _open_install_folder(self):
        install_dir = self.install_entry.get().strip()
        if not install_dir:
            messagebox.showwarning("Folder install", "Tentukan folder install dulu.")
            return
        ok, message = open_folder(install_dir)
        if not ok:
            messagebox.showwarning("Buka folder", message)
        self.log(message)

    # ------------------------------------------------------------------
    # Alur MAIN — otomatis, bisa dilanjutkan
    # ------------------------------------------------------------------

    def _start_main(self):
        if self._running:
            return
        self._save_settings()
        self._running = True
        self.play_btn.configure(state="disabled")
        self.progress["value"] = 0
        install_dir = self.install_entry.get().strip()
        game_folder = self.game_entry.get().strip()
        if not install_dir:
            self._running = False
            self.play_btn.configure(state="normal")
            messagebox.showwarning("Folder install", "Tentukan folder install dulu.")
            return
        threading.Thread(
            target=self._main_worker,
            args=(install_dir, game_folder),
            daemon=True,
        ).start()

    def _main_worker(self, install_dir: str, game_folder: str):
        q = self.queue
        q.put(("log", "=== MAIN dimulai ==="))
        try:
            # Langkah 1: cek sistem (info saja — tidak pernah memblokir).
            q.put(("status", "Langkah 1/4: memeriksa PC..."))
            q.put(("log", "Langkah 1/4: memeriksa PC (hanya info, tidak menghalangi)..."))
            try:
                checks = run_checks(install_dir or None)
                ok, gagal, tidak_diketahui = summarize(checks)
                for check in checks:
                    if check["status"] == FAIL:
                        q.put(("log", f"  Perhatian — {check['name']}: {check['detail']}"))
                        if check["tip"]:
                            q.put(("log", f"    Saran: {check['tip']}"))
                q.put(("log", f"Cek sistem selesai: {ok} lolos, {gagal} perlu perhatian, "
                              f"{tidak_diketahui} tidak dapat diperiksa."))
                if gagal:
                    q.put(("log", "  (Yang 'perlu perhatian' hanya peringatan — "
                                  "MAIN tetap lanjut.)"))
            except Exception as exc:  # noqa: BLE001 - cek sistem tidak boleh menghentikan MAIN
                q.put(("log", f"Cek sistem tidak bisa jalan ({exc}) — lanjut saja."))
            q.put(("progress_value", 10))

            # Langkah 2: unduh + ekstrak port (lewati bila sudah terpasang).
            q.put(("status", "Langkah 2/4: menyiapkan port..."))
            existing = find_launcher(install_dir)
            if existing is not None:
                q.put(("log", f"Langkah 2/4: port sudah terpasang ({existing.name}) — lewati unduh."))
            else:
                q.put(("log", f"Langkah 2/4: mengunduh port {PORT_TAG} ({PORT_ASSET})..."))
                try:
                    exe = install_port(
                        install_dir,
                        progress_cb=lambda d, t: q.put(("progress", (d, t))),
                        log=lambda m: q.put(("log", m)),
                    )
                    q.put(("log", f"Port terpasang: {exe}"))
                except Exception as exc:  # noqa: BLE001 - tulis error + cara lanjut
                    q.put(("log", f"GAGAL mengunduh port: {exc}"))
                    q.put(("log", "Yang harus dilakukan: periksa koneksi internet, "
                                  "lalu tekan MAIN lagi untuk melanjutkan."))
                    q.put(("status", "Unduhan port gagal — tekan MAIN lagi untuk melanjutkan."))
                    q.put(("done", "Unduhan port gagal — tekan MAIN lagi."))
                    return
            q.put(("progress_value", 60))

            # Langkah 3: validasi folder game (peringatan saja — tidak memblokir).
            q.put(("status", "Langkah 3/4: memeriksa folder game..."))
            if game_folder:
                q.put(("log", f"Langkah 3/4: memeriksa folder game: {game_folder}"))
                try:
                    result = validate_game_folder(game_folder)
                    q.put(("log", f"  {result['detail']}"))
                    if not result["valid"]:
                        q.put(("log", "  (Ini hanya peringatan — tetap lanjut. Port akan "
                                      "meminta folder game yang benar saat pertama main.)"))
                except Exception as exc:  # noqa: BLE001
                    q.put(("log", f"  Folder game tidak bisa diperiksa ({exc}) — lanjut saja."))
            else:
                q.put(("log", "Langkah 3/4: folder game belum dipilih — nanti pilih "
                              "di dalam port saat pertama main."))
            q.put(("progress_value", 90))

            # Langkah 4: jalankan launcher port.
            q.put(("status", "Langkah 4/4: membuka game..."))
            q.put(("log", "Langkah 4/4: membuka launcher port..."))
            ok, message = launch_port(install_dir)
            if ok:
                q.put(("log", message))
                q.put(("log", "Selamat bermain!"))
                q.put(("progress_value", 100))
                q.put(("status", "Game dibuka."))
                q.put(("done", "Game dibuka — selamat bermain!"))
            else:
                q.put(("log", f"GAGAL membuka game: {message}"))
                q.put(("log", "Yang harus dilakukan: tekan MAIN lagi. Bila masih gagal, "
                              "tekan 'Salin Log' dan kirimkan log-nya."))
                q.put(("status", "Gagal membuka game — tekan MAIN lagi."))
                q.put(("done", "Gagal membuka game — tekan MAIN lagi."))
        except Exception as exc:  # noqa: BLE001 - jangan pernah crash tanpa pesan
            q.put(("log", f"Terjadi kesalahan tak terduga: {exc}"))
            q.put(("log", "Yang harus dilakukan: tekan MAIN lagi. Bila masih gagal, "
                          "tekan 'Salin Log' dan kirimkan log-nya."))
            q.put(("status", "Terjadi kesalahan — tekan MAIN lagi."))
            q.put(("done", "Terjadi kesalahan — tekan MAIN lagi."))


def run():
    app = App()
    app.mainloop()
