# Epic 02: Detectores de Situação

## Objetivo

Criar detectores que classificam automaticamente a situação da conversa para buscar conhecimento relevante: objeções, perfil do médico e objetivo da conversa.

## Contexto

A Julia precisa saber:
1. **Tem objeção?** → Buscar catálogo de respostas
2. **Qual perfil do médico?** → Buscar guia de adaptação
3. **Qual objetivo?** → Ajustar tom e estratégia

Os detectores usam combinação de:
- Regex para padrões conhecidos (rápido)
- LLM para classificação ambígua (quando necessário)

## Pré-requisitos

- [x] E01 concluído (base de conhecimento indexada)
- [x] Claude API funcionando (app/services/llm.py)

---

## Story 2.1: Detector de Objeções

### Objetivo
Detectar quando médico está fazendo uma objeção e classificar o tipo.

### Tarefas

1. **Criar** `app/services/conhecimento/detector_objecao.py`:
```python
"""
Detector de objeções em mensagens de médicos.

Baseado no catálogo: docs/julia/julia_catalogo_objecoes_respostas.md
"""
import re
import logging
from dataclasses import dataclass
from typing import Optional
from enum import Enum

logger = logging.getLogger(__name__)


class TipoObjecao(str, Enum):
    """Tipos de objeção catalogados."""
    PRECO = "preco"           # Valor baixo, pagamento
    TEMPO = "tempo"           # Agenda cheia, sem tempo
    CONFIANCA = "confianca"   # Não conhece, desconfiado
    PROCESSO = "processo"     # Burocracia, documentos
    DISPONIBILIDADE = "disponibilidade"  # Horários não batem
    QUALIDADE = "qualidade"   # Dúvidas sobre hospital/condições
    LEALDADE = "lealdade"     # Já trabalha com outro
    RISCO = "risco"           # Medo de problemas
    MOTIVACAO = "motivacao"   # Não quer mais plantões
    COMUNICACAO = "comunicacao"  # Forma de contato


@dataclass
class DeteccaoObjecao:
    """Resultado da detecção de objeção."""
    tem_objecao: bool
    tipo: Optional[TipoObjecao]
    confianca: float  # 0.0 a 1.0
    trecho_detectado: Optional[str]


class DetectorObjecao:
    """Detecta objeções em mensagens."""

    # Padrões regex por tipo de objeção
    PADROES = {
        TipoObjecao.PRECO: [
            r'\b(pag|valor|pagar?|remunera|ganhar?|pouco|baixo|menos)\b.*\b(pouco|baixo|menos|mais)\b',
            r'\bvocês?\s+pag',
            r'\b(quanto|qual)\s+(é\s+)?(o\s+)?valor\b',
            r'\bpreço\b',
            r'\bo\s+valor\s+é\s+baixo\b',
            r'\bnão\s+compensa\b',
            r'\boutros?\s+pag.*mais\b',
        ],
        TipoObjecao.TEMPO: [
            r'\b(sem|não\s+tenho|falta\s+de?)\s+tempo\b',
            r'\bagenda\s+(cheia|lotada|apertada)\b',
            r'\b(ocupado|corrido|atarefado)\b',
            r'\bnão\s+(posso|consigo|dá)\b',
            r'\bmuito\s+trabalho\b',
            r'\bdepois\b.*\b(fal|conversa|vej)\b',
        ],
        TipoObjecao.CONFIANCA: [
            r'\bnão\s+(conheço|sei|ouvi)\b',
            r'\b(quem|como|onde)\s+é\b.*\b(revoluna|vocês)\b',
            r'\bnunca\s+ouvi\s+falar\b',
            r'\bconfi[aá]\b',
            r'\b(golpe|fraude|fake)\b',
            r'\bcomo\s+(conseguiu|pegou|achou)\s+meu\b',
        ],
        TipoObjecao.PROCESSO: [
            r'\b(burocra|documento|papelada)\b',
            r'\b(muito|demora)\s+(cadastro|processo)\b',
            r'\b(complicado|difícil)\s+(pra|para)\s+(se\s+)?cadastrar\b',
        ],
        TipoObjecao.DISPONIBILIDADE: [
            r'\b(horário|dia|data)\s+(não|n)\s+(bate|serve|funciona)\b',
            r'\bnão\s+tenho\s+disponibilidade\b',
            r'\bsó\s+(tenho|posso)\s+(em|no|na)\b',
            r'\bfinal\s+de\s+semana\b.*\bnão\b',
        ],
        TipoObjecao.QUALIDADE: [
            r'\b(hospital|clínica|unidade)\s+(é\s+)?(boa?|ruim|péssim)\b',
            r'\bestrutura\b',
            r'\binfra\b',
            r'\b(equipamento|material)\b',
            r'\bcondi[çc][õo]es\s+de\s+trabalho\b',
        ],
        TipoObjecao.LEALDADE: [
            r'\b(já|trabalho)\s+(com|pra)\s+(outr|uma)\b',
            r'\btenho\s+(minha|uma)\s+(agência|plataforma|empresa)\b',
            r'\bfidelizado\b',
            r'\bnão\s+pretendo\s+mudar\b',
        ],
        TipoObjecao.RISCO: [
            r'\bmedo\b',
            r'\b(problema|risco|complicação)\b',
            r'\be\s+se\s+(der|acontecer)\b',
            r'\bgarantia\b',
        ],
        TipoObjecao.MOTIVACAO: [
            r'\bnão\s+(quero|preciso)\s+(mais\s+)?plantão\b',
            r'\b(cansado|saturado|cheio)\s+de\s+plantão\b',
            r'\bvou\s+(para|reduzir|diminuir)\b',
            r'\bnão\s+tô\s+(afim|interessado)\b',
        ],
        TipoObjecao.COMUNICACAO: [
            r'\b(onde|como)\s+(conseguiu|pegou|achou)\s+meu\b',
            r'\bnão\s+(gosto|quero)\s+(de\s+)?(msg|whats|ligação)\b',
            r'\bprefiro\s+(email|ligar|pessoalmente)\b',
        ],
    }

    # Padrões de NÃO-objeção (para evitar falso positivo)
    PADROES_EXCLUSAO = [
        r'\bquero\s+(sim|ver|saber)\b',
        r'\bme\s+(interess|manda)\b',
        r'\b(show|legal|boa|beleza|blz)\b',
        r'\bpode\s+(mandar|falar|enviar)\b',
    ]

    def detectar(self, mensagem: str) -> DeteccaoObjecao:
        """
        Detecta se mensagem contém objeção.

        Args:
            mensagem: Texto da mensagem do médico

        Returns:
            Resultado da detecção
        """
        mensagem_lower = mensagem.lower().strip()

        # Verificar padrões de exclusão primeiro
        for padrao in self.PADROES_EXCLUSAO:
            if re.search(padrao, mensagem_lower):
                logger.debug(f"Exclusão detectada: {padrao}")
                return DeteccaoObjecao(
                    tem_objecao=False,
                    tipo=None,
                    confianca=0.9,
                    trecho_detectado=None
                )

        # Buscar por tipo de objeção
        melhor_match = None
        melhor_confianca = 0.0

        for tipo, padroes in self.PADROES.items():
            for padrao in padroes:
                match = re.search(padrao, mensagem_lower)
                if match:
                    # Calcular confiança baseado na especificidade do match
                    confianca = min(0.95, 0.7 + (len(match.group()) / 100))

                    if confianca > melhor_confianca:
                        melhor_confianca = confianca
                        melhor_match = (tipo, match.group())

        if melhor_match:
            tipo, trecho = melhor_match
            logger.info(f"Objeção detectada: {tipo.value} (confiança: {melhor_confianca:.2f})")
            return DeteccaoObjecao(
                tem_objecao=True,
                tipo=tipo,
                confianca=melhor_confianca,
                trecho_detectado=trecho
            )

        # Nenhuma objeção detectada
        return DeteccaoObjecao(
            tem_objecao=False,
            tipo=None,
            confianca=0.8,  # Confiança de que NÃO é objeção
            trecho_detectado=None
        )

    def detectar_multiplas(self, mensagem: str) -> list[DeteccaoObjecao]:
        """
        Detecta múltiplas objeções na mesma mensagem.

        Args:
            mensagem: Texto da mensagem

        Returns:
            Lista de objeções detectadas
        """
        mensagem_lower = mensagem.lower().strip()
        objecoes = []
        tipos_encontrados = set()

        for tipo, padroes in self.PADROES.items():
            for padrao in padroes:
                match = re.search(padrao, mensagem_lower)
                if match and tipo not in tipos_encontrados:
                    confianca = min(0.95, 0.7 + (len(match.group()) / 100))
                    objecoes.append(DeteccaoObjecao(
                        tem_objecao=True,
                        tipo=tipo,
                        confianca=confianca,
                        trecho_detectado=match.group()
                    ))
                    tipos_encontrados.add(tipo)

        return objecoes
```

### DoD

- [ ] `DetectorObjecao` implementado
- [ ] 10 tipos de objeção definidos
- [ ] Padrões regex para cada tipo
- [ ] Padrões de exclusão (falso positivo)
- [ ] Método `detectar()` retorna `DeteccaoObjecao`
- [ ] Método `detectar_multiplas()` para mensagens complexas
- [ ] Confiança calculada (0.0 a 1.0)

### Testes

```python
# tests/conhecimento/test_detector_objecao.py
import pytest
from app.services.conhecimento.detector_objecao import (
    DetectorObjecao,
    TipoObjecao
)

@pytest.fixture
def detector():
    return DetectorObjecao()

class TestDetectarObjecoes:
    """Testes de detecção de objeções."""

    def test_detecta_objecao_preco(self, detector):
        """Detecta objeção de preço."""
        result = detector.detectar("Vocês pagam muito pouco")

        assert result.tem_objecao is True
        assert result.tipo == TipoObjecao.PRECO
        assert result.confianca > 0.7

    def test_detecta_objecao_tempo(self, detector):
        """Detecta objeção de tempo."""
        result = detector.detectar("Não tenho tempo, agenda muito cheia")

        assert result.tem_objecao is True
        assert result.tipo == TipoObjecao.TEMPO

    def test_detecta_objecao_confianca(self, detector):
        """Detecta objeção de confiança."""
        result = detector.detectar("Nunca ouvi falar da Revoluna")

        assert result.tem_objecao is True
        assert result.tipo == TipoObjecao.CONFIANCA

    def test_detecta_objecao_lealdade(self, detector):
        """Detecta objeção de lealdade."""
        result = detector.detectar("Já trabalho com outra empresa")

        assert result.tem_objecao is True
        assert result.tipo == TipoObjecao.LEALDADE

    def test_detecta_objecao_motivacao(self, detector):
        """Detecta objeção de motivação."""
        result = detector.detectar("Não quero mais plantão, estou saturado")

        assert result.tem_objecao is True
        assert result.tipo == TipoObjecao.MOTIVACAO

    def test_nao_detecta_mensagem_positiva(self, detector):
        """Não detecta objeção em mensagem positiva."""
        result = detector.detectar("Show! Me manda as vagas")

        assert result.tem_objecao is False

    def test_nao_detecta_pergunta_informativa(self, detector):
        """Não detecta objeção em pergunta informativa."""
        result = detector.detectar("Quero saber mais sobre as vagas")

        assert result.tem_objecao is False

    def test_detecta_multiplas_objecoes(self, detector):
        """Detecta múltiplas objeções na mesma mensagem."""
        result = detector.detectar_multiplas(
            "Vocês pagam pouco e ainda não tenho tempo"
        )

        assert len(result) >= 2
        tipos = {r.tipo for r in result}
        assert TipoObjecao.PRECO in tipos
        assert TipoObjecao.TEMPO in tipos

    def test_confianca_varia(self, detector):
        """Confiança varia com match."""
        r1 = detector.detectar("pagam pouco")  # Match curto
        r2 = detector.detectar("o valor que vocês pagam é muito baixo")  # Match longo

        assert r2.confianca > r1.confianca
```

---

## Story 2.2: Detector de Perfil de Médico

### Objetivo
Classificar perfil do médico baseado em informações do contexto e padrões de comunicação.

### Tarefas

1. **Criar** `app/services/conhecimento/detector_perfil.py`:
```python
"""
Detector de perfil de médico.

Baseado no guia: docs/julia/guia_adaptacao_perfis_medicos.md
"""
import re
import logging
from dataclasses import dataclass
from typing import Optional
from enum import Enum
from datetime import datetime

logger = logging.getLogger(__name__)


class PerfilMedico(str, Enum):
    """Perfis de médico catalogados."""
    RECEM_FORMADO = "recem_formado"      # 0-2 anos
    EM_DESENVOLVIMENTO = "em_desenvolvimento"  # 2-7 anos
    EXPERIENTE = "experiente"            # 7-15 anos
    SENIOR = "senior"                    # 15+ anos
    ESPECIALISTA = "especialista"        # Subespecialista
    EM_TRANSICAO = "em_transicao"        # Mudando de área


@dataclass
class DeteccaoPerfil:
    """Resultado da detecção de perfil."""
    perfil: PerfilMedico
    confianca: float
    indicadores: list[str]  # O que levou à classificação


class DetectorPerfil:
    """Detecta perfil do médico."""

    # Anos de formação por perfil
    ANOS_PERFIL = {
        (0, 2): PerfilMedico.RECEM_FORMADO,
        (2, 7): PerfilMedico.EM_DESENVOLVIMENTO,
        (7, 15): PerfilMedico.EXPERIENTE,
        (15, 100): PerfilMedico.SENIOR,
    }

    # Padrões de comunicação por perfil
    PADROES_COMUNICACAO = {
        PerfilMedico.RECEM_FORMADO: [
            r'\b(estou|to)\s+(aprendendo|começando|iniciando)\b',
            r'\bprimeiros?\s+(plantão|plantões)\b',
            r'\b(r1|r2|residente)\b',
            r'\brecém\s*(formado|formada)?\b',
        ],
        PerfilMedico.SENIOR: [
            r'\b(\d{2,})\s*anos\s*(de)?\s*(experiência|profiss)\b',
            r'\b(professor|docente|preceptor)\b',
            r'\bna\s+minha\s+época\b',
            r'\b(coordeno|supervisiono|gerencio)\b',
            r'\bequipe\s+(que)?\s*(coordeno|minha)\b',
        ],
        PerfilMedico.ESPECIALISTA: [
            r'\b(subespecialidade|subespecialista)\b',
            r'\b(fellow|fellowship)\b',
            r'\b(mestrado|doutorado|phd)\b',
            r'\bpesquisa\s+(em|sobre)\b',
        ],
        PerfilMedico.EM_TRANSICAO: [
            r'\b(mudando|transição|trocar)\s+(de)?\s*(área|especialidade)\b',
            r'\b(cansei|cansado)\s+(de|da)\s+(emergência|uti|plantão)\b',
            r'\bquero\s+(ir\s+para|migrar|mudar)\b',
        ],
    }

    def detectar_por_contexto(
        self,
        anos_formacao: Optional[int] = None,
        especialidade: Optional[str] = None,
        historico_mensagens: Optional[list[str]] = None
    ) -> DeteccaoPerfil:
        """
        Detecta perfil baseado em contexto disponível.

        Args:
            anos_formacao: Anos desde formação (se conhecido)
            especialidade: Especialidade do médico
            historico_mensagens: Mensagens anteriores

        Returns:
            Perfil detectado
        """
        indicadores = []
        perfil = None
        confianca = 0.5

        # 1. Por anos de formação (mais confiável)
        if anos_formacao is not None:
            for (min_anos, max_anos), p in self.ANOS_PERFIL.items():
                if min_anos <= anos_formacao < max_anos:
                    perfil = p
                    confianca = 0.9
                    indicadores.append(f"{anos_formacao} anos de formação")
                    break

        # 2. Por padrões no histórico (menos confiável)
        if historico_mensagens:
            texto_completo = " ".join(historico_mensagens).lower()

            for p, padroes in self.PADROES_COMUNICACAO.items():
                for padrao in padroes:
                    if re.search(padrao, texto_completo):
                        if perfil is None:
                            perfil = p
                            confianca = 0.7
                        indicadores.append(f"Padrão: {padrao[:30]}...")

        # 3. Fallback para "Em Desenvolvimento" (mais comum)
        if perfil is None:
            perfil = PerfilMedico.EM_DESENVOLVIMENTO
            confianca = 0.4
            indicadores.append("Default (sem informações)")

        logger.info(f"Perfil detectado: {perfil.value} (confiança: {confianca:.2f})")
        return DeteccaoPerfil(
            perfil=perfil,
            confianca=confianca,
            indicadores=indicadores
        )

    def calcular_anos_formacao(self, ano_formatura: Optional[int]) -> Optional[int]:
        """
        Calcula anos desde a formatura.

        Args:
            ano_formatura: Ano de formatura (ex: 2015)

        Returns:
            Anos de experiência ou None
        """
        if ano_formatura is None:
            return None

        return datetime.now().year - ano_formatura

    def detectar_por_mensagem(self, mensagem: str) -> Optional[DeteccaoPerfil]:
        """
        Tenta detectar perfil por uma única mensagem.

        Útil para ajustar perfil em tempo real.

        Args:
            mensagem: Mensagem do médico

        Returns:
            Perfil se detectado, None se inconclusivo
        """
        mensagem_lower = mensagem.lower()

        for perfil, padroes in self.PADROES_COMUNICACAO.items():
            for padrao in padroes:
                if re.search(padrao, mensagem_lower):
                    return DeteccaoPerfil(
                        perfil=perfil,
                        confianca=0.75,
                        indicadores=[f"Mensagem: {padrao[:30]}..."]
                    )

        return None
```

### DoD

- [ ] `DetectorPerfil` implementado
- [ ] 6 perfis definidos (PerfilMedico enum)
- [ ] Detecção por anos de formação
- [ ] Detecção por padrões de comunicação
- [ ] Fallback para perfil mais comum
- [ ] Confiança calculada

### Testes

```python
# tests/conhecimento/test_detector_perfil.py
import pytest
from app.services.conhecimento.detector_perfil import (
    DetectorPerfil,
    PerfilMedico
)

@pytest.fixture
def detector():
    return DetectorPerfil()

class TestDetectarPerfil:
    """Testes de detecção de perfil."""

    def test_detecta_recem_formado_por_anos(self, detector):
        """Detecta recém-formado por anos."""
        result = detector.detectar_por_contexto(anos_formacao=1)

        assert result.perfil == PerfilMedico.RECEM_FORMADO
        assert result.confianca >= 0.9

    def test_detecta_senior_por_anos(self, detector):
        """Detecta sênior por anos."""
        result = detector.detectar_por_contexto(anos_formacao=20)

        assert result.perfil == PerfilMedico.SENIOR
        assert result.confianca >= 0.9

    def test_detecta_senior_por_padrao(self, detector):
        """Detecta sênior por padrão de comunicação."""
        result = detector.detectar_por_contexto(
            historico_mensagens=["Coordeno uma equipe de 10 médicos"]
        )

        assert result.perfil == PerfilMedico.SENIOR
        assert result.confianca >= 0.7

    def test_detecta_recem_formado_por_padrao(self, detector):
        """Detecta recém-formado por padrão."""
        result = detector.detectar_por_contexto(
            historico_mensagens=["Estou começando, é meu primeiro plantão"]
        )

        assert result.perfil == PerfilMedico.RECEM_FORMADO

    def test_detecta_especialista(self, detector):
        """Detecta especialista/subespecialista."""
        result = detector.detectar_por_contexto(
            historico_mensagens=["Fiz fellowship em cardio intervencionista"]
        )

        assert result.perfil == PerfilMedico.ESPECIALISTA

    def test_detecta_transicao(self, detector):
        """Detecta médico em transição."""
        result = detector.detectar_por_contexto(
            historico_mensagens=["Cansei da UTI, quero migrar para ambulatório"]
        )

        assert result.perfil == PerfilMedico.EM_TRANSICAO

    def test_fallback_sem_info(self, detector):
        """Fallback para em_desenvolvimento sem info."""
        result = detector.detectar_por_contexto()

        assert result.perfil == PerfilMedico.EM_DESENVOLVIMENTO
        assert result.confianca < 0.5

    def test_anos_prevalece_sobre_padrao(self, detector):
        """Anos de formação prevalece sobre padrão."""
        result = detector.detectar_por_contexto(
            anos_formacao=1,
            historico_mensagens=["Coordeno uma equipe"]  # Padrão de sênior
        )

        # Anos (1) indica recém-formado, deve prevalecer
        assert result.perfil == PerfilMedico.RECEM_FORMADO

    def test_calcula_anos_formacao(self, detector):
        """Calcula anos desde formatura."""
        from datetime import datetime
        ano_atual = datetime.now().year

        anos = detector.calcular_anos_formacao(ano_atual - 5)
        assert anos == 5
```

---

## Story 2.3: Detector de Objetivo da Conversa

### Objetivo
Classificar objetivo atual da conversa (prospectar, qualificar, ofertar, negociar, manter).

### Tarefas

1. **Criar** `app/services/conhecimento/detector_objetivo.py`:
```python
"""
Detector de objetivo da conversa.

Baseado no sistema de prompts avançado.
"""
import logging
from dataclasses import dataclass
from typing import Optional
from enum import Enum

logger = logging.getLogger(__name__)


class ObjetivoConversa(str, Enum):
    """Objetivos possíveis da conversa."""
    PROSPECTAR = "prospectar"      # Primeiro contato, conhecer
    QUALIFICAR = "qualificar"      # Entender perfil e interesse
    OFERTAR = "ofertar"            # Apresentar vagas específicas
    NEGOCIAR = "negociar"          # Ajustar condições
    FECHAR = "fechar"              # Confirmar reserva
    MANTER = "manter"              # Relacionamento pós-reserva


@dataclass
class DeteccaoObjetivo:
    """Resultado da detecção de objetivo."""
    objetivo: ObjetivoConversa
    confianca: float
    motivo: str


class DetectorObjetivo:
    """Detecta objetivo da conversa."""

    def detectar(
        self,
        primeira_mensagem: bool,
        tem_reserva_ativa: bool,
        num_interacoes: int,
        medico_mostrou_interesse: bool,
        objecao_detectada: bool,
        vaga_oferecida: bool
    ) -> DeteccaoObjetivo:
        """
        Detecta objetivo baseado no estado da conversa.

        Args:
            primeira_mensagem: Se é a primeira interação
            tem_reserva_ativa: Se médico tem reserva confirmada
            num_interacoes: Número de trocas de mensagem
            medico_mostrou_interesse: Se médico demonstrou interesse
            objecao_detectada: Se última mensagem tem objeção
            vaga_oferecida: Se já oferecemos vaga específica

        Returns:
            Objetivo detectado
        """
        # 1. Primeira mensagem = prospectar
        if primeira_mensagem:
            return DeteccaoObjetivo(
                objetivo=ObjetivoConversa.PROSPECTAR,
                confianca=0.95,
                motivo="Primeira interação"
            )

        # 2. Tem reserva = manter relacionamento
        if tem_reserva_ativa:
            return DeteccaoObjetivo(
                objetivo=ObjetivoConversa.MANTER,
                confianca=0.9,
                motivo="Médico já tem reserva ativa"
            )

        # 3. Objeção detectada = negociar
        if objecao_detectada:
            return DeteccaoObjetivo(
                objetivo=ObjetivoConversa.NEGOCIAR,
                confianca=0.85,
                motivo="Médico fez objeção"
            )

        # 4. Interesse + vaga oferecida = fechar
        if medico_mostrou_interesse and vaga_oferecida:
            return DeteccaoObjetivo(
                objetivo=ObjetivoConversa.FECHAR,
                confianca=0.8,
                motivo="Médico interessado e vaga oferecida"
            )

        # 5. Interesse sem vaga = ofertar
        if medico_mostrou_interesse:
            return DeteccaoObjetivo(
                objetivo=ObjetivoConversa.OFERTAR,
                confianca=0.8,
                motivo="Médico demonstrou interesse"
            )

        # 6. Poucas interações = qualificar
        if num_interacoes < 4:
            return DeteccaoObjetivo(
                objetivo=ObjetivoConversa.QUALIFICAR,
                confianca=0.7,
                motivo="Poucas interações, ainda conhecendo"
            )

        # 7. Default = ofertar (já conhecemos o médico)
        return DeteccaoObjetivo(
            objetivo=ObjetivoConversa.OFERTAR,
            confianca=0.6,
            motivo="Default após qualificação"
        )

    def detectar_interesse(self, mensagem: str) -> bool:
        """
        Detecta se mensagem indica interesse.

        Args:
            mensagem: Mensagem do médico

        Returns:
            True se demonstra interesse
        """
        padroes_interesse = [
            "interessado", "interesse",
            "quero", "queria",
            "me manda", "manda aí",
            "pode", "pode sim",
            "show", "legal", "boa",
            "quais", "tem vagas",
            "disponível", "quando",
        ]

        mensagem_lower = mensagem.lower()
        return any(p in mensagem_lower for p in padroes_interesse)
```

### DoD

- [ ] `DetectorObjetivo` implementado
- [ ] 6 objetivos definidos (ObjetivoConversa enum)
- [ ] Lógica de detecção baseada em estado
- [ ] Método `detectar_interesse()` auxiliar
- [ ] Confiança calculada

### Testes

```python
# tests/conhecimento/test_detector_objetivo.py
import pytest
from app.services.conhecimento.detector_objetivo import (
    DetectorObjetivo,
    ObjetivoConversa
)

@pytest.fixture
def detector():
    return DetectorObjetivo()

class TestDetectarObjetivo:
    """Testes de detecção de objetivo."""

    def test_primeira_mensagem_prospectar(self, detector):
        """Primeira mensagem = prospectar."""
        result = detector.detectar(
            primeira_mensagem=True,
            tem_reserva_ativa=False,
            num_interacoes=0,
            medico_mostrou_interesse=False,
            objecao_detectada=False,
            vaga_oferecida=False
        )

        assert result.objetivo == ObjetivoConversa.PROSPECTAR

    def test_reserva_ativa_manter(self, detector):
        """Reserva ativa = manter relacionamento."""
        result = detector.detectar(
            primeira_mensagem=False,
            tem_reserva_ativa=True,
            num_interacoes=10,
            medico_mostrou_interesse=True,
            objecao_detectada=False,
            vaga_oferecida=True
        )

        assert result.objetivo == ObjetivoConversa.MANTER

    def test_objecao_negociar(self, detector):
        """Objeção detectada = negociar."""
        result = detector.detectar(
            primeira_mensagem=False,
            tem_reserva_ativa=False,
            num_interacoes=5,
            medico_mostrou_interesse=True,
            objecao_detectada=True,
            vaga_oferecida=True
        )

        assert result.objetivo == ObjetivoConversa.NEGOCIAR

    def test_interesse_com_vaga_fechar(self, detector):
        """Interesse + vaga oferecida = fechar."""
        result = detector.detectar(
            primeira_mensagem=False,
            tem_reserva_ativa=False,
            num_interacoes=5,
            medico_mostrou_interesse=True,
            objecao_detectada=False,
            vaga_oferecida=True
        )

        assert result.objetivo == ObjetivoConversa.FECHAR

    def test_interesse_sem_vaga_ofertar(self, detector):
        """Interesse sem vaga = ofertar."""
        result = detector.detectar(
            primeira_mensagem=False,
            tem_reserva_ativa=False,
            num_interacoes=5,
            medico_mostrou_interesse=True,
            objecao_detectada=False,
            vaga_oferecida=False
        )

        assert result.objetivo == ObjetivoConversa.OFERTAR

    def test_poucas_interacoes_qualificar(self, detector):
        """Poucas interações = qualificar."""
        result = detector.detectar(
            primeira_mensagem=False,
            tem_reserva_ativa=False,
            num_interacoes=2,
            medico_mostrou_interesse=False,
            objecao_detectada=False,
            vaga_oferecida=False
        )

        assert result.objetivo == ObjetivoConversa.QUALIFICAR

    def test_detecta_interesse_positivo(self, detector):
        """Detecta interesse em mensagem positiva."""
        assert detector.detectar_interesse("Quero ver as vagas") is True
        assert detector.detectar_interesse("Show, me manda aí") is True
        assert detector.detectar_interesse("Pode sim, estou interessado") is True

    def test_detecta_interesse_negativo(self, detector):
        """Não detecta interesse em mensagem neutra."""
        assert detector.detectar_interesse("Não tenho tempo") is False
        assert detector.detectar_interesse("Quem é você?") is False
```

---

## Story 2.4: Orquestrador de Detecção

### Objetivo
Criar orquestrador que coordena todos os detectores e retorna análise completa da situação.

### Tarefas

1. **Criar** `app/services/conhecimento/orquestrador.py`:
```python
"""
Orquestrador de detecção de situação.

Coordena detectores e retorna análise completa.
"""
import logging
from dataclasses import dataclass
from typing import Optional

from .detector_objecao import DetectorObjecao, DeteccaoObjecao, TipoObjecao
from .detector_perfil import DetectorPerfil, DeteccaoPerfil, PerfilMedico
from .detector_objetivo import DetectorObjetivo, DeteccaoObjetivo, ObjetivoConversa

logger = logging.getLogger(__name__)


@dataclass
class ContextoMedico:
    """Contexto conhecido sobre o médico."""
    nome: Optional[str] = None
    especialidade: Optional[str] = None
    anos_formacao: Optional[int] = None
    tem_reserva_ativa: bool = False
    historico_mensagens: Optional[list[str]] = None


@dataclass
class AnaliseConversacional:
    """Análise completa da situação da conversa."""
    # Detecções
    objecao: DeteccaoObjecao
    perfil: DeteccaoPerfil
    objetivo: DeteccaoObjetivo

    # Flags de ação
    precisa_conhecimento_objecao: bool
    precisa_conhecimento_perfil: bool
    precisa_exemplos: bool

    # Resumo para log
    resumo: str


class OrquestradorDeteccao:
    """
    Orquestra detectores para análise completa.

    Uso:
        orquestrador = OrquestradorDeteccao()
        analise = orquestrador.analisar(
            mensagem="Vocês pagam muito pouco",
            contexto=ContextoMedico(anos_formacao=20),
            primeira_mensagem=False,
            num_interacoes=3
        )
    """

    def __init__(self):
        self.detector_objecao = DetectorObjecao()
        self.detector_perfil = DetectorPerfil()
        self.detector_objetivo = DetectorObjetivo()

    def analisar(
        self,
        mensagem: str,
        contexto: ContextoMedico,
        primeira_mensagem: bool = False,
        num_interacoes: int = 0,
        vaga_oferecida: bool = False
    ) -> AnaliseConversacional:
        """
        Analisa situação completa da conversa.

        Args:
            mensagem: Última mensagem do médico
            contexto: Contexto conhecido
            primeira_mensagem: Se é primeira interação
            num_interacoes: Total de trocas
            vaga_oferecida: Se já oferecemos vaga

        Returns:
            Análise completa
        """
        # 1. Detectar objeção
        objecao = self.detector_objecao.detectar(mensagem)

        # 2. Detectar perfil
        perfil = self.detector_perfil.detectar_por_contexto(
            anos_formacao=contexto.anos_formacao,
            especialidade=contexto.especialidade,
            historico_mensagens=contexto.historico_mensagens
        )

        # Tentar refinar por mensagem atual
        perfil_msg = self.detector_perfil.detectar_por_mensagem(mensagem)
        if perfil_msg and perfil_msg.confianca > perfil.confianca:
            perfil = perfil_msg

        # 3. Detectar interesse para objetivo
        medico_mostrou_interesse = self.detector_objetivo.detectar_interesse(mensagem)

        # 4. Detectar objetivo
        objetivo = self.detector_objetivo.detectar(
            primeira_mensagem=primeira_mensagem,
            tem_reserva_ativa=contexto.tem_reserva_ativa,
            num_interacoes=num_interacoes,
            medico_mostrou_interesse=medico_mostrou_interesse,
            objecao_detectada=objecao.tem_objecao,
            vaga_oferecida=vaga_oferecida
        )

        # 5. Determinar necessidades de conhecimento
        precisa_conhecimento_objecao = (
            objecao.tem_objecao and objecao.confianca > 0.6
        )

        precisa_conhecimento_perfil = (
            perfil.perfil in [PerfilMedico.SENIOR, PerfilMedico.ESPECIALISTA, PerfilMedico.EM_TRANSICAO]
            or perfil.confianca < 0.6
        )

        precisa_exemplos = (
            objetivo.objetivo in [ObjetivoConversa.NEGOCIAR, ObjetivoConversa.FECHAR]
        )

        # 6. Gerar resumo
        resumo = self._gerar_resumo(objecao, perfil, objetivo)

        logger.info(f"Análise: {resumo}")

        return AnaliseConversacional(
            objecao=objecao,
            perfil=perfil,
            objetivo=objetivo,
            precisa_conhecimento_objecao=precisa_conhecimento_objecao,
            precisa_conhecimento_perfil=precisa_conhecimento_perfil,
            precisa_exemplos=precisa_exemplos,
            resumo=resumo
        )

    def _gerar_resumo(
        self,
        objecao: DeteccaoObjecao,
        perfil: DeteccaoPerfil,
        objetivo: DeteccaoObjetivo
    ) -> str:
        """Gera resumo textual da análise."""
        partes = []

        if objecao.tem_objecao:
            partes.append(f"Objeção:{objecao.tipo.value}")
        partes.append(f"Perfil:{perfil.perfil.value}")
        partes.append(f"Objetivo:{objetivo.objetivo.value}")

        return " | ".join(partes)
```

2. **Atualizar** `app/services/conhecimento/__init__.py`:
```python
"""Módulo de conhecimento dinâmico para Julia."""
from .indexador import IndexadorConhecimento
from .buscador import BuscadorConhecimento
from .orquestrador import (
    OrquestradorDeteccao,
    ContextoMedico,
    AnaliseConversacional
)
from .detector_objecao import DetectorObjecao, TipoObjecao
from .detector_perfil import DetectorPerfil, PerfilMedico
from .detector_objetivo import DetectorObjetivo, ObjetivoConversa

__all__ = [
    "IndexadorConhecimento",
    "BuscadorConhecimento",
    "OrquestradorDeteccao",
    "ContextoMedico",
    "AnaliseConversacional",
    "DetectorObjecao",
    "TipoObjecao",
    "DetectorPerfil",
    "PerfilMedico",
    "DetectorObjetivo",
    "ObjetivoConversa",
]
```

### DoD

- [ ] `OrquestradorDeteccao` implementado
- [ ] Coordena 3 detectores
- [ ] `ContextoMedico` dataclass para input
- [ ] `AnaliseConversacional` dataclass para output
- [ ] Flags de necessidade de conhecimento
- [ ] Resumo textual para logs
- [ ] Exports atualizados em `__init__.py`

### Testes

```python
# tests/conhecimento/test_orquestrador.py
import pytest
from app.services.conhecimento import (
    OrquestradorDeteccao,
    ContextoMedico,
    TipoObjecao,
    PerfilMedico,
    ObjetivoConversa
)

@pytest.fixture
def orquestrador():
    return OrquestradorDeteccao()

class TestOrquestradorDeteccao:
    """Testes do orquestrador."""

    def test_analise_primeira_mensagem(self, orquestrador):
        """Analisa primeira mensagem."""
        result = orquestrador.analisar(
            mensagem="Oi, tudo bem?",
            contexto=ContextoMedico(),
            primeira_mensagem=True
        )

        assert result.objetivo.objetivo == ObjetivoConversa.PROSPECTAR
        assert result.objecao.tem_objecao is False

    def test_analise_objecao_preco(self, orquestrador):
        """Analisa objeção de preço."""
        result = orquestrador.analisar(
            mensagem="Vocês pagam muito pouco",
            contexto=ContextoMedico(anos_formacao=20),
            primeira_mensagem=False,
            num_interacoes=5
        )

        assert result.objecao.tem_objecao is True
        assert result.objecao.tipo == TipoObjecao.PRECO
        assert result.objetivo.objetivo == ObjetivoConversa.NEGOCIAR
        assert result.perfil.perfil == PerfilMedico.SENIOR
        assert result.precisa_conhecimento_objecao is True

    def test_analise_senior_precisa_conhecimento(self, orquestrador):
        """Médico sênior precisa conhecimento de perfil."""
        result = orquestrador.analisar(
            mensagem="Me manda as vagas",
            contexto=ContextoMedico(anos_formacao=25),
            primeira_mensagem=False,
            num_interacoes=3
        )

        assert result.perfil.perfil == PerfilMedico.SENIOR
        assert result.precisa_conhecimento_perfil is True

    def test_analise_interesse_ofertar(self, orquestrador):
        """Médico interessado = ofertar."""
        result = orquestrador.analisar(
            mensagem="Quero ver as vagas disponíveis",
            contexto=ContextoMedico(),
            primeira_mensagem=False,
            num_interacoes=3,
            vaga_oferecida=False
        )

        assert result.objetivo.objetivo == ObjetivoConversa.OFERTAR

    def test_resumo_gerado(self, orquestrador):
        """Resumo é gerado corretamente."""
        result = orquestrador.analisar(
            mensagem="Vocês pagam pouco",
            contexto=ContextoMedico(anos_formacao=20),
            primeira_mensagem=False,
            num_interacoes=5
        )

        assert "Objeção:preco" in result.resumo
        assert "Perfil:senior" in result.resumo
        assert "Objetivo:negociar" in result.resumo
```

---

## Checklist do Épico

- [ ] **S13.E2.1** - Detector de objeções
- [ ] **S13.E2.2** - Detector de perfil
- [ ] **S13.E2.3** - Detector de objetivo
- [ ] **S13.E2.4** - Orquestrador
- [ ] Todos os testes passando
- [ ] 10 tipos de objeção detectados
- [ ] 6 perfis detectados
- [ ] 6 objetivos detectados
