from apscheduler.schedulers.background import BackgroundScheduler
from .tasks import complete_past_events

def start():
    """
    Starts the background scheduler and adds the automated task.
    This is configured for frequent execution for testing purposes.
    """
    scheduler = BackgroundScheduler()
    # For testing, we run the job every 60 seconds.
    # For a real application, you would change this back to minutes=5 or more.
    scheduler.add_job(
        complete_past_events, 
        'interval', 
        minutes = 1, 
        id='complete_events_job', 
        replace_existing=True
    )
    scheduler.start()
    print("Scheduler started in TESTING mode (runs every 1 minute)...")

