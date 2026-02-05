"""
Executor de campanhas.

Responsavel por:
- Buscar destinatarios elegiveis
- Gerar mensagens apropriadas por tipo
- Enfileirar envios em fila_mensagens
- Atualizar contadores

Sprint 35 - Epic 04
"""
import logging
from typing import List, Optional

from app.services.abertura import obter_abertura_texto
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

        # 2. Validar status
        if campanha.status not in (StatusCampanha.AGENDADA, StatusCampanha.ATIVA):
            logger.warning(
                f"Campanha {campanha_id} tem status {campanha.status.value}, "
                "nao pode ser executada"
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
            destinatarios = [
                d for d in destinatarios
                if d.get("id") not in clientes_ja_receberam
            ]
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

        # 7. Criar envios
        enviados = 0
        for dest in destinatarios:
            try:
                sucesso = await self._criar_envio(campanha, dest)
                if sucesso:
                    enviados += 1
            except Exception as e:
                logger.error(f"Erro ao criar envio para {dest.get('id')}: {e}")

        # 8. Atualizar contador de enviados
        await campanha_repository.incrementar_enviados(campanha_id, enviados)

        logger.info(f"Campanha {campanha_id}: {enviados}/{len(destinatarios)} envios criados")
        return True

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

        # Adicionar chips excluídos se configurado
        if campanha.audience_filters and campanha.audience_filters.chips_excluidos:
            metadata["chips_excluidos"] = campanha.audience_filters.chips_excluidos

        # Enfileirar
        await fila_service.enfileirar(
            cliente_id=cliente_id,
            conteudo=mensagem,
            tipo="campanha",
            prioridade=3,  # Prioridade baixa para campanhas
            metadata=metadata,
        )

        return True

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
            # Discovery: usar aberturas dinamicas
            return await obter_abertura_texto(cliente_id, nome)

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
