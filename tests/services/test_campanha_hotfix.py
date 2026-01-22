"""Testes do hotfix da campanha - Sprint 35 Epic 01.

Valida que a funcao criar_envios_campanha funciona com o schema atual do banco.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.campanha import criar_envios_campanha


@pytest.fixture
def mock_campanha_discovery():
    """Campanha discovery como a 16."""
    return {
        "id": 16,
        "nome_template": "Piloto Discovery",
        "tipo_campanha": "discovery",
        "corpo": "[DISCOVERY] Usar aberturas dinamicas",
        "status": "agendada",
        "audience_filters": {
            "regioes": [],
            "especialidades": [],
            "quantidade_alvo": 50
        },
        "pode_ofertar": False,
    }


@pytest.fixture
def mock_campanha_oferta():
    """Campanha de oferta com template."""
    return {
        "id": 17,
        "nome_template": "Oferta Cardiologia",
        "tipo_campanha": "oferta",
        "corpo": "Oi {nome}! Temos vagas para {especialidade} na regiao do ABC",
        "status": "agendada",
        "audience_filters": {
            "regioes": ["abc"],
            "especialidades": ["cardiologia"],
            "quantidade_alvo": 20
        },
        "pode_ofertar": True,
    }


@pytest.fixture
def mock_destinatario():
    """Destinatario de teste."""
    return {
        "id": "123e4567-e89b-12d3-a456-426614174000",
        "primeiro_nome": "Carlos",
        "especialidade_nome": "Cardiologia",
    }


@pytest.mark.asyncio
async def test_criar_envios_campanha_discovery(mock_campanha_discovery, mock_destinatario):
    """Testa criacao de envios para campanha discovery."""
    with patch("app.services.campanha.supabase") as mock_supabase, \
         patch("app.services.segmentacao.segmentacao_service") as mock_seg, \
         patch("app.services.fila.fila_service") as mock_fila, \
         patch("app.services.campanha.obter_abertura_texto") as mock_abertura:

        # Setup mocks
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = mock_campanha_discovery
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()
        mock_seg.buscar_segmento = AsyncMock(return_value=[mock_destinatario])
        mock_fila.enfileirar = AsyncMock()
        mock_abertura.return_value = "Oi Dr Carlos! Tudo bem?\n\nSou a Julia da Revoluna"

        # Executar
        await criar_envios_campanha(16)

        # Verificar que usou abertura dinamica
        mock_abertura.assert_called_once_with(
            cliente_id=mock_destinatario["id"],
            nome=mock_destinatario["primeiro_nome"]
        )

        # Verificar que enfileirou
        mock_fila.enfileirar.assert_called_once()
        call_args = mock_fila.enfileirar.call_args
        assert call_args.kwargs["cliente_id"] == mock_destinatario["id"]
        assert call_args.kwargs["tipo"] == "discovery"
        assert "campanha_id" in call_args.kwargs["metadata"]
        assert call_args.kwargs["metadata"]["campanha_id"] == "16"


@pytest.mark.asyncio
async def test_criar_envios_campanha_oferta_com_template(mock_campanha_oferta, mock_destinatario):
    """Testa criacao de envios para campanha de oferta com template."""
    with patch("app.services.campanha.supabase") as mock_supabase, \
         patch("app.services.segmentacao.segmentacao_service") as mock_seg, \
         patch("app.services.fila.fila_service") as mock_fila, \
         patch("app.services.campanha.obter_abertura_texto") as mock_abertura:

        # Setup mocks
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = mock_campanha_oferta
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()
        mock_seg.buscar_segmento = AsyncMock(return_value=[mock_destinatario])
        mock_fila.enfileirar = AsyncMock()

        # Executar
        await criar_envios_campanha(17)

        # Verificar que NAO usou abertura dinamica (usa corpo)
        mock_abertura.assert_not_called()

        # Verificar que enfileirou com mensagem do template
        mock_fila.enfileirar.assert_called_once()
        call_args = mock_fila.enfileirar.call_args
        assert call_args.kwargs["cliente_id"] == mock_destinatario["id"]
        assert call_args.kwargs["tipo"] == "oferta"
        # Verificar que mensagem foi formatada com nome e especialidade
        assert "Carlos" in call_args.kwargs["conteudo"]
        assert "Cardiologia" in call_args.kwargs["conteudo"]


@pytest.mark.asyncio
async def test_criar_envios_nao_usa_mensagem_template(mock_campanha_discovery):
    """Garante que nao tenta acessar mensagem_template (campo que nao existe)."""
    with patch("app.services.campanha.supabase") as mock_supabase, \
         patch("app.services.segmentacao.segmentacao_service") as mock_seg, \
         patch("app.services.fila.fila_service") as mock_fila, \
         patch("app.services.campanha.obter_abertura_texto") as mock_abertura:

        # Campanha sem mensagem_template (como a real no banco)
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = mock_campanha_discovery
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()
        mock_seg.buscar_segmento = AsyncMock(return_value=[])

        # Deve executar sem erro (nao tentar acessar mensagem_template)
        await criar_envios_campanha(16)

        # Se chegou aqui, nao deu KeyError
        assert True


@pytest.mark.asyncio
async def test_criar_envios_usa_audience_filters(mock_campanha_oferta, mock_destinatario):
    """Garante que usa audience_filters (nao config)."""
    with patch("app.services.campanha.supabase") as mock_supabase, \
         patch("app.services.segmentacao.segmentacao_service") as mock_seg, \
         patch("app.services.fila.fila_service") as mock_fila:

        # Setup
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = mock_campanha_oferta
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()
        mock_seg.buscar_segmento = AsyncMock(return_value=[mock_destinatario])
        mock_fila.enfileirar = AsyncMock()

        # Executar
        await criar_envios_campanha(17)

        # Verificar que buscar_segmento foi chamado com filtros corretos
        mock_seg.buscar_segmento.assert_called_once()
        call_args = mock_seg.buscar_segmento.call_args
        filtros = call_args[0][0]  # primeiro argumento posicional

        # Deve ter especialidade e regiao do audience_filters
        assert filtros.get("especialidade") == "cardiologia"
        assert filtros.get("regiao") == "abc"


@pytest.mark.asyncio
async def test_criar_envios_atualiza_enviados(mock_campanha_discovery, mock_destinatario):
    """Garante que atualiza campo 'enviados' (nao envios_criados)."""
    with patch("app.services.campanha.supabase") as mock_supabase, \
         patch("app.services.segmentacao.segmentacao_service") as mock_seg, \
         patch("app.services.fila.fila_service") as mock_fila, \
         patch("app.services.campanha.obter_abertura_texto") as mock_abertura:

        # Setup
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = mock_campanha_discovery
        mock_update = MagicMock()
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = mock_update
        mock_seg.buscar_segmento = AsyncMock(return_value=[mock_destinatario])
        mock_fila.enfileirar = AsyncMock()
        mock_abertura.return_value = "Oi!"

        # Executar
        await criar_envios_campanha(16)

        # Verificar que update foi chamado com 'enviados'
        update_calls = mock_supabase.table.return_value.update.call_args_list
        assert len(update_calls) > 0

        # Pegar o dicionario passado para update
        update_data = update_calls[0][0][0]
        assert "enviados" in update_data
        assert "envios_criados" not in update_data
        assert update_data["enviados"] == 1  # 1 destinatario


@pytest.mark.asyncio
async def test_criar_envios_usa_tipo_campanha(mock_campanha_discovery, mock_destinatario):
    """Garante que usa tipo_campanha (nao tipo)."""
    with patch("app.services.campanha.supabase") as mock_supabase, \
         patch("app.services.segmentacao.segmentacao_service") as mock_seg, \
         patch("app.services.fila.fila_service") as mock_fila, \
         patch("app.services.campanha.obter_abertura_texto") as mock_abertura:

        # Setup
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = mock_campanha_discovery
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()
        mock_seg.buscar_segmento = AsyncMock(return_value=[mock_destinatario])
        mock_fila.enfileirar = AsyncMock()
        mock_abertura.return_value = "Oi!"

        # Executar
        await criar_envios_campanha(16)

        # Verificar que enfileirar usou tipo_campanha
        call_args = mock_fila.enfileirar.call_args
        assert call_args.kwargs["tipo"] == "discovery"  # do tipo_campanha


@pytest.mark.asyncio
async def test_criar_envios_campanha_nao_encontrada():
    """Testa comportamento quando campanha nao existe."""
    with patch("app.services.campanha.supabase") as mock_supabase:

        # Campanha nao encontrada
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = None

        # Deve executar sem erro
        await criar_envios_campanha(999)

        # Se chegou aqui, tratou corretamente
        assert True
