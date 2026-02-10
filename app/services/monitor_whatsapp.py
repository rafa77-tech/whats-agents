"""
Monitor de conexao WhatsApp.
Detecta problemas de criptografia e conexao, envia alertas e pode reiniciar automaticamente.
"""

import asyncio
import subprocess
import logging
from datetime import datetime, timedelta
from typing import Tuple

from app.core.config import settings
from app.core.timezone import agora_brasilia
from app.services.whatsapp import evolution

# Sprint 47: enviar_slack removido - alertas agora são apenas logados
from app.services.redis import cache_get_json, cache_set_json

logger = logging.getLogger(__name__)

# Configuracoes do monitor (V2 - baixo ruido)
# Ref: Slack V2 - SRE Review 31/12/2025
MONITOR_CONFIG = {
    "intervalo_verificacao_segundos": 300,  # Verificar a cada 5 min (era 60s)
    "threshold_erros_criptografia": 3,  # Alertar apos 3 erros
    "janela_erros_minutos": 5,  # Janela de tempo para contar erros
    "cooldown_alerta_minutos": 45,  # Cooldown aumentado (era 15min)
    "checks_consecutivos_para_alerta": 2,  # Alertar so apos 2 checks falhos
    "auto_restart_evolution": False,  # Desativado em prod Railway (nao tem docker local)
}

# Cache keys
CACHE_ULTIMO_ALERTA = "monitor:whatsapp:ultimo_alerta"
CACHE_CONTADOR_ERROS = "monitor:whatsapp:contador_erros"
CACHE_CHECKS_FALHOS = "monitor:whatsapp:checks_falhos_consecutivos"


async def verificar_conexao_whatsapp() -> Tuple[bool, str, dict]:
    """
    Verifica se a conexao WhatsApp esta funcionando.

    Returns:
        Tuple[bool, str, dict]: (conectado, status_msg, detalhes)
    """
    try:
        result = await evolution.verificar_conexao()

        state = result.get("instance", {}).get("state", "unknown")
        instance_name = result.get("instance", {}).get("instanceName", "unknown")

        if state == "open":
            return True, f"Conectado ({instance_name})", result
        else:
            return False, f"Desconectado - state: {state}", result

    except Exception as e:
        logger.error(f"Erro ao verificar conexao WhatsApp: {e}")
        return False, f"Erro: {str(e)}", {}


async def verificar_erros_criptografia_logs() -> Tuple[bool, int]:
    """
    Verifica logs da Evolution API para erros de criptografia.

    Returns:
        Tuple[bool, int]: (tem_erros, quantidade)
    """
    try:
        # Executar docker logs e procurar por PreKeyError
        result = subprocess.run(
            ["docker", "compose", "logs", "evolution-api", "--since", "5m"],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=settings.BASE_DIR if hasattr(settings, "BASE_DIR") else None,
        )

        logs = result.stdout + result.stderr

        # Contar erros de criptografia
        erros_prekey = logs.count("PreKeyError")
        erros_decrypt = logs.count("failed to decrypt")

        total_erros = erros_prekey + erros_decrypt

        if total_erros > 0:
            logger.warning(f"Detectados {total_erros} erros de criptografia nos logs")

        return total_erros > 0, total_erros

    except subprocess.TimeoutExpired:
        logger.error("Timeout ao verificar logs da Evolution API")
        return False, 0
    except Exception as e:
        logger.error(f"Erro ao verificar logs: {e}")
        return False, 0


async def enviar_alerta_conexao(tipo: str, mensagem: str, detalhes: dict = None):
    """
    Loga alerta de conexão.

    Sprint 47: Removida notificação Slack - dashboard monitora conexões.

    Args:
        tipo: Tipo do alerta (desconectado, criptografia, reconectado)
        mensagem: Mensagem descritiva
        detalhes: Detalhes adicionais
    """
    # Verificar cooldown para evitar spam de logs
    ultimo_alerta = await cache_get_json(CACHE_ULTIMO_ALERTA)
    if ultimo_alerta:
        ultimo_tipo = ultimo_alerta.get("tipo")
        ultimo_tempo = datetime.fromisoformat(ultimo_alerta.get("timestamp", "2000-01-01"))
        cooldown = timedelta(minutes=MONITOR_CONFIG["cooldown_alerta_minutos"])

        if ultimo_tipo == tipo and agora_brasilia() - ultimo_tempo < cooldown:
            logger.debug(f"Alerta {tipo} em cooldown, ignorando")
            return

    # Logar alerta
    log_level = logging.WARNING if tipo in ("desconectado", "criptografia") else logging.INFO
    logger.log(
        log_level,
        f"[MonitorWhatsApp] Alerta de conexão: {tipo}",
        extra={
            "tipo": tipo,
            "mensagem": mensagem,
            "detalhes": detalhes,
            "instancia": settings.EVOLUTION_INSTANCE,
        },
    )

    # Salvar no cache para cooldown
    await cache_set_json(
        CACHE_ULTIMO_ALERTA,
        {"tipo": tipo, "timestamp": agora_brasilia().isoformat(), "mensagem": mensagem},
        ttl=3600,
    )


async def _incrementar_checks_falhos() -> int:
    """
    Incrementa contador de checks falhos consecutivos.

    Returns:
        Numero de checks falhos consecutivos
    """
    try:
        dados = await cache_get_json(CACHE_CHECKS_FALHOS) or {"count": 0}
        dados["count"] = dados.get("count", 0) + 1
        dados["last_check"] = agora_brasilia().isoformat()
        await cache_set_json(CACHE_CHECKS_FALHOS, dados, ttl=3600)  # 1 hora
        return dados["count"]
    except Exception as e:
        logger.error(f"Erro ao incrementar checks falhos: {e}")
        return 1


async def _resetar_checks_falhos():
    """Reseta contador de checks falhos (conexao OK)."""
    try:
        await cache_set_json(CACHE_CHECKS_FALHOS, {"count": 0}, ttl=3600)
    except Exception as e:
        logger.error(f"Erro ao resetar checks falhos: {e}")


async def reiniciar_evolution_api():
    """
    Reinicia o container da Evolution API.
    """
    logger.warning("Reiniciando Evolution API...")

    await enviar_alerta_conexao(
        "reiniciando", "Reiniciando Evolution API devido a erros de criptografia"
    )

    try:
        result = subprocess.run(
            ["docker", "compose", "restart", "evolution-api"],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=settings.BASE_DIR if hasattr(settings, "BASE_DIR") else None,
        )

        if result.returncode == 0:
            logger.info("Evolution API reiniciada com sucesso")
            # Aguardar reconexao
            await asyncio.sleep(15)
            return True
        else:
            logger.error(f"Erro ao reiniciar Evolution API: {result.stderr}")
            return False

    except Exception as e:
        logger.error(f"Erro ao reiniciar Evolution API: {e}")
        return False


async def executar_verificacao_whatsapp():
    """
    Job principal de verificacao do WhatsApp.
    Executa todas as verificacoes e toma acoes necessarias.

    V2: Alerta so dispara apos N checks consecutivos falhos.
    Isso evita alertas por oscilacoes momentaneas.
    """
    logger.debug("Executando verificacao de conexao WhatsApp...")

    # 1. Verificar conexao basica
    conectado, status_msg, detalhes = await verificar_conexao_whatsapp()

    if not conectado:
        # V2: Incrementar contador de checks falhos
        checks_falhos = await _incrementar_checks_falhos()
        threshold = MONITOR_CONFIG["checks_consecutivos_para_alerta"]

        if checks_falhos >= threshold:
            await enviar_alerta_conexao("desconectado", status_msg, detalhes)
            return {
                "status": "desconectado",
                "mensagem": status_msg,
                "acao_tomada": "alerta_enviado",
                "checks_falhos": checks_falhos,
            }
        else:
            logger.warning(
                f"WhatsApp desconectado (check {checks_falhos}/{threshold}), "
                f"aguardando confirmacao antes de alertar"
            )
            return {
                "status": "desconectado_aguardando",
                "mensagem": f"Check {checks_falhos}/{threshold} - aguardando confirmacao",
                "acao_tomada": None,
            }
    else:
        # Conexao OK - resetar contador de checks falhos
        await _resetar_checks_falhos()

    # 2. Verificar erros de criptografia nos logs
    tem_erros, qtd_erros = await verificar_erros_criptografia_logs()

    if tem_erros and qtd_erros >= MONITOR_CONFIG["threshold_erros_criptografia"]:
        logger.warning(f"Detectados {qtd_erros} erros de criptografia")

        await enviar_alerta_conexao(
            "criptografia",
            f"Detectados {qtd_erros} erros de criptografia (PreKeyError). "
            f"Mensagens podem nao estar sendo recebidas.",
            {"erros": qtd_erros},
        )

        # Auto-restart se configurado
        if MONITOR_CONFIG["auto_restart_evolution"]:
            reiniciou = await reiniciar_evolution_api()

            if reiniciou:
                # Verificar se reconectou
                await asyncio.sleep(10)
                reconectado, _, _ = await verificar_conexao_whatsapp()

                if reconectado:
                    await enviar_alerta_conexao(
                        "reconectado", "Evolution API reiniciada e reconectada com sucesso"
                    )
                    return {
                        "status": "reconectado",
                        "mensagem": "Reiniciado automaticamente",
                        "acao_tomada": "restart_evolution",
                    }
                else:
                    return {
                        "status": "erro_persistente",
                        "mensagem": "Restart nao resolveu - intervencao manual necessaria",
                        "acao_tomada": "restart_falhou",
                    }

        return {
            "status": "erro_criptografia",
            "mensagem": f"{qtd_erros} erros detectados",
            "acao_tomada": "alerta_enviado",
        }

    # Tudo OK
    return {"status": "ok", "mensagem": status_msg, "acao_tomada": None}


async def iniciar_monitor_background():
    """
    Inicia o monitor em background (loop infinito).
    """
    logger.info("Iniciando monitor de conexao WhatsApp...")

    while True:
        try:
            resultado = await executar_verificacao_whatsapp()
            logger.debug(f"Verificacao WhatsApp: {resultado['status']}")
        except Exception as e:
            logger.error(f"Erro no monitor WhatsApp: {e}")

        await asyncio.sleep(MONITOR_CONFIG["intervalo_verificacao_segundos"])


# Funcao para testar manualmente
async def testar_monitor():
    """Executa uma verificacao manual do monitor."""
    print("Testando monitor de conexao WhatsApp...")

    # Verificar conexao
    conectado, msg, detalhes = await verificar_conexao_whatsapp()
    print(f"Conexao: {'OK' if conectado else 'ERRO'} - {msg}")

    # Verificar logs
    tem_erros, qtd = await verificar_erros_criptografia_logs()
    print(f"Erros de criptografia: {qtd}")

    # Executar verificacao completa
    resultado = await executar_verificacao_whatsapp()
    print(f"Resultado: {resultado}")

    return resultado
