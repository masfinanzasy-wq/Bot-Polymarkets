"""
Dashboard de terminal interactivo en tiempo real utilizando Rich.
Renders estado de conexiones, indicadores spot, mercados M5, señales y PnL de Paper Trading.
"""
import sys
import time
import os
import psutil
from typing import Optional, List

# Forzar codificación UTF-8 para consola de Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from app.indicators.schemas import AnalysisSnapshot
from app.polymarket.schemas import PolymarketMarket
from app.predictors.schemas import PredictionSignal
from app.execution.schemas import PaperPortfolioSummary


class TerminalDashboard:
    """
    Componente visual de terminal interactivo para el Bot de Polymarket.
    Renderiza un layout limpio con paneles de métricas spot, Polymarket, PnL y logs.
    """

    def __init__(self):
        self.console = Console(safe_box=True)
        self.recent_logs: List[str] = []
        self.max_log_entries = 6

    def add_log_entry(self, message: str) -> None:
        """
        Agrega un evento al feed de logs recientes de la pantalla.
        """
        timestamp_str = time.strftime("%H:%M:%S")
        self.recent_logs.append(f"[{timestamp_str}] {message}")
        if len(self.recent_logs) > self.max_log_entries:
            self.recent_logs.pop(0)

    def generate_layout(
        self,
        snapshot: Optional[AnalysisSnapshot] = None,
        market: Optional[PolymarketMarket] = None,
        last_signal: Optional[PredictionSignal] = None,
        portfolio: Optional[PaperPortfolioSummary] = None,
        binance_connected: bool = True,
        polymarket_connected: bool = True,
    ) -> Layout:
        """
        Construye la estructura de paneles mediante Rich Layout.
        """
        layout = Layout()

        # División vertical principal: Header, Body, Footer
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="body", ratio=1),
            Layout(name="footer", size=7),
        )

        # Divisores del cuerpo: Spot/Indicators, Polymarket M5, Portafolio
        layout["body"].split_row(
            Layout(name="spot", ratio=1),
            Layout(name="polymarket", ratio=1),
            Layout(name="portfolio", ratio=1),
        )

        # Header Panel
        header_text = Text(
            " [BOT] POLYMARKET M5 PREDICTIVE TRADING BOT - MODO SOMBRA (PAPER TRADING)",
            style="bold cyan center",
        )
        layout["header"].update(Panel(header_text, style="cyan"))

        # Panel 1: Spot & Indicadores Técnicos
        spot_table = Table(show_header=False, box=None, expand=True)
        if snapshot:
            spot_table.add_row("Símbolo Referencia:", f"[bold white]{snapshot.symbol.upper()}[/bold white]")
            spot_table.add_row("Precio Spot Ticker:", f"[bold yellow]${snapshot.last_price:,.2f}[/bold yellow]")
            spot_table.add_row("EMA 9 / EMA 21:", f"${snapshot.ema_9 or 0:,.2f} / ${snapshot.ema_21 or 0:,.2f}")
            spot_table.add_row("VWAP:", f"${snapshot.vwap or 0:,.2f}")
            spot_table.add_row("RSI (14):", f"{snapshot.rsi_14 or 0:.1f}")

            delta_color = "green" if snapshot.volume_delta_ratio >= 0 else "red"
            spot_table.add_row("Order Flow Delta:", f"[{delta_color}]{snapshot.volume_delta_ratio:+.2f}[/{delta_color}]")

            trend_color = "green" if snapshot.spot_trend_score >= 0 else "red"
            spot_table.add_row("Spot Trend Score:", f"[{trend_color}]{snapshot.spot_trend_score:+.2f}[/{trend_color}]")
        else:
            spot_table.add_row("Estado:", "[dim]Esperando datos de Binance Spot...[/dim]")

        layout["spot"].update(Panel(spot_table, title="[bold green]1. Binance Spot Metrics[/bold green]", border_style="green"))

        # Panel 2: Polymarket M5 Active Contract
        poly_table = Table(show_header=False, box=None, expand=True)
        if market:
            poly_table.add_row("Pregunta Mercado:", f"[bold white]{market.question[:35]}...[/bold white]")
            poly_table.add_row("Liquidez:", f"${market.liquidity:,.2f}")
            poly_table.add_row("Volumen Total:", f"${market.volume:,.2f}")

            yes_tok = market.yes_token
            if yes_tok:
                poly_table.add_row("Token SÍ (YES):", f"{yes_tok.token_id[:8]}...")
            if snapshot and snapshot.implied_prob_polymarket:
                poly_table.add_row("Prob. Implícita SÍ:", f"[bold magenta]{snapshot.implied_prob_polymarket*100:.1f}%[/bold magenta]")
            if snapshot and snapshot.expected_value_ev is not None:
                ev_color = "bold green" if snapshot.expected_value_ev >= 0.05 else "yellow"
                poly_table.add_row("Expected Value (EV):", f"[{ev_color}]{snapshot.expected_value_ev*100:+.1f}%[/{ev_color}]")
        else:
            poly_table.add_row("Estado:", "[dim]Monitoreando mercados de Polymarket...[/dim]")

        layout["polymarket"].update(Panel(poly_table, title="[bold magenta]2. Polymarket M5 Active[/bold magenta]", border_style="magenta"))

        # Panel 3: Portafolio de Paper Trading
        port_table = Table(show_header=False, box=None, expand=True)
        if portfolio:
            pnl_color = "bold green" if portfolio.total_realized_pnl >= 0 else "bold red"
            port_table.add_row("Balance Inicial:", f"${portfolio.initial_balance:,.2f} USD")
            port_table.add_row("Balance Actual:", f"[bold yellow]${portfolio.current_balance:,.2f} USD[/bold yellow]")
            port_table.add_row("PnL Realizado:", f"[{pnl_color}]${portfolio.total_realized_pnl:+,.2f} USD[/{pnl_color}]")
            port_table.add_row("Operaciones Totales:", f"{portfolio.total_trades} (Ganadas: {portfolio.winning_trades} | Perdedores: {portfolio.losing_trades})")
            port_table.add_row("Precisión (Win Rate):", f"[bold cyan]{portfolio.win_rate_pct:.1f}%[/bold cyan]")
            port_table.add_row("Posiciones Activas:", f"{portfolio.active_positions_count}")
        else:
            port_table.add_row("Estado:", "[dim]Inicializando portafolio virtual...[/dim]")

        layout["portfolio"].update(Panel(port_table, title="[bold yellow]3. Paper Portfolio PnL[/bold yellow]", border_style="yellow"))

        # Panel Footer: Estado del Sistema, Recursos y Log Feed
        try:
            process = psutil.Process(os.getpid())
            cpu_usage = process.cpu_percent()
            mem_usage = process.memory_info().rss / (1024 * 1024)
        except Exception:
            cpu_usage, mem_usage = 0.0, 0.0

        bin_status = "[bold green]ONLINE[/bold green]" if binance_connected else "[bold red]OFFLINE[/bold red]"
        poly_status = "[bold green]ONLINE[/bold green]" if polymarket_connected else "[bold red]OFFLINE[/bold red]"

        system_status_line = (
            f"Binance WS: {bin_status}  |  Polymarket REST: {poly_status}  |  "
            f"CPU: {cpu_usage:.1f}%  |  RAM: {mem_usage:.1f} MB"
        )

        log_lines_text = "\n".join(self.recent_logs) if self.recent_logs else "Esperando eventos del sistema..."
        footer_content = f"{system_status_line}\n─" * 1 + f"\n{log_lines_text}"

        layout["footer"].update(Panel(footer_content, title="[bold blue]Estado del Sistema & Log Feed[/bold blue]", border_style="blue"))

        return layout
