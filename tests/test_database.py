"""
Pruebas de integración asíncronas del repositorio de persistencia en base de datos.
"""
import time
import pytest
from app.database.repository import TradeRepository
from app.indicators.schemas import AnalysisSnapshot
from app.predictors.schemas import PredictionSignal, SignalType
from app.execution.schemas import PaperPosition, PositionStatus


class TestTradeRepository:
    """Pruebas de integración del patrón Repository con SQLite en memoria."""

    async def test_save_and_retrieve_metric_snapshot(self, trade_repository: TradeRepository):
        """Guardar un snapshot y verificar que se persiste correctamente."""
        snap = AnalysisSnapshot(
            symbol="btcusdt",
            last_price=65000.0,
            timestamp=time.time(),
            ema_9=64900.0,
            vwap=64950.0,
            rsi_14=58.0,
            spot_trend_score=0.45,
            estimated_win_prob=0.60,
        )
        result = await trade_repository.save_metric_snapshot(snap)
        assert result is not None
        assert result.id is not None
        assert result.last_price == pytest.approx(65000.0)
        assert result.symbol == "btcusdt"

    async def test_save_prediction_signal(self, trade_repository: TradeRepository):
        """Guardar señal de predicción y verificar integridad."""
        signal = PredictionSignal(
            market_condition_id="0x_db_test_market",
            token_id="tok_yes_db",
            outcome=SignalType.BUY_YES,
            confidence_score=0.90,
            estimated_win_prob=0.68,
            implied_prob_polymarket=0.45,
            expected_value_ev=0.23,
            target_price=0.45,
            reason="Prueba de persistencia de señal",
            timestamp=time.time(),
        )
        result = await trade_repository.save_prediction_signal(signal)
        assert result is not None
        assert result.outcome == "BUY_YES"
        assert result.confidence_score == pytest.approx(0.90)

    async def test_save_open_trade(self, trade_repository: TradeRepository):
        """Guardar trade abierto debe persistir con status OPEN."""
        pos = PaperPosition(
            id="pos_db_test_001",
            market_condition_id="0x_db_test",
            token_id="tok_yes_db",
            outcome=SignalType.BUY_YES,
            entry_price=0.455,
            shares=109.89,
            cost_usd=50.0,
            entry_time=time.time(),
            status=PositionStatus.OPEN,
            reason="Apertura de prueba",
        )
        result = await trade_repository.save_or_update_trade(pos)
        assert result is not None
        assert result.status == "OPEN"
        assert result.position_id == "pos_db_test_001"

    async def test_update_trade_on_settlement(self, trade_repository: TradeRepository):
        """Cerrar un trade debe actualizar el status y PnL correctamente."""
        now = time.time()
        pos = PaperPosition(
            id="pos_settle_001",
            market_condition_id="0x_settle",
            token_id="tok_yes_db",
            outcome=SignalType.BUY_YES,
            entry_price=0.45,
            shares=111.11,
            cost_usd=50.0,
            entry_time=now,
            status=PositionStatus.OPEN,
            reason="Abierta",
        )
        await trade_repository.save_or_update_trade(pos)

        # Simular cierre ganador
        pos.status = PositionStatus.CLOSED_WIN
        pos.exit_price = 1.00
        pos.pnl_usd = 61.11
        pos.pnl_pct = 122.22
        pos.exit_time = now + 300.0

        updated = await trade_repository.save_or_update_trade(pos)
        assert updated.status == "CLOSED_WIN"
        assert updated.pnl_usd == pytest.approx(61.11, rel=0.01)

    async def test_get_all_trades_returns_history(self, trade_repository: TradeRepository):
        """get_all_trades debe retornar todos los trades persistidos."""
        now = time.time()
        for i in range(3):
            pos = PaperPosition(
                id=f"pos_hist_{i:03d}",
                market_condition_id="0x_hist",
                token_id=f"tok_{i}",
                outcome=SignalType.BUY_YES,
                entry_price=0.45,
                shares=100.0,
                cost_usd=45.0,
                entry_time=now + i,
                status=PositionStatus.CLOSED_WIN,
                pnl_usd=55.0,
                reason="Hist test",
            )
            await trade_repository.save_or_update_trade(pos)

        all_trades = await trade_repository.get_all_trades()
        assert len(all_trades) == 3
