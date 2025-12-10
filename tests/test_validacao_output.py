"""
Testes para o servico de validacao de output.

Garante que Julia nunca revele que e IA.
"""
import pytest

from app.services.validacao_output import (
    detectar_revelacao_ia,
    detectar_formato_proibido,
    detectar_linguagem_robotica,
    OutputValidator,
    validar_e_corrigir,
    ValidacaoResult,
)


class TestDetectarRevelacaoIA:
    """Testes para deteccao de revelacao de IA."""

    def test_detecta_sou_ia(self):
        """Deve detectar 'sou uma IA'."""
        resultado = detectar_revelacao_ia("Na verdade, sou uma IA")
        assert resultado.valido is False
        assert resultado.severidade == "critica"
        assert resultado.tipo_violacao == "mencao_ia"

    def test_detecta_sou_inteligencia_artificial(self):
        """Deve detectar 'sou inteligencia artificial'."""
        resultado = detectar_revelacao_ia("Eu sou uma inteligencia artificial")
        assert resultado.valido is False
        assert resultado.tipo_violacao == "mencao_ia"

    def test_detecta_sou_bot(self):
        """Deve detectar 'sou um bot'."""
        resultado = detectar_revelacao_ia("Desculpa, mas sou um bot")
        assert resultado.valido is False
        assert resultado.tipo_violacao == "mencao_bot"

    def test_detecta_sou_chatbot(self):
        """Deve detectar 'sou chatbot'."""
        resultado = detectar_revelacao_ia("Sou um chatbot programado para ajudar")
        assert resultado.valido is False
        assert resultado.tipo_violacao == "mencao_bot"

    def test_detecta_sou_assistente_virtual(self):
        """Deve detectar 'sou assistente virtual'."""
        resultado = detectar_revelacao_ia("Sou uma assistente virtual")
        assert resultado.valido is False
        assert resultado.tipo_violacao == "mencao_assistente"

    def test_detecta_modelo_linguagem(self):
        """Deve detectar 'modelo de linguagem'."""
        resultado = detectar_revelacao_ia("Como modelo de linguagem, nao posso")
        assert resultado.valido is False
        assert resultado.tipo_violacao == "mencao_modelo"

    def test_detecta_claude(self):
        """Deve detectar mencao ao Claude."""
        resultado = detectar_revelacao_ia("Sou o Claude da Anthropic")
        assert resultado.valido is False
        assert resultado.tipo_violacao == "mencao_claude"

    def test_detecta_gpt(self):
        """Deve detectar mencao ao GPT."""
        resultado = detectar_revelacao_ia("Sou baseado no GPT")
        assert resultado.valido is False
        assert resultado.tipo_violacao == "mencao_gpt"

    def test_detecta_criado_anthropic(self):
        """Deve detectar 'criado pela Anthropic'."""
        resultado = detectar_revelacao_ia("Fui criado pela Anthropic")
        assert resultado.valido is False
        assert resultado.tipo_violacao == "mencao_empresa"

    def test_detecta_criado_openai(self):
        """Deve detectar 'criado pela OpenAI'."""
        resultado = detectar_revelacao_ia("Sou treinado pela OpenAI")
        assert resultado.valido is False
        assert resultado.tipo_violacao == "mencao_empresa"

    def test_detecta_nao_sou_pessoa(self):
        """Deve detectar 'nao sou pessoa'."""
        resultado = detectar_revelacao_ia("Nao sou exatamente uma pessoa")
        assert resultado.valido is False
        assert resultado.severidade == "alta"
        assert resultado.tipo_violacao == "evasiva_pessoa"

    def test_detecta_nao_tenho_corpo(self):
        """Deve detectar 'nao tenho corpo fisico'."""
        resultado = detectar_revelacao_ia("Eu nao tenho um corpo fisico")
        assert resultado.valido is False
        assert resultado.tipo_violacao == "evasiva_corpo"

    def test_detecta_sou_programa(self):
        """Deve detectar 'sou um programa'."""
        resultado = detectar_revelacao_ia("Bom, eu sou um programa")
        assert resultado.valido is False
        assert resultado.severidade == "critica"
        assert resultado.tipo_violacao == "evasiva_programa"

    def test_detecta_fui_programada(self):
        """Deve detectar 'fui programada para'."""
        resultado = detectar_revelacao_ia("Fui programada para ajudar medicos")
        assert resultado.valido is False
        assert resultado.tipo_violacao == "evasiva_programado"

    def test_detecta_conhecimento_cortado(self):
        """Deve detectar 'meu conhecimento foi cortado em'."""
        resultado = detectar_revelacao_ia("Meu conhecimento foi cortado em 2024")
        assert resultado.valido is False
        assert resultado.tipo_violacao == "limitacao_conhecimento"

    def test_nao_detecta_resposta_normal(self):
        """Nao deve detectar resposta normal."""
        resultado = detectar_revelacao_ia(
            "Oi Dr Carlos! Tudo bem? Tenho uma vaga otima pra vc"
        )
        assert resultado.valido is True

    def test_nao_detecta_julia_normal(self):
        """Nao deve detectar conversa normal da Julia."""
        resultado = detectar_revelacao_ia(
            "Opa, blz? Surgiu uma vaga no Hospital Sirio que pode te interessar"
        )
        assert resultado.valido is True

    def test_nao_detecta_resposta_medica(self):
        """Nao deve detectar resposta sobre trabalho."""
        resultado = detectar_revelacao_ia(
            "O plantao e das 19h as 7h, o valor e R$ 2.500"
        )
        assert resultado.valido is True


class TestDetectarFormatoProibido:
    """Testes para deteccao de formato proibido."""

    def test_detecta_bullet_point(self):
        """Deve detectar bullet points."""
        resultado = detectar_formato_proibido("- Item 1\n- Item 2")
        assert resultado.valido is False
        assert resultado.tipo_violacao == "bullet_point"

    def test_detecta_lista_numerada(self):
        """Deve detectar lista numerada."""
        resultado = detectar_formato_proibido("1. Primeiro\n2. Segundo")
        assert resultado.valido is False
        assert resultado.tipo_violacao == "lista_numerada"

    def test_detecta_markdown_bold(self):
        """Deve detectar markdown bold."""
        resultado = detectar_formato_proibido("Isso e **muito importante**")
        assert resultado.valido is False
        assert resultado.tipo_violacao == "markdown_bold"

    def test_detecta_markdown_code(self):
        """Deve detectar markdown code."""
        resultado = detectar_formato_proibido("Use o comando `docker run`")
        assert resultado.valido is False
        assert resultado.tipo_violacao == "markdown_code"

    def test_detecta_markdown_header(self):
        """Deve detectar markdown header."""
        resultado = detectar_formato_proibido("## Titulo da Secao")
        assert resultado.valido is False
        assert resultado.tipo_violacao == "markdown_header"

    def test_detecta_saudacao_formal(self):
        """Deve detectar saudacao formal."""
        resultado = detectar_formato_proibido("Prezado Dr. Carlos")
        assert resultado.valido is False
        assert resultado.tipo_violacao == "saudacao_formal"

    def test_detecta_despedida_formal(self):
        """Deve detectar despedida formal."""
        resultado = detectar_formato_proibido("Atenciosamente, Julia")
        assert resultado.valido is False
        assert resultado.tipo_violacao == "despedida_formal"

    def test_nao_detecta_texto_normal(self):
        """Nao deve detectar texto normal."""
        resultado = detectar_formato_proibido(
            "Oi! A vaga e no Sao Luiz, plantao noturno"
        )
        assert resultado.valido is True


class TestDetectarLinguagemRobotica:
    """Testes para deteccao de linguagem robotica."""

    def test_detecta_gostaríamos_informar(self):
        """Deve detectar 'gostariamos de informar'."""
        resultado = detectar_linguagem_robotica(
            "Gostariamos de informar que a vaga foi preenchida"
        )
        assert resultado.valido is False
        assert resultado.tipo_violacao == "formal_informar"

    def test_detecta_vimos_por_meio_desta(self):
        """Deve detectar 'vimos por meio desta'."""
        resultado = detectar_linguagem_robotica(
            "Vimos por meio desta comunicar que..."
        )
        assert resultado.valido is False
        assert resultado.tipo_violacao == "formal_carta"

    def test_detecta_vossa_senhoria(self):
        """Deve detectar 'vossa senhoria'."""
        resultado = detectar_linguagem_robotica("Vossa senhoria sera informado")
        assert resultado.valido is False
        assert resultado.tipo_violacao == "formal_vossa"

    def test_detecta_sua_ligacao_importante(self):
        """Deve detectar 'sua ligacao e muito importante'."""
        resultado = detectar_linguagem_robotica(
            "Sua ligacao e muito importante para nos"
        )
        assert resultado.valido is False
        assert resultado.tipo_violacao == "sac_importante"

    def test_detecta_obrigado_contato(self):
        """Deve detectar 'obrigado por entrar em contato'."""
        resultado = detectar_linguagem_robotica("Obrigada por entrar em contato")
        assert resultado.valido is False
        assert resultado.tipo_violacao == "sac_contato"

    def test_nao_detecta_linguagem_informal(self):
        """Nao deve detectar linguagem informal."""
        resultado = detectar_linguagem_robotica(
            "Opa, blz? Vc viu a msg que mandei sobre o plantao?"
        )
        assert resultado.valido is True


class TestOutputValidator:
    """Testes para o validador completo."""

    def test_valida_resposta_ok(self):
        """Deve validar resposta normal."""
        validator = OutputValidator()
        resultado = validator.validar(
            "Oi Dr Carlos! Tem uma vaga otima no Sao Luiz, te interessa?"
        )
        assert resultado.valido is True

    def test_bloqueia_revelacao_ia(self):
        """Deve bloquear revelacao de IA."""
        validator = OutputValidator()
        resultado = validator.validar(
            "Desculpa, mas eu sou uma inteligencia artificial"
        )
        assert resultado.valido is False
        assert resultado.severidade == "critica"

    def test_bloqueia_formato_proibido(self):
        """Deve bloquear formato proibido."""
        validator = OutputValidator()
        resultado = validator.validar(
            "Vagas disponiveis:\n- Hospital Sirio\n- Hospital Albert Einstein"
        )
        assert resultado.valido is False

    def test_bloqueia_linguagem_robotica(self):
        """Deve bloquear linguagem robotica."""
        validator = OutputValidator()
        resultado = validator.validar(
            "Gostariamos de informar que sua solicitacao foi processada"
        )
        assert resultado.valido is False

    def test_registra_metricas(self):
        """Deve registrar metricas de validacao."""
        validator = OutputValidator()

        # Validar algumas respostas
        validator.validar("Oi, tudo bem?")
        validator.validar("Sou uma IA")
        validator.validar("- Item 1")

        metricas = validator.get_metricas()
        assert metricas["total_validacoes"] == 3
        assert "mencao_ia" in metricas["falhas_por_tipo"]

    def test_texto_vazio_valido(self):
        """Texto vazio deve ser valido."""
        validator = OutputValidator()
        resultado = validator.validar("")
        assert resultado.valido is True

    def test_texto_none_valido(self):
        """Texto None deve ser tratado como vazio."""
        validator = OutputValidator()
        resultado = validator.validar(None)
        assert resultado.valido is True


class TestValidarECorrigir:
    """Testes para validacao com correcao."""

    @pytest.mark.asyncio
    async def test_nao_modifica_texto_valido(self):
        """Nao deve modificar texto valido."""
        texto = "Oi Dr Carlos! Tudo bem?"
        corrigido, modificado = await validar_e_corrigir(texto)
        assert corrigido == texto
        assert modificado is False

    @pytest.mark.asyncio
    async def test_remove_bullets(self):
        """Deve remover bullet points."""
        texto = "Vagas:\n- Hospital A\n- Hospital B"
        corrigido, modificado = await validar_e_corrigir(texto)
        assert modificado is True
        assert "- " not in corrigido

    @pytest.mark.asyncio
    async def test_remove_markdown_bold(self):
        """Deve remover markdown bold."""
        texto = "Isso e **muito importante**"
        corrigido, modificado = await validar_e_corrigir(texto)
        assert modificado is True
        assert "**" not in corrigido
        assert "muito importante" in corrigido

    @pytest.mark.asyncio
    async def test_remove_markdown_code(self):
        """Deve remover markdown code."""
        texto = "Use o comando `docker run`"
        corrigido, modificado = await validar_e_corrigir(texto)
        assert modificado is True
        assert "`" not in corrigido
        assert "docker run" in corrigido

    @pytest.mark.asyncio
    async def test_bloqueia_revelacao_critica(self):
        """Deve bloquear (retornar vazio) em revelacao critica."""
        texto = "Eu sou uma inteligencia artificial"
        corrigido, modificado = await validar_e_corrigir(texto)
        assert modificado is True
        assert corrigido == ""  # Bloqueado

    @pytest.mark.asyncio
    async def test_bloqueia_mencao_claude(self):
        """Deve bloquear mencao ao Claude."""
        texto = "Sou o Claude da Anthropic"
        corrigido, modificado = await validar_e_corrigir(texto)
        assert modificado is True
        assert corrigido == ""  # Bloqueado

    @pytest.mark.asyncio
    async def test_bloqueia_sou_bot(self):
        """Deve bloquear 'sou bot'."""
        texto = "Sou um bot programado para ajudar"
        corrigido, modificado = await validar_e_corrigir(texto)
        assert modificado is True
        assert corrigido == ""  # Bloqueado


class TestCasosReais:
    """Testes com casos reais que podem acontecer."""

    def test_julia_responde_se_e_bot(self):
        """Julia deve passar quando perguntam se e bot."""
        validator = OutputValidator()

        # Resposta esperada quando perguntam se e bot
        resultado = validator.validar(
            "Haha bot? Que nada, sou a Julia da Revoluna! "
            "Trabalho com escalas medicas ha uns 4 anos ja"
        )
        assert resultado.valido is True

    def test_julia_responde_identidade(self):
        """Julia deve passar ao falar sobre si mesma."""
        validator = OutputValidator()
        resultado = validator.validar(
            "Sou a Julia, escalista da Revoluna. "
            "Cuido das vagas de anestesio aqui na regiao do ABC"
        )
        assert resultado.valido is True

    def test_julia_oferece_vaga(self):
        """Julia deve passar ao oferecer vaga."""
        validator = OutputValidator()
        resultado = validator.validar(
            "Opa Dr Carlos! Surgiu uma vaga no Sao Luiz que pode te interessar. "
            "Plantao noturno de anestesio, dia 15, das 19h as 7h. R$ 2.500"
        )
        assert resultado.valido is True

    def test_julia_confirma_reserva(self):
        """Julia deve passar ao confirmar reserva."""
        validator = OutputValidator()
        resultado = validator.validar(
            "Show! Reservei pra vc entao. "
            "Vou precisar de alguns docs pra finalizar ok?"
        )
        assert resultado.valido is True

    def test_julia_usa_abreviacao(self):
        """Julia deve passar usando abreviacoes."""
        validator = OutputValidator()
        resultado = validator.validar(
            "Blz, vc ta de plantao qndo? Posso ver oq tem disponivel pra vc"
        )
        assert resultado.valido is True
