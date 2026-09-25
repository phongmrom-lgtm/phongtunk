from dotenv import load_dotenv
load_dotenv()
import asyncio
import logging
import os
import random
import re
import urllib.parse
from collections import defaultdict
from datetime import datetime, timedelta

import psycopg
from psycopg.rows import tuple_row
from psycopg_pool import ConnectionPool
import pytz

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    Update,
)

from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    ChatMemberHandler,
    filters,
)


# ============================================================
# CẤU HÌNH
# ============================================================

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()

# Danh sách ID Admin
ADMIN_IDS = [5633649201]

TIMEZONE = pytz.timezone("Asia/Ho_Chi_Minh")

# Kênh/Nhóm BẮT BUỘC kiểm tra tham gia
REQUIRED_CHECK_CHANNELS = [
    "@sanhugame",
    "@sancode22",
    "@xombao247",
    "@thongbaohit88",
    "@sancodehit88",
    "@vtc345",
    "@vtc567",
    "@hocviencbm",
]

# Kênh hiển thị thêm KHÔNG kiểm tra tham gia
OPTIONAL_DISPLAY_CHANNELS = []

SUPPORT_GROUP = "https://t.me/hocviencbm"

MIN_WITHDRAW = 3500   # Min rút tối thiểu 3,500đ
MAX_WITHDRAW = 6000   # Min rút tối đa 6,000đ
REFERRAL_REWARD = 1000


# ============================================================
# DANH SÁCH PREMIUM EMOJI (ĐÃ CẬP NHẬT TỪ THÔNG ĐIỆP JSON CỦA BẠN)
# ============================================================
E = {
    "LIKE": '<tg-emoji emoji-id="5465465194056525619">👍</tg-emoji>',
    "LOVE_FACE": '<tg-emoji emoji-id="5465262274031659421">🥰</tg-emoji>',
    "WAVE": '<tg-emoji emoji-id="5462910521739063094">👋</tg-emoji>',
    "DISLIKE": '<tg-emoji emoji-id="5465225015190367274">👎</tg-emoji>',
    "LAUGH": '<tg-emoji emoji-id="5463121572137022242">😂</tg-emoji>',
    "ROCK": '<tg-emoji emoji-id="5463412289883353404">🤟</tg-emoji>',
    "SLEEP": '<tg-emoji emoji-id="5462990652943904884">😴</tg-emoji>',
    "POOP": '<tg-emoji emoji-id="5465198330558557107">💩</tg-emoji>',
    "HANDSHAKE": '<tg-emoji emoji-id="5463256910851546817">🤝</tg-emoji>',
    "SWORD": '<tg-emoji emoji-id="5463277406435422003">🗡</tg-emoji>',
    "SHIELD": '<tg-emoji emoji-id="5465154440287757794">🛡</tg-emoji>',
    "THERMOMETER": '<tg-emoji emoji-id="5463054218459884779">🌡</tg-emoji>',
    "DIZZY": '<tg-emoji emoji-id="5463274047771000031">😵</tg-emoji>',
    "POINT_RIGHT": '<tg-emoji emoji-id="5463392464314315076">👉</tg-emoji>',
    "BANDAGE": '<tg-emoji emoji-id="5463156928307801722">🤕</tg-emoji>',
    # Alias biểu tượng bổ sung
    "SPARKLES": '<tg-emoji emoji-id="5465262274031659421">🥰</tg-emoji>',
    "FIRE": '<tg-emoji emoji-id="5463277406435422003">🗡</tg-emoji>',
    "GEM": '<tg-emoji emoji-id="5465154440287757794">🛡</tg-emoji>',
    "WARN": '<tg-emoji emoji-id="5463054218459884779">🌡</tg-emoji>',
    "STOP": '<tg-emoji emoji-id="5463274047771000031">😵</tg-emoji>',
}


# ============================================================
# ANTI SPAM
# ============================================================

SPAM_WINDOW_SECONDS = 4
SPAM_MAX_MESSAGES = 10
TEMP_BAN_MINUTES = 2

user_msg_tracker = defaultdict(list)
temp_bans = {}
user_withdraw_state = {}


# ============================================================
# LOG
# ============================================================

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)


# ============================================================
# DATABASE POSTGRESQL (CONNECTION POOL)
# ============================================================

db_pool = None

def get_pool():
    global db_pool
    if db_pool is None:
        if not DATABASE_URL:
            raise RuntimeError("Chưa cấu hình DATABASE_URL trên Railway.")
        db_pool = ConnectionPool(
            DATABASE_URL,
            min_size=1,
            max_size=10,
            kwargs={"row_factory": tuple_row},
            open=True
        )
    return db_pool


def _db_query_sync(query, params=(), fetchone=False, fetchall=False, commit=False):
    pool = get_pool()
    with pool.connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(query, params)
            if fetchone:
                return cursor.fetchone()
            if fetchall:
                return cursor.fetchall()
            if commit:
                conn.commit()
            return None


async def db_query(query, params=(), fetchone=False, fetchall=False, commit=False):
    return await asyncio.to_thread(
        _db_query_sync, query, params, fetchone, fetchall, commit
    )


def _db_transaction_sync(callback):
    pool = get_pool()
    with pool.connection() as conn:
        with conn.cursor() as cursor:
            result = callback(cursor)
            conn.commit()
            return result


async def db_transaction(callback):
    return await asyncio.to_thread(_db_transaction_sync, callback)


def _init_db_sync():
    pool = get_pool()
    with pool.connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    user_id BIGINT PRIMARY KEY,
                    username TEXT,
                    balance BIGINT NOT NULL DEFAULT 0,
                    bank_info TEXT,
                    referrer_id BIGINT,
                    is_banned INTEGER NOT NULL DEFAULT 0,
                    is_withdraw_banned INTEGER NOT NULL DEFAULT 0,
                    joined_at TEXT
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS transactions (
                    id BIGSERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    type TEXT NOT NULL,
                    amount BIGINT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    details TEXT
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS groups (
                    chat_id BIGINT PRIMARY KEY
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
                """
            )
            # Bảng Kho Code (1: 3500đ, 2: 6000đ)
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS code_stock (
                    id BIGSERIAL PRIMARY KEY,
                    type_code INTEGER NOT NULL,
                    code_val TEXT NOT NULL,
                    is_used INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL
                )
                """
            )
            cursor.execute(
                """
                INSERT INTO settings (key, value)
                VALUES ('maintenance', '0')
                ON CONFLICT (key) DO NOTHING
                """
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_transactions_user ON transactions(user_id, id DESC)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_transactions_withdraw ON transactions(type, status, id)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_users_referrer ON users(referrer_id)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_code_stock ON code_stock(type_code, is_used)"
            )
        conn.commit()
        logger.info("Database PostgreSQL đã sẵn sàng.")


async def init_db():
    await asyncio.to_thread(_init_db_sync)


def get_now_str():
    return datetime.now(TIMEZONE).strftime("%Y-%m-%d %H:%M:%S")


# ============================================================
# KEYBOARD
# ============================================================

def get_main_keyboard():
    keyboard = [
        [
            KeyboardButton("👤 Tài Khoản"),
            KeyboardButton("🎁 Mời Bạn Bè"),
        ],
        [
            KeyboardButton("💳 Rút Code"),
            KeyboardButton("🔝 Top"),
        ],
        [
            KeyboardButton("💬 Nhóm Hỗ Trợ"),
            KeyboardButton("📜 Lịch Sử Giao Dịch"),
        ],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


# ============================================================
# MAINTENANCE
# ============================================================

async def is_maintenance():
    res = await db_query(
        "SELECT value FROM settings WHERE key='maintenance'",
        fetchone=True,
    )
    return bool(res and res[0] == "1")


# ============================================================
# CAPTCHA
# ============================================================

def generate_captcha():
    a = random.randint(1, 20)
    b = random.randint(1, 20)
    correct_ans = a + b
    options = {correct_ans}
    while len(options) < 4:
        wrong = correct_ans + random.randint(-5, 5)
        if wrong > 0 and wrong != correct_ans:
            options.add(wrong)
    opts_list = list(options)
    random.shuffle(opts_list)
    return a, b, correct_ans, opts_list


# ============================================================
# KIỂM TRA THAM GIA KÊNH
# ============================================================

async def get_missing_channels(bot, user_id):
    async def check_one(channel):
        try:
            member = await bot.get_chat_member(chat_id=channel, user_id=user_id)
            if member.status in ("left", "kicked"):
                return channel
        except Exception as exc:
            logger.warning(f"Lỗi check kênh {channel} cho user {user_id}: {exc}")
            return channel
        return None

    tasks = [check_one(ch) for ch in REQUIRED_CHECK_CHANNELS]
    results = await asyncio.gather(*tasks)
    return [ch for ch in results if ch is not None]


async def check_channel_membership(bot, user_id):
    missing = await get_missing_channels(bot, user_id)
    return len(missing) == 0


def build_channel_buttons(missing_channels):
    buttons = []
    for ch in missing_channels:
        channel_url = f"https://t.me/{ch.replace('@', '')}"
        buttons.append([
            InlineKeyboardButton(f"{E['POINT_RIGHT']} Tham gia: {ch}", url=channel_url)
        ])
    for ch in OPTIONAL_DISPLAY_CHANNELS:
        channel_url = f"https://t.me/{ch.replace('@', '')}"
        buttons.append([
            InlineKeyboardButton(f"{E['LOVE_FACE']} Tham gia: {ch} (Tham khảo)", url=channel_url)
        ])
    buttons.append([
        InlineKeyboardButton("❇️ XÁC NHẬN ĐÃ THAM GIA ❇️", callback_data="verify_join")
    ])
    return buttons


# ============================================================
# XỬ LÝ RỜI/THAM GIA LẠI
# ============================================================

async def chat_member_updated_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = update.chat_member or update.my_chat_member
    if not result:
        return
    old_state = result.old_chat_member.status
    new_state = result.new_chat_member.status
    user = result.new_chat_member.user

    user_info = await db_query(
        "SELECT referrer_id FROM users WHERE user_id=%s",
        (user.id,),
        fetchone=True,
    )
    if not user_info or not user_info[0]:
        return
    ref_id = user_info[0]
    username_str = f"@{user.username}" if user.username else str(user.id)

    if old_state in ("member", "administrator", "creator") and new_state in ("left", "kicked"):
        await db_query(
            "UPDATE users SET is_withdraw_banned=1 WHERE user_id=%s",
            (ref_id,),
            commit=True,
        )
        user_withdraw_state.pop(ref_id, None)
        try:
            await context.bot.send_message(
                chat_id=user.id,
                text=(
                    f"{E['DISLIKE']} <b>THÔNG BÁO TỪ HỆ THỐNG</b>\n"
                    f"━━━━━━━━━━━━━━━━━━\n"
                    f"{E['DIZZY']} Bạn đã rời khỏi nhóm/kênh đối tác bắt buộc.\n"
                    f"{E['THERMOMETER']} Tài khoản của bạn và người giới thiệu bạn đã bị hạn chế các tính năng rút tiền!"
                ),
                parse_mode="HTML",
            )
        except Exception as exc:
            logger.warning("Không gửi được thông báo cho người rời nhóm %s: %s", user.id, exc)
        try:
            await context.bot.send_message(
                chat_id=ref_id,
                text=(
                    f"{E['DISLIKE']} <b>CẢNH BÁO KHÓA RÚT TIỀN!</b>\n"
                    f"━━━━━━━━━━━━━━━━━━\n"
                    f"{E['DIZZY']} Thành viên được bạn mời (<b>{username_str}</b> - <code>{user.id}</code>) đã rời khỏi nhóm/kênh đối tác.\n"
                    f"{E['THERMOMETER']} <b>Lý do bị khóa:</b> Người được bạn mời đã rời nhóm nên hệ thống tiến hành khoá tính năng rút tiền của bạn!"
                ),
                parse_mode="HTML",
            )
        except Exception as exc:
            logger.warning("Không gửi được thông báo khóa rút tiền cho referrer %s: %s", ref_id, exc)

    elif old_state in ("left", "kicked") and new_state in ("member", "administrator", "creator"):
        is_fully_joined = await check_channel_membership(context.bot, user.id)
        if is_fully_joined:
            invited_users = await db_query(
                "SELECT user_id FROM users WHERE referrer_id=%s",
                (ref_id,),
                fetchall=True,
            )
            all_friends_joined = True
            if invited_users:
                async def check_friend(inv_id):
                    return await check_channel_membership(context.bot, inv_id)
                tasks = [check_friend(inv_id) for (inv_id,) in invited_users]
                results = await asyncio.gather(*tasks)
                if not all(results):
                    all_friends_joined = False
            if all_friends_joined:
                await db_query(
                    "UPDATE users SET is_withdraw_banned=0 WHERE user_id=%s",
                    (ref_id,),
                    commit=True,
                )
                try:
                    await context.bot.send_message(
                        chat_id=ref_id,
                        text=(
                            f"{E['LIKE']} <b>THÔNG BÁO MỞ KHÓA RÚT TIỀN!</b>\n"
                            f"━━━━━━━━━━━━━━━━━━\n"
                            f"{E['LOVE_FACE']} Thành viên được bạn mời (<b>{username_str}</b> - <code>{user.id}</code>) đã tham gia lại nhóm/kênh đối tác.\n"
                            f"{E['ROCK']} <b>Hệ thống đã tự động mở khóa tính năng rút tiền cho bạn!</b>"
                        ),
                        parse_mode="HTML",
                    )
                except Exception as exc:
                    logger.warning("Không gửi được thông báo mở khóa rút tiền cho referrer %s: %s", ref_id, exc)


# ============================================================
# ANTI SPAM
# ============================================================

async def handle_anti_spam(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    chat = update.effective_chat
    user = update.effective_user
    message = update.effective_message

    if not chat or chat.type != "private":
        return False

    if not user or user.id in ADMIN_IDS or not message:
        return False

    now = datetime.now()
    ban_until = temp_bans.get(user.id)
    if ban_until:
        if now < ban_until:
            remaining_seconds = max(0, int((ban_until - now).total_seconds()))
            minutes = remaining_seconds // 60
            seconds = remaining_seconds % 60
            await message.reply_text(
                f"{E['DISLIKE']} <b>BẠN ĐÃ BỊ TẠM CẤM!</b>\n"
                f"{E['BANDAGE']} Vui lòng chờ: <b>{minutes} phút {seconds} giây</b>\n"
                f"{E['THERMOMETER']} Lý do: <b>Spam tin nhắn quá nhanh.</b>",
                parse_mode="HTML"
            )
            return True
        temp_bans.pop(user.id, None)

    times = user_msg_tracker[user.id]
    times.append(now)
    cutoff = now - timedelta(seconds=SPAM_WINDOW_SECONDS)
    user_msg_tracker[user.id] = [t for t in times if t >= cutoff]

    if len(user_msg_tracker[user.id]) >= SPAM_MAX_MESSAGES:
        temp_bans[user.id] = now + timedelta(minutes=TEMP_BAN_MINUTES)
        user_msg_tracker[user.id].clear()
        await message.reply_text(
            f"{E['DISLIKE']} <b>CẢNH BÁO ANTI-SPAM</b>\n"
            f"{E['DIZZY']} Bạn đã bị cấm <b>{TEMP_BAN_MINUTES} phút</b>!\n"
            f"{E['THERMOMETER']} Lý do: Gửi quá <b>{SPAM_MAX_MESSAGES} tin nhắn</b> trong <b>{SPAM_WINDOW_SECONDS}s</b>.",
            parse_mode="HTML"
        )
        return True

    return False


# ============================================================
# USER
# ============================================================

async def ensure_user_exists(update: Update):
    user = update.effective_user
    if not user:
        return None
    row = await db_query(
        "SELECT user_id, balance, bank_info, is_banned, is_withdraw_banned, referrer_id FROM users WHERE user_id=%s",
        (user.id,),
        fetchone=True,
    )
    if row:
        current_username = user.username or ""
        await db_query(
            "UPDATE users SET username=%s WHERE user_id=%s",
            (current_username, user.id),
            commit=True,
        )
    else:
        await db_query(
            "INSERT INTO users (user_id, username, balance, joined_at) VALUES (%s, %s, 0, %s) ON CONFLICT (user_id) DO NOTHING",
            (user.id, user.username or "", get_now_str()),
            commit=True,
        )
        row = await db_query(
            "SELECT user_id, balance, bank_info, is_banned, is_withdraw_banned, referrer_id FROM users WHERE user_id=%s",
            (user.id,),
            fetchone=True,
        )
    return row


# ============================================================
# START
# ============================================================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await handle_anti_spam(update, context):
        return
    user = update.effective_user
    chat = update.effective_chat
    if not user or not chat:
        return
    if chat.type != "private":
        await db_query(
            "INSERT INTO groups(chat_id) VALUES(%s) ON CONFLICT (chat_id) DO NOTHING",
            (chat.id,),
            commit=True,
        )
        return
    if await is_maintenance() and user.id not in ADMIN_IDS:
        await update.message.reply_text(
            f"{E['DIZZY']} <b>HỆ THỐNG ĐANG BẢO TRÌ</b>\n"
            f"{E['BANDAGE']} Bot đang thực hiện nâng cấp định kỳ, vui lòng quay lại sau!",
            parse_mode="HTML"
        )
        return

    db_user = await db_query(
        "SELECT user_id, is_banned, referrer_id FROM users WHERE user_id=%s",
        (user.id,),
        fetchone=True,
    )

    if db_user and db_user[1] == 1:
        await update.message.reply_text(
            f"{E['DISLIKE']} <b>Tài khoản của bạn đã bị cấm vĩnh viễn khỏi hệ thống!</b>",
            parse_mode="HTML"
        )
        return

    referrer_id = None
    if context.args:
        try:
            ref_id = int(context.args[0])
            if ref_id != user.id:
                referrer_id = ref_id
        except (ValueError, TypeError):
            pass

    if not db_user:
        await db_query(
            "INSERT INTO users (user_id, username, balance, referrer_id, joined_at) VALUES (%s, %s, 0, %s, %s) ON CONFLICT (user_id) DO NOTHING",
            (user.id, user.username or "", referrer_id, get_now_str()),
            commit=True,
        )
    else:
        await db_query(
            "UPDATE users SET username=%s WHERE user_id=%s",
            (user.username or "", user.id),
            commit=True,
        )

    missing_channels = await get_missing_channels(context.bot, user.id)
    if missing_channels:
        buttons = build_channel_buttons(missing_channels)
        missing_text = "\n".join([f"• <b>{ch}</b>" for ch in missing_channels])
        await update.message.reply_text(
            f"{E['THERMOMETER']} <b>BẠN CHƯA THAM GIA ĐỦ CÁC KÊNH/NHÓM!</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"{E['DIZZY']} Bạn còn thiếu <b>{len(missing_channels)}</b> kênh/nhóm sau:\n\n"
            f"{missing_text}\n\n"
            f"{E['POINT_RIGHT']} Vui lòng tham gia đầy đủ rồi bấm nút <b>XÁC NHẬN ĐÃ THAM GIA</b> bên dưới!",
            reply_markup=InlineKeyboardMarkup(buttons),
            parse_mode="HTML",
        )
        return
    await update.message.reply_text(
        f"{E['LOVE_FACE']} <b>CHÀO MỪNG BẠN TRỜ LẠI HỆ THỐNG!</b>\n"
        f"{E['ROCK']} Hãy chọn một tính năng trong menu bên dưới:",
        reply_markup=get_main_keyboard(),
        parse_mode="HTML"
    )


# ============================================================
# GỬI CAPTCHA
# ============================================================

async def send_captcha_challenge(update_or_query, context: ContextTypes.DEFAULT_TYPE, message_text=""):
    a, b, correct_ans, options = generate_captcha()
    context.user_data["captcha_ans"] = correct_ans
    buttons = []
    row = []
    for opt in options:
        row.append(InlineKeyboardButton(f"🔹 {opt}", callback_data=f"captcha_{opt}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    caption = (f"{message_text}\n\n" if message_text else "")
    caption += (
        f"{E['ROCK']} <b>XÁC MINH CAPTCHA BẢO MẬT</b>\n"
        f"{E['POINT_RIGHT']} Vui lòng giải phép tính bên dưới để hoàn tất đăng ký:\n"
        f"{E['BANDAGE']} <b>{a} + {b} = ?</b>"
    )
    if hasattr(update_or_query, "edit_message_text"):
        await update_or_query.edit_message_text(
            caption,
            reply_markup=InlineKeyboardMarkup(buttons),
            parse_mode="HTML",
        )
    else:
        await context.bot.send_message(
            chat_id=update_or_query.from_user.id,
            text=caption,
            reply_markup=InlineKeyboardMarkup(buttons),
            parse_mode="HTML",
        )


# ============================================================
# VERIFY JOIN
# ============================================================

async def verify_join_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query:
        return
    user = query.from_user
    try:
        await query.answer()
    except Exception:
        pass
    if await is_maintenance() and user.id not in ADMIN_IDS:
        try:
            await query.answer("🔴 Hệ thống đang bảo trì.", show_alert=True)
        except Exception:
            pass
        return
    missing_channels = await get_missing_channels(context.bot, user.id)
    if missing_channels:
        buttons = build_channel_buttons(missing_channels)
        missing_text = "\n".join([f"• <b>{ch}</b>" for ch in missing_channels])
        try:
            await query.edit_message_text(
                f"{E['THERMOMETER']} <b>BẠN CHƯA THAM GIA ĐỦ CÁC KÊNH/NHÓM!</b>\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"{E['DIZZY']} Bạn vẫn chưa tham gia đủ <b>{len(missing_channels)}</b> kênh/nhóm sau:\n\n"
                f"{missing_text}\n\n"
                f"{E['POINT_RIGHT']} Vui lòng tham gia đầy đủ rồi bấm nút bên dưới để xác nhận lại!",
                reply_markup=InlineKeyboardMarkup(buttons),
                parse_mode="HTML",
            )
        except Exception:
            pass
        return
    await send_captcha_challenge(query, context)


# ============================================================
# CAPTCHA CALLBACK
# ============================================================

async def captcha_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query:
        return
    user = query.from_user
    data = query.data or ""
    try:
        selected_ans = int(data.split("_")[1])
    except (IndexError, ValueError):
        return
    correct_ans = context.user_data.get("captcha_ans")
    if selected_ans != correct_ans:
        try:
            await query.answer("❌ Phép tính sai! Vui lòng thử lại.", show_alert=True)
        except Exception:
            pass
        await send_captcha_challenge(
            query,
            context,
            message_text=f"{E['THERMOMETER']} <b>Bạn đã chọn sai kết quả! Vui lòng tính lại.</b>",
        )
        return
    context.user_data.pop("captcha_ans", None)
    try:
        await query.answer("✅ Xác minh CAPTCHA thành công!")
    except Exception:
        pass
    db_user = await db_query(
        "SELECT referrer_id FROM users WHERE user_id=%s",
        (user.id,),
        fetchone=True,
    )
    if db_user and db_user[0]:
        ref_id = db_user[0]
        try:
            def reward_referrer(cursor):
                details = f"Mời {user.id}"
                cursor.execute(
                    "INSERT INTO transactions (user_id, type, amount, status, created_at, details) VALUES (%s, %s, %s, %s, %s, %s)",
                    (ref_id, "Thưởng Mời Bạn", REFERRAL_REWARD, "Thành công", get_now_str(), details),
                )
                cursor.execute(
                    "UPDATE users SET balance = balance + %s WHERE user_id=%s",
                    (REFERRAL_REWARD, ref_id),
                )
                return True
            rewarded = await db_transaction(reward_referrer)
            if rewarded:
                username_str = f"@{user.username}" if user.username else str(user.id)
                try:
                    await context.bot.send_message(
                        chat_id=ref_id,
                        text=(
                            f"{E['LOVE_FACE']} <b>THƯỞNG MỜI BẠN BÈ!</b>\n"
                            f"{E['LIKE']} Bạn nhận được <b>+{REFERRAL_REWARD:,}đ</b>\n"
                            f"{E['POINT_RIGHT']} Từ người dùng: <b>{username_str}</b>"
                        ),
                        parse_mode="HTML"
                    )
                except Exception as exc:
                    logger.warning("Không gửi được thông báo referrer: %s", exc)
        except Exception as exc:
            logger.exception("Lỗi transaction thưởng giới thiệu: %s", exc)
    try:
        await query.delete_message()
    except Exception:
        pass
    await context.bot.send_message(
        chat_id=user.id,
        text=(
            f"{E['LAUGH']} <b>XÁC MINH THÀNH CÔNG!</b>\n"
            f"{E['ROCK']} <b>Chào mừng bạn đã gia nhập hệ thống Bot VIP!</b>"
        ),
        reply_markup=get_main_keyboard(),
        parse_mode="HTML",
    )


# ============================================================
# MENU & RÚT CODE CALLBACKS
# ============================================================

async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    user = update.effective_user
    if not message or not user:
        return
    if update.effective_chat.type != "private":
        return
    db_user = await ensure_user_exists(update)
    user_withdraw_state.pop(user.id, None)
    if await is_maintenance() and user.id not in ADMIN_IDS:
        await message.reply_text(
            f"{E['DIZZY']} <b>HỆ THỐNG ĐANG BẢO TRÌ</b>\n"
            f"{E['BANDAGE']} Vui lòng quay lại sau!",
            parse_mode="HTML"
        )
        return
    if not db_user or db_user[3] == 1:
        await message.reply_text(
            f"{E['DISLIKE']} <b>Tài khoản của bạn đã bị cấm khỏi hệ thống!</b>",
            parse_mode="HTML"
        )
        return
    if user.id not in ADMIN_IDS:
        missing_channels = await get_missing_channels(context.bot, user.id)
        if missing_channels:
            buttons = build_channel_buttons(missing_channels)
            missing_text = "\n".join([f"• <b>{ch}</b>" for ch in missing_channels])
            await message.reply_text(
                f"{E['THERMOMETER']} <b>BẠN CHƯA THAM GIA ĐỦ CÁC KÊNH/NHÓM!</b>\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"{E['DIZZY']} Bạn còn thiếu <b>{len(missing_channels)}</b> kênh/nhóm sau:\n\n"
                f"{missing_text}\n\n"
                f"{E['POINT_RIGHT']} Vui lòng tham gia đầy đủ rồi bấm nút bên dưới để tiếp tục!",
                reply_markup=InlineKeyboardMarkup(buttons),
                parse_mode="HTML"
            )
            return
    text = (message.text or "").strip()
    if text in ["Tài Khoản", "👤 Tài Khoản"]:
        balance = db_user[1]
        res = await db_query("SELECT COUNT(*) FROM users WHERE referrer_id=%s", (user.id,), fetchone=True)
        invited_count = res[0]
        res_withdraw = await db_query(
            "SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE user_id=%s AND type LIKE 'Mua Code%%' AND status='Thành công'",
            (user.id,),
            fetchone=True,
        )
        total_withdraw = res_withdraw[0]
        msg = (
            f"{E['LOVE_FACE']} <b>THÔNG TIN TÀI KHOẢN VIP</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"{E['POINT_RIGHT']} <b>ID:</b> <code>{user.id}</code>\n"
            f"{E['LIKE']} <b>Số dư:</b> <code>{balance:,}đ</code>\n"
            f"{E['ROCK']} <b>Đã mời:</b> <code>{invited_count}</code> người\n"
            f"{E['HANDSHAKE']} <b>Đã dùng mua Code:</b> <code>{total_withdraw:,}đ</code>"
        )
        await message.reply_text(msg, parse_mode="HTML")
    elif text in ["Mời Bạn Bè", "🎁 Mời Bạn Bè"]:
        try:
            bot_info = await context.bot.get_me()
            bot_username = bot_info.username
        except Exception as exc:
            logger.exception("Không lấy được username bot: %s", exc)
            await message.reply_text("❌ Không lấy được thông tin bot. Vui lòng thử lại.")
            return
        if not bot_username:
            await message.reply_text("❌ Bot chưa có username, không thể tạo link mời.")
            return
        ref_link = f"https://t.me/{bot_username}?start={user.id}"
        msg = (
            f"{E['LOVE_FACE']} <b>CHƯƠNG TRÌNH MỜI BẠN BÈ</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"{E['POINT_RIGHT']} <b>Link giới thiệu của bạn:</b>\n"
            f"<code>{ref_link}</code>\n\n"
            f"{E['BANDAGE']} <b>Thể lệ nhận thưởng:</b>\n"
            f"• {E['LIKE']} Nhận ngay: <b>+{REFERRAL_REWARD:,}đ</b> / lượt mời thành công.\n"
            f"• {E['POINT_RIGHT']} Bạn bè phải tham gia đủ kênh & hoàn thành CAPTCHA.\n"
            f"• {E['ROCK']} Min rút tối thiểu: <b>{MIN_WITHDRAW:,}đ</b>\n"
            f"• {E['SHIELD']} Rút tối đa: <b>{MAX_WITHDRAW:,}đ</b>"
        )
        await message.reply_text(msg, parse_mode="HTML")
    elif text in ["Top", "🔝 Top"]:
        top_users = await db_query(
            """
            SELECT u.user_id, u.username, COUNT(r.user_id) AS ref_count
            FROM users u
            JOIN users r ON r.referrer_id = u.user_id
            WHERE u.is_banned = 0
            GROUP BY u.user_id, u.username
            ORDER BY ref_count DESC
            LIMIT 10
            """,
            fetchall=True
        )
        if not top_users:
            await message.reply_text(f"{E['BANDAGE']} <b>Hiện chưa có ai trong bảng xếp hạng Top tuyển ref!</b>", parse_mode="HTML")
            return
        
        msg = f"{E['ROCK']} <b>TOP 10 THÀNH VIÊN TUYỂN REF NHIỀU NHẤT</b>\n━━━━━━━━━━━━━━━━━━\n\n"
        for idx, (top_id, top_username, ref_count) in enumerate(top_users, start=1):
            name_str = f"@{top_username}" if top_username else f"User {top_id}"
            icon = E['LIKE'] if idx <= 3 else E['POINT_RIGHT']
            msg += f"{icon} <b>Top {idx}:</b> {name_str} — <code>{ref_count:,}</code> bạn bè\n"
            
        await message.reply_text(msg, parse_mode="HTML")
    elif text in ["Nhóm Hỗ Trợ", "💬 Nhóm Hỗ Trợ"]:
        await message.reply_text(
            f"{E['WAVE']} <b>NHÓM HỖ TRỢ CHÍNH THỨC:</b>\n👉 {SUPPORT_GROUP}\n\n"
            f"{E['ROCK']} <b>ADMIN:</b> @echcutodz",
            parse_mode="HTML",
        )
    elif text in ["Lịch Sử", "Lịch Sử Giao Dịch", "📜 Lịch Sử Giao Dịch"]:
        txs = await db_query(
            "SELECT type, amount, status, created_at, details FROM transactions WHERE user_id=%s ORDER BY id DESC LIMIT 10",
            (user.id,),
            fetchall=True,
        )
        if not txs:
            await message.reply_text(f"{E['BANDAGE']} <b>Bạn chưa có giao dịch nào.</b>", parse_mode="HTML")
            return
        msg = f"{E['ROCK']} <b>LỊCH SỬ GIAO DỊCH GẦN ĐÂY</b>\n━━━━━━━━━━━━━━━━━━\n\n"
        for tx_type, amount, status, created_at, details in txs:
            icon = E['LIKE'] if status == "Thành công" else E['DISLIKE']
            msg += (
                f"{icon} <b>{tx_type}</b>: <code>{amount:,}đ</code>\n"
                f"{E['SHIELD']} Chi tiết: <code>{details or 'Không có'}</code>\n"
                f"{E['BANDAGE']} Thời gian: <code>{created_at}</code>\n"
                "----------------------------------\n"
            )
        await message.reply_text(msg, parse_mode="HTML")
    elif text in ["Rút Code", "💳 Rút Code", "Rút Tiền", "💳 Rút Tiền"]:
        if db_user[4] == 1:
            await message.reply_text(f"{E['DISLIKE']} <b>Tài khoản của bạn đã bị CẤM RÚT CODE!</b>", parse_mode="HTML")
            return
        
        buttons = [
            [
                InlineKeyboardButton("🛡 Code 3.500đ", callback_data="buycode_select_1"),
                InlineKeyboardButton("🗡 Code 6.000đ", callback_data="buycode_select_2"),
            ]
        ]
        await message.reply_text(
            f"{E['SHIELD']} <b>HỆ THỐNG RÚT CODE TỰ ĐỘNG</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"{E['LIKE']} <b>Số dư hiện tại:</b> <code>{db_user[1]:,}đ</code>\n\n"
            f"{E['LOVE_FACE']} Vui lòng chọn loại Code bạn muốn đổi:",
            reply_markup=InlineKeyboardMarkup(buttons),
            parse_mode="HTML"
        )


# Callback chọn loại Code và Xác Nhận Mua
async def code_buy_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query:
        return
    user = query.from_user
    data = query.data or ""
    try:
        await query.answer()
    except Exception:
        pass

    db_user = await db_query(
        "SELECT balance, is_banned, is_withdraw_banned FROM users WHERE user_id=%s",
        (user.id,),
        fetchone=True,
    )
    if not db_user or db_user[1] == 1:
        await query.edit_message_text(f"{E['DISLIKE']} Tài khoản của bạn đã bị khóa!")
        return
    if db_user[2] == 1:
        await query.edit_message_text(f"{E['DISLIKE']} Tài khoản của bạn đã bị cấm rút code!")
        return

    balance = db_user[0]

    if data.startswith("buycode_select_"):
        code_type = int(data.split("_")[2])
        cost = 3500 if code_type == 1 else 6000
        val = 6666 if code_type == 1 else 12222
        
        buttons = [
            [
                InlineKeyboardButton(f"✅ XÁC NHẬN MUA ({cost:,}đ)", callback_data=f"buycode_confirm_{code_type}")
            ]
        ]
        await query.edit_message_text(
            f"{E['SHIELD']} <b>XÁC NHẬN ĐỔI CODE</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"{E['SWORD']} <b>Loại Code:</b> Code {cost:,}đ\n"
            f"{E['LOVE_FACE']} <b>Trị giá Code:</b> <code>{val:,}đ</code>\n"
            f"{E['LIKE']} <b>Giá mua:</b> <code>{cost:,}đ</code>\n"
            f"{E['ROCK']} <b>Số dư của bạn:</b> <code>{balance:,}đ</code>\n\n"
            f"<i>Bấm nút bên dưới để tiến hành thanh toán và lấy mã Code!</i>",
            reply_markup=InlineKeyboardMarkup(buttons),
            parse_mode="HTML"
        )

    elif data.startswith("buycode_confirm_"):
        code_type = int(data.split("_")[2])
        cost = 3500 if code_type == 1 else 6000
        val = 6666 if code_type == 1 else 12222

        if balance < cost:
            await query.edit_message_text(
                f"{E['DISLIKE']} <b>SỐ DƯ KHÔNG ĐỦ!</b>\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"Bạn cần <b>{cost:,}đ</b> để mua loại Code này. Số dư hiện tại: <b>{balance:,}đ</b>"
            )
            return

        def process_buy_code(cursor):
            # Kiểm tra kho code
            cursor.execute(
                "SELECT id, code_val FROM code_stock WHERE type_code=%s AND is_used=0 ORDER BY id ASC LIMIT 1 FOR UPDATE",
                (code_type,)
            )
            stock_item = cursor.fetchone()
            if not stock_item:
                return "OUT_OF_STOCK"

            code_stock_id, code_val = stock_item

            # Trừ tiền
            cursor.execute(
                "UPDATE users SET balance = balance - %s WHERE user_id=%s AND balance >= %s",
                (cost, user.id, cost)
            )
            if cursor.rowcount != 1:
                return "NOT_ENOUGH_BALANCE"

            # Đánh dấu code đã dùng
            cursor.execute(
                "UPDATE code_stock SET is_used=1 WHERE id=%s",
                (code_stock_id,)
            )

            # Ghi lịch sử giao dịch
            details = f"Code: {code_val}"
            cursor.execute(
                "INSERT INTO transactions (user_id, type, amount, status, created_at, details) VALUES (%s, %s, %s, %s, %s, %s)",
                (user.id, f"Mua Code {cost}đ", cost, "Thành công", get_now_str(), details)
            )
            return code_val

        try:
            result = await db_transaction(process_buy_code)
        except Exception as exc:
            logger.exception("Lỗi khi mua code: %s", exc)
            await query.edit_message_text("❌ Đã xảy ra lỗi trong quá trình xử lý mua code.")
            return

        if result == "OUT_OF_STOCK":
            await query.edit_message_text(
                f"{E['THERMOMETER']} <b>RẤT TIẾC, KHO CODE NÀY ĐÃ HẾT!</b>\n"
                f"Vui lòng liên hệ Admin hoặc quay lại sau.",
                parse_mode="HTML"
            )
        elif result == "NOT_ENOUGH_BALANCE":
            await query.edit_message_text(f"{E['DISLIKE']} Số dư không đủ!")
        else:
            await query.edit_message_text(
                f"{E['LOVE_FACE']} <b>MUA CODE THÀNH CÔNG!</b>\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"{E['LIKE']} <b>Số Tiền Mua:</b> {cost:,}đ\n"
                f"{E['ROCK']} <b>Code Trị Giá:</b> {val:,}đ\n"
                f"{E['POINT_RIGHT']} <b>Mã Code:</b> <code>{result}</code>\n\n"
                f"{E['THERMOMETER']} <b>Quy Định Rút Code</b>\n"
                f"1. Cược Đủ 3 Vòng Cược Của Code\n"
                f"2. Tài Khoản Tân Thủ Đánh Code Lên Yêu Cầu Nạp 50K Để Rút\n"
                f"3. Tài Khoản Nào Đã Có Lịch Sử Nạp Trên 50K Rút Không Cần Nạp\n"
                f"4. Không Được Dồn Quá 5 Code Cho 1 Tài Khoản\n"
                f"{E['POOP']} Phát Hiện Khấu Toàn Bộ Số Dư",
                parse_mode="HTML"
            )


# ============================================================
# ADMIN COMMANDS
# ============================================================

def is_admin(update: Update):
    return bool(update.effective_user and update.effective_user.id in ADMIN_IDS)


async def admin_commands(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return
    message = update.effective_message
    if not message:
        return
    cmd = (message.text or "").split()[0].split("@")[0].lower()
    args = context.args or []
    raw_text = message.text or ""
    try:
        # Lệnh thêm Code 3500đ (/code1) & 6000đ (/code2)
        if cmd in ["/code1", "/code2"]:
            type_code = 1 if cmd == "/code1" else 2
            price_label = "3.500đ" if type_code == 1 else "6.000đ"
            
            lines = raw_text.split(maxsplit=1)
            if len(lines) < 2:
                await message.reply_text(
                    f"{E['THERMOMETER']} <b>Cú pháp:</b> <code>{cmd} mã_code1 mã_code2 ...</code>\n"
                    f"Hoặc xuống dòng từng mã code để thêm số lượng lớn.",
                    parse_mode="HTML"
                )
                return
            
            codes_raw = lines[1]
            codes = re.split(r"[\s\n]+", codes_raw.strip())
            codes = [c.strip() for c in codes if c.strip()]
            
            if not codes:
                await message.reply_text("❌ Không tìm thấy mã code hợp lệ.")
                return

            def add_codes(cursor):
                now = get_now_str()
                count = 0
                for c in codes:
                    cursor.execute(
                        "INSERT INTO code_stock (type_code, code_val, created_at) VALUES (%s, %s, %s)",
                        (type_code, c, now)
                    )
                    count += 1
                return count

            added_count = await db_transaction(add_codes)
            await message.reply_text(
                f"{E['LIKE']} <b>THÊM KHO CODE THÀNH CÔNG!</b>\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"• Loại code: <b>{price_label}</b>\n"
                f"• Đã thêm: <b>{added_count:,}</b> code vào kho.",
                parse_mode="HTML"
            )

        # Lệnh xóa Code 3500đ (/xoacode1) & 6000đ (/xoacode2)
        elif cmd in ["/xoacode1", "/xoacode2"]:
            type_code = 1 if cmd == "/xoacode1" else 2
            price_label = "3.500đ" if type_code == 1 else "6.000đ"

            lines = raw_text.split(maxsplit=1)
            if len(lines) < 2:
                await message.reply_text(
                    f"{E['THERMOMETER']} <b>Cú pháp:</b> <code>{cmd} mã_code1 mã_code2 ...</code>\n"
                    f"Hoặc xuống dòng từng mã code để xóa nhiều code cùng lúc.",
                    parse_mode="HTML"
                )
                return

            codes_raw = lines[1]
            codes = re.split(r"[\s\n]+", codes_raw.strip())
            codes = [c.strip() for c in codes if c.strip()]

            if not codes:
                await message.reply_text("❌ Không tìm thấy mã code hợp lệ để xóa.")
                return

            def delete_codes(cursor):
                cursor.execute(
                    "DELETE FROM code_stock WHERE type_code=%s AND code_val = ANY(%s)",
                    (type_code, codes)
                )
                return cursor.rowcount

            deleted_count = await db_transaction(delete_codes)
            await message.reply_text(
                f"{E['DISLIKE']} <b>XÓA KHO CODE THÀNH CÔNG!</b>\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"• Loại code: <b>{price_label}</b>\n"
                f"• Đã xóa thành công: <b>{deleted_count:,} / {len(codes):,}</b> code khỏi kho.",
                parse_mode="HTML"
            )

        elif cmd == "/kho":
            res1 = await db_query("SELECT COUNT(*) FROM code_stock WHERE type_code=1 AND is_used=0", fetchone=True)
            res2 = await db_query("SELECT COUNT(*) FROM code_stock WHERE type_code=2 AND is_used=0", fetchone=True)
            cnt1 = res1[0] if res1 else 0
            cnt2 = res2[0] if res2 else 0
            
            await message.reply_text(
                f"{E['ROCK']} <b>THỐNG KÊ KHO CODE HIỆN TẠI</b>\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"• Kho Code 3.500đ: <b>{cnt1:,}</b> code chưa dùng\n"
                f"• Kho Code 6.000đ: <b>{cnt2:,}</b> code chưa dùng",
                parse_mode="HTML"
            )

        # LỆNH MỚI: DÙNG ĐỂ XEM DANH SÁCH NHỮNG AI ĐÃ RÚT CODE FULL THÔNG TIN
        elif cmd == "/rutcode":
            rows = await db_query(
                """
                SELECT t.user_id, u.username, t.type, t.details, t.created_at
                FROM transactions t
                LEFT JOIN users u ON t.user_id = u.user_id
                WHERE t.type LIKE 'Mua Code%' AND t.status = 'Thành công'
                ORDER BY t.id DESC
                LIMIT 30
                """,
                fetchall=True
            )
            if not rows:
                await message.reply_text(f"{E['BANDAGE']} <b>Chưa có người dùng nào rút code!</b>", parse_mode="HTML")
                return

            msg = f"{E['ROCK']} <b>DANH SÁCH THÀNH VIÊN ĐÃ RÚT CODE (30 MỚI NHẤT)</b>\n━━━━━━━━━━━━━━━━━━\n\n"
            for user_id, username, code_type_str, details, created_at in rows:
                user_tag = f"@{username}" if username else f"Chưa có @username"
                msg += (
                    f"{E['POINT_RIGHT']} <b>User:</b> {user_tag} | <b>ID:</b> <code>{user_id}</code>\n"
                    f"{E['LIKE']} <b>Loại Code:</b> <code>{code_type_str}</code>\n"
                    f"{E['SHIELD']} <b>Nội dung:</b> <code>{details or 'Không rõ'}</code>\n"
                    f"{E['BANDAGE']} <b>Thời gian:</b> <code>{created_at}</code>\n"
                    "----------------------------------\n"
                )
            await message.reply_text(msg, parse_mode="HTML")

        elif cmd == "/resetall":
            await db_query("TRUNCATE TABLE users, transactions, code_stock RESTART IDENTITY", commit=True)
            user_msg_tracker.clear()
            temp_bans.clear()
            user_withdraw_state.clear()
            await db_query(
                "INSERT INTO users (user_id, username, balance, joined_at) VALUES (%s, %s, 0, %s) ON CONFLICT (user_id) DO NOTHING",
                (message.from_user.id, message.from_user.username or "", get_now_str()),
                commit=True
            )
            await message.reply_text(
                f"{E['WAVE']} <b>ĐÃ RESET TOÀN BỘ HỆ THỐNG!</b>\n"
                f"• Toàn bộ người dùng, kho code & lịch sử giao dịch đã được xóa hoàn toàn.",
                parse_mode="HTML"
            )
        elif cmd == "/tong":
            res = await db_query("SELECT COUNT(*) FROM users", fetchone=True)
            total_users = res[0]
            users = await db_query("SELECT user_id, username FROM users ORDER BY joined_at DESC LIMIT 50", fetchall=True)
            msg = (
                f"{E['ROCK']} <b>THỐNG KÊ TỔNG NGUỜI DÙNG</b>\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"{E['LIKE']} Tổng số người dùng trong hệ thống: <b>{total_users:,}</b>\n\n"
                f"{E['POINT_RIGHT']} <b>Bấm vào nút ID bên dưới để kiểm tra full thông tin:</b>"
            )
            buttons = []
            row = []
            for u_id, u_name in users:
                btn_text = f"🆔 {u_id}"
                if u_name:
                    btn_text += f" (@{u_name})"
                row.append(InlineKeyboardButton(btn_text, callback_data=f"userinfo_{u_id}"))
                if len(row) == 2:
                    buttons.append(row)
                    row = []
            if row:
                buttons.append(row)
            await message.reply_text(
                msg,
                reply_markup=InlineKeyboardMarkup(buttons) if buttons else None,
                parse_mode="HTML",
            )
        elif cmd == "/tb":
            if not args:
                await message.reply_text(f"Cú pháp: <code>/tb Nội dung thông báo</code>", parse_mode="HTML")
                return
            content = " ".join(args).strip()
            users = await db_query("SELECT user_id FROM users WHERE is_banned=0", fetchall=True)
            groups = await db_query("SELECT chat_id FROM groups", fetchall=True)
            count = 0
            for (target_id,) in users:
                try:
                    await context.bot.send_message(
                        chat_id=target_id,
                        text=f"{E['ROCK']} <b>THÔNG BÁO HỆ THỐNG</b>\n━━━━━━━━━━━━━━━━━━\n\n{content}",
                        parse_mode="HTML",
                    )
                    count += 1
                except Exception:
                    pass
                await asyncio.sleep(0.05)
            for (chat_id,) in groups:
                try:
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text=f"{E['ROCK']} <b>THÔNG BÁO HỆ THỐNG</b>\n━━━━━━━━━━━━━━━━━━\n\n{content}",
                        parse_mode="HTML",
                    )
                    count += 1
                except Exception:
                    pass
                await asyncio.sleep(0.05)
            await message.reply_text(f"{E['LIKE']} Đã phát thông báo tới <b>{count}</b> người dùng/nhóm.", parse_mode="HTML")
        elif cmd == "/info":
            if len(args) < 1:
                await message.reply_text(f"{E['POINT_RIGHT']} <b>Cú pháp:</b> <code>/info USER_ID</code>", parse_mode="HTML")
                return
            try:
                target_id = int(args[0])
            except (ValueError, TypeError):
                await message.reply_text("❌ USER_ID không hợp lệ.")
                return
            u = await db_query("SELECT * FROM users WHERE user_id=%s", (target_id,), fetchone=True)
            if not u:
                await message.reply_text("❌ Không tìm thấy user này.")
                return
            res = await db_query("SELECT COUNT(*) FROM users WHERE referrer_id=%s", (target_id,), fetchone=True)
            invited_count = res[0]
            username = f"@{u[1]}" if u[1] else "Chưa đặt"
            referrer = u[4] if u[4] is not None else "Không có"
            msg = (
                f"{E['LOVE_FACE']} <b>THÔNG TIN CHI TIẾT USER</b>\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"{E['POINT_RIGHT']} ID: <code>{u[0]}</code>\n"
                f"{E['ROCK']} Username: {username}\n"
                f"{E['LIKE']} Số dư: <code>{u[2]:,}đ</code>\n"
                f"{E['POINT_RIGHT']} Khách giới thiệu: <code>{referrer}</code>\n"
                f"{E['ROCK']} Tổng đã mời: <code>{invited_count}</code> người\n"
                f"{E['DISLIKE']} Khóa TK: <b>{'CÓ' if u[5] else 'KHÔNG'}</b>\n"
                f"{E['DIZZY']} Cấm rút code: <b>{'CÓ' if u[6] else 'KHÔNG'}</b>\n"
                f"{E['BANDAGE']} Tham gia: <code>{u[7]}</code>"
            )
            await message.reply_text(msg, parse_mode="HTML")
        elif cmd == "/ban":
            if len(args) < 1:
                await message.reply_text("Cú pháp: <code>/ban USER_ID</code>", parse_mode="HTML")
                return
            target_id = int(args[0])
            await db_query("UPDATE users SET is_banned=1 WHERE user_id=%s", (target_id,), commit=True)
            user_withdraw_state.pop(target_id, None)
            await message.reply_text(f"{E['DISLIKE']} Đã cấm vĩnh viễn user <code>{target_id}</code>.", parse_mode="HTML")
        elif cmd == "/moban":
            if len(args) < 1:
                await message.reply_text(f"{E['POINT_RIGHT']} <b>Cú pháp:</b> <code>/moban USER_ID</code>", parse_mode="HTML")
                return
            target_id = int(args[0])
            await db_query("UPDATE users SET is_banned=0 WHERE user_id=%s", (target_id,), commit=True)
            await message.reply_text(f"{E['LIKE']} <b>Đã mở ban tài khoản cho ID:</b> <code>{target_id}</code>", parse_mode="HTML")
        elif cmd == "/cam":
            if len(args) < 1:
                await message.reply_text("Cú pháp: <code>/cam USER_ID</code>", parse_mode="HTML")
                return
            target_id = int(args[0])
            await db_query("UPDATE users SET is_withdraw_banned=1 WHERE user_id=%s", (target_id,), commit=True)
            user_withdraw_state.pop(target_id, None)
            await message.reply_text(f"{E['DIZZY']} Đã cấm rút code ID <code>{target_id}</code>.", parse_mode="HTML")
        elif cmd == "/mocam":
            if len(args) < 1:
                await message.reply_text(f"{E['POINT_RIGHT']} <b>Cú pháp:</b> <code>/mocam USER_ID</code>", parse_mode="HTML")
                return
            target_id = int(args[0])
            await db_query("UPDATE users SET is_withdraw_banned=0 WHERE user_id=%s", (target_id,), commit=True)
            await message.reply_text(f"{E['LIKE']} <b>Đã mở cấm rút code cho ID:</b> <code>{target_id}</code>", parse_mode="HTML")
        elif cmd in ("/nap", "/tru"):
            if len(args) < 2:
                await message.reply_text(f"Cú pháp: <code>{cmd} USER_ID SO_TIEN</code>", parse_mode="HTML")
                return
            target_id = int(args[0])
            amount = int(args[1])
            if amount <= 0:
                await message.reply_text("❌ Số tiền phải lớn hơn 0.")
                return
            exists = await db_query("SELECT user_id FROM users WHERE user_id=%s", (target_id,), fetchone=True)
            if not exists:
                await message.reply_text("❌ User chưa tồn tại.")
                return
            if cmd == "/nap":
                def add_money(cursor):
                    cursor.execute("UPDATE users SET balance=balance+%s WHERE user_id=%s", (amount, target_id))
                    cursor.execute(
                        "INSERT INTO transactions (user_id, type, amount, status, created_at, details) VALUES (%s, %s, %s, %s, %s, %s)",
                        (target_id, "Nạp Tiền (Admin)", amount, "Thành công", get_now_str(), "Cộng từ Admin"),
                    )
                    return True
                await db_transaction(add_money)
                await message.reply_text(f"{E['LIKE']} Đã cộng <b>+{amount:,}đ</b> cho ID <code>{target_id}</code>.", parse_mode="HTML")
            else:
                def deduct(cursor):
                    cursor.execute("UPDATE users SET balance=balance-%s WHERE user_id=%s AND balance>=%s", (amount, target_id, amount))
                    if cursor.rowcount != 1:
                        return False
                    cursor.execute(
                        "INSERT INTO transactions (user_id, type, amount, status, created_at, details) VALUES (%s, %s, %s, %s, %s, %s)",
                        (target_id, "Trừ Tiền (Admin)", amount, "Thành công", get_now_str(), "Trừ từ Admin"),
                    )
                    return True
                ok = await db_transaction(deduct)
                if not ok:
                    await message.reply_text("❌ Số dư user không đủ để trừ.")
                    return
                await message.reply_text(f"{E['DISLIKE']} Đã trừ <b>-{amount:,}đ</b> của ID <code>{target_id}</code>.", parse_mode="HTML")
        elif cmd == "/baotri":
            curr = await is_maintenance()
            new_val = "0" if curr else "1"
            await db_query("UPDATE settings SET value=%s WHERE key='maintenance'", (new_val,), commit=True)
            status_str = "BẮT ĐẦU BẢO TRÌ 🔴" if new_val == "1" else "TẮT BẢO TRÌ 🟢"
            await message.reply_text(f"{E['DIZZY']} Trạng thái hệ thống: <b>{status_str}</b>", parse_mode="HTML")
    except Exception as exc:
        logger.exception("Lỗi admin command %s: %s", cmd, exc)
        await message.reply_text("❌ Đã xảy ra lỗi khi xử lý lệnh.")


# ============================================================
# DISPATCHER
# ============================================================

async def text_message_dispatcher(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_message:
        return
    if await handle_anti_spam(update, context):
        return
    await menu_handler(update, context)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error("Exception khi xử lý update: %s", context.error, exc_info=context.error)


# ============================================================
# MAIN
# ============================================================

async def post_init(application: Application) -> None:
    await init_db()

def main():
    if not BOT_TOKEN:
        raise RuntimeError("Chưa cấu hình BOT_TOKEN.")
    if not DATABASE_URL:
        raise RuntimeError("Chưa cấu hình DATABASE_URL.")

    app = Application.builder().token(BOT_TOKEN).post_init(post_init).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(ChatMemberHandler(chat_member_updated_handler, ChatMemberHandler.CHAT_MEMBER))
    app.add_handler(CallbackQueryHandler(verify_join_callback, pattern=r"^verify_join$"))
    app.add_handler(CallbackQueryHandler(captcha_callback, pattern=r"^captcha_\d+$"))
    app.add_handler(CallbackQueryHandler(code_buy_callback, pattern=r"^buycode_"))

    admin_cmds = [
        "code1", "code2", "xoacode1", "xoacode2", "kho", "rutcode", "resetall", "tong", "tb", "info", "ban", "moban",
        "cam", "mocam", "nap", "tru", "baotri"
    ]
    for command in admin_cmds:
        app.add_handler(CommandHandler(command, admin_commands))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_message_dispatcher))
    app.add_error_handler(error_handler)

    logger.info("🤖 Bot đang chạy...")
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)


if __name__ == "__main__":
    main()
