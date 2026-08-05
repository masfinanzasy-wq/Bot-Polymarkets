"""
Fixtures reutilizables para toda la suite de pruebas del bot de Polymarket.
"""
import time
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.config import get_settings_for_env, TestingSettings
from app.database.models import Base
from app.database.repository import TradeRepository
from app.indicators import IndicatorsEngine, AnalysisSnapshot
from app.polymarket.schemas import (
    PolymarketMarket,
    PolymarketToken,
    PolymarketOrderBook,
    PolymarketOrderBookLevel,
)
from app.predictors import PredictorEngine
from app.risk import RiskManager
from app.execution import PaperExecutionEngine


# ─── Fixtures de Configuración ────────────────────────────────────────────────

@pytest.fixture(scope="session")
def test_settings() -> TestingSettings:
    return get_settings_for_env("testing")


# ─── Fixtures de Base de Datos ────────────────────────────────────────────────

@pytest_asyncio.fixture
async def db_session():
    """
    Crea un motor SQLite en memoria y provee una sesión asíncrona limpia por test.
    """
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with factory() as session:
        yield session

    await engine.dispose()


@pytest_asyncio.fixture
async def trade_repository(db_session: AsyncSession) -> TradeRepository:
    return TradeRepository(db_session)


# ─── Fixtures de Dominio de Trading ───────────────────────────────────────────

@pytest.fixture
def indicators_engine() -> IndicatorsEngine:
    return IndicatorsEngine(max_buffer_size=200)


@pytest.fixture
def predictor_engine() -> PredictorEngine:
    return PredictorEngine(min_ev_threshold=0.05, min_liquidity=50.0)


@pytest.fixture
def risk_manager() -> RiskManager:
    return RiskManager(max_position_usd=50.0, max_daily_loss_usd=200.0)


@pytest.fixture
def paper_engine() -> PaperExecutionEngine:
    return PaperExecutionEngine(initial_balance=1000.0)


@pytest.fixture
def dummy_market() -> PolymarketMarket:
    return PolymarketMarket(
        condition_id="0x_test_fixture_market",
        question="Will BTC be UP in 5 mins?",
        slug="btc-up-5m",
        liquidity=500.0,
        volume=5000.0,
        tokens=[
            PolymarketToken(token_id="yes_tok_fixture", outcome="Yes"),
            PolymarketToken(token_id="no_tok_fixture", outcome="No"),
        ],
    )


@pytest.fixture
def yes_order_book() -> PolymarketOrderBook:
    return PolymarketOrderBook(
        token_id="yes_tok_fixture",
        bids=[PolymarketOrderBookLevel(price=0.43, size=200.0)],
        asks=[PolymarketOrderBookLevel(price=0.45, size=200.0)],
    )


@pytest.fixture
def no_order_book() -> PolymarketOrderBook:
    return PolymarketOrderBook(
        token_id="no_tok_fixture",
        bids=[PolymarketOrderBookLevel(price=0.53, size=200.0)],
        asks=[PolymarketOrderBookLevel(price=0.55, size=200.0)],
    )


@pytest.fixture
def bullish_snapshot() -> AnalysisSnapshot:
    return AnalysisSnapshot(
        symbol="btcusdt",
        last_price=64500.0,
        timestamp=time.time(),
        ema_9=64400.0,
        ema_21=64200.0,
        vwap=64350.0,
        rsi_14=65.0,
        volume_delta_ratio=0.70,
        spot_trend_score=0.75,
        estimated_win_prob=0.72,
    )


@pytest.fixture
def bearish_snapshot() -> AnalysisSnapshot:
    return AnalysisSnapshot(
        symbol="btcusdt",
        last_price=63000.0,
        timestamp=time.time(),
        ema_9=63100.0,
        ema_21=63300.0,
        vwap=63150.0,
        rsi_14=38.0,
        volume_delta_ratio=-0.65,
        spot_trend_score=-0.70,
        estimated_win_prob=0.28,
    )
