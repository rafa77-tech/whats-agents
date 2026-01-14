# Epic 07: Templates de Mensagem no Banco

## Severidade: BAIXO

## Objetivo

Mover mensagens hardcoded para o banco de dados, permitindo atualizacao sem deploy.

## Problema Atual

### Mensagens Hardcoded

```python
# app/services/optout.py
MENSAGEM_CONFIRMACAO_OPTOUT = (
    "Entendi! Desativei seu cadastro aqui.\n\n"
    "Se mudar de ideia, é só me chamar que reativo rapidinho!"
)

# app/pipeline/pre_processors.py
def _gerar_resposta_agradecimento(self, action: str) -> str:
    if action == "confirmed":
        return (
            "Anotado! Obrigada pela confirmacao.\n\n"
            "Qualquer duvida é só falar!"
        )
```

### Consequencias

1. **Requer deploy:** Mudar texto = commit + deploy
2. **Sem versionamento:** Nao ha historico de mudancas
3. **Nao editavel:** Gestor nao pode ajustar mensagens
4. **Duplicacao:** Mesma mensagem em varios lugares

---

## Stories

### S30.E7.1: Criar Tabela `message_templates`

**Objetivo:** Criar tabela para armazenar templates de mensagem.

**Tarefas:**

1. Criar migration:

```sql
-- Migration: create_message_templates
-- Sprint 30 - S30.E7.1

CREATE TABLE IF NOT EXISTS public.message_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Identificacao
    key TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    description TEXT,

    -- Conteudo
    content TEXT NOT NULL,

    -- Categoria
    category TEXT NOT NULL CHECK (category IN (
        'optout',
        'confirmacao',
        'handoff',
        'erro',
        'boas_vindas',
        'followup'
    )),

    -- Controle
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    created_by TEXT,  -- Quem criou (slack user)
    updated_by TEXT   -- Ultima edicao
);

-- Indice para busca por key (mais comum)
CREATE INDEX IF NOT EXISTS idx_templates_key ON public.message_templates(key);

-- Indice para busca por categoria
CREATE INDEX IF NOT EXISTS idx_templates_category ON public.message_templates(category);

-- Comentarios
COMMENT ON TABLE message_templates IS 'Templates de mensagens da Julia - Sprint 30';
COMMENT ON COLUMN message_templates.key IS 'Chave unica para busca (ex: optout_confirmacao)';
COMMENT ON COLUMN message_templates.content IS 'Conteudo da mensagem, pode conter placeholders {nome}';
```

2. Aplicar migration:
   ```bash
   # Via MCP
   mcp__supabase-prod__apply_migration
   ```

3. Inserir templates iniciais:

```sql
-- Templates iniciais
INSERT INTO public.message_templates (key, name, content, category, description) VALUES
    -- Opt-out
    ('optout_confirmacao', 'Confirmacao de Opt-out',
     E'Entendi! Desativei seu cadastro aqui.\n\nSe mudar de ideia, é só me chamar que reativo rapidinho!',
     'optout', 'Mensagem enviada quando medico pede para sair da lista'),

    ('optout_ja_desativado', 'Ja esta Opt-out',
     'Vc ja estava fora da lista. Se quiser voltar, é só me avisar!',
     'optout', 'Quando medico pede optout mas ja estava fora'),

    -- Confirmacao de plantao
    ('confirmacao_recebida', 'Confirmacao Recebida',
     E'Anotado! Obrigada pela confirmacao.\n\nQualquer duvida é só falar!',
     'confirmacao', 'Quando medico confirma presenca no plantao'),

    ('confirmacao_cancelamento', 'Cancelamento Recebido',
     E'Entendi, cancelei sua reserva.\n\nSe surgir outro interesse, me avisa!',
     'confirmacao', 'Quando medico cancela plantao'),

    -- Handoff
    ('handoff_iniciando', 'Iniciando Handoff',
     'Vou pedir pra minha supervisora te ajudar, um momento!',
     'handoff', 'Quando conversa vai para humano'),

    ('handoff_humano_assumiu', 'Humano Assumiu',
     'Oi! Aqui é a {nome_supervisor}, como posso ajudar?',
     'handoff', 'Mensagem do humano ao assumir'),

    -- Erros
    ('erro_temporario', 'Erro Temporario',
     'Ops, tive um probleminha aqui. Pode repetir?',
     'erro', 'Quando ocorre erro recuperavel'),

    ('erro_sistema', 'Erro de Sistema',
     'Desculpa, estou com um problema tecnico. Vou pedir pra alguem te ajudar!',
     'erro', 'Quando ocorre erro grave'),

    -- Boas vindas
    ('boas_vindas_novo', 'Boas Vindas Novo Medico',
     E'Oi Dr {nome}! Tudo bem?\n\nSou a Julia da Revoluna, a gente trabalha com escalas medicas.',
     'boas_vindas', 'Primeira mensagem para medico novo'),

    -- Follow-up
    ('followup_sem_resposta', 'Follow-up Sem Resposta',
     E'Oi de novo! Vi que nao conseguimos conversar.\n\nSe tiver interesse em plantoes, me avisa!',
     'followup', 'Quando medico nao responde')
ON CONFLICT (key) DO NOTHING;
```

**DoD:**
- [ ] Migration criada
- [ ] Tabela `message_templates` criada
- [ ] Templates iniciais inseridos (10+)
- [ ] Commit: `feat(templates): cria tabela message_templates`

---

### S30.E7.2: Criar Repository de Templates

**Objetivo:** Criar repository para buscar templates com cache.

**Arquivo:** `app/services/templates/repository.py`

**Tarefas:**

1. Criar diretorio:
   ```bash
   mkdir -p app/services/templates
   ```

2. Criar `app/services/templates/repository.py`:

```python
"""
Repository para templates de mensagem.

Sprint 30 - S30.E7.2
"""
import logging
from typing import Optional, Dict
from functools import lru_cache

from app.services.supabase import supabase
from app.services.redis import redis_client

logger = logging.getLogger(__name__)

# TTL do cache em segundos (5 minutos)
CACHE_TTL = 300


class TemplateRepository:
    """
    Repository para templates de mensagem.

    Uso:
        repo = TemplateRepository()
        msg = await repo.get("optout_confirmacao", nome="Joao")
    """

    def __init__(self, use_cache: bool = True):
        self.use_cache = use_cache

    async def get(self, key: str, **placeholders) -> Optional[str]:
        """
        Busca template por key e substitui placeholders.

        Args:
            key: Chave do template (ex: 'optout_confirmacao')
            **placeholders: Valores para substituir (ex: nome='Joao')

        Returns:
            Mensagem formatada ou None se nao encontrar

        Example:
            msg = await repo.get("boas_vindas_novo", nome="Carlos")
            # Retorna: "Oi Dr Carlos! Tudo bem?..."
        """
        content = await self._get_content(key)
        if not content:
            logger.warning(f"Template nao encontrado: {key}")
            return None

        # Substituir placeholders
        try:
            return content.format(**placeholders)
        except KeyError as e:
            logger.error(f"Placeholder faltando em template {key}: {e}")
            return content  # Retorna sem substituir

    async def _get_content(self, key: str) -> Optional[str]:
        """Busca conteudo do template (com cache)."""
        # Tentar cache primeiro
        if self.use_cache:
            cached = await self._get_from_cache(key)
            if cached:
                return cached

        # Buscar do banco
        content = await self._get_from_db(key)
        if content and self.use_cache:
            await self._set_cache(key, content)

        return content

    async def _get_from_cache(self, key: str) -> Optional[str]:
        """Busca do cache Redis."""
        try:
            cache_key = f"template:{key}"
            return redis_client.get(cache_key)
        except Exception as e:
            logger.debug(f"Cache miss para template {key}: {e}")
            return None

    async def _set_cache(self, key: str, content: str) -> None:
        """Salva no cache Redis."""
        try:
            cache_key = f"template:{key}"
            redis_client.setex(cache_key, CACHE_TTL, content)
        except Exception as e:
            logger.debug(f"Erro ao cachear template {key}: {e}")

    async def _get_from_db(self, key: str) -> Optional[str]:
        """Busca do banco de dados."""
        try:
            response = (
                supabase.table("message_templates")
                .select("content")
                .eq("key", key)
                .eq("is_active", True)
                .execute()
            )
            if response.data:
                return response.data[0]["content"]
            return None
        except Exception as e:
            logger.error(f"Erro ao buscar template {key}: {e}")
            return None

    async def list_by_category(self, category: str) -> list:
        """Lista templates de uma categoria."""
        try:
            response = (
                supabase.table("message_templates")
                .select("key, name, content, description")
                .eq("category", category)
                .eq("is_active", True)
                .order("name")
                .execute()
            )
            return response.data or []
        except Exception as e:
            logger.error(f"Erro ao listar templates: {e}")
            return []

    async def update(self, key: str, content: str, updated_by: str) -> bool:
        """Atualiza conteudo de um template."""
        try:
            response = (
                supabase.table("message_templates")
                .update({
                    "content": content,
                    "updated_by": updated_by,
                    "updated_at": "now()"
                })
                .eq("key", key)
                .execute()
            )

            # Invalidar cache
            if self.use_cache:
                try:
                    redis_client.delete(f"template:{key}")
                except:
                    pass

            return bool(response.data)
        except Exception as e:
            logger.error(f"Erro ao atualizar template {key}: {e}")
            return False

    def invalidate_cache(self, key: str = None) -> None:
        """Invalida cache de template(s)."""
        try:
            if key:
                redis_client.delete(f"template:{key}")
            else:
                # Invalidar todos (pattern)
                for k in redis_client.scan_iter("template:*"):
                    redis_client.delete(k)
        except Exception as e:
            logger.debug(f"Erro ao invalidar cache: {e}")


# Singleton para uso facil
template_repo = TemplateRepository()


# Helper function
async def get_template(key: str, **placeholders) -> Optional[str]:
    """
    Busca template por key.

    Uso simples:
        from app.services.templates import get_template

        msg = await get_template("optout_confirmacao")
    """
    return await template_repo.get(key, **placeholders)
```

3. Criar `app/services/templates/__init__.py`:

```python
"""
Templates de mensagem.

Sprint 30 - S30.E7.2
"""
from .repository import (
    TemplateRepository,
    template_repo,
    get_template,
)

__all__ = [
    "TemplateRepository",
    "template_repo",
    "get_template",
]
```

**DoD:**
- [ ] `TemplateRepository` implementado
- [ ] Cache Redis funcionando
- [ ] `get_template` helper criado
- [ ] Commit: `feat(templates): cria repository com cache`

---

### S30.E7.3: Migrar Mensagens de Opt-out

**Objetivo:** Substituir mensagens hardcoded por templates do banco.

**Arquivo:** `app/services/optout.py`

**Tarefas:**

1. Identificar mensagens hardcoded:
   ```bash
   grep -n "MENSAGEM_\|= \"" app/services/optout.py
   ```

2. Substituir por templates:

   **Antes:**
   ```python
   MENSAGEM_CONFIRMACAO_OPTOUT = (
       "Entendi! Desativei seu cadastro aqui.\n\n"
       "Se mudar de ideia, é só me chamar que reativo rapidinho!"
   )

   async def processar_optout(telefone: str):
       # ...
       return MENSAGEM_CONFIRMACAO_OPTOUT
   ```

   **Depois:**
   ```python
   from app.services.templates import get_template

   async def processar_optout(telefone: str):
       # ...
       msg = await get_template("optout_confirmacao")
       return msg or "Cadastro desativado."  # Fallback
   ```

3. Manter fallback para caso template nao exista

4. Rodar testes:
   ```bash
   uv run pytest tests/services/test_optout.py -v
   ```

**DoD:**
- [ ] `MENSAGEM_*` constantes removidas
- [ ] Usando `get_template()`
- [ ] Fallback implementado
- [ ] Testes passando
- [ ] Commit: `refactor(optout): usa templates do banco`

---

### S30.E7.4: Migrar Mensagens de Confirmacao

**Objetivo:** Substituir mensagens de confirmacao de plantao.

**Arquivo:** `app/pipeline/pre_processors.py`

**Tarefas:**

1. Encontrar mensagens hardcoded:
   ```bash
   grep -n "return \"" app/pipeline/pre_processors.py | head -20
   ```

2. Substituir `_gerar_resposta_agradecimento`:

   **Antes:**
   ```python
   def _gerar_resposta_agradecimento(self, action: str) -> str:
       if action == "confirmed":
           return (
               "Anotado! Obrigada pela confirmacao.\n\n"
               "Qualquer duvida é só falar!"
           )
   ```

   **Depois:**
   ```python
   async def _gerar_resposta_agradecimento(self, action: str) -> str:
       key = f"confirmacao_{action}"
       msg = await get_template(key)
       return msg or "Anotado!"
   ```

3. Atualizar chamadores para async

4. Rodar testes

**DoD:**
- [ ] Mensagens de confirmacao migradas
- [ ] Fallbacks implementados
- [ ] Testes passando
- [ ] Commit: `refactor(pipeline): usa templates para confirmacoes`

---

### S30.E7.5: Adicionar Cache Redis

**Objetivo:** Garantir que cache esta funcionando corretamente.

**Tarefas:**

1. Verificar integracao com Redis existente

2. Criar teste de cache:

```python
# tests/services/templates/test_cache.py
import pytest
from unittest.mock import patch, MagicMock

from app.services.templates import TemplateRepository


class TestTemplateCache:
    """Testes de cache de templates."""

    @pytest.mark.asyncio
    async def test_usa_cache_quando_disponivel(self):
        """Deve usar cache se disponivel."""
        with patch("app.services.templates.repository.redis_client") as mock_redis:
            mock_redis.get.return_value = "Mensagem cacheada"

            repo = TemplateRepository()
            msg = await repo.get("test_key")

            assert msg == "Mensagem cacheada"
            mock_redis.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_busca_db_se_cache_vazio(self):
        """Deve buscar do DB se cache vazio."""
        with patch("app.services.templates.repository.redis_client") as mock_redis:
            mock_redis.get.return_value = None

            with patch("app.services.templates.repository.supabase") as mock_db:
                mock_db.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
                    {"content": "Mensagem do DB"}
                ]

                repo = TemplateRepository()
                msg = await repo.get("test_key")

                assert msg == "Mensagem do DB"

    @pytest.mark.asyncio
    async def test_invalida_cache_apos_update(self):
        """Deve invalidar cache apos update."""
        with patch("app.services.templates.repository.redis_client") as mock_redis:
            with patch("app.services.templates.repository.supabase") as mock_db:
                mock_db.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [{}]

                repo = TemplateRepository()
                await repo.update("test_key", "novo conteudo", "user")

                mock_redis.delete.assert_called_with("template:test_key")
```

**DoD:**
- [ ] Cache Redis integrado
- [ ] Testes de cache passando
- [ ] TTL configurado (5 min)
- [ ] Commit: `test(templates): testes de cache`

---

### S30.E7.6: Criar Interface Admin (Slack)

**Objetivo:** Permitir edicao de templates via Slack.

**Arquivo:** `app/tools/slack/template_tools.py`

**Tarefas:**

1. Criar tools para Slack:

```python
"""
Tools de templates para Slack.

Sprint 30 - S30.E7.6
"""
from app.services.templates import template_repo


async def listar_templates(category: str = None) -> str:
    """Lista templates disponiveis."""
    if category:
        templates = await template_repo.list_by_category(category)
    else:
        # Listar todas categorias
        templates = []
        for cat in ['optout', 'confirmacao', 'handoff', 'erro']:
            templates.extend(await template_repo.list_by_category(cat))

    if not templates:
        return "Nenhum template encontrado."

    lines = ["*Templates disponiveis:*\n"]
    for t in templates:
        lines.append(f"- `{t['key']}`: {t['name']}")

    return "\n".join(lines)


async def ver_template(key: str) -> str:
    """Mostra conteudo de um template."""
    content = await template_repo._get_from_db(key)
    if not content:
        return f"Template `{key}` nao encontrado."

    return f"*Template `{key}`:*\n```\n{content}\n```"


async def editar_template(key: str, novo_conteudo: str, usuario: str) -> str:
    """Edita conteudo de um template."""
    success = await template_repo.update(key, novo_conteudo, usuario)
    if success:
        return f"Template `{key}` atualizado com sucesso!"
    return f"Erro ao atualizar template `{key}`."
```

2. Registrar tools no agente Slack

3. Testar via Slack:
   ```
   @julia listar templates
   @julia ver template optout_confirmacao
   @julia editar template optout_confirmacao "Nova mensagem aqui"
   ```

**DoD:**
- [ ] Tools de template criadas
- [ ] Registradas no agente Slack
- [ ] Funcionando via Slack
- [ ] Commit: `feat(slack): tools para gerenciar templates`

---

## Checklist do Epic

- [ ] **S30.E7.1** - Tabela criada
- [ ] **S30.E7.2** - Repository implementado
- [ ] **S30.E7.3** - Opt-out migrado
- [ ] **S30.E7.4** - Confirmacoes migradas
- [ ] **S30.E7.5** - Cache funcionando
- [ ] **S30.E7.6** - Interface Slack
- [ ] Todas mensagens hardcoded migradas
- [ ] Testes passando

---

## Arquivos Criados/Modificados

| Arquivo | Acao | Linhas |
|---------|------|--------|
| Migration | Criar | ~50 |
| `app/services/templates/__init__.py` | Criar | ~15 |
| `app/services/templates/repository.py` | Criar | ~150 |
| `app/services/optout.py` | Modificar | ~-20 |
| `app/pipeline/pre_processors.py` | Modificar | ~-20 |
| `app/tools/slack/template_tools.py` | Criar | ~50 |
| Tests | Criar | ~80 |

---

## Tempo Estimado

| Story | Complexidade | Estimativa |
|-------|--------------|------------|
| S30.E7.1 | Baixa | 30min |
| S30.E7.2 | Baixa | 1h |
| S30.E7.3 | Baixa | 30min |
| S30.E7.4 | Baixa | 30min |
| S30.E7.5 | Baixa | 30min |
| S30.E7.6 | Media | 1h |
| **Total** | | **~4h** |

---

## Beneficios

1. **Sem deploy:** Gestor pode editar mensagens em tempo real
2. **Versionamento:** Historico de quem editou quando
3. **A/B Testing:** Facil trocar mensagens para testar
4. **Centralizacao:** Todas mensagens em um lugar
5. **Cache:** Performance mantida com Redis
