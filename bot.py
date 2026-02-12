import logging
import os
from datetime import datetime, timedelta
import datetime as dt
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
    ConversationHandler,
)

from config import BOT_TOKEN, MOOD_BUTTONS, CHECKIN_COOLDOWN_SECONDS, CHECKIN_DAY, CHECKIN_HOUR
from storage import Database
from classifier import MoodClassifier
from content_loader import ContentLoader
from admin import handle_stats, handle_broadcast, handle_reload, is_admin

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# Conversation states
AWAITING_MOOD_TEXT = 1

# Global instances
db = Database()
classifier = MoodClassifier()
content_loader = ContentLoader()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command"""
    user = update.effective_user
    user_id = user.id

    # Register user
    db.register_user(user_id, user.username)

    welcome_text = """
👋 **Welcome to Mood Check-In Bot**

I'm here to check in with you weekly and help you reflect on how you're feeling.

🔒 **Privacy:** Your mood logs are stored only for bot functionality. We don't share your data.

What can you do?
• Use /checkin to check in anytime
• I'll send you a weekly prompt
• Select your mood or describe it in words
• Get personalized support based on how you're feeling

Ready? Let's go! 💙
    """

    keyboard = [[KeyboardButton("Check in now 🙂")]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)

    await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode="Markdown")
    logger.info(f"User {user_id} ({user.username}) started bot")


async def checkin_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle /checkin command or 'Check in now' button"""
    user_id = update.effective_user.id

    # Check rate limit
    can_checkin, time_remaining = db.can_checkin(user_id, CHECKIN_COOLDOWN_SECONDS)

    if not can_checkin:
        hours = time_remaining.total_seconds() / 3600
        days = int(hours // 24)
        hours = int(hours % 24)

        if days > 0:
            message = f"⏰ You already did your weekly check-in.\n\nNext check-in available in: {days}d {hours}h"
        else:
            message = f"⏰ You already did your weekly check-in.\n\nNext check-in available in: {int(hours)}h"

        if update.message:
            await update.message.reply_text(message)
        else:
            await update.callback_query.edit_message_text(message)
        return ConversationHandler.END

    # Show mood buttons
    prompt_text = "**How are you feeling right now?**"

    buttons = []
    for mood_label in MOOD_BUTTONS.keys():
        buttons.append([InlineKeyboardButton(mood_label, callback_data=f"mood_{mood_label}")])

    buttons.append([InlineKeyboardButton("✍️ Type my mood", callback_data="mood_text")])

    keyboard = InlineKeyboardMarkup(buttons)

    if update.message:
        await update.message.reply_text(prompt_text, reply_markup=keyboard, parse_mode="Markdown")
    else:
        await update.callback_query.edit_message_text(prompt_text, reply_markup=keyboard, parse_mode="Markdown")

    return AWAITING_MOOD_TEXT


async def mood_button_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle mood button selection"""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    callback_data = query.data

    # Check if user chose text input
    if callback_data == "mood_text":
        await query.edit_message_text(
            "📝 Describe how you're feeling in your own words. (Send one message)"
        )
        return AWAITING_MOOD_TEXT

    # Extract mood button label
    mood_label = callback_data.replace("mood_", "")

    # Classify mood
    category = classifier.classify(mood_label, is_button=True)

    # Get personalized response
    response = content_loader.get_response_for_mood(category)

    # Log check-in
    db.log_checkin(
        user_id,
        category,
        "button",
        mood_raw=None,
        response_text_id=response.get("text_id"),
        meme_file=response.get("meme"),
        video_url=response.get("video"),
    )

    # Send response based on category
    await send_mood_response(query, category, response)

    logger.info(f"User {user_id} checked in via button: {category}")
    return ConversationHandler.END


async def mood_text_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle free-text mood input"""
    user_id = update.effective_user.id
    mood_text = update.message.text

    if not mood_text or mood_text.strip() == "":
        await update.message.reply_text("Please describe your mood (e.g., 'I feel anxious today')")
        return AWAITING_MOOD_TEXT

    # Classify mood from text
    category = classifier.classify_text_mood(mood_text)

    # Get personalized response
    response = content_loader.get_response_for_mood(category)

    # Log check-in
    db.log_checkin(
        user_id,
        category,
        "text",
        mood_raw=mood_text,
        response_text_id=response.get("text_id"),
        meme_file=response.get("meme"),
        video_url=response.get("video"),
    )

    # Send response
    await send_mood_response(update.message, category, response)

    logger.info(f"User {user_id} checked in via text: {category}")
    return ConversationHandler.END


async def send_mood_response(message_or_query, category, response):
    """Send appropriate response based on mood category"""
    text = response.get("text", "Thanks for checking in.")
    meme = response.get("meme")
    video = response.get("video")

    # Determine if we're dealing with a Message or CallbackQuery
    is_query = hasattr(message_or_query, "edit_message_text")

    response_parts = []

    # Category-specific responses
    if category == "POSITIVE":
        # Meme + text
        if meme and os.path.exists(meme):
            if is_query:
                await message_or_query.edit_message_text(text)
            else:
                await message_or_query.reply_text(text)

            with open(meme, "rb") as photo:
                if is_query:
                    await message_or_query.edit_message_media(None)  # Clear message first
                await (message_or_query.message.reply_photo(photo) if is_query else message_or_query.reply_photo(photo))
        else:
            if is_query:
                await message_or_query.edit_message_text(f"😄 {text}")
            else:
                await message_or_query.reply_text(f"😄 {text}")

    elif category == "NEUTRAL_TIRED":
        # Text + optional image
        response_text = f"😴 {text}"
        if is_query:
            await message_or_query.edit_message_text(response_text)
        else:
            await message_or_query.reply_text(response_text)

        if meme and os.path.exists(meme):
            with open(meme, "rb") as photo:
                if is_query:
                    await message_or_query.message.reply_photo(photo)
                else:
                    await message_or_query.reply_photo(photo)

    elif category == "SAD_LOW":
        # Text + optional video
        response_text = f"💙 {text}"
        if video:
            response_text += f"\n\n💭 Watch this: {video}"

        if is_query:
            await message_or_query.edit_message_text(response_text)
        else:
            await message_or_query.reply_text(response_text)

    elif category == "ANGRY_FRUSTRATED":
        # Text only (no meme)
        response_text = f"🔥 {text}"
        if is_query:
            await message_or_query.edit_message_text(response_text)
        else:
            await message_or_query.reply_text(response_text)

    elif category == "ANXIOUS_STRESSED":
        # Grounding text + optional video
        response_text = f"🌬️ {text}"
        if video:
            response_text += f"\n\n🎵 Calm music: {video}"

        if is_query:
            await message_or_query.edit_message_text(response_text)
        else:
            await message_or_query.reply_text(response_text)

    elif category == "HEAVY_DEEP":
        # Gentle support + encouragement
        response_text = f"💙 {text}\n\n🤝 Please reach out to someone you trust. Crisis support is available 24/7."

        if is_query:
            await message_or_query.edit_message_text(response_text)
        else:
            await message_or_query.reply_text(response_text)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle unexpected messages"""
    text = update.message.text

    # Check if in AWAITING_MOOD_TEXT state
    if context.user_data.get("awaiting_mood") == AWAITING_MOOD_TEXT:
        return await mood_text_received(update, context)

    # Handle "Check in now" button from welcome
    if text == "Check in now 🙂":
        return await checkin_start(update, context)

    # Default response
    await update.message.reply_text("Type /checkin to start a mood check-in or /start for help.")
    return ConversationHandler.END


async def weekly_broadcast(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send weekly check-in prompt to all users"""
    users = db.get_all_active_users()

    success_count = 0
    fail_count = 0

    for user_id in users:
        try:
            buttons = []
            for mood_label in MOOD_BUTTONS.keys():
                buttons.append([InlineKeyboardButton(mood_label, callback_data=f"mood_{mood_label}")])

            buttons.append([InlineKeyboardButton("✍️ Type my mood", callback_data="mood_text")])

            keyboard = InlineKeyboardMarkup(buttons)

            await context.bot.send_message(
                chat_id=user_id,
                text="**🎯 Weekly Mood Check-In**\n\nHow are you feeling this week?\n\n(You can also use /checkin anytime)",
                reply_markup=keyboard,
                parse_mode="Markdown",
            )
            success_count += 1
        except Exception as e:
            fail_count += 1
            logger.warning(f"Failed to send weekly prompt to {user_id}: {e}")

    logger.info(f"Weekly broadcast completed: {success_count} sent, {fail_count} failed")


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel conversation"""
    await update.message.reply_text("❌ Check-in cancelled.")
    return ConversationHandler.END


def main() -> None:
    """Start the bot"""
    # Create application
    application = Application.builder().token(BOT_TOKEN).build()

    # Conversation handler for check-in flow
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("checkin", checkin_start),
            MessageHandler(filters.TEXT & filters.Regex("Check in now"), checkin_start),
        ],
        states={
            AWAITING_MOOD_TEXT: [
                CallbackQueryHandler(mood_button_selected, pattern="^mood_"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, mood_text_received),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler("stats", lambda u, c: handle_stats(u, c, db)))
    application.add_handler(CommandHandler("broadcast", lambda u, c: handle_broadcast(u, c, db)))
    application.add_handler(CommandHandler("reload", lambda u, c: handle_reload(u, c, content_loader)))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Start weekly scheduler using job_queue
    async def start_schedule(app):
        """Start weekly schedule on app startup"""
        # Parse day to number (0=Monday, 6=Sunday)
        day_map = {"MON": 0, "TUE": 1, "WED": 2, "THU": 3, "FRI": 4, "SAT": 5, "SUN": 6}
        day_of_week = day_map.get(CHECKIN_DAY, 6)
        
        app.job_queue.run_daily(
            weekly_broadcast,
            time=dt.time(hour=CHECKIN_HOUR, minute=0),
            days=(day_of_week,),
            job_kwargs={"id": "weekly_checkin", "replace_existing": True}
        )
        logger.info(f"Weekly scheduler started for {CHECKIN_DAY} at {CHECKIN_HOUR}:00")

    application.post_init = start_schedule

    # Run bot
    logger.info("Bot started. Running with long polling...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
