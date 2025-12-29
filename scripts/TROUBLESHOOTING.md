# NBA Stats API Scripts - Guía de Troubleshooting

## 🔴 Errores Comunes y Soluciones

### 1. "DATABASE_URL not found in environment variables"

**Causa**: Falta el archivo `.env` o no está configurado correctamente.

**Solución**:
```bash
# Asegúrate de tener un archivo .env en la raíz del proyecto con:
cat > .env << EOF
DATABASE_URL=postgresql://user:password@host:5432/database_name
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_JWT_SECRET=your_jwt_secret_here
SUPABASE_ANON_KEY=your_anon_key_here
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key_here
REDIS_URL=redis://localhost:6379
EOF
```

**Verificar**:
```bash
python -c "from dotenv import load_dotenv; load_dotenv(); import os; print(os.getenv('DATABASE_URL'))"
```

---

### 2. "Plan 'free' no existe en la base de datos"

**Causa**: La tabla `subscription_plans` no tiene un plan llamado 'free'.

**Solución**:
```sql
-- Conectarse a la BD y ejecutar:
INSERT INTO subscription_plans (
    plan_name,
    display_name,
    description,
    rate_limit_per_minute,
    rate_limit_per_hour,
    rate_limit_per_day,
    price_monthly_cents,
    price_yearly_cents,
    is_active
) VALUES (
    'free',
    'Free Plan',
    'Free plan for testing and development',
    10,
    100,
    1000,
    0,
    0,
    true
);

-- Verificar
SELECT * FROM subscription_plans WHERE plan_name = 'free';
```

---

### 3. "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required"

**Causa**: Falta configuración de Supabase.

**Solución**:
1. Ve a [Supabase Dashboard](https://app.supabase.com)
2. Selecciona tu proyecto
3. Settings → API
4. Copia:
   - `Project URL` → `SUPABASE_URL`
   - `Service Role Key` → `SUPABASE_SERVICE_ROLE_KEY`
5. Actualiza `.env`

```bash
# Verificar
python -c "import os; from dotenv import load_dotenv; load_dotenv(); print(f'Supabase URL: {os.getenv(\"SUPABASE_URL\")}')"
```

---

### 4. "Connection refused" al conectar a BD

**Causa**: La BD no está disponible.

**Soluciones**:

**Opción A - BD Local/Docker**:
```bash
# Verificar que el contenedor está corriendo
docker-compose ps

# Si no está, iniciarlo
docker-compose up -d
```

**Opción B - BD Remota**:
```bash
# Verificar conectividad
ping host_de_la_bd

# Verificar puerto
nc -zv host_de_la_bd 5432

# O usar pgAdmin para probar conexión
```

**Verificar URL**:
```bash
python -c "
from urllib.parse import urlparse
import os
from dotenv import load_dotenv

load_dotenv()
db_url = os.getenv('DATABASE_URL')
parsed = urlparse(db_url)

print(f'Host: {parsed.hostname}')
print(f'Port: {parsed.port}')
print(f'Database: {parsed.path}')
print(f'User: {parsed.username}')
"
```

---

### 5. "No players found with the given filters"

**Causa**: La tabla `players` está vacía.

**Solución**:
```bash
# Ejecutar los scrapers primero
python app/scrappers/main.py

# O cargar datos de prueba
# Ver if hay un script de datos iniciales
ls -la *.py | grep -i seed
```

---

### 6. "Connection timed out" al probar endpoints

**Causa**: La API FastAPI no está corriendo.

**Solución**:
```bash
# En otra terminal, inicia la API
cd e:\Proyectos\nba-stats-api
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Verificar que está corriendo
curl http://localhost:8000/api/v1/users/health
```

---

### 7. "Redis not configured, rate limiting disabled"

**Causa**: La variable `REDIS_URL` no está configurada (advertencia, no error).

**Solución**:

**Si quieres usar Redis**:
```bash
# Actualizar .env
echo "REDIS_URL=redis://localhost:6379" >> .env

# Verificar que Redis está corriendo
redis-cli ping
# Debería retornar: PONG

# Si no está instalado
# Windows: usar Windows Subsystem for Linux (WSL) o contenedor Docker
docker run -d -p 6379:6379 redis:latest
```

**Si prefieres desactivar rate limiting**:
- Simplemente ignora esta advertencia
- Los scripts funcionarán sin limitaciones

---

### 8. "Module 'app' not found"

**Causa**: El path no está configurado correctamente.

**Solución**:
```bash
# Asegúrate de estar en el directorio correcto
cd e:\Proyectos\nba-stats-api

# Verifica la estructura
ls -la app/
# Debería ver: __init__.py, main.py, api/, core/, models/, etc.

# Si aún falla, intenta:
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
python scripts/main.py test@example.com
```

---

### 9. "Duplicate key value violates unique constraint"

**Causa**: El usuario con ese email ya existe.

**Solución**:
```bash
# Opción 1: Usar un email diferente
python scripts/main.py unique-email-$(date +%s)@example.com

# Opción 2: Eliminar usuario previo
# En la BD:
DELETE FROM users WHERE email = 'test@example.com';
DELETE FROM auth.users WHERE email = 'test@example.com'; -- En Supabase

# Opción 3: El script debería manejarlo automáticamente (ver user_creator.py)
```

---

### 10. "Request #X returned status 401 Unauthorized"

**Causa**: La API key no es válida o está mal formada.

**Solución**:
```bash
# Verificar que la API key está siendo usada correctamente
# Headers debe ser:
# X-API-Key: bestat_nba_{tu_clave_completa}

# En Python:
import httpx
headers = {"X-API-Key": "bestat_nba_tu_clave_aqui"}
response = httpx.get("http://localhost:8000/api/v1/games", headers=headers)
print(response.status_code)  # Debería ser 200
```

---

### 11. "Request #X returned status 429 Too Many Requests"

**Causa**: Se alcanzó el límite de rate limiting (es el comportamiento esperado).

**Solución**:
```bash
# Esto es ESPERADO
# El script está diseñado para hacer requests hasta alcanzar el límite

# Si quieres más requests, cambia la ventana de límite:
python scripts/main.py test@example.com --limit-window hour
# O
python scripts/main.py test@example.com --limit-window day

# O aumenta los límites del plan en subscription_plans:
UPDATE subscription_plans
SET rate_limit_per_minute = 100
WHERE plan_name = 'free';
```

---

### 12. "SCRAM authentication failed"

**Causa**: Contraseña de BD incorrecta.

**Solución**:
```bash
# Verificar DATABASE_URL en .env
cat .env | grep DATABASE_URL

# Asegúrate de que contiene:
# - Usuario correcto
# - Contraseña correcta (sin caracteres especiales sin escapar)
# - Host correcto
# - Puerto correcto (por defecto 5432)

# Ejemplo:
# DATABASE_URL=postgresql://admin:mypassword@localhost:5432/nba_db

# Si tiene caracteres especiales, encodificar:
# @ en contraseña → %40
# : en contraseña → %3A
# # en contraseña → %23
```

---

### 13. "Asyncio event loop already running"

**Causa**: Intentar ejecutar `asyncio.run()` en Jupyter o entorno que ya tiene loop.

**Solución**:
```bash
# Si estás en Jupyter Notebook:
import nest_asyncio
nest_asyncio.apply()

# Si estás en terminal, simplemente ejecuta:
python scripts/main.py test@example.com
# No uses python interactivo >>> 

# O en Python interactivo:
import asyncio
from scripts.main import TestFlowOrchestrator

# En lugar de:
# asyncio.run(...)

# Usa:
orchestrator = TestFlowOrchestrator()
loop = asyncio.get_event_loop()
result = loop.run_until_complete(orchestrator.run_complete_flow("test@example.com"))
```

---

## 🟡 Advertencias y Mensajes Informativos

### "[RATE LIMITER] Redis not configured, rate limiting disabled"

**Severidad**: ⚠️ Advertencia

**Significado**: La funcionalidad de rate limiting no funcionará porque Redis no está configurado.

**Acción**: 
- Opcional: Configurar Redis en `.env`
- O: Ignorar si no necesitas rate limiting

---

### "Cleaning URL parameters (removing sslmode)"

**Severidad**: ℹ️ Informativo

**Significado**: La URL de BD contenía parámetro `?sslmode=require` que fue removido para asyncpg.

**Acción**: Normal, no requiere acción.

---

## 🔍 Debugging Avanzado

### Ver todas las queries SQL

```python
import logging
from sqlalchemy import event
from sqlalchemy.engine import Engine

logging.basicConfig()
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

# O escuchar eventos
@event.listens_for(Engine, "before_cursor_execute")
def receive_before_cursor_execute(conn, cursor, statement, params, context, executemany):
    print(f"[SQL] {statement}")
    print(f"[PARAMS] {params}")
```

### Ver headers HTTP

```python
import httpx

async def debug_request():
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "http://localhost:8000/api/v1/games",
            headers={"X-API-Key": "bestat_nba_..."}
        )
        print("Response Headers:")
        for k, v in response.headers.items():
            print(f"  {k}: {v}")
```

### Ver contenido de Redis

```bash
# Conectarse a Redis CLI
redis-cli

# Ver todas las keys de rate limiting
KEYS "ratelimit:*"

# Ver valor de una key específica
GET "ratelimit:apikey:1:minute:1703424000"

# Ver TTL
TTL "ratelimit:apikey:1:minute:1703424000"
```

### Ver logs de la aplicación

```bash
# Si ejecutas la API localmente con logs
python -m uvicorn app.main:app --reload --log-level debug

# Los logs también se guardan en:
cat logs/app.log
```

---

## 📋 Checklist de Debugging

Antes de reportar un error, verifica:

- [ ] `.env` existe y tiene todas las variables requeridas
- [ ] BD está corriendo y accesible
- [ ] Supabase está configurado correctamente
- [ ] Las tablas existen (`users`, `subscription_plans`, etc.)
- [ ] El plan 'free' existe en `subscription_plans`
- [ ] La API FastAPI está corriendo en `http://localhost:8000`
- [ ] Redis está configurado (si quieres rate limiting)
- [ ] Tienes permiso de lectura/escritura en la BD
- [ ] Python 3.9+ está instalado
- [ ] Todas las dependencias están instaladas (`pip install -r requirements.txt`)

---

## 🆘 Obtener Más Ayuda

### Archivo de Log Completo
```bash
python scripts/main.py test@example.com 2>&1 | tee debug.log
# Ver debug.log para más detalles
```

### Ejecutar con Modo Verbose
```bash
# En el código, modificar:
# app/core/database.py línea ~18: print(...) está activo
# Los prints mostrarán información de cada paso
```

### Contactar al Equipo de Desarrollo
Incluir en el reporte:
1. Output completo del error
2. Archivo `.env` (sin valores sensibles)
3. Versión de Python: `python --version`
4. SO: Windows/Linux/Mac
5. Paso donde falla (1-4)
6. Pasos para reproducir
