# Epic 08: Testes e Validacao

## Objetivo

Criar/atualizar testes unitarios e de integracao para os novos modulos de campanhas.

## Contexto

Os novos modulos `campanha_repository` e `campanha_executor` precisam de testes para garantir funcionamento correto e prevenir regressoes.

---

## Story 8.1: Estrutura de Testes

### Objetivo

Criar estrutura de diretorio e fixtures para testes de campanhas.

### Tarefas

1. **Criar diretorio de testes**:

```bash
mkdir -p tests/services/campanhas
touch tests/services/campanhas/__init__.py
```

2. **Criar arquivo de fixtures** `tests/services/campanhas/conftest.py`:

```python
"""Fixtures para testes de campanhas."""
import pytest
from datetime import datetime, UTC
from unittest.mock import AsyncMock, MagicMock

from app.services.campanhas.types import (
    CampanhaData,
    TipoCampanha,
    StatusCampanha,
    AudienceFilters,
)


@pytest.fixture
def mock_supabase():
    """Mock do cliente Supabase."""
    mock = MagicMock()
    mock.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = None
    mock.table.return_value.insert.return_value.execute.return_value.data = [{}]
    mock.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [{}]
    return mock


@pytest.fixture
def campanha_discovery():
    """Campanha discovery de exemplo."""
    return CampanhaData(
        id=16,
        nome_template="Campanha Discovery Teste",
        tipo_campanha=TipoCampanha.DISCOVERY,
        status=StatusCampanha.AGENDADA,
        corpo=None,
        tom="amigavel",
        audience_filters=AudienceFilters(
            especialidades=["cardiologia"],
            regioes=["SP"],
            quantidade_alvo=50,
        ),
        agendar_para=datetime.now(UTC),
        total_destinatarios=50,
        enviados=0,
        created_at=datetime.now(UTC),
    )


@pytest.fixture
def campanha_oferta():
    """Campanha oferta de exemplo."""
    return CampanhaData(
        id=17,
        nome_template="Campanha Oferta Teste",
        tipo_campanha=TipoCampanha.OFERTA,
        status=StatusCampanha.RASCUNHO,
        corpo="Oi {nome}, temos uma vaga especial...",
        tom="profissional",
        audience_filters=AudienceFilters(
            especialidades=["ortopedia"],
            regioes=["RJ"],
            quantidade_alvo=30,
        ),
        agendar_para=None,
        total_destinatarios=30,
        enviados=0,
        created_at=datetime.now(UTC),
    )


@pytest.fixture
def mock_fila_service():
    """Mock do fila_service."""
    mock = AsyncMock()
    mock.enfileirar = AsyncMock(return_value={"id": 123})
    return mock


@pytest.fixture
def mock_abertura_service():
    """Mock do servico de abertura."""
    mock = AsyncMock()
    mock.return_value = "Oi Dr Carlos! Tudo bem? Sou a Julia da Revoluna..."
    return mock


@pytest.fixture
def lista_medicos():
    """Lista de medicos para segmentacao."""
    return [
        {"id": 1, "nome": "Carlos Silva", "telefone": "11999990001", "especialidade": "cardiologia"},
        {"id": 2, "nome": "Maria Santos", "telefone": "11999990002", "especialidade": "cardiologia"},
        {"id": 3, "nome": "Joao Oliveira", "telefone": "11999990003", "especialidade": "cardiologia"},
    ]
```

### DoD

- [ ] Diretorio `tests/services/campanhas/` criado
- [ ] `conftest.py` com fixtures basicas
- [ ] Fixtures para campanhas discovery e oferta
- [ ] Mocks para servicos externos

---

## Story 8.2: Testes do Repository

### Objetivo

Criar testes unitarios para `campanha_repository`.

### Tarefas

1. **Criar arquivo** `tests/services/campanhas/test_repository.py`:

```python
"""Testes do campanha_repository."""
import pytest
from datetime import datetime, UTC
from unittest.mock import patch, MagicMock

from app.services.campanhas.repository import CampanhaRepository
from app.services.campanhas.types import (
    TipoCampanha,
    StatusCampanha,
    AudienceFilters,
)


class TestCampanhaRepositoryCriar:
    """Testes de criacao de campanha."""

    @pytest.mark.asyncio
    async def test_criar_campanha_discovery_sucesso(self, mock_supabase):
        """Testa criacao de campanha discovery."""
        # Arrange
        mock_supabase.table.return_value.insert.return_value.execute.return_value.data = [{
            "id": 18,
            "nome_template": "Nova Discovery",
            "tipo_campanha": "discovery",
            "status": "rascunho",
        }]

        with patch("app.services.campanhas.repository.supabase", mock_supabase):
            repo = CampanhaRepository()

            # Act
            campanha = await repo.criar(
                nome_template="Nova Discovery",
                tipo_campanha=TipoCampanha.DISCOVERY,
                audience_filters=AudienceFilters(
                    especialidades=["cardiologia"],
                    regioes=["SP"],
                    quantidade_alvo=50,
                ),
            )

            # Assert
            assert campanha is not None
            assert campanha.id == 18
            assert campanha.tipo_campanha == TipoCampanha.DISCOVERY

    @pytest.mark.asyncio
    async def test_criar_campanha_com_corpo(self, mock_supabase):
        """Testa criacao de campanha com corpo definido."""
        mock_supabase.table.return_value.insert.return_value.execute.return_value.data = [{
            "id": 19,
            "nome_template": "Oferta Especial",
            "tipo_campanha": "oferta",
            "corpo": "Oi {nome}, temos uma vaga...",
            "status": "rascunho",
        }]

        with patch("app.services.campanhas.repository.supabase", mock_supabase):
            repo = CampanhaRepository()

            campanha = await repo.criar(
                nome_template="Oferta Especial",
                tipo_campanha=TipoCampanha.OFERTA,
                corpo="Oi {nome}, temos uma vaga...",
                audience_filters=AudienceFilters(quantidade_alvo=30),
            )

            assert campanha.corpo == "Oi {nome}, temos uma vaga..."


class TestCampanhaRepositoryBuscar:
    """Testes de busca de campanha."""

    @pytest.mark.asyncio
    async def test_buscar_por_id_existente(self, mock_supabase, campanha_discovery):
        """Testa busca de campanha existente."""
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = {
            "id": 16,
            "nome_template": "Campanha Discovery Teste",
            "tipo_campanha": "discovery",
            "status": "agendada",
        }

        with patch("app.services.campanhas.repository.supabase", mock_supabase):
            repo = CampanhaRepository()

            campanha = await repo.buscar_por_id(16)

            assert campanha is not None
            assert campanha.id == 16

    @pytest.mark.asyncio
    async def test_buscar_por_id_inexistente(self, mock_supabase):
        """Testa busca de campanha que nao existe."""
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = None

        with patch("app.services.campanhas.repository.supabase", mock_supabase):
            repo = CampanhaRepository()

            campanha = await repo.buscar_por_id(999)

            assert campanha is None


class TestCampanhaRepositoryAtualizar:
    """Testes de atualizacao de campanha."""

    @pytest.mark.asyncio
    async def test_atualizar_status(self, mock_supabase):
        """Testa atualizacao de status."""
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [{
            "id": 16,
            "status": "ativa",
        }]

        with patch("app.services.campanhas.repository.supabase", mock_supabase):
            repo = CampanhaRepository()

            sucesso = await repo.atualizar_status(16, StatusCampanha.ATIVA)

            assert sucesso is True

    @pytest.mark.asyncio
    async def test_incrementar_enviados(self, mock_supabase):
        """Testa incremento de contador de enviados."""
        # Primeiro retorna campanha com enviados=5
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = {
            "enviados": 5,
        }
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [{
            "enviados": 6,
        }]

        with patch("app.services.campanhas.repository.supabase", mock_supabase):
            repo = CampanhaRepository()

            novo_valor = await repo.incrementar_enviados(16)

            assert novo_valor == 6


class TestCampanhaRepositoryListar:
    """Testes de listagem de campanhas."""

    @pytest.mark.asyncio
    async def test_listar_agendadas(self, mock_supabase):
        """Testa listagem de campanhas agendadas."""
        mock_supabase.table.return_value.select.return_value.eq.return_value.lte.return_value.execute.return_value.data = [
            {"id": 16, "nome_template": "Campanha 1", "status": "agendada"},
            {"id": 17, "nome_template": "Campanha 2", "status": "agendada"},
        ]

        with patch("app.services.campanhas.repository.supabase", mock_supabase):
            repo = CampanhaRepository()

            campanhas = await repo.listar_agendadas_para_executar()

            assert len(campanhas) == 2
```

2. **Rodar testes**:

```bash
uv run pytest tests/services/campanhas/test_repository.py -v
```

### DoD

- [ ] Arquivo `test_repository.py` criado
- [ ] Testes para `criar()` (discovery e com corpo)
- [ ] Testes para `buscar_por_id()` (existe e nao existe)
- [ ] Testes para `atualizar_status()`
- [ ] Testes para `incrementar_enviados()`
- [ ] Testes para `listar_agendadas_para_executar()`
- [ ] Todos os testes passam

---

## Story 8.3: Testes do Executor

### Objetivo

Criar testes unitarios para `campanha_executor`.

### Tarefas

1. **Criar arquivo** `tests/services/campanhas/test_executor.py`:

```python
"""Testes do campanha_executor."""
import pytest
from datetime import datetime, UTC
from unittest.mock import patch, AsyncMock, MagicMock

from app.services.campanhas.executor import CampanhaExecutor
from app.services.campanhas.types import (
    CampanhaData,
    TipoCampanha,
    StatusCampanha,
    AudienceFilters,
)


class TestCampanhaExecutorExecutar:
    """Testes de execucao de campanha."""

    @pytest.mark.asyncio
    async def test_executar_campanha_discovery_sucesso(
        self,
        campanha_discovery,
        mock_fila_service,
        mock_abertura_service,
        lista_medicos,
    ):
        """Testa execucao completa de campanha discovery."""
        with patch("app.services.campanhas.executor.campanha_repository") as mock_repo, \
             patch("app.services.campanhas.executor.fila_service", mock_fila_service), \
             patch("app.services.campanhas.executor.obter_abertura_texto", mock_abertura_service), \
             patch("app.services.campanhas.executor.segmentar_audiencia") as mock_segment:

            # Setup
            mock_repo.buscar_por_id = AsyncMock(return_value=campanha_discovery)
            mock_repo.atualizar_status = AsyncMock(return_value=True)
            mock_repo.incrementar_enviados = AsyncMock(return_value=1)
            mock_segment.return_value = lista_medicos

            executor = CampanhaExecutor()

            # Act
            sucesso = await executor.executar(16)

            # Assert
            assert sucesso is True
            mock_repo.atualizar_status.assert_called()
            assert mock_fila_service.enfileirar.call_count == 3  # 3 medicos

    @pytest.mark.asyncio
    async def test_executar_campanha_nao_encontrada(self):
        """Testa execucao de campanha inexistente."""
        with patch("app.services.campanhas.executor.campanha_repository") as mock_repo:
            mock_repo.buscar_por_id = AsyncMock(return_value=None)

            executor = CampanhaExecutor()

            sucesso = await executor.executar(999)

            assert sucesso is False

    @pytest.mark.asyncio
    async def test_executar_campanha_status_invalido(self, campanha_discovery):
        """Testa execucao de campanha com status invalido."""
        campanha_discovery.status = StatusCampanha.CONCLUIDA

        with patch("app.services.campanhas.executor.campanha_repository") as mock_repo:
            mock_repo.buscar_por_id = AsyncMock(return_value=campanha_discovery)

            executor = CampanhaExecutor()

            sucesso = await executor.executar(16)

            assert sucesso is False

    @pytest.mark.asyncio
    async def test_executar_campanha_oferta_com_corpo(
        self,
        campanha_oferta,
        mock_fila_service,
        lista_medicos,
    ):
        """Testa execucao de campanha oferta usando corpo."""
        with patch("app.services.campanhas.executor.campanha_repository") as mock_repo, \
             patch("app.services.campanhas.executor.fila_service", mock_fila_service), \
             patch("app.services.campanhas.executor.segmentar_audiencia") as mock_segment:

            mock_repo.buscar_por_id = AsyncMock(return_value=campanha_oferta)
            mock_repo.atualizar_status = AsyncMock(return_value=True)
            mock_repo.incrementar_enviados = AsyncMock(return_value=1)
            mock_segment.return_value = lista_medicos

            executor = CampanhaExecutor()

            sucesso = await executor.executar(17)

            assert sucesso is True
            # Verificar que usou corpo e nao abertura dinamica
            call_args = mock_fila_service.enfileirar.call_args_list[0]
            assert "temos uma vaga" in call_args[1].get("mensagem", "")


class TestCampanhaExecutorGerarMensagem:
    """Testes de geracao de mensagem."""

    @pytest.mark.asyncio
    async def test_gerar_mensagem_discovery(
        self,
        campanha_discovery,
        mock_abertura_service,
    ):
        """Testa geracao de mensagem para discovery."""
        medico = {"id": 1, "nome": "Carlos", "telefone": "11999990001"}

        with patch("app.services.campanhas.executor.obter_abertura_texto", mock_abertura_service):
            executor = CampanhaExecutor()

            mensagem = await executor._gerar_mensagem(campanha_discovery, medico)

            assert mensagem is not None
            mock_abertura_service.assert_called_once()

    @pytest.mark.asyncio
    async def test_gerar_mensagem_com_corpo(self, campanha_oferta):
        """Testa geracao de mensagem usando corpo."""
        medico = {"id": 1, "nome": "Carlos", "telefone": "11999990001"}

        executor = CampanhaExecutor()

        mensagem = await executor._gerar_mensagem(campanha_oferta, medico)

        assert "Carlos" in mensagem
        assert "temos uma vaga" in mensagem


class TestCampanhaExecutorSegmentacao:
    """Testes de segmentacao de audiencia."""

    @pytest.mark.asyncio
    async def test_segmentar_com_filtros(self, campanha_discovery):
        """Testa segmentacao com filtros de especialidade e regiao."""
        with patch("app.services.campanhas.executor.supabase") as mock_supabase:
            mock_supabase.table.return_value.select.return_value.in_.return_value.in_.return_value.limit.return_value.execute.return_value.data = [
                {"id": 1, "nome": "Carlos"},
                {"id": 2, "nome": "Maria"},
            ]

            executor = CampanhaExecutor()

            medicos = await executor._segmentar_audiencia(campanha_discovery)

            assert len(medicos) == 2
```

2. **Rodar testes**:

```bash
uv run pytest tests/services/campanhas/test_executor.py -v
```

### DoD

- [ ] Arquivo `test_executor.py` criado
- [ ] Testes para `executar()` (sucesso, nao encontrada, status invalido)
- [ ] Testes para `_gerar_mensagem()` (discovery e com corpo)
- [ ] Testes para `_segmentar_audiencia()`
- [ ] Todos os testes passam

---

## Story 8.4: Testes dos Types

### Objetivo

Criar testes para os types e validacoes.

### Tarefas

1. **Criar arquivo** `tests/services/campanhas/test_types.py`:

```python
"""Testes dos types de campanha."""
import pytest
from datetime import datetime, UTC

from app.services.campanhas.types import (
    TipoCampanha,
    StatusCampanha,
    AudienceFilters,
    CampanhaData,
)


class TestTipoCampanha:
    """Testes do enum TipoCampanha."""

    def test_valores_validos(self):
        """Testa todos os valores do enum."""
        assert TipoCampanha.DISCOVERY.value == "discovery"
        assert TipoCampanha.OFERTA.value == "oferta"
        assert TipoCampanha.REATIVACAO.value == "reativacao"
        assert TipoCampanha.FOLLOWUP.value == "followup"

    def test_criar_de_string(self):
        """Testa criacao a partir de string."""
        tipo = TipoCampanha("discovery")
        assert tipo == TipoCampanha.DISCOVERY

    def test_string_invalida_levanta_erro(self):
        """Testa que string invalida levanta ValueError."""
        with pytest.raises(ValueError):
            TipoCampanha("tipo_invalido")


class TestStatusCampanha:
    """Testes do enum StatusCampanha."""

    def test_valores_validos(self):
        """Testa todos os valores do enum."""
        assert StatusCampanha.RASCUNHO.value == "rascunho"
        assert StatusCampanha.AGENDADA.value == "agendada"
        assert StatusCampanha.ATIVA.value == "ativa"
        assert StatusCampanha.PAUSADA.value == "pausada"
        assert StatusCampanha.CONCLUIDA.value == "concluida"
        assert StatusCampanha.CANCELADA.value == "cancelada"


class TestAudienceFilters:
    """Testes do dataclass AudienceFilters."""

    def test_criar_com_valores(self):
        """Testa criacao com todos os campos."""
        filters = AudienceFilters(
            especialidades=["cardiologia", "ortopedia"],
            regioes=["SP", "RJ"],
            quantidade_alvo=100,
        )

        assert filters.especialidades == ["cardiologia", "ortopedia"]
        assert filters.regioes == ["SP", "RJ"]
        assert filters.quantidade_alvo == 100

    def test_criar_com_defaults(self):
        """Testa criacao com valores default."""
        filters = AudienceFilters()

        assert filters.especialidades == []
        assert filters.regioes == []
        assert filters.quantidade_alvo == 50

    def test_to_dict(self):
        """Testa conversao para dicionario."""
        filters = AudienceFilters(
            especialidades=["cardiologia"],
            regioes=["SP"],
            quantidade_alvo=30,
        )

        d = filters.to_dict()

        assert d["especialidades"] == ["cardiologia"]
        assert d["regioes"] == ["SP"]
        assert d["quantidade_alvo"] == 30


class TestCampanhaData:
    """Testes do dataclass CampanhaData."""

    def test_criar_campanha_completa(self):
        """Testa criacao de campanha com todos os campos."""
        campanha = CampanhaData(
            id=16,
            nome_template="Teste",
            tipo_campanha=TipoCampanha.DISCOVERY,
            status=StatusCampanha.RASCUNHO,
        )

        assert campanha.id == 16
        assert campanha.nome_template == "Teste"
        assert campanha.tipo_campanha == TipoCampanha.DISCOVERY

    def test_campanha_discovery_sem_corpo(self):
        """Testa que campanha discovery pode nao ter corpo."""
        campanha = CampanhaData(
            id=17,
            nome_template="Discovery",
            tipo_campanha=TipoCampanha.DISCOVERY,
            status=StatusCampanha.RASCUNHO,
            corpo=None,
        )

        assert campanha.corpo is None

    def test_campanha_usa_geracao_dinamica(self):
        """Testa metodo que indica se usa geracao dinamica."""
        discovery = CampanhaData(
            id=16,
            nome_template="Discovery",
            tipo_campanha=TipoCampanha.DISCOVERY,
            status=StatusCampanha.RASCUNHO,
            corpo=None,
        )

        oferta = CampanhaData(
            id=17,
            nome_template="Oferta",
            tipo_campanha=TipoCampanha.OFERTA,
            status=StatusCampanha.RASCUNHO,
            corpo="Template...",
        )

        assert discovery.usa_geracao_dinamica() is True
        assert oferta.usa_geracao_dinamica() is False
```

2. **Rodar testes**:

```bash
uv run pytest tests/services/campanhas/test_types.py -v
```

### DoD

- [ ] Arquivo `test_types.py` criado
- [ ] Testes para `TipoCampanha` enum
- [ ] Testes para `StatusCampanha` enum
- [ ] Testes para `AudienceFilters` dataclass
- [ ] Testes para `CampanhaData` dataclass
- [ ] Todos os testes passam

---

## Story 8.5: Testes de Integracao

### Objetivo

Criar testes de integracao para o fluxo completo.

### Tarefas

1. **Criar arquivo** `tests/services/campanhas/test_integration.py`:

```python
"""Testes de integracao do modulo de campanhas."""
import pytest
from datetime import datetime, UTC
from unittest.mock import patch, AsyncMock, MagicMock

from app.services.campanhas import campanha_repository, campanha_executor
from app.services.campanhas.types import TipoCampanha, StatusCampanha


@pytest.mark.integration
class TestFluxoCompletoCampanha:
    """Testes do fluxo completo de campanha."""

    @pytest.mark.asyncio
    async def test_criar_e_executar_campanha(self):
        """Testa fluxo completo: criar -> agendar -> executar."""
        with patch("app.services.campanhas.repository.supabase") as mock_db, \
             patch("app.services.campanhas.executor.fila_service") as mock_fila, \
             patch("app.services.campanhas.executor.obter_abertura_texto") as mock_abertura:

            # Setup mocks
            mock_db.table.return_value.insert.return_value.execute.return_value.data = [{
                "id": 20,
                "nome_template": "Fluxo Completo",
                "tipo_campanha": "discovery",
                "status": "rascunho",
            }]
            mock_db.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = {
                "id": 20,
                "nome_template": "Fluxo Completo",
                "tipo_campanha": "discovery",
                "status": "agendada",
                "audience_filters": {"especialidades": ["cardiologia"], "quantidade_alvo": 2},
            }
            mock_db.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [{}]
            mock_db.table.return_value.select.return_value.in_.return_value.limit.return_value.execute.return_value.data = [
                {"id": 1, "nome": "Carlos", "telefone": "11999990001"},
            ]

            mock_fila.enfileirar = AsyncMock(return_value={"id": 100})
            mock_abertura.return_value = "Oi Dr Carlos!"

            # 1. Criar campanha
            campanha = await campanha_repository.criar(
                nome_template="Fluxo Completo",
                tipo_campanha=TipoCampanha.DISCOVERY,
            )

            assert campanha is not None
            assert campanha.id == 20

            # 2. Executar campanha
            sucesso = await campanha_executor.executar(20)

            assert sucesso is True
            mock_fila.enfileirar.assert_called()


@pytest.mark.integration
class TestFluxoCampanhaComErro:
    """Testes de fluxo com erros."""

    @pytest.mark.asyncio
    async def test_executar_campanha_sem_destinatarios(self):
        """Testa execucao quando nao ha destinatarios."""
        with patch("app.services.campanhas.executor.campanha_repository") as mock_repo, \
             patch("app.services.campanhas.executor.segmentar_audiencia") as mock_segment:

            mock_repo.buscar_por_id = AsyncMock(return_value=MagicMock(
                id=21,
                status=StatusCampanha.AGENDADA,
                tipo_campanha=TipoCampanha.DISCOVERY,
            ))
            mock_segment.return_value = []  # Nenhum destinatario

            sucesso = await campanha_executor.executar(21)

            # Deve concluir sem enviar nada
            assert sucesso is True  # ou False, dependendo da regra de negocio
```

2. **Rodar testes de integracao**:

```bash
uv run pytest tests/services/campanhas/test_integration.py -v -m integration
```

### DoD

- [ ] Arquivo `test_integration.py` criado
- [ ] Teste de fluxo completo (criar -> executar)
- [ ] Teste de fluxo com erro
- [ ] Testes marcados com `@pytest.mark.integration`
- [ ] Todos os testes passam

---

## Story 8.6: Cobertura e CI

### Objetivo

Garantir cobertura minima e configurar CI.

### Tarefas

1. **Rodar cobertura**:

```bash
uv run pytest tests/services/campanhas/ -v --cov=app/services/campanhas --cov-report=term-missing
```

2. **Verificar cobertura minima** (70%):

```bash
uv run pytest tests/services/campanhas/ --cov=app/services/campanhas --cov-fail-under=70
```

3. **Gerar relatorio HTML**:

```bash
uv run pytest tests/services/campanhas/ --cov=app/services/campanhas --cov-report=html
# Abrir htmlcov/index.html
```

4. **Verificar que todos os testes do projeto passam**:

```bash
uv run pytest tests/ -v --tb=short
```

### DoD

- [ ] Cobertura >= 70% no modulo campanhas
- [ ] Nenhum teste falhando
- [ ] Relatorio de cobertura gerado

---

## Checklist do Epico

- [ ] **S35.E08.1** - Estrutura de testes criada
- [ ] **S35.E08.2** - Testes do repository
- [ ] **S35.E08.3** - Testes do executor
- [ ] **S35.E08.4** - Testes dos types
- [ ] **S35.E08.5** - Testes de integracao
- [ ] **S35.E08.6** - Cobertura >= 70%

### Comandos de Verificacao

```bash
# Rodar todos os testes de campanhas
uv run pytest tests/services/campanhas/ -v

# Verificar cobertura
uv run pytest tests/services/campanhas/ --cov=app/services/campanhas --cov-fail-under=70

# Rodar todos os testes do projeto
uv run pytest tests/ -v --tb=short
```

---

## Tempo Estimado

| Story | Tempo |
|-------|-------|
| 8.1 Estrutura e fixtures | 30min |
| 8.2 Testes repository | 1h |
| 8.3 Testes executor | 1h |
| 8.4 Testes types | 30min |
| 8.5 Testes integracao | 45min |
| 8.6 Cobertura e CI | 15min |
| **Total** | **4h** |
