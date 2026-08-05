"""
Script de prueba de integración para el motor de Paper Trading (Modo Sombra) y RiskManager.
Simula ciclo completo: Análisis -> Señal -> Risk Sizing -> Apertura -> Liquidación -> PnL.
"""
import sys
import time
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

from app.indicators.schemas import AnalysisSnapshot
from app.polymarket.schemas import PolymarketMarket, PolymarketToken, PolymarketOrderBook, PolymarketOrderBookLevel
from app.predictors import PredictorEngine
from app.risk import RiskManager
from app.execution import PaperExecutionEngine
from app.logger.logger import sys_logger


def test_paper_trading_pipeline():
    predictor = PredictorEngine(min_ev_threshold=0.05)
    risk = RiskManager(max_position_usd=50.0)
    execution = PaperExecutionEngine(initial_balance=1000.0)

    market = PolymarketMarket(
        condition_id="0xm5_btc_test",
        question="Will Bitcoin be UP in next 5 mins?",
        slug="btc-up-5m",
        liquidity=250.0,
        tokens=[
            PolymarketToken(token_id="yes_tok_99", outcome="Yes"),
            PolymarketToken(token_id="no_tok_99", outcome="No"),
        ]
    )

    yes_book = PolymarketOrderBook(
        token_id="yes_tok_99",
        asks=[PolymarketOrderBookLevel(price=0.45, size=500.0)]
    )

    # --- OPERACIÓN 1: Señal Alcista y Ganadora ---
    sys_logger.info("\n=== INICIANDO OPERACIÓN #1 (BUY_YES -> VICTORIA) ===")
    snapshot1 = AnalysisSnapshot(
        symbol="btcusdt",
        last_price=64200.0,
        timestamp=time.time(),
        spot_trend_score=0.80,
        estimated_win_prob=0.72  # EV = (0.72 * 1.0) - 0.45 = +27%
    )
    sig1 = predictor.evaluate_market(snapshot1, market, yes_book=yes_book)
    size1 = risk.calculate_position_size(sig1, execution.balance, execution.total_realized_pnl)
    
    pos1 = execution.open_position(sig1, size1)
    assert pos1 is not None

    # Simular paso del tiempo y victoria del contrato M5
    execution.settle_position(pos1.id, won=True)

    # --- OPERACIÓN 2: Señal Bajista y Perdedora ---
    sys_logger.info("\n=== INICIANDO OPERACIÓN #2 (BUY_NO -> DERROTA) ===")
    no_book = PolymarketOrderBook(
        token_id="no_tok_99",
        asks=[PolymarketOrderBookLevel(price=0.50, size=500.0)]
    )
    snapshot2 = AnalysisSnapshot(
        symbol="btcusdt",
        last_price=63800.0,
        timestamp=time.time(),
        spot_trend_score=-0.80,
        estimated_win_prob=0.20  # Prob NO = 80% vs Ask NO = 0.50 -> EV = +30%
    )
    sig2 = predictor.evaluate_market(snapshot2, market, no_book=no_book)
    size2 = risk.calculate_position_size(sig2, execution.balance, execution.total_realized_pnl)
    
    pos2 = execution.open_position(sig2, size2)
    assert pos2 is not None

    # Simular derrota del contrato M5
    execution.settle_position(pos2.id, won=False)

    # --- VERIFICAR MÉTRICAS FINALES DE PORTAFOLIO ---
    summary = execution.get_summary()
    sys_logger.info("\n=== RESUMEN FINAL DEL PORTAFOLIO EN PAPER TRADING ===")
    sys_logger.info(f"Balance Inicial: ${summary.initial_balance:,.2f} USD")
    sys_logger.info(f"Balance Actual: ${summary.current_balance:,.2f} USD")
    sys_logger.info(f"PnL Realizado: ${summary.total_realized_pnl:+,.2f} USD")
    sys_logger.info(f"Total de Operaciones: {summary.total_trades} (Ganadas: {summary.winning_trades} | Perdedores: {summary.losing_trades})")
    sys_logger.info(f"Precisión (Win Rate): {summary.win_rate_pct:.1f}%")

    assert summary.total_trades == 2
    assert summary.winning_trades == 1
    assert summary.losing_trades == 1
    assert summary.win_rate_pct == 50.0

if __name__ == "__main__":
    test_paper_trading_pipeline()
