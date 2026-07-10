"""Background timeout notifier — checks expired timeouts and sends notifications."""

import sys
import os
import json
import time
import random
import logging

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)
sys.path.insert(0, os.path.join(_root, "api"))


_IMAGES = os.path.join(_root, "images", "dragons")


def _upload_image(vk, filepath: str, peer_id=0, session_factory=None, user_id=None) -> str:
    last_error = None
    last_tb = ""
    for attempt in range(3):
        try:
            if not os.path.isfile(filepath):
                return ""
            upload_url = vk.photos.getMessagesUploadServer(peer_id=peer_id)["upload_url"]
            import requests
            with open(filepath, "rb") as f:
                resp = requests.post(upload_url, files={"photo": ("image.jpg", f, "image/jpeg")}, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            saved = vk.photos.saveMessagesPhoto(photo=data["photo"], server=data["server"], hash=data["hash"])[0]
            return f"photo{saved['owner_id']}_{saved['id']}"
        except Exception as e:
            last_error = e
            import traceback
            last_tb = traceback.format_exc()
            if attempt < 2:
                time.sleep(1)
    logger = logging.getLogger("timeout_scheduler")
    logger.error(f"Upload failed after 3 retries: {last_error}\n{last_tb}")
    if session_factory:
        from bot.services.grow_service import log_to_db
        db = None
        try:
            db = session_factory()
            log_to_db(
                source="scheduler",
                error_type="UPLOAD",
                message=f"Upload failed after 3 retries: {last_error}",
                traceback_text=last_tb,
                user_id=user_id,
                db=db,
            )
        finally:
            if db:
                db.close()
    return ""


def run_timeout_checker(session_factory, vk, interval=30):
    logger = logging.getLogger("timeout_scheduler")
    while True:
        try:
            db = session_factory()
            try:
                _check_expired(db, vk, logger, session_factory)
                _check_care_due(db, vk, logger, session_factory)
                _heartbeat(db)
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Checker error: {e}")
            try:
                from datetime import datetime
                import traceback
                db = session_factory()
                from models import ErrorLog
                err = ErrorLog(
                    source="scheduler",
                    error_type=type(e).__name__,
                    message=str(e),
                    traceback_text=traceback.format_exc(),
                    created_at=datetime.now().isoformat(),
                )
                db.add(err)
                db.commit()
                db.close()
            except Exception:
                pass
        time.sleep(interval)


def _heartbeat(db):
    from datetime import datetime
    from models import ServiceHeartbeat
    now = datetime.now().isoformat()
    hb = db.query(ServiceHeartbeat).filter(ServiceHeartbeat.service_name == "bot").first()
    if hb:
        hb.last_seen = now
        hb.status = "online"
    else:
        db.add(ServiceHeartbeat(service_name="bot", last_seen=now, status="online"))
    db.commit()


def _check_expired(db, vk, logger, session_factory=None):
    from datetime import datetime
    from models import UserDragon, User, Dragon, UserProgress
    from bot.services.grow_service import get_dragon_step, get_total_steps, rarity_name, rarity_stars
    from bot.handlers.grow import format_step

    now_str = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    expired = db.query(UserDragon).filter(
        UserDragon.next_step_available_at != None,
        UserDragon.next_step_available_at <= now_str,
        UserDragon.timeout_notified == False,
        UserDragon.completed_at == "",
    ).all()

    if not expired:
        return

    logger.info(f"Found {len(expired)} expired timeouts to notify")

    for ud in expired:
        db.refresh(ud)
        if not ud.next_step_available_at or ud.timeout_notified or ud.completed_at:
            continue

        user = db.query(User).filter(User.vk_id == ud.user_id).first()
        dragon = db.query(Dragon).filter(Dragon.id == ud.dragon_id).first()
        family_name = ""
        if dragon and dragon.family_id:
            from models import Family
            family = db.query(Family).filter(Family.id == dragon.family_id).first()
            if family:
                family_name = family.name
        if not user or not dragon:
            continue

        completed_count = db.query(UserProgress).filter(
            UserProgress.user_id == ud.user_id,
            UserProgress.dragon_id == ud.dragon_id,
            UserProgress.completed == True,
        ).count()
        next_step_num = completed_count + 1
        total = get_total_steps(db, ud.dragon_id)

        if completed_count >= total:
            from bot.services.grow_service import complete_dragon
            complete_dragon(db, ud.user_id, ud.dragon_id)
            ud.timeout_notified = True
            active = user.current_dragon_id == ud.dragon_id
            if active:
                user.state = "idle"
                user.current_dragon_id = None
                user.current_step = 0
            db.commit()

            msg = (
                f"🎉 Поздравляю! Ты вырастил дракона!\n\n"
                f"🐲 {dragon.name} 🐲\n"
                f"Редкость: {rarity_name(dragon.rarity)} {rarity_stars(dragon.rarity)}\n"
            )
            if family_name:
                msg += f"Коллекция: {family_name}\n"
            if dragon.description:
                msg += f"\n{dragon.description}\n"
            msg += "\nЗагляни в мини-приложение, чтобы увидеть его в своей коллекции!"

            keyboard_json = json.dumps({
                "one_time": True,
                "buttons": [
                    [{"action": {"type": "text", "label": "🥚 Добавить яйцо дракона", "payload": json.dumps({"cmd": "pin"}, ensure_ascii=False)}, "color": "primary"}],
                    [
                        {"action": {"type": "text", "label": "🔄🥚 Сменить яйцо дракона", "payload": json.dumps({"cmd": "garden"}, ensure_ascii=False)}, "color": "secondary"},
                        {"action": {"type": "text", "label": "❓ Помощь", "payload": json.dumps({"cmd": "help"}, ensure_ascii=False)}, "color": "secondary"},
                    ],
                    [{"action": {"type": "open_link", "label": "📖 Мой Бестиарий", "link": "https://vk.com/app54663330"}}],
                ],
            }, ensure_ascii=False)
            attachment = ""
            if dragon.dragon_path:
                filepath = os.path.join(_IMAGES, os.path.basename(dragon.dragon_path))
                if os.path.isfile(filepath):
                    attachment = _upload_image(vk, filepath, peer_id=ud.user_id, session_factory=session_factory, user_id=ud.user_id)
            _send(vk, ud.user_id, msg, keyboard_json, logger, attachment, session_factory=session_factory)
            continue

        ud.timeout_notified = True
        db.commit()

        is_active = (user.current_dragon_id == ud.dragon_id)
        same_dragon = is_active and user.current_step == next_step_num

        if same_dragon:
            step_def = get_dragon_step(db, ud.dragon_id, next_step_num)
            norm = step_def.crosses_norm if step_def else "?"
            msg = (
                f"⏰ Время пришло! Ты можешь продолжить выращивание «{dragon.egg_type or dragon.name or '?'}».\n\n"
                f"{format_step(step_def, next_step_num, total)}"
                f"\n\n🎯 Норма: {norm} крестиков\nВыбери режим:"
            )
            from bot.keyboard import step_buttons_keyboard
            keyboard_json = step_buttons_keyboard()
            attachment = ""
            if dragon and dragon.egg_path:
                filepath = os.path.join(_IMAGES, os.path.basename(dragon.egg_path))
                if os.path.isfile(filepath):
                    attachment = _upload_image(vk, filepath, peer_id=ud.user_id, session_factory=session_factory, user_id=ud.user_id)
            _send(vk, ud.user_id, msg, keyboard_json, logger, attachment, session_factory=session_factory)
        else:
            msg = (
                f"⏰ Выращивание яйца «{dragon.egg_type or dragon.name or '?'}» готово к следующему этапу!\n"
                f"Нажми кнопку ниже, чтобы переключиться."
            )
            keyboard_json = _switch_garden_keyboard(ud.dragon_id)
            attachment = ""
            if dragon and dragon.egg_path:
                filepath = os.path.join(_IMAGES, os.path.basename(dragon.egg_path))
                if os.path.isfile(filepath):
                    attachment = _upload_image(vk, filepath, peer_id=ud.user_id, session_factory=session_factory, user_id=ud.user_id)
            _send(vk, ud.user_id, msg, keyboard_json, logger, attachment, session_factory=session_factory)


def _switch_garden_keyboard(dragon_id: int):
    return json.dumps({
        "one_time": True,
        "buttons": [
            [{"action": {"type": "text", "label": "🥚 Перейти к выращиванию яйца", "payload": json.dumps({"cmd": "switch_to", "dragon_id": dragon_id}, ensure_ascii=False)}, "color": "primary"}],
            [{"action": {"type": "text", "label": "🔄🥚 Сменить яйцо дракона", "payload": json.dumps({"cmd": "garden"}, ensure_ascii=False)}, "color": "secondary"},
             {"action": {"type": "text", "label": "❓ Помощь", "payload": json.dumps({"cmd": "help"}, ensure_ascii=False)}, "color": "secondary"}],
            [{"action": {"type": "open_link", "label": "📖 Мой Бестиарий", "link": "https://vk.com/app54663330"}}],
        ],
    }, ensure_ascii=False)


def _check_care_due(db, vk, logger, session_factory=None):
    from datetime import datetime
    from models import EpicCareState, UserDragon
    now_str = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    due = db.query(EpicCareState).filter(
        EpicCareState.next_action_at != None,
        EpicCareState.next_action_at <= now_str,
        EpicCareState.care_notified == False,
    ).all()
    for care in due:
        ud = db.query(UserDragon).filter(UserDragon.id == care.user_dragon_id).first()
        care.care_notified = True
        db.commit()
        if not ud or ud.completed_at:
            continue
        kb = json.dumps({
            "one_time": False,
            "buttons": [
                [{"action": {"type": "text", "label": "🐲 Продолжить заботу", "payload": json.dumps({"cmd": "epic"}, ensure_ascii=False)}, "color": "primary"}],
                [{"action": {"type": "open_link", "label": "📖 Мой Бестиарий", "link": "https://vk.com/app54663330"}}],
            ],
        }, ensure_ascii=False)
        _send(vk, ud.user_id, "🐲 Твой эпический малыш заскучал — пора продолжить заботу!", kb, logger, session_factory=session_factory)


def _send(vk, user_id, message, keyboard, logger, attachment="", session_factory=None):
    try:
        kwargs = {
            "user_id": user_id,
            "message": message,
            "random_id": random.randint(1, 2**31 - 1),
            "keyboard": keyboard,
        }
        if attachment:
            kwargs["attachment"] = attachment
        vk.messages.send(**kwargs)
    except Exception as e:
        import traceback
        logger.error(f"Failed to send notification to {user_id}: {e}\n{traceback.format_exc()}")
        if session_factory:
            from bot.services.grow_service import log_to_db
            db = None
            try:
                db = session_factory()
                log_to_db(
                    source="scheduler",
                    error_type="NOTIFY",
                    message=f"Failed to send notification to {user_id}: {e}",
                    traceback_text=traceback.format_exc(),
                    user_id=user_id,
                    db=db,
                )
            finally:
                if db:
                    db.close()
