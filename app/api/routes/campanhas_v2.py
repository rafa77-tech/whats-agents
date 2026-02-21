"""
Rotas de Campanhas (v2 - Arquitetura DDD)

Esta é a versão refatorada do módulo de rotas de campanhas, seguindo
os princípios do Domain-Driven Design estabelecidos nos ADRs:

- ADR-006: Bounded Contexts explícitos
- ADR-007: Sem SQL direto em rotas (toda lógica via Application Service)
- ADR-008: Linguagem Ubíqua e estados canônicos

DIFERENÇA EM RELAÇÃO À VERSÃO ORIGINAL (campanhas.py):
- Antes: A rota acessava `supabase.table(...)` diretamente em múltiplos endpoints.
- Depois: A rota delega TODA a lógica ao `CampanhasApplicationService`.
  A rota só conhece HTTP: recebe requests, chama o serviço, retorna responses.

COMO USAR:
Para ativar esta versão, substitua o import em `app/main.py`:
  # Antes:
  from app.api.routes import campanhas
  app.include_router(campanhas.router)

  # Depois:
  from app.api.routes import campanhas_v2
  app.include_router(campanhas_v2.router)

Ou, para uma migração gradual, inclua ambos os routers com prefixos diferentes.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

# O único import de domínio que a rota precisa: o Application Service
from app.contexts.campanhas.application import campanhas_service

router = APIRouter(prefix="/v2/campanhas", tags=["campanhas-v2"])


# ---------------------------------------------------------------------------
# Schemas de Request/Response (Pydantic)
# Responsabilidade: Apenas validação e serialização de dados HTTP.
# ---------------------------------------------------------------------------

class CriarCampanhaRequest(BaseModel):
    """Schema de entrada para criação de campanha."""
    nome_template: str = Field(..., description="Nome identificador da campanha")
    tipo_campanha: str = Field(
        default="oferta",
        description="Tipo: discovery, oferta, oferta_plantao, reativacao, followup",
    )
    corpo: Optional[str] = Field(
        None, description="Corpo da mensagem com placeholders {nome}, {especialidade}"
    )
    tom: Optional[str] = Field(default="amigavel", description="Tom da mensagem")
    objetivo: Optional[str] = Field(None, description="Objetivo da campanha em linguagem natural")
    especialidades: Optional[List[str]] = Field(
        default=None, description="Filtro de especialidades médicas"
    )
    regioes: Optional[List[str]] = Field(default=None, description="Filtro de regiões geográficas")
    quantidade_alvo: int = Field(default=50, description="Quantidade alvo de envios")
    modo_selecao: str = Field(
        default="deterministico",
        description="Modo de seleção: deterministico ou aleatorio",
    )
    agendar_para: Optional[datetime] = Field(None, description="Data/hora para agendamento")
    pode_ofertar: bool = Field(default=True, description="Se pode ofertar vagas nesta campanha")
    chips_excluidos: Optional[List[str]] = Field(
        default=None, description="IDs de chips a NÃO usar nesta campanha"
    )


# ---------------------------------------------------------------------------
# Endpoints
# Responsabilidade: Apenas orquestração HTTP.
# Nenhum endpoint deve conter lógica de negócio ou acesso a dados.
# ---------------------------------------------------------------------------

@router.post("/")
async def criar_campanha(dados: CriarCampanhaRequest):
    """
    Cria uma nova campanha outbound.

    Delega toda a lógica de validação, contagem de audiência e persistência
    ao Application Service do contexto de Campanhas.
    """
    campanha = await campanhas_service.criar_campanha(
        nome_template=dados.nome_template,
        tipo_campanha=dados.tipo_campanha,
        corpo=dados.corpo,
        tom=dados.tom,
        objetivo=dados.objetivo,
        especialidades=dados.especialidades,
        regioes=dados.regioes,
        quantidade_alvo=dados.quantidade_alvo,
        modo_selecao=dados.modo_selecao,
        agendar_para=dados.agendar_para,
        pode_ofertar=dados.pode_ofertar,
        chips_excluidos=dados.chips_excluidos,
    )
    return campanha.to_dict()


@router.get("/")
async def listar_campanhas(
    status: Optional[str] = None,
    tipo: Optional[str] = None,
    limit: int = 50,
):
    """
    Lista campanhas com filtros opcionais.

    ANTES: Acessava supabase.table("campanhas") diretamente nesta rota.
    DEPOIS: Delega ao Application Service, que usa o repositório.
    """
    return await campanhas_service.listar_campanhas(status=status, tipo=tipo, limit=limit)


@router.get("/{campanha_id}")
async def buscar_campanha(campanha_id: int):
    """
    Busca os detalhes de uma campanha específica.
    """
    campanha = await campanhas_service.buscar_campanha(campanha_id)
    return campanha.to_dict()


@router.post("/{campanha_id}/executar")
async def executar_campanha(campanha_id: int):
    """
    Inicia a execução de uma campanha agendada ou ativa.

    ANTES: A rota buscava a campanha, validava o status e chamava o executor.
    DEPOIS: Delega toda essa orquestração ao Application Service.
    """
    return await campanhas_service.executar_campanha(campanha_id)


@router.get("/{campanha_id}/relatorio")
async def relatorio_campanha(campanha_id: int):
    """
    Retorna o relatório completo de uma campanha.

    ANTES: Acessava supabase.table("fila_mensagens") diretamente nesta rota.
    DEPOIS: Delega ao Application Service, que consolida os dados via repositório.
    """
    return await campanhas_service.relatorio_campanha(campanha_id)


@router.patch("/{campanha_id}/status")
async def atualizar_status_campanha(campanha_id: int, novo_status: str):
    """
    Atualiza o status de uma campanha.
    """
    return await campanhas_service.atualizar_status(campanha_id, novo_status)


@router.post("/segmento/preview")
async def preview_segmento(filtros: Dict[str, Any]):
    """
    Pré-visualiza um segmento de audiência antes de criar uma campanha.
    """
    return await campanhas_service.preview_segmento(filtros)
