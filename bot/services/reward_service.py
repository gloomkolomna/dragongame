import sys
import os
import json
import time
import random
import logging

_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _root)
sys.path.insert(0, os.path.join(_root, "api"))

_IMAGES = os.path.join(_root, "images", "dragons")


def _upload_image(vk, filepath: str) -> str:
    last_error = None
    for attempt in range(3):
        try:
            if not os.path.isfile(filepath):
                return ""
            upload_url = vk.photos.getMessagesUploadServer(peer_id=0)["upload_url"]
            import requests
            with open(filepath, "rb") as f:
                resp = requests.post(upload_url, files={"photo": ("image.jpg", f, "image/jpeg")}, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            saved = vk.photos.saveMessagesPhoto(photo=data["photo"], server=data["server"], hash=data["hash"])[0]
            return f"photo{saved['owner_id']}_{saved['id']}"
        except Exception as e:
            last_error = e
            if attempt < 2:
                time.sleep(1)
    logger = logging.getLogger("reward_scheduler")
    logger.error(f"Reward upload failed after 3 retries: {last_error}")
    return ""


def run_reward_scheduler(session_factory, vk, interval_hours=24):
    logger = logging.getLogger("reward_scheduler")
    while True:
        db = session_factory()
        try:
            _process_rewards(db, vk, logger)
        except Exception as e:
            logger.error(f"Reward scheduler error: {e}")
            import traceback
            from bot.services.grow_service import log_to_db
            log_to_db(
                source="reward_scheduler",
                error_type=type(e).__name__,
                message=str(e),
                traceback_text=traceback.format_exc(),
                db=db,
            )
        finally:
            db.close()
        time.sleep(interval_hours * 3600)


def _process_rewards(db, vk, logger):
    from datetime import datetime, timedelta
    from models import RewardConfig, User, UserRewardPin, UserDragon, Dragon, DonorCache, DragonReservation
    from services.payment_service import is_donor

    configs = db.query(RewardConfig).filter(RewardConfig.is_active == True).all()
    if not configs:
        return

    now = datetime.now()
    all_dragons = db.query(Dragon).filter(Dragon.is_active == True, Dragon.is_epic == False, Dragon.pin_code.isnot(None), Dragon.pin_code != "").all()

    for cfg in configs:
        if cfg.eggs_per_period <= 0:
            continue

        rarity_ids = None
        if cfg.rarity_filter:
            try:
                rarity_ids = [int(r.strip()) for r in cfg.rarity_filter.split(",") if r.strip().isdigit()]
            except (ValueError, TypeError):
                pass

        eligible_dragons = all_dragons
        if rarity_ids:
            eligible_dragons = [d for d in all_dragons if d.rarity in rarity_ids]
        if not eligible_dragons:
            continue

        all_users = db.query(User).all()

        for user in all_users:
            if cfg.user_type == "donor":
                if not is_donor(user.vk_id, db):
                    continue
                donor_row = db.query(DonorCache).filter(DonorCache.vk_id == user.vk_id).first()
                if donor_row and donor_row.don_since:
                    try:
                        don_since_dt = datetime.fromisoformat(donor_row.don_since)
                        if now - don_since_dt < timedelta(days=cfg.period_days):
                            continue
                    except (ValueError, TypeError):
                        pass

            period_start = now - timedelta(days=cfg.period_days)
            period_start_str = period_start.strftime("%Y-%m-%dT%H:%M:%S")

            pins_this_period = db.query(UserRewardPin).filter(
                UserRewardPin.user_id == user.vk_id,
                UserRewardPin.issued_at >= period_start_str,
                UserRewardPin.config_id == cfg.id,
            ).count()

            if pins_this_period >= cfg.eggs_per_period:
                continue

            remaining = cfg.eggs_per_period - pins_this_period

            user_dragon_ids = set(
                row[0] for row in db.query(UserDragon.dragon_id).filter(
                    UserDragon.user_id == user.vk_id,
                ).all()
            )

            already_received = set(
                row[0] for row in db.query(UserRewardPin.dragon_id).filter(
                    UserRewardPin.user_id == user.vk_id,
                    UserRewardPin.dragon_id.isnot(None),
                ).all()
            )

            excluded = user_dragon_ids | already_received

            reserved_for_user = {
                r[0] for r in db.query(DragonReservation.dragon_id).filter(
                    DragonReservation.is_activated == False,
                    ((DragonReservation.vk_user_id == user.vk_id) | (DragonReservation.vk_user_id == None)),
                ).all()
            }
            excluded = excluded | reserved_for_user

            available = [d for d in eligible_dragons if d.id not in excluded]
            if not available:
                continue

            to_issue = min(remaining, len(available))
            chosen = random.sample(available, to_issue)
            now_str = now.strftime("%Y-%m-%dT%H:%M:%S")

            for dragon in chosen:
                pin_record = UserRewardPin(
                    user_id=user.vk_id,
                    dragon_id=dragon.id,
                    pin_code=dragon.pin_code or "",
                    config_id=cfg.id,
                    issued_at=now_str,
                    activated=False,
                    notified=False,
                )
                db.add(pin_record)

                existing_reservation = db.query(DragonReservation).filter(
                    DragonReservation.dragon_id == dragon.id,
                    DragonReservation.is_activated == False,
                ).first()
                if not existing_reservation:
                    reservation = DragonReservation(
                        vk_url=f"https://vk.ru/id{user.vk_id}",
                        vk_user_id=user.vk_id,
                        dragon_id=dragon.id,
                        is_activated=False,
                        notes=f"Бесплатное яйцо (конфигурация #{cfg.id})",
                        created_at=now_str,
                        updated_at=now_str,
                    )
                    db.add(reservation)
                    try:
                        import config
                        if config.VK_GROUP_TOKEN:
                            import vk_api
                            vk_api_obj = vk_api.VkApi(token=config.VK_GROUP_TOKEN, api_version="5.199").get_api()
                            users = vk_api_obj.users.get(user_ids=str(user.vk_id), fields="first_name,last_name")
                            if users:
                                u = users[0]
                                reservation.vk_name = f"{u.get('first_name', '')} {u.get('last_name', '')}".strip()
                    except Exception:
                        pass

                db.commit()

                attachment = ""
                if dragon.egg_path:
                    filepath = os.path.join(_IMAGES, os.path.basename(dragon.egg_path))
                    if os.path.isfile(filepath):
                        attachment = _upload_image(vk, filepath)

                msg = (
                    f"🎁 В твоей коллекции пополнение!\n\n"
                    f"Тебе выдано бесплатное яйцо дракона «{dragon.egg_type or dragon.name}» за донат.\n"
                    f"PIN-код: {dragon.pin_code}\n\n"
                    f"Введи его, нажав «🥚 Добавить яйцо дракона» в разделе «📖 Список Бестиария»."
                )

                keyboard = json.dumps({
                    "one_time": True,
                    "buttons": [
                        [{"action": {"type": "text", "label": "🥚 Добавить яйцо дракона", "payload": json.dumps({"cmd": "pin"}, ensure_ascii=False)}, "color": "primary"}],
                        [{"action": {"type": "text", "label": "📖 Список Бестиария", "payload": json.dumps({"cmd": "garden"}, ensure_ascii=False)}, "color": "secondary"},
                         {"action": {"type": "text", "label": "❓ Помощь", "payload": json.dumps({"cmd": "help"}, ensure_ascii=False)}, "color": "secondary"}],
                        [{"action": {"type": "open_link", "label": "📖 Мой Бестиарий", "link": "https://vk.ru/app54663330"}}],
                    ],
                }, ensure_ascii=False)

                try:
                    from bot.handlers.commands import user_has_legendary
                    from bot.keyboard import keyboard_with_legends
                    if user_has_legendary(db, user.vk_id):
                        keyboard = keyboard_with_legends(keyboard)
                except Exception:
                    pass
                try:
                    from bot.handlers.epic import user_has_epic
                    from bot.keyboard import keyboard_with_epics
                    if user_has_epic(db, user.vk_id):
                        keyboard = keyboard_with_epics(keyboard)
                except Exception:
                    pass

                try:
                    vk.messages.send(
                        user_id=user.vk_id,
                        message=msg,
                        random_id=random.randint(1, 2**31 - 1),
                        keyboard=keyboard,
                        attachment=attachment,
                    )
                    pin_record.notified = True
                    db.commit()
                    logger.info(f"Issued free PIN {dragon.pin_code} (dragon {dragon.id}) to user {user.vk_id}")
                except Exception as e:
                    logger.error(f"Failed to notify user {user.vk_id} about reward PIN: {e}")
