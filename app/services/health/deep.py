"""
Deep health check logic.

Sprint 58 - Epic 3: Extraido de app/api/routes/health.py

Verifica TUDO que precisa estar funcionando para o app operar:
- Environment: APP_ENV bate com marker no banco
- Project Ref: SUPABASE_PROJECT_REF bate com marker no banco
- Redis: conexao ativa
- Supabase: conexao ativa
- Schema: tabelas criticas existem
- Views: views criticas existem e respondem
- Migration: ultima migration aplicada >= esperada
- Prompts: prompts core existem, ativos, com sentinelas obrigatorias
"""

import logging

from app.services.redis import verificar_conexao_redis
from app.services.supabase import supabase
from app.core.config import settings

from app.services.health.constants import (
    APP_ENV,
    SUPABASE_PROJECT_REF,
    CRITICAL_TABLES,
    CRITICAL_VIEWS,
    EXPECTED_SCHEMA_VERSION,
    GIT_SHA,
    DEPLOYMENT_ID,
    RAILWAY_ENVIRONMENT,
    RUN_MODE,
)
from app.services.health.schema import gerar_schema_fingerprint, verificar_contrato_prompts

logger = logging.getLogger(__name__)


async def executar_deep_health_check() -> dict:
    """
    Executa deep health check completo.

    Returns:
        dict com status, checks, version, schema, deploy_safe, e http_status.
        http_status indica qual status code o endpoint deve retornar.
    """
    checks = {
        "environment": {"status": "pending", "app_env": APP_ENV, "db_env": None},
        "project_ref": {"status": "pending", "app_ref": SUPABASE_PROJECT_REF, "db_ref": None},
        "localhost_check": {"status": "pending"},
        "dev_guardrails": {"status": "pending"},
        "redis": {"status": "pending", "message": None},
        "supabase": {"status": "pending", "message": None},
        "tables": {"status": "pending", "missing": []},
        "views": {"status": "pending", "missing": []},
        "schema_version": {
            "status": "pending",
            "current": None,
            "expected": EXPECTED_SCHEMA_VERSION,
        },
        "prompts": {"status": "pending"},
    }

    all_ok = True
    critical_mismatch = False

    # 0. HARD GUARD: Check environment marker
    all_ok, critical_mismatch = _verificar_environment(checks, all_ok, critical_mismatch)

    # 0b. HARD GUARD: Check Supabase project ref
    all_ok, critical_mismatch = _verificar_project_ref(checks, all_ok, critical_mismatch)

    # Se hard guard falhou, retornar imediatamente
    if critical_mismatch:
        logger.critical("[health/deep] CRITICAL MISMATCH - DEPLOY TO WRONG ENVIRONMENT DETECTED!")
        return {
            "status": "CRITICAL",
            "message": "DEPLOY TO WRONG ENVIRONMENT DETECTED! ROLLBACK IMMEDIATELY!",
            "checks": checks,
            "runtime_endpoints": settings.runtime_endpoints,
            "deploy_safe": False,
            "http_status": 503,
        }

    # 0c. LOCALHOST CHECK
    all_ok, critical_mismatch = _verificar_localhost(checks, all_ok, critical_mismatch)

    # 0d. DEV GUARDRAILS
    all_ok = _verificar_dev_guardrails(checks, all_ok)

    # Sprint 59 Epic 3.3: Paralelizar checks independentes
    import asyncio

    # Run async checks in parallel
    redis_result, prompts_result = await asyncio.gather(
        _verificar_redis_deep(checks, True),
        _verificar_prompts(checks, True),
    )
    if not redis_result:
        all_ok = False
    if not prompts_result:
        all_ok = False

    # Sync checks (all use supabase client, run sequentially)
    all_ok = _verificar_supabase_deep(checks, all_ok)
    all_ok = _verificar_tabelas_criticas(checks, all_ok)
    all_ok = _verificar_views_criticas(checks, all_ok)
    all_ok = _verificar_schema_version(checks, all_ok)

    # Resultado final
    overall_status = "healthy" if all_ok else "unhealthy"
    http_status = 200 if all_ok else 503

    if not all_ok:
        logger.error(f"[health/deep] FAILED: {checks}")

    # Gerar schema fingerprint para deteccao de drift
    schema_fp = gerar_schema_fingerprint()

    return {
        "status": overall_status,
        "version": {
            "git_sha": GIT_SHA,
            "deployment_id": DEPLOYMENT_ID,
            "railway_environment": RAILWAY_ENVIRONMENT,
            "run_mode": RUN_MODE,
        },
        "runtime_endpoints": settings.runtime_endpoints,
        "schema": schema_fp,
        "checks": checks,
        "deploy_safe": all_ok,
        "http_status": http_status,
    }


def _verificar_environment(checks: dict, all_ok: bool, critical_mismatch: bool) -> tuple:
    """Verifica marker de environment no banco."""
    try:
        result = (
            supabase.table("app_settings")
            .select("value")
            .eq("key", "environment")
            .single()
            .execute()
        )
        db_env = result.data.get("value") if result.data else None
        checks["environment"]["db_env"] = db_env

        if db_env == APP_ENV:
            checks["environment"]["status"] = "ok"
        else:
            checks["environment"]["status"] = "CRITICAL"
            checks["environment"]["message"] = (
                f"ENVIRONMENT MISMATCH! APP_ENV={APP_ENV}, DB={db_env}"
            )
            all_ok = False
            critical_mismatch = True
            logger.critical(
                f"[health/deep] CRITICAL: Environment mismatch! APP_ENV={APP_ENV}, DB={db_env}"
            )
    except Exception as e:
        checks["environment"]["status"] = "error"
        checks["environment"]["message"] = str(e)
        all_ok = False
        logger.error(f"[health/deep] Environment check failed: {e}")

    return all_ok, critical_mismatch


def _verificar_project_ref(checks: dict, all_ok: bool, critical_mismatch: bool) -> tuple:
    """Verifica Supabase project ref no banco."""
    if SUPABASE_PROJECT_REF:
        try:
            result = (
                supabase.table("app_settings")
                .select("value")
                .eq("key", "supabase_project_ref")
                .single()
                .execute()
            )
            db_ref = result.data.get("value") if result.data else None
            checks["project_ref"]["db_ref"] = db_ref

            if db_ref == SUPABASE_PROJECT_REF:
                checks["project_ref"]["status"] = "ok"
            else:
                checks["project_ref"]["status"] = "CRITICAL"
                checks["project_ref"]["message"] = (
                    f"PROJECT REF MISMATCH! Expected={SUPABASE_PROJECT_REF}, DB={db_ref}"
                )
                all_ok = False
                critical_mismatch = True
                logger.critical(
                    f"[health/deep] CRITICAL: Project ref mismatch! "
                    f"Expected={SUPABASE_PROJECT_REF}, DB={db_ref}"
                )
        except Exception as e:
            checks["project_ref"]["status"] = "error"
            checks["project_ref"]["message"] = str(e)
            all_ok = False
            logger.error(f"[health/deep] Project ref check failed: {e}")
    else:
        checks["project_ref"]["status"] = "skipped"
        checks["project_ref"]["message"] = "SUPABASE_PROJECT_REF not configured"

    return all_ok, critical_mismatch


def _verificar_localhost(checks: dict, all_ok: bool, critical_mismatch: bool) -> tuple:
    """Valida que nao ha URLs apontando para localhost."""
    localhost_violations = settings.has_localhost_urls
    checks["localhost_check"] = {
        "status": "pending",
        "violations": localhost_violations,
        "runtime_endpoints": settings.runtime_endpoints,
    }

    if localhost_violations:
        if settings.is_production:
            checks["localhost_check"]["status"] = "CRITICAL"
            checks["localhost_check"]["message"] = (
                f"LOCALHOST DETECTED IN PRODUCTION! Violations: {localhost_violations}"
            )
            all_ok = False
            critical_mismatch = True
            logger.critical(
                f"[health/deep] CRITICAL: Localhost URLs in production: {localhost_violations}"
            )
        else:
            checks["localhost_check"]["status"] = "warning"
            checks["localhost_check"]["message"] = (
                f"Localhost URLs detected (OK for local dev): {localhost_violations}"
            )
            logger.warning(f"[health/deep] Localhost URLs in dev: {localhost_violations}")
    else:
        checks["localhost_check"]["status"] = "ok"

    return all_ok, critical_mismatch


def _verificar_dev_guardrails(checks: dict, all_ok: bool) -> bool:
    """Valida que ambiente DEV tem protecoes configuradas."""
    if not settings.is_production:
        allowlist = settings.outbound_allowlist_numbers
        checks["dev_guardrails"] = {
            "status": "pending",
            "app_env": settings.APP_ENV,
            "is_production": False,
            "allowlist_configured": len(allowlist) > 0,
            "allowlist_count": len(allowlist),
        }

        if not allowlist:
            checks["dev_guardrails"]["status"] = "CRITICAL"
            checks["dev_guardrails"]["message"] = (
                "DEV environment has EMPTY OUTBOUND_ALLOWLIST! "
                "All outbound messages will be BLOCKED (fail-closed). "
                "Configure OUTBOUND_ALLOWLIST with test phone numbers."
            )
            all_ok = False
            logger.critical(
                f"[health/deep] CRITICAL: DEV environment without OUTBOUND_ALLOWLIST! "
                f"APP_ENV={settings.APP_ENV}"
            )
        else:
            checks["dev_guardrails"]["status"] = "ok"
            logger.info(
                f"[health/deep] DEV guardrails OK: allowlist has {len(allowlist)} numbers"
            )
    else:
        checks["dev_guardrails"] = {
            "status": "skipped",
            "message": "Production environment - DEV guardrails not applicable",
            "app_env": settings.APP_ENV,
            "is_production": True,
        }

    return all_ok


async def _verificar_redis_deep(checks: dict, all_ok: bool) -> bool:
    """Verifica Redis para deep check."""
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

    return all_ok


def _verificar_supabase_deep(checks: dict, all_ok: bool) -> bool:
    """Verifica Supabase para deep check."""
    try:
        supabase.table("clientes").select("id").limit(1).execute()
        checks["supabase"]["status"] = "ok"
    except Exception as e:
        checks["supabase"]["status"] = "error"
        checks["supabase"]["message"] = str(e)
        all_ok = False
        logger.error(f"[health/deep] Supabase check failed: {e}")

    return all_ok


def _verificar_tabelas_criticas(checks: dict, all_ok: bool) -> bool:
    """Verifica que tabelas criticas existem."""
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

    return all_ok


def _verificar_views_criticas(checks: dict, all_ok: bool) -> bool:
    """Verifica que views criticas existem e respondem."""
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

    return all_ok


def _verificar_schema_version(checks: dict, all_ok: bool) -> bool:
    """Verifica versao do schema via app_settings."""
    try:
        result = (
            supabase.table("app_settings")
            .select("value")
            .eq("key", "schema_version")
            .single()
            .execute()
        )
        if result.data:
            current_version = result.data.get("value")
            checks["schema_version"]["current"] = current_version

            if current_version and current_version >= EXPECTED_SCHEMA_VERSION:
                checks["schema_version"]["status"] = "ok"
            else:
                checks["schema_version"]["status"] = "warning"
                checks["schema_version"]["message"] = (
                    f"Schema behind: {current_version} < {EXPECTED_SCHEMA_VERSION}"
                )
        else:
            checks["schema_version"]["status"] = "error"
            checks["schema_version"]["message"] = "schema_version not found in app_settings"
            all_ok = False
    except Exception as e:
        checks["schema_version"]["status"] = "error"
        checks["schema_version"]["message"] = str(e)
        logger.warning(f"[health/deep] Schema version check failed: {e}")

    return all_ok


async def _verificar_prompts(checks: dict, all_ok: bool) -> bool:
    """Verifica contrato de prompts."""
    prompt_result = await verificar_contrato_prompts()
    checks["prompts"] = prompt_result

    if prompt_result["status"] == "error":
        all_ok = False
        logger.error(f"[health/deep] Prompt contract FAILED: {prompt_result}")
    elif prompt_result["status"] == "warning":
        logger.warning(
            f"[health/deep] Prompt contract warnings: {prompt_result.get('missing_warnings', [])}"
        )

    return all_ok
