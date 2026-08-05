"""
Rutas de API REST para la Autenticación y Perfil de Usuarios en la Plataforma SaaS.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database.connection import get_async_session
from app.database.models import UserModel, UserWalletModel
from app.security.auth import hash_password, verify_password, create_access_token, get_current_user_payload
from app.security.vault import EncryptionVault

router = APIRouter(prefix="/api/v1/auth", tags=["SaaS Authentication"])
vault = EncryptionVault()


class UserRegisterSchema(BaseModel):
    email: str
    password: str


class UserLoginSchema(BaseModel):
    email: str
    password: str


class WalletRegisterSchema(BaseModel):
    polygon_address: str
    private_key: str


@router.post("/register")
async def register_user(payload: UserRegisterSchema, db: AsyncSession = Depends(get_async_session)):
    """Registro de nuevo cliente en la plataforma SaaS."""
    email = payload.email.strip().lower()
    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="Formato de correo electrónico inválido.")

    if len(payload.password) < 6:
        raise HTTPException(status_code=400, detail="La contraseña debe contener al menos 6 caracteres.")

    try:
        # Verificar si el usuario ya existe
        result = await db.execute(select(UserModel).where(UserModel.email == email))
        existing_user = result.scalar_one_or_none()
        if existing_user:
            raise HTTPException(status_code=400, detail="El correo electrónico ya se encuentra registrado.")

        # Crear usuario
        hashed_pwd = hash_password(payload.password)
        new_user = UserModel(email=email, password_hash=hashed_pwd, plan_tier="STARTER", role="USER")
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)

        token = create_access_token({"sub": new_user.id, "email": new_user.email, "role": new_user.role, "plan": new_user.plan_tier})
        return {"success": True, "token": token, "user": {"id": new_user.id, "email": new_user.email, "plan_tier": new_user.plan_tier}}

    except HTTPException:
        raise
    except Exception as e:
        # Intentar inicializar tablas si faltan
        try:
            from app.database.connection import init_db
            await init_db()
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=f"Error en la base de datos al registrar usuario. Asegúrate de tener configurado DATABASE_URL ({e})")


@router.post("/login")
async def login_user(payload: UserLoginSchema, db: AsyncSession = Depends(get_async_session)):
    """Inicio de sesión y entrega de JWT token."""
    email = payload.email.strip().lower()
    try:
        result = await db.execute(select(UserModel).where(UserModel.email == email))
        user = result.scalar_one_or_none()

        if not user or not verify_password(payload.password, user.password_hash):
            raise HTTPException(status_code=401, detail="Credenciales incorrectas.")

        if not user.is_active:
            raise HTTPException(status_code=403, detail="Cuenta inactiva. Contacta a soporte.")

        token = create_access_token({"sub": user.id, "email": user.email, "role": user.role, "plan": user.plan_tier})
        return {"success": True, "token": token, "user": {"id": user.id, "email": user.email, "plan_tier": user.plan_tier}}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al iniciar sesión en la base de datos: {e}")


@router.get("/me")
async def get_current_user_profile(
    user_payload: dict = Depends(get_current_user_payload),
    db: AsyncSession = Depends(get_async_session)
):
    """Consulta el perfil y el estado de suscripción del usuario autenticado."""
    user_id = user_payload.get("sub")
    result = await db.execute(select(UserModel).where(UserModel.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=44, detail="Usuario no encontrado.")

    return {
        "user_id": user.id,
        "email": user.email,
        "role": user.role,
        "plan_tier": user.plan_tier,
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }


@router.post("/wallet")
async def register_user_wallet(
    payload: WalletRegisterSchema,
    user_payload: dict = Depends(get_current_user_payload),
    db: AsyncSession = Depends(get_async_session)
):
    """Cifra la clave privada del cliente con AES-256 y la vincula de forma segura a su perfil SaaS."""
    user_id = user_payload.get("sub")
    
    if not payload.private_key.startswith("0x") or len(payload.private_key) != 66:
        raise HTTPException(status_code=400, detail="Formato de clave privada de Polygon inválido (debe comenzar con 0x y tener 66 caracteres).")

    encrypted_key = vault.encrypt(payload.private_key)

    new_wallet = UserWalletModel(
        user_id=user_id,
        polygon_address=payload.polygon_address,
        encrypted_private_key=encrypted_key,
        is_active=True,
    )
    db.add(new_wallet)
    await db.commit()

    return {"success": True, "message": "Billetera Polygon cifrada y vinculada correctamente a la bóveda del usuario."}
