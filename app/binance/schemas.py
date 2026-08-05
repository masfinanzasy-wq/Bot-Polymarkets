"""
Esquemas Pydantic para validación y parseo de mensajes recibidos de Binance WebSocket.
"""
from pydantic import BaseModel, Field
from typing import Optional


class BinanceTradeTick(BaseModel):
    """
    Representa un tick de transacción de compra/venta en tiempo real (aggTrade).
    """
    event_type: str = Field(alias="e")
    event_time: int = Field(alias="E")
    symbol: str = Field(alias="s")
    trade_id: int = Field(alias="a")
    price: float = Field(alias="p")
    quantity: float = Field(alias="q")
    trade_time: int = Field(alias="T")
    is_buyer_maker: bool = Field(alias="m")

    @property
    def price_float(self) -> float:
        return float(self.price)

    @property
    def quantity_float(self) -> float:
        return float(self.quantity)


class BinanceKlineData(BaseModel):
    """
    Detalle de la vela (kline) contenida en el tick de Binance.
    """
    start_time: int = Field(alias="t")
    close_time: int = Field(alias="T")
    symbol: str = Field(alias="s")
    interval: str = Field(alias="i")
    open_price: float = Field(alias="o")
    close_price: float = Field(alias="c")
    high_price: float = Field(alias="h")
    low_price: float = Field(alias="l")
    volume: float = Field(alias="v")
    number_of_trades: int = Field(alias="n")
    is_kline_closed: bool = Field(alias="x")
    quote_asset_volume: float = Field(alias="q")
    taker_buy_base_volume: float = Field(alias="V")
    taker_buy_quote_volume: float = Field(alias="Q")


class BinanceKlineTick(BaseModel):
    """
    Evento completo de actualización de vela (kline) de Binance.
    """
    event_type: str = Field(alias="e")
    event_time: int = Field(alias="E")
    symbol: str = Field(alias="s")
    kline: BinanceKlineData = Field(alias="k")
