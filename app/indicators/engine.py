"""
Motor de cálculo de indicadores técnicos cuantitativos y métricas de Expected Value (EV).
"""
import math
import time
from collections import deque
from typing import List, Optional, Deque
from app.binance.schemas import BinanceTradeTick
from app.indicators.schemas import AnalysisSnapshot
from app.logger.logger import sys_logger


class IndicatorsEngine:
    """
    Motor cuantitativo en tiempo real que acumula ticks spot y mantiene
    métricas de EMA, VWAP, RSI, Delta de Volumen, Volatilidad y Expected Value.
    """

    def __init__(self, max_buffer_size: int = 1000):
        self.max_buffer_size = max_buffer_size
        self.prices: Deque[float] = deque(maxlen=max_buffer_size)
        self.volumes: Deque[float] = deque(maxlen=max_buffer_size)
        self.timestamps: Deque[float] = deque(maxlen=max_buffer_size)
        
        # Order flow tracking
        self.buy_volume: float = 0.0
        self.sell_volume: float = 0.0

        # State cache for EMAs
        self._ema_9: Optional[float] = None
        self._ema_21: Optional[float] = None

    def update_tick(self, tick: BinanceTradeTick) -> AnalysisSnapshot:
        """
        Ingesta un tick de Binance en tiempo real y recalcula todo el snapshot técnico.
        """
        price = tick.price_float
        quantity = tick.quantity_float
        now = tick.trade_time / 1000.0 if tick.trade_time > 1e11 else time.time()

        self.prices.append(price)
        self.volumes.append(quantity)
        self.timestamps.append(now)

        # Actualizar order flow delta (Taker Buy vs Taker Sell)
        if not tick.is_buyer_maker:
            self.buy_volume += quantity
        else:
            self.sell_volume += quantity

        # Recalcular EMAs
        self._ema_9 = self._calculate_ema(price, self._ema_9, span=9)
        self._ema_21 = self._calculate_ema(price, self._ema_21, span=21)

        # Recalcular VWAP
        vwap = self._calculate_vwap()

        # Recalcular RSI
        rsi = self._calculate_rsi(period=14)

        # Momentum y Volatilidad
        momentum_pct = self._calculate_momentum(period=10)
        volatility = self._calculate_volatility(period=20)

        # Delta de Volumen
        total_vol = self.buy_volume + self.sell_volume
        delta_ratio = 0.0
        if total_vol > 0:
            delta_ratio = (self.buy_volume - self.sell_volume) / total_vol

        # Trend Score (-1.0 a +1.0)
        trend_score = self._calculate_trend_score(
            price=price,
            ema_9=self._ema_9,
            ema_21=self._ema_21,
            vwap=vwap,
            rsi=rsi,
            delta_ratio=delta_ratio,
        )

        # Estimación de probabilidad estadística de ganar en M5 (0.0 a 1.0)
        estimated_p_win = 0.5 + (trend_score * 0.35)
        estimated_p_win = max(0.05, min(0.95, estimated_p_win))

        return AnalysisSnapshot(
            symbol=tick.symbol,
            last_price=price,
            timestamp=now,
            ema_9=self._ema_9,
            ema_21=self._ema_21,
            vwap=vwap,
            rsi_14=rsi,
            momentum_pct=momentum_pct,
            volatility_std=volatility,
            buy_volume_delta=self.buy_volume - self.sell_volume,
            total_volume=total_vol,
            volume_delta_ratio=delta_ratio,
            spot_trend_score=trend_score,
            estimated_win_prob=estimated_p_win,
        )

    def calculate_ev(self, snapshot: AnalysisSnapshot, polymarket_implied_prob: float) -> AnalysisSnapshot:
        """
        Enriquece el snapshot incorporando la probabilidad implícita de Polymarket y calculando el EV.
        
        Formula: EV = (P_win * 1.00 USD) - Costo (Precio del token SÍ)
        """
        snapshot.implied_prob_polymarket = polymarket_implied_prob
        p_win = snapshot.estimated_win_prob
        cost = polymarket_implied_prob

        if cost > 0:
            # Expected Value neto por cada $1 invertido
            snapshot.expected_value_ev = (p_win * 1.00) - cost
            # Risk Reward = Ganancia Potencial / Riesgo Potencial
            potential_profit = 1.00 - cost
            potential_risk = cost
            snapshot.risk_reward_ratio = potential_profit / potential_risk if potential_risk > 0 else None

        return snapshot

    def _calculate_ema(self, current_price: float, previous_ema: Optional[float], span: int) -> float:
        multiplier = 2.0 / (span + 1.0)
        if previous_ema is None:
            return current_price
        return (current_price - previous_ema) * multiplier + previous_ema

    def _calculate_vwap(self) -> Optional[float]:
        if not self.prices or not self.volumes:
            return None
        sum_pv = sum(p * v for p, v in zip(self.prices, self.volumes))
        sum_v = sum(self.volumes)
        return sum_pv / sum_v if sum_v > 0 else None

    def _calculate_rsi(self, period: int = 14) -> Optional[float]:
        if len(self.prices) < period + 1:
            return None

        prices_list = list(self.prices)[-(period + 1):]
        gains = 0.0
        losses = 0.0

        for i in range(1, len(prices_list)):
            change = prices_list[i] - prices_list[i - 1]
            if change > 0:
                gains += change
            else:
                losses += abs(change)

        avg_gain = gains / period
        avg_loss = losses / period

        if avg_loss == 0:
            return 100.0

        rs = avg_gain / avg_loss
        return 100.0 - (100.0 / (1.0 + rs))

    def _calculate_momentum(self, period: int = 10) -> Optional[float]:
        if len(self.prices) < period:
            return None
        old_price = self.prices[-period]
        current_price = self.prices[-1]
        if old_price == 0:
            return 0.0
        return ((current_price - old_price) / old_price) * 100.0

    def _calculate_volatility(self, period: int = 20) -> Optional[float]:
        if len(self.prices) < period:
            return None
        recent_prices = list(self.prices)[-period:]
        mean = sum(recent_prices) / period
        variance = sum((x - mean) ** 2 for x in recent_prices) / period
        return math.sqrt(variance)

    def _calculate_trend_score(
        self,
        price: float,
        ema_9: Optional[float],
        ema_21: Optional[float],
        vwap: Optional[float],
        rsi: Optional[float],
        delta_ratio: float,
    ) -> float:
        score = 0.0

        # Componente 1: Posición relativa a EMAs
        if ema_9 and ema_21:
            if price > ema_9 > ema_21:
                score += 0.35
            elif price < ema_9 < ema_21:
                score -= 0.35

        # Componente 2: VWAP
        if vwap:
            if price > vwap:
                score += 0.25
            else:
                score -= 0.25

        # Componente 3: Volume Delta Ratio
        score += delta_ratio * 0.25

        # Componente 4: RSI Momentum
        if rsi:
            if rsi > 55:
                score += 0.15
            elif rsi < 45:
                score -= 0.15

        return max(-1.0, min(1.0, score))
