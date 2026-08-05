"""
Módulo de Notificaciones por Telegram para el envío de Alertas de Oportunidades y Resultados de Operaciones en Tiempo Real.
"""
import httpx
from typing import Optional, Dict, Any
from app.config import settings
from app.logger.logger import sys_logger
from app.predictors.schemas import PredictionSignal, SignalType
from app.execution.schemas import PaperPosition


class TelegramNotifier:
    """
    Cliente de notificaciones para Telegram Bot API.
    """

    def __init__(self, bot_token: Optional[str] = None):
        self.bot_token = bot_token or settings.TELEGRAM_BOT_TOKEN
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}" if self.bot_token else None

    async def send_message(self, chat_id: str, text: str) -> bool:
        """
        Envía un mensaje de texto formateado en HTML a un chat_id de Telegram.
        """
        if not self.base_url or not chat_id:
            sys_logger.debug("Telegram Bot Token o Chat ID ausente. Omitiendo notificación por Telegram.")
            return False

        endpoint = f"{self.base_url}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(endpoint, json=payload)
                if response.status_code == 200:
                    sys_logger.info(f"Notificación Telegram enviada a chat_id={chat_id}")
                    return True
                else:
                    sys_logger.warning(f"Error Telegram API HTTP {response.status_code}: {response.text}")
                    return False
        except Exception as e:
            sys_logger.error(f"Error al enviar mensaje por Telegram: {e}")
            return False

    async def send_signal_alert(self, chat_id: str, signal: PredictionSignal, question: str) -> bool:
        """
        Envía una alerta de señal predictiva de alto EV.
        """
        outcome_emoji = "🟢 SÍ (UP)" if signal.outcome == SignalType.BUY_YES else "🔴 NO (DOWN)"
        message = (
            f"⚡ <b>¡NUEVA OPORTUNIDAD EN POLYMARKET!</b>\n\n"
            f"📌 <b>Mercado:</b> {question}\n"
            f"🎯 <b>Señal:</b> {outcome_emoji}\n"
            f"📈 <b>Prob. Estimada Spot:</b> {signal.estimated_win_prob*100:.1f}%\n"
            f"📊 <b>Prob. Implícita Polymarket:</b> {signal.implied_prob_polymarket*100:.1f}%\n"
            f"💡 <b>Valor Esperado (EV):</b> +{signal.expected_value_ev*100:.2f}%\n"
            f"📝 <b>Análisis:</b> <i>{signal.reason}</i>\n"
        )
        return await self.send_message(chat_id, message)

    async def send_trade_settlement_alert(self, chat_id: str, position: PaperPosition, current_balance: float) -> bool:
        """
        Envía una alerta instantánea cuando una posición es cerrada en el mercado.
        """
        is_win = "CLOSED_WIN" in str(position.status)
        status_emoji = "🏆 GANADA" if is_win else "❌ PERDIDA"
        pnl_prefix = "+" if position.pnl_usd >= 0 else ""

        message = (
            f"🎯 <b>¡OPERACIÓN CERRADA EN POLYMARKET!</b>\n\n"
            f"📊 <b>Resultado:</b> {status_emoji}\n"
            f"🎲 <b>Dirección:</b> {position.outcome.value}\n"
            f"💵 <b>Inversión:</b> ${position.cost_usd:.2f} USD\n"
            f"💰 <b>PnL Realizado:</b> <b>{pnl_prefix}${position.pnl_usd:.2f} USD</b> ({position.pnl_pct:+.2f}%)\n"
            f"💳 <b>Nuevo Saldo Portafolio:</b> ${current_balance:.2f} USD\n"
        )
        return await self.send_message(chat_id, message)
