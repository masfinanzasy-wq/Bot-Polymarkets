"""
Pruebas unitarias del motor de Paper Trading y Risk Manager.
"""
import pytest
from app.execution import PaperExecutionEngine
from app.execution.schemas import PositionStatus
from app.risk import RiskManager
from app.predictors.schemas import PredictionSignal, SignalType
import time


def _make_buy_yes_signal(ev: float = 0.20, confidence: float = 0.80) -> PredictionSignal:
    return PredictionSignal(
        market_condition_id="0x_test",
        token_id="tok_yes",
        outcome=SignalType.BUY_YES,
        confidence_score=confidence,
        estimated_win_prob=0.65,
        implied_prob_polymarket=0.45,
        expected_value_ev=ev,
        target_price=0.45,
        reason="Señal de prueba BUY_YES",
        timestamp=time.time(),
    )


class TestRiskManager:
    """Pruebas del módulo de gestión de riesgo."""

    def test_kelly_returns_positive_size(self, risk_manager: RiskManager):
        """Con señal de alta confianza debe retornar un tamaño de posición positivo."""
        signal = _make_buy_yes_signal()
        size = risk_manager.calculate_position_size(signal, 1000.0, 0.0)
        assert size > 0

    def test_max_position_cap_respected(self, risk_manager: RiskManager):
        """El tamaño de posición nunca debe superar MAX_POSITION_SIZE_USD."""
        signal = _make_buy_yes_signal()
        size = risk_manager.calculate_position_size(signal, 10000.0, 0.0)
        assert size <= risk_manager.max_position_usd

    def test_returns_zero_on_hold_signal(self, risk_manager: RiskManager):
        """Señal HOLD debe retornar size=0 (no operar)."""
        hold_signal = PredictionSignal(
            market_condition_id="0x_test",
            outcome=SignalType.HOLD,
            confidence_score=0.0,
            estimated_win_prob=0.50,
            implied_prob_polymarket=0.50,
            expected_value_ev=0.0,
            target_price=0.0,
            reason="HOLD",
            timestamp=time.time(),
        )
        size = risk_manager.calculate_position_size(hold_signal, 1000.0, 0.0)
        assert size == 0.0

    def test_daily_loss_limit_blocks_trading(self, risk_manager: RiskManager):
        """Al superar el límite de pérdida diaria, el sizing debe retornar 0."""
        signal = _make_buy_yes_signal()
        # current_daily_pnl = -250 <= -max_daily_loss_usd (-200)
        size = risk_manager.calculate_position_size(signal, 1000.0, current_daily_pnl=-250.0)
        assert size == 0.0


class TestPaperExecutionEngine:
    """Pruebas del motor de simulación de ejecución."""

    def test_open_position_reduces_balance(self, paper_engine: PaperExecutionEngine):
        """Abrir posición debe descontar costo del saldo disponible."""
        signal = _make_buy_yes_signal()
        initial_balance = paper_engine.balance
        paper_engine.open_position(signal, size_usd=50.0)
        assert paper_engine.balance == pytest.approx(initial_balance - 50.0, rel=0.01)

    def test_win_increases_balance(self, paper_engine: PaperExecutionEngine):
        """Una victoria debe incrementar el saldo con el payout completo."""
        signal = _make_buy_yes_signal()
        pos = paper_engine.open_position(signal, size_usd=50.0)
        balance_before = paper_engine.balance
        closed = paper_engine.settle_position(pos.id, won=True)
        assert closed.status == PositionStatus.CLOSED_WIN
        assert paper_engine.balance > balance_before  # Ganamos más de lo que tenemos

    def test_loss_does_not_recover_cost(self, paper_engine: PaperExecutionEngine):
        """Una derrota no debe devolver el costo de entrada."""
        signal = _make_buy_yes_signal()
        balance_before_open = paper_engine.balance
        pos = paper_engine.open_position(signal, size_usd=50.0)
        closed = paper_engine.settle_position(pos.id, won=False)
        assert closed.pnl_usd == pytest.approx(-50.0, rel=0.01)
        assert paper_engine.balance == pytest.approx(balance_before_open - 50.0, rel=0.01)

    def test_win_rate_tracking(self, paper_engine: PaperExecutionEngine):
        """El win rate debe calcularse correctamente con 3 ganadas de 4."""
        signal = _make_buy_yes_signal()
        for won in [True, True, True, False]:
            pos = paper_engine.open_position(signal, size_usd=10.0)
            paper_engine.settle_position(pos.id, won=won)
        summary = paper_engine.get_summary()
        assert summary.total_trades == 4
        assert summary.winning_trades == 3
        assert summary.win_rate_pct == pytest.approx(75.0, rel=0.01)

    def test_summary_initial_state(self, paper_engine: PaperExecutionEngine):
        """El resumen inicial debe reflejar el saldo de partida sin operaciones."""
        summary = paper_engine.get_summary()
        assert summary.initial_balance == 1000.0
        assert summary.current_balance == 1000.0
        assert summary.total_trades == 0
        assert summary.win_rate_pct == 0.0
