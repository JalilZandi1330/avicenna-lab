# Avicenna Bot (v2)

Telegram bot for @AvicennaScience_bot — points, referrals & leaderboard.

## Deploy on Railway
1. New Project → Deploy from GitHub repo → `JalilZandi1330/avicenna-lab`
2. Set **Root Directory** = `bot` (or use start command: `python bot/avicenna_bot.py`)
3. Environment variables:
   - `BOT_TOKEN` = Telegram bot token
   - `MINIAPP_URL` = https://jalilzandi1330.github.io/avicenna-lab/
4. Attach a Volume at `/data/workspace` (persists `users.json`)

## Commands
- `/start ref_<id>` — registers user + referral credit
- `/panel` — personal stats + invite link
- `/top` — leaderboard
- `/send <text>` — admin broadcast
- `/stats`, `/setpoints` — admin tools
