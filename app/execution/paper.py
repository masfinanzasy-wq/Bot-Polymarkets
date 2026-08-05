"""
Motor de ejecución en Modo Sombra (Paper Trading) con simulador de slippage y métricas de PnL.
"""
import time
import uuid
from typing import Dict, List, Optional
from app.execution.schemas import PaperPosition, PositionStatus, PaperPortfolioSummary
from app.predictors.schemas import PredictionSignal, SignalType
from app.logger.logger import sys_logger


class PaperExecutionEngine:
    """
    Simulador de ejecución (Paper Trading) de alta fidelidad.
    
    Registra:
    - Entradas con simulación de slippage y spread.
    - Salidas y liquidación binaria ($1.00 por victoria, $0.00 por derrota).
    - PnL realizado/no realizado.
    - Win Rate, aciertos, errores y trazabilidad auditada de motivos.
    """

    def __init__(self, initial_balance: float = 1000.0, default_slippage: float = 0.005):
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.default_slippage = default_slippage

        self.positions: Dict[str, PaperPosition] = {}
        self.closed_positions: List[PaperPosition] = []

        self.total_realized_pnl: float = 0.0
        self.winning_trades: int = 0
        self.losing_trades: int = 0

    def open_position(
        self,
        signal: PredictionSignal,
        size_usd: float,
        slippage: Optional[float] = None,
    ) -> Optional[PaperPosition]:
        """
        Simula la apertura de una posición en el token correspondiente (YES o NO).
        """
        if size_usd <= 0 or self.balance < size_usd:
            sys_logger.warning(
                f"PaperTrading: Saldo insuficiente (${self.balance:.2f}) para abrir posición de ${size_usd:.2f} USD."
            )
            return None

        if not signal.token_id or signal.outcome == SignalType.HOLD:
            return None

        eff_slippage = slippage if slippage is not None else self.default_slippage
        # Aplicar slippage al precio de entrada
        entry_price = min(0.99, signal.target_price + eff_slippage)
        shares = size_usd / entry_price
        now = time.time()

        position_id = str(uuid.uuid4())[:8]
        position = PaperPosition(
            id=position_id,
            market_condition_id=signal.market_condition_id,
            token_id=signal.token_id,
            outcome=signal.outcome,
            entry_price=entry_price,
            shares=shares,
            cost_usd=size_usd,
            entry_time=now,
            status=PositionStatus.OPEN,
            reason=signal.reason,
        )

        # Descontar costo del saldo disponible
        self.balance -= size_usd
        self.positions[position_id] = position

        sys_logger.info(
            f"PaperTrading: POSICIÓN ABIERTA [{position.outcome.value}] ID={position_id} | "
            f"Costo: ${size_usd:.2f} | Acciones: {shares:.2f} @ ${entry_price:.4f} | Razón: {signal.reason[:60]}..."
        )
        return position

    def settle_position(self, position_id: str, won: bool) -> Optional[PaperPosition]:
        """
        Liquidación binaria de la posición al cierre de la vela M5.
        - Si ganó: exit_price = $1.00 USD por acción.
        - Si perdió: exit_price = $0.00 USD por acción.
        """
        position = self.positions.get(position_id)
        if not position or position.status != PositionStatus.OPEN:
            return None

        now = time.time()
        payout = (position.shares * 1.00) if won else 0.0
        pnl = payout - position.cost_usd
        pnl_pct = (pnl / position.cost_usd) * 100.0 if position.cost_usd > 0 else 0.0

        position.exit_time = now
        position.exit_price = 1.00 if won else 0.00
        position.pnl_usd = round(pnl, 2)
        position.pnl_pct = round(pnl_pct, 2)
        position.status = PositionStatus.CLOSED_WIN if won else PositionStatus.CLOSED_LOSS

        # Actualizar portafolio
        self.balance += payout
        self.total_realized_pnl += pnl

        if won:
            self.winning_trades += 1
        else:
            self.losing_trades += 1

        # Mover a posiciones cerradas
        del self.positions[position_id]
        self.closed_positions.append(position)

        sys_logger.info(
            f"PaperTrading: POSICIÓN CERRADA [{position.status.value}] ID={position_id} | "
            f"Payout: ${payout:.2f} | PnL: ${pnl:+.2f} ({pnl_pct:+.1f}%) | Nuevo Saldo: ${self.balance:.2f}"
        )
        return position

    def get_summary(self) -> PaperPortfolioSummary:
        """
        Retorna las métricas cuantitativas consolidadas del portafolio en Paper Trading.
        """
        total_trades = self.winning_trades + self.losing_trades
        win_rate = (self.winning_trades / total_trades * 100.0) if total_trades > 0 else 0.0

        # PnL no realizado de posiciones abiertas
        unrealized_pnl = 0.0
        for pos in self.positions.values():
            unrealized_pnl += (pos.shares * pos.entry_price) - pos.cost_usd

        return PaperPortfolioSummary(
            initial_balance=self.initial_balance,
            current_balance=round(self.balance, 2),
            total_realized_pnl=round(self.total_realized_pnl, 2),
            total_unrealized_pnl=round(unrealized_pnl, 2),
            total_trades=total_trades,
            winning_trades=self.winning_trades,
            losing_trades=self.losing_trades,
            win_rate_pct=round(win_rate, 1),
            active_positions_count=len(self.positions),
        )
