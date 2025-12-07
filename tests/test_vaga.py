"""
Testes do servico de vagas.
"""
import pytest
from datetime import datetime
from app.services.vaga import (
    filtrar_por_preferencias,
    formatar_vaga_para_mensagem,
)


class TestFiltrarPorPreferencias:
    """Testes para filtro de preferencias."""

    def test_sem_preferencias(self):
        """Retorna todas as vagas se nao ha preferencias."""
        vagas = [
            {"id": "1", "hospital_id": "h1", "valor": 2000},
            {"id": "2", "hospital_id": "h2", "valor": 2500},
        ]
        resultado = filtrar_por_preferencias(vagas, {})
        assert len(resultado) == 2

    def test_preferencias_none(self):
        """Retorna todas as vagas se preferencias e None."""
        vagas = [{"id": "1", "hospital_id": "h1", "valor": 2000}]
        resultado = filtrar_por_preferencias(vagas, None)
        assert len(resultado) == 1

    def test_filtra_hospital_bloqueado(self):
        """Remove vagas de hospitais bloqueados."""
        vagas = [
            {"id": "1", "hospital_id": "h1", "valor": 2000},
            {"id": "2", "hospital_id": "h2", "valor": 2500},
            {"id": "3", "hospital_id": "h1", "valor": 3000},
        ]
        preferencias = {"hospitais_bloqueados": ["h1"]}
        resultado = filtrar_por_preferencias(vagas, preferencias)

        assert len(resultado) == 1
        assert resultado[0]["id"] == "2"

    def test_filtra_setor_bloqueado(self):
        """Remove vagas de setores bloqueados."""
        vagas = [
            {"id": "1", "setor_id": "s1", "valor": 2000},
            {"id": "2", "setor_id": "s2", "valor": 2500},
            {"id": "3", "setor_id": None, "valor": 3000},
        ]
        preferencias = {"setores_bloqueados": ["s1"]}
        resultado = filtrar_por_preferencias(vagas, preferencias)

        assert len(resultado) == 2
        assert all(v["id"] != "1" for v in resultado)

    def test_filtra_valor_minimo(self):
        """Remove vagas com valor abaixo do minimo."""
        vagas = [
            {"id": "1", "valor": 1500},
            {"id": "2", "valor": 2000},
            {"id": "3", "valor": 2500},
        ]
        preferencias = {"valor_minimo": 2000}
        resultado = filtrar_por_preferencias(vagas, preferencias)

        assert len(resultado) == 2
        assert all(v["valor"] >= 2000 for v in resultado)

    def test_valor_none_nao_filtra(self):
        """Vagas com valor None nao passam no filtro de valor minimo."""
        vagas = [
            {"id": "1", "valor": None},
            {"id": "2", "valor": 2000},
        ]
        preferencias = {"valor_minimo": 1500}
        resultado = filtrar_por_preferencias(vagas, preferencias)

        assert len(resultado) == 1
        assert resultado[0]["id"] == "2"

    def test_combinacao_filtros(self):
        """Aplica multiplos filtros combinados."""
        vagas = [
            {"id": "1", "hospital_id": "h1", "setor_id": "s1", "valor": 2000},
            {"id": "2", "hospital_id": "h2", "setor_id": "s1", "valor": 2500},
            {"id": "3", "hospital_id": "h2", "setor_id": "s2", "valor": 1500},
            {"id": "4", "hospital_id": "h2", "setor_id": "s2", "valor": 3000},
        ]
        preferencias = {
            "hospitais_bloqueados": ["h1"],
            "setores_bloqueados": ["s1"],
            "valor_minimo": 2000,
        }
        resultado = filtrar_por_preferencias(vagas, preferencias)

        # Vaga 1: hospital bloqueado
        # Vaga 2: setor bloqueado
        # Vaga 3: valor abaixo do minimo
        # Vaga 4: passa em todos
        assert len(resultado) == 1
        assert resultado[0]["id"] == "4"


class TestFormatarVagaParaMensagem:
    """Testes para formatacao de vaga em mensagem."""

    def test_vaga_completa(self):
        """Formata vaga com todos os dados."""
        vaga = {
            "id": "abc12345-6789",
            "hospitais": {"nome": "Hospital Brasil"},
            "data": "2025-12-15",
            "periodos": {"nome": "Diurno"},
            "setores": {"nome": "UTI"},
            "valor": 2500,
        }
        resultado = formatar_vaga_para_mensagem(vaga)

        assert "Hospital Brasil" in resultado
        assert "segunda" in resultado  # 15/12/2025 e segunda
        assert "15/12" in resultado
        assert "diurno" in resultado
        assert "UTI" in resultado
        assert "2.500" in resultado

    def test_vaga_sem_setor(self):
        """Formata vaga sem setor."""
        vaga = {
            "hospitais": {"nome": "Hospital A"},
            "data": "2025-12-20",
            "periodos": {"nome": "Noturno"},
            "setores": {},
            "valor": 2000,
        }
        resultado = formatar_vaga_para_mensagem(vaga)

        assert "Hospital A" in resultado
        assert "noturno" in resultado
        assert "2.000" in resultado

    def test_vaga_sem_valor(self):
        """Formata vaga sem valor definido."""
        vaga = {
            "hospitais": {"nome": "Hospital B"},
            "data": "2025-12-21",
            "periodos": {"nome": "SD12"},
            "valor": None,
        }
        resultado = formatar_vaga_para_mensagem(vaga)

        assert "Hospital B" in resultado
        assert "sd12" in resultado
        assert "R$" not in resultado

    def test_vaga_dados_minimos(self):
        """Formata vaga com dados minimos."""
        vaga = {
            "hospitais": {},
            "data": "",
            "periodos": {},
            "valor": 0,
        }
        resultado = formatar_vaga_para_mensagem(vaga)

        assert "Hospital" in resultado  # Valor default

    def test_data_sabado(self):
        """Formata data de sabado corretamente."""
        vaga = {
            "hospitais": {"nome": "Hospital C"},
            "data": "2025-12-13",  # Sabado
            "periodos": {"nome": "Diurno"},
            "valor": 1800,
        }
        resultado = formatar_vaga_para_mensagem(vaga)

        assert "sabado" in resultado
        assert "13/12" in resultado

    def test_data_domingo(self):
        """Formata data de domingo corretamente."""
        vaga = {
            "hospitais": {"nome": "Hospital D"},
            "data": "2025-12-14",  # Domingo
            "periodos": {"nome": "Noturno"},
            "valor": 2200,
        }
        resultado = formatar_vaga_para_mensagem(vaga)

        assert "domingo" in resultado
        assert "14/12" in resultado
