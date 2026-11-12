# Personal AI Assistant

Asisten AI percakapan ringan yang berjalan di Windows Command Prompt. Ajukan pertanyaan umum lewat CLI dengan jawaban streaming dan dukungan API chat yang kompatibel dengan OpenAI.

> Project ini adalah klien CLI independen yang menggunakan API penyedia model. Project tidak berafiliasi dengan OpenAI atau penyedia model lain. Akses model dan biaya API mengikuti ketentuan penyedia Anda.

## Fitur

- Percakapan AI dari CMD
- Jawaban tampil secara streaming
- Dukungan provider yang kompatibel dengan OpenAI Chat Completions
- API key, endpoint, dan model diatur melalui `.env`
- Konteks percakapan terbaru selama sesi berjalan
- Perintah `/help`, `/reset`, dan `/exit`
- Opsi build menjadi executable console Windows

## Persyaratan

- Windows 10 atau lebih baru
- Python 3.10 atau lebih baru untuk menjalankan source atau membuat executable
- API key dan endpoint dari provider yang kompatibel dengan OpenAI

## Menjalankan dari source

Buka CMD di folder project, lalu jalankan:

```bat
py -m venv .venv
.venv\Scripts\activate
py -m pip install -r requirements.txt
copy .env.example .env
```

Isi API key provider di `.env`, kemudian jalankan:

```bat
py -m personal_ai.chat
```

Atau klik dua kali `Personal AI.bat`.

## Konfigurasi

| Variabel | Fungsi | Default |
| --- | --- | --- |
| `ROUTER_API_KEY` | API key provider | Wajib diisi |
| `ROUTER_BASE_URL` | URL dasar API kompatibel OpenAI | `http://localhost:20128/v1` |
| `ROUTER_MODEL` | ID model yang diterima provider | `cx/gpt-6-luna[1m]` |

Default mengikuti konfigurasi awal 9Router. Ubah nilainya sesuai provider yang digunakan. Nama `ROUTER_*` dipertahankan agar konfigurasi lama tetap berlaku; endpoint dapat diarahkan ke layanan kompatibel lainnya.

## Perintah CLI

| Perintah | Fungsi |
| --- | --- |
| `/help` | Tampilkan daftar perintah |
| `/reset` | Hapus konteks percakapan |
| `/exit` | Keluar dari aplikasi |
| `Ctrl+C` | Hentikan sesi |

Konteks percakapan disimpan di memori dan tidak ditulis ke disk. Aplikasi mengirim maksimal 40 pesan percakapan terbaru beserta system prompt. Pesan yang lebih lama akan dikeluarkan dari konteks.

## Build executable Windows

Jalankan `build.bat` dari folder project. Script memasang dependensi build ke `.venv` dan membuat:

```text
dist\Personal AI.exe
```

Salin `.env` ke folder yang sama dengan executable sebelum menjalankannya. Executable membuka jendela console; bukan aplikasi GUI. Untuk pin ke taskbar, buat shortcut ke executable lalu pin shortcut tersebut. Windows mungkin menampilkan peringatan SmartScreen karena executable hasil build lokal tidak ditandatangani.

## Tes

```bat
.venv\Scripts\python.exe -m unittest discover -s tests -v
```

## Struktur project

```text
personal_ai/              Kode aplikasi
 tests/                   Tes standard library
Personal AI.bat           Jalankan dari source
build.bat                 Build executable console Windows
requirements.txt          Dependensi runtime
requirements-build.txt    Dependensi build
.env.example              Template konfigurasi
```

## Keamanan

- Jangan commit atau membagikan `.env`; file ini berisi API key dan dikecualikan melalui `.gitignore`.
- Jangan publikasikan executable bersama file `.env` yang berisi API key pribadi.
- Penggunaan API dapat dikenai biaya sesuai tarif dan limit provider.

## Lisensi

Project belum memiliki lisensi. Tambahkan file `LICENSE` sebelum memberi izin penggunaan ulang atau redistribusi.
