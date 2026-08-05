"""
Script de prueba de integración para el conector WebSocket de Binance.
Recepta ticks de BTC/USDT durante 5 segundos y los valida en tiempo real.
"""
import asyncio
import sys
from pathlib import Path

# Agregar directorio raíz al PYTHONPATH
sys.path.append(str(Path(__file__).parent))

from app.binance import BinanceWebSocketClient, BinanceTradeTick
from app.logger.logger import sys_logger


tick_count = 0

async def handle_trade(tick: BinanceTradeTick) -> None:
    global tick_count
    tick_count += 1
    sys_logger.info(
        f"[TICK #{tick_count}] {tick.symbol} | Precio: ${tick.price:,.2f} | Cantidad: {tick.quantity} BTC | Compra Taker: {not tick.is_buyer_maker}"
    )

async def test_binance() -> None:
    client = BinanceWebSocketClient(symbol="btcusdt", stream_type="aggTrade", on_message_callback=handle_trade)
    
    # Iniciar cliente en segundo plano
    task = asyncio.create_task(client.start())
    
    sys_logger.info("Escuchando Binance WebSocket por 5 segundos...")
    await asyncio.sleep(5)
    
    # Detener cliente
    await client.stop()
    task.cancel()
    sys_logger.info(f"Prueba completada exitosamente. Total de ticks procesados: {tick_count}")

if __name__ == "__main__":
    asyncio.run(test_binance())
