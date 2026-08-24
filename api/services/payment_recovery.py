"""Фоновый recovery-poller: отмена просроченных заказов (>1 ч) + додоставка
оплат, подтверждённых шлюзом, чей вебхук не дошёл (pending >10 мин)."""

import os
import sys
import threading
import time
import logging

logger = logging.getLogger("payment_recovery")

_started = False
_started_lock = threading.Lock()


def run_recovery_loop(session_factory, interval=60):
    while True:
        try:
            db = session_factory()
            try:
                from routes.payment import _cancel_expired_orders, recover_pending_gateway_orders
                cancelled = _cancel_expired_orders(db)
                for o in cancelled:
                    logger.info(f"Auto-cancelled expired order #{o.id} (vk_id={o.vk_id})")
                recover_pending_gateway_orders(db)
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Payment recovery error: {e}")
        time.sleep(interval)


def start_payment_recovery(session_factory, interval=60):
    global _started
    with _started_lock:
        if _started:
            return
        _started = True
    if os.getenv("TESTING"):
        logger.info("TESTING env set — payment recovery disabled")
        return
    thread = threading.Thread(
        target=run_recovery_loop,
        args=(session_factory, interval),
        daemon=True,
    )
    thread.start()
    print("Payment recovery poller started", file=sys.stderr)
