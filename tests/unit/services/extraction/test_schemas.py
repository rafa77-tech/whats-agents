"""
Testes para schemas do servico de extracao.

Sprint 53: Discovery Intelligence Pipeline.
"""

import pytest
from app.services.extraction.schemas import (
    ExtractionContext,
    ExtractionResult,
    Interesse,
    ProximoPasso,
    TipoObjecao,
    SeveridadeObjecao,
    Objecao,
)


class TestExtractionContext:
    """Testes para ExtractionContext."""

    def test_create_context_minimal(self):
        """Contexto minimo valido."""
        ctx = ExtractionContext(
            mensagem_medico="Oi, tenho interesse",
            resposta_julia="Otimo! Me conta mais",
            nome_medico="Dr. Teste",
        )
        assert ctx.mensagem_medico == "Oi, tenho interesse"
        assert ctx.resposta_julia == "Otimo! Me conta mais"
        assert ctx.nome_medico == "Dr. Teste"
        assert ctx.especialidade_cadastrada is None
        assert ctx.campanha_id is None

    def test_create_context_full(self):
        """Contexto completo."""
        ctx = ExtractionContext(
            mensagem_medico="Oi, tenho interesse em vagas no RJ",
            resposta_julia="Otimo! Temos varias opcoes",
            nome_medico="Dr. Carlos",
            especialidade_cadastrada="Cardiologia",
            regiao_cadastrada="Sao Paulo",
            campanha_id=19,
            tipo_campanha="discovery",
            conversa_id="uuid-123",
            cliente_id="uuid-456",
        )
        assert ctx.campanha_id == 19
        assert ctx.tipo_campanha == "discovery"
        assert ctx.especialidade_cadastrada == "Cardiologia"


class TestExtractionResult:
    """Testes para ExtractionResult."""

    def test_interesse_positivo(self):
        """Interesse positivo com score alto."""
        result = ExtractionResult(
            interesse=Interesse.POSITIVO,
            interesse_score=0.85,
            proximo_passo=ProximoPasso.ENVIAR_VAGAS,
            confianca=0.9,
        )
        assert result.interesse == Interesse.POSITIVO
        assert result.interesse_score > 0.8
        assert result.proximo_passo == ProximoPasso.ENVIAR_VAGAS

    def test_interesse_negativo(self):
        """Interesse negativo com objecao."""
        result = ExtractionResult(
            interesse=Interesse.NEGATIVO,
            interesse_score=0.2,
            objecao=Objecao(
                tipo=TipoObjecao.EMPRESA_ATUAL,
                descricao="Ja trabalho com outra empresa",
                severidade=SeveridadeObjecao.ALTA,
            ),
            proximo_passo=ProximoPasso.MARCAR_INATIVO,
            confianca=0.8,
        )
        assert result.interesse == Interesse.NEGATIVO
        assert result.objecao is not None
        assert result.objecao.tipo == TipoObjecao.EMPRESA_ATUAL
        assert result.objecao.severidade == SeveridadeObjecao.ALTA

    def test_to_dict(self):
        """Serializacao para dicionario."""
        result = ExtractionResult(
            interesse=Interesse.POSITIVO,
            interesse_score=0.8,
            especialidade_mencionada="Cardiologia",
            preferencias=["plantoes noturnos"],
            proximo_passo=ProximoPasso.ENVIAR_VAGAS,
            confianca=0.9,
        )
        data = result.to_dict()

        assert data["interesse"] == "positivo"
        assert data["interesse_score"] == 0.8
        assert data["especialidade_mencionada"] == "Cardiologia"
        assert data["preferencias"] == ["plantoes noturnos"]
        assert data["proximo_passo"] == "enviar_vagas"
        assert data["objecao"] is None

    def test_to_dict_with_objecao(self):
        """Serializacao com objecao."""
        result = ExtractionResult(
            interesse=Interesse.NEGATIVO,
            interesse_score=0.2,
            objecao=Objecao(
                tipo=TipoObjecao.PRECO,
                descricao="Muito caro",
                severidade=SeveridadeObjecao.MEDIA,
            ),
            proximo_passo=ProximoPasso.AGENDAR_FOLLOWUP,
            confianca=0.7,
        )
        data = result.to_dict()

        assert data["objecao"] is not None
        assert data["objecao"]["tipo"] == "preco"
        assert data["objecao"]["descricao"] == "Muito caro"
        assert data["objecao"]["severidade"] == "media"

    def test_from_dict(self):
        """Desserializacao de dicionario."""
        data = {
            "interesse": "positivo",
            "interesse_score": 0.85,
            "especialidade_mencionada": "Pediatria",
            "regiao_mencionada": "Rio de Janeiro",
            "preferencias": ["fins de semana"],
            "restricoes": ["nao faco noturno"],
            "proximo_passo": "enviar_vagas",
            "confianca": 0.9,
        }
        result = ExtractionResult.from_dict(data)

        assert result.interesse == Interesse.POSITIVO
        assert result.interesse_score == 0.85
        assert result.especialidade_mencionada == "Pediatria"
        assert result.regiao_mencionada == "Rio de Janeiro"
        assert "fins de semana" in result.preferencias
        assert "nao faco noturno" in result.restricoes

    def test_from_dict_with_objecao(self):
        """Desserializacao com objecao."""
        data = {
            "interesse": "negativo",
            "interesse_score": 0.1,
            "objecao": {
                "tipo": "distancia",
                "descricao": "Muito longe",
                "severidade": "alta",
            },
            "proximo_passo": "marcar_inativo",
            "confianca": 0.8,
        }
        result = ExtractionResult.from_dict(data)

        assert result.objecao is not None
        assert result.objecao.tipo == TipoObjecao.DISTANCIA
        assert result.objecao.severidade == SeveridadeObjecao.ALTA

    def test_from_dict_defaults(self):
        """Desserializacao com valores default."""
        data = {}
        result = ExtractionResult.from_dict(data)

        assert result.interesse == Interesse.INCERTO
        assert result.interesse_score == 0.5
        assert result.proximo_passo == ProximoPasso.SEM_ACAO
        assert result.preferencias == []
        assert result.restricoes == []


class TestEnums:
    """Testes para enums."""

    def test_interesse_values(self):
        """Valores de interesse."""
        assert Interesse.POSITIVO.value == "positivo"
        assert Interesse.NEGATIVO.value == "negativo"
        assert Interesse.NEUTRO.value == "neutro"
        assert Interesse.INCERTO.value == "incerto"

    def test_proximo_passo_values(self):
        """Valores de proximo passo."""
        assert ProximoPasso.ENVIAR_VAGAS.value == "enviar_vagas"
        assert ProximoPasso.AGENDAR_FOLLOWUP.value == "agendar_followup"
        assert ProximoPasso.AGUARDAR_RESPOSTA.value == "aguardar_resposta"
        assert ProximoPasso.ESCALAR_HUMANO.value == "escalar_humano"
        assert ProximoPasso.MARCAR_INATIVO.value == "marcar_inativo"
        assert ProximoPasso.SEM_ACAO.value == "sem_acao"

    def test_tipo_objecao_values(self):
        """Valores de tipo de objecao."""
        assert TipoObjecao.PRECO.value == "preco"
        assert TipoObjecao.TEMPO.value == "tempo"
        assert TipoObjecao.CONFIANCA.value == "confianca"
        assert TipoObjecao.DISTANCIA.value == "distancia"
        assert TipoObjecao.DISPONIBILIDADE.value == "disponibilidade"
        assert TipoObjecao.EMPRESA_ATUAL.value == "empresa_atual"
        assert TipoObjecao.PESSOAL.value == "pessoal"
        assert TipoObjecao.OUTRO.value == "outro"

    def test_severidade_values(self):
        """Valores de severidade."""
        assert SeveridadeObjecao.BAIXA.value == "baixa"
        assert SeveridadeObjecao.MEDIA.value == "media"
        assert SeveridadeObjecao.ALTA.value == "alta"
