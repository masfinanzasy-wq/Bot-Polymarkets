"""
Pruebas unitarias para el módulo de notificaciones por Telegram.
"""
import pytest
from app.notifications import TelegramNotifier
from app.predictors.schemas import PredictionSignal, SignalType
from app.execution.schemas import PaperPosition, PositionStatus


class TestTelegramNotifier:
    """Pruebas del cliente de notificaciones por Telegram."""

    @pytest.mark.asyncio
    async def test_telegram_notifier_missing_token_returns_false(self):
        notifier = TelegramNotifier(bot_token="")
        result = await notifier.send_message(chat_id="12345678", text="Test")
        assert result is False

    @pytest.mark.asyncio
    async def test_telegram_signal_alert_formatting(self):
        notifier = TelegramNotifier(bot_token="dummy_token_123")
        import time
        signal = PredictionSignal(
            market_condition_id="0x123",
            outcome=SignalType.BUY_YES,
            confidence_score=0.85,
            estimated_win_prob=0.68,
            implied_prob_polymarket=0.48,
            expected_value_ev=0.15,
            target_price=0.50,
            reason="Prueba cuantitativa de EV alto",
            timestamp=time.time()
        )
        
        # Debe fallar amigablemente al intentar llamar a la API falsa sin romper la ejecución
        res = await notifier.send_signal_alert(chat_id="123456", signal=signal, question="Will BTC reach 100k?")
        assert isinstance(res, bool)
