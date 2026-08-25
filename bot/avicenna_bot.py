import os
import json
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

TOKEN = os.environ.get("BOT_TOKEN", "8936163126:***")
ADMIN_ID = 7075416645
USERS_FILE = "/data/workspace/users.json"
# Mini App URL — GitHub Pages (the deployed mini app)
MINIAPP_URL = os.environ.get("MINIAPP_URL", "https://jalilzandi1330.github.io/avicenna-lab/")

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# ==================== STORAGE ====================

def load_data():
    """users.json now stores a dict: {user_id: {points, invites, invited_by, name}}"""
    default = {}
    if not os.path.exists(USERS_FILE):
        return default
    try:
        with open(USERS_FILE, "r") as f:
            data = json.load(f)
        # Legacy migration: old format was a plain list of IDs
        if isinstance(data, list):
            return {str(uid): {"points": 10, "invites": 0, "invited_by": None, "name": ""} for uid in data}
        return data
    except Exception:
        return default

def save_data(data):
    tmp = USERS_FILE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(data, f, ensure_ascii=False)
    os.replace(tmp, USERS_FILE)  # atomic write, never corrupt the file

db = load_data()

# One-time migration: give existing 24 users their welcome bonus
MIGRATED = db and all(isinstance(v, dict) for v in db.values())
if MIGRATED:
    logging.info(f"Loaded {len(db)} users (dict format OK)")

def get_uid(update: Update) -> str:
    return str(update.effective_user.id)

def add_points(uid: str, amount: int):
    if uid in db:
        db[uid]["points"] += amount

# ==================== COMMANDS ====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    uid = str(user.id)
    is_new = uid not in db

    # --- Referral handling: /start ref_<inviter_id> ---
    ref_bonus_msg = ""
    if is_new:
        invited_by = None
        if context.args and context.args[0].startswith("ref_"):
            try:
                candidate = context.args[0][4:]
                if candidate.isdigit() and candidate != uid and candidate in db:
                    invited_by = candidate
            except Exception:
                pass

        db[uid] = {
            "points": 10,          # welcome bonus
            "invites": 0,
            "invited_by": invited_by,
            "name": user.first_name or "",
        }
        if invited_by:
            add_points(invited_by, 50)   # inviter reward
            db[invited_by]["invites"] += 1
            ref_bonus_msg = f"\n🎁 شما با لینک دعوت دوستتان وارد شدید! (+۱۰ امتیاز خوش‌آمد)\n"
            try:
                await context.bot.send_message(
                    chat_id=int(invited_by),
                    text=f"🎉 تبریک! **{user.first_name}** با لینک دعوت شما به آزمایشگاه ابن‌سینا پیوست!\n"
                         f"✅ +۵۰ امتیاز دریافت کردید.",
                    parse_mode="Markdown",
                )
            except Exception:
                pass  # inviter blocked the bot
        save_data(db)
        logging.info(f"New user: {uid} ({user.first_name}), invited_by={invited_by}")

    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("🔬 ورود به آزمایشگاه", web_app=WebAppInfo(url=MINIAPP_URL))
    ]])
    points = db.get(uid, {}).get("points", 0)
    welcome_text = (
        f"سلام {user.first_name} عزیز! 👋\n"
        "به مینی‌اپ علمی **آزمایشگاه ابن‌سینا (Avicenna Lab)** خوش آمدید. 🔬\n\n"
        "🧪 ابزارها: رسم توابع ریاضی، موازنه واکنش، مدل سه‌بعدی مولکول‌ها\n"
        f"⭐ امتیاز فعلی شما: **{points}**\n"
        f"👥 با هر دعوت موفق: **+۵۰ امتیاز** بگیرید!\n\n"
        f"لینک دعوت اختصاصی شما:\n`https://t.me/AvicennaScience_bot?start=ref_{uid}`\n"
        f"{ref_bonus_msg}"
        "👇 برای ورود روی دکمه زیر بزنید:"
    )
    await update.message.reply_text(welcome_text, reply_markup=keyboard, parse_mode="Markdown")

async def panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show personal stats + invite link."""
    uid = get_uid(update)
    info = db.get(uid, {"points": 0, "invites": 0})
    rank = sorted(db.items(), key=lambda kv: kv[1].get("points", 0), reverse=True)
    my_rank = next((i for i, (k, _) in enumerate(rank, 1) if k == uid), "-")
    link = f"https://t.me/AvicennaScience_bot?start=ref_{uid}"
    text = (
        f"📊 پنل کاربری شما\n\n"
        f"⭐ امتیاز: *{info.get('points', 0)}*\n"
        f"🏆 رتبه در بین همه کاربران: *{my_rank}* از {len(db)}\n"
        f"👥 تعداد دعوت موفق: *{info.get('invites', 0)}*\n\n"
        f"🔗 لینک دعوت شما:\n`{link}`\n\n"
        f"💎 پاداش‌ها:\n• هر دعوت موفق: +۵۰ امتیاز\n• عضویت اولیه: +۱۰ امتیاز"
    )
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("🔬 باز کردن مینی‌اپ", web_app=WebAppInfo(url=MINIAPP_URL))]])
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=kb)

async def top(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Leaderboard."""
    ranked = sorted(db.items(), key=lambda kv: kv[1].get("points", 0), reverse=True)[:10]
    medals = ["🥇", "🥈", "🥉"] + ["▫️"] * 7
    lines = ["🏅 جدول امتیازات برترین کاربران:\n"]
    for i, (uid_, info) in enumerate(ranked):
        name = info.get("name") or f"کاربر {uid_[-4:]}"
        lines.append(f"{medals[i]} {name} — ⭐ {info.get('points', 0)}")
    await update.message.reply_text("\n".join(lines))

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    text = " ".join(context.args)
    if not text:
        await update.message.reply_text("❌ لطفاً متن پیام را وارد کنید.\nمثال:\n`/send سلام همگی! آپدیت جدید منتشر شد.`", parse_mode="Markdown")
        return
    success, failed = 0, 0
    for uid in list(db.keys()):
        try:
            await context.bot.send_message(chat_id=int(uid), text=text)
            success += 1
        except Exception as e:
            failed += 1
            logging.error(f"Failed to send to {uid}: {e}")
    await update.message.reply_text(f"📊 گزارش ارسال همگانی:\n✅ موفق: {success}\n❌ ناموفق: {failed}\n👥 کل کاربران: {len(db)}")

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    total_points = sum(v.get("points", 0) for v in db.values())
    total_invites = sum(v.get("invites", 0) for v in db.values())
    await update.message.reply_text(
        f"📈 آمار آزمایشگاه ابن‌سینا:\n"
        f"👥 کل کاربران: {len(db)}\n"
        f"⭐ مجموع امتیازات صادرشده: {total_points}\n"
        f"🔗 کل دعوت‌های موفق: {total_invites}"
    )

async def setpoints(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/setpoints <user_id> <amount> — admin manual adjustment"""
    if update.effective_user.id != ADMIN_ID:
        return
    try:
        target, amount = context.args[0], int(context.args[1])
        if target in db:
            db[target]["points"] = amount
            save_data(db)
            await update.message.reply_text(f"✅ امتیاز کاربر {target} روی {amount} تنظیم شد.")
        else:
            await update.message.reply_text("❌ چنین کاربری یافت نشد.")
    except (IndexError, ValueError):
        await update.message.reply_text("فرمت: `/setpoints <user_id> <amount>`", parse_mode="Markdown")

async def post_init(app):
    # Glassy bottom Menu Button -> opens Mini App directly
    await app.bot.set_chat_menu_button(menu_button={"type": "web_app", "text": "🔬 آزمایشگاه", "web_app": {"url": MINIAPP_URL}})
    await app.bot.set_my_commands([
        {"command": "start", "description": "شروع / ورود به آزمایشگاه"},
        {"command": "panel", "description": "پنل کاربری: امتیاز و لینک دعوت"},
        {"command": "top", "description": "جدول برترین کاربران"},
    ])
    logging.info("Menu button + commands registered")

if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).post_init(post_init).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("panel", panel))
    app.add_handler(CommandHandler("top", top))
    app.add_handler(CommandHandler("send", broadcast))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("setpoints", setpoints))
    print("🤖 Avicenna Bot Runner Started (v2 — points & referrals)")
    app.run_polling()
