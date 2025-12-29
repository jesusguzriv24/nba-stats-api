"""
Script principal que orquesta todo el flujo:
1. Crear un usuario
2. Asignar suscripción 'free'
3. Crear una API key
4. Usar la API key para hacer requests hasta alcanzar el límite

Uso:
    python main.py [email] [--api-url http://localhost:8000] [--limit-window minute]

Ejemplos:
    python main.py test@example.com
    python main.py test@example.com --api-url http://localhost:8000 --limit-window hour
"""

import sys
import asyncio
import argparse
import os
from pathlib import Path
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Agregar el directorio raíz al path para importar módulos de la app
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.user_creator import UserCreator
from scripts.subscription_assigner import SubscriptionAssigner
from scripts.api_key_creator import APIKeyCreator
from scripts.endpoint_tester import EndpointTester
from app.core.database import async_session_maker


class TestFlowOrchestrator:
    """Orquestador del flujo completo de pruebas."""
    
    def __init__(self, api_base_url: str = "https://bestat-nba-api.onrender.com/api/v1"):
        """
        Inicializar el orquestador.
        
        Args:
            api_base_url (str): URL base de la API
        """
        self.api_base_url = api_base_url
        self.user_info = None
        self.subscription_info = None
        self.api_key_info = None
        self.test_results = None
    
    async def get_jwt_token(self, email: str, password: str) -> str:
        """
        Obtener JWT token del usuario usando Supabase.
        
        Args:
            email (str): Email del usuario
            password (str): Contraseña del usuario
        
        Returns:
            str: JWT token
        """
        from supabase import create_client
        
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_ANON_KEY")
        
        if not supabase_url or not supabase_key:
            raise ValueError("SUPABASE_URL y SUPABASE_ANON_KEY son requeridos")
        
        supabase = create_client(supabase_url, supabase_key)
        
        try:
            auth_response = supabase.auth.sign_in_with_password({
                "email": email,
                "password": password
            })
            
            if auth_response.session:
                return auth_response.session.access_token
            else:
                raise ValueError(f"Error obteniendo token: {auth_response}")
        except Exception as e:
            print(f"[ORCHEST] Error obteniendo JWT: {e}")
            raise
    
    async def run_complete_flow(
        self,
        email: str,
        limit_window: str = "minute"
    ) -> dict:
        """
        Ejecutar el flujo completo.
        
        Args:
            email (str): Email para el nuevo usuario
            limit_window (str): Ventana de límite a probar ('minute', 'hour', 'day')
        
        Returns:
            dict: Resumen de todo el proceso
        """
        
        print("\n" + "=" * 70)
        print(" NBA STATS API - FLUJO COMPLETO DE PRUEBAS".center(70))
        print("=" * 70)
        
        db_session = async_session_maker()
        
        try:
            # PASO 1: Crear usuario
            print("\n" + "─" * 70)
            print(" PASO 1: CREAR USUARIO".ljust(70))
            print("─" * 70)
            
            user_creator = UserCreator()
            self.user_info = await user_creator.create_user(email, db_session=db_session)
            print(f"\n✓ Usuario creado:")
            print(f"  ID en BD: {self.user_info['id']}")
            print(f"  Email: {self.user_info['email']}")
            print(f"  Supabase UUID: {self.user_info['supabase_user_id']}")
            
            # PASO 2: Asignar suscripción 'free'
            print("\n" + "─" * 70)
            print(" PASO 2: ASIGNAR SUSCRIPCIÓN 'FREE'".ljust(70))
            print("─" * 70)
            
            subscription_assigner = SubscriptionAssigner()
            self.subscription_info = await subscription_assigner.assign_free_subscription(
                user_id=self.user_info['id'],
                db_session=db_session
            )
            print(f"\n✓ Suscripción asignada:")
            print(f"  ID: {self.subscription_info['subscription_id']}")
            print(f"  Plan: {self.subscription_info['plan_name']}")
            print(f"  Estado: {self.subscription_info['status']}")
            print(f"  Límites:")
            print(f"    - Por minuto: {self.subscription_info['rate_limits']['per_minute']}")
            print(f"    - Por hora: {self.subscription_info['rate_limits']['per_hour']}")
            print(f"    - Por día: {self.subscription_info['rate_limits']['per_day']}")
            
            # PASO 3: Crear API key
            print("\n" + "─" * 70)
            print(" PASO 3: CREAR API KEY".ljust(70))
            print("─" * 70)
            
            api_key_creator = APIKeyCreator()
            self.api_key_info = await api_key_creator.create_api_key(
                user_id=self.user_info['id'],
                key_name="Test API Key",
                db_session=db_session
            )
            print(f"\n✓ API Key creada:")
            print(f"  ID: {self.api_key_info['id']}")
            print(f"  Nombre: {self.api_key_info['name']}")
            print(f"  Plan: {self.api_key_info['rate_limit_plan']}")
            
            # PASO 4: Usar API key para probar endpoints hasta límite
            print("\n" + "─" * 70)
            print(f" PASO 4: PROBAR ENDPOINTS HASTA LÍMITE ({limit_window.upper()})".ljust(70))
            print("─" * 70)
            
            # Obtener JWT token para autenticación
            print(f"\n[ORCHEST] Obteniendo JWT token...")
            try:
                jwt_token = await self.get_jwt_token(
                    email=self.user_info['email'],
                    password=self.user_info['password']
                )
                print(f"✓ JWT token obtenido")
            except Exception as jwt_error:
                print(f"⚠️  No se pudo obtener JWT: {jwt_error}")
                print(f"    Usando API key en su lugar")
                jwt_token = None
            
            endpoint_tester = EndpointTester(
                api_key=self.api_key_info['api_key'],
                jwt_token=jwt_token,
                api_base_url=self.api_base_url
            )
            
            # Endpoints a probar
            endpoints = [
                {'endpoint': '/games', 'method': 'GET', 'params': {'limit': 5, 'skip': 0}},
                {'endpoint': '/players', 'method': 'GET', 'params': {'limit': 5, 'skip': 0}},
                {'endpoint': '/teams', 'method': 'GET', 'params': {'limit': 5}},
            ]
            
            self.test_results = await endpoint_tester.test_endpoints_until_limit(
                endpoints=endpoints,
                limit_window=limit_window
            )
            
            # RESUMEN FINAL
            print("\n" + "=" * 70)
            print(" RESUMEN FINAL".center(70))
            print("=" * 70)
            
            successful_requests = sum(1 for r in self.test_results if r['success'])
            failed_requests = len(self.test_results) - successful_requests
            
            print(f"\n✓ Flujo completado exitosamente")
            print(f"\n  Usuario:")
            print(f"    Email: {self.user_info['email']}")
            print(f"    ID: {self.user_info['id']}")
            print(f"\n  Suscripción:")
            print(f"    Plan: {self.subscription_info['plan_name']}")
            print(f"    Límite por minuto: {self.subscription_info['rate_limits']['per_minute']}")
            print(f"\n  Requests realizados:")
            print(f"    Total: {len(self.test_results)}")
            print(f"    Exitosos: {successful_requests}")
            print(f"    Fallidos: {failed_requests}")
            print(f"\n  API Key:")
            print(f"    Últimos 8 caracteres: ...{self.api_key_info['last_chars']}")
            print(f"    Clave completa (GUARDADA DURANTE LA SESIÓN):")
            print(f"    {self.api_key_info['api_key']}")
            
            print("\n" + "=" * 70 + "\n")
            
            return {
                'user': self.user_info,
                'subscription': self.subscription_info,
                'api_key': self.api_key_info,
                'test_results': self.test_results,
                'summary': {
                    'total_requests': len(self.test_results),
                    'successful_requests': successful_requests,
                    'failed_requests': failed_requests
                }
            }
        
        except Exception as e:
            print(f"\n✗ Error durante el flujo: {str(e)}")
            import traceback
            traceback.print_exc()
            raise
        
        finally:
            await db_session.close()


async def main():
    """Función principal."""
    
    # Parsear argumentos de línea de comandos
    parser = argparse.ArgumentParser(
        description="NBA Stats API - Flujo completo de pruebas"
    )
    parser.add_argument(
        "email",
        help="Email del usuario a crear"
    )
    parser.add_argument(
        "--api-url",
        default="https://bestat-nba-api.onrender.com/api/v1",
        help="URL base de la API (default: https://bestat-nba-api.onrender.com/api/v1)"
    )
    parser.add_argument(
        "--limit-window",
        default="minute",
        choices=["minute", "hour", "day"],
        help="Ventana de límite a probar (default: minute)"
    )
    
    args = parser.parse_args()
    
    try:
        orchestrator = TestFlowOrchestrator(api_base_url=args.api_url)
        result = await orchestrator.run_complete_flow(
            email=args.email,
            limit_window=args.limit_window
        )
        
        # Retornar código de salida exitoso
        sys.exit(0)
    
    except Exception as e:
        print(f"\n✗ Error fatal: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
