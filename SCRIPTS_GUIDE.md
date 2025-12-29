# 📊 Análisis Completo y Guía de Uso

## 🎯 Objetivo

He analizado el flujo de tu API y creado un conjunto de **scripts modulares** que permiten:

1. ✅ **Crear un usuario** en la tabla `users`
2. ✅ **Asignar suscripción "free"** al usuario
3. ✅ **Generar una API key** segura (con hashing Argon2)
4. ✅ **Realizar requests** a los endpoints usando la API key
5. ✅ **Continuar hasta alcanzar el rate limit** (HTTP 429)

Todo esto se puede ejecutar de forma **independiente o unificada**.

---

## 📁 Estructura de Carpetas Creada

```
scripts/
├── __init__.py                          # Paquete Python
├── config.py                            # ⚙️  Configuración compartida
├── user_generator.py                    # 👤 Crear usuarios
├── subscription_generator.py            # 📋 Asignar suscripciones
├── apikey_generator.py                  # 🔑 Generar API keys
├── api_client.py                        # 🌐 Cliente HTTP para testear
├── main_test_flow.py                    # 🚀 Orquestador principal
├── quick_test.py                        # ⚡ Test rápido (3 requests)
├── README.md                            # 📖 Documentación detallada
└── WORKFLOW_ARCHITECTURE.md             # 🏗️  Diagramas de flujo
```

### Tamaños de Archivos
- **user_generator.py** (3.5 KB) - Crear usuarios
- **subscription_generator.py** (6.2 KB) - Gestionar suscripciones
- **apikey_generator.py** (5.9 KB) - Generar API keys
- **api_client.py** (10.9 KB) - Cliente HTTP
- **main_test_flow.py** (4.9 KB) - Script principal
- **quick_test.py** (3.9 KB) - Verificación rápida
- **config.py** (3.2 KB) - Configuración
- **README.md** (11.7 KB) - Guía completa
- **WORKFLOW_ARCHITECTURE.md** (20.3 KB) - Diagramas detallados

---

## 🚀 Cómo Usar

### Opción 1: Flujo Completo (Recomendado)

```bash
# Desde la raíz del proyecto
python -m scripts.main_test_flow
```

**Esto hace:**
1. Crea un usuario único con email basado en timestamp
2. Asigna el plan "free" (10 req/min, 100 req/hora, 1000 req/día)
3. Genera una API key segura
4. Realiza requests a 3 endpoints `/v1/games/`, `/v1/players/`, `/v1/teams/`
5. Continúa hasta alcanzar el rate limit (HTTP 429)
6. Muestra un reporte detallado

**Output esperado:**
```
[STEP 1/4] Creating test user...
✓ User created successfully!
  - ID: 1
  - Email: test_user_20250102_151530@example.com

[STEP 2/4] Assigning free subscription...
✓ Free subscription assigned successfully!
  - Subscription ID: 1
  - Rate Limits: 10/min, 100/hora, 1000/día

[STEP 3/4] Generating API key...
✓ API Key created successfully!
  - Key ID: 1
  - Last 8 chars: ...tK9mP2vQ

[STEP 4/4] Testing API endpoints until rate limit...
[  1] /v1/games/        Status: 200 | Elapsed:   0.5s
[  2] /v1/players/      Status: 200 | Elapsed:   0.6s
[  3] /v1/teams/        Status: 200 | Elapsed:   0.7s
...
[ 10] /v1/teams/        Status: 429 | Elapsed:   5.2s

✓ Rate limit reached!
  Total requests: 10
```

---

### Opción 2: Test Rápido (Verificación)

```bash
# Verifica que todo funciona (solo 3 requests)
python scripts/quick_test.py
```

**Usado para:**
- Verificar configuración antes de test completo
- Probar sin alcanzar rate limits
- Diagnóstico rápido

---

### Opción 3: Módulos Individuales

```bash
# Solo crear usuario
python scripts/user_generator.py

# Solo asignar suscripción
python scripts/subscription_generator.py

# Solo generar API key
python scripts/apikey_generator.py

# Solo testear API
python scripts/api_client.py
```

---

### Opción 4: Desde Tu Propio Script

```python
import asyncio
from scripts.user_generator import create_test_user
from scripts.subscription_generator import assign_free_subscription
from scripts.apikey_generator import create_api_key_for_user
from scripts.api_client import APIClient

async def my_custom_flow():
    # Crear usuario
    user, msg = await create_test_user("custom@example.com")
    print(msg)
    
    # Asignar suscripción
    sub, msg = await assign_free_subscription(user)
    print(msg)
    
    # Generar API key
    key_data, msg = await create_api_key_for_user(user, "My Key")
    print(msg)
    
    # Testear API
    client = APIClient("http://localhost:8000", key_data["key"])
    await client.test_endpoints_until_rate_limited(["/v1/games/"])
    client.print_summary()

asyncio.run(my_custom_flow())
```

---

## 🔍 Análisis del Flujo de Trabajo

### 1️⃣ **Fase 1: Creación de Usuario** (user_generator.py)

```
Entrada: email: str
         ↓
Lógica:  1. Verifica si usuario existe
         2. Genera UUID dummy para Supabase (ya que no usamos auth)
         3. Crea registro en tabla users
         4. Retorna objeto User
         ↓
Salida:  User(id=1, email="...", supabase_user_id="...")
```

**Base de Datos:**
```sql
INSERT INTO users (email, role, is_active, supabase_user_id, created_at, updated_at)
VALUES ('test@example.com', 'user', true, '<UUID>', NOW(), NOW());
```

---

### 2️⃣ **Fase 2: Asignación de Suscripción** (subscription_generator.py)

```
Entrada: user: User
         ↓
Lógica:  1. Crea/obtiene plan "free":
            - rate_limit_per_minute: 10
            - rate_limit_per_hour: 100
            - rate_limit_per_day: 1000
            - precio: $0
            
         2. Crea UserSubscription:
            - user_id → User
            - plan_id → SubscriptionPlan
            - status: 'active'
            - current_period_end: NOW() + 1 mes
            ↓
Salida:  UserSubscription(id=1, plan_name="free", valid_until="2025-02-02")
```

**Base de Datos:**
```sql
-- Plan (si no existe)
INSERT INTO subscription_plans 
  (plan_name, rate_limit_per_minute, rate_limit_per_hour, rate_limit_per_day)
VALUES ('free', 10, 100, 1000);

-- Suscripción del usuario
INSERT INTO user_subscriptions (user_id, plan_id, status, subscribed_at, current_period_start, current_period_end)
VALUES (1, 1, 'active', NOW(), NOW(), NOW() + INTERVAL '1 month');
```

---

### 3️⃣ **Fase 3: Generación de API Key** (apikey_generator.py)

```
Entrada: user: User, name: str, rate_limit_plan: str
         ↓
Lógica:  1. Genera token seguro:
            key = "bestat_nba_" + random(32 bytes)
            Ej: "bestat_nba_xK9mP2vQ7sL4nR8wE3jT1dF6hY5cV0bN"
            
         2. Hashea con Argon2:
            key_hash = argon2.hash(key)
            Ej: "$argon2id$v=19$m=65540,t=3,p=4$..."
            
         3. Extrae últimos 8 caracteres:
            last_chars = "5cV0bN"
            
         4. Almacena en BD:
            - key_hash (nunca el key original)
            - last_chars (para mostrar en UI)
            - is_active: true
            - expires_at: NOW() + 365 días
            ↓
Salida:  {
           "key": "bestat_nba_xK9mP2vQ7sL4nR8wE3jT1dF6hY5cV0bN",  ← MOSTRAR UNA VEZ
           "key_hash": "$argon2id$...",
           "last_chars": "5cV0bN",
           "api_key_id": 1
         }
```

**Base de Datos:**
```sql
INSERT INTO api_keys (user_id, key_hash, name, last_chars, is_active, rate_limit_plan, expires_at)
VALUES (1, '$argon2id$...', 'Test Key', '5cV0bN', true, 'free', NOW() + INTERVAL '365 days');
```

**🔐 Seguridad:**
- ✅ Key nunca se almacena en texto plano
- ✅ Se hashea con Argon2 (función de derivación de claves)
- ✅ Solo se muestra una vez al crear
- ✅ Verificación mediante `pwd_context.verify()`

---

### 4️⃣ **Fase 4: Testing de API** (api_client.py)

```
Entrada: base_url: str, api_key: str, endpoints: List[str]
         ↓
Para cada request:
         
  1. Construir request:
     GET /v1/games/ HTTP/1.1
     Host: localhost:8000
     X-API-Key: bestat_nba_xK9mP2vQ7sL4nR8wE3jT1dF6hY5cV0bN
     
  2. Server recibe request:
     a. dependencies.py::get_current_user_from_api_key()
     b. Valida X-API-Key header
     c. Busca en BD por key_hash
     d. Verifica con Argon2 (securo)
     e. Obtiene usuario y su suscripción
     f. **RATE LIMITING (Redis)**:
        - ratelimit:user:1:minute:1735430400
        - ratelimit:user:1:hour:1735430400
        - ratelimit:user:1:day:20250101
        Si cualquier contador ≥ límite → return HTTP 429
        Si OK → incrementa contadores, procesa request
     
  3. Response:
     - HTTP 200 OK → request exitoso, continuar
     - HTTP 429 Too Many Requests → RATE LIMITED, PARAR ✓
     - HTTP 401 Unauthorized → API key inválida/revocada
     - HTTP 4xx/5xx → error en servidor
     ↓
Salida: {
          "total_requests": 10,
          "successful_requests": 9,
          "failed_requests": 1,
          "elapsed_time_seconds": 5.2,
          "requests_per_minute": 115.38,
          "rate_limited": true,
          "rate_limited_at": "2025-01-02T15:15:35.123456"
        }
```

**Rate Limiting en Redis:**
```
Key: ratelimit:user:<user_id>:<window>:<timestamp>
                                 ↑
                    minute | hour | day

Por Minuto:
  ratelimit:user:1:minute:1735430400 = 1
  ratelimit:user:1:minute:1735430400 = 2
  ratelimit:user:1:minute:1735430400 = 3
  ...
  ratelimit:user:1:minute:1735430400 = 10 → ¡LÍMITE ALCANZADO!
  
  Siguiente request en mismo minuto → 429 Too Many Requests

Por Hora:
  ratelimit:user:1:hour:1735430400 = 100 (máximo)

Por Día:
  ratelimit:user:1:day:20250101 = 1000 (máximo)
```

---

## 📊 Diagrama de Flujo Completo

```
┌─────────────────────────────────────────────────────────────────┐
│                   main_test_flow.py                             │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ↓
┌──────────────────────────────────────────────────────────────────┐
│  PASO 1: create_test_user("test_user_timestamp@example.com")    │
│  → INSERT INTO users (email, role, is_active, ...)              │
│  ← User(id=1, email=...)                                        │
└──────────────────────────────────────────────────────────────────┘
                            │
                            ↓
┌──────────────────────────────────────────────────────────────────┐
│  PASO 2: assign_free_subscription(user)                          │
│  → Obtiene/crea plan "free"                                     │
│  → INSERT INTO user_subscriptions (user_id, plan_id, ...)       │
│  ← UserSubscription(id=1, status='active')                      │
└──────────────────────────────────────────────────────────────────┘
                            │
                            ↓
┌──────────────────────────────────────────────────────────────────┐
│  PASO 3: create_api_key_for_user(user)                           │
│  → Genera token: "bestat_nba_..."                               │
│  → Hashea con Argon2                                            │
│  → INSERT INTO api_keys (user_id, key_hash, ...)               │
│  ← {key: "bestat_nba_...", api_key_id: 1}                       │
└──────────────────────────────────────────────────────────────────┘
                            │
                            ↓
┌──────────────────────────────────────────────────────────────────┐
│  PASO 4: client.test_endpoints_until_rate_limited([...])        │
│                                                                  │
│  Loop:                                                           │
│    1. GET /v1/games/ + Header: X-API-Key: bestat_nba_...       │
│    2. Server valida key (Argon2), obtiene user, subscription   │
│    3. Server chequea Redis rate limiter                        │
│       ├─ Si contador < límite → responde 200 OK               │
│       └─ Si contador = límite → responde 429 Too Many         │
│    4. Cliente recibe respuesta                                 │
│       ├─ Si 200 → incrementa contador, continúa               │
│       └─ Si 429 → PARA, rate limit alcanzado ✓                │
│    5. Repite con siguiente endpoint                            │
│                                                                  │
│  Salida: summary = {                                            │
│    total_requests: 10,                                          │
│    rate_limited: true,                                          │
│    elapsed_time_seconds: 5.2                                    │
│  }                                                              │
└──────────────────────────────────────────────────────────────────┘
                            │
                            ↓
        ┌─────────────────────────────────────┐
        │  Print Summary & Report             │
        │  ✓ TEST COMPLETED SUCCESSFULLY      │
        └─────────────────────────────────────┘
```

---

## 🔑 Características Principales

### ✅ Modularidad
- Cada fase es **independiente**
- Pueden ejecutarse **por separado o juntas**
- Reutilizables en otros contextos

### ✅ Seguridad
- **API keys hasheadas** con Argon2
- **Nunca se almacenan en texto plano**
- **Verificación segura** en cada request
- **Revocación** inmediata disponible

### ✅ Rate Limiting
- **Redis-based** para performance
- **3 ventanas de tiempo** (minuto, hora, día)
- **Automático** basado en suscripción
- **HTTP 429** para límites alcanzados

### ✅ Logging
- **Todos los requests** se registran en `api_usage_logs`
- **Timestamps** y **response times**
- **Errores** y **status codes**
- **IP address** y **User-Agent**

### ✅ Documentación
- **README.md** - Guía completa
- **WORKFLOW_ARCHITECTURE.md** - Diagramas detallados
- **Docstrings** en todos los módulos
- **Ejemplos de uso** en cada función

---

## 📋 Requisitos Previos

Antes de ejecutar:

1. **API ejecutándose:**
   ```bash
   cd ..  # desde scripts/
   python -m uvicorn app.main:app --reload
   ```

2. **PostgreSQL configurada:**
   - Database URL en `.env`
   - Migraciones ejecutadas

3. **Redis ejecutándose:**
   - Para rate limiting
   - URL en `.env` (REDIS_URL)

4. **Dependencias instaladas:**
   ```bash
   pip install -r requirements.txt
   ```

---

## 🎓 Qué Aprendes

Al ejecutar estos scripts aprendes:

1. ✅ **Cómo funciona la autenticación** con API keys
2. ✅ **Cómo se hashean** las claves de forma segura
3. ✅ **Cómo funciona el rate limiting** con Redis
4. ✅ **Estructura de suscripciones** en tu API
5. ✅ **Flujo completo** user → subscription → key → API
6. ✅ **Testing de APIs** con autenticación

---

## 🚀 Próximos Pasos

Puedes extender esto para:
- [ ] Crear tests para múltiples usuarios concurrentes
- [ ] Probar diferentes planes (free, premium, pro)
- [ ] Verificar rate limits específicos
- [ ] Generar reportes de uso
- [ ] Integración con CI/CD

---

## 📞 Soporte

- Ver `scripts/README.md` para documentación detallada
- Ver `scripts/WORKFLOW_ARCHITECTURE.md` para diagramas
- Todos los módulos tienen docstrings completos
- Ejecuta `quick_test.py` para verificación rápida

¡Todo está listo para usar! 🎉
