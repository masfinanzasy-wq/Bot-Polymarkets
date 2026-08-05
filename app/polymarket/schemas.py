"""
Esquemas Pydantic para mercados, tokens, ordenes y precios de Polymarket.
"""
from pydantic import BaseModel, Field
from typing import List, Optional


class PolymarketToken(BaseModel):
    """
    Representa un token de resultado (ej. YES o NO) en el CLOB de Polymarket.
    """
    token_id: str
    outcome: str  # 'Yes' o 'No'
    price: float = 0.0  # Precio actual (probabilidad implícita de 0.0 a 1.0)


class PolymarketOrderBookLevel(BaseModel):
    """
    Representa un nivel del libro de órdenes (Bid o Ask).
    """
    price: float
    size: float


class PolymarketOrderBook(BaseModel):
    """
    Libro de órdenes (CLOB) para un token específico.
    """
    token_id: str
    bids: List[PolymarketOrderBookLevel] = Field(default_factory=list)
    asks: List[PolymarketOrderBookLevel] = Field(default_factory=list)
    
    @property
    def best_bid(self) -> Optional[float]:
        return self.bids[0].price if self.bids else None

    @property
    def best_ask(self) -> Optional[float]:
        return self.asks[0].price if self.asks else None

    @property
    def midpoint(self) -> Optional[float]:
        bid = self.best_bid
        ask = self.best_ask
        if bid is not None and ask is not None:
            return (bid + ask) / 2.0
        return bid or ask


class PolymarketMarket(BaseModel):
    """
    Mercado M5 o de predicción activo en Polymarket.
    """
    condition_id: str
    question: str
    slug: str
    end_date_iso: Optional[str] = None
    active: bool = True
    closed: bool = False
    liquidity: float = 0.0
    volume: float = 0.0
    tokens: List[PolymarketToken] = Field(default_factory=list)

    @property
    def yes_token(self) -> Optional[PolymarketToken]:
        for token in self.tokens:
            if token.outcome.lower() in ("yes", "si", "1"):
                return token
        return None

    @property
    def no_token(self) -> Optional[PolymarketToken]:
        for token in self.tokens:
            if token.outcome.lower() in ("no", "0"):
                return token
        return None
