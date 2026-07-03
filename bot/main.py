"""VK Bot — main entry point with longpoll listener and keyboard support."""

import sys
import os
import json
import random
import threading
import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)
sys.path.insert(0, os.path.join(_root, "api"))

import config
from db import SessionLocal
from bot.fsm import IDLE, AWAIT_PIN, AWAIT_GARDEN, is_growing
from bot.handlers.commands import handle_start, handle_help, handle_status, handle_garden, switch_dragon, cancel_garden, handle_switch_to
from bot.handlers.pin import handle_pin_command, handle_pin_entry
from bot.handlers.grow import handle_grow_message
from bot.services.user_service import get_or_create_user
from bot.scheduler import run_timeout_checker
from bot.keyboard import idle_keyboard, growing_keyboard, await_pin_keyboard, await_garden_keyboard


def get_keyboard(state: str, user=None) -> str:
    if state == AWAIT_PIN:
        return await_pin_keyboard()
    if state == AWAIT_GARDEN:
        return await_garden_keyboard()
    if is_growing(state):
        return growing_keyboard()
    return idle_keyboard(has_active=bool(user and user.current_dragon_id))


def extract_cmd(text: str, payload_str: str) -> str | None:
    """Extract command from button payload or text."""
    if payload_str:
        try:
            payload = json.loads(payload_str)
            cmd = payload.get("cmd", "")
            if cmd:
                return cmd
        except (json.JSONDecodeError, TypeError):
            pass
    t = text.strip().lower()

    # Payload-based commands from keyboard buttons
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

    def upload_image(filepath: str) -> str:
        """Upload local image to VK and return attachment string."""
        try:
            if not os.path.isfile(filepath):
                return ""
            upload_url = vk.photos.getMessagesUploadServer(peer_id=0)["upload_url"]
            import requests
            with open(filepath, "rb") as f:
                resp = requests.post(upload_url, files={"photo": ("image.jpg", f, "image/jpeg")}).json()
            saved = vk.photos.saveMessagesPhoto(photo=resp["photo"], server=resp["server"], hash=resp["hash"])[0]
            return f"photo{saved['owner_id']}_{saved['id']}"
        except Exception as e:
            print(f"Image upload failed: {e}")
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

            # AWAIT_GARDEN: expect number for switching, or 0/"не менять" to cancel
            if user.state == AWAIT_GARDEN and not cmd:
                t = text.strip().lower()
                if t in ("0", "не менять"):
                    cancel_garden(user, db, send_message)
                    continue
                if t.isdigit():
                    switch_dragon(user, int(t), db, send_message)
                    continue

            # switch_to: parse dragon_id from payload
            if cmd == "switch_to":
                try:
                    payload = json.loads(payload_str) if payload_str else {}
                    dragon_id = payload.get("dragon_id")
                except (json.JSONDecodeError, TypeError):
                    dragon_id = None
                if dragon_id:
                    handle_switch_to(user, dragon_id, db, send_message)
                else:
                    send_message("Не удалось переключиться. Попробуй через «🔄 Сменить дракона».")
                continue

            if cmd == "start":
                handle_start(user, db, send_message)
            elif cmd == "help":
                handle_help(send_message)
            elif cmd == "status":
                handle_status(user, db, send_message)
            elif cmd == "garden":
                handle_garden(user, db, send_message)
            elif cmd == "garden_cancel":
                cancel_garden(user, db, send_message)
            elif cmd == "pin":
                handle_pin_command(user, db, send_message)

            # AWAIT_PIN: check for 4-digit PIN
            elif user.state == AWAIT_PIN and text and not cmd:
                handle_pin_entry(user, text, db, send_message, upload_image)

            # GROWING: photo + keyword
            elif is_growing(user.state) and user.current_dragon_id:
                handle_grow_message(user, text, attachments, db, send_message, upload_image)

            # IDLE: anything else → prompt
            elif user.state == IDLE and text and not cmd:
                send_message(
                    "🐉 Добро пожаловать в Бестиарий драконьих легенд!\n"
                    "Нажми «🐉 Добавить дракона» чтобы начать выращивание."
                )

        except Exception as exc:
            print(f"Error processing message from {user_id}: {exc}")
            try:
                vk.messages.send(
                    user_id=user_id,
                    message="Произошла ошибка. Попробуй ещё раз.",
                    random_id=random.randint(1, 2**31 - 1),
                    keyboard=idle_keyboard(),
                )
            except Exception:
                pass
        finally:
            db.close()


if __name__ == "__main__":
    main()
