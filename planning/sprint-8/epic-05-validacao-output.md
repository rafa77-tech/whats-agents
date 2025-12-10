# Epic 05: Validacao de Output

## Prioridade: P1 (Importante)

## Objetivo

> **Criar sistema de validacao para garantir que respostas da Julia nunca revelem que ela e IA.**

Este e um dos criterios mais criticos do projeto: medicos nao devem perceber que estao falando com uma IA. Precisamos de uma camada de validacao ANTES de enviar qualquer mensagem.

---

## Problema

Sem validacao, a Julia pode:
1. Dizer "como uma IA" ou "como assistente virtual"
2. Responder perguntas sobre ser bot de forma evasiva
3. Usar linguagem muito robotica
4. Enviar respostas com formato de lista/bullet points
5. Usar linguagem formal demais

---

## Arquitetura Proposta

```
┌─────────────────────────────────────────────────────────────────┐
│                    VALIDACAO DE OUTPUT                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  RESPOSTA GERADA PELO LLM                                       │
│        │                                                         │
│        ▼                                                         │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              VALIDADORES                                 │   │
│  │                                                          │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │   │
│  │  │ Detector    │  │ Formato     │  │ Linguagem   │     │   │
│  │  │ de IA       │  │ Validator   │  │ Validator   │     │   │
│  │  │             │  │             │  │             │     │   │
│  │  │ • "sou IA"  │  │ • bullets   │  │ • formal    │     │   │
│  │  │ • "bot"     │  │ • listas    │  │ • corporat. │     │   │
│  │  │ • "assist." │  │ • markdown  │  │ • robotico  │     │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘     │   │
│  │                                                          │   │
│  └─────────────────────────────────────────────────────────┘   │
│        │                                                         │
│        ▼                                                         │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              RESULTADO                                   │   │
│  │                                                          │   │
│  │  PASSOU → Envia resposta                                │   │
│  │  FALHOU → Re-gera ou alerta gestor                      │   │
│  │                                                          │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Stories

---

# S8.E5.1 - Criar detector de revelacao de IA

## Objetivo

> **Detectar padroes que revelam que Julia e uma IA.**

## Codigo Esperado

**Arquivo:** `app/services/validacao_output.py`

```python
"""
Validacao de output para garantir que Julia nunca revele ser IA.
"""
import re
import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class ValidacaoResult:
    """Resultado da validacao."""
    valido: bool
    motivo: Optional[str] = None
    tipo_violacao: Optional[str] = None
    trecho_problematico: Optional[str] = None
    severidade: str = "baixa"  # baixa, media, alta, critica


# Padroes que indicam revelacao de IA
PADROES_REVELACAO_IA = [
    # Mencoes diretas
    (r'\b(sou|como)\s+(uma?\s+)?(ia|intelig[eê]ncia\s+artificial)\b', 'mencao_ia', 'critica'),
    (r'\b(sou|como)\s+(um?\s+)?(bot|rob[oô]|chatbot)\b', 'mencao_bot', 'critica'),
    (r'\b(sou|como)\s+(um?\s+)?assistente\s+virtual\b', 'mencao_assistente', 'critica'),
    (r'\bassistente\s+de\s+ia\b', 'mencao_assistente_ia', 'critica'),
    (r'\bmodelo\s+de\s+linguagem\b', 'mencao_modelo', 'critica'),
    (r'\b(criado|desenvolvido|treinado)\s+(pela|por)\s+(anthropic|openai|google)\b', 'mencao_empresa', 'critica'),

    # Frases evasivas sobre ser IA
    (r'n[aã]o\s+sou\s+(exatamente\s+)?(uma?\s+)?pessoa', 'evasiva_pessoa', 'alta'),
    (r'n[aã]o\s+tenho\s+(um\s+)?corpo\s+f[ií]sico', 'evasiva_corpo', 'alta'),
    (r'existo\s+apenas\s+(como|no)\s+(texto|digital)', 'evasiva_existencia', 'alta'),

    # Limitacoes de IA
    (r'minhas?\s+capacidades?\s+(s[aã]o|est[aã]o)\s+limitadas?', 'limitacao_ia', 'media'),
    (r'n[aã]o\s+tenho\s+acesso\s+a\s+informa[çc][oõ]es\s+(em\s+tempo\s+real|atuais)', 'limitacao_tempo_real', 'media'),
    (r'meu\s+conhecimento\s+(foi\s+)?cortado\s+em', 'limitacao_conhecimento', 'alta'),

    # Respostas roboticas
    (r'^(claro|certamente|com\s+prazer)[,!]\s+vou', 'resposta_robotica', 'baixa'),
    (r'como\s+posso\s+ajud[aá]-l[ao]\s+hoje', 'resposta_robotica', 'baixa'),
    (r'estou\s+aqui\s+para\s+ajudar', 'resposta_robotica', 'baixa'),
]


def detectar_revelacao_ia(texto: str) -> ValidacaoResult:
    """
    Detecta se o texto revela que Julia e IA.

    Args:
        texto: Resposta a validar

    Returns:
        ValidacaoResult com detalhes da validacao
    """
    texto_lower = texto.lower()

    for padrao, tipo, severidade in PADROES_REVELACAO_IA:
        match = re.search(padrao, texto_lower)
        if match:
            logger.warning(
                f"Revelacao de IA detectada: tipo={tipo}, "
                f"trecho='{match.group()}'"
            )
            return ValidacaoResult(
                valido=False,
                motivo=f"Texto revela que Julia e IA ({tipo})",
                tipo_violacao=tipo,
                trecho_problematico=match.group(),
                severidade=severidade
            )

    return ValidacaoResult(valido=True)


# Padroes de formato proibido
PADROES_FORMATO_PROIBIDO = [
    # Bullet points e listas
    (r'^\s*[-•*]\s+', 'bullet_point', 'media'),
    (r'^\s*\d+[.)]\s+', 'lista_numerada', 'media'),
    (r'\n\s*[-•*]\s+', 'bullet_point_inline', 'media'),
    (r'\n\s*\d+[.)]\s+', 'lista_inline', 'media'),

    # Markdown
    (r'\*\*[^*]+\*\*', 'markdown_bold', 'baixa'),
    (r'__[^_]+__', 'markdown_bold_alt', 'baixa'),
    (r'`[^`]+`', 'markdown_code', 'baixa'),
    (r'#{1,6}\s+', 'markdown_header', 'media'),

    # Estrutura muito formal
    (r'(prezado|estimado|caro)\s+(dr|doutor|senhor)', 'saudacao_formal', 'media'),
    (r'(atenciosamente|cordialmente|respeitosamente)', 'despedida_formal', 'media'),
]


def detectar_formato_proibido(texto: str) -> ValidacaoResult:
    """
    Detecta formatos proibidos (listas, markdown, etc).

    Args:
        texto: Resposta a validar

    Returns:
        ValidacaoResult com detalhes
    """
    for padrao, tipo, severidade in PADROES_FORMATO_PROIBIDO:
        match = re.search(padrao, texto, re.MULTILINE)
        if match:
            logger.warning(
                f"Formato proibido detectado: tipo={tipo}, "
                f"trecho='{match.group()[:50]}'"
            )
            return ValidacaoResult(
                valido=False,
                motivo=f"Formato proibido ({tipo})",
                tipo_violacao=tipo,
                trecho_problematico=match.group()[:100],
                severidade=severidade
            )

    return ValidacaoResult(valido=True)


# Padroes de linguagem corporativa/robotica
PADROES_LINGUAGEM_ROBOTICA = [
    # Muito formal
    (r'gostar[ií]amos?\s+de\s+informar', 'formal_informar', 'media'),
    (r'temos\s+o\s+prazer\s+de', 'formal_prazer', 'media'),
    (r'vimos\s+por\s+meio\s+desta', 'formal_carta', 'alta'),
    (r'segue\s+(em\s+)?anexo', 'formal_anexo', 'media'),

    # Excesso de formalidade
    (r'vossa\s+(senhoria|excel[eê]ncia)', 'formal_vossa', 'alta'),
    (r'mui(to)?\s+respeitosamente', 'formal_respeitosamente', 'media'),

    # Linguagem de servico de atendimento
    (r'sua\s+(liga[çc][aã]o|chamada)\s+[eé]\s+muito\s+importante', 'sac_importante', 'alta'),
    (r'em\s+que\s+posso\s+(lhe\s+)?ser\s+[uú]til', 'sac_util', 'media'),
    (r'agrade[çc]o\s+(a\s+)?sua\s+(prefer[eê]ncia|paci[eê]ncia)', 'sac_agradeco', 'media'),
]


def detectar_linguagem_robotica(texto: str) -> ValidacaoResult:
    """
    Detecta linguagem muito formal ou robotica.

    Args:
        texto: Resposta a validar

    Returns:
        ValidacaoResult com detalhes
    """
    texto_lower = texto.lower()

    for padrao, tipo, severidade in PADROES_LINGUAGEM_ROBOTICA:
        match = re.search(padrao, texto_lower)
        if match:
            logger.warning(
                f"Linguagem robotica detectada: tipo={tipo}"
            )
            return ValidacaoResult(
                valido=False,
                motivo=f"Linguagem muito formal/robotica ({tipo})",
                tipo_violacao=tipo,
                trecho_problematico=match.group(),
                severidade=severidade
            )

    return ValidacaoResult(valido=True)
```

## Criterios de Aceite

1. **Padroes de IA:** Detecta mencoes diretas de IA/bot
2. **Frases evasivas:** Detecta respostas que evitam admitir
3. **Severidade:** Classifica violacoes por gravidade
4. **Trecho identificado:** Retorna parte problematica

## DoD

- [ ] `detectar_revelacao_ia()` implementado
- [ ] `detectar_formato_proibido()` implementado
- [ ] `detectar_linguagem_robotica()` implementado
- [ ] Pelo menos 20 padroes de revelacao IA
- [ ] Pelo menos 10 padroes de formato
- [ ] Pelo menos 10 padroes de linguagem
- [ ] Severidade em cada padrao
- [ ] Logs de violacoes

---

# S8.E5.2 - Criar validador completo

## Objetivo

> **Combinar todos os validadores em funcao unica.**

## Codigo Esperado

**Arquivo:** `app/services/validacao_output.py` (adicionar)

```python
from typing import Callable, Awaitable


class OutputValidator:
    """
    Validador completo de output.

    Executa todos os validadores em sequencia.
    """

    def __init__(self):
        self.validadores: list[Callable[[str], ValidacaoResult]] = [
            detectar_revelacao_ia,
            detectar_formato_proibido,
            detectar_linguagem_robotica,
        ]
        self.metricas = {
            "total_validacoes": 0,
            "falhas_por_tipo": {},
        }

    def adicionar_validador(
        self,
        validador: Callable[[str], ValidacaoResult]
    ) -> "OutputValidator":
        """Adiciona validador customizado."""
        self.validadores.append(validador)
        return self

    def validar(self, texto: str) -> ValidacaoResult:
        """
        Executa todos os validadores.

        Para no primeiro que falhar (fail-fast).

        Args:
            texto: Texto a validar

        Returns:
            ValidacaoResult (primeiro que falhar ou sucesso)
        """
        self.metricas["total_validacoes"] += 1

        if not texto or not texto.strip():
            return ValidacaoResult(valido=True)

        for validador in self.validadores:
            resultado = validador(texto)

            if not resultado.valido:
                # Registrar metrica
                tipo = resultado.tipo_violacao or "desconhecido"
                self.metricas["falhas_por_tipo"][tipo] = \
                    self.metricas["falhas_por_tipo"].get(tipo, 0) + 1

                return resultado

        return ValidacaoResult(valido=True)

    def get_metricas(self) -> dict:
        """Retorna metricas de validacao."""
        return self.metricas.copy()


# Instancia global
output_validator = OutputValidator()


async def validar_resposta(texto: str) -> ValidacaoResult:
    """
    Funcao helper para validar resposta.

    Args:
        texto: Resposta a validar

    Returns:
        ValidacaoResult
    """
    return output_validator.validar(texto)


async def validar_e_corrigir(
    texto: str,
    tentativas_max: int = 2
) -> tuple[str, bool]:
    """
    Valida e tenta corrigir resposta se invalida.

    Se validacao falhar, tenta:
    1. Remover formatacao proibida
    2. Se ainda falhar, retorna texto original com flag

    Args:
        texto: Resposta a validar
        tentativas_max: Maximo de correcoes

    Returns:
        Tuple (texto_corrigido, foi_modificado)
    """
    resultado = output_validator.validar(texto)

    if resultado.valido:
        return texto, False

    # Tentar corrigir
    texto_corrigido = texto

    for _ in range(tentativas_max):
        # Remover bullets
        texto_corrigido = re.sub(r'^\s*[-•*]\s+', '', texto_corrigido, flags=re.MULTILINE)
        texto_corrigido = re.sub(r'\n\s*[-•*]\s+', '\n', texto_corrigido)

        # Remover listas numeradas
        texto_corrigido = re.sub(r'^\s*\d+[.)]\s+', '', texto_corrigido, flags=re.MULTILINE)

        # Remover markdown
        texto_corrigido = re.sub(r'\*\*([^*]+)\*\*', r'\1', texto_corrigido)
        texto_corrigido = re.sub(r'`([^`]+)`', r'\1', texto_corrigido)

        # Validar novamente
        resultado = output_validator.validar(texto_corrigido)
        if resultado.valido:
            return texto_corrigido, True

    # Se ainda falhar, logar e retornar
    logger.error(
        f"Resposta invalida apos correcoes: {resultado.motivo}. "
        f"Trecho: {resultado.trecho_problematico}"
    )

    # Se for critico (revelacao IA), nao envia
    if resultado.severidade == "critica":
        logger.critical(
            f"BLOQUEADO: Resposta revelaria IA! "
            f"Tipo: {resultado.tipo_violacao}"
        )
        return "", True  # Retorna vazio para nao enviar

    return texto_corrigido, True
```

## Criterios de Aceite

1. **Fail-fast:** Para no primeiro validador que falhar
2. **Metricas:** Conta validacoes e falhas por tipo
3. **Correcao automatica:** Tenta corrigir formato
4. **Bloqueio critico:** Nao envia se revelaria IA

## DoD

- [ ] Classe OutputValidator implementada
- [ ] `validar_resposta()` helper criado
- [ ] `validar_e_corrigir()` implementado
- [ ] Metricas de falhas registradas
- [ ] Correcao de formato funciona
- [ ] Bloqueio de revelacao critica funciona

---

# S8.E5.3 - Integrar no pipeline

## Objetivo

> **Adicionar validador como pos-processador no pipeline.**

## Codigo Esperado

**Arquivo:** `app/pipeline/post_processors.py` (adicionar)

```python
from app.services.validacao_output import validar_e_corrigir, output_validator


class ValidateOutputProcessor(PostProcessor):
    """
    Valida resposta antes de enviar.

    Prioridade: 5 (roda antes de tudo)
    """
    name = "validate_output"
    priority = 5

    async def process(
        self,
        context: ProcessorContext,
        response: str
    ) -> ProcessorResult:
        if not response:
            return ProcessorResult(success=True, response=response)

        # Validar e tentar corrigir
        texto_validado, foi_corrigido = await validar_e_corrigir(response)

        if foi_corrigido:
            logger.info(f"Resposta corrigida pela validacao")
            context.metadata["output_corrigido"] = True

        if not texto_validado:
            # Foi bloqueado (revelaria IA)
            logger.error("Resposta bloqueada - revelaria IA")
            context.metadata["output_bloqueado"] = True

            # Notificar gestor
            await self._notificar_bloqueio(context, response)

            return ProcessorResult(
                success=False,
                should_continue=False,
                error="Resposta bloqueada - revelaria IA"
            )

        return ProcessorResult(success=True, response=texto_validado)

    async def _notificar_bloqueio(self, context: ProcessorContext, resposta_original: str):
        """Notifica gestor sobre resposta bloqueada."""
        from app.services.slack import enviar_alerta_slack

        try:
            await enviar_alerta_slack(
                tipo="output_bloqueado",
                mensagem=f"Resposta bloqueada para medico {context.medico.get('primeiro_nome', 'N/A')}",
                detalhes={
                    "telefone": context.telefone[:8] + "...",
                    "resposta_original": resposta_original[:200],
                    "motivo": "Revelaria IA"
                },
                urgente=True
            )
        except Exception as e:
            logger.error(f"Erro ao notificar bloqueio: {e}")
```

**Arquivo:** `app/pipeline/setup.py` (modificar)

```python
from .post_processors import (
    ValidateOutputProcessor,  # Novo
    TimingProcessor,
    SendMessageProcessor,
    SaveInteractionProcessor,
    MetricsProcessor,
)


def criar_pipeline() -> MessageProcessor:
    pipeline = MessageProcessor()

    # ... pre-processadores ...

    # Pos-processadores
    pipeline.add_post_processor(ValidateOutputProcessor())   # 5 - PRIMEIRO
    pipeline.add_post_processor(TimingProcessor())           # 10
    pipeline.add_post_processor(SendMessageProcessor())      # 20
    pipeline.add_post_processor(SaveInteractionProcessor())  # 30
    pipeline.add_post_processor(MetricsProcessor())          # 40

    return pipeline
```

## Criterios de Aceite

1. **Prioridade 5:** Roda antes de todos pos-processadores
2. **Correcao transparente:** Corrige sem parar pipeline
3. **Bloqueio funciona:** Nao envia se critico
4. **Notificacao:** Alerta gestor quando bloqueia

## DoD

- [ ] ValidateOutputProcessor implementado
- [ ] Prioridade 5 (primeiro pos-processador)
- [ ] Registrado no pipeline
- [ ] Notificacao Slack quando bloqueia
- [ ] Logs de correcoes e bloqueios

---

# S8.E5.4 - Criar endpoint de metricas

## Objetivo

> **Expor metricas de validacao para monitoramento.**

## Codigo Esperado

**Arquivo:** `app/api/routes/admin.py` (adicionar)

```python
from fastapi import APIRouter
from app.services.validacao_output import output_validator

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/validacao/metricas")
async def get_metricas_validacao():
    """
    Retorna metricas de validacao de output.

    Util para monitorar quantas respostas estao sendo corrigidas/bloqueadas.
    """
    metricas = output_validator.get_metricas()

    total = metricas["total_validacoes"]
    falhas = sum(metricas["falhas_por_tipo"].values())
    taxa_falha = (falhas / total * 100) if total > 0 else 0

    return {
        "total_validacoes": total,
        "total_falhas": falhas,
        "taxa_falha_percent": round(taxa_falha, 2),
        "falhas_por_tipo": metricas["falhas_por_tipo"],
        "status": "ok" if taxa_falha < 5 else "atencao" if taxa_falha < 10 else "critico"
    }


@router.post("/validacao/testar")
async def testar_validacao(texto: str):
    """
    Testa validacao de um texto.

    Util para debug e ajuste de padroes.
    """
    from app.services.validacao_output import (
        detectar_revelacao_ia,
        detectar_formato_proibido,
        detectar_linguagem_robotica
    )

    resultados = {
        "revelacao_ia": detectar_revelacao_ia(texto).__dict__,
        "formato": detectar_formato_proibido(texto).__dict__,
        "linguagem": detectar_linguagem_robotica(texto).__dict__,
    }

    todas_validas = all(r["valido"] for r in resultados.values())

    return {
        "texto": texto,
        "valido": todas_validas,
        "detalhes": resultados
    }
```

## Criterios de Aceite

1. **Endpoint metricas:** Retorna estatisticas
2. **Endpoint teste:** Permite testar texto
3. **Status calculado:** Indica se ta ok/atencao/critico

## DoD

- [ ] GET `/admin/validacao/metricas` implementado
- [ ] POST `/admin/validacao/testar` implementado
- [ ] Taxa de falha calculada
- [ ] Status baseado em thresholds

---

## Resumo do Epic

| Story | Descricao | Complexidade |
|-------|-----------|--------------|
| S8.E5.1 | Detector de revelacao IA | Media |
| S8.E5.2 | Validador completo | Media |
| S8.E5.3 | Integrar no pipeline | Baixa |
| S8.E5.4 | Endpoint metricas | Baixa |

## Arquivos Criados/Modificados

| Arquivo | Acao |
|---------|------|
| `app/services/validacao_output.py` | Criar |
| `app/pipeline/post_processors.py` | Modificar |
| `app/pipeline/setup.py` | Modificar |
| `app/api/routes/admin.py` | Modificar |
