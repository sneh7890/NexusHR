"""
scheduler.py — background job that auto clocks out users who forgot.
Runs every day at 23:59 server time.
"""
import datetime
import logging
from apscheduler.schedulers.background import BackgroundScheduler

logger = logging.getLogger(__name__)

_scheduler = None


def auto_clockout_job(app):
    """
    Finds all active timesheets from TODAY that still have no clock_out
    and sets their clock_out to 23:59:00.
    Also closes any open breaks before clocking out.
    """
    with app.app_context():
        from app.database import get_db
        try:
            today = datetime.date.today().isoformat()
            clock_out_time = today + " 23:59:00"
            db = get_db()

            # Find all active timesheets with no clock_out for today
            active = db.execute(
                "SELECT t.id, u.full_name FROM timesheets t "
                "JOIN users u ON u.id = t.user_id "
                "WHERE t.date = ? AND t.status = 'active' "
                "AND t.clock_in IS NOT NULL AND t.clock_out IS NULL",
                (today,)
            ).fetchall()

            count = 0
            for ts in active:
                ts_id = ts[0]
                name  = ts[1]

                # Close any open break first
                db.execute(
                    "UPDATE breaks SET break_out = ? "
                    "WHERE timesheet_id = ? AND break_out IS NULL",
                    (clock_out_time, ts_id)
                )

                # Clock out at 23:59
                db.execute(
                    "UPDATE timesheets SET clock_out = ?, status = 'completed' "
                    "WHERE id = ?",
                    (clock_out_time, ts_id)
                )
                count += 1
                logger.info("Auto clocked out: %s (ts_id=%s)", name, ts_id)

            db.commit()

            if count > 0:
                logger.info("Auto clock-out job: %d user(s) clocked out at 23:59", count)
            else:
                logger.info("Auto clock-out job: no active sessions found for %s", today)

        except Exception as e:
            logger.error("Auto clock-out job failed: %s", str(e))


def start_scheduler(app):
    global _scheduler
    if _scheduler is not None:
        return  # Already running

    _scheduler = BackgroundScheduler(daemon=True)

    # Run every day at 23:59
    _scheduler.add_job(
        func=auto_clockout_job,
        args=[app],
        trigger='cron',
        hour=23,
        minute=59,
        second=0,
        id='auto_clockout',
        replace_existing=True
    )

    _scheduler.start()
    logger.info("Auto clock-out scheduler started — runs daily at 23:59")
    print("  Auto clock-out scheduler started (runs daily at 23:59)")
