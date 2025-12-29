"""
Ejemplos avanzados de uso de los scripts.

Este archivo contiene ejemplos detallados para casos de uso más complejos.
"""

import asyncio
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from scripts.user_creator import UserCreator
from scripts.subscription_assigner import SubscriptionAssigner
from scripts.api_key_creator import APIKeyCreator
from scripts.endpoint_tester import EndpointTester

from app.core.database import async_session_maker
from app.models.user import User
from sqlalchemy import select


# ============================================================================
# EJEMPLO 1: Crear múltiples usuarios con diferentes suscripciones
# ============================================================================

async def example_create_multiple_users():
    """Crear varios usuarios de prueba."""
    
    users_data = [
        "user1@test.com",
        "user2@test.com",
        "user3@test.com",
    ]
    
    created_users = []
    user_creator = UserCreator()
    
    print("\n[EJEMPLO 1] Creando múltiples usuarios...")
    print("-" * 70)
    
    for email in users_data:
        try:
            user = await user_creator.create_user(email)
            created_users.append(user)
            print(f"✓ {email} -> ID {user['id']}")
        except Exception as e:
            print(f"✗ {email} -> Error: {e}")
    
    return created_users


# ============================================================================
# EJEMPLO 2: Crear usuario, suscripción y API key todo junto
# ============================================================================

async def example_complete_user_setup(email: str, db_session: AsyncSession = None):
    """Setup completo de un usuario."""
    
    use_own_session = db_session is None
    if use_own_session:
        db_session = async_session_maker()
    
    try:
        print(f"\n[EJEMPLO 2] Setup completo para {email}")
        print("-" * 70)
        
        # 1. Crear usuario
        user_creator = UserCreator()
        user = await user_creator.create_user(email, db_session=db_session)
        print(f"✓ Usuario creado: {user['id']}")
        
        # 2. Asignar suscripción
        subscription_assigner = SubscriptionAssigner()
        subscription = await subscription_assigner.assign_free_subscription(
            user_id=user['id'],
            db_session=db_session
        )
        print(f"✓ Suscripción asignada: {subscription['subscription_id']}")
        
        # 3. Crear API key
        api_key_creator = APIKeyCreator()
        api_key = await api_key_creator.create_api_key(
            user_id=user['id'],
            key_name=f"API Key for {email}",
            db_session=db_session
        )
        print(f"✓ API key creada: {api_key['id']}")
        
        return {
            'user': user,
            'subscription': subscription,
            'api_key': api_key
        }
    
    finally:
        if use_own_session:
            await db_session.close()


# ============================================================================
# EJEMPLO 3: Probar un endpoint específico múltiples veces
# ============================================================================

async def example_test_specific_endpoint(api_key: str):
    """Probar un endpoint específico múltiples veces."""
    
    print(f"\n[EJEMPLO 3] Probando endpoint específico")
    print("-" * 70)
    
    tester = EndpointTester(api_key)
    
    # Probar solo el endpoint /games 10 veces
    results = []
    for i in range(10):
        result = await tester.test_endpoint(
            endpoint='/games',
            method='GET',
            params={'limit': 5, 'skip': 0}
        )
        results.append(result)
        
        status = "✓" if result['success'] else "✗"
        print(f"{status} Request {i+1}: {result['status_code']}")
        
        # Pausa entre requests
        await asyncio.sleep(0.1)
    
    return results


# ============================================================================
# EJEMPLO 4: Probar diferentes endpoints secuencialmente
# ============================================================================

async def example_test_all_endpoints(api_key: str):
    """Probar varios endpoints y comparar respuestas."""
    
    print(f"\n[EJEMPLO 4] Probando todos los endpoints")
    print("-" * 70)
    
    tester = EndpointTester(api_key)
    
    endpoints_to_test = [
        ('/games', {'limit': 5}),
        ('/players', {'limit': 5}),
        ('/teams', {'limit': 5}),
        ('/me', {}),  # Perfil del usuario
    ]
    
    results = {}
    
    for endpoint, params in endpoints_to_test:
        print(f"\nProbando {endpoint}...")
        result = await tester.test_endpoint(
            endpoint=endpoint,
            params=params if params else None
        )
        
        results[endpoint] = result
        
        if result['success']:
            # Mostrar información de la respuesta
            if isinstance(result['response'], list):
                print(f"  ✓ Retornó lista con {len(result['response'])} items")
            elif isinstance(result['response'], dict):
                print(f"  ✓ Retornó objeto con campos: {list(result['response'].keys())}")
            else:
                print(f"  ✓ Retornó: {type(result['response'])}")
        else:
            print(f"  ✗ Error: {result['error']}")
    
    return results


# ============================================================================
# EJEMPLO 5: Monitorear el progreso del rate limiting
# ============================================================================

async def example_monitor_rate_limits(api_key: str, endpoint: str = '/games'):
    """Hacer requests y monitorear en detalle el rate limiting."""
    
    print(f"\n[EJEMPLO 5] Monitoreando rate limits")
    print("-" * 70)
    
    tester = EndpointTester(api_key)
    
    print(f"Haciendo requests a {endpoint}...")
    print(f"{'#':<5} {'Status':<10} {'Remaining/Min':<15} {'Remaining/Hour':<15} {'Remaining/Day':<15}")
    print("-" * 70)
    
    for i in range(20):
        result = await tester.test_endpoint(
            endpoint=endpoint,
            params={'limit': 5}
        )
        
        info = result['rate_limit_info']
        status = "✓" if result['success'] else "✗"
        
        remaining_min = info.get('remaining_minute', 'N/A')
        remaining_hour = info.get('remaining_hour', 'N/A')
        remaining_day = info.get('remaining_day', 'N/A')
        
        print(f"{i+1:<5} {status:<10} {str(remaining_min):<15} {str(remaining_hour):<15} {str(remaining_day):<15}")
        
        await asyncio.sleep(0.2)


# ============================================================================
# EJEMPLO 6: Obtener información de usuario de la base de datos
# ============================================================================

async def example_query_user_info(user_id: int):
    """Consultar información completa del usuario de la BD."""
    
    print(f"\n[EJEMPLO 6] Consultando información del usuario {user_id}")
    print("-" * 70)
    
    db_session = async_session_maker()
    
    try:
        # Consultar usuario
        result = await db_session.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            print(f"Usuario {user_id} no encontrado")
            return None
        
        print(f"\nUsuario: {user.email}")
        print(f"  ID: {user.id}")
        print(f"  UUID Supabase: {user.supabase_user_id}")
        print(f"  Rol: {user.role}")
        print(f"  Activo: {user.is_active}")
        print(f"  Creado: {user.created_at}")
        
        # API Keys
        print(f"\nAPI Keys ({len(user.api_keys)}):")
        for key in user.api_keys:
            print(f"  - {key.name} (ID: {key.id}, Últimos: ...{key.last_chars})")
        
        # Suscripciones
        print(f"\nSuscripciones ({len(user.subscriptions)}):")
        for sub in user.subscriptions:
            plan_name = sub.plan.plan_name if sub.plan else "N/A"
            print(f"  - Plan: {plan_name}, Status: {sub.status}")
            print(f"    Período: {sub.current_period_start} - {sub.current_period_end}")
        
        return user
    
    finally:
        await db_session.close()


# ============================================================================
# EJEMPLO 7: Ejecutar flujo completo con captura de datos
# ============================================================================

async def example_full_flow_with_logging(email: str):
    """Ejecutar flujo completo con logging detallado."""
    
    print(f"\n[EJEMPLO 7] Flujo completo con logging: {email}")
    print("=" * 70)
    
    # Paso 1: Crear usuario
    print(f"\n[1/4] Creando usuario...")
    setup = await example_complete_user_setup(email)
    user = setup['user']
    api_key = setup['api_key']['api_key']
    
    print(f"Usuario ID: {user['id']}")
    print(f"Email: {user['email']}")
    print(f"API Key: {api_key[:20]}...")
    
    # Paso 2: Esperar un momento
    print(f"\n[2/4] Esperando antes de probar endpoints...")
    await asyncio.sleep(2)
    
    # Paso 3: Probar endpoints
    print(f"\n[3/4] Probando endpoints...")
    test_results = await example_test_all_endpoints(api_key)
    
    # Paso 4: Mostrar resumen
    print(f"\n[4/4] Resumen:")
    print("-" * 70)
    successful = sum(1 for r in test_results.values() if r['success'])
    print(f"Endpoints exitosos: {successful}/{len(test_results)}")
    
    return setup


# ============================================================================
# MAIN: Ejecutar todos los ejemplos
# ============================================================================

async def run_all_examples():
    """Ejecutar todos los ejemplos."""
    
    print("\n" + "=" * 70)
    print(" EJEMPLOS AVANZADOS DE USO".center(70))
    print("=" * 70)
    
    try:
        # Ejemplo 1
        # await example_create_multiple_users()
        
        # Ejemplo 2 & 3 & 4
        setup = await example_complete_user_setup("advanced-example@test.com")
        api_key = setup['api_key']['api_key']
        user_id = setup['user']['id']
        
        # Ejemplo 3
        await example_test_specific_endpoint(api_key)
        
        # Ejemplo 4
        await example_test_all_endpoints(api_key)
        
        # Ejemplo 5
        await example_monitor_rate_limits(api_key)
        
        # Ejemplo 6
        await example_query_user_info(user_id)
        
        print("\n✓ Todos los ejemplos completados")
    
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # Descomentar el ejemplo que quieras ejecutar:
    
    # asyncio.run(example_create_multiple_users())
    # asyncio.run(example_complete_user_setup("test@example.com"))
    # asyncio.run(example_full_flow_with_logging("test@example.com"))
    
    asyncio.run(run_all_examples())
