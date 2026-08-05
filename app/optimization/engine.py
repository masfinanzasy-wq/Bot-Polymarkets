"""
Motor de Optimización Continua y Aprendizaje adaptativo de parámetros.
Analiza el historial de operaciones y ajusta dinámicamente el riesgo y los umbrales de predicción.
"""
from typing import Sequence
from app.execution.schemas import PaperPosition, PositionStatus
from app.optimization.schemas import PerformanceMetrics, AdaptiveParameters
from app.logger.logger import sys_logger


class OptimizationEngine:
    """
    Motor que ajusta dinámicamente parámetros clave (EV mínimo, Fracción de Kelly, etc.)
    en función del Win Rate, Drawdown y Profit Factor observados en ejecuciones pasadas.
    """

    def __init__(
        self,
        base_min_ev: float = 0.05,
        base_kelly_fraction: float = 0.25,
        target_win_rate: float = 0.60,
    ):
        self.base_min_ev = base_min_ev
        self.base_kelly_fraction = base_kelly_fraction
        self.target_win_rate = target_win_rate

    def calculate_performance(self, positions: Sequence[PaperPosition]) -> PerformanceMetrics:
        """
        Calcula las métricas cuantitativas clave a partir de una lista de posiciones cerradas.
        """
        closed_positions = [p for p in positions if p.status in (PositionStatus.CLOSED_WIN, PositionStatus.CLOSED_LOSS)]
        total = len(closed_positions)
        if total == 0:
            return PerformanceMetrics()

        wins = sum(1 for p in closed_positions if p.status == PositionStatus.CLOSED_WIN)
        losses = total - wins
        win_rate = (wins / total) * 100.0

        gross_profit = sum(p.pnl_usd for p in closed_positions if p.pnl_usd > 0)
        gross_loss = abs(sum(p.pnl_usd for p in closed_positions if p.pnl_usd < 0))
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else (gross_profit if gross_profit > 0 else 1.0)

        total_pnl = sum(p.pnl_usd for p in closed_positions)
        avg_pnl = total_pnl / total

        # Cálculo de Max Drawdown acumulado
        peak = 0.0
        current_cum = 0.0
        max_dd = 0.0
        for p in closed_positions:
            current_cum += p.pnl_usd
            if current_cum > peak:
                peak = current_cum
            dd = peak - current_cum
            if dd > max_dd:
                max_dd = dd

        return PerformanceMetrics(
            total_trades=total,
            winning_trades=wins,
            losing_trades=losses,
            win_rate_pct=round(win_rate, 2),
            total_pnl_usd=round(total_pnl, 2),
            profit_factor=round(profit_factor, 2),
            avg_trade_pnl_usd=round(avg_pnl, 2),
            max_drawdown_usd=round(max_dd, 2),
        )

    def optimize_parameters(self, positions: Sequence[PaperPosition]) -> AdaptiveParameters:
        """
        Genera un nuevo conjunto de parámetros adaptativos según las métricas históricas.
        Reglas de adaptación:
        1. Si Win Rate < 50% (rendimiento bajo): Aumenta el EV mínimo exigido y reduce la fracción de Kelly.
        2. Si Win Rate > 65% (rendimiento superior): Mantiene/reduce ligeramente el EV mínimo para capturar más trades y aumentar Kelly.
        3. Si Max Drawdown es alto (> $50 USD): Reduce el Kelly a la mitad por seguridad.
        """
        metrics = self.calculate_performance(positions)
        
        # Con pocas operaciones (< 5), mantenemos valores base por precaución
        if metrics.total_trades < 5:
            return AdaptiveParameters(
                min_ev_threshold=self.base_min_ev,
                kelly_fraction=self.base_kelly_fraction,
                adaptation_reason=f"Muestra insuficiente ({metrics.total_trades}/5 trades). Usando parametros base.",
            )

        new_min_ev = self.base_min_ev
        new_kelly = self.base_kelly_fraction
        reasons = []

        win_rate_dec = metrics.win_rate_pct / 100.0

        # Regla 1: Win rate bajo -> Exigir mayor EV para operar
        if win_rate_dec < 0.50:
            new_min_ev = max(self.base_min_ev * 1.5, 0.08)
            new_kelly = self.base_kelly_fraction * 0.6
            reasons.append(f"Win rate bajo ({metrics.win_rate_pct}%): EV sube a {new_min_ev:.2f}, Kelly baja a {new_kelly:.2f}")

        # Regla 2: Win rate alto -> Optimizar volumen capturando buenas oportunidades
        elif win_rate_dec >= 0.65:
            new_min_ev = max(self.base_min_ev * 0.9, 0.04)
            new_kelly = min(self.base_kelly_fraction * 1.25, 0.40)
            reasons.append(f"Win rate alto ({metrics.win_rate_pct}%): EV ajustado a {new_min_ev:.2f}, Kelly sube a {new_kelly:.2f}")

        # Regla 3: Protección ante Drawdown
        if metrics.max_drawdown_usd > 50.0:
            new_kelly = new_kelly * 0.5
            reasons.append(f"Max Drawdown elevado (${metrics.max_drawdown_usd}): Kelly reducido 50% por seguridad")

        final_reason = " | ".join(reasons) if reasons else "Rendimiento estable. Parametros dentro de rango optimo."
        
        sys_logger.info(f"Optimizacion de parametros completada: EV={new_min_ev:.3f}, Kelly={new_kelly:.3f}")
        return AdaptiveParameters(
            min_ev_threshold=round(new_min_ev, 3),
            kelly_fraction=round(new_kelly, 3),
            adaptation_reason=final_reason,
        )
