"""VK Bot — main entry point with longpoll listener and keyboard support."""

import sys
import os
import json
import random
import threading
import traceback
import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)
sys.path.insert(0, os.path.join(_root, "api"))

import config
from db import SessionLocal
from bot.fsm import IDLE, AWAIT_PIN, AWAIT_GARDEN, is_growing, is_waiting_text, grow_state, step_from_state, is_legend, is_legend_waiting, is_epic_egg, is_epic_egg_waiting, is_epic_care, is_epic_care_waiting, AWAIT_EPIC_NAME, AWAIT_EPIC_RESTART
from bot.handlers.commands import handle_start, handle_help, handle_garden, switch_dragon, cancel_garden, handle_switch_to, handle_balance
from bot.handlers.pin import handle_pin_command, handle_pin_entry
from bot.handlers.grow import handle_grow_message, handle_grow_command, handle_norm_command, handle_x2_command, handle_back_command
from bot.handlers.shop import handle_shop_command, handle_buy
from bot.handlers.legend import handle_legend_start, handle_legend_mode, handle_legend_message
from bot.handlers.epic import handle_epic_command, handle_epic_egg_mode, handle_epic_egg_message, handle_epic_name
from bot.services.user_service import get_or_create_user
from bot.scheduler import run_timeout_checker
from bot.keyboard import idle_keyboard, growing_keyboard, waiting_keyboard, start_growing_keyboard, step_buttons_keyboard, await_pin_keyboard, await_garden_keyboard
from datetime import datetime


from datetime import datetime


def _handle_growing_chat(user, db, send_message, upload_image=None):
    from bot.services.grow_service import get_timeout_remaining, get_dragon_step, get_total_steps
    from models import Dragon
    dragon = db.query(Dragon).filter(Dragon.id == user.current_dragon_id).first()
    label = dragon.egg_type or "яйцо" if dragon else "?"
    has_progress = user.current_step > 1

    remaining = get_timeout_remaining(db, user.vk_id, user.current_dragon_id)
    if remaining is not None:
        total_secs = int(remaining.total_seconds())
        hours, remainder = divmod(total_secs, 3600)
        minutes = remainder // 60
        send_message(
            f"{'🐣' if has_progress else '🥚'} Яйцо «{label}» выращивается!\n"
            f"⏳ До следующего шага осталось: {hours} ч. {minutes} мин."
        )
    else:
        total = get_total_steps(db, user.current_dragon_id)
        step_def = get_dragon_step(db, user.current_dragon_id, user.current_step)
        msg = f"{'🐣' if has_progress else '🥚'} {label}\n📋 Шаг {user.current_step} из {total}"
        if step_def:
            msg += f"\n\n🎯 Норма: {step_def.crosses_norm} крестиков\nВыбери режим:"
        attachment = ""
        if upload_image and dragon and dragon.egg_path:
            filepath = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "images", "dragons",
                os.path.basename(dragon.egg_path),
            )
            if os.path.isfile(filepath):
                attachment = upload_image(filepath, peer_id=user.vk_id)
        send_message(msg, attachment=attachment, keyboard=step_buttons_keyboard())


def get_keyboard(state: str, user=None) -> str:
    if state == AWAIT_PIN:
        return await_pin_keyboard()
    if state == AWAIT_GARDEN:
        return await_garden_keyboard()
    if is_growing(state):
        if is_waiting_text(state):
            return waiting_keyboard()
        return growing_keyboard()
    return idle_keyboard(has_active=bool(user and user.current_dragon_id))


def extract_cmd(text: str, payload_str: str) -> str | None:
    if payload_str:
        try:
            payload = json.loads(payload_str)
            cmd = payload.get("cmd", "")
            if cmd:
                return cmd
        except (json.JSONDecodeError, TypeError):
            pass
    t = text.strip().lower()

    if "дракона" in t or "/pin" in t:
        return "pin"
    if "/start" in t or "выращивать" in t:
        return "start"
    if "помощь" in t or "/help" in t:
        return "help"
    if "бестиарий" in t or "сменить" in t or "/garden" in t:
        return "garden"
    if "копилка" in t or "копилку" in t or "баланс" in t:
        return "balance"
    if "магазин" in t or "лавка" in t:
        return "shop"
    if "эпическ" in t or "пещера" in t or "пещеру" in t:
        return "epic"
    if "выращиванию" in t:
        return "grow"
    if t in ("норма", "норма"):
        return "norm"
    if t in ("штраф", "штраф (x2)", "x2"):
        return "x2"
    if t in ("назад", "◀ назад"):
        return "back"
    return None


def main():
    if not config.VK_GROUP_TOKEN or not config.VK_GROUP_ID:
        print("VK_GROUP_TOKEN and VK_GROUP_ID not set in .env — bot sleeping.")
        import time
        while True:
            time.sleep(60)
        return

    vk_session = vk_api.VkApi(token=config.VK_GROUP_TOKEN, api_version="5.199")
    vk = vk_session.get_api()
    longpoll = VkBotLongPoll(vk_session, group_id=config.VK_GROUP_ID)

    print(f"Dragons bot started (group {config.VK_GROUP_ID})")

    scheduler_thread = threading.Thread(
        target=run_timeout_checker,
        args=(SessionLocal, vk, 30),
        daemon=True,
    )
    scheduler_thread.start()
    print("Timeout scheduler started")

    def upload_image(filepath: str, log_error=None, peer_id=0) -> str:
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
                    import time
                    time.sleep(1)
        msg = f"Image upload failed after 3 retries: {last_error}"
        print(msg)
        if log_error:
            log_error(str(last_error), last_tb)
        return ""

    for event in longpoll.listen():
        if event.type != VkBotEventType.MESSAGE_NEW:
            continue

        msg = event.object.message
        user_id = msg.get("from_id")
        text = msg.get("text", "").strip()
        attachments = msg.get("attachments", [])
        payload_str = msg.get("payload", "")

        if not user_id:
            continue
        if not text and not attachments:
            continue

        db = SessionLocal()
        try:
            user = get_or_create_user(db, user_id)

            def send_message(message, keyboard=None, attachment=""):
                if not message and not attachment:
                    return
                kwargs = {
                    "user_id": user_id,
                    "message": message or "",
                    "random_id": random.randint(1, 2**31 - 1),
                }
                if keyboard is None:
                    keyboard = get_keyboard(user.state, user)
                if keyboard:
                    kwargs["keyboard"] = keyboard
                if attachment:
                    kwargs["attachment"] = attachment
                vk.messages.send(**kwargs)

            cmd = extract_cmd(text, payload_str)

            try:
                from bot.handlers.epic import maybe_offer_epic
                maybe_offer_epic(user, db, send_message, upload_image)
            except Exception as e:
                from bot.services.grow_service import log_to_db
                log_to_db(
                    source="bot",
                    error_type="EPIC_SPAWN",
                    message=f"maybe_offer_epic failed for user {user.vk_id}: {e}",
                    traceback_text=__import__("traceback").format_exc(),
                    user_id=user.vk_id,
                    db=db,
                )

            if user.state == AWAIT_GARDEN and not cmd:
                t = text.strip().lower()
                if t in ("0", "не менять"):
                    cancel_garden(user, db, send_message, upload_image)
                    continue
                if t.isdigit():
                    switch_dragon(user, int(t), db, send_message, upload_image)
                    continue

            if cmd == "switch_to":
                try:
                    payload = json.loads(payload_str) if payload_str else {}
                    dragon_id = payload.get("dragon_id")
                except (json.JSONDecodeError, TypeError):
                    dragon_id = None
                if dragon_id:
                    handle_switch_to(user, dragon_id, db, send_message, upload_image)
                else:
                    send_message("Не удалось переключиться. Попробуй через «🔄🥚 Сменить яйцо дракона».")
                continue

            if cmd == "shop":
                page = 0
                try:
                    payload = json.loads(payload_str) if payload_str else {}
                    page = int(payload.get("page", 0) or 0)
                except (json.JSONDecodeError, TypeError, ValueError):
                    page = 0
                handle_shop_command(user, db, send_message, page)
                continue

            if cmd == "buy":
                try:
                    payload = json.loads(payload_str) if payload_str else {}
                    item_id = payload.get("item_id")
                except (json.JSONDecodeError, TypeError):
                    item_id = None
                if item_id:
                    handle_buy(user, int(item_id), db, send_message)
                else:
                    send_message("Не удалось купить товар.")
                continue

            if cmd == "legend":
                try:
                    payload = json.loads(payload_str) if payload_str else {}
                    dragon_id = payload.get("dragon_id")
                except (json.JSONDecodeError, TypeError):
                    dragon_id = None
                if dragon_id:
                    handle_legend_start(user, int(dragon_id), db, send_message, upload_image)
                else:
                    send_message("Не удалось открыть легенду.")
                continue

            if is_legend(user.state) and cmd in ("norm", "x2"):
                handle_legend_mode(user, cmd, db, send_message)
                continue

            if is_legend_waiting(user.state) and not cmd:
                handle_legend_message(user, text, attachments, db, send_message, upload_image)
                continue

            if cmd == "epic":
                handle_epic_command(user, db, send_message, upload_image)
                continue

            if is_epic_egg(user.state) and cmd in ("norm", "x2"):
                handle_epic_egg_mode(user, cmd, db, send_message)
                continue

            if is_epic_egg_waiting(user.state) and not cmd:
                handle_epic_egg_message(user, text, attachments, db, send_message, upload_image)
                continue

            if is_epic_care(user.state) and cmd in ("norm", "x2"):
                from bot.handlers.epic_care import handle_care_mode
                handle_care_mode(user, cmd, db, send_message)
                continue

            if is_epic_care_waiting(user.state) and not cmd:
                from bot.handlers.epic_care import handle_care_message
                handle_care_message(user, text, attachments, db, send_message, upload_image)
                continue

            if user.state == AWAIT_EPIC_NAME and text and not cmd:
                handle_epic_name(user, text, db, send_message, upload_image)
                continue

            if cmd == "epic_restart":
                try:
                    payload = json.loads(payload_str) if payload_str else {}
                    mode = payload.get("mode", "random")
                except (json.JSONDecodeError, TypeError):
                    mode = "random"
                from bot.handlers.epic_care import handle_epic_restart
                handle_epic_restart(user, mode, db, send_message, upload_image)
                continue

            if cmd == "start":
                handle_start(user, db, send_message)
            elif cmd == "help":
                handle_help(send_message)
            elif cmd == "balance":
                handle_balance(user, db, send_message)
            elif cmd == "garden":
                handle_garden(user, db, send_message)
            elif cmd == "garden_cancel":
                cancel_garden(user, db, send_message, upload_image)
            elif cmd == "pin":
                handle_pin_command(user, db, send_message)
            elif cmd == "grow":
                handle_grow_command(user, db, send_message, upload_image)
            elif cmd == "norm":
                handle_norm_command(user, db, send_message)
            elif cmd == "x2":
                handle_x2_command(user, db, send_message)
            elif cmd == "back":
                handle_back_command(user, db, send_message, upload_image)

            elif user.state == AWAIT_PIN and text and not cmd:
                handle_pin_entry(user, text, db, send_message, upload_image)

            elif is_waiting_text(user.state) and user.current_dragon_id:
                handle_grow_message(user, text, attachments, db, send_message, upload_image)

            elif is_growing(user.state) and user.current_dragon_id and text and not cmd:
                from bot.services.grow_service import get_timeout_remaining
                if not is_waiting_text(user.state) and not get_timeout_remaining(db, user.vk_id, user.current_dragon_id):
                    send_message(
                        "⚠ Сначала выбери режим выращивания: «🎯 Норма» или «⚡ Штраф (x2)».",
                        keyboard=step_buttons_keyboard(),
                    )
                else:
                    _handle_growing_chat(user, db, send_message, upload_image)

            elif user.state == IDLE and text and not cmd:
                from models import UserDragon
                has_any = db.query(UserDragon).filter(UserDragon.user_id == user_id).first() is not None
                if has_any:
                    send_message(
                        "🐉 Добро пожаловать в Бестиарий драконьих легенд!\n"
                        "Нажми «🥚 Добавить яйцо дракона» чтобы начать выращивание."
                    )
                else:
                    send_message(
                        "🐉 У тебя пока нет ни одного яйца дракона для выращивания.\n"
                        "Нажми «🥚 Добавить яйцо дракона» чтобы начать выращивание."
                    )

        except Exception as exc:
            print(f"Error processing message from {user_id}: {exc}")
            traceback.print_exc()
            try:
                from models import ErrorLog
                err = ErrorLog(
                    source="bot",
                    error_type=type(exc).__name__,
                    message=str(exc),
                    traceback_text=traceback.format_exc(),
                    user_id=user_id,
                    created_at=datetime.now().isoformat(),
                )
                db.add(err)
                db.commit()
            except Exception:
                pass
        finally:
            db.close()


if __name__ == "__main__":
    main()
