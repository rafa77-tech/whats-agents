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
from app.services.whatsapp import evolution
from app.services.slack import enviar_slack
from app.services.redis import cache_get_json, cache_set_json

logger = logging.getLogger(__name__)

# Configuracoes do monitor
MONITOR_CONFIG = {
    "intervalo_verificacao_segundos": 60,  # Verificar a cada 60s
    "threshold_erros_criptografia": 3,  # Alertar apos 3 erros
    "janela_erros_minutos": 5,  # Janela de tempo para contar erros
    "cooldown_alerta_minutos": 15,  # Nao enviar alerta repetido em menos de 15min
    "auto_restart_evolution": True,  # Reiniciar Evolution automaticamente
}

# Cache keys
CACHE_ULTIMO_ALERTA = "monitor:whatsapp:ultimo_alerta"
CACHE_CONTADOR_ERROS = "monitor:whatsapp:contador_erros"


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
            cwd=settings.BASE_DIR if hasattr(settings, 'BASE_DIR') else None
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
    Envia alerta de conexao para o Slack.

    Args:
        tipo: Tipo do alerta (desconectado, criptografia, reconectado)
        mensagem: Mensagem descritiva
        detalhes: Detalhes adicionais
    """
    # Verificar cooldown
    ultimo_alerta = await cache_get_json(CACHE_ULTIMO_ALERTA)
    if ultimo_alerta:
        ultimo_tipo = ultimo_alerta.get("tipo")
        ultimo_tempo = datetime.fromisoformat(ultimo_alerta.get("timestamp", "2000-01-01"))
        cooldown = timedelta(minutes=MONITOR_CONFIG["cooldown_alerta_minutos"])

        # Nao enviar se mesmo tipo de alerta dentro do cooldown
        if ultimo_tipo == tipo and datetime.now() - ultimo_tempo < cooldown:
            logger.debug(f"Alerta {tipo} em cooldown, ignorando")
            return

    # Definir icone e cor baseado no tipo
    icones = {
        "desconectado": ":rotating_light:",
        "criptografia": ":warning:",
        "reconectado": ":white_check_mark:",
        "reiniciando": ":arrows_counterclockwise:",
    }
    cores = {
        "desconectado": "#F44336",  # Vermelho
        "criptografia": "#FF9800",  # Laranja
        "reconectado": "#4CAF50",   # Verde
        "reiniciando": "#2196F3",   # Azul
    }

    icone = icones.get(tipo, ":bell:")
    cor = cores.get(tipo, "#607D8B")

    # Montar mensagem Slack
    slack_msg = {
        "text": f"{icone} WhatsApp Monitor: {tipo.upper()}",
        "attachments": [{
            "color": cor,
            "fields": [
                {"title": "Status", "value": mensagem, "short": False},
                {"title": "Horario", "value": datetime.now().strftime("%d/%m/%Y %H:%M:%S"), "short": True},
                {"title": "Instancia", "value": settings.EVOLUTION_INSTANCE, "short": True},
            ]
        }]
    }

    if detalhes:
        slack_msg["attachments"][0]["fields"].append({
            "title": "Detalhes",
            "value": str(detalhes)[:200],
            "short": False
        })

    try:
        await enviar_slack(slack_msg)
        logger.info(f"Alerta de conexao enviado: {tipo}")

        # Salvar no cache
        await cache_set_json(CACHE_ULTIMO_ALERTA, {
            "tipo": tipo,
            "timestamp": datetime.now().isoformat(),
            "mensagem": mensagem
        }, ttl=3600)  # 1 hora

    except Exception as e:
        logger.error(f"Erro ao enviar alerta Slack: {e}")


async def reiniciar_evolution_api():
    """
    Reinicia o container da Evolution API.
    """
    logger.warning("Reiniciando Evolution API...")

    await enviar_alerta_conexao(
        "reiniciando",
        "Reiniciando Evolution API devido a erros de criptografia"
    )

    try:
        result = subprocess.run(
            ["docker", "compose", "restart", "evolution-api"],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=settings.BASE_DIR if hasattr(settings, 'BASE_DIR') else None
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
    """
    logger.debug("Executando verificacao de conexao WhatsApp...")

    # 1. Verificar conexao basica
    conectado, status_msg, detalhes = await verificar_conexao_whatsapp()

    if not conectado:
        await enviar_alerta_conexao("desconectado", status_msg, detalhes)
        return {
            "status": "desconectado",
            "mensagem": status_msg,
            "acao_tomada": "alerta_enviado"
        }

    # 2. Verificar erros de criptografia nos logs
    tem_erros, qtd_erros = await verificar_erros_criptografia_logs()

    if tem_erros and qtd_erros >= MONITOR_CONFIG["threshold_erros_criptografia"]:
        logger.warning(f"Detectados {qtd_erros} erros de criptografia")

        await enviar_alerta_conexao(
            "criptografia",
            f"Detectados {qtd_erros} erros de criptografia (PreKeyError). "
            f"Mensagens podem nao estar sendo recebidas.",
            {"erros": qtd_erros}
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
                        "reconectado",
                        "Evolution API reiniciada e reconectada com sucesso"
                    )
                    return {
                        "status": "reconectado",
                        "mensagem": "Reiniciado automaticamente",
                        "acao_tomada": "restart_evolution"
                    }
                else:
                    return {
                        "status": "erro_persistente",
                        "mensagem": "Restart nao resolveu - intervencao manual necessaria",
                        "acao_tomada": "restart_falhou"
                    }

        return {
            "status": "erro_criptografia",
            "mensagem": f"{qtd_erros} erros detectados",
            "acao_tomada": "alerta_enviado"
        }

    # Tudo OK
    return {
        "status": "ok",
        "mensagem": status_msg,
        "acao_tomada": None
    }


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
