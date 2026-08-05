"""
Modelos ORM de SQLAlchemy para PostgreSQL.
Tablas de snapshots de métricas, señales de predicción y registro de operaciones.
"""
from datetime import datetime
from sqlalchemy import String, Float, Integer, Boolean, Text, DateTime, Column, ForeignKey
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class UserModel(Base):
    """
    Tabla de usuarios para la plataforma SaaS Multi-Tenant.
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(120), unique=True, nullable=False, index=True)
    password_hash = Column(String(256), nullable=False)
    role = Column(String(20), nullable=False, default="USER")  # ADMIN, USER
    plan_tier = Column(String(20), nullable=False, default="STARTER")  # STARTER, PRO, WHALE
    is_active = Column(Boolean, nullable=False, default=True)
    telegram_chat_id = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    wallets = relationship("UserWalletModel", back_populates="user", cascade="all, delete-orphan")


class UserWalletModel(Base):
    """
    Bóveda de billeteras cifradas por usuario (Polygon Private Keys encriptadas con AES-256).
    """
    __tablename__ = "user_wallets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    polygon_address = Column(String(64), nullable=True)
    encrypted_private_key = Column(Text, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("UserModel", back_populates="wallets")


class MetricSnapshotModel(Base):
    """
    Tabla de métricas técnicas e indicadores cuantitativos procesados tick a tick.
    """
    __tablename__ = "metric_snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False, index=True)
    last_price = Column(Float, nullable=False)
    ema_9 = Column(Float, nullable=True)
    ema_21 = Column(Float, nullable=True)
    vwap = Column(Float, nullable=True)
    rsi_14 = Column(Float, nullable=True)
    volume_delta_ratio = Column(Float, nullable=False, default=0.0)
    spot_trend_score = Column(Float, nullable=False, default=0.0)
    estimated_win_prob = Column(Float, nullable=False, default=0.5)
    implied_prob_polymarket = Column(Float, nullable=True)
    expected_value_ev = Column(Float, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)


class PredictionSignalModel(Base):
    """
    Tabla de señales probabilísticas generadas por el PredictorEngine.
    """
    __tablename__ = "prediction_signals"

    id = Column(Integer, primary_key=True, autoincrement=True)
    market_condition_id = Column(String(100), nullable=False, index=True)
    token_id = Column(String(100), nullable=True)
    outcome = Column(String(20), nullable=False)  # BUY_YES, BUY_NO, HOLD
    confidence_score = Column(Float, nullable=False, default=0.0)
    estimated_win_prob = Column(Float, nullable=False, default=0.5)
    implied_prob_polymarket = Column(Float, nullable=False, default=0.5)
    expected_value_ev = Column(Float, nullable=False, default=0.0)
    target_price = Column(Float, nullable=False, default=0.0)
    reason = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)


class TradeRecordModel(Base):
    """
    Tabla de operaciones históricas (Paper Trading y Modo Real).
    """
    __tablename__ = "trade_records"

    position_id = Column(String(50), primary_key=True)
    market_condition_id = Column(String(100), nullable=False, index=True)
    token_id = Column(String(100), nullable=False)
    outcome = Column(String(20), nullable=False)
    entry_price = Column(Float, nullable=False)
    exit_price = Column(Float, nullable=True)
    shares = Column(Float, nullable=False)
    cost_usd = Column(Float, nullable=False)
    pnl_usd = Column(Float, nullable=False, default=0.0)
    pnl_pct = Column(Float, nullable=False, default=0.0)
    status = Column(String(20), nullable=False)  # OPEN, CLOSED_WIN, CLOSED_LOSS
    reason = Column(Text, nullable=True)
    opened_at = Column(DateTime, default=datetime.utcnow, index=True)
    closed_at = Column(DateTime, nullable=True)
