# 📚 NBA Stats API Scripts - Índice y Guía Rápida

## 📁 Estructura de Archivos

```
scripts/
├── __init__.py                 # Inicializador del módulo
├── main.py                     # ⭐ SCRIPT PRINCIPAL - Ejecutar este
├── user_creator.py             # Módulo: Crear usuarios
├── subscription_assigner.py     # Módulo: Asignar suscripciones
├── api_key_creator.py          # Módulo: Generar API keys
├── endpoint_tester.py          # Módulo: Probar endpoints
├── examples.py                 # Ejemplos avanzados de uso
├── requirements-scripts.txt     # Dependencias (referencia)
├── README.md                   # Documentación completa
├── ARCHITECTURE.md             # Diagramas y flujo técnico
├── TROUBLESHOOTING.md          # Solución de problemas
└── INDEX.md                    # Este archivo
```

## 🚀 Inicio Rápido

### 1️⃣ Antes de Empezar

```bash
# Asegúrate de estar en el directorio correcto
cd e:\Proyectos\nba-stats-api

# Verificar que tienes .env configurado
cat .env | grep DATABASE_URL

# La API debe estar corriendo
# En otra terminal:
python -m uvicorn app.main:app --reload --port 8000
```

### 2️⃣ Ejecutar el Flujo Completo

```bash
# Forma simple (con email de prueba)
python scripts/main.py test@example.com

# Forma avanzada (con opciones)
python scripts/main.py myuser@example.com --api-url http://localhost:8000/api/v1 --limit-window minute
```

### 3️⃣ Verificar Resultados

Abre tu cliente de base de datos (pgAdmin, DBeaver, etc) y verifica:
- Tabla `users`: Nuevo usuario creado
- Tabla `user_subscriptions`: Suscripción 'free' asignada
- Tabla `api_keys`: API key creada

---

## 📖 Documentación Detallada

| Archivo | Propósito | Cuándo Leer |
|---------|-----------|-----------|
| **README.md** | Guía completa, uso, instalación | Primero |
| **ARCHITECTURE.md** | Diagramas técnicos, flujos de datos | Entender la arquitectura |
| **TROUBLESHOOTING.md** | Errores y soluciones | Cuando algo falla |
| **examples.py** | Ejemplos avanzados de código | Implementar casos específicos |

---

## 🔧 Módulos Individuales

### 📝 user_creator.py

**Propósito**: Crear un usuario en Supabase y en la BD

```python
from scripts.user_creator import create_user
import asyncio

async def main():
    user = await create_user("newuser@example.com")
    print(f"Usuario creado: {user['id']}")

asyncio.run(main())
```

**Salida**:
```json
{
  "id": 1,
  "email": "newuser@example.com",
  "supabase_user_id": "uuid-uuid-uuid",
  "created_at": "2025-01-23T12:00:00",
  "password": "random-password"
}
```

---

### 📋 subscription_assigner.py

**Propósito**: Asignar una suscripción 'free' a un usuario

```python
from scripts.subscription_assigner import assign_free_subscription
import asyncio

async def main():
    sub = await assign_free_subscription(user_id=1)
    print(f"Plan: {sub['plan_name']}")

asyncio.run(main())
```

**Salida**:
```json
{
  "subscription_id": 1,
  "user_id": 1,
  "plan_name": "free",
  "status": "active",
  "rate_limits": {
    "per_minute": 10,
    "per_hour": 100,
    "per_day": 1000
  }
}
```

---

### 🔑 api_key_creator.py

**Propósito**: Generar una API key para un usuario

```python
from scripts.api_key_creator import create_api_key
import asyncio

async def main():
    key = await create_api_key(user_id=1, key_name="My Key")
    print(f"Clave: {key['api_key']}")  # ⚠️ Solo se muestra esta vez

asyncio.run(main())
```

**Salida**:
```json
{
  "id": 1,
  "user_id": 1,
  "name": "My Key",
  "api_key": "bestat_nba_xK9mP2vQ7sL4nR8wE3jT1dF6hY5cV0bN",
  "last_chars": "5cV0bN",
  "rate_limit_plan": "free",
  "created_at": "2025-01-23T12:00:00"
}
```

---

### 🔍 endpoint_tester.py

**Propósito**: Hacer requests a endpoints hasta alcanzar límite de rate limiting

```python
from scripts.endpoint_tester import test_endpoints_until_limit
import asyncio

async def main():
    results = await test_endpoints_until_limit(
        api_key="bestat_nba_...",
        limit_window="minute"
    )
    print(f"Total requests: {len(results)}")

asyncio.run(main())
```

**Salida** (parcial):
```
✓ Request #1: /games - 200
  Por minuto: 9/10 restantes
✓ Request #2: /players - 200
  Por minuto: 8/10 restantes
...
✓ Request #10: /games - 200
  Por minuto: 0/10 restantes

✓ LÍMITE DE RATE LIMITING ALCANZADO
  Total de requests: 10
```

---

### ⭐ main.py

**Propósito**: Orquesta todos los pasos en una ejecución

```bash
# Ejecución simple
python scripts/main.py test@example.com

# Ejecución avanzada
python scripts/main.py test@example.com \
  --api-url http://localhost:8000/api/v1 \
  --limit-window hour
```

**Pasos que ejecuta**:
1. ✓ Crear usuario
2. ✓ Asignar suscripción free
3. ✓ Crear API key
4. ✓ Probar endpoints hasta límite

---

### 📚 examples.py

**Propósito**: Ejemplos avanzados de uso

```bash
# Ver ejemplos en código
cat scripts/examples.py

# Ejecutar ejemplos (descomentar el que quieras)
python scripts/examples.py
```

**Ejemplos incluidos**:
- `example_create_multiple_users()` - Crear varios usuarios
- `example_complete_user_setup()` - Setup completo en una función
- `example_test_specific_endpoint()` - Probar endpoint específico
- `example_test_all_endpoints()` - Probar todos los endpoints
- `example_monitor_rate_limits()` - Monitorear límites en detalle
- `example_query_user_info()` - Consultar usuario de BD

---

## 🔄 Flujos Comunes

### Flujo 1: Crear un Usuario Completo

```bash
python scripts/main.py nuevousuario@example.com
```

**Resultado**:
- ✓ Usuario creado en Supabase y BD
- ✓ Suscripción 'free' asignada
- ✓ API key generada
- ✓ 10 requests realizados (límite por minuto)

---

### Flujo 2: Probar Límite de Hora

```bash
python scripts/main.py usuario2@example.com --limit-window hour
```

**Resultado**:
- ✓ Mismo setup que arriba
- ✓ Continúa hasta alcanzar 100 requests (límite por hora)

---

### Flujo 3: Probar Límite de Día

```bash
python scripts/main.py usuario3@example.com --limit-window day
```

**Resultado**:
- ✓ Mismo setup que arriba
- ✓ Continúa hasta alcanzar 1000 requests (límite por día)

---

### Flujo 4: Crear Usuario y Probar Manualmente

```python
import asyncio
from scripts.user_creator import UserCreator
from scripts.subscription_assigner import SubscriptionAssigner
from scripts.api_key_creator import APIKeyCreator

async def custom_flow():
    # Paso 1
    creator = UserCreator()
    user = await creator.create_user("custom@example.com")
    print(f"Usuario: {user['id']}")
    
    # Paso 2
    assigner = SubscriptionAssigner()
    sub = await assigner.assign_free_subscription(user['id'])
    print(f"Suscripción: {sub['plan_name']}")
    
    # Paso 3
    api_creator = APIKeyCreator()
    key = await api_creator.create_api_key(user['id'])
    print(f"API Key: {key['api_key'][:20]}...")

asyncio.run(custom_flow())
```

---

## ⚙️ Parámetros y Opciones

### main.py - Parámetros

```bash
python scripts/main.py [EMAIL] [OPTIONS]

Parámetros:
  EMAIL                          Email del nuevo usuario (requerido)

Opciones:
  --api-url URL                  URL base de la API
                                 Default: http://localhost:8000/api/v1
  
  --limit-window {minute|hour|day}  Ventana de límite a probar
                                 Default: minute
```

---

## 🔐 Información de Seguridad

### API Keys
- ✓ Se hashean con Argon2
- ✓ Se muestran solo una vez al crear
- ✓ No se pueden recuperar después
- ✓ Deben ser almacenadas de forma segura

### Supabase
- ✓ Usa `SERVICE_ROLE_KEY` (requiere permisos de admin)
- ✓ Contraseñas se almacenan en Supabase Auth
- ✓ Sincronización de usuarios con BD local

### Rate Limiting
- ✓ Se almacena en Redis (no en BD)
- ✓ Ventanas independientes (minuto, hora, día)
- ✓ Reseteadas automáticamente

---

## 📊 Limites Default (Plan Free)

| Ventana | Límite |
|---------|--------|
| Por minuto | 10 |
| Por hora | 100 |
| Por día | 1000 |

Modificables en tabla `subscription_plans`.

---

## 🐛 Problemas Comunes

| Problema | Solución |
|----------|----------|
| "DATABASE_URL not found" | Ver `.env` configuration |
| "Plan 'free' no existe" | Insertar plan en `subscription_plans` |
| "Connection refused" | Verificar que BD está corriendo |
| "429 Too Many Requests" | Es esperado, alcanzó el límite |
| "No players found" | Ejecutar scrapers primero |
| "API no responde" | Verificar que FastAPI está corriendo |

Para más detalles, ver **TROUBLESHOOTING.md**.

---

## 🎓 Aprender Más

### Entender la Arquitectura
```bash
# Lee este archivo para entender flujos
cat scripts/ARCHITECTURE.md
```

### Ver Ejemplos de Código
```bash
# Lee este archivo para ver casos de uso
cat scripts/examples.py
```

### Resolver Problemas
```bash
# Lee este archivo cuando algo falla
cat scripts/TROUBLESHOOTING.md
```

### Configuración Inicial
```bash
# Lee este archivo para instrucciones de instalación
cat scripts/README.md
```

---

## 🚀 Próximos Pasos

1. **Instalar dependencias**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configurar .env**:
   ```bash
   # Copiar variables de entorno necesarias
   ```

3. **Iniciar la API**:
   ```bash
   python -m uvicorn app.main:app --reload --port 8000
   ```

4. **Ejecutar scripts**:
   ```bash
   python scripts/main.py test@example.com
   ```

5. **Explorar ejemplos**:
   ```bash
   python scripts/examples.py
   ```

---

## 📞 Contacto y Soporte

- **Errores**: Ver TROUBLESHOOTING.md
- **Arquitectura**: Ver ARCHITECTURE.md
- **Uso**: Ver README.md
- **Ejemplos**: Ver examples.py

---

## 📝 Licencia

Ver LICENSE en la raíz del proyecto.

---

**Última actualización**: Enero 2025

**Versión**: 1.0.0

**Estado**: ✓ Listo para producción
