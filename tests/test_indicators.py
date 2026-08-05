"""
Pruebas unitarias del Motor de Indicadores Técnicos (IndicatorsEngine).
"""
import time
import pytest
from app.indicators import IndicatorsEngine
from app.binance.schemas import BinanceTradeTick


def _make_tick(price: float, qty: float = 0.01, buyer_maker: bool = False) -> BinanceTradeTick:
    """Helper que construye un BinanceTradeTick válido para pruebas."""
    return BinanceTradeTick(
        e="aggTrade",
        E=int(time.time() * 1000),
        s="BTCUSDT",
        a=12345,
        p=str(price),
        q=str(qty),
        T=int(time.time() * 1000),
        m=buyer_maker,
    )


class TestIndicatorsEngine:
    """Suite de pruebas unitarias del IndicatorsEngine."""

    def test_initial_state(self, indicators_engine: IndicatorsEngine):
        """El motor debe iniciar sin precios ni EMAs calculadas."""
        assert len(indicators_engine.prices) == 0
        assert indicators_engine._ema_9 is None
        assert indicators_engine._ema_21 is None

    def test_first_tick_initializes_emas(self, indicators_engine: IndicatorsEngine):
        """El primer tick debe inicializar EMA9 y EMA21 con el precio actual."""
        tick = _make_tick(price=60000.0)
        snapshot = indicators_engine.update_tick(tick)
        assert snapshot.ema_9 == 60000.0
        assert snapshot.ema_21 == 60000.0
        assert snapshot.last_price == 60000.0

    def test_ema_converges_toward_price(self, indicators_engine: IndicatorsEngine):
        """Tras múltiples ticks alcistas, EMA9 debe superar a EMA21."""
        for i in range(30):
            tick = _make_tick(price=60000.0 + i * 10.0, qty=0.5, buyer_maker=False)
            snapshot = indicators_engine.update_tick(tick)
        # EMA9 reacciona más rápido → debe ser mayor a EMA21 en tendencia alcista
        assert snapshot.ema_9 > snapshot.ema_21

    def test_vwap_calculated_correctly(self, indicators_engine: IndicatorsEngine):
        """VWAP debe ser el promedio ponderado por volumen."""
        tick1 = _make_tick(price=100.0, qty=1.0)
        tick2 = _make_tick(price=200.0, qty=1.0)
        indicators_engine.update_tick(tick1)
        snap = indicators_engine.update_tick(tick2)
        # VWAP = (100*1 + 200*1) / 2 = 150.0
        assert snap.vwap == pytest.approx(150.0, rel=0.01)

    def test_order_flow_delta_buy_pressure(self, indicators_engine: IndicatorsEngine):
        """Con compras agresivas, el delta_ratio debe ser positivo."""
        for _ in range(10):
            tick = _make_tick(price=63000.0, qty=1.0, buyer_maker=False)  # Taker buyer
            snap = indicators_engine.update_tick(tick)
        assert snap.volume_delta_ratio > 0

    def test_order_flow_delta_sell_pressure(self, indicators_engine: IndicatorsEngine):
        """Con ventas agresivas, el delta_ratio debe ser negativo."""
        for _ in range(10):
            tick = _make_tick(price=63000.0, qty=1.0, buyer_maker=True)  # Taker seller
            snap = indicators_engine.update_tick(tick)
        assert snap.volume_delta_ratio < 0

    def test_rsi_requires_enough_data(self, indicators_engine: IndicatorsEngine):
        """RSI no debe calcularse con menos de 15 ticks."""
        for i in range(10):
            tick = _make_tick(price=63000.0 + i)
            snap = indicators_engine.update_tick(tick)
        assert snap.rsi_14 is None

    def test_rsi_overbought(self, indicators_engine: IndicatorsEngine):
        """RSI debe acercarse a 100 con ticks persistentemente alcistas."""
        for i in range(20):
            tick = _make_tick(price=60000.0 + i * 200.0)
            snap = indicators_engine.update_tick(tick)
        assert snap.rsi_14 > 70

    def test_ev_calculation(self, indicators_engine: IndicatorsEngine):
        """EV = (P_win * 1.0) - Costo. Con P_win=0.72 y costo=0.45, EV = +0.27."""
        tick = _make_tick(price=64000.0)
        snap = indicators_engine.update_tick(tick)
        snap.estimated_win_prob = 0.72
        enriched = indicators_engine.calculate_ev(snap, polymarket_implied_prob=0.45)
        assert enriched.expected_value_ev == pytest.approx(0.27, rel=0.01)

    def test_trend_score_range(self, indicators_engine: IndicatorsEngine):
        """El Spot Trend Score debe estar siempre entre -1.0 y +1.0."""
        for i in range(40):
            tick = _make_tick(price=63000.0 + i * 50)
            snap = indicators_engine.update_tick(tick)
        assert -1.0 <= snap.spot_trend_score <= 1.0
