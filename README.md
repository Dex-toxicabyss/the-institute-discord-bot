# THE INSTITUTE — Esports Broadcast & Campus Community Bot (v2.8)

Bot Discord 24/7 untuk sinkronisasi jadwal, sistem prediksi interaktif, rekap skor resmi MPL ID & VCT (Valorant), serta pencarian party mabar (*Looking For Group*) di server **Gasak Galo**.

## What This Does

Mengotomatiskan penarikan jadwal pertandingan 7 hari ke depan dan hasil akhir dari situs resmi MPL ID, Liquipedia API, dan VLR.gg ke 7 channel khusus tanpa duplikasi pesan. Dilengkapi kartu *Broadcast Center* dengan tombol voting 1-klik, pembagian hadiah otomatis (`+75 XP` & `+100 Coins`) bagi penebak jitu, serta fitur pencari skuad mabar (`/lfg`) dan papan klasemen kampus (`/leaderboard`).

## Tech Stack

- **Runtime**: Python 3.13 (`discord.py >= 2.3.0`)
- **Database**: MySQL 8.0 (`mysql-connector-python` / `pymysql`) untuk persistensi jadwal, *state flag* pengumuman (`channel_id`), voting, dan profil mahasiswa
- **Deployment**: Docker (`python:3.13-slim`) & Railway Cloud 24/7

## Channel Routing Architecture

| Kategori | Channel Target | Fungsi & State |
| :--- | :--- | :--- |
| **MPL Schedule & Poll** | `#📺・mpl-watch-party`, `#🔮・mpl-predictions` | Kartu jadwal 7 hari & tombol Vote (`channel_id = 1`) |
| **MPL Official Results** | `#🏆・mpl-results`, `#📜・match-results` | Kartu skor akhir & pencairan XP/Coins (`channel_id = 2`) |
| **VCT Schedule & Poll** | `#📺・valorant-watch-party`, `#🔮・valorant-predictions` | Kartu jadwal VCT 7 hari & tombol Vote (`channel_id = 1`) |
| **VCT Official Results** | `#🏆・valorant-results`, `#📜・match-results` | Kartu skor akhir VCT & pencairan XP/Coins (`channel_id = 2`) |
| **Community & Ranks** | `#🔎・looking-for-group`, `#📊・leaderboards` | Kartu party mabar interaktif & klasemen Hall of Fame |

## Getting Started

### 1. Persiapan Environment
Salin `.env.example` menjadi `.env` dan isi kredensial yang sesuai (jangan pernah meng-commit `.env` ke Git):

```bash
cp .env.example .env