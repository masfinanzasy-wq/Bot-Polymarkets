"""
Motor de predicción cuantitativa que evalúa señales múltiples, filtros de liquidez/spread y EV.
"""
import time
from typing import Optional
from app.config.settings import settings
from app.indicators.schemas import AnalysisSnapshot
from app.polymarket.schemas import PolymarketMarket, PolymarketOrderBook
from app.predictors.schemas import PredictionSignal, SignalType
from app.logger.logger import sys_logger


class PredictorEngine:
    """
    Motor cuantitativo que combina reglas estadísticas, filtros de riesgo/liquidez
    y modelos de Expected Value para emitir señales de compra (YES/NO) o mantener (HOLD).
    """

    def __init__(
        self,
        min_ev_threshold: float = settings.MIN_EXPECTED_VALUE,
        max_spread: float = 0.10,  # Spread máximo de 10 centavos
        min_liquidity: float = 50.0,
    ):
        self.min_ev_threshold = min_ev_threshold
        self.max_spread = max_spread
        self.min_liquidity = min_liquidity

    def evaluate_market(
        self,
        snapshot: AnalysisSnapshot,
        market: PolymarketMarket,
        yes_book: Optional[PolymarketOrderBook] = None,
        no_book: Optional[PolymarketOrderBook] = None,
    ) -> PredictionSignal:
        """
        Evalúa un mercado M5 combinando el snapshot spot y los libros de órdenes del CLOB.
        """
        now = time.time()
        condition_id = market.condition_id

        # 1. Filtro de liquidez básica
        if market.liquidity < self.min_liquidity:
            return PredictionSignal(
                market_condition_id=condition_id,
                outcome=SignalType.HOLD,
                confidence_score=0.0,
                reason=f"Filtro Rechazado: Liquidez (${market.liquidity:.2f}) menor al mínimo (${self.min_liquidity:.2f})",
                timestamp=now,
            )

        yes_token = market.yes_token
        no_token = market.no_token

        if not yes_token or not no_token:
            return PredictionSignal(
                market_condition_id=condition_id,
                outcome=SignalType.HOLD,
                confidence_score=0.0,
                reason="Filtro Rechazado: Falta token de resultado YES o NO en el mercado",
                timestamp=now,
            )

        # Precios de compra en el CLOB (Best Ask)
        yes_ask = yes_book.best_ask if yes_book and yes_book.best_ask else 0.50
        no_ask = no_book.best_ask if no_book and no_book.best_ask else (1.0 - yes_ask)

        # Verificación de Spread de YES
        if yes_book and yes_book.best_bid and yes_book.best_ask:
            yes_spread = yes_book.best_ask - yes_book.best_bid
            if yes_spread > self.max_spread:
                return PredictionSignal(
                    market_condition_id=condition_id,
                    outcome=SignalType.HOLD,
                    confidence_score=0.0,
                    reason=f"Filtro Rechazado: Spread excesivo en token SÍ (${yes_spread:.2f} > ${self.max_spread:.2f})",
                    timestamp=now,
                )

        # Probabilidades estimadas desde el spot
        p_win_yes = snapshot.estimated_win_prob
        p_win_no = 1.0 - p_win_yes

        # Cálculo de Expected Value (EV)
        ev_yes = (p_win_yes * 1.00) - yes_ask
        ev_no = (p_win_no * 1.00) - no_ask

        # 2. Evaluación de Señal BUY_YES
        if ev_yes >= self.min_ev_threshold and snapshot.spot_trend_score >= 0.30:
            confidence = min(1.0, (ev_yes / 0.20) * 0.5 + (snapshot.spot_trend_score * 0.5))
            reason_str = (
                f"SEÑAL COMPRA SÍ: EV = +{ev_yes*100:.1f}% >= +{self.min_ev_threshold*100:.1f}%. "
                f"Prob Spot = {p_win_yes*100:.1f}% vs Precio Ask = ${yes_ask:.2f}. "
                f"Trend Score Spot = +{snapshot.spot_trend_score:.2f}."
            )
            return PredictionSignal(
                market_condition_id=condition_id,
                token_id=yes_token.token_id,
                outcome=SignalType.BUY_YES,
                confidence_score=confidence,
                estimated_win_prob=p_win_yes,
                implied_prob_polymarket=yes_ask,
                expected_value_ev=ev_yes,
                target_price=yes_ask,
                reason=reason_str,
                timestamp=now,
            )

        # 3. Evaluación de Señal BUY_NO
        if ev_no >= self.min_ev_threshold and snapshot.spot_trend_score <= -0.30:
            confidence = min(1.0, (ev_no / 0.20) * 0.5 + (abs(snapshot.spot_trend_score) * 0.5))
            reason_str = (
                f"SEÑAL COMPRA NO: EV = +{ev_no*100:.1f}% >= +{self.min_ev_threshold*100:.1f}%. "
                f"Prob Spot NO = {p_win_no*100:.1f}% vs Precio Ask NO = ${no_ask:.2f}. "
                f"Trend Score Spot = {snapshot.spot_trend_score:.2f}."
            )
            return PredictionSignal(
                market_condition_id=condition_id,
                token_id=no_token.token_id,
                outcome=SignalType.BUY_NO,
                confidence_score=confidence,
                estimated_win_prob=p_win_no,
                implied_prob_polymarket=no_ask,
                expected_value_ev=ev_no,
                target_price=no_ask,
                reason=reason_str,
                timestamp=now,
            )

        # 4. Sin ventaja estadística suficiente (HOLD)
        best_ev = max(ev_yes, ev_no)
        return PredictionSignal(
            market_condition_id=condition_id,
            outcome=SignalType.HOLD,
            confidence_score=0.0,
            estimated_win_prob=p_win_yes,
            implied_prob_polymarket=yes_ask,
            expected_value_ev=best_ev,
            reason=f"HOLD: EV Máximo de {best_ev*100:+.1f}% insuficiente (< +{self.min_ev_threshold*100:.1f}%) o tendencia neutral.",
            timestamp=now,
        )
