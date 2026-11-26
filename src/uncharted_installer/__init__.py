"""Uncharted PC Installer — mainkan Uncharted: The Nathan Drake Collection
(Uncharted 1, 2, 3) secara native di Windows.

Ini BUKAN emulator. Aplikasi ini adalah installer/launcher untuk port native
open-source Uncharted PC (Supermedo/uncharted_pc, GPL v2+), yang merupakan
port dari versi PlayStation 4 "Uncharted: The Nathan Drake Collection".

Penjelasan jujur: kode game PS3 tidak bisa jalan native di PC — PS3 memakai
CPU Cell (PowerPC) dan GPU RSX yang arsitekturnya berbeda total dari PC
x86-64. Yang bisa jalan native di PC adalah port dari versi PS4-nya, karena
PS4 sudah memakai CPU/GPU x86-64 (AMD Jaguar + GCN), sehingga kodenya bisa
dikompilasi ulang untuk Windows. Port inilah yang diunduh dan dipasang oleh
aplikasi ini.

Aplikasi ini TIDAK menyertakan file game apa pun. Pengguna wajib memakai
dump PS4 "Uncharted: The Nathan Drake Collection" miliknya sendiri
(mis. CUSA02343 / CUSA02320), termasuk update 1.02 bila ada.
"""

__version__ = "1.1.0"
__app_name__ = "Uncharted PC Installer"
