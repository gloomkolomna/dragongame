"""Character service — axes, balance, and character summary for epic dragons."""

from models import CharacterAxis, CharacterBalance, UserDragon


def get_axes(db):
    return db.query(CharacterAxis).filter(CharacterAxis.is_active == True).order_by(CharacterAxis.sort_order, CharacterAxis.id).all()


def get_all_axes(db):
    return db.query(CharacterAxis).order_by(CharacterAxis.sort_order, CharacterAxis.id).all()


def upsert_balance(db, user_dragon_id, axis_id, delta):
    row = db.query(CharacterBalance).filter(
        CharacterBalance.user_dragon_id == user_dragon_id,
        CharacterBalance.axis_id == axis_id,
    ).first()
    if row:
        row.score = (row.score or 0) + delta
    else:
        row = CharacterBalance(user_dragon_id=user_dragon_id, axis_id=axis_id, score=delta)
        db.add(row)
    db.commit()
    return row


def get_balances(db, user_dragon_id):
    return db.query(CharacterBalance).filter(CharacterBalance.user_dragon_id == user_dragon_id).all()


def character_summary(db, user_dragon_id):
    axes = get_axes(db)
    balances = {b.axis_id: b.score for b in get_balances(db, user_dragon_id)}
    result = []
    for axis in axes:
        score = balances.get(axis.id, 0)
        if score > 0:
            result.append({"axis": axis.positive_label, "label": axis.positive_label, "polarity": "positive"})
        elif score < 0:
            result.append({"axis": axis.negative_label, "label": axis.negative_label, "polarity": "negative"})
    return result
