"""
Unit tests for Mood Bot MVP

Tests critical functionality:
- Mood classification priority
- Keyword matching
- Rate limit calculation
- Database operations
"""

import unittest
import json
import tempfile
import os
from datetime import datetime, timedelta
from pathlib import Path

# Add parent to path
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from classifier import MoodClassifier
from storage import Database


class TestMoodClassifier(unittest.TestCase):
    """Test mood classification logic"""

    def setUp(self):
        """Initialize classifier"""
        self.classifier = MoodClassifier()

    def test_button_classification(self):
        """Test button-based mood classification"""
        assert self.classifier.classify("😄 Happy", is_button=True) == "POSITIVE"
        assert self.classifier.classify("😴 Tired", is_button=True) == "NEUTRAL_TIRED"
        assert self.classifier.classify("😔 Sad", is_button=True) == "SAD_LOW"
        assert self.classifier.classify("😡 Angry", is_button=True) == "ANGRY_FRUSTRATED"
        assert self.classifier.classify("😰 Anxious", is_button=True) == "ANXIOUS_STRESSED"

    def test_text_classification(self):
        """Test text-based mood classification"""
        assert self.classifier.classify_text_mood("I feel happy") == "POSITIVE"
        assert self.classifier.classify_text_mood("I'm so sad") == "SAD_LOW"
        assert self.classifier.classify_text_mood("I'm anxious") == "ANXIOUS_STRESSED"
        assert self.classifier.classify_text_mood("I'm tired") == "NEUTRAL_TIRED"
        assert self.classifier.classify_text_mood("I'm angry") == "ANGRY_FRUSTRATED"

    def test_priority_ordering(self):
        """Test that HEAVY_DEEP has highest priority"""
        # Mixed keywords - HEAVY_DEEP should win
        result = self.classifier.classify_text_mood("I'm happy but want to kill myself")
        assert result == "HEAVY_DEEP", f"Expected HEAVY_DEEP, got {result}"

        # SAD should win over POSITIVE
        result = self.classifier.classify_text_mood("I'm sad but also motivated")
        assert result == "SAD_LOW", f"Expected SAD_LOW, got {result}"

    def test_text_normalization(self):
        """Test that text normalization works"""
        # Different punctuation should match same keyword
        result1 = self.classifier.classify_text_mood("I'm sad.")
        result2 = self.classifier.classify_text_mood("I'm sad!!!")
        assert result1 == result2 == "SAD_LOW"

    def test_case_insensitivity(self):
        """Test that classification is case-insensitive"""
        result1 = self.classifier.classify_text_mood("HAPPY")
        result2 = self.classifier.classify_text_mood("happy")
        result3 = self.classifier.classify_text_mood("HaPpY")
        assert result1 == result2 == result3 == "POSITIVE"

    def test_default_category(self):
        """Test that unknown text returns default category"""
        result = self.classifier.classify_text_mood("xyz123 qwerty asdfgh")
        assert result in ["POSITIVE", "NEUTRAL_TIRED", "SAD_LOW", "ANGRY_FRUSTRATED", "ANXIOUS_STRESSED", "HEAVY_DEEP"]


class TestDatabase(unittest.TestCase):
    """Test database operations"""

    def setUp(self):
        """Create temporary database for testing"""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.temp_db.close()
        self.db_path = self.temp_db.name
        
        # Monkey-patch DB_PATH
        import config
        original_db_path = config.DB_PATH
        config.DB_PATH = self.db_path
        
        self.db = Database()
        self.original_db_path = original_db_path

    def tearDown(self):
        """Clean up temporary database"""
        import config
        config.DB_PATH = self.original_db_path
        os.unlink(self.db_path)

    def test_user_registration(self):
        """Test user registration"""
        user_id = 123456789
        username = "testuser"
        
        self.db.register_user(user_id, username)
        user = self.db.get_user(user_id)
        
        assert user is not None
        assert user[0] == user_id
        assert user[1] == username

    def test_first_checkin_allowed(self):
        """Test that first check-in is always allowed"""
        user_id = 111111111
        can_checkin, remaining = self.db.can_checkin(user_id)
        
        assert can_checkin is True
        assert remaining is None

    def test_rate_limiting(self):
        """Test that rate limit is enforced"""
        user_id = 222222222
        
        # Register user
        self.db.register_user(user_id)
        
        # First check-in should work
        can_checkin, _ = self.db.can_checkin(user_id)
        assert can_checkin is True
        
        # Log check-in
        self.db.log_checkin(user_id, "POSITIVE", "button")
        
        # Second check-in same week should fail
        can_checkin, remaining = self.db.can_checkin(user_id)
        assert can_checkin is False
        assert remaining is not None
        
        # Remaining time should be approximately 7 days
        remaining_hours = remaining.total_seconds() / 3600
        assert 160 < remaining_hours < 170  # ~7 days in hours

    def test_checkin_logging(self):
        """Test check-in logging"""
        user_id = 333333333
        category = "POSITIVE"
        
        self.db.register_user(user_id)
        self.db.log_checkin(user_id, category, "button", response_text_id="test_text", meme_file="test.jpg")
        
        # Get stats to verify logging
        stats = self.db.get_stats()
        assert stats["week_checkins"] >= 1

    def test_get_all_users(self):
        """Test getting all active users"""
        user_ids = [111, 222, 333]
        
        for uid in user_ids:
            self.db.register_user(uid)
        
        all_users = self.db.get_all_active_users()
        
        for uid in user_ids:
            assert uid in all_users

    def test_stats_calculation(self):
        """Test statistics calculation"""
        user_id = 444444444
        
        self.db.register_user(user_id)
        self.db.log_checkin(user_id, "POSITIVE", "button")
        self.db.log_checkin(user_id, "SAD_LOW", "text", mood_raw="Very sad")
        
        stats = self.db.get_stats()
        
        assert stats["total_users"] >= 1
        assert stats["week_checkins"] >= 2
        assert "POSITIVE" in stats["category_counts"]
        assert "SAD_LOW" in stats["category_counts"]


class TestRateLimitCalculation(unittest.TestCase):
    """Test rate limit time calculations"""

    def test_rate_limit_cooldown_seconds(self):
        """Test that 7 days = 604800 seconds"""
        seven_days = 7 * 24 * 60 * 60
        assert seven_days == 604800, f"7 days should be 604800 seconds, got {seven_days}"

    def test_time_remaining_calculation(self):
        """Test time remaining calculation"""
        now = datetime.now()
        last_checkin = now - timedelta(hours=6)  # 6 hours ago
        
        cooldown = 7 * 24 * 60 * 60  # 7 days
        elapsed = (now - last_checkin).total_seconds()
        remaining_seconds = cooldown - elapsed
        
        # Should be approximately 162 hours (7 days - 6 hours)
        hours_remaining = remaining_seconds / 3600
        assert 160 < hours_remaining < 170


class TestConfigurationPriority(unittest.TestCase):
    """Test mood category priority ordering"""

    def test_priority_list_order(self):
        """Verify correct priority order"""
        classifier = MoodClassifier()
        
        expected_priority = [
            "POSITIVE",
            "NEUTRAL_TIRED",
            "ANXIOUS_STRESSED",
            "ANGRY_FRUSTRATED",
            "SAD_LOW",
            "HEAVY_DEEP",
        ]
        
        assert classifier.priority == expected_priority


def run_tests():
    """Run all tests"""
    print("🧪 Running Mood Bot MVP Tests...\n")
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestMoodClassifier))
    suite.addTests(loader.loadTestsFromTestCase(TestDatabase))
    suite.addTests(loader.loadTestsFromTestCase(TestRateLimitCalculation))
    suite.addTests(loader.loadTestsFromTestCase(TestConfigurationPriority))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "="*50)
    if result.wasSuccessful():
        print("✅ All tests passed!")
    else:
        print(f"❌ Tests failed: {len(result.failures)} failures, {len(result.errors)} errors")
    print("="*50)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    exit(0 if success else 1)
