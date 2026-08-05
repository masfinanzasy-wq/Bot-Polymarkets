"""
Esquemas Pydantic para señales de predicción y toma de decisiones probabilísticas.
"""
from enum import Enum
from pydantic import BaseModel, Field
from typing import Optional, List


class SignalType(str, Enum):
    BUY_YES = "BUY_YES"
    BUY_NO = "BUY_NO"
    HOLD = "HOLD"


class PredictionSignal(BaseModel):
    """
    Señal de trading cuantitativa generada por el PredictorEngine.
    """
    market_condition_id: str
    token_id: Optional[str] = None
    outcome: SignalType = SignalType.HOLD
    confidence_score: float = Field(default=0.0, description="Puntuación de 0.0 a 1.0")
    estimated_win_prob: float = Field(default=0.5)
    implied_prob_polymarket: float = Field(default=0.5)
    expected_value_ev: float = Field(default=0.0)
    target_price: float = Field(default=0.0)
    reason: str = Field(default="", description="Explicación detallada y auditable del motivo de la decisión")
    timestamp: float
