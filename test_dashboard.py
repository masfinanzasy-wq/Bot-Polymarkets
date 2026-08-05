"""
Script de prueba de integración para el TerminalDashboard en tiempo real.
Conecta a Binance WS, procesa indicadores spot, simula señales y renderiza la pantalla Rich.
"""
import asyncio
import sys
import time
from pathlib import Path
from rich.live import Live

sys.path.append(str(Path(__file__).parent))

from app.binance import BinanceWebSocketClient, BinanceTradeTick
from app.indicators import IndicatorsEngine, AnalysisSnapshot
from app.polymarket import PolymarketMarket, PolymarketToken
from app.predictors import PredictorEngine
from app.risk import RiskManager
from app.execution import PaperExecutionEngine
from app.dashboard import TerminalDashboard
from app.logger.logger import sys_logger


dashboard = TerminalDashboard()
indicators_engine = IndicatorsEngine()
predictor_engine = PredictorEngine()
risk_manager = RiskManager()
execution_engine = PaperExecutionEngine()

current_snapshot: AnalysisSnapshot = None
tick_count = 0

dummy_market = PolymarketMarket(
    condition_id="0x_live_btc_5m",
    question="Will Bitcoin price be UP in next 5 mins?",
    slug="btc-up-5m",
    liquidity=1250.0,
    volume=8450.0,
    tokens=[
        PolymarketToken(token_id="tok_yes_live", outcome="Yes"),
        PolymarketToken(token_id="tok_no_live", outcome="No"),
    ]
)

async def handle_trade(tick: BinanceTradeTick) -> None:
    global tick_count, current_snapshot
    tick_count += 1

    current_snapshot = indicators_engine.update_tick(tick)
    
    # Simular probabilidad implícita de Polymarket (0.47)
    current_snapshot = indicators_engine.calculate_ev(current_snapshot, 0.47)

    # Evaluar predicción
    signal = predictor_engine.evaluate_market(current_snapshot, dummy_market)

    # Si hay señal relevante, pasar por el gestor de riesgo y ejecutar en Paper Trading
    if signal.outcome != "HOLD" and signal.confidence_score > 0:
        size = risk_manager.calculate_position_size(signal, execution_engine.balance, execution_engine.total_realized_pnl)
        if size > 0:
            pos = execution_engine.open_position(signal, size)
            if pos:
                dashboard.add_log_entry(f"SEÑAL GENERADA: {signal.outcome.value} (${size:.2f} USD)")
                # Simular cierre aleatorio tras 2 ticks
                if tick_count % 3 == 0:
                    execution_engine.settle_position(pos.id, won=True)
                    dashboard.add_log_entry(f"POSICIÓN CERRADA: GANADA (+${pos.pnl_usd:.2f})")

    dashboard.add_log_entry(f"Tick #{tick_count}: BTC = ${tick.price:,.2f}")

async def run_live_dashboard() -> None:
    client = BinanceWebSocketClient(symbol="btcusdt", stream_type="aggTrade", on_message_callback=handle_trade)
    task = asyncio.create_task(client.start())

    sys_logger.info("Iniciando Dashboard interactivo de Terminal Rich (duración 6s)...")
    
    with Live(dashboard.generate_layout(), refresh_per_second=4) as live:
        for _ in range(30):  # 15 segundos de ejecución en vivo
            await asyncio.sleep(0.5)
            summary = execution_engine.get_summary()
            layout = dashboard.generate_layout(
                snapshot=current_snapshot,
                market=dummy_market,
                portfolio=summary,
                binance_connected=True,
                polymarket_connected=True,
            )
            live.update(layout)

    await client.stop()
    task.cancel()
    sys_logger.info("Prueba de Dashboard de Terminal completada con éxito.")

if __name__ == "__main__":
    asyncio.run(run_live_dashboard())
