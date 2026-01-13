"""
Script para aplicar migrations da Sprint 25.

Uso:
    python migrations/sprint-25/apply.py

Requer: SUPABASE_URL e SUPABASE_SERVICE_KEY no .env
"""
import os
from pathlib import Path
from supabase import create_client

# Carregar .env
from dotenv import load_dotenv
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("Erro: SUPABASE_URL e SUPABASE_SERVICE_KEY necessarios no .env")
    exit(1)

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Diretorio das migrations
MIGRATIONS_DIR = Path(__file__).parent

# Ordem das migrations
MIGRATIONS = [
    "001_chips_schema.sql",
    "002_chips_triggers.sql",
]


def apply_migrations():
    """Aplica todas as migrations em ordem."""
    for migration_file in MIGRATIONS:
        path = MIGRATIONS_DIR / migration_file
        if not path.exists():
            print(f"[SKIP] {migration_file} nao encontrado")
            continue

        print(f"[APPLY] {migration_file}...")

        sql = path.read_text()

        try:
            # Executar via RPC (raw SQL)
            supabase.rpc("exec_sql", {"sql": sql}).execute()
            print(f"[OK] {migration_file}")
        except Exception as e:
            print(f"[ERROR] {migration_file}: {e}")
            # Tentar executar direto se RPC nao existir
            try:
                # Alternativa: usar postgrest-py direto
                print(f"[RETRY] Tentando via psycopg2...")
                import psycopg2
                conn_str = SUPABASE_URL.replace("https://", "postgresql://postgres:").replace(".supabase.co", f".supabase.co:5432/postgres?password={SUPABASE_KEY}")
                # Isso nao vai funcionar sem a senha do DB
                print("[INFO] Execute manualmente no Supabase SQL Editor")
            except:
                pass


if __name__ == "__main__":
    print("=== Sprint 25 Migrations ===")
    print(f"URL: {SUPABASE_URL}")
    print()

    apply_migrations()

    print()
    print("Se houve erros, execute os SQLs manualmente no Supabase SQL Editor:")
    for m in MIGRATIONS:
        print(f"  - migrations/sprint-25/{m}")
