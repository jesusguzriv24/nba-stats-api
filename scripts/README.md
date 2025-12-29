# NBA Stats API - Scripts de Pruebas

Conjunto de scripts en Python para ejecutar un flujo completo de pruebas de la API de NBA Stats, incluyendo:
1. Creación de usuarios
2. Asignación de suscripciones
3. Generación de API keys
4. Pruebas de endpoints con rate limiting

## 📋 Estructura

```
scripts/
├── __init__.py                 # Inicializador del módulo
├── user_creator.py            # Crear usuarios en Supabase + BD
├── subscription_assigner.py    # Asignar suscripciones 'free'
├── api_key_creator.py          # Generar API keys
├── endpoint_tester.py          # Probar endpoints hasta límite
├── main.py                     # Script orquestrador principal
└── README.md                   # Este archivo
```

## 🚀 Requisitos

Antes de ejecutar los scripts, asegúrate de tener:

1. **Python 3.9+** instalado
2. **Las variables de entorno configuradas** en `.env`:
   - `DATABASE_URL`: Conexión a PostgreSQL
   - `SUPABASE_URL`: URL de Supabase
   - `SUPABASE_SERVICE_ROLE_KEY`: Clave de servicio de Supabase
   - `REDIS_URL`: Conexión a Redis (para rate limiting)

3. **Las dependencias instaladas**:
   ```bash
   pip install -r requirements.txt
   ```

4. **La API corriendo** en `http://localhost:8000` (o la URL que especifiques)

5. **Las tablas de BD creadas** (incluyendo `subscription_plans` con al menos un plan 'free')

## 📖 Uso

### Opción 1: Ejecutar el flujo completo (Recomendado)

```bash
python scripts/main.py test@example.com
```

**Parámetros opcionales:**

```bash
# Especificar URL de la API
python scripts/main.py test@example.com --api-url http://api.example.com/api/v1

# Especificar ventana de límite (minute, hour, day)
python scripts/main.py test@example.com --limit-window hour
```

**Ejemplo completo:**

```bash
python scripts/main.py newuser@test.com --api-url http://localhost:8000/api/v1 --limit-window minute
```

### Opción 2: Ejecutar módulos individualmente

#### Crear un usuario

```python
import asyncio
from scripts.user_creator import create_user

async def main():
    user = await create_user("myuser@example.com")
    print(f"Usuario creado: {user['id']} - {user['email']}")

asyncio.run(main())
```

#### Asignar suscripción

```python
import asyncio
from scripts.subscription_assigner import assign_free_subscription

async def main():
    subscription = await assign_free_subscription(user_id=1)
    print(f"Suscripción: {subscription['plan_name']}")

asyncio.run(main())
```

#### Crear API key

```python
import asyncio
from scripts.api_key_creator import create_api_key

async def main():
    api_key = await create_api_key(user_id=1, key_name="My API Key")
    print(f"API Key: {api_key['api_key']}")

asyncio.run(main())
```

#### Probar endpoints

```python
import asyncio
from scripts.endpoint_tester import test_endpoints_until_limit

async def main():
    results = await test_endpoints_until_limit(
        api_key="bestat_nba_...",
        limit_window="minute"
    )
    print(f"Requests realizados: {len(results)}")

asyncio.run(main())
```

## 📊 Flujo Completo Explicado

Cuando ejecutas `python scripts/main.py test@example.com`, el script realiza:

### 1. **Crear Usuario** (user_creator.py)
   - Crea un usuario en Supabase Auth
   - Registra el usuario en la tabla `users` de la BD
   - Retorna: ID, email, UUID de Supabase

### 2. **Asignar Suscripción 'Free'** (subscription_assigner.py)
   - Obtiene el plan 'free' de `subscription_plans`
   - Crea un registro en `user_subscriptions` para el usuario
   - Configuración:
     - Duración: 30 días
     - Precio: $0 (gratis)
     - Límites de rate limiting del plan free

### 3. **Crear API Key** (api_key_creator.py)
   - Genera una clave segura usando `secrets.token_urlsafe(32)`
   - Guarda el hash Argon2 en `api_keys`
   - **IMPORTANTE**: La clave completa se muestra solo una vez
   - Hereda los límites del plan free

### 4. **Probar Endpoints** (endpoint_tester.py)
   - Hace requests repetidos a endpoints usando la API key
   - Monitorea los límites de rate limiting
   - Continúa hasta alcanzar el límite configurado
   - Endpoints probados:
     - `/games`
     - `/players`
     - `/teams`

## 🔐 Seguridad

### API Keys
- **Nunca** se almacena la clave completa en la BD
- Solo se guarda el hash Argon2
- Se muestra la clave completa una sola vez al crear
- Los últimos 8 caracteres se guardan para referencia en UI

### Contraseñas de Usuario
- Se pueden proporcionar o se generan aleatoriamente
- Se almacenan en Supabase Auth (no en nuestra BD)

## 📈 Rate Limiting

El plan 'free' típicamente tiene los siguientes límites:

| Ventana | Límite |
|---------|--------|
| Por minuto | 10 |
| Por hora | 100 |
| Por día | 1000 |

Estos valores se configuran en la tabla `subscription_plans`.

## ⚠️ Notas Importantes

1. **Base de datos debe estar limpia**: Si ejecutas el script múltiples veces con el mismo email, el usuario previo será eliminado y recreado.

2. **API debe estar corriendo**: Asegúrate de que la API FastAPI esté activa en `http://localhost:8000` (o la URL especificada).

3. **Redis para rate limiting**: Si Redis no está configurado, el rate limiting se desactiva.

4. **Supabase Auth**: El script usa `SUPABASE_SERVICE_ROLE_KEY` para crear usuarios, requiere permisos de administrador.

## 🐛 Troubleshooting

### Error: "DATABASE_URL not found"
```bash
# Asegúrate de tener .env en la raíz del proyecto con:
echo "DATABASE_URL=postgresql://user:pass@host/db" >> .env
```

### Error: "Plan 'free' no existe"
```bash
# Debes insertar el plan 'free' en subscription_plans:
INSERT INTO subscription_plans (
    plan_name, display_name, 
    rate_limit_per_minute, rate_limit_per_hour, rate_limit_per_day,
    price_monthly_cents, price_yearly_cents, is_active
) VALUES (
    'free', 'Free Plan',
    10, 100, 1000,
    0, 0, true
);
```

### Error: "No players found" en endpoint tester
Asegúrate de que la tabla `players` tenga datos. Si no, ejecuta los scrapers primero.

## 📝 Ejemplo de Salida

```
======================================================================
                   NBA STATS API - FLUJO COMPLETO DE PRUEBAS
======================================================================

──────────────────────────────────────────────────────────────────────
 PASO 1: CREAR USUARIO
──────────────────────────────────────────────────────────────────────

[USER CREATOR] Creando usuario en Supabase Auth: test@example.com
✓ Usuario creado en Supabase: 1234-5678-90ab-cdef
[USER CREATOR] Registrando usuario en base de datos...
✓ Usuario registrado en BD con ID: 1

──────────────────────────────────────────────────────────────────────
 PASO 2: ASIGNAR SUSCRIPCIÓN 'FREE'
──────────────────────────────────────────────────────────────────────

[SUBSCRIPTION ASSIGNER] Asignando suscripción 'free' al usuario 1
✓ Plan 'free' encontrado: free
✓ Suscripción creada con ID: 1
  Plan: free
  Estado: active
  Vence el: 2025-01-27 12:34:56.789012+00:00
  Límites del plan:
    - Por minuto: 10
    - Por hora: 100
    - Por día: 1000

[... resto de la salida ...]
```

## 🔄 Automatización

Puedes crear un script bash para ejecutar múltiples pruebas:

```bash
#!/bin/bash

for i in {1..5}; do
    echo "Ejecución $i..."
    python scripts/main.py "user$i@example.com" --limit-window minute
    echo "---"
done
```

## 📞 Soporte

Si encuentras problemas:
1. Revisa los logs en `logs/`
2. Verifica que todas las dependencias estén instaladas
3. Asegúrate de que las variables de entorno estén configuradas
4. Revisa la salida del error para pistas sobre qué falló

## 📄 Licencia

Ver LICENSE en la raíz del proyecto.
