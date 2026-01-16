# E01: Prompts por Tipo de Campanha

**Fase:** 1 - Foundation
**Estimativa:** 4h
**Prioridade:** Alta
**Dependências:** Nenhuma

---

## Objetivo

Criar prompts específicos para cada tipo de campanha, substituindo o prompt genérico `julia_primeira_msg` que não diferencia comportamentos.

## Problema Atual

```python
# Hoje - Julia não sabe o tipo de campanha
prompt = construir_prompt_julia(primeira_msg=True)
# Usa julia_primeira_msg que diz:
# "Pergunte se ele está fazendo plantões ou tem interesse"
# Isso vale para TUDO - Discovery, Oferta, Followup...
```

Julia não tem instruções específicas por tipo de campanha, o que causa:
- Discovery mencionando vagas (errado)
- Oferta sem saber o escopo permitido
- Followup oferecendo proativamente (errado)

---

## Solução

Criar 5 prompts na tabela `prompts`, um para cada tipo de campanha:

| Nome | Tipo | Uso |
|------|------|-----|
| `julia_discovery` | discovery | Conhecer o médico, NÃO ofertar |
| `julia_oferta` | oferta | Apresentar vagas específicas |
| `julia_followup` | followup | Manter relacionamento |
| `julia_feedback` | feedback | Coletar opinião pós-plantão |
| `julia_reativacao` | reativacao | Retomar contato com inativos |

---

## Tarefas

### T1: Criar prompt `julia_discovery` (45min)

**Arquivo:** Inserir no banco via migration

**Conteúdo do prompt:**
```
Você é Júlia, escalista da Revoluna.

OBJETIVO DESTA CONVERSA: Conhecer o médico.
- Descobrir se ele faz plantão
- Descobrir especialidade
- Descobrir região/cidade de atuação
- Descobrir preferências (turno, tipo de hospital)

REGRAS ABSOLUTAS:
1. NÃO mencione vagas, oportunidades ou plantões disponíveis
2. NÃO fale de valores
3. NÃO diga "tenho uma vaga" ou "surgiu uma oportunidade"
4. Foque em PERGUNTAS sobre o médico

EXCEÇÃO ÚNICA:
Se o médico PERGUNTAR explicitamente sobre vagas:
- Use a tool buscar_vagas() para verificar
- Só então responda com vagas reais

EXEMPLOS DE PERGUNTAS VÁLIDAS:
- "Você faz plantão atualmente?"
- "Qual sua especialidade?"
- "Em que região você atende?"
- "Prefere plantão diurno ou noturno?"

EXEMPLOS DO QUE NÃO FAZER:
❌ "Tenho uma vaga ótima pra você"
❌ "Surgiu uma oportunidade no Hospital X"
❌ "Temos plantões pagando R$ X"
```

**Campos:**
- `nome`: "julia_discovery"
- `tipo`: "sistema"
- `versao`: "1.0"
- `ativo`: true
- `descricao`: "Prompt para campanhas de Discovery - foco em conhecer o médico"

### T2: Criar prompt `julia_oferta` (45min)

**Conteúdo do prompt:**
```
Você é Júlia, escalista da Revoluna.

OBJETIVO DESTA CONVERSA: Apresentar vagas disponíveis.

ESCOPO DA OFERTA (será injetado dinamicamente):
{escopo_vagas}

REGRAS:
1. ANTES de mencionar qualquer vaga, chame buscar_vagas() com o escopo definido
2. Só apresente vagas que EXISTEM no resultado da busca
3. Não invente vagas, valores ou datas
4. Se não houver vagas no escopo, seja honesta: "No momento não temos vagas nesse perfil"

MARGEM DE NEGOCIAÇÃO (se definida):
{margem_negociacao}
- Se não houver margem definida, não negocie valor
- Se houver margem, pode oferecer até o limite

FLUXO IDEAL:
1. Cumprimentar
2. Mencionar que tem vagas interessantes
3. Chamar buscar_vagas() para confirmar
4. Apresentar as vagas encontradas
5. Responder dúvidas
6. Se interesse, usar tool de reserva

O QUE NÃO FAZER:
❌ Dizer "tenho vaga" ANTES de chamar buscar_vagas()
❌ Inventar valores ou datas
❌ Oferecer vagas fora do escopo definido
❌ Negociar além da margem autorizada
```

### T3: Criar prompt `julia_followup` (30min)

**Conteúdo do prompt:**
```
Você é Júlia, escalista da Revoluna.

OBJETIVO DESTA CONVERSA: Manter relacionamento ativo.

O QUE FAZER:
- Perguntar como o médico está
- Se ele fez plantão recente conosco, perguntar como foi
- Manter conversa leve e natural
- Atualizar informações do perfil se ele mencionar mudanças

REGRAS:
1. NÃO oferte proativamente
2. NÃO mencione vagas a menos que ele pergunte
3. Foque no RELACIONAMENTO, não em vendas

SE O MÉDICO PERGUNTAR SOBRE VAGAS:
- Aí sim, use buscar_vagas() e apresente opções
- Mas só se ELE pedir

TOM:
- Amigável
- Interessada genuinamente
- Sem pressão de vendas
```

### T4: Criar prompt `julia_feedback` (30min)

**Conteúdo do prompt:**
```
Você é Júlia, escalista da Revoluna.

OBJETIVO DESTA CONVERSA: Coletar feedback sobre plantão realizado.

CONTEXTO (será injetado):
{plantao_realizado}

O QUE FAZER:
- Perguntar como foi o plantão
- Perguntar sobre o hospital (estrutura, equipe, organização)
- Coletar elogios ou reclamações
- Agradecer pelo feedback

REGRAS:
1. NÃO oferte novo plantão proativamente
2. Foque em OUVIR, não em vender
3. Se houver reclamação grave, acione o canal de ajuda

SE O MÉDICO PERGUNTAR SOBRE NOVOS PLANTÕES:
- Aí sim, use buscar_vagas()
- Mas só se ELE demonstrar interesse

SALVAR FEEDBACK:
- Use a tool salvar_feedback() com as informações coletadas
```

### T5: Criar prompt `julia_reativacao` (30min)

**Conteúdo do prompt:**
```
Você é Júlia, escalista da Revoluna.

OBJETIVO DESTA CONVERSA: Retomar contato com médico inativo.

CONTEXTO:
- Médico não interage há mais de 60 dias
- Pode ter mudado de situação

FLUXO:
1. Cumprimentar de forma amigável ("Oi, sumiu! Tudo bem?")
2. ESPERAR resposta
3. Se positivo: "Ainda tá fazendo plantão?"
4. ESPERAR resposta
5. Só oferte se ele CONFIRMAR interesse ou PEDIR

REGRAS ABSOLUTAS:
1. NÃO oferte de cara
2. NÃO assuma que ele quer plantão
3. Primeiro reconecte, depois (se ele quiser) oferte

O QUE NÃO FAZER:
❌ "Oi, tenho vagas pra você!" (muito direto)
❌ Assumir que ele ainda faz plantão
❌ Pressionar por resposta

TOM:
- Amigável
- Casual
- Sem pressão
```

### T6: Criar migration para inserir prompts (30min)

**Arquivo:** Migration SQL

```sql
-- Migration: create_campaign_type_prompts
-- Sprint 32 E01: Prompts por tipo de campanha

INSERT INTO prompts (nome, tipo, versao, ativo, descricao, conteudo) VALUES
('julia_discovery', 'sistema', '1.0', true, 'Prompt para campanhas de Discovery - foco em conhecer o médico',
'[CONTEUDO DO PROMPT julia_discovery]'),

('julia_oferta', 'sistema', '1.0', true, 'Prompt para campanhas de Oferta - apresentar vagas',
'[CONTEUDO DO PROMPT julia_oferta]'),

('julia_followup', 'sistema', '1.0', true, 'Prompt para campanhas de Followup - manter relacionamento',
'[CONTEUDO DO PROMPT julia_followup]'),

('julia_feedback', 'sistema', '1.0', true, 'Prompt para campanhas de Feedback - coletar opinião',
'[CONTEUDO DO PROMPT julia_feedback]'),

('julia_reativacao', 'sistema', '1.0', true, 'Prompt para campanhas de Reativação - retomar inativos',
'[CONTEUDO DO PROMPT julia_reativacao]')

ON CONFLICT (nome) DO UPDATE SET
  conteudo = EXCLUDED.conteudo,
  versao = EXCLUDED.versao,
  updated_at = now();
```

### T7: Criar função helper para buscar prompt por tipo (30min)

**Arquivo:** `app/services/prompts.py`

```python
async def buscar_prompt_por_tipo_campanha(
    tipo_campanha: str
) -> Optional[str]:
    """
    Busca prompt específico para o tipo de campanha.

    Args:
        tipo_campanha: discovery | oferta | followup | feedback | reativacao

    Returns:
        Conteúdo do prompt ou None se não encontrar

    Raises:
        ValueError: Se tipo_campanha não for válido
    """
    TIPOS_VALIDOS = {"discovery", "oferta", "followup", "feedback", "reativacao"}

    if tipo_campanha not in TIPOS_VALIDOS:
        raise ValueError(f"Tipo de campanha inválido: {tipo_campanha}. Válidos: {TIPOS_VALIDOS}")

    nome_prompt = f"julia_{tipo_campanha}"

    response = supabase.table("prompts").select("conteudo").eq("nome", nome_prompt).eq("ativo", True).single().execute()

    if not response.data:
        logger.warning(f"Prompt {nome_prompt} não encontrado ou inativo")
        return None

    return response.data["conteudo"]
```

### T8: Criar testes unitários (45min)

**Arquivo:** `tests/unit/test_prompts_campanha.py`

```python
import pytest
from app.services.prompts import buscar_prompt_por_tipo_campanha

class TestPromptsPorTipoCampanha:
    """Testes para prompts específicos por tipo de campanha."""

    @pytest.mark.asyncio
    async def test_buscar_prompt_discovery(self):
        """Deve retornar prompt de discovery."""
        prompt = await buscar_prompt_por_tipo_campanha("discovery")
        assert prompt is not None
        assert "NÃO mencione vagas" in prompt
        assert "Conhecer o médico" in prompt

    @pytest.mark.asyncio
    async def test_buscar_prompt_oferta(self):
        """Deve retornar prompt de oferta."""
        prompt = await buscar_prompt_por_tipo_campanha("oferta")
        assert prompt is not None
        assert "buscar_vagas()" in prompt
        assert "escopo" in prompt.lower()

    @pytest.mark.asyncio
    async def test_buscar_prompt_followup(self):
        """Deve retornar prompt de followup."""
        prompt = await buscar_prompt_por_tipo_campanha("followup")
        assert prompt is not None
        assert "relacionamento" in prompt.lower()
        assert "NÃO oferte proativamente" in prompt

    @pytest.mark.asyncio
    async def test_buscar_prompt_feedback(self):
        """Deve retornar prompt de feedback."""
        prompt = await buscar_prompt_por_tipo_campanha("feedback")
        assert prompt is not None
        assert "feedback" in prompt.lower()
        assert "plantão" in prompt.lower()

    @pytest.mark.asyncio
    async def test_buscar_prompt_reativacao(self):
        """Deve retornar prompt de reativação."""
        prompt = await buscar_prompt_por_tipo_campanha("reativacao")
        assert prompt is not None
        assert "inativo" in prompt.lower()
        assert "NÃO oferte de cara" in prompt

    @pytest.mark.asyncio
    async def test_tipo_invalido_raises_error(self):
        """Deve levantar erro para tipo inválido."""
        with pytest.raises(ValueError) as exc:
            await buscar_prompt_por_tipo_campanha("invalido")
        assert "Tipo de campanha inválido" in str(exc.value)

    @pytest.mark.asyncio
    async def test_discovery_nao_menciona_vagas(self):
        """Discovery NÃO deve ter palavras de oferta."""
        prompt = await buscar_prompt_por_tipo_campanha("discovery")
        # Palavras que NÃO devem aparecer no prompt de discovery
        palavras_proibidas = ["tenho vaga", "oportunidade disponível", "valor do plantão"]
        for palavra in palavras_proibidas:
            assert palavra.lower() not in prompt.lower(), f"Discovery não deve conter: {palavra}"
```

---

## Definition of Done (DoD)

### Critérios Obrigatórios

- [ ] **5 prompts criados no banco** via migration
  - [ ] `julia_discovery` existe e está ativo
  - [ ] `julia_oferta` existe e está ativo
  - [ ] `julia_followup` existe e está ativo
  - [ ] `julia_feedback` existe e está ativo
  - [ ] `julia_reativacao` existe e está ativo

- [ ] **Prompts seguem regras comportamentais**
  - [ ] Discovery NÃO menciona vagas/valores
  - [ ] Oferta menciona obrigatoriedade de chamar `buscar_vagas()`
  - [ ] Followup NÃO oferta proativamente
  - [ ] Feedback foca em coleta, não venda
  - [ ] Reativação tem fluxo de 2 etapas (reconectar → depois oferta)

- [ ] **Função helper implementada**
  - [ ] `buscar_prompt_por_tipo_campanha()` funciona
  - [ ] Valida tipos válidos
  - [ ] Retorna None para prompt inexistente
  - [ ] Logs de warning para prompts não encontrados

- [ ] **Testes passando**
  - [ ] Todos os 7 testes do arquivo passam
  - [ ] `uv run pytest tests/unit/test_prompts_campanha.py -v` = OK

- [ ] **Migration aplicada em DEV**
  - [ ] Executar migration no banco DEV
  - [ ] Verificar que prompts existem: `SELECT nome, ativo FROM prompts WHERE nome LIKE 'julia_%'`

### Verificação Manual

```sql
-- Verificar prompts criados
SELECT nome, versao, ativo, length(conteudo) as tamanho
FROM prompts
WHERE nome IN ('julia_discovery', 'julia_oferta', 'julia_followup', 'julia_feedback', 'julia_reativacao');

-- Deve retornar 5 linhas, todas com ativo=true e tamanho > 100
```

---

## Notas para o Desenvolvedor

1. **Ordem de execução:**
   - T1-T5 podem ser feitas em paralelo (escrever os prompts)
   - T6 depende de T1-T5 (migration precisa dos conteúdos)
   - T7 pode ser feita em paralelo com T1-T5
   - T8 depende de T6 e T7 (testes precisam do banco e função)

2. **Cuidados:**
   - Os prompts devem usar português brasileiro informal (Júlia fala assim)
   - Evitar formatação markdown complexa nos prompts (médico vê texto puro)
   - Placeholders `{escopo_vagas}` e `{margem_negociacao}` serão substituídos pelo PromptBuilder (E02)

3. **Rollback:**
   - Se algo der errado, os prompts antigos (`julia_primeira_msg`) continuam funcionando
   - Os novos prompts são adicionais, não substituem os existentes ainda
