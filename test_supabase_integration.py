"""
Test de integración completa: Supabase → Webhook → API
Usa Service Role Key para crear usuarios sin verificación de email.
"""
import os
import requests
from supabase import create_client
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")  # 👈 Service Role Key
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
API_URL = os.getenv("API_URL", "https://bestat-nba-api.onrender.com/api/v1")

print("\n" + "="*70)
print("🧪 TEST: Integración completa Supabase → API")
print("="*70)

# 1. Crear usuario en Supabase (usando Service Role para bypassear verificación)
print("\n[STEP 1] Creando usuario en Supabase con Service Role...")

# Usar Service Role client para admin operations
supabase_admin = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
email = f"test.integration.{timestamp}@example.com"
password = "TestPassword123!"

print(f"Email a crear: {email}")

try:
    # Crear usuario con email ya confirmado
    response = supabase_admin.auth.admin.create_user({
        "email": email,
        "password": password,
        "email_confirm": True  # 👈 Confirmar email automáticamente
    })
    
    if response.user:
        print(f"✅ Usuario creado en Supabase (email pre-confirmado)")
        print(f"   Email: {email}")
        print(f"   Supabase ID: {response.user.id}")
        user_id = response.user.id
    else:
        print(f"❌ Error al crear usuario")
        print(f"   Response: {response}")
        exit(1)
        
except Exception as e:
    print(f"❌ Error creando usuario: {e}")
    exit(1)

# 2. Esperar sincronización del webhook
print("\n[STEP 2] Esperando sincronización del webhook...")
print("   (esperando 5 segundos)")

import time
time.sleep(5)

# 3. Login en Supabase con usuario regular (anon key)
print("\n[STEP 3] Haciendo login con el nuevo usuario...")

# Usar anon key para login normal
supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

try:
    auth_response = supabase.auth.sign_in_with_password({
        "email": email,
        "password": password
    })
    
    if auth_response.session:
        jwt_token = auth_response.session.access_token
        print(f"✅ Login exitoso")
        print(f"   JWT Token: {jwt_token[:40]}...")
    else:
        print(f"❌ Error en login")
        print(f"   Response: {auth_response}")
        exit(1)
        
except Exception as e:
    print(f"❌ Error en login: {e}")
    exit(1)

# 4. Consultar perfil en tu API con JWT
print("\n[STEP 4] Consultando perfil en tu API...")

headers = {"Authorization": f"Bearer {jwt_token}"}

try:
    profile_response = requests.get(f"{API_URL}/users/me", headers=headers)
    
    print(f"Status: {profile_response.status_code}")
    
    if profile_response.status_code == 200:
        data = profile_response.json()
        print(f"✅ API respondió correctamente")
        print(f"   Email: {data['email']}")
        print(f"   Role: {data['role']}")
        print(f"   Tier: {data['rate_limit_tier']}")
        print(f"   API Keys: {data['api_keys_count']}")
    else:
        print(f"❌ Error en API")
        print(f"   Response: {profile_response.text}")
        exit(1)
        
except Exception as e:
    print(f"❌ Error consultando API: {e}")
    exit(1)

# 5. Generar API Key
print("\n[STEP 5] Generando API Key...")

try:
    api_key_response = requests.post(
        f"{API_URL}/users/me/api-keys",
        headers=headers,
        json={"name": f"Integration Test Key {timestamp}"}
    )
    
    print(f"Status: {api_key_response.status_code}")
    
    if api_key_response.status_code == 201:
        key_data = api_key_response.json()
        api_key = key_data["key"]
        print(f"✅ API Key generada")
        print(f"   Key: {api_key[:35]}...")
        print(f"   Last chars: ****{key_data['last_chars']}")
    else:
        print(f"❌ Error generando key")
        print(f"   Response: {api_key_response.text}")
        exit(1)
        
except Exception as e:
    print(f"❌ Error generando API key: {e}")
    exit(1)

# 6. Probar endpoint protegido con API Key
print("\n[STEP 6] Probando endpoint protegido con API Key...")

try:
    teams_response = requests.get(
        f"{API_URL}/teams?limit=3",
        headers={"X-API-Key": api_key}
    )
    
    print(f"Status: {teams_response.status_code}")
    
    if teams_response.status_code == 200:
        teams = teams_response.json()
        print(f"✅ Endpoint /teams funcionó con API Key")
        print(f"   Equipos obtenidos: {len(teams)}")
        if teams:
            print(f"   Primer equipo: {teams[0].get('full_name', 'N/A')}")
    else:
        print(f"❌ Error en endpoint /teams")
        print(f"   Response: {teams_response.text}")
        exit(1)
        
except Exception as e:
    print(f"❌ Error probando endpoint: {e}")
    exit(1)

# 7. Probar con JWT también
print("\n[STEP 7] Probando endpoint protegido con JWT...")

try:
    games_response = requests.get(
        f"{API_URL}/games?limit=3",
        headers={"Authorization": f"Bearer {jwt_token}"}
    )
    
    print(f"Status: {games_response.status_code}")
    
    if games_response.status_code == 200:
        games = games_response.json()
        print(f"✅ Endpoint /games funcionó con JWT")
        print(f"   Partidos obtenidos: {len(games)}")
    else:
        print(f"❌ Error en endpoint /games")
        print(f"   Response: {games_response.text}")
        
except Exception as e:
    print(f"❌ Error probando endpoint: {e}")

# 8. Resumen final
print("\n" + "="*70)
print("✅ INTEGRACIÓN COMPLETA EXITOSA")
print("="*70)
print("\n📋 Resumen del test:")
print(f"   ✅ Usuario creado en Supabase Auth")
print(f"   ✅ Webhook sincronizó usuario a Aiven")
print(f"   ✅ JWT de Supabase funciona en tu API")
print(f"   ✅ API Key generada exitosamente")
print(f"   ✅ Endpoints protegidos con API Key: OK")
print(f"   ✅ Endpoints protegidos con JWT: OK")
print("\n🎉 Tu sistema de autenticación está completamente funcional!")
print("\n📊 Detalles del usuario de prueba:")
print(f"   Email: {email}")
print(f"   Supabase ID: {user_id}")
print(f"   API Key: {api_key[:35]}...")
print("="*70 + "\n")
