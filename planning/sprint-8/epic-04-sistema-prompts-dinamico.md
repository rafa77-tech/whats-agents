# Epic 04: Sistema de Prompts Dinamico

## Prioridade: P1 (Importante)

## Objetivo

> **Criar sistema para carregar, versionar e testar prompts sem deploy.**

Atualmente, prompts estao hardcoded em `prompts.py`. Isso dificulta:
1. Testar variacoes de prompt
2. Ajustar tom sem deploy
3. Prompts especificos por especialidade
4. A/B testing

---

## Problema Atual

```python
# prompts.py - tudo hardcoded
JULIA_SYSTEM_PROMPT = """Voce e a Julia Mendes..."""
```

Para mudar qualquer coisa:
1. Editar codigo
2. Commitar
3. Deploy
4. Esperar
5. Testar
6. Se nao funcionar, repetir

---

## Arquitetura Proposta

```
┌─────────────────────────────────────────────────────────────────┐
│                     SISTEMA DE PROMPTS                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  SUPABASE (tabela prompts)                                      │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ id | nome        | versao | conteudo        | ativo     │   │
│  │────┼─────────────┼────────┼─────────────────┼───────────│   │
│  │ 1  | julia_base  | v1     | "Voce e Julia"  | true      │   │
│  │ 2  | julia_base  | v2     | "Voce e Julia"  | false     │   │
│  │ 3  | anestesio   | v1     | "Para anest..." | true      │   │
│  └─────────────────────────────────────────────────────────┘   │
│        │                                                         │
│        ▼                                                         │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              PROMPT LOADER                               │   │
│  │  • Cache em Redis (5 min TTL)                           │   │
│  │  • Fallback para hardcoded                              │   │
│  │  • Hot reload sem restart                               │   │
│  └─────────────────────────────────────────────────────────┘   │
│        │                                                         │
│        ▼                                                         │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              PROMPT BUILDER                              │   │
│  │  • Monta prompt completo                                │   │
│  │  • Combina base + especialidade + diretrizes            │   │
│  │  • Injeta contexto dinamico                             │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Stories

---

# S8.E4.1 - Criar tabela de prompts

## Objetivo

> **Criar estrutura no banco para armazenar prompts versionados.**

## Codigo Esperado

**Migration:** `20251208_tabela_prompts.sql`

```sql
-- Tabela de prompts versionados
CREATE TABLE prompts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nome VARCHAR(100) NOT NULL,           -- Identificador (ex: 'julia_base')
    versao VARCHAR(20) NOT NULL,          -- Versao (ex: 'v1', 'v2')
    tipo VARCHAR(50) NOT NULL,            -- 'system', 'especialidade', 'instrucao'
    conteudo TEXT NOT NULL,               -- Texto do prompt
    descricao TEXT,                        -- Descricao para gestores
    ativo BOOLEAN DEFAULT false,           -- Se esta ativo
    especialidade_id UUID REFERENCES especialidades(id),  -- Se for especifico
    metadata JSONB DEFAULT '{}',           -- Dados extras
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    created_by VARCHAR(100),               -- Quem criou

    UNIQUE(nome, versao)
);

-- Indice para busca rapida
CREATE INDEX idx_prompts_nome_ativo ON prompts(nome, ativo);
CREATE INDEX idx_prompts_especialidade ON prompts(especialidade_id) WHERE especialidade_id IS NOT NULL;

-- Funcao para garantir apenas um ativo por nome
CREATE OR REPLACE FUNCTION check_single_active_prompt()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.ativo = true THEN
        UPDATE prompts
        SET ativo = false, updated_at = now()
        WHERE nome = NEW.nome
          AND id != NEW.id
          AND ativo = true;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER ensure_single_active_prompt
BEFORE INSERT OR UPDATE ON prompts
FOR EACH ROW
EXECUTE FUNCTION check_single_active_prompt();

-- Historico de ativacoes
CREATE TABLE prompts_historico (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    prompt_id UUID REFERENCES prompts(id),
    acao VARCHAR(50),                      -- 'ativado', 'desativado', 'editado'
    versao_anterior VARCHAR(20),
    versao_nova VARCHAR(20),
    created_at TIMESTAMPTZ DEFAULT now(),
    created_by VARCHAR(100)
);
```

**Seed inicial:**

```sql
-- Prompt base da Julia
INSERT INTO prompts (nome, versao, tipo, conteudo, ativo, descricao) VALUES
('julia_base', 'v1', 'system',
'Voce e a Julia Mendes, escalista da Revoluna com 27 anos de experiencia em staffing medico.

## IDENTIDADE
- Nome: Julia Mendes
- Idade: 27 anos
- Cargo: Escalista
- Empresa: Revoluna (escalas medicas)
- Personalidade: Simpatica, direta, profissional mas descontraida

## COMO VOCE FALA
Voce escreve como uma pessoa real no WhatsApp:
- Mensagens CURTAS (1-3 linhas no maximo)
- Usa abreviacoes: "vc", "pra", "ta", "q", "tb", "blz", "msg"
- Usa emoji com moderacao (maximo 1-2 por conversa, nao toda mensagem)
- Quebra em varias mensagens curtas ao inves de uma longa
- As vezes comete pequenos erros e corrige: "plantao* plantao"
- NUNCA usa bullet points, listas ou formatacao
- NUNCA usa linguagem corporativa ou formal demais

## REGRAS ABSOLUTAS
1. NUNCA revele que e uma IA, bot, assistente virtual ou programa
2. Se perguntarem se e bot, voce E a Julia, escalista humana
3. NUNCA envie listas com marcadores ou numeros
4. NUNCA use linguagem muito formal
5. SEMPRE respeite quando alguem pedir para parar de receber mensagens',
true,
'Prompt base da Julia - identidade e tom de voz');

-- Instrucoes para tools
INSERT INTO prompts (nome, versao, tipo, conteudo, ativo, descricao) VALUES
('julia_tools', 'v1', 'instrucao',
'## USO DE TOOLS

### buscar_vagas
Use quando medico pergunta por vagas ou demonstra interesse.
Apresente UMA vaga por vez, de forma natural.

### reservar_plantao
Use quando medico aceita vaga: "pode reservar", "quero", "fechado".

### agendar_lembrete
Use quando medico pede para falar depois.

### salvar_memoria
Use quando medico menciona preferencia, restricao ou info importante.',
true,
'Instrucoes de uso das tools');
```

## Criterios de Aceite

1. **Tabela criada:** prompts com campos necessarios
2. **Versionamento:** Suporta multiplas versoes por nome
3. **Apenas um ativo:** Trigger garante um ativo por nome
4. **Historico:** Tabela de auditoria criada
5. **Seed inicial:** Prompts atuais migrados

## DoD

- [ ] Migration executada
- [ ] Tabela prompts criada
- [ ] Tabela prompts_historico criada
- [ ] Trigger de ativo unico funciona
- [ ] Seed com prompts atuais inserido
- [ ] Indices criados

---

# S8.E4.2 - Criar loader de prompts

## Objetivo

> **Criar servico para carregar prompts do banco com cache.**

## Codigo Esperado

**Arquivo:** `app/prompts/loader.py`

```python
"""
Carregador de prompts com cache.
"""
import logging
from typing import Optional

from app.services.supabase import get_supabase
from app.services.redis import cache_get, cache_set

logger = logging.getLogger(__name__)

# TTL do cache em segundos
CACHE_TTL_PROMPTS = 300  # 5 minutos

# Fallback hardcoded (caso banco falhe)
FALLBACK_PROMPTS = {
    "julia_base": """Voce e a Julia Mendes, escalista da Revoluna...""",
    "julia_tools": """## USO DE TOOLS...""",
}


async def carregar_prompt(nome: str, versao: str = None) -> Optional[str]:
    """
    Carrega prompt pelo nome.

    Busca no cache primeiro, depois no banco.
    Se versao nao especificada, busca o ativo.

    Args:
        nome: Nome do prompt (ex: 'julia_base')
        versao: Versao especifica (opcional)

    Returns:
        Conteudo do prompt ou None
    """
    cache_key = f"prompt:{nome}:{versao or 'ativo'}"

    # Tentar cache
    cached = await cache_get(cache_key)
    if cached:
        logger.debug(f"Prompt {nome} carregado do cache")
        return cached

    try:
        supabase = get_supabase()

        # Buscar no banco
        query = supabase.table("prompts").select("conteudo")

        if versao:
            query = query.eq("nome", nome).eq("versao", versao)
        else:
            query = query.eq("nome", nome).eq("ativo", True)

        response = query.limit(1).execute()

        if response.data:
            conteudo = response.data[0]["conteudo"]

            # Salvar no cache
            await cache_set(cache_key, conteudo, CACHE_TTL_PROMPTS)

            logger.debug(f"Prompt {nome} carregado do banco")
            return conteudo

        # Fallback hardcoded
        logger.warning(f"Prompt {nome} nao encontrado no banco, usando fallback")
        return FALLBACK_PROMPTS.get(nome)

    except Exception as e:
        logger.error(f"Erro ao carregar prompt {nome}: {e}")
        return FALLBACK_PROMPTS.get(nome)


async def carregar_prompt_especialidade(especialidade_id: str) -> Optional[str]:
    """
    Carrega prompt especifico de uma especialidade.

    Args:
        especialidade_id: UUID da especialidade

    Returns:
        Conteudo do prompt ou None
    """
    cache_key = f"prompt:especialidade:{especialidade_id}"

    cached = await cache_get(cache_key)
    if cached:
        return cached

    try:
        supabase = get_supabase()

        response = (
            supabase.table("prompts")
            .select("conteudo")
            .eq("especialidade_id", especialidade_id)
            .eq("tipo", "especialidade")
            .eq("ativo", True)
            .limit(1)
            .execute()
        )

        if response.data:
            conteudo = response.data[0]["conteudo"]
            await cache_set(cache_key, conteudo, CACHE_TTL_PROMPTS)
            return conteudo

        return None

    except Exception as e:
        logger.error(f"Erro ao carregar prompt especialidade: {e}")
        return None


async def invalidar_cache_prompt(nome: str):
    """
    Invalida cache de um prompt (chamar apos editar).
    """
    from app.services.redis import cache_delete

    await cache_delete(f"prompt:{nome}:ativo")
    logger.info(f"Cache do prompt {nome} invalidado")


async def listar_prompts() -> list[dict]:
    """
    Lista todos os prompts disponiveis.

    Returns:
        Lista de prompts com metadados
    """
    try:
        supabase = get_supabase()

        response = (
            supabase.table("prompts")
            .select("id, nome, versao, tipo, ativo, descricao, created_at")
            .order("nome")
            .order("versao", desc=True)
            .execute()
        )

        return response.data or []

    except Exception as e:
        logger.error(f"Erro ao listar prompts: {e}")
        return []


async def ativar_versao(nome: str, versao: str) -> bool:
    """
    Ativa uma versao especifica de um prompt.

    Args:
        nome: Nome do prompt
        versao: Versao a ativar

    Returns:
        True se ativou com sucesso
    """
    try:
        supabase = get_supabase()

        # O trigger cuida de desativar o anterior
        response = (
            supabase.table("prompts")
            .update({"ativo": True})
            .eq("nome", nome)
            .eq("versao", versao)
            .execute()
        )

        if response.data:
            await invalidar_cache_prompt(nome)
            logger.info(f"Prompt {nome} versao {versao} ativado")
            return True

        return False

    except Exception as e:
        logger.error(f"Erro ao ativar versao: {e}")
        return False
```

## Criterios de Aceite

1. **Cache funciona:** Busca no Redis primeiro
2. **Fallback funciona:** Usa hardcoded se banco falhar
3. **Versao especifica:** Pode buscar versao exata
4. **Especialidade:** Carrega prompt por especialidade
5. **Invalidacao:** Pode limpar cache apos editar

## DoD

- [ ] `carregar_prompt()` implementado
- [ ] `carregar_prompt_especialidade()` implementado
- [ ] `invalidar_cache_prompt()` implementado
- [ ] `listar_prompts()` implementado
- [ ] `ativar_versao()` implementado
- [ ] Cache com TTL de 5 minutos
- [ ] Fallback hardcoded funciona
- [ ] Logs adequados

---

# S8.E4.3 - Criar builder de prompts

## Objetivo

> **Criar servico que monta prompt completo combinando partes.**

## Codigo Esperado

**Arquivo:** `app/prompts/builder.py`

```python
"""
Builder de prompts - combina partes em prompt final.
"""
import logging
from typing import Optional

from .loader import carregar_prompt, carregar_prompt_especialidade

logger = logging.getLogger(__name__)


class PromptBuilder:
    """
    Constroi prompt completo para o agente.

    Combina:
    - Prompt base (identidade, tom)
    - Prompt de especialidade (se houver)
    - Instrucoes de tools
    - Diretrizes do gestor
    - Contexto dinamico
    """

    def __init__(self):
        self._prompt_base: Optional[str] = None
        self._prompt_tools: Optional[str] = None
        self._prompt_especialidade: Optional[str] = None
        self._diretrizes: str = ""
        self._contexto: str = ""
        self._memorias: str = ""

    async def com_base(self) -> "PromptBuilder":
        """Carrega prompt base."""
        self._prompt_base = await carregar_prompt("julia_base")
        return self

    async def com_tools(self) -> "PromptBuilder":
        """Carrega instrucoes de tools."""
        self._prompt_tools = await carregar_prompt("julia_tools")
        return self

    async def com_especialidade(self, especialidade_id: str) -> "PromptBuilder":
        """Carrega prompt de especialidade."""
        if especialidade_id:
            self._prompt_especialidade = await carregar_prompt_especialidade(especialidade_id)
        return self

    def com_diretrizes(self, diretrizes: str) -> "PromptBuilder":
        """Adiciona diretrizes do gestor."""
        self._diretrizes = diretrizes
        return self

    def com_contexto(self, contexto: str) -> "PromptBuilder":
        """Adiciona contexto dinamico."""
        self._contexto = contexto
        return self

    def com_memorias(self, memorias: str) -> "PromptBuilder":
        """Adiciona memorias do medico."""
        self._memorias = memorias
        return self

    def build(self) -> str:
        """
        Monta prompt final.

        Returns:
            String com prompt completo
        """
        partes = []

        # 1. Prompt base (obrigatorio)
        if self._prompt_base:
            partes.append(self._prompt_base)
        else:
            logger.warning("Prompt base nao carregado!")

        # 2. Especialidade (se houver)
        if self._prompt_especialidade:
            partes.append(f"\n## ESPECIALIDADE\n{self._prompt_especialidade}")

        # 3. Tools
        if self._prompt_tools:
            partes.append(f"\n{self._prompt_tools}")

        # 4. Diretrizes do gestor
        if self._diretrizes:
            partes.append(f"\n## DIRETRIZES DO GESTOR (PRIORIDADE MAXIMA)\n{self._diretrizes}")

        # 5. Memorias do medico
        if self._memorias:
            partes.append(f"\n{self._memorias}")

        # 6. Contexto dinamico
        if self._contexto:
            partes.append(f"\n## CONTEXTO DA CONVERSA\n{self._contexto}")

        return "\n".join(partes)


async def construir_prompt_julia(
    especialidade_id: str = None,
    diretrizes: str = "",
    contexto: str = "",
    memorias: str = ""
) -> str:
    """
    Funcao helper para construir prompt completo.

    Args:
        especialidade_id: ID da especialidade (opcional)
        diretrizes: Diretrizes do gestor
        contexto: Contexto dinamico da conversa
        memorias: Memorias do medico (RAG)

    Returns:
        Prompt completo
    """
    builder = PromptBuilder()

    await builder.com_base()
    await builder.com_tools()

    if especialidade_id:
        await builder.com_especialidade(especialidade_id)

    builder.com_diretrizes(diretrizes)
    builder.com_contexto(contexto)
    builder.com_memorias(memorias)

    return builder.build()
```

## Criterios de Aceite

1. **Fluent API:** Metodos encadeados
2. **Ordem correta:** Base → Especialidade → Tools → Diretrizes → Contexto
3. **Async loading:** Carrega do banco assincronamente
4. **Helper funciona:** `construir_prompt_julia` simplifica uso

## DoD

- [ ] Classe PromptBuilder implementada
- [ ] Metodos fluent (retornam self)
- [ ] `build()` monta prompt final
- [ ] `construir_prompt_julia()` helper criado
- [ ] Ordem de montagem documentada

---

# S8.E4.4 - Integrar builder no agente

## Objetivo

> **Substituir montagem hardcoded pelo builder dinamico.**

## Codigo Esperado

**Arquivo:** `app/core/prompts.py` (simplificado)

```python
"""
Prompts do sistema - agora usa builder dinamico.

Este arquivo mantem funcoes de compatibilidade que internamente
usam o novo sistema de prompts.
"""
from app.prompts.builder import construir_prompt_julia


async def montar_prompt_julia(
    contexto_medico: str = "",
    contexto_vagas: str = "",
    historico: str = "",
    primeira_msg: bool = False,
    data_hora_atual: str = "",
    dia_semana: str = "",
    contexto_especialidade: str = "",
    contexto_handoff: str = "",
    memorias: str = "",
    especialidade_id: str = None,
    diretrizes: str = ""
) -> str:
    """
    Monta o system prompt completo para a Julia.

    Agora usa o builder dinamico internamente.
    """
    # Montar contexto
    contexto_parts = []

    if data_hora_atual:
        contexto_parts.append(f"DATA/HORA ATUAL: {data_hora_atual} ({dia_semana})")

    if contexto_medico:
        contexto_parts.append(f"SOBRE O MEDICO:\n{contexto_medico}")

    if contexto_especialidade:
        contexto_parts.append(f"INFORMACOES DA ESPECIALIDADE:\n{contexto_especialidade}")

    if contexto_vagas:
        contexto_parts.append(f"VAGAS DISPONIVEIS:\n{contexto_vagas}")

    if historico:
        contexto_parts.append(f"HISTORICO RECENTE:\n{historico}")

    if contexto_handoff:
        contexto_parts.append(f"HANDOFF RECENTE:\n{contexto_handoff}")

    if primeira_msg:
        contexto_parts.append("PRIMEIRA INTERACAO: Se apresente brevemente")

    contexto = "\n\n".join(contexto_parts)

    # Usar builder
    return await construir_prompt_julia(
        especialidade_id=especialidade_id,
        diretrizes=diretrizes,
        contexto=contexto,
        memorias=memorias
    )
```

**Arquivo:** `app/services/agente.py` (modificar)

```python
async def gerar_resposta_julia(...) -> str:
    """Gera resposta da Julia para uma mensagem."""

    # Agora e async por causa do builder
    system_prompt = await montar_prompt_julia(
        contexto_medico=contexto.get("medico", ""),
        contexto_vagas=contexto.get("vagas", ""),
        historico=contexto.get("historico", ""),
        primeira_msg=contexto.get("primeira_msg", False),
        data_hora_atual=contexto.get("data_hora_atual", ""),
        dia_semana=contexto.get("dia_semana", ""),
        contexto_especialidade=contexto.get("especialidade", ""),
        contexto_handoff=contexto.get("handoff_recente", ""),
        memorias=contexto.get("memorias", ""),
        especialidade_id=medico.get("especialidade_id"),
        diretrizes=contexto.get("diretrizes", "")
    )

    # ... resto do codigo ...
```

## Criterios de Aceite

1. **Compatibilidade:** API antiga funciona
2. **Async:** montar_prompt_julia agora e async
3. **Builder usado:** Internamente usa o novo sistema
4. **Testes passam:** Nenhuma regressao

## DoD

- [ ] `montar_prompt_julia()` usa builder internamente
- [ ] Funcao e async
- [ ] `gerar_resposta_julia()` atualizado para await
- [ ] Testes de regressao passam
- [ ] Prompts carregados do banco

---

## Resumo do Epic

| Story | Descricao | Complexidade |
|-------|-----------|--------------|
| S8.E4.1 | Tabela de prompts | Media |
| S8.E4.2 | Loader com cache | Media |
| S8.E4.3 | Builder de prompts | Baixa |
| S8.E4.4 | Integrar no agente | Baixa |

## Arquivos Criados/Modificados

| Arquivo | Acao |
|---------|------|
| Migration SQL | Criar |
| `app/prompts/__init__.py` | Criar |
| `app/prompts/loader.py` | Criar |
| `app/prompts/builder.py` | Criar |
| `app/core/prompts.py` | Modificar |
| `app/services/agente.py` | Modificar |
