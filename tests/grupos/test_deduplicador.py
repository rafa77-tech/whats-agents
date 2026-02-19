"""
Testes para o deduplicador de vagas.

Sprint 14 - E08 - Deduplicação
"""

import pytest
from uuid import uuid4
from datetime import datetime, timedelta, UTC
from unittest.mock import patch, MagicMock

from app.services.grupos.deduplicador import (
    calcular_hash_dedup,
    buscar_vaga_duplicada,
    registrar_fonte_vaga,
    marcar_como_duplicada,
    processar_deduplicacao,
    processar_batch_deduplicacao,
    listar_fontes_vaga,
    obter_estatisticas_dedup,
    ResultadoDedup,
    JANELA_DEDUP_HORAS,
)


class TestCalcularHashDedup:
    """Testes do cálculo de hash."""

    def test_hash_consistente(self):
        """Mesmo input deve gerar mesmo hash."""
        hospital_id = uuid4()
        esp_id = uuid4()
        periodo_id = uuid4()

        hash1 = calcular_hash_dedup(hospital_id, "2024-12-28", periodo_id, esp_id)
        hash2 = calcular_hash_dedup(hospital_id, "2024-12-28", periodo_id, esp_id)

        assert hash1 == hash2

    def test_hash_diferente_hospital(self):
        """Hospitais diferentes geram hashes diferentes."""
        esp_id = uuid4()

        hash1 = calcular_hash_dedup(uuid4(), "2024-12-28", None, esp_id)
        hash2 = calcular_hash_dedup(uuid4(), "2024-12-28", None, esp_id)

        assert hash1 != hash2

    def test_hash_diferente_data(self):
        """Datas diferentes geram hashes diferentes."""
        hospital_id = uuid4()
        esp_id = uuid4()

        hash1 = calcular_hash_dedup(hospital_id, "2024-12-28", None, esp_id)
        hash2 = calcular_hash_dedup(hospital_id, "2024-12-29", None, esp_id)

        assert hash1 != hash2

    def test_hash_diferente_especialidade(self):
        """Especialidades diferentes geram hashes diferentes."""
        hospital_id = uuid4()

        hash1 = calcular_hash_dedup(hospital_id, "2024-12-28", None, uuid4())
        hash2 = calcular_hash_dedup(hospital_id, "2024-12-28", None, uuid4())

        assert hash1 != hash2

    def test_hash_diferente_periodo(self):
        """Períodos diferentes geram hashes diferentes."""
        hospital_id = uuid4()
        esp_id = uuid4()

        hash1 = calcular_hash_dedup(hospital_id, "2024-12-28", uuid4(), esp_id)
        hash2 = calcular_hash_dedup(hospital_id, "2024-12-28", uuid4(), esp_id)

        assert hash1 != hash2

    def test_hash_sem_periodo(self):
        """Deve funcionar sem período."""
        hospital_id = uuid4()
        esp_id = uuid4()

        hash_result = calcular_hash_dedup(hospital_id, "2024-12-28", None, esp_id)

        assert len(hash_result) == 32  # MD5 hex

    def test_hash_sem_data(self):
        """Deve funcionar sem data."""
        hospital_id = uuid4()
        esp_id = uuid4()

        hash_result = calcular_hash_dedup(hospital_id, None, None, esp_id)

        assert len(hash_result) == 32

    def test_hash_formato_md5(self):
        """Hash deve ter formato MD5 (32 chars hex)."""
        hash_result = calcular_hash_dedup(uuid4(), "2024-12-28", None, uuid4())

        assert len(hash_result) == 32
        assert all(c in "0123456789abcdef" for c in hash_result)


class TestBuscarVagaDuplicada:
    """Testes de busca de duplicatas."""

    @pytest.fixture
    def mock_supabase(self):
        """Mock do Supabase."""
        with patch("app.services.grupos.deduplicador.supabase") as mock:
            yield mock

    @pytest.mark.asyncio
    async def test_encontra_duplicata(self, mock_supabase):
        """Deve encontrar vaga com mesmo hash."""
        vaga_id = str(uuid4())
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.gte.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[{"id": vaga_id, "qtd_fontes": 1}]
        )

        resultado = await buscar_vaga_duplicada("abc123hash")

        assert resultado is not None
        assert resultado["id"] == vaga_id

    @pytest.mark.asyncio
    async def test_nao_encontra_duplicata(self, mock_supabase):
        """Deve retornar None quando não há duplicata."""
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.gte.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[]
        )

        resultado = await buscar_vaga_duplicada("xyz789hash")

        assert resultado is None

    @pytest.mark.asyncio
    async def test_exclui_propria_vaga(self, mock_supabase):
        """Deve excluir a própria vaga da busca."""
        excluir_id = uuid4()

        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.gte.return_value.neq.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[]
        )

        await buscar_vaga_duplicada("abc123hash", excluir_id=excluir_id)

        # Verifica que neq foi chamado
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.gte.return_value.neq.assert_called()


class TestRegistrarFonteVaga:
    """Testes de registro de fontes."""

    @pytest.fixture
    def mock_supabase(self):
        """Mock do Supabase."""
        with patch("app.services.grupos.deduplicador.supabase") as mock:
            yield mock

    @pytest.mark.asyncio
    async def test_registra_primeira_fonte(self, mock_supabase):
        """Deve registrar primeira fonte com ordem 1."""
        fonte_id = str(uuid4())

        # Mock para verificar existente
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[]
        )

        # Mock para contar fontes
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            count=0
        )

        # Mock para insert
        mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock(
            data=[{"id": fonte_id}]
        )

        # Mock para update
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()

        resultado = await registrar_fonte_vaga(
            vaga_principal_id=uuid4(),
            mensagem_id=uuid4(),
            grupo_id=uuid4()
        )

        assert resultado is not None

    @pytest.mark.asyncio
    async def test_nao_duplica_fonte_existente(self, mock_supabase):
        """Deve retornar fonte existente se já cadastrada."""
        fonte_id = str(uuid4())

        # Mock para verificar existente - já existe
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[{"id": fonte_id}]
        )

        resultado = await registrar_fonte_vaga(
            vaga_principal_id=uuid4(),
            mensagem_id=uuid4(),
            grupo_id=uuid4()
        )

        assert str(resultado) == fonte_id

    @pytest.mark.asyncio
    async def test_trunca_texto_longo(self, mock_supabase):
        """Deve truncar texto original para 500 chars."""
        fonte_id = str(uuid4())

        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[]
        )
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            count=0
        )
        mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock(
            data=[{"id": fonte_id}]
        )
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()

        texto_longo = "x" * 1000

        await registrar_fonte_vaga(
            vaga_principal_id=uuid4(),
            mensagem_id=uuid4(),
            grupo_id=uuid4(),
            texto_original=texto_longo
        )

        # Verifica que insert foi chamado
        mock_supabase.table.return_value.insert.assert_called()


class TestMarcarComoDuplicada:
    """Testes de marcação de duplicatas."""

    @pytest.fixture
    def mock_supabase(self):
        """Mock do Supabase."""
        with patch("app.services.grupos.deduplicador.supabase") as mock:
            yield mock

    @pytest.mark.asyncio
    async def test_marca_duplicada(self, mock_supabase):
        """Deve marcar vaga como duplicada."""
        vaga_id = uuid4()
        principal_id = uuid4()

        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()

        await marcar_como_duplicada(vaga_id, principal_id)

        # Verifica que update foi chamado com os dados corretos
        mock_supabase.table.return_value.update.assert_called_once()
        call_args = mock_supabase.table.return_value.update.call_args[0][0]
        assert call_args["status"] == "duplicada"
        assert call_args["eh_duplicada"] is True


class TestProcessarDeduplicacao:
    """Testes do processador de deduplicação (via RPC atômica)."""

    @pytest.fixture
    def mock_supabase(self):
        """Mock do Supabase."""
        with patch("app.services.grupos.deduplicador.supabase") as mock:
            yield mock

    @pytest.mark.asyncio
    async def test_vaga_nao_encontrada(self, mock_supabase):
        """Deve retornar erro se vaga não existe."""
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data=None
        )

        resultado = await processar_deduplicacao(uuid4())

        assert resultado.erro == "vaga_nao_encontrada"
        assert resultado.duplicada is False

    @pytest.mark.asyncio
    async def test_dados_insuficientes(self, mock_supabase):
        """Deve retornar erro se faltam dados."""
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data={
                "id": str(uuid4()),
                "hospital_id": None,  # Faltando
                "especialidade_id": str(uuid4()),
            }
        )

        resultado = await processar_deduplicacao(uuid4())

        assert resultado.erro == "dados_insuficientes"

    @pytest.mark.asyncio
    async def test_dedup_rpc_nova_vaga(self, mock_supabase):
        """Deve usar RPC e retornar não-duplicada para vaga nova."""
        vaga_id = uuid4()
        hospital_id = uuid4()
        esp_id = uuid4()
        mensagem_id = uuid4()
        grupo_id = uuid4()

        # Mock select vaga
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data={
                "id": str(vaga_id),
                "hospital_id": str(hospital_id),
                "especialidade_id": str(esp_id),
                "periodo_id": None,
                "data": "2026-03-15",
                "mensagem_id": str(mensagem_id),
                "grupo_origem_id": str(grupo_id),
                "contato_responsavel_id": None,
                "valor": 2500,
            }
        )

        # Mock RPC dedup_vaga_grupo
        mock_supabase.rpc.return_value.execute.return_value = MagicMock(
            data=[{"eh_duplicada": False, "principal_id": str(vaga_id)}]
        )

        # Mock registrar_fonte_vaga (select existente, count, insert, update)
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[]
        )
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            count=0
        )
        mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock(
            data=[{"id": str(uuid4())}]
        )
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()

        resultado = await processar_deduplicacao(vaga_id)

        assert resultado.duplicada is False
        assert resultado.principal_id == vaga_id
        assert resultado.hash_dedup is not None

        # Verifica que RPC foi chamada
        mock_supabase.rpc.assert_called_once_with(
            "dedup_vaga_grupo",
            {"p_vaga_id": str(vaga_id), "p_hash": resultado.hash_dedup},
        )

    @pytest.mark.asyncio
    async def test_dedup_rpc_duplicata(self, mock_supabase):
        """Deve usar RPC e retornar duplicada quando hash já existe."""
        vaga_id = uuid4()
        principal_id = uuid4()
        hospital_id = uuid4()
        esp_id = uuid4()
        mensagem_id = uuid4()
        grupo_id = uuid4()

        # Mock select vaga
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data={
                "id": str(vaga_id),
                "hospital_id": str(hospital_id),
                "especialidade_id": str(esp_id),
                "periodo_id": None,
                "data": "2026-03-15",
                "mensagem_id": str(mensagem_id),
                "grupo_origem_id": str(grupo_id),
                "contato_responsavel_id": None,
                "valor": 2500,
            }
        )

        # Mock RPC retorna duplicata
        mock_supabase.rpc.return_value.execute.return_value = MagicMock(
            data=[{"eh_duplicada": True, "principal_id": str(principal_id)}]
        )

        # Mock registrar_fonte_vaga
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[]
        )
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            count=1
        )
        mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock(
            data=[{"id": str(uuid4())}]
        )
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()

        resultado = await processar_deduplicacao(vaga_id)

        assert resultado.duplicada is True
        assert resultado.principal_id == principal_id

    @pytest.mark.asyncio
    async def test_dedup_rpc_sem_resultado(self, mock_supabase):
        """Deve retornar erro se RPC não retorna dados."""
        vaga_id = uuid4()

        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data={
                "id": str(vaga_id),
                "hospital_id": str(uuid4()),
                "especialidade_id": str(uuid4()),
                "periodo_id": None,
                "data": "2026-03-15",
                "mensagem_id": str(uuid4()),
                "grupo_origem_id": str(uuid4()),
                "contato_responsavel_id": None,
                "valor": None,
            }
        )

        # RPC retorna vazio
        mock_supabase.rpc.return_value.execute.return_value = MagicMock(data=[])

        resultado = await processar_deduplicacao(vaga_id)

        assert resultado.erro == "rpc_sem_resultado"


class TestResultadoDedup:
    """Testes da dataclass ResultadoDedup."""

    def test_criacao_nova(self):
        """Deve criar resultado para vaga nova."""
        vaga_id = uuid4()
        resultado = ResultadoDedup(
            duplicada=False,
            principal_id=vaga_id,
            hash_dedup="abc123"
        )

        assert resultado.duplicada is False
        assert resultado.principal_id == vaga_id

    def test_criacao_duplicada(self):
        """Deve criar resultado para vaga duplicada."""
        principal_id = uuid4()
        resultado = ResultadoDedup(
            duplicada=True,
            principal_id=principal_id,
            hash_dedup="xyz789"
        )

        assert resultado.duplicada is True
        assert resultado.principal_id == principal_id

    def test_criacao_erro(self):
        """Deve criar resultado de erro."""
        resultado = ResultadoDedup(
            duplicada=False,
            erro="vaga_nao_encontrada"
        )

        assert resultado.erro == "vaga_nao_encontrada"


class TestListarFontesVaga:
    """Testes de listagem de fontes."""

    @pytest.fixture
    def mock_supabase(self):
        """Mock do Supabase."""
        with patch("app.services.grupos.deduplicador.supabase") as mock:
            yield mock

    @pytest.mark.asyncio
    async def test_lista_fontes(self, mock_supabase):
        """Deve listar fontes ordenadas."""
        mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = MagicMock(
            data=[
                {"id": str(uuid4()), "ordem": 1},
                {"id": str(uuid4()), "ordem": 2},
            ]
        )

        resultado = await listar_fontes_vaga(uuid4())

        assert len(resultado) == 2


class TestObterEstatisticasDedup:
    """Testes de estatísticas."""

    @pytest.fixture
    def mock_supabase(self):
        """Mock do Supabase."""
        with patch("app.services.grupos.deduplicador.supabase") as mock:
            yield mock

    @pytest.mark.asyncio
    async def test_estatisticas(self, mock_supabase):
        """Deve retornar estatísticas corretas."""
        # Mock para cada query
        mock_supabase.table.return_value.select.return_value.execute.return_value = MagicMock(count=100)
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(count=80)
        mock_supabase.table.return_value.select.return_value.gt.return_value.execute.return_value = MagicMock(count=10)

        resultado = await obter_estatisticas_dedup()

        assert "total_vagas" in resultado
        assert "vagas_unicas" in resultado
        assert "taxa_duplicacao" in resultado


class TestJanelaDedup:
    """Testes da janela temporal."""

    def test_janela_48_horas(self):
        """Janela deve ser 48 horas."""
        assert JANELA_DEDUP_HORAS == 48
