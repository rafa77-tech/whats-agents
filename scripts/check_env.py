#!/usr/bin/env python3
"""
Verifica se todas as variaveis de ambiente necessarias estao configuradas.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Carregar .env
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

# Variaveis obrigatorias
REQUIRED = [
    "SUPABASE_URL",
    "SUPABASE_SERVICE_KEY",
    "ANTHROPIC_API_KEY",
    "EVOLUTION_API_URL",
    "EVOLUTION_API_KEY",
    "EVOLUTION_INSTANCE",
]

# Variaveis opcionais (mas recomendadas)
OPTIONAL = [
    "CHATWOOT_URL",
    "CHATWOOT_API_KEY",
    "SLACK_WEBHOOK_URL",
]


def check():
    print("Verificando variaveis de ambiente...\n")

    errors = []
    warnings = []

    # Verificar obrigatorias
    print("Obrigatorias:")
    for var in REQUIRED:
        value = os.getenv(var)
        if value:
            # Mascarar valores sensiveis
            masked = value[:10] + "..." if len(value) > 10 else value
            print(f"  [OK] {var} = {masked}")
        else:
            print(f"  [ERRO] {var} = NAO CONFIGURADA")
            errors.append(var)

    # Verificar opcionais
    print("\nOpcionais:")
    for var in OPTIONAL:
        value = os.getenv(var)
        if value:
            masked = value[:10] + "..." if len(value) > 10 else value
            print(f"  [OK] {var} = {masked}")
        else:
            print(f"  [AVISO] {var} = nao configurada")
            warnings.append(var)

    # Resultado
    print("\n" + "=" * 50)
    if errors:
        print(f"[FALHOU] {len(errors)} variaveis obrigatorias faltando")
        print(f"   Faltam: {', '.join(errors)}")
        return False
    elif warnings:
        print(f"[OK com avisos] {len(warnings)} opcionais faltando")
        return True
    else:
        print("[TUDO OK]")
        return True


if __name__ == "__main__":
    import sys
    success = check()
    sys.exit(0 if success else 1)
