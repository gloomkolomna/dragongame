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
    __table_args__ = (UniqueConstraint("user_id", "dragon_id", "step_number"),)


class UserDragon(Base):
    __tablename__ = "user_dragons"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.vk_id", ondelete="CASCADE"), nullable=False)
    dragon_id = Column(Integer, ForeignKey("dragons.id", ondelete="CASCADE"), nullable=False)
    completed_at = Column(String, default="")
    next_step_available_at = Column(String, nullable=True, default=None)
    timeout_notified = Column(Boolean, default=False)
    __table_args__ = (UniqueConstraint("user_id", "dragon_id"),)


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


class ApiRequestLog(Base):
    __tablename__ = "api_request_logs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    method = Column(String, default="")
    path = Column(String, default="")
    status_code = Column(Integer, default=0)
    client_ip = Column(String, default="")
    created_at = Column(String, default="")
    service_name = Column(String, unique=True, nullable=False)
    last_seen = Column(String, default="")
    status = Column(String, default="unknown")
