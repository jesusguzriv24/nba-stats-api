# Scripts for NBA Stats API Testing

Este directorio contiene scripts modulares para automatizar el testing y validación de la API de NBA Stats.

## 📋 Descripción General

Los scripts están diseñados para ejecutar un flujo completo de pruebas:

1. **Crear un usuario** en la base de datos
2. **Asignar una suscripción** (Free plan)
3. **Generar una API key** para el usuario
4. **Realizar requests a la API** hasta alcanzar el límite de rate limiting

## 📁 Estructura de Módulos

### 1. `user_generator.py`
Crea usuarios en la tabla `users` sin necesidad de Supabase Auth.

**Funciones principales:**
- `create_test_user(email, role="user", is_active=True)` - Crea un nuevo usuario
- `get_user_by_email(email)` - Busca un usuario por email
- `get_user_by_id(user_id)` - Busca un usuario por ID

**Uso independiente:**
```bash
python scripts/user_generator.py
```

### 2. `subscription_generator.py`
Asigna suscripciones a usuarios, vinculando con el plan "free".

**Funciones principales:**
- `assign_free_subscription(user)` - Asigna plan free a un usuario
- `get_or_create_free_plan()` - Crea el plan free si no existe
- `get_user_subscription(user_id)` - Obtiene suscripción activa del usuario
- `get_subscription_plan(plan_name)` - Obtiene un plan por nombre

**Detalles del Plan Free:**
```
- Rate Limit por Minuto: 10
- Rate Limit por Hora: 100
- Rate Limit por Día: 1000
- Precio: $0 USD
```

**Uso independiente:**
```bash
python scripts/subscription_generator.py
```

### 3. `apikey_generator.py`
Genera API keys seguras usando hashing Argon2.

**Funciones principales:**
- `create_api_key_for_user(user, name, rate_limit_plan, expires_in_days)` - Genera nueva API key
- `get_user_api_keys(user_id)` - Obtiene todas las API keys activas del usuario
- `revoke_api_key(api_key_id)` - Revoca una API key
- `get_api_key_by_id(api_key_id)` - Obtiene una API key por ID

**Características de Seguridad:**
- Las keys se hashean con Argon2 (nunca se almacenan en texto plano)
- Solo se muestran una vez al crear
- Se guardan los últimos 8 caracteres para referencia en UI
- Soportan expiración configurable

**Uso independiente:**
```bash
python scripts/apikey_generator.py
```

### 4. `api_client.py`
Cliente HTTP para hacer requests autenticados a la API y testear rate limiting.

**Clase principal: `APIClient`**
- Constructor: `APIClient(base_url, api_key, rate_limit_per_minute)`
- `make_request(endpoint, method, params, json_data)` - Realiza un request
- `test_endpoints_until_rate_limited(endpoints, delay)` - Testea hasta alcanzar límite
- `get_summary()` - Resumen de actividad
- `print_summary()` - Imprime resumen formateado

**Características:**
- Autenticación automática vía header `X-API-Key`
- Detección de rate limiting (HTTP 429)
- Logging de requests
- Seguimiento de tiempos y estadísticas

**Uso independiente:**
```bash
python scripts/api_client.py
```

### 5. `main_test_flow.py`
Orquestador principal que ejecuta el flujo completo.

**Flujo ejecutado:**
```
1. Crear usuario con email único (basado en timestamp)
2. Asignar suscripción free al usuario
3. Generar API key para el usuario
4. Testear API endpoints hasta alcanzar rate limit
5. Mostrar reporte detallado
```

**Configuración ajustable:**
```python
API_BASE_URL = "http://localhost:8000"
API_ENDPOINTS = ["/v1/games/", "/v1/players/", "/v1/teams/"]
DELAY_BETWEEN_REQUESTS = 0.05  # segundos
```

## 🚀 Instalación y Uso

### Requisitos Previos
1. **API ejecutándose:** La API debe estar en ejecución en `http://localhost:8000`
2. **PostgreSQL:** Base de datos configurada (ver `.env`)
3. **Redis:** Redis ejecutándose para rate limiting
4. **Python:** Dependencias instaladas (`pip install -r requirements.txt`)

### Opción 1: Ejecutar Flujo Completo
```bash
# Desde la raíz del proyecto
python -m scripts.main_test_flow

# O directamente
cd scripts && python main_test_flow.py
```

### Opción 2: Ejecutar Módulos Individuales
```bash
# Crear usuario
python scripts/user_generator.py

# Crear suscripción
python scripts/subscription_generator.py

# Generar API key
python scripts/apikey_generator.py

# Testear API
python scripts/api_client.py
```

### Opción 3: Usar en tu Propio Script
```python
import asyncio
from scripts.user_generator import create_test_user
from scripts.subscription_generator import assign_free_subscription
from scripts.apikey_generator import create_api_key_for_user

async def my_test():
    # Crear usuario
    user, msg = await create_test_user("myuser@example.com")
    print(msg)
    
    # Asignar suscripción
    sub, msg = await assign_free_subscription(user)
    print(msg)
    
    # Generar API key
    key, msg = await create_api_key_for_user(user, "My Key")
    print(msg)

asyncio.run(my_test())
```

## 📊 Salida Esperada

### Flujo Completo
```
======================================================================
               NBA STATS API - COMPLETE TEST FLOW
======================================================================

[STEP 1/4] Creating test user...
----------------------------------------------------------------------
✓ User created successfully!
  - ID: 1
  - Email: test_user_20250102_151530@example.com
  - Role: user
  - Supabase ID: 550e8400-e29b-41d4-a716-446655440000

[STEP 2/4] Assigning free subscription...
----------------------------------------------------------------------
✓ Free subscription assigned successfully!
  - Subscription ID: 1
  - Plan: free
  - Status: active
  - Period: 2025-01-02 to 2025-02-02
  - Rate Limits:
    • Per Minute: 10
    • Per Hour: 100
    • Per Day: 1000

[STEP 3/4] Generating API key...
----------------------------------------------------------------------
✓ API Key created successfully!
  - Key ID: 1
  - Name: Test Key
  - Last 8 chars: ...tK9mP2vQ
  - Rate Limit Plan: free
  - Expires: 2026-01-02

⚠️  IMPORTANT: The full API key below is only shown once!
   Copy and store it securely - you won't be able to see it again.

   Key: bestat_nba_xK9mP2vQ7sL4nR8wE3jT1dF6hY5cV0bN

[STEP 4/4] Testing API endpoints until rate limit...
----------------------------------------------------------------------
[  1] /v1/games/                         Status: 200 | Elapsed:   0.5s
[  2] /v1/players/                       Status: 200 | Elapsed:   0.6s
[  3] /v1/teams/                         Status: 200 | Elapsed:   0.7s
...
[ 10] /v1/games/                         Status: 429 | Elapsed:   5.2s

✓ Rate limit reached!
  Total requests: 10
  Time taken: 5.20s
  Error: Rate limited! Status: 429

============================================================
API CLIENT SUMMARY
============================================================
Total Requests:       10
Successful:           9
Failed:               1
Elapsed Time:         5.2s
Requests/Minute:      115.38
Rate Limited:         Yes
Rate Limited At:      2025-01-02T15:15:35.123456
============================================================

======================================================================
✓ TEST FLOW COMPLETED SUCCESSFULLY
======================================================================

📊 TEST SUMMARY:
   User Email:           test_user_20250102_151530@example.com
   User ID:              1
   Subscription:         Free Plan
   API Key ID:           1
   API Key Last Chars:   ...tK9mP2vQ
   Total Requests Made:  10
   Rate Limited:         Yes
   API Base URL:         http://localhost:8000
   Endpoints Tested:     /v1/games/, /v1/players/, /v1/teams/
======================================================================
```

## 🔐 Notas de Seguridad

1. **API Keys**: Nunca compartir las API keys completas. Solo se muestran una vez.
2. **Hashing**: Las keys se almacenan hasheadas con Argon2, no en texto plano.
3. **Rate Limiting**: Implementado a través de Redis con ventanas de tiempo configurables.
4. **Expiración**: Las keys pueden expirar (por defecto: 365 días).
5. **Revocación**: Las keys pueden ser revocadas inmediatamente.

## 🛠 Troubleshooting

### Error: "Database URL not found"
```bash
# Verifica que .env existe en la raíz del proyecto con:
# DATABASE_URL=postgres://...
```

### Error: "Redis not configured, rate limiting disabled"
```bash
# Verifica que Redis está corriendo:
# Redis debe estar en el puerto especificado en REDIS_URL
```

### Error: "Connection refused" en API
```bash
# Asegúrate de que la API está ejecutándose:
cd .. && python -m uvicorn app.main:app --reload
```

### Error: "User already exists"
```bash
# El email se genera con timestamp, pero puedes usar uno único:
from scripts.user_generator import create_test_user
await create_test_user("tu_email_unico@example.com")
```

## 📝 Ejemplos de Uso Avanzado

### Crear múltiples usuarios y probar concurrencia
```python
import asyncio
from scripts.user_generator import create_test_user
from scripts.subscription_generator import assign_free_subscription
from scripts.apikey_generator import create_api_key_for_user

async def create_multiple_users(count: int):
    tasks = []
    for i in range(count):
        email = f"user_{i}_{datetime.now().timestamp()}@example.com"
        task = create_test_user(email)
        tasks.append(task)
    
    users = await asyncio.gather(*tasks)
    return [u[0] for u in users]

users = asyncio.run(create_multiple_users(5))
```

### Probar diferentes endpoints
```python
from scripts.api_client import APIClient

client = APIClient("http://localhost:8000", your_api_key)
endpoints = [
    "/v1/games/?season=2024",
    "/v1/players/?position=PG",
    "/v1/teams/?division=Eastern",
]
await client.test_endpoints_until_rate_limited(endpoints)
```

## 📚 Referencia de API de Modelos

### User
```python
user.id              # ID único
user.email           # Email
user.supabase_user_id # UUID de Supabase
user.role            # 'user' o 'admin'
user.is_active       # Booleano
user.created_at      # DateTime
user.updated_at      # DateTime
```

### UserSubscription
```python
sub.id                       # ID único
sub.user_id                  # FK a users
sub.plan_id                  # FK a subscription_plans
sub.status                   # 'active', 'cancelled', etc.
sub.billing_cycle            # 'monthly' o 'yearly'
sub.subscribed_at            # Fecha de suscripción
sub.current_period_start     # Inicio del período
sub.current_period_end       # Fin del período
```

### APIKey
```python
key.id                              # ID único
key.user_id                         # FK a users
key.key_hash                        # Hash Argon2
key.name                            # Nombre descriptivo
key.last_chars                      # Últimos 8 caracteres
key.is_active                       # Booleano
key.rate_limit_plan                 # 'free', 'premium', etc.
key.created_at                      # Fecha creación
key.expires_at                      # Fecha expiración
key.revoked_at                      # Fecha revocación
```

## 📞 Soporte

Para más información sobre la API, ver:
- [README.md](../README.md) - Documentación principal
- [app/api/v1/endpoints/](../app/api/v1/endpoints/) - Endpoints disponibles
- [app/core/rate_limiter.py](../app/core/rate_limiter.py) - Sistema de rate limiting
- [app/core/security.py](../app/core/security.py) - Funciones de seguridad
