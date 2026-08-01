"""Background scheduler — auto-cancels expired payment orders (older than 1 hour)."""

import os
import sys
import time
import threading
import logging

logger = logging.getLogger("payment_scheduler")

_started = False
_started_lock = threading.Lock()


def run_payment_expiry_loop(session_factory, interval=300):
    while True:
        try:
            db = session_factory()
            try:
                from routes.payment import _cancel_expired_orders
                cancelled = _cancel_expired_orders(db)
                if cancelled:
                    for o in cancelled:
                        logger.info(f"Auto-cancelled expired order #{o.id} (vk_id={o.vk_id})")
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Payment scheduler error: {e}")
        time.sleep(interval)


def start_payment_scheduler(session_factory, interval=300):
    global _started
    with _started_lock:
        if _started:
            return
        _started = True
    if os.getenv("TESTING"):
        logger.info("TESTING env set — payment scheduler disabled")
        return
    thread = threading.Thread(
        target=run_payment_expiry_loop,
        args=(session_factory, interval),
        daemon=True,
    )
    thread.start()
    print("Payment expiry scheduler started", file=sys.stderr)
