"""
Module para crear un nuevo usuario en el sistema.

Este módulo maneja:
1. Creación de usuario en Supabase Auth
2. Registro del usuario en la tabla 'users' de la base de datos
"""

import os
import uuid
from dotenv import load_dotenv
from supabase import create_client, Client
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import select

# Cargar variables de entorno
load_dotenv()

# Importar modelos después de cargar env vars
from app.core.database import Base, async_session_maker
from app.models.user import User
from app.models.api_key import APIKey
from app.models.user_subscription import UserSubscription
from app.models.subscription_plan import SubscriptionPlan
from app.models.api_usage_log import APIUsageLog
from app.models.api_usage_aggregate import APIUsageAggregate


class UserCreator:
    """Clase para crear usuarios en Supabase y en la base de datos."""
    
    def __init__(self):
        """Inicializar cliente de Supabase."""
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        
        if not self.supabase_url or not self.supabase_key:
            raise ValueError("SUPABASE_URL y SUPABASE_SERVICE_ROLE_KEY son requeridos")
        
        self.supabase: Client = create_client(
            self.supabase_url,
            self.supabase_key
        )
    
    async def create_user(
        self,
        email: str,
        password: str = None,
        db_session: AsyncSession = None
    ) -> dict:
        """
        Crear un nuevo usuario en Supabase y en la base de datos.
        
        Args:
            email (str): Email del usuario
            password (str, optional): Contraseña. Si no se proporciona, se genera una aleatoria
            db_session (AsyncSession, optional): Sesión de BD. Si no se proporciona, se crea una
        
        Returns:
            dict: Información del usuario creado {
                'id': int (ID en BD),
                'email': str,
                'supabase_user_id': str (UUID),
                'created_at': datetime
            }
        """
        
        # Generar contraseña aleatoria si no se proporciona
        if not password:
            password = str(uuid.uuid4())
        
        try:
            # 1. Crear usuario en Supabase Auth
            print(f"\n[USER CREATOR] Creando usuario en Supabase Auth: {email}")
            
            # Intentar crear usuario
            try:
                auth_response = self.supabase.auth.admin.create_user({
                    "email": email,
                    "password": password,
                    "email_confirm": True  # Confirmar email automáticamente
                })
                supabase_user_id = auth_response.user.id
                print(f"✓ Usuario creado en Supabase: {supabase_user_id}")
            except Exception as auth_error:
                # Si el usuario ya existe, intentar obtenerlo y eliminarlo
                if "already been registered" in str(auth_error):
                    print(f"[USER CREATOR] Usuario ya existe, eliminando y recreando...")
                    try:
                        # Buscar usuario por email y eliminarlo
                        users_list = self.supabase.auth.admin.list_users()
                        # users_list es una lista directa
                        for user in users_list:
                            if user.email == email:
                                self.supabase.auth.admin.delete_user(user.id)
                                print(f"[USER CREATOR] Usuario previo eliminado")
                                break
                    except Exception as delete_error:
                        print(f"[USER CREATOR] No se pudo eliminar usuario previo: {delete_error}")
                    
                    # Intentar crear de nuevo
                    try:
                        auth_response = self.supabase.auth.admin.create_user({
                            "email": email,
                            "password": password,
                            "email_confirm": True
                        })
                        supabase_user_id = auth_response.user.id
                        print(f"✓ Usuario creado en Supabase: {supabase_user_id}")
                    except Exception as retry_error:
                        print(f"✗ Error al recrear usuario: {str(retry_error)}")
                        raise
                else:
                    raise auth_error
            
            # 2. Registrar usuario en tabla 'users' de la BD
            print(f"[USER CREATOR] Registrando usuario en base de datos...")
            
            # Usar sesión proporcionada o crear una nueva
            use_own_session = db_session is None
            if use_own_session:
                db_session = async_session_maker()
            
            try:
                # Verificar si el usuario ya existe
                result = await db_session.execute(
                    select(User).where(User.email == email)
                )
                existing_user = result.scalar_one_or_none()
                
                if existing_user:
                    # Eliminar y recrear si existe
                    await db_session.delete(existing_user)
                    await db_session.commit()
                    print(f"[USER CREATOR] Usuario existente eliminado para recrearlo")
                
                # Crear nuevo usuario en BD
                new_user = User(
                    supabase_user_id=supabase_user_id,
                    email=email,
                    role="user",
                    is_active=True
                )
                
                db_session.add(new_user)
                await db_session.commit()
                await db_session.refresh(new_user)
                
                print(f"✓ Usuario registrado en BD con ID: {new_user.id}")
                
                return {
                    'id': new_user.id,
                    'email': new_user.email,
                    'supabase_user_id': new_user.supabase_user_id,
                    'created_at': new_user.created_at,
                    'password': password  # Retornar para posible uso posterior
                }
            
            finally:
                if use_own_session:
                    await db_session.close()
        
        except Exception as e:
            print(f"✗ Error al crear usuario: {str(e)}")
            raise


async def create_user(email: str, password: str = None) -> dict:
    """
    Función helper para crear un usuario fácilmente.
    
    Args:
        email (str): Email del usuario
        password (str, optional): Contraseña del usuario
    
    Returns:
        dict: Información del usuario creado
    """
    creator = UserCreator()
    return await creator.create_user(email, password)


if __name__ == "__main__":
    import asyncio
    
    # Ejemplo de uso
    async def main():
        email = "testuser@example.com"
        try:
            user_info = await create_user(email)
            print(f"\n✓ Usuario creado exitosamente:")
            print(f"  ID: {user_info['id']}")
            print(f"  Email: {user_info['email']}")
            print(f"  Supabase UUID: {user_info['supabase_user_id']}")
        except Exception as e:
            print(f"Error: {e}")
    
    asyncio.run(main())
