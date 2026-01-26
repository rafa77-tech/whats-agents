"""Testes para parser de mensagem."""

import pytest

from app.services.grupos.extrator_v2.parser_mensagem import (
    parsear_mensagem,
    _classificar_linha,
    TipoSecao,
    MensagemParsed,
)


class TestClassificarLinha:
    """Testes para classificação de linhas individuais."""

    def test_linha_local_com_emoji(self):
        """Linha com emoji de local."""
        linha = _classificar_linha("📍 Hospital Campo Limpo", 0)
        assert linha.tipo == TipoSecao.LOCAL
        assert linha.confianca >= 0.5

    def test_linha_local_com_keyword(self):
        """Linha com keyword de local."""
        linha = _classificar_linha("Hospital São Luiz ABC", 0)
        assert linha.tipo == TipoSecao.LOCAL
        assert linha.confianca >= 0.3

    def test_linha_endereco(self):
        """Linha com endereço."""
        linha = _classificar_linha("Av. Brasil, 1000 - Centro", 0)
        assert linha.tipo == TipoSecao.LOCAL
        assert linha.confianca >= 0.3

    def test_linha_data_com_emoji(self):
        """Linha com emoji de data."""
        linha = _classificar_linha("🗓 26/01 - Segunda - Manhã", 0)
        assert linha.tipo == TipoSecao.DATA
        assert linha.confianca >= 0.5

    def test_linha_data_com_pattern(self):
        """Linha com padrão de data."""
        linha = _classificar_linha("26/01 - Segunda - Manhã 7-13h", 0)
        assert linha.tipo == TipoSecao.DATA
        assert linha.confianca >= 0.3

    def test_linha_valor_com_emoji(self):
        """Linha com emoji de valor."""
        linha = _classificar_linha("💰 R$ 1.700", 0)
        assert linha.tipo == TipoSecao.VALOR
        assert linha.confianca >= 0.5

    def test_linha_valor_com_pattern(self):
        """Linha com padrão monetário."""
        linha = _classificar_linha("Segunda a Sexta: R$ 1.700", 0)
        assert linha.tipo == TipoSecao.VALOR
        assert linha.confianca >= 0.3

    def test_linha_contato_com_emoji(self):
        """Linha com emoji de contato."""
        linha = _classificar_linha("📲 Eloisa - 11999999999", 0)
        assert linha.tipo == TipoSecao.CONTATO
        assert linha.confianca >= 0.5

    def test_linha_contato_com_whatsapp(self):
        """Linha com link WhatsApp."""
        linha = _classificar_linha("wa.me/5511939050162", 0)
        assert linha.tipo == TipoSecao.CONTATO
        assert linha.confianca >= 0.4

    def test_linha_contato_com_keyword(self):
        """Linha com keyword de contato."""
        linha = _classificar_linha("Interessados falar com Maria", 0)
        assert linha.tipo == TipoSecao.CONTATO
        assert linha.confianca >= 0.3

    def test_linha_vazia(self):
        """Linha vazia retorna DESCONHECIDO."""
        linha = _classificar_linha("", 0)
        assert linha.tipo == TipoSecao.DESCONHECIDO
        assert linha.confianca == 0.0

    def test_linha_sem_indicadores(self):
        """Linha sem indicadores claros."""
        linha = _classificar_linha("Bom dia pessoal!", 0)
        assert linha.tipo == TipoSecao.DESCONHECIDO


class TestParsearMensagem:
    """Testes para parsing completo de mensagem."""

    def test_mensagem_completa(self):
        """Parseia mensagem com todas as seções."""
        texto = """📍 Hospital Campo Limpo
Estrada Itapecirica, 1661 - SP

🗓 26/01 - Segunda - Tarde 13-19h
🗓 27/01 - Terça - Noite 19-7h

💰 Segunda a Sexta: R$ 1.700
💰 Sábado e Domingo: R$ 1.800

📲 Eloisa
wa.me/5511939050162"""

        msg = parsear_mensagem(texto)

        assert msg.tem_local is True
        assert msg.tem_datas is True
        assert msg.tem_valores is True
        assert msg.tem_contato is True

        assert len(msg.secoes_local) >= 1
        assert len(msg.secoes_data) == 2
        assert len(msg.secoes_valor) == 2
        assert len(msg.secoes_contato) >= 1

    def test_mensagem_sem_emoji(self):
        """Parseia mensagem sem emojis (só keywords)."""
        texto = """Hospital São Luiz ABC
Av. Brasil, 1000

28/01 - Quarta - Noturno 19-7h

Valor: R$ 2.000 PJ

Interessados ligar para João: 11999999999"""

        msg = parsear_mensagem(texto)

        assert msg.tem_local is True
        assert msg.tem_datas is True
        assert msg.tem_valores is True
        assert msg.tem_contato is True

    def test_mensagem_minima(self):
        """Parseia mensagem mínima."""
        texto = "Hospital ABC - 26/01 manhã R$ 1500"

        msg = parsear_mensagem(texto)

        # Linha única pode ter múltiplas classificações
        # O parser deve identificar pelo menos data e valor
        assert msg.tem_datas is True or msg.tem_valores is True

    def test_mensagem_vazia(self):
        """Mensagem vazia retorna objeto vazio."""
        msg = parsear_mensagem("")

        assert msg.tem_local is False
        assert msg.tem_datas is False
        assert msg.tem_valores is False
        assert msg.tem_contato is False

    def test_mensagem_none(self):
        """Mensagem None não quebra."""
        msg = parsear_mensagem(None)
        assert isinstance(msg, MensagemParsed)

    def test_preserva_texto_original(self):
        """Preserva texto original na resposta."""
        texto = "📍 Hospital ABC"
        msg = parsear_mensagem(texto)
        assert msg.texto_original == texto

    def test_multiplos_hospitais(self):
        """Detecta múltiplos hospitais."""
        texto = """📍 Hospital ABC
📍 Hospital XYZ
🗓 26/01 manhã"""

        msg = parsear_mensagem(texto)
        assert len(msg.secoes_local) == 2

    def test_multiplas_datas(self):
        """Detecta múltiplas datas."""
        texto = """📍 Hospital ABC
🗓 26/01 - Segunda
🗓 27/01 - Terça
🗓 28/01 - Quarta
🗓 29/01 - Quinta
🗓 30/01 - Sexta"""

        msg = parsear_mensagem(texto)
        assert len(msg.secoes_data) == 5

    def test_regras_valor_diferentes(self):
        """Detecta diferentes regras de valor."""
        texto = """💰 Valores:
Segunda a Sexta: R$ 1.700
Sábado: R$ 1.800
Domingo: R$ 2.000
Feriado: R$ 2.500"""

        msg = parsear_mensagem(texto)
        assert len(msg.secoes_valor) >= 4


class TestCasosReais:
    """Testes com casos reais de grupos médicos."""

    def test_caso_real_1(self):
        """Caso real: formato típico com emojis."""
        texto = """🔴🔴PRECISO🔴🔴

📍UPA CAMPO LIMPO
📅 27/01 SEGUNDA
⏰ 19 as 07
💰1.600
📲11964391344"""

        msg = parsear_mensagem(texto)

        assert msg.tem_local is True
        assert msg.tem_datas is True
        assert msg.tem_valores is True
        assert msg.tem_contato is True

    def test_caso_real_2(self):
        """Caso real: formato de lista de datas."""
        texto = """*PLANTÕES CLINICA MÉDICA*

Hospital Santa Casa ABC

26/01 dom diurno 7-19h
27/01 seg noturno 19-7h
28/01 ter diurno 7-19h

Valor R$ 1.500 (dom +100)

Int. Maria 11 99999-9999"""

        msg = parsear_mensagem(texto)

        assert msg.tem_local is True
        assert len(msg.secoes_data) >= 3
        assert msg.tem_valores is True
        assert msg.tem_contato is True

    def test_caso_real_3(self):
        """Caso real: formato compacto."""
        texto = """CM PS Central 28/12 noturno 1800 PJ - Ana 11987654321"""

        msg = parsear_mensagem(texto)

        # Mesmo em formato compacto, deve identificar elementos
        assert len(msg.linhas) > 0
