import os
from bot.fsm import AWAIT_PIN, intro_chapter_state, intro_chapter_from_state, is_intro_chapter
from bot.keyboard import intro_keyboard, intro_last_keyboard, empty_keyboard

_INTRO_IMAGES = os.path.join(os.path.dirname(__file__), "..", "..", "images", "intro")


def _is_last_chapter(db, chapter_num):
    from models import IntroChapter
    return db.query(IntroChapter).filter(
        IntroChapter.chapter_number > chapter_num,
        IntroChapter.is_active == True,
    ).first() is None


def _intro_chapter_image(chapter):
    if not chapter or not chapter.image_path:
        return None
    return os.path.join(_INTRO_IMAGES, os.path.basename(chapter.image_path))


def start_intro(user, db, send_message, upload_image=None):
    from models import IntroChapter
    chapter = db.query(IntroChapter).filter(
        IntroChapter.chapter_number == 1,
        IntroChapter.is_active == True,
    ).first()

    if not chapter:
        user.state = AWAIT_PIN
        db.commit()
        send_message("Введи PIN-код с яйца, чтобы начать выращивание.", keyboard=empty_keyboard())
        return

    user.state = intro_chapter_state(1)
    db.commit()

    attachment = ""
    if chapter.image_path and upload_image:
        filepath = _intro_chapter_image(chapter)
        if filepath and os.path.isfile(filepath):
            def log_err(msg, tb=""):
                from datetime import datetime
                from models import ErrorLog
                db.add(ErrorLog(source="bot", error_type="UPLOAD", message=f"{msg} (file={filepath})", user_id=user.vk_id, traceback_text=tb, created_at=datetime.now().isoformat()))
                db.commit()
            attachment = upload_image(filepath, log_error=log_err, peer_id=user.vk_id)

    send_message(
        chapter.text,
        attachment=attachment,
        keyboard=intro_last_keyboard() if _is_last_chapter(db, 1) else intro_keyboard(),
    )


def handle_intro_next(user, db, send_message, upload_image=None):
    from models import IntroChapter
    current_chapter = intro_chapter_from_state(user.state)
    next_chapter_num = current_chapter + 1

    chapter = db.query(IntroChapter).filter(
        IntroChapter.chapter_number == next_chapter_num,
        IntroChapter.is_active == True,
    ).first()

    if not chapter:
        user.state = AWAIT_PIN
        db.commit()
        send_message(
            "✨ История рассказана! Теперь ты готов вырастить своего первого дракона.\n"
            "Введи PIN-код с яйца, чтобы начать.",
            keyboard=empty_keyboard(),
        )
        return

    user.state = intro_chapter_state(next_chapter_num)
    db.commit()

    attachment = ""
    if chapter.image_path and upload_image:
        filepath = _intro_chapter_image(chapter)
        if filepath and os.path.isfile(filepath):
            def log_err(msg, tb=""):
                from datetime import datetime
                from models import ErrorLog
                db.add(ErrorLog(source="bot", error_type="UPLOAD", message=f"{msg} (file={filepath})", user_id=user.vk_id, traceback_text=tb, created_at=datetime.now().isoformat()))
                db.commit()
            attachment = upload_image(filepath, log_error=log_err, peer_id=user.vk_id)

    send_message(
        chapter.text,
        attachment=attachment,
        keyboard=intro_last_keyboard() if _is_last_chapter(db, next_chapter_num) else intro_keyboard(),
    )


def handle_intro_chat(user, db, send_message, upload_image=None):
    from models import IntroChapter
    current = intro_chapter_from_state(user.state)
    chapter = db.query(IntroChapter).filter(
        IntroChapter.chapter_number == current,
        IntroChapter.is_active == True,
    ).first()

    if not chapter:
        user.state = AWAIT_PIN
        db.commit()
        send_message("Введи PIN-код с яйца, чтобы начать выращивание.", keyboard=empty_keyboard())
        return

    attachment = ""
    if chapter.image_path and upload_image:
        filepath = _intro_chapter_image(chapter)
        if filepath and os.path.isfile(filepath):
            def log_err(msg, tb=""):
                from datetime import datetime
                from models import ErrorLog
                db.add(ErrorLog(source="bot", error_type="UPLOAD", message=f"{msg} (file={filepath})", user_id=user.vk_id, traceback_text=tb, created_at=datetime.now().isoformat()))
                db.commit()
            attachment = upload_image(filepath, log_error=log_err, peer_id=user.vk_id)

    send_message(
        chapter.text,
        attachment=attachment,
        keyboard=intro_last_keyboard() if _is_last_chapter(db, current) else intro_keyboard(),
    )
