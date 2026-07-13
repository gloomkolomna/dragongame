from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, Text, ForeignKey, UniqueConstraint
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class Family(Base):
    __tablename__ = "families"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    description = Column(Text, default="")
    sort_order = Column(Integer, default=0)
    color = Column(String(7), default="#9b6fc7")
    image_path = Column(String, default="")


class Dragon(Base):
    __tablename__ = "dragons"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    egg_type = Column(String, default="")
    rarity = Column(Integer, nullable=False)
    steps_count = Column(Integer, nullable=False)
    egg_path = Column(String, default="")       # картинка ЯЙЦА
    dragon_path = Column(String, default="")    # картинка ВЗРОСЛОГО дракона
    description = Column(Text, default="")
    is_active = Column(Boolean, default=True)
    pin_code = Column(String(5), nullable=True, unique=True)
    family_id = Column(Integer, ForeignKey("families.id", ondelete="SET NULL"), nullable=True)
    is_epic = Column(Boolean, default=False)
    epic_cost_stitches = Column(Integer, nullable=True, default=None)
    legend_image_path = Column(String, default="")
    legend_title = Column(String, default="")
    legend_full_text = Column(Text, default="")


class DragonStep(Base):
    __tablename__ = "dragon_steps"
    id = Column(Integer, primary_key=True, autoincrement=True)
    dragon_id = Column(Integer, ForeignKey("dragons.id", ondelete="CASCADE"), nullable=False)
    step_number = Column(Integer, nullable=False)
    task_description = Column(Text, default="")
    magic_action = Column(Text, default="")
    hint = Column(Text, default="")
    keyword = Column(String, default="вышито")
    timeout_hours = Column(Integer, default=0)
    timeout_minutes = Column(Integer, default=0)
    crosses_norm = Column(Integer, default=1000)
    phase = Column(Integer, default=0)
    image_path = Column(String, default="")


class CollectionGrid(Base):
    __tablename__ = "collection_grid"
    id = Column(Integer, primary_key=True, autoincrement=True)
    family_id = Column(Integer, ForeignKey("families.id", ondelete="CASCADE"), nullable=False)
    cell_x = Column(Integer, nullable=False)
    cell_y = Column(Integer, nullable=False)
    dragon_id = Column(Integer, ForeignKey("dragons.id", ondelete="SET NULL"), nullable=True, unique=True)
    __table_args__ = (UniqueConstraint("family_id", "cell_x", "cell_y"),)



class User(Base):
    __tablename__ = "users"
    vk_id = Column(Integer, primary_key=True)
    state = Column(String, default="idle")
    current_dragon_id = Column(Integer, nullable=True)
    current_step = Column(Integer, default=0)
    state_data = Column(Text, default="{}")
    registered_at = Column(String, default="")
    stitches_balance = Column(Integer, default=0)
    epic_unlocked = Column(Boolean, default=False)
    epic_dragon_id = Column(Integer, nullable=True)
    custom_price_per_dragon = Column(Integer, nullable=True)


class UserProgress(Base):
    __tablename__ = "user_progress"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.vk_id", ondelete="CASCADE"), nullable=False)
    dragon_id = Column(Integer, ForeignKey("dragons.id", ondelete="CASCADE"), nullable=False)
    step_number = Column(Integer, nullable=False)
    photo_before_id = Column(Text, default="")
    photo_after_id = Column(Text, default="")
    completed = Column(Boolean, default=False)
    completed_at = Column(String, default="")
    epic_name = Column(String, default="")
    __table_args__ = (UniqueConstraint("user_id", "dragon_id", "step_number"),)


class UserLegendProgress(Base):
    __tablename__ = "user_legend_progress"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.vk_id", ondelete="CASCADE"), nullable=False)
    dragon_id = Column(Integer, ForeignKey("dragons.id", ondelete="CASCADE"), nullable=False)
    fragment_number = Column(Integer, nullable=False)
    photo_before_id = Column(Text, default="")
    photo_after_id = Column(Text, default="")
    completed = Column(Boolean, default=False)
    completed_at = Column(String, default="")
    __table_args__ = (UniqueConstraint("user_id", "dragon_id", "fragment_number"),)


class UserDragon(Base):
    __tablename__ = "user_dragons"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.vk_id", ondelete="CASCADE"), nullable=False)
    dragon_id = Column(Integer, ForeignKey("dragons.id", ondelete="CASCADE"), nullable=False)
    completed_at = Column(String, default="")
    next_step_available_at = Column(String, nullable=True, default=None)
    timeout_notified = Column(Boolean, default=False)
    __table_args__ = ()


class ErrorLog(Base):
    __tablename__ = "error_logs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    source = Column(String, default="bot")
    error_type = Column(String, default="")
    message = Column(Text, default="")
    traceback_text = Column(Text, default="")
    user_id = Column(Integer, nullable=True)
    created_at = Column(String, default="")


class ServiceHeartbeat(Base):
    __tablename__ = "service_heartbeats"
    id = Column(Integer, primary_key=True, autoincrement=True)
    service_name = Column(String, unique=True, nullable=False)
    last_seen = Column(String, default="")
    status = Column(String, default="unknown")


class ApiRequestLog(Base):
    __tablename__ = "api_request_logs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    method = Column(String, default="")
    path = Column(String, default="")
    status_code = Column(Integer, default=0)
    client_ip = Column(String, default="")
    created_at = Column(String, default="")


# ─── Копилка / анти-чит ───

class SuspiciousReport(Base):
    __tablename__ = "suspicious_reports"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.vk_id", ondelete="CASCADE"), nullable=False)
    dragon_id = Column(Integer, ForeignKey("dragons.id", ondelete="SET NULL"), nullable=True)
    step_number = Column(Integer, default=0)
    declared_crosses = Column(Integer, default=0)
    normal_crosses = Column(Integer, default=0)
    mode = Column(String, default="norm")
    raw_message = Column(Text, default="")
    photo_before_id = Column(Text, default="")
    photo_after_id = Column(Text, default="")
    status = Column(String, default="pending")
    admin_note = Column(Text, default="")
    created_at = Column(String, default="")


# ─── Магазин ───

class ShopItem(Base):
    __tablename__ = "shop_items"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    description = Column(Text, default="")
    cost_stitches = Column(Integer, default=0)
    category = Column(String, default="")
    image_path = Column(String, default="")
    is_consumable = Column(Boolean, default=True)
    sort_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    is_legend_book = Column(Boolean, default=False)
    is_optional = Column(Boolean, default=False)


class StageShopItem(Base):
    __tablename__ = "stage_shop_items"
    id = Column(Integer, primary_key=True, autoincrement=True)
    stage_key = Column(String, nullable=False)
    item_id = Column(Integer, ForeignKey("shop_items.id", ondelete="CASCADE"), nullable=False)
    sort_order = Column(Integer, default=0)
    __table_args__ = (UniqueConstraint("stage_key", "item_id"),)


class UserInventory(Base):
    __tablename__ = "user_inventory"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.vk_id", ondelete="CASCADE"), nullable=False)
    item_id = Column(Integer, ForeignKey("shop_items.id", ondelete="CASCADE"), nullable=False)
    quantity = Column(Integer, default=1)
    acquired_at = Column(String, default="")
    __table_args__ = (UniqueConstraint("user_id", "item_id"),)


class UserItemUsage(Base):
    __tablename__ = "user_item_usage"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.vk_id", ondelete="CASCADE"), nullable=False)
    item_id = Column(Integer, ForeignKey("shop_items.id", ondelete="CASCADE"), nullable=False)
    user_dragon_id = Column(Integer, ForeignKey("user_dragons.id", ondelete="CASCADE"), nullable=False)
    used_at = Column(String, default="")
    __table_args__ = (UniqueConstraint("user_id", "item_id", "user_dragon_id"),)


# ─── Эпический дракон: общие стадии и уход ───

class EpicStage(Base):
    __tablename__ = "epic_stages"
    id = Column(Integer, primary_key=True, autoincrement=True)
    dragon_id = Column(Integer, ForeignKey("dragons.id", ondelete="CASCADE"), nullable=False)
    stage_number = Column(Integer, nullable=False)
    name = Column(String, default="")
    description = Column(Text, default="")
    image_path = Column(String, default="")
    image_start = Column(String, default="")
    image_end = Column(String, default="")
    cycles_count = Column(Integer, default=3)


class EpicStageAction(Base):
    __tablename__ = "epic_stage_actions"
    id = Column(Integer, primary_key=True, autoincrement=True)
    dragon_id = Column(Integer, ForeignKey("dragons.id", ondelete="CASCADE"), nullable=False)
    stage_id = Column(Integer, ForeignKey("epic_stages.id", ondelete="CASCADE"), nullable=False)
    action_label = Column(String, default="")
    order_in_cycle = Column(Integer, default=0)
    task = Column(Text, default="")
    hint = Column(Text, default="")
    crosses_norm = Column(Integer, default=1000)
    image_path = Column(String, default="")
    action_type = Column(String, default="simple")
    timeout_hours = Column(Integer, default=0)
    timeout_minutes = Column(Integer, default=0)
    random_outcome = Column(Boolean, default=True)
    character_axis_id = Column(Integer, ForeignKey("character_axes.id", ondelete="SET NULL"), nullable=True)
    description = Column(Text, default="")
    confirm_button_label = Column(String, default="")


class EpicActionOutcome(Base):
    __tablename__ = "epic_action_outcomes"
    id = Column(Integer, primary_key=True, autoincrement=True)
    action_id = Column(Integer, ForeignKey("epic_stage_actions.id", ondelete="CASCADE"), nullable=False)
    polarity = Column(String, default="positive")
    label = Column(String, default="")
    moodlet_title = Column(String, default="")
    moodlet_text = Column(Text, default="")
    image_path = Column(String, default="")
    __table_args__ = (UniqueConstraint("action_id", "polarity"),)


class EpicActionItem(Base):
    __tablename__ = "epic_action_items"
    id = Column(Integer, primary_key=True, autoincrement=True)
    action_id = Column(Integer, ForeignKey("epic_stage_actions.id", ondelete="CASCADE"), nullable=False)
    item_id = Column(Integer, ForeignKey("shop_items.id", ondelete="CASCADE"), nullable=False)
    __table_args__ = (UniqueConstraint("action_id", "item_id"),)


class EpicCareState(Base):
    __tablename__ = "epic_care_state"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_dragon_id = Column(Integer, ForeignKey("user_dragons.id", ondelete="CASCADE"), nullable=False)
    stage_id = Column(Integer, ForeignKey("epic_stages.id", ondelete="SET NULL"), nullable=True)
    current_action_order = Column(Integer, default=0)
    current_sub_action_id = Column(Integer, ForeignKey("epic_sub_actions.id", ondelete="SET NULL"), nullable=True)
    current_step_order = Column(Integer, default=0)
    sub_had_penalty = Column(Boolean, default=False)
    next_action_at = Column(String, nullable=True, default=None)
    care_notified = Column(Boolean, default=False)
    cycles_completed = Column(Integer, default=0)


# ─── Характер (оси + баланс) ───

class CharacterAxis(Base):
    __tablename__ = "character_axes"
    id = Column(Integer, primary_key=True, autoincrement=True)
    positive_label = Column(String, default="")
    negative_label = Column(String, default="")
    sort_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)


class CharacterBalance(Base):
    __tablename__ = "character_balance"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_dragon_id = Column(Integer, ForeignKey("user_dragons.id", ondelete="CASCADE"), nullable=False)
    axis_id = Column(Integer, ForeignKey("character_axes.id", ondelete="CASCADE"), nullable=False)
    score = Column(Integer, default=0)
    __table_args__ = (UniqueConstraint("user_dragon_id", "axis_id"),)


# ─── Составные действия (composite) ───

class EpicSubAction(Base):
    __tablename__ = "epic_sub_actions"
    id = Column(Integer, primary_key=True, autoincrement=True)
    action_id = Column(Integer, ForeignKey("epic_stage_actions.id", ondelete="CASCADE"), nullable=False)
    label = Column(String, default="")
    description = Column(Text, default="")
    confirm_button_label = Column(String, default="")
    random_outcome = Column(Boolean, default=True)
    order_in_sub = Column(Integer, default=0)
    image_path = Column(String, default="")
    character_axis_id = Column(Integer, ForeignKey("character_axes.id", ondelete="SET NULL"), nullable=True)
    __table_args__ = (UniqueConstraint("action_id", "label"),)


class EpicSubActionItem(Base):
    __tablename__ = "epic_sub_action_items"
    id = Column(Integer, primary_key=True, autoincrement=True)
    sub_action_id = Column(Integer, ForeignKey("epic_sub_actions.id", ondelete="CASCADE"), nullable=False)
    item_id = Column(Integer, ForeignKey("shop_items.id", ondelete="CASCADE"), nullable=False)
    __table_args__ = (UniqueConstraint("sub_action_id", "item_id"),)


class EpicSubActionStep(Base):
    __tablename__ = "epic_sub_action_steps"
    id = Column(Integer, primary_key=True, autoincrement=True)
    sub_action_id = Column(Integer, ForeignKey("epic_sub_actions.id", ondelete="CASCADE"), nullable=False)
    step_label = Column(String, default="")
    order = Column(Integer, default=0)
    task = Column(Text, default="")
    hint = Column(Text, default="")
    crosses_norm = Column(Integer, default=1000)
    image_path = Column(String, default="")
    timeout_hours = Column(Integer, default=0)
    timeout_minutes = Column(Integer, default=0)


class EpicSubActionOutcome(Base):
    __tablename__ = "epic_sub_action_outcomes"
    id = Column(Integer, primary_key=True, autoincrement=True)
    sub_action_id = Column(Integer, ForeignKey("epic_sub_actions.id", ondelete="CASCADE"), nullable=False)
    polarity = Column(String, default="positive")
    label = Column(String, default="")
    moodlet_title = Column(String, default="")
    moodlet_text = Column(Text, default="")
    image_path = Column(String, default="")
    __table_args__ = (UniqueConstraint("sub_action_id", "polarity"),)


# ─── Эпический дракон: выборы на стадии ───
# DEPRECATED: движок «блоков выбора» убран (решение #14 — характер формируется покупками).
# Таблицы сохранены для обратной совместимости схемы; не используются в коде/роутах/боте.

class StageChoiceBlock(Base):
    __tablename__ = "stage_choice_blocks"
    id = Column(Integer, primary_key=True, autoincrement=True)
    stage_id = Column(Integer, ForeignKey("epic_stages.id", ondelete="CASCADE"), nullable=False)
    block_key = Column(String, default="")
    title = Column(String, default="")
    prompt_text = Column(Text, default="")
    choice_type = Column(String, default="single")
    min_picks = Column(Integer, default=1)
    max_picks = Column(Integer, default=1)
    group_limits = Column(Text, default="{}")
    order_in_stage = Column(Integer, default=0)
    locked_after_done = Column(Boolean, default=True)


class StageChoiceOption(Base):
    __tablename__ = "stage_choice_options"
    id = Column(Integer, primary_key=True, autoincrement=True)
    block_id = Column(Integer, ForeignKey("stage_choice_blocks.id", ondelete="CASCADE"), nullable=False)
    label = Column(String, default="")
    group = Column(String, default="neutral")
    description = Column(Text, default="")
    image_path = Column(String, default="")


class UserStageChoice(Base):
    __tablename__ = "user_stage_choices"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_dragon_id = Column(Integer, ForeignKey("user_dragons.id", ondelete="CASCADE"), nullable=False)
    block_id = Column(Integer, ForeignKey("stage_choice_blocks.id", ondelete="CASCADE"), nullable=False)
    option_id = Column(Integer, ForeignKey("stage_choice_options.id", ondelete="CASCADE"), nullable=False)
    chosen_at = Column(String, default="")


# ─── Эпический дракон: мудлеты ───

class EpicMoodlet(Base):
    __tablename__ = "epic_moodlets"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_dragon_id = Column(Integer, ForeignKey("user_dragons.id", ondelete="CASCADE"), nullable=False)
    key = Column(String, default="")
    title = Column(String, default="")
    polarity = Column(String, default="positive")
    text = Column(Text, default="")
    image_path = Column(String, default="")
    axis_id = Column(Integer, ForeignKey("character_axes.id", ondelete="SET NULL"), nullable=True)
    stage_id = Column(Integer, ForeignKey("epic_stages.id", ondelete="SET NULL"), nullable=True)
    acquired_at = Column(String, default="")


# ─── Сокровища (Фаза 8) ───

class Treasure(Base):
    __tablename__ = "treasures"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    description = Column(Text, default="")
    image_path = Column(String, default="")
    dragon_id = Column(Integer, ForeignKey("dragons.id", ondelete="CASCADE"), unique=True, nullable=True)
    family_id = Column(Integer, ForeignKey("families.id", ondelete="CASCADE"), nullable=True, default=None)
    is_active = Column(Boolean, default=True)


class UserTreasure(Base):
    __tablename__ = "user_treasures"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.vk_id", ondelete="CASCADE"), nullable=False)
    treasure_id = Column(Integer, ForeignKey("treasures.id", ondelete="CASCADE"), nullable=False)
    acquired_at = Column(String, default=lambda: datetime.now().strftime("%Y-%m-%dT%H:%M:%S"))
    __table_args__ = (UniqueConstraint("user_id", "treasure_id"),)


# ─── Robokassa: покупка наборов драконов ───

class PricingConfig(Base):
    __tablename__ = "pricing_config"
    id = Column(Integer, primary_key=True, default=1)
    base_price_per_dragon = Column(Integer, default=10000)
    updated_at = Column(String, default="")


class DragonSet(Base):
    __tablename__ = "dragon_sets"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    quantity = Column(Integer, nullable=False)
    discount_percent = Column(Integer, default=0)
    donor_discount_percent = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(String, default="")


class PaymentOrder(Base):
    __tablename__ = "payment_orders"
    id = Column(Integer, primary_key=True, autoincrement=True)
    vk_id = Column(Integer, ForeignKey("users.vk_id", ondelete="CASCADE"), nullable=False)
    set_id = Column(Integer, ForeignKey("dragon_sets.id", ondelete="SET NULL"), nullable=True)
    amount_rub = Column(Integer, default=0)
    quantity = Column(Integer, default=0)
    price_per_pin = Column(Integer, default=0)
    robokassa_inv_id = Column(Integer, nullable=True)
    status = Column(String(20), default="pending")
    dragon_ids = Column(Text, default="[]")
    notified = Column(Boolean, default=False)
    created_at = Column(String, default="")
    completed_at = Column(String, nullable=True)


# ─── Донат (VK Donut) ───

class DonorCache(Base):
    __tablename__ = "donor_cache"
    vk_id = Column(Integer, primary_key=True)
    is_don = Column(Boolean, default=False)
    don_since = Column(String, nullable=True)
    updated_at = Column(String, default="")
    last_synced_at = Column(String, default="")


class IntroChapter(Base):
    __tablename__ = "intro_chapters"
    id = Column(Integer, primary_key=True, autoincrement=True)
    chapter_number = Column(Integer, nullable=False, unique=True)
    text = Column(Text, default="")
    image_path = Column(String, default="")
    is_active = Column(Boolean, default=True)
