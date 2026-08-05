"""
Rutas de API REST para la Gestión de Planes, Checkout y Webhooks de Suscripción SaaS.
"""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.billing import BillingEngine, PlanTier, CheckoutRequest, CheckoutResponse
from app.database.connection import get_async_session
from app.database.models import UserModel
from app.security.auth import get_current_user_payload
from app.logger.logger import sys_logger

router = APIRouter(prefix="/api/v1/billing", tags=["SaaS Billing & Subscriptions"])


@router.get("/plans")
async def get_subscription_plans():
    """Devuelve el catálogo completo de planes de membresía SaaS."""
    return {"success": True, "plans": BillingEngine.get_all_plans()}


@router.post("/checkout", response_model=CheckoutResponse)
async def create_checkout_session(
    payload: CheckoutRequest,
    user_payload: dict = Depends(get_current_user_payload),
    db: AsyncSession = Depends(get_async_session)
):
    """Crea una URL de pasarela de pago (Stripe o Cripto USDC) para la suscripción del usuario."""
    user_id = user_payload.get("sub")
    user_email = user_payload.get("email", "user@example.com")

    if payload.plan_tier == PlanTier.STARTER:
        # Plan gratuito
        result = await db.execute(select(UserModel).where(UserModel.id == user_id))
        user = result.scalar_one_or_none()
        if user:
            user.plan_tier = PlanTier.STARTER.value
            await db.commit()
        return CheckoutResponse(
            success=True,
            checkout_url="",
            session_id=f"starter_free_{user_id}",
            plan_tier=PlanTier.STARTER,
            message="Tu cuenta se encuentra activa en el Plan Starter Gratuito."
        )

    try:
        response = BillingEngine.create_checkout_session(
            user_id=user_id,
            user_email=user_email,
            plan_tier=payload.plan_tier,
            payment_method=payload.payment_method
        )
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al generar sesión de pago: {e}")


@router.post("/webhook")
async def payment_webhook(request: Request, db: AsyncSession = Depends(get_async_session)):
    """
    Webhook de recepción de pagos (Stripe / Coinbase Commerce).
    Actualiza automáticamente el plan_tier del usuario en la base de datos Supabase.
    """
    try:
        body = await request.json()
        event_type = body.get("type", "")
        data = body.get("data", {})

        sys_logger.info(f"Billing Webhook recibido: {event_type}")

        # Simulación / Evento Stripe checkout.session.completed
        if event_type in ["checkout.session.completed", "payment.success"]:
            user_id = data.get("user_id") or data.get("client_reference_id")
            new_plan = data.get("plan_tier", "PRO")

            if user_id:
                result = await db.execute(select(UserModel).where(UserModel.id == int(user_id)))
                user = result.scalar_one_or_none()
                if user:
                    user.plan_tier = new_plan
                    await db.commit()
                    sys_logger.info(f"PLAN ACTUALIZADO: Usuario #{user_id} subió a Plan {new_plan}")
                    return {"success": True, "message": f"Usuario #{user_id} actualizado a Plan {new_plan}"}

        return {"success": True, "message": "Evento procesado sin modificaciones"}
    except Exception as e:
        sys_logger.error(f"Error procesando webhook de pago: {e}")
        return {"success": False, "error": str(e)}
