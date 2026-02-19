# Telegram Mood Assist Bot

A weekly emotional wellness bot that checks in with users, classifies their mood, and provides personalized support.

## Features

✅ **Weekly Check-Ins** - Automated weekly mood prompts at configurable time  
✅ **Button + Free Text Input** - Quick mood selection or detailed description  
✅ **Smart Classification** - Rule-based mood categories with priority ordering  
✅ **Personalized Responses** - Tailored content based on mood:
- **Positive**: Meme + encouragement
- **Neutral/Tired**: Gentle activation text
- **Sad/Low**: Supportive text + optional YouTube
- **Angry**: Regulation text (no meme)
- **Anxious**: Grounding techniques + optional YouTube
- **Heavy/Deep**: Crisis support resources

✅ **Rate Limiting** - 1 check-in per user per week  
✅ **SQLite Logging** - Secure data persistence  
✅ **Admin Commands** - Stats, broadcast, content reload  

## Setup

### 1. Prerequisites
- Python 3.10+
- Telegram Bot Token (from [@BotFather](https://t.me/botfather))

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure Environment
```bash
cp .env.example .env
```

Edit `.env`:
```
BOT_TOKEN=your_telegram_bot_token
ADMIN_IDS=your_user_id_here
TIMEZONE=Asia/Qyzylorda
CHECKIN_DAY=SUN
CHECKIN_HOUR=18
LOG_RAW_TEXT=false
```

### 4. Add Media (Optional)
Place meme images in `media/memes/` (jpg/png):
- `meme_happy_001.jpg`
- `meme_happy_002.jpg`
- `meme_calm_001.jpg`

Update `content/responses.json` with your filenames.

### 5. Run the Bot
```bash
python bot.py
```

## Commands

| Command | Description |
|---------|-------------|
| `/start` | Welcome & register user |
| `/checkin` | Start mood check-in anytime |
| `/stats` | View bot statistics (admin only) |
| `/broadcast <msg>` | Send message to all users (admin only) |
| `/reload` | Reload content without restart (admin only) |

## Database Schema

**users**
```
- user_id (PK)
- username
- first_seen_at
- last_checkin_at
- timezone
```

**checkins**
```
- id (PK)
- user_id (FK)
- created_at
- input_type (button/text)
- mood_raw (only if LOG_RAW_TEXT=true)
- category
- response_text_id
- meme_file
- video_url
```

## Content Structure

### keywords.json
Mood keywords for free-text classification:
```json
{
  "POSITIVE": ["happy", "great", "excited", ...],
  "SAD_LOW": ["sad", "down", "depressed", ...],
  ...
}
```

### responses.json
Responses and media per mood category:
```json
{
  "POSITIVE": {
    "texts": ["Love this energy. Keep it simple...", ...],
    "memes": ["meme_happy_001.jpg", ...]
  },
  ...
}
```

## Classification Priority

When multiple keywords match, priority order (highest to lowest):
1. **HEAVY_DEEP** (safety signals)
2. **SAD_LOW**
3. **ANGRY_FRUSTRATED**
4. **ANXIOUS_STRESSED**
5. **NEUTRAL_TIRED**
6. **POSITIVE**

## Mood Categories & Responses

| Category | Response | Media |
|----------|----------|-------|
| POSITIVE | Encouraging text | ✅ Meme image |
| NEUTRAL_TIRED | Gentle activation | 🔄 Optional calm image |
| SAD_LOW | Supportive text | 🔄 Optional YouTube |
| ANGRY_FRUSTRATED | Regulation text | ❌ None |
| ANXIOUS_STRESSED | Grounding technique | 🔄 Optional YouTube |
| HEAVY_DEEP | Crisis support note | ❌ None |

## Privacy & Security

- Minimal data storage (user_id + timestamps + mood category)
- Raw mood text logging is **disabled by default** (set `LOG_RAW_TEXT=false`)
- Bot token stored in environment variables (never in code)
- All data stored locally in SQLite

## Deployment

### Local Development
```bash
python bot.py
```

### Production (Render/Fly.io)
1. Create app and add environment variables
2. Set buildpack: `Python`
3. Create `Procfile`:
```
web: python bot.py
```
4. Deploy and monitor logs

### Using Webhook (Advanced)
Replace long polling with webhook for better performance:
```python
# In bot.py, replace run_polling with:
await application.bot.set_webhook("https://your-domain.com/webhook")
app = web.AppRunner(web.Application())
# ... implement webhook handler
```

## Testing

### Unit Tests
```bash
python -m pytest tests/
```

### Manual Testing
1. `/start` - Register user
2. `/checkin` - Test mood buttons and free text
3. Test each mood category
4. Verify rate limiting (try check-in twice)
5. `/stats` - Check admin command

### Test Scenarios
- [ ] Happy mood → meme + text
- [ ] Tired mood → text only
- [ ] Sad mood → text + YouTube
- [ ] Mixed keywords ("tired but anxious") → highest priority wins
- [ ] Heavy/deep phrases → crisis support response
- [ ] Second check-in same week → rate limit message
- [ ] Admin /stats → see category breakdown
- [ ] Scheduler triggers weekly prompt

## Troubleshooting

**Bot doesn't respond to /start**
- Check BOT_TOKEN in .env
- Verify bot is running: `python bot.py`

**Mood not classified correctly**
- Review keywords in `content/keywords.json`
- Add missing keywords to category
- Check priority order (HEAVY_DEEP has highest priority)

**Memes not sending**
- Verify media path in `content/responses.json`
- Check file exists in `media/memes/`
- Fallback to text-only response if file missing

**Weekly scheduler not running**
- Check TIMEZONE is valid (pytz format)
- Verify CHECKIN_DAY and CHECKIN_HOUR settings
- Check bot is running continuously (not just testing)

**Rate limit not working**
- Verify CHECKIN_COOLDOWN_SECONDS = 604800 (7 days)
- Check SQLite table: `SELECT * FROM users WHERE user_id = YOUR_ID`

## File Structure

```
mood_assist/
├── bot.py                 # Main bot logic
├── config.py              # Configuration & env vars
├── storage.py             # SQLite database
├── classifier.py          # Mood classification
├── content_loader.py      # JSON content loading
├── scheduler.py           # Weekly scheduler
├── admin.py               # Admin commands
├── requirements.txt       # Dependencies
├── .env.example           # Environment template
├── content/
│   ├── keywords.json      # Mood keywords
│   └── responses.json     # Responses by category
├── media/
│   ├── memes/             # Happy mood images
│   └── calm/              # Calming images
└── mood_bot.db            # SQLite database (auto-created)
```

## Future Enhancements

- [ ] Multi-language support
- [ ] Personalized statistics dashboard
- [ ] Mood trends analysis
- [ ] Integration with crisis hotlines (regional)
- [ ] Custom user response times
- [ ] Mood export (CSV)
- [ ] A/B testing for response optimization

## Support & Security

**For security concerns:**
- Never share bot token or admin IDs in public repos
- Use environment variables for all secrets
- Regularly audit user data (privacy-first design)

**For questions:**
- Check logs: `python bot.py 2>&1 | tee bot.log`
- Review [python-telegram-bot docs](https://docs.python-telegram-bot.org/)

## License

MIT License - feel free to modify and deploy!

---

**Built with care for mental wellness. Use responsibly. 💙**
