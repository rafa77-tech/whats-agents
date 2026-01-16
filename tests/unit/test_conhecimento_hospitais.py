"""
Testes para serviço de Conhecimento de Hospitais.

Sprint 32 E11 - Julia aprende com respostas do gestor.
"""
import pytest
from unittest.mock import patch, MagicMock


class TestSalvarConhecimento:
    """Testes para salvar_conhecimento()."""

    @pytest.mark.asyncio
    async def test_cria_novo_conhecimento(self):
        """Deve criar novo conhecimento quando não existe."""
        from app.services.conhecimento_hospitais import salvar_conhecimento

        with patch("app.services.conhecimento_hospitais.supabase") as mock_supabase:
            # Não existe conhecimento anterior
            mock_select = MagicMock()
            mock_select.data = []
            mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = mock_select

            # Insert
            mock_insert = MagicMock()
            mock_insert.data = [{"id": "conhec-123", "atributo": "estacionamento", "valor": "Gratuito"}]
            mock_supabase.table.return_value.insert.return_value.execute.return_value = mock_insert

            resultado = await salvar_conhecimento(
                hospital_id="hosp-123",
                atributo="estacionamento",
                valor="Gratuito para médicos",
                fonte="gestor",
            )

            assert resultado is not None
            mock_supabase.table.return_value.insert.assert_called_once()

    @pytest.mark.asyncio
    async def test_atualiza_conhecimento_existente(self):
        """Deve atualizar conhecimento quando já existe."""
        from app.services.conhecimento_hospitais import salvar_conhecimento

        with patch("app.services.conhecimento_hospitais.supabase") as mock_supabase:
            # Já existe conhecimento
            mock_select = MagicMock()
            mock_select.data = [{"id": "conhec-existente"}]
            mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = mock_select

            # Update
            mock_update = MagicMock()
            mock_update.data = [{"id": "conhec-existente", "valor": "Atualizado"}]
            mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = mock_update

            resultado = await salvar_conhecimento(
                hospital_id="hosp-123",
                atributo="estacionamento",
                valor="Gratuito e coberto",
                fonte="gestor",
            )

            assert resultado is not None
            mock_supabase.table.return_value.update.assert_called_once()


class TestBuscarConhecimento:
    """Testes para buscar_conhecimento()."""

    @pytest.mark.asyncio
    async def test_busca_atributo_especifico(self):
        """Deve buscar atributo específico."""
        from app.services.conhecimento_hospitais import buscar_conhecimento

        with patch("app.services.conhecimento_hospitais.supabase") as mock_supabase:
            mock_result = MagicMock()
            mock_result.data = [{"atributo": "refeicao", "valor": "Refeitório 24h"}]
            mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = mock_result

            resultado = await buscar_conhecimento("hosp-123", "refeicao")

            assert resultado is not None
            assert resultado["valor"] == "Refeitório 24h"

    @pytest.mark.asyncio
    async def test_busca_todos_conhecimentos(self):
        """Deve buscar todos os conhecimentos do hospital."""
        from app.services.conhecimento_hospitais import buscar_conhecimento

        with patch("app.services.conhecimento_hospitais.supabase") as mock_supabase:
            mock_result = MagicMock()
            mock_result.data = [
                {"atributo": "refeicao", "valor": "Refeitório 24h"},
                {"atributo": "estacionamento", "valor": "Gratuito"},
            ]
            mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_result

            resultado = await buscar_conhecimento("hosp-123")

            assert len(resultado) == 2

    @pytest.mark.asyncio
    async def test_retorna_none_se_nao_encontrado(self):
        """Deve retornar None se atributo não existe."""
        from app.services.conhecimento_hospitais import buscar_conhecimento

        with patch("app.services.conhecimento_hospitais.supabase") as mock_supabase:
            mock_result = MagicMock()
            mock_result.data = []
            mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = mock_result

            resultado = await buscar_conhecimento("hosp-123", "wifi")

            assert resultado is None


class TestJuliaSabeSobreHospital:
    """Testes para julia_sabe_sobre_hospital()."""

    @pytest.mark.asyncio
    async def test_encontra_resposta_para_pergunta(self):
        """Deve encontrar resposta quando Julia sabe."""
        from app.services.conhecimento_hospitais import julia_sabe_sobre_hospital

        with patch("app.services.conhecimento_hospitais.buscar_conhecimento") as mock_buscar:
            mock_buscar.return_value = {"valor": "Sim, tem estacionamento gratuito"}

            resultado = await julia_sabe_sobre_hospital(
                hospital_id="hosp-123",
                pergunta="Tem estacionamento?",
            )

            assert resultado == "Sim, tem estacionamento gratuito"

    @pytest.mark.asyncio
    async def test_retorna_none_se_nao_sabe(self):
        """Deve retornar None se Julia não sabe."""
        from app.services.conhecimento_hospitais import julia_sabe_sobre_hospital

        with patch("app.services.conhecimento_hospitais.buscar_conhecimento") as mock_buscar:
            mock_buscar.return_value = None

            resultado = await julia_sabe_sobre_hospital(
                hospital_id="hosp-123",
                pergunta="Tem piscina?",
            )

            assert resultado is None

    @pytest.mark.asyncio
    async def test_detecta_atributo_refeicao(self):
        """Deve detectar pergunta sobre refeição."""
        from app.services.conhecimento_hospitais import julia_sabe_sobre_hospital

        with patch("app.services.conhecimento_hospitais.buscar_conhecimento") as mock_buscar:
            mock_buscar.return_value = {"valor": "Refeitório 24h incluso"}

            resultado = await julia_sabe_sobre_hospital(
                hospital_id="hosp-123",
                pergunta="Tem comida inclusa?",
            )

            assert resultado == "Refeitório 24h incluso"
            mock_buscar.assert_called_with("hosp-123", "refeicao")

    @pytest.mark.asyncio
    async def test_detecta_atributo_estacionamento(self):
        """Deve detectar pergunta sobre estacionamento."""
        from app.services.conhecimento_hospitais import julia_sabe_sobre_hospital

        with patch("app.services.conhecimento_hospitais.buscar_conhecimento") as mock_buscar:
            mock_buscar.return_value = {"valor": "Sim, gratuito"}

            resultado = await julia_sabe_sobre_hospital(
                hospital_id="hosp-123",
                pergunta="Onde posso estacionar meu carro?",
            )

            assert resultado == "Sim, gratuito"
            mock_buscar.assert_called_with("hosp-123", "estacionamento")


class TestJuliaAprendeu:
    """Testes para julia_aprendeu()."""

    @pytest.mark.asyncio
    async def test_salva_conhecimento_do_gestor(self):
        """Deve salvar conhecimento quando gestor responde."""
        from app.services.conhecimento_hospitais import julia_aprendeu

        with patch("app.services.conhecimento_hospitais.salvar_conhecimento") as mock_salvar:
            mock_salvar.return_value = {"id": "conhec-novo"}

            resultado = await julia_aprendeu(
                hospital_id="hosp-123",
                pergunta="Tem estacionamento?",
                resposta_gestor="Sim, gratuito no subsolo",
            )

            assert resultado is True
            mock_salvar.assert_called_once()

    @pytest.mark.asyncio
    async def test_detecta_atributo_da_pergunta(self):
        """Deve detectar o atributo correto da pergunta."""
        from app.services.conhecimento_hospitais import julia_aprendeu

        with patch("app.services.conhecimento_hospitais.salvar_conhecimento") as mock_salvar:
            mock_salvar.return_value = {"id": "conhec-novo"}

            await julia_aprendeu(
                hospital_id="hosp-123",
                pergunta="Tem vestiário para trocar de roupa?",
                resposta_gestor="Sim, com armários individuais",
            )

            # Verificar que salvou com atributo correto
            call_args = mock_salvar.call_args
            assert call_args[1]["atributo"] == "vestiario"


class TestObterContextoHospital:
    """Testes para obter_contexto_hospital()."""

    @pytest.mark.asyncio
    async def test_formata_contexto_completo(self):
        """Deve formatar contexto com todos os conhecimentos."""
        from app.services.conhecimento_hospitais import obter_contexto_hospital

        with patch("app.services.conhecimento_hospitais.listar_conhecimentos_hospital") as mock_listar:
            mock_listar.return_value = [
                {"atributo": "refeicao", "valor": "Refeitório 24h"},
                {"atributo": "estacionamento", "valor": "Gratuito"},
            ]

            resultado = await obter_contexto_hospital("hosp-123")

            assert "Informações do hospital:" in resultado
            assert "Refeição: Refeitório 24h" in resultado
            assert "Estacionamento: Gratuito" in resultado

    @pytest.mark.asyncio
    async def test_retorna_vazio_sem_conhecimentos(self):
        """Deve retornar string vazia sem conhecimentos."""
        from app.services.conhecimento_hospitais import obter_contexto_hospital

        with patch("app.services.conhecimento_hospitais.listar_conhecimentos_hospital") as mock_listar:
            mock_listar.return_value = []

            resultado = await obter_contexto_hospital("hosp-sem-info")

            assert resultado == ""


class TestNormalizarAtributo:
    """Testes para _normalizar_atributo()."""

    def test_normaliza_sinonimos(self):
        """Deve normalizar sinônimos para atributo padrão."""
        from app.services.conhecimento_hospitais import _normalizar_atributo

        assert _normalizar_atributo("comida") == "refeicao"
        assert _normalizar_atributo("alimentacao") == "refeicao"
        assert _normalizar_atributo("parking") == "estacionamento"
        assert _normalizar_atributo("internet") == "wifi"

    def test_mantem_atributos_conhecidos(self):
        """Deve manter atributos já conhecidos."""
        from app.services.conhecimento_hospitais import _normalizar_atributo

        assert _normalizar_atributo("refeicao") == "refeicao"
        assert _normalizar_atributo("estacionamento") == "estacionamento"
        assert _normalizar_atributo("wifi") == "wifi"

    def test_retorna_outro_para_desconhecidos(self):
        """Deve retornar 'outro' para atributos desconhecidos."""
        from app.services.conhecimento_hospitais import _normalizar_atributo

        assert _normalizar_atributo("piscina") == "outro"
        assert _normalizar_atributo("qualquer_coisa") == "outro"


class TestDetectarAtributoDaPergunta:
    """Testes para _detectar_atributo_da_pergunta()."""

    def test_detecta_refeicao(self):
        """Deve detectar perguntas sobre refeição."""
        from app.services.conhecimento_hospitais import _detectar_atributo_da_pergunta

        assert _detectar_atributo_da_pergunta("tem refeição?") == "refeicao"
        assert _detectar_atributo_da_pergunta("como é a comida?") == "refeicao"
        assert _detectar_atributo_da_pergunta("tem refeitório?") == "refeicao"

    def test_detecta_estacionamento(self):
        """Deve detectar perguntas sobre estacionamento."""
        from app.services.conhecimento_hospitais import _detectar_atributo_da_pergunta

        assert _detectar_atributo_da_pergunta("tem estacionamento?") == "estacionamento"
        assert _detectar_atributo_da_pergunta("onde deixo meu carro?") == "estacionamento"
        assert _detectar_atributo_da_pergunta("tem vaga de garagem?") == "estacionamento"

    def test_detecta_wifi(self):
        """Deve detectar perguntas sobre wifi."""
        from app.services.conhecimento_hospitais import _detectar_atributo_da_pergunta

        assert _detectar_atributo_da_pergunta("tem wifi?") == "wifi"
        assert _detectar_atributo_da_pergunta("como é a internet?") == "wifi"

    def test_retorna_none_para_desconhecido(self):
        """Deve retornar None para perguntas não identificáveis."""
        from app.services.conhecimento_hospitais import _detectar_atributo_da_pergunta

        assert _detectar_atributo_da_pergunta("qual o endereço?") == "acesso"
        assert _detectar_atributo_da_pergunta("pergunta aleatória") is None
