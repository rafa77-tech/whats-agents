# Epic 2: Feedback do Gestor

## Objetivo

> **Permitir que gestor avalie e melhore a Júlia continuamente.**

---

## Stories

---

# S4.E2.1 - Interface de avaliação de conversas

## Objetivo

> **Criar interface simples para gestor avaliar conversas.**

**Resultado esperado:** Gestor acessa lista de conversas e avalia cada uma.

## Tarefas

### 1. Criar endpoint de listagem

```python
# app/routes/admin.py

from fastapi import APIRouter, Query
from typing import Optional

router = APIRouter(prefix="/admin", tags=["admin"])

@router.get("/conversas")
async def listar_conversas(
    status: Optional[str] = None,
    avaliada: Optional[bool] = None,
    limite: int = Query(default=20, le=100),
    offset: int = 0
):
    """
    Lista conversas para avaliação do gestor.

    Filtros:
    - status: ativa, encerrada
    - avaliada: true/false (tem avaliação do gestor)
    """
    query = (
        supabase.table("conversations")
        .select("""
            *,
            clientes(primeiro_nome, telefone, especialidade_id),
            metricas_conversa(*),
            avaliacoes_qualidade(score_geral, avaliador)
        """)
        .order("created_at", desc=True)
        .range(offset, offset + limite - 1)
    )

    if status:
        query = query.eq("status", status)

    response = query.execute()
    conversas = response.data

    # Filtrar por avaliação se necessário
    if avaliada is not None:
        conversas = [
            c for c in conversas
            if any(a["avaliador"] == "gestor" for a in c.get("avaliacoes_qualidade", []))
            == avaliada
        ]

    return {
        "conversas": conversas,
        "total": len(conversas),
        "offset": offset,
        "limite": limite
    }


@router.get("/conversas/{conversa_id}")
async def obter_conversa_detalhada(conversa_id: str):
    """Retorna conversa com todas as interações."""
    conversa = (
        supabase.table("conversations")
        .select("*, clientes(*)")
        .eq("id", conversa_id)
        .single()
        .execute()
    ).data

    interacoes = (
        supabase.table("interacoes")
        .select("*")
        .eq("conversa_id", conversa_id)
        .order("created_at")
        .execute()
    ).data

    avaliacoes = (
        supabase.table("avaliacoes_qualidade")
        .select("*")
        .eq("conversa_id", conversa_id)
        .execute()
    ).data

    return {
        "conversa": conversa,
        "interacoes": interacoes,
        "avaliacoes": avaliacoes
    }
```

### 2. Criar página de avaliação

```html
<!-- static/avaliar.html -->
<!DOCTYPE html>
<html>
<head>
    <title>Avaliar Conversas - Júlia</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; max-width: 1200px; }
        .conversa-item { border: 1px solid #ddd; padding: 15px; margin: 10px 0; border-radius: 8px; cursor: pointer; }
        .conversa-item:hover { background: #f5f5f5; }
        .mensagem { padding: 10px; margin: 5px 0; border-radius: 8px; }
        .mensagem.medico { background: #e3f2fd; text-align: left; }
        .mensagem.julia { background: #e8f5e9; text-align: right; }
        .avaliacao-form { background: #fff3e0; padding: 20px; border-radius: 8px; margin-top: 20px; }
        .score-input { display: flex; gap: 20px; margin: 10px 0; }
        .score-input label { min-width: 120px; }
        .score-input input { width: 60px; }
        .modal { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); }
        .modal-content { background: white; margin: 5% auto; padding: 20px; width: 80%; max-height: 80%; overflow-y: auto; border-radius: 8px; }
        .tag { display: inline-block; background: #e0e0e0; padding: 2px 8px; border-radius: 4px; margin: 2px; font-size: 12px; }
    </style>
</head>
<body>
    <h1>📝 Avaliar Conversas</h1>

    <div>
        <label>Filtrar:</label>
        <select id="filtro-avaliada" onchange="carregarConversas()">
            <option value="">Todas</option>
            <option value="false">Não avaliadas</option>
            <option value="true">Avaliadas</option>
        </select>
    </div>

    <div id="lista-conversas"></div>

    <!-- Modal de avaliação -->
    <div id="modal" class="modal">
        <div class="modal-content">
            <span onclick="fecharModal()" style="float:right;cursor:pointer;font-size:24px">&times;</span>
            <h2>Conversa com <span id="nome-medico"></span></h2>
            <div id="mensagens"></div>

            <div class="avaliacao-form">
                <h3>Avaliação</h3>
                <div class="score-input">
                    <label>Naturalidade (1-10):</label>
                    <input type="number" id="score-naturalidade" min="1" max="10">
                </div>
                <div class="score-input">
                    <label>Persona (1-10):</label>
                    <input type="number" id="score-persona" min="1" max="10">
                </div>
                <div class="score-input">
                    <label>Objetivo (1-10):</label>
                    <input type="number" id="score-objetivo" min="1" max="10">
                </div>
                <div class="score-input">
                    <label>Satisfação (1-10):</label>
                    <input type="number" id="score-satisfacao" min="1" max="10">
                </div>

                <div style="margin-top: 15px;">
                    <label>Notas:</label>
                    <textarea id="notas" rows="3" style="width:100%"></textarea>
                </div>

                <div style="margin-top: 15px;">
                    <label>Tags:</label>
                    <div id="tags"></div>
                    <input type="text" id="nova-tag" placeholder="Adicionar tag..." onkeypress="adicionarTag(event)">
                </div>

                <button onclick="salvarAvaliacao()" style="margin-top:20px;padding:10px 20px">Salvar Avaliação</button>
            </div>
        </div>
    </div>

    <script>
        let conversaAtual = null;
        let tagsAtuais = [];

        async function carregarConversas() {
            const avaliada = document.getElementById('filtro-avaliada').value;
            const url = `/admin/conversas?limite=50${avaliada ? `&avaliada=${avaliada}` : ''}`;
            const resp = await fetch(url);
            const data = await resp.json();

            document.getElementById('lista-conversas').innerHTML = data.conversas.map(c => `
                <div class="conversa-item" onclick="abrirConversa('${c.id}')">
                    <strong>${c.clientes?.primeiro_nome || 'Médico'}</strong>
                    <span class="tag">${c.status}</span>
                    ${c.avaliacoes_qualidade?.some(a => a.avaliador === 'gestor') ? '<span class="tag" style="background:#c8e6c9">✓ Avaliada</span>' : ''}
                    <br>
                    <small>Score auto: ${c.avaliacoes_qualidade?.[0]?.score_geral || '-'}/10</small>
                    <small> | ${new Date(c.created_at).toLocaleDateString()}</small>
                </div>
            `).join('');
        }

        async function abrirConversa(id) {
            const resp = await fetch(`/admin/conversas/${id}`);
            const data = await resp.json();
            conversaAtual = data;

            document.getElementById('nome-medico').textContent = data.conversa.clientes?.primeiro_nome || 'Médico';
            document.getElementById('mensagens').innerHTML = data.interacoes.map(i => `
                <div class="mensagem ${i.direcao === 'entrada' ? 'medico' : 'julia'}">
                    <small>${i.direcao === 'entrada' ? '👨‍⚕️' : '👩‍💼'}</small>
                    ${i.conteudo}
                    <br><small style="color:#999">${new Date(i.created_at).toLocaleTimeString()}</small>
                </div>
            `).join('');

            document.getElementById('modal').style.display = 'block';
        }

        function fecharModal() {
            document.getElementById('modal').style.display = 'none';
            conversaAtual = null;
        }

        async function salvarAvaliacao() {
            const avaliacao = {
                conversa_id: conversaAtual.conversa.id,
                naturalidade: parseInt(document.getElementById('score-naturalidade').value),
                persona: parseInt(document.getElementById('score-persona').value),
                objetivo: parseInt(document.getElementById('score-objetivo').value),
                satisfacao: parseInt(document.getElementById('score-satisfacao').value),
                notas: document.getElementById('notas').value,
                tags: tagsAtuais
            };

            await fetch('/admin/avaliacoes', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(avaliacao)
            });

            alert('Avaliação salva!');
            fecharModal();
            carregarConversas();
        }

        carregarConversas();
    </script>
</body>
</html>
```

## DoD

- [ ] Endpoint de listagem funciona
- [ ] Endpoint de detalhes funciona
- [ ] Página de avaliação acessível
- [ ] Filtro por status de avaliação
- [ ] Modal mostra conversa completa

---

# S4.E2.2 - Sistema de notas e tags

## Objetivo

> **Permitir gestor categorizar conversas com tags e notas.**

**Resultado esperado:** Tags e notas são salvas e podem ser filtradas.

## Tarefas

### 1. Criar endpoint de avaliação

```python
# app/routes/admin.py (adicionar)

from pydantic import BaseModel
from typing import List, Optional

class AvaliacaoGestor(BaseModel):
    conversa_id: str
    naturalidade: int
    persona: int
    objetivo: int
    satisfacao: int
    notas: Optional[str] = None
    tags: Optional[List[str]] = []

@router.post("/avaliacoes")
async def criar_avaliacao_gestor(avaliacao: AvaliacaoGestor):
    """Salva avaliação do gestor."""
    score_geral = (
        avaliacao.naturalidade +
        avaliacao.persona +
        avaliacao.objetivo +
        avaliacao.satisfacao
    ) / 4

    return (
        supabase.table("avaliacoes_qualidade")
        .insert({
            "conversa_id": avaliacao.conversa_id,
            "naturalidade": avaliacao.naturalidade,
            "persona": avaliacao.persona,
            "objetivo": avaliacao.objetivo,
            "satisfacao": avaliacao.satisfacao,
            "score_geral": round(score_geral),
            "notas": avaliacao.notas,
            "avaliador": "gestor",
            "tags": avaliacao.tags
        })
        .execute()
    ).data[0]
```

### 2. Adicionar coluna de tags

```sql
-- migration: adicionar_tags_avaliacoes.sql

ALTER TABLE avaliacoes_qualidade
ADD COLUMN tags TEXT[] DEFAULT '{}';

CREATE INDEX idx_avaliacoes_tags ON avaliacoes_qualidade USING GIN(tags);
```

### 3. Tags pré-definidas

```python
# app/constants/tags.py

TAGS_PREDEFINIDAS = {
    "qualidade": [
        "resposta_excelente",
        "resposta_boa",
        "resposta_ruim",
        "perdeu_persona",
        "muito_formal",
        "muito_informal",
    ],
    "situacao": [
        "vaga_reservada",
        "sem_interesse",
        "indeciso",
        "precisa_followup",
        "optout",
    ],
    "problema": [
        "erro_informacao",
        "resposta_inadequada",
        "deveria_handoff",
        "handoff_desnecessario",
        "tempo_lento",
    ],
    "destaque": [
        "usar_como_exemplo",
        "precisa_ajuste_prompt",
        "bug_detectado",
    ],
}
```

### 4. Endpoint de busca por tag

```python
@router.get("/conversas/por-tag/{tag}")
async def buscar_por_tag(tag: str, limite: int = 50):
    """Busca conversas que têm determinada tag."""
    avaliacoes = (
        supabase.table("avaliacoes_qualidade")
        .select("conversa_id")
        .contains("tags", [tag])
        .execute()
    ).data

    conversa_ids = [a["conversa_id"] for a in avaliacoes]

    conversas = (
        supabase.table("conversations")
        .select("*, clientes(primeiro_nome)")
        .in_("id", conversa_ids)
        .limit(limite)
        .execute()
    ).data

    return {"conversas": conversas, "total": len(conversas)}
```

## DoD

- [ ] Endpoint de avaliação aceita tags
- [ ] Tags salvas no banco
- [ ] Tags pré-definidas disponíveis
- [ ] Busca por tag funciona
- [ ] Interface permite adicionar tags

---

# S4.E2.3 - Sugestões de melhoria do prompt

## Objetivo

> **Coletar sugestões específicas para melhorar o prompt.**

**Resultado esperado:** Gestor pode sugerir melhorias que são agregadas.

## Tarefas

### 1. Criar tabela de sugestões

```sql
-- migration: criar_tabela_sugestoes_prompt.sql

CREATE TABLE sugestoes_prompt (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversa_id UUID REFERENCES conversations(id),
    avaliacao_id UUID REFERENCES avaliacoes_qualidade(id),

    tipo VARCHAR(50), -- 'adicionar_regra', 'remover_regra', 'ajustar_tom', 'exemplo'
    descricao TEXT NOT NULL,
    exemplo_ruim TEXT,  -- O que Júlia disse
    exemplo_bom TEXT,   -- O que deveria ter dito

    status VARCHAR(20) DEFAULT 'pendente', -- 'pendente', 'implementada', 'rejeitada'
    implementada_em TIMESTAMPTZ,

    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### 2. Criar endpoint de sugestões

```python
# app/routes/admin.py (adicionar)

class SugestaoPrompt(BaseModel):
    conversa_id: str
    avaliacao_id: Optional[str] = None
    tipo: str  # 'adicionar_regra', 'remover_regra', 'ajustar_tom', 'exemplo'
    descricao: str
    exemplo_ruim: Optional[str] = None
    exemplo_bom: Optional[str] = None

@router.post("/sugestoes")
async def criar_sugestao(sugestao: SugestaoPrompt):
    """Cria sugestão de melhoria do prompt."""
    return (
        supabase.table("sugestoes_prompt")
        .insert(sugestao.dict())
        .execute()
    ).data[0]


@router.get("/sugestoes")
async def listar_sugestoes(status: str = "pendente"):
    """Lista sugestões de melhoria."""
    return (
        supabase.table("sugestoes_prompt")
        .select("*, conversations(clientes(primeiro_nome))")
        .eq("status", status)
        .order("created_at", desc=True)
        .execute()
    ).data


@router.patch("/sugestoes/{sugestao_id}")
async def atualizar_sugestao(sugestao_id: str, status: str):
    """Atualiza status da sugestão."""
    atualizacao = {"status": status}
    if status == "implementada":
        atualizacao["implementada_em"] = datetime.utcnow().isoformat()

    return (
        supabase.table("sugestoes_prompt")
        .update(atualizacao)
        .eq("id", sugestao_id)
        .execute()
    ).data[0]
```

### 3. Agregar sugestões similares

```python
async def agregar_sugestoes() -> dict:
    """
    Agrupa sugestões similares para facilitar análise.

    Retorna sugestões agrupadas por tipo e frequência.
    """
    sugestoes = (
        supabase.table("sugestoes_prompt")
        .select("*")
        .eq("status", "pendente")
        .execute()
    ).data

    # Agrupar por tipo
    por_tipo = {}
    for s in sugestoes:
        tipo = s["tipo"]
        if tipo not in por_tipo:
            por_tipo[tipo] = []
        por_tipo[tipo].append(s)

    # Ordenar por frequência
    resumo = {}
    for tipo, lista in por_tipo.items():
        resumo[tipo] = {
            "total": len(lista),
            "exemplos": lista[:5]  # 5 exemplos mais recentes
        }

    return resumo
```

## DoD

- [ ] Tabela de sugestões criada
- [ ] Endpoint de criação funciona
- [ ] Listagem com filtro por status
- [ ] Atualização de status funciona
- [ ] Agregação de sugestões similares

---

# S4.E2.4 - Integrar feedback no treinamento

## Objetivo

> **Usar feedback do gestor para melhorar prompt automaticamente.**

**Resultado esperado:** Exemplos bons/ruins são adicionados ao prompt.

## Tarefas

### 1. Extrair exemplos de conversas avaliadas

```python
# app/services/feedback.py

async def extrair_exemplos_treinamento() -> dict:
    """
    Extrai exemplos bons e ruins das avaliações do gestor.

    Returns:
        dict com exemplos categorizados
    """
    # Buscar avaliações do gestor com score alto e baixo
    avaliacoes = (
        supabase.table("avaliacoes_qualidade")
        .select("*, conversations(id)")
        .eq("avaliador", "gestor")
        .execute()
    ).data

    exemplos_bons = []
    exemplos_ruins = []

    for av in avaliacoes:
        if av["score_geral"] >= 8:
            # Buscar interações desta conversa
            interacoes = await obter_interacoes(av["conversa_id"])
            exemplos_bons.append({
                "conversa_id": av["conversa_id"],
                "score": av["score_geral"],
                "interacoes": interacoes,
                "porque_bom": av.get("notas")
            })
        elif av["score_geral"] <= 4:
            interacoes = await obter_interacoes(av["conversa_id"])
            exemplos_ruins.append({
                "conversa_id": av["conversa_id"],
                "score": av["score_geral"],
                "interacoes": interacoes,
                "porque_ruim": av.get("notas")
            })

    return {
        "bons": exemplos_bons[:10],  # Top 10
        "ruins": exemplos_ruins[:10]
    }
```

### 2. Gerar seção de exemplos para prompt

```python
async def gerar_exemplos_prompt() -> str:
    """
    Gera seção de exemplos para adicionar ao prompt.
    """
    exemplos = await extrair_exemplos_treinamento()

    texto = "## Exemplos de Conversas\n\n"

    # Exemplos bons
    texto += "### ✅ Respostas que funcionaram bem:\n\n"
    for ex in exemplos["bons"][:5]:
        # Pegar última troca (pergunta + resposta)
        msgs = ex["interacoes"][-4:]  # Últimas 2 trocas
        texto += "```\n"
        for m in msgs:
            quem = "Médico" if m["direcao"] == "entrada" else "Júlia"
            texto += f"{quem}: {m['conteudo']}\n"
        texto += "```\n"
        if ex["porque_bom"]:
            texto += f"_Por que funciona: {ex['porque_bom']}_\n\n"

    # Exemplos ruins
    texto += "### ❌ Evitar respostas assim:\n\n"
    for ex in exemplos["ruins"][:5]:
        msgs = ex["interacoes"][-4:]
        texto += "```\n"
        for m in msgs:
            quem = "Médico" if m["direcao"] == "entrada" else "Júlia"
            texto += f"{quem}: {m['conteudo']}\n"
        texto += "```\n"
        if ex["porque_ruim"]:
            texto += f"_Problema: {ex['porque_ruim']}_\n\n"

    return texto
```

### 3. Atualizar prompt automaticamente

```python
async def atualizar_prompt_com_feedback():
    """
    Atualiza arquivo de prompt com novos exemplos.

    Executar semanalmente ou após N novas avaliações.
    """
    exemplos_texto = await gerar_exemplos_prompt()

    # Ler prompt atual
    with open("app/prompts/julia.py", "r") as f:
        prompt_atual = f.read()

    # Substituir seção de exemplos
    # (Assumindo que há marcadores ## Exemplos de Conversas ... ## Fim Exemplos)
    import re
    novo_prompt = re.sub(
        r"## Exemplos de Conversas.*?## Fim Exemplos",
        f"{exemplos_texto}\n## Fim Exemplos",
        prompt_atual,
        flags=re.DOTALL
    )

    # Salvar
    with open("app/prompts/julia.py", "w") as f:
        f.write(novo_prompt)

    logger.info("Prompt atualizado com novos exemplos do feedback")
```

## DoD

- [ ] Extração de exemplos bons/ruins funciona
- [ ] Gerador de seção de exemplos funciona
- [ ] Prompt pode ser atualizado automaticamente
- [ ] Exemplos incluem contexto (por que bom/ruim)
- [ ] Processo não quebra prompt existente
