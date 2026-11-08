# 🏛️ THE INSTITUTE — Esports Broadcast & Campus Community Bot

Automated 24/7 Discord broadcast hub, match prediction engine, and party-finding (LFG) system for **MPL Indonesia** & **VCT (Valorant Champions Tour)** communities.

![Python](https://img.shields.io/badge/Python-3.13-3776AB?style=flat-square&logo=python&logoColor=white)
![discord.py](https://img.shields.io/badge/discord.py-2.3%2B-5865F2?style=flat-square&logo=discord&logoColor=white)
![MySQL](https://img.shields.io/badge/MySQL-8.0-4479A1?style=flat-square&logo=mysql&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Containerized-2496ED?style=flat-square&logo=docker&logoColor=white)
![Railway](https://img.shields.io/badge/Hosted_on-Railway_24%2F7-0B0D0E?style=flat-square&logo=railway&logoColor=white)
![License](https://img.shields.io/badge/License-GPLv3-DC2626?style=flat-square&logo=gnu&logoColor=white?style=flat-square)

---

## What This Does

Managing campus esports watch parties manually requires constant schedule checking, manual poll creation, and repetitive score updates across multiple channels. **THE INSTITUTE Bot (v2.8)** solves this by scraping official **MPL ID**, **Liquipedia**, and **VLR.gg** feeds every 5 minutes, automatically routing interactive match cards to 7 dedicated Discord channels, and rewarding students with XP and Coins when their match predictions hit.

---

## Key Features

- **📡 Multi-Source Live Schedule & Result Sync**: Aggregates 7-day upcoming schedules, live match states, and verified final scores from `id-mpl.com`, Liquipedia MediaWiki APIs, and `vlr.gg`.
- **🗳️ Interactive 1-Click Match Predictions**: Persistent `discord.ui.View` buttons (`🔹 Vote Team A` / `🔸 Vote Team B`) with real-time community vote progress bars.
- **🔒 Idempotent Multi-Channel State Machine**: Uses database state flags (`0 = Unannounced`, `1 = Broadcasted to Watch Party/Predictions`, `2 = Settled in Results`) so restarts or resyncs never spam duplicate cards.
- **💰 Automated Prediction Payouts & Campus Economy**: Automatically settles finished matches and credits `+75 XP`, `+100 Coins`, and `+1 Esports Point` to accurate predictors.
- **🎮 Interactive Looking-For-Group (`/lfg`)**: 5-slot dynamic squad recruitment cards for Mobile Legends and Valorant that auto-lock and notify members once a party is full.
- **🛡️ Self-Auditing Channel Diagnostics (`/verify_channels`)**: Read-only permission and database health auditor across all 7 target esports channels.

---

## Tech Stack

- **Runtime**: **Python 3.13 (`discord.py >= 2.3.0`)** — Native support for Discord Slash Commands (`app_commands`), persistent UI views, and async background tasks.
- **Database**: **MySQL 8.0 (`MySQLAutoAdapter`)** — Custom connection wrapper with automatic reconnection, SQLite-to-MySQL parameter translation (`?` to `%s`), and environment fallback between local Docker and Railway Private Networking.
- **Containerization**: **Docker (`python:3.13-slim`)** — Lightweight image ensuring identical runtime behavior between local Windows development and cloud deployment.
- **Cloud Hosting**: **Railway (24/7 PaaS)** — Zero-downtime cloud container execution linked via private internal networking (`mysql.railway.internal`) to managed MySQL.

---

## How It Works

### 1. Scraper & Sync Pipeline (`sync_external_schedules`)
Every 5 minutes, an asynchronous background loop (`@tasks.loop(minutes=5)`) executes non-blocking HTTP parsers via `asyncio.to_thread()`:
1. **MPL Parser (`parse_mpl_schedule`)**: Extracts verified match fixtures and scores from the official MPL ID schedule page alongside Liquipedia's MediaWiki API.
2. **Valorant Parser (`parse_vlr_matches`)**: Scrapes live VCT match cards and completed scores directly from `vlr.gg/matches` and `vlr.gg/matches/results` with VCT Tier-1 team prioritization and JSON API fallback.
3. **Quota Isolation**: Announcement counters (`announced_upcoming` & `announced_results`) reset per game provider so MPL updates never starve Valorant announcements.

### 2. Channel Routing Matrix

| Category | Target Channels | Trigger State | Database Flag |
| :--- | :--- | :--- | :--- |
| **MPL Broadcast & Poll** | `#📺・mpl-watch-party`, `#🔮・mpl-predictions` | `UPCOMING` / `LIVE` (Next 7 Days) | `channel_id = 1` |
| **MPL Official Results** | `#🏆・mpl-results`, `#📜・match-results` | `FINISHED` (`score_a > 0` or `score_b > 0`) | `channel_id = 2` |
| **VCT Broadcast & Poll** | `#📺・valorant-watch-party`, `#🔮・valorant-predictions` | `UPCOMING` / `LIVE` (Next 7 Days) | `channel_id = 1` |
| **VCT Official Results** | `#🏆・valorant-results`, `#📜・match-results` | `FINISHED` (`score_a > 0` or `score_b > 0`) | `channel_id = 2` |
| **Squad Finder & Ranks** | `#🔎・looking-for-group`, `#📊・leaderboards` | On-demand via `/lfg` & `/refresh_leaderboard` | Stateless / `users` |

---

## Getting Started

### Prerequisites
- Python 3.11+ or Docker Desktop
- A Discord Bot Application with **Server Members Intent** and **Message Content Intent** enabled in the [Discord Developer Portal](https://discord.com/developers/applications)
- MySQL 8.0 instance (Local Docker or Railway MySQL)

### 1. Clone & Configure Environment
```bash
git clone [https://github.com/YOUR_USERNAME/the-institute-discord-bot.git](https://github.com/YOUR_USERNAME/the-institute-discord-bot.git)
cd the-institute-discord-bot
cp .env.example .env