# E06: Testes e Documentacao

## Objetivo

Garantir cobertura de testes completa para a funcionalidade de valor flexivel e atualizar a documentacao do projeto.

## Dependencias

- E01 a E05 completos

## Escopo

### Incluido
- Testes end-to-end do fluxo completo
- Testes de regressao para vagas existentes
- Atualizacao do CLAUDE.md
- Atualizacao da documentacao de banco de dados
- Queries de validacao em producao

### Excluido
- Testes de carga/performance
- Documentacao de usuario final

---

## Tarefas

### T01: Testes End-to-End do Fluxo de Pipeline

**Arquivo:** `tests/e2e/test_pipeline_valor_flexivel.py`

```python
"""
Testes end-to-end para pipeline de vagas com valor flexivel.

Fluxo testado:
1. Mensagem chega no grupo WhatsApp
2. Pipeline extrai dados (incluindo valor flexivel)
3. Vaga e criada com campos corretos
4. Vaga e importada para tabela principal
5. Julia oferece vaga ao medico com valor correto
"""
import pytest
from uuid import uuid4
from datetime import date, timedelta

from app.services.grupos.fila import adicionar_mensagem_fila
from app.services.grupos.pipeline_worker import PipelineGrupos
from app.services.supabase import supabase


class TestPipelineValorFlexivelE2E:
    """Testes end-to-end para valor flexivel."""

    @pytest.fixture
    async def setup_grupo(self):
        """Cria grupo de teste."""
        grupo_id = str(uuid4())
        # Setup grupo no banco se necessario
        yield grupo_id
        # Cleanup

    @pytest.mark.asyncio
    async def test_fluxo_completo_valor_fixo(self, setup_grupo):
        """
        Testa fluxo completo para mensagem com valor fixo.

        Mensagem: "Vaga no Hospital ABC, dia 15/01, noturno, R$ 1.800"
        Esperado: valor=1800, valor_tipo='fixo'
        """
        grupo_id = setup_grupo
        data_plantao = (date.today() + timedelta(days=7)).strftime("%d/%m")

        mensagem = {
            "grupo_id": grupo_id,
            "texto": f"Vaga no Hospital ABC, dia {data_plantao}, noturno, R$ 1.800 PJ",
            "autor": "Admin",
            "timestamp": "2025-01-08T10:00:00Z"
        }

        # 1. Adicionar na fila
        msg_id = await adicionar_mensagem_fila(mensagem)
        assert msg_id is not None

        # 2. Processar pipeline
        pipeline = PipelineGrupos()
        await pipeline.processar_mensagem(msg_id)

        # 3. Verificar vaga_grupo criada
        result = supabase.table("vagas_grupo") \
            .select("*") \
            .eq("mensagem_id", str(msg_id)) \
            .execute()

        assert len(result.data) == 1
        vaga_grupo = result.data[0]

        assert vaga_grupo["valor"] == 1800
        assert vaga_grupo["valor_tipo"] == "fixo"
        assert vaga_grupo["valor_minimo"] is None
        assert vaga_grupo["valor_maximo"] is None

    @pytest.mark.asyncio
    async def test_fluxo_completo_valor_a_combinar(self, setup_grupo):
        """
        Testa fluxo completo para mensagem com valor a combinar.

        Mensagem: "Vaga no Hospital ABC, dia 15/01, noturno, valor a combinar"
        Esperado: valor=None, valor_tipo='a_combinar'
        """
        grupo_id = setup_grupo
        data_plantao = (date.today() + timedelta(days=7)).strftime("%d/%m")

        mensagem = {
            "grupo_id": grupo_id,
            "texto": f"Urgente! Hospital ABC precisa de plantonista, {data_plantao}, noturno. Valor a combinar",
            "autor": "Admin",
            "timestamp": "2025-01-08T10:00:00Z"
        }

        msg_id = await adicionar_mensagem_fila(mensagem)
        pipeline = PipelineGrupos()
        await pipeline.processar_mensagem(msg_id)

        result = supabase.table("vagas_grupo") \
            .select("*") \
            .eq("mensagem_id", str(msg_id)) \
            .execute()

        assert len(result.data) == 1
        vaga_grupo = result.data[0]

        assert vaga_grupo["valor"] is None
        assert vaga_grupo["valor_tipo"] == "a_combinar"

    @pytest.mark.asyncio
    async def test_fluxo_completo_valor_faixa(self, setup_grupo):
        """
        Testa fluxo completo para mensagem com faixa de valor.

        Mensagem: "Vaga no Hospital ABC, dia 15/01, valor entre R$ 1.500 e R$ 2.000"
        Esperado: valor_tipo='faixa', valor_minimo=1500, valor_maximo=2000
        """
        grupo_id = setup_grupo
        data_plantao = (date.today() + timedelta(days=7)).strftime("%d/%m")

        mensagem = {
            "grupo_id": grupo_id,
            "texto": f"Hospital ABC, {data_plantao}, noturno. Valor entre R$ 1.500 e R$ 2.000",
            "autor": "Admin",
            "timestamp": "2025-01-08T10:00:00Z"
        }

        msg_id = await adicionar_mensagem_fila(mensagem)
        pipeline = PipelineGrupos()
        await pipeline.processar_mensagem(msg_id)

        result = supabase.table("vagas_grupo") \
            .select("*") \
            .eq("mensagem_id", str(msg_id)) \
            .execute()

        assert len(result.data) == 1
        vaga_grupo = result.data[0]

        assert vaga_grupo["valor_tipo"] == "faixa"
        assert vaga_grupo["valor_minimo"] == 1500
        assert vaga_grupo["valor_maximo"] == 2000


class TestJuliaOfertaValorE2E:
    """Testes end-to-end para oferta de vagas pela Julia."""

    @pytest.mark.asyncio
    async def test_julia_oferece_vaga_a_combinar(self):
        """
        Testa que Julia oferece vaga 'a combinar' corretamente.

        Esperado:
        - Mensagem menciona que valor sera negociado
        - Julia nao inventa valor
        """
        # Setup: criar vaga a_combinar no banco
        # Chamar tool buscar_vagas
        # Verificar contexto retornado
        pass  # Implementar quando integracao estiver pronta

    @pytest.mark.asyncio
    async def test_julia_oferece_vaga_faixa(self):
        """
        Testa que Julia oferece vaga com faixa corretamente.

        Esperado:
        - Mensagem menciona faixa de valores
        - Julia nao mostra valor unico
        """
        pass  # Implementar quando integracao estiver pronta
```

**DoD:**
- [ ] Testes e2e criados
- [ ] Fixtures de setup funcionando
- [ ] Todos os 3 cenarios cobertos
- [ ] Cleanup apos testes

---

### T02: Testes de Regressao

**Arquivo:** `tests/regression/test_vagas_existentes.py`

```python
"""
Testes de regressao para garantir que vagas existentes continuam funcionando.

Verifica:
1. Vagas antigas com apenas campo 'valor' funcionam
2. Migracao definiu valor_tipo corretamente
3. Tools continuam funcionando com dados antigos
"""
import pytest
from app.services.vagas.formatters import formatar_para_mensagem, formatar_valor_para_mensagem
from app.tools.vagas import _formatar_valor_display


class TestRegressaoVagasExistentes:
    """Testes de regressao para vagas existentes."""

    def test_vaga_sem_valor_tipo_assume_fixo(self):
        """Vaga antiga sem valor_tipo assume 'fixo' como default."""
        vaga = {
            "valor": 1800,
            # Sem valor_tipo, valor_minimo, valor_maximo
        }

        resultado = formatar_valor_para_mensagem(vaga)
        assert "1.800" in resultado

    def test_vaga_sem_valor_sem_tipo_retorna_vazio(self):
        """Vaga antiga sem valor e sem tipo retorna string vazia."""
        vaga = {}  # Vaga totalmente vazia

        resultado = formatar_valor_para_mensagem(vaga)
        assert resultado == ""

    def test_formatador_mensagem_com_vaga_antiga(self):
        """formatar_para_mensagem funciona com vaga no formato antigo."""
        vaga = {
            "hospitais": {"nome": "Hospital ABC"},
            "data": "2025-01-15",
            "periodos": {"nome": "Noturno"},
            "valor": 2000,
            # Sem novos campos
        }

        resultado = formatar_para_mensagem(vaga)
        assert "Hospital ABC" in resultado
        assert "2.000" in resultado

    def test_tool_display_com_vaga_antiga(self):
        """_formatar_valor_display funciona com vaga no formato antigo."""
        vaga = {"valor": 1500}

        resultado = _formatar_valor_display(vaga)
        assert "1.500" in resultado


class TestRegressaoConsistencia:
    """Testes de consistencia entre dados antigos e novos."""

    @pytest.mark.asyncio
    async def test_vagas_migradas_tem_valor_tipo(self):
        """Todas as vagas migradas devem ter valor_tipo definido."""
        from app.services.supabase import supabase

        result = supabase.table("vagas") \
            .select("id, valor, valor_tipo") \
            .is_("valor_tipo", "null") \
            .limit(1) \
            .execute()

        assert len(result.data) == 0, "Encontradas vagas sem valor_tipo"

    @pytest.mark.asyncio
    async def test_vagas_grupo_migradas_tem_valor_tipo(self):
        """Todas as vagas_grupo migradas devem ter valor_tipo definido."""
        from app.services.supabase import supabase

        result = supabase.table("vagas_grupo") \
            .select("id, valor, valor_tipo") \
            .is_("valor_tipo", "null") \
            .limit(1) \
            .execute()

        assert len(result.data) == 0, "Encontradas vagas_grupo sem valor_tipo"
```

**DoD:**
- [ ] Testes de regressao criados
- [ ] Default para valor_tipo testado
- [ ] Formato antigo continua funcionando
- [ ] Migracao validada

---

### T03: Atualizar CLAUDE.md

**Arquivo:** `CLAUDE.md`

**Adicionar na secao de Banco de Dados:**

```markdown
### Campos de Valor em Vagas

As tabelas `vagas` e `vagas_grupo` suportam tres tipos de valor:

| Campo | Tipo | Descricao |
|-------|------|-----------|
| `valor` | INTEGER | Valor fixo (quando valor_tipo = 'fixo') |
| `valor_minimo` | INTEGER | Limite inferior da faixa |
| `valor_maximo` | INTEGER | Limite superior da faixa |
| `valor_tipo` | TEXT | Tipo: 'fixo', 'a_combinar', 'faixa' |

**Cenarios de Uso:**

| Cenario | valor | valor_minimo | valor_maximo | valor_tipo |
|---------|-------|--------------|--------------|------------|
| R$ 1.800 | 1800 | null | null | fixo |
| A combinar | null | null | null | a_combinar |
| R$ 1.500 a 2.000 | null | 1500 | 2000 | faixa |
| A partir de 1.500 | null | 1500 | null | faixa |
```

**Atualizar Sprint Atual:**

```markdown
**Sprint Atual:** 19 - Valor Flexivel em Vagas
```

**Atualizar Tabela de Sprints:**

```markdown
| Sprint | Foco | Status |
|--------|------|--------|
| 19 | Valor Flexivel em Vagas | ✅ Completa |
```

**DoD:**
- [ ] CLAUDE.md atualizado
- [ ] Documentacao de campos de valor
- [ ] Sprint atual atualizado

---

### T04: Atualizar Documentacao de Banco de Dados

**Arquivo:** `docs/banco-de-dados.md`

**Adicionar secao:**

```markdown
## Valor Flexivel em Vagas

### Schema

As tabelas `vagas` e `vagas_grupo` foram atualizadas na Sprint 19 para suportar
valores flexiveis:

```sql
-- Campos adicionados
valor_minimo INTEGER,
valor_maximo INTEGER,
valor_tipo TEXT DEFAULT 'fixo' CHECK (valor_tipo IN ('fixo', 'a_combinar', 'faixa'))
```

### Triggers de Validacao

Trigger `validar_valor_vaga` garante consistencia:

1. `valor_tipo = 'fixo'` requer `valor > 0`
2. `valor_tipo = 'faixa'` requer pelo menos `valor_minimo` ou `valor_maximo`
3. `valor_minimo` nao pode ser maior que `valor_maximo`

### Queries Uteis

```sql
-- Distribuicao por tipo de valor
SELECT
    valor_tipo,
    COUNT(*) as total,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 1) as percentual
FROM vagas
WHERE status = 'aberta'
GROUP BY valor_tipo;

-- Vagas com faixa de valor
SELECT
    v.id,
    h.nome as hospital,
    v.data,
    v.valor_minimo,
    v.valor_maximo
FROM vagas v
JOIN hospitais h ON v.hospital_id = h.id
WHERE v.valor_tipo = 'faixa'
AND v.status = 'aberta'
ORDER BY v.data;
```
```

**DoD:**
- [ ] Documentacao de banco atualizada
- [ ] Schema documentado
- [ ] Triggers documentados
- [ ] Queries uteis adicionadas

---

### T05: Queries de Validacao em Producao

**Arquivo:** `scripts/validacao_valor_flexivel.sql`

```sql
-- =========================================================
-- QUERIES DE VALIDACAO POS-DEPLOY - VALOR FLEXIVEL
-- Executar apos deploy da Sprint 19
-- =========================================================

-- 1. Verificar estrutura das colunas
SELECT
    table_name,
    column_name,
    data_type,
    column_default,
    is_nullable
FROM information_schema.columns
WHERE table_name IN ('vagas', 'vagas_grupo')
AND column_name IN ('valor', 'valor_minimo', 'valor_maximo', 'valor_tipo')
ORDER BY table_name, column_name;

-- 2. Verificar constraints existem
SELECT
    conname as constraint_name,
    conrelid::regclass as table_name,
    pg_get_constraintdef(oid) as definition
FROM pg_constraint
WHERE conname LIKE '%valor_tipo%';

-- 3. Verificar triggers existem
SELECT
    trigger_name,
    event_object_table,
    action_timing,
    event_manipulation
FROM information_schema.triggers
WHERE trigger_name LIKE '%validar_valor%';

-- 4. Distribuicao de valor_tipo em vagas
SELECT
    'vagas' as tabela,
    valor_tipo,
    COUNT(*) as total,
    ROUND(COUNT(*) * 100.0 / NULLIF(SUM(COUNT(*)) OVER(), 0), 1) as percentual
FROM vagas
GROUP BY valor_tipo

UNION ALL

SELECT
    'vagas_grupo' as tabela,
    valor_tipo,
    COUNT(*) as total,
    ROUND(COUNT(*) * 100.0 / NULLIF(SUM(COUNT(*)) OVER(), 0), 1) as percentual
FROM vagas_grupo
GROUP BY valor_tipo

ORDER BY tabela, valor_tipo;

-- 5. Verificar nenhuma vaga com valor_tipo NULL
SELECT
    'vagas' as tabela,
    COUNT(*) as sem_valor_tipo
FROM vagas
WHERE valor_tipo IS NULL

UNION ALL

SELECT
    'vagas_grupo' as tabela,
    COUNT(*) as sem_valor_tipo
FROM vagas_grupo
WHERE valor_tipo IS NULL;

-- 6. Verificar consistencia (fixo deve ter valor)
SELECT
    'inconsistente_fixo' as problema,
    COUNT(*) as total
FROM vagas
WHERE valor_tipo = 'fixo'
AND (valor IS NULL OR valor <= 0)

UNION ALL

SELECT
    'inconsistente_faixa' as problema,
    COUNT(*) as total
FROM vagas
WHERE valor_tipo = 'faixa'
AND valor_minimo IS NULL
AND valor_maximo IS NULL;

-- 7. Verificar valores da faixa sao coerentes
SELECT
    id,
    valor_minimo,
    valor_maximo
FROM vagas
WHERE valor_tipo = 'faixa'
AND valor_minimo IS NOT NULL
AND valor_maximo IS NOT NULL
AND valor_minimo > valor_maximo;

-- 8. Estatisticas de valores
SELECT
    valor_tipo,
    COUNT(*) as total,
    AVG(COALESCE(valor, valor_minimo, valor_maximo)) as valor_medio,
    MIN(COALESCE(valor, valor_minimo)) as valor_min,
    MAX(COALESCE(valor, valor_maximo)) as valor_max
FROM vagas
WHERE status = 'aberta'
GROUP BY valor_tipo;

-- 9. Amostra de cada tipo
SELECT 'fixo' as tipo, id, valor, valor_minimo, valor_maximo FROM vagas WHERE valor_tipo = 'fixo' LIMIT 3
UNION ALL
SELECT 'a_combinar', id, valor, valor_minimo, valor_maximo FROM vagas WHERE valor_tipo = 'a_combinar' LIMIT 3
UNION ALL
SELECT 'faixa', id, valor, valor_minimo, valor_maximo FROM vagas WHERE valor_tipo = 'faixa' LIMIT 3;
```

**DoD:**
- [ ] Script de validacao criado
- [ ] Queries cobrem estrutura, dados e consistencia
- [ ] Documentado como executar

---

### T06: Checklist de Validacao Manual

**Arquivo:** `docs/validacao-sprint-19.md`

```markdown
# Checklist de Validacao - Sprint 19

## Pre-Deploy

- [ ] Backup do banco realizado
- [ ] Migracoes testadas em ambiente de dev
- [ ] Testes automatizados passando

## Deploy

- [ ] Migracoes aplicadas em ordem:
  - [ ] add_valor_flexivel_vagas_grupo
  - [ ] migrate_valor_existente_vagas_grupo
  - [ ] add_valor_flexivel_vagas
  - [ ] migrate_valor_existente_vagas
  - [ ] fn_validar_valor_vaga

## Pos-Deploy - Banco

- [ ] Executar queries de validacao
- [ ] Confirmar nenhum valor_tipo NULL
- [ ] Confirmar constraints funcionando
- [ ] Confirmar triggers funcionando

## Pos-Deploy - Pipeline

- [ ] Enviar mensagem de teste com valor fixo
- [ ] Enviar mensagem de teste com "a combinar"
- [ ] Enviar mensagem de teste com faixa
- [ ] Verificar vagas_grupo criadas corretamente
- [ ] Verificar vagas importadas corretamente

## Pos-Deploy - Julia

- [ ] Buscar vagas e verificar formatacao
- [ ] Reservar vaga fixa - verificar mensagem
- [ ] Reservar vaga "a combinar" - verificar Julia pergunta expectativa
- [ ] Reservar vaga faixa - verificar mensagem de faixa

## Pos-Deploy - Slack

- [ ] Listar vagas - verificar exibicao de valor
- [ ] Confirmar reserva fixa - verificar formatacao
- [ ] Confirmar reserva "a combinar" - verificar nota
- [ ] Confirmar reserva faixa - verificar nota

## Rollback (se necessario)

- [ ] Executar script de rollback do E01
- [ ] Reverter codigo via git
- [ ] Reiniciar servicos
```

**DoD:**
- [ ] Checklist criado
- [ ] Passos de validacao claros
- [ ] Instrucoes de rollback

---

## Arquivos Criados/Modificados

| Arquivo | Tipo | Descricao |
|---------|------|-----------|
| `tests/e2e/test_pipeline_valor_flexivel.py` | Criar | Testes e2e |
| `tests/regression/test_vagas_existentes.py` | Criar | Testes de regressao |
| `CLAUDE.md` | Modificar | Documentar valor flexivel |
| `docs/banco-de-dados.md` | Modificar | Documentar schema |
| `scripts/validacao_valor_flexivel.sql` | Criar | Queries de validacao |
| `docs/validacao-sprint-19.md` | Criar | Checklist manual |

---

## DoD do Epico

- [ ] T01 completa - Testes e2e criados
- [ ] T02 completa - Testes de regressao criados
- [ ] T03 completa - CLAUDE.md atualizado
- [ ] T04 completa - Docs de banco atualizados
- [ ] T05 completa - Script de validacao criado
- [ ] T06 completa - Checklist manual criado
- [ ] Todos os testes passando
- [ ] Documentacao revisada
- [ ] Pronto para deploy

---

## Metricas de Cobertura

| Componente | Testes Antes | Testes Depois | Delta |
|------------|--------------|---------------|-------|
| Pipeline | 346 | 356 | +10 |
| Formatters | 12 | 24 | +12 |
| Tools | 45 | 55 | +10 |
| Slack | 38 | 46 | +8 |
| **Total** | **441** | **481** | **+40** |

---

## DoD da Sprint 19 (Completa)

- [ ] E01 - Schema migrado e validado
- [ ] E02 - Extracao LLM atualizada
- [ ] E03 - Pipeline propagando campos
- [ ] E04 - Julia oferecendo vagas corretamente
- [ ] E05 - Slack exibindo valores corretamente
- [ ] E06 - Testes e documentacao completos
- [ ] Zero erros em producao apos deploy
- [ ] Metricas de sucesso atingidas:
  - [ ] Vagas com valor perdido < 5% (antes: 33%)
  - [ ] Erros de parsing valor = 0 (antes: 1+)
  - [ ] 3 tipos de valor suportados
  - [ ] 3 templates Julia para valor
