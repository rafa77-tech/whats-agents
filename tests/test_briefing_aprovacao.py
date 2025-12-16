"""
Testes do fluxo de aprovacao de briefings.

Sprint 11 - Epic 04: Fluxo de Aprovacao
"""
import pytest
import json
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.briefing_aprovacao import (
    StatusAprovacao,
    BriefingPendente,
    BriefingAprovacaoService,
    KEYWORDS_APROVACAO,
    KEYWORDS_CANCELAR,
    KEYWORDS_AJUSTE,
)
from app.services.briefing_analyzer import (
    AnaliseResult,
    TipoDemanda,
    PassoPlano,
)


class TestStatusAprovacao:
    """Testes do enum StatusAprovacao."""

    def test_status_existem(self):
        """Todos os status esperados existem."""
        assert StatusAprovacao.AGUARDANDO.value == "aguardando"
        assert StatusAprovacao.APROVADO.value == "aprovado"
        assert StatusAprovacao.AJUSTE_SOLICITADO.value == "ajuste"
        assert StatusAprovacao.DUVIDA.value == "duvida"
        assert StatusAprovacao.CANCELADO.value == "cancelado"
        assert StatusAprovacao.EXECUTANDO.value == "executando"
        assert StatusAprovacao.CONCLUIDO.value == "concluido"


class TestKeywords:
    """Testes das keywords de deteccao."""

    def test_keywords_aprovacao(self):
        """Keywords de aprovacao estao definidas."""
        assert "pode ir" in KEYWORDS_APROVACAO
        assert "sim" in KEYWORDS_APROVACAO
        assert "aprovado" in KEYWORDS_APROVACAO
        assert "go" in KEYWORDS_APROVACAO

    def test_keywords_cancelar(self):
        """Keywords de cancelamento estao definidas."""
        assert "cancela" in KEYWORDS_CANCELAR
        assert "para" in KEYWORDS_CANCELAR
        assert "esquece" in KEYWORDS_CANCELAR

    def test_keywords_ajuste(self):
        """Keywords de ajuste estao definidas."""
        assert "ajusta" in KEYWORDS_AJUSTE
        assert "muda" in KEYWORDS_AJUSTE
        assert "na verdade" in KEYWORDS_AJUSTE


class TestBriefingPendente:
    """Testes do dataclass BriefingPendente."""

    def test_cria_briefing_pendente(self):
        """Cria BriefingPendente corretamente."""
        plano = AnaliseResult(doc_id="doc1", doc_nome="teste")
        agora = datetime.now()

        briefing = BriefingPendente(
            id="bp1",
            doc_id="doc1",
            doc_nome="campanha-dezembro",
            doc_url="https://...",
            channel_id="C123",
            user_id="U456",
            plano=plano,
            status=StatusAprovacao.AGUARDANDO,
            criado_em=agora,
            atualizado_em=agora,
            expira_em=agora + timedelta(hours=24)
        )

        assert briefing.id == "bp1"
        assert briefing.doc_nome == "campanha-dezembro"
        assert briefing.status == StatusAprovacao.AGUARDANDO


class TestDetectarIntencao:
    """Testes da deteccao de intencao."""

    def setup_method(self):
        """Setup para cada teste."""
        self.service = BriefingAprovacaoService()

    def test_detecta_aprovacao_sim(self):
        """Detecta aprovacao com 'sim'."""
        assert self.service._detectar_intencao("sim") == StatusAprovacao.APROVADO

    def test_detecta_aprovacao_pode_ir(self):
        """Detecta aprovacao com 'pode ir'."""
        assert self.service._detectar_intencao("pode ir!") == StatusAprovacao.APROVADO

    def test_detecta_aprovacao_manda_ver(self):
        """Detecta aprovacao com 'manda ver'."""
        assert self.service._detectar_intencao("manda ver") == StatusAprovacao.APROVADO

    def test_detecta_cancelamento(self):
        """Detecta cancelamento."""
        assert self.service._detectar_intencao("cancela") == StatusAprovacao.CANCELADO
        assert self.service._detectar_intencao("esquece isso") == StatusAprovacao.CANCELADO

    def test_detecta_ajuste(self):
        """Detecta pedido de ajuste."""
        assert self.service._detectar_intencao("ajusta o passo 2") == StatusAprovacao.AJUSTE_SOLICITADO
        assert self.service._detectar_intencao("na verdade, muda o prazo") == StatusAprovacao.AJUSTE_SOLICITADO

    def test_detecta_duvida_com_pergunta(self):
        """Detecta duvida quando tem interrogacao."""
        assert self.service._detectar_intencao("quanto tempo vai levar?") == StatusAprovacao.DUVIDA

    def test_default_duvida(self):
        """Default eh duvida se nao detectar nada."""
        assert self.service._detectar_intencao("hmm interessante") == StatusAprovacao.DUVIDA

    def test_case_insensitive(self):
        """Deteccao eh case insensitive."""
        assert self.service._detectar_intencao("SIM") == StatusAprovacao.APROVADO
        assert self.service._detectar_intencao("CANCELA") == StatusAprovacao.CANCELADO


class TestBriefingAprovacaoService:
    """Testes do servico de aprovacao."""

    @pytest.mark.asyncio
    async def test_criar_pendente(self):
        """Cria briefing pendente no banco."""
        plano = AnaliseResult(
            doc_id="doc1",
            doc_nome="briefing-teste",
            resumo_demanda="Preencher vagas"
        )

        mock_result = MagicMock()
        mock_result.data = [{"id": "bp123"}]

        with patch("app.services.briefing_aprovacao.supabase") as mock_supabase:
            mock_supabase.table().insert().execute.return_value = mock_result

            service = BriefingAprovacaoService()
            briefing_id = await service.criar_pendente(
                doc_id="doc1",
                doc_nome="briefing-teste",
                doc_url="https://...",
                channel_id="C123",
                user_id="U456",
                plano=plano
            )

        assert briefing_id == "bp123"

    @pytest.mark.asyncio
    async def test_buscar_pendente_encontra(self):
        """Busca briefing pendente existente."""
        plano_dict = AnaliseResult(
            doc_id="doc1",
            doc_nome="teste",
            passos=[PassoPlano(numero=1, descricao="Passo")]
        ).to_dict()

        agora = datetime.now()
        mock_result = MagicMock()
        mock_result.data = [{
            "id": "bp1",
            "doc_id": "doc1",
            "doc_nome": "campanha-teste",
            "doc_url": "https://...",
            "channel_id": "C123",
            "user_id": "U456",
            "plano": json.dumps(plano_dict),
            "status": "aguardando",
            "criado_em": agora.isoformat(),
            "atualizado_em": agora.isoformat(),
            "expira_em": (agora + timedelta(hours=24)).isoformat(),
        }]

        with patch("app.services.briefing_aprovacao.supabase") as mock_supabase:
            mock_supabase.table().select().eq().eq().gt().order().limit().execute.return_value = mock_result

            service = BriefingAprovacaoService()
            briefing = await service.buscar_pendente("C123")

        assert briefing is not None
        assert briefing.id == "bp1"
        assert briefing.doc_nome == "campanha-teste"
        assert briefing.status == StatusAprovacao.AGUARDANDO

    @pytest.mark.asyncio
    async def test_buscar_pendente_nao_encontra(self):
        """Retorna None se nao houver pendente."""
        mock_result = MagicMock()
        mock_result.data = []

        with patch("app.services.briefing_aprovacao.supabase") as mock_supabase:
            mock_supabase.table().select().eq().eq().gt().order().limit().execute.return_value = mock_result

            service = BriefingAprovacaoService()
            briefing = await service.buscar_pendente("C123")

        assert briefing is None

    @pytest.mark.asyncio
    async def test_processar_resposta_aprovacao(self):
        """Processa aprovacao corretamente."""
        plano = AnaliseResult(doc_id="doc1", doc_nome="teste")
        briefing = BriefingPendente(
            id="bp1",
            doc_id="doc1",
            doc_nome="campanha",
            doc_url="https://...",
            channel_id="C123",
            user_id="U456",
            plano=plano,
            status=StatusAprovacao.AGUARDANDO,
            criado_em=datetime.now(),
            atualizado_em=datetime.now(),
            expira_em=datetime.now() + timedelta(hours=24)
        )

        with patch("app.services.briefing_aprovacao.supabase"):
            with patch("app.services.briefing_aprovacao.atualizar_secao_plano", new_callable=AsyncMock):
                with patch("app.services.briefing_aprovacao.adicionar_linha_historico", new_callable=AsyncMock):
                    service = BriefingAprovacaoService()
                    status, msg = await service.processar_resposta(briefing, "pode ir!")

        assert status == StatusAprovacao.APROVADO
        assert "comecar" in msg.lower() or "executar" in msg.lower()

    @pytest.mark.asyncio
    async def test_processar_resposta_cancelamento(self):
        """Processa cancelamento corretamente."""
        plano = AnaliseResult(doc_id="doc1", doc_nome="teste")
        briefing = BriefingPendente(
            id="bp1",
            doc_id="doc1",
            doc_nome="campanha",
            doc_url="https://...",
            channel_id="C123",
            user_id="U456",
            plano=plano,
            status=StatusAprovacao.AGUARDANDO,
            criado_em=datetime.now(),
            atualizado_em=datetime.now(),
            expira_em=datetime.now() + timedelta(hours=24)
        )

        with patch("app.services.briefing_aprovacao.supabase"):
            with patch("app.services.briefing_aprovacao.adicionar_linha_historico", new_callable=AsyncMock):
                service = BriefingAprovacaoService()
                status, msg = await service.processar_resposta(briefing, "cancela")

        assert status == StatusAprovacao.CANCELADO
        assert "cancel" in msg.lower()

    @pytest.mark.asyncio
    async def test_processar_resposta_ajuste(self):
        """Processa pedido de ajuste."""
        plano = AnaliseResult(doc_id="doc1", doc_nome="teste")
        briefing = BriefingPendente(
            id="bp1",
            doc_id="doc1",
            doc_nome="campanha",
            doc_url="https://...",
            channel_id="C123",
            user_id="U456",
            plano=plano,
            status=StatusAprovacao.AGUARDANDO,
            criado_em=datetime.now(),
            atualizado_em=datetime.now(),
            expira_em=datetime.now() + timedelta(hours=24)
        )

        with patch("app.services.briefing_aprovacao.adicionar_linha_historico", new_callable=AsyncMock):
            service = BriefingAprovacaoService()
            status, msg = await service.processar_resposta(briefing, "ajusta o passo 3")

        assert status == StatusAprovacao.AJUSTE_SOLICITADO
        assert "ajuste" in msg.lower() or "mudar" in msg.lower()

    @pytest.mark.asyncio
    async def test_processar_resposta_duvida(self):
        """Processa duvida."""
        plano = AnaliseResult(doc_id="doc1", doc_nome="teste")
        briefing = BriefingPendente(
            id="bp1",
            doc_id="doc1",
            doc_nome="campanha",
            doc_url="https://...",
            channel_id="C123",
            user_id="U456",
            plano=plano,
            status=StatusAprovacao.AGUARDANDO,
            criado_em=datetime.now(),
            atualizado_em=datetime.now(),
            expira_em=datetime.now() + timedelta(hours=24)
        )

        service = BriefingAprovacaoService()
        status, msg = await service.processar_resposta(briefing, "quanto tempo vai levar?")

        assert status == StatusAprovacao.DUVIDA
        assert "ajudar" in msg.lower() or "perguntar" in msg.lower()


class TestProcessarBriefingCompleto:
    """Testes da funcao processar_briefing_completo."""

    @pytest.mark.asyncio
    async def test_fluxo_completo(self):
        """Testa fluxo completo de processamento."""
        analise = AnaliseResult(
            doc_id="doc1",
            doc_nome="briefing-teste",
            resumo_demanda="Preencher vagas",
            passos=[PassoPlano(numero=1, descricao="Buscar")]
        )

        # Mock do analyzer
        with patch("app.services.briefing_aprovacao.analisar_briefing", new_callable=AsyncMock) as mock_analisar:
            mock_analisar.return_value = analise

            # Mock da escrita no doc
            with patch("app.services.briefing_aprovacao.atualizar_secao_plano", new_callable=AsyncMock):
                # Mock do service
                with patch.object(BriefingAprovacaoService, "criar_pendente", new_callable=AsyncMock) as mock_criar:
                    mock_criar.return_value = "bp123"

                    from app.services.briefing_aprovacao import processar_briefing_completo
                    briefing_id, mensagem = await processar_briefing_completo(
                        doc_id="doc1",
                        doc_nome="briefing-teste",
                        conteudo="Preciso preencher 5 vagas...",
                        doc_url="https://...",
                        channel_id="C123",
                        user_id="U456"
                    )

        assert briefing_id == "bp123"
        assert "briefing-teste" in mensagem


class TestDictParaAnalise:
    """Testes da conversao de dict para AnaliseResult."""

    def test_converte_dict_basico(self):
        """Converte dict basico."""
        data = {
            "doc_id": "doc1",
            "doc_nome": "teste",
            "timestamp": "2025-12-15T14:30:00",
            "resumo_demanda": "Preencher vagas",
            "tipo_demanda": "operacional",
            "deadline": None,
            "urgencia": "alta",
            "dados_disponiveis": ["contatos"],
            "dados_faltantes": [],
            "ferramentas_necessarias": [],
            "ferramentas_faltantes": [],
            "perguntas_para_gestor": [],
            "passos": [],
            "metricas_sucesso": [],
            "riscos": [],
            "necessidades": [],
            "viavel": True,
            "ressalvas": [],
            "avaliacao_honesta": "OK"
        }

        service = BriefingAprovacaoService()
        resultado = service._dict_para_analise(data)

        assert resultado.doc_id == "doc1"
        assert resultado.resumo_demanda == "Preencher vagas"
        assert resultado.tipo_demanda == TipoDemanda.OPERACIONAL

    def test_converte_dict_com_passos(self):
        """Converte dict com passos."""
        data = {
            "doc_id": "doc1",
            "doc_nome": "teste",
            "passos": [
                {"numero": 1, "descricao": "Passo 1", "prazo": "amanha", "requer_ajuda": False, "tipo_ajuda": None},
                {"numero": 2, "descricao": "Passo 2", "prazo": None, "requer_ajuda": True, "tipo_ajuda": "ferramenta"},
            ],
            "tipo_demanda": "mapeamento",
            "necessidades": [],
            "dados_disponiveis": [],
            "dados_faltantes": [],
            "ferramentas_necessarias": [],
            "ferramentas_faltantes": [],
            "perguntas_para_gestor": [],
            "metricas_sucesso": [],
            "riscos": [],
            "ressalvas": [],
        }

        service = BriefingAprovacaoService()
        resultado = service._dict_para_analise(data)

        assert len(resultado.passos) == 2
        assert resultado.passos[0].descricao == "Passo 1"
        assert resultado.passos[1].requer_ajuda is True

    def test_tipo_invalido_usa_default(self):
        """Tipo invalido usa OPERACIONAL como default."""
        data = {
            "doc_id": "doc1",
            "doc_nome": "teste",
            "tipo_demanda": "tipo_invalido",
            "passos": [],
            "necessidades": [],
        }

        service = BriefingAprovacaoService()
        resultado = service._dict_para_analise(data)

        assert resultado.tipo_demanda == TipoDemanda.OPERACIONAL
