"""
Executor de campanhas.

Responsavel por:
- Buscar destinatarios elegiveis
- Gerar mensagens apropriadas por tipo
- Enfileirar envios em fila_mensagens
- Atualizar contadores

Sprint 35 - Epic 04
Sprint 57 - Anti-spam: cooldown, limite sem resposta, conclusao automatica
"""

import logging
from typing import List, Optional

from app.services.abertura import obter_abertura_texto
from app.services.campaign_cooldown import check_campaign_cooldown
from app.services.campanhas.repository import campanha_repository
from app.services.campanhas.types import (
    CampanhaData,
    StatusCampanha,
    TipoCampanha,
)
from app.services.fila import fila_service
from app.services.segmentacao import segmentacao_service
from app.services.supabase import supabase

logger = logging.getLogger(__name__)

# Anti-spam: maximo de outbound sem resposta antes de parar de contactar
MAX_UNANSWERED_OUTBOUND = 2


class CampanhaExecutor:
    """Executor de campanhas."""

    async def executar(self, campanha_id: int) -> bool:
        """
        Executa uma campanha.

        Args:
            campanha_id: ID da campanha a executar

        Returns:
            True se executada com sucesso
        """
        logger.info(f"Iniciando execucao da campanha {campanha_id}")

        # 1. Buscar campanha
        campanha = await campanha_repository.buscar_por_id(campanha_id)
        if not campanha:
            logger.error(f"Campanha {campanha_id} nao encontrada")
            return False

        # 2. Validar status - AGENDADA ou ATIVA podem ser executadas
        # Dashboard define status='ativa' antes de chamar o executor,
        # por isso precisamos aceitar ambos os status aqui.
        status_permitidos = (StatusCampanha.AGENDADA, StatusCampanha.ATIVA)
        if campanha.status not in status_permitidos:
            logger.warning(
                f"Campanha {campanha_id} tem status {campanha.status.value}, "
                f"apenas 'agendada' ou 'ativa' pode ser executada"
            )
            return False

        # 3. Atualizar status para ativa
        await campanha_repository.atualizar_status(campanha_id, StatusCampanha.ATIVA)

        # 4. Buscar destinatarios
        destinatarios = await self._buscar_destinatarios(campanha)
        if not destinatarios:
            logger.warning(f"Campanha {campanha_id} nao tem destinatarios elegiveis")
            await campanha_repository.atualizar_status(campanha_id, StatusCampanha.CONCLUIDA)
            return True

        # 5. Sprint 44: Filtrar clientes que já receberam esta campanha (deduplicação)
        clientes_ja_receberam = await self._buscar_clientes_ja_enviados(campanha_id)
        if clientes_ja_receberam:
            destinatarios_antes = len(destinatarios)
            destinatarios = [d for d in destinatarios if d.get("id") not in clientes_ja_receberam]
            duplicados = destinatarios_antes - len(destinatarios)
            if duplicados > 0:
                logger.info(
                    f"Campanha {campanha_id}: {duplicados} destinatarios ignorados "
                    f"(ja receberam esta campanha)"
                )

        if not destinatarios:
            logger.info(f"Campanha {campanha_id}: todos destinatarios ja receberam")
            await campanha_repository.atualizar_status(campanha_id, StatusCampanha.CONCLUIDA)
            return True

        # 6. Atualizar total de destinatarios
        await campanha_repository.atualizar_total_destinatarios(campanha_id, len(destinatarios))

        # 7. Criar envios com verificacoes anti-spam (#109, #110)
        enviados = 0
        skipped_cooldown = 0
        skipped_unanswered = 0
        for dest in destinatarios:
            cliente_id = dest.get("id")
            try:
                # Anti-spam #109: verificar cooldown entre campanhas
                cooldown = await check_campaign_cooldown(cliente_id, campanha_id)
                if cooldown.is_blocked:
                    skipped_cooldown += 1
                    logger.debug(
                        f"Campanha {campanha_id}: {cliente_id[:8]} em cooldown ({cooldown.reason})"
                    )
                    continue

                # Anti-spam #110: verificar limite de outbound sem resposta
                if await self._excedeu_limite_sem_resposta(cliente_id):
                    skipped_unanswered += 1
                    logger.debug(
                        f"Campanha {campanha_id}: {cliente_id[:8]} excedeu limite "
                        f"de {MAX_UNANSWERED_OUTBOUND} outbound sem resposta"
                    )
                    continue

                sucesso = await self._criar_envio(campanha, dest)
                if sucesso:
                    enviados += 1
            except Exception as e:
                logger.error(f"Erro ao criar envio para {cliente_id}: {e}")

        # 8. Atualizar contador de enviados
        await campanha_repository.incrementar_enviados(campanha_id, enviados)

        # 9. Anti-spam #111: concluir campanha apos execucao
        await campanha_repository.atualizar_status(campanha_id, StatusCampanha.CONCLUIDA)

        logger.info(
            f"Campanha {campanha_id}: {enviados}/{len(destinatarios)} envios criados "
            f"(cooldown={skipped_cooldown}, sem_resposta={skipped_unanswered})"
        )
        return True

    async def _excedeu_limite_sem_resposta(self, cliente_id: str) -> bool:
        """
        Verifica se medico excedeu limite de outbound sem resposta (#110).

        Conta campanhas enviadas sem nenhuma resposta inbound do medico.
        Se >= MAX_UNANSWERED_OUTBOUND, retorna True.

        Args:
            cliente_id: ID do cliente

        Returns:
            True se excedeu limite
        """
        try:
            # Contar campanhas enviadas para este medico
            enviadas = (
                supabase.table("campaign_contact_history")
                .select("id", count="exact")
                .eq("cliente_id", cliente_id)
                .execute()
            )
            total_campanhas = enviadas.count or 0

            if total_campanhas < MAX_UNANSWERED_OUTBOUND:
                return False

            # Verificar se tem alguma resposta inbound
            respostas = (
                supabase.table("interacoes")
                .select("id", count="exact")
                .eq("cliente_id", cliente_id)
                .eq("tipo", "entrada")
                .limit(1)
                .execute()
            )

            tem_resposta = (respostas.count or 0) > 0
            return not tem_resposta

        except Exception as e:
            logger.warning(f"Erro ao verificar limite sem resposta: {e}")
            return False  # Na duvida, permite envio

    async def _buscar_clientes_ja_enviados(self, campanha_id: int) -> set:
        """
        Busca IDs de clientes que já receberam esta campanha.

        Args:
            campanha_id: ID da campanha

        Returns:
            Set com IDs dos clientes que já receberam
        """
        try:
            response = (
                supabase.table("fila_mensagens")
                .select("cliente_id")
                .contains("metadata", {"campanha_id": str(campanha_id)})
                .execute()
            )

            if response.data:
                return {row["cliente_id"] for row in response.data}
            return set()

        except Exception as e:
            logger.warning(f"Erro ao buscar clientes ja enviados: {e}")
            return set()

    async def _buscar_destinatarios(self, campanha: CampanhaData) -> List[dict]:
        """
        Busca destinatarios elegiveis para a campanha.

        Args:
            campanha: Dados da campanha

        Returns:
            Lista de destinatarios
        """
        af = campanha.audience_filters
        filtros = {}

        # Se tem clientes especificos, ignora filtros demograficos
        clientes_especificos = None
        if af and af.clientes_especificos:
            clientes_especificos = af.clientes_especificos
        else:
            # Mapear filtros demograficos
            if af:
                if af.especialidades:
                    filtros["especialidade"] = af.especialidades[0]
                if af.regioes:
                    filtros["regiao"] = af.regioes[0]

        # Parametros de controle
        limite = af.quantidade_alvo if af else 50
        pressure_score_max = af.pressure_score_max if af else 50
        modo_selecao = af.modo_selecao if af else "deterministico"

        try:
            # Sprint 44: Usar buscar_alvos_campanha que filtra por elegibilidade
            # (conversas ativas, cooling_off, contact_cap, pressure_score, etc)
            return await segmentacao_service.buscar_alvos_campanha(
                filtros=filtros,
                dias_sem_contato=7,  # Não recontatar em 7 dias
                limite=limite,
                pressure_score_max=pressure_score_max,
                modo_selecao=modo_selecao,
                clientes_especificos=clientes_especificos,
            )
        except Exception as e:
            logger.error(f"Erro ao buscar destinatarios: {e}")
            return []

    async def _criar_envio(self, campanha: CampanhaData, destinatario: dict) -> bool:
        """
        Cria envio para um destinatario.

        Args:
            campanha: Dados da campanha
            destinatario: Dados do destinatario

        Returns:
            True se criado com sucesso
        """
        cliente_id = destinatario.get("id")

        # Gerar mensagem baseada no tipo
        mensagem = await self._gerar_mensagem(campanha, destinatario)

        if not mensagem:
            logger.warning(f"Nao foi possivel gerar mensagem para {cliente_id}")
            return False

        # Preparar metadata
        metadata = {
            "campanha_id": str(campanha.id),
            "tipo_campanha": campanha.tipo_campanha.value,
        }

        # Adicionar objetivo e pode_ofertar para contexto no pipeline inbound
        if campanha.objetivo:
            metadata["objetivo"] = campanha.objetivo
        metadata["pode_ofertar"] = campanha.pode_ofertar

        # Adicionar chips excluídos se configurado
        if campanha.audience_filters and campanha.audience_filters.chips_excluidos:
            metadata["chips_excluidos"] = campanha.audience_filters.chips_excluidos

        # Sprint 66: Meta template info para envio via template
        if campanha.meta_template_name:
            await self._adicionar_meta_template_info(
                metadata, campanha, destinatario
            )

        # Enfileirar
        await fila_service.enfileirar(
            cliente_id=cliente_id,
            conteudo=mensagem,
            tipo="campanha",
            prioridade=3,  # Prioridade baixa para campanhas
            metadata=metadata,
        )

        return True

    async def _gerar_abertura_contextualizada(
        self,
        nome: str,
        objetivo: str,
    ) -> Optional[str]:
        """
        Gera abertura contextualizada via LLM (Haiku) baseada no objetivo.

        Args:
            nome: Nome do médico
            objetivo: Objetivo da campanha em linguagem natural

        Returns:
            Mensagem de abertura ou None se LLM falhar
        """
        try:
            from app.services.llm import gerar_resposta

            prompt = (
                "Você é Julia Mendes, 27 anos, escalista da Revoluna.\n"
                "Gere UMA mensagem de abertura para WhatsApp para este médico.\n\n"
                "REGRAS:\n"
                "- Máximo 3 linhas curtas\n"
                "- Tom informal mas profissional (vc, pra, tá)\n"
                "- NÃO use bullet points\n"
                "- NÃO mencione plantão ou vagas a menos que o objetivo peça\n"
                "- Se apresente brevemente como Julia da Revoluna\n"
                "- Conecte naturalmente com o objetivo\n\n"
                f"Nome do médico: Dr {nome}\n"
                f"Objetivo da conversa: {objetivo}\n\n"
                "Responda APENAS com a mensagem, sem explicações."
            )

            resposta = await gerar_resposta(
                mensagem=prompt,
                max_tokens=150,
            )

            if resposta and len(resposta.strip()) > 10:
                return resposta.strip()
            return None

        except Exception as e:
            logger.warning(f"Erro ao gerar abertura contextualizada: {e}")
            return None

    async def _gerar_mensagem(
        self,
        campanha: CampanhaData,
        destinatario: dict,
    ) -> Optional[str]:
        """
        Gera mensagem para o destinatario baseada no tipo de campanha.

        Args:
            campanha: Dados da campanha
            destinatario: Dados do destinatario

        Returns:
            Mensagem gerada ou None
        """
        cliente_id = destinatario.get("id")
        # RPC retorna "nome" (alias de primeiro_nome), mas outras fontes podem usar "primeiro_nome"
        nome = destinatario.get("nome") or destinatario.get("primeiro_nome", "")
        especialidade = destinatario.get("especialidade_nome", "medico")

        if campanha.tipo_campanha == TipoCampanha.DISCOVERY:
            # Discovery com objetivo: gerar abertura contextualizada via LLM
            if campanha.objetivo:
                abertura = await self._gerar_abertura_contextualizada(nome, campanha.objetivo)
                if abertura:
                    return abertura
            # Fallback: usar aberturas soft (sem mencionar plantao)
            return await obter_abertura_texto(cliente_id, nome, soft=True)

        elif campanha.tipo_campanha in (TipoCampanha.OFERTA, TipoCampanha.OFERTA_PLANTAO):
            # Oferta: usar corpo como template
            if campanha.corpo:
                return self._formatar_template(campanha.corpo, nome, especialidade)
            return None

        elif campanha.tipo_campanha == TipoCampanha.REATIVACAO:
            # Reativacao: usar corpo ou template padrao
            if campanha.corpo:
                return self._formatar_template(campanha.corpo, nome, especialidade)
            return f"Oi Dr {nome}! Tudo bem? Faz tempo que a gente nao se fala..."

        elif campanha.tipo_campanha == TipoCampanha.FOLLOWUP:
            # Followup: usar corpo ou template padrao
            if campanha.corpo:
                return self._formatar_template(campanha.corpo, nome, especialidade)
            return f"Oi Dr {nome}! Lembrei de vc..."

        # Fallback
        if campanha.corpo:
            return self._formatar_template(campanha.corpo, nome, especialidade)

        return None

    async def _adicionar_meta_template_info(
        self,
        metadata: dict,
        campanha: "CampanhaData",
        destinatario: dict,
    ) -> None:
        """
        Sprint 66: Adiciona meta_template info à metadata do envio.

        Busca template aprovado e mapeia variáveis do destinatário.

        Args:
            metadata: Dict de metadata do envio (modificado in-place)
            campanha: Dados da campanha
            destinatario: Dados do destinatário
        """
        try:
            from app.services.meta.template_service import template_service
            from app.services.meta.template_mapper import template_mapper

            template = await template_service.buscar_template_por_nome(
                campanha.meta_template_name
            )
            if not template:
                logger.warning(
                    f"Template Meta '{campanha.meta_template_name}' não encontrado "
                    f"ou não aprovado, campanha {campanha.id} usará texto"
                )
                return

            if template.get("status") != "APPROVED":
                logger.warning(
                    f"Template '{campanha.meta_template_name}' status "
                    f"'{template.get('status')}', ignorando"
                )
                return

            # Mapear variáveis
            components = template_mapper.mapear_variaveis(
                template, destinatario, campanha.escopo_vagas or {}
            )

            metadata["meta_template"] = {
                "name": campanha.meta_template_name,
                "language": campanha.meta_template_language,
                "components": components,
            }

        except Exception as e:
            logger.warning(
                f"Erro ao preparar template Meta para campanha {campanha.id}: {e}"
            )

    def _formatar_template(
        self,
        template: str,
        nome: str,
        especialidade: str,
    ) -> str:
        """
        Formata template com variaveis.

        Args:
            template: Template com placeholders
            nome: Nome do destinatario
            especialidade: Especialidade

        Returns:
            Template formatado
        """
        try:
            # Suportar diferentes formatos de placeholder
            # Importante: substituir chaves duplas ANTES das simples
            resultado = template
            resultado = resultado.replace("{{nome}}", nome)
            resultado = resultado.replace("{{especialidade}}", especialidade)
            resultado = resultado.replace("{nome}", nome)
            resultado = resultado.replace("{especialidade}", especialidade)
            return resultado
        except Exception as e:
            logger.warning(f"Erro ao formatar template: {e}")
            return template


# Instancia singleton
campanha_executor = CampanhaExecutor()
