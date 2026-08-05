"""
Esquemas Pydantic para el motor de Paper Trading y métricas de portafolio simulado.
"""
from enum import Enum
from pydantic import BaseModel, Field
from typing import List, Optional
from app.predictors.schemas import SignalType


class PositionStatus(str, Enum):
    OPEN = "OPEN"
    CLOSED_WIN = "CLOSED_WIN"
    CLOSED_LOSS = "CLOSED_LOSS"


class PaperPosition(BaseModel):
    """
    Representa una posición virtual en el modo Paper Trading.
    """
    id: str
    market_condition_id: str
    token_id: str
    outcome: SignalType
    entry_price: float
    shares: float
    cost_usd: float
    entry_time: float
    exit_time: Optional[float] = None
    exit_price: Optional[float] = None
    pnl_usd: float = 0.0
    pnl_pct: float = 0.0
    status: PositionStatus = PositionStatus.OPEN
    reason: str = ""


class PaperPortfolioSummary(BaseModel):
    """
    Resumen de rendimiento del portafolio en Paper Trading.
    """
    initial_balance: float = 1000.0
    current_balance: float = 1000.0
    total_realized_pnl: float = 0.0
    total_unrealized_pnl: float = 0.0
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate_pct: float = 0.0
    active_positions_count: int = 0
