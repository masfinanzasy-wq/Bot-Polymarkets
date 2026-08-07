"""
Servidor API FastAPI para el Bot de Polymarket M5.
Ofrece endpoints REST, transmisión WebSocket en tiempo real de métricas, señales y ordenes.
"""
import asyncio
import json
import random
import time
from pathlib import Path
from typing import List

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.logger.logger import sys_logger
from app.indicators import IndicatorsEngine
from app.binance.schemas import BinanceTradeTick

from app.security import SecurityHeadersMiddleware, RateLimiterMiddleware
from app.api.auth_routes import router as auth_router
from app.api.billing_routes import router as billing_router
from app.api.admin_routes import router as admin_router

app = FastAPI(
    title=settings.APP_NAME,
    description="API REST y Dashboard Web en Tiempo Real para el Bot de Trading Predictivo en Polymarket M5",
    version="2.0.0",
)

# Incluir Rutas SaaS (Autenticación, Planes de Suscripción y Panel Maestro Admin)
app.include_router(auth_router)
app.include_router(billing_router)
app.include_router(admin_router)

# Registrar Capa de Seguridad (Headers de Seguridad y Rate Limiter por IP)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RateLimiterMiddleware, max_requests_per_minute=120, auth_max_requests=5)

# Habilitar CORS dinámico desde configuración
origins = [o.strip() for o in settings.ALLOWED_CORS_ORIGINS.split(",") if o.strip()]
if "*" in origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

WEB_DIR = Path(__file__).parent.parent / "web"

if WEB_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(WEB_DIR)), name="static")

# Connection Manager para WebSockets
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        sys_logger.info(f"Nuevo cliente WebSocket conectado. Total clientes: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            sys_logger.info(f"Cliente WebSocket desconectado. Total clientes: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
            except Exception:
                self.disconnect(connection)

manager = ConnectionManager()
indicators_engine = IndicatorsEngine()
current_price = 63450.0

async def live_data_broadcaster():
    """
    Tarea en segundo plano que genera y transmite métricas en tiempo real a todos los clientes.
    """
    global current_price
    while True:
        await asyncio.sleep(0.2) # 5 actualizaciones por segundo (200ms)
        if not manager.active_connections:
            continue

        # Simular variación de precio spot realista para transmisión backend
        delta = random.choice([-5.0, -2.5, -1.0, 0.0, 1.0, 2.5, 5.0])
        current_price = max(10000.0, current_price + delta)
        
        tick = BinanceTradeTick(
            e="aggTrade",
            E=int(time.time() * 1000),
            s="BTCUSDT",
            a=random.randint(10000, 99999),
            p=str(current_price),
            q=str(round(random.uniform(0.01, 1.5), 4)),
            T=int(time.time() * 1000),
            m=random.choice([True, False])
        )

        snap = indicators_engine.update_tick(tick)
        snap = indicators_engine.calculate_ev(snap, polymarket_implied_prob=0.48)

        payload = {
            "type": "market_snapshot",
            "timestamp": time.time(),
            "symbol": "BTCUSDT",
            "last_price": snap.last_price,
            "ema_9": snap.ema_9,
            "ema_21": snap.ema_21,
            "vwap": snap.vwap,
            "rsi_14": snap.rsi_14 or 50.0,
            "volume_delta_ratio": snap.volume_delta_ratio,
            "spot_trend_score": snap.spot_trend_score,
            "win_prob": snap.estimated_win_prob,
            "expected_value_ev": snap.expected_value_ev,
        }

        await manager.broadcast(payload)

from app.database.connection import init_db

@app.on_event("startup")
async def startup_event():
    try:
        await init_db()
    except Exception as err:
        sys_logger.warning(f"Modo Serverless Vercel (Sin DB local activa): {err}")
    try:
        asyncio.create_task(live_data_broadcaster())
    except Exception:
        pass

@app.get("/", response_class=FileResponse)
async def serve_dashboard():
    """Sirve la aplicación SPA del Dashboard Web."""
    index_file = WEB_DIR / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return JSONResponse({"status": "online", "message": "Polymarket M5 Bot API active"})


@app.get("/styles.css", response_class=FileResponse)
async def serve_css():
    return FileResponse(str(WEB_DIR / "styles.css"))


@app.get("/app.js", response_class=FileResponse)
async def serve_js():
    return FileResponse(str(WEB_DIR / "app.js"))

@app.post("/api/v1/auth/verify-key")
async def verify_access_key(payload: dict):
    """Verifica si la clave de acceso ingresada coincide con la clave configurada."""
    provided_key = payload.get("key", "")
    expected_key = settings.DASHBOARD_ACCESS_KEY
    if provided_key == expected_key:
        return {"success": True, "message": "Acceso concedido"}
    return JSONResponse({"success": False, "message": "Clave de acceso incorrecta"}, status_code=401)


@app.get("/api/v1/health")
async def health_check():
    """Endpoint de estado de salud del sistema."""
    return {
        "status": "healthy",
        "environment": settings.ENVIRONMENT,
        "paper_trading": settings.PAPER_TRADING,
        "app": settings.APP_NAME,
        "active_ws_clients": len(manager.active_connections)
    }

@app.get("/api/v1/wallet/balance/{address}")
async def get_polygon_wallet_balance(address: str):
    """Consulta el saldo real de USDC y MATIC en la red Polygon Mainnet."""
    address = address.strip()
    if not address.startswith("0x") or len(address) < 40:
        return JSONResponse({"error": "Dirección de Polygon inválida"}, status_code=400)

    try:
        import httpx
        rpc_url = "https://polygon-rpc.com"
        async with httpx.AsyncClient(timeout=6.0) as client:
            clean_addr = address[2:].zfill(64)
            data_call = "0x70a08231" + clean_addr

            p_matic = {"jsonrpc": "2.0", "method": "eth_getBalance", "params": [address, "latest"], "id": 1}
            p_usdc_nat = {"jsonrpc": "2.0", "method": "eth_call", "params": [{"to": "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359", "data": data_call}, "latest"], "id": 2}
            p_usdc_brg = {"jsonrpc": "2.0", "method": "eth_call", "params": [{"to": "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174", "data": data_call}, "latest"], "id": 3}

            r1, r2, r3 = await asyncio.gather(
                client.post(rpc_url, json=p_matic),
                client.post(rpc_url, json=p_usdc_nat),
                client.post(rpc_url, json=p_usdc_brg),
                return_exceptions=True
            )

            matic_hex = r1.json().get("result", "0x0") if not isinstance(r1, Exception) else "0x0"
            usdc_nat_hex = r2.json().get("result", "0x0") if not isinstance(r2, Exception) else "0x0"
            usdc_brg_hex = r3.json().get("result", "0x0") if not isinstance(r3, Exception) else "0x0"

            matic_val = int(matic_hex, 16) / 1e18 if matic_hex and matic_hex != "0x" else 0.0
            usdc_nat_val = int(usdc_nat_hex, 16) / 1e6 if usdc_nat_hex and usdc_nat_hex != "0x" else 0.0
            usdc_brg_val = int(usdc_brg_hex, 16) / 1e6 if usdc_brg_hex and usdc_brg_hex != "0x" else 0.0

            total_usdc = usdc_nat_val + usdc_brg_val

            return {
                "address": address,
                "usdc_balance": round(total_usdc, 2),
                "matic_balance": round(matic_val, 4),
                "success": True
            }
    except Exception as e:
        return {"address": address, "usdc_balance": 0.0, "matic_balance": 0.0, "success": False, "detail": str(e)}

@app.websocket("/ws/live")
async def websocket_endpoint(websocket: WebSocket):
    """Endpoint WebSocket para recibir transmisiones en directo de indicadores y señales."""
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Escuchar mensajes de cliente (p. ej. ping)
            await websocket.send_json({"type": "pong", "time": time.time()})
    except WebSocketDisconnect:
        manager.disconnect(websocket)
