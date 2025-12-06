# Epic 2: Agente Júlia

## Objetivo do Epic

> **Criar o agente Júlia que gera respostas naturais usando Claude.**

Este epic transforma mensagens recebidas em respostas que parecem humanas.

---

## Stories

1. [S1.E2.1 - System prompt completo da Júlia](#s1e21---system-prompt-completo-da-júlia)
2. [S1.E2.2 - Buscar/criar médico no banco](#s1e22---buscarcriaar-médico-no-banco)
3. [S1.E2.3 - Buscar/criar conversa](#s1e23---buscarcriaar-conversa)
4. [S1.E2.4 - Carregar histórico recente](#s1e24---carregar-histórico-recente)
5. [S1.E2.5 - Montar contexto para LLM](#s1e25---montar-contexto-para-llm)
6. [S1.E2.6 - Chamar Claude e processar resposta](#s1e26---chamar-claude-e-processar-resposta)
7. [S1.E2.7 - Enviar resposta e salvar interação](#s1e27---enviar-resposta-e-salvar-interação)

---

# S1.E2.1 - System prompt completo da Júlia

## Objetivo

> **Criar o system prompt que define a personalidade e comportamento da Júlia.**

O system prompt é o "cérebro" da Júlia. Define quem ela é, como fala, o que pode e não pode fazer.

**Resultado esperado:** System prompt completo que faz o Claude responder como uma escalista humana de 27 anos.

---

## Contexto

- O prompt define TODO o comportamento da Júlia
- Precisa ser detalhado mas não muito longo (tokens = custo)
- Referência: `CLAUDE.md` (persona) e `docs/CONVERSAS_REFERENCIA.md`

---

## Responsável

**Dev**

---

## Pré-requisitos

- [ ] Leitura do `CLAUDE.md` seção Persona
- [ ] Leitura do `docs/CONVERSAS_REFERENCIA.md`

---

## Tarefas

### 1. Criar arquivo de prompts

```bash
cat > /Users/rafaelpivovar/Documents/Projetos/whatsapp-api/app/core/prompts.py << 'EOF'
"""
Prompts do sistema para o agente Júlia.
"""

JULIA_SYSTEM_PROMPT = """Você é a Júlia Mendes, escalista da Revoluna com 27 anos de experiência em staffing médico.

## IDENTIDADE
- Nome: Júlia Mendes
- Idade: 27 anos
- Cargo: Escalista
- Empresa: Revoluna (escalas médicas)
- Personalidade: Simpática, direta, profissional mas descontraída

## COMO VOCÊ FALA
Você escreve como uma pessoa real no WhatsApp:
- Mensagens CURTAS (1-3 linhas no máximo)
- Usa abreviações: "vc", "pra", "tá", "q", "tb", "blz", "msg"
- Usa emoji com moderação (máximo 1-2 por conversa, não toda mensagem)
- Quebra em várias mensagens curtas ao invés de uma longa
- Às vezes comete pequenos erros e corrige: "plantao* plantão"
- NUNCA usa bullet points, listas ou formatação
- NUNCA usa linguagem corporativa ou formal demais
- Responde de forma natural, como em uma conversa real

## EXEMPLOS DE COMO FALAR

Certo ✓:
"Oi Dr Carlos! Tudo bem?"
"Sou a Júlia da Revoluna"
"Trabalho com escalas médicas aqui no ABC"
"Vc tá fazendo plantões?"

Errado ✗:
"Olá Dr. Carlos, como você está? Meu nome é Júlia e trabalho na empresa Revoluna, que atua no segmento de escalas médicas na região do ABC. Gostaria de saber se você tem interesse em oportunidades de plantão."

## REGRAS ABSOLUTAS
1. NUNCA revele que é uma IA, bot, assistente virtual ou programa
2. Se perguntarem se é bot, você É a Júlia, escalista humana
3. NUNCA envie listas com marcadores ou números
4. NUNCA use linguagem muito formal ("prezado", "cordialmente", etc)
5. NUNCA responda perguntas fora do seu escopo (política, religião, etc)
6. SEMPRE respeite quando alguém pedir para parar de receber mensagens

## SEU TRABALHO
- Você ajuda médicos a encontrar plantões
- Você conhece os hospitais e vagas disponíveis
- Você pode tirar dúvidas sobre vagas, valores, horários
- Você reserva plantões quando o médico aceita
- Você passa para um supervisor humano quando necessário

## SITUAÇÕES ESPECIAIS
- Se o médico ficar irritado: peça desculpas e ofereça passar para seu supervisor
- Se não souber responder: diga que vai verificar e já retorna
- Se pedirem desconto: você pode negociar dentro da margem informada
- Se for assunto pessoal/fora do trabalho: seja educada mas redirecione

## CONTEXTO DA CONVERSA
{contexto}

## INSTRUÇÕES PARA ESTA RESPOSTA
- Leia a mensagem do médico
- Responda de forma natural e curta
- Mantenha o tom informal mas profissional
- Se for primeira mensagem, se apresente brevemente
- Se o médico mostrar interesse, pergunte sobre disponibilidade ou ofereça vaga
"""


JULIA_PROMPT_PRIMEIRA_MSG = """
Esta é a PRIMEIRA interação com este médico. Você está fazendo prospecção.
- Se apresente brevemente
- Mencione que trabalha com escalas médicas
- Pergunte se ele está fazendo plantões ou tem interesse
- Seja natural, não pareça roteiro
"""


JULIA_PROMPT_CONTINUACAO = """
Esta é uma conversa em andamento.
- Continue naturalmente de onde parou
- Responda o que o médico perguntou/disse
- Se ele mostrou interesse, ofereça detalhes ou vaga
"""


def montar_prompt_julia(
    contexto_medico: str = "",
    contexto_vagas: str = "",
    historico: str = "",
    primeira_msg: bool = False
) -> str:
    """
    Monta o system prompt completo para a Júlia.

    Args:
        contexto_medico: Info sobre o médico (nome, especialidade, etc)
        contexto_vagas: Vagas disponíveis relevantes
        historico: Histórico recente da conversa
        primeira_msg: Se é primeira interação

    Returns:
        System prompt formatado
    """
    contexto_parts = []

    if contexto_medico:
        contexto_parts.append(f"SOBRE O MÉDICO:\n{contexto_medico}")

    if contexto_vagas:
        contexto_parts.append(f"VAGAS DISPONÍVEIS:\n{contexto_vagas}")

    if historico:
        contexto_parts.append(f"HISTÓRICO RECENTE:\n{historico}")

    contexto = "\n\n".join(contexto_parts) if contexto_parts else "Nenhum contexto adicional."

    prompt = JULIA_SYSTEM_PROMPT.format(contexto=contexto)

    if primeira_msg:
        prompt += "\n\n" + JULIA_PROMPT_PRIMEIRA_MSG
    else:
        prompt += "\n\n" + JULIA_PROMPT_CONTINUACAO

    return prompt
EOF
```

### 2. Testar prompt com diferentes cenários

```bash
cat > /Users/rafaelpivovar/Documents/Projetos/whatsapp-api/tests/test_prompts.py << 'EOF'
"""
Testes do system prompt da Júlia.
"""
import pytest
from app.core.prompts import montar_prompt_julia


class TestMontarPrompt:
    def test_prompt_basico(self):
        prompt = montar_prompt_julia()
        assert "Júlia Mendes" in prompt
        assert "escalista" in prompt
        assert "NUNCA revele que é uma IA" in prompt

    def test_prompt_com_contexto_medico(self):
        prompt = montar_prompt_julia(
            contexto_medico="Dr. Carlos, anestesista, CRM 123456"
        )
        assert "Dr. Carlos" in prompt
        assert "SOBRE O MÉDICO" in prompt

    def test_prompt_primeira_msg(self):
        prompt = montar_prompt_julia(primeira_msg=True)
        assert "PRIMEIRA interação" in prompt
        assert "Se apresente" in prompt

    def test_prompt_continuacao(self):
        prompt = montar_prompt_julia(primeira_msg=False)
        assert "conversa em andamento" in prompt
EOF
```

### 3. Testar geração de resposta

Adicione rota de teste em `app/api/routes/test_llm.py`:

```python
from app.core.prompts import montar_prompt_julia

@router.post("/llm/julia")
async def test_julia_resposta(request: MensagemRequest):
    """Testa resposta da Júlia com prompt completo."""
    try:
        system = montar_prompt_julia(
            contexto_medico="Dr. Carlos, anestesista",
            primeira_msg=True
        )

        resposta = await gerar_resposta(
            mensagem=request.mensagem,
            system_prompt=system,
        )

        return {
            "entrada": request.mensagem,
            "resposta": resposta,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

### 4. Validar qualidade das respostas

Teste manualmente com cenários:

```bash
# Cenário 1: Saudação
curl -X POST http://localhost:8000/test/llm/julia \
  -H "Content-Type: application/json" \
  -d '{"mensagem": "Oi"}'

# Cenário 2: Interesse em plantão
curl -X POST http://localhost:8000/test/llm/julia \
  -H "Content-Type: application/json" \
  -d '{"mensagem": "Tenho interesse em plantão"}'

# Cenário 3: Pergunta se é bot
curl -X POST http://localhost:8000/test/llm/julia \
  -H "Content-Type: application/json" \
  -d '{"mensagem": "Isso é um robô?"}'
```

**Verificar:**
- Resposta é curta (1-3 linhas)?
- Usa abreviações (vc, pra, tá)?
- Não usa bullet points?
- Não revela que é IA?

---

## DoD (Definition of Done)

- [ ] Arquivo `app/core/prompts.py` criado
- [ ] `JULIA_SYSTEM_PROMPT` completo e detalhado
- [ ] Função `montar_prompt_julia()` implementada
- [ ] Testes unitários passando
- [ ] Respostas são curtas (1-3 linhas)
- [ ] Respostas usam linguagem informal
- [ ] Respostas não revelam que é IA
- [ ] 10 cenários testados manualmente com qualidade OK

---
---

# S1.E2.2 - Buscar/criar médico no banco

## Objetivo

> **Quando receber mensagem, buscar ou criar registro do médico no banco.**

Precisamos saber quem é o médico para personalizar a conversa.

**Resultado esperado:** Função que recebe telefone e retorna dados do médico (existente ou recém-criado).

---

## Responsável

**Dev**

---

## Pré-requisitos

- [ ] Sprint 0 completa (Supabase configurado)

---

## Tarefas

### 1. Criar serviço de médicos

```bash
cat > /Users/rafaelpivovar/Documents/Projetos/whatsapp-api/app/services/medico.py << 'EOF'
"""
Serviço para gerenciamento de médicos.
"""
from typing import Optional
import logging

from app.services.supabase import supabase

logger = logging.getLogger(__name__)


async def buscar_medico_por_telefone(telefone: str) -> Optional[dict]:
    """
    Busca médico pelo número de telefone.

    Args:
        telefone: Número no formato 5511999999999

    Returns:
        Dados do médico ou None se não encontrado
    """
    try:
        response = (
            supabase.table("clientes")
            .select("*")
            .eq("telefone", telefone)
            .execute()
        )
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error(f"Erro ao buscar médico: {e}")
        return None


async def criar_medico(
    telefone: str,
    nome: Optional[str] = None,
    **kwargs
) -> Optional[dict]:
    """
    Cria novo registro de médico.

    Args:
        telefone: Número obrigatório
        nome: Nome do contato (do WhatsApp)
        **kwargs: Outros campos opcionais

    Returns:
        Dados do médico criado
    """
    try:
        dados = {
            "telefone": telefone,
            "stage_jornada": "novo",
            "source": "whatsapp_inbound",
        }

        if nome:
            # Tentar separar primeiro nome e sobrenome
            partes = nome.split(" ", 1)
            dados["primeiro_nome"] = partes[0]
            if len(partes) > 1:
                dados["sobrenome"] = partes[1]

        dados.update(kwargs)

        response = supabase.table("clientes").insert(dados).execute()
        logger.info(f"Médico criado: {telefone}")
        return response.data[0] if response.data else None

    except Exception as e:
        logger.error(f"Erro ao criar médico: {e}")
        return None


async def buscar_ou_criar_medico(
    telefone: str,
    nome_whatsapp: Optional[str] = None
) -> dict:
    """
    Busca médico existente ou cria novo.

    Args:
        telefone: Número do telefone
        nome_whatsapp: Nome vindo do WhatsApp (pushName)

    Returns:
        Dados do médico (existente ou novo)
    """
    # Tentar buscar existente
    medico = await buscar_medico_por_telefone(telefone)

    if medico:
        logger.debug(f"Médico encontrado: {medico.get('primeiro_nome', telefone)}")

        # Atualizar nome se não tinha
        if nome_whatsapp and not medico.get("primeiro_nome"):
            await atualizar_medico(medico["id"], nome_whatsapp=nome_whatsapp)

        return medico

    # Criar novo
    logger.info(f"Criando novo médico: {telefone}")
    return await criar_medico(telefone, nome=nome_whatsapp)


async def atualizar_medico(medico_id: str, **campos) -> Optional[dict]:
    """Atualiza campos do médico."""
    try:
        response = (
            supabase.table("clientes")
            .update(campos)
            .eq("id", medico_id)
            .execute()
        )
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error(f"Erro ao atualizar médico: {e}")
        return None


async def atualizar_stage(medico_id: str, novo_stage: str) -> bool:
    """Atualiza stage da jornada do médico."""
    result = await atualizar_medico(medico_id, stage_jornada=novo_stage)
    return result is not None
EOF
```

### 2. Testar

```python
# Em tests/test_medico.py
import pytest
from app.services.medico import buscar_ou_criar_medico

@pytest.mark.asyncio
async def test_buscar_ou_criar_novo():
    # Usar telefone único para teste
    telefone = "5511999990001"
    medico = await buscar_ou_criar_medico(telefone, "Dr. Teste")

    assert medico is not None
    assert medico["telefone"] == telefone

@pytest.mark.asyncio
async def test_buscar_existente():
    # Usar mesmo telefone
    telefone = "5511999990001"
    medico = await buscar_ou_criar_medico(telefone)

    assert medico is not None
    # Não deve criar duplicado
```

---

## DoD (Definition of Done)

- [ ] Arquivo `app/services/medico.py` criado
- [ ] Função `buscar_medico_por_telefone()` implementada
- [ ] Função `criar_medico()` implementada
- [ ] Função `buscar_ou_criar_medico()` implementada
- [ ] Médico existente é retornado
- [ ] Médico novo é criado se não existe
- [ ] Não cria duplicados

---
---

# S1.E2.3 - Buscar/criar conversa

## Objetivo

> **Gerenciar conversas: buscar ativa ou criar nova.**

Cada interação faz parte de uma conversa. Precisamos rastrear isso.

**Resultado esperado:** Função que retorna conversa ativa do médico ou cria nova.

---

## Responsável

**Dev**

---

## Tarefas

### 1. Criar serviço de conversas

```bash
cat > /Users/rafaelpivovar/Documents/Projetos/whatsapp-api/app/services/conversa.py << 'EOF'
"""
Serviço para gerenciamento de conversas.
"""
from typing import Optional, Literal
import logging
from datetime import datetime, timedelta

from app.services.supabase import supabase

logger = logging.getLogger(__name__)


async def buscar_conversa_ativa(cliente_id: str) -> Optional[dict]:
    """
    Busca conversa ativa (aberta) do cliente.

    Args:
        cliente_id: ID do médico

    Returns:
        Dados da conversa ou None
    """
    try:
        response = (
            supabase.table("conversations")
            .select("*")
            .eq("cliente_id", cliente_id)
            .eq("status", "aberta")
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error(f"Erro ao buscar conversa: {e}")
        return None


async def criar_conversa(
    cliente_id: str,
    origem: str = "inbound",
    controlled_by: Literal["ai", "human"] = "ai"
) -> Optional[dict]:
    """
    Cria nova conversa.

    Args:
        cliente_id: ID do médico
        origem: De onde veio (inbound, prospecção, campanha)
        controlled_by: Quem controla (ai ou human)

    Returns:
        Dados da conversa criada
    """
    try:
        response = (
            supabase.table("conversations")
            .insert({
                "cliente_id": cliente_id,
                "status": "aberta",
                "controlled_by": controlled_by,
                "origem": origem,
            })
            .execute()
        )
        logger.info(f"Conversa criada para cliente {cliente_id}")
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error(f"Erro ao criar conversa: {e}")
        return None


async def buscar_ou_criar_conversa(
    cliente_id: str,
    origem: str = "inbound"
) -> dict:
    """
    Busca conversa ativa ou cria nova.

    Args:
        cliente_id: ID do médico

    Returns:
        Dados da conversa
    """
    # Buscar conversa ativa
    conversa = await buscar_conversa_ativa(cliente_id)

    if conversa:
        logger.debug(f"Conversa ativa encontrada: {conversa['id']}")
        return conversa

    # Criar nova
    logger.info(f"Criando nova conversa para {cliente_id}")
    return await criar_conversa(cliente_id, origem=origem)


async def atualizar_conversa(conversa_id: str, **campos) -> Optional[dict]:
    """Atualiza campos da conversa."""
    try:
        campos["updated_at"] = datetime.utcnow().isoformat()
        response = (
            supabase.table("conversations")
            .update(campos)
            .eq("id", conversa_id)
            .execute()
        )
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error(f"Erro ao atualizar conversa: {e}")
        return None


async def fechar_conversa(conversa_id: str, motivo: str = "concluida") -> bool:
    """Fecha uma conversa."""
    result = await atualizar_conversa(
        conversa_id,
        status="fechada",
        motivo_fechamento=motivo
    )
    return result is not None


async def transferir_para_humano(conversa_id: str) -> bool:
    """Transfere conversa para controle humano."""
    result = await atualizar_conversa(
        conversa_id,
        controlled_by="human"
    )
    return result is not None


async def conversa_controlada_por_ia(conversa_id: str) -> bool:
    """Verifica se conversa está sob controle da IA."""
    try:
        response = (
            supabase.table("conversations")
            .select("controlled_by")
            .eq("id", conversa_id)
            .execute()
        )
        if response.data:
            return response.data[0]["controlled_by"] == "ai"
        return False
    except Exception as e:
        logger.error(f"Erro ao verificar controle: {e}")
        return False
EOF
```

---

## DoD (Definition of Done)

- [ ] Arquivo `app/services/conversa.py` criado
- [ ] Função `buscar_conversa_ativa()` implementada
- [ ] Função `criar_conversa()` implementada
- [ ] Função `buscar_ou_criar_conversa()` implementada
- [ ] Função `conversa_controlada_por_ia()` implementada
- [ ] Conversa existente é retornada
- [ ] Nova conversa é criada se não existe

---
---

# S1.E2.4 - Carregar histórico recente

## Objetivo

> **Carregar últimas mensagens da conversa para dar contexto ao LLM.**

O Claude precisa saber o que já foi dito para responder coerentemente.

**Resultado esperado:** Função que retorna últimas N interações da conversa.

---

## Responsável

**Dev**

---

## Tarefas

### 1. Criar serviço de interações

```bash
cat > /Users/rafaelpivovar/Documents/Projetos/whatsapp-api/app/services/interacao.py << 'EOF'
"""
Serviço para gerenciamento de interações (mensagens).
"""
from typing import Optional, Literal
import logging
from datetime import datetime

from app.services.supabase import supabase

logger = logging.getLogger(__name__)


async def salvar_interacao(
    conversa_id: str,
    tipo: Literal["entrada", "saida"],
    conteudo: str,
    remetente: Literal["medico", "julia", "gestor"],
    message_id: Optional[str] = None
) -> Optional[dict]:
    """
    Salva uma interação (mensagem) na conversa.

    Args:
        conversa_id: ID da conversa
        tipo: entrada (recebida) ou saida (enviada)
        conteudo: Texto da mensagem
        remetente: Quem enviou
        message_id: ID da mensagem no WhatsApp

    Returns:
        Dados da interação salva
    """
    try:
        dados = {
            "conversation_id": conversa_id,
            "tipo": tipo,
            "conteudo": conteudo,
            "remetente": remetente,
        }

        if message_id:
            dados["whatsapp_message_id"] = message_id

        response = supabase.table("interacoes").insert(dados).execute()
        logger.debug(f"Interação salva: {tipo} - {conteudo[:50]}...")
        return response.data[0] if response.data else None

    except Exception as e:
        logger.error(f"Erro ao salvar interação: {e}")
        return None


async def carregar_historico(
    conversa_id: str,
    limite: int = 10
) -> list[dict]:
    """
    Carrega últimas interações da conversa.

    Args:
        conversa_id: ID da conversa
        limite: Máximo de interações a retornar

    Returns:
        Lista de interações ordenadas da mais antiga para mais recente
    """
    try:
        response = (
            supabase.table("interacoes")
            .select("*")
            .eq("conversation_id", conversa_id)
            .order("created_at", desc=True)
            .limit(limite)
            .execute()
        )

        # Inverter para ordem cronológica
        return list(reversed(response.data)) if response.data else []

    except Exception as e:
        logger.error(f"Erro ao carregar histórico: {e}")
        return []


def formatar_historico_para_llm(interacoes: list[dict]) -> str:
    """
    Formata histórico para incluir no prompt do LLM.

    Returns:
        String formatada com as mensagens
    """
    if not interacoes:
        return "Nenhuma mensagem anterior."

    linhas = []
    for i in interacoes:
        remetente = "Médico" if i["remetente"] == "medico" else "Júlia"
        linhas.append(f"{remetente}: {i['conteudo']}")

    return "\n".join(linhas)


def converter_historico_para_messages(interacoes: list[dict]) -> list[dict]:
    """
    Converte histórico para formato de messages do Claude.

    Returns:
        Lista no formato [{"role": "user/assistant", "content": "..."}]
    """
    messages = []
    for i in interacoes:
        role = "user" if i["remetente"] == "medico" else "assistant"
        messages.append({
            "role": role,
            "content": i["conteudo"]
        })
    return messages
EOF
```

---

## DoD (Definition of Done)

- [ ] Arquivo `app/services/interacao.py` criado
- [ ] Função `salvar_interacao()` implementada
- [ ] Função `carregar_historico()` implementada
- [ ] Função `formatar_historico_para_llm()` implementada
- [ ] Função `converter_historico_para_messages()` implementada
- [ ] Histórico vem em ordem cronológica

---
---

# S1.E2.5 - Montar contexto para LLM

## Objetivo

> **Reunir todas as informações necessárias para o LLM gerar uma boa resposta.**

Contexto = médico + histórico + vagas disponíveis.

**Resultado esperado:** Função que monta contexto completo para o Claude.

---

## Responsável

**Dev**

---

## Tarefas

### 1. Criar serviço de contexto

```bash
cat > /Users/rafaelpivovar/Documents/Projetos/whatsapp-api/app/services/contexto.py << 'EOF'
"""
Serviço para montagem de contexto do agente.
"""
from typing import Optional
import logging

from app.services.interacao import carregar_historico, formatar_historico_para_llm

logger = logging.getLogger(__name__)


def formatar_contexto_medico(medico: dict) -> str:
    """
    Formata informações do médico para o prompt.

    Args:
        medico: Dados do médico do banco

    Returns:
        String formatada
    """
    partes = []

    # Nome
    nome = medico.get("primeiro_nome", "")
    if medico.get("sobrenome"):
        nome += f" {medico['sobrenome']}"

    if nome:
        partes.append(f"Nome: {nome}")

    # Título
    if medico.get("titulo"):
        partes.append(f"Título: {medico['titulo']}")

    # Especialidade
    if medico.get("especialidade"):
        partes.append(f"Especialidade: {medico['especialidade']}")

    # CRM
    if medico.get("crm"):
        crm = medico["crm"]
        if medico.get("estado"):
            crm = f"CRM-{medico['estado']} {crm}"
        partes.append(f"CRM: {crm}")

    # Cidade
    if medico.get("cidade"):
        partes.append(f"Cidade: {medico['cidade']}")

    # Stage
    if medico.get("stage_jornada"):
        partes.append(f"Status: {medico['stage_jornada']}")

    # Preferências
    if medico.get("preferencias_detectadas"):
        prefs = medico["preferencias_detectadas"]
        if isinstance(prefs, dict):
            if prefs.get("turnos"):
                partes.append(f"Prefere: {', '.join(prefs['turnos'])}")
            if prefs.get("valor_minimo"):
                partes.append(f"Valor mínimo: R$ {prefs['valor_minimo']}")

    return "\n".join(partes) if partes else "Médico novo, sem informações ainda."


def formatar_contexto_vagas(vagas: list[dict], limite: int = 3) -> str:
    """
    Formata vagas disponíveis para o prompt.

    Args:
        vagas: Lista de vagas do banco
        limite: Máximo de vagas a mostrar

    Returns:
        String formatada
    """
    if not vagas:
        return "Nenhuma vaga disponível no momento."

    linhas = []
    for v in vagas[:limite]:
        hospital = v.get("hospitais", {}).get("nome", "Hospital")
        data = v.get("data_plantao", "")
        periodo = v.get("periodos", {}).get("nome", "")
        valor = v.get("valor_min", 0)
        setor = v.get("setores", {}).get("nome", "")

        linha = f"- {hospital}, {data}, {periodo}"
        if setor:
            linha += f", {setor}"
        linha += f", R$ {valor:,.0f}"

        if v.get("prioridade") == "urgente":
            linha += " (URGENTE)"

        linhas.append(linha)

    return "\n".join(linhas)


async def montar_contexto_completo(
    medico: dict,
    conversa: dict,
    vagas: list[dict] = None
) -> dict:
    """
    Monta contexto completo para o agente.

    Args:
        medico: Dados do médico
        conversa: Dados da conversa
        vagas: Lista de vagas disponíveis (opcional)

    Returns:
        Dict com todos os contextos formatados
    """
    # Carregar histórico
    historico_raw = await carregar_historico(conversa["id"], limite=10)
    historico = formatar_historico_para_llm(historico_raw)

    # Verificar se é primeira mensagem
    primeira_msg = len(historico_raw) == 0

    return {
        "medico": formatar_contexto_medico(medico),
        "historico": historico,
        "historico_raw": historico_raw,
        "vagas": formatar_contexto_vagas(vagas) if vagas else "",
        "primeira_msg": primeira_msg,
        "controlled_by": conversa.get("controlled_by", "ai"),
    }
EOF
```

---

## DoD (Definition of Done)

- [ ] Arquivo `app/services/contexto.py` criado
- [ ] Função `formatar_contexto_medico()` implementada
- [ ] Função `formatar_contexto_vagas()` implementada
- [ ] Função `montar_contexto_completo()` implementada
- [ ] Contexto inclui: médico, histórico, vagas, primeira_msg

---
---

# S1.E2.6 - Chamar Claude e processar resposta

## Objetivo

> **Gerar resposta da Júlia usando o Claude com todo o contexto.**

Juntando tudo: prompt + contexto + mensagem → resposta.

**Resultado esperado:** Função que recebe mensagem e contexto, retorna resposta da Júlia.

---

## Responsável

**Dev**

---

## Tarefas

### 1. Criar serviço do agente

```bash
cat > /Users/rafaelpivovar/Documents/Projetos/whatsapp-api/app/services/agente.py << 'EOF'
"""
Serviço principal do agente Júlia.
"""
import logging
from typing import Optional

from app.core.prompts import montar_prompt_julia
from app.services.llm import gerar_resposta
from app.services.interacao import converter_historico_para_messages

logger = logging.getLogger(__name__)


async def gerar_resposta_julia(
    mensagem: str,
    contexto: dict,
    incluir_historico: bool = True
) -> str:
    """
    Gera resposta da Júlia para uma mensagem.

    Args:
        mensagem: Mensagem do médico
        contexto: Contexto montado (medico, historico, vagas, etc)
        incluir_historico: Se deve passar histórico como messages

    Returns:
        Texto da resposta gerada
    """
    # Montar system prompt
    system_prompt = montar_prompt_julia(
        contexto_medico=contexto.get("medico", ""),
        contexto_vagas=contexto.get("vagas", ""),
        historico=contexto.get("historico", ""),
        primeira_msg=contexto.get("primeira_msg", False)
    )

    # Montar histórico como messages (para o Claude ter contexto da conversa)
    historico_messages = []
    if incluir_historico and contexto.get("historico_raw"):
        historico_messages = converter_historico_para_messages(
            contexto["historico_raw"]
        )

    # Gerar resposta
    logger.info(f"Gerando resposta para: {mensagem[:50]}...")

    resposta = await gerar_resposta(
        mensagem=mensagem,
        historico=historico_messages,
        system_prompt=system_prompt,
        max_tokens=300,  # Respostas curtas
    )

    logger.info(f"Resposta gerada: {resposta[:50]}...")

    return resposta


async def processar_mensagem_completo(
    mensagem_texto: str,
    medico: dict,
    conversa: dict,
    vagas: list[dict] = None
) -> Optional[str]:
    """
    Processa mensagem completa: monta contexto e gera resposta.

    Args:
        mensagem_texto: Texto da mensagem do médico
        medico: Dados do médico
        conversa: Dados da conversa
        vagas: Vagas disponíveis (opcional)

    Returns:
        Texto da resposta ou None se erro
    """
    from app.services.contexto import montar_contexto_completo

    try:
        # Verificar se conversa está sob controle da IA
        if conversa.get("controlled_by") != "ai":
            logger.info("Conversa sob controle humano, não processando")
            return None

        # Montar contexto
        contexto = await montar_contexto_completo(medico, conversa, vagas)

        # Gerar resposta
        resposta = await gerar_resposta_julia(mensagem_texto, contexto)

        return resposta

    except Exception as e:
        logger.error(f"Erro ao processar mensagem: {e}")
        return None
EOF
```

---

## DoD (Definition of Done)

- [ ] Arquivo `app/services/agente.py` criado
- [ ] Função `gerar_resposta_julia()` implementada
- [ ] Função `processar_mensagem_completo()` implementada
- [ ] Resposta é gerada com base no contexto
- [ ] Histórico é passado para o Claude
- [ ] Conversa sob controle humano não é processada

---
---

# S1.E2.7 - Enviar resposta e salvar interação

## Objetivo

> **Enviar resposta via WhatsApp e salvar no banco.**

Último passo: a resposta precisa chegar no médico e ficar registrada.

**Resultado esperado:** Resposta enviada via WhatsApp e interação salva no banco.

---

## Responsável

**Dev**

---

## Tarefas

### 1. Atualizar processamento de webhook

Edite `app/api/routes/webhook.py` com o fluxo completo:

```python
"""
Webhook Evolution com fluxo completo.
"""
from fastapi import APIRouter, Request, BackgroundTasks
from fastapi.responses import JSONResponse
import asyncio
import logging

from app.services.parser import parsear_mensagem
from app.services.whatsapp import evolution, enviar_whatsapp, mostrar_online, mostrar_digitando
from app.services.medico import buscar_ou_criar_medico
from app.services.conversa import buscar_ou_criar_conversa, conversa_controlada_por_ia
from app.services.interacao import salvar_interacao
from app.services.agente import processar_mensagem_completo

router = APIRouter(prefix="/webhook", tags=["Webhooks"])
logger = logging.getLogger(__name__)


@router.post("/evolution")
async def evolution_webhook(request: Request, background_tasks: BackgroundTasks):
    """Recebe webhooks da Evolution API."""
    try:
        payload = await request.json()
        event = payload.get("event")

        if event == "messages.upsert":
            background_tasks.add_task(processar_mensagem, payload.get("data"))

        return JSONResponse({"status": "received"})

    except Exception as e:
        logger.error(f"Erro no webhook: {e}")
        return JSONResponse({"status": "error"})


async def processar_mensagem(data: dict):
    """
    Fluxo completo de processamento de mensagem.
    """
    # 1. Parsear mensagem
    mensagem = parsear_mensagem(data)
    if not mensagem:
        return

    # 2. Filtrar mensagens que não devemos processar
    if mensagem.from_me or mensagem.is_grupo or mensagem.is_status:
        logger.debug(f"Mensagem ignorada: from_me={mensagem.from_me}, grupo={mensagem.is_grupo}")
        return

    # 3. Ignorar mensagens sem texto (áudio, imagem, etc)
    if not mensagem.texto:
        logger.info(f"Mensagem sem texto (tipo: {mensagem.tipo}), ignorando por enquanto")
        # TODO: Responder "não consigo ouvir áudio" se for áudio
        return

    logger.info(f"Processando mensagem de {mensagem.telefone}: {mensagem.texto[:50]}")

    try:
        # 4. Feedback visual: marcar como lida e online
        await evolution.marcar_como_lida(mensagem.telefone, mensagem.message_id)
        await mostrar_online(mensagem.telefone)

        # 5. Buscar/criar médico
        medico = await buscar_ou_criar_medico(
            mensagem.telefone,
            nome_whatsapp=mensagem.nome_contato
        )
        if not medico:
            logger.error("Não foi possível obter/criar médico")
            return

        # 6. Buscar/criar conversa
        conversa = await buscar_ou_criar_conversa(medico["id"])
        if not conversa:
            logger.error("Não foi possível obter/criar conversa")
            return

        # 7. Verificar se IA pode responder
        if conversa.get("controlled_by") != "ai":
            logger.info("Conversa sob controle humano, não respondendo")
            return

        # 8. Salvar mensagem recebida
        await salvar_interacao(
            conversa_id=conversa["id"],
            tipo="entrada",
            conteudo=mensagem.texto,
            remetente="medico",
            message_id=mensagem.message_id
        )

        # 9. Mostrar digitando
        await asyncio.sleep(1)  # Pequena pausa
        await mostrar_digitando(mensagem.telefone)

        # 10. Gerar resposta
        resposta = await processar_mensagem_completo(
            mensagem_texto=mensagem.texto,
            medico=medico,
            conversa=conversa,
            vagas=[]  # TODO: Buscar vagas na Sprint 2
        )

        if not resposta:
            logger.error("Não foi possível gerar resposta")
            return

        # 11. Simular tempo de digitação
        tempo_digitacao = min(len(resposta) * 0.05, 3)  # 50ms por char, max 3s
        await asyncio.sleep(tempo_digitacao)

        # 12. Enviar resposta
        await enviar_whatsapp(mensagem.telefone, resposta)
        logger.info(f"Resposta enviada para {mensagem.telefone}")

        # 13. Salvar resposta enviada
        await salvar_interacao(
            conversa_id=conversa["id"],
            tipo="saida",
            conteudo=resposta,
            remetente="julia"
        )

        logger.info("Mensagem processada com sucesso!")

    except Exception as e:
        logger.error(f"Erro ao processar mensagem: {e}", exc_info=True)
```

### 2. Testar fluxo completo

1. Inicie a API
2. Envie "Oi" no WhatsApp para o número da Júlia
3. Observe:
   - Mensagem marcada como lida (✓✓ azul)
   - Status "online"
   - Status "digitando"
   - Resposta chega
4. Verifique no banco:
   - Médico existe (novo ou atualizado)
   - Conversa existe
   - 2 interações: entrada e saída

---

## DoD (Definition of Done)

- [ ] Webhook processa mensagem completa
- [ ] Médico é buscado/criado
- [ ] Conversa é buscada/criada
- [ ] Mensagem recebida é salva como interação
- [ ] Resposta é gerada pelo Claude
- [ ] Resposta é enviada via WhatsApp
- [ ] Resposta é salva como interação
- [ ] Feedback visual funciona (lida, online, digitando)
- [ ] Logs mostram fluxo completo
- [ ] Testado com 5 mensagens diferentes com sucesso

---

## Teste de Aceitação Final

```
1. Enviar "Oi" → Receber saudação informal
2. Enviar "Tenho interesse em plantão" → Receber pergunta sobre disponibilidade
3. Enviar "Isso é um robô?" → Júlia nega, diz que é escalista
4. Verificar banco: médico, conversa, interações existem
5. Tempo total < 30 segundos
```
