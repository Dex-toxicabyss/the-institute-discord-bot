import os
import random
import mysql.connector
import time
import re
import json
import asyncio
import urllib.request
import urllib.error
from html.parser import HTMLParser
from datetime import datetime, timezone, timedelta

import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv

# =========================================================
# THE INSTITUTE v2.8 — COMPETITIVE ESPORTS & CAMPUS ENGINE
# =========================================================

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID", "0"))

if not TOKEN or not GUILD_ID:
    raise RuntimeError("DISCORD_TOKEN and GUILD_ID must exist in .env")

GUILD = discord.Object(id=GUILD_ID)

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

# =========================================================
# DATABASE (MYSQL DOCKER AUTO-ADAPTER)
# =========================================================

class MySQLAutoAdapter:
    def __init__(self):
        self.conn = mysql.connector.connect(
            host=os.getenv("DB_HOST", "host.docker.internal"),
            port=int(os.getenv("DB_PORT", "3307")),
            user=os.getenv("DB_USER", "root"),
            password=os.getenv("DB_PASSWORD", "root"),
            database=os.getenv("DB_NAME", "the_institute"),
            autocommit=False
        )

    def ping(self):
        if not self.conn.is_connected():
            self.conn.reconnect(attempts=3, delay=2)

    def cursor(self):
        self.ping()
        return MySQLCursorWrapper(self.conn.cursor(dictionary=True))

    def commit(self):
        self.ping()
        self.conn.commit()


class MySQLCursorWrapper:
    def __init__(self, real_cursor):
        self.cur = real_cursor

    def execute(self, sql, params=None):
        sql_mysql = sql.replace("?", "%s")
        if "ON CONFLICT" in sql_mysql:
            sql_mysql = """
                INSERT INTO votes(match_id, user_id, choice)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE choice=VALUES(choice)
            """
        return self.cur.execute(sql_mysql, params or ())

    def fetchone(self):
        return self.cur.fetchone()

    def fetchall(self):
        return self.cur.fetchall()

    @property
    def lastrowid(self):
        return self.cur.lastrowid


db = MySQLAutoAdapter()
cursor = db.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id BIGINT PRIMARY KEY,
    xp INT DEFAULT 0,
    coins INT DEFAULT 0,
    mpl_points INT DEFAULT 0,
    reputation INT DEFAULT 0,
    house VARCHAR(50) DEFAULT 'Unassigned',
    messages INT DEFAULT 0,
    registered_at VARCHAR(50)
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS matches (
    id INT AUTO_INCREMENT PRIMARY KEY,
    game VARCHAR(50) NOT NULL,
    team_a VARCHAR(100) NOT NULL,
    team_b VARCHAR(100) NOT NULL,
    start_time VARCHAR(50) NOT NULL,
    status VARCHAR(20) DEFAULT 'UPCOMING',
    score_a INT DEFAULT 0,
    score_b INT DEFAULT 0,
    channel_id BIGINT DEFAULT 0,
    source VARCHAR(50) DEFAULT 'manual',
    external_id VARCHAR(255) UNIQUE,
    created_at VARCHAR(50) NOT NULL
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS votes (
    match_id INT,
    user_id BIGINT,
    choice VARCHAR(100) NOT NULL,
    PRIMARY KEY (match_id, user_id)
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS tournaments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    format VARCHAR(50) NOT NULL DEFAULT 'single',
    status VARCHAR(50) NOT NULL DEFAULT 'REGISTRATION',
    created_at VARCHAR(50) NOT NULL
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS tournament_teams (
    tournament_id INT,
    slot INT,
    team VARCHAR(100) NOT NULL,
    PRIMARY KEY (tournament_id, slot)
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS tournament_matches (
    id INT AUTO_INCREMENT PRIMARY KEY,
    tournament_id INT,
    round_no INT,
    match_no INT,
    team_a VARCHAR(100),
    team_b VARCHAR(100),
    winner VARCHAR(100),
    score_a INT DEFAULT 0,
    score_b INT DEFAULT 0,
    status VARCHAR(20) DEFAULT 'PENDING'
)
""")

db.commit()

# =========================================================
# CONFIG & VISUAL ASSETS
# =========================================================

XP_COOLDOWN = 60
XP_MIN = 10
XP_MAX = 20
xp_cooldowns = {}

HOUSE_ROLES = {
    "RRQ": "🏆 RRQ",
    "EVOS": "🦅 EVOS",
    "ONIC": "⚡ ONIC",
    "AE": "🦁 AE",
}

HOUSE_EMOJIS = {
    "RRQ": "🏆",
    "EVOS": "🦅",
    "ONIC": "⚡",
    "AE": "🦁",
}

HOUSE_VISUALS = {
    "RRQ": {
        "color": 0xF1C40F,
        "motto": "Viva RRQ • Kings of Kings",
        "icon": "https://cdn.discordapp.com/embed/avatars/4.png",
    },
    "EVOS": {
        "color": 0x3498DB,
        "motto": "EVOS Roar • White Tiger Dynasty",
        "icon": "https://cdn.discordapp.com/embed/avatars/0.png",
    },
    "ONIC": {
        "color": 0xF1C40F,
        "motto": "Go ONIC • Sky Kings",
        "icon": "https://cdn.discordapp.com/embed/avatars/3.png",
    },
    "AE": {
        "color": 0xE74C3C,
        "motto": "Alter Champs • Unbreakable Spirit",
        "icon": "https://cdn.discordapp.com/embed/avatars/5.png",
    },
}

ROLES = {
    "🤖 INSTITUTE AI": 0x00F0FF,
    "👑 KING": 0xF1C40F,
    "🏛️ CHANCELLOR": 0x9B59B6,
    "🎓 DEAN": 0x3498DB,
    "🛡️ FACULTY": 0x95A5A6,
    "🔨 MODERATOR": 0xE74C3C,
    "💎 INVESTOR": 0x2ECC71,
    "🏆 ALUMNI": 0xBDC3C7,
    "🎖️ HONORS": 0x8E44AD,
    "🏆 RRQ": 0xF1C40F,
    "🦅 EVOS": 0x3498DB,
    "⚡ ONIC": 0xF1C40F,
    "🦁 AE": 0xE74C3C,
    "🎓 STUDENT": 0x3498DB,
    "🌱 FRESHMAN": 0x7F8C8D,
    "💻 COMPUTER SCIENCE": 0x2980B9,
    "🎨 DESIGN": 0xE67E22,
    "💼 BUSINESS": 0x27AE60,
    "🎬 MEDIA": 0xE84393,
    "🔬 SCIENCE": 0x16A085,
    "🎮 GAMER": 0x5865F2,
    "🔫 FPS": 0xED4245,
    "⚔️ MOBA": 0xEB459E,
    "🧙 RPG": 0x57F287,
    "🌎 SANDBOX": 0xFEE75C,
}

HOISTED_ROLES = {
    "🤖 INSTITUTE AI", "👑 KING", "🏛️ CHANCELLOR", "🎓 DEAN",
    "🛡️ FACULTY", "🔨 MODERATOR", "💎 INVESTOR", "🎖️ HONORS",
    "🏆 RRQ", "🦅 EVOS", "⚡ ONIC", "🦁 AE", "🎓 STUDENT",
}

ROLE_ICON_FILES = {
    "👑 KING": "king.png",
    "🏛️ CHANCELLOR": "chancellor.png",
    "🎓 DEAN": "dean.png",
    "🔨 MODERATOR": "moderator.png",
    "💎 INVESTOR": "investor.png",
    "🏆 RRQ": "rrq.png",
    "🦅 EVOS": "evos.png",
    "⚡ ONIC": "onic.png",
    "🦁 AE": "ae.png",
    "🎓 STUDENT": "student.png",
}

MAJORS = {
    "Computer Science": ("💻 COMPUTER SCIENCE", "💻", "Software Engineering, AI & Systems"),
    "Design": ("🎨 DESIGN", "🎨", "UI/UX, Visual Arts & Motion Graphics"),
    "Business": ("💼 BUSINESS", "💼", "Entrepreneurship, Finance & Strategy"),
    "Media": ("🎬 MEDIA", "🎬", "Content Creation, Streaming & Production"),
    "Science": ("🔬 SCIENCE", "🔬", "Research, Data & Applied Sciences"),
}

GAMES = {
    "FPS": ("🔫 FPS", "🔫", "Valorant, CS2 & Tactical Shooters"),
    "MOBA": ("⚔️ MOBA", "⚔️", "Mobile Legends, Dota 2 & League"),
    "RPG": ("🧙 RPG", "🧙", "Genshin, Honkai, MMO & Action RPGs"),
    "Sandbox": ("🌎 SANDBOX", "🌎", "Minecraft, Roblox & Open World"),
    "Gamer": ("🎮 GAMER", "🎮", "All-Around Competitive & Casual Gaming"),
}

CHANNELS = {
    "🚪 THE GATE": ["👋・welcome", "📜・constitution", "📢・bulletin", "🪪・registration", "🗺️・campus-map"],
    "🏫 STUDENT LIFE": ["💬・commons", "🗣️・after-class", "😂・campus-chaos", "📸・yearbook", "🎨・showcase", "🤝・introductions"],
    "🎓 ACADEMIA": ["📚・library", "🧠・study-hall", "💻・computer-science", "🎨・design-studio", "💼・business-school", "🎬・media-lab", "🔬・research-lab"],
    "🎮 GAME LAB": ["🎮・game-lobby", "🔎・looking-for-group", "🏆・tournaments", "📊・leaderboards", "📜・match-results"],
    "📺 WATCH PARTY": [
        "📺・mpl-watch-party", "💬・mpl-match-discussion", "🔮・mpl-predictions", "🏆・mpl-results", "🔥・mpl-hype",
        "📺・valorant-watch-party", "💬・valorant-match-discussion", "🔮・valorant-predictions", "🏆・valorant-results", "🔥・valorant-hype"
    ],
    "🎵 MUSIC": ["🎵・music-lounge"],
    "🏆 ACTIVITIES": ["🎉・events", "🏅・achievements", "🗳️・elections", "🧩・clubs", "💡・projects"],
    "💎 THE SOCIETY": ["🥂・the-lounge", "🕯️・private-discussion", "🗝️・the-vault", "🎩・society-events"],
    "👑 ADMINISTRATION": ["🏛️・chancellor-office", "🎓・dean-office", "🛡️・faculty-room", "🔨・mod-room", "📋・reports", "📊・server-logs"],
}

VOICE_CHANNELS = {
    "🏫 STUDENT LIFE": ["🔊・student-lounge", "🔊・study-room"],
    "🎓 ACADEMIA": ["🔊・study-hall", "🔊・group-study"],
    "🎮 GAME LAB": ["🔊・gaming-lounge", "🔊・squad-room-1", "🔊・squad-room-2", "🔊・tournament-room"],
    "📺 WATCH PARTY": ["🔊・mpl-watch-party", "🔊・valorant-watch-party"],
    "🎵 MUSIC": ["🔊・music-room"],
    "🏆 ACTIVITIES": ["🔊・event-stage"],
}

MPL_SOURCE = "https://id-mpl.com/id/schedule"
VALORANT_SOURCE = "https://valorantesports.com/id-ID/valorantesports?leagues=vct_pacific"
MPL_SCHEDULE_URL = "https://id-mpl.com/schedule"
AUTO_SYNC_MINUTES = 5
HTTP_TIMEOUT = 15

# =========================================================
# HELPERS
# =========================================================

def now_iso():
    return datetime.now(timezone.utc).isoformat()

def get_role(guild, name):
    return discord.utils.get(guild.roles, name=name)

def get_category(guild, name):
    return discord.utils.get(guild.categories, name=name)

def _clean_channel_slug(text: str) -> str:
    return re.sub(r"[^a-z0-9-]", "", text.lower()).strip("-")

def get_channel(guild, name):
    if not guild:
        return None
    exact = discord.utils.get(guild.text_channels, name=name)
    if exact:
        return exact
    target_slug = _clean_channel_slug(name)
    if not target_slug:
        return None
    for ch in guild.text_channels:
        ch_slug = _clean_channel_slug(ch.name)
        if ch_slug == target_slug or target_slug in ch_slug:
            return ch
    return None

def watch_channel(guild, game):
    slug = "mpl-watch-party" if game.upper() == "MPL" else "valorant-watch-party"
    return get_channel(guild, slug)

def ensure_user(user_id):
    cursor.execute("SELECT user_id FROM users WHERE user_id=?", (user_id,))
    if cursor.fetchone() is None:
        cursor.execute(
            "INSERT INTO users(user_id, registered_at) VALUES (?, ?)",
            (user_id, now_iso())
        )
        db.commit()

def get_user(user_id):
    ensure_user(user_id)
    cursor.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    return cursor.fetchone()

def add_rewards(user_id, xp=0, coins=0, mpl_points=0, reputation=0):
    ensure_user(user_id)
    cursor.execute("""
        UPDATE users
        SET xp=xp+?, coins=coins+?, mpl_points=mpl_points+?, reputation=reputation+?
        WHERE user_id=?
    """, (xp, coins, mpl_points, reputation, user_id))
    db.commit()

def level_info(xp):
    level = 1
    required = 100
    remaining = xp
    while remaining >= required:
        remaining -= required
        level += 1
        required = 100 * level
    return level, remaining, required

def house_of(member):
    for key, role_name in HOUSE_ROLES.items():
        role = get_role(member.guild, role_name)
        if role and role in member.roles:
            return key
    return "Unassigned"

def major_of(member):
    for key, (role_name, _, _) in MAJORS.items():
        role = get_role(member.guild, role_name)
        if role and role in member.roles:
            return role_name
    return "Undeclared"

def games_of(member):
    picked = []
    for key, (role_name, _, _) in GAMES.items():
        role = get_role(member.guild, role_name)
        if role and role in member.roles:
            picked.append(role_name)
    return ", ".join(picked) if picked else "None"

def require_admin(interaction):
    return interaction.user.guild_permissions.administrator or interaction.user.guild_permissions.manage_guild

def format_match(row):
    start = datetime.fromisoformat(row["start_time"])
    unix = int(start.timestamp())
    return (
        f"**{row['team_a']}** vs **{row['team_b']}**\n"
        f"🕒 <t:{unix}:F> • <t:{unix}:R>\n"
        f"📌 Status: **{row['status']}**"
    )

def house_leaderboard():
    cursor.execute("""
        SELECT house, SUM(mpl_points) AS points, COUNT(*) AS members
        FROM users
        WHERE house IN ('RRQ','EVOS','ONIC','AE')
        GROUP BY house
        ORDER BY points DESC
    """)
    totals = {r["house"]: (r["points"] or 0, r["members"]) for r in cursor.fetchall()}
    return [(h, totals.get(h, (0, 0))[0], totals.get(h, (0, 0))[1]) for h in HOUSE_ROLES]

# =========================================================
# BROADCAST UI EMBED & PERSISTENT 1-CLICK VOTE VIEW (v2.8)
# =========================================================

def _build_vote_bar(match_id, team_a, team_b):
    cursor.execute("SELECT choice, COUNT(*) AS cnt FROM votes WHERE match_id=? GROUP BY choice", (match_id,))
    counts = {r["choice"].upper(): r["cnt"] for r in cursor.fetchall()}
    ca = counts.get(team_a.upper(), 0)
    cb = counts.get(team_b.upper(), 0)
    total = ca + cb
    if total == 0:
        return "▱▱▱▱▱▱▱▱▱▱ `0 votes cast — Click a button below to predict!`", 50, 50, 0
    pct_a = round((ca / total) * 100)
    pct_b = 100 - pct_a
    filled = round(pct_a / 10)
    bar = ("▰" * filled) + ("▱" * (10 - filled))
    return f"`{team_a}` **{pct_a}%** {bar} **{pct_b}%** `{team_b}` ({total} votes)", pct_a, pct_b, total


class MatchVoteView(discord.ui.View):
    def __init__(self, match_id: int, team_a: str, team_b: str):
        super().__init__(timeout=None)
        btn_a = discord.ui.Button(
            label=f"Vote {team_a[:20]}",
            style=discord.ButtonStyle.primary,
            emoji="🔹",
            custom_id=f"quickvote:{match_id}:{team_a[:30]}"
        )
        btn_b = discord.ui.Button(
            label=f"Vote {team_b[:20]}",
            style=discord.ButtonStyle.danger,
            emoji="🔸",
            custom_id=f"quickvote:{match_id}:{team_b[:30]}"
        )
        self.add_item(btn_a)
        self.add_item(btn_b)


def build_broadcast_match_embed(row, is_result=False, rewarded_count=0):
    game_upper = row["game"].upper()
    is_mpl = (game_upper == "MPL")
    match_id = row["id"]

    try:
        dt = datetime.fromisoformat(row["start_time"])
        unix = int(dt.timestamp())
        date_full = f"<t:{unix}:D>"
        time_short = f"<t:{unix}:t>"
        rel_time = f"<t:{unix}:R>"
    except Exception:
        date_full = row["start_time"][:10]
        time_short = row["start_time"][11:16]
        rel_time = "Scheduled"

    vote_bar_str, _, _, _ = _build_vote_bar(match_id, row["team_a"], row["team_b"])

    if is_result or row["status"] == "FINISHED":
        winner = row["team_a"] if row["score_a"] > row["score_b"] else row["team_b"] if row["score_b"] > row["score_a"] else "DRAW"
        embed = discord.Embed(
            title=f"🏆 {game_upper} OFFICIAL FINAL RESULT  •  MATCH #{match_id}",
            description=f"### 🔹 **{row['team_a']}**   `{row['score_a']}`  —  `{row['score_b']}`   **{row['team_b']}** 🔸\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            colour=discord.Colour.from_rgb(16, 185, 129),
        )
        embed.add_field(name="👑 Winner", value=f"**{winner}**", inline=True)
        embed.add_field(name="🗓️ Played On", value=f"{date_full} ({rel_time})", inline=True)
        embed.add_field(name="📡 Source", value=f"`{row['source']}`", inline=True)
        embed.add_field(name="📊 Community Poll", value=vote_bar_str, inline=False)
        if rewarded_count > 0:
            embed.add_field(
                name="🎁 Prediction Payout",
                value=f"**{rewarded_count} students** won `+75 XP` & `🪙 +100 Coins`!",
                inline=False
            )
        embed.set_footer(text="THE INSTITUTE • Esports Broadcast Center • Verified Result")
        return embed

    is_live = (row["status"] == "LIVE")
    accent_color = (
        discord.Colour.from_rgb(239, 68, 68) if is_live
        else (discord.Colour.from_rgb(245, 158, 11) if is_mpl else discord.Colour.from_rgb(255, 70, 85))
    )
    status_header = "🔴 **LIVE BROADCAST NOW**" if is_live else f"⏳ **UPCOMING MATCH (7-DAY SCHEDULE)**  •  Starts {rel_time}"

    embed = discord.Embed(
        title=f"{'🛡️ MPL INDONESIA' if is_mpl else '🎯 VALORANT CHAMPIONS TOUR'}  •  MATCH #{match_id}",
        description=f"{status_header}\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        colour=accent_color,
    )
    embed.add_field(name="🔹 TEAM A", value=f"**{row['team_a']}**\nScore: `{row['score_a']}`", inline=True)
    embed.add_field(name="⚡ KICKOFF", value=f"**{time_short}**\n{date_full}\n({rel_time})", inline=True)
    embed.add_field(name="🔸 TEAM B", value=f"**{row['team_b']}**\nScore: `{row['score_b']}`", inline=True)
    embed.add_field(name="🔮 LIVE COMMUNITY PREDICTION", value=vote_bar_str, inline=False)
    embed.set_footer(text=f"Source: {row['source']} • Click a button below or use /vote {match_id} [team] (+75 XP & +100 Coins)")
    return embed

# =========================================================
# AUTOMATIC LIVE / SCHEDULE & MULTI-CHANNEL ROUTER (v2.8)
# =========================================================

SYNC_LOCK = asyncio.Lock()

class _TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        if tag.lower() in {"script", "style", "noscript"}:
            self.skip += 1

    def handle_endtag(self, tag):
        if tag.lower() in {"script", "style", "noscript"} and self.skip:
            self.skip -= 1

    def handle_data(self, data):
        if not self.skip:
            text = " ".join(data.split())
            if text:
                self.parts.append(text)

    def text(self):
        return "\n".join(self.parts)

def fetch_text(url, is_liquipedia=False):
    ua = (
        "TheInstituteCampusBot/2.8 (https://discord.gg/theinstitute; admin@theinstitute.gg)"
        if is_liquipedia
        else "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    )
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": ua,
            "Accept": "application/json,text/html,application/xhtml+xml,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9,id;q=0.8",
        },
    )
    with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as response:
        raw = response.read()
        return raw.decode("utf-8", errors="ignore")

def _parse_relative_offset(rel_str, is_past=False):
    now = datetime.now(timezone.utc)
    if not rel_str:
        return (now - timedelta(hours=3)) if is_past else (now + timedelta(hours=3))

    s = rel_str.lower()
    if "live" in s or "ongoing" in s or "now" in s:
        return now

    days = hours = mins = 0
    m_w = re.search(r"(\d+)\s*w", s)
    m_d = re.search(r"(\d+)\s*d", s)
    m_h = re.search(r"(\d+)\s*h", s)
    m_m = re.search(r"(\d+)\s*m", s)
    if m_w:
        days += int(m_w.group(1)) * 7
    if m_d:
        days += int(m_d.group(1))
    if m_h:
        hours += int(m_h.group(1))
    if m_m:
        mins += int(m_m.group(1))

    delta = timedelta(days=days, hours=hours, minutes=mins)
    if delta.total_seconds() == 0:
        delta = timedelta(hours=2)

    target = (now - delta) if is_past else (now + delta)
    rounded_min = 30 if target.minute >= 30 else 0
    return target.replace(minute=rounded_min, second=0, microsecond=0)

def _extract_liquipedia_matches(api_url, game_label, source_label):
    now_utc = datetime.now(timezone.utc)
    results = []
    try:
        raw_json = json.loads(fetch_text(api_url, is_liquipedia=True))
        html_body = raw_json.get("parse", {}).get("text", {}).get("*", "")
        table_blocks = re.findall(
            r'<table[^>]*infobox_matches_content[^>]*>(.*?)</table>',
            html_body, re.S
        )
        for block in table_blocks[:45]:
            ts_match = re.search(r'data-timestamp="(\d+)"', block)
            if not ts_match:
                continue
            ts_val = int(ts_match.group(1))
            start_dt = datetime.fromtimestamp(ts_val, tz=timezone.utc)

            if start_dt < now_utc - timedelta(days=14) or start_dt > now_utc + timedelta(days=7):
                continue

            teams = re.findall(r'data-highlightingclass="([^"]+)"', block)
            if len(teams) < 2:
                teams = re.findall(r'class="team-template-text"[^>]*>(?:<a[^>]*>)?([^<]+)', block)
            if len(teams) < 2:
                continue

            t1, t2 = teams[0].strip(), teams[1].strip()
            if not t1 or not t2 or "TBD" in (t1.upper(), t2.upper()) or t1.lower() == t2.lower():
                continue

            score_a = score_b = 0
            has_score = False
            versus_block = re.search(r'class="versus"[^>]*>(.*?)</td>', block, re.S)
            search_area = versus_block.group(1) if versus_block else block
            score_nums = re.findall(r'>\s*([0-5])\s*<', search_area)
            if len(score_nums) >= 2:
                sa, sb = int(score_nums[0]), int(score_nums[1])
                if sa > 0 or sb > 0:
                    score_a, score_b = sa, sb
                    has_score = True
            else:
                sm = re.search(r'([0-5])\s*(?:&#58;|:|-|–)\s*([0-5])', search_area)
                if sm:
                    sa, sb = int(sm.group(1)), int(sm.group(2))
                    if sa > 0 or sb > 0:
                        score_a, score_b = sa, sb
                        has_score = True

            if start_dt > now_utc + timedelta(minutes=10):
                status = "UPCOMING"
                score_a, score_b = 0, 0
            elif has_score and start_dt <= now_utc:
                status = "FINISHED"
            elif start_dt <= now_utc <= start_dt + timedelta(hours=3):
                status = "LIVE"
            else:
                if not has_score:
                    continue
                status = "FINISHED"

            clean_t1 = re.sub(r"[^a-z0-9]", "", t1.lower())[:20]
            clean_t2 = re.sub(r"[^a-z0-9]", "", t2.lower())[:20]
            ext_id = f"{game_label.lower()}:lq:{ts_val}:{clean_t1}:{clean_t2}"[:240]

            results.append({
                "external_id": ext_id,
                "game": game_label.upper(),
                "team_a": t1[:45],
                "team_b": t2[:45],
                "start_time": start_dt.isoformat(),
                "source": source_label,
                "status": status,
                "score_a": score_a,
                "score_b": score_b,
            })
    except Exception:
        pass
    return results

def parse_mpl_schedule():
    now_utc = datetime.now(timezone.utc)
    matches = []

    for page_name in ("Liquipedia:Upcoming_and_ongoing_matches", "Liquipedia:Matches"):
        lq_url = f"https://liquipedia.net/mobilelegends/api.php?action=parse&page={page_name}&prop=text&format=json"
        matches.extend(_extract_liquipedia_matches(lq_url, "MPL", "Liquipedia MLBB Official"))

    try:
        raw = fetch_text(MPL_SCHEDULE_URL)
        parser = _TextExtractor()
        parser.feed(raw)
        lines = [re.sub(r"\s+", " ", x).strip() for x in parser.text().splitlines() if x.strip()]

        date_re = re.compile(
            r"^(?:Senin|Selasa|Rabu|Kamis|Jumat|Sabtu|Minggu|Monday|Tuesday|Wednesday|"
            r"Thursday|Friday|Saturday|Sunday),?\s+(\d{1,2})\s+"
            r"(Jan(?:uari|uary)?|Feb(?:ruari|ruary)?|Mar(?:et|ch)?|Apr(?:il)?|"
            r"Mei|May|Jun(?:i|e)?|Jul(?:i|y)?|Agt|Aug(?:ustus|ust)?|"
            r"Sep(?:tember)?|Okt(?:ober)?|Oct(?:ober)?|Nov(?:ember)?|"
            r"Des(?:ember)?|Dec(?:ember)?)\s+(20\d{2})$", re.I)
        time_re = re.compile(r"^(\d{1,2}):(\d{2})(?:\s*WIB)?$", re.I)

        known_teams = {"RRQ", "EVOS", "ONIC", "AE", "BTR", "GEEK", "DEWA", "NAVI", "TLID"}
        month_map = {
            "jan": 1, "feb": 2, "mar": 3, "apr": 4, "mei": 5, "may": 5,
            "jun": 6, "jul": 7, "agt": 8, "aug": 8, "sep": 9, "okt": 10, "oct": 10,
            "nov": 11, "des": 12, "dec": 12,
        }

        current_date = None
        last_valid_idx = -999

        for i, line in enumerate(lines):
            dm = date_re.match(line)
            if dm:
                month = month_map.get(dm.group(2).lower()[:3])
                if month:
                    current_date = (int(dm.group(3)), month, int(dm.group(1)))
                    last_valid_idx = i
                continue

            if i - last_valid_idx > 25:
                current_date = None
                continue

            tm = time_re.match(line)
            if not tm or current_date is None:
                continue

            before = next((lines[j].upper() for j in range(i - 1, max(-1, i - 7), -1) if lines[j].upper() in known_teams), None)
            after = next((lines[j].upper() for j in range(i + 1, min(len(lines), i + 7)) if lines[j].upper() in known_teams), None)
            if not before or not after or before == after:
                continue

            # Perbarui last_valid_idx agar match ke-2 dan ke-3 di hari yang sama tetap terbaca
            last_valid_idx = i

            window = lines[max(0, i - 4):min(len(lines), i + 5)]
            digits = [int(x) for x in window if x.isdigit() and 0 <= int(x) <= 5]
            score_a, score_b = (digits[0], digits[1]) if len(digits) >= 2 else (0, 0)
            has_score = (score_a > 0 or score_b > 0)

            year, month, day = current_date
            hour, minute = int(tm.group(1)), int(tm.group(2))
            start_dt = datetime(year, month, day, hour, minute, tzinfo=timezone(timedelta(hours=7))).astimezone(timezone.utc)

            if has_score and start_dt > now_utc:
                continue
            if not has_score and start_dt < now_utc - timedelta(hours=3):
                continue
            if start_dt > now_utc + timedelta(days=7) or start_dt < now_utc - timedelta(days=30):
                continue

            if start_dt > now_utc:
                status = "UPCOMING"
            elif start_dt <= now_utc <= start_dt + timedelta(hours=3) and not has_score:
                status = "LIVE"
            else:
                status = "FINISHED"

            ext_id = f"mpl:{start_dt.strftime('%Y%m%d%H%M')}:{before.lower()}:{after.lower()}"
            matches.append({
                "external_id": ext_id,
                "game": "MPL",
                "team_a": before,
                "team_b": after,
                "start_time": start_dt.isoformat(),
                "source": "MPL ID Official",
                "status": status,
                "score_a": score_a,
                "score_b": score_b,
            })
    except Exception:
        pass

    unique = {item["external_id"]: item for item in matches}
    return list(unique.values())

def parse_vlr_matches():
    """Tarik jadwal Upcoming (7 hari) & Results VCT langsung dari VLR.gg + VLR API + Liquipedia."""
    combined = {}
    now_utc = datetime.now(timezone.utc)

    vct_keywords = (
        "vct", "champions", "masters", "pacific", "americas", "emea", "china", "cn ",
        "ascension", "kickoff", "stage", "game changers", "challengers", "red bull", "soop",
        "prx", "paper rex", "rrq", "rex regum", "t1", "gen.g", "geng", "drx", "zeta", "dfm",
        "talon", "team secret", "global esports", "boom", "sentinels", "nrg", "g2", "100 thieves",
        "cloud9", "kru", "leviatán", "leviatan", "loud", "furia", "mibr", "fnatic", "heretics",
        "vitality", "team liquid", "karmine", "fut", "edward", "edg", "bilibili", "blg", "fpx", "trace"
    )

    # 1. Scrape Langsung Halaman Resmi VLR.gg (Results & Upcoming) — Paling Akurat & Stabil
    direct_pages = [
        ("https://www.vlr.gg/matches/results", "FINISHED"),
        ("https://www.vlr.gg/matches", "UPCOMING"),
    ]
    for page_url, default_mode in direct_pages:
        try:
            raw_html = fetch_text(page_url)
            # Pisahkan per kartu match (<a href="/12345/..." class="...match-item...">)
            cards = re.findall(
                r'<a\s+href="/(\d+)/([^"]+)"\s+class="[^"]*match-item[^"]*"[^>]*>(.*?)</a>',
                raw_html, re.S
            )
            all_parsed = []
            for match_id_str, slug, block in cards[:45]:
                teams = [
                    re.sub(r"\s+", " ", t).strip()
                    for t in re.findall(r'class="[^"]*match-item-vs-team-name[^"]*"[^>]*>.*?class="text-of"[^>]*>([^<]+)<', block, re.S)
                ]
                if len(teams) < 2:
                    teams = [re.sub(r"\s+", " ", t).strip() for t in re.findall(r'class="text-of"[^>]*>([^<]+)<', block)]
                if len(teams) < 2:
                    continue

                team_a, team_b = teams[0], teams[1]
                if not team_a or not team_b or "TBD" in (team_a.upper(), team_b.upper()):
                    continue

                scores_raw = re.findall(r'class="[^"]*match-item-vs-team-score[^"]*"[^>]*>\s*([^<\s]+)\s*<', block)
                score_a = int(scores_raw[0]) if len(scores_raw) >= 1 and scores_raw[0].isdigit() else 0
                score_b = int(scores_raw[1]) if len(scores_raw) >= 2 and scores_raw[1].isdigit() else 0

                eta_m = re.search(r'class="ml-eta"[^>]*>\s*([^<]+)\s*<', block)
                status_m = re.search(r'class="ml-status"[^>]*>\s*([^<]+)\s*<', block)
                eta_str = (eta_m.group(1).strip() if eta_m else "") or (status_m.group(1).strip() if status_m else "")

                ev_m = re.search(r'class="match-item-event"[^>]*>(.*?)</div>', block, re.S)
                ev_text = re.sub(r"<[^>]+>", " ", ev_m.group(1) if ev_m else "VCT").strip()
                ev_Lines = [x.strip() for x in ev_text.splitlines() if x.strip()]
                event_name = ev_Lines[-1] if ev_Lines else "VCT"

                status = default_mode
                if "live" in eta_str.lower():
                    status = "LIVE"
                    start_dt = now_utc
                elif status == "FINISHED":
                    if score_a == 0 and score_b == 0:
                        continue
                    start_dt = _parse_relative_offset(eta_str, is_past=True)
                else:
                    start_dt = _parse_relative_offset(eta_str, is_past=False)
                    if start_dt > now_utc + timedelta(days=7):
                        continue

                haystack = f"{team_a} {team_b} {event_name} {slug}".lower()
                is_vct_priority = any(k in haystack for k in vct_keywords)

                item_data = {
                    "external_id": f"vlr:{match_id_str}"[:240],
                    "game": "VALORANT",
                    "team_a": team_a[:45],
                    "team_b": team_b[:45],
                    "start_time": start_dt.isoformat(),
                    "source": f"VLR • {event_name}"[:50],
                    "status": status,
                    "score_a": score_a,
                    "score_b": score_b,
                    "_priority": 1 if is_vct_priority else 0,
                }
                all_parsed.append(item_parsed := item_data)

            # Utamakan pertandingan resmi VCT / tim Tier-1
            all_parsed.sort(key=lambda x: x["_priority"], reverse=True)
            for item in all_parsed[:15]:
                item.pop("_priority", None)
                combined[item["external_id"]] = item
        except Exception:
            pass

    # 2. Fallback VLR JSON API jika akses langsung terhalang
    if len(combined) < 4:
        vlr_sources = [
            ("https://vlrggapi.vercel.app/match?q=live_score", "LIVE"),
            ("https://vlrggapi.vercel.app/match?q=upcoming", "UPCOMING"),
            ("https://vlrggapi.vercel.app/match?q=results", "FINISHED"),
        ]
        for url, mode in vlr_sources:
            try:
                raw = fetch_text(url)
                payload = json.loads(raw)
                rows = payload.get("data", {}).get("segments", [])
                for row in rows[:15]:
                    team_a = str(row.get("team1") or "").strip()
                    team_b = str(row.get("team2") or "").strip()
                    if not team_a or not team_b or "TBD" in (team_a.upper(), team_b.upper()):
                        continue

                    score_a = int(row.get("score1")) if str(row.get("score1", "")).isdigit() else 0
                    score_b = int(row.get("score2")) if str(row.get("score2", "")).isdigit() else 0
                    if mode == "FINISHED" and score_a == 0 and score_b == 0:
                        continue

                    rel_text = str(row.get("time_until_match") or row.get("time_completed") or "")
                    start_dt = _parse_relative_offset(rel_text, is_past=(mode == "FINISHED"))
                    if mode == "UPCOMING" and start_dt > now_utc + timedelta(days=7):
                        continue

                    match_page = str(row.get("match_page") or "").strip("/")
                    event_name = str(row.get("match_event") or row.get("tournament_name") or "VCT").strip()
                    ext_id = f"vlr:{match_page or (team_a.lower() + '-' + team_b.lower())}"[:240]

                    combined.setdefault(ext_id, {
                        "external_id": ext_id,
                        "game": "VALORANT",
                        "team_a": team_a[:45],
                        "team_b": team_b[:45],
                        "start_time": start_dt.isoformat(),
                        "source": f"VLR • {event_name}"[:50],
                        "status": mode,
                        "score_a": score_a,
                        "score_b": score_b,
                    })
            except Exception:
                continue

    return list(combined.values())
def upsert_external_match(item):
    external_id = item["external_id"]
    cursor.execute("SELECT id, status, score_a, score_b, channel_id FROM matches WHERE external_id=?", (external_id,))
    existing = cursor.fetchone()

    new_status = item.get("status", "UPCOMING")
    score_a = item.get("score_a", 0)
    score_b = item.get("score_b", 0)

    if existing:
        old_status = existing["status"]
        ann_state = existing["channel_id"] or 0

        if old_status == "FINISHED" and new_status != "FINISHED":
            new_status = "FINISHED"
            if score_a == 0 and score_b == 0:
                score_a, score_b = existing["score_a"], existing["score_b"]

        status_changed = (old_status != new_status) or (existing["score_a"] != score_a) or (existing["score_b"] != score_b)
        cursor.execute("""
            UPDATE matches
            SET game=?, team_a=?, team_b=?, start_time=?, status=?,
                score_a=?, score_b=?, source=?
            WHERE external_id=?
        """, (
            item["game"], item["team_a"], item["team_b"], item["start_time"],
            new_status, score_a, score_b, item["source"], external_id
        ))
        db.commit()
        return existing["id"], False, new_status, ann_state, status_changed

    cursor.execute("""
        INSERT INTO matches
        (game, team_a, team_b, start_time, status, score_a, score_b, channel_id, source, external_id, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?)
    """, (
        item["game"], item["team_a"], item["team_b"], item["start_time"],
        new_status, score_a, score_b, item["source"], external_id, now_iso()
    ))
    db.commit()
    return cursor.lastrowid, True, new_status, 0, True

async def route_match_announcement(guild, match_id, target_state):
    cursor.execute("SELECT * FROM matches WHERE id=?", (match_id,))
    row = cursor.fetchone()
    if not row:
        return

    game_upper = row["game"].upper()
    is_mpl = (game_upper == "MPL")

    if target_state == 2:
        winner = row["team_a"] if row["score_a"] > row["score_b"] else row["team_b"] if row["score_b"] > row["score_a"] else None
        rewarded_count = 0
        if winner:
            cursor.execute("SELECT user_id, choice FROM votes WHERE match_id=?", (match_id,))
            for v in cursor.fetchall():
                if v["choice"].lower() == winner.lower():
                    add_rewards(v["user_id"], xp=75, coins=100, mpl_points=75, reputation=2)
                    rewarded_count += 1

        embed = build_broadcast_match_embed(row, is_result=True, rewarded_count=rewarded_count)
        res_ch = get_channel(guild, "mpl-results" if is_mpl else "valorant-results")
        global_res_ch = get_channel(guild, "match-results")
        if res_ch:
            await res_ch.send(embed=embed)
        if global_res_ch and global_res_ch != res_ch:
            await global_res_ch.send(embed=embed)

        cursor.execute("UPDATE matches SET channel_id=? WHERE id=?", (target_state, match_id))
        db.commit()
        return

    # target_state == 1 -> Kirim ke #watch-party DAN #predictions beserta Tombol Vote 1-Klik
    embed = build_broadcast_match_embed(row, is_result=False)
    wp_ch = get_channel(guild, "mpl-watch-party" if is_mpl else "valorant-watch-party")
    pred_ch = get_channel(guild, "mpl-predictions" if is_mpl else "valorant-predictions")

    if wp_ch:
        await wp_ch.send(embed=embed, view=MatchVoteView(row["id"], row["team_a"], row["team_b"]))
    if pred_ch:
        await pred_ch.send(embed=embed, view=MatchVoteView(row["id"], row["team_a"], row["team_b"]))

    cursor.execute("UPDATE matches SET channel_id=? WHERE id=?", (target_state, match_id))
    db.commit()

async def sync_external_schedules(guild):
    async with SYNC_LOCK:
        imported, changed, errors = 0, 0, []
        now_utc = datetime.now(timezone.utc)

        cursor.execute("SELECT id, start_time, status FROM matches WHERE status IN ('UPCOMING', 'LIVE')")
        for row in cursor.fetchall():
            try:
                start_dt = datetime.fromisoformat(row["start_time"]).astimezone(timezone.utc)
            except Exception:
                continue

            if now_utc > start_dt + timedelta(hours=3):
                cursor.execute("UPDATE matches SET status='FINISHED' WHERE id=?", (row["id"],))
                changed += 1
            elif start_dt <= now_utc <= start_dt + timedelta(hours=3) and row["status"] == "UPCOMING":
                cursor.execute("UPDATE matches SET status='LIVE' WHERE id=?", (row["id"],))
                changed += 1
        db.commit()

        # Kuota di-reset untuk SETIAP game (MPL dapat kuota sendiri, VALORANT dapat kuota sendiri!)
        for provider, parser in (("MPL", parse_mpl_schedule), ("VALORANT", parse_vlr_matches)):
            announced_upcoming = 0
            announced_results = 0
            try:
                items = await asyncio.to_thread(parser)
                for item in items:
                    match_id, created, new_status, ann_state, is_changed = upsert_external_match(item)
                    if created:
                        imported += 1
                    elif is_changed:
                        changed += 1

                    if new_status in ("UPCOMING", "LIVE") and ann_state == 0 and announced_upcoming < 6:
                        try:
                            await route_match_announcement(guild, match_id, target_state=1)
                            announced_upcoming += 1
                        except Exception:
                            pass
                    elif new_status == "FINISHED" and ann_state < 2 and (item.get("score_a", 0) > 0 or item.get("score_b", 0) > 0) and announced_results < 6:
                        try:
                            await route_match_announcement(guild, match_id, target_state=2)
                            announced_results += 1
                        except Exception:
                            pass
            except Exception as exc:
                errors.append(f"{provider}: {type(exc).__name__}: {exc}")

        return imported, changed, errors
# =========================================================
# PERSISTENT REGISTRATION & ROLE CARD VIEW
# =========================================================

class RegistrationView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🎓 Verify & Claim Student ID", style=discord.ButtonStyle.success, custom_id="reg_verify", row=0)
    async def verify_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        student_role = get_role(interaction.guild, "🎓 STUDENT")
        freshman_role = get_role(interaction.guild, "🌱 FRESHMAN")
        if not student_role:
            await interaction.response.send_message("❌ Roles are not initialized yet. Run `/setup` first.", ephemeral=True)
            return

        if student_role in interaction.user.roles:
            await interaction.response.send_message("✅ Your Student ID is already active!", ephemeral=True)
            return

        roles_to_add = [student_role]
        if freshman_role:
            roles_to_add.append(freshman_role)

        try:
            await interaction.user.add_roles(*roles_to_add)
        except discord.Forbidden:
            await interaction.response.send_message(
                "⚠️ Bot permission error: Move the Bot's role to the very top in **Server Settings > Roles**.",
                ephemeral=True
            )
            return

        ensure_user(interaction.user.id)
        embed = discord.Embed(
            title="🪪 STUDENT ID ISSUED — ACCESS GRANTED",
            description=(
                f"Welcome to **THE INSTITUTE**, {interaction.user.mention}!\n\n"
                "🎓 **Status:** Verified Student (`🎓 STUDENT`)\n"
                "🔓 **Access:** All Campus, Academia, Game Lab & Watch Party channels are now unlocked.\n\n"
                "👇 *Complete your profile below by selecting your Esports House, Academic Major, and Game Roles!*"
            ),
            colour=discord.Colour.from_rgb(52, 152, 219)
        )
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.select(
        placeholder="🏆 1. Select Your Esports House (RRQ / EVOS / ONIC / AE)...",
        custom_id="reg_house",
        row=1,
        options=[
            discord.SelectOption(label="RRQ", description="House of Kings • Viva RRQ", emoji="🏆"),
            discord.SelectOption(label="EVOS", description="White Tiger Dynasty • EVOS Roar", emoji="🦅"),
            discord.SelectOption(label="ONIC", description="Sky Kings • Go ONIC", emoji="⚡"),
            discord.SelectOption(label="AE", description="Alter Champs • Alter Ego", emoji="🦁"),
        ]
    )
    async def house_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        choice = select.values[0]
        target_role_name = HOUSE_ROLES[choice]
        target_role = get_role(interaction.guild, target_role_name)

        if not target_role:
            await interaction.response.send_message("❌ House roles not found. Run `/setup` first.", ephemeral=True)
            return

        old_roles = [get_role(interaction.guild, r) for r in HOUSE_ROLES.values() if get_role(interaction.guild, r) in interaction.user.roles]
        try:
            if old_roles:
                await interaction.user.remove_roles(*old_roles)
            await interaction.user.add_roles(target_role)
        except discord.Forbidden:
            await interaction.response.send_message("⚠️ Move the Bot's role above House roles in **Server Settings > Roles**.", ephemeral=True)
            return

        ensure_user(interaction.user.id)
        cursor.execute("UPDATE users SET house=? WHERE user_id=?", (choice, interaction.user.id))
        db.commit()

        vis = HOUSE_VISUALS[choice]
        embed = discord.Embed(
            title=f"{HOUSE_EMOJIS[choice]} ALLEGIANCE PLEDGED: HOUSE {choice}",
            description=(
                f"*\"{vis['motto']}\"*\n\n"
                f"You are now representing **{target_role_name}** in **THE INSTITUTE House Cup**.\n"
                f"Earn MPL Points for your House by winning predictions (`/vote`) and tournaments!"
            ),
            colour=discord.Colour(vis["color"])
        )
        embed.set_thumbnail(url=vis["icon"])
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.select(
        placeholder="🎓 2. Select Your Academic Major...",
        custom_id="reg_major",
        row=2,
        options=[
            discord.SelectOption(label=key, description=desc, emoji=emoji)
            for key, (role_name, emoji, desc) in MAJORS.items()
        ]
    )
    async def major_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        choice = select.values[0]
        role_name, emoji, desc = MAJORS[choice]
        target_role = get_role(interaction.guild, role_name)
        if not target_role:
            await interaction.response.send_message("❌ Major role not found. Run `/setup` first.", ephemeral=True)
            return

        old_majors = [get_role(interaction.guild, r[0]) for r in MAJORS.values() if get_role(interaction.guild, r[0]) in interaction.user.roles]
        try:
            if old_majors:
                await interaction.user.remove_roles(*old_majors)
            await interaction.user.add_roles(target_role)
        except discord.Forbidden:
            await interaction.response.send_message("⚠️ Bot role hierarchy is too low to assign Major roles.", ephemeral=True)
            return

        embed = discord.Embed(
            title=f"{emoji} MAJOR DECLARED: {choice.upper()}",
            description=f"You have joined the **{role_name}** faculty.\n*{desc}*",
            colour=target_role.colour
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.select(
        placeholder="🎮 3. Select Your Game Divisions (Multi-Select)...",
        custom_id="reg_games",
        min_values=1,
        max_values=len(GAMES),
        row=3,
        options=[
            discord.SelectOption(label=key, description=desc, emoji=emoji)
            for key, (role_name, emoji, desc) in GAMES.items()
        ]
    )
    async def games_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        selected_names = [GAMES[val][0] for val in select.values]
        all_game_roles = [get_role(interaction.guild, r[0]) for r in GAMES.values()]
        roles_to_add = [get_role(interaction.guild, name) for name in selected_names if get_role(interaction.guild, name)]
        roles_to_remove = [r for r in all_game_roles if r and r in interaction.user.roles and r not in roles_to_add]

        try:
            if roles_to_remove:
                await interaction.user.remove_roles(*roles_to_remove)
            if roles_to_add:
                await interaction.user.add_roles(*roles_to_add)
        except discord.Forbidden:
            await interaction.response.send_message("⚠️ Bot role hierarchy is too low to assign Game roles.", ephemeral=True)
            return

        await interaction.response.send_message(
            f"🎮 **Game Divisions Updated:** {', '.join(f'`{n}`' for n in selected_names)}",
            ephemeral=True
        )

# =========================================================
# BOT CLASS, READY, INTERACTION ROUTER & AUTO-WELCOME
# =========================================================

class InstituteBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        self.add_view(RegistrationView())


bot = InstituteBot()

@bot.event
async def on_interaction(interaction: discord.Interaction):
    """Tangani klik tombol Vote (quickvote:match_id:team) secara permanen bahkan setelah restart."""
    if interaction.type == discord.InteractionType.component:
        cid = (interaction.data or {}).get("custom_id", "")
        if cid.startswith("quickvote:"):
            parts = cid.split(":", 2)
            if len(parts) == 3:
                _, mid_str, chosen_team = parts
                try:
                    match_id = int(mid_str)
                except ValueError:
                    return

                cursor.execute("SELECT * FROM matches WHERE id=?", (match_id,))
                row = cursor.fetchone()
                if not row or row["status"] == "FINISHED":
                    await interaction.response.send_message("❌ Voting is already closed for this match.", ephemeral=True)
                    return

                ensure_user(interaction.user.id)
                cursor.execute("SELECT choice FROM votes WHERE match_id=? AND user_id=?", (match_id, interaction.user.id))
                already_voted = cursor.fetchone() is not None

                cursor.execute(
                    "INSERT INTO votes(match_id, user_id, choice) VALUES (?, ?, ?) ON CONFLICT(match_id, user_id) DO UPDATE SET choice=excluded.choice",
                    (match_id, interaction.user.id, chosen_team)
                )
                db.commit()

                if not already_voted:
                    add_rewards(interaction.user.id, xp=10, coins=15, reputation=1)

                new_embed = build_broadcast_match_embed(row, is_result=False)
                await interaction.response.edit_message(
                    embed=new_embed,
                    view=MatchVoteView(row["id"], row["team_a"], row["team_b"])
                )


@tasks.loop(minutes=AUTO_SYNC_MINUTES)
async def schedule_sync_loop():
    guild = bot.get_guild(GUILD_ID)
    if guild is None:
        return
    try:
        imported, changed, errors = await sync_external_schedules(guild)
        print(f"[AUTO-SYNC] imported={imported} changed={changed}" + (f" info={'; '.join(errors)}" if errors else ""))
    except Exception as exc:
        print(f"[AUTO-SYNC] warning: {exc}")

@schedule_sync_loop.before_loop
async def before_schedule_sync_loop():
    await bot.wait_until_ready()

@bot.event
async def on_ready():
    synced = await bot.tree.sync(guild=GUILD)
    await bot.change_presence(
        status=discord.Status.online,
        activity=discord.Activity(type=discord.ActivityType.watching, name="THE INSTITUTE • MPL & VCT ⚡")
    )
    print("--------------------------------")
    print(f"Logged in as {bot.user}")
    print(f"Connected to Guild ID: {GUILD_ID}")
    print(f"Synced {len(synced)} command(s)")
    print("🏛️ THE INSTITUTE v2.8 is online.")
    print("📡 Automatic 7-day schedule & multi-channel router is ready.")
    print("--------------------------------")

    if not schedule_sync_loop.is_running():
        schedule_sync_loop.start()

@bot.event
async def on_member_join(member: discord.Member):
    ensure_user(member.id)
    welcome_ch = get_channel(member.guild, "👋・welcome")
    reg_ch = get_channel(member.guild, "🪪・registration")
    if welcome_ch:
        reg_mention = reg_ch.mention if reg_ch else "`#🪪・registration`"
        embed = discord.Embed(
            title="🏛️ WELCOME TO THE INSTITUTE",
            description=(
                f"Greetings {member.mention}, welcome to **THE INSTITUTE** — Competitive Esports & Academia.\n\n"
                f"🪪 **Step 1:** Head over to {reg_mention} to claim your **Student ID**.\n"
                f"🏆 **Step 2:** Pledge your allegiance to **RRQ, EVOS, ONIC, or AE**.\n"
                f"🎓 **Step 3:** Declare your **Academic Major** & **Game Divisions**."
            ),
            colour=discord.Colour.gold()
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text=f"Member #{member.guild.member_count} • THE INSTITUTE v2.8")
        try:
            await welcome_ch.send(embed=embed)
        except discord.Forbidden:
            pass

# =========================================================
# SETUP & GATE INITIALIZATION
# =========================================================

@bot.tree.command(name="setup", description="Initialize or repair THE INSTITUTE roles, icons, and channels.", guild=GUILD)
async def setup(interaction: discord.Interaction):
    if not require_admin(interaction):
        await interaction.response.send_message("❌ Manage Server or Administrator required.", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)
    guild = interaction.guild
    can_use_role_icons = "ROLE_ICONS" in guild.features
    icons_loaded = 0

    for name, value in ROLES.items():
        role = get_role(guild, name)
        should_hoist = name in HOISTED_ROLES
        if not role:
            try:
                role = await guild.create_role(
                    name=name,
                    colour=discord.Colour(value),
                    hoist=should_hoist,
                    reason="THE INSTITUTE v2.8"
                )
            except discord.Forbidden:
                continue
        else:            pass
# =========================================================
# RESTORED SLASH COMMANDS (SCHEDULE, MATCHES, VOTES & PROFILES)
# =========================================================

@bot.tree.command(name="sync_schedule", description="Admin: Force sync MPL & Valorant schedules and results now.", guild=GUILD)
async def sync_schedule(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Admin only.", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)
    imported, changed, errors = await sync_external_schedules(interaction.guild)
    msg = (
        f"⚡ **Schedule Sync Complete!**\n"
        f"➕ New matches: **{imported}**\n"
        f"🔄 Status/Score updates: **{changed}**"
    )
    if errors:
        msg += f"\n⚠️ Notes: `{'; '.join(errors)}`"
    await interaction.followup.send(msg, ephemeral=True)


@bot.tree.command(name="reset_schedules", description="Admin: Purge old schedule data, clean channels, and resync.", guild=GUILD)
async def reset_schedules(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Admin only.", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)
    guild = interaction.guild

    cursor.execute("DELETE FROM matches WHERE source != 'manual'")
    db.commit()

    target_slugs = [
        "mpl-watch-party", "mpl-predictions", "mpl-results",
        "valorant-watch-party", "valorant-predictions", "valorant-results",
        "match-results"
    ]
    cleaned_msgs = 0
    for slug in target_slugs:
        ch = get_channel(guild, slug)
        if ch:
            try:
                deleted = await ch.purge(limit=50, check=lambda m: m.author == guild.me)
                cleaned_msgs += len(deleted)
            except Exception:
                pass

    imported, changed, errors = await sync_external_schedules(guild)

    await interaction.followup.send(
        f"🧹 **Schedule Reset & Multi-Channel Resync Complete!**\n"
        f"• Old bot messages cleaned: **{cleaned_msgs}**\n"
        f"• Fresh verified matches & results imported: **{imported}**\n"
        + (f"⚠️ Notes: {', '.join(errors)}" if errors else "✅ Watch Party, Predictions, and Results channels are now populated!"),
        ephemeral=True
    )


@bot.tree.command(name="matches", description="View the 7-day upcoming & live match calendar.", guild=GUILD)
async def matches(interaction: discord.Interaction, game: str = "all"):
    game = game.lower()
    if game not in ("all", "mpl", "valorant"):
        await interaction.response.send_message("❌ Use `all`, `mpl`, or `valorant`.", ephemeral=True)
        return

    if game == "all":
        cursor.execute("SELECT * FROM matches WHERE status IN ('UPCOMING', 'LIVE') ORDER BY start_time ASC")
    else:
        cursor.execute("SELECT * FROM matches WHERE UPPER(game)=? AND status IN ('UPCOMING', 'LIVE') ORDER BY start_time ASC", (game.upper(),))

    now_utc = datetime.now(timezone.utc)
    limit_utc = now_utc + timedelta(days=7)
    grouped_days = {}

    for r in cursor.fetchall():
        try:
            dt = datetime.fromisoformat(r["start_time"]).astimezone(timezone.utc)
            if dt + timedelta(hours=3) < now_utc:
                cursor.execute("UPDATE matches SET status='FINISHED' WHERE id=?", (r["id"],))
                continue
            if dt > limit_utc:
                continue
            wib_dt = dt.astimezone(timezone(timedelta(hours=7)))
            day_key = wib_dt.strftime("🗓️ %A, %d %b %Y")
            grouped_days.setdefault(day_key, []).append((dt, r))
        except Exception:
            continue
    db.commit()

    if not grouped_days:
        await interaction.response.send_message("📅 No matches scheduled in the next 7 days. Check `/results` for recent final scores!", ephemeral=True)
        return

    embed = discord.Embed(
        title="📅 THE INSTITUTE — 7-DAY ESPORTS BROADCAST SCHEDULE",
        description="Auto-updated daily • All times adjusted to your local timezone",
        colour=discord.Colour.from_rgb(245, 158, 11)
    )
    for day_label, items in list(grouped_days.items())[:7]:
        lines = []
        for dt, r in items:
            unix = int(dt.timestamp())
            badge = "🔴 `LIVE`" if r["status"] == "LIVE" else f"⏰ <t:{unix}:t>"
            icon = "🛡️" if r["game"].upper() == "MPL" else "🎯"
            lines.append(f"{icon} **`#{r['id']}`** {badge} — **{r['team_a']}** vs **{r['team_b']}** (<t:{unix}:R>)")
        embed.add_field(name=day_label, value="\n".join(lines), inline=False)

    embed.set_footer(text="Updated automatically every 5 mins • Click buttons in #watch-party or #predictions to vote")
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="results", description="View verified finished match scores (past dates only).", guild=GUILD)
async def results(interaction: discord.Interaction, game: str = "all"):
    game = game.lower()
    if game not in ("all", "mpl", "valorant"):
        await interaction.response.send_message("❌ Use `all`, `mpl`, or `valorant`.", ephemeral=True)
        return

    if game == "all":
        cursor.execute("SELECT * FROM matches WHERE status='FINISHED' AND (score_a > 0 OR score_b > 0) ORDER BY start_time DESC LIMIT 25")
    else:
        cursor.execute("SELECT * FROM matches WHERE UPPER(game)=? AND status='FINISHED' AND (score_a > 0 OR score_b > 0) ORDER BY start_time DESC LIMIT 25", (game.upper(),))

    now_utc = datetime.now(timezone.utc)
    valid_results = []
    for r in cursor.fetchall():
        try:
            dt = datetime.fromisoformat(r["start_time"]).astimezone(timezone.utc)
            if dt > now_utc:
                continue
            valid_results.append((dt, r))
        except Exception:
            continue

    valid_results.sort(key=lambda x: x[0], reverse=True)
    top_results = [r for _, r in valid_results[:10]]

    if not top_results:
        await interaction.response.send_message("🏆 No finished match results recorded yet.", ephemeral=True)
        return

    lines = []
    for r in top_results:
        try:
            unix = int(datetime.fromisoformat(r["start_time"]).timestamp())
            when = f"<t:{unix}:d>"
        except Exception:
            when = r["start_time"][:10]
        icon = "🛡️" if r["game"].upper() == "MPL" else "🎯"
        lines.append(f"{icon} **#{r['id']} {r['game'].upper()}** ({when}) — **{r['team_a']}** `{r['score_a']} – {r['score_b']}` **{r['team_b']}**")

    embed = discord.Embed(
        title="🏆 OFFICIAL MATCH RESULTS",
        description="\n\n".join(lines),
        colour=discord.Colour.from_rgb(16, 185, 129)
    )
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="vote", description="Predict the winner of an upcoming or live match.", guild=GUILD)
async def vote(interaction: discord.Interaction, match_id: int, team: str):
    cursor.execute("SELECT * FROM matches WHERE id=?", (match_id,))
    row = cursor.fetchone()
    if not row:
        await interaction.response.send_message("❌ Match ID not found.", ephemeral=True)
        return
    if row["status"] == "FINISHED":
        await interaction.response.send_message("❌ Voting is closed for this match.", ephemeral=True)
        return

    team_clean = team.strip()
    if team_clean.lower() not in (row["team_a"].lower(), row["team_b"].lower()):
        await interaction.response.send_message(
            f"❌ Invalid team. Choose **{row['team_a']}** or **{row['team_b']}**.",
            ephemeral=True
        )
        return

    chosen = row["team_a"] if team_clean.lower() == row["team_a"].lower() else row["team_b"]
    ensure_user(interaction.user.id)
    cursor.execute(
        "INSERT INTO votes(match_id, user_id, choice) VALUES (?, ?, ?) ON CONFLICT(match_id, user_id) DO UPDATE SET choice=excluded.choice",
        (match_id, interaction.user.id, chosen)
    )
    db.commit()
    await interaction.response.send_message(
        f"🔮 Locked in your prediction for **{chosen}** in Match **#{match_id}** ({row['team_a']} vs {row['team_b']})!",
        ephemeral=True
    )


@bot.tree.command(name="match", description="Admin: Manually create a Watch Party match card.", guild=GUILD)
async def match(interaction: discord.Interaction, game: str, team_a: str, team_b: str, minutes_from_now: int = 60):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Admin only.", ephemeral=True)
        return

    game_up = game.upper()
    if game_up not in ("MPL", "VALORANT"):
        await interaction.response.send_message("❌ Game must be `mpl` or `valorant`.", ephemeral=True)
        return

    start_dt = datetime.now(timezone.utc) + timedelta(minutes=minutes_from_now)
    cursor.execute(
        """INSERT INTO matches (game, team_a, team_b, start_time, status, score_a, score_b, channel_id, source, created_at)
           VALUES (?, ?, ?, ?, 'UPCOMING', 0, 0, 1, 'manual', ?)""",
        (game_up, team_a.upper(), team_b.upper(), start_dt.isoformat(), now_iso())
    )
    db.commit()
    match_id = cursor.lastrowid

    await route_match_announcement(interaction.guild, match_id, target_state=1)
    await interaction.response.send_message(f"✅ Created Match **#{match_id}**: **{team_a.upper()}** vs **{team_b.upper()}**!", ephemeral=True)


@bot.tree.command(name="profile", description="Check your student profile, XP, Coins, and House.", guild=GUILD)
async def profile(interaction: discord.Interaction, member: discord.Member = None):
    target = member or interaction.user
    ensure_user(target.id)
    cursor.execute("SELECT * FROM users WHERE user_id=?", (target.id,))
    u = cursor.fetchone()

    embed = discord.Embed(
        title=f"🪪 STUDENT RECORD — {target.display_name}",
        colour=discord.Colour.gold()
    )
    embed.add_field(name="🏛️ House", value=f"**{u['house']}**", inline=True)
    embed.add_field(name="✨ XP", value=f"`{u['xp']}`", inline=True)
    embed.add_field(name="🪙 Coins", value=f"`{u['coins']}`", inline=True)
    embed.add_field(name="🏆 Esports Points", value=f"`{u['mpl_points']}`", inline=True)
    embed.add_field(name="⭐ Reputation", value=f"`{u['reputation']}`", inline=True)
    embed.add_field(name="💬 Messages", value=f"`{u['messages']}`", inline=True)
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="leaderboard", description="View top students ranked by XP, Coins, or Esports Points.", guild=GUILD)
async def leaderboard(interaction: discord.Interaction):
    cursor.execute("SELECT * FROM users ORDER BY xp DESC, mpl_points DESC LIMIT 10")
    rows = cursor.fetchall()
    if not rows:
        await interaction.response.send_message("📊 No leaderboard data yet.", ephemeral=True)
        return

    lines = []
    for idx, r in enumerate(rows, 1):
        medal = "🥇" if idx == 1 else "🥈" if idx == 2 else "🥉" if idx == 3 else f"`#{idx}`"
        lines.append(f"{medal} <@{r['user_id']}> — ✨ `{r['xp']} XP` • 🪙 `{r['coins']}` • 🏆 `{r['mpl_points']} pts`")

    embed = discord.Embed(
        title="🏆 THE INSTITUTE — CAMPUS LEADERBOARD",
        description="\n".join(lines),
        colour=discord.Colour.gold()
    )
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="verify_channels", description="Admin: Audit sync status, DB counts, and bot permissions across all 7 esports channels.", guild=GUILD)
async def verify_channels(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Admin only.", ephemeral=True)
        return

    guild = interaction.guild
    me = guild.me

    target_slugs = [
        ("MPL Watch Party", "mpl-watch-party"),
        ("MPL Predictions", "mpl-predictions"),
        ("MPL Results", "mpl-results"),
        ("Valorant Watch Party", "valorant-watch-party"),
        ("Valorant Predictions", "valorant-predictions"),
        ("Valorant Results", "valorant-results"),
        ("Global Match Results", "match-results"),
    ]

    report_lines = []
    for label, slug in target_slugs:
        ch = get_channel(guild, slug)
        if not ch:
            report_lines.append(f"❌ **{label}** (`{slug}`) — Channel tidak ditemukan")
            continue
        perms = ch.permissions_for(me)
        ok_view = perms.view_channel
        ok_send = perms.send_messages
        ok_embed = perms.embed_links
        ok_purge = perms.manage_messages
        if ok_view and ok_send and ok_embed:
            perm_badge = "✅ Ready" + (" (Purge OK)" if ok_purge else " ⚠️ (No Manage Messages)")
        else:
            missing = [name for name, val in (("View", ok_view), ("Send", ok_send), ("Embed", ok_embed)) if not val]
            perm_badge = f"🚫 Kurang izin: `{', '.join(missing)}`"
        report_lines.append(f"• {ch.mention} — {perm_badge}")

    cursor.execute("SELECT game, status, COUNT(*) AS cnt FROM matches GROUP BY game, status")
    db_rows = cursor.fetchall()
    db_summary = [f"`{r['game']} • {r['status']}`: **{r['cnt']}**" for r in db_rows] or ["Belum ada data di tabel `matches`."]

    embed = discord.Embed(
        title="🔍 THE INSTITUTE — CHANNEL & SYNC AUDIT",
        description="\n".join(report_lines),
        colour=discord.Colour.from_rgb(59, 130, 246)
    )
    embed.add_field(name="🗄️ MySQL Database Match Counts", value="\n".join(db_summary), inline=False)
    embed.set_footer(text="Read-only audit • Gunakan /reset_schedules jika ingin menarik ulang seluruh data")
    await interaction.response.send_message(embed=embed, ephemeral=True)
# =========================================================
# LFG (LOOKING FOR GROUP) & HYPE BROADCAST MODULE
# =========================================================

class LFGJoinView(discord.ui.View):
    def __init__(self, game: str, host_name: str, max_slots: int = 5):
        super().__init__(timeout=10800) # Aktif selama 3 jam
        self.game = game
        self.host_name = host_name
        self.max_slots = max_slots
        self.members = [host_name]

        self.update_button()

    def update_button(self):
        self.join_btn.label = f"Join Squad ({len(self.members)}/{self.max_slots})"
        if len(self.members) >= self.max_slots:
            self.join_btn.disabled = True
            self.join_btn.style = discord.ButtonStyle.danger
            self.join_btn.label = "Squad Full 🚀"

    @discord.ui.button(label="Join Squad", style=discord.ButtonStyle.success, emoji="🎮", custom_id="lfg_join_btn")
    async def join_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        display_name = interaction.user.display_name
        if display_name in self.members:
            await interaction.response.send_message("⚠️ Kamu sudah bergabung di squad ini!", ephemeral=True)
            return

        if len(self.members) < self.max_slots:
            self.members.append(display_name)
            self.update_button()

            member_list = "\n".join([f"• {m}" + (" 👑 (Host)" if i == 0 else "") for i, m in enumerate(self.members)])
            embed = interaction.message.embeds[0]
            embed.set_field_at(0, name=f"👥 Members ({len(self.members)}/{self.max_slots})", value=member_list, inline=False)

            if len(self.members) >= self.max_slots:
                embed.add_field(name="🚀 Status", value="**Squad Penuh!** Silakan masuk ke Voice Channel mabar.", inline=False)
                self.stop()

            await interaction.response.edit_message(embed=embed, view=self)
            if len(self.members) >= self.max_slots:
                await interaction.followup.send(f"🎉 Squad **{self.game}** sudah lengkap! Silakan masuk ke voice channel bersama.", ephemeral=False)
        else:
            await interaction.response.send_message("❌ Maaf, squad sudah penuh!", ephemeral=True)


@bot.tree.command(name="lfg", description="Buat party mabar (LFG) instan di channel Looking For Group.", guild=GUILD)
async def lfg(interaction: discord.Interaction, game: str, mode: str = "Ranked / Competitive", max_slots: int = 5):
    game_up = game.upper()
    if game_up not in ("ML", "MOBILE LEGENDS", "VALORANT", "VALO"):
        await interaction.response.send_message("❌ Game harus `Mobile Legends` atau `Valorant`.", ephemeral=True)
        return

    game_title = "Mobile Legends: Bang Bang" if "ML" in game_up or "MOBILE" in game_up else "Valorant"
    host = interaction.user.display_name

    embed = discord.Embed(
        title=f"🔎 LFG • SQUAD MABAR {game_title.upper()}",
        description=f"**Host:** {interaction.user.mention}\n**Mode:** `{mode}`\n\nTekan tombol di bawah untuk bergabung ke dalam squad!",
        colour=discord.Colour.from_rgb(59, 130, 246)
    )
    embed.add_field(name=f"👥 Members (1/{max_slots})", value=f"• {host} 👑 (Host)", inline=False)
    embed.set_footer(text="THE INSTITUTE • Looking For Group System")

    view = LFGJoinView(game=game_title, host_name=host, max_slots=max_slots)

    # Kirim ke channel LFG secara otomatis
    lfg_ch = get_channel(interaction.guild, "looking-for-group")
    target_ch = lfg_ch or interaction.channel

    await target_ch.send(embed=embed, view=view)
    if target_ch != interaction.channel:
        await interaction.response.send_message(f"✅ Sesi LFG berhasil disiarkan ke {target_ch.mention}!", ephemeral=True)
    else:
        await interaction.response.send_message("✅ Sesi LFG berhasil dibuat!", ephemeral=True)


@bot.tree.command(name="refresh_leaderboard", description="Admin: Perbarui papan klasemen poin dan XP di channel leaderboards.", guild=GUILD)
async def refresh_leaderboard(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Admin only.", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)
    guild = interaction.guild
    lb_ch = get_channel(guild, "leaderboards")
    if not lb_ch:
        await interaction.followup.send("❌ Channel `#📊・leaderboards` tidak ditemukan.", ephemeral=True)
        return

    # Bersihkan pesan lama bot di channel leaderboard
    try:
        await lb_ch.purge(limit=20, check=lambda m: m.author == guild.me)
    except Exception:
        pass

    cursor.execute("SELECT * FROM users ORDER BY xp DESC, mpl_points DESC LIMIT 10")
    rows = cursor.fetchall()
    if not rows:
        await lb_ch.send("📊 Belum ada data mahasiswa di leaderboard.")
        await interaction.followup.send("✅ Leaderboard dibersihkan (belum ada data).", ephemeral=True)
        return

    lines = []
    for idx, r in enumerate(rows, 1):
        medal = "🥇" if idx == 1 else "🥈" if idx == 2 else "🥉" if idx == 3 else f"`#{idx}`"
        lines.append(f"{medal} <@{r['user_id']}> — ✨ `{r['xp']} XP` • 🪙 `{r['coins']}` • 🏆 `{r['mpl_points']} pts`")

    embed = discord.Embed(
        title="🏆 THE INSTITUTE — CAMPUS HALL OF FAME",
        description="Papan peringkat mahasiswa teraktif berdasarkan perolehan XP, Koin, dan Prediksi Esports.\n\n" + "\n".join(lines),
        colour=discord.Colour.gold()
    )
    embed.set_footer(text="Diperbarui secara otomatis • Terus aktif di server untuk naik peringkat!")
    
    await lb_ch.send(embed=embed)
    await interaction.followup.send("✅ Papan klasemen Hall of Fame berhasil diperbarui di `#📊・leaderboards`!", ephemeral=True)
import addons_all_in_one
addons_all_in_one.setup_all_in_one(bot, GUILD, db, cursor, get_channel)

bot.run(TOKEN)

