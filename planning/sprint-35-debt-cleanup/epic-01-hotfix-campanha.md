# Epic 01: Hotfix Campanha 16

## Objetivo

Corrigir a funcao `criar_envios_campanha()` para que a campanha 16 execute sem erros.

## Contexto

A campanha 16 foi agendada para 21/01/2026 12:00 e esta falhando a cada minuto com:

```
[ERRO] Erro ao iniciar campanha 16: 'mensagem_template'
```

O job `processar-campanhas-agendadas` chama `criar_envios_campanha()` que tenta acessar colunas que nao existem na tabela `campanhas`.

### Mapeamento de Colunas

| Codigo Atual | Coluna Real | Acao |
|--------------|-------------|------|
| `campanha["mensagem_template"]` | **NAO EXISTE** | Usar `obter_abertura_texto()` para discovery |
| `campanha["tipo"]` | `tipo_campanha` | Renomear |
| `campanha.get("config", {})` | `audience_filters` | Renomear |
| `envios_criados` (update) | `enviados` | Renomear |

### Arquivos Envolvidos

- `app/services/campanha.py` - Funcao `criar_envios_campanha()` (linhas 255-313)
- `app/services/jobs/campanhas.py` - Chama a funcao

---

## Story 1.1: Corrigir Acesso a Colunas

### Objetivo

Atualizar `criar_envios_campanha()` para usar os nomes corretos das colunas.

### Tarefas

1. **Abrir arquivo** `app/services/campanha.py`

2. **Localizar funcao** `criar_envios_campanha` (linha ~255)

3. **Corrigir linha 277** - config para audience_filters:

```python
# ANTES (linha 277)
config = campanha.get("config", {})

# DEPOIS
config = campanha.get("audience_filters", {})
```

4. **Corrigir linha 281-286** - filtros para novo formato:

```python
# ANTES
if config.get("filtro_especialidades"):
    filtros["especialidade"] = config["filtro_especialidades"][0]
if config.get("filtro_regioes"):
    filtros["regiao"] = config["filtro_regioes"][0]

# DEPOIS
if config.get("especialidades"):
    filtros["especialidade"] = config["especialidades"][0]
if config.get("regioes"):
    filtros["regiao"] = config["regioes"][0]
```

5. **Corrigir linha 303** - tipo para tipo_campanha:

```python
# ANTES
tipo=campanha["tipo"],

# DEPOIS
tipo=campanha.get("tipo_campanha", "campanha"),
```

6. **Corrigir linha 310** - envios_criados para enviados:

```python
# ANTES
supabase.table("campanhas").update({
    "envios_criados": len(destinatarios)
}).eq("id", campanha_id).execute()

# DEPOIS
supabase.table("campanhas").update({
    "enviados": len(destinatarios)
}).eq("id", campanha_id).execute()
```

### DoD

- [ ] Linha 277 corrigida (`config` -> `audience_filters`)
- [ ] Linhas 281-286 corrigidas (nomes de filtros)
- [ ] Linha 303 corrigida (`tipo` -> `tipo_campanha`)
- [ ] Linha 310 corrigida (`envios_criados` -> `enviados`)

---

## Story 1.2: Implementar Geracao Dinamica de Mensagem

### Objetivo

Para campanhas do tipo `discovery`, gerar mensagem usando o servico de aberturas em vez de template fixo.

### Tarefas

1. **Adicionar import** no topo do arquivo `app/services/campanha.py`:

```python
# Adicionar apos linha 19 (que ja tem: from app.services.abertura import obter_abertura)
from app.services.abertura import obter_abertura_texto
```

2. **Substituir bloco de geracao de mensagem** (linhas 291-297):

```python
# ANTES (linhas 291-297)
# Criar envio para cada destinatario
for dest in destinatarios:
    # Personalizar mensagem
    mensagem = campanha["mensagem_template"].format(
        nome=dest.get("primeiro_nome", ""),
        especialidade=dest.get("especialidade_nome", "médico")
    )

# DEPOIS
# Criar envio para cada destinatario
for dest in destinatarios:
    # Gerar mensagem baseada no tipo de campanha
    tipo_campanha = campanha.get("tipo_campanha", "campanha")

    if tipo_campanha == "discovery":
        # Discovery: usar aberturas dinamicas para variedade
        mensagem = await obter_abertura_texto(
            cliente_id=dest["id"],
            nome=dest.get("primeiro_nome", "")
        )
    else:
        # Outros tipos: usar corpo como template
        corpo = campanha.get("corpo", "")
        if "{nome}" in corpo or "{especialidade}" in corpo:
            mensagem = corpo.format(
                nome=dest.get("primeiro_nome", ""),
                especialidade=dest.get("especialidade_nome", "medico")
            )
        else:
            mensagem = corpo
```

### DoD

- [ ] Import de `obter_abertura_texto` adicionado
- [ ] Geracao de mensagem diferenciada por tipo_campanha
- [ ] Campanhas discovery usam aberturas dinamicas
- [ ] Outros tipos usam `corpo` como template

---

## Story 1.3: Usar fila_mensagens em vez de envios_campanha

### Objetivo

Garantir que os envios vao para `fila_mensagens` (que ja esta configurado) e nao para `envios_campanha` (que nao existe).

### Tarefas

1. **Verificar bloco de enfileiramento** (linhas 299-306):

```python
# Codigo atual (deve estar correto se usa fila_service)
await fila_service.enfileirar(
    cliente_id=dest["id"],
    conteudo=mensagem,
    tipo=campanha.get("tipo_campanha", "campanha"),
    prioridade=3,
    metadata={"campanha_id": campanha_id}
)
```

2. **Se estiver usando supabase.table("envios_campanha")**, substituir por:

```python
await fila_service.enfileirar(
    cliente_id=dest["id"],
    conteudo=mensagem,
    tipo=campanha.get("tipo_campanha", "campanha"),
    prioridade=3,
    metadata={"campanha_id": str(campanha_id)}
)
```

3. **Verificar se `fila_service` esta importado** no topo do arquivo:

```python
from app.services.fila import fila_service
```

### DoD

- [ ] Envios usam `fila_service.enfileirar()`
- [ ] Nenhuma referencia a `envios_campanha` na funcao
- [ ] `metadata.campanha_id` passado como string

---

## Story 1.4: Testar Hotfix Localmente

### Objetivo

Validar que as correcoes funcionam antes de deploy.

### Tarefas

1. **Criar teste unitario** em `tests/services/test_campanha_hotfix.py`:

```python
"""Testes do hotfix da campanha."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.campanha import criar_envios_campanha


@pytest.fixture
def mock_campanha_discovery():
    """Campanha discovery como a 16."""
    return {
        "id": 16,
        "nome_template": "Piloto Discovery",
        "tipo_campanha": "discovery",
        "corpo": "[DISCOVERY] Usar aberturas dinamicas",
        "status": "agendada",
        "audience_filters": {
            "regioes": [],
            "especialidades": [],
            "quantidade_alvo": 50
        },
        "pode_ofertar": False,
    }


@pytest.fixture
def mock_destinatario():
    """Destinatario de teste."""
    return {
        "id": "123e4567-e89b-12d3-a456-426614174000",
        "primeiro_nome": "Carlos",
        "especialidade_nome": "Cardiologia",
    }


@pytest.mark.asyncio
async def test_criar_envios_campanha_discovery(mock_campanha_discovery, mock_destinatario):
    """Testa criacao de envios para campanha discovery."""
    with patch("app.services.campanha.supabase") as mock_supabase, \
         patch("app.services.campanha.segmentacao_service") as mock_seg, \
         patch("app.services.campanha.fila_service") as mock_fila, \
         patch("app.services.campanha.obter_abertura_texto") as mock_abertura:

        # Setup mocks
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = mock_campanha_discovery
        mock_seg.buscar_segmento = AsyncMock(return_value=[mock_destinatario])
        mock_fila.enfileirar = AsyncMock()
        mock_abertura.return_value = "Oi Dr Carlos! Tudo bem?\n\nSou a Julia da Revoluna"

        # Executar
        await criar_envios_campanha(16)

        # Verificar que usou abertura dinamica
        mock_abertura.assert_called_once_with(
            cliente_id=mock_destinatario["id"],
            nome=mock_destinatario["primeiro_nome"]
        )

        # Verificar que enfileirou
        mock_fila.enfileirar.assert_called_once()
        call_args = mock_fila.enfileirar.call_args
        assert call_args.kwargs["cliente_id"] == mock_destinatario["id"]
        assert "campanha_id" in call_args.kwargs["metadata"]


@pytest.mark.asyncio
async def test_criar_envios_nao_usa_mensagem_template(mock_campanha_discovery):
    """Garante que nao tenta acessar mensagem_template."""
    with patch("app.services.campanha.supabase") as mock_supabase, \
         patch("app.services.campanha.segmentacao_service") as mock_seg, \
         patch("app.services.campanha.fila_service") as mock_fila, \
         patch("app.services.campanha.obter_abertura_texto") as mock_abertura:

        # Campanha sem mensagem_template (como a real)
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = mock_campanha_discovery
        mock_seg.buscar_segmento = AsyncMock(return_value=[])

        # Deve executar sem erro (nao tentar acessar mensagem_template)
        await criar_envios_campanha(16)

        # Se chegou aqui, nao deu KeyError
        assert True
```

2. **Rodar testes**:

```bash
uv run pytest tests/services/test_campanha_hotfix.py -v
```

3. **Verificar se nao quebrou outros testes**:

```bash
uv run pytest tests/ -k campanha -v
```

### DoD

- [ ] Teste `test_criar_envios_campanha_discovery` passa
- [ ] Teste `test_criar_envios_nao_usa_mensagem_template` passa
- [ ] Nenhum outro teste de campanha quebrou

---

## Story 1.5: Deploy e Validacao

### Objetivo

Fazer deploy do hotfix e validar que a campanha 16 executa.

### Tarefas

1. **Commit das mudancas**:

```bash
git add app/services/campanha.py tests/services/test_campanha_hotfix.py
git commit -m "fix(campanhas): corrigir criar_envios_campanha para schema atual

- Usar audience_filters em vez de config
- Usar tipo_campanha em vez de tipo
- Usar enviados em vez de envios_criados
- Gerar mensagem dinamica para discovery
- Usar fila_mensagens via fila_service

Fixes: Campanha 16 falhando com KeyError 'mensagem_template'

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

2. **Push e deploy**:

```bash
git push origin main
# Aguardar deploy automatico no Railway
```

3. **Monitorar logs** (Railway):

```bash
railway logs --filter campanha -n 50
```

4. **Verificar que erro parou**:

- Nao deve mais aparecer `[ERRO] Erro ao iniciar campanha 16: 'mensagem_template'`
- Deve aparecer `Campanha 16 iniciada` ou similar

5. **Verificar envios em fila_mensagens**:

```sql
-- Via MCP Supabase
SELECT COUNT(*)
FROM fila_mensagens
WHERE metadata->>'campanha_id' = '16';
```

### DoD

- [ ] Commit feito com mensagem descritiva
- [ ] Deploy realizado
- [ ] Logs nao mostram mais erro `'mensagem_template'`
- [ ] Envios aparecem em `fila_mensagens`

---

## Checklist do Epico

- [ ] **S35.E01.1** - Colunas corrigidas
- [ ] **S35.E01.2** - Geracao dinamica implementada
- [ ] **S35.E01.3** - Usando fila_mensagens
- [ ] **S35.E01.4** - Testes passando
- [ ] **S35.E01.5** - Deploy e validacao

### Validacao Final

```bash
# 1. Rodar testes
uv run pytest tests/services/test_campanha_hotfix.py -v

# 2. Verificar que nao tem mais erros nos logs
railway logs --filter "Erro ao iniciar campanha" -n 20

# 3. Verificar envios criados
# (via MCP Supabase)
SELECT COUNT(*) FROM fila_mensagens WHERE metadata->>'campanha_id' = '16';
```

---

## Tempo Estimado

| Story | Tempo |
|-------|-------|
| 1.1 Corrigir colunas | 15min |
| 1.2 Geracao dinamica | 30min |
| 1.3 Usar fila_mensagens | 15min |
| 1.4 Testes | 30min |
| 1.5 Deploy | 30min |
| **Total** | **2h** |
