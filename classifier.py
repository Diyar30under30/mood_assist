import json
import re
import unicodedata
from config import CONTENT_DIR, MOOD_BUTTONS
from pathlib import Path


class MoodClassifier:
    def __init__(self):
        self.keywords = self._load_keywords()
        # Priority order (higher index = higher priority)
        self.priority = [
            "POSITIVE",
            "NEUTRAL_TIRED",
            "ANXIOUS_STRESSED",
            "ANGRY_FRUSTRATED",
            "SAD_LOW",
            "HEAVY_DEEP",
        ]

    def _load_keywords(self):
        """Load keywords from JSON file"""
        keywords_file = Path(CONTENT_DIR) / "keywords.json"
        try:
            with open(keywords_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            return {}

    def _normalize_text(self, text):
        """Normalize text: lowercase, remove punctuation, strip whitespace"""
        # Lowercase
        text = text.lower()
        # Remove punctuation
        text = re.sub(r'[^\w\s]', ' ', text)
        # Remove extra whitespace
        text = ' '.join(text.split())
        return text

    def classify_button_mood(self, button_label):
        """Classify mood from button selection (direct mapping)"""
        return MOOD_BUTTONS.get(button_label, None)

    def classify_text_mood(self, user_text):
        """
        Classify mood from free text using keyword matching.
        Priority: HEAVY_DEEP > SAD_LOW > ANGRY_FRUSTRATED > ANXIOUS_STRESSED > NEUTRAL_TIRED > POSITIVE
        """
        normalized = self._normalize_text(user_text)
        words = normalized.split()

        # Check each category in reverse priority order (high priority last)
        matched_categories = set()

        for category, keywords in self.keywords.items():
            for keyword in keywords:
                keyword_normalized = self._normalize_text(keyword)
                # Check if keyword matches (full word or phrase)
                if keyword_normalized in normalized or any(
                    kw in words for kw in keyword_normalized.split()
                ):
                    matched_categories.add(category)
                    break

        # Return highest priority category
        if not matched_categories:
            return "NEUTRAL_TIRED"  # Default category

        # Sort by priority and return highest
        for category in reversed(self.priority):
            if category in matched_categories:
                return category

        return list(matched_categories)[0]

    def classify(self, mood_input, is_button=False):
        """
        Classify mood from either button or text input.
        
        Args:
            mood_input: Either button label or free text
            is_button: True if input is from button selection
            
        Returns:
            Category string
        """
        if is_button:
            category = self.classify_button_mood(mood_input)
            return category if category else "NEUTRAL_TIRED"
        else:
            return self.classify_text_mood(mood_input)
