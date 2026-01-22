# Migracao de Codigo: Campanhas

> Guia rapido para atualizar codigo legado
> Sprint 35 - Debt Cleanup

## Tabela de Substituicao

### Colunas

| Codigo Antigo | Codigo Novo |
|---------------|-------------|
| `campanha["nome"]` | `campanha["nome_template"]` |
| `campanha["tipo"]` | `campanha["tipo_campanha"]` |
| `campanha["mensagem_template"]` | Ver "Geracao de Mensagem" abaixo |
| `campanha.get("config", {})` | `campanha.get("audience_filters", {})` |
| `config["filtro_especialidades"]` | `audience_filters["especialidades"]` |
| `config["filtro_regioes"]` | `audience_filters["regioes"]` |
| `config["filtro_tags"]` | **Removido** - nao usar |
| `campanha["envios_criados"]` | `campanha["enviados"]` |
| `campanha["finalizada_em"]` | `campanha["concluida_em"]` |

### Tabelas

| Codigo Antigo | Codigo Novo |
|---------------|-------------|
| `supabase.table("envios_campanha").insert(...)` | `fila_service.enfileirar(...)` |
| `supabase.table("envios_campanha").select(...)` | Query em `campaign_sends` view |
| Metricas manuais (COUNT, etc) | Query em `campaign_metrics` view |

---

## Geracao de Mensagem

### Antigo (NAO FUNCIONA)

```python
# Isso vai dar KeyError porque mensagem_template nao existe
mensagem = campanha["mensagem_template"].format(nome=nome)
```

### Novo - Para Discovery

```python
from app.services.abertura import obter_abertura_texto

# Gera mensagem dinamica com variedade
mensagem = await obter_abertura_texto(
    cliente_id=cliente_id,
    nome=nome
)
```

### Novo - Para Outros Tipos (oferta, followup, etc)

```python
# Usa o campo corpo como template
corpo = campanha.get("corpo", "")

if "{nome}" in corpo or "{especialidade}" in corpo:
    mensagem = corpo.format(
        nome=nome,
        especialidade=especialidade
    )
else:
    mensagem = corpo
```

### Codigo Completo Recomendado

```python
from app.services.abertura import obter_abertura_texto

tipo_campanha = campanha.get("tipo_campanha", "campanha")

if tipo_campanha == "discovery":
    # Discovery: aberturas dinamicas
    mensagem = await obter_abertura_texto(cliente_id, nome)
else:
    # Outros: usa corpo como template
    corpo = campanha.get("corpo", "")
    if "{nome}" in corpo or "{especialidade}" in corpo:
        mensagem = corpo.format(nome=nome, especialidade=especialidade)
    else:
        mensagem = corpo
```

---

## Enfileirar Envios

### Antigo (NAO FUNCIONA)

```python
# Tabela envios_campanha foi removida
supabase.table("envios_campanha").insert({
    "campanha_id": campanha_id,
    "cliente_id": cliente_id,
    "status": "pendente"
}).execute()
```

### Novo

```python
from app.services.fila import fila_service

await fila_service.enfileirar(
    cliente_id=cliente_id,
    conteudo=mensagem,
    tipo=tipo_campanha,  # "discovery", "oferta", etc
    prioridade=3,  # Campanhas tem prioridade baixa
    metadata={"campanha_id": str(campanha_id)}
)
```

---

## Consultar Envios

### Antigo

```python
envios = supabase.table("envios_campanha").select("*").eq("campanha_id", 16).execute()
```

### Novo - Via View

```python
envios = supabase.table("campaign_sends").select("*").eq("campaign_id", 16).execute()
```

### Novo - Via Repository (Recomendado)

```python
from app.services.campaign_sends import campaign_sends_repo

envios = await campaign_sends_repo.listar_por_campanha(campanha_id=16)
```

---

## Metricas

### Antigo (manual)

```python
total = supabase.table("envios_campanha").select("id", count="exact").eq("campanha_id", 16).execute().count
enviados = supabase.table("envios_campanha").select("id", count="exact").eq("campanha_id", 16).eq("status", "enviado").execute().count
```

### Novo - Via View

```python
metricas = supabase.table("campaign_metrics").select("*").eq("campaign_id", 16).single().execute()

# Campos disponiveis:
# - total_sends
# - delivered
# - bypassed
# - blocked
# - failed
# - pending
# - delivery_rate
# - block_rate
```

---

## Imports Necessarios

```python
# Adicionar
from app.services.abertura import obter_abertura_texto
from app.services.fila import fila_service

# Opcional - para queries
from app.services.campaign_sends import campaign_sends_repo
```

---

## Checklist de Migracao

Para cada arquivo que usa campanhas:

- [ ] Substituir `config` por `audience_filters`
- [ ] Substituir `filtro_especialidades` por `especialidades`
- [ ] Substituir `filtro_regioes` por `regioes`
- [ ] Substituir `tipo` por `tipo_campanha`
- [ ] Substituir `envios_criados` por `enviados`
- [ ] Remover referencias a `mensagem_template`
- [ ] Usar geracao dinamica para discovery
- [ ] Usar `corpo` como template para outros tipos
- [ ] Remover INSERT em `envios_campanha`
- [ ] Usar `fila_service.enfileirar()` para enfileirar
- [ ] Remover SELECT em `envios_campanha`
- [ ] Usar view `campaign_sends` para queries
- [ ] Testar funcionalidade

---

## Arquivos que Precisam Migracao

| Arquivo | Status | Observacao |
|---------|--------|------------|
| `app/services/campanha.py` | Parcial | `criar_envios_campanha` corrigido (E01) |
| `app/api/routes/campanhas.py` | Pendente | Epic 05 |
| `app/api/routes/piloto.py` | Pendente | Referencias a envios_campanha |
| `app/services/jobs/campanhas.py` | Pendente | Verificar referencias |

---

## Referencia Rapida

```
ANTIGO                          NOVO
------                          ----
nome                    ->      nome_template
tipo                    ->      tipo_campanha
mensagem_template       ->      obter_abertura_texto() ou corpo
config                  ->      audience_filters
filtro_especialidades   ->      especialidades
filtro_regioes          ->      regioes
envios_criados          ->      enviados
envios_campanha (table) ->      fila_mensagens + campaign_sends (view)
```
