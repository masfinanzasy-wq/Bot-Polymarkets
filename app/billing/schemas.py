"""
Esquemas Pydantic para el módulo de billing, checkout y gestión de membresías SaaS.
"""
from enum import Enum
from pydantic import BaseModel
from typing import List, Optional


class PlanTier(str, Enum):
    STARTER = "STARTER"
    PRO = "PRO"
    WHALE = "WHALE"


class PlanInfo(BaseModel):
    tier: PlanTier
    name: str
    price_usd: float
    max_capital_usd: float
    features: List[str]
    is_popular: bool = False


class CheckoutRequest(BaseModel):
    plan_tier: PlanTier
    payment_method: str = "stripe"  # "stripe" o "crypto_usdc"


class CheckoutResponse(BaseModel):
    success: bool
    checkout_url: str
    session_id: str
    plan_tier: PlanTier
    message: str
