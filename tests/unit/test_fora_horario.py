"""
Testes unitarios para fora_horario.py

Sprint 22 - Responsividade Inteligente
"""
import pytest
from datetime import datetime, time, timedelta
from unittest.mock import patch, AsyncMock

from app.services.fora_horario import (
    eh_horario_comercial,
    proximo_horario_comercial,
    selecionar_template_ack,
    verificar_ack_recente,
    pode_responder_fora_horario,
    ACK_TEMPLATES,
    TZ_BRASIL,
    HORARIO_INICIO,
    HORARIO_FIM,
)
from app.services.message_context_classifier import ContextType, ContextClassification


class TestEhHorarioComercial:
    """Testes de verificacao de horario comercial."""

    def test_dia_util_dentro_horario(self):
        """Dia util dentro do horario deve retornar True."""
        # Terca 10:00
        dt = datetime(2025, 12, 30, 10, 0, tzinfo=TZ_BRASIL)
        assert eh_horario_comercial(dt) is True

    def test_dia_util_antes_horario(self):
        """Dia util antes do horario deve retornar False."""
        # Terca 07:00
        dt = datetime(2025, 12, 30, 7, 0, tzinfo=TZ_BRASIL)
        assert eh_horario_comercial(dt) is False

    def test_dia_util_apos_horario(self):
        """Dia util apos o horario deve retornar False."""
        # Terca 21:00
        dt = datetime(2025, 12, 30, 21, 0, tzinfo=TZ_BRASIL)
        assert eh_horario_comercial(dt) is False

    def test_sabado(self):
        """Sabado deve retornar False."""
        # Sabado 10:00
        dt = datetime(2025, 12, 27, 10, 0, tzinfo=TZ_BRASIL)
        assert eh_horario_comercial(dt) is False

    def test_domingo(self):
        """Domingo deve retornar False."""
        # Domingo 10:00
        dt = datetime(2025, 12, 28, 10, 0, tzinfo=TZ_BRASIL)
        assert eh_horario_comercial(dt) is False

    def test_limite_inicio(self):
        """08:00 exato deve estar dentro do horario."""
        dt = datetime(2025, 12, 30, 8, 0, tzinfo=TZ_BRASIL)
        assert eh_horario_comercial(dt) is True

    def test_limite_fim(self):
        """20:00 exato deve estar dentro do horario."""
        dt = datetime(2025, 12, 30, 20, 0, tzinfo=TZ_BRASIL)
        assert eh_horario_comercial(dt) is True


class TestProximoHorarioComercial:
    """Testes de calculo do proximo horario comercial."""

    def test_durante_horario_comercial(self):
        """Durante horario comercial, retorna agora."""
        dt = datetime(2025, 12, 30, 10, 0, tzinfo=TZ_BRASIL)
        proximo = proximo_horario_comercial(dt)
        assert proximo == dt

    def test_antes_horario_dia_util(self):
        """Antes do horario em dia util, retorna 08:00 do mesmo dia."""
        dt = datetime(2025, 12, 30, 6, 0, tzinfo=TZ_BRASIL)
        proximo = proximo_horario_comercial(dt)
        assert proximo.hour == 8
        assert proximo.minute == 0
        assert proximo.date() == dt.date()

    def test_apos_horario_dia_util(self):
        """Apos horario em dia util, retorna 08:00 do proximo dia util."""
        dt = datetime(2025, 12, 30, 21, 0, tzinfo=TZ_BRASIL)
        proximo = proximo_horario_comercial(dt)
        assert proximo.hour == 8
        assert proximo.minute == 0
        assert proximo.date() == dt.date() + timedelta(days=1)

    def test_sexta_a_noite(self):
        """Sexta a noite, retorna segunda 08:00."""
        # Sexta 21:00
        dt = datetime(2025, 12, 26, 21, 0, tzinfo=TZ_BRASIL)
        proximo = proximo_horario_comercial(dt)
        assert proximo.weekday() == 0  # Segunda
        assert proximo.hour == 8

    def test_sabado(self):
        """Sabado, retorna segunda 08:00."""
        dt = datetime(2025, 12, 27, 12, 0, tzinfo=TZ_BRASIL)
        proximo = proximo_horario_comercial(dt)
        assert proximo.weekday() == 0  # Segunda
        assert proximo.hour == 8


class TestSelecionarTemplateAck:
    """Testes de selecao de template de ack."""

    def test_template_vaga_por_contexto(self):
        """Contexto com oferta_pendente deve selecionar template vaga."""
        classificacao = ContextClassification(
            tipo=ContextType.REPLY_DIRETA,
            prioridade=1,
            confianca=0.9,
            razao="teste"
        )
        template = selecionar_template_ack(
            classificacao,
            contexto={"oferta_pendente": True}
        )
        assert template.tipo == "vaga"

    def test_template_aceite_vaga(self):
        """Classificacao ACEITE_VAGA deve selecionar template aceite_vaga (sem prometer reserva)."""
        classificacao = ContextClassification(
            tipo=ContextType.ACEITE_VAGA,
            prioridade=1,
            confianca=0.9,
            razao="teste"
        )
        template = selecionar_template_ack(classificacao)
        assert template.tipo == "aceite_vaga"
        # Verifica que template NAO promete reserva
        assert "garantir" in template.mensagem.lower() or "reserva" in template.mensagem.lower()

    def test_template_confirmacao(self):
        """Classificacao CONFIRMACAO deve selecionar template confirmacao."""
        classificacao = ContextClassification(
            tipo=ContextType.CONFIRMACAO,
            prioridade=1,
            confianca=0.9,
            razao="teste"
        )
        template = selecionar_template_ack(classificacao)
        assert template.tipo == "confirmacao"

    def test_template_generico_default(self):
        """Sem contexto especifico, seleciona template generico."""
        classificacao = ContextClassification(
            tipo=ContextType.REPLY_DIRETA,
            prioridade=1,
            confianca=0.9,
            razao="teste"
        )
        template = selecionar_template_ack(classificacao)
        assert template.tipo == "generico"


class TestPodeResponderForaHorario:
    """Testes de permissao de ack fora do horario."""

    def test_reply_direta_pode(self):
        """REPLY_DIRETA pode receber ack."""
        classificacao = ContextClassification(
            tipo=ContextType.REPLY_DIRETA,
            prioridade=1,
            confianca=0.9,
            razao="teste"
        )
        assert pode_responder_fora_horario(classificacao) is True

    def test_aceite_vaga_pode(self):
        """ACEITE_VAGA pode receber ack."""
        classificacao = ContextClassification(
            tipo=ContextType.ACEITE_VAGA,
            prioridade=1,
            confianca=0.9,
            razao="teste"
        )
        assert pode_responder_fora_horario(classificacao) is True

    def test_campanha_fria_nao_pode(self):
        """CAMPANHA_FRIA nao deve receber ack (nao faz sentido)."""
        classificacao = ContextClassification(
            tipo=ContextType.CAMPANHA_FRIA,
            prioridade=5,
            confianca=0.9,
            razao="teste"
        )
        assert pode_responder_fora_horario(classificacao) is False


class TestAckCeiling:
    """Testes do ceiling de ack (Ajuste B)."""

    @pytest.mark.asyncio
    @patch("app.services.fora_horario.supabase")
    async def test_sem_ack_recente(self, mock_supabase):
        """Sem ack recente, deve retornar False."""
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.gte.return_value.limit.return_value.execute.return_value.data = []

        resultado = await verificar_ack_recente("cliente-123")
        assert resultado is False

    @pytest.mark.asyncio
    @patch("app.services.fora_horario.supabase")
    async def test_com_ack_recente(self, mock_supabase):
        """Com ack recente, deve retornar True."""
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.gte.return_value.limit.return_value.execute.return_value.data = [
            {"id": "ack-123", "ack_enviado_em": datetime.now().isoformat()}
        ]

        resultado = await verificar_ack_recente("cliente-123")
        assert resultado is True

    @pytest.mark.asyncio
    @patch("app.services.fora_horario.supabase")
    async def test_erro_permite_ack(self, mock_supabase):
        """Em caso de erro, permite ack (fail open)."""
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.gte.return_value.limit.return_value.execute.side_effect = Exception("DB error")

        resultado = await verificar_ack_recente("cliente-123")
        assert resultado is False


class TestAckTemplates:
    """Testes de conteudo dos templates."""

    def test_templates_existem(self):
        """Verifica que templates obrigatorios existem."""
        assert "generico" in ACK_TEMPLATES
        assert "vaga" in ACK_TEMPLATES
        assert "aceite_vaga" in ACK_TEMPLATES  # Sprint 22: template separado que NAO promete reserva
        assert "confirmacao" in ACK_TEMPLATES

    def test_templates_tem_placeholder_nome(self):
        """Templates devem ter placeholder {nome}."""
        for tipo, template in ACK_TEMPLATES.items():
            assert "{nome}" in template.mensagem, f"Template {tipo} sem {{nome}}"

    def test_templates_nao_sao_muito_longos(self):
        """Templates nao devem ser muito longos."""
        for tipo, template in ACK_TEMPLATES.items():
            assert len(template.mensagem) < 500, f"Template {tipo} muito longo"
