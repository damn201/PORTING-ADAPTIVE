# Uncharted PC Installer

Installer/launcher Windows untuk memainkan **Uncharted: The Nathan Drake Collection
(Uncharted 1, 2, 3) secara native di PC** — **BUKAN emulator**.

Aplikasi ini memasang port native open-source **Uncharted PC**
([Supermedo/uncharted_pc](https://github.com/Supermedo/uncharted_pc), v0.3.15,
lisensi GPL v2 atau lebih baru), lalu membantumu memeriksa PC, memilih folder
game, dan memainkan gamenya dengan satu klik.

## Penjelasan jujur: kenapa ini bisa native?

Kode game **PS3 tidak bisa jalan native di PC**. PS3 memakai CPU Cell
(PowerPC) dan GPU RSX — arsitekturnya berbeda total dari PC x86-64, sehingga
game PS3 hanya bisa dimainkan lewat emulator (mis. RPCS3).

Yang bisa jalan native di PC adalah port dari versi **PS4**-nya, yaitu
*Uncharted: The Nathan Drake Collection*. PS4 sudah memakai CPU/GPU x86-64
(AMD Jaguar + GCN), sehingga kodenya bisa dikompilasi ulang untuk Windows.
Port inilah yang diunduh dan dipasang oleh aplikasi ini. Jadi yang kamu
mainkan adalah Uncharted 1, 2, dan 3 versi PS4 (Nathan Drake Collection),
yang berjalan native di Windows — tanpa emulator.

## Syarat PC

(Dari README port.)

- Windows 10 (1903+) atau Windows 11 64-bit
- CPU Intel Core generasi ke-3+ / AMD Ryzen / AMD FX
  (butuh instruksi AVX, F16C, BMI1, MOVBE, LZCNT)
- GPU dengan **Vulkan 1.3** + driver terbaru
- **VRAM 6 GB direkomendasikan** (kartu 4 GB bisa crash)
- RAM bebas ~8 GB
- Ruang disk kosong minimal **50 GB** (port 117 MB + game ~44 GB)

Aplikasi ini punya tab **Cek Sistem** yang memeriksa semua syarat di atas
dan memberi tahu mana yang lolos, gagal, atau tidak dapat diperiksa.

## File game yang dibutuhkan

Aplikasi ini **TIDAK menyertakan file game apa pun**. Kamu wajib memakai
dump PS4 *Uncharted: The Nathan Drake Collection* **milikmu sendiri**
(mis. CUSA02343 / CUSA02320), idealnya dengan **update 1.02**.

Folder game yang valid wajib berisi:

```
eboot.bin
sce_sys/
u1data/
u2data/
u3data/
```

Idealnya juga ada:

```
big2-ps4_Shipping.elf
big3-ps4_Shipping.elf
```

Tab **Game** di aplikasi akan memvalidasi folder yang kamu pilih dan
menampilkan file yang hilang bila ada.

## Cara pakai

1. Jalankan `UnchartedPCInstaller.exe`.
2. **Cek Sistem** — tekan "Jalankan Cek Sistem", pastikan semuanya lolos.
3. **Unduh Port** — pilih folder install, tekan "Unduh Port" (117,3 MB),
   lalu "Verifikasi" untuk memastikan `Uncharted.exe` ada.
4. **Game** — pilih folder dump PS4 Nathan Drake Collection milikmu,
   tekan "Validasi Folder Game", lalu "Simpan".
5. **Main** — tekan **MAIN**. Di dalam port: pilih folder game, pilih game
   (Uncharted 1 / 2 / 3), lalu tekan **PLAY**.

Cara pakai portnya secara manual (tanpa installer ini) juga sama:
ekstrak `uncharted-windows.zip`, jalankan `Uncharted.exe`, pilih folder
game, pilih game, tekan PLAY.

## Port alternatif

Selain port utama (Supermedo/uncharted_pc v0.3.15), ada port lain yang
juga berbasis Nathan Drake Collection:

- **BilalReloaded** v0.8.6 — aset `Uncharted-windows.zip` (115,9 MB),
  launcher `Uncharted Launcher.exe`, membutuhkan folder CUSA02344 +
  update 1.02.

Installer ini hanya memakai port Supermedo; port BilalReloaded dicantumkan
di sini sebagai alternatif untuk dicoba sendiri bila port utama bermasalah
di PC kamu.

## Build sendiri

### Windows (hasil: `dist\UnchartedPCInstaller.exe`)

```bat
build\build-windows.bat
```

Syarat: Python 3.12 terpasang dan ada di PATH. Semua DLL runtime (Tk/Tcl)
terbundel di dalam exe.

### GitHub Actions

Push tag `v*` (mis. `v1.0.0`) atau jalankan manual via tab Actions.
Runner `windows-latest` membangun exe dan mengunggah artifact bernama
**UnchartedPCInstaller-Windows**.

### Tes mandiri (tanpa GUI)

```sh
PYTHONPATH=src python -m uncharted_installer --self-test
```

Tes ini memeriksa: rilis port di GitHub bisa dijangkau, validasi folder
game pada folder tiruan, dan cek sistem tidak crash. Unit test:

```sh
PYTHONPATH=src python -m unittest discover -s tests -v
```

## Lisensi

- **Uncharted PC Installer** (aplikasi ini): kode installer/launcher di sini
  bebas dipakai untuk keperluan pribadi.
- **Port Uncharted PC** (Supermedo/uncharted_pc): GPL v2 atau lebih baru.
- **Uncharted, Nathan Drake, dan aset game** adalah milik Sony Interactive
  Entertainment / Naughty Dog. Aplikasi ini tidak menyertakan, mendistribusikan,
  atau menyediakan file game, key, atau konten berhak cipta apa pun —
  gunakan hanya dump PS4 milikmu sendiri.
