"""
Esquemas de datos para el Módulo de Optimización Continua y Aprendizaje.
"""
from pydantic import BaseModel, Field
import time


class PerformanceMetrics(BaseModel):
    """Métricas cuantitativas del historial de operaciones pasadas."""
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate_pct: float = 0.0
    total_pnl_usd: float = 0.0
    profit_factor: float = 0.0
    avg_trade_pnl_usd: float = 0.0
    max_drawdown_usd: float = 0.0


class AdaptiveParameters(BaseModel):
    """Parámetros dinámicos optimizados automáticamente según el rendimiento."""
    min_ev_threshold: float = Field(default=0.05, description="Umbral mínimo de EV requerido")
    kelly_fraction: float = Field(default=0.25, description="Fracción de Kelly aplicada")
    max_spread_allowed: float = Field(default=0.10, description="Spread máximo tolerado en el libro de órdenes")
    min_liquidity_usd: float = Field(default=50.0, description="Liquidez mínima requerida")
    last_updated: float = Field(default_factory=time.time)
    adaptation_reason: str = Field(default="Parámetros iniciales por defecto")
