# NBA Stats API - Documentación Técnica del Flujo de Scripts

## 📐 Diagrama de Flujo General

```
┌─────────────────────────────────────────────────────────────────────┐
│                     SCRIPT PRINCIPAL (main.py)                      │
│                  Orquesta todo el flujo de pruebas                   │
└────────────────────────┬────────────────────────────────────────────┘
                         │
        ┌────────────────┼────────────────┐
        │                │                │
        ▼                ▼                ▼
   ┌─────────────┐  ┌──────────────┐  ┌───────────────┐
   │ user_creator│  │subscription  │  │ api_key       │
   │.py          │  │_assigner.py  │  │_creator.py    │
   └─────────────┘  └──────────────┘  └───────────────┘
        │                │                │
        └────────────────┼────────────────┘
                         │
                         ▼
                ┌──────────────────────┐
                │ endpoint_tester.py   │
                │ (Prueba endpoints)   │
                └──────────────────────┘
```

## 🔄 Detalle del Flujo Paso a Paso

### PASO 1: Crear Usuario (user_creator.py)

```
Entrada: email, password (opcional)
   │
   ├─► Crear usuario en Supabase Auth
   │    └─► POST /auth/v1/admin/users
   │    └─► Retorna: UUID de Supabase
   │
   ├─► Registrar en tabla 'users' de BD
   │    └─► INSERT INTO users (...)
   │    └─► Retorna: ID de BD
   │
Salida: {
    'id': int,                    # ID en tabla users
    'email': str,                 # Email del usuario
    'supabase_user_id': str,      # UUID de Supabase Auth
    'created_at': datetime,       # Fecha de creación
    'password': str               # Contraseña (si fue generada)
}
```

**Tablas afectadas:**
- `users` (INSERT)
- Supabase Auth (CREATE)

---

### PASO 2: Asignar Suscripción Free (subscription_assigner.py)

```
Entrada: user_id
   │
   ├─► Obtener plan 'free' de subscription_plans
   │    └─► SELECT * FROM subscription_plans WHERE plan_name = 'free'
   │
   ├─► Crear registro de suscripción
   │    ├─► Fecha inicio: ahora
   │    ├─► Fecha fin: ahora + 30 días
   │    ├─► Estado: 'active'
   │    └─► Plan ID: ID del plan 'free'
   │
   ├─► INSERT INTO user_subscriptions (...)
   │
Salida: {
    'subscription_id': int,       # ID en user_subscriptions
    'user_id': int,               # ID del usuario
    'plan_name': str,             # "free"
    'status': str,                # "active"
    'current_period_end': datetime,
    'rate_limits': {
        'per_minute': int,        # Límite por minuto
        'per_hour': int,          # Límite por hora
        'per_day': int            # Límite por día
    }
}
```

**Tablas afectadas:**
- `subscription_plans` (SELECT)
- `user_subscriptions` (INSERT)
- Opcionalmente `user_subscriptions` (UPDATE si hay suscripción previa)

**Límites típicos del plan 'free':**
```
┌──────────────┬─────────┐
│ Ventana      │ Límite  │
├──────────────┼─────────┤
│ Por minuto   │ 10      │
│ Por hora     │ 100     │
│ Por día      │ 1000    │
└──────────────┴─────────┘
```

---

### PASO 3: Crear API Key (api_key_creator.py)

```
Entrada: user_id, key_name
   │
   ├─► Generar clave segura
   │    └─► secrets.token_urlsafe(32) 
   │    └─► Formato: "bestat_nba_{random_token}"
   │    └─► Longitud total: ~51 caracteres
   │
   ├─► Hashear con Argon2
   │    └─► pwd_context.hash(api_key)
   │
   ├─► Guardar en BD (api_keys)
   │    ├─► key_hash: hash Argon2 (única forma segura de almacenar)
   │    ├─► last_chars: últimos 8 caracteres (para UI)
   │    ├─► rate_limit_plan: heredado del plan actual
   │    └─► is_active: true
   │
Salida: {
    'id': int,                    # ID en api_keys
    'user_id': int,               # ID del usuario propietario
    'name': str,                  # Nombre descriptivo
    'api_key': str,               # CLAVE COMPLETA (solo esta vez!)
    'last_chars': str,            # últimos 8 caracteres
    'is_active': bool,            # true
    'rate_limit_plan': str,       # "free"
    'created_at': datetime
}
```

**Importante:**
```
⚠️  La clave COMPLETA solo se muestra UNA VEZ
    Nunca se puede recuperar después
    Si se pierde, debe revocarse y crear una nueva
```

**Tablas afectadas:**
- `api_keys` (INSERT)
- `subscription_plans` (SELECT)

---

### PASO 4: Probar Endpoints (endpoint_tester.py)

```
Entrada: api_key, endpoints, limit_window
   │
   ├─► Crear cliente HTTP (httpx.AsyncClient)
   │    └─► Headers: {'X-API-Key': api_key}
   │
   ├─► Bucle de requests
   │    │
   │    ├─► Request a endpoint
   │    │    └─► GET /games?limit=5
   │    │    └─► Headers incluye X-API-Key
   │    │
   │    ├─► Leer headers de rate limiting
   │    │    ├─► X-RateLimit-Limit-Minute
   │    │    ├─► X-RateLimit-Remaining-Minute
   │    │    ├─► X-RateLimit-Reset-Minute
   │    │    ├─► X-RateLimit-Limit-Hour
   │    │    ├─► X-RateLimit-Remaining-Hour
   │    │    ├─► X-RateLimit-Reset-Hour
   │    │    ├─► X-RateLimit-Limit-Day
   │    │    ├─► X-RateLimit-Remaining-Day
   │    │    └─► X-RateLimit-Reset-Day
   │    │
   │    ├─► Evaluar si se alcanzó el límite
   │    │    └─► Si remaining_{limit_window} == 0
   │    │    └─► Salir del bucle
   │    │
   │    ├─► Pausa breve (0.5 segundos)
   │    │
   │    └─► Rotar al siguiente endpoint
   │
Salida: [
    {
        'request_number': int,
        'endpoint': str,
        'status_code': int,
        'success': bool,
        'timestamp': str (ISO 8601),
        'rate_limit_info': {
            'limit_minute': int,
            'remaining_minute': int,
            'reset_minute': int,
            'limit_hour': int,
            'remaining_hour': int,
            'reset_hour': int,
            'limit_day': int,
            'remaining_day': int,
            'reset_day': int,
        },
        'response': dict|list|str,
        'error': str|None
    },
    ... (más requests)
]
```

**Endpoints probados:**
- `/games` - Obtener lista de juegos
- `/players` - Obtener lista de jugadores
- `/teams` - Obtener lista de equipos
- `/stats` - Obtener estadísticas (opcional)

---

## 🗄️ Estructura de Base de Datos

### Tabla: `users`
```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    supabase_user_id VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    role VARCHAR(50) DEFAULT 'user',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### Tabla: `subscription_plans`
```sql
CREATE TABLE subscription_plans (
    id SERIAL PRIMARY KEY,
    plan_name VARCHAR(50) UNIQUE NOT NULL,
    display_name VARCHAR(100) NOT NULL,
    description TEXT,
    rate_limit_per_minute INT NOT NULL,
    rate_limit_per_hour INT NOT NULL,
    rate_limit_per_day INT NOT NULL,
    price_monthly_cents INT DEFAULT 0,
    price_yearly_cents INT DEFAULT 0,
    promo_price_monthly_cents INT,
    promo_price_yearly_cents INT,
    promo_expires_at TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    features TEXT,
    display_order INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### Tabla: `user_subscriptions`
```sql
CREATE TABLE user_subscriptions (
    id SERIAL PRIMARY KEY,
    user_id INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    plan_id INT NOT NULL REFERENCES subscription_plans(id),
    status VARCHAR(50) DEFAULT 'active',
    billing_cycle VARCHAR(50) DEFAULT 'monthly',
    payment_provider VARCHAR(50),
    payment_provider_subscription_id VARCHAR(255),
    current_period_start TIMESTAMP NOT NULL,
    current_period_end TIMESTAMP NOT NULL,
    cancelled_at TIMESTAMP,
    cancel_at_period_end BOOLEAN DEFAULT FALSE,
    trial_start TIMESTAMP,
    trial_end TIMESTAMP,
    price_paid_cents INT NOT NULL,
    auto_renew BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### Tabla: `api_keys`
```sql
CREATE TABLE api_keys (
    id SERIAL PRIMARY KEY,
    user_id INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    key_hash VARCHAR(255) NOT NULL,
    name VARCHAR(100) NOT NULL,
    last_chars VARCHAR(8) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    rate_limit_plan VARCHAR(50) DEFAULT 'free',
    custom_rate_limit_per_minute INT,
    custom_rate_limit_per_hour INT,
    custom_rate_limit_per_day INT,
    scopes VARCHAR(500),
    allowed_ips VARCHAR(500),
    created_at TIMESTAMP DEFAULT NOW(),
    last_used_at TIMESTAMP,
    revoked_at TIMESTAMP,
    expires_at TIMESTAMP
);
```

---

## 🔐 Flujo de Seguridad

### Generación de API Key
```
secrets.token_urlsafe(32)
         │
         ├─► 32 bytes aleatorios
         ├─► Codificados en base64url
         └─► ~43 caracteres
         
                 │
         bestat_nba_{random}
                 │
                 ├─► Añadir prefijo
                 └─► ~51 caracteres (API_KEY)
                 
                 │
         pwd_context.hash()
                 │
                 ├─► Argon2 (algoritmo moderno)
                 ├─► Parámetro único (salt)
                 └─► Hash de ~100 caracteres (KEY_HASH)
                 
                 │
          Guardar en BD
                 │
                 ├─► KEY_HASH: para verificación segura
                 ├─► LAST_CHARS: para UI (sin exponer la clave)
                 └─► API_KEY: mostrado solo una vez al usuario
```

### Verificación de API Key
```
Cliente: X-API-Key: bestat_nba_{clave_completa}
             │
             └─► API recibe header
                 │
                 ├─► Buscar KEY_HASH en BD por usuario/API key ID
                 │
                 ├─► pwd_context.verify(cliente_key, stored_hash)
                 │
                 └─► ✓ Válido o ✗ Inválido
```

---

## ⏱️ Rate Limiting en Redis

```
Solicitud HTTP con X-API-Key
     │
     ├─► Extraer user_id y api_key_id
     │
     ├─► Obtener plan de suscripción
     │    └─► LIMIT_MINUTE, LIMIT_HOUR, LIMIT_DAY
     │
     ├─► Calcular ventanas de tiempo
     │    ├─► minute_start = (now // 60) * 60
     │    ├─► hour_start = (now // 3600) * 3600
     │    └─► day_start = (now // 86400) * 86400
     │
     ├─► Keys en Redis
     │    ├─► ratelimit:apikey:{api_key_id}:minute:{minute_start}
     │    ├─► ratelimit:apikey:{api_key_id}:hour:{hour_start}
     │    └─► ratelimit:apikey:{api_key_id}:day:{day_start}
     │
     ├─► INCR en Redis (operación atómica)
     │    │
     │    ├─► count_minute++
     │    ├─► count_hour++
     │    └─► count_day++
     │
     ├─► Validar límites
     │    ├─► if count_minute > LIMIT_MINUTE → ❌ 429 Too Many Requests
     │    ├─► if count_hour > LIMIT_HOUR → ❌ 429 Too Many Requests
     │    └─► if count_day > LIMIT_DAY → ❌ 429 Too Many Requests
     │
     └─► Retornar con headers
          ├─► X-RateLimit-Limit-Minute: {limit}
          ├─► X-RateLimit-Remaining-Minute: {limit - count}
          ├─► X-RateLimit-Reset-Minute: {unix_timestamp}
          └─► ... (igual para hour y day)
```

---

## 📊 Ejemplo Completo de Ejecución

### Input
```bash
$ python scripts/main.py test@example.com --limit-window minute
```

### Proceso
```
1. Crear usuario
   Supabase Auth: CREATE
   DB users: INSERT (ID=5)

2. Asignar suscripción free
   subscription_plans: SELECT (plan_id=1)
   user_subscriptions: INSERT (sub_id=3)

3. Crear API key
   api_keys: INSERT (id=7)
   Retorna clave: bestat_nba_xK9mP2vQ7sL4nR8wE3jT1dF6hY5cV0bN

4. Probar endpoints (LIMIT_MINUTE=10)
   Request 1:  /games  ✓ remaining: 9/10
   Request 2:  /players ✓ remaining: 8/10
   Request 3:  /teams  ✓ remaining: 7/10
   Request 4:  /games  ✓ remaining: 6/10
   Request 5:  /players ✓ remaining: 5/10
   Request 6:  /teams  ✓ remaining: 4/10
   Request 7:  /games  ✓ remaining: 3/10
   Request 8:  /players ✓ remaining: 2/10
   Request 9:  /teams  ✓ remaining: 1/10
   Request 10: /games  ✓ remaining: 0/10
   
   ✓ LÍMITE ALCANZADO
```

### Output
```
✓ Usuario creado: ID 5, test@example.com
✓ Suscripción asignada: ID 3, plan=free
✓ API key creada: ID 7, últimos=...0bN
✓ 10 requests realizados hasta alcanzar límite
```

---

## 🔄 Relaciones Entre Tablas

```
                    users (1)
                      │
        ┌─────────────┼─────────────┐
        │             │             │
        ▼             ▼             ▼
    api_keys    user_subscriptions  (otros)
        │             │
        │             ▼
        │      subscription_plans
        │
        └─► utilizadas para autenticar requests
             a través de X-API-Key header
```

---

## 📈 Flujo de Datos en Tiempo Real

```
Usuario → main.py
    │
    ├─→ user_creator
    │   └─→ Supabase Auth + DB
    │       └─→ user_info
    │
    ├─→ subscription_assigner
    │   └─→ subscription_plans + DB
    │       └─→ subscription_info
    │
    ├─→ api_key_creator
    │   └─→ BD
    │       └─→ api_key_info (con clave completa)
    │
    └─→ endpoint_tester
        └─→ HTTP requests con X-API-Key
            ├─→ authentication (verify_api_key)
            ├─→ rate limiting (rate_limiter)
            └─→ response con headers de límites
                └─→ test_results

    └─→ Output final (resumen completo)
```

---

## 🎯 Puntos Clave a Recordar

1. **API Key**: Se muestra solo UNA VEZ al crear. No se puede recuperar.

2. **Rate Limiting**: Se almacena en Redis con keys basadas en:
   - API Key ID o User ID
   - Ventana de tiempo (minuto/hora/día)

3. **Seguridad**: Las claves se hashean con Argon2, no se guardan en texto plano.

4. **Subscripción**: Heredada del plan que tiene el usuario al crear la API key.

5. **Headers de Rate Limit**: La API retorna headers indicando el estado actual.

---

## 🔍 Debugging

Para ver qué está pasando internamente:

```python
# Activar logging detallado
import logging
logging.basicConfig(level=logging.DEBUG)

# Ver queries SQL
from sqlalchemy import event
event.listen(Engine, "before_cursor_execute", lambda conn, cursor, statement, parameters, context, executemany: print(statement))
```
