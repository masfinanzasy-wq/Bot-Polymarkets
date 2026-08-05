"""
Cliente WebSocket asíncrono para Binance con reconexión automática y validación Pydantic.
"""
import asyncio
import json
import websockets
from typing import Callable, Awaitable, Optional, Any
from websockets.exceptions import ConnectionClosed, WebSocketException

from app.config.settings import settings
from app.logger.logger import sys_logger
from app.binance.schemas import BinanceTradeTick, BinanceKlineTick


class BinanceWebSocketClient:
    """
    Cliente WebSocket para conectarse a streams en tiempo real de Binance Spot.
    
    Implementa:
    - Reconexión automática con exponential backoff.
    - Validación y parseo estricto con Pydantic.
    - Despacho asíncrono de eventos a través de callbacks.
    """

    def __init__(
        self,
        symbol: str = "btcusdt",
        stream_type: str = "aggTrade",  # 'aggTrade' o 'kline_1s'
        on_message_callback: Optional[Callable[[Any], Awaitable[None]]] = None,
        max_reconnect_delay: int = 30,
    ):
        self.symbol = symbol.lower()
        self.stream_type = stream_type
        self.on_message_callback = on_message_callback
        self.max_reconnect_delay = max_reconnect_delay
        
        self.ws_url = f"{settings.BINANCE_WS_URL}/{self.symbol}@{self.stream_type}"
        self._is_running = False
        self._ws_connection: Optional[websockets.WebSocketClientProtocol] = None

    async def start(self) -> None:
        """
        Inicia el loop de conexión WebSocket continuo con reconexión automática.
        """
        self._is_running = True
        reconnect_delay = 1

        sys_logger.info(f"Iniciando Binance WS Client para {self.symbol}@{self.stream_type}")

        while self._is_running:
            try:
                sys_logger.info(f"Conectando a Binance WS: {self.ws_url}")
                async with websockets.connect(self.ws_url, ping_interval=20, ping_timeout=10) as ws:
                    self._ws_connection = ws
                    reconnect_delay = 1  # Resetear delay tras conexión exitosa
                    sys_logger.info(f"Conexión Binance WS establecida ({self.symbol})")

                    async for message in ws:
                        if not self._is_running:
                            break
                        await self._process_raw_message(message)

            except (ConnectionClosed, WebSocketException) as e:
                sys_logger.warning(
                    f"Conexión Binance WS perdida ({e}). Reconectando en {reconnect_delay}s..."
                )
            except Exception as e:
                sys_logger.error(f"Error inesperado en Binance WS Client: {e}")

            if self._is_running:
                await asyncio.sleep(reconnect_delay)
                reconnect_delay = min(reconnect_delay * 2, self.max_reconnect_delay)

        sys_logger.info("Binance WS Client detenido.")

    async def stop(self) -> None:
        """
        Detiene limpiamente la conexión WebSocket.
        """
        self._is_running = False
        if self._ws_connection:
            await self._ws_connection.close()
            sys_logger.info("Conexión Binance WS cerrada por el usuario.")

    async def _process_raw_message(self, raw_message: str) -> None:
        """
        Parsea y valida el mensaje JSON entrante con Pydantic.
        """
        try:
            data = json.loads(raw_message)
            event_type = data.get("e")

            parsed_msg: Any = None
            if event_type == "aggTrade":
                parsed_msg = BinanceTradeTick.model_validate(data)
            elif event_type == "kline":
                parsed_msg = BinanceKlineTick.model_validate(data)
            else:
                parsed_msg = data

            if self.on_message_callback:
                await self.on_message_callback(parsed_msg)

        except Exception as err:
            sys_logger.error(f"Error al validar mensaje de Binance: {err} | Mensaje: {raw_message[:100]}")
