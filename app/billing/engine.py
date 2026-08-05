"""
Motor de facturación y pasarela de pagos para Stripe y Crypto (USDC en Polygon).
"""
import time
from typing import List, Optional, Dict, Any
from app.billing.schemas import PlanTier, PlanInfo, CheckoutResponse
from app.logger.logger import sys_logger


class BillingEngine:
    """
    Gestor de membresías y pasarelas de pago SaaS.
    """

    PLANS: Dict[PlanTier, PlanInfo] = {
        PlanTier.STARTER: PlanInfo(
            tier=PlanTier.STARTER,
            name="Starter (Gratuito)",
            price_usd=0.0,
            max_capital_usd=100.0,
            features=[
                "Paper Trading ilimitado",
                "Indicadores técnicos en tiempo real",
                "Dashboard Web Glassmorphism",
                "Soporte de la comunidad"
            ],
            is_popular=False,
        ),
        PlanTier.PRO: PlanInfo(
            tier=PlanTier.PRO,
            name="Pro Trader",
            price_usd=49.0,
            max_capital_usd=1000.0,
            features=[
                "Live Trading con dinero real en Polygon",
                "Capital de hasta $1,000.00 USD",
                "Alertas instantáneas por Telegram",
                "Gestión de riesgo dinámico Kelly",
                "Optimización de estrategias 24/7"
            ],
            is_popular=True,
        ),
        PlanTier.WHALE: PlanInfo(
            tier=PlanTier.WHALE,
            name="Whale VIP",
            price_usd=149.0,
            max_capital_usd=100000.0,
            features=[
                "Capital de trading ilimitado",
                "Ejecución multi-cripto (BTC, ETH, SOL)",
                "Bóveda AES-256 prioritaria",
                "Bot de Telegram exclusivo",
                "Soporte técnico VIP dedicado"
            ],
            is_popular=False,
        ),
    }

    @classmethod
    def get_all_plans(cls) -> List[PlanInfo]:
        """Devuelve el catálogo completo de planes de suscripción."""
        return list(cls.PLANS.values())

    @classmethod
    def create_checkout_session(cls, user_id: int, user_email: str, plan_tier: PlanTier, payment_method: str = "stripe") -> CheckoutResponse:
        """
        Genera una sesión de checkout para Stripe o Pago en Cripto (USDC).
        """
        plan = cls.PLANS.get(plan_tier)
        if not plan:
            raise ValueError(f"Plan no válido: {plan_tier}")

        session_id = f"cs_test_{int(time.time())}_{user_id}"

        if payment_method == "crypto_usdc":
            checkout_url = f"https://pay.coinbase.com/checkout?session={session_id}&amount={plan.price_usd}"
            msg = "Sesión de checkout Cripto (USDC en Polygon) generada exitosamente."
        else:
            checkout_url = f"https://checkout.stripe.com/c/pay/{session_id}"
            msg = "Sesión de checkout de Stripe generada exitosamente."

        sys_logger.info(f"Billing: Checkout creado para usuario #{user_id} ({user_email}) -> Plan {plan_tier.value} (${plan.price_usd}/mo)")
        
        return CheckoutResponse(
            success=True,
            checkout_url=checkout_url,
            session_id=session_id,
            plan_tier=plan_tier,
            message=msg,
        )
