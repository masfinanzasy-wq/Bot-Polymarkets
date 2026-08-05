# Polymarket Predictive M5 Trading Bot

Bot profesional de predicción y ejecución de trading para mercados binarios de 5 minutos (M5) en Polymarket, utilizando señales de alta frecuencia y análisis spot de BTC/USDT en Binance.

## Arquitectura del Proyecto

```
polymarket-bot/
├── app/
│   ├── api/            # Endpoints FastAPI para monitoreo y control externo
│   ├── binance/        # Conector WebSocket y REST para datos spot de Binance
│   ├── polymarket/     # Conector para GraphQL / REST / CLOB de Polymarket
│   ├── indicators/     # Motor de cálculo técnico en tiempo real (EMA, VWAP, Delta)
│   ├── predictors/     # Motor cuantitativo de probabilidades y Expected Value (EV)
│   ├── risk/           # Control de riesgo, tamaño de posición y límites
│   ├── execution/      # Motores de ejecución (Paper Trading y Modo Real)
│   ├── strategies/     # Estrategias modulares de trading
│   ├── database/       # ORM (SQLAlchemy), conexiones PostgreSQL y migración
│   ├── dashboard/      # Interfaz visual de terminal interactiva (Textual)
│   ├── logger/         # Configuración centralizada de Loguru
│   ├── config/         # Gestión de configuración mediante Pydantic Settings
│   └── utils/          # Helpers y utilidades generales
├── tests/              # Batería de pruebas unitarias e integración con Pytest
├── docs/               # Documentación técnica adicional
├── data/               # Almacenamiento local de datos temporales
└── logs/               # Archivos de logs rotativos del sistema
```

## Estado del Proyecto

- **Fase 1: Definición de Objetivos** - Completada ✅
- **Fase 2: Diseño de Arquitectura** - Completada ✅
- **Fase 3: Estructura del Proyecto** - En progreso ⏳
