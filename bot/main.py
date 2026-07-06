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
from bot.fsm import IDLE, AWAIT_PIN, AWAIT_GARDEN, is_growing, is_waiting_text, grow_state, step_from_state
from bot.handlers.commands import handle_start, handle_help, handle_status, handle_garden, switch_dragon, cancel_garden, handle_switch_to
from bot.handlers.pin import handle_pin_command, handle_pin_entry
from bot.handlers.grow import handle_grow_message, handle_grow_command, handle_norm_command, handle_x2_command, handle_back_command
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
    if "статус" in t or "/status" in t:
        return "status"
    if "помощь" in t or "/help" in t:
        return "help"
    if "бестиарий" in t or "сменить" in t or "/garden" in t:
        return "garden"
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
        try:
            if not os.path.isfile(filepath):
                return ""
            upload_url = vk.photos.getMessagesUploadServer(peer_id=peer_id)["upload_url"]
            import requests
            with open(filepath, "rb") as f:
                resp = requests.post(upload_url, files={"photo": ("image.jpg", f, "image/jpeg")}, timeout=30).json()
            saved = vk.photos.saveMessagesPhoto(photo=resp["photo"], server=resp["server"], hash=resp["hash"])[0]
            return f"photo{saved['owner_id']}_{saved['id']}"
        except Exception as e:
            msg = f"Image upload failed: {e}"
            print(msg)
            if log_error:
                log_error(str(e))
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

            if cmd == "start":
                handle_start(user, db, send_message)
            elif cmd == "help":
                handle_help(send_message)
            elif cmd == "status":
                handle_status(user, db, send_message, upload_image)
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
