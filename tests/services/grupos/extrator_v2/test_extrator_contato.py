"""Testes para extrator de contato."""
import pytest

from app.services.grupos.extrator_v2.extrator_contato import (
    extrair_contato,
    _normalizar_telefone,
    _extrair_telefone,
    _extrair_nome,
)


class TestNormalizarTelefone:
    """Testes para normalização de telefone."""

    def test_telefone_completo(self):
        """Telefone já com DDI."""
        assert _normalizar_telefone("5511999999999") == "5511999999999"

    def test_telefone_sem_ddi(self):
        """Telefone sem DDI."""
        assert _normalizar_telefone("11999999999") == "5511999999999"

    def test_telefone_com_formatacao(self):
        """Telefone formatado."""
        assert _normalizar_telefone("(11) 99999-9999") == "5511999999999"
        assert _normalizar_telefone("+55 11 99999-9999") == "5511999999999"

    def test_telefone_curto(self):
        """Telefone só com número."""
        assert _normalizar_telefone("999999999").startswith("5511")


class TestExtrairTelefone:
    """Testes para extração de telefone."""

    def test_wame(self):
        """Link wa.me."""
        tel, raw = _extrair_telefone("wa.me/5511939050162")
        assert tel == "5511939050162"
        assert "wa.me" in raw

    def test_telefone_direto(self):
        """Telefone direto no texto."""
        tel, raw = _extrair_telefone("Ligar: 11999999999")
        assert tel == "5511999999999"

    def test_telefone_formatado(self):
        """Telefone formatado."""
        tel, raw = _extrair_telefone("(11) 99999-9999")
        assert tel == "5511999999999"

    def test_sem_telefone(self):
        """Texto sem telefone."""
        resultado = _extrair_telefone("Interessados mandar mensagem")
        assert resultado is None


class TestExtrairNome:
    """Testes para extração de nome."""

    def test_falar_com(self):
        """Padrão 'falar com Nome'."""
        nome = _extrair_nome("Interessados falar com Eloisa")
        assert nome == "Eloisa"

    def test_contato(self):
        """Padrão 'contato: Nome'."""
        nome = _extrair_nome("Contato: Maria")
        assert nome == "Maria"

    def test_nome_telefone(self):
        """Padrão 'Nome - telefone'."""
        nome = _extrair_nome("João - 11999999999")
        assert nome == "João"

    def test_nome_composto(self):
        """Nome composto."""
        nome = _extrair_nome("Falar com Maria Silva")
        assert nome == "Maria Silva"

    def test_sem_nome(self):
        """Texto sem nome."""
        nome = _extrair_nome("11999999999")
        assert nome is None


class TestExtrairContato:
    """Testes para extração completa de contato."""

    def test_contato_completo(self):
        """Extrai contato com nome e telefone."""
        linhas = [
            "📲 Interessados falar com Eloisa",
            "wa.me/5511939050162"
        ]
        contato = extrair_contato(linhas)

        assert contato is not None
        assert contato.nome == "Eloisa"
        assert contato.whatsapp == "5511939050162"
        assert contato.confianca >= 0.9

    def test_contato_so_telefone(self):
        """Extrai apenas telefone."""
        linhas = ["📲 11999999999"]
        contato = extrair_contato(linhas)

        assert contato is not None
        assert contato.whatsapp == "5511999999999"
        assert contato.nome is None

    def test_contato_em_uma_linha(self):
        """Contato em uma única linha."""
        linhas = ["Eloisa - wa.me/5511939050162"]
        contato = extrair_contato(linhas)

        assert contato is not None
        assert contato.nome == "Eloisa"
        assert contato.whatsapp == "5511939050162"

    def test_lista_vazia(self):
        """Lista vazia retorna None."""
        contato = extrair_contato([])
        assert contato is None

    def test_sem_telefone_retorna_none(self):
        """Sem telefone retorna None."""
        linhas = ["Interessados mandar mensagem"]
        contato = extrair_contato(linhas)
        assert contato is None


class TestCasosReais:
    """Testes com formatos reais."""

    def test_formato_emoji(self):
        """Formato com emoji."""
        linhas = ["📲11964391344"]
        contato = extrair_contato(linhas)

        assert contato is not None
        assert "64391344" in contato.whatsapp

    def test_formato_wame_completo(self):
        """wa.me com DDI."""
        linhas = ["wa.me/5511939050162"]
        contato = extrair_contato(linhas)

        assert contato is not None
        assert contato.whatsapp == "5511939050162"

    def test_formato_nome_separado(self):
        """Nome em linha separada."""
        linhas = [
            "📲 Eloisa",
            "wa.me/5511939050162"
        ]
        contato = extrair_contato(linhas)

        assert contato is not None
        assert contato.nome == "Eloisa"

    def test_formato_interessados(self):
        """Formato 'Interessados...'."""
        linhas = ["Interessados chamar Maria: 11 99999-9999"]
        contato = extrair_contato(linhas)

        assert contato is not None
        assert contato.nome == "Maria"
