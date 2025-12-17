"""Testes para os detectores de situação."""
import pytest
from app.services.conhecimento import (
    DetectorObjecao,
    TipoObjecao,
    DetectorPerfil,
    PerfilMedico,
    DetectorObjetivo,
    ObjetivoConversa,
)


class TestDetectorObjecao:
    """Testes para DetectorObjecao."""

    @pytest.fixture
    def detector(self):
        return DetectorObjecao()

    # Testes de PRECO
    @pytest.mark.parametrize(
        "mensagem",
        [
            "O valor está muito baixo",
            "Paga pouco para o trabalho",
            "Esse preço não compensa",
            "Valor muito baixo pra mim",
        ],
    )
    def test_detecta_objecao_preco(self, detector, mensagem):
        resultado = detector.detectar(mensagem)
        assert resultado.tem_objecao is True
        assert resultado.tipo == TipoObjecao.PRECO
        assert resultado.confianca >= 0.7

    # Testes de TEMPO
    @pytest.mark.parametrize(
        "mensagem",
        [
            "Não tenho tempo agora",
            "Minha agenda está cheia",
            "Estou muito ocupado essa semana",
            "Sem tempo no momento",
        ],
    )
    def test_detecta_objecao_tempo(self, detector, mensagem):
        resultado = detector.detectar(mensagem)
        assert resultado.tem_objecao is True
        assert resultado.tipo == TipoObjecao.TEMPO
        assert resultado.confianca >= 0.7

    # Testes de CONFIANCA
    @pytest.mark.parametrize(
        "mensagem",
        [
            "Não conheço a Revoluna",
            "Nunca ouvi falar de vocês",
            "Como funciona isso?",
            "É golpe?",
        ],
    )
    def test_detecta_objecao_confianca(self, detector, mensagem):
        resultado = detector.detectar(mensagem)
        assert resultado.tem_objecao is True
        assert resultado.tipo == TipoObjecao.CONFIANCA
        assert resultado.confianca >= 0.7

    # Testes de MOTIVACAO
    @pytest.mark.parametrize(
        "mensagem",
        [
            "Não quero fazer plantão",
            "Parei de fazer plantão",
            "Não tenho interesse",
            "No momento não preciso",
        ],
    )
    def test_detecta_objecao_motivacao(self, detector, mensagem):
        resultado = detector.detectar(mensagem)
        assert resultado.tem_objecao is True
        assert resultado.tipo == TipoObjecao.MOTIVACAO
        assert resultado.confianca >= 0.7

    # Testes de COMUNICACAO
    @pytest.mark.parametrize(
        "mensagem",
        [
            "Vou pensar",
            "Depois a gente fala",
            "Me liga depois",
        ],
    )
    def test_detecta_objecao_comunicacao(self, detector, mensagem):
        resultado = detector.detectar(mensagem)
        assert resultado.tem_objecao is True
        assert resultado.tipo == TipoObjecao.COMUNICACAO
        assert resultado.confianca >= 0.7

    # Teste de NÃO objeção
    @pytest.mark.parametrize(
        "mensagem",
        [
            "Oi, tudo bem?",
            "Quais vagas tem disponíveis?",
            "Pode me contar mais?",
            "Me manda os detalhes",
            "Legal, gostei",
        ],
    )
    def test_nao_detecta_objecao_mensagens_neutras(self, detector, mensagem):
        resultado = detector.detectar(mensagem)
        assert resultado.tem_objecao is False
        assert resultado.tipo == TipoObjecao.NENHUMA

    def test_detecta_subtipo_preco_valor_baixo(self, detector):
        resultado = detector.detectar("O valor está muito baixo")
        assert resultado.subtipo == "valor_baixo"

    def test_detecta_subtipo_tempo_agenda_cheia(self, detector):
        resultado = detector.detectar("Minha agenda está cheia")
        assert resultado.subtipo == "agenda_cheia"


class TestDetectorPerfil:
    """Testes para DetectorPerfil."""

    @pytest.fixture
    def detector(self):
        return DetectorPerfil()

    # Testes por dados
    def test_detecta_recem_formado_por_anos(self, detector):
        resultado = detector.detectar_por_dados(anos_experiencia=1)
        assert resultado.perfil == PerfilMedico.RECEM_FORMADO
        assert resultado.confianca >= 0.9

    def test_detecta_em_desenvolvimento_por_anos(self, detector):
        resultado = detector.detectar_por_dados(anos_experiencia=5)
        assert resultado.perfil == PerfilMedico.EM_DESENVOLVIMENTO
        assert resultado.confianca >= 0.8

    def test_detecta_experiente_por_anos(self, detector):
        resultado = detector.detectar_por_dados(anos_experiencia=10)
        assert resultado.perfil == PerfilMedico.EXPERIENTE
        assert resultado.confianca >= 0.8

    def test_detecta_senior_por_anos(self, detector):
        resultado = detector.detectar_por_dados(anos_experiencia=20)
        assert resultado.perfil == PerfilMedico.SENIOR
        assert resultado.confianca >= 0.9

    def test_detecta_especialista_por_subespecialidade(self, detector):
        resultado = detector.detectar_por_dados(
            anos_experiencia=10, subespecialidade="Cardiologia Intervencionista"
        )
        assert resultado.perfil == PerfilMedico.ESPECIALISTA
        assert resultado.confianca >= 0.9

    def test_detecta_senior_por_titulo(self, detector):
        resultado = detector.detectar_por_dados(
            anos_experiencia=8, titulo="Professor Doutor"
        )
        assert resultado.perfil == PerfilMedico.SENIOR
        assert resultado.confianca >= 0.8

    # Testes por mensagem
    def test_detecta_recem_formado_por_mensagem(self, detector):
        resultado = detector.detectar_por_mensagem(
            "Acabei de formar, estou na residência R1"
        )
        assert resultado.perfil == PerfilMedico.RECEM_FORMADO

    def test_detecta_senior_por_mensagem(self, detector):
        resultado = detector.detectar_por_mensagem(
            "Trabalho há décadas, sou preceptor na faculdade"
        )
        assert resultado.perfil == PerfilMedico.SENIOR

    def test_retorna_desconhecido_sem_indicadores(self, detector):
        resultado = detector.detectar_por_mensagem("Oi, tudo bem?")
        assert resultado.perfil == PerfilMedico.DESCONHECIDO

    def test_abordagem_recomendada_existe(self, detector):
        for perfil in PerfilMedico:
            assert perfil.value in detector.ABORDAGENS or perfil == PerfilMedico.DESCONHECIDO


class TestDetectorObjetivo:
    """Testes para DetectorObjetivo."""

    @pytest.fixture
    def detector(self):
        return DetectorObjetivo()

    # Testes por stage
    def test_detecta_prospectar_para_novo(self, detector):
        resultado = detector.detectar_por_stage("novo")
        assert resultado.objetivo == ObjetivoConversa.PROSPECTAR

    def test_detecta_qualificar_para_respondeu(self, detector):
        resultado = detector.detectar_por_stage("respondeu")
        assert resultado.objetivo == ObjetivoConversa.QUALIFICAR

    def test_detecta_ofertar_para_em_conversacao(self, detector):
        resultado = detector.detectar_por_stage("em_conversacao")
        assert resultado.objetivo == ObjetivoConversa.OFERTAR

    def test_detecta_reativar_para_inativo(self, detector):
        resultado = detector.detectar_por_stage("inativo")
        assert resultado.objetivo == ObjetivoConversa.REATIVAR

    def test_detecta_manter_para_ativo(self, detector):
        resultado = detector.detectar_por_stage("ativo")
        assert resultado.objetivo == ObjetivoConversa.MANTER

    # Testes por contexto
    def test_prioriza_objecao_para_negociar(self, detector):
        resultado = detector.detectar_por_contexto(
            mensagens_recentes=["olá"],
            tem_objecao=True,
        )
        assert resultado.objetivo == ObjetivoConversa.NEGOCIAR

    def test_prioriza_reserva_para_fechar(self, detector):
        resultado = detector.detectar_por_contexto(
            mensagens_recentes=["olá"],
            tem_reserva=True,
        )
        assert resultado.objetivo == ObjetivoConversa.FECHAR

    def test_detecta_reativar_por_dias_inativo(self, detector):
        resultado = detector.detectar_por_contexto(
            mensagens_recentes=["olá"],
            dias_desde_ultima_msg=10,
        )
        assert resultado.objetivo == ObjetivoConversa.REATIVAR

    # Testes por mensagem
    def test_detecta_fechar_por_mensagem_aceite(self, detector):
        resultado = detector.detectar_por_mensagem("Quero essa vaga, pode reservar")
        assert resultado.objetivo == ObjetivoConversa.FECHAR

    def test_detecta_qualificar_por_mensagem_interesse(self, detector):
        resultado = detector.detectar_por_mensagem("Como funciona o pagamento?")
        assert resultado.objetivo == ObjetivoConversa.QUALIFICAR

    def test_detecta_negociar_por_mensagem_duvida(self, detector):
        resultado = detector.detectar_por_mensagem("Não sei, preciso pensar")
        assert resultado.objetivo == ObjetivoConversa.NEGOCIAR

    def test_proxima_acao_definida(self, detector):
        for objetivo in ObjetivoConversa:
            assert objetivo.value in detector.PROXIMAS_ACOES


class TestIntegracaoDetectores:
    """Testes de integração entre detectores."""

    def test_detectores_funcionam_juntos(self):
        """Verifica que todos detectores podem ser usados em sequência."""
        mensagem = "O valor está muito baixo, não tenho interesse agora"

        objecao = DetectorObjecao().detectar(mensagem)
        perfil = DetectorPerfil().detectar_por_mensagem(mensagem)
        objetivo = DetectorObjetivo().detectar_por_mensagem(mensagem)

        # Deve detectar objeção
        assert objecao.tem_objecao is True

        # Perfil pode ser desconhecido (mensagem não tem indicadores)
        assert perfil.perfil is not None

        # Deve inferir algum objetivo
        assert objetivo.objetivo is not None
        assert objetivo.proxima_acao is not None

    def test_cenario_medico_senior_com_objecao(self):
        """Cenário real: médico sênior com objeção de preço."""
        objecao = DetectorObjecao().detectar("Paga muito pouco para minha experiência")
        perfil = DetectorPerfil().detectar_por_dados(anos_experiencia=20)
        objetivo = DetectorObjetivo().detectar_por_contexto(
            mensagens_recentes=["Paga muito pouco"],
            tem_objecao=True,
        )

        assert objecao.tipo == TipoObjecao.PRECO
        assert perfil.perfil == PerfilMedico.SENIOR
        assert objetivo.objetivo == ObjetivoConversa.NEGOCIAR
        assert "NUNCA pressione" in perfil.recomendacao_abordagem

    def test_cenario_recem_formado_interessado(self):
        """Cenário real: recém-formado mostrando interesse."""
        objecao = DetectorObjecao().detectar(
            "Acabei a residência, quais vagas tem para cardiologia?"
        )
        perfil = DetectorPerfil().detectar_por_mensagem(
            "Acabei a residência, quais vagas tem?"
        )
        objetivo = DetectorObjetivo().detectar_por_mensagem(
            "Quais vagas tem para cardiologia?"
        )

        # Não deve ter objeção (é interesse)
        assert objecao.tem_objecao is False
        assert perfil.perfil == PerfilMedico.RECEM_FORMADO
        assert objetivo.objetivo == ObjetivoConversa.QUALIFICAR
