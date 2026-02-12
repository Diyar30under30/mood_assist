from config import ADMIN_IDS
import logging

logger = logging.getLogger(__name__)


def is_admin(user_id):
    """Check if user is an admin"""
    return user_id in ADMIN_IDS


async def handle_stats(update, context, db):
    """Handle /stats command - show bot statistics"""
    user_id = update.effective_user.id

    if not is_admin(user_id):
        await update.message.reply_text("❌ Admin access required.")
        return

    stats = db.get_stats()

    stats_text = f"""
📊 **Mood Bot Statistics**

Total users: {stats['total_users']}
Check-ins this week: {stats['week_checkins']}

**Category Breakdown (this week):**
"""

    for category, count in sorted(stats['category_counts'].items()):
        stats_text += f"\n  {category}: {count}"

    await update.message.reply_text(stats_text, parse_mode="Markdown")
    logger.info(f"Stats viewed by admin {user_id}")


async def handle_broadcast(update, context, db):
    """Handle /broadcast command - send message to all users"""
    user_id = update.effective_user.id

    if not is_admin(user_id):
        await update.message.reply_text("❌ Admin access required.")
        return

    # Get message to broadcast
    if not context.args:
        await update.message.reply_text(
            "Usage: /broadcast <message>\n\nExample: /broadcast How are you doing?"
        )
        return

    broadcast_message = " ".join(context.args)
    users = db.get_all_active_users()

    if not users:
        await update.message.reply_text("No active users to broadcast to.")
        return

    success_count = 0
    fail_count = 0

    for user_id_target in users:
        try:
            await context.bot.send_message(
                chat_id=user_id_target,
                text=f"📢 Message from bot:\n\n{broadcast_message}",
            )
            success_count += 1
        except Exception as e:
            fail_count += 1
            logger.warning(f"Failed to send broadcast to {user_id_target}: {e}")

    await update.message.reply_text(
        f"✅ Broadcast sent!\n\nSuccess: {success_count}\nFailed: {fail_count}",
        parse_mode="Markdown",
    )
    logger.info(
        f"Broadcast by admin {user_id}: {success_count} success, {fail_count} failed"
    )


async def handle_reload(update, context, content_loader):
    """Handle /reload command - reload content without restart"""
    user_id = update.effective_user.id

    if not is_admin(user_id):
        await update.message.reply_text("❌ Admin access required.")
        return

    try:
        content_loader.reload()
        await update.message.reply_text("✅ Content reloaded successfully!")
        logger.info(f"Content reloaded by admin {user_id}")
    except Exception as e:
        await update.message.reply_text(f"❌ Error reloading content: {str(e)}")
        logger.error(f"Error reloading content: {e}")
