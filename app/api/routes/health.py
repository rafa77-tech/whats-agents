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
from app.core.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)

# Hard guards de ambiente - CRÍTICO para evitar staging↔prod mix
APP_ENV = os.getenv("APP_ENV", "development")
SUPABASE_PROJECT_REF = os.getenv("SUPABASE_PROJECT_REF", "")

# Versioning info (injected by CI/CD build or Railway runtime)
# Railway fornece RAILWAY_GIT_COMMIT_SHA automaticamente em runtime
# Nota: Dockerfile seta GIT_SHA="unknown" como default, então precisamos ignorar esse valor
def _get_version_var(explicit_name: str, railway_name: str) -> str:
    """Busca variável de versão, ignorando 'unknown' do Dockerfile."""
    explicit = os.getenv(explicit_name)
    railway = os.getenv(railway_name)
    # Ignora se for "unknown" (default do Dockerfile)
    if explicit and explicit != "unknown":
        return explicit
    if railway:
        return railway
    return "unknown"

GIT_SHA = _get_version_var("GIT_SHA", "RAILWAY_GIT_COMMIT_SHA")
DEPLOYMENT_ID = _get_version_var("BUILD_TIME", "RAILWAY_DEPLOYMENT_ID")
RAILWAY_ENVIRONMENT = os.getenv("RAILWAY_ENVIRONMENT", "unknown")
RUN_MODE = os.getenv("RUN_MODE", "unknown")

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
EXPECTED_SCHEMA_VERSION = "20251231211500"  # create_get_table_columns_for_fingerprint

# Contrato de prompts - sentinelas obrigatórias para deploy seguro
REQUIRED_PROMPTS = {
    "julia_base": {
        "min_len": 2000,
        "required_sentinels": [
            "[INVARIANT:INBOUND_ALWAYS_REPLY]",
            "[INVARIANT:OPTOUT_ABSOLUTE]",
            "[INVARIANT:KILL_SWITCHES_PRIORITY]",
            "[INVARIANT:NO_CONFIRM_WITHOUT_RESERVATION]",
            "[INVARIANT:NO_IDENTITY_DEBATE]",
            "[CAPABILITY:HANDOFF]",  # Promovido para BLOQUEADOR - handoff é crítico
            "[FALLBACK:DIRETRIZES_EMPTY_OK]",
        ],
        "warning_sentinels": [
            "[INVARIANT:OUTBOUND_QUIET_HOURS]",
            "[INVARIANT:NO_METACOMMUNICATION]",
        ],
    },
    "julia_primeira_msg": {
        "min_len": 100,
        "required_sentinels": [],
        "warning_sentinels": [],
    },
    "julia_tools": {
        "min_len": 300,
        "required_sentinels": [],
        "warning_sentinels": [],
    },
}


def _generate_schema_fingerprint() -> dict:
    """
    Gera fingerprint do schema para detecção de drift.

    Contrato:
    - hash(sorted(table_names) + sorted(column_definitions))
    - Inclui apenas tabelas críticas
    - Mudança no fingerprint indica possível drift

    Returns:
        dict com fingerprint e detalhes
    """
    import hashlib

    try:
        # Buscar estrutura das tabelas críticas
        result = supabase.rpc(
            "get_table_columns_for_fingerprint",
            {"table_names": CRITICAL_TABLES}
        ).execute()

        if not result.data:
            # Fallback: usar query direta
            columns_query = supabase.table("information_schema.columns").select(
                "table_name, column_name, data_type, is_nullable"
            ).in_("table_name", CRITICAL_TABLES).execute()

            if columns_query.data:
                columns = columns_query.data
            else:
                return {
                    "fingerprint": "error",
                    "error": "Could not fetch schema info",
                    "tables_checked": CRITICAL_TABLES,
                }
        else:
            columns = result.data

        # Ordenar por tabela e coluna para consistência
        sorted_columns = sorted(
            columns,
            key=lambda c: (c.get("table_name", ""), c.get("column_name", ""))
        )

        # Criar string para hash
        fingerprint_str = ""
        for col in sorted_columns:
            fingerprint_str += f"{col.get('table_name', '')}:{col.get('column_name', '')}:{col.get('data_type', '')}:{col.get('is_nullable', '')}|"

        # Gerar hash SHA256 truncado (primeiros 16 chars)
        fingerprint = hashlib.sha256(fingerprint_str.encode()).hexdigest()[:16]

        return {
            "fingerprint": fingerprint,
            "tables_checked": CRITICAL_TABLES,
            "columns_count": len(sorted_columns),
        }

    except Exception as e:
        logger.warning(f"[health] Schema fingerprint generation failed: {e}")
        # Fallback simples: hash da lista de tabelas
        import hashlib
        simple_fp = hashlib.sha256(
            "|".join(sorted(CRITICAL_TABLES)).encode()
        ).hexdigest()[:16]

        return {
            "fingerprint": f"fallback-{simple_fp}",
            "tables_checked": CRITICAL_TABLES,
            "error": str(e),
        }


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


async def _check_prompt_contract() -> dict:
    """
    Valida contrato de prompts.

    Retorna dict com:
    - status: ok | error | warning
    - missing: prompts que não existem
    - inactive: prompts que existem mas não estão ativos
    - too_short: prompts com tamanho abaixo do mínimo
    - missing_sentinels: sentinelas obrigatórias ausentes
    - missing_warnings: sentinelas de warning ausentes
    - versions: versão de cada prompt
    """
    result = {
        "status": "pending",
        "missing": [],
        "inactive": [],
        "too_short": [],
        "missing_sentinels": [],
        "missing_warnings": [],
        "versions": {},
    }

    has_error = False
    has_warning = False

    try:
        # Buscar todos os prompts necessários
        response = supabase.table("prompts").select(
            "nome, versao, ativo, conteudo"
        ).in_("nome", list(REQUIRED_PROMPTS.keys())).execute()

        found = {r["nome"]: r for r in (response.data or [])}

        for nome, req in REQUIRED_PROMPTS.items():
            prompt = found.get(nome)

            # Check existência
            if not prompt:
                result["missing"].append(nome)
                has_error = True
                continue

            # Check ativo
            if not prompt.get("ativo"):
                result["inactive"].append(nome)
                has_error = True
                continue

            # Registrar versão
            result["versions"][nome] = prompt.get("versao")

            conteudo = prompt.get("conteudo") or ""

            # Check tamanho mínimo
            if len(conteudo) < req["min_len"]:
                result["too_short"].append({
                    "nome": nome,
                    "len": len(conteudo),
                    "min": req["min_len"]
                })
                has_error = True

            # Check sentinelas obrigatórias (BLOQUEADOR)
            for sentinel in req.get("required_sentinels", []):
                if sentinel not in conteudo:
                    result["missing_sentinels"].append({
                        "prompt": nome,
                        "sentinel": sentinel
                    })
                    has_error = True

            # Check sentinelas de warning
            for sentinel in req.get("warning_sentinels", []):
                if sentinel not in conteudo:
                    result["missing_warnings"].append({
                        "prompt": nome,
                        "sentinel": sentinel
                    })
                    has_warning = True

        if has_error:
            result["status"] = "error"
        elif has_warning:
            result["status"] = "warning"
        else:
            result["status"] = "ok"

    except Exception as e:
        result["status"] = "error"
        result["message"] = str(e)
        logger.error(f"[health/deep] Prompt contract check failed: {e}")

    return result


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
    - Prompts: prompts core existem, ativos, com sentinelas obrigatórias

    Retorna 200 se TUDO ok, 503 se qualquer check falhar.
    CI/CD deve usar este endpoint para validar deploy.

    HARD GUARDS: Environment e Project Ref são verificados PRIMEIRO.
    Se não baterem, o deploy é considerado CRÍTICO e deve ser revertido.
    """
    checks = {
        "environment": {"status": "pending", "app_env": APP_ENV, "db_env": None},
        "project_ref": {"status": "pending", "app_ref": SUPABASE_PROJECT_REF, "db_ref": None},
        "dev_guardrails": {"status": "pending"},  # DEV allowlist validation
        "redis": {"status": "pending", "message": None},
        "supabase": {"status": "pending", "message": None},
        "tables": {"status": "pending", "missing": []},
        "views": {"status": "pending", "missing": []},
        "schema_version": {"status": "pending", "current": None, "expected": EXPECTED_SCHEMA_VERSION},
        "prompts": {"status": "pending"},
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

    # 0c. DEV GUARDRAILS: Validar que ambiente DEV tem proteções configuradas
    # Em DEV (APP_ENV != production), OUTBOUND_ALLOWLIST não pode estar vazia
    # Isso garante fail-closed: DEV sem allowlist = não envia para ninguém
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
        # Em PROD, este check é skipped
        checks["dev_guardrails"] = {
            "status": "skipped",
            "message": "Production environment - DEV guardrails not applicable",
            "app_env": settings.APP_ENV,
            "is_production": True,
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

    # 5. Check schema version (via app_settings - contrato Sprint 18)
    try:
        result = supabase.table("app_settings").select("value").eq("key", "schema_version").single().execute()
        if result.data:
            current_version = result.data.get("value")
            checks["schema_version"]["current"] = current_version

            # Comparar versões (são strings no formato YYYYMMDDHHMMSS)
            if current_version and current_version >= EXPECTED_SCHEMA_VERSION:
                checks["schema_version"]["status"] = "ok"
            else:
                checks["schema_version"]["status"] = "warning"
                checks["schema_version"]["message"] = f"Schema behind: {current_version} < {EXPECTED_SCHEMA_VERSION}"
                # Warning não falha o deploy, mas avisa
        else:
            checks["schema_version"]["status"] = "error"
            checks["schema_version"]["message"] = "schema_version not found in app_settings"
            all_ok = False
    except Exception as e:
        checks["schema_version"]["status"] = "error"
        checks["schema_version"]["message"] = str(e)
        # Não falha se não conseguir verificar versão
        logger.warning(f"[health/deep] Schema version check failed: {e}")

    # 6. Check prompt contract (sentinelas obrigatórias)
    prompt_result = await _check_prompt_contract()
    checks["prompts"] = prompt_result

    if prompt_result["status"] == "error":
        all_ok = False
        logger.error(f"[health/deep] Prompt contract FAILED: {prompt_result}")
    elif prompt_result["status"] == "warning":
        logger.warning(f"[health/deep] Prompt contract warnings: {prompt_result.get('missing_warnings', [])}")

    # Resultado final
    overall_status = "healthy" if all_ok else "unhealthy"

    if not all_ok:
        response.status_code = 503
        logger.error(f"[health/deep] FAILED: {checks}")

    # Gerar schema fingerprint para detecção de drift
    schema_fp = _generate_schema_fingerprint()

    return {
        "status": overall_status,
        "version": {
            "git_sha": GIT_SHA,
            "deployment_id": DEPLOYMENT_ID,
            "railway_environment": RAILWAY_ENVIRONMENT,
            "run_mode": RUN_MODE,
        },
        "schema": schema_fp,
        "checks": checks,
        "timestamp": datetime.utcnow().isoformat(),
        "deploy_safe": all_ok,
    }


@router.get("/health/schema")
async def schema_info():
    """
    Retorna informações do schema do banco.

    Útil para debug e verificação manual.
    Usa app_settings como fonte de verdade (contrato Sprint 18).
    """
    try:
        # Buscar schema_version e schema_applied_at de app_settings
        result = supabase.table("app_settings").select("key, value").in_(
            "key", ["schema_version", "schema_applied_at"]
        ).execute()

        settings_map = {r["key"]: r["value"] for r in (result.data or [])}
        current_version = settings_map.get("schema_version")
        applied_at = settings_map.get("schema_applied_at")

        # Gerar fingerprint
        schema_fp = _generate_schema_fingerprint()

        return {
            "current_version": current_version,
            "expected_version": EXPECTED_SCHEMA_VERSION,
            "schema_up_to_date": current_version >= EXPECTED_SCHEMA_VERSION if current_version else False,
            "applied_at": applied_at,
            "fingerprint": schema_fp.get("fingerprint"),
            "critical_tables": CRITICAL_TABLES,
            "critical_views": CRITICAL_VIEWS,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        return {
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
        }


# SLA por job: max_age_seconds baseado na frequência do cron
# Se job não roda há mais tempo que o SLA, é considerado "stale" (crítico)
JOB_SLA_SECONDS = {
    # Jobs de 1 minuto: SLA = 3 minutos (3x a frequência)
    "processar_mensagens_agendadas": 180,
    "processar_campanhas_agendadas": 180,
    # Jobs de 5 minutos: SLA = 15 minutos
    "verificar_whatsapp": 900,
    "processar_grupos": 900,
    # Jobs de 10 minutos: SLA = 30 minutos
    "processar_handoffs": 1800,
    # Jobs de 15 minutos: SLA = 45 minutos
    "verificar_alertas": 2700,
    "verificar_alertas_grupos": 2700,
    # Jobs horários: SLA = 2 horas
    "sincronizar_briefing": 7200,
    "processar_confirmacao_plantao": 7200,
    # Jobs diários: SLA = 25 horas (margem para variação)
    "processar_followups": 90000,
    "processar_pausas_expiradas": 90000,
    "avaliar_conversas_pendentes": 90000,
    "report_manha": 90000,
    "report_fim_dia": 90000,
    "sincronizar_templates": 90000,
    "limpar_grupos_finalizados": 90000,
    "consolidar_metricas_grupos": 90000,
    "doctor_state_manutencao_diaria": 90000,
    # Jobs semanais: SLA = 8 dias
    "report_semanal": 691200,
    "atualizar_prompt_feedback": 691200,
    "doctor_state_manutencao_semanal": 691200,
    # Jobs seg-sex: SLA = 3 dias (pode pular fim de semana)
    "processar_retomadas": 259200,
}

# Jobs críticos que DEVEM estar rodando para o sistema funcionar
CRITICAL_JOBS = [
    "processar_mensagens_agendadas",
    "processar_campanhas_agendadas",
    "verificar_whatsapp",
    "processar_grupos",
]


@router.get("/health/jobs")
async def job_executions_status():
    """
    Retorna status das execuções dos jobs do scheduler.

    Sprint 18 - GAP 1: Observabilidade de jobs.

    Mostra:
    - Última execução de cada job
    - Status (success/error/timeout)
    - Duração média
    - Erros nas últimas 24h
    - **Stale jobs** (não rodaram dentro do SLA)

    Status:
    - healthy: Todos jobs OK
    - degraded: Erros ou timeouts, mas jobs rodando
    - critical: Jobs críticos stale (scheduler pode estar morto)
    """
    try:
        from datetime import timedelta

        now = datetime.utcnow()

        # Últimas 24h
        since = (now - timedelta(hours=24)).isoformat()

        # Buscar todas execuções das últimas 24h
        result = supabase.table("job_executions").select(
            "job_name, started_at, finished_at, status, duration_ms, items_processed, error"
        ).gte("started_at", since).order("started_at", desc=True).execute()

        executions = result.data or []

        # Agrupar por job
        jobs_summary = {}
        for ex in executions:
            name = ex["job_name"]
            if name not in jobs_summary:
                jobs_summary[name] = {
                    "last_run": None,
                    "last_status": None,
                    "runs_24h": 0,
                    "success_24h": 0,
                    "errors_24h": 0,
                    "timeouts_24h": 0,
                    "avg_duration_ms": 0,
                    "total_items_processed": 0,
                    "last_error": None,
                    "durations": [],
                    "sla_seconds": JOB_SLA_SECONDS.get(name),
                    "is_stale": False,
                    "seconds_since_last_run": None,
                }

            summary = jobs_summary[name]
            summary["runs_24h"] += 1

            # Primeira execução encontrada = mais recente
            if summary["last_run"] is None:
                summary["last_run"] = ex["started_at"]
                summary["last_status"] = ex["status"]

                # Calcular idade da última execução
                try:
                    last_run_dt = datetime.fromisoformat(ex["started_at"].replace("+00:00", "").replace("Z", ""))
                    age_seconds = (now - last_run_dt).total_seconds()
                    summary["seconds_since_last_run"] = int(age_seconds)

                    # Verificar se está stale
                    sla = JOB_SLA_SECONDS.get(name)
                    if sla and age_seconds > sla:
                        summary["is_stale"] = True
                except Exception:
                    pass

            # Contadores por status
            if ex["status"] == "success":
                summary["success_24h"] += 1
            elif ex["status"] == "error":
                summary["errors_24h"] += 1
                if summary["last_error"] is None:
                    summary["last_error"] = ex.get("error")
            elif ex["status"] == "timeout":
                summary["timeouts_24h"] += 1

            # Duração
            if ex.get("duration_ms"):
                summary["durations"].append(ex["duration_ms"])

            # Items processados
            if ex.get("items_processed"):
                summary["total_items_processed"] += ex["items_processed"]

        # Calcular médias e limpar
        for name, summary in jobs_summary.items():
            if summary["durations"]:
                summary["avg_duration_ms"] = int(sum(summary["durations"]) / len(summary["durations"]))
            del summary["durations"]

        # Coletar alertas
        jobs_with_errors = [n for n, s in jobs_summary.items() if s["errors_24h"] > 0]
        jobs_with_timeouts = [n for n, s in jobs_summary.items() if s["timeouts_24h"] > 0]
        stale_jobs = [n for n, s in jobs_summary.items() if s["is_stale"]]

        # Jobs críticos que não aparecem (nunca rodaram ou não rodaram nas últimas 24h)
        missing_critical = [j for j in CRITICAL_JOBS if j not in jobs_summary]

        # Jobs críticos que estão stale
        critical_stale = [j for j in stale_jobs if j in CRITICAL_JOBS]

        # Determinar status geral
        status = "healthy"

        if jobs_with_errors or jobs_with_timeouts:
            status = "degraded"

        # CRITICAL: scheduler pode estar morto
        if critical_stale or missing_critical:
            status = "critical"

        return {
            "status": status,
            "jobs": jobs_summary,
            "alerts": {
                "jobs_with_errors": jobs_with_errors,
                "jobs_with_timeouts": jobs_with_timeouts,
                "stale_jobs": stale_jobs,
                "critical_stale": critical_stale,
                "missing_critical": missing_critical,
            },
            "sla_config": {
                "critical_jobs": CRITICAL_JOBS,
                "sla_definitions": JOB_SLA_SECONDS,
            },
            "period": "24h",
            "total_executions": len(executions),
            "timestamp": now.isoformat(),
        }

    except Exception as e:
        logger.error(f"[health/jobs] Error: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
        }
