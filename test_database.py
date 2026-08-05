"""
Script de prueba de integración para el módulo de Persistencia.
Crea tablas asíncronas, inserta snapshots, señales y operaciones, y las consulta.
"""
import asyncio
import sys
import time
from pathlib import Path
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

sys.path.append(str(Path(__file__).parent))

from app.database import Base, TradeRepository
from app.indicators.schemas import AnalysisSnapshot
from app.predictors.schemas import PredictionSignal, SignalType
from app.execution.schemas import PaperPosition, PositionStatus
from app.logger.logger import sys_logger


async def test_persistence():
    # Usar SQLite asíncrono en memoria para prueba ultrarrápida sin requerir servidor Postgres activo
    test_engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    test_session_factory = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    sys_logger.info("Base de Datos: Tablas creadas en motor de prueba asíncrono.")

    async with test_session_factory() as session:
        repo = TradeRepository(session)

        # 1. Guardar MetricSnapshot
        now = time.time()
        snapshot = AnalysisSnapshot(
            symbol="btcusdt",
            last_price=63950.0,
            timestamp=now,
            ema_9=63900.0,
            ema_21=63850.0,
            vwap=63920.0,
            rsi_14=62.5,
            volume_delta_ratio=0.45,
            spot_trend_score=0.65,
            estimated_win_prob=0.68,
            implied_prob_polymarket=0.46,
            expected_value_ev=0.22,
        )
        saved_snap = await repo.save_metric_snapshot(snapshot)
        assert saved_snap is not None
        sys_logger.info(f"DB: Snapshot de métricas guardado exitosamente (ID: {saved_snap.id})")

        # 2. Guardar PredictionSignal
        signal = PredictionSignal(
            market_condition_id="0x_test_cond_123",
            token_id="tok_yes_777",
            outcome=SignalType.BUY_YES,
            confidence_score=0.85,
            estimated_win_prob=0.68,
            implied_prob_polymarket=0.46,
            expected_value_ev=0.22,
            target_price=0.46,
            reason="Compra SÍ probada por EV +22%",
            timestamp=now,
        )
        saved_sig = await repo.save_prediction_signal(signal)
        assert saved_sig is not None
        sys_logger.info(f"DB: Señal de predicción guardada exitosamente (ID: {saved_sig.id})")

        # 3. Guardar y actualizar TradeRecord
        pos = PaperPosition(
            id="pos_trade_999",
            market_condition_id="0x_test_cond_123",
            token_id="tok_yes_777",
            outcome=SignalType.BUY_YES,
            entry_price=0.465,
            shares=107.52,
            cost_usd=50.0,
            entry_time=now,
            status=PositionStatus.OPEN,
            reason=signal.reason,
        )
        saved_trade = await repo.save_or_update_trade(pos)
        assert saved_trade is not None
        sys_logger.info(f"DB: Posición de Trade creada (Status: {saved_trade.status})")

        # Simular cierre de posición
        pos.exit_price = 1.00
        pos.pnl_usd = 57.52
        pos.pnl_pct = 115.04
        pos.status = PositionStatus.CLOSED_WIN
        pos.exit_time = time.time()

        updated_trade = await repo.save_or_update_trade(pos)
        assert updated_trade.status == "CLOSED_WIN"
        sys_logger.info(f"DB: Posición de Trade actualizada a CLOSED_WIN (PnL: +${updated_trade.pnl_usd:.2f})")

        # 4. Consultar historial de operaciones
        all_trades = await repo.get_all_trades()
        assert len(all_trades) == 1
        sys_logger.info(f"DB: Consulta de trades históricos completada. Total registros: {len(all_trades)}")

    await test_engine.dispose()
    sys_logger.info("Prueba de Persistencia completada exitosamente!")

if __name__ == "__main__":
    asyncio.run(test_persistence())
