"""
Module para crear una API key para un usuario.

Este módulo maneja:
1. Generar una API key segura
2. Guardarla en la tabla 'api_keys'
3. Retornar la clave completa (solo una vez)
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import async_session_maker
from app.core.security import generate_api_key
from app.models.api_key import APIKey
from app.models.subscription_plan import SubscriptionPlan
from app.models.user_subscription import UserSubscription
from app.models.user import User
from app.models.api_usage_log import APIUsageLog
from app.models.api_usage_aggregate import APIUsageAggregate


class APIKeyCreator:
    """Clase para crear API keys para usuarios."""
    
    async def create_api_key(
        self,
        user_id: int,
        key_name: str = "Default API Key",
        db_session: AsyncSession = None
    ) -> dict:
        """
        Crear una nueva API key para un usuario.
        
        Args:
            user_id (int): ID del usuario
            key_name (str): Nombre descriptivo de la API key
            db_session (AsyncSession, optional): Sesión de BD. Si no se proporciona, se crea una
        
        Returns:
            dict: Información de la API key {
                'id': int,
                'user_id': int,
                'name': str,
                'api_key': str (clave completa - MOSTRADA SOLO ESTA VEZ),
                'last_chars': str,
                'rate_limit_plan': str,
                'created_at': datetime
            }
        """
        
        # Usar sesión proporcionada o crear una nueva
        use_own_session = db_session is None
        if use_own_session:
            db_session = async_session_maker()
        
        try:
            print(f"\n[API KEY CREATOR] Creando API key para usuario {user_id}")
            
            # Obtener plan actual del usuario (debería ser 'free')
            result = await db_session.execute(
                select(SubscriptionPlan).where(SubscriptionPlan.plan_name == "free")
            )
            free_plan = result.scalar_one_or_none()
            
            if not free_plan:
                raise ValueError("Plan 'free' no existe en la base de datos")
            
            # Generar API key segura
            key_data = generate_api_key()
            print(f"✓ API key generada con prefijo 'bestat_nba_'")
            
            # Crear registro en BD
            new_api_key = APIKey(
                user_id=user_id,
                key_hash=key_data["key_hash"],
                name=key_name,
                last_chars=key_data["last_chars"],
                is_active=True,
                rate_limit_plan=free_plan.plan_name,
                scopes=None,
                allowed_ips=None,
                expires_at=None
            )
            
            db_session.add(new_api_key)
            await db_session.commit()
            await db_session.refresh(new_api_key)
            
            print(f"✓ API key guardada en BD con ID: {new_api_key.id}")
            print(f"  Nombre: {new_api_key.name}")
            print(f"  Últimos 8 caracteres: ...{new_api_key.last_chars}")
            print(f"  Plan de límites: {new_api_key.rate_limit_plan}")
            print(f"  Límites:")
            print(f"    - Por minuto: {free_plan.rate_limit_per_minute}")
            print(f"    - Por hora: {free_plan.rate_limit_per_hour}")
            print(f"    - Por día: {free_plan.rate_limit_per_day}")
            
            print(f"\n⚠️  IMPORTANTE: La API key solo se muestra UNA VEZ")
            print(f"    Guárdala en un lugar seguro, no podrás verla nuevamente")
            print(f"\n📋 API Key:")
            print(f"    {key_data['key']}")
            print(f"\n")
            
            return {
                'id': new_api_key.id,
                'user_id': new_api_key.user_id,
                'name': new_api_key.name,
                'api_key': key_data['key'],  # Clave completa (SOLO AHORA)
                'last_chars': new_api_key.last_chars,
                'is_active': new_api_key.is_active,
                'rate_limit_plan': new_api_key.rate_limit_plan,
                'created_at': new_api_key.created_at
            }
        
        finally:
            if use_own_session:
                await db_session.close()


async def create_api_key(
    user_id: int,
    key_name: str = "Default API Key"
) -> dict:
    """
    Función helper para crear una API key.
    
    Args:
        user_id (int): ID del usuario
        key_name (str): Nombre de la API key
    
    Returns:
        dict: Información de la API key
    """
    creator = APIKeyCreator()
    return await creator.create_api_key(user_id, key_name)


if __name__ == "__main__":
    import asyncio
    
    # Ejemplo de uso
    async def main():
        try:
            # Este ejemplo requiere que exista un usuario con ID 1
            api_key_info = await create_api_key(
                user_id=1,
                key_name="Test Key"
            )
            print(f"\n✓ API key creada exitosamente:")
            print(f"  ID: {api_key_info['id']}")
            print(f"  Clave: {api_key_info['api_key']}")
        except Exception as e:
            print(f"Error: {e}")
    
    asyncio.run(main())
