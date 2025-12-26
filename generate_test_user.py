"""
Script para crear usuario y obtener JWT token.
"""
import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")

print("\n" + "="*70)
print("🔑 GENERAR USUARIO Y JWT PARA TESTING")
print("="*70)

# Crear usuario con service role
supabase_admin = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

email = "test.ratelimit@example.com"
password = "TestPassword123!"

print(f"\n[1] Creando usuario: {email}")

try:
    response = supabase_admin.auth.admin.create_user({
        "email": email,
        "password": password,
        "email_confirm": True
    })
    
    if response.user:
        print(f"✅ Usuario creado: {response.user.id}")
    else:
        print(f"ℹ️  Usuario ya existe o error: {response}")
        
except Exception as e:
    print(f"ℹ️  Usuario probablemente ya existe: {e}")

# Login para obtener JWT
print(f"\n[2] Obteniendo JWT token...")

supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

try:
    auth_response = supabase.auth.sign_in_with_password({
        "email": email,
        "password": password
    })
    
    if auth_response.session:
        jwt_token = auth_response.session.access_token
        
        print(f"\n✅ JWT Token obtenido:")
        print(f"\n{jwt_token}\n")
        
        print("="*70)
        print("🔑 COPIA ESTE TOKEN PARA USAR EN SWAGGER UI")
        print("="*70)
        print(f"\nAuthorization: Bearer {jwt_token}\n")
        
    else:
        print(f"❌ Error obteniendo token: {auth_response}")
        
except Exception as e:
    print(f"❌ Error: {e}")
