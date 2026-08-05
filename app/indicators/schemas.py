"""
Esquemas de datos Pydantic para snapshots de análisis técnico y métricas cuantitativas.
"""
from pydantic import BaseModel, Field
from typing import Optional


class AnalysisSnapshot(BaseModel):
    """
    Snapshot completo de métricas cuantitativas calculadas en tiempo real.
    """
    symbol: str
    last_price: float
    timestamp: float

    # Indicadores Técnicos
    ema_9: Optional[float] = None
    ema_21: Optional[float] = None
    vwap: Optional[float] = None
    rsi_14: Optional[float] = None
    atr_14: Optional[float] = None
    momentum_pct: Optional[float] = None
    volatility_std: Optional[float] = None

    # Order Flow & Volumen
    buy_volume_delta: float = 0.0
    total_volume: float = 0.0
    volume_delta_ratio: float = 0.0  # -1.0 (100% ventas) a +1.0 (100% compras)

    # Probabilidades & Expected Value (EV)
    spot_trend_score: float = 0.0    # -1.0 (Bajista fuerte) a +1.0 (Alcista fuerte)
    estimated_win_prob: float = 0.5  # Probabilidad estadística de terminar UP (0.0 a 1.0)
    implied_prob_polymarket: Optional[float] = None  # Precio del token SÍ en Polymarket
    expected_value_ev: Optional[float] = None         # EV = (P_win * Payout) - Cost
    risk_reward_ratio: Optional[float] = None
