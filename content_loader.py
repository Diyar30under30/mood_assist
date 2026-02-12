import json
import random
from pathlib import Path
from config import CONTENT_DIR, MEDIA_DIR


class ContentLoader:
    def __init__(self):
        self.responses = self._load_responses()

    def _load_responses(self):
        """Load response content from JSON file"""
        responses_file = Path(CONTENT_DIR) / "responses.json"
        try:
            with open(responses_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            return {}

    def reload(self):
        """Reload content from disk (for admin /reload command)"""
        self.responses = self._load_responses()

    def get_content_for_category(self, category):
        """
        Get content for a mood category.
        
        Returns dict with:
        - text: selected response text
        - meme: meme filename (if available)
        - video: YouTube URL (if available)
        - text_id: text identifier for logging
        """
        if category not in self.responses:
            return {
                "text": "Thanks for checking in. Take care of yourself.",
                "meme": None,
                "video": None,
                "text_id": "default",
            }

        category_data = self.responses[category]
        
        result = {
            "text": None,
            "meme": None,
            "video": None,
            "text_id": None,
        }

        # Get random text
        if "texts" in category_data and category_data["texts"]:
            result["text"] = random.choice(category_data["texts"])
            result["text_id"] = f"{category}_text"

        # Get random meme (for POSITIVE and NEUTRAL_TIRED only)
        if category in ["POSITIVE", "NEUTRAL_TIRED"]:
            if "memes" in category_data and category_data["memes"]:
                meme_filename = random.choice(category_data["memes"])
                meme_path = Path(MEDIA_DIR) / "memes" / meme_filename
                if meme_path.exists():
                    result["meme"] = str(meme_path)
                else:
                    result["meme"] = None  # File not found, will skip

        # Get random video (for SAD_LOW, ANXIOUS_STRESSED)
        if category in ["SAD_LOW", "ANXIOUS_STRESSED"]:
            if "videos" in category_data and category_data["videos"]:
                result["video"] = random.choice(category_data["videos"])

        return result

    def get_response_for_mood(self, category):
        """
        Get the complete response for a mood category.
        Determines what content to send based on category rules:
        - POSITIVE: meme + text
        - NEUTRAL_TIRED: text + optional calm image
        - SAD_LOW: supportive text + optional YouTube
        - ANGRY_FRUSTRATED: regulation text only
        - ANXIOUS_STRESSED: grounding text + optional YouTube
        - HEAVY_DEEP: gentle supportive text + encouragement
        """
        content = self.get_content_for_category(category)

        # Ensure there's always a text response
        if not content["text"]:
            content["text"] = self._get_default_text(category)

        return content

    def _get_default_text(self, category):
        """Get fallback text for each category"""
        defaults = {
            "POSITIVE": "That's wonderful! Keep riding this wave and enjoy the moment.",
            "NEUTRAL_TIRED": "It's okay to feel neutral. Rest when you need it.",
            "SAD_LOW": "I hear you. You're not alone in this. One step at a time.",
            "ANGRY_FRUSTRATED": "Your feelings are valid. Take a breath and give yourself space.",
            "ANXIOUS_STRESSED": "Breathe. You're safe right now. One moment at a time.",
            "HEAVY_DEEP": "I'm glad you're here. Please reach out to someone you trust. Your life matters.",
        }
        return defaults.get(category, "Thanks for checking in with me.")

    def check_media_exists(self, media_path):
        """Check if media file exists"""
        if not media_path:
            return False
        return Path(media_path).exists()
