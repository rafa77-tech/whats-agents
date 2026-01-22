# Epic 05: Atualizar Endpoints

## Objetivo

Refatorar `app/api/routes/campanhas.py` para usar os nomes corretos de colunas e o novo modulo de campanhas.

## Contexto

Os endpoints atuais tentam inserir e ler colunas que nao existem no banco. Este epico atualiza todos os endpoints para usar o schema correto.

---

## Story 5.1: Atualizar Endpoint POST /campanhas/

### Objetivo

Corrigir endpoint de criacao de campanhas.

### Tarefas

1. **Atualizar modelo Pydantic** em `app/api/routes/campanhas.py`:

```python
# ANTES
class CriarCampanha(BaseModel):
    nome: str
    tipo: str
    mensagem_template: str
    filtro_especialidades: Optional[List[str]] = None
    filtro_regioes: Optional[List[str]] = None
    filtro_tags: Optional[List[str]] = None
    agendar_para: Optional[datetime] = None
    max_por_dia: int = 50

# DEPOIS
class CriarCampanha(BaseModel):
    """Modelo para criacao de campanha."""
    nome_template: str
    tipo_campanha: str  # discovery, oferta, reativacao, followup
    corpo: Optional[str] = None  # Template da mensagem (opcional para discovery)
    tom: Optional[str] = "amigavel"
    especialidades: Optional[List[str]] = None
    regioes: Optional[List[str]] = None
    quantidade_alvo: int = 50
    agendar_para: Optional[datetime] = None
    pode_ofertar: bool = False
```

2. **Atualizar endpoint** `criar_campanha()`:

```python
# ANTES
@router.post("/")
async def criar_campanha(dados: CriarCampanha):
    campanha_resp = (
        supabase.table("campanhas")
        .insert({
            "nome": dados.nome,
            "tipo": dados.tipo,
            "mensagem_template": dados.mensagem_template,
            ...
        })
        .execute()
    )

# DEPOIS
from app.services.campanhas import campanha_repository
from app.services.campanhas.types import TipoCampanha, AudienceFilters

@router.post("/")
async def criar_campanha(dados: CriarCampanha):
    """Cria nova campanha."""
    # Validar tipo
    try:
        tipo = TipoCampanha(dados.tipo_campanha)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Tipo invalido: {dados.tipo_campanha}. "
                   f"Use: discovery, oferta, reativacao, followup"
        )

    # Montar filtros
    audience_filters = AudienceFilters(
        especialidades=dados.especialidades or [],
        regioes=dados.regioes or [],
        quantidade_alvo=dados.quantidade_alvo,
    )

    # Criar via repository
    campanha = await campanha_repository.criar(
        nome_template=dados.nome_template,
        tipo_campanha=tipo,
        corpo=dados.corpo,
        tom=dados.tom,
        agendar_para=dados.agendar_para,
        audience_filters=audience_filters,
        pode_ofertar=dados.pode_ofertar,
        created_by="api",
    )

    if not campanha:
        raise HTTPException(status_code=500, detail="Erro ao criar campanha")

    return {
        "id": campanha.id,
        "nome_template": campanha.nome_template,
        "tipo_campanha": campanha.tipo_campanha.value,
        "status": campanha.status.value,
    }
```

### DoD

- [ ] Modelo `CriarCampanha` atualizado com nomes corretos
- [ ] Endpoint usa `campanha_repository.criar()`
- [ ] Validacao de tipo_campanha implementada
- [ ] Resposta usa nomes corretos

---

## Story 5.2: Atualizar Endpoint POST /{id}/iniciar

### Objetivo

Corrigir endpoint de inicializacao de campanhas.

### Tarefas

1. **Atualizar endpoint** `iniciar_campanha()`:

```python
# ANTES
@router.post("/{campanha_id}/iniciar")
async def iniciar_campanha(campanha_id: str):
    supabase.table("campanhas").update({
        "status": "ativa",
        "iniciada_em": datetime.utcnow().isoformat()
    }).eq("id", campanha_id).execute()
    await criar_envios_campanha(campanha_id)
    return {"status": "iniciada"}

# DEPOIS
from app.services.campanhas import campanha_executor, campanha_repository
from app.services.campanhas.types import StatusCampanha

@router.post("/{campanha_id}/iniciar")
async def iniciar_campanha(campanha_id: int):
    """Inicia execucao de campanha."""
    # Verificar se campanha existe
    campanha = await campanha_repository.buscar_por_id(campanha_id)
    if not campanha:
        raise HTTPException(status_code=404, detail="Campanha nao encontrada")

    # Verificar status
    if campanha.status not in (StatusCampanha.AGENDADA, StatusCampanha.RASCUNHO):
        raise HTTPException(
            status_code=400,
            detail=f"Campanha com status {campanha.status.value} nao pode ser iniciada"
        )

    # Executar
    sucesso = await campanha_executor.executar(campanha_id)

    if not sucesso:
        raise HTTPException(status_code=500, detail="Erro ao executar campanha")

    return {
        "status": "iniciada",
        "campanha_id": campanha_id,
    }
```

### DoD

- [ ] Endpoint usa `campanha_executor.executar()`
- [ ] Validacao de existencia da campanha
- [ ] Validacao de status antes de iniciar
- [ ] Parametro `campanha_id` e `int` (nao `str`)

---

## Story 5.3: Atualizar Endpoint de Relatorio

### Objetivo

Corrigir endpoint de relatorio que usa colunas erradas.

### Tarefas

1. **Localizar endpoint** de relatorio (provavelmente `GET /{id}/relatorio`)

2. **Atualizar para usar nomes corretos**:

```python
# ANTES (exemplo do erro nos logs)
@router.get("/{campanha_id}/relatorio")
async def relatorio_campanha(campanha_id: int):
    campanha = supabase.table("campanhas").select("*").eq("id", campanha_id).single().execute()
    return {
        "nome": campanha["nome"],  # KeyError!
        ...
    }

# DEPOIS
@router.get("/{campanha_id}/relatorio")
async def relatorio_campanha(campanha_id: int):
    """Retorna relatorio da campanha."""
    campanha = await campanha_repository.buscar_por_id(campanha_id)

    if not campanha:
        raise HTTPException(status_code=404, detail="Campanha nao encontrada")

    # Buscar metricas da view
    metricas_resp = (
        supabase.table("campaign_metrics")
        .select("*")
        .eq("campaign_id", campanha_id)
        .single()
        .execute()
    )

    metricas = metricas_resp.data if metricas_resp.data else {}

    return {
        "campanha": {
            "id": campanha.id,
            "nome_template": campanha.nome_template,
            "tipo_campanha": campanha.tipo_campanha.value,
            "status": campanha.status.value,
            "total_destinatarios": campanha.total_destinatarios,
            "enviados": campanha.enviados,
        },
        "metricas": {
            "total_sends": metricas.get("total_sends", 0),
            "delivered": metricas.get("delivered", 0),
            "delivery_rate": metricas.get("delivery_rate", 0),
            "blocked": metricas.get("blocked", 0),
            "failed": metricas.get("failed", 0),
        }
    }
```

### DoD

- [ ] Endpoint usa `campanha_repository`
- [ ] Usa `nome_template` em vez de `nome`
- [ ] Usa view `campaign_metrics` para metricas
- [ ] Nao quebra com KeyError

---

## Story 5.4: Remover Funcao Duplicada

### Objetivo

Remover funcao `criar_envios_campanha` local que duplica logica.

### Tarefas

1. **Localizar funcao** `criar_envios_campanha` em `app/api/routes/campanhas.py` (se existir)

2. **Remover funcao** e substituir por uso do executor:

```python
# REMOVER esta funcao se existir no arquivo:
async def criar_envios_campanha(campanha_id: str):
    # ... codigo legado ...

# Usar em vez disso:
from app.services.campanhas import campanha_executor
# await campanha_executor.executar(campanha_id)
```

3. **Verificar imports** - remover imports nao usados:

```python
# Remover se nao usado mais:
# from app.services.campanha import criar_envios_campanha
# from app.services.segmentacao import segmentacao_service
# from app.fragmentos.mensagens import formatar_primeiro_contato
```

### DoD

- [ ] Funcao duplicada removida
- [ ] Imports nao usados removidos
- [ ] Arquivo usa apenas `campanha_repository` e `campanha_executor`

---

## Story 5.5: Testes dos Endpoints

### Objetivo

Criar/atualizar testes para os endpoints.

### Tarefas

1. **Criar/atualizar arquivo** `tests/api/routes/test_campanhas.py`:

```python
"""Testes dos endpoints de campanhas."""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

from app.main import app
from app.services.campanhas.types import (
    CampanhaData,
    TipoCampanha,
    StatusCampanha,
)


client = TestClient(app)


@pytest.fixture
def mock_campanha():
    """Campanha mockada."""
    return CampanhaData(
        id=16,
        nome_template="Teste",
        tipo_campanha=TipoCampanha.DISCOVERY,
        status=StatusCampanha.RASCUNHO,
    )


def test_criar_campanha_sucesso():
    """Testa criacao de campanha com sucesso."""
    with patch("app.api.routes.campanhas.campanha_repository") as mock_repo:
        mock_repo.criar = AsyncMock(return_value=CampanhaData(
            id=17,
            nome_template="Nova Campanha",
            tipo_campanha=TipoCampanha.DISCOVERY,
            status=StatusCampanha.RASCUNHO,
        ))

        response = client.post("/campanhas/", json={
            "nome_template": "Nova Campanha",
            "tipo_campanha": "discovery",
            "quantidade_alvo": 50,
        })

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == 17
        assert data["tipo_campanha"] == "discovery"


def test_criar_campanha_tipo_invalido():
    """Testa criacao de campanha com tipo invalido."""
    response = client.post("/campanhas/", json={
        "nome_template": "Teste",
        "tipo_campanha": "tipo_invalido",
    })

    assert response.status_code == 400
    assert "Tipo invalido" in response.json()["detail"]


def test_iniciar_campanha_sucesso(mock_campanha):
    """Testa inicio de campanha."""
    mock_campanha.status = StatusCampanha.AGENDADA

    with patch("app.api.routes.campanhas.campanha_repository") as mock_repo, \
         patch("app.api.routes.campanhas.campanha_executor") as mock_exec:

        mock_repo.buscar_por_id = AsyncMock(return_value=mock_campanha)
        mock_exec.executar = AsyncMock(return_value=True)

        response = client.post("/campanhas/16/iniciar")

        assert response.status_code == 200
        assert response.json()["status"] == "iniciada"


def test_iniciar_campanha_nao_encontrada():
    """Testa inicio de campanha que nao existe."""
    with patch("app.api.routes.campanhas.campanha_repository") as mock_repo:
        mock_repo.buscar_por_id = AsyncMock(return_value=None)

        response = client.post("/campanhas/999/iniciar")

        assert response.status_code == 404


def test_relatorio_campanha(mock_campanha):
    """Testa relatorio de campanha."""
    with patch("app.api.routes.campanhas.campanha_repository") as mock_repo, \
         patch("app.api.routes.campanhas.supabase") as mock_supabase:

        mock_repo.buscar_por_id = AsyncMock(return_value=mock_campanha)
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = {
            "total_sends": 50,
            "delivered": 45,
            "delivery_rate": 90.0,
        }

        response = client.get("/campanhas/16/relatorio")

        assert response.status_code == 200
        data = response.json()
        assert data["campanha"]["nome_template"] == "Teste"
        assert data["metricas"]["total_sends"] == 50
```

2. **Rodar testes**:

```bash
uv run pytest tests/api/routes/test_campanhas.py -v
```

### DoD

- [ ] Testes criados/atualizados
- [ ] Teste `test_criar_campanha_sucesso` passa
- [ ] Teste `test_criar_campanha_tipo_invalido` passa
- [ ] Teste `test_iniciar_campanha_sucesso` passa
- [ ] Teste `test_relatorio_campanha` passa

---

## Checklist do Epico

- [ ] **S35.E05.1** - POST /campanhas/ atualizado
- [ ] **S35.E05.2** - POST /{id}/iniciar atualizado
- [ ] **S35.E05.3** - GET /{id}/relatorio atualizado
- [ ] **S35.E05.4** - Codigo duplicado removido
- [ ] **S35.E05.5** - Testes passando

### Arquivos Modificados

- `app/api/routes/campanhas.py`
- `tests/api/routes/test_campanhas.py`

---

## Tempo Estimado

| Story | Tempo |
|-------|-------|
| 5.1 POST /campanhas/ | 45min |
| 5.2 POST /{id}/iniciar | 30min |
| 5.3 GET /{id}/relatorio | 30min |
| 5.4 Remover duplicado | 15min |
| 5.5 Testes | 1h |
| **Total** | **3h** |
