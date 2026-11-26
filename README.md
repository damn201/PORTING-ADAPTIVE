# Uncharted PC Installer v1.1.0

Installer/launcher Windows untuk memainkan **Uncharted: The Nathan Drake Collection
(Uncharted 1, 2, 3) secara native di PC** — **BUKAN emulator**.

Aplikasi ini memasang port native open-source **Uncharted PC**
([Supermedo/uncharted_pc](https://github.com/Supermedo/uncharted_pc), v0.3.15,
lisensi GPL v2 atau lebih baru), lalu membantumu memainkan gamenya dengan
satu klik.

## Baru di v1.1.0 — UI satu layar, tinggal MAIN

v1.0.0 memakai 5 tab yang tiap langkahnya bisa gagal dengan pesan teknis.
v1.1.0 menggantinya dengan **satu layar saja**:

1. Pilih **Folder Game** (boleh dikosongkan — port akan menanyakannya
   sendiri saat pertama main).
2. Tentukan **Folder Install** (default `C:\Games\UnchartedPC`).
3. Tekan tombol besar **▶ MAIN** — selesai. Semua langkah berjalan
   otomatis dan berurutan: cek sistem → unduh + ekstrak port → periksa
   folder game → buka launcher port.

Semua langkah **bisa dilanjutkan**: langkah yang sudah selesai dilewati
(mis. port yang sudah terpasang tidak diunduh ulang). Bila ada langkah
gagal, log menulis error persisnya + "yang harus dilakukan" dalam Bahasa
Indonesia yang sederhana — tekan MAIN lagi untuk melanjutkan. Tombol
**Salin Log** menyalin seluruh log ke clipboard agar mudah dikirim bila
ada error.

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

Aplikasi ini punya cek sistem, tetapi hasilnya hanya peringatan —
**tidak pernah memblokir tombol MAIN**. Syarat seperti instruksi CPU
(AVX, F16C, BMI1, MOVBE, LZCNT) hanya ditulis di log bila tidak terpenuhi.

## File game yang dibutuhkan

Aplikasi ini **TIDAK menyertakan file game apa pun**. Kamu wajib memakai
dump PS4 *Uncharted: The Nathan Drake Collection* **milikmu sendiri**
(mis. CUSA02343 / CUSA02320 / CUSA02344), idealnya dengan **update 1.02**.

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

**Validasi longgar (v1.1.0):** aplikasi mencari file wajib secara
rekursif sampai 2 level ke dalam folder yang dipilih — jadi boleh memilih
folder induk yang berisi subfolder game. Dan bila folder tetap tidak
lengkap, itu **hanya peringatan, bukan blokir**: aplikasi tetap membuka
port, dan port akan meminta kamu memilih folder game yang benar saat
pertama main (memang begitu cara port ini dirancang).

## Cara pakai

1. Jalankan `UnchartedPCInstaller.exe`.
2. **Folder Game** — pilih folder dump PS4 Nathan Drake Collection
   milikmu (boleh dikosongkan).
3. **Folder Install** — default `C:\Games\UnchartedPC`.
4. Tekan **▶ MAIN**. Aplikasi otomatis: memeriksa PC (peringatan saja),
   mengunduh + mengekstrak port (dilewati bila sudah terpasang),
   memeriksa folder game (peringatan saja), lalu membuka launcher port.
5. Di dalam port: pilih folder game bila diminta, pilih game
   (Uncharted 1 / 2 / 3), lalu tekan **PLAY**.

Bila ada langkah yang gagal, baca log-nya lalu tekan **MAIN** lagi —
langkah yang sudah selesai tidak diulang. Bila masih gagal, tekan
**Salin Log** dan kirimkan log-nya.

Cara pakai portnya secara manual (tanpa installer ini) juga sama:
ekstrak `uncharted-windows.zip`, jalankan `Uncharted.exe`, pilih folder
game, pilih game, tekan PLAY.

## Port alternatif (fallback otomatis)

Selain port utama (Supermedo/uncharted_pc v0.3.15), installer v1.1.0
memiliki fallback **otomatis** ke port **BilalReloaded** v0.8.6
([bc160201983/Uncharted-The-Nathan-Drake-Collection-PC-port](https://github.com/bc160201983/Uncharted-The-Nathan-Drake-Collection-PC-port),
873 bintang, aset `Uncharted-windows.zip` 115,9 MB = 121.477.657 byte,
launcher `Uncharted Launcher.exe`, terverifikasi 26 Nov 2026, lisensi
tidak tercantum di GitHub). Bila unduhan Supermedo gagal (mis. 404 atau
koneksi putus), installer otomatis mencoba BilalReloaded — kamu tidak
perlu melakukan apa-apa. Unduhan juga dicoba ulang sampai 3 kali bila
koneksi gagal/terputus, dan ukuran file hasil unduhan diverifikasi.

Alur normal **tidak pernah memakai GitHub API** — unduhan memakai URL
yang sudah ditulis di kode. API GitHub hanya dipakai oleh `--self-test`,
dan kegagalan API di sana (mis. rate-limit 403) dilaporkan sebagai
"tidak dapat diperiksa", bukan kegagalan.

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

Tes ini memeriksa: rilis port di GitHub bisa dijangkau (kegagalan API,
mis. rate-limit, hanya dilaporkan "tidak dapat diperiksa", bukan gagal),
validasi folder game pada folder tiruan (termasuk pencarian rekursif),
dan cek sistem tidak crash. Unit test:

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
