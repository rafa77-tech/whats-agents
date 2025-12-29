# Servicos e Componentes

> Detalhes dos 118 modulos de servico do sistema

---

## Organizacao

Os servicos estao em `app/services/` e sao organizados por responsabilidade:

```
app/services/
├── Core do Agente
│   ├── agente.py          # Orquestrador principal (WhatsApp)
│   ├── agente_slack.py    # Agente conversacional Slack (Sprint 9)
│   ├── llm.py             # Cliente Anthropic
│   ├── conversa.py        # Gestao de conversas
│   ├── interacao.py       # Log de mensagens
│   └── medico.py          # Gestao de medicos
│
├── Inteligencia
│   ├── deteccao_bot.py    # Detecta quando percebem IA
│   ├── handoff_detector.py # Detecta triggers de handoff
│   ├── optout.py          # Detecta opt-out
│   ├── contexto.py        # Monta contexto para LLM
│   ├── memoria.py         # RAG com embeddings (Sprint 8)
│   ├── embedding.py       # Cliente Voyage AI (Sprint 8)
│   └── validacao_output.py # Valida output do LLM (Sprint 8)
│
├── Mensagens
│   ├── whatsapp.py        # Cliente Evolution API
│   ├── mensagem.py        # Formatacao de mensagens
│   ├── parser.py          # Parse de payloads
│   ├── timing.py          # Humanizacao de timing
│   ├── abertura.py        # Variacoes de abertura (Sprint 8)
│   └── fila_mensagens.py  # Fila de envio agendado
│
├── Resiliencia
│   ├── rate_limiter.py    # Limites de envio
│   ├── circuit_breaker.py # Protecao contra falhas
│   ├── redis.py           # Cliente Redis
│   └── monitor_whatsapp.py # Health check WhatsApp
│
├── Integracao
│   ├── supabase.py        # Cliente banco de dados
│   ├── chatwoot.py        # Cliente Chatwoot
│   ├── slack.py           # Notificacoes Slack (outbound)
│   ├── slack_comandos.py  # Comandos Slack (inbound)
│   ├── slack_formatter.py # Formatacao respostas Slack (Sprint 9)
│   ├── google_docs.py     # Leitura de briefing
│   ├── briefing.py        # Sincronizacao de briefing (Sprint 7)
│   └── briefing_parser.py # Parser do Google Docs (Sprint 7)
│
├── Negocio
│   ├── vaga.py            # Gestao de vagas/plantoes
│   ├── campanha.py        # Campanhas de outreach
│   ├── followup.py        # Follow-ups automaticos
│   ├── handoff.py         # Execucao de handoff
│   ├── segmentacao.py     # Segmentacao de medicos
│   └── tipos_abordagem.py # 5 tipos de abordagem (Sprint 9)
│
└── Analytics
    ├── metricas.py        # Coleta de metricas
    ├── qualidade.py       # Avaliacao de qualidade
    ├── relatorio.py       # Geracao de reports
    ├── feedback.py        # Loop de feedback
    └── alertas.py         # Sistema de alertas
```

---

## Core do Agente

### agente.py

Orquestrador principal do agente Julia.

**Funcoes principais:**

```python
async def processar_mensagem_completo(
    medico: dict,
    conversa: dict,
    mensagem: str,
    historico: list
) -> str:
    """
    Pipeline completo de processamento.
    1. Monta contexto
    2. Chama LLM com tools
    3. Processa tool calls se houver
    4. Retorna resposta final
    """

async def processar_tool_call(
    tool_name: str,
    tool_input: dict,
    medico: dict,
    conversa: dict
) -> str:
    """
    Executa uma tool e retorna resultado.
    Tools disponiveis: buscar_vagas, reservar_plantao, agendar_lembrete
    """

async def enviar_resposta(
    telefone: str,
    resposta: str,
    conversa_id: str
) -> bool:
    """
    Envia resposta com humanizacao.
    1. Quebra mensagem longa
    2. Calcula delays
    3. Mostra "digitando"
    4. Envia partes
    """
```

### llm.py

Cliente para API da Anthropic (Claude).

**Funcoes principais:**

```python
async def gerar_resposta(
    mensagem: str,
    contexto: dict,
    historico: list = None
) -> str:
    """
    Gera resposta simples sem tools.
    Usa Claude Haiku por padrao.
    """

async def gerar_resposta_com_tools(
    mensagem: str,
    contexto: dict,
    historico: list,
    tools: list
) -> dict:
    """
    Gera resposta com capacidade de usar tools.
    Retorna: {"content": str, "tool_use": list}
    """

async def continuar_apos_tool(
    mensagens_anteriores: list,
    resultado_tool: str
) -> str:
    """
    Continua geracao apos execucao de tool.
    """
```

**Configuracao:**

```python
# Modelos
LLM_MODEL = "claude-3-5-haiku-20241022"        # 80% das chamadas
LLM_MODEL_COMPLEX = "claude-sonnet-4-20250514"  # 20% (negociacao)

# Parametros
MAX_TOKENS = 1024
TEMPERATURE = 0.7
```

### conversa.py

Gestao do ciclo de vida de conversas.

```python
async def buscar_ou_criar_conversa(
    cliente_id: str,
    instance_id: str = None
) -> dict:
    """
    Busca conversa ativa ou cria nova.
    """

async def atualizar_status_conversa(
    conversa_id: str,
    status: str,
    controlled_by: str = None
) -> None:
    """
    Atualiza status: active, paused, escalated, completed
    """

async def encerrar_conversa(
    conversa_id: str,
    motivo: str = None
) -> None:
    """
    Marca conversa como completed.
    """
```

### interacao.py

Persistencia de todas as mensagens.

```python
async def salvar_interacao(
    cliente_id: str,
    conversa_id: str,
    origem: str,      # "medico" ou "julia"
    tipo: str,        # "texto", "audio", "imagem"
    conteudo: str,
    metadata: dict = None
) -> dict:
    """
    Salva interacao no banco.
    """

async def carregar_historico(
    conversa_id: str,
    limite: int = 20
) -> list:
    """
    Carrega ultimas N interacoes.
    """

def formatar_historico_para_llm(
    interacoes: list
) -> list:
    """
    Converte para formato Messages API.
    [{"role": "user", "content": "..."}, ...]
    """
```

---

## Inteligencia

### deteccao_bot.py

Detecta quando medicos percebem que estao falando com IA.

**37 padroes regex:**

```python
PADROES_DETECCAO = [
    r"\bbot\b",
    r"\brob[oô]\b",
    r"\bia\b",
    r"isso [eé] autom[aá]tico",
    r"[eé] um? bot",
    r"voc[eê] [eé] (uma? )?(m[aá]quina|rob[oô]|bot|ia)",
    r"intelig[eê]ncia artificial",
    r"resposta autom[aá]tica",
    # ... mais 29 padroes
]
```

**Funcoes:**

```python
def detectar_mencao_bot(mensagem: str) -> dict:
    """
    Retorna: {"detectado": bool, "padrao": str, "trecho": str}
    """

async def registrar_deteccao_bot(
    cliente_id: str,
    conversa_id: str,
    mensagem: str,
    padrao: str,
    trecho: str
) -> None:
    """
    Salva na tabela metricas_deteccao_bot.
    """

async def calcular_taxa_deteccao(dias: int = 7) -> dict:
    """
    Retorna taxa de deteccao no periodo.
    {"total_conversas": N, "deteccoes": M, "taxa_percentual": X}
    """
```

### handoff_detector.py

Detecta quando escalar para humano.

**Triggers:**

| Trigger | Descricao |
|---------|-----------|
| `explicito` | "quero falar com humano", "me passa pra alguem" |
| `juridico` | mencoes a processo, advogado, CFM |
| `sentimento_negativo` | insultos, raiva extrema |
| `confianca_baixa` | LLM indica incerteza |

```python
def detectar_trigger_handoff(
    mensagem: str,
    contexto: dict = None
) -> dict:
    """
    Retorna: {"trigger": bool, "tipo": str, "motivo": str}
    """
```

### optout.py

Detecta pedidos de opt-out (parar mensagens).

**Padroes detectados:**

```python
PADROES_OPTOUT = [
    r"\bpare?\b",
    r"\bparar\b",
    r"\bstop\b",
    r"\bsair?\b",
    r"\bnao quero\b",
    r"\bnao me mand[ae]\b",
    r"\bremov[ae]\b",
    r"\bbloquear?\b",
    # ... mais padroes
]
```

```python
def detectar_optout(mensagem: str) -> bool:
    """
    Retorna True se detectar pedido de opt-out.
    """

async def processar_optout(
    cliente_id: str,
    conversa_id: str
) -> None:
    """
    1. Marca cliente como opt_out=True
    2. Envia mensagem de confirmacao
    3. Encerra conversa
    """

async def pode_enviar_proativo(cliente_id: str) -> bool:
    """
    Verifica se pode enviar mensagem proativa.
    False se opt_out=True ou bloqueado=True
    """
```

### contexto.py

Monta contexto completo para o LLM.

```python
async def montar_contexto_completo(
    medico: dict,
    conversa: dict,
    vagas: list = None
) -> dict:
    """
    Retorna dict com:
    - medico: dados formatados
    - especialidade: info da especialidade
    - historico: conversas anteriores
    - vagas: plantoes disponiveis
    - diretrizes: do briefing do gestor
    - handoff_recente: se houve handoff
    - data_hora_atual: para contexto temporal
    """
```

---

## Mensagens

### whatsapp.py

Cliente para Evolution API.

```python
# Cliente global
evolution = EvolutionClient()

async def enviar_mensagem(
    telefone: str,
    mensagem: str,
    instance: str = None
) -> bool:
    """
    Envia mensagem de texto.
    """

async def enviar_audio(
    telefone: str,
    audio_base64: str
) -> bool:
    """
    Envia mensagem de audio.
    """

async def marcar_como_lida(
    telefone: str,
    message_id: str
) -> None:
    """
    Marca mensagem como lida (check azul).
    """

async def mostrar_online() -> None:
    """
    Mostra status "online" no WhatsApp.
    """

async def mostrar_digitando(telefone: str) -> None:
    """
    Mostra "digitando..." para o contato.
    """
```

### timing.py

Humanizacao de timing de respostas.

```python
def calcular_delay_resposta(
    tamanho_mensagem: int,
    complexidade: str = "normal"
) -> float:
    """
    Calcula delay baseado no tamanho.
    Simula tempo de leitura + digitacao.

    Retorna: segundos (2-15)
    """

def esta_em_horario_comercial() -> bool:
    """
    Verifica se esta entre 08:00-20:00 Seg-Sex.
    """

def proximo_horario_disponivel() -> datetime:
    """
    Retorna proximo horario comercial.
    """
```

### mensagem.py

Formatacao e processamento de mensagens.

```python
def quebrar_mensagem(
    texto: str,
    max_chars: int = 4000
) -> list:
    """
    Quebra mensagem longa em partes.
    Respeita limites do WhatsApp.
    """

def tratar_mensagem_longa(
    texto: str,
    limite_truncar: int = 10000,
    limite_rejeitar: int = 50000
) -> tuple:
    """
    Retorna: (texto_tratado, foi_truncado, rejeitado)
    """
```

---

## Resiliencia

### rate_limiter.py

Rate limiting distribuido via Redis.

```python
async def pode_enviar(telefone: str = None) -> bool:
    """
    Verifica se pode enviar mensagem agora.
    Checa: limite hora, limite dia, horario comercial.
    """

async def registrar_envio(telefone: str = None) -> None:
    """
    Registra envio nos contadores Redis.
    """

async def obter_estatisticas() -> dict:
    """
    Retorna uso atual vs limites.
    """

async def tempo_ate_liberacao() -> int:
    """
    Segundos ate poder enviar novamente.
    """
```

### circuit_breaker.py

Circuit breaker para APIs externas.

```python
class CircuitBreaker:
    """
    Estados: CLOSED -> OPEN -> HALF_OPEN -> CLOSED

    - CLOSED: Normal, chamadas passam
    - OPEN: Muitas falhas, bloqueia por X segundos
    - HALF_OPEN: Teste de recuperacao
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: int = 30
    ):
        pass

    async def call(self, func, *args, **kwargs):
        """
        Executa funcao com protecao de circuit.
        Levanta CircuitOpenError se aberto.
        """

# Instancias globais
circuit_claude = CircuitBreaker("claude")
circuit_evolution = CircuitBreaker("evolution")
circuit_supabase = CircuitBreaker("supabase")
```

---

## Negocio

### vaga.py

Gestao de vagas e plantoes.

```python
async def buscar_vagas_compativeis(
    medico: dict,
    filtros: dict = None,
    limite: int = 5
) -> list:
    """
    Busca vagas que combinam com perfil do medico.
    Considera: especialidade, cidade, valor, data.
    """

async def reservar_vaga(
    vaga_id: str,
    medico_id: str
) -> dict:
    """
    Reserva vaga para medico.
    Atualiza status para 'reservada'.
    """

def formatar_vaga_para_mensagem(vaga: dict) -> str:
    """
    Formata vaga para texto de mensagem.
    Ex: "Hospital X, dia 15/12, noturno, R$ 2.500"
    """
```

### handoff.py

Execucao de handoff IA -> Humano.

```python
async def iniciar_handoff(
    conversa_id: str,
    motivo: str,
    trigger_type: str
) -> dict:
    """
    1. Atualiza controlled_by = 'human'
    2. Cria registro em handoffs
    3. Sincroniza com Chatwoot
    4. Notifica no Slack
    5. Envia msg ao medico
    """

async def finalizar_handoff(
    handoff_id: str,
    notas: str = None
) -> None:
    """
    Marca handoff como resolvido.
    Volta controlled_by para 'ai'.
    """
```

### followup.py

Sistema de follow-ups automaticos.

```python
# Stages de follow-up
STAGES = {
    "48h": timedelta(hours=48),
    "5d": timedelta(days=5),
    "15d": timedelta(days=15)
}

async def processar_followups_pendentes() -> dict:
    """
    Processa todos os follow-ups do dia.
    Retorna contagem por stage.
    """

async def agendar_followup(
    cliente_id: str,
    conversa_id: str,
    stage: str,
    mensagem: str
) -> None:
    """
    Agenda mensagem de follow-up.
    """
```

---

## Analytics

### relatorio.py

Geracao de reports.

```python
async def gerar_report_periodo(tipo: str) -> dict:
    """
    Gera report de periodo (manha, almoco, tarde, fim_dia).
    """

async def gerar_report_semanal() -> dict:
    """
    Gera report consolidado da semana.
    """

async def enviar_report_periodo_slack(report: dict) -> None:
    """
    Formata e envia report para Slack.
    """
```

### metricas.py

Coleta de metricas.

```python
class MetricasService:
    async def coletar_metricas(
        inicio: datetime,
        fim: datetime
    ) -> dict:
        """
        Coleta metricas do periodo.
        """

    async def calcular_taxa_resposta() -> float:
        """
        % de mensagens que receberam resposta.
        """

    async def calcular_tempo_medio_resposta() -> float:
        """
        Tempo medio de resposta em segundos.
        """
```

---

## Como Adicionar Novo Servico

1. Criar arquivo em `app/services/novo_servico.py`
2. Implementar funcoes async
3. Adicionar logging estruturado
4. Adicionar tratamento de erros
5. Documentar funcoes com docstrings
6. Criar testes em `tests/test_novo_servico.py`

**Template:**

```python
"""
Servico para [descricao].
"""
import logging
from app.services.supabase import get_supabase

logger = logging.getLogger(__name__)


async def minha_funcao(param: str) -> dict:
    """
    Descricao da funcao.

    Args:
        param: Descricao do parametro

    Returns:
        Dict com resultado
    """
    try:
        # Implementacao
        logger.info(f"Executando minha_funcao: {param}")
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Erro em minha_funcao: {e}")
        raise
```
