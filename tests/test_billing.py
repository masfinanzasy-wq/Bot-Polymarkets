"""
Pruebas unitarias para el módulo de facturación, checkout y planes de membresía SaaS.
"""
import pytest
from app.billing import BillingEngine, PlanTier


class TestSaaSBilling:
    """Pruebas del catálogo de planes y sesiones de checkout."""

    def test_get_all_plans_returns_catalog(self):
        plans = BillingEngine.get_all_plans()
        assert len(plans) == 3
        tiers = [p.tier for p in plans]
        assert PlanTier.STARTER in tiers
        assert PlanTier.PRO in tiers
        assert PlanTier.WHALE in tiers

    def test_pro_plan_pricing_and_features(self):
        pro_plan = BillingEngine.PLANS[PlanTier.PRO]
        assert pro_plan.price_usd == 49.0
        assert pro_plan.max_capital_usd == 1000.0
        assert pro_plan.is_popular is True

    def test_create_checkout_session_stripe(self):
        resp = BillingEngine.create_checkout_session(
            user_id=10,
            user_email="trader@test.com",
            plan_tier=PlanTier.PRO,
            payment_method="stripe"
        )
        assert resp.success is True
        assert "stripe.com" in resp.checkout_url
        assert resp.plan_tier == PlanTier.PRO
        assert "cs_test_" in resp.session_id

    def test_create_checkout_session_crypto(self):
        resp = BillingEngine.create_checkout_session(
            user_id=12,
            user_email="crypto@test.com",
            plan_tier=PlanTier.WHALE,
            payment_method="crypto_usdc"
        )
        assert resp.success is True
        assert "coinbase.com" in resp.checkout_url
        assert resp.plan_tier == PlanTier.WHALE
