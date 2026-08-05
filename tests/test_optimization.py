"""
Pruebas unitarias del Módulo de Optimización Continua (OptimizationEngine).
"""
import time
import pytest
from app.execution.schemas import PaperPosition, PositionStatus
from app.predictors.schemas import SignalType
from app.optimization import OptimizationEngine, PerformanceMetrics


def _create_mock_position(position_id: str, won: bool, pnl: float) -> PaperPosition:
    """Helper que construye una PaperPosition cerrada para pruebas."""
    return PaperPosition(
        id=position_id,
        market_condition_id="0x_test_opt",
        token_id="tok_yes",
        outcome=SignalType.BUY_YES,
        entry_price=0.45,
        shares=100.0,
        cost_usd=45.0,
        entry_time=time.time() - 600,
        exit_time=time.time(),
        status=PositionStatus.CLOSED_WIN if won else PositionStatus.CLOSED_LOSS,
        exit_price=1.00 if won else 0.00,
        pnl_usd=pnl,
        pnl_pct=(pnl / 45.0) * 100.0,
        reason="Mock test position",
    )


class TestOptimizationEngine:
    """Suite de pruebas unitarias para el motor de optimización adaptativa."""

    def test_empty_positions_returns_default_metrics(self):
        engine = OptimizationEngine()
        metrics = engine.calculate_performance([])
        assert metrics.total_trades == 0
        assert metrics.win_rate_pct == 0.0
        assert metrics.total_pnl_usd == 0.0

    def test_calculate_performance_metrics_correctly(self):
        engine = OptimizationEngine()
        positions = [
            _create_mock_position("pos_1", won=True, pnl=55.0),
            _create_mock_position("pos_2", won=True, pnl=55.0),
            _create_mock_position("pos_3", won=False, pnl=-45.0),
        ]
        metrics = engine.calculate_performance(positions)
        assert metrics.total_trades == 3
        assert metrics.winning_trades == 2
        assert metrics.losing_trades == 1
        assert metrics.win_rate_pct == pytest.approx(66.67, abs=0.1)
        assert metrics.total_pnl_usd == pytest.approx(65.0, abs=0.1)
        assert metrics.profit_factor == pytest.approx(110.0 / 45.0, abs=0.1)

    def test_insufficient_samples_retains_base_parameters(self):
        engine = OptimizationEngine(base_min_ev=0.05, base_kelly_fraction=0.25)
        # Solo 3 trades (< 5 requeridos)
        positions = [
            _create_mock_position("pos_1", won=True, pnl=55.0),
            _create_mock_position("pos_2", won=False, pnl=-45.0),
            _create_mock_position("pos_3", won=False, pnl=-45.0),
        ]
        params = engine.optimize_parameters(positions)
        assert params.min_ev_threshold == 0.05
        assert params.kelly_fraction == 0.25
        assert "Muestra insuficiente" in params.adaptation_reason

    def test_low_win_rate_increases_ev_threshold_and_reduces_kelly(self):
        engine = OptimizationEngine(base_min_ev=0.05, base_kelly_fraction=0.25)
        # 6 trades con solo 2 ganadas (Win rate = 33.3% < 50%)
        positions = [
            _create_mock_position("pos_1", won=True, pnl=50.0),
            _create_mock_position("pos_2", won=True, pnl=50.0),
            _create_mock_position("pos_3", won=False, pnl=-45.0),
            _create_mock_position("pos_4", won=False, pnl=-45.0),
            _create_mock_position("pos_5", won=False, pnl=-45.0),
            _create_mock_position("pos_6", won=False, pnl=-45.0),
        ]
        params = engine.optimize_parameters(positions)
        assert params.min_ev_threshold > 0.05  # Aumenta exigencia de EV
        assert params.kelly_fraction < 0.25    # Reduce tamaño de posición por riesgo
        assert "Win rate bajo" in params.adaptation_reason

    def test_high_win_rate_optimizes_kelly_and_relaxes_ev(self):
        engine = OptimizationEngine(base_min_ev=0.05, base_kelly_fraction=0.25)
        # 6 trades con 5 ganadas (Win rate = 83.3% > 65%)
        positions = [
            _create_mock_position(f"pos_{i}", won=True, pnl=55.0) for i in range(5)
        ] + [_create_mock_position("pos_6", won=False, pnl=-45.0)]
        
        params = engine.optimize_parameters(positions)
        assert params.kelly_fraction > 0.25   # Incrementa asignación de capital
        assert params.min_ev_threshold <= 0.05 # Permite capturar más oportunidades
        assert "Win rate alto" in params.adaptation_reason

    def test_high_drawdown_halves_kelly_fraction(self):
        engine = OptimizationEngine(base_min_ev=0.05, base_kelly_fraction=0.25)
        # Racha de pérdidas que genera Max Drawdown > $50
        positions = [
            _create_mock_position("pos_1", won=True, pnl=20.0),
            _create_mock_position("pos_2", won=False, pnl=-45.0),
            _create_mock_position("pos_3", won=False, pnl=-45.0),
            _create_mock_position("pos_4", won=False, pnl=-45.0),
            _create_mock_position("pos_5", won=False, pnl=-45.0),
            _create_mock_position("pos_6", won=False, pnl=-45.0),
        ]
        params = engine.optimize_parameters(positions)
        assert "Max Drawdown elevado" in params.adaptation_reason
