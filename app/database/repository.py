"""
Patrón Repository para la inserción y consulta asíncrona de snapshots, señales y operaciones.
"""
from datetime import datetime
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database.models import MetricSnapshotModel, PredictionSignalModel, TradeRecordModel
from app.indicators.schemas import AnalysisSnapshot
from app.predictors.schemas import PredictionSignal
from app.execution.schemas import PaperPosition
from app.logger.logger import sys_logger


class TradeRepository:
    """
    Repositorio de acceso a datos para persistencia de operaciones, señales y métricas.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def save_metric_snapshot(self, snapshot: AnalysisSnapshot) -> Optional[MetricSnapshotModel]:
        """
        Guarda un snapshot cuantitativo de métricas en la base de datos.
        """
        try:
            db_metric = MetricSnapshotModel(
                symbol=snapshot.symbol,
                last_price=snapshot.last_price,
                ema_9=snapshot.ema_9,
                ema_21=snapshot.ema_21,
                vwap=snapshot.vwap,
                rsi_14=snapshot.rsi_14,
                volume_delta_ratio=snapshot.volume_delta_ratio,
                spot_trend_score=snapshot.spot_trend_score,
                estimated_win_prob=snapshot.estimated_win_prob,
                implied_prob_polymarket=snapshot.implied_prob_polymarket,
                expected_value_ev=snapshot.expected_value_ev,
                timestamp=datetime.fromtimestamp(snapshot.timestamp),
            )
            self.session.add(db_metric)
            await self.session.commit()
            return db_metric
        except Exception as e:
            await self.session.rollback()
            sys_logger.error(f"Error al guardar MetricSnapshot en DB: {e}")
            return None

    async def save_prediction_signal(self, signal: PredictionSignal) -> Optional[PredictionSignalModel]:
        """
        Guarda una señal de predicción generada en la base de datos.
        """
        try:
            db_signal = PredictionSignalModel(
                market_condition_id=signal.market_condition_id,
                token_id=signal.token_id,
                outcome=signal.outcome.value,
                confidence_score=signal.confidence_score,
                estimated_win_prob=signal.estimated_win_prob,
                implied_prob_polymarket=signal.implied_prob_polymarket,
                expected_value_ev=signal.expected_value_ev,
                target_price=signal.target_price,
                reason=signal.reason,
                timestamp=datetime.fromtimestamp(signal.timestamp),
            )
            self.session.add(db_signal)
            await self.session.commit()
            return db_signal
        except Exception as e:
            await self.session.rollback()
            sys_logger.error(f"Error al guardar PredictionSignal en DB: {e}")
            return None

    async def save_or_update_trade(self, position: PaperPosition) -> Optional[TradeRecordModel]:
        """
        Guarda o actualiza una posición/trade en la base de datos.
        """
        try:
            stmt = select(TradeRecordModel).where(TradeRecordModel.position_id == position.id)
            result = await self.session.execute(stmt)
            db_trade = result.scalar_one_or_none()

            opened_dt = datetime.fromtimestamp(position.entry_time)
            closed_dt = datetime.fromtimestamp(position.exit_time) if position.exit_time else None

            if not db_trade:
                db_trade = TradeRecordModel(
                    position_id=position.id,
                    market_condition_id=position.market_condition_id,
                    token_id=position.token_id,
                    outcome=position.outcome.value,
                    entry_price=position.entry_price,
                    exit_price=position.exit_price,
                    shares=position.shares,
                    cost_usd=position.cost_usd,
                    pnl_usd=position.pnl_usd,
                    pnl_pct=position.pnl_pct,
                    status=position.status.value,
                    reason=position.reason,
                    opened_at=opened_dt,
                    closed_at=closed_dt,
                )
                self.session.add(db_trade)
            else:
                db_trade.exit_price = position.exit_price
                db_trade.pnl_usd = position.pnl_usd
                db_trade.pnl_pct = position.pnl_pct
                db_trade.status = position.status.value
                db_trade.closed_at = closed_dt

            await self.session.commit()
            return db_trade
        except Exception as e:
            await self.session.rollback()
            sys_logger.error(f"Error al guardar TradeRecord en DB: {e}")
            return None

    async def get_all_trades(self) -> List[TradeRecordModel]:
        """
        Obtiene el historial de todas las operaciones registradas.
        """
        try:
            stmt = select(TradeRecordModel).order_by(TradeRecordModel.opened_at.desc())
            result = await self.session.execute(stmt)
            return list(result.scalars().all())
        except Exception as e:
            sys_logger.error(f"Error al consultar Trades de DB: {e}")
            return []
