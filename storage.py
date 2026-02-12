import sqlite3
from datetime import datetime, timedelta
from config import DB_PATH, LOG_RAW_TEXT


class Database:
    def __init__(self):
        self.db_path = DB_PATH
        self.init_db()

    def get_connection(self):
        """Get database connection"""
        return sqlite3.connect(self.db_path)

    def init_db(self):
        """Initialize database schema"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # Users table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_checkin_at TIMESTAMP,
                timezone TEXT DEFAULT 'Asia/Qyzylorda'
            )
        """
        )

        # Check-ins table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS checkins (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                input_type TEXT NOT NULL,
                mood_raw TEXT,
                category TEXT NOT NULL,
                response_text_id TEXT,
                meme_file TEXT,
                video_url TEXT,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        """
        )

        conn.commit()
        conn.close()

    def register_user(self, user_id, username=None):
        """Register or update user"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT OR IGNORE INTO users (user_id, username)
            VALUES (?, ?)
        """,
            (user_id, username),
        )

        conn.commit()
        conn.close()

    def get_user(self, user_id):
        """Get user info"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        user = cursor.fetchone()
        conn.close()

        return user

    def get_last_checkin(self, user_id):
        """Get user's last check-in timestamp"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT last_checkin_at FROM users WHERE user_id = ?", (user_id,)
        )
        result = cursor.fetchone()
        conn.close()

        if result and result[0]:
            return datetime.fromisoformat(result[0])
        return None

    def can_checkin(self, user_id, cooldown_seconds=604800):
        """Check if user can do a check-in (cooldown: default 7 days)"""
        last_checkin = self.get_last_checkin(user_id)

        if last_checkin is None:
            return True, None

        time_elapsed = datetime.now() - last_checkin
        if time_elapsed.total_seconds() >= cooldown_seconds:
            return True, None

        time_remaining = timedelta(seconds=cooldown_seconds) - time_elapsed
        return False, time_remaining

    def log_checkin(self, user_id, category, input_type, mood_raw=None, response_text_id=None, meme_file=None, video_url=None):
        """Log a completed check-in"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # Store raw text only if configured
        stored_raw = mood_raw if LOG_RAW_TEXT else None

        cursor.execute(
            """
            INSERT INTO checkins (user_id, input_type, mood_raw, category, response_text_id, meme_file, video_url)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
            (user_id, input_type, stored_raw, category, response_text_id, meme_file, video_url),
        )

        # Update user's last_checkin_at
        cursor.execute(
            "UPDATE users SET last_checkin_at = CURRENT_TIMESTAMP WHERE user_id = ?",
            (user_id,),
        )

        conn.commit()
        conn.close()

    def get_all_active_users(self):
        """Get all users who have started the bot"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT user_id FROM users")
        users = [row[0] for row in cursor.fetchall()]
        conn.close()

        return users

    def get_stats(self):
        """Get bot statistics"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # Total users
        cursor.execute("SELECT COUNT(*) FROM users")
        total_users = cursor.fetchone()[0]

        # Check-ins this week
        cursor.execute(
            """
            SELECT COUNT(*) FROM checkins
            WHERE created_at >= datetime('now', '-7 days')
        """
        )
        week_checkins = cursor.fetchone()[0]

        # Category breakdown this week
        cursor.execute(
            """
            SELECT category, COUNT(*) as count FROM checkins
            WHERE created_at >= datetime('now', '-7 days')
            GROUP BY category
        """
        )
        category_counts = dict(cursor.fetchall())

        conn.close()

        return {
            "total_users": total_users,
            "week_checkins": week_checkins,
            "category_counts": category_counts,
        }
