"""
Cliente Evolution API para WhatsApp.

Sprint 18.1 - B2: Retry/backoff antes do circuit breaker.
"""

import asyncio
import random
import httpx
from typing import Literal
import logging

from app.core.config import settings
from app.services.circuit_breaker import circuit_evolution
from app.services.rate_limiter import pode_enviar, registrar_envio

logger = logging.getLogger(__name__)


# =============================================================================
# RETRY CONFIG (Sprint 18.1 - B2)
# =============================================================================

RETRY_CONFIG = {
    "max_attempts": 4,
    "base_delays": [0.5, 1.0, 2.0, 4.0],  # Exponencial
    "jitter_factor": 0.25,  # ±25%
    "retryable_status_codes": {408, 425, 429, 500, 502, 503, 504},
    "non_retryable_status_codes": {400, 401, 403, 404, 422},
}


class RateLimitError(Exception):
    """Exceção quando rate limit é atingido."""

    def __init__(self, motivo: str):
        self.motivo = motivo
        super().__init__(f"Rate limit: {motivo}")


class EvolutionClient:
    """Cliente para Evolution API."""

    def __init__(self):
        self.base_url = settings.EVOLUTION_API_URL
        self.api_key = settings.EVOLUTION_API_KEY
        self.instance = settings.EVOLUTION_INSTANCE

        if not self.api_key:
            raise ValueError("EVOLUTION_API_KEY e obrigatorio")

    @property
    def headers(self) -> dict:
        return {
            "apikey": self.api_key,
            "Content-Type": "application/json",
        }

    async def _fazer_request(
        self, method: str, url: str, payload: dict = None, timeout: float = 30.0
    ) -> dict:
        """
        Faz request HTTP com retry/backoff + circuit breaker.

        Sprint 18.1 - B2: Retry antes de contar falha no circuit.
        Fluxo: Request → Retry (se transitório) → Circuit Breaker
        """

        async def _request_com_retry():
            last_error = None
            last_status_code = None

            for attempt in range(RETRY_CONFIG["max_attempts"]):
                try:
                    async with httpx.AsyncClient() as client:
                        if method == "POST":
                            response = await client.post(
                                url, json=payload, headers=self.headers, timeout=timeout
                            )
                        else:
                            response = await client.get(url, headers=self.headers, timeout=timeout)
                        response.raise_for_status()
                        return response.json()

                except httpx.HTTPStatusError as e:
                    last_error = e
                    last_status_code = e.response.status_code

                    # Não retryable: propaga imediatamente
                    if last_status_code in RETRY_CONFIG["non_retryable_status_codes"]:
                        logger.warning(
                            f"Erro não-retryable {last_status_code} em {url}",
                            extra={"status_code": last_status_code, "attempt": attempt + 1},
                        )
                        raise

                    # Retryable: espera e tenta de novo
                    if last_status_code in RETRY_CONFIG["retryable_status_codes"]:
                        if attempt < RETRY_CONFIG["max_attempts"] - 1:
                            delay = self._calcular_delay_retry(attempt)
                            logger.warning(
                                f"Retry {attempt + 1}/{RETRY_CONFIG['max_attempts']} "
                                f"após {last_status_code}, aguardando {delay:.2f}s",
                                extra={
                                    "status_code": last_status_code,
                                    "attempt": attempt + 1,
                                    "delay": delay,
                                },
                            )
                            await asyncio.sleep(delay)
                            continue

                    # Status code não mapeado: propaga
                    raise

                except (httpx.TimeoutException, httpx.NetworkError) as e:
                    last_error = e

                    # Erros de rede/timeout são retryable
                    if attempt < RETRY_CONFIG["max_attempts"] - 1:
                        delay = self._calcular_delay_retry(attempt)
                        error_type = type(e).__name__
                        logger.warning(
                            f"Retry {attempt + 1}/{RETRY_CONFIG['max_attempts']} "
                            f"após {error_type}, aguardando {delay:.2f}s",
                            extra={
                                "error_type": error_type,
                                "attempt": attempt + 1,
                                "delay": delay,
                            },
                        )
                        await asyncio.sleep(delay)
                        continue

                    # Última tentativa falhou
                    raise

            # Não deveria chegar aqui, mas por segurança
            if last_error:
                raise last_error
            raise RuntimeError("Retry loop exauriu sem resultado")

        return await circuit_evolution.executar(_request_com_retry)

    def _calcular_delay_retry(self, attempt: int) -> float:
        """
        Calcula delay com exponential backoff + jitter.

        Args:
            attempt: Número da tentativa (0-indexed)

        Returns:
            Delay em segundos
        """
        base_delay = RETRY_CONFIG["base_delays"][min(attempt, len(RETRY_CONFIG["base_delays"]) - 1)]
        jitter = base_delay * RETRY_CONFIG["jitter_factor"] * (2 * random.random() - 1)
        return max(0.1, base_delay + jitter)

    async def enviar_mensagem(
        self, telefone: str, texto: str, verificar_rate_limit: bool = True
    ) -> dict:
        """
        Envia mensagem de texto para um numero.

        Args:
            telefone: Numero no formato 5511999999999
            texto: Texto da mensagem
            verificar_rate_limit: Se True, verifica rate limiting antes de enviar

        Returns:
            Resposta da API

        Raises:
            RateLimitError: Se rate limit foi atingido
            CircuitOpenError: Se circuit breaker está aberto
        """
        # Verificar rate limiting (apenas para mensagens proativas)
        if verificar_rate_limit:
            ok, motivo = await pode_enviar(telefone)
            if not ok:
                logger.warning(f"Rate limit para {telefone[:8]}...: {motivo}")
                raise RateLimitError(motivo)

        url = f"{self.base_url}/message/sendText/{self.instance}"
        payload = {
            "number": telefone,
            "text": texto,
        }

        result = await self._fazer_request("POST", url, payload, timeout=30.0)
        logger.info(f"Mensagem enviada para {telefone[:8]}...")

        # Registrar envio no rate limiter
        await registrar_envio(telefone)

        return result

    async def enviar_presenca(
        self,
        telefone: str,
        presenca: Literal["available", "composing", "recording", "paused"],
        delay: int = 3000,
    ) -> dict:
        """
        Envia status de presenca (online, digitando, etc).

        Args:
            telefone: Numero do destinatario
            presenca: Tipo de presenca
            delay: Tempo em ms para manter a presenca
        """
        url = f"{self.base_url}/chat/sendPresence/{self.instance}"
        payload = {
            "number": telefone,
            "presence": presenca,
            "delay": delay,
        }

        return await self._fazer_request("POST", url, payload, timeout=10.0)

    async def marcar_como_lida(self, telefone: str, message_id: str, from_me: bool = False) -> dict:
        """Marca mensagem como lida."""
        url = f"{self.base_url}/chat/markMessageAsRead/{self.instance}"
        payload = {
            "readMessages": [
                {
                    "remoteJid": telefone if "@" in telefone else f"{telefone}@s.whatsapp.net",
                    "fromMe": from_me,
                    "id": message_id,
                }
            ]
        }

        return await self._fazer_request("POST", url, payload, timeout=10.0)

    async def verificar_conexao(self) -> dict:
        """Verifica status da conexao WhatsApp."""
        url = f"{self.base_url}/instance/connectionState/{self.instance}"
        return await self._fazer_request("GET", url, timeout=10.0)

    async def buscar_contatos(self, push_name: str = None) -> list:
        """
        Busca contatos na Evolution API.

        Args:
            push_name: Filtrar por nome do contato (opcional)

        Returns:
            Lista de contatos
        """
        url = f"{self.base_url}/chat/findContacts/{self.instance}"
        payload = {}
        if push_name:
            payload["where"] = {"pushName": push_name}

        try:
            result = await self._fazer_request("POST", url, payload, timeout=10.0)
            return result if isinstance(result, list) else []
        except Exception as e:
            logger.warning(f"Erro ao buscar contatos: {e}")
            return []

    async def resolver_lid_para_telefone(self, push_name: str) -> str:
        """
        Resolve LID para número de telefone real.

        Busca contatos pelo pushName e retorna o que tem formato
        @s.whatsapp.net (número real) em vez de @lid.

        Args:
            push_name: Nome do contato no WhatsApp

        Returns:
            Número de telefone ou string vazia se não encontrado
        """
        if not push_name:
            return ""

        contatos = await self.buscar_contatos(push_name)

        for contato in contatos:
            remote_jid = contato.get("remoteJid", "")
            # Pegar apenas contatos com número real (não LID)
            if "@s.whatsapp.net" in remote_jid:
                telefone = remote_jid.split("@")[0]
                logger.info(f"LID resolvido para {telefone} via pushName '{push_name}'")
                return telefone

        logger.warning(f"Nao foi possivel resolver LID para pushName '{push_name}'")
        return ""

    async def buscar_info_grupo(self, grupo_jid: str) -> dict:
        """
        Busca informações de um grupo pelo JID.

        Args:
            grupo_jid: JID do grupo (ex: "123456789@g.us")

        Returns:
            Dict com informações do grupo (subject, size, participants, etc)
        """
        # Buscar na lista de grupos (Evolution API v2)
        grupos = await self.listar_grupos()
        for grupo in grupos:
            if grupo.get("id") == grupo_jid:
                return grupo
        return {}

    async def buscar_participantes_grupo(self, grupo_jid: str) -> list:
        """
        Busca participantes de um grupo específico.

        Args:
            grupo_jid: JID do grupo

        Returns:
            Lista de participantes com id (LID) e phoneNumber
        """
        # Usar endpoint específico para participantes (mais eficiente que fetchAllGroups)
        url = f"{self.base_url}/group/participants/{self.instance}"

        async def _request():
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url, params={"groupJid": grupo_jid}, headers=self.headers, timeout=15.0
                )
                response.raise_for_status()
                return response.json()

        try:
            result = await circuit_evolution.executar(_request)
            # Retorna lista de participantes diretamente
            return (
                result.get("participants", [])
                if isinstance(result, dict)
                else result
                if isinstance(result, list)
                else []
            )
        except Exception as e:
            logger.warning(f"Erro ao buscar participantes do grupo {grupo_jid}: {e}")
            return []

    async def resolver_lid_para_telefone_via_grupo(self, lid: str, grupo_jid: str) -> str:
        """
        Resolve LID para telefone real usando participantes do grupo.

        Args:
            lid: LID do contato (ex: "123456@lid")
            grupo_jid: JID do grupo onde o contato está

        Returns:
            Telefone no formato 5511999999999 ou string vazia
        """
        if not lid or not grupo_jid:
            return ""

        # Normalizar LID (remover @lid se presente)
        lid_normalizado = lid.split("@")[0] + "@lid"

        participantes = await self.buscar_participantes_grupo(grupo_jid)

        for p in participantes:
            if p.get("id") == lid_normalizado:
                phone = p.get("phoneNumber", "")
                if phone and "@s.whatsapp.net" in phone:
                    telefone = phone.split("@")[0]
                    logger.debug(f"LID {lid} resolvido para {telefone}")
                    return telefone

        logger.debug(f"LID {lid} não encontrado no grupo {grupo_jid}")
        return ""

    async def listar_grupos(self) -> list:
        """
        Lista todos os grupos que a instância participa.

        Returns:
            Lista de grupos com id, subject, size, etc
        """
        url = f"{self.base_url}/group/fetchAllGroups/{self.instance}"

        async def _request():
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url, params={"getParticipants": "false"}, headers=self.headers, timeout=15.0
                )
                response.raise_for_status()
                return response.json()

        try:
            result = await circuit_evolution.executar(_request)
            return result if isinstance(result, list) else []
        except Exception as e:
            logger.warning(f"Erro ao listar grupos: {e}")
            return []

    async def buscar_info_grupo_por_invite(self, invite_code: str) -> dict:
        """
        Busca informações de um grupo pelo código de convite.

        Args:
            invite_code: Código de convite (ex: "ABC123xyz...")

        Returns:
            Dict com informações do grupo ou None se inválido
        """
        url = f"{self.base_url}/group/inviteInfo/{self.instance}"

        async def _request():
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url, params={"inviteCode": invite_code}, headers=self.headers, timeout=15.0
                )
                response.raise_for_status()
                return response.json()

        try:
            result = await circuit_evolution.executar(_request)
            return result if isinstance(result, dict) else None
        except Exception as e:
            logger.warning(f"Erro ao buscar info do grupo por invite {invite_code}: {e}")
            return None

    async def entrar_grupo_por_invite(self, invite_code: str) -> dict:
        """
        Entra em um grupo usando código de convite.

        Args:
            invite_code: Código de convite (ex: "ABC123xyz...")

        Returns:
            {
                "sucesso": bool,
                "jid": str (se sucesso),
                "aguardando_aprovacao": bool,
                "erro": str (se falha)
            }
        """
        url = f"{self.base_url}/group/acceptInviteCode/{self.instance}"

        async def _request():
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url, json={"inviteCode": invite_code}, headers=self.headers, timeout=30.0
                )
                response.raise_for_status()
                return response.json()

        try:
            result = await circuit_evolution.executar(_request)

            # Processar resposta da Evolution API
            if isinstance(result, dict):
                # Sucesso direto
                if result.get("id") or result.get("groupJid"):
                    return {
                        "sucesso": True,
                        "jid": result.get("id") or result.get("groupJid"),
                        "aguardando_aprovacao": False,
                    }

                # Aguardando aprovação do admin
                if result.get("status") == "pending" or "pending" in str(result).lower():
                    return {
                        "sucesso": False,
                        "aguardando_aprovacao": True,
                        "jid": None,
                    }

                # Erro específico
                if result.get("error") or result.get("message"):
                    return {
                        "sucesso": False,
                        "aguardando_aprovacao": False,
                        "erro": result.get("error") or result.get("message"),
                    }

            # Resposta inesperada
            logger.warning(f"Resposta inesperada ao entrar no grupo: {result}")
            return {
                "sucesso": False,
                "aguardando_aprovacao": False,
                "erro": f"Resposta inesperada: {result}",
            }

        except Exception as e:
            erro = str(e)
            logger.warning(f"Erro ao entrar no grupo {invite_code}: {erro}")

            # Detectar se é aguardando aprovação pelo erro
            if "pending" in erro.lower() or "approval" in erro.lower():
                return {
                    "sucesso": False,
                    "aguardando_aprovacao": True,
                    "erro": erro,
                }

            return {
                "sucesso": False,
                "aguardando_aprovacao": False,
                "erro": erro,
            }

    async def check_number_status(self, phone: str) -> dict:
        """
        Verifica se número tem WhatsApp via Evolution API.

        Sprint 32 E04 - Validação prévia evita desperdício de mensagens.

        Args:
            phone: Número no formato 5511999999999 (sem +)

        Returns:
            {
                "exists": True/False,
                "jid": "5511999999999@s.whatsapp.net" (se existe),
                "number": "5511999999999",
                "error": "mensagem" (se erro)
            }

        Docs Evolution API:
            POST /chat/whatsappNumbers/{instance}
            Body: {"numbers": ["5511999999999"]}
        """
        try:
            # Normalizar número (remover +, espaços, etc.)
            numero_limpo = "".join(filter(str.isdigit, phone))

            # Garantir que tem código do país
            if not numero_limpo.startswith("55"):
                numero_limpo = f"55{numero_limpo}"

            url = f"{self.base_url}/chat/whatsappNumbers/{self.instance}"

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    url, headers=self.headers, json={"numbers": [numero_limpo]}
                )

                if response.status_code != 200:
                    logger.warning(f"checkNumberStatus erro HTTP: {response.status_code}")
                    return {"exists": False, "error": f"HTTP {response.status_code}"}

                data = response.json()

                # Resposta da Evolution API:
                # [{"exists": true, "jid": "5511999999999@s.whatsapp.net", "number": "5511999999999"}]
                if data and len(data) > 0:
                    resultado = data[0]
                    return {
                        "exists": resultado.get("exists", False),
                        "jid": resultado.get("jid"),
                        "number": resultado.get("number"),
                    }

                return {"exists": False, "error": "Resposta vazia"}

        except httpx.TimeoutException:
            logger.warning(f"checkNumberStatus timeout para {phone}")
            return {"exists": False, "error": "timeout"}

        except Exception as e:
            logger.error(f"checkNumberStatus erro: {e}")
            return {"exists": False, "error": str(e)}

    async def set_webhook(self, url: str, events: list = None) -> dict:
        """Configura webhook da instancia."""
        if events is None:
            events = ["MESSAGES_UPSERT", "CONNECTION_UPDATE"]

        webhook_url = f"{self.base_url}/webhook/set/{self.instance}"
        payload = {
            "webhook": {"enabled": True, "url": url, "webhookByEvents": False, "events": events}
        }

        result = await self._fazer_request("POST", webhook_url, payload, timeout=10.0)
        logger.info(f"Webhook configurado: {url}")
        return result


# Instancia global
evolution = EvolutionClient()


# Funcoes de conveniencia
async def enviar_whatsapp(telefone: str, texto: str, verificar_rate_limit: bool = True) -> dict:
    """
    Funcao de conveniencia para enviar mensagem.

    Args:
        telefone: Número do destinatário
        texto: Texto da mensagem
        verificar_rate_limit: Se True, verifica rate limit antes de enviar

    Raises:
        RateLimitError: Se rate limit foi atingido
        CircuitOpenError: Se Evolution API está indisponível
    """
    return await evolution.enviar_mensagem(telefone, texto, verificar_rate_limit)


async def mostrar_digitando(telefone: str) -> dict:
    """Mostra 'digitando...' para o contato."""
    return await evolution.enviar_presenca(telefone, "composing")


async def mostrar_online(telefone: str) -> dict:
    """Mostra status online para o contato."""
    return await evolution.enviar_presenca(telefone, "available")


async def manter_digitando(telefone: str, duracao_max: int = 30):
    """
    Mantém status 'digitando' por até X segundos.
    Útil enquanto aguarda resposta do LLM.
    """
    import asyncio

    inicio = asyncio.get_event_loop().time()
    while asyncio.get_event_loop().time() - inicio < duracao_max:
        await mostrar_digitando(telefone)
        await asyncio.sleep(5)  # Reenviar a cada 5s


async def enviar_com_digitacao(telefone: str, texto: str, tempo_digitacao: float = None) -> dict:
    """
    Envia mensagem com simulação de digitação.

    1. Mostra "composing" (digitando)
    2. Aguarda tempo proporcional
    3. Envia mensagem

    Args:
        telefone: Número do destinatário
        texto: Texto da mensagem
        tempo_digitacao: Tempo de digitação em segundos (opcional, calcula automaticamente)

    Returns:
        Resultado do envio
    """
    import asyncio
    from app.services.timing import calcular_tempo_digitacao

    tempo = tempo_digitacao or calcular_tempo_digitacao(texto)

    # Iniciar "digitando"
    await mostrar_digitando(telefone)

    # Aguardar tempo de digitação
    await asyncio.sleep(tempo)

    # Enviar mensagem
    return await evolution.enviar_mensagem(
        telefone=telefone,
        texto=texto,
        verificar_rate_limit=False,  # Respostas não contam no rate limit
    )
