import asyncio
import io
import logging
import os
import random
import re
import string
import urllib.parse
from collections import defaultdict
from datetime import datetime, timedelta

from dotenv import load_dotenv
import psycopg
from psycopg.rows import tuple_row
from psycopg_pool import ConnectionPool
import pytz
from PIL import Image, ImageDraw, ImageFont

load_dotenv()

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    Update,
    WebAppInfo,
)

from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# ============================================================
# CẤU HÌNH
# ============================================================

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
MINI_APP_URL = os.getenv("MINI_APP_URL", "https://phongmrom-lgtm.github.io/phongtunk/").strip()
ADMIN_IDS = [5633649201]
TIMEZONE = pytz.timezone("Asia/Ho_Chi_Minh")

REQUIRED_CHECK_CHANNELS = [
    "@khuyenmaionline", "@sanhugame", "@sancode22", "@xombao247",
    "@thongbaohit88", "@sancodehit88", "@vtc345", "@vtc567",
    "@hocviencbm", "@hongtinmoingay24", "https://t.me/conmuamenmenl",
]
OPTIONAL_DISPLAY_CHANNELS = []
SUPPORT_GROUP = "https://t.me/hocviencbm"
CODE_PRICE = 2000
MIN_WITHDRAW = 2000
MAX_WITHDRAW = 10000
REFERRAL_REWARD = 1000

# ============================================================
# DANH SÁCH CUSTOM PREMIUM EMOJI
# ============================================================
E = {
    "WAVE": '<tg-emoji emoji-id="5235701688014217208">👋</tg-emoji>',
    "SMILE": '<tg-emoji emoji-id="5238185738184435219">🙂</tg-emoji>',
    "LOVE_FACE": '<tg-emoji emoji-id="5197387964098813812">🥰</tg-emoji>',
    "BLUSH": '<tg-emoji emoji-id="5238015713314086319">☺️</tg-emoji>',
    "CAR_RED": '<tg-emoji emoji-id="5240037474679398914">🚘</tg-emoji>',
    "BANANA": '<tg-emoji emoji-id="5242466828441099349">🍌</tg-emoji>',
    "KEYBOARD": '<tg-emoji emoji-id="5242451907724716893">⌨</tg-emoji>',
    "CARD": '<tg-emoji emoji-id="5240066289614987080">💳</tg-emoji>',
    "GUN": '<tg-emoji emoji-id="5235762367312173706">🔫</tg-emoji>',
    "LIGHTNING": '<tg-emoji emoji-id="5456140674028019486">⚡</tg-emoji>',
    "CHECK": '<tg-emoji emoji-id="5206607081334906820">✔️</tg-emoji>',
    "CHECK2": '<tg-emoji emoji-id="5206607081334906820">✔</tg-emoji>',
    "CROSS": '<tg-emoji emoji-id="5210952531676504517">❌</tg-emoji>',
    "CANDLE": '<tg-emoji emoji-id="5451882707875276247">🕯</tg-emoji>',
    "CHART": '<tg-emoji emoji-id="5231200819986047254">📊</tg-emoji>',
    "MONEY_FLY": '<tg-emoji emoji-id="5231005931550030290">💸</tg-emoji>',
    "MONEY_BAG": '<tg-emoji emoji-id="5409048419211682843">💵</tg-emoji>',
    "RIGHT": '<tg-emoji emoji-id="5416117059207572332">➡️</tg-emoji>',
    "POINT_RIGHT": '<tg-emoji emoji-id="5416117059207572332">➡️️</tg-emoji>',
    "FIRE": '<tg-emoji emoji-id="5424972470023104089">🔥</tg-emoji>',
    "BOOM": '<tg-emoji emoji-id="5276032951342088188">💥</tg-emoji>',
    "REFRESH": '<tg-emoji emoji-id="5375338737028841420">🔄</tg-emoji>',
    "TOP": '<tg-emoji emoji-id="5415655814079723871">🔝</tg-emoji>',
    "PLUS": '<tg-emoji emoji-id="5397916757333654639">➕</tg-emoji>',
    "PIN": '<tg-emoji emoji-id="5391032818111363540">📍</tg-emoji>',
    "SOON": '<tg-emoji emoji-id="5440621591387980068">🔜</tg-emoji>',
    "CROWN": '<tg-emoji emoji-id="5217822164362739968">👑</tg-emoji>',
    "MAIL": '<tg-emoji emoji-id="5253742260054409879">✉️</tg-emoji>',
    "LOCK": '<tg-emoji emoji-id="5296369303661067030">🔒</tg-emoji>',
    "CLIP": '<tg-emoji emoji-id="5305265301917549162">📎</tg-emoji>',
    "GEAR": '<tg-emoji emoji-id="5341715473882955310">⚙️</tg-emoji>',
    "HOURGLASS": '<tg-emoji emoji-id="5386367538735104399">⌛</tg-emoji>',
    "SPEAKER": '<tg-emoji emoji-id="5388632425314140043">🔈</tg-emoji>',
    "GAME": '<tg-emoji emoji-id="5361741454685256344">🎮</tg-emoji>',
    "DOWN": '<tg-emoji emoji-id="5406745015365943482">⬇️</tg-emoji>',
    "DROP": '<tg-emoji emoji-id="5393512611968995988">💧</tg-emoji>',
    "SNOW": '<tg-emoji emoji-id="5449449325434266744">❄️</tg-emoji>',
    "BULB": '<tg-emoji emoji-id="5422439311196834318">💡</tg-emoji>',
    "ALARM": '<tg-emoji emoji-id="5395695537687123235">🚨</tg-emoji>',
    "PARTY": '<tg-emoji emoji-id="5461151367559141950">🎉</tg-emoji>',
    "HOME": '<tg-emoji emoji-id="5416041192905265756">🏠</tg-emoji>',
    "GIFT": '<tg-emoji emoji-id="5442939099906325301">🎁</tg-emoji>',
    "BELL": '<tg-emoji emoji-id="5440833702642857683">🔔</tg-emoji>',
    "LINK": '<tg-emoji emoji-id="5440410042773824003">🔗</tg-emoji>',
    "OUTBOX": '<tg-emoji emoji-id="5445355530111437729">📤</tg-emoji>',
    "INBOX": '<tg-emoji emoji-id="5443127283898405358">📥</tg-emoji>',
    "BAG": '<tg-emoji emoji-id="5294167145079395967">🛍</tg-emoji>',
    "BANK": '<tg-emoji emoji-id="5332455502917949981">🏦</tg-emoji>',
    "SHIELD": '<tg-emoji emoji-id="5197288647275071607">🛡</tg-emoji>',
    "MONEY": '<tg-emoji emoji-id="5278467510604160626">💰</tg-emoji>',
    "HEART": '<tg-emoji emoji-id="5267102644886853973">❤️</tg-emoji>',
    "COIN": '<tg-emoji emoji-id="5264713049637409446">🪙</tg-emoji>',
    "CAR": '<tg-emoji emoji-id="5282927142651319521">🚗</tg-emoji>',
    "LAB": '<tg-emoji emoji-id="5390919199046521002">🧪</tg-emoji>',
    "UNLOCK": '<tg-emoji emoji-id="5465443379917629504">🔓</tg-emoji>',
    "LIKE": '<tg-emoji emoji-id="5465465194056525619">👍</tg-emoji>',
    "LAUGH": '<tg-emoji emoji-id="5463121572137022242">😂</tg-emoji>',
    "BANDAGE": '<tg-emoji emoji-id="5463156928307801722">🤕</tg-emoji>',
    "OK": '<tg-emoji emoji-id="5463423955014529788">👌</tg-emoji>',
    "QUESTION": '<tg-emoji emoji-id="5463139580934892960">❓</tg-emoji>',
    "MUTE": '<tg-emoji emoji-id="5462990730253319917">🔇</tg-emoji>',
    "DESKTOP": '<tg-emoji emoji-id="5375099322666859339">🖥</tg-emoji>',
    "WARN": '<tg-emoji emoji-id="5373059848856421989">❗️</tg-emoji>',
    "EXCLAMATION_QUESTION": '<tg-emoji emoji-id="5226618356169194833">⁉️</tg-emoji>',
    "DEVIL": '<tg-emoji emoji-id="5228962845672096235">😈</tg-emoji>',
    "DISLIKE": '<tg-emoji emoji-id="5210952531676504517">❌</tg-emoji>',
    "DIZZY": '<tg-emoji emoji-id="5463156928307801722">🤕</tg-emoji>',
    "THERMOMETER": '<tg-emoji emoji-id="5373059848856421989">❗️</tg-emoji>',
    "ROCK": '<tg-emoji emoji-id="5424972470023104089">🔥</tg-emoji>',
    "PHONE": '<tg-emoji emoji-id="5242451907724716893">⌨️</tg-emoji>',
    "HANDSHAKE": '<tg-emoji emoji-id="5235701688014217208">👋</tg-emoji>',
    "CHART_UP": '<tg-emoji emoji-id="5231200819986047254">📊</tg-emoji>',
    "CHART_DOWN": '<tg-emoji emoji-id="5231200819986047254">📊</tg-emoji>',
    "UP": '<tg-emoji emoji-id="5415655814079723871">🔝</tg-emoji>',
    "PROHIBITED": '<tg-emoji emoji-id="5210952531676504517">❌</tg-emoji>',
    "NO_ENTRY": '<tg-emoji emoji-id="5210952531676504517">❌</tg-emoji>',
    "SWORD": '<tg-emoji emoji-id="5235762367312173706">🔫</tg-emoji>',
    "POOP": '<tg-emoji emoji-id="5228962845672096235">😈</tg-emoji>',
    
    "NUM_1": '<tg-emoji emoji-id="5305763715692377402">1️⃣</tg-emoji>',
    "NUM_2": '<tg-emoji emoji-id="5307907239380528763">2️⃣</tg-emoji>',
    "NUM_3": '<tg-emoji emoji-id="5859438077352612949">3️⃣</tg-emoji>',
    "NUM_4": '<tg-emoji emoji-id="5305255243104138538">4️⃣</tg-emoji>',
}

# ============================================================
# ANTI SPAM & RATE LIMIT HELPERS
# ============================================================
SPAM_WINDOW_SECONDS = 4
SPAM_MAX_MESSAGES = 10
TEMP_BAN_MINUTES = 2
user_msg_tracker = defaultdict(list)
temp_bans = {}
user_withdraw_state = {}
pending_captcha_users = {}

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
            raise RuntimeError("Chưa cấu hình DATABASE_URL.")
        db_pool = ConnectionPool(
            DATABASE_URL, min_size=1, max_size=10,
            kwargs={"row_factory": tuple_row}, open=True
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
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id BIGINT PRIMARY KEY,
                    username TEXT,
                    balance BIGINT NOT NULL DEFAULT 0,
                    bank_info TEXT,
                    referrer_id BIGINT,
                    is_banned INTEGER NOT NULL DEFAULT 0,
                    is_withdraw_banned INTEGER NOT NULL DEFAULT 0,
                    joined_at TEXT,
                    phone_number TEXT
                )
            """)
            cursor.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS ip_address TEXT;")
            cursor.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS skip_ip INTEGER DEFAULT 0;")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS transactions (
                    id BIGSERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    type TEXT NOT NULL,
                    amount BIGINT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    details TEXT
                )
            """)
            cursor.execute("CREATE TABLE IF NOT EXISTS groups (chat_id BIGINT PRIMARY KEY)")
            cursor.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS code_stock (
                    id BIGSERIAL PRIMARY KEY,
                    type_code INTEGER NOT NULL DEFAULT 1,
                    code_val TEXT NOT NULL,
                    is_used INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS code_deleted_log (
                    id BIGSERIAL PRIMARY KEY,
                    code_val TEXT NOT NULL,
                    deleted_at TEXT NOT NULL
                )
            """)
            default_settings = [
                ('maintenance', '0'), ('verify_phone', '1'), ('verify_ip', '1'),
                ('verify_channel', '1'), ('verify_captcha', '1'), ('allow_withdraw', '1')
            ]
            for key, val in default_settings:
                cursor.execute(
                    "INSERT INTO settings (key, value) VALUES (%s, %s) ON CONFLICT (key) DO NOTHING",
                    (key, val)
                )
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_transactions_user ON transactions(user_id, id DESC)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_transactions_withdraw ON transactions(type, status, id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_referrer ON users(referrer_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_code_stock ON code_stock(type_code, is_used)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_phone ON users(phone_number)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_ip ON users(ip_address)")
            cursor.execute("""
                DELETE FROM transactions t1
                USING transactions t2
                WHERE t1.id > t2.id
                  AND t1.user_id = t2.user_id
                  AND t1.details = t2.details
                  AND t1.type = 'Thưởng Mời Bạn'
                  AND t2.type = 'Thưởng Mời Bạn';
            """)
            cursor.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_ref_reward 
                ON transactions(user_id, details) 
                WHERE type='Thưởng Mời Bạn'
            """)
        conn.commit()
        logger.info("Database PostgreSQL đã sẵn sàng.")

async def init_db():
    await asyncio.to_thread(_init_db_sync)

def get_now_str():
    return datetime.now(TIMEZONE).strftime("%Y-%m-%d %H:%M:%S")

async def get_valid_referrals_count(user_id: int) -> int:
    res = await db_query(
        "SELECT COUNT(*) FROM transactions WHERE user_id=%s AND type='Thưởng Mời Bạn' AND status='Thành công'",
        (user_id,), fetchone=True
    )
    return res[0] if res else 0

# ============================================================
# CẤU HÌNH BẬT/TẮT XÁC MINH & TÍNH NĂNG
# ============================================================
async def get_verify_setting(key: str) -> bool:
    res = await db_query("SELECT value FROM settings WHERE key=%s", (key,), fetchone=True)
    return bool(res and res[0] == "1")

async def set_verify_setting(key: str, value: bool):
    val_str = "1" if value else "0"
    await db_query("UPDATE settings SET value=%s WHERE key=%s", (val_str, key), commit=True)

# ============================================================
# KEYBOARD
# ============================================================
def get_main_keyboard():
    keyboard = [
        [KeyboardButton("👤 Tài Khoản"), KeyboardButton("🎁 Mời Bạn Bè")],
        [KeyboardButton("💳 Rút Code"), KeyboardButton("🔝 Top")],
        [KeyboardButton("💬 Nhóm Hỗ Trợ"), KeyboardButton("📜 Lịch Sử Giao Dịch")],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_contact_keyboard():
    keyboard = [[KeyboardButton("📱 Chia sẻ số điện thoại", request_contact=True)]]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)

# ============================================================
# MAINTENANCE
# ============================================================
async def is_maintenance():
    res = await db_query("SELECT value FROM settings WHERE key='maintenance'", fetchone=True)
    return bool(res and res[0] == "1")

# ============================================================
# HÀM TẠO CAPTCHA NGẪU NHIÊN (CHỮ, SỐ, HOẶC CẢ HAI)
# ============================================================
def generate_random_captcha():
    """Tạo chuỗi captcha ngẫu nhiên gồm chữ cái, số hoặc cả hai."""
    length = random.randint(4, 6)
    choice = random.randint(0, 2)
    if choice == 0:
        characters = string.digits
    elif choice == 1:
        characters = string.ascii_letters
    else:
        characters = string.ascii_letters + string.digits
    captcha_text = ''.join(random.choice(characters) for _ in range(length))
    return captcha_text

def generate_captcha_image_bytes(captcha_text: str) -> bytes:
    """Vẽ ảnh chứa chuỗi captcha ngẫu nhiên trên nền tối."""
    img_width, img_height = 400, 160
    image = Image.new("RGB", (img_width, img_height), color=(15, 20, 35))
    draw = ImageDraw.Draw(image)
    
    for _ in range(25):
        rx1 = random.randint(0, img_width)
        ry1 = random.randint(0, img_height)
        draw.point((rx1, ry1), fill=(random.randint(50, 150), random.randint(50, 150), random.randint(100, 200)))

    try:
        font = ImageFont.truetype("arial.ttf", 46)
    except IOError:
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 46)
        except IOError:
            font = ImageFont.load_default()

    for _ in range(5):
        x1 = random.randint(0, img_width)
        y1 = random.randint(0, img_height)
        x2 = random.randint(0, img_width)
        y2 = random.randint(0, img_height)
        draw.line([(x1, y1), (x2, y2)], fill=(random.randint(50, 150), random.randint(50, 150), random.randint(100, 200)), width=1)

    text_to_draw = captcha_text
    
    try:
        bbox = draw.textbbox((0, 0), text_to_draw, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
    except AttributeError:
        text_width, text_height = 200, 50

    x = (img_width - text_width) // 2
    y = (img_height - text_height) // 2 - 5

    draw.text((x, y), text_to_draw, fill=(255, 204, 51), font=font)

    bio = io.BytesIO()
    image.save(bio, format="PNG")
    bio.seek(0)
    return bio.getvalue()

# ============================================================
# KIỂM TRA THAM GIA KÊNH
# ============================================================
async def get_missing_channels(bot, user_id):
    async def check_one(channel):
        try:
            ch_target = channel
            if "t.me/" in channel:
                ch_target = "@" + channel.split("t.me/")[-1].strip("/")
            member = await bot.get_chat_member(chat_id=ch_target, user_id=user_id)
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
    CUSTOM_CHANNEL_URLS = {}
    buttons = []
    for ch in missing_channels:
        if "t.me/" in ch:
            channel_url = ch
        else:
            channel_url = CUSTOM_CHANNEL_URLS.get(ch, f"https://t.me/{ch.replace('@', '')}")
        buttons.append([InlineKeyboardButton(f"{E['POINT_RIGHT']} Tham gia: {ch}", url=channel_url)])
    for ch in OPTIONAL_DISPLAY_CHANNELS:
        if "t.me/" in ch:
            channel_url = ch
        else:
            channel_url = CUSTOM_CHANNEL_URLS.get(ch, f"https://t.me/{ch.replace('@', '')}")
        buttons.append([InlineKeyboardButton(f"{E['LOVE_FACE']} Tham gia: {ch} (Tham khảo)", url=channel_url)])
    buttons.append([InlineKeyboardButton("❇ XÁC NHẬN ĐÃ THAM GIA ❇️", callback_data="verify_join")])
    return buttons

# ============================================================
# ANTI SPAM
# ============================================================
async def handle_anti_spam(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    chat = update.effective_chat
    user = update.effective_user
    message = update.effective_message
    if not chat or chat.type != "private": return False
    if not user or user.id in ADMIN_IDS or not message: return False

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
    if not user: return None
    row = await db_query(
        "SELECT user_id, balance, bank_info, is_banned, is_withdraw_banned, referrer_id, phone_number, ip_address, skip_ip FROM users WHERE user_id=%s",
        (user.id,), fetchone=True,
    )
    if row:
        current_username = user.username or ""
        await db_query("UPDATE users SET username=%s WHERE user_id=%s", (current_username, user.id), commit=True)
    else:
        await db_query(
            "INSERT INTO users (user_id, username, balance, joined_at) VALUES (%s, %s, 0, %s) ON CONFLICT (user_id) DO NOTHING",
            (user.id, user.username or "", get_now_str()), commit=True,
        )
        row = await db_query(
            "SELECT user_id, balance, bank_info, is_banned, is_withdraw_banned, referrer_id, phone_number, ip_address, skip_ip FROM users WHERE user_id=%s",
            (user.id,), fetchone=True,
        )
    return row

# ============================================================
# XÁC MINH SĐT VÀ IP
# ============================================================
async def prompt_phone_verification(message_or_bot, user_id):
    msg = (
        f"{E['LOCK']} <b>XÁC MINH SỐ ĐIỆN THOẠI</b>\n\n"
        f"{E['WARN']} <b>Yêu cầu tài khoản hợp lệ:</b>\n"
        f"{E['CHECK']} Số điện thoại Việt Nam (+84)\n"
        f"{E['CHECK']} Tên hiển thị không quá 20 ký tự\n"
        f"{E['CHECK']} Có username (@)\n"
        f"{E['CHECK']} Có ảnh đại diện\n"
        f"{E['POINT_RIGHT']} <b>Nhấn nút bên dưới để chia sẻ số điện thoại:</b>"
    )
    if hasattr(message_or_bot, "reply_text"):
        await message_or_bot.reply_text(msg, reply_markup=get_contact_keyboard(), parse_mode="HTML")
    else:
        await message_or_bot.send_message(chat_id=user_id, text=msg, reply_markup=get_contact_keyboard(), parse_mode="HTML")

async def check_phone_verified(user_id) -> bool:
    row = await db_query("SELECT phone_number FROM users WHERE user_id=%s", (user_id,), fetchone=True)
    return bool(row and row[0])

async def check_ip_verified(user_id) -> bool:
    row = await db_query("SELECT ip_address, skip_ip FROM users WHERE user_id=%s", (user_id,), fetchone=True)
    if not row: return False
    ip_addr, skip_ip = row[0], row[1]
    if skip_ip == 1 or (ip_addr and len(ip_addr.strip()) > 0): return True
    return False

def get_miniapp_keyboard():
    keyboard = [[KeyboardButton("🌐 BẤM VÀO ĐÂY ĐỂ XÁC MINH IP", web_app=WebAppInfo(url=MINI_APP_URL))]]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)

async def prompt_ip_verification(message_or_bot, user_id):
    msg = (
        f"🌐 <b>XÁC MINH IP TÀI KHOẢN (MINI APP)</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"{E['POINT_RIGHT']} Vui lòng nhấn vào nút <b>🌐 BẤM VÀO ĐÂY ĐỂ XÁC MINH IP</b> bên dưới để xác minh IP kết nối của bạn!"
    )
    if hasattr(message_or_bot, "reply_text"):
        await message_or_bot.reply_text(msg, reply_markup=get_miniapp_keyboard(), parse_mode="HTML")
    else:
        await message_or_bot.send_message(chat_id=user_id, text=msg, reply_markup=get_miniapp_keyboard(), parse_mode="HTML")

# ============================================================
# GỬI CAPTCHA VÀ XỬ LÝ TIMEOUT
# ============================================================
async def send_captcha_challenge(update_or_msg, context: ContextTypes.DEFAULT_TYPE, user_id: int, message_text="", is_retry=False):
    if is_retry:
        if user_id in pending_captcha_users:
            pending_captcha_users[user_id]["retry_count"] += 1
            retry_count = pending_captcha_users[user_id]["retry_count"]
        else:
            retry_count = 1
    else:
        retry_count = 0

    captcha_text = await asyncio.to_thread(generate_random_captcha)
    img_bytes = await asyncio.to_thread(generate_captcha_image_bytes, captcha_text)
    
    pending_captcha_users[user_id] = {
        "answer": captcha_text,
        "attempts": 3,
        "expires_at": datetime.now() + timedelta(seconds=60),
        "message_id": None,
        "retry_count": retry_count,
        "chat_id": user_id
    }
    
    caption = (f"{message_text}\n\n" if message_text else "")
    caption += (
        f"🛡 <b>XÁC MINH CAPTCHA</b>\n\n"
        f"Nhập mã trong ảnh.\n"
        f"⏳ <b>60 giây</b>\n"
        f"✔️ <b>Còn 3 lần thử</b>"
    )
    
    sent_msg = None
    if hasattr(update_or_msg, "reply_photo"):
        sent_msg = await update_or_msg.reply_photo(
            photo=img_bytes,
            caption=caption,
            parse_mode="HTML",
            reply_markup=ReplyKeyboardRemove()
        )
    else:
        sent_msg = await context.bot.send_photo(
            chat_id=user_id,
            photo=img_bytes,
            caption=caption,
            parse_mode="HTML",
            reply_markup=ReplyKeyboardRemove()
        )
    
    if sent_msg:
        pending_captcha_users[user_id]["message_id"] = sent_msg.message_id
    
    asyncio.create_task(captcha_timeout_checker(context, user_id, sent_msg.message_id))

async def captcha_timeout_checker(context: ContextTypes.DEFAULT_TYPE, user_id: int, message_id: int):
    await asyncio.sleep(60)
    if user_id not in pending_captcha_users:
        return
    
    data = pending_captcha_users[user_id]
    if data["message_id"] != message_id:
        return
    
    if data["retry_count"] >= 3:
        await db_query("UPDATE users SET is_banned=1, is_withdraw_banned=1 WHERE user_id=%s", (user_id,), commit=True)
        pending_captcha_users.pop(user_id, None)
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=(
                    f"{E['DISLIKE']} <b>BẠN ĐÃ BỊ KHÓA TÀI KHOẢN VĨNH VIỄN!</b>\n"
                    f"━━━━━━━━━━━━━━━━━━\n"
                    f"{E['THERMOMETER']} Lý do: Không trả lời Captcha sau 3 lần gửi lại."
                ),
                parse_mode="HTML",
                reply_markup=ReplyKeyboardRemove()
            )
        except Exception:
            pass
        return
    
    try:
        await context.bot.send_message(
            chat_id=user_id,
            text=f"{E['REFRESH']} <b>Hết thời gian! Đang gửi lại Captcha mới...</b>\nLần thử {data['retry_count'] + 1}/3",
            parse_mode="HTML"
        )
        try:
            await context.bot.delete_message(chat_id=user_id, message_id=message_id)
        except Exception:
            pass
        await send_captcha_challenge(None, context, user_id, message_text="", is_retry=True)
    except Exception as e:
        logger.error(f"Lỗi gửi lại captcha cho {user_id}: {e}")

async def handle_captcha_input(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, user_input: str) -> bool:
    if user_id not in pending_captcha_users:
        return False
    
    data = pending_captcha_users[user_id]
    
    if datetime.now() > data["expires_at"]:
        pending_captcha_users.pop(user_id, None)
        await context.bot.send_message(
            chat_id=user_id,
            text=f"{E['HOURGLASS']} <b>Captcha đã hết hạn!</b> Vui lòng bấm /start để làm lại.",
            parse_mode="HTML"
        )
        return True
    
    if user_input.strip().lower() == data["answer"].lower():
        pending_captcha_users.pop(user_id, None)
        await context.bot.send_message(
            chat_id=user_id,
            text=f"{E['CHECK']} <b>Xác minh Captcha thành công!</b>",
            parse_mode="HTML"
        )
        user = update.effective_user
        await proceed_next_verification(update.message, context, user)
        return True
    else:
        data["attempts"] -= 1
        if data["attempts"] <= 0:
            await db_query("UPDATE users SET is_banned=1, is_withdraw_banned=1 WHERE user_id=%s", (user_id,), commit=True)
            pending_captcha_users.pop(user_id, None)
            await context.bot.send_message(
                chat_id=user_id,
                text=(
                    f"{E['DISLIKE']} <b>BẠN ĐÃ BỊ KHÓA TÀI KHOẢN VĨNH VIỄN!</b>\n"
                    f"━━━━━━━━━━━━━━━━━━\n"
                    f"{E['THERMOMETER']} Lý do: Nhập sai Captcha quá 3 lần."
                ),
                parse_mode="HTML",
                reply_markup=ReplyKeyboardRemove()
            )
        else:
            await context.bot.send_message(
                chat_id=user_id,
                text=f"{E['DISLIKE']} <b>Kết quả không chính xác!</b> Còn lại <b>{data['attempts']}</b> lần thử.",
                parse_mode="HTML"
            )
        return True

# ============================================================
# PROCEED NEXT VERIFICATION
# ============================================================
async def proceed_next_verification(update_or_msg, context: ContextTypes.DEFAULT_TYPE, user):
    user_id = user.id

    # 1. Xác minh SĐT
    if await get_verify_setting("verify_phone"):
        if not await check_phone_verified(user_id) and user_id not in ADMIN_IDS:
            await prompt_phone_verification(update_or_msg, user_id)
            return

    # 2. Xác minh IP
    if await get_verify_setting("verify_ip"):
        if not await check_ip_verified(user_id) and user_id not in ADMIN_IDS:
            await prompt_ip_verification(update_or_msg, user_id)
            return

    # 3. Xác minh CAPTCHA (MỚI - ĐƯA LÊN TRƯỚC CHECK KÊNH)
    if await get_verify_setting("verify_captcha"):
        if user_id in pending_captcha_users:
            return
        await send_captcha_challenge(update_or_msg, context, user_id)
        return

    # 4. Xác minh Kênh
    if await get_verify_setting("verify_channel"):
        if user_id not in ADMIN_IDS:
            missing_channels = await get_missing_channels(context.bot, user_id)
            if missing_channels:
                buttons = build_channel_buttons(missing_channels)
                missing_text = "\n".join([f"• <b>{ch}</b>" for ch in missing_channels])
                msg = (
                    f"{E['THERMOMETER']} <b>BẠN CHƯA THAM GIA ĐỦ CÁC KÊNH/NHÓM!</b>\n"
                    f"━━━━━━━━━━━━━━━━━━\n"
                    f"{E['DIZZY']} Bạn còn thiếu <b>{len(missing_channels)}</b> kênh/nhóm sau:\n\n"
                    f"{missing_text}\n\n"
                    f"{E['POINT_RIGHT']} Vui lòng tham gia đầy đủ rồi bấm nút <b>XÁC NHẬN ĐÃ THAM GIA</b> bên dưới!"
                )
                if hasattr(update_or_msg, "reply_text"):
                    await update_or_msg.reply_text(msg, reply_markup=InlineKeyboardMarkup(buttons), parse_mode="HTML")
                else:
                    await context.bot.send_message(chat_id=user_id, text=msg, reply_markup=InlineKeyboardMarkup(buttons), parse_mode="HTML")
                return

    # 5. Hoàn tất
    await finalize_user_registration(user, context)

# ============================================================
# START
# ============================================================
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await handle_anti_spam(update, context): return
    user = update.effective_user
    chat = update.effective_chat
    if not user or not chat: return
    if chat.type != "private":
        await db_query("INSERT INTO groups(chat_id) VALUES(%s) ON CONFLICT (chat_id) DO NOTHING", (chat.id,), commit=True)
        return
    if await is_maintenance() and user.id not in ADMIN_IDS:
        await update.message.reply_text(
            f"{E['DIZZY']} <b>HỆ THỐNG ĐANG BẢO TRÌ</b>\n"
            f"{E['BANDAGE']} Bot đang thực hiện nâng cấp định kỳ, vui lòng quay lại sau!",
            parse_mode="HTML"
        )
        return

    db_user = await db_query(
        "SELECT user_id, is_banned, referrer_id, phone_number, ip_address, skip_ip FROM users WHERE user_id=%s",
        (user.id,), fetchone=True,
    )

    if db_user and db_user[1] == 1:
        user_ip = db_user[4] if (len(db_user) > 4 and db_user[4]) else "Không xác định"
        await update.message.reply_text(
            f"{E['LIGHTNING']} <b>PHÁT HIỆN TRÙNG IP!</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"Địa chỉ IP <code>{user_ip}</code> đã được tài khoản khác sử dụng.\n"
            f"Tài khoản của bạn đã bị <b>khóa vĩnh viễn</b> do trùng IP và full thông tin!",
            parse_mode="HTML", reply_markup=ReplyKeyboardRemove()
        )
        return

    referrer_id = None
    if not db_user:
        if context.args:
            try:
                ref_id = int(context.args[0])
                if ref_id != user.id:
                    ref_exists = await db_query("SELECT user_id FROM users WHERE user_id=%s", (ref_id,), fetchone=True)
                    if ref_exists: referrer_id = ref_id
            except (ValueError, TypeError): pass

        await db_query(
            "INSERT INTO users (user_id, username, balance, referrer_id, joined_at) VALUES (%s, %s, 0, %s, %s) ON CONFLICT (user_id) DO NOTHING",
            (user.id, user.username or "", referrer_id, get_now_str()), commit=True,
        )
    else:
        await db_query("UPDATE users SET username=%s WHERE user_id=%s", (user.username or "", user.id), commit=True)

    await proceed_next_verification(update.message, context, user)

# ============================================================
# XỬ LÝ CALLBACK XÁC NHẬN THAM GIA KÊNH
# ============================================================
async def verify_join_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query: return
    user = query.from_user
    try: await query.answer()
    except Exception: pass
    if await is_maintenance() and user.id not in ADMIN_IDS:
        try: await query.answer("🔴 Hệ thống đang bảo trì.", show_alert=True)
        except Exception: pass
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
                reply_markup=InlineKeyboardMarkup(buttons), parse_mode="HTML",
            )
        except Exception: pass
        return

    if await get_verify_setting("verify_captcha"):
        try: await query.delete_message()
        except Exception: pass
        await send_captcha_challenge(query.message, context, user.id)
    else:
        try: await query.delete_message()
        except Exception: pass
        await finalize_user_registration(user, context)

# ============================================================
# CONTACT HANDLER
# ============================================================
async def contact_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    user = update.effective_user
    if not message or not message.contact or not user: return
    contact = message.contact
    if contact.user_id != user.id:
        await message.reply_text(
            f"{E['CROSS']} <b>Số điện thoại xác minh không thuộc về tài khoản Telegram này!</b>",
            parse_mode="HTML", reply_markup=get_contact_keyboard()
        )
        return
    phone = contact.phone_number or ""
    if not (phone.startswith("84") or phone.startswith("+84")):
        await message.reply_text(
            f"{E['CROSS']} <b>Yêu cầu bị từ chối!</b>\nHệ thống chỉ chấp nhận số điện thoại Việt Nam (+84).",
            parse_mode="HTML", reply_markup=get_contact_keyboard()
        )
        return
    full_name = f"{user.first_name or ''} {user.last_name or ''}".strip()
    if len(full_name) > 20:
        await message.reply_text(
            f"{E['CROSS']} <b>Tên hiển thị không hợp lệ!</b>\n"
            f"Tên tài khoản của bạn hiện dài <b>{len(full_name)}</b> ký tự (yêu cầu không quá 20 ký tự).\n"
            f"Vui lòng đổi lại tên hiển thị ngắn hơn và thử lại!",
            parse_mode="HTML", reply_markup=get_contact_keyboard()
        )
        return
    if not user.username:
        await message.reply_text(
            f"{E['CROSS']} <b>Chưa thiết lập Username!</b>\n"
            f"Tài khoản của bạn chưa cài đặt username (@username).\n"
            f"Vui lòng truy cập Cài đặt Telegram -> Tạo Username rồi nhấn xác minh lại!",
            parse_mode="HTML", reply_markup=get_contact_keyboard()
        )
        return
    try:
        user_photos = await context.bot.get_user_profile_photos(user.id, limit=1)
        if user_photos.total_count == 0:
            await message.reply_text(
                f"{E['CROSS']} <b>Thiếu ảnh đại diện!</b>\n"
                f"Tài khoản của bạn cần phải có ảnh đại diện (avatar).\n"
                f"Vui lòng cập nhật ảnh đại diện cho Telegram rồi thử lại!",
                parse_mode="HTML", reply_markup=get_contact_keyboard()
            )
            return
    except Exception as exc:
        logger.warning(f"Lỗi kiểm tra avatar user {user.id}: {exc}")

    await db_query("UPDATE users SET phone_number=%s WHERE user_id=%s", (phone, user.id), commit=True)
    await message.reply_text(
        f"{E['CHECK']} Xác minh số điện thoại thành công!\n\n"
        f"{E['HOURGLASS']} Đang kiểm tra điều kiện tiếp theo...",
        parse_mode="HTML", reply_markup=ReplyKeyboardRemove()
    )
    await proceed_next_verification(message, context, user)

# ============================================================
# WEB APP DATA HANDLER (XÁC MINH IP)
# ============================================================
async def web_app_data_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    user = update.effective_user
    if not message or not message.web_app_data or not user: return
    import json
    try:
        data = json.loads(message.web_app_data.data)
        user_ip = data.get("ip")
        if not user_ip:
            await message.reply_text(f"{E['CROSS']} Không lấy được thông tin IP. Vui lòng thử lại!", parse_mode="HTML")
            return

        current_user_db = await db_query("SELECT ip_address FROM users WHERE user_id=%s", (user.id,), fetchone=True)
        old_user_ip = current_user_db[0] if current_user_db else None

        if old_user_ip != user_ip:
            duplicate = await db_query(
                "SELECT user_id FROM users WHERE ip_address=%s AND user_id!=%s AND skip_ip=0",
                (user_ip, user.id), fetchone=True
            )
            if duplicate and user.id not in ADMIN_IDS:
                await db_query(
                    "UPDATE users SET is_banned=1, is_withdraw_banned=1, ip_address=%s WHERE user_id=%s",
                    (user_ip, user.id), commit=True
                )
                user_withdraw_state.pop(user.id, None)
                await message.reply_text(
                    f"{E['LIGHTNING']} <b>PHÁT HIỆN TRÙNG IP!</b>\n"
                    f"━━━━━━━━━━━━━━━━━━\n"
                    f"Địa chỉ IP <code>{user_ip}</code> đã được tài khoản khác sử dụng.\n"
                    f"Tài khoản của bạn đã bị <b>khóa vĩnh viễn</b> do trùng IP và full thông tin!",
                    parse_mode="HTML", reply_markup=ReplyKeyboardRemove()
                )
                return

        await db_query("UPDATE users SET ip_address=%s WHERE user_id=%s", (user_ip, user.id), commit=True)
        await message.reply_text(
            f"{E['CHECK']} Xác minh IP thành công!\n\n"
            f"{E['HOURGLASS']} Đang kiểm tra điều kiện tiếp theo...",
            parse_mode="HTML", reply_markup=ReplyKeyboardRemove()
        )
        await proceed_next_verification(message, context, user)
    except Exception as exc:
        logger.exception("Lỗi khi xử lý dữ liệu từ MiniApp: %s", exc)
        await message.reply_text(f"{E['CROSS']} Có lỗi xảy ra trong quá trình xác minh IP.", parse_mode="HTML")

# ============================================================
# FINALIZE REGISTRATION
# ============================================================
async def finalize_user_registration(user, context: ContextTypes.DEFAULT_TYPE):
    db_user = await db_query("SELECT referrer_id FROM users WHERE user_id=%s", (user.id,), fetchone=True)
    if db_user and db_user[0]:
        ref_id = db_user[0]
        try:
            def reward_referrer(cursor):
                detail_exact = f"Mời {user.id}"
                cursor.execute(
                    "SELECT id FROM transactions WHERE user_id=%s AND type='Thưởng Mời Bạn' AND details=%s",
                    (ref_id, detail_exact)
                )
                if cursor.fetchone(): return False
                cursor.execute(
                    "INSERT INTO transactions (user_id, type, amount, status, created_at, details) VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING",
                    (ref_id, "Thưởng Mời Bạn", REFERRAL_REWARD, "Thành công", get_now_str(), detail_exact),
                )
                if cursor.rowcount == 0: return False
                cursor.execute("UPDATE users SET balance = balance + %s WHERE user_id=%s", (REFERRAL_REWARD, ref_id))
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

    await context.bot.send_message(
        chat_id=user.id,
        text=(
            f"{E['LIKE']} <b>XÁC MINH THÀNH CÔNG!</b>\n"
            f"{E['ROCK']} <b>Chào mừng bạn đã gia nhập hệ thống Bot VIP!</b>"
        ),
        reply_markup=get_main_keyboard(), parse_mode="HTML",
    )

# ============================================================
# MENU HANDLER (CẬP NHẬT XỬ LÝ CAPTCHA)
# ============================================================
async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    user = update.effective_user
    if not message or not user: return
    if update.effective_chat.type != "private": return

    if user.id in pending_captcha_users:
        user_input = (message.text or "").strip()
        if await handle_captcha_input(update, context, user.id, user_input):
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
        ip_val = db_user[7] if (db_user and len(db_user) > 7 and db_user[7]) else "Không xác định"
        await message.reply_text(
            f"{E['LIGHTNING']} <b>PHÁT HIỆN TRÙNG IP!</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"Địa chỉ IP <code>{ip_val}</code> đã được tài khoản khác sử dụng.\n"
            f"Tài khoản của bạn đã bị <b>khóa vĩnh viễn</b> do trùng IP và full thông tin!",
            parse_mode="HTML", reply_markup=ReplyKeyboardRemove()
        )
        return

    if await get_verify_setting("verify_phone"):
        if not await check_phone_verified(user.id) and user.id not in ADMIN_IDS:
            await prompt_phone_verification(message, user.id)
            return

    if await get_verify_setting("verify_ip"):
        if not await check_ip_verified(user.id) and user.id not in ADMIN_IDS:
            await prompt_ip_verification(message, user.id)
            return

    if await get_verify_setting("verify_captcha"):
        if user.id not in pending_captcha_users:
            await send_captcha_challenge(message, context, user.id)
            return

    if await get_verify_setting("verify_channel"):
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
                    reply_markup=InlineKeyboardMarkup(buttons), parse_mode="HTML"
                )
                return

    text = (message.text or "").strip()
    if text in ["Tài Khoản", "👤 Tài Khoản"]:
        balance = db_user[1]
        phone_str = db_user[6] if len(db_user) > 6 and db_user[6] else "Chưa xác minh"
        ip_str = db_user[7] if len(db_user) > 7 and db_user[7] else "Chưa xác minh"
        invited_count = await get_valid_referrals_count(user.id)
        res_withdraw = await db_query(
            "SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE user_id=%s AND type LIKE 'Mua Code%%' AND status='Thành công'",
            (user.id,), fetchone=True,
        )
        total_withdraw = res_withdraw[0]
        msg = (
            f"{E['LOVE_FACE']} <b>THÔNG TIN TÀI KHOẢN VIP</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"{E['POINT_RIGHT']} <b>ID:</b> <code>{user.id}</code>\n"
            f"{E['PHONE']} <b>SĐT:</b> <code>{phone_str}</code>\n"
            f"🌐 <b>IP:</b> <code>{ip_str}</code>\n"
            f"{E['LIKE']} <b>Số dư:</b> <code>{balance:,}đ</code>\n"
            f"{E['ROCK']} <b>Đã mời thành công:</b> <code>{invited_count}</code> người\n"
            f"{E['HANDSHAKE']} <b>Đã dùng mua Code:</b> <code>{total_withdraw:,}đ</code>"
        )
        await message.reply_text(msg, parse_mode="HTML")
    elif text in ["Mời Bạn Bè", "🎁 Mời Bạn Bè"]:
        try:
            bot_info = await context.bot.get_me()
            bot_username = bot_info.username
        except Exception as exc:
            logger.exception("Không lấy được username bot: %s", exc)
            await message.reply_text(f"{E['CROSS']} Không lấy được thông tin bot. Vui lòng thử lại.", parse_mode="HTML")
            return
        if not bot_username:
            await message.reply_text(f"{E['CROSS']} Bot chưa có username, không thể tạo link mời.", parse_mode="HTML")
            return
        ref_link = f"https://t.me/{bot_username}?start={user.id}"
        msg = (
            f"{E['LOVE_FACE']} <b>CHƯƠNG TRÌNH MỜI BẠN BÈ</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"{E['POINT_RIGHT']} <b>Link giới thiệu của bạn:</b>\n"
            f"<code>{ref_link}</code>\n\n"
            f"{E['BANDAGE']} <b>Thể lệ nhận thưởng:</b>\n"
            f"• {E['LIKE']} Nhận ngay: <b>+{REFERRAL_REWARD:,}đ</b> / lượt mời thành công.\n"
            f"• {E['POINT_RIGHT']} Bạn bè phải hoàn tất các bước xác minh theo yêu cầu hệ thống.\n"
            f"• {E['ROCK']} Giá mua Code: <b>{CODE_PRICE:,}đ</b>"
        )
        await message.reply_text(msg, parse_mode="HTML")
    elif text in ["Top", "🔝 Top"]:
        top_users = await db_query(
            """
            SELECT t.user_id, u.username, COUNT(t.id) AS ref_count
            FROM transactions t
            JOIN users u ON u.user_id = t.user_id
            WHERE t.type = 'Thưởng Mời Bạn' AND t.status = 'Thành công' AND u.is_banned = 0
            GROUP BY t.user_id, u.username
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
            (user.id,), fetchall=True,
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
        if not await get_verify_setting("allow_withdraw") and user.id not in ADMIN_IDS:
            await message.reply_text(f"{E['DISLIKE']} <b>Tính năng rút tiền hiện đang TẮT bởi Quản trị viên!</b>", parse_mode="HTML")
            return
        if db_user[4] == 1:
            await message.reply_text(f"{E['DISLIKE']} <b>Tài khoản của bạn đã bị CẤM RÚT CODE!</b>", parse_mode="HTML")
            return
        buttons = [[InlineKeyboardButton(f"✅ XÁC NHẬN MUA CODE (Giá {CODE_PRICE:,}đ)", callback_data="buycode_confirm")]]
        await message.reply_text(
            f"{E['SHIELD']} <b>HỆ THỐNG RÚT CODE TỰ ĐỘNG</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"{E['LIKE']} <b>Số dư hiện tại:</b> <code>{db_user[1]:,}đ</code>\n\n"
            f"{E['LOVE_FACE']} Nhấn nút bên dưới để xác nhận mua code giá <b>{CODE_PRICE:,}đ</b>:",
            reply_markup=InlineKeyboardMarkup(buttons), parse_mode="HTML"
        )

# ============================================================
# CODE BUY CALLBACK
# ============================================================
async def code_buy_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query: return
    user = query.from_user
    data = query.data or ""
    try: await query.answer()
    except Exception: pass
    if not await get_verify_setting("allow_withdraw") and user.id not in ADMIN_IDS:
        await query.edit_message_text(f"{E['DISLIKE']} <b>Tính năng rút tiền đang bị khóa bởi Hệ thống!</b>", parse_mode="HTML")
        return
    db_user = await db_query(
        "SELECT balance, is_banned, is_withdraw_banned FROM users WHERE user_id=%s",
        (user.id,), fetchone=True,
    )
    if not db_user or db_user[1] == 1:
        await query.edit_message_text(f"{E['DISLIKE']} <b>Tài khoản của bạn đã bị khóa vĩnh viễn!</b>", parse_mode="HTML")
        return
    if db_user[2] == 1:
        await query.edit_message_text(f"{E['DISLIKE']} <b>Tài khoản của bạn đã bị cấm rút code!</b>", parse_mode="HTML")
        return
    balance = db_user[0]
    if data == "buycode_confirm":
        if balance < CODE_PRICE:
            await query.edit_message_text(
                f"{E['DISLIKE']} <b>SỐ DƯ KHÔNG ĐỦ!</b>\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"Bạn cần tối thiểu <b>{CODE_PRICE:,}đ</b> để mua code. Số dư hiện tại: <b>{balance:,}đ</b>",
                parse_mode="HTML"
            )
            return
        def process_buy_code(cursor):
            cursor.execute("SELECT id, code_val FROM code_stock WHERE is_used=0 ORDER BY id ASC LIMIT 1 FOR UPDATE")
            stock_item = cursor.fetchone()
            if not stock_item: return "OUT_OF_STOCK"
            code_stock_id, code_val = stock_item
            cursor.execute("UPDATE users SET balance = balance - %s WHERE user_id=%s AND balance >= %s", (CODE_PRICE, user.id, CODE_PRICE))
            if cursor.rowcount != 1: return "NOT_ENOUGH_BALANCE"
            cursor.execute("UPDATE code_stock SET is_used=1 WHERE id=%s", (code_stock_id,))
            details = f"Code: {code_val}"
            cursor.execute(
                "INSERT INTO transactions (user_id, type, amount, status, created_at, details) VALUES (%s, %s, %s, %s, %s, %s)",
                (user.id, f"Mua Code {CODE_PRICE}đ", CODE_PRICE, "Thành công", get_now_str(), details)
            )
            return code_val
        try:
            result = await db_transaction(process_buy_code)
        except Exception as exc:
            logger.exception("Lỗi khi mua code: %s", exc)
            await query.edit_message_text(f"{E['CROSS']} Đã xảy ra lỗi trong quá trình xử lý mua code.", parse_mode="HTML")
            return
        if result == "OUT_OF_STOCK":
            await query.edit_message_text(
                f"{E['THERMOMETER']} <b>RẤT TIẾC, KHO CODE HIỆN ĐÃ HẾT!</b>\nVui lòng liên hệ Admin hoặc quay lại sau.",
                parse_mode="HTML"
            )
        elif result == "NOT_ENOUGH_BALANCE":
            await query.edit_message_text(f"{E['DISLIKE']} <b>Số dư không đủ!</b>", parse_mode="HTML")
        else:
            await query.edit_message_text(
                f"{E['LOVE_FACE']} <b>MUA CODE THÀNH CÔNG!</b>\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"{E['LIKE']} <b>Số Tiền Mua:</b> {CODE_PRICE:,}đ\n"
                f"{E['POINT_RIGHT']} <b>Mã Code:</b> <code>{result}</code>\n\n"
                f"{E['THERMOMETER']} <b>Quy Định Rút Code</b>\n"
                f"{E['NUM_1']} Cược Đủ 1 Vòng Cược Số Tiền Code Là Đủ Điều Kiện Rút Tiền\n"
                f"{E['NUM_2']} Những Tài Khoản Nào Chưa Có Lịch Sử Nạp Trên 50K Muốn Rút Thì Yêu Cầu Nạp 50K Và Cược 50K ( X1 VC )\n"
                f"{E['NUM_3']} Tài Khoản Nào Đã Có Lịch Sử Nạp Trên 50K Rồi Thì Code Lên Rút Thoải Mãi\n"
                f"{E['NUM_4']} Không Được Rồn Code Và Không Được Nhập Quá 5 Code Trên 1Ngày ( Code Từ Bot Không Cấm Nhập Code Từ Sự Kiện Khác )",
                parse_mode="HTML"
            )

# ============================================================
# ADMIN PANEL COMMAND /menu & TOGGLE CALLBACKS
# ============================================================
def is_admin(update: Update):
    return bool(update.effective_user and update.effective_user.id in ADMIN_IDS)

async def build_admin_menu():
    st_phone = await get_verify_setting("verify_phone")
    st_ip = await get_verify_setting("verify_ip")
    st_channel = await get_verify_setting("verify_channel")
    st_captcha = await get_verify_setting("verify_captcha")
    st_withdraw = await get_verify_setting("allow_withdraw")

    btn_phone = InlineKeyboardButton(f"📱 Xác minh SĐT: {'🟢 BẬT' if st_phone else '🔴 TẮT'}", callback_data="toggle_verify_phone")
    btn_ip = InlineKeyboardButton(f"🌐 Xác minh IP Mini App: {'🟢 BẬT' if st_ip else '🔴 TẮT'}", callback_data="toggle_verify_ip")
    btn_channel = InlineKeyboardButton(f"📢 Check Kênh/Nhóm: {'🟢 BẬT' if st_channel else '🔴 TẮT'}", callback_data="toggle_verify_channel")
    btn_captcha = InlineKeyboardButton(f"🧩 Check CAPTCHA: {'🟢 BẬT' if st_captcha else '🔴 TẮT'}", callback_data="toggle_verify_captcha")
    btn_withdraw = InlineKeyboardButton(f"💳 Tính năng Rút Tiền: {'🟢 BẬT' if st_withdraw else '🔴 TẮT'}", callback_data="toggle_allow_withdraw")
    btn_verify_all = InlineKeyboardButton(f"🔄 Xác Minh Toàn Bộ Thành Viên", callback_data="admin_verify_all")

    buttons = [[btn_phone], [btn_ip], [btn_channel], [btn_captcha], [btn_withdraw], [btn_verify_all]]
    text = (
        f"{E['GEAR']} <b>BẢNG ĐIỀU KHIỂN QUẢN TRỊ VIÊN</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"<i>Nhấn vào từng nút bấm bên dưới để Bật/Tắt cấu hình xác minh & tính năng tương ứng:</i>"
    )
    return text, InlineKeyboardMarkup(buttons)

async def admin_menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update): return
    text, reply_markup = await build_admin_menu()
    await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="HTML")

async def admin_toggle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query or not is_admin(update): return
    data = query.data or ""
    if data == "admin_verify_all":
        await db_query("UPDATE users SET phone_number = NULL, ip_address = NULL, skip_ip = 0", commit=True)
        try: await query.answer("Đã đặt lại xác minh toàn bộ thành công!", show_alert=True)
        except Exception: pass
        await query.message.reply_text(
            f"{E['LIKE']} <b>ĐÃ ĐẶT LẠI TRẠNG THÁI XÁC MINH TOÀN BỘ THÀNH VIÊN!</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"Tất cả người dùng sẽ phải xác minh lại từ đầu khi tương tác với Bot.",
            parse_mode="HTML"
        )
        return
    key_map = {
        "toggle_verify_phone": "verify_phone",
        "toggle_verify_ip": "verify_ip",
        "toggle_verify_channel": "verify_channel",
        "toggle_verify_captcha": "verify_captcha",
        "toggle_allow_withdraw": "allow_withdraw",
    }
    if data in key_map:
        setting_key = key_map[data]
        curr_val = await get_verify_setting(setting_key)
        new_val = not curr_val
        await set_verify_setting(setting_key, new_val)
        status_text = "🟢 BẬT" if new_val else "🔴 TẮT"
        try: await query.answer(f"Đã chuyển trạng thái sang {status_text}")
        except Exception: pass
        text, reply_markup = await build_admin_menu()
        try: await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="HTML")
        except Exception: pass

# ============================================================
# ADMIN COMMANDS
# ============================================================
async def admin_commands(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update): return
    message = update.effective_message
    if not message: return
    cmd = (message.text or "").split()[0].split("@")[0].lower()
    args = context.args or []
    raw_text = message.text or ""
    try:
        if cmd == "/bo":
            if not args:
                await message.reply_text(f"{E['WARN']} <b>Cú pháp:</b> <code>/bo USER_ID</code>", parse_mode="HTML")
                return
            try: target_id = int(args[0])
            except ValueError:
                await message.reply_text(f"{E['CROSS']} USER_ID không hợp lệ.", parse_mode="HTML")
                return
            await db_query("UPDATE users SET skip_ip=1 WHERE user_id=%s", (target_id,), commit=True)
            await message.reply_text(f"{E['LIKE']} Đã thiết lập bỏ qua bước xác minh IP cho ID: <code>{target_id}</code>.", parse_mode="HTML")

        elif cmd == "/moip":
            if not args:
                await message.reply_text(f"{E['WARN']} <b>Cú pháp:</b> <code>/moip USER_ID</code>", parse_mode="HTML")
                return
            try: target_id = int(args[0])
            except ValueError:
                await message.reply_text(f"{E['CROSS']} USER_ID không hợp lệ.", parse_mode="HTML")
                return
            await db_query("UPDATE users SET is_banned=0, is_withdraw_banned=1 WHERE user_id=%s", (target_id,), commit=True)
            await message.reply_text(f"{E['LIKE']} Đã mở khóa trùng IP và bỏ qua bước kiểm tra IP cho ID: <code>{target_id}</code>.", parse_mode="HTML")

        elif cmd == "/xmtb":
            await db_query("UPDATE users SET phone_number = NULL, ip_address = NULL, skip_ip = 0", commit=True)
            await message.reply_text(
                f"{E['LIKE']} <b>ĐÃ ĐẶT LẠI TRẠNG THÁI XÁC MINH!</b>\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"Toàn bộ thành viên trong hệ thống sẽ phải thực hiện lại các bước kiểm tra (SĐT, IP, Kênh, Captcha) khi tương tác với Bot tiếp theo.",
                parse_mode="HTML"
            )

        elif cmd in ("/xoatb", "/xoacodeall"):
            def clear_all_codes(cursor):
                cursor.execute("SELECT code_val FROM code_stock")
                rows = cursor.fetchall()
                now = get_now_str()
                for (cval,) in rows:
                    cursor.execute("INSERT INTO code_deleted_log (code_val, deleted_at) VALUES (%s, %s)", (cval, now))
                cursor.execute("DELETE FROM code_stock")
                return len(rows)
            count_deleted = await db_transaction(clear_all_codes)
            await message.reply_text(
                f"{E['DISLIKE']} <b>ĐÃ XÓA TOÀN BỘ KHO CODE!</b>\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"• Đã xóa sạch: <b>{count_deleted:,}</b> mã code khỏi hệ thống (Đã lưu vào lịch sử xóa).",
                parse_mode="HTML"
            )

        elif cmd == "/lsxoa":
            deleted_logs = await db_query(
                "SELECT id, code_val, deleted_at FROM code_deleted_log ORDER BY id DESC LIMIT 50", fetchall=True
            )
            if not deleted_logs:
                await message.reply_text(f"{E['BANDAGE']} <b>Chưa có lịch sử mã code nào bị xóa!</b>", parse_mode="HTML")
                return
            msg = (
                f"{E['ROCK']} <b>LỊCH SỬ MÃ CODE ĐÃ XÓA</b>\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"{E['POINT_RIGHT']} <i>Hiển thị 50 mã code đã xóa gần nhất:</i>\n\n"
            )
            for cid, cval, cat in deleted_logs:
                msg += f"• ID: <code>{cid}</code> | Code: <code>{cval}</code> | Xóa lúc: <code>{cat}</code>\n"
            if len(msg) > 4000: msg = msg[:3950] + "\n\n<i>... (Danh sách quá dài đã được rút gọn)</i>"
            await message.reply_text(msg, parse_mode="HTML")

        elif cmd == "/dl":
            if not args:
                await message.reply_text(f"{E['WARN']} <b>Cú pháp:</b> <code>/dl USER_ID</code>", parse_mode="HTML")
                return
            try: target_id = int(args[0])
            except (ValueError, TypeError):
                await message.reply_text(f"{E['CROSS']} USER_ID không hợp lệ.", parse_mode="HTML")
                return
            u = await db_query("SELECT user_id, username, balance, referrer_id, is_banned, is_withdraw_banned, joined_at, phone_number, ip_address FROM users WHERE user_id=%s", (target_id,), fetchone=True)
            if not u:
                await message.reply_text(f"{E['CROSS']} Không tìm thấy ID <code>{target_id}</code> trong cơ sở dữ liệu.", parse_mode="HTML")
                return
            try:
                bot_info = await context.bot.get_me()
                bot_username = bot_info.username
            except Exception: bot_username = "Bot"
            ref_id = u[3]
            ref_info_text = f"{E['DOWN']} <b>Không có (Không bấm link của ai)</b>"
            if ref_id:
                ref_user = await db_query("SELECT user_id, username, phone_number, ip_address FROM users WHERE user_id=%s", (ref_id,), fetchone=True)
                if ref_user:
                    ref_uname = f"@{ref_user[1]}" if ref_user[1] else "Chưa đặt username"
                    ref_phone = ref_user[2] if ref_user[2] else "Chưa xác minh SĐT"
                    ref_ip = ref_user[3] if len(ref_user) > 3 and ref_user[3] else "Chưa xác minh IP"
                    ref_bot_link = f"https://t.me/{bot_username}?start={ref_id}"
                    ref_info_text = (
                        f"{E['CHECK2']} <b>NGƯỜI GIỚI THIỆU:</b>\n"
                        f"{E['UP']} <b>ID:</b> <code>{ref_user[0]}</code>\n"
                        f"{E['PHONE']} <b>SĐT:</b> <code>{ref_phone}</code>\n"
                        f"🌐 <b>IP:</b> <code>{ref_ip}</code>\n"
                        f"{E['CROWN']} <b>User:</b> {ref_uname}\n"
                        f"{E['CHART_UP']} <b>Link Bot Ref:</b> <code>{ref_bot_link}</code>"
                    )
                else:
                    ref_info_text = f"{E['WARN']} <b>ID Giới thiệu:</b> <code>{ref_id}</code> (Dữ liệu đã bị xoá)"
            u_uname = f"@{u[1]}" if u[1] else "Chưa đặt username"
            u_phone = u[7] if u[7] else "Chưa xác minh SĐT"
            u_ip = u[8] if len(u) > 8 and u[8] else "Chưa xác minh IP"
            u_bot_link = f"https://t.me/{bot_username}?start={u[0]}"
            invited_count = await get_valid_referrals_count(target_id)
            msg = (
                f"{E['CANDLE']} <b>KIỂM TRA THÔNG TIN ID:</b> <code>{target_id}</code>\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"{E['CHART_UP']} <b>THÔNG TIN ĐỐI TƯỢNG:</b>\n"
                f"{E['UP']} <b>ID:</b> <code>{u[0]}</code>\n"
                f"{E['PHONE']} <b>SĐT:</b> <code>{u_phone}</code>\n"
                f"🌐 <b>IP:</b> <code>{u_ip}</code>\n"
                f"{E['CROWN']} <b>User:</b> {u_uname}\n"
                f"{E['MONEY']} <b>Số dư:</b> <code>{u[2]:,}đ</code>\n"
                f"{E['CHART']} <b>Đã mời thành công:</b> <code>{invited_count}</code> người\n"
                f"{E['CHART_DOWN']} <b>Link Bot Ref:</b> <code>{u_bot_link}</code>\n"
                f"{E['PROHIBITED']} <b>Khóa TK:</b> <b>{'CÓ' if u[4] else 'KHÔNG'}</b>\n"
                f"{E['NO_ENTRY']} <b>Cấm rút:</b> <b>{'CÓ' if u[5] else 'KHÔNG'}</b>\n"
                f"{E['BANDAGE']} <b>Tham gia:</b> <code>{u[6]}</code>\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"{ref_info_text}"
            )
            await message.reply_text(msg, parse_mode="HTML", disable_web_page_preview=True)

        elif cmd == "/checkgd":
            if not args:
                await message.reply_text(f"{E['WARN']} <b>Cú pháp:</b> <code>/checkgd ID_USER</code>", parse_mode="HTML")
                return
            try: target_id = int(args[0])
            except ValueError:
                await message.reply_text(f"{E['CROSS']} ID không hợp lệ!", parse_mode="HTML")
                return
            txs = await db_query(
                "SELECT type, amount, status, created_at, details FROM transactions WHERE user_id=%s ORDER BY id DESC LIMIT 20",
                (target_id,), fetchall=True
            )
            if not txs:
                await message.reply_text(f"{E['BANDAGE']} Người dùng <code>{target_id}</code> chưa từng có giao dịch nào.", parse_mode="HTML")
                return
            msg = f"{E['CHART']} <b>LỊCH SỬ GIAO DỊCH CỦA ID:</b> <code>{target_id}</code>\n━━━━━━━━━━━━━━━━━━\n\n"
            for tx_type, amount, status, created_at, details in txs:
                icon = E['CHECK'] if status == "Thành công" else E['CROSS']
                msg += (
                    f"{icon} <b>Loại:</b> {tx_type}\n"
                    f"{E['MONEY']} <b>Số tiền:</b> <code>{amount:,}đ</code>\n"
                    f"{E['SHIELD']} <b>Chi tiết:</b> <code>{details or 'Không có'}</code>\n"
                    f"{E['LIGHTNING']} <b>Thời gian:</b> <code>{created_at}</code>\n"
                    "----------------------------------\n"
                )
            await message.reply_text(msg, parse_mode="HTML")

        elif cmd == "/lsfull":
            if not args:
                await message.reply_text(f"{E['WARN']} <b>Cú pháp:</b> <code>/lsfull ID_USER</code>", parse_mode="HTML")
                return
            try: target_id = int(args[0])
            except ValueError:
                await message.reply_text(f"{E['CROSS']} ID không hợp lệ!", parse_mode="HTML")
                return
            txs = await db_query(
                "SELECT id, type, amount, status, created_at, details FROM transactions WHERE user_id=%s ORDER BY id DESC",
                (target_id,), fetchall=True
            )
            if not txs:
                await message.reply_text(f"{E['BANDAGE']} Người dùng <code>{target_id}</code> không có lịch sử giao dịch nào.", parse_mode="HTML")
                return
            header = f"{E['ROCK']} <b>FULL LỊCH SỬ GIAO DỊCH ID:</b> <code>{target_id}</code> (Tổng: {len(txs)} giao dịch)\n━━━━━━━━━━━━━━━━━━\n\n"
            chunks = [header]
            current_chunk_idx = 0
            for tx_id, tx_type, amount, status, created_at, details in txs:
                icon = E['CHECK'] if status == "Thành công" else E['CROSS']
                line = (
                    f"{icon} <b>Mã GD:</b> #{tx_id} | <b>Loại:</b> {tx_type}\n"
                    f"{E['MONEY']} <b>Số tiền:</b> <code>{amount:,}đ</code> | <b>Trạng thái:</b> {status}\n"
                    f"{E['SHIELD']} <b>Chi tiết:</b> <code>{details or 'Không có'}</code>\n"
                    f"{E['LIGHTNING']} <b>Thời gian:</b> <code>{created_at}</code>\n"
                    "----------------------------------\n"
                )
                if len(chunks[current_chunk_idx]) + len(line) > 3900:
                    chunks.append(line)
                    current_chunk_idx += 1
                else:
                    chunks[current_chunk_idx] += line
            for chunk_content in chunks:
                await message.reply_text(chunk_content, parse_mode="HTML")
                await asyncio.sleep(0.3)

        elif cmd in ("/checkbb", "/bb"):
            if not args:
                await message.reply_text(f"{E['WARN']} <b>Cú pháp:</b> <code>/bb ID_USER</code> hoặc <code>/checkbb ID_USER</code>", parse_mode="HTML")
                return
            try: target_id = int(args[0])
            except ValueError:
                await message.reply_text(f"{E['CROSS']} ID không hợp lệ!", parse_mode="HTML")
                return
            invited = await db_query(
                "SELECT user_id, username, joined_at, phone_number, ip_address FROM users WHERE referrer_id=%s ORDER BY user_id DESC",
                (target_id,), fetchall=True
            )
            if not invited:
                await message.reply_text(f"{E['BANDAGE']} Người dùng <code>{target_id}</code> chưa mời được bạn bè nào.", parse_mode="HTML")
                return
            total_invited = len(invited)
            header = f"{E['TOP']} <b>DANH SÁCH BẠN BÈ MỜI BỞI ID:</b> <code>{target_id}</code>\n{E['LIKE']} <b>Tổng số bạn bè mời:</b> <code>{total_invited:,}</code> người\n━━━━━━━━━━━━━━━━━━\n\n"
            chunks = [header]
            current_chunk_idx = 0
            all_buttons = []
            row = []
            for u_id, username, joined_at, phone, ip_addr in invited:
                uname_str = f"@{username}" if username else "Không có @username"
                phone_str = phone if phone else "Chưa xác minh SĐT"
                ip_str = ip_addr if ip_addr else "Chưa xác minh IP"
                joined_str = joined_at if joined_at else "Không rõ"
                line = (
                    f"{E['CROWN']} <b>Full @name:</b> {uname_str}\n"
                    f"{E['PLUS']} <b>ID:</b> <code>{u_id}</code>\n"
                    f"{E['PHONE']} <b>SĐT:</b> <code>{phone_str}</code>\n"
                    f"🌐 <b>IP:</b> <code>{ip_str}</code>\n"
                    f"{E['LIGHTNING']} <b>Ngày tham gia:</b> <code>{joined_str}</code>\n"
                    "----------------------------------\n"
                )
                if len(chunks[current_chunk_idx]) + len(line) > 3800:
                    chunks.append(line)
                    current_chunk_idx += 1
                else:
                    chunks[current_chunk_idx] += line
                row.append(InlineKeyboardButton(f"🆔 {u_id}", url=f"tg://user?id={u_id}"))
                if len(row) == 2:
                    all_buttons.append(row)
                    row = []
            if row: all_buttons.append(row)
            for idx, chunk_content in enumerate(chunks):
                markup = InlineKeyboardMarkup(all_buttons) if (idx == len(chunks) - 1 and all_buttons) else None
                await message.reply_text(chunk_content, reply_markup=markup, parse_mode="HTML", disable_web_page_preview=True)
                await asyncio.sleep(0.3)

        elif cmd == "/addcode":
            lines = raw_text.split(maxsplit=1)
            if len(lines) < 2:
                await message.reply_text(
                    f"{E['THERMOMETER']} <b>Cú pháp:</b> <code>/addcode mã_code1 mã_code2 ...</code>\n"
                    f"Hoặc xuống dòng từng mã code để thêm số lượng lớn. Bot sẽ tự động phân tích và thêm vào kho.",
                    parse_mode="HTML"
                )
                return
            codes_raw = lines[1]
            codes = re.split(r"[\s\n]+", codes_raw.strip())
            codes = [c.strip() for c in codes if c.strip()]
            if not codes:
                await message.reply_text(f"{E['CROSS']} Không tìm thấy mã code hợp lệ.", parse_mode="HTML")
                return
            def add_codes_auto(cursor):
                now = get_now_str()
                count = 0
                for c in codes:
                    cursor.execute(
                        "INSERT INTO code_stock (type_code, code_val, created_at) VALUES (%s, %s, %s)",
                        (1, c, now)
                    )
                    count += 1
                return count
            added_count = await db_transaction(add_codes_auto)
            await message.reply_text(
                f"{E['LIKE']} <b>THÊM CODE VÀO KHO THÀNH CÔNG!</b>\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"• Đã tự động phân tích và thêm thành công: <b>{added_count:,}</b> mã code vào hệ thống.",
                parse_mode="HTML"
            )

        elif cmd == "/dscode":
            codes_list = await db_query(
                "SELECT id, type_code, code_val, created_at FROM code_stock WHERE is_used=0 ORDER BY id DESC LIMIT 50", fetchall=True
            )
            res_total = await db_query("SELECT COUNT(*) FROM code_stock WHERE is_used=0", fetchone=True)
            total_count = res_total[0] if res_total else 0
            if not codes_list:
                await message.reply_text(f"{E['BANDAGE']} <b>Kho code hiện đang trống!</b>", parse_mode="HTML")
                return
            msg = (
                f"{E['ROCK']} <b>DANH SÁCH TOÀN BỘ MÃ CODE TRONG KHO</b>\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"{E['LIKE']} Tổng số lượng chưa dùng: <b>{total_count:,}</b> code\n"
                f"{E['POINT_RIGHT']} <i>Hiển thị 50 mã code mới nhất:</i>\n\n"
            )
            for cid, tcode, cval, cat in codes_list:
                msg += f"• ID: <code>{cid}</code> | Code: <code>{cval}</code> | Thêm lúc: <code>{cat}</code>\n"
            if len(msg) > 4000: msg = msg[:3950] + "\n\n<i>... (Danh sách quá dài đã được rút gọn)</i>"
            await message.reply_text(msg, parse_mode="HTML")

        elif cmd == "/kho":
            res1 = await db_query("SELECT COUNT(*) FROM code_stock WHERE is_used=0", fetchone=True)
            cnt = res1[0] if res1 else 0
            await message.reply_text(
                f"{E['ROCK']} <b>THỐNG KÊ KHO CODE HIỆN TẠI</b>\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"• Tổng số code chưa sử dụng: <b>{cnt:,}</b> code",
                parse_mode="HTML"
            )

        elif cmd == "/rutcode":
            rows = await db_query(
                """
                SELECT t.user_id, u.username, t.type, t.details, t.created_at
                FROM transactions t
                LEFT JOIN users u ON t.user_id = u.user_id
                WHERE t.type LIKE 'Mua Code%' AND t.status = 'Thành công'
                ORDER BY t.id DESC LIMIT 30
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
                    f"{E['LIKE']} <b>Loại Giao Dịch:</b> <code>{code_type_str}</code>\n"
                    f"{E['SHIELD']} <b>Nội dung:</b> <code>{details or 'Không rõ'}</code>\n"
                    f"{E['BANDAGE']} <b>Thời gian:</b> <code>{created_at}</code>\n"
                    "----------------------------------\n"
                )
            await message.reply_text(msg, parse_mode="HTML")

        elif cmd == "/resetall":
            await db_query("TRUNCATE TABLE users, transactions, code_stock, code_deleted_log RESTART IDENTITY", commit=True)
            user_msg_tracker.clear()
            temp_bans.clear()
            user_withdraw_state.clear()
            pending_captcha_users.clear()
            await db_query(
                "INSERT INTO users (user_id, username, balance, joined_at) VALUES (%s, %s, 0, %s) ON CONFLICT (user_id) DO NOTHING",
                (message.from_user.id, message.from_user.username or "", get_now_str()), commit=True
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
                if u_name: btn_text += f" (@{u_name})"
                row.append(InlineKeyboardButton(btn_text, callback_data=f"userinfo_{u_id}"))
                if len(row) == 2:
                    buttons.append(row)
                    row = []
            if row: buttons.append(row)
            await message.reply_text(msg, reply_markup=InlineKeyboardMarkup(buttons) if buttons else None, parse_mode="HTML")

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
                except Exception: pass
                await asyncio.sleep(0.05)
            for (chat_id,) in groups:
                try:
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text=f"{E['ROCK']} <b>THÔNG BÁO HỆ THỐNG</b>\n━━━━━━━━━━━━━━━━━━\n\n{content}",
                        parse_mode="HTML",
                    )
                    count += 1
                except Exception: pass
                await asyncio.sleep(0.05)
            await message.reply_text(f"{E['LIKE']} Đã phát thông báo tới <b>{count}</b> người dùng/nhóm.", parse_mode="HTML")

        elif cmd == "/info":
            if len(args) < 1:
                await message.reply_text(f"{E['POINT_RIGHT']} <b>Cú pháp:</b> <code>/info USER_ID</code>", parse_mode="HTML")
                return
            try: target_id = int(args[0])
            except (ValueError, TypeError):
                await message.reply_text(f"{E['CROSS']} USER_ID không hợp lệ.", parse_mode="HTML")
                return
            u = await db_query("SELECT * FROM users WHERE user_id=%s", (target_id,), fetchone=True)
            if not u:
                await message.reply_text(f"{E['CROSS']} Không tìm thấy user này.", parse_mode="HTML")
                return
            invited_count = await get_valid_referrals_count(target_id)
            username = f"@{u[1]}" if u[1] else "Chưa đặt"
            referrer = u[4] if u[4] is not None else "Không có"
            phone_val = u[8] if len(u) > 8 and u[8] else "Chưa xác minh"
            ip_val = u[9] if len(u) > 9 and u[9] else "Chưa xác minh"
            msg = (
                f"{E['LOVE_FACE']} <b>THÔNG TIN CHI TIẾT USER</b>\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"{E['POINT_RIGHT']} ID: <code>{u[0]}</code>\n"
                f"{E['PHONE']} SĐT: <code>{phone_val}</code>\n"
                f"🌐 IP: <code>{ip_val}</code>\n"
                f"{E['ROCK']} Username: {username}\n"
                f"{E['LIKE']} Số dư: <code>{u[2]:,}đ</code>\n"
                f"{E['POINT_RIGHT']} Khách giới thiệu: <code>{referrer}</code>\n"
                f"{E['ROCK']} Đã mời thành công: <code>{invited_count}</code> người\n"
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
                await message.reply_text(f"{E['CROSS']} Số tiền phải lớn hơn 0.", parse_mode="HTML")
                return
            exists = await db_query("SELECT user_id FROM users WHERE user_id=%s", (target_id,), fetchone=True)
            if not exists:
                await message.reply_text(f"{E['CROSS']} User chưa tồn tại.", parse_mode="HTML")
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
                    if cursor.rowcount != 1: return False
                    cursor.execute(
                        "INSERT INTO transactions (user_id, type, amount, status, created_at, details) VALUES (%s, %s, %s, %s, %s, %s)",
                        (target_id, "Trừ Tiền (Admin)", amount, "Thành công", get_now_str(), "Trừ từ Admin"),
                    )
                    return True
                ok = await db_transaction(deduct)
                if not ok:
                    await message.reply_text(f"{E['CROSS']} Số dư user không đủ để trừ.", parse_mode="HTML")
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
        await message.reply_text(f"{E['CROSS']} Đã xảy ra lỗi khi xử lý lệnh.", parse_mode="HTML")

# ============================================================
# DISPATCHER & MAIN
# ============================================================
async def text_message_dispatcher(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_message: return
    if await handle_anti_spam(update, context): return
    await menu_handler(update, context)

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error("Exception khi xử lý update: %s", context.error, exc_info=context.error)

async def post_init(application: Application) -> None:
    await init_db()

def main():
    if not BOT_TOKEN: raise RuntimeError("Chưa cấu hình BOT_TOKEN.")
    if not DATABASE_URL: raise RuntimeError("Chưa cấu hình DATABASE_URL.")
    app = Application.builder().token(BOT_TOKEN).post_init(post_init).build()
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("menu", admin_menu_command))
    app.add_handler(CallbackQueryHandler(admin_toggle_callback, pattern=r"^(toggle_|admin_verify_all)"))
    app.add_handler(CallbackQueryHandler(verify_join_callback, pattern=r"^verify_join$"))
    app.add_handler(CallbackQueryHandler(code_buy_callback, pattern=r"^buycode_"))
    app.add_handler(MessageHandler(filters.CONTACT, contact_handler))
    app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, web_app_data_handler))
    admin_cmds = [
        "addcode", "dscode", "xoatb", "xoacodeall", "lsxoa", "xmtb", "kho", "rutcode", "resetall", "tong", "tb", "info", "ban", "moban",
        "cam", "mocam", "nap", "tru", "baotri", "checkgd", "checkbb", "bb", "lsfull", "dl", "bo", "moip"
    ]
    for command in admin_cmds:
        app.add_handler(CommandHandler(command, admin_commands))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_message_dispatcher))
    app.add_error_handler(error_handler)
    logger.info("🤖 Bot chạy thành công với Captcha chuỗi ký tự...")
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)

if __name__ == "__main__":
    main()
