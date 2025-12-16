"""
Testes do BriefingAnalyzer.

Sprint 11 - Epic 02: Analise Inteligente
"""
import pytest
import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.briefing_analyzer import (
    TipoDemanda,
    PassoPlano,
    NecessidadeIdentificada,
    AnaliseResult,
    BriefingAnalyzer,
    formatar_plano_para_documento,
    formatar_plano_para_slack,
    analisar_briefing,
    PROMPT_ANALISE,
)


class TestTipoDemanda:
    """Testes do enum TipoDemanda."""

    def test_tipos_existem(self):
        """Todos os tipos esperados existem."""
        assert TipoDemanda.OPERACIONAL.value == "operacional"
        assert TipoDemanda.MAPEAMENTO.value == "mapeamento"
        assert TipoDemanda.EXPANSAO.value == "expansao"
        assert TipoDemanda.INTELIGENCIA.value == "inteligencia"
        assert TipoDemanda.NOVO_TERRITORIO.value == "novo_territorio"
        assert TipoDemanda.MISTO.value == "misto"

    def test_tipo_from_string(self):
        """Converte string para enum."""
        assert TipoDemanda("operacional") == TipoDemanda.OPERACIONAL
        assert TipoDemanda("misto") == TipoDemanda.MISTO


class TestPassoPlano:
    """Testes do dataclass PassoPlano."""

    def test_passo_basico(self):
        """Cria passo basico."""
        passo = PassoPlano(numero=1, descricao="Fazer algo")
        assert passo.numero == 1
        assert passo.descricao == "Fazer algo"
        assert passo.prazo is None
        assert passo.requer_ajuda is False

    def test_passo_completo(self):
        """Cria passo com todos os campos."""
        passo = PassoPlano(
            numero=2,
            descricao="Tarefa complexa",
            prazo="ate sexta",
            requer_ajuda=True,
            tipo_ajuda="ferramenta"
        )
        assert passo.requer_ajuda is True
        assert passo.tipo_ajuda == "ferramenta"


class TestNecessidadeIdentificada:
    """Testes do dataclass NecessidadeIdentificada."""

    def test_necessidade_basica(self):
        """Cria necessidade basica."""
        nec = NecessidadeIdentificada(
            tipo="dados",
            descricao="Lista de contatos",
            caso_uso="Para enviar mensagens"
        )
        assert nec.tipo == "dados"
        assert nec.prioridade == "media"  # default
        assert nec.alternativa_temporaria is None

    def test_necessidade_completa(self):
        """Cria necessidade com todos os campos."""
        nec = NecessidadeIdentificada(
            tipo="ferramenta",
            descricao="API de email",
            caso_uso="Enviar confirmacoes",
            alternativa_temporaria="Fazer manualmente",
            prioridade="alta"
        )
        assert nec.prioridade == "alta"
        assert nec.alternativa_temporaria == "Fazer manualmente"


class TestAnaliseResult:
    """Testes do dataclass AnaliseResult."""

    def test_analise_minima(self):
        """Cria analise com campos minimos."""
        analise = AnaliseResult(
            doc_id="doc1",
            doc_nome="briefing-teste"
        )
        assert analise.doc_id == "doc1"
        assert analise.tipo_demanda == TipoDemanda.OPERACIONAL  # default
        assert analise.viavel is True  # default
        assert analise.passos == []

    def test_analise_completa(self):
        """Cria analise completa."""
        passos = [PassoPlano(numero=1, descricao="Passo 1")]
        necessidades = [NecessidadeIdentificada(
            tipo="dados", descricao="X", caso_uso="Y"
        )]

        analise = AnaliseResult(
            doc_id="doc1",
            doc_nome="briefing-teste",
            resumo_demanda="Preencher vagas urgentes",
            tipo_demanda=TipoDemanda.OPERACIONAL,
            deadline="sexta",
            urgencia="alta",
            dados_disponiveis=["contatos", "vagas"],
            dados_faltantes=["preferencias"],
            ferramentas_necessarias=["enviar_mensagem"],
            ferramentas_faltantes=["enviar_email"],
            perguntas_para_gestor=["Qual o horario limite?"],
            passos=passos,
            metricas_sucesso=["80% de vagas preenchidas"],
            riscos=["Feriado pode atrasar"],
            necessidades=necessidades,
            viavel=True,
            ressalvas=["Depende de resposta rapida"],
            avaliacao_honesta="Acho que da pra fazer"
        )

        assert analise.urgencia == "alta"
        assert len(analise.passos) == 1
        assert "contatos" in analise.dados_disponiveis

    def test_to_dict(self):
        """Converte para dicionario."""
        analise = AnaliseResult(
            doc_id="doc1",
            doc_nome="briefing-teste",
            tipo_demanda=TipoDemanda.MAPEAMENTO
        )

        d = analise.to_dict()
        assert d["doc_id"] == "doc1"
        assert d["tipo_demanda"] == "mapeamento"  # string, nao enum
        assert isinstance(d["passos"], list)


class TestFormatarPlanoParaDocumento:
    """Testes da funcao formatar_plano_para_documento."""

    def test_formata_plano_basico(self):
        """Formata plano basico."""
        analise = AnaliseResult(
            doc_id="doc1",
            doc_nome="briefing-teste",
            resumo_demanda="Preencher 5 vagas",
            tipo_demanda=TipoDemanda.OPERACIONAL,
            urgencia="alta",
            passos=[
                PassoPlano(numero=1, descricao="Buscar medicos"),
                PassoPlano(numero=2, descricao="Enviar mensagens"),
            ],
            viavel=True,
            avaliacao_honesta="Acho viavel"
        )

        resultado = formatar_plano_para_documento(analise)

        assert "## Plano da Julia" in resultado
        assert "Preencher 5 vagas" in resultado
        assert "operacional" in resultado
        assert "alta" in resultado
        assert "Buscar medicos" in resultado
        assert "Enviar mensagens" in resultado
        assert "Viavel" in resultado
        assert "Acho viavel" in resultado

    def test_formata_plano_com_perguntas(self):
        """Formata plano com perguntas para gestor."""
        analise = AnaliseResult(
            doc_id="doc1",
            doc_nome="briefing-teste",
            resumo_demanda="Teste",
            perguntas_para_gestor=[
                "Qual o prazo?",
                "Posso oferecer desconto?"
            ]
        )

        resultado = formatar_plano_para_documento(analise)

        assert "Perguntas para voce" in resultado
        assert "Qual o prazo?" in resultado

    def test_formata_plano_com_necessidades(self):
        """Formata plano com necessidades identificadas."""
        analise = AnaliseResult(
            doc_id="doc1",
            doc_nome="briefing-teste",
            resumo_demanda="Teste",
            necessidades=[
                NecessidadeIdentificada(
                    tipo="ferramenta",
                    descricao="API de email",
                    caso_uso="Confirmar reservas",
                    prioridade="alta"
                )
            ]
        )

        resultado = formatar_plano_para_documento(analise)

        assert "Necessidades identificadas" in resultado
        assert "ferramenta" in resultado
        assert "API de email" in resultado

    def test_formata_plano_nao_viavel(self):
        """Formata plano nao viavel."""
        analise = AnaliseResult(
            doc_id="doc1",
            doc_nome="briefing-teste",
            resumo_demanda="Missao impossivel",
            viavel=False,
            ressalvas=["Prazo muito curto", "Dados insuficientes"],
            avaliacao_honesta="Nao da pra fazer nesse prazo"
        )

        resultado = formatar_plano_para_documento(analise)

        assert "Dificil/Impossivel" in resultado
        assert "Prazo muito curto" in resultado


class TestFormatarPlanoParaSlack:
    """Testes da funcao formatar_plano_para_slack."""

    def test_formata_resumido(self):
        """Formata resumo para Slack."""
        analise = AnaliseResult(
            doc_id="doc1",
            doc_nome="campanha-dezembro",
            resumo_demanda="Preencher 10 vagas no Sao Luiz",
            passos=[
                PassoPlano(numero=1, descricao="Buscar anestesistas"),
                PassoPlano(numero=2, descricao="Filtrar por regiao"),
                PassoPlano(numero=3, descricao="Enviar ofertas"),
            ]
        )

        resultado = formatar_plano_para_slack(analise, "https://doc.url")

        assert "campanha-dezembro" in resultado
        assert "Preencher 10 vagas" in resultado
        assert "Buscar anestesistas" in resultado
        assert "https://doc.url" in resultado

    def test_limita_5_passos(self):
        """Limita a 5 passos no Slack."""
        passos = [PassoPlano(numero=i, descricao=f"Passo {i}") for i in range(1, 10)]

        analise = AnaliseResult(
            doc_id="doc1",
            doc_nome="briefing",
            resumo_demanda="Teste",
            passos=passos
        )

        resultado = formatar_plano_para_slack(analise, "https://doc.url")

        assert "Passo 5" in resultado
        assert "Passo 6" not in resultado
        assert "mais" in resultado.lower()  # "...e mais X passos"

    def test_mostra_perguntas(self):
        """Mostra perguntas se houver."""
        analise = AnaliseResult(
            doc_id="doc1",
            doc_nome="briefing",
            resumo_demanda="Teste",
            perguntas_para_gestor=["Posso comecar amanha?"]
        )

        resultado = formatar_plano_para_slack(analise, "https://...")

        assert "confirmar" in resultado.lower()
        assert "amanha" in resultado

    def test_avisa_nao_viavel(self):
        """Avisa quando nao viavel."""
        analise = AnaliseResult(
            doc_id="doc1",
            doc_nome="briefing",
            resumo_demanda="Teste",
            viavel=False,
            ressalvas=["Prazo impossivel"]
        )

        resultado = formatar_plano_para_slack(analise, "https://...")

        assert "atencao" in resultado.lower()
        assert "Prazo impossivel" in resultado


class TestPromptAnalise:
    """Testes do prompt de analise."""

    def test_prompt_tem_placeholders(self):
        """Prompt tem placeholders para contexto e briefing."""
        assert "{dados_contexto}" in PROMPT_ANALISE
        assert "{briefing_content}" in PROMPT_ANALISE

    def test_prompt_menciona_ferramentas(self):
        """Prompt menciona ferramentas disponiveis."""
        assert "WhatsApp" in PROMPT_ANALISE
        assert "medicos" in PROMPT_ANALISE.lower()
        assert "vagas" in PROMPT_ANALISE.lower()

    def test_prompt_pede_json(self):
        """Prompt pede resposta em JSON."""
        assert "JSON" in PROMPT_ANALISE
        assert '"resumo_demanda"' in PROMPT_ANALISE


class TestBriefingAnalyzerIntegration:
    """Testes de integracao do BriefingAnalyzer (com mocks)."""

    @pytest.mark.asyncio
    async def test_analise_parseia_resposta_json(self):
        """Analise parseia resposta JSON do LLM."""
        resposta_llm = json.dumps({
            "resumo_demanda": "Preencher vagas urgentes",
            "tipo_demanda": "operacional",
            "deadline": "sexta",
            "urgencia": "alta",
            "dados_disponiveis": ["contatos"],
            "dados_faltantes": [],
            "ferramentas_necessarias": ["enviar_mensagem"],
            "ferramentas_faltantes": [],
            "perguntas_para_gestor": [],
            "passos": [
                {"numero": 1, "descricao": "Buscar medicos", "prazo": None, "requer_ajuda": False, "tipo_ajuda": None}
            ],
            "metricas_sucesso": ["80% preenchidas"],
            "riscos": [],
            "necessidades": [],
            "viavel": True,
            "ressalvas": [],
            "avaliacao_honesta": "Viavel"
        })

        # Mock do cliente Anthropic
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=resposta_llm)]

        with patch.object(BriefingAnalyzer, "__init__", lambda x: None):
            analyzer = BriefingAnalyzer()
            analyzer.client = MagicMock()
            analyzer.client.messages.create.return_value = mock_response
            analyzer.model = "claude-3-haiku"

            # Mock do contexto
            with patch("app.services.briefing_analyzer._buscar_dados_contexto", new_callable=AsyncMock) as mock_ctx:
                mock_ctx.return_value = "- Total: 100 medicos"

                resultado = await analyzer.analisar("doc1", "briefing", "Preciso preencher vagas")

        assert resultado.resumo_demanda == "Preencher vagas urgentes"
        assert resultado.tipo_demanda == TipoDemanda.OPERACIONAL
        assert resultado.urgencia == "alta"
        assert len(resultado.passos) == 1
        assert resultado.viavel is True

    @pytest.mark.asyncio
    async def test_analise_trata_json_com_markdown(self):
        """Analise trata JSON envolvido em markdown."""
        resposta_llm = """```json
{
    "resumo_demanda": "Teste",
    "tipo_demanda": "mapeamento",
    "viavel": true,
    "passos": [],
    "dados_disponiveis": [],
    "dados_faltantes": [],
    "ferramentas_necessarias": [],
    "ferramentas_faltantes": [],
    "perguntas_para_gestor": [],
    "metricas_sucesso": [],
    "riscos": [],
    "necessidades": [],
    "ressalvas": [],
    "avaliacao_honesta": "OK"
}
```"""

        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=resposta_llm)]

        with patch.object(BriefingAnalyzer, "__init__", lambda x: None):
            analyzer = BriefingAnalyzer()
            analyzer.client = MagicMock()
            analyzer.client.messages.create.return_value = mock_response
            analyzer.model = "claude-3-haiku"

            with patch("app.services.briefing_analyzer._buscar_dados_contexto", new_callable=AsyncMock) as mock_ctx:
                mock_ctx.return_value = "- Contexto"

                resultado = await analyzer.analisar("doc1", "briefing", "Conteudo")

        assert resultado.resumo_demanda == "Teste"
        assert resultado.tipo_demanda == TipoDemanda.MAPEAMENTO

    @pytest.mark.asyncio
    async def test_analise_erro_retorna_resultado_erro(self):
        """Erro na analise retorna resultado com erro."""
        with patch.object(BriefingAnalyzer, "__init__", lambda x: None):
            analyzer = BriefingAnalyzer()
            analyzer.client = MagicMock()
            analyzer.client.messages.create.side_effect = Exception("API Error")
            analyzer.model = "claude-3-haiku"

            with patch("app.services.briefing_analyzer._buscar_dados_contexto", new_callable=AsyncMock) as mock_ctx:
                mock_ctx.return_value = "- Contexto"

                resultado = await analyzer.analisar("doc1", "briefing", "Conteudo")

        assert "Erro" in resultado.resumo_demanda
        assert resultado.viavel is False


class TestAnalisarBriefingConvenience:
    """Testes da funcao de conveniencia analisar_briefing."""

    @pytest.mark.asyncio
    async def test_funcao_conveniencia(self):
        """Funcao de conveniencia usa singleton."""
        with patch("app.services.briefing_analyzer.get_analyzer") as mock_get:
            mock_analyzer = AsyncMock()
            mock_analyzer.analisar.return_value = AnaliseResult(
                doc_id="doc1",
                doc_nome="teste"
            )
            mock_get.return_value = mock_analyzer

            resultado = await analisar_briefing("doc1", "teste", "conteudo")

            mock_analyzer.analisar.assert_called_once_with("doc1", "teste", "conteudo")
            assert resultado.doc_id == "doc1"
