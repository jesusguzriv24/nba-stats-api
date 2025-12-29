"""
Module para asignar una suscripción 'free' a un usuario.

Este módulo maneja:
1. Obtener el plan 'free' de la tabla subscription_plans
2. Crear una suscripción para el usuario
"""

from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pytz import UTC

from app.core.database import async_session_maker
from app.models.subscription_plan import SubscriptionPlan
from app.models.user_subscription import UserSubscription
from app.models.user import User
from app.models.api_key import APIKey
from app.models.api_usage_log import APIUsageLog
from app.models.api_usage_aggregate import APIUsageAggregate


class SubscriptionAssigner:
    """Clase para asignar suscripciones a usuarios."""
    
    async def get_free_plan(self, db_session: AsyncSession) -> SubscriptionPlan:
        """
        Obtener el plan 'free' de la base de datos.
        
        Args:
            db_session (AsyncSession): Sesión de BD
        
        Returns:
            SubscriptionPlan: Plan 'free'
        
        Raises:
            ValueError: Si el plan 'free' no existe
        """
        result = await db_session.execute(
            select(SubscriptionPlan).where(SubscriptionPlan.plan_name == "free")
        )
        plan = result.scalar_one_or_none()
        
        if not plan:
            raise ValueError("Plan 'free' no existe en la base de datos")
        
        return plan
    
    async def assign_free_subscription(
        self,
        user_id: int,
        db_session: AsyncSession = None
    ) -> dict:
        """
        Asignar una suscripción 'free' a un usuario.
        
        Args:
            user_id (int): ID del usuario
            db_session (AsyncSession, optional): Sesión de BD. Si no se proporciona, se crea una
        
        Returns:
            dict: Información de la suscripción {
                'subscription_id': int,
                'user_id': int,
                'plan_name': str,
                'status': str,
                'current_period_end': datetime
            }
        """
        
        # Usar sesión proporcionada o crear una nueva
        use_own_session = db_session is None
        if use_own_session:
            db_session = async_session_maker()
        
        try:
            print(f"\n[SUBSCRIPTION ASSIGNER] Asignando suscripción 'free' al usuario {user_id}")
            
            # Obtener plan 'free'
            free_plan = await self.get_free_plan(db_session)
            print(f"✓ Plan 'free' encontrado: {free_plan.plan_name}")
            
            # Verificar si el usuario ya tiene una suscripción activa
            result = await db_session.execute(
                select(UserSubscription).where(
                    (UserSubscription.user_id == user_id) &
                    (UserSubscription.status == "active")
                )
            )
            existing_subscription = result.scalar_one_or_none()
            
            if existing_subscription:
                print(f"[SUBSCRIPTION ASSIGNER] Usuario ya tiene suscripción activa, cancelando...")
                existing_subscription.status = "cancelled"
                existing_subscription.cancelled_at = datetime.now(UTC)
                await db_session.flush()
            
            # Crear nueva suscripción
            now = datetime.now(UTC)
            # Plan free tiene duración de 30 días
            period_end = now + timedelta(days=30)
            
            new_subscription = UserSubscription(
                user_id=user_id,
                plan_id=free_plan.id,
                status="active",
                billing_cycle="monthly",
                payment_provider=None,
                payment_provider_subscription_id=None,
                current_period_start=now,
                current_period_end=period_end,
                cancelled_at=None,
                cancel_at_period_end=False,
                trial_start=None,
                trial_end=None,
                price_paid_cents=0,  # Free plan no cuesta
                auto_renew=True
            )
            
            db_session.add(new_subscription)
            await db_session.commit()
            await db_session.refresh(new_subscription)
            
            print(f"✓ Suscripción creada con ID: {new_subscription.id}")
            print(f"  Plan: {free_plan.plan_name}")
            print(f"  Estado: {new_subscription.status}")
            print(f"  Vence el: {new_subscription.current_period_end}")
            print(f"  Límites del plan:")
            print(f"    - Por minuto: {free_plan.rate_limit_per_minute}")
            print(f"    - Por hora: {free_plan.rate_limit_per_hour}")
            print(f"    - Por día: {free_plan.rate_limit_per_day}")
            
            return {
                'subscription_id': new_subscription.id,
                'user_id': new_subscription.user_id,
                'plan_name': free_plan.plan_name,
                'status': new_subscription.status,
                'current_period_end': new_subscription.current_period_end,
                'rate_limits': {
                    'per_minute': free_plan.rate_limit_per_minute,
                    'per_hour': free_plan.rate_limit_per_hour,
                    'per_day': free_plan.rate_limit_per_day
                }
            }
        
        finally:
            if use_own_session:
                await db_session.close()


async def assign_free_subscription(user_id: int) -> dict:
    """
    Función helper para asignar suscripción 'free' a un usuario.
    
    Args:
        user_id (int): ID del usuario
    
    Returns:
        dict: Información de la suscripción
    """
    assigner = SubscriptionAssigner()
    return await assigner.assign_free_subscription(user_id)


if __name__ == "__main__":
    import asyncio
    
    # Ejemplo de uso
    async def main():
        try:
            # Este ejemplo requiere que exista un usuario con ID 1
            subscription_info = await assign_free_subscription(user_id=1)
            print(f"\n✓ Suscripción asignada exitosamente:")
            print(f"  ID: {subscription_info['subscription_id']}")
            print(f"  Plan: {subscription_info['plan_name']}")
        except Exception as e:
            print(f"Error: {e}")
    
    asyncio.run(main())
