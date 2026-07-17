"""Donor sync worker — periodically pulls donor status from the donut backend."""

import sys
import os
import time
import logging

_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _root)
sys.path.insert(0, os.path.join(_root, "api"))


def run_donor_sync(session_factory, interval_hours=8):
    logger = logging.getLogger("donor_sync")
    while True:
        db = session_factory()
        try:
            _sync_all(db, logger)
            _sync_logs(db, logger)
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
    from models import User

    if not config.DONUT_API_URL or not config.DONUT_API_KEY:
        return

    users = db.query(User).all()

    for user in users:
        sync_user(db, user.vk_id, logger)


def sync_user(db, vk_id, logger=None):
    import config
    from models import DonorCache

    if not config.DONUT_API_URL or not config.DONUT_API_KEY:
        return

    import httpx
    from datetime import datetime

    headers = {"X-API-Key": config.DONUT_API_KEY}
    now = datetime.now().isoformat()
    try:
        resp = httpx.get(
            f"{config.DONUT_API_URL}/{vk_id}",
            headers=headers,
            timeout=10,
        )
        if resp.status_code != 200:
            return
        data = resp.json()
    except Exception as e:
        if logger:
            logger.error(f"donor sync failed for {vk_id}: {e}")
        return

    is_don = bool(data.get("is_don", False))
    don_since = data.get("don_since")

    donor = db.query(DonorCache).filter(DonorCache.vk_id == vk_id).first()
    if not donor:
        donor = DonorCache(
            vk_id=vk_id,
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


def _logs_url():
    import config

    if config.DONUT_LOGS_URL:
        return config.DONUT_LOGS_URL
    if config.DONUT_API_URL:
        return config.DONUT_API_URL.rsplit("/", 1)[0] + "/donor-logs"
    return ""


def _sync_logs(db, logger=None):
    import config
    from models import DonorEventLog

    url = _logs_url()
    if not url or not config.DONUT_API_KEY:
        return

    import httpx
    from datetime import datetime
    from sqlalchemy import func

    headers = {"X-API-Key": config.DONUT_API_KEY}
    limit = 1000

    while True:
        since = db.query(func.max(DonorEventLog.created_at)).scalar() or ""
        params = {"limit": limit}
        if since:
            params["since"] = since
        try:
            resp = httpx.get(url, headers=headers, params=params, timeout=10)
            if resp.status_code != 200:
                return
            events = resp.json()
        except Exception as e:
            if logger:
                logger.error(f"donor logs sync failed: {e}")
            return

        if not events:
            return

        now = datetime.now().isoformat()
        known_ids = {
            row[0]
            for row in db.query(DonorEventLog.source_id).filter(
                DonorEventLog.source_id.in_([e.get("id") for e in events if e.get("id") is not None])
            )
        }
        added = 0
        for event in events:
            source_id = event.get("id")
            if source_id is not None and source_id in known_ids:
                continue
            db.add(DonorEventLog(
                source_id=source_id,
                vk_id=event.get("vk_id"),
                event_type=event.get("event_type", ""),
                created_at=event.get("created_at", ""),
                synced_at=now,
            ))
            added += 1
        db.commit()

        if len(events) < limit or added == 0:
            return
