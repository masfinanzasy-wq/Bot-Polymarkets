"""
Script de simulación de Paper Trading con capital inicial de $100.00 USD.
Procesa datos de mercado en tiempo real, genera señales EV, aplica Kelly Criterion y muestra reporte de rendimiento.
"""
import asyncio
import time
import random
from app.binance import BinanceWebSocketClient, BinanceTradeTick
from app.indicators import IndicatorsEngine, AnalysisSnapshot
from app.polymarket import PolymarketMarket, PolymarketToken
from app.predictors import PredictorEngine, SignalType
from app.risk import RiskManager
from app.execution import PaperExecutionEngine
from app.optimization import OptimizationEngine
from app.logger.logger import sys_logger
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console(safe_box=True)

async def run_simulation_100usd(duration_seconds: int = 20):
    sys_logger.info("==========================================================")
    sys_logger.info("INICIANDO SIMULACIÓN DE TRADING CON $100.00 USD")
    sys_logger.info("==========================================================")

    # 1. Inicializar motores con $100.00 USD de capital inicial
    INITIAL_BALANCE = 100.0
    indicators_engine = IndicatorsEngine()
    predictor_engine = PredictorEngine(min_ev_threshold=0.04, min_liquidity=50.0)
    risk_manager = RiskManager(max_position_usd=15.0, max_daily_loss_usd=30.0)
    paper_engine = PaperExecutionEngine(initial_balance=INITIAL_BALANCE)
    opt_engine = OptimizationEngine(base_min_ev=0.04, base_kelly_fraction=0.25)

    dummy_market = PolymarketMarket(
        condition_id="0x_sim_btc_5m",
        question="Will BTC be UP in 5 minutes?",
        slug="btc-up-5m",
        liquidity=1500.0,
        volume=12000.0,
        tokens=[
            PolymarketToken(token_id="tok_yes_sim", outcome="Yes"),
            PolymarketToken(token_id="tok_no_sim", outcome="No"),
        ]
    )

    tick_counter = 0

    async def on_tick(tick: BinanceTradeTick):
        nonlocal tick_counter
        tick_counter += 1

        snap = indicators_engine.update_tick(tick)
        
        # Simular probabilidad implícita de mercado (0.48)
        snap = indicators_engine.calculate_ev(snap, polymarket_implied_prob=0.48)

        # Evaluar predicción EV
        signal = predictor_engine.evaluate_market(snap, dummy_market)

        if signal.outcome != SignalType.HOLD and signal.confidence_score > 0:
            # Calcular tamaño de posición Kelly basado en el saldo actual ($100)
            size = risk_manager.calculate_position_size(
                signal,
                current_balance=paper_engine.balance,
                current_daily_pnl=paper_engine.total_realized_pnl
            )

            if size > 0:
                pos = paper_engine.open_position(signal, size_usd=size)
                if pos:
                    # Simular resolución de mercado (75% probabilidad de éxito según señal)
                    won = random.random() < signal.estimated_win_prob
                    await asyncio.sleep(0.1)
                    paper_engine.settle_position(pos.id, won=won)

    client = BinanceWebSocketClient(symbol="btcusdt", stream_type="aggTrade", on_message_callback=on_tick)
    task = asyncio.create_task(client.start())

    sys_logger.info(f"Conectado a Binance WS. Ejecutando simulación durante {duration_seconds} segundos...")
    await asyncio.sleep(duration_seconds)

    await client.stop()
    task.cancel()

    # Obtener resultados y métricas
    summary = paper_engine.get_summary()
    opt_metrics = opt_engine.calculate_performance(paper_engine.closed_positions)

    # Imprimir reporte formateado en consola
    console.print("\n")
    table = Table(title="[REPORTE FINAL DE SIMULACION ($100.00 USD CAP)]", show_header=True, header_style="bold cyan")
    table.add_column("Métrica", style="bold")
    table.add_column("Valor", justify="right")

    table.add_row("Capital Inicial", f"${INITIAL_BALANCE:.2f} USD")
    table.add_row("Saldo Final Actual", f"${summary.current_balance:.2f} USD")
    
    pnl_style = "bold green" if summary.total_realized_pnl >= 0 else "bold red"
    pnl_pct = (summary.total_realized_pnl / summary.initial_balance) * 100.0
    pnl_str = f"+${summary.total_realized_pnl:.2f} USD ({pnl_pct:+.2f}%)" if summary.total_realized_pnl >= 0 else f"-${abs(summary.total_realized_pnl):.2f} USD ({pnl_pct:+.2f}%)"
    table.add_row("PnL Realizado Total", f"[{pnl_style}]{pnl_str}[/{pnl_style}]")
    
    table.add_row("Total de Operaciones", str(summary.total_trades))
    table.add_row("Operaciones Ganadas", f"[green]{summary.winning_trades}[/green]")
    table.add_row("Operaciones Perdedoras", f"[red]{summary.losing_trades}[/red]")
    table.add_row("Precisión (Win Rate)", f"{summary.win_rate_pct:.1f}%")
    table.add_row("Profit Factor", f"{opt_metrics.profit_factor:.2f}")
    table.add_row("Max Drawdown", f"${opt_metrics.max_drawdown_usd:.2f} USD")

    console.print(table)
    console.print("\n")

if __name__ == "__main__":
    asyncio.run(run_simulation_100usd(20))
