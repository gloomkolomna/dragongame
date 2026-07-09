"""Donor sync worker — periodically pulls donor status from the donut backend."""

import sys
import os
import time
import logging

_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _root)
sys.path.insert(0, os.path.join(_root, "api"))


def run_donor_sync(session_factory, interval_hours=24):
    logger = logging.getLogger("donor_sync")
    while True:
        db = session_factory()
        try:
            _sync_all(db, logger)
        except Exception as e:
            import traceback
            from bot.services.grow_service import log_to_db
            log_to_db(
                source="donor_sync",
                error_type=type(e).__name__,
                message=str(e),
                traceback_text=traceback.format_exc(),
                db=db,
            )
        finally:
            db.close()
        time.sleep(interval_hours * 3600)


def _sync_all(db, logger=None):
    import config
    from models import User, DonorCache

    if not config.DONUT_API_URL or not config.DONUT_API_KEY:
        return

    import httpx
    from datetime import datetime

    users = db.query(User).all()
    headers = {"X-API-Key": config.DONUT_API_KEY}

    for user in users:
        now = datetime.now().isoformat()
        try:
            resp = httpx.get(
                f"{config.DONUT_API_URL}/{user.vk_id}",
                headers=headers,
                timeout=10,
            )
            if resp.status_code != 200:
                continue
            data = resp.json()
        except Exception as e:
            if logger:
                logger.error(f"donor sync failed for {user.vk_id}: {e}")
            continue

        is_don = bool(data.get("is_don", False))
        don_since = data.get("don_since")

        donor = db.query(DonorCache).filter(DonorCache.vk_id == user.vk_id).first()
        if not donor:
            donor = DonorCache(
                vk_id=user.vk_id,
                is_don=is_don,
                don_since=don_since,
                updated_at=now,
                last_synced_at=now,
            )
            db.add(donor)
        else:
            donor.is_don = is_don
            donor.don_since = don_since
            donor.updated_at = now
            donor.last_synced_at = now
        db.commit()
