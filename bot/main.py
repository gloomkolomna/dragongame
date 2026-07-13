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
from bot.fsm import IDLE, AWAIT_PIN, AWAIT_GARDEN, AWAIT_LEGENDS, AWAIT_EPICS, AWAIT_INCUBATOR, AWAIT_RULES, is_growing, is_waiting_text, grow_state, step_from_state, is_legend, is_legend_waiting, is_epic_egg, is_epic_egg_waiting, is_epic_care, is_epic_care_waiting, is_epic_care_sub, is_epic_care_sub_waiting, AWAIT_EPIC_NAME, AWAIT_EPIC_RESTART, is_intro_chapter, intro_chapter_from_state
from bot.handlers.commands import handle_start, handle_help, handle_garden, switch_dragon, cancel_garden, handle_switch_to, handle_balance, handle_legends, handle_legends_pick, cancel_legends, user_has_legendary
from bot.handlers.pin import handle_pin_command, handle_pin_entry
from bot.handlers.grow import handle_grow_message, handle_grow_command, handle_norm_command, handle_x2_command, handle_back_command
from bot.handlers.shop import handle_shop_command, handle_buy, handle_inventory
from bot.handlers.legend import handle_legend_start, handle_legend_mode, handle_legend_message
from bot.handlers.epic import handle_epic_command, handle_epic_egg_mode, handle_epic_egg_message, handle_epic_name, handle_epics, handle_epics_pick, cancel_epics, user_has_epic
from bot.handlers.rules import handle_rules, handle_rules_section, handle_rules_pick, cancel_rules
from bot.handlers.intro import handle_intro_next, handle_intro_chat, start_intro
from bot.services.user_service import get_or_create_user
from bot.scheduler import run_timeout_checker
from bot.services.donor_sync import run_donor_sync
from bot.keyboard import idle_keyboard, growing_keyboard, waiting_keyboard, start_growing_keyboard, step_buttons_keyboard, await_pin_keyboard, await_garden_keyboard, keyboard_with_legends, keyboard_with_epics, keyboard_with_incubator, intro_keyboard, empty_keyboard
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
        from bot.handlers.grow import step_attachment
        attachment = step_attachment(db, user, dragon, step_def, upload_image)
        send_message(msg, attachment=attachment, keyboard=step_buttons_keyboard())


def get_keyboard(state: str, user=None) -> str:
    if state == AWAIT_EPIC_NAME:
        from bot.keyboard import epic_name_keyboard
        return epic_name_keyboard()
    if state == AWAIT_PIN:
        return await_pin_keyboard()
    if state == AWAIT_GARDEN:
        return await_garden_keyboard(with_cancel=True)
    if state == AWAIT_INCUBATOR:
        return empty_keyboard()
    if state == AWAIT_EPIC_RESTART:
        from bot.keyboard import epic_restart_keyboard
        return epic_restart_keyboard()
    if state == AWAIT_RULES:
        from bot.handlers.rules import SECTIONS_MENU_VIEW
        from bot.keyboard import rules_menu_keyboard
        return rules_menu_keyboard(SECTIONS_MENU_VIEW)
    if is_intro_chapter(state):
        return intro_keyboard()
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
    if "правила" in t or "/rules" in t:
        return "rules"
    if "легендарн" in t:
        return "legends"
    if "бестиарий" in t or "сменить" in t or "/garden" in t:
        return "garden"
    if "копилка" in t or "копилку" in t or "баланс" in t:
        return "balance"
    if "магазин" in t or "лавка" in t:
        return "shop"
    if "инвентарь" in t:
        return "inventory"
    if "эпические драконы" in t:
        return "epics"
    if "эпическ" in t or "пещера" in t or "пещеру" in t:
        return "epic"
    if "инкубатор" in t:
        return "incubator"
    if "выращиванию" in t:
        return "grow"
    if "читать" in t:
        return "intro_next"
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

    donor_sync_thread = threading.Thread(
        target=run_donor_sync,
        args=(SessionLocal, config.DONOR_SYNC_INTERVAL_HOURS),
        daemon=True,
    )
    donor_sync_thread.start()
    print("Donor sync started")

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
                    try:
                        if (user.state not in (AWAIT_LEGENDS, AWAIT_EPIC_NAME)
                                and not is_legend(user.state)
                                and user_has_legendary(db, user.vk_id)):
                            keyboard = keyboard_with_legends(keyboard)
                    except Exception:
                        pass
                    try:
                        if (user.state not in (AWAIT_EPICS, AWAIT_EPIC_NAME)
                                and not is_epic_egg(user.state)
                                and not is_epic_care(user.state)
                                and user_has_epic(db, user.vk_id)):
                            keyboard = keyboard_with_epics(keyboard)
                    except Exception:
                        pass
                    try:
                        if (user.state not in (AWAIT_EPICS, AWAIT_EPIC_NAME, AWAIT_INCUBATOR)
                                and not is_epic_egg(user.state)
                                and not is_epic_care(user.state)
                                and user.epic_unlocked):
                            keyboard = keyboard_with_incubator(keyboard)
                    except Exception:
                        pass
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

            if user.state == AWAIT_EPIC_NAME:
                if cmd in ("garden", "help", "rules", "start"):
                    if cmd == "garden":
                        handle_garden(user, db, send_message)
                    elif cmd == "help":
                        handle_help(send_message)
                    elif cmd == "rules":
                        handle_rules(user, db, send_message)
                    elif cmd == "start":
                        handle_start(user, db, send_message, upload_image)
                    continue
                if text:
                    handle_epic_name(user, text, db, send_message, upload_image)
                continue

            if user.state == AWAIT_GARDEN and not cmd:
                t = text.strip().lower()
                if t in ("0", "не менять"):
                    cancel_garden(user, db, send_message, upload_image)
                    continue
                if t.isdigit():
                    switch_dragon(user, int(t), db, send_message, upload_image)
                    continue

            if user.state == AWAIT_LEGENDS and not cmd:
                t = text.strip().lower()
                if t in ("0", "назад", "отмена", "не читать"):
                    cancel_legends(user, db, send_message)
                    continue
                if t.isdigit():
                    handle_legends_pick(user, int(t), db, send_message, upload_image)
                    continue

            if user.state == AWAIT_EPICS and not cmd:
                t = text.strip().lower()
                if t in ("0", "назад", "отмена"):
                    cancel_epics(user, db, send_message)
                    continue
                if t.isdigit():
                    handle_epics_pick(user, int(t), db, send_message, upload_image)
                    continue

            if user.state == AWAIT_INCUBATOR and not cmd:
                t = text.strip().lower()
                if t in ("0", "назад", "отмена"):
                    from bot.handlers.incubator import handle_incubator_cancel
                    handle_incubator_cancel(user, db, send_message)
                    continue
                if t.isdigit():
                    from bot.handlers.incubator import handle_incubator_pick
                    handle_incubator_pick(user, int(t), db, send_message, upload_image)
                    continue

            if user.state == AWAIT_RULES and not cmd:
                t = text.strip().lower()
                if t in ("0", "закрыть правила", "назад", "отмена"):
                    cancel_rules(user, db, send_message, upload_image)
                    continue
                if t.isdigit():
                    handle_rules_pick(user, db, send_message, int(t))
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

            if cmd == "inventory":
                handle_inventory(user, db, send_message)
                continue

            if cmd == "buy":
                try:
                    payload = json.loads(payload_str) if payload_str else {}
                    item_id = payload.get("item_id")
                except (json.JSONDecodeError, TypeError):
                    item_id = None
                if item_id:
                    handle_buy(user, int(item_id), db, send_message, upload_image)
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

            if cmd == "rules_section":
                section_key = ""
                try:
                    payload = json.loads(payload_str) if payload_str else {}
                    section_key = payload.get("section", "")
                except (json.JSONDecodeError, TypeError):
                    section_key = ""
                handle_rules_section(user, db, send_message, section_key)
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

            if cmd == "incubator":
                from bot.handlers.incubator import handle_incubator
                handle_incubator(user, db, send_message, upload_image)
                continue

            if cmd == "incubator_buy":
                try:
                    payload = json.loads(payload_str) if payload_str else {}
                    dragon_id = payload.get("dragon_id")
                except (json.JSONDecodeError, TypeError):
                    dragon_id = None
                if dragon_id:
                    from bot.handlers.incubator import handle_incubator_pick
                    handle_incubator_pick(user, int(dragon_id), db, send_message, upload_image)
                continue

            if cmd == "incubator_confirm":
                from bot.handlers.incubator import handle_incubator_confirm
                handle_incubator_confirm(user, db, send_message, upload_image)
                continue

            if cmd == "incubator_cancel":
                from bot.handlers.incubator import handle_incubator_cancel
                handle_incubator_cancel(user, db, send_message)
                continue

            if is_epic_egg(user.state) and cmd in ("norm", "x2"):
                handle_epic_egg_mode(user, cmd, db, send_message)
                continue

            if is_epic_egg_waiting(user.state) and not cmd:
                handle_epic_egg_message(user, text, attachments, db, send_message, upload_image)
                continue

            if cmd == "choose_sub":
                try:
                    payload = json.loads(payload_str) if payload_str else {}
                    sub_id = payload.get("sub_id")
                except (json.JSONDecodeError, TypeError):
                    sub_id = None
                if sub_id:
                    from bot.handlers.epic_care import handle_choose_sub
                    handle_choose_sub(user, int(sub_id), db, send_message, upload_image)
                continue

            if cmd == "confirm_sub":
                from bot.handlers.epic_care import handle_confirm_sub
                handle_confirm_sub(user, db, send_message, upload_image)
                continue

            if cmd == "sub_back":
                from bot.handlers.epic_care import handle_sub_back
                handle_sub_back(user, db, send_message, upload_image)
                continue

            if is_epic_care_sub(user.state) and cmd in ("norm", "x2"):
                from bot.handlers.epic_care import handle_sub_mode
                handle_sub_mode(user, cmd, db, send_message)
                continue

            if is_epic_care_sub_waiting(user.state) and not cmd:
                from bot.handlers.epic_care import handle_sub_message
                handle_sub_message(user, text, attachments, db, send_message, upload_image)
                continue

            if is_epic_care(user.state) and cmd == "use_item":
                from bot.handlers.epic_care import handle_care_use_item
                handle_care_use_item(user, db, send_message, upload_image)
                continue

            if is_epic_care(user.state) and cmd == "skip_item":
                from bot.handlers.epic_care import handle_care_skip_item
                handle_care_skip_item(user, db, send_message, upload_image)
                continue

            if is_epic_care(user.state) and cmd in ("norm", "x2"):
                from bot.handlers.epic_care import handle_care_mode
                handle_care_mode(user, cmd, db, send_message)
                continue

            if is_epic_care_waiting(user.state) and not cmd:
                from bot.handlers.epic_care import handle_care_message
                handle_care_message(user, text, attachments, db, send_message, upload_image)
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
                handle_start(user, db, send_message, upload_image)
            elif cmd == "help":
                handle_help(send_message)
            elif cmd == "rules":
                handle_rules(user, db, send_message)
            elif cmd == "rules_close":
                cancel_rules(user, db, send_message, upload_image)
            elif cmd == "balance":
                handle_balance(user, db, send_message)
            elif cmd == "garden":
                handle_garden(user, db, send_message)
            elif cmd == "legends":
                handle_legends(user, db, send_message)
            elif cmd == "epics":
                handle_epics(user, db, send_message)
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

            elif cmd == "intro_next" and is_intro_chapter(user.state):
                handle_intro_next(user, db, send_message, upload_image)

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

            elif user.state == AWAIT_EPIC_RESTART and text and not cmd:
                from bot.keyboard import epic_restart_keyboard
                send_message(
                    "🐲 Выбери, кого растить дальше: «🐲 Такого же заново» или «🎲 Нового случайного».\n"
                    "Или нажми «🔄🥚 Сменить яйцо дракона», чтобы вернуться к другим драконам.",
                    keyboard=epic_restart_keyboard(),
                )

            elif is_intro_chapter(user.state) and text and not cmd:
                handle_intro_chat(user, db, send_message, upload_image)

            elif user.state == IDLE and text and not cmd:
                from models import UserDragon, IntroChapter
                has_any = db.query(UserDragon).filter(UserDragon.user_id == user_id).first() is not None
                if has_any:
                    send_message(
                        "🐲 Добро пожаловать в Бестиарий драконьих легенд!\n"
                        "Нажми «🥚 Добавить яйцо дракона» чтобы начать выращивание."
                    )
                else:
                    has_intro = db.query(IntroChapter).filter(IntroChapter.is_active == True).first() is not None
                    if has_intro:
                        start_intro(user, db, send_message, upload_image)
                    else:
                        send_message(
                            "🐲 У тебя пока нет ни одного яйца дракона для выращивания.\n"
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
