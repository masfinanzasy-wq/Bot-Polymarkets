"""
Módulo de gestión de riesgo, sizing de posición y límites de protección de capital.
"""
from typing import Optional
from app.config.settings import settings
from app.predictors.schemas import PredictionSignal, SignalType
from app.logger.logger import sys_logger


class RiskManager:
    """
    Controlador de riesgo cuantitativo.
    
    Aplica:
    - Verificación de límites de pérdida diaria acumulada (Max Daily Loss).
    - Dimensionamiento de posición (Kelly Criterium o porcentaje fijo).
    - Límite máximo de exposición por orden.
    """

    def __init__(
        self,
        max_position_usd: float = settings.MAX_POSITION_SIZE_USD,
        max_daily_loss_usd: float = settings.MAX_DAILY_LOSS_USD,
        fractional_kelly: float = 0.25,  # 1/4 Kelly para conservar capital
    ):
        self.max_position_usd = max_position_usd
        self.max_daily_loss_usd = max_daily_loss_usd
        self.fractional_kelly = fractional_kelly

    def calculate_position_size(
        self,
        signal: PredictionSignal,
        current_balance: float,
        current_daily_pnl: float,
    ) -> float:
        """
        Calcula el tamaño de posición en USD que se permite arriesgar.
        Retorna 0.0 si la operación viola las reglas de riesgo.
        """
        # 1. Verificar si alcanzamos el límite de pérdida diaria
        if current_daily_pnl <= -self.max_daily_loss_usd:
            sys_logger.warning(
                f"Riesgo: Límite de pérdida diaria alcanzado (${current_daily_pnl:.2f} <= -${self.max_daily_loss_usd:.2f}). Se cancelan nuevas posiciones."
            )
            return 0.0

        if signal.outcome == SignalType.HOLD or signal.confidence_score <= 0:
            return 0.0

        # 2. Cálculo del Criterio de Kelly
        # b = cuota (Payout / Costo - 1)
        price = signal.target_price if signal.target_price > 0 else 0.50
        b = (1.00 / price) - 1.0
        p = signal.estimated_win_prob
        q = 1.0 - p

        kelly_pct = 0.0
        if b > 0:
            kelly_pct = (b * p - q) / b

        kelly_pct = max(0.0, kelly_pct)
        # Aplicar fracción de Kelly (ej. 25% del valor de Kelly)
        adjusted_pct = kelly_pct * self.fractional_kelly

        # Calcular tamaño recomendado
        size_usd = current_balance * adjusted_pct

        # Topar con el máximo permitido por configuración
        final_size = min(size_usd, self.max_position_usd, current_balance * 0.10)

        sys_logger.debug(
            f"Riesgo Sizing: Kelly Raw = {kelly_pct*100:.1f}% | Kelly Adj = {adjusted_pct*100:.1f}% | Tamaño final = ${final_size:.2f} USD"
        )

        return round(final_size, 2)
