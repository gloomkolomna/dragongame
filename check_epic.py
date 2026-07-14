"""Check epic_unlocked status for user account debugging."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "api"))

from db import SessionLocal
from models import User, Dragon, UserDragon

db = SessionLocal()

vk_id = int(sys.argv[1]) if len(sys.argv) > 1 else None
if not vk_id:
    vk_ids = [u.vk_id for u in db.query(User.vk_id).limit(10).all()]
    if not vk_ids:
        print("No users in DB.")
        db.close()
        sys.exit(1)
    vk_id = vk_ids[0]
    print(f"No VK ID given, using first user: {vk_id}")

user = db.query(User).filter(User.vk_id == vk_id).first()
if not user:
    print(f"User {vk_id} not found.")
    db.close()
    sys.exit(1)

print(f"\n=== User {vk_id} ===")
print(f"  state:            {user.state}")
print(f"  epic_unlocked:    {user.epic_unlocked}")
print(f"  epic_dragon_id:   {user.epic_dragon_id}")
print(f"  stitches_balance: {user.stitches_balance}")
print(f"  current_dragon_id: {user.current_dragon_id}")
print(f"  current_step:     {user.current_step}")

regular_completed = db.query(UserDragon).join(Dragon, Dragon.id == UserDragon.dragon_id).filter(
    UserDragon.user_id == vk_id,
    UserDragon.completed_at != "",
    Dragon.is_epic == False,
).count()
print(f"\n  Completed regular dragons: {regular_completed}")

epic_pool = db.query(Dragon).filter(Dragon.is_epic == True).all()
print(f"  Epic dragons in pool: {len(epic_pool)}")
for d in epic_pool:
    print(f"    Dragon#{d.id} {d.egg_type or d.name}")

epic_ud_rows = db.query(UserDragon).join(Dragon, Dragon.id == UserDragon.dragon_id).filter(
    UserDragon.user_id == vk_id, Dragon.is_epic == True
).all()
print(f"  Epic UserDragon rows: {len(epic_ud_rows)}")
for ud in epic_ud_rows:
    d = db.query(Dragon).filter(Dragon.id == ud.dragon_id).first()
    status = "completed" if ud.completed_at else "active"
    print(f"    Dragon#{ud.dragon_id} ({d.egg_type if d else '?'}) -- {status}")

if not user.epic_unlocked:
    print()
    if regular_completed == 0:
        print("  -> epic_unlocked=False: no completed regular dragons yet. Grow one first.")
    elif len(epic_pool) == 0:
        print("  -> epic_unlocked=False: no epic dragons in pool. Add them in admin panel.")
        print("     Then bot's maybe_spawn_first_epic will fire on next message.")
    else:
        print(f"  -> WARNING: {regular_completed} completed dragon(s) + {len(epic_pool)} epic(s) in pool, but epic_unlocked=False.")
        print("     Run this SQL: UPDATE users SET epic_unlocked = 1 WHERE vk_id = ?;")
        print(f"     Or: api\\venv\\Scripts\\python.exe check_epic.py {vk_id} --fix")
    print()

if "--fix" in sys.argv and not user.epic_unlocked:
    user.epic_unlocked = True
    db.commit()
    print("  FIXED: epic_unlocked set to True.")

db.close()
