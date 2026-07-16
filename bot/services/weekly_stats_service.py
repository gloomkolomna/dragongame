import sys
import os
import time
import logging
from datetime import datetime, timedelta, timezone

_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _root)
sys.path.insert(0, os.path.join(_root, "api"))

import config

MSK = timezone(timedelta(hours=3))


def _monday_of_week(dt: datetime) -> datetime:
    return (dt - timedelta(days=dt.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)


def _get_weekly_stats(db):
    from models import UserDragon, Dragon
    from sqlalchemy import func

    now = datetime.now(MSK)
    week_start = now - timedelta(days=7)
    week_start_str = week_start.strftime("%Y-%m-%dT%H:%M:%S")
    now_str = now.strftime("%Y-%m-%dT%H:%M:%S")

    stats = (
        db.query(Dragon.rarity, func.count(UserDragon.id))
        .join(Dragon, UserDragon.dragon_id == Dragon.id)
        .filter(
            UserDragon.completed_at >= week_start_str,
            UserDragon.completed_at <= now_str,
            UserDragon.completed_at != "",
        )
        .group_by(Dragon.rarity)
        .all()
    )

    result = {1: 0, 2: 0, 3: 0}
    for rarity, count in stats:
        result[rarity] = count
    return result


def _get_top_users(db, limit=5):
    from models import UserDragon
    from sqlalchemy import func, desc

    now = datetime.now(MSK)
    week_start = now - timedelta(days=7)
    week_start_str = week_start.strftime("%Y-%m-%dT%H:%M:%S")
    now_str = now.strftime("%Y-%m-%dT%H:%M:%S")

    top = (
        db.query(UserDragon.user_id, func.count(UserDragon.id).label("cnt"))
        .filter(
            UserDragon.completed_at >= week_start_str,
            UserDragon.completed_at <= now_str,
            UserDragon.completed_at != "",
        )
        .group_by(UserDragon.user_id)
        .order_by(desc("cnt"))
        .limit(limit)
        .all()
    )
    return [(uid, cnt) for uid, cnt in top]


def _resolve_names(vk, user_ids):
    result = {}
    if not user_ids:
        return result
    try:
        users = vk.users.get(user_ids=",".join(str(uid) for uid in user_ids), fields="first_name,last_name")
        for u in users:
            uid = u.get("id", 0)
            name = f"{u.get('first_name', '')} {u.get('last_name', '')}".strip()
            result[uid] = name
    except Exception as e:
        logging.getLogger("weekly_stats").error(f"Failed to resolve user names: {e}")
    return result


def _plural(n, forms):
    n = abs(n)
    if n % 10 == 1 and n % 100 != 11:
        return forms[0]
    if 2 <= n % 10 <= 4 and not (12 <= n % 100 <= 14):
        return forms[1]
    return forms[2]


def _rarity_word(rarity, n):
    labels = {
        1: ("обычный", "обычных", "обычных"),
        2: ("редкий", "редких", "редких"),
        3: ("легендарный", "легендарных", "легендарных"),
    }
    return _plural(n, labels.get(rarity, ("дракон", "драконов", "драконов")))


def _build_post_text(stats, top_with_names):
    ordinary = stats.get(1, 0)
    rare = stats.get(2, 0)
    legendary = stats.get(3, 0)

    ow = _rarity_word(1, ordinary)
    rw = _rarity_word(2, rare)
    lw = _rarity_word(3, legendary)

    lines = [
        f"Благодаря усилиям вышивальщиц нашей группы, за прошедшую неделю было всего выращено {ordinary} {ow}, {rare} {rw} и {legendary} {lw} драконов!",
    ]

    if top_with_names:
        lines.append("")
        lines.append("Топ вышивальщиц недели:")
        for i, (vk_id, name, count) in enumerate(top_with_names, 1):
            dword = _plural(count, ("дракон", "дракона", "драконов"))
            lines.append(f"{i}. @id{vk_id} ({name}) — {count} {dword}")

    return "\n".join(lines)


def run_weekly_post_scheduler(session_factory, vk, check_interval=60):
    logger = logging.getLogger("weekly_stats")
    logger.info("Weekly stats scheduler started")

    while True:
        db = session_factory()
        try:
            _check_and_post(db, vk, logger)
        except Exception as e:
            logger.error(f"Weekly stats error: {e}")
            import traceback
            try:
                from bot.services.grow_service import log_to_db
                log_to_db(
                    source="weekly_stats",
                    error_type=type(e).__name__,
                    message=str(e),
                    traceback_text=traceback.format_exc(),
                    db=db,
                )
            except Exception:
                pass
        finally:
            db.close()
        time.sleep(check_interval)


def _check_and_post(db, vk, logger):
    from models import ServiceHeartbeat

    now = datetime.now(MSK)

    if now.weekday() != 0:
        return
    if now.hour != 10 or now.minute >= 5:
        return

    monday_str = _monday_of_week(now).strftime("%Y-%m-%d")

    sent = db.query(ServiceHeartbeat).filter(
        ServiceHeartbeat.service_name == "weekly_post",
        ServiceHeartbeat.last_seen >= monday_str,
    ).first()
    if sent:
        return

    stats = _get_weekly_stats(db)
    top = _get_top_users(db, 5)

    if not top and all(v == 0 for v in stats.values()):
        logger.info(f"No completions for week of {monday_str}, skipping post")
        return

    user_ids = [uid for uid, _ in top]
    names = _resolve_names(vk, user_ids)

    top_with_names = []
    for uid, cnt in top:
        name = names.get(uid, f"ID{uid}")
        top_with_names.append((uid, name, cnt))

    text = _build_post_text(stats, top_with_names)

    group_id = config.VK_GROUP_ID
    vk.wall.post(owner_id=-group_id, from_group=1, message=text)

    heartbeat = db.query(ServiceHeartbeat).filter(
        ServiceHeartbeat.service_name == "weekly_post"
    ).first()
    if heartbeat:
        heartbeat.last_seen = monday_str
    else:
        db.add(ServiceHeartbeat(service_name="weekly_post", last_seen=monday_str, status="sent"))
    db.commit()

    logger.info(f"Weekly stats posted for {monday_str}: ordinary={stats[1]} rare={stats[2]} legendary={stats[3]} top_users={len(top_with_names)}")
