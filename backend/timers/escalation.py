"""Timer trigger: runs the escalation check automatically.

Schedule (NCRONTAB, six fields: second minute hour day month weekday):
    "0 0 */6 * * *"  =  at minute 0 of every 6th hour (00:00, 06:00, 12:00, 18:00 UTC)
To change it, edit the schedule text below and redeploy.
"""
import logging

import azure.functions as func

from repositories import open_repos
from services.escalation import run_escalation

bp = func.Blueprint()


@bp.timer_trigger(schedule="0 0 */6 * * *", arg_name="timer", run_on_startup=False, use_monitor=True)
def escalation_timer(timer: func.TimerRequest) -> None:
    if timer.past_due:
        logging.info("The escalation timer is running late (the app was probably asleep).")
    try:
        with open_repos() as (repo, _ref):
            result = run_escalation(repo)
    except Exception:
        logging.exception("Escalation check failed")
        raise  # lets Azure record the run as failed
    logging.info("Escalation check finished: checked=%s new=%s already=%s",
                 result["checked"], result["newEscalations"], result["alreadyEscalated"])
