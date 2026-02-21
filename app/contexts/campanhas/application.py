"""
Application Service do Bounded Context: Campanhas Outbound

Este módulo é o ponto de entrada para todos os casos de uso do contexto
de Campanhas. Ele orquestra a interação entre os repositórios, os
serviços de domínio e a infraestrutura (fila, segmentação), mas NÃO
contém regras de negócio — essas pertencem ao domínio.

Princípio: ADR-007 — As rotas da API chamam apenas este módulo.
A rota não sabe nada sobre Supabase, repositórios ou regras de negócio.

Padrão: API Route -> Application Service -> Repository/Domain Service

IMPORTANTE: Este módulo lança exceções de domínio (app.core.exceptions),
NUNCA exceções HTTP. A conversão para HTTP é responsabilidade da rota.
"""

import logging
from typing import Any, Dict, List, Optional

from app.core.exceptions import DatabaseError, NotFoundError, ValidationError
from app.services.campanhas.executor import campanha_executor
from app.services.campanhas.repository import campanha_repository
from app.services.campanhas.types import (
    AudienceFilters,
    CampanhaData,
    StatusCampanha,
    TipoCampanha,
)
from app.services.segmentacao import segmentacao_service

logger = logging.getLogger(__name__)


class CampanhasApplicationService:
    """
    Application Service para o contexto de Campanhas Outbound.

    Cada método público representa um caso de uso (use case) do sistema.
    A rota da API deve chamar apenas estes métodos, sem acessar diretamente
    repositórios, serviços de domínio ou o banco de dados.

    Exceções lançadas:
        - NotFoundError: recurso não encontrado
        - ValidationError: dados de entrada inválidos
        - DatabaseError: falha na persistência
    """

    def __init__(self, repository=None, executor=None, segmentacao=None):
        """
        Permite injeção de dependências para testes.

        Args:
            repository: Repositório de campanhas (default: singleton existente)
            executor: Executor de campanhas (default: singleton existente)
            segmentacao: Serviço de segmentação (default: singleton existente)
        """
        self._repository = repository or campanha_repository
        self._executor = executor or campanha_executor
        self._segmentacao = segmentacao or segmentacao_service

    async def criar_campanha(
        self,
        nome_template: str,
        tipo_campanha: str,
        corpo: Optional[str] = None,
        tom: Optional[str] = "amigavel",
        objetivo: Optional[str] = None,
        especialidades: Optional[List[str]] = None,
        regioes: Optional[List[str]] = None,
        quantidade_alvo: int = 50,
        modo_selecao: str = "deterministico",
        agendar_para=None,
        pode_ofertar: bool = True,
        chips_excluidos: Optional[List[str]] = None,
    ) -> CampanhaData:
        """
        Caso de Uso: Criar uma nova campanha.

        Valida os dados de entrada, conta a audiência e persiste a campanha.
        Usa o repositório existente (services/campanhas/repository.py) que
        inclui invalidação de cache Redis.

        Returns:
            O objeto CampanhaData da campanha criada.

        Raises:
            ValidationError: Se o tipo de campanha for inválido.
            DatabaseError: Se a persistência falhar.
        """
        # 1. Validar tipo de campanha
        try:
            tipo = TipoCampanha(tipo_campanha)
        except ValueError:
            raise ValidationError(
                f"Tipo de campanha inválido: '{tipo_campanha}'. "
                f"Valores aceitos: {[t.value for t in TipoCampanha]}",
            )

        # 2. Montar filtros para contagem de audiência
        filtros = {}
        if especialidades:
            filtros["especialidade"] = especialidades[0]
        if regioes:
            filtros["regiao"] = regioes[0]

        total_destinatarios = await self._segmentacao.contar_segmento(filtros)

        # 3. Montar o objeto de filtros de audiência
        audience_filters = AudienceFilters(
            regioes=regioes or [],
            especialidades=especialidades or [],
            quantidade_alvo=quantidade_alvo,
            modo_selecao=modo_selecao,
            chips_excluidos=chips_excluidos or [],
        )

        # 4. Persistir via repositório existente (com cache Redis)
        campanha = await self._repository.criar(
            nome_template=nome_template,
            tipo_campanha=tipo,
            corpo=corpo,
            tom=tom,
            objetivo=objetivo,
            audience_filters=audience_filters,
            agendar_para=agendar_para,
            pode_ofertar=pode_ofertar,
        )

        if not campanha:
            raise DatabaseError("Erro ao criar campanha no banco de dados.")

        # Atualizar total de destinatários após a criação
        if total_destinatarios > 0:
            await self._repository.atualizar_total_destinatarios(
                campanha.id, total_destinatarios
            )

        logger.info(
            f"[CampanhasApplicationService] Campanha criada: id={campanha.id}, tipo={tipo.value}"
        )
        return campanha

    async def executar_campanha(self, campanha_id: int) -> Dict[str, Any]:
        """
        Caso de Uso: Executar (iniciar o envio de) uma campanha.

        Valida se a campanha existe e se está em um estado que permite
        execução, antes de delegar ao executor de domínio.

        Raises:
            NotFoundError: Se a campanha não for encontrada.
            ValidationError: Se a campanha não puder ser iniciada no estado atual.
            DatabaseError: Se ocorrer um erro durante a execução.
        """
        # 1. Buscar a campanha pelo repositório
        campanha = await self._repository.buscar_por_id(campanha_id)
        if not campanha:
            raise NotFoundError("Campanha", str(campanha_id))

        # 2. Validar a transição de estado
        estados_executaveis = (StatusCampanha.AGENDADA, StatusCampanha.ATIVA)
        if campanha.status not in estados_executaveis:
            raise ValidationError(
                f"Campanha com status '{campanha.status.value}' não pode ser iniciada. "
                f"Status permitidos: {[s.value for s in estados_executaveis]}",
            )

        # 3. Delegar a execução ao executor
        sucesso = await self._executor.executar(campanha_id)
        if not sucesso:
            raise DatabaseError("Erro interno ao executar a campanha.")

        logger.info(
            f"[CampanhasApplicationService] Campanha {campanha_id} iniciada com sucesso."
        )
        return {
            "status": "iniciada",
            "campanha_id": campanha_id,
            "message": "Campanha iniciada com sucesso.",
        }

    async def buscar_campanha(self, campanha_id: int) -> CampanhaData:
        """
        Caso de Uso: Buscar os detalhes de uma campanha específica.

        Raises:
            NotFoundError: Se a campanha não for encontrada.
        """
        campanha = await self._repository.buscar_por_id(campanha_id)
        if not campanha:
            raise NotFoundError("Campanha", str(campanha_id))
        return campanha

    async def listar_campanhas(
        self,
        status: Optional[str] = None,
        tipo: Optional[str] = None,
        limit: int = 50,
    ) -> Dict[str, Any]:
        """
        Caso de Uso: Listar campanhas com filtros opcionais.

        Delega ao repositório existente que já possui método listar_por_status.
        Para listagem geral, usa busca direta.
        """
        if status:
            try:
                status_enum = StatusCampanha(status)
                campanhas = await self._repository.listar_por_status(status_enum)
            except ValueError:
                raise ValidationError(
                    f"Status inválido: '{status}'. "
                    f"Valores aceitos: {[s.value for s in StatusCampanha]}",
                )
        else:
            # O repositório existente não tem listar genérico com filtros,
            # mas listar_ativas/listar_agendadas cobrem os casos de uso.
            # Para listagem geral, delegamos ao repositório.
            campanhas = await self._listar_todas(tipo=tipo, limit=limit)

        campanhas_dict = [c.to_dict() for c in campanhas[:limit]]
        return {"campanhas": campanhas_dict, "total": len(campanhas_dict)}

    async def _listar_todas(
        self,
        tipo: Optional[str] = None,
        limit: int = 50,
    ) -> List[CampanhaData]:
        """
        Listagem interna que agrega resultados de todos os status.

        Usa os métodos existentes do repositório para evitar duplicação.
        """
        todas = []
        for status_enum in StatusCampanha:
            campanhas = await self._repository.listar_por_status(status_enum)
            if tipo:
                campanhas = [c for c in campanhas if c.tipo_campanha.value == tipo]
            todas.extend(campanhas)

        # Ordenar por created_at decrescente
        todas.sort(key=lambda c: c.created_at or "", reverse=True)
        return todas[:limit]

    async def relatorio_campanha(self, campanha_id: int) -> Dict[str, Any]:
        """
        Caso de Uso: Gerar o relatório completo de uma campanha.

        Consolida os dados da campanha com métricas de envio.

        Raises:
            NotFoundError: Se a campanha não for encontrada.
        """
        campanha = await self._repository.buscar_por_id(campanha_id)
        if not campanha:
            raise NotFoundError("Campanha", str(campanha_id))

        return {
            "campanha_id": campanha_id,
            "nome": campanha.nome_template,
            "tipo_campanha": campanha.tipo_campanha.value,
            "status": campanha.status.value,
            "contadores": {
                "total_destinatarios": campanha.total_destinatarios,
                "enviados": campanha.enviados,
                "entregues": campanha.entregues,
                "respondidos": campanha.respondidos,
            },
            "periodo": {
                "criada_em": campanha.created_at.isoformat()
                if campanha.created_at
                else None,
                "agendada_para": campanha.agendar_para.isoformat()
                if campanha.agendar_para
                else None,
                "iniciada_em": campanha.iniciada_em.isoformat()
                if campanha.iniciada_em
                else None,
                "concluida_em": campanha.concluida_em.isoformat()
                if campanha.concluida_em
                else None,
            },
            "audience_filters": campanha.audience_filters.to_dict()
            if campanha.audience_filters
            else {},
        }

    async def atualizar_status(
        self, campanha_id: int, novo_status: str
    ) -> Dict[str, Any]:
        """
        Caso de Uso: Atualizar o status de uma campanha.

        Usa o repositório existente que inclui invalidação de cache Redis.

        Raises:
            ValidationError: Se o status for inválido.
            NotFoundError: Se a campanha não for encontrada.
            DatabaseError: Se a atualização falhar.
        """
        # 1. Validar o novo status
        try:
            status = StatusCampanha(novo_status)
        except ValueError:
            raise ValidationError(
                f"Status inválido: '{novo_status}'. "
                f"Valores aceitos: {[s.value for s in StatusCampanha]}",
            )

        # 2. Verificar se a campanha existe
        campanha = await self._repository.buscar_por_id(campanha_id)
        if not campanha:
            raise NotFoundError("Campanha", str(campanha_id))

        # 3. Persistir (repositório existente já invalida cache Redis)
        sucesso = await self._repository.atualizar_status(campanha_id, status)
        if not sucesso:
            raise DatabaseError("Erro ao atualizar o status da campanha.")

        return {
            "campanha_id": campanha_id,
            "status_anterior": campanha.status.value,
            "status_novo": status.value,
        }

    async def preview_segmento(self, filtros: Dict[str, Any]) -> Dict[str, Any]:
        """
        Caso de Uso: Pré-visualizar um segmento de audiência.
        """
        total = await self._segmentacao.contar_segmento(filtros)
        amostra = await self._segmentacao.buscar_segmento(filtros, limite=10)
        return {
            "total": total,
            "amostra": [
                {
                    "nome": m.get("primeiro_nome"),
                    "especialidade": m.get("especialidade_nome"),
                    "regiao": m.get("regiao"),
                }
                for m in amostra
            ],
        }


# Factory function seguindo o padrão de deps.py
def get_campanhas_service() -> CampanhasApplicationService:
    """
    Retorna instância do CampanhasApplicationService.

    Para testes, crie com dependências mockadas:
        service = CampanhasApplicationService(
            repository=mock_repo,
            executor=mock_executor,
            segmentacao=mock_seg,
        )
    """
    return CampanhasApplicationService()
