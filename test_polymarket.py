"""
Script de prueba de integración para el conector de Polymarket.
Consulta los mercados crypto en la Gamma API y el CLOB en tiempo real.
"""
import asyncio
import sys
from pathlib import Path

# Agregar directorio raíz al PYTHONPATH
sys.path.append(str(Path(__file__).parent))

from app.polymarket import PolymarketClient
from app.logger.logger import sys_logger


async def test_polymarket() -> None:
    client = PolymarketClient()
    
    sys_logger.info("Buscando mercados activos de Criptomonedas en Polymarket...")
    markets = await client.get_active_crypto_markets()
    
    sys_logger.info(f"Total de mercados crypto encontrados: {len(markets)}")
    
    for idx, market in enumerate(markets[:5], 1):
        sys_logger.info(f"\n--- Mercado #{idx}: {market.question} ---")
        sys_logger.info(f"Liquidez: ${market.liquidity:,.2f} | Volumen: ${market.volume:,.2f}")
        
        yes_token = market.yes_token
        no_token = market.no_token
        
        if yes_token:
            mid = await client.get_token_midpoint(yes_token.token_id)
            book = await client.get_order_book(yes_token.token_id)
            prob_pct = (mid * 100) if mid is not None else 0.0
            sys_logger.info(f"  Token SÍ ({yes_token.token_id[:8]}...): Midpoint/Probabilidad = {prob_pct:.1f}%")
            if book:
                sys_logger.info(f"    Best Bid: ${book.best_bid} | Best Ask: ${book.best_ask}")
                
        if no_token:
            mid = await client.get_token_midpoint(no_token.token_id)
            prob_pct = (mid * 100) if mid is not None else 0.0
            sys_logger.info(f"  Token NO ({no_token.token_id[:8]}...): Midpoint/Probabilidad = {prob_pct:.1f}%")

if __name__ == "__main__":
    asyncio.run(test_polymarket())
