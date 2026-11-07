import hmac

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

import config
from db import get_db
from services.external_rewards import ExternalRewardError, grant_random_egg, revoke_egg

router = APIRouter(prefix="/api/internal/rewards", tags=["internal-rewards"])


class EggGrantIn(BaseModel):
    vk_id: int = Field(gt=0)
    external_reward_id: str = Field(min_length=1, max_length=200)


class EggRevokeIn(BaseModel):
    external_reward_id: str = Field(min_length=1, max_length=200)


def require_integration_key(x_integration_key: str = Header(default="")):
    if not config.HOLIDAYS_INTEGRATION_KEY:
        raise HTTPException(status_code=503, detail="Интеграция не настроена")
    if not hmac.compare_digest(x_integration_key, config.HOLIDAYS_INTEGRATION_KEY):
        raise HTTPException(status_code=403, detail="Неверный ключ интеграции")


@router.post("/dragon-egg", dependencies=[Depends(require_integration_key)])
def grant_egg(data: EggGrantIn, db: Session = Depends(get_db)):
    try:
        return grant_random_egg(db, data.vk_id, data.external_reward_id.strip())
    except ExternalRewardError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail)


@router.post("/dragon-egg/revoke", dependencies=[Depends(require_integration_key)])
def revoke(data: EggRevokeIn, db: Session = Depends(get_db)):
    try:
        return revoke_egg(db, data.external_reward_id.strip())
    except ExternalRewardError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail)
