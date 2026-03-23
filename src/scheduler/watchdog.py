"""
Watchdog: перевіряє що periodic jobs активні в RQ scheduler.
Якщо baf_polling зник — реєструє всі jobs знову.
Запускається через cron кожні 5 хвилин.
"""
import sys
from rq.job import Job
from src.core.queue import get_queue
from src.core.logger import get_logger

logger = get_logger(__name__)

BAF_FUNC = "src.scheduler.baf_polling.BafPollingWorker.run_polling"


def check_and_restore():
    q = get_queue("default")
    conn = q.connection
    reg = q.scheduled_job_registry

    registered = set()
    for jid in reg.get_job_ids():
        try:
            j = Job.fetch(jid, connection=conn)
            registered.add(j.func_name)
        except Exception:
            pass

    if BAF_FUNC not in registered:
        logger.warning("watchdog_jobs_missing", registered=list(registered))
        from src.scheduler.periodic import setup_periodic_jobs
        setup_periodic_jobs()
        logger.info("watchdog_jobs_restored")
    else:
        logger.info("watchdog_ok", registered=list(registered))


if __name__ == "__main__":
    check_and_restore()
