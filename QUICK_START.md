# 🚀 QUICK START - NBA Stats API Test Scripts

## ⚡ 30 segundos para comenzar

```bash
# 1. Verifica que todo está configurado
python scripts/quick_test.py

# 2. Ejecuta el flujo completo
python scripts/main_test_flow.py
```

---

## ✅ Requisitos Previos

Antes de ejecutar, asegúrate de:

1. **PostgreSQL conectada** - Verifica que `.env` tiene `DATABASE_URL`
2. **Redis ejecutándose** - Para rate limiting
3. **API ejecutándose** - En `http://localhost:8000`

```bash
# Si la API no está ejecutándose:
python -m uvicorn app.main:app --reload
```

---

## 📖 Documentación

| Archivo | Propósito |
|---------|-----------|
| `scripts/README.md` | 📚 Documentación completa |
| `scripts/WORKFLOW_ARCHITECTURE.md` | 🏗️ Diagramas y flujos |
| `SCRIPTS_GUIDE.md` | 📊 Análisis detallado |
| `SCRIPTS_SUMMARY.py` | 📝 Resumen ejecutivo |

---

## 🎯 Opciones de Ejecución

### Opción 1: Test Rápido (3 requests)
```bash
python scripts/quick_test.py
```
✓ Verifica que todo funciona  
✓ No alcanza rate limit  
✓ Toma ~5 segundos

### Opción 2: Flujo Completo (hasta rate limit)
```bash
python scripts/main_test_flow.py
```
✓ Crea usuario → suscripción → API key → testea API  
✓ Continúa hasta alcanzar rate limit (HTTP 429)  
✓ Muestra reporte detallado  
✓ Toma ~5-7 segundos

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

## 📊 Qué Sucede

### Con `main_test_flow.py`:

```
[STEP 1/4] Creating test user...
✓ User created successfully!
  - ID: 1
  - Email: test_user_20250102_151530@example.com

[STEP 2/4] Assigning free subscription...
✓ Free subscription assigned successfully!
  - Rate Limits: 10/min, 100/hora, 1000/día

[STEP 3/4] Generating API key...
✓ API Key created successfully!
  - Key: bestat_nba_xK9mP2vQ7sL4nR8wE3jT1dF6hY5cV0bN

[STEP 4/4] Testing API endpoints until rate limit...
[  1] /v1/games/    Status: 200
[  2] /v1/players/  Status: 200
[  3] /v1/teams/    Status: 200
...
[ 10] /v1/teams/    Status: 429 ✓ Rate Limited!

Total Requests: 10
Elapsed Time: 5.2s
```

---

## 🔍 Troubleshooting

### Error: "Database URL not found"
```
Solución: Verifica que .env tiene DATABASE_URL=postgres://...
```

### Error: "Redis not configured"
```
Solución: Inicia Redis
redis-server
# O verifica REDIS_URL en .env
```

### Error: "Connection refused" en API
```
Solución: Inicia la API en otra terminal
python -m uvicorn app.main:app --reload
```

---

## 📚 Aprenderás

✓ Cómo funcionan API keys con Argon2  
✓ Cómo se implementan suscripciones  
✓ Cómo funciona rate limiting con Redis  
✓ Flujo usuario → autenticación → API  
✓ Mejores prácticas de seguridad  

---

## 🎓 Próximos Pasos

1. Lee [scripts/README.md](scripts/README.md) para documentación completa
2. Lee [SCRIPTS_GUIDE.md](SCRIPTS_GUIDE.md) para análisis detallado
3. Personaliza los scripts para tus necesidades
4. Crea tests adicionales basados en estos ejemplos

---

**¡Listo para empezar!** 🚀

```bash
python scripts/quick_test.py  # Verifica
python scripts/main_test_flow.py  # Ejecuta
```
