"""
Cliente asíncrono HTTP/REST para interactuar con la Gamma API y el CLOB de Polymarket.
"""
import httpx
import json
from typing import List, Optional, Dict, Any
from app.config.settings import settings
from app.logger.logger import sys_logger
from app.polymarket.schemas import (
    PolymarketMarket,
    PolymarketToken,
    PolymarketOrderBook,
    PolymarketOrderBookLevel,
)


class PolymarketClient:
    """
    Cliente de datos para Polymarket.
    
    Permite:
    - Descubrir mercados activos de Criptomonedas (BTC/ETH en M5/Corto plazo).
    - Consultar precios, midpoints y probabilidades implícitas en el CLOB.
    - Obtener el libro de órdenes (bids/asks), volumen y liquidez.
    """

    GAMMA_API_URL = "https://gamma-api.polymarket.com"
    CLOB_API_URL = settings.POLYMARKET_HOST

    def __init__(self, timeout: float = 10.0):
        self.timeout = timeout
        self.headers = {"Accept": "application/json"}

    async def get_active_crypto_markets(self, filter_keyword: Optional[str] = None) -> List[PolymarketMarket]:
        """
        Consulta la Gamma API (/events?tag_slug=crypto) para extraer mercados de Criptomonedas activos.
        """
        endpoint = f"{self.GAMMA_API_URL}/events"
        params = {
            "tag_slug": "crypto",
            "active": "true",
            "closed": "false",
            "limit": 50,
        }

        markets: List[PolymarketMarket] = []

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(endpoint, params=params, headers=self.headers)
                response.raise_for_status()
                events = response.json()

                for event in events:
                    raw_markets = event.get("markets", [])
                    for raw in raw_markets:
                        question = raw.get("question", "")
                        
                        if filter_keyword and filter_keyword.lower() not in question.lower():
                            continue

                        # Extraer tokens y clobTokenIds
                        clob_ids = raw.get("clobTokenIds")
                        outcomes = raw.get("outcomes")

                        tokens: List[PolymarketToken] = []
                        if clob_ids and outcomes:
                            try:
                                clob_list = json.loads(clob_ids) if isinstance(clob_ids, str) else clob_ids
                                outcomes_list = json.loads(outcomes) if isinstance(outcomes, str) else outcomes
                                
                                for token_id, outcome_name in zip(clob_list, outcomes_list):
                                    tokens.append(PolymarketToken(token_id=str(token_id), outcome=str(outcome_name)))
                            except Exception as parse_err:
                                sys_logger.debug(f"Error parseando tokens: {parse_err}")

                        market = PolymarketMarket(
                            condition_id=raw.get("conditionId", ""),
                            question=question,
                            slug=raw.get("slug", ""),
                            end_date_iso=raw.get("endDate"),
                            active=raw.get("active", True),
                            closed=raw.get("closed", False),
                            liquidity=float(raw.get("liquidity", 0.0) or 0.0),
                            volume=float(raw.get("volume", 0.0) or 0.0),
                            tokens=tokens,
                        )
                        markets.append(market)

            sys_logger.info(f"Polymarket: Se encontraron {len(markets)} mercados de Cripto activos.")
            return markets

        except Exception as e:
            sys_logger.error(f"Error al consultar Gamma API de Polymarket: {e}")
            return []

    async def get_order_book(self, token_id: str) -> Optional[PolymarketOrderBook]:
        """
        Obtiene el libro de órdenes (CLOB) para un token específico de Polymarket.
        """
        endpoint = f"{self.CLOB_API_URL}/book"
        params = {"token_id": token_id}

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(endpoint, params=params, headers=self.headers)
                if response.status_code == 404:
                    return None
                response.raise_for_status()
                data = response.json()

                bids = [
                    PolymarketOrderBookLevel(price=float(item["price"]), size=float(item["size"]))
                    for item in data.get("bids", [])
                ]
                asks = [
                    PolymarketOrderBookLevel(price=float(item["price"]), size=float(item["size"]))
                    for item in data.get("asks", [])
                ]

                bids.sort(key=lambda x: x.price, reverse=True)
                asks.sort(key=lambda x: x.price)

                return PolymarketOrderBook(token_id=token_id, bids=bids, asks=asks)

        except Exception as e:
            sys_logger.error(f"Error al consultar CLOB OrderBook (Token {token_id[:8]}...): {e}")
            return None

    async def get_token_midpoint(self, token_id: str) -> Optional[float]:
        """
        Consulta el precio midpoint (probabilidad implícita directa) del token en el CLOB.
        """
        endpoint = f"{self.CLOB_API_URL}/midpoint"
        params = {"token_id": token_id}

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(endpoint, params=params, headers=self.headers)
                if response.status_code != 200:
                    return None
                data = response.json()
                mid = data.get("mid")
                return float(mid) if mid is not None else None
        except Exception:
            return None

    async def place_live_order(
        self,
        token_id: str,
        price: float,
        size_usd: float,
        side: str = "BUY",
    ) -> Optional[Dict[str, Any]]:
        """
        Firma y envía una orden real a la Polymarket CLOB en la blockchain de Polygon (Modo Real).
        Requiere POLYMARKET_PRIVATE_KEY y PAPER_TRADING=False.
        """
        if settings.PAPER_TRADING:
            sys_logger.warning("place_live_order llamado mientras PAPER_TRADING=True. Ignorando orden real.")
            return None

        if not settings.POLYMARKET_PRIVATE_KEY or settings.POLYMARKET_PRIVATE_KEY == "your_polygon_private_key_here":
            sys_logger.error("No se puede enviar orden real: POLYMARKET_PRIVATE_KEY no configurada en .env.")
            return None

        try:
            # Intento de importar ClobClient si está instalado
            from py_clob_client.client import ClobClient
            from py_clob_client.clob_types import OrderArgs

            client = ClobClient(
                host=self.CLOB_API_URL,
                key=settings.POLYMARKET_PRIVATE_KEY,
                chain_id=settings.POLYMARKET_CHAIN_ID,
            )

            # Crear firma y enviar orden de tipo GTC (Good 'Til Cancelled)
            order_args = OrderArgs(
                price=price,
                size=size_usd / price if price > 0 else 0.0,
                side=side,
                token_id=token_id,
            )
            signed_order = client.create_order(order_args)
            response = client.post_order(signed_order)

            sys_logger.info(f"ORDEN REAL ENVIADA AL CLOB: ID={response.get('orderID')} | {side} {token_id[:8]}... @ ${price:.4f}")
            return response

        except ImportError:
            sys_logger.error("La librería py-clob-client no está instalada. Instálala ejecutando: pip install py-clob-client")
            return None
        except Exception as e:
            sys_logger.error(f"Error al enviar orden real al CLOB de Polymarket: {e}")
            return None
