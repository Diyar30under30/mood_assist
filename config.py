import os
from dotenv import load_dotenv

load_dotenv()

# Bot Configuration
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_IDS = list(map(int, os.getenv("ADMIN_IDS", "").split(","))) if os.getenv("ADMIN_IDS") else []

# Timezone
TIMEZONE = os.getenv("TIMEZONE", "Asia/Qyzylorda")
CHECKIN_DAY = os.getenv("CHECKIN_DAY", "SUN").upper()
CHECKIN_HOUR = int(os.getenv("CHECKIN_HOUR", "18"))

# Logging
LOG_RAW_TEXT = os.getenv("LOG_RAW_TEXT", "false").lower() == "true"

# Database
DB_PATH = os.getenv("DB_PATH", "mood_bot.db")

# Content
CONTENT_DIR = "content"
MEDIA_DIR = "media"

# Rate Limit (seconds = 7 days)
CHECKIN_COOLDOWN_SECONDS = 7 * 24 * 60 * 60

# Mood Categories
MOOD_CATEGORIES = [
    "POSITIVE",
    "NEUTRAL_TIRED",
    "SAD_LOW",
    "ANGRY_FRUSTRATED",
    "ANXIOUS_STRESSED",
    "HEAVY_DEEP",
]

# Button Labels for Mood Selection
MOOD_BUTTONS = {
    "😄 Happy": "POSITIVE",
    "🙂 Okay": "NEUTRAL_TIRED",
    "😴 Tired": "NEUTRAL_TIRED",
    "😔 Sad": "SAD_LOW",
    "😡 Angry": "ANGRY_FRUSTRATED",
    "😰 Anxious": "ANXIOUS_STRESSED",
    "🕳️ Empty": "HEAVY_DEEP",
}
