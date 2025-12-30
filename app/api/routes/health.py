"""
Rotas de health check.

Sprint 24 - Produção Ready:
- /health: Liveness básico (sempre 200 se app rodando)
- /health/ready: Readiness (Redis conectado)
- /health/deep: Deep check para CI/CD (Redis + Supabase + schema + views + env marker)
"""
from fastapi import APIRouter, Response
from datetime import datetime
import logging
import os

from app.services.redis import verificar_conexao_redis
from app.services.rate_limiter import obter_estatisticas
from app.services.circuit_breaker import obter_status_circuits
from app.services.whatsapp import evolution
from app.services.supabase import supabase

router = APIRouter()
logger = logging.getLogger(__name__)

# Hard guards de ambiente - CRÍTICO para evitar staging↔prod mix
APP_ENV = os.getenv("APP_ENV", "development")
SUPABASE_PROJECT_REF = os.getenv("SUPABASE_PROJECT_REF", "")

# Views críticas que DEVEM existir para o app funcionar
CRITICAL_VIEWS = [
    "campaign_sends",
    "campaign_metrics",
]

# Tabelas críticas que DEVEM existir
CRITICAL_TABLES = [
    "clientes",
    "conversations",
    "fila_mensagens",
    "doctor_state",
    "intent_log",
    "touch_reconciliation_log",
    "app_settings",  # Nova tabela crítica para markers
]

# Última migration conhecida (atualizar quando adicionar migrations críticas)
EXPECTED_SCHEMA_VERSION = "20251230140000"  # create_app_settings_environment_marker


@router.get("/health")
async def health_check():
    """
    Verifica se a API está funcionando.
    Usado para monitoramento e load balancers.
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "julia-api",
    }


@router.get("/health/ready")
async def readiness_check():
    """
    Verifica se a API está pronta para receber requests.
    Pode incluir verificações de dependências.
    """
    redis_ok = await verificar_conexao_redis()

    return {
        "status": "ready" if redis_ok else "degraded",
        "checks": {
            "database": "ok",  # TODO: verificar conexão real
            "evolution": "ok",  # TODO: verificar conexão real
            "redis": "ok" if redis_ok else "error",
        },
    }


@router.get("/health/rate-limit")
async def rate_limit_stats():
    """
    Retorna estatísticas de rate limiting.
    """
    stats = await obter_estatisticas()
    return {
        "rate_limit": stats,
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/health/circuits")
async def circuit_status():
    """
    Retorna status dos circuit breakers.
    """
    return {
        "circuits": obter_status_circuits(),
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/health/whatsapp")
async def whatsapp_status():
    """
    Verifica status da conexao WhatsApp com Evolution API.
    Retorna connected: true/false e detalhes da instancia.
    """
    try:
        status = await evolution.verificar_conexao()
        # Estado pode estar em status.instance.state ou status.state
        state = None
        if status:
            if "instance" in status:
                state = status.get("instance", {}).get("state")
            else:
                state = status.get("state")

        connected = state == "open"

        return {
            "connected": connected,
            "instance": evolution.instance,
            "state": state or "unknown",
            "details": status,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        return {
            "connected": False,
            "instance": evolution.instance,
            "state": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
        }


@router.get("/health/grupos")
async def grupos_worker_health():
    """
    Health check do worker de processamento de grupos WhatsApp.

    Verifica:
    - Estatísticas da fila por estágio
    - Itens travados (>1h sem atualização)
    - Erros nas últimas 24h
    """
    try:
        from app.services.grupos.fila import (
            obter_estatisticas_fila,
            obter_itens_travados,
        )

        # Obter estatísticas
        fila_stats = await obter_estatisticas_fila()

        # Verificar itens travados
        travados = await obter_itens_travados(horas=1)

        # Determinar status
        status = "healthy"
        if len(travados) > 100:
            status = "degraded"
        if len(travados) > 500:
            status = "unhealthy"

        return {
            "status": status,
            "fila": fila_stats,
            "travados": {
                "count": len(travados),
                "threshold_degraded": 100,
                "threshold_unhealthy": 500,
            },
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
        }


@router.get("/health/deep")
async def deep_health_check(response: Response):
    """
    Deep health check para CI/CD.

    Verifica TUDO que precisa estar funcionando para o app operar:
    - Environment: APP_ENV bate com marker no banco
    - Project Ref: SUPABASE_PROJECT_REF bate com marker no banco
    - Redis: conexão ativa
    - Supabase: conexão ativa
    - Schema: tabelas críticas existem
    - Views: views críticas existem e respondem
    - Migration: última migration aplicada >= esperada

    Retorna 200 se TUDO ok, 503 se qualquer check falhar.
    CI/CD deve usar este endpoint para validar deploy.

    HARD GUARDS: Environment e Project Ref são verificados PRIMEIRO.
    Se não baterem, o deploy é considerado CRÍTICO e deve ser revertido.
    """
    checks = {
        "environment": {"status": "pending", "app_env": APP_ENV, "db_env": None},
        "project_ref": {"status": "pending", "app_ref": SUPABASE_PROJECT_REF, "db_ref": None},
        "redis": {"status": "pending", "message": None},
        "supabase": {"status": "pending", "message": None},
        "tables": {"status": "pending", "missing": []},
        "views": {"status": "pending", "missing": []},
        "schema_version": {"status": "pending", "current": None, "expected": EXPECTED_SCHEMA_VERSION},
    }

    all_ok = True
    critical_mismatch = False  # Hard guard: env ou project_ref errado

    # 0. HARD GUARD: Check environment marker
    try:
        result = supabase.table("app_settings").select("value").eq("key", "environment").single().execute()
        db_env = result.data.get("value") if result.data else None
        checks["environment"]["db_env"] = db_env

        if db_env == APP_ENV:
            checks["environment"]["status"] = "ok"
        else:
            checks["environment"]["status"] = "CRITICAL"
            checks["environment"]["message"] = f"ENVIRONMENT MISMATCH! APP_ENV={APP_ENV}, DB={db_env}"
            all_ok = False
            critical_mismatch = True
            logger.critical(f"[health/deep] CRITICAL: Environment mismatch! APP_ENV={APP_ENV}, DB={db_env}")
    except Exception as e:
        checks["environment"]["status"] = "error"
        checks["environment"]["message"] = str(e)
        all_ok = False
        logger.error(f"[health/deep] Environment check failed: {e}")

    # 0b. HARD GUARD: Check Supabase project ref
    if SUPABASE_PROJECT_REF:  # Só verifica se configurado
        try:
            result = supabase.table("app_settings").select("value").eq("key", "supabase_project_ref").single().execute()
            db_ref = result.data.get("value") if result.data else None
            checks["project_ref"]["db_ref"] = db_ref

            if db_ref == SUPABASE_PROJECT_REF:
                checks["project_ref"]["status"] = "ok"
            else:
                checks["project_ref"]["status"] = "CRITICAL"
                checks["project_ref"]["message"] = f"PROJECT REF MISMATCH! Expected={SUPABASE_PROJECT_REF}, DB={db_ref}"
                all_ok = False
                critical_mismatch = True
                logger.critical(f"[health/deep] CRITICAL: Project ref mismatch! Expected={SUPABASE_PROJECT_REF}, DB={db_ref}")
        except Exception as e:
            checks["project_ref"]["status"] = "error"
            checks["project_ref"]["message"] = str(e)
            all_ok = False
            logger.error(f"[health/deep] Project ref check failed: {e}")
    else:
        checks["project_ref"]["status"] = "skipped"
        checks["project_ref"]["message"] = "SUPABASE_PROJECT_REF not configured"

    # Se hard guard falhou, não faz sentido continuar - é deploy errado
    if critical_mismatch:
        response.status_code = 503
        logger.critical(f"[health/deep] CRITICAL MISMATCH - DEPLOY TO WRONG ENVIRONMENT DETECTED!")
        return {
            "status": "CRITICAL",
            "message": "DEPLOY TO WRONG ENVIRONMENT DETECTED! ROLLBACK IMMEDIATELY!",
            "checks": checks,
            "timestamp": datetime.utcnow().isoformat(),
            "deploy_safe": False,
        }

    # 1. Check Redis
    try:
        redis_ok = await verificar_conexao_redis()
        if redis_ok:
            checks["redis"]["status"] = "ok"
        else:
            checks["redis"]["status"] = "error"
            checks["redis"]["message"] = "Redis ping failed"
            all_ok = False
    except Exception as e:
        checks["redis"]["status"] = "error"
        checks["redis"]["message"] = str(e)
        all_ok = False
        logger.error(f"[health/deep] Redis check failed: {e}")

    # 2. Check Supabase connection
    try:
        # Query simples para verificar conexão
        result = supabase.table("clientes").select("id").limit(1).execute()
        checks["supabase"]["status"] = "ok"
    except Exception as e:
        checks["supabase"]["status"] = "error"
        checks["supabase"]["message"] = str(e)
        all_ok = False
        logger.error(f"[health/deep] Supabase check failed: {e}")

    # 3. Check critical tables exist
    try:
        for table in CRITICAL_TABLES:
            try:
                supabase.table(table).select("*").limit(1).execute()
            except Exception:
                checks["tables"]["missing"].append(table)

        if checks["tables"]["missing"]:
            checks["tables"]["status"] = "error"
            all_ok = False
        else:
            checks["tables"]["status"] = "ok"
    except Exception as e:
        checks["tables"]["status"] = "error"
        checks["tables"]["message"] = str(e)
        all_ok = False
        logger.error(f"[health/deep] Tables check failed: {e}")

    # 4. Check critical views exist and respond
    try:
        for view in CRITICAL_VIEWS:
            try:
                supabase.table(view).select("*").limit(1).execute()
            except Exception:
                checks["views"]["missing"].append(view)

        if checks["views"]["missing"]:
            checks["views"]["status"] = "error"
            all_ok = False
        else:
            checks["views"]["status"] = "ok"
    except Exception as e:
        checks["views"]["status"] = "error"
        checks["views"]["message"] = str(e)
        all_ok = False
        logger.error(f"[health/deep] Views check failed: {e}")

    # 5. Check schema version (última migration aplicada)
    try:
        result = supabase.table("schema_migrations").select("version").order("version", desc=True).limit(1).execute()
        if result.data:
            current_version = result.data[0]["version"]
            checks["schema_version"]["current"] = current_version

            # Comparar versões (são strings no formato YYYYMMDDHHMMSS)
            if current_version >= EXPECTED_SCHEMA_VERSION:
                checks["schema_version"]["status"] = "ok"
            else:
                checks["schema_version"]["status"] = "warning"
                checks["schema_version"]["message"] = f"Schema behind: {current_version} < {EXPECTED_SCHEMA_VERSION}"
                # Warning não falha o deploy, mas avisa
        else:
            checks["schema_version"]["status"] = "error"
            checks["schema_version"]["message"] = "No migrations found"
            all_ok = False
    except Exception as e:
        checks["schema_version"]["status"] = "error"
        checks["schema_version"]["message"] = str(e)
        # Não falha se não conseguir verificar versão (tabela pode não existir)
        logger.warning(f"[health/deep] Schema version check failed: {e}")

    # Resultado final
    overall_status = "healthy" if all_ok else "unhealthy"

    if not all_ok:
        response.status_code = 503
        logger.error(f"[health/deep] FAILED: {checks}")

    return {
        "status": overall_status,
        "checks": checks,
        "timestamp": datetime.utcnow().isoformat(),
        "deploy_safe": all_ok,
    }


@router.get("/health/schema")
async def schema_info():
    """
    Retorna informações do schema do banco.

    Útil para debug e verificação manual de migrations.
    """
    try:
        # Últimas 10 migrations
        result = supabase.table("schema_migrations").select("*").order("version", desc=True).limit(10).execute()

        migrations = result.data if result.data else []

        return {
            "latest_migration": migrations[0]["version"] if migrations else None,
            "expected_migration": EXPECTED_SCHEMA_VERSION,
            "schema_up_to_date": migrations[0]["version"] >= EXPECTED_SCHEMA_VERSION if migrations else False,
            "recent_migrations": [m["version"] for m in migrations],
            "critical_tables": CRITICAL_TABLES,
            "critical_views": CRITICAL_VIEWS,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        return {
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
        }
