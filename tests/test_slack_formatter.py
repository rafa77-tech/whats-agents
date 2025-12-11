"""
Testes do modulo de formatacao Slack.
"""
import pytest
from datetime import datetime, timezone

from app.services.slack_formatter import (
    # Formatacao basica
    bold,
    code,
    quote,
    lista,
    lista_numerada,
    # Formatacao de dados
    formatar_telefone,
    formatar_valor,
    formatar_porcentagem,
    formatar_data,
    formatar_data_hora,
    # Templates
    template_metricas,
    template_comparacao,
    template_lista_medicos,
    template_lista_vagas,
    template_medico_info,
    template_confirmacao_envio,
    template_sucesso_envio,
    template_sucesso_bloqueio,
    template_sucesso_reserva,
    template_status_sistema,
    template_lista_handoffs,
    template_historico,
    # Erros
    formatar_erro,
)


class TestFormatacaoBasica:
    """Testes de formatacao basica Slack."""

    def test_bold(self):
        """Testa formatacao bold."""
        assert bold("teste") == "*teste*"

    def test_code(self):
        """Testa formatacao code."""
        assert code("11999") == "`11999`"

    def test_quote(self):
        """Testa formatacao quote."""
        assert quote("linha 1") == "> linha 1"
        assert quote("linha 1\nlinha 2") == "> linha 1\n> linha 2"

    def test_lista_simples(self):
        """Testa lista simples."""
        itens = ["item 1", "item 2"]
        resultado = lista(itens)
        assert "• item 1" in resultado
        assert "• item 2" in resultado

    def test_lista_com_limite(self):
        """Testa lista com limite."""
        itens = [f"item {i}" for i in range(10)]
        resultado = lista(itens, max_itens=5)
        assert "• item 4" in resultado
        assert "...e mais 5" in resultado

    def test_lista_numerada(self):
        """Testa lista numerada."""
        itens = ["a", "b", "c"]
        resultado = lista_numerada(itens)
        assert "1. a" in resultado
        assert "2. b" in resultado
        assert "3. c" in resultado


class TestFormatacaoDados:
    """Testes de formatacao de dados."""

    def test_formatar_telefone_11_digitos(self):
        """Testa formatacao de telefone com 11 digitos."""
        resultado = formatar_telefone("11999887766")
        assert "`11 99988-7766`" == resultado

    def test_formatar_telefone_com_mascara(self):
        """Testa formatacao de telefone ja mascarado."""
        resultado = formatar_telefone("(11) 99988-7766")
        assert "11 99988-7766" in resultado

    def test_formatar_valor_milhares(self):
        """Testa formatacao de valor."""
        assert formatar_valor(2500) == "R$ 2.500"
        assert formatar_valor(1000) == "R$ 1.000"
        assert formatar_valor(500) == "R$ 500"

    def test_formatar_porcentagem(self):
        """Testa formatacao de porcentagem."""
        assert formatar_porcentagem(27.5) == "27.5%"
        assert formatar_porcentagem(30) == "30%"
        assert formatar_porcentagem(30.0) == "30%"

    def test_formatar_data_string(self):
        """Testa formatacao de data string."""
        resultado = formatar_data("2024-12-15")
        assert resultado == "15/12"

    def test_formatar_data_datetime(self):
        """Testa formatacao de datetime."""
        data = datetime(2024, 12, 15, 10, 30, tzinfo=timezone.utc)
        resultado = formatar_data(data)
        assert resultado == "15/12"


class TestTemplateMetricas:
    """Testes do template de metricas."""

    def test_metricas_hoje_bom(self):
        """Testa metricas com taxa boa."""
        metricas = {
            "enviadas": 100,
            "respostas": 35,
            "taxa_resposta": 35.0,
            "positivas": 20,
            "negativas": 5,
            "optouts": 2,
            "vagas_reservadas": 3
        }
        resultado = template_metricas(metricas, "hoje")
        assert "Dia bom" in resultado
        assert "35%" in resultado
        assert "Positivas: 20" in resultado

    def test_metricas_hoje_fraco(self):
        """Testa metricas com taxa fraca."""
        metricas = {
            "enviadas": 100,
            "respostas": 10,
            "taxa_resposta": 10.0,
        }
        resultado = template_metricas(metricas, "hoje")
        assert "Dia fraco" in resultado

    def test_metricas_semana(self):
        """Testa metricas de semana."""
        metricas = {"enviadas": 100, "respostas": 25, "taxa_resposta": 25.0}
        resultado = template_metricas(metricas, "semana")
        assert "*Semana:*" in resultado


class TestTemplateComparacao:
    """Testes do template de comparacao."""

    def test_comparacao_melhora(self):
        """Testa comparacao com melhora."""
        resultado_tool = {
            "periodo1": {
                "nome": "semana",
                "metricas": {"taxa_resposta": 32, "enviadas": 100, "respostas": 32}
            },
            "periodo2": {
                "nome": "semana_passada",
                "metricas": {"taxa_resposta": 28, "enviadas": 100, "respostas": 28}
            },
            "variacao": {
                "taxa_resposta": "+4 pontos",
                "enviadas": "0%",
                "respostas": "+14.3%",
                "tendencia": "melhora"
            }
        }
        resultado = template_comparacao(resultado_tool)
        assert "Essa semana vs Semana passada" in resultado
        assert "📈" in resultado
        assert "melhora" in resultado.lower()


class TestTemplateListaMedicos:
    """Testes do template de lista de medicos."""

    def test_lista_vazia(self):
        """Testa lista vazia."""
        resultado = template_lista_medicos([])
        assert "Nenhum medico" in resultado

    def test_lista_com_medicos(self):
        """Testa lista com medicos."""
        medicos = [
            {"nome": "Dr Carlos", "telefone": "11999887766", "especialidade": "Anestesio"},
            {"nome": "Dra Maria", "telefone": "11988776655", "especialidade": "Cardio"},
        ]
        resultado = template_lista_medicos(medicos, "responderam_hoje")
        assert "Dr Carlos" in resultado
        assert "Dra Maria" in resultado
        assert "respondeu hoje" in resultado

    def test_lista_com_limite(self):
        """Testa limite de 10 medicos."""
        medicos = [{"nome": f"Dr {i}", "telefone": f"1199988776{i}"} for i in range(15)]
        resultado = template_lista_medicos(medicos)
        assert "...e mais 5" in resultado


class TestTemplateVagas:
    """Testes do template de vagas."""

    def test_vagas_vazia(self):
        """Testa lista vazia."""
        resultado = template_lista_vagas([])
        assert "Nenhuma vaga" in resultado

    def test_vagas_com_dados(self):
        """Testa lista com vagas."""
        vagas = [
            {"hospital": "Sao Luiz", "data": "2024-12-15", "periodo": "Noturno", "valor": 2500},
            {"hospital": "Einstein", "data": "2024-12-16", "periodo": "Diurno", "valor": 3000},
        ]
        resultado = template_lista_vagas(vagas)
        assert "Sao Luiz" in resultado
        assert "15/12" in resultado
        assert "R$ 2.500" in resultado


class TestTemplateMedicoInfo:
    """Testes do template de info do medico."""

    def test_medico_completo(self):
        """Testa medico com todos os dados."""
        medico = {
            "nome": "Dr Carlos Silva",
            "telefone": "11999887766",
            "crm": "123456",
            "especialidade": "Anestesiologia",
            "cidade": "Sao Paulo",
            "bloqueado": False,
        }
        resultado = template_medico_info(medico)
        assert "*Dr Carlos Silva*" in resultado
        assert "CRM: 123456" in resultado
        assert "Anestesiologia" in resultado

    def test_medico_bloqueado(self):
        """Testa medico bloqueado."""
        medico = {"nome": "Dr Test", "bloqueado": True}
        resultado = template_medico_info(medico)
        assert "Bloqueado" in resultado


class TestTemplateConfirmacao:
    """Testes do template de confirmacao."""

    def test_confirmacao_envio(self):
        """Testa preview de envio."""
        resultado = template_confirmacao_envio(
            telefone="11999887766",
            mensagem="Oi Dr! Tudo bem?",
            nome="Dr Carlos"
        )
        assert "Dr Carlos" in resultado
        assert "Oi Dr!" in resultado
        assert "Posso enviar" in resultado

    def test_sucesso_envio(self):
        """Testa mensagem de sucesso."""
        resultado = template_sucesso_envio(nome="Dr Carlos")
        assert "Pronto" in resultado
        assert "Dr Carlos" in resultado

    def test_sucesso_bloqueio(self):
        """Testa mensagem de bloqueio."""
        resultado = template_sucesso_bloqueio(nome="Dr Carlos")
        assert "Bloqueado" in resultado
        assert "Dr Carlos" in resultado


class TestTemplateStatus:
    """Testes do template de status."""

    def test_status_ativo(self):
        """Testa status ativo."""
        dados = {
            "status": "ativo",
            "conversas_ativas": 5,
            "handoffs_pendentes": 0,
            "vagas_abertas": 10,
            "mensagens_hoje": 20
        }
        resultado = template_status_sistema(dados)
        assert "ativo" in resultado
        assert "✅" in resultado
        assert "Conversas ativas: 5" in resultado

    def test_status_com_handoffs(self):
        """Testa status com handoffs pendentes."""
        dados = {
            "status": "ativo",
            "conversas_ativas": 5,
            "handoffs_pendentes": 2,
            "vagas_abertas": 10,
            "mensagens_hoje": 20
        }
        resultado = template_status_sistema(dados)
        assert "⚠️" in resultado
        assert "2 handoff" in resultado


class TestFormatarErro:
    """Testes de formatacao de erro."""

    def test_erro_medico_nao_encontrado(self):
        """Testa erro de medico nao encontrado."""
        resultado = formatar_erro("Medico nao encontrado: 11999")
        assert "Nao achei" in resultado

    def test_erro_telefone_invalido(self):
        """Testa erro de telefone invalido."""
        resultado = formatar_erro("Telefone invalido")
        assert "nao parece valido" in resultado

    def test_erro_whatsapp(self):
        """Testa erro do WhatsApp."""
        resultado = formatar_erro("WhatsApp connection failed")
        assert "WhatsApp ta com problema" in resultado

    def test_erro_500(self):
        """Testa erro 500."""
        resultado = formatar_erro("Error 500: Internal Server Error")
        assert "problema" in resultado

    def test_erro_generico(self):
        """Testa erro generico."""
        resultado = formatar_erro("Algum erro estranho aconteceu aqui")
        assert "erro" in resultado.lower()
