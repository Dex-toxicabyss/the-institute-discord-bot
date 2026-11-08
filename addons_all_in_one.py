import os
import random
import json
import asyncio
import datetime
import urllib.request
import discord
from discord import app_commands

# =========================================================
# 0. LINEAR + APPLE HIG DESIGN SYSTEM FOR DISCORD UI
# =========================================================

class UI:
    INDIGO  = discord.Colour.from_rgb(94, 106, 210)   # #5E6AD2 Linear Primary
    BLUE    = discord.Colour.from_rgb(0, 113, 227)    # #0071E3 Apple System Blue
    EMERALD = discord.Colour.from_rgb(16, 185, 129)   # #10B981 Semantic Success
    AMBER   = discord.Colour.from_rgb(245, 158, 11)   # #F59E0B Gold / Championship
    CRIMSON = discord.Colour.from_rgb(239, 68, 68)    # #EF4444 Alert / Moderation / Live
    SURFACE = discord.Colour.from_rgb(38, 39, 46)     # #26272E Linear Raised Dark Surface
    DIVIDER = "──────────────────────────────"

    @staticmethod
    def bar(value: float, total: float, length: int = 10) -> str:
        if total <= 0:
            return "▱" * length + " `0%`"
        ratio = max(0.0, min(1.0, value / total))
        filled = round(ratio * length)
        pct = int(ratio * 100)
        return ("▰" * filled) + ("▱" * (length - filled)) + f" `{pct}%`"

    @staticmethod
    def card(eyebrow: str, title: str, description: str = "", colour: discord.Colour = None) -> discord.Embed:
        header = f"`THE INSTITUTE // {eyebrow.upper()}`\n### {title}"
        body = f"{header}\n{UI.DIVIDER}\n{description}" if description else f"{header}\n{UI.DIVIDER}"
        emb = discord.Embed(
            description=body,
            colour=colour or UI.INDIGO,
            timestamp=datetime.datetime.now(datetime.timezone.utc),
        )
        emb.set_footer(text="THE INSTITUTE OS v3.0 • Gasak Galo")
        return emb


# =========================================================
# 1. ARCHIVE DATA: MPL & VCT SEASONS + HALL OF CHAMPIONS
# =========================================================

SEASON_ARCHIVES = {
    "MPL": {
        "MPL ID Season 14": [
            ("Team Liquid ID", "RRQ Hoshi", 4, 3, "Grand Final"),
            ("RRQ Hoshi", "Team Liquid ID", 3, 1, "Upper Bracket Final"),
            ("Bigetron Alpha", "Geek Fam", 3, 0, "Playoffs R1"),
            ("Fnatic ONIC", "Geek Fam", 2, 3, "Playoffs R1"),
        ],
        "MPL ID Season 13": [
            ("Fnatic ONIC", "EVOS Glory", 4, 2, "Grand Final"),
            ("EVOS Glory", "Geek Fam", 3, 2, "Lower Bracket Final"),
            ("Bigetron Alpha", "Aura Fire", 3, 0, "Regular Season"),
        ],
        "MPL ID Season 12": [
            ("ONIC Esports", "Geek Fam", 4, 2, "Grand Final"),
            ("Rex Regum Qeon", "Bigetron Alpha", 1, 3, "Playoffs"),
        ],
    },
    "VALORANT": {
        "VCT Pacific 2024 • Stage 2": [
            ("Gen.G", "DRX", 3, 1, "Grand Final"),
            ("Paper Rex", "DRX", 2, 3, "Lower Bracket Final"),
            ("Team Secret", "Talon Esports", 2, 0, "Knockouts"),
            ("Rex Regum Qeon", "DetonatioN FocusMe", 2, 0, "Group Stage"),
        ],
        "VCT Pacific 2024 • Stage 1": [
            ("Paper Rex", "Gen.G", 3, 2, "Grand Final"),
            ("T1", "Gen.G", 0, 3, "Lower Bracket Final"),
            ("DRX", "Team Secret", 2, 1, "Group Alpha"),
        ],
        "VCT Pacific 2024 • Kickoff": [
            ("Gen.G", "Paper Rex", 3, 1, "Grand Final"),
            ("DRX", "T1", 2, 0, "Semifinals"),
            ("Rex Regum Qeon", "Gen.G", 1, 2, "Play-Ins"),
        ],
        "VCT Champions 2024 • Seoul": [
            ("EDward Gaming", "Team Heretics", 3, 2, "World Grand Final"),
            ("Sentinels", "Fnatic", 2, 1, "Upper Quarterfinals"),
            ("DRX", "Trace Esports", 2, 0, "Playoffs"),
        ],
    },
}

CHAMPIONS_LEDGER = {
    "MPL": [
        ("MPL ID Season 14", "Team Liquid ID", "RRQ Hoshi", "4 - 3", "AeronnShikii"),
        ("MPL ID Season 13", "Fnatic ONIC", "EVOS Glory", "4 - 2", "CW"),
        ("MPL ID Season 12", "ONIC Esports", "Geek Fam", "4 - 2", "Kiboy"),
        ("MPL ID Season 11", "ONIC Esports", "EVOS Legends", "4 - 0", "Sanz"),
        ("MPL ID Season 10", "ONIC Esports", "RRQ Hoshi", "4 - 1", "Kairi"),
    ],
    "VALORANT": [
        ("VCT Champions 2024", "EDward Gaming", "Team Heretics", "3 - 2", "ZmjjKK"),
        ("VCT Masters Shanghai", "Gen.G", "Team Heretics", "3 - 2", "t3xture"),
        ("VCT Pacific Stage 2", "Gen.G", "DRX", "3 - 1", "Meteor"),
        ("VCT Pacific Stage 1", "Paper Rex", "Gen.G", "3 - 2", "f0rsakeN"),
        ("VCT Pacific 2023", "Paper Rex", "DRX", "3 - 2", "something"),
    ],
}

TRIVIA_BANK = [
    {
        "q": "Siapakah tim yang menjuarai MPL Indonesia Season 14 setelah mengalahkan RRQ Hoshi 4-3?",
        "options": ["Team Liquid ID", "Fnatic ONIC", "Bigetron Alpha", "EVOS Glory"],
        "answer": 0,
        "topic": "MPL ID History",
    },
    {
        "q": "Tim manakah yang berhasil menjuarai VCT Champions 2024 di Seoul?",
        "options": ["Paper Rex", "Team Heretics", "EDward Gaming", "Sentinels"],
        "answer": 2,
        "topic": "VCT Global",
    },
    {
        "q": "Siapakah peraih gelar Finals MVP pada Grand Final VCT Pacific Stage 1 2024 bersama Paper Rex?",
        "options": ["mindfreak", "f0rsakeN", "d4v41", "something"],
        "answer": 1,
        "topic": "VCT Pacific",
    },
    {
        "q": "Berapa batas waktu maksimal jadwal pertandingan yang masuk ke kategori Upcoming Schedule di bot ini?",
        "options": ["3 Hari", "7 Hari", "14 Hari", "30 Hari"],
        "answer": 1,
        "topic": "The Institute System",
    },
]


# =========================================================
# 2. INTERACTIVE VIEWS: ROLES, GIVEAWAY, TRIVIA, TICKETS, MUSIC
# =========================================================

class SelfRoleView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    async def _toggle_role(self, interaction: discord.Interaction, role_name: str, colour: discord.Colour):
        guild = interaction.guild
        role = discord.utils.find(lambda r: r.name.lower() == role_name.lower(), guild.roles)
        if not role:
            try:
                role = await guild.create_role(name=role_name, colour=colour, mentionable=True, reason="Auto-created by SelfRoleView")
            except Exception as e:
                await interaction.response.send_message(
                    f"Gagal membuat role `{role_name}`. Pastikan bot punya izin `Manage Roles` ({e}).",
                    ephemeral=True,
                )
                return

        if role in interaction.user.roles:
            try:
                await interaction.user.remove_roles(role)
                await interaction.response.send_message(f"Role {role.mention} dilepas dari profilmu.", ephemeral=True)
            except Exception as e:
                await interaction.response.send_message(f"Gagal melepas role (`{e}`). Pastikan posisi role bot berada di atas role tersebut.", ephemeral=True)
        else:
            try:
                await interaction.user.add_roles(role)
                await interaction.response.send_message(f"Role {role.mention} berhasil dipasang ke profilmu!", ephemeral=True)
            except Exception as e:
                await interaction.response.send_message(f"Gagal memasang role (`{e}`). Pastikan posisi role bot berada di atas role tersebut.", ephemeral=True)

    @discord.ui.button(label="MPL ID Roster", style=discord.ButtonStyle.primary, custom_id="sr_mpl")
    async def role_mpl(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._toggle_role(interaction, "MPL Watchers", UI.AMBER)

    @discord.ui.button(label="VCT Pacific Roster", style=discord.ButtonStyle.danger, custom_id="sr_vct")
    async def role_vct(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._toggle_role(interaction, "VCT Agents", UI.CRIMSON)

    @discord.ui.button(label="Mabar Squad (LFG)", style=discord.ButtonStyle.success, custom_id="sr_lfg")
    async def role_lfg(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._toggle_role(interaction, "Mabar Ready", UI.EMERALD)

    @discord.ui.button(label="Watch Party Ping", style=discord.ButtonStyle.secondary, custom_id="sr_wp")
    async def role_wp(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._toggle_role(interaction, "Watch Party Insider", UI.BLUE)


class GiveawayJoinView(discord.ui.View):
    def __init__(self, giveaway_id: int, prize: str, coins_bonus: int, db, cursor):
        super().__init__(timeout=None)
        self.giveaway_id = giveaway_id
        self.prize = prize
        self.coins_bonus = coins_bonus
        self.db = db
        self.cursor = cursor

    @discord.ui.button(label="Enter Giveaway (0 Joined)", style=discord.ButtonStyle.success, custom_id="gw_join_btn")
    async def join_giveaway(self, interaction: discord.Interaction, button: discord.ui.Button):
        uid = interaction.user.id
        self.cursor.execute(
            "SELECT id FROM giveaway_entries WHERE giveaway_id = ? AND user_id = ?",
            (self.giveaway_id, uid),
        )
        if self.cursor.fetchone():
            await interaction.response.send_message("Kamu sudah terdaftar di giveaway ini!", ephemeral=True)
            return

        self.cursor.execute(
            "INSERT INTO giveaway_entries (giveaway_id, user_id) VALUES (?, ?)",
            (self.giveaway_id, uid),
        )
        self.db.commit()

        self.cursor.execute("SELECT COUNT(*) AS cnt FROM giveaway_entries WHERE giveaway_id = ?", (self.giveaway_id,))
        total = self.cursor.fetchone()["cnt"]
        odds = round((1 / max(1, total)) * 100, 1)

        button.label = f"Enter Giveaway ({total} Joined)"
        emb = interaction.message.embeds[0]
        if len(emb.fields) >= 2:
            emb.set_field_at(1, name="PARTICIPANTS", value=f"`{total} Users` (`{odds}%` win rate)", inline=True)
        await interaction.response.edit_message(embed=emb, view=self)
        await interaction.followup.send(f"Kamu berhasil masuk undian **{self.prize}**! Peluang saat ini: `{odds}%`.", ephemeral=True)


class TriviaView(discord.ui.View):
    def __init__(self, item: dict, db, cursor, add_reward_fn):
        super().__init__(timeout=60)
        self.item = item
        self.db = db
        self.cursor = cursor
        self.add_reward = add_reward_fn
        self.answered_users = set()

        for idx, opt_text in enumerate(item["options"]):
            btn = discord.ui.Button(
                label=f"{chr(65 + idx)}. {opt_text}",
                style=discord.ButtonStyle.secondary,
                custom_id=f"trv_{idx}",
            )
            btn.callback = self._make_callback(idx, opt_text)
            self.add_item(btn)

    def _make_callback(self, idx: int, opt_text: str):
        async def callback(interaction: discord.Interaction):
            if interaction.user.id in self.answered_users:
                await interaction.response.send_message("Kamu sudah menjawab kuis ini!", ephemeral=True)
                return
            self.answered_users.add(interaction.user.id)

            if idx == self.item["answer"]:
                self.add_reward(interaction.user.id, coins_delta=150, xp_delta=50)
                for child in self.children:
                    child.disabled = True
                emb = UI.card(
                    "MINI GAMES // TRIVIA WINNER",
                    self.item["q"],
                    (
                        f"**Pemenang Cepat:** {interaction.user.mention}\n"
                        f"**Jawaban Benar:** `{opt_text}`\n"
                        f"**Hadiah Diterima:** `+150 Coins` & `+50 XP`"
                    ),
                    UI.EMERALD,
                )
                await interaction.response.edit_message(embed=emb, view=self)
            else:
                await interaction.response.send_message(
                    f"Jawaban `{opt_text}` kurang tepat! Coba lagi di sesi berikutnya.",
                    ephemeral=True,
                )
        return callback


class TicketCloseView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Close Ticket", style=discord.ButtonStyle.danger, custom_id="ticket_close_btn")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Menutup channel tiket dalam 3 detik...", ephemeral=False)
        await asyncio.sleep(3)
        try:
            await interaction.channel.delete(reason=f"Ticket closed by {interaction.user}")
        except Exception:
            pass


class TicketLaunchView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    async def _create_ticket(self, interaction: discord.Interaction, category_label: str):
        guild = interaction.guild
        safe_name = "".join(c for c in interaction.user.name.lower() if c.isalnum())[:12]
        ch_name = f"ticket-{safe_name}"

        existing = discord.utils.get(guild.text_channels, name=ch_name)
        if existing:
            await interaction.response.send_message(f"Tiket aktif kamu sudah ada di {existing.mention}.", ephemeral=True)
            return

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True),
        }
        for role in guild.roles:
            if role.permissions.administrator or role.permissions.manage_guild:
                overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True)

        try:
            ticket_ch = await guild.create_text_channel(
                name=ch_name,
                overwrites=overwrites,
                topic=f"Ticket {category_label} | User: {interaction.user} ({interaction.user.id})",
            )
        except Exception as e:
            await interaction.response.send_message(f"Gagal membuat channel tiket (`{e}`). Pastikan izin `Manage Channels` aktif.", ephemeral=True)
            return

        emb = UI.card(
            f"SUPPORT DESK // {category_label}",
            f"Ticket #{safe_name.upper()}",
            (
                f"Halo {interaction.user.mention}, silakan jelaskan detail kebutuhanmu di bawah ini.\n"
                f"Moderator akan segera bergabung ke ruang privat ini.\n\n"
                f"**Category:** `{category_label}`\n"
                f"**Opened:** <t:{int(datetime.datetime.now(datetime.timezone.utc).timestamp())}:R>"
            ),
            UI.INDIGO,
        )
        await ticket_ch.send(embed=emb, view=TicketCloseView())
        await interaction.response.send_message(f"Ruang tiket privat berhasil dibuat: {ticket_ch.mention}", ephemeral=True)

    @discord.ui.button(label="Moderation Report", style=discord.ButtonStyle.danger, custom_id="tkt_report")
    async def btn_report(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._create_ticket(interaction, "Moderation Report")

    @discord.ui.button(label="Tournament Desk", style=discord.ButtonStyle.primary, custom_id="tkt_tourney")
    async def btn_tourney(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._create_ticket(interaction, "Tournament Verification")

    @discord.ui.button(label="General Support", style=discord.ButtonStyle.secondary, custom_id="tkt_help")
    async def btn_help(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._create_ticket(interaction, "General Support")


class HypeMeterView(discord.ui.View):
    def __init__(self, label_a: str, label_b: str):
        super().__init__(timeout=None)
        self.count_a = 1
        self.count_b = 1
        self.label_a = label_a
        self.label_b = label_b
        self.btn_a.label = f"Support {label_a} (1)"
        self.btn_b.label = f"Support {label_b} (1)"

    async def _refresh(self, interaction: discord.Interaction):
        total = self.count_a + self.count_b
        emb = interaction.message.embeds[0]
        bar_str = f"**{self.label_a}** {UI.bar(self.count_a, total, 10)} **{self.label_b}**"
        if emb.fields:
            emb.set_field_at(0, name="LIVE CROWD PULSE", value=bar_str, inline=False)
        else:
            emb.add_field(name="LIVE CROWD PULSE", value=bar_str, inline=False)
        await interaction.response.edit_message(embed=emb, view=self)

    @discord.ui.button(label="Team A", style=discord.ButtonStyle.primary, custom_id="hype_btn_a")
    async def btn_a(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.count_a += 1
        button.label = f"Support {self.label_a} ({self.count_a})"
        await self._refresh(interaction)

    @discord.ui.button(label="Team B", style=discord.ButtonStyle.success, custom_id="hype_btn_b")
    async def btn_b(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.count_b += 1
        button.label = f"Support {self.label_b} ({self.count_b})"
        await self._refresh(interaction)


class TournamentRegView(discord.ui.View):
    def __init__(self, title: str, max_teams: int):
        super().__init__(timeout=None)
        self.title = title
        self.max_teams = max_teams
        self.teams = []

    @discord.ui.button(label="Register Roster (0 Slots)", style=discord.ButtonStyle.success, custom_id="tourney_reg_btn")
    async def reg_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        team_entry = f"`{interaction.user.display_name}'s Squad` ({interaction.user.mention})"
        if any(interaction.user.mention in t for t in self.teams):
            await interaction.response.send_message("Roster kamu sudah terdaftar di turnamen ini.", ephemeral=True)
            return
        if len(self.teams) >= self.max_teams:
            await interaction.response.send_message("Slot turnamen sudah penuh.", ephemeral=True)
            return

        self.teams.append(team_entry)
        button.label = f"Register Roster ({len(self.teams)}/{self.max_teams})"
        if len(self.teams) >= self.max_teams:
            button.disabled = True
            button.label = "Bracket Locked (Full)"

        embed = interaction.message.embeds[0]
        team_lines = "\n".join(f"`0{i}` {t}" for i, t in enumerate(self.teams, 1))
        embed.set_field_at(
            0,
            name=f"REGISTERED ROSTERS ({len(self.teams)}/{self.max_teams})",
            value=f"{UI.bar(len(self.teams), self.max_teams, 10)}\n{team_lines}",
            inline=False,
        )
        await interaction.response.edit_message(embed=embed, view=self)
        await interaction.followup.send(f"Roster **{team_entry}** resmi terdaftar di **{self.title}**!", ephemeral=True)


# =========================================================
# 3. MUSIC ENGINE & AI ASSISTANT
# =========================================================

MUSIC_QUEUES = {}

YTDL_OPTIONS = {
    "format": "bestaudio/best",
    "noplaylist": True,
    "quiet": True,
    "default_search": "ytsearch",
    "source_address": "0.0.0.0",
}

FFMPEG_OPTIONS = {
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
    "options": "-vn",
}


def extract_audio_info(query: str) -> dict:
    import yt_dlp
    with yt_dlp.YoutubeDL(YTDL_OPTIONS) as ydl:
        info = ydl.extract_info(query, download=False)
        if "entries" in info:
            info = info["entries"][0]
        return {
            "title": info.get("title", "Unknown Track"),
            "url": info["url"],
            "webpage": info.get("webpage_url", ""),
            "duration": info.get("duration", 0),
        }


class MusicControlView(discord.ui.View):
    def __init__(self, bot_instance):
        super().__init__(timeout=None)
        self.bot = bot_instance

    @discord.ui.button(label="Pause / Resume", style=discord.ButtonStyle.secondary, custom_id="music_pause")
    async def pause_resume(self, interaction: discord.Interaction, button: discord.ui.Button):
        vc = interaction.guild.voice_client
        if not vc:
            await interaction.response.send_message("Bot sedang tidak berada di voice channel.", ephemeral=True)
            return
        if vc.is_playing():
            vc.pause()
            await interaction.response.send_message("Playback paused.", ephemeral=True)
        elif vc.is_paused():
            vc.resume()
            await interaction.response.send_message("Playback resumed.", ephemeral=True)
        else:
            await interaction.response.send_message("Tidak ada audio aktif.", ephemeral=True)

    @discord.ui.button(label="Skip Track", style=discord.ButtonStyle.primary, custom_id="music_skip")
    async def skip_track(self, interaction: discord.Interaction, button: discord.ui.Button):
        vc = interaction.guild.voice_client
        if vc and (vc.is_playing() or vc.is_paused()):
            vc.stop()
            await interaction.response.send_message("Track skipped.", ephemeral=False)
        else:
            await interaction.response.send_message("Tidak ada antrean untuk di-skip.", ephemeral=True)

    @discord.ui.button(label="Disconnect", style=discord.ButtonStyle.danger, custom_id="music_stop")
    async def stop_music(self, interaction: discord.Interaction, button: discord.ui.Button):
        vc = interaction.guild.voice_client
        MUSIC_QUEUES.pop(interaction.guild.id, None)
        if vc:
            await vc.disconnect()
            await interaction.response.send_message("Audio session terminated.", ephemeral=False)
        else:
            await interaction.response.send_message("Bot sudah di luar voice channel.", ephemeral=True)


def query_ai_assistant(prompt: str, user_name: str) -> str:
    groq_key = os.getenv("GROQ_API_KEY", "").strip()
    gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
    system_prompt = (
        "Kamu adalah AI resmi server Discord 'Gasak Galo' (THE INSTITUTE). "
        "Jawab dengan bahasa Indonesia yang tajam, ringkas, tanpa basa-basi robotik. "
        "Kamu ahli di MPL Indonesia, VCT Pacific/Champions, pengembangan software, dan fitur server."
    )

    if groq_key:
        try:
            payload = json.dumps({
                "model": "llama-3.3-70b-versatile",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"[{user_name}]: {prompt}"},
                ],
                "max_tokens": 500,
                "temperature": 0.6,
            }).encode("utf-8")
            req = urllib.request.Request(
                "https://api.groq.com/openai/v1/chat/completions",
                data=payload,
                headers={"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json", "User-Agent": "Mozilla/5.0"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=12) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data["choices"][0]["message"]["content"].strip()
        except Exception as e:
            return f"Koneksi GROQ API gagal (`{e}`)."

    if gemini_key:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={gemini_key}"
            payload = json.dumps({
                "contents": [{"parts": [{"text": f"{system_prompt}\n\nUser ({user_name}): {prompt}"}]}]
            }).encode("utf-8")
            req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"}, method="POST")
            with urllib.request.urlopen(req, timeout=12) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data["candidates"][0]["content"]["parts"][0]["text"].strip()
        except Exception as e:
            return f"Koneksi Gemini API gagal (`{e}`)."

    p_low = prompt.lower()
    if "mpl" in p_low or "juara" in p_low:
        return (
            "**Arsip Juara MPL ID:**\n"
            "• `S14` **Team Liquid ID** (4-3 vs RRQ Hoshi)\n"
            "• `S13` **Fnatic ONIC** (4-2 vs EVOS Glory)\n"
            "• `S12` **ONIC Esports** (4-2 vs Geek Fam)\n"
            "Jalankan `/champions game:mpl` atau `/season_results game:mpl` untuk tabel lengkap."
        )
    if "vct" in p_low or "valorant" in p_low:
        return (
            "**Arsip Juara VCT:**\n"
            "• `Champions 2024` **EDward Gaming** (3-2 vs Team Heretics)\n"
            "• `Pacific Stage 2` **Gen.G** (3-1 vs DRX)\n"
            "• `Pacific Stage 1` **Paper Rex** (3-2 vs Gen.G)\n"
            "Jalankan `/champions game:valorant` atau `/season_results game:valorant`."
        )
    return (
        f"Halo **{user_name}**, modul AI berjalan dalam mode lokal. "
        f"Tambahkan `GROQ_API_KEY` atau `GEMINI_API_KEY` di Railway Variables untuk mengaktifkan LLM penuh. "
        f"Command populer: `/server_stats`, `/giveaway_start`, `/coinflip`, `/slots`, `/trivia`, `/role_panel`."
    )


# =========================================================
# 4. MAIN SETUP & EVENT LISTENERS
# =========================================================

def setup_all_in_one(bot: discord.Client, guild_obj: discord.Object, db, cursor, get_channel):
    # Ensure database schema for seasons, warnings, and giveaways
    try:
        cursor.execute("ALTER TABLE matches ADD COLUMN season VARCHAR(80) DEFAULT 'Current Season'")
        db.commit()
    except Exception:
        pass

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS mod_warnings (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id BIGINT,
            moderator_id BIGINT,
            reason TEXT,
            created_at VARCHAR(40)
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS giveaways (
            id INT AUTO_INCREMENT PRIMARY KEY,
            prize VARCHAR(255),
            coins_bonus INT DEFAULT 500,
            host_id BIGINT,
            status VARCHAR(20) DEFAULT 'ACTIVE',
            created_at VARCHAR(40)
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS giveaway_entries (
            id INT AUTO_INCREMENT PRIMARY KEY,
            giveaway_id INT,
            user_id BIGINT
        )
        """
    )
    db.commit()

    # Helper Economy: Tambah/Kurangi Coins & XP
    def update_user_economy(user_id: int, coins_delta: int = 0, xp_delta: int = 0) -> dict:
        cursor.execute("SELECT user_id, coins, xp FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        if not row:
            init_coins = max(0, 500 + coins_delta)
            init_xp = max(0, 100 + xp_delta)
            cursor.execute(
                "INSERT INTO users (user_id, house, xp, coins, mpl_points, rep) VALUES (?, 'Rosethorn', ?, ?, 0, 0)",
                (user_id, init_xp, init_coins),
            )
            db.commit()
            return {"coins": init_coins, "xp": init_xp}
        new_coins = max(0, int(row["coins"]) + coins_delta)
        new_xp = max(0, int(row["xp"]) + xp_delta)
        cursor.execute("UPDATE users SET coins = ?, xp = ? WHERE user_id = ?", (new_coins, new_xp, user_id))
        db.commit()
        return {"coins": new_coins, "xp": new_xp}

    # Helper Log Finder
    def find_log_channel(guild: discord.Guild):
        for slug in ("mod-logs", "server-logs", "audit-logs", "logs"):
            ch = get_channel(guild, slug)
            if ch:
                return ch
        return None

    # ---------------------------------------------------------
    # EVENT LISTENERS: LOGGING, WELCOME, & AUTO-ROLE
    # ---------------------------------------------------------

    async def on_member_join_listener(member: discord.Member):
        if member.guild.id != guild_obj.id:
            return
        guild = member.guild

        # 1. Auto-Role Assignment
        auto_role = None
        for r_slug in ("member", "student", "warga", "verified", "initiate"):
            auto_role = discord.utils.find(lambda r: r_slug in r.name.lower(), guild.roles)
            if auto_role:
                break
        if auto_role:
            try:
                await member.add_roles(auto_role, reason="The Institute Auto-Role")
            except Exception:
                pass

        # 2. Welcome Card Broadcast
        welcome_ch = get_channel(guild, "welcome") or get_channel(guild, "general") or guild.system_channel
        if welcome_ch:
            created_ts = int(member.created_at.timestamp())
            role_label = auto_role.mention if auto_role else "`Default Access`"
            emb = UI.card(
                "ONBOARDING // NEW ARRIVAL",
                f"Welcome to {guild.name}",
                (
                    f"Selamat datang {member.mention} di pusat komunitas & *broadcast hub* **Gasak Galo**.\n\n"
                    f"**Member Index:** `#{guild.member_count}`\n"
                    f"**Auto-Assigned Role:** {role_label}\n"
                    f"**Account Created:** <t:{created_ts}:R>\n\n"
                    f"**Quick Navigation:**\n"
                    f"• Cek jadwal & voting: `/matches` atau `/season_results`\n"
                    f"• Cari teman mabar: `/lfg` di channel Looking For Group\n"
                    f"• Klaim koin & mini games: `/trivia`, `/coinflip`, `/slots`"
                ),
                UI.BLUE,
            )
            if member.display_avatar:
                emb.set_thumbnail(url=member.display_avatar.url)
            try:
                await welcome_ch.send(content=member.mention, embed=emb)
            except Exception:
                pass

        # 3. Audit Log
        log_ch = find_log_channel(guild)
        if log_ch:
            log_emb = UI.card(
                "SECURITY LOG // MEMBER JOIN",
                f"{member} Joined",
                f"**User:** {member.mention} (`{member.id}`)\n**Population:** `{guild.member_count} Members`",
                UI.EMERALD,
            )
            try:
                await log_ch.send(embed=log_emb)
            except Exception:
                pass

    async def on_member_remove_listener(member: discord.Member):
        if member.guild.id != guild_obj.id:
            return
        log_ch = find_log_channel(member.guild)
        if log_ch:
            emb = UI.card(
                "SECURITY LOG // MEMBER LEFT",
                f"{member} Departed",
                f"**User:** `{member}` (`{member.id}`)\n**Population:** `{member.guild.member_count} Members`",
                UI.AMBER,
            )
            try:
                await log_ch.send(embed=emb)
            except Exception:
                pass

    async def on_message_delete_listener(message: discord.Message):
        if not message.guild or message.guild.id != guild_obj.id or message.author.bot:
            return
        log_ch = find_log_channel(message.guild)
        if not log_ch:
            return
        content = (message.content or "[Attachment / Embed Only]")[:900]
        emb = UI.card(
            "AUDIT LOG // MESSAGE DELETED",
            f"Deleted in #{message.channel.name}",
            (
                f"**Author:** {message.author.mention} (`{message.author.id}`)\n"
                f"**Channel:** {message.channel.mention}\n"
                f"**Content:**\n```\n{content}\n```"
            ),
            UI.CRIMSON,
        )
        try:
            await log_ch.send(embed=emb)
        except Exception:
            pass

    async def on_message_edit_listener(before: discord.Message, after: discord.Message):
        if not before.guild or before.guild.id != guild_obj.id or before.author.bot:
            return
        if before.content == after.content:
            return
        log_ch = find_log_channel(before.guild)
        if not log_ch:
            return
        b_txt = (before.content or "[Empty]")[:400]
        a_txt = (after.content or "[Empty]")[:400]
        emb = UI.card(
            "AUDIT LOG // MESSAGE EDITED",
            f"Modified in #{before.channel.name}",
            (
                f"**Author:** {before.author.mention} • [Jump to Message]({after.jump_url})\n"
                f"**Before:**\n```\n{b_txt}\n```\n"
                f"**After:**\n```\n{a_txt}\n```"
            ),
            UI.SURFACE,
        )
        try:
            await log_ch.send(embed=emb)
        except Exception:
            pass

    async def on_voice_state_update_listener(member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        if member.guild.id != guild_obj.id or member.bot:
            return
        if before.channel == after.channel:
            return
        log_ch = find_log_channel(member.guild)
        if not log_ch:
            return

        if not before.channel and after.channel:
            action = f"Joined voice **{after.channel.name}**"
            col = UI.EMERALD
        elif before.channel and not after.channel:
            action = f"Disconnected from **{before.channel.name}**"
            col = UI.SURFACE
        else:
            action = f"Moved `{before.channel.name}` → `{after.channel.name}`"
            col = UI.BLUE

        emb = UI.card(
            "VOICE TELEMETRY // STATE CHANGE",
            f"{member.display_name}",
            f"**User:** {member.mention}\n**Event:** {action}",
            col,
        )
        try:
            await log_ch.send(embed=emb)
        except Exception:
            pass

    bot.add_listener(on_member_join_listener, "on_member_join")
    bot.add_listener(on_member_remove_listener, "on_member_remove")
    bot.add_listener(on_message_delete_listener, "on_message_delete")
    bot.add_listener(on_message_edit_listener, "on_message_edit")
    bot.add_listener(on_voice_state_update_listener, "on_voice_state_update")

    # ---------------------------------------------------------
    # 7-DAY SCHEDULE FILTER & ARCHIVE BUILDERS
    # ---------------------------------------------------------

    def enforce_7day_window_and_seed_seasons():
        now_utc = datetime.datetime.now(datetime.timezone.utc)
        cutoff_7d = now_utc + datetime.timedelta(days=7)

        cursor.execute("SELECT id, game, team_a, team_b, start_time, status, score_a, score_b FROM matches")
        rows = cursor.fetchall()
        for r in rows:
            st_raw = r.get("start_time") or ""
            try:
                dt = datetime.datetime.fromisoformat(str(st_raw).replace("Z", "+00:00"))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=datetime.timezone.utc)
                if dt > cutoff_7d or dt < (now_utc - datetime.timedelta(hours=6)):
                    if r["status"] != "FINISHED":
                        cursor.execute("UPDATE matches SET status = 'FINISHED', channel_id = 2 WHERE id = ?", (r["id"],))
            except Exception:
                pass

        for game_key, seasons_dict in SEASON_ARCHIVES.items():
            for season_name, match_list in seasons_dict.items():
                for idx, (ta, tb, sa, sb, stage_note) in enumerate(match_list, 1):
                    ext_id = f"archive_{game_key}_{season_name}_{idx}".replace(" ", "_").lower()
                    cursor.execute("SELECT id FROM matches WHERE external_id = ?", (ext_id,))
                    if not cursor.fetchone():
                        cursor.execute(
                            """
                            INSERT INTO matches (external_id, game, team_a, team_b, start_time, status, score_a, score_b, channel_id, season)
                            VALUES (?, ?, ?, ?, ?, 'FINISHED', ?, ?, 2, ?)
                            """,
                            (ext_id, game_key, ta, tb, f"{season_name} ({stage_note})", sa, sb, season_name),
                        )
        db.commit()

    def build_season_embed(game_key: str, selected_season: str = None) -> discord.Embed:
        game_title = "MPL INDONESIA" if game_key == "MPL" else "VALORANT CHAMPIONS TOUR"
        colour = UI.AMBER if game_key == "MPL" else UI.CRIMSON
        emb = UI.card(
            f"SEASON ARCHIVE // {game_key}",
            f"{game_title} — Verified Results",
            "Jadwal aktif dibatasi ketat `0–7 Hari` ke depan. Seluruh laga lampau dikelompokkan per Season.",
            colour,
        )
        for s_name, m_list in SEASON_ARCHIVES.get(game_key, {}).items():
            if selected_season and selected_season.lower() not in s_name.lower():
                continue
            lines = []
            for ta, tb, sa, sb, stage_note in m_list:
                tag_a = "WIN " if sa > sb else ""
                tag_b = " WIN" if sb > sa else ""
                lines.append(f"`{stage_note}` • **{ta}** `{tag_a}{sa} : {sb}{tag_b}` **{tb}**")
            emb.add_field(name=f"SEASON // {s_name.upper()}", value="\n".join(lines), inline=False)

        cursor.execute(
            "SELECT team_a, team_b, score_a, score_b FROM matches WHERE game = ? AND status = 'FINISHED' AND external_id NOT LIKE 'archive_%' ORDER BY id DESC LIMIT 5",
            (game_key,),
        )
        live_finished = cursor.fetchall()
        if live_finished:
            recent_lines = [f"• **{r['team_a']}** `{r['score_a']} : {r['score_b']}` **{r['team_b']}**" for r in live_finished]
            emb.add_field(name="CURRENT SPLIT // LATEST SETTLED", value="\n".join(recent_lines), inline=False)
        return emb

    def build_champions_embed(game_key: str) -> discord.Embed:
        game_title = "MPL INDONESIA" if game_key == "MPL" else "VCT PACIFIC & GLOBAL"
        emb = UI.card(
            f"HALL OF CHAMPIONS // {game_key}",
            f"{game_title} — Dynasty Ledger",
            "Rekor pemenang Grand Final, skor akhir, dan peraih gelar Finals MVP.",
            UI.AMBER,
        )
        for season_label, champ, runner_up, score_str, fmvp in CHAMPIONS_LEDGER.get(game_key, []):
            emb.add_field(
                name=f"{season_label.upper()}",
                value=f"**Champion:** `{champ}`\n**Final:** `{score_str}` vs {runner_up}\n**FMVP:** `{fmvp}`",
                inline=True,
            )
        return emb

    def build_server_stats_embed(guild: discord.Guild) -> discord.Embed:
        total_members = guild.member_count or len(guild.members)
        bots = sum(1 for m in guild.members if m.bot)
        humans = max(1, total_members - bots)
        online = sum(1 for m in guild.members if not m.bot and m.status != discord.Status.offline)
        in_voice = sum(len(vc.members) for vc in guild.voice_channels)

        cursor.execute("SELECT COUNT(*) AS cnt FROM matches WHERE status != 'FINISHED'")
        active_matches = cursor.fetchone()["cnt"]
        cursor.execute("SELECT COUNT(*) AS cnt FROM users")
        economy_users = cursor.fetchone()["cnt"]

        emb = UI.card(
            "TELEMETRY // SERVER PULSE",
            f"{guild.name} — Live Operations",
            f"Real-time infrastructure & population metrics.\n**Active Ratio:** {UI.bar(online, humans, 12)}",
            UI.BLUE,
        )
        emb.add_field(name="POPULATION", value=f"`{total_members}` Total\n`{humans}` Humans / `{bots}` Bots", inline=True)
        emb.add_field(name="ACTIVITY", value=f"`{online}` Online\n`{in_voice}` In Voice", inline=True)
        emb.add_field(name="BOOST TIER", value=f"`Level {guild.premium_tier}`\n`{guild.premium_subscription_count}` Boosts", inline=True)
        emb.add_field(name="ESPORTS DB", value=f"`{active_matches}` Active Fixtures\n`{economy_users}` Ranked Profiles", inline=True)
        emb.add_field(name="CHANNELS", value=f"`{len(guild.text_channels)}` Text / `{len(guild.voice_channels)}` Voice", inline=True)
        emb.add_field(name="LATENCY", value=f"`{round(bot.latency * 1000)} ms` Gateway", inline=True)
        if guild.icon:
            emb.set_thumbnail(url=guild.icon.url)
        return emb

    # Remove existing command registrations to prevent collisions on reload
    for cmd_name in [
        "season_results", "champions", "sync_all_channels", "ticket_panel",
        "purge", "warn", "timeout", "kick", "ban", "ai", "play", "queue",
        "skip", "stop", "server_stats", "social_alert", "giveaway_start",
        "giveaway_roll", "coinflip", "slots", "trivia", "role_panel", "welcome_test",
    ]:
        bot.tree.remove_command(cmd_name, guild=guild_obj)

    # ---------------------------------------------------------
    # SLASH COMMANDS: SERVER STATS, SOCIAL ALERT, ROLES, WELCOME
    # ---------------------------------------------------------

    @bot.tree.command(name="server_stats", description="Tampilkan panel telemetri populasi, status online, voice, dan database server.", guild=guild_obj)
    async def server_stats_cmd(interaction: discord.Interaction):
        emb = build_server_stats_embed(interaction.guild)
        await interaction.response.send_message(embed=emb)

    @bot.tree.command(name="social_alert", description="Admin: Siarkan kartu pengumuman Live Stream / Konten baru (YouTube/Twitch/TikTok/X).", guild=guild_obj)
    async def social_alert_cmd(
        interaction: discord.Interaction,
        platform: str,
        creator: str,
        title: str,
        url: str,
        ping_everyone: bool = False,
    ):
        if not interaction.user.guild_permissions.manage_messages:
            await interaction.response.send_message("Membutuhkan izin `Manage Messages`.", ephemeral=True)
            return

        plat_up = platform.upper()
        col = UI.CRIMSON if "YOUTUBE" in plat_up or "YT" in plat_up else UI.INDIGO
        emb = UI.card(
            f"SOCIAL PULSE // {plat_up} ALERT",
            title,
            (
                f"**Creator / Channel:** `{creator}`\n"
                f"**Platform:** `{platform}`\n"
                f"**Status:** `LIVE / NEW UPLOAD`\n\n"
                f"Klik tombol di bawah untuk menonton atau membuka tautan resmi."
            ),
            col,
        )
        view = discord.ui.View()
        if url.startswith("http"):
            view.add_item(discord.ui.Button(label=f"Open on {platform}", url=url, style=discord.ButtonStyle.link))

        target_ch = (
            get_channel(interaction.guild, "social-alerts")
            or get_channel(interaction.guild, "announcements")
            or interaction.channel
        )
        content_ping = "@everyone" if ping_everyone else None
        await target_ch.send(content=content_ping, embed=emb, view=view)
        await interaction.response.send_message(f"Social alert berhasil disiarkan ke {target_ch.mention}!", ephemeral=True)

    @bot.tree.command(name="role_panel", description="Admin: Pasang panel interaktif Self-Role & Onboarding di channel ini.", guild=guild_obj)
    async def role_panel_cmd(interaction: discord.Interaction):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("Hanya Admin yang dapat memasang panel role.", ephemeral=True)
            return
        emb = UI.card(
            "IDENTITY // SELF-ROLE ASSIGNMENT",
            "Select Your Campus & Esports Roles",
            (
                "Klik tombol di bawah untuk mengaktifkan atau melepas role notifikasi di profil kamu:\n\n"
                "• **MPL ID Roster** — Notifikasi jadwal, prediksi, & watch party MPL Indonesia\n"
                "• **VCT Pacific Roster** — Notifikasi jadwal & hasil Valorant Champions Tour\n"
                "• **Mabar Squad (LFG)** — Akses panggilan party mabar 5-slot\n"
                "• **Watch Party Ping** — Undangan nongkrong bareng di Voice Channel"
            ),
            UI.INDIGO,
        )
        await interaction.channel.send(embed=emb, view=SelfRoleView())
        await interaction.response.send_message("Panel Self-Role berhasil dipasang!", ephemeral=True)

    @bot.tree.command(name="welcome_test", description="Admin: Uji coba pengiriman kartu Welcome & Auto-Role untuk profilmu.", guild=guild_obj)
    async def welcome_test_cmd(interaction: discord.Interaction):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("Hanya Admin yang dapat menjalankan tes ini.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        await on_member_join_listener(interaction.user)
        await interaction.followup.send("Simulasi kartu Welcome & Auto-Role berhasil dikirim!", ephemeral=True)

    # ---------------------------------------------------------
    # SLASH COMMANDS: GIVEAWAY SYSTEM
    # ---------------------------------------------------------

    @bot.tree.command(name="giveaway_start", description="Admin: Mulai sesi Giveaway interaktif dengan bonus Coins otomatis.", guild=guild_obj)
    async def giveaway_start_cmd(interaction: discord.Interaction, prize: str, duration_minutes: int = 60, bonus_coins: int = 1000):
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("Membutuhkan izin `Manage Server`.", ephemeral=True)
            return

        now_utc = datetime.datetime.now(datetime.timezone.utc)
        end_ts = int((now_utc + datetime.timedelta(minutes=max(1, duration_minutes))).timestamp())
        cursor.execute(
            "INSERT INTO giveaways (prize, coins_bonus, host_id, status, created_at) VALUES (?, ?, ?, 'ACTIVE', ?)",
            (prize, bonus_coins, interaction.user.id, now_utc.strftime("%Y-%m-%d %H:%M UTC")),
        )
        db.commit()
        cursor.execute("SELECT id FROM giveaways ORDER BY id DESC LIMIT 1")
        gw_id = cursor.fetchone()["id"]

        emb = UI.card(
            f"COMMUNITY DROP // GIVEAWAY #{gw_id}",
            prize,
            "Klik tombol **Enter Giveaway** di bawah untuk masuk ke daftar undian resmi.",
            UI.AMBER,
        )
        emb.add_field(name="REWARD POOL", value=f"`{prize}`\n`+{bonus_coins} Coins`", inline=True)
        emb.add_field(name="PARTICIPANTS", value="`0 Users` (`100%` win rate)", inline=True)
        emb.add_field(name="ENDS IN", value=f"<t:{end_ts}:R>\nHost: {interaction.user.mention}", inline=True)

        view = GiveawayJoinView(gw_id, prize, bonus_coins, db, cursor)
        target_ch = get_channel(interaction.guild, "giveaways") or interaction.channel
        await target_ch.send(embed=emb, view=view)
        await interaction.response.send_message(f"Giveaway `#{gw_id}` berhasil diluncurkan di {target_ch.mention}!", ephemeral=True)

    @bot.tree.command(name="giveaway_roll", description="Admin: Undi pemenang dari Giveaway yang sedang aktif.", guild=guild_obj)
    async def giveaway_roll_cmd(interaction: discord.Interaction, giveaway_id: int = 0):
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("Membutuhkan izin `Manage Server`.", ephemeral=True)
            return

        if giveaway_id <= 0:
            cursor.execute("SELECT * FROM giveaways WHERE status = 'ACTIVE' ORDER BY id DESC LIMIT 1")
        else:
            cursor.execute("SELECT * FROM giveaways WHERE id = ?", (giveaway_id,))
        gw = cursor.fetchone()
        if not gw:
            await interaction.response.send_message("Giveaway tidak ditemukan.", ephemeral=True)
            return

        cursor.execute("SELECT user_id FROM giveaway_entries WHERE giveaway_id = ?", (gw["id"],))
        entries = [r["user_id"] for r in cursor.fetchall()]
        if not entries:
            await interaction.response.send_message(f"Belum ada peserta di Giveaway `#{gw['id']}`.", ephemeral=True)
            return

        winner_id = random.choice(entries)
        update_user_economy(winner_id, coins_delta=int(gw["coins_bonus"]), xp_delta=100)
        cursor.execute("UPDATE giveaways SET status = 'ENDED' WHERE id = ?", (gw["id"],))
        db.commit()

        emb = UI.card(
            f"GIVEAWAY SETTLED // DRAW #{gw['id']}",
            f"Winner: {gw['prize']}",
            (
                f"Selamat kepada <@{winner_id}> yang terpilih dari `{len(entries)}` peserta!\n\n"
                f"**Prize Claimed:** `{gw['prize']}`\n"
                f"**Wallet Credited:** `+{gw['coins_bonus']} Coins` & `+100 XP`"
            ),
            UI.EMERALD,
        )
        await interaction.response.send_message(content=f"<@{winner_id}>", embed=emb)

    # ---------------------------------------------------------
    # SLASH COMMANDS: MINI GAMES (COINFLIP, SLOTS, TRIVIA)
    # ---------------------------------------------------------

    @bot.tree.command(name="coinflip", description="Mini Game: Taruhkan Coins kamu di lempar koin (Heads / Tails) berhadiah 2x lipat.", guild=guild_obj)
    async def coinflip_cmd(interaction: discord.Interaction, bet: int = 100, side: str = "heads"):
        bet = max(10, min(bet, 10000))
        choice = "heads" if side.lower().startswith("h") else "tails"
        profile = update_user_economy(interaction.user.id, 0, 0)
        if profile["coins"] < bet:
            await interaction.response.send_message(f"Saldo Coins kamu (`{profile['coins']}`) tidak cukup untuk taruhan `{bet}`.", ephemeral=True)
            return

        landed = random.choice(["heads", "tails"])
        won = choice == landed
        delta = bet if won else -bet
        updated = update_user_economy(interaction.user.id, coins_delta=delta, xp_delta=15 if won else 5)

        emb = UI.card(
            "ARCADE // QUANTUM COINFLIP",
            "Double Hit!" if won else "House Wins",
            (
                f"**Player:** {interaction.user.mention}\n"
                f"**Your Call:** `{choice.upper()}` • **Landed:** `{landed.upper()}`\n"
                f"**Net Result:** `{'+' if won else ''}{delta} Coins`\n"
                f"**Updated Balance:** `{updated['coins']} Coins` (`{updated['xp']} XP`)"
            ),
            UI.EMERALD if won else UI.SURFACE,
        )
        await interaction.response.send_message(embed=emb)

    @bot.tree.command(name="slots", description="Mini Game: Putar mesin Esports Slots dengan kesempatan Jackpot hingga 10x.", guild=guild_obj)
    async def slots_cmd(interaction: discord.Interaction, bet: int = 100):
        bet = max(10, min(bet, 10000))
        profile = update_user_economy(interaction.user.id, 0, 0)
        if profile["coins"] < bet:
            await interaction.response.send_message(f"Saldo Coins kamu (`{profile['coins']}`) kurang untuk taruhan `{bet}`.", ephemeral=True)
            return

        symbols = ["💎", "👑", "⚡", "🔥", "🎯"]
        reels = [random.choice(symbols) for _ in range(3)]
        if reels[0] == reels[1] == reels[2]:
            mult = 10 if reels[0] == "👑" else 5
            delta = bet * (mult - 1)
            status_title = f"JACKPOT {mult}X!"
            col = UI.AMBER
        elif reels[0] == reels[1] or reels[1] == reels[2] or reels[0] == reels[2]:
            mult = 2
            delta = bet
            status_title = "DOUBLE MATCH (2X)"
            col = UI.EMERALD
        else:
            mult = 0
            delta = -bet
            status_title = "NO MATCH"
            col = UI.SURFACE

        updated = update_user_economy(interaction.user.id, coins_delta=delta, xp_delta=20 if delta > 0 else 5)
        emb = UI.card(
            "ARCADE // ESPORTS SLOTS",
            status_title,
            (
                f"### `[ {reels[0]}  |  {reels[1]}  |  {reels[2]} ]`\n"
                f"**Payout:** `{'+' if delta > 0 else ''}{delta} Coins`\n"
                f"**Current Wallet:** `{updated['coins']} Coins` • `{updated['xp']} XP`"
            ),
            col,
        )
        await interaction.response.send_message(embed=emb)

    @bot.tree.command(name="trivia", description="Mini Game: Jawab kuis cepat MPL & VCT berhadiah +150 Coins dan +50 XP.", guild=guild_obj)
    async def trivia_cmd(interaction: discord.Interaction):
        item = random.choice(TRIVIA_BANK)
        emb = UI.card(
            f"ARCADE // {item['topic'].upper()}",
            item["q"],
            "Klik jawaban yang paling tepat di bawah ini. Pemenang tercepat langsung menerima `+150 Coins` & `+50 XP`!",
            UI.AMBER,
        )
        await interaction.response.send_message(embed=emb, view=TriviaView(item, db, cursor, update_user_economy))

    # ---------------------------------------------------------
    # SLASH COMMANDS: ESPORTS SEASONS, CHAMPIONS, & SYNC ALL
    # ---------------------------------------------------------

    @bot.tree.command(name="season_results", description="Lihat arsip hasil pertandingan MPL atau VCT per Season.", guild=guild_obj)
    async def season_results(interaction: discord.Interaction, game: str = "all", season: str = ""):
        enforce_7day_window_and_seed_seasons()
        g = game.upper()
        embeds = []
        if g in ("ALL", "MPL", "ML"):
            embeds.append(build_season_embed("MPL", season or None))
        if g in ("ALL", "VALORANT", "VCT", "VALO"):
            embeds.append(build_season_embed("VALORANT", season or None))
        if not embeds:
            await interaction.response.send_message("Pilih `all`, `mpl`, atau `valorant`.", ephemeral=True)
            return
        await interaction.response.send_message(embeds=embeds)

    @bot.tree.command(name="champions", description="Tampilkan Hall of Champions MPL ID & VCT per Season.", guild=guild_obj)
    async def champions(interaction: discord.Interaction, game: str = "all"):
        g = game.upper()
        embeds = []
        if g in ("ALL", "MPL", "ML"):
            embeds.append(build_champions_embed("MPL"))
        if g in ("ALL", "VALORANT", "VCT", "VALO"):
            embeds.append(build_champions_embed("VALORANT"))
        if not embeds:
            await interaction.response.send_message("Pilih `all`, `mpl`, atau `valorant`.", ephemeral=True)
            return
        await interaction.response.send_message(embeds=embeds)

    @bot.tree.command(name="sync_all_channels", description="Admin: Perbarui seluruh channel dengan UI Design System v3.0.", guild=guild_obj)
    async def sync_all_channels(interaction: discord.Interaction):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("Hanya Admin yang dapat menjalankan sinkronisasi penuh.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        enforce_7day_window_and_seed_seasons()
        guild = interaction.guild
        activated = []

        mpl_res_ch = get_channel(guild, "mpl-results")
        if mpl_res_ch:
            await mpl_res_ch.send(embeds=[build_champions_embed("MPL"), build_season_embed("MPL")])
            activated.append(mpl_res_ch.mention)

        val_res_ch = get_channel(guild, "valorant-results")
        if val_res_ch:
            await val_res_ch.send(embeds=[build_champions_embed("VALORANT"), build_season_embed("VALORANT")])
            activated.append(val_res_ch.mention)

        all_res_ch = get_channel(guild, "match-results")
        if all_res_ch:
            await all_res_ch.send(embeds=[build_season_embed("MPL"), build_season_embed("VALORANT")])
            activated.append(all_res_ch.mention)

        mpl_hype_ch = get_channel(guild, "mpl-hype")
        if mpl_hype_ch:
            h_emb = UI.card("CROWD PULSE // MPL ID", "MPL Watch Party Hype Meter", "Dukung tim favoritmu sebelum laga dimulai!", UI.AMBER)
            h_emb.add_field(name="LIVE CROWD PULSE", value=f"**RRQ Hoshi** {UI.bar(1, 2, 10)} **Team Liquid ID**", inline=False)
            await mpl_hype_ch.send(embed=h_emb, view=HypeMeterView("RRQ Hoshi", "Team Liquid ID"))
            activated.append(mpl_hype_ch.mention)

        val_hype_ch = get_channel(guild, "valorant-hype")
        if val_hype_ch:
            vh_emb = UI.card("CROWD PULSE // VCT PACIFIC", "VCT Watch Party Hype Meter", "Adu dukungan komunitas sebelum map dimulai!", UI.CRIMSON)
            vh_emb.add_field(name="LIVE CROWD PULSE", value=f"**Paper Rex** {UI.bar(1, 2, 10)} **Gen.G / RRQ**", inline=False)
            await val_hype_ch.send(embed=vh_emb, view=HypeMeterView("Paper Rex", "Gen.G / RRQ"))
            activated.append(val_hype_ch.mention)

        tourney_ch = get_channel(guild, "tournaments")
        if tourney_ch:
            t_emb = UI.card("COMPETITIVE // CAMPUS BRACKET", "Gasak Galo Internal Cup", "Klik tombol di bawah untuk mendaftarkan roster tim kamu.", UI.AMBER)
            t_emb.add_field(name="REGISTERED ROSTERS (0/8)", value=f"{UI.bar(0, 8, 10)}\nBelum ada roster terdaftar.", inline=False)
            await tourney_ch.send(embed=t_emb, view=TournamentRegView("Gasak Galo Internal Cup", 8))
            activated.append(tourney_ch.mention)

        stats_ch = get_channel(guild, "server-stats") or get_channel(guild, "leaderboards")
        if stats_ch:
            await stats_ch.send(embed=build_server_stats_embed(guild))
            activated.append(stats_ch.mention)

        await interaction.followup.send(f"UI v3.0 berhasil disinkronkan ke: {', '.join(activated)}", ephemeral=True)

    # ---------------------------------------------------------
    # SLASH COMMANDS: TICKETS, MODERATION, AI, & MUSIC
    # ---------------------------------------------------------

    @bot.tree.command(name="ticket_panel", description="Admin: Pasang panel pembuka tiket layanan privat.", guild=guild_obj)
    async def ticket_panel(interaction: discord.Interaction):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("Hanya Admin yang dapat memasang panel tiket.", ephemeral=True)
            return
        emb = UI.card(
            "CONCIERGE // PRIVATE TICKETING",
            "Support & Verification Desk",
            "Pilih salah satu kategori di bawah untuk membuka ruang diskusi privat bersama moderator server.",
            UI.INDIGO,
        )
        await interaction.channel.send(embed=emb, view=TicketLaunchView())
        await interaction.response.send_message("Panel tiket v3.0 berhasil dipasang!", ephemeral=True)

    async def send_mod_log(guild: discord.Guild, eyebrow: str, title: str, details: str, colour: discord.Colour):
        log_ch = find_log_channel(guild)
        if log_ch:
            try:
                await log_ch.send(embed=UI.card(eyebrow, title, details, colour))
            except Exception:
                pass

    @bot.tree.command(name="purge", description="Moderator: Bersihkan sejumlah pesan terakhir di channel ini.", guild=guild_obj)
    async def purge(interaction: discord.Interaction, amount: int = 10):
        if not interaction.user.guild_permissions.manage_messages:
            await interaction.response.send_message("Membutuhkan izin `Manage Messages`.", ephemeral=True)
            return
        amount = max(1, min(amount, 100))
        await interaction.response.defer(ephemeral=True)
        deleted = await interaction.channel.purge(limit=amount)
        await send_mod_log(
            interaction.guild,
            "MODERATION // PURGE",
            f"{len(deleted)} Messages Cleared",
            f"**Executor:** {interaction.user.mention}\n**Channel:** {interaction.channel.mention}",
            UI.BLUE,
        )
        await interaction.followup.send(f"Berhasil membersihkan `{len(deleted)}` pesan.", ephemeral=True)

    @bot.tree.command(name="warn", description="Moderator: Berikan peringatan resmi kepada member.", guild=guild_obj)
    async def warn(interaction: discord.Interaction, member: discord.Member, reason: str):
        if not interaction.user.guild_permissions.moderate_members:
            await interaction.response.send_message("Membutuhkan izin `Moderate Members`.", ephemeral=True)
            return
        now_str = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        cursor.execute(
            "INSERT INTO mod_warnings (user_id, moderator_id, reason, created_at) VALUES (?, ?, ?, ?)",
            (member.id, interaction.user.id, reason, now_str),
        )
        db.commit()
        cursor.execute("SELECT COUNT(*) AS cnt FROM mod_warnings WHERE user_id = ?", (member.id,))
        total_warns = cursor.fetchone()["cnt"]

        details = f"**Target:** {member.mention} (`{member.id}`)\n**Moderator:** {interaction.user.mention}\n**Reason:** `{reason}`\n**Strike Count:** `#{total_warns}`"
        await send_mod_log(interaction.guild, "MODERATION // WARNING", f"Warning Issued to {member.display_name}", details, UI.AMBER)
        await interaction.response.send_message(embed=UI.card("MODERATION // NOTICE", f"Strike #{total_warns} Recorded", details, UI.AMBER))

    @bot.tree.command(name="timeout", description="Moderator: Bekukan sementara member dalam hitungan menit.", guild=guild_obj)
    async def timeout_cmd(interaction: discord.Interaction, member: discord.Member, minutes: int = 10, reason: str = "Rule violation"):
        if not interaction.user.guild_permissions.moderate_members:
            await interaction.response.send_message("Membutuhkan izin `Moderate Members`.", ephemeral=True)
            return
        await member.timeout(datetime.timedelta(minutes=max(1, min(minutes, 40320))), reason=reason)
        details = f"**Target:** {member.mention}\n**Duration:** `{minutes} Mins`\n**Moderator:** {interaction.user.mention}\n**Reason:** `{reason}`"
        await send_mod_log(interaction.guild, "MODERATION // TIMEOUT", f"{member.display_name} Muted", details, UI.CRIMSON)
        await interaction.response.send_message(embed=UI.card("MODERATION // TIMEOUT", f"{member.display_name} Timed Out", details, UI.CRIMSON))

    @bot.tree.command(name="kick", description="Moderator: Keluarkan member dari server.", guild=guild_obj)
    async def kick_cmd(interaction: discord.Interaction, member: discord.Member, reason: str = "Rule violation"):
        if not interaction.user.guild_permissions.kick_members:
            await interaction.response.send_message("Membutuhkan izin `Kick Members`.", ephemeral=True)
            return
        await member.kick(reason=reason)
        details = f"**Target:** `{member}` (`{member.id}`)\n**Moderator:** {interaction.user.mention}\n**Reason:** `{reason}`"
        await send_mod_log(interaction.guild, "MODERATION // KICK", f"{member} Kicked", details, UI.CRIMSON)
        await interaction.response.send_message(embed=UI.card("MODERATION // KICK", f"{member} Removed", details, UI.CRIMSON))

    @bot.tree.command(name="ban", description="Admin: Banned member secara permanen.", guild=guild_obj)
    async def ban_cmd(interaction: discord.Interaction, member: discord.Member, reason: str = "Severe violation"):
        if not interaction.user.guild_permissions.ban_members:
            await interaction.response.send_message("Membutuhkan izin `Ban Members`.", ephemeral=True)
            return
        await member.ban(reason=reason)
        details = f"**Target:** `{member}` (`{member.id}`)\n**Moderator:** {interaction.user.mention}\n**Reason:** `{reason}`"
        await send_mod_log(interaction.guild, "MODERATION // BAN", f"{member} Banned", details, UI.CRIMSON)
        await interaction.response.send_message(embed=UI.card("MODERATION // BAN", f"{member} Permanently Banned", details, UI.CRIMSON))

    @bot.tree.command(name="ai", description="Tanya apa saja ke AI Asisten server.", guild=guild_obj)
    async def ai_cmd(interaction: discord.Interaction, prompt: str):
        await interaction.response.defer()
        answer = await asyncio.to_thread(query_ai_assistant, prompt, interaction.user.display_name)
        emb = UI.card("NEURAL ENGINE // AI ASSISTANT", prompt[:80], answer[:3800], UI.INDIGO)
        await interaction.followup.send(embed=emb)

    def play_next_in_queue(guild: discord.Guild):
        queue = MUSIC_QUEUES.get(guild.id, [])
        vc = guild.voice_client
        if not vc or not queue:
            return
        next_track = queue.pop(0)
        source = discord.FFmpegPCMAudio(next_track["url"], **FFMPEG_OPTIONS)
        vc.play(source, after=lambda e: play_next_in_queue(guild))

    @bot.tree.command(name="play", description="Putar musik dari judul lagu atau URL di Voice Channel.", guild=guild_obj)
    async def play_cmd(interaction: discord.Interaction, query: str):
        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.response.send_message("Masuk ke Voice Channel terlebih dahulu!", ephemeral=True)
            return
        await interaction.response.defer()
        voice_channel = interaction.user.voice.channel
        vc = interaction.guild.voice_client
        try:
            if not vc:
                vc = await voice_channel.connect()
            elif vc.channel != voice_channel:
                await vc.move_to(voice_channel)
            track = await asyncio.to_thread(extract_audio_info, query)
        except Exception as e:
            await interaction.followup.send(f"Gagal memutar audio (`{e}`).")
            return

        track["requester"] = interaction.user.display_name
        queue = MUSIC_QUEUES.setdefault(interaction.guild.id, [])

        if vc.is_playing() or vc.is_paused():
            queue.append(track)
            emb = UI.card(
                "AUDIO ENGINE // QUEUED",
                track["title"],
                f"**Requested By:** `{track['requester']}`\n**Queue Position:** `#{len(queue)}`",
                UI.SURFACE,
            )
        else:
            source = discord.FFmpegPCMAudio(track["url"], **FFMPEG_OPTIONS)
            vc.play(source, after=lambda e: play_next_in_queue(interaction.guild))
            emb = UI.card(
                "AUDIO ENGINE // NOW PLAYING",
                track["title"],
                f"**Channel:** {voice_channel.mention}\n**Requested By:** `{track['requester']}`",
                UI.INDIGO,
            )
        await interaction.followup.send(embed=emb, view=MusicControlView(bot))

    @bot.tree.command(name="queue", description="Lihat daftar antrean lagu saat ini.", guild=guild_obj)
    async def queue_cmd(interaction: discord.Interaction):
        queue = MUSIC_QUEUES.get(interaction.guild.id, [])
        if not queue:
            await interaction.response.send_message("Antrean musik kosong.", ephemeral=True)
            return
        lines = [f"`0{i}` **{t['title']}** (`{t['requester']}`)" for i, t in enumerate(queue[:15], 1)]
        await interaction.response.send_message(embed=UI.card("AUDIO ENGINE // QUEUE", "Upcoming Tracks", "\n".join(lines), UI.SURFACE))

    @bot.tree.command(name="skip", description="Lewati lagu yang sedang diputar.", guild=guild_obj)
    async def skip_cmd(interaction: discord.Interaction):
        vc = interaction.guild.voice_client
        if vc and (vc.is_playing() or vc.is_paused()):
            vc.stop()
            await interaction.response.send_message(embed=UI.card("AUDIO ENGINE", "Track Skipped", "Beralih ke antrean berikutnya.", UI.SURFACE))
        else:
            await interaction.response.send_message("Tidak ada audio aktif.", ephemeral=True)

    @bot.tree.command(name="stop", description="Hentikan musik dan keluar dari Voice Channel.", guild=guild_obj)
    async def stop_cmd(interaction: discord.Interaction):
        MUSIC_QUEUES.pop(interaction.guild.id, None)
        vc = interaction.guild.voice_client
        if vc:
            await vc.disconnect()
            await interaction.response.send_message(embed=UI.card("AUDIO ENGINE", "Disconnected", "Antrean dibersihkan dan sesi ditutup.", UI.SURFACE))
        else:
            await interaction.response.send_message("Bot tidak berada di voice channel.", ephemeral=True)

    enforce_7day_window_and_seed_seasons()