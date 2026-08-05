"""
Pruebas unitarias del Motor de Predicción (PredictorEngine) y señales cuantitativas.
"""
import pytest
from app.predictors import PredictorEngine, SignalType
from app.indicators.schemas import AnalysisSnapshot
from app.polymarket.schemas import PolymarketMarket, PolymarketOrderBook, PolymarketOrderBookLevel


class TestPredictorEngine:
    """Suite de pruebas unitarias del PredictorEngine."""

    def test_generates_buy_yes_on_bullish(
        self, predictor_engine, dummy_market, yes_order_book, no_order_book, bullish_snapshot
    ):
        """En condición alcista fuerte con EV positivo debe emitir BUY_YES."""
        signal = predictor_engine.evaluate_market(bullish_snapshot, dummy_market, yes_order_book, no_order_book)
        assert signal.outcome == SignalType.BUY_YES
        assert signal.confidence_score > 0
        assert signal.expected_value_ev > 0.05

    def test_generates_buy_no_on_bearish(
        self, predictor_engine, dummy_market, yes_order_book, no_order_book, bearish_snapshot
    ):
        """En condición bajista fuerte con EV positivo en NO debe emitir BUY_NO."""
        signal = predictor_engine.evaluate_market(bearish_snapshot, dummy_market, yes_order_book, no_order_book)
        assert signal.outcome == SignalType.BUY_NO
        assert signal.confidence_score > 0
        assert signal.expected_value_ev > 0.05

    def test_hold_when_low_ev(
        self, predictor_engine, dummy_market, yes_order_book, no_order_book
    ):
        """Con EV insuficiente y tendencia neutral debe emitir HOLD."""
        neutral_snapshot = AnalysisSnapshot(
            symbol="btcusdt",
            last_price=63500.0,
            timestamp=0,
            spot_trend_score=0.05,
            estimated_win_prob=0.46,
        )
        signal = predictor_engine.evaluate_market(neutral_snapshot, dummy_market, yes_order_book, no_order_book)
        assert signal.outcome == SignalType.HOLD
        assert signal.confidence_score == 0.0

    def test_hold_when_low_liquidity(
        self, predictor_engine, bullish_snapshot, yes_order_book, no_order_book
    ):
        """Con liquidez por debajo del mínimo debe emitir HOLD por filtro de liquidez."""
        illiquid_market = PolymarketMarket(
            condition_id="0x_illiquid",
            question="Test Market",
            slug="test",
            liquidity=5.0,  # Muy por debajo del mínimo de $50
            tokens=[],
        )
        signal = predictor_engine.evaluate_market(bullish_snapshot, illiquid_market)
        assert signal.outcome == SignalType.HOLD
        assert "Liquidez" in signal.reason

    def test_hold_when_spread_too_high(self, predictor_engine, dummy_market, bullish_snapshot):
        """Con spread excesivo debe rechazar la operación."""
        wide_spread_book = PolymarketOrderBook(
            token_id="yes_tok_fixture",
            bids=[PolymarketOrderBookLevel(price=0.30, size=100.0)],
            asks=[PolymarketOrderBookLevel(price=0.75, size=100.0)],  # Spread = 0.45 >> max_spread
        )
        signal = predictor_engine.evaluate_market(bullish_snapshot, dummy_market, wide_spread_book)
        assert signal.outcome == SignalType.HOLD
        assert "Spread" in signal.reason

    def test_signal_has_reason(self, predictor_engine, dummy_market, yes_order_book, bullish_snapshot):
        """Toda señal debe contener una cadena de razón no vacía para auditoría."""
        signal = predictor_engine.evaluate_market(bullish_snapshot, dummy_market, yes_order_book)
        assert signal.reason != ""
        assert len(signal.reason) > 10

    def test_signal_ev_matches_calculation(
        self, predictor_engine, dummy_market, yes_order_book, bullish_snapshot
    ):
        """EV de la señal = (P_win * 1.0) - Ask_price."""
        signal = predictor_engine.evaluate_market(bullish_snapshot, dummy_market, yes_order_book)
        if signal.outcome == SignalType.BUY_YES:
            expected_ev = (bullish_snapshot.estimated_win_prob * 1.0) - yes_order_book.best_ask
            assert signal.expected_value_ev == pytest.approx(expected_ev, rel=0.01)
