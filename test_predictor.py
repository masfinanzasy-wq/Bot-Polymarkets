"""
Script de prueba de unidad e integración para el PredictorEngine.
Prueba condiciones Alcistas (BUY_YES), Bajistas (BUY_NO) y Neutrales (HOLD).
"""
import sys
import time
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

from app.indicators.schemas import AnalysisSnapshot
from app.polymarket.schemas import PolymarketMarket, PolymarketToken, PolymarketOrderBook, PolymarketOrderBookLevel
from app.predictors import PredictorEngine, SignalType
from app.logger.logger import sys_logger


def test_predictor_engine():
    predictor = PredictorEngine(min_ev_threshold=0.05, min_liquidity=50.0)

    # Crear mercado simulado M5
    dummy_market = PolymarketMarket(
        condition_id="0xabc123",
        question="Will BTC be higher in 5 mins?",
        slug="btc-up-5m",
        liquidity=500.0,
        volume=2500.0,
        tokens=[
            PolymarketToken(token_id="tok_yes_123", outcome="Yes"),
            PolymarketToken(token_id="tok_no_123", outcome="No"),
        ]
    )

    # Libros de órdenes simulados (Ask YES = $0.45, Ask NO = $0.55)
    yes_book = PolymarketOrderBook(
        token_id="tok_yes_123",
        bids=[PolymarketOrderBookLevel(price=0.43, size=100.0)],
        asks=[PolymarketOrderBookLevel(price=0.45, size=100.0)]
    )

    no_book = PolymarketOrderBook(
        token_id="tok_no_123",
        bids=[PolymarketOrderBookLevel(price=0.53, size=100.0)],
        asks=[PolymarketOrderBookLevel(price=0.55, size=100.0)]
    )

    sys_logger.info("=== CASO 1: CONDICIÓN ALCISTA FUERTE (BUY_YES) ===")
    bullish_snapshot = AnalysisSnapshot(
        symbol="btcusdt",
        last_price=64000.0,
        timestamp=time.time(),
        spot_trend_score=0.75,
        estimated_win_prob=0.70  # 70% prob vs 45 centavos costo -> EV = +25%
    )
    sig1 = predictor.evaluate_market(bullish_snapshot, dummy_market, yes_book, no_book)
    sys_logger.info(f"Resultado: {sig1.outcome.value} | Confianza: {sig1.confidence_score:.2f} | EV: {sig1.expected_value_ev*100:+.1f}%")
    sys_logger.info(f"Razon: {sig1.reason}\n")
    assert sig1.outcome == SignalType.BUY_YES

    sys_logger.info("=== CASO 2: CONDICIÓN BAJISTA FUERTE (BUY_NO) ===")
    bearish_snapshot = AnalysisSnapshot(
        symbol="btcusdt",
        last_price=63000.0,
        timestamp=time.time(),
        spot_trend_score=-0.75,
        estimated_win_prob=0.25  # 25% prob YES -> 75% prob NO vs 55 centavos costo NO -> EV = +20%
    )
    sig2 = predictor.evaluate_market(bearish_snapshot, dummy_market, yes_book, no_book)
    sys_logger.info(f"Resultado: {sig2.outcome.value} | Confianza: {sig2.confidence_score:.2f} | EV: {sig2.expected_value_ev*100:+.1f}%")
    sys_logger.info(f"Razon: {sig2.reason}\n")
    assert sig2.outcome == SignalType.BUY_NO

    sys_logger.info("=== CASO 3: SIN VENTAJA ESTADÍSTICA SUFICIENTE (HOLD) ===")
    neutral_snapshot = AnalysisSnapshot(
        symbol="btcusdt",
        last_price=63500.0,
        timestamp=time.time(),
        spot_trend_score=0.10,
        estimated_win_prob=0.47  # EV insuficiente
    )
    sig3 = predictor.evaluate_market(neutral_snapshot, dummy_market, yes_book, no_book)
    sys_logger.info(f"Resultado: {sig3.outcome.value} | EV: {sig3.expected_value_ev*100:+.1f}%")
    sys_logger.info(f"Razon: {sig3.reason}\n")
    assert sig3.outcome == SignalType.HOLD

    sys_logger.info("Todas las pruebas unitarias del PredictorEngine pasaron exitosamente!")

if __name__ == "__main__":
    test_predictor_engine()
