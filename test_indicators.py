"""
Script de prueba para verificar el cálculo del motor de indicadores cuantitativos
y el cálculo de Expected Value (EV) en tiempo real.
"""
import asyncio
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

from app.binance import BinanceWebSocketClient, BinanceTradeTick
from app.indicators import IndicatorsEngine
from app.logger.logger import sys_logger


engine = IndicatorsEngine()
tick_count = 0

async def handle_trade(tick: BinanceTradeTick) -> None:
    global tick_count
    tick_count += 1

    # Ingestar tick en el motor cuantitativo
    snapshot = engine.update_tick(tick)

    # Simular una probabilidad implícita de Polymarket para el token SÍ (ejemplo: 48 centavos = 0.48)
    simulated_polymarket_prob = 0.48
    snapshot = engine.calculate_ev(snapshot, simulated_polymarket_prob)

    if tick_count % 5 == 0:  # Mostrar snapshot cada 5 ticks
        sys_logger.info(f"\n--- Analysis Snapshot #{tick_count} ---")
        sys_logger.info(f"Precio Spot BTC: ${snapshot.last_price:,.2f}")
        sys_logger.info(f"EMA 9: ${snapshot.ema_9:,.2f} | EMA 21: ${snapshot.ema_21:,.2f}")
        sys_logger.info(f"VWAP: ${snapshot.vwap:,.2f} | RSI(14): {snapshot.rsi_14 or 0.0:.1f}")
        sys_logger.info(f"Order Flow Delta Ratio: {snapshot.volume_delta_ratio:+.2f}")
        sys_logger.info(f"Spot Trend Score: {snapshot.spot_trend_score:+.2f}")
        sys_logger.info(f"Prob. Ganar Estimada (Spot): {snapshot.estimated_win_prob * 100:.1f}%")
        sys_logger.info(f"Prob. Implícita Polymarket: {snapshot.implied_prob_polymarket * 100:.1f}%")
        
        if snapshot.expected_value_ev is not None:
            ev_pct = snapshot.expected_value_ev * 100
            sys_logger.info(f"EXPECTED VALUE (EV): {ev_pct:+.2f}%")

async def test_indicators() -> None:
    client = BinanceWebSocketClient(symbol="btcusdt", stream_type="aggTrade", on_message_callback=handle_trade)
    task = asyncio.create_task(client.start())
    
    sys_logger.info("Ingestando ticks de Binance para el motor de indicadores por 6 segundos...")
    await asyncio.sleep(6)
    
    await client.stop()
    task.cancel()
    sys_logger.info(f"Prueba del Motor de Indicadores completada. Ticks procesados: {tick_count}")

if __name__ == "__main__":
    asyncio.run(test_indicators())
