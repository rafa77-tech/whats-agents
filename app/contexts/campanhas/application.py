"""
Application Service do Bounded Context: Campanhas Outbound

Este módulo é o ponto de entrada para todos os casos de uso do contexto
de Campanhas. Ele orquestra a interação entre os repositórios, os
serviços de domínio e a infraestrutura (fila, segmentação), mas NÃO
contém regras de negócio — essas pertencem ao domínio.

Princípio: ADR-007 — As rotas da API chamam apenas este módulo.
A rota não sabe nada sobre Supabase, repositórios ou regras de negócio.

Padrão: API Route -> Application Service -> Repository/Domain Service
"""
import logging
from typing import Any, Dict, List, Optional

from fastapi import HTTPException

from app.contexts.campanhas.repositories import campanha_repository
from app.services.campanhas.executor import campanha_executor
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
    """

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
        Delega a criação ao repositório legado (services/campanhas/repository.py)
        para manter compatibilidade durante a migração gradual.

        Returns:
            O objeto CampanhaData da campanha criada.

        Raises:
            HTTPException 400: Se o tipo de campanha for inválido.
        """
        # 1. Validar tipo de campanha (regra de negócio simples de entrada)
        try:
            tipo = TipoCampanha(tipo_campanha)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Tipo de campanha inválido: '{tipo_campanha}'. "
                       f"Valores aceitos: {[t.value for t in TipoCampanha]}",
            )

        # 2. Montar filtros para contagem de audiência
        filtros = {}
        if especialidades:
            filtros["especialidade"] = especialidades[0]
        if regioes:
            filtros["regiao"] = regioes[0]

        total_destinatarios = await segmentacao_service.contar_segmento(filtros)

        # 3. Montar o objeto de filtros de audiência
        audience_filters = AudienceFilters(
            regioes=regioes or [],
            especialidades=especialidades or [],
            quantidade_alvo=quantidade_alvo,
            modo_selecao=modo_selecao,
            chips_excluidos=chips_excluidos or [],
        )

        # 4. Delegar a persistência ao repositório legado (durante a migração)
        # TODO (Fase 2): Migrar a lógica de criação para campanha_repository
        from app.services.campanhas.repository import campanha_repository as legacy_repo
        campanha = await legacy_repo.criar(
            nome_template=nome_template,
            tipo_campanha=tipo,
            corpo=corpo,
            tom=tom,
            objetivo=objetivo,
            audience_filters=audience_filters,
            agendar_para=agendar_para,
            pode_ofertar=pode_ofertar,
        )

        # Atualizar total de destinatários após a criação
        if campanha and total_destinatarios > 0:
            await legacy_repo.atualizar_total_destinatarios(campanha.id, total_destinatarios)

        if not campanha:
            raise HTTPException(status_code=500, detail="Erro ao criar campanha no banco de dados.")

        logger.info(f"[CampanhasApplicationService] Campanha criada: id={campanha.id}, tipo={tipo.value}")
        return campanha

    async def executar_campanha(self, campanha_id: int) -> Dict[str, Any]:
        """
        Caso de Uso: Executar (iniciar o envio de) uma campanha.

        Valida se a campanha existe e se está em um estado que permite
        execução, antes de delegar ao executor de domínio.

        Args:
            campanha_id: O identificador único da campanha a ser executada.

        Returns:
            Um dicionário com o resultado da operação.

        Raises:
            HTTPException 404: Se a campanha não for encontrada.
            HTTPException 400: Se a campanha não puder ser iniciada no estado atual.
            HTTPException 500: Se ocorrer um erro durante a execução.
        """
        # 1. Buscar a campanha pelo repositório (sem SQL na rota)
        campanha = await campanha_repository.buscar_por_id(campanha_id)
        if not campanha:
            raise HTTPException(status_code=404, detail=f"Campanha {campanha_id} não encontrada.")

        # 2. Validar a transição de estado (regra de negócio)
        estados_executaveis = (StatusCampanha.AGENDADA, StatusCampanha.ATIVA)
        if campanha.status not in estados_executaveis:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Campanha com status '{campanha.status.value}' não pode ser iniciada. "
                    f"Status permitidos: {[s.value for s in estados_executaveis]}"
                ),
            )

        # 3. Delegar a execução ao serviço de domínio (executor)
        sucesso = await campanha_executor.executar(campanha_id)
        if not sucesso:
            raise HTTPException(status_code=500, detail="Erro interno ao executar a campanha.")

        logger.info(f"[CampanhasApplicationService] Campanha {campanha_id} iniciada com sucesso.")
        return {
            "status": "iniciada",
            "campanha_id": campanha_id,
            "message": "Campanha iniciada com sucesso.",
        }

    async def buscar_campanha(self, campanha_id: int) -> CampanhaData:
        """
        Caso de Uso: Buscar os detalhes de uma campanha específica.

        Args:
            campanha_id: O identificador único da campanha.

        Returns:
            O objeto CampanhaData da campanha.

        Raises:
            HTTPException 404: Se a campanha não for encontrada.
        """
        campanha = await campanha_repository.buscar_por_id(campanha_id)
        if not campanha:
            raise HTTPException(status_code=404, detail=f"Campanha {campanha_id} não encontrada.")
        return campanha

    async def listar_campanhas(
        self,
        status: Optional[str] = None,
        tipo: Optional[str] = None,
        limit: int = 50,
    ) -> Dict[str, Any]:
        """
        Caso de Uso: Listar campanhas com filtros opcionais.

        Este método substitui o acesso direto ao Supabase que existia
        na rota GET /campanhas/.

        Returns:
            Um dicionário com a lista de campanhas e o total.
        """
        campanhas = await campanha_repository.listar(status=status, tipo=tipo, limit=limit)
        campanhas_dict = [c.to_dict() for c in campanhas]
        return {"campanhas": campanhas_dict, "total": len(campanhas_dict)}

    async def relatorio_campanha(self, campanha_id: int) -> Dict[str, Any]:
        """
        Caso de Uso: Gerar o relatório completo de uma campanha.

        Consolida os dados da campanha com os dados da fila de envios,
        sem que a rota precise conhecer nenhuma dessas fontes de dados.

        Args:
            campanha_id: O identificador único da campanha.

        Returns:
            Um dicionário com o relatório consolidado.

        Raises:
            HTTPException 404: Se a campanha não for encontrada.
        """
        # 1. Buscar dados da campanha
        campanha = await campanha_repository.buscar_por_id(campanha_id)
        if not campanha:
            raise HTTPException(status_code=404, detail=f"Campanha {campanha_id} não encontrada.")

        # 2. Buscar dados da fila de envios (via repositório, sem SQL na rota)
        envios = await campanha_repository.buscar_envios_da_fila(campanha_id)

        # 3. Calcular métricas da fila
        enviados_fila = len([e for e in envios if e["status"] == "enviada"])
        erros = len([e for e in envios if e["status"] == "erro"])
        pendentes = len([e for e in envios if e["status"] == "pendente"])

        # 4. Montar e retornar o relatório consolidado
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
            "fila": {
                "total": len(envios),
                "enviados": enviados_fila,
                "erros": erros,
                "pendentes": pendentes,
                "taxa_entrega": enviados_fila / len(envios) if envios else 0,
            },
            "periodo": {
                "criada_em": campanha.created_at.isoformat() if campanha.created_at else None,
                "agendada_para": campanha.agendar_para.isoformat() if campanha.agendar_para else None,
                "iniciada_em": campanha.iniciada_em.isoformat() if campanha.iniciada_em else None,
                "concluida_em": campanha.concluida_em.isoformat() if campanha.concluida_em else None,
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

        Args:
            campanha_id: O identificador único da campanha.
            novo_status: O novo status em formato string.

        Returns:
            Um dicionário confirmando a mudança de status.

        Raises:
            HTTPException 400: Se o status for inválido.
            HTTPException 404: Se a campanha não for encontrada.
            HTTPException 500: Se a atualização falhar.
        """
        # 1. Validar o novo status
        try:
            status = StatusCampanha(novo_status)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Status inválido: '{novo_status}'. "
                       f"Valores aceitos: {[s.value for s in StatusCampanha]}",
            )

        # 2. Verificar se a campanha existe
        campanha = await campanha_repository.buscar_por_id(campanha_id)
        if not campanha:
            raise HTTPException(status_code=404, detail=f"Campanha {campanha_id} não encontrada.")

        # 3. Persistir a mudança de status
        sucesso = await campanha_repository.atualizar_status(campanha_id, status)
        if not sucesso:
            raise HTTPException(status_code=500, detail="Erro ao atualizar o status da campanha.")

        return {
            "campanha_id": campanha_id,
            "status_anterior": campanha.status.value,
            "status_novo": status.value,
        }

    async def preview_segmento(self, filtros: Dict[str, Any]) -> Dict[str, Any]:
        """
        Caso de Uso: Pré-visualizar um segmento de audiência antes de criar uma campanha.

        Args:
            filtros: Dicionário com os filtros de segmentação.

        Returns:
            Um dicionário com o total e uma amostra de médicos.
        """
        total = await segmentacao_service.contar_segmento(filtros)
        amostra = await segmentacao_service.buscar_segmento(filtros, limite=10)
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


# Instância singleton para uso nas rotas
campanhas_service = CampanhasApplicationService()
