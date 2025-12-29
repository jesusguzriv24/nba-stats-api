"""
Module para probar endpoints con la API key hasta alcanzar el límite de rate limiting.

Este módulo maneja:
1. Hacer requests a varios endpoints usando la API key
2. Monitorear los límites de rate limiting
3. Continuar hasta alcanzar el límite configurado
"""

import httpx
import asyncio
from typing import List, Dict
from datetime import datetime

# URL base de la API (ajustar según tu configuración)
API_BASE_URL = "https://bestat-nba-api.onrender.com/api/v1"


class EndpointTester:
    """Clase para probar endpoints con la API key."""
    
    def __init__(self, api_key: str = None, jwt_token: str = None, api_base_url: str = API_BASE_URL):
        """
        Inicializar el tester de endpoints.
        
        Args:
            api_key (str): API key a usar
            jwt_token (str): JWT token (alternativa a API key)
            api_base_url (str): URL base de la API
        """
        self.api_key = api_key
        self.jwt_token = jwt_token
        self.api_base_url = api_base_url
        
        # Construir headers
        self.headers = {"Content-Type": "application/json"}
        if api_key:
            self.headers["X-API-Key"] = api_key
        elif jwt_token:
            self.headers["Authorization"] = f"Bearer {jwt_token}"
        
        self.request_count = 0
        self.rate_limit_info = {}
    
    async def test_endpoint(
        self,
        endpoint: str,
        method: str = "GET",
        params: Dict = None
    ) -> Dict:
        """
        Hacer un request a un endpoint.
        
        Args:
            endpoint (str): Ruta del endpoint (ej: "/games")
            method (str): Método HTTP
            params (Dict): Parámetros de query o body
        
        Returns:
            Dict: Respuesta y información de rate limiting
        """
        url = f"{self.api_base_url}{endpoint}"
        
        try:
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                if method == "GET":
                    response = await client.get(url, headers=self.headers, params=params)
                elif method == "POST":
                    response = await client.post(url, headers=self.headers, json=params)
                else:
                    response = await client.request(method, url, headers=self.headers)
            
            self.request_count += 1
            
            # Extraer información de rate limiting de los headers
            rate_limit_info = {
                'limit_minute': response.headers.get('X-RateLimit-Limit-Minute', 'N/A'),
                'remaining_minute': response.headers.get('X-RateLimit-Remaining-Minute', 'N/A'),
                'reset_minute': response.headers.get('X-RateLimit-Reset-Minute', 'N/A'),
                'limit_hour': response.headers.get('X-RateLimit-Limit-Hour', 'N/A'),
                'remaining_hour': response.headers.get('X-RateLimit-Remaining-Hour', 'N/A'),
                'reset_hour': response.headers.get('X-RateLimit-Reset-Hour', 'N/A'),
                'limit_day': response.headers.get('X-RateLimit-Limit-Day', 'N/A'),
                'remaining_day': response.headers.get('X-RateLimit-Remaining-Day', 'N/A'),
                'reset_day': response.headers.get('X-RateLimit-Reset-Day', 'N/A'),
            }
            
            self.rate_limit_info = rate_limit_info
            
            return {
                'success': response.status_code == 200,
                'status_code': response.status_code,
                'endpoint': endpoint,
                'request_number': self.request_count,
                'timestamp': datetime.now().isoformat(),
                'rate_limit_info': rate_limit_info,
                'response': response.json() if response.status_code == 200 else response.text,
                'error': None if response.status_code == 200 else f"HTTP {response.status_code}"
            }
        
        except Exception as e:
            return {
                'success': False,
                'status_code': None,
                'endpoint': endpoint,
                'request_number': self.request_count,
                'timestamp': datetime.now().isoformat(),
                'rate_limit_info': self.rate_limit_info,
                'response': None,
                'error': str(e)
            }
    
    async def test_endpoints_until_limit(
        self,
        endpoints: List[Dict] = None,
        limit_window: str = "minute"
    ) -> List[Dict]:
        """
        Hacer requests a los endpoints hasta alcanzar el límite de rate limiting.
        
        Args:
            endpoints (List[Dict]): Lista de endpoints a probar
                Ejemplo: [
                    {'endpoint': '/games', 'method': 'GET'},
                    {'endpoint': '/players', 'method': 'GET'},
                ]
            limit_window (str): Ventana de límite a alcanzar ('minute', 'hour', 'day')
        
        Returns:
            List[Dict]: Lista de resultados de requests
        """
        
        if endpoints is None:
            # Endpoints por defecto
            endpoints = [
                {'endpoint': '/games', 'method': 'GET', 'params': {'limit': 10}},
                {'endpoint': '/players', 'method': 'GET', 'params': {'limit': 10}},
                {'endpoint': '/teams', 'method': 'GET', 'params': {'limit': 10}},
                {'endpoint': '/stats', 'method': 'GET', 'params': {'limit': 10}},
            ]
        
        results = []
        endpoint_index = 0
        
        print(f"\n[ENDPOINT TESTER] Iniciando pruebas de endpoints")
        print(f"[ENDPOINT TESTER] Límite a alcanzar: {limit_window}")
        print(f"[ENDPOINT TESTER] Endpoints: {len(endpoints)}")
        print("-" * 70)
        
        while True:
            # Seleccionar siguiente endpoint (rotar)
            endpoint_config = endpoints[endpoint_index % len(endpoints)]
            endpoint = endpoint_config['endpoint']
            method = endpoint_config.get('method', 'GET')
            params = endpoint_config.get('params', {})
            
            # Hacer request
            result = await self.test_endpoint(endpoint, method, params)
            results.append(result)
            
            # Mostrar resultado
            self._print_request_result(result)
            
            # Verificar límite
            remaining_key = f"remaining_{limit_window}"
            if remaining_key in self.rate_limit_info:
                try:
                    remaining = int(self.rate_limit_info[remaining_key])
                    limit_key = f"limit_{limit_window}"
                    limit = int(self.rate_limit_info.get(limit_key, remaining + 1))
                    
                    if remaining == 0:
                        print(f"\n{'='*70}")
                        print(f"✓ LÍMITE DE RATE LIMITING ALCANZADO")
                        print(f"  Ventana: {limit_window}")
                        print(f"  Total de requests: {self.request_count}")
                        print(f"{'='*70}\n")
                        break
                except (ValueError, TypeError):
                    pass
            
            # Pausa breve entre requests
            await asyncio.sleep(0.5)
            
            # Avanzar al siguiente endpoint
            endpoint_index += 1
        
        return results
    
    def _print_request_result(self, result: Dict):
        """Mostrar resultado de un request de forma legible."""
        
        status = "✓" if result['success'] else "✗"
        
        print(f"{status} Request #{result['request_number']}: {result['endpoint']} - {result['status_code']}")
        
        # Mostrar límites
        if result['rate_limit_info']:
            info = result['rate_limit_info']
            if info.get('remaining_minute') != 'N/A':
                print(f"  Por minuto: {info.get('remaining_minute')}/{info.get('limit_minute')} restantes")
            if info.get('remaining_hour') != 'N/A':
                print(f"  Por hora: {info.get('remaining_hour')}/{info.get('limit_hour')} restantes")
            if info.get('remaining_day') != 'N/A':
                print(f"  Por día: {info.get('remaining_day')}/{info.get('limit_day')} restantes")
        
        if result['error']:
            print(f"  Error: {result['error']}")


async def test_endpoints_until_limit(
    api_key: str,
    endpoints: List[Dict] = None,
    limit_window: str = "minute"
) -> List[Dict]:
    """
    Función helper para probar endpoints hasta alcanzar límite.
    
    Args:
        api_key (str): API key a usar
        endpoints (List[Dict]): Lista de endpoints
        limit_window (str): Ventana de límite ('minute', 'hour', 'day')
    
    Returns:
        List[Dict]: Resultados de los requests
    """
    tester = EndpointTester(api_key)
    return await tester.test_endpoints_until_limit(endpoints, limit_window)


if __name__ == "__main__":
    import asyncio
    
    # Ejemplo de uso
    async def main():
        api_key = "bestat_nba_YOUR_API_KEY_HERE"
        
        try:
            # Endpoints a probar
            endpoints = [
                {'endpoint': '/games', 'method': 'GET', 'params': {'limit': 5}},
                {'endpoint': '/players', 'method': 'GET', 'params': {'limit': 5}},
            ]
            
            results = await test_endpoints_until_limit(
                api_key=api_key,
                endpoints=endpoints,
                limit_window="minute"  # O "hour", "day"
            )
            
            print(f"\n✓ Pruebas completadas: {len(results)} requests realizados")
        
        except Exception as e:
            print(f"Error: {e}")
    
    asyncio.run(main())
