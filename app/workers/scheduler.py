"""
Scheduler para executar jobs agendados.
"""
import asyncio
import httpx
import logging
import sys
import uuid
from datetime import datetime, timezone
from typing import Optional
from app.core.config import settings

# Configurar logging para stdout (Railway captura stdout)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    stream=sys.stdout,
    force=True
)
logger = logging.getLogger(__name__)

# URL da API
JULIA_API_URL = settings.JULIA_API_URL

# Supabase para persistência de execuções
SUPABASE_URL = settings.SUPABASE_URL
SUPABASE_KEY = settings.SUPABASE_SERVICE_KEY


async def _registrar_inicio_job(job_name: str) -> str:
    """Registra início de execução de job. Retorna execution_id."""
    execution_id = str(uuid.uuid4())
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{SUPABASE_URL}/rest/v1/job_executions",
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}",
                    "Content-Type": "application/json",
                    "Prefer": "return=minimal",
                },
                json={
                    "id": execution_id,
                    "job_name": job_name,
                    "started_at": datetime.now(timezone.utc).isoformat(),
                    "status": "running",
                },
            )
            if response.status_code not in (200, 201):
                logger.warning(f"Erro ao registrar início do job: {response.status_code}")
    except Exception as e:
        logger.warning(f"Erro ao registrar início do job: {e}")
    return execution_id


async def _registrar_fim_job(
    execution_id: str,
    status: str,
    duration_ms: int,
    response_code: Optional[int] = None,
    error: Optional[str] = None,
    items_processed: Optional[int] = None,
):
    """Registra fim de execução de job."""
    try:
        data = {
            "finished_at": datetime.now(timezone.utc).isoformat(),
            "status": status,
            "duration_ms": duration_ms,
        }
        if response_code is not None:
            data["response_code"] = response_code
        if error is not None:
            data["error"] = error[:500]  # Limitar tamanho do erro
        if items_processed is not None:
            data["items_processed"] = items_processed

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.patch(
                f"{SUPABASE_URL}/rest/v1/job_executions?id=eq.{execution_id}",
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}",
                    "Content-Type": "application/json",
                    "Prefer": "return=minimal",
                },
                json=data,
            )
            if response.status_code not in (200, 204):
                logger.warning(f"Erro ao registrar fim do job: {response.status_code}")
    except Exception as e:
        logger.warning(f"Erro ao registrar fim do job: {e}")


JOBS = [
    {
        "name": "processar_mensagens_agendadas",
        "endpoint": "/jobs/processar-mensagens-agendadas",
        "schedule": "* * * * *",  # A cada minuto
    },
    {
        "name": "processar_campanhas_agendadas",
        "endpoint": "/jobs/processar-campanhas-agendadas",
        "schedule": "* * * * *",  # A cada minuto
    },
    {
        "name": "verificar_alertas",
        "endpoint": "/jobs/verificar-alertas",
        "schedule": "*/15 * * * *",  # A cada 15 minutos
    },
    {
        "name": "processar_followups",
        "endpoint": "/jobs/processar-followups",
        "schedule": "0 10 * * *",  # Diário às 10h
    },
    {
        "name": "processar_pausas_expiradas",
        "endpoint": "/jobs/processar-pausas-expiradas",
        "schedule": "0 6 * * *",  # Diário às 6h
    },
    # REMOVIDO: followup_diario (duplicado de processar_followups)
    # Ref: Slack V2 - SRE Review 31/12/2025
    {
        "name": "avaliar_conversas_pendentes",
        "endpoint": "/jobs/avaliar-conversas-pendentes",
        "schedule": "0 2 * * *",  # Diário às 2h
    },
    # REMOVIDO: relatorio_diario (legado, substituido por reports periodicos)
    # Ref: Slack V2 - SRE Review 31/12/2025
    # Reports periódicos (V2 - reduzido para 2x por dia + semanal)
    # Ref: Slack V2 - SRE Review 31/12/2025
    # Removidos: report_almoco e report_tarde (ruido excessivo)
    {
        "name": "report_manha",
        "endpoint": "/jobs/report-periodo?tipo=manha",
        "schedule": "0 10 * * *",  # 10h todos os dias
    },
    # REMOVIDO: report_almoco (13h) - ruido excessivo
    # REMOVIDO: report_tarde (17h) - ruido excessivo
    {
        "name": "report_fim_dia",
        "endpoint": "/jobs/report-periodo?tipo=fim_dia",
        "schedule": "0 20 * * *",  # 20h todos os dias
    },
    {
        "name": "report_semanal",
        "endpoint": "/jobs/report-semanal",
        "schedule": "0 9 * * 1",  # Segunda às 9h
    },
    {
        "name": "atualizar_prompt_feedback",
        "endpoint": "/jobs/atualizar-prompt-feedback",
        "schedule": "0 2 * * 0",  # Semanal (domingo às 2h)
    },
    # Manutenção do doctor_state (Sprint 15 - Policy Engine)
    {
        "name": "doctor_state_manutencao_diaria",
        "endpoint": "/jobs/doctor-state-manutencao-diaria",
        "schedule": "0 3 * * *",  # Diário às 3h
    },
    {
        "name": "doctor_state_manutencao_semanal",
        "endpoint": "/jobs/doctor-state-manutencao-semanal",
        "schedule": "0 4 * * 1",  # Segunda às 4h
    },
    # Sincronizacao de briefing (Google Docs)
    {
        "name": "sincronizar_briefing",
        "endpoint": "/jobs/sincronizar-briefing",
        "schedule": "0 * * * *",  # A cada hora, minuto 0
    },
    # Sincronizacao de templates de campanha (Google Docs)
    {
        "name": "sincronizar_templates",
        "endpoint": "/jobs/sync-templates",
        "schedule": "0 6 * * *",  # Diário às 6h
    },
    # Monitor de conexao WhatsApp (V2 - baixo ruido)
    {
        "name": "verificar_whatsapp",
        "endpoint": "/jobs/verificar-whatsapp",
        "schedule": "*/5 * * * *",  # A cada 5 minutos (era 1 min)
    },
    # Processamento de grupos WhatsApp (Sprint 14)
    {
        "name": "processar_grupos",
        "endpoint": "/jobs/processar-grupos",
        "schedule": "* * * * *",  # A cada minuto (batch_size=200, max_workers=20)
    },
    {
        "name": "limpar_grupos_finalizados",
        "endpoint": "/jobs/limpar-grupos-finalizados",
        "schedule": "0 3 * * *",  # Diário às 3h
    },
    {
        "name": "verificar_alertas_grupos",
        "endpoint": "/jobs/verificar-alertas-grupos",
        "schedule": "*/15 * * * *",  # A cada 15 minutos
    },
    {
        "name": "consolidar_metricas_grupos",
        "endpoint": "/jobs/consolidar-metricas-grupos",
        "schedule": "0 1 * * *",  # Diário à 1h (consolida dia anterior)
    },
    # Confirmação de plantão (Sprint 17)
    {
        "name": "processar_confirmacao_plantao",
        "endpoint": "/jobs/processar-confirmacao-plantao",
        "schedule": "0 * * * *",  # A cada hora, minuto 0
    },
    # External Handoff - Follow-up e Expiracao (Sprint 20)
    {
        "name": "processar_handoffs",
        "endpoint": "/jobs/processar-handoffs",
        "schedule": "*/10 * * * *",  # A cada 10 minutos
    },
    # Retomada de mensagens fora do horario (Sprint 22)
    {
        "name": "processar_retomadas",
        "endpoint": "/jobs/processar-retomadas",
        "schedule": "0 8 * * 1-5",  # 08:00 seg-sex
    },
]


def parse_cron(schedule: str) -> dict:
    """Parse cron expression simples."""
    parts = schedule.split()
    if len(parts) != 5:
        raise ValueError(f"Cron inválido: {schedule}")
    return {
        "minute": parts[0],
        "hour": parts[1],
        "day": parts[2],
        "month": parts[3],
        "weekday": parts[4],
    }


def matches_cron_field(field: str, value: int) -> bool:
    """Verifica se valor corresponde ao campo cron."""
    if field == "*":
        return True
    
    # Suporta */N (a cada N)
    if field.startswith("*/"):
        interval = int(field[2:])
        return value % interval == 0
    
    # Suporta lista (1,2,3)
    if "," in field:
        return str(value) in field.split(",")
    
    # Valor exato
    return str(value) == field


def should_run(schedule: str, now: datetime) -> bool:
    """Verifica se job deve executar agora."""
    try:
        cron = parse_cron(schedule)
    except ValueError as e:
        logger.error(f"Erro ao parsear cron {schedule}: {e}")
        return False
    
    # Verificar minuto
    if not matches_cron_field(cron["minute"], now.minute):
        return False
    
    # Verificar hora
    if not matches_cron_field(cron["hour"], now.hour):
        return False
    
    # Verificar dia do mês
    if not matches_cron_field(cron["day"], now.day):
        return False
    
    # Verificar mês
    if not matches_cron_field(cron["month"], now.month):
        return False
    
    # Verificar dia da semana (0=domingo, 6=sábado)
    # Cron: 0=domingo, 7=domingo também
    if cron["weekday"] != "*":
        weekday_cron = cron["weekday"]
        weekday_now = now.weekday()  # 0=segunda, 6=domingo
        # Converter: Python weekday -> Cron weekday
        # Python: 0=seg, 1=ter, ..., 6=dom
        # Cron: 0=dom, 1=seg, ..., 6=sab
        cron_weekday = (weekday_now + 1) % 7
        if not matches_cron_field(weekday_cron, cron_weekday):
            return False
    
    return True


async def execute_job(job: dict):
    """Executa um job com persistência de histórico."""
    import time
    start_time = time.time()
    execution_id = await _registrar_inicio_job(job["name"])

    try:
        url = f"{JULIA_API_URL}{job['endpoint']}"
        logger.info(f"🔄 Executando job: {job['name']} -> {url}")

        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(url)
            duration_ms = int((time.time() - start_time) * 1000)

            if response.status_code == 200:
                # Tentar extrair info do response para log
                items_processed = None
                try:
                    data = response.json()
                    items_processed = data.get("processados", data.get("count", data.get("total")))
                    count_str = items_processed if items_processed is not None else "?"
                    print(f"   ✅ {job['name']} OK (processados: {count_str})", flush=True)
                except Exception:
                    print(f"   ✅ {job['name']} OK", flush=True)

                logger.info(f"✅ Job {job['name']} executado com sucesso")

                # Persistir sucesso
                await _registrar_fim_job(
                    execution_id=execution_id,
                    status="success",
                    duration_ms=duration_ms,
                    response_code=response.status_code,
                    items_processed=items_processed,
                )
            else:
                print(f"   ❌ {job['name']} FAIL: {response.status_code}", flush=True)
                logger.error(f"❌ Job {job['name']} falhou: {response.status_code} - {response.text}")

                # Persistir erro
                await _registrar_fim_job(
                    execution_id=execution_id,
                    status="error",
                    duration_ms=duration_ms,
                    response_code=response.status_code,
                    error=response.text[:500] if response.text else None,
                )

    except httpx.TimeoutException:
        duration_ms = int((time.time() - start_time) * 1000)
        print(f"   ⏱️ {job['name']} TIMEOUT", flush=True)
        logger.error(f"⏱️  Timeout ao executar job {job['name']}")

        # Persistir timeout
        await _registrar_fim_job(
            execution_id=execution_id,
            status="timeout",
            duration_ms=duration_ms,
            error="Timeout após 300s",
        )

    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        print(f"   ❌ {job['name']} ERROR: {e}", flush=True)
        logger.error(f"❌ Erro ao executar job {job['name']}: {e}", exc_info=True)

        # Persistir erro
        await _registrar_fim_job(
            execution_id=execution_id,
            status="error",
            duration_ms=duration_ms,
            error=str(e),
        )


async def scheduler_loop():
    """Loop principal do scheduler."""
    print("=" * 60, flush=True)
    print("🕐 SCHEDULER INICIADO", flush=True)
    print(f"📡 API URL: {JULIA_API_URL}", flush=True)
    print(f"📋 {len(JOBS)} jobs configurados:", flush=True)
    for job in JOBS:
        print(f"   - {job['name']} ({job['schedule']})", flush=True)
    print("=" * 60, flush=True)

    logger.info("🕐 Scheduler iniciado")
    logger.info(f"📡 API URL: {JULIA_API_URL}")
    logger.info(f"📋 {len(JOBS)} jobs configurados")
    
    last_minute = -1
    
    while True:
        try:
            now = datetime.now()
            
            # Executar jobs apenas no início de cada minuto
            if now.minute != last_minute:
                last_minute = now.minute
                
                for job in JOBS:
                    if should_run(job["schedule"], now):
                        print(f"⏰ [{now.strftime('%H:%M:%S')}] Trigger: {job['name']}", flush=True)
                        logger.info(f"⏰ Trigger: {job['name']} (schedule: {job['schedule']})")
                        await execute_job(job)
            
            # Aguardar até próximo segundo
            await asyncio.sleep(1)
            
        except KeyboardInterrupt:
            logger.info("🛑 Scheduler interrompido")
            break
        except Exception as e:
            logger.error(f"❌ Erro no scheduler: {e}", exc_info=True)
            await asyncio.sleep(10)  # Aguardar antes de retry


if __name__ == "__main__":
    asyncio.run(scheduler_loop())

