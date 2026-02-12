from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from config import TIMEZONE, CHECKIN_DAY, CHECKIN_HOUR
import logging

logger = logging.getLogger(__name__)


class WeeklyScheduler:
    def __init__(self):
        self.scheduler = AsyncIOScheduler(timezone=TIMEZONE)
        self.job_id = None

    def start(self, callback):
        """
        Start the scheduler with weekly check-in job.
        
        Args:
            callback: async function to call for weekly broadcast
        """
        # Map day names to cron format
        day_map = {
            "MON": "mon",
            "TUE": "tue",
            "WED": "wed",
            "THU": "thu",
            "FRI": "fri",
            "SAT": "sat",
            "SUN": "sun",
        }

        trigger_day = day_map.get(CHECKIN_DAY, "sun")

        # Schedule weekly job
        self.job_id = self.scheduler.add_job(
            callback,
            CronTrigger(
                day_of_week=trigger_day,
                hour=CHECKIN_HOUR,
                minute=0,
                timezone=TIMEZONE,
            ),
            id="weekly_checkin",
            name="Weekly mood check-in broadcast",
        )

        if not self.scheduler.running:
            self.scheduler.start()
            logger.info(
                f"Weekly scheduler started: {CHECKIN_DAY} at {CHECKIN_HOUR}:00 {TIMEZONE}"
            )

    def stop(self):
        """Stop the scheduler"""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("Scheduler stopped")

    def is_running(self):
        """Check if scheduler is running"""
        return self.scheduler.running

    def get_next_run_time(self):
        """Get next scheduled run time"""
        if self.job_id:
            job = self.scheduler.get_job(self.job_id)
            if job:
                return job.next_run_time
        return None
