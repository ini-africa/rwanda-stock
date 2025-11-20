import time
import scraper
import threading

def start_scheduler(interval_seconds=60*5):
    """
    Runs the scraper every `interval_seconds`.
    """
    print("Starting scheduler...")
    while True:
        scraper.scrape_rse_data()
        time.sleep(interval_seconds)
