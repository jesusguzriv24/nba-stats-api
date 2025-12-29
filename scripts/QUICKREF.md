# ⚡ Quick Reference Card

## 🎯 Lo Más Importante

```bash
# ✓ Ejecutar TODO en una línea:
python scripts/main.py miusuario@example.com
```

¡Eso es! El script hace todo automáticamente:
1. Crea usuario
2. Asigna suscripción free
3. Genera API key
4. Prueba endpoints hasta límite

---

## 📋 Checklist Previo

- [ ] Estoy en la carpeta: `e:\Proyectos\nba-stats-api`
- [ ] Tengo `.env` con variables configuradas
- [ ] La API está corriendo: `http://localhost:8000`
- [ ] BD está disponible
- [ ] Plan 'free' existe en `subscription_plans`

---

## 🚀 Comandos Principales

### Flujo Completo
```bash
python scripts/main.py test@example.com
```

### Con Opciones
```bash
python scripts/main.py test@example.com --limit-window hour
python scripts/main.py test@example.com --api-url http://api.example.com/api/v1
```

### Crear Solo Usuario
```python
python -c "
import asyncio
from scripts.user_creator import create_user
asyncio.run(create_user('test@example.com'))
"
```

### Crear Solo API Key
```python
python -c "
import asyncio
from scripts.api_key_creator import create_api_key
asyncio.run(create_api_key(user_id=1))
"
```

---

## 📊 Rate Limits (Plan Free)

```
Minuto: 10 requests
Hora:   100 requests  
Día:    1000 requests
```

Verificar en tabla `subscription_plans`.

---

## 🔐 API Key Info

- **Formato**: `bestat_nba_{random_string}`
- **Longitud**: ~51 caracteres
- **Almacenamiento**: Hash Argon2 (nunca texto plano)
- **Recuperación**: ❌ No posible después de creada
- **Header**: `X-API-Key: bestat_nba_...`

---

## 📁 Archivos Clave

| Archivo | Descripción |
|---------|------------|
| `main.py` | Ejecutar esto |
| `user_creator.py` | Crear usuarios |
| `subscription_assigner.py` | Asignar suscripción |
| `api_key_creator.py` | Generar API key |
| `endpoint_tester.py` | Probar endpoints |
| `README.md` | Documentación completa |
| `ARCHITECTURE.md` | Diagramas técnicos |

---

## 🆘 Si Algo Falla

1. **Error de BD**: Verificar `.env` → `DATABASE_URL`
2. **Error de Supabase**: Verificar `.env` → `SUPABASE_*`
3. **Error de API**: Verificar que FastAPI está corriendo
4. **Error de plan**: Insertar plan 'free' en BD

Ver **TROUBLESHOOTING.md** para más detalles.

---

## 🔄 Flujo Visual

```
main.py
  ↓
user_creator.py    → Crea usuario en BD + Supabase
  ↓
subscription_assigner.py → Suscripción 'free'
  ↓
api_key_creator.py → API key segura
  ↓
endpoint_tester.py → Pruebas hasta límite
  ↓
✓ Completado
```

---

## 📞 Documentación Rápida

- **¿Cómo instaló?** → README.md
- **¿Cómo funciona internamente?** → ARCHITECTURE.md
- **¿Cómo debuguear errores?** → TROUBLESHOOTING.md
- **¿Otros ejemplos?** → examples.py

---

## 💡 Tips

✓ Usar emails únicos: `test-$(date +%s)@example.com`
✓ Guardar API keys en un lugar seguro
✓ Incrementar límites si necesitas más requests
✓ Ver logs en `logs/` para debugging

---

## ⏱️ Tiempo Estimado

| Paso | Tiempo |
|------|--------|
| Setup inicial | 2 min |
| Crear usuario | 3 seg |
| Asignar suscripción | 1 seg |
| Crear API key | 1 seg |
| Pruebas de endpoints | 10 seg (hasta límite) |
| **TOTAL** | **~20 seg** |

---

## 🎯 Salida Esperada

```
✓ Usuario creado: ID 5, test@example.com
✓ Suscripción asignada: ID 3, plan=free
✓ API key creada: ID 7
✓ 10 requests realizados (límite por minuto)

RESUMEN:
- Usuario: test@example.com
- Suscripción: free (10 req/min)
- API Key: bestat_nba_xK9mP2vQ7sL4nR8wE3jT1dF6hY5cV0bN
```

---

**Listo para empezar? → Ejecuta: `python scripts/main.py test@example.com`**
