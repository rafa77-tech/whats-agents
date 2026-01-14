# Epic 03: Repository Pattern

## Severidade: CRITICO

## Objetivo

Introduzir o padrao Repository para desacoplar a logica de negocio do Supabase, permitindo:
- Testes unitarios sem mocks complexos de import
- Injecao de dependencia via FastAPI Depends
- Facilidade para trocar banco de dados no futuro
- Codigo mais limpo e testavel

## Problema Atual

### Acoplamento Direto

```python
# Problema: 40+ arquivos importam supabase diretamente
from app.services.supabase import supabase

async def buscar_medico(id: str):
    # Acoplado ao Supabase
    return supabase.table("clientes").select("*").eq("id", id).execute()
```

### Consequencias

1. **Testes dificeis:** Precisam mockar `supabase` via `@patch`
2. **Dependencia oculta:** Funcoes nao declaram que precisam do banco
3. **Impossivel trocar:** Mudar de Supabase requer alterar dezenas de arquivos

### Solucao: Repository Pattern

```python
# Solucao: Repository com interface clara
class ClienteRepository:
    def __init__(self, db: DatabaseClient):
        self.db = db

    async def buscar_por_id(self, id: str) -> Optional[Cliente]:
        return self.db.table("clientes").select("*").eq("id", id).execute()

# Uso com dependency injection
async def endpoint(repo: ClienteRepository = Depends(get_cliente_repo)):
    cliente = await repo.buscar_por_id("123")

# Teste facil
def test_buscar_cliente():
    mock_db = MockDatabase()
    repo = ClienteRepository(mock_db)
    # Testar sem patches!
```

---

## Stories

### S30.E3.1: Criar Interface Base

**Objetivo:** Definir a interface base que todos os repositories implementarao.

**Contexto:** Uma interface comum garante consistencia e facilita testes.

**Arquivos a Criar:**
- `app/repositories/__init__.py`
- `app/repositories/base.py`

**Tarefas:**

1. Criar diretorio:
   ```bash
   mkdir -p app/repositories
   ```

2. Criar `app/repositories/base.py`:

```python
"""
Base Repository - Interface comum para todos os repositories.

Sprint 30 - S30.E3.1
"""
from abc import ABC, abstractmethod
from typing import TypeVar, Generic, Optional, List, Any
from dataclasses import dataclass

# Type variable para entidades
T = TypeVar('T')


@dataclass
class QueryResult(Generic[T]):
    """Resultado padronizado de query."""
    data: Optional[T] = None
    success: bool = True
    error: Optional[str] = None
    count: Optional[int] = None


class BaseRepository(ABC, Generic[T]):
    """
    Interface base para repositories.

    Todos os repositories devem herdar desta classe e implementar
    os metodos abstratos.

    Attributes:
        table_name: Nome da tabela no banco de dados
    """

    def __init__(self, db_client: Any):
        """
        Inicializa o repository.

        Args:
            db_client: Cliente de banco de dados (Supabase, Mock, etc.)
        """
        self.db = db_client

    @property
    @abstractmethod
    def table_name(self) -> str:
        """Nome da tabela no banco."""
        pass

    @abstractmethod
    async def buscar_por_id(self, id: str) -> Optional[T]:
        """
        Busca entidade por ID.

        Args:
            id: UUID da entidade

        Returns:
            Entidade ou None se nao encontrada
        """
        pass

    @abstractmethod
    async def listar(
        self,
        limit: int = 100,
        offset: int = 0,
        **filters
    ) -> List[T]:
        """
        Lista entidades com filtros opcionais.

        Args:
            limit: Maximo de resultados
            offset: Pular N primeiros resultados
            **filters: Filtros adicionais (ex: status="ativa")

        Returns:
            Lista de entidades
        """
        pass

    @abstractmethod
    async def criar(self, data: dict) -> T:
        """
        Cria nova entidade.

        Args:
            data: Dados da entidade

        Returns:
            Entidade criada com ID
        """
        pass

    @abstractmethod
    async def atualizar(self, id: str, data: dict) -> Optional[T]:
        """
        Atualiza entidade existente.

        Args:
            id: UUID da entidade
            data: Campos a atualizar

        Returns:
            Entidade atualizada ou None se nao encontrada
        """
        pass

    @abstractmethod
    async def deletar(self, id: str) -> bool:
        """
        Deleta entidade.

        Args:
            id: UUID da entidade

        Returns:
            True se deletou, False se nao encontrada
        """
        pass

    # Metodos utilitarios (implementacao padrao)

    async def existe(self, id: str) -> bool:
        """Verifica se entidade existe."""
        return await self.buscar_por_id(id) is not None

    async def contar(self, **filters) -> int:
        """Conta entidades com filtros."""
        # Implementacao padrao - pode ser sobrescrita
        items = await self.listar(**filters)
        return len(items)
```

3. Criar `app/repositories/__init__.py`:

```python
"""
Repositories - Camada de acesso a dados.

Sprint 30

Este modulo implementa o padrao Repository para desacoplar
a logica de negocio do banco de dados.

Uso:
    from app.repositories import ClienteRepository, ConversaRepository

    # Com dependency injection
    async def endpoint(repo: ClienteRepository = Depends(get_cliente_repo)):
        cliente = await repo.buscar_por_id("123")

    # Em testes
    def test_algo():
        mock_db = MockDatabase()
        repo = ClienteRepository(mock_db)
        # Testar sem patches!
"""
from .base import BaseRepository, QueryResult

__all__ = [
    "BaseRepository",
    "QueryResult",
]
```

**Como Testar:**

```bash
# Verificar que importa sem erros
python -c "from app.repositories import BaseRepository, QueryResult; print('OK')"

# Verificar tipos
uv run mypy app/repositories/base.py --ignore-missing-imports
```

**DoD:**
- [ ] Diretorio `app/repositories/` criado
- [ ] `base.py` com interface BaseRepository
- [ ] `__init__.py` com exports
- [ ] Importa sem erros
- [ ] Commit: `feat(repositories): cria interface BaseRepository`

---

### S30.E3.2: Implementar ClienteRepository

**Objetivo:** Criar repository para a entidade Cliente (medico).

**Contexto:** `clientes` eh a tabela mais acessada. Consolidar o acesso aqui.

**Arquivo:** `app/repositories/cliente.py`

**Tarefas:**

1. Criar `app/repositories/cliente.py`:

```python
"""
Repository para Clientes (Medicos).

Sprint 30 - S30.E3.2
"""
import logging
from typing import Optional, List, Any
from dataclasses import dataclass

from .base import BaseRepository

logger = logging.getLogger(__name__)


@dataclass
class Cliente:
    """Entidade Cliente (Medico)."""
    id: str
    telefone: str
    nome: Optional[str] = None
    email: Optional[str] = None
    crm: Optional[str] = None
    especialidade_id: Optional[str] = None
    status: str = "ativo"
    opt_out: bool = False
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict) -> "Cliente":
        """Cria Cliente a partir de dict do banco."""
        return cls(
            id=data.get("id", ""),
            telefone=data.get("telefone", ""),
            nome=data.get("nome"),
            email=data.get("email"),
            crm=data.get("crm"),
            especialidade_id=data.get("especialidade_id"),
            status=data.get("status", "ativo"),
            opt_out=data.get("opt_out", False),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
        )


class ClienteRepository(BaseRepository[Cliente]):
    """
    Repository para operacoes de Cliente.

    Uso:
        repo = ClienteRepository(supabase)
        cliente = await repo.buscar_por_telefone("5511999999999")
    """

    @property
    def table_name(self) -> str:
        return "clientes"

    async def buscar_por_id(self, id: str) -> Optional[Cliente]:
        """Busca cliente por ID."""
        try:
            response = (
                self.db.table(self.table_name)
                .select("*")
                .eq("id", id)
                .execute()
            )
            if response.data:
                return Cliente.from_dict(response.data[0])
            return None
        except Exception as e:
            logger.error(f"Erro ao buscar cliente {id}: {e}")
            return None

    async def listar(
        self,
        limit: int = 100,
        offset: int = 0,
        **filters
    ) -> List[Cliente]:
        """Lista clientes com filtros."""
        try:
            query = self.db.table(self.table_name).select("*")

            # Aplicar filtros
            if "status" in filters:
                query = query.eq("status", filters["status"])
            if "opt_out" in filters:
                query = query.eq("opt_out", filters["opt_out"])
            if "especialidade_id" in filters:
                query = query.eq("especialidade_id", filters["especialidade_id"])

            response = query.range(offset, offset + limit - 1).execute()
            return [Cliente.from_dict(item) for item in response.data or []]
        except Exception as e:
            logger.error(f"Erro ao listar clientes: {e}")
            return []

    async def criar(self, data: dict) -> Cliente:
        """Cria novo cliente."""
        try:
            response = (
                self.db.table(self.table_name)
                .insert(data)
                .execute()
            )
            if response.data:
                logger.info(f"Cliente criado: {response.data[0].get('id')}")
                return Cliente.from_dict(response.data[0])
            raise ValueError("Falha ao criar cliente")
        except Exception as e:
            logger.error(f"Erro ao criar cliente: {e}")
            raise

    async def atualizar(self, id: str, data: dict) -> Optional[Cliente]:
        """Atualiza cliente existente."""
        try:
            response = (
                self.db.table(self.table_name)
                .update(data)
                .eq("id", id)
                .execute()
            )
            if response.data:
                logger.info(f"Cliente atualizado: {id}")
                return Cliente.from_dict(response.data[0])
            return None
        except Exception as e:
            logger.error(f"Erro ao atualizar cliente {id}: {e}")
            return None

    async def deletar(self, id: str) -> bool:
        """Deleta cliente (soft delete via status)."""
        try:
            response = (
                self.db.table(self.table_name)
                .update({"status": "inativo"})
                .eq("id", id)
                .execute()
            )
            return bool(response.data)
        except Exception as e:
            logger.error(f"Erro ao deletar cliente {id}: {e}")
            return False

    # Metodos especificos de Cliente

    async def buscar_por_telefone(self, telefone: str) -> Optional[Cliente]:
        """
        Busca cliente por telefone.

        Args:
            telefone: Numero do telefone (sera normalizado)

        Returns:
            Cliente ou None
        """
        telefone_limpo = "".join(filter(str.isdigit, telefone))
        try:
            response = (
                self.db.table(self.table_name)
                .select("*")
                .eq("telefone", telefone_limpo)
                .execute()
            )
            if response.data:
                return Cliente.from_dict(response.data[0])
            return None
        except Exception as e:
            logger.error(f"Erro ao buscar cliente por telefone: {e}")
            return None

    async def buscar_ou_criar(
        self,
        telefone: str,
        nome: Optional[str] = None
    ) -> Cliente:
        """
        Busca cliente pelo telefone ou cria novo.

        Args:
            telefone: Numero do telefone
            nome: Nome do cliente (usado na criacao)

        Returns:
            Cliente existente ou recem-criado
        """
        cliente = await self.buscar_por_telefone(telefone)
        if cliente:
            return cliente

        telefone_limpo = "".join(filter(str.isdigit, telefone))
        return await self.criar({
            "telefone": telefone_limpo,
            "nome": nome or "Medico",
            "status": "ativo",
            "opt_out": False,
        })

    async def marcar_opt_out(self, id: str) -> bool:
        """Marca cliente como opt-out."""
        result = await self.atualizar(id, {"opt_out": True})
        return result is not None

    async def listar_ativos(self, limit: int = 100) -> List[Cliente]:
        """Lista apenas clientes ativos e nao opt-out."""
        return await self.listar(
            limit=limit,
            status="ativo",
            opt_out=False
        )
```

2. Atualizar `app/repositories/__init__.py`:

```python
from .base import BaseRepository, QueryResult
from .cliente import ClienteRepository, Cliente

__all__ = [
    "BaseRepository",
    "QueryResult",
    "ClienteRepository",
    "Cliente",
]
```

**Como Testar:**

```bash
# Verificar import
python -c "from app.repositories import ClienteRepository, Cliente; print('OK')"

# Criar teste basico
uv run pytest tests/repositories/test_cliente.py -v
```

**DoD:**
- [ ] `cliente.py` criado com ClienteRepository
- [ ] Dataclass Cliente criada
- [ ] Todos os metodos da interface implementados
- [ ] Metodos especificos (buscar_por_telefone, buscar_ou_criar)
- [ ] Commit: `feat(repositories): implementa ClienteRepository`

---

### S30.E3.3: Implementar ConversaRepository

**Objetivo:** Criar repository para a entidade Conversa.

**Arquivo:** `app/repositories/conversa.py`

**Tarefas:**

1. Criar `app/repositories/conversa.py`:

```python
"""
Repository para Conversas.

Sprint 30 - S30.E3.3
"""
import logging
from typing import Optional, List, Literal
from dataclasses import dataclass
from datetime import datetime

from .base import BaseRepository

logger = logging.getLogger(__name__)

ControlledBy = Literal["ai", "human"]
ConversaStatus = Literal["ativa", "encerrada", "pausada"]


@dataclass
class Conversa:
    """Entidade Conversa."""
    id: str
    cliente_id: str
    status: ConversaStatus = "ativa"
    controlled_by: ControlledBy = "ai"
    chatwoot_conversation_id: Optional[int] = None
    instance_name: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict) -> "Conversa":
        """Cria Conversa a partir de dict do banco."""
        return cls(
            id=data.get("id", ""),
            cliente_id=data.get("cliente_id", ""),
            status=data.get("status", "ativa"),
            controlled_by=data.get("controlled_by", "ai"),
            chatwoot_conversation_id=data.get("chatwoot_conversation_id"),
            instance_name=data.get("instance_name"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
        )

    @property
    def is_ai_controlled(self) -> bool:
        """Verifica se IA esta controlando."""
        return self.controlled_by == "ai"


class ConversaRepository(BaseRepository[Conversa]):
    """
    Repository para operacoes de Conversa.

    Uso:
        repo = ConversaRepository(supabase)
        conversa = await repo.buscar_ativa_por_cliente("cliente-id")
    """

    @property
    def table_name(self) -> str:
        return "conversations"

    async def buscar_por_id(self, id: str) -> Optional[Conversa]:
        """Busca conversa por ID."""
        try:
            response = (
                self.db.table(self.table_name)
                .select("*")
                .eq("id", id)
                .execute()
            )
            if response.data:
                return Conversa.from_dict(response.data[0])
            return None
        except Exception as e:
            logger.error(f"Erro ao buscar conversa {id}: {e}")
            return None

    async def listar(
        self,
        limit: int = 100,
        offset: int = 0,
        **filters
    ) -> List[Conversa]:
        """Lista conversas com filtros."""
        try:
            query = self.db.table(self.table_name).select("*")

            if "status" in filters:
                query = query.eq("status", filters["status"])
            if "controlled_by" in filters:
                query = query.eq("controlled_by", filters["controlled_by"])
            if "cliente_id" in filters:
                query = query.eq("cliente_id", filters["cliente_id"])

            response = (
                query
                .order("created_at", desc=True)
                .range(offset, offset + limit - 1)
                .execute()
            )
            return [Conversa.from_dict(item) for item in response.data or []]
        except Exception as e:
            logger.error(f"Erro ao listar conversas: {e}")
            return []

    async def criar(self, data: dict) -> Conversa:
        """Cria nova conversa."""
        try:
            response = (
                self.db.table(self.table_name)
                .insert(data)
                .execute()
            )
            if response.data:
                logger.info(f"Conversa criada: {response.data[0].get('id')}")
                return Conversa.from_dict(response.data[0])
            raise ValueError("Falha ao criar conversa")
        except Exception as e:
            logger.error(f"Erro ao criar conversa: {e}")
            raise

    async def atualizar(self, id: str, data: dict) -> Optional[Conversa]:
        """Atualiza conversa existente."""
        try:
            response = (
                self.db.table(self.table_name)
                .update(data)
                .eq("id", id)
                .execute()
            )
            if response.data:
                return Conversa.from_dict(response.data[0])
            return None
        except Exception as e:
            logger.error(f"Erro ao atualizar conversa {id}: {e}")
            return None

    async def deletar(self, id: str) -> bool:
        """Deleta conversa (encerra)."""
        result = await self.atualizar(id, {"status": "encerrada"})
        return result is not None

    # Metodos especificos de Conversa

    async def buscar_ativa_por_cliente(self, cliente_id: str) -> Optional[Conversa]:
        """
        Busca conversa ativa de um cliente.

        Args:
            cliente_id: UUID do cliente

        Returns:
            Conversa ativa ou None
        """
        try:
            response = (
                self.db.table(self.table_name)
                .select("*")
                .eq("cliente_id", cliente_id)
                .eq("status", "ativa")
                .execute()
            )
            if response.data:
                return Conversa.from_dict(response.data[0])
            return None
        except Exception as e:
            logger.error(f"Erro ao buscar conversa ativa: {e}")
            return None

    async def criar_ou_buscar_ativa(
        self,
        cliente_id: str,
        instance_name: Optional[str] = None
    ) -> Conversa:
        """
        Busca conversa ativa ou cria nova.

        Args:
            cliente_id: UUID do cliente
            instance_name: Nome da instancia WhatsApp

        Returns:
            Conversa existente ou nova
        """
        conversa = await self.buscar_ativa_por_cliente(cliente_id)
        if conversa:
            return conversa

        return await self.criar({
            "cliente_id": cliente_id,
            "status": "ativa",
            "controlled_by": "ai",
            "instance_name": instance_name,
        })

    async def transferir_para_humano(self, id: str) -> Optional[Conversa]:
        """Transfere conversa para controle humano."""
        return await self.atualizar(id, {"controlled_by": "human"})

    async def transferir_para_ia(self, id: str) -> Optional[Conversa]:
        """Transfere conversa para controle da IA."""
        return await self.atualizar(id, {"controlled_by": "ai"})

    async def encerrar(self, id: str) -> Optional[Conversa]:
        """Encerra conversa."""
        return await self.atualizar(id, {"status": "encerrada"})

    async def listar_controladas_por_ia(self, limit: int = 100) -> List[Conversa]:
        """Lista conversas ativas controladas pela IA."""
        return await self.listar(
            limit=limit,
            status="ativa",
            controlled_by="ai"
        )

    async def contar_por_status(self) -> dict:
        """Conta conversas agrupadas por status."""
        try:
            response = (
                self.db.table(self.table_name)
                .select("status")
                .execute()
            )
            counts = {"ativa": 0, "encerrada": 0, "pausada": 0}
            for row in response.data or []:
                status = row.get("status", "ativa")
                counts[status] = counts.get(status, 0) + 1
            return counts
        except Exception as e:
            logger.error(f"Erro ao contar conversas: {e}")
            return {}
```

2. Atualizar `app/repositories/__init__.py`:

```python
from .base import BaseRepository, QueryResult
from .cliente import ClienteRepository, Cliente
from .conversa import ConversaRepository, Conversa

__all__ = [
    "BaseRepository",
    "QueryResult",
    "ClienteRepository",
    "Cliente",
    "ConversaRepository",
    "Conversa",
]
```

**DoD:**
- [ ] `conversa.py` criado com ConversaRepository
- [ ] Dataclass Conversa criada
- [ ] Metodos especificos implementados
- [ ] Commit: `feat(repositories): implementa ConversaRepository`

---

### S30.E3.4: Implementar VagaRepository

**Objetivo:** Criar repository para a entidade Vaga.

**Arquivo:** `app/repositories/vaga.py`

**Tarefas:**

1. Criar `app/repositories/vaga.py`:

```python
"""
Repository para Vagas.

Sprint 30 - S30.E3.4
"""
import logging
from typing import Optional, List, Literal
from dataclasses import dataclass
from datetime import datetime, date

from .base import BaseRepository

logger = logging.getLogger(__name__)

VagaStatus = Literal["aberta", "reservada", "preenchida", "cancelada"]


@dataclass
class Vaga:
    """Entidade Vaga."""
    id: str
    hospital_id: str
    especialidade_id: Optional[str] = None
    data_plantao: Optional[str] = None
    hora_inicio: Optional[str] = None
    hora_fim: Optional[str] = None
    valor: Optional[float] = None
    status: VagaStatus = "aberta"
    medico_id: Optional[str] = None
    descricao: Optional[str] = None
    created_at: Optional[str] = None

    # Campos populados via join
    hospital_nome: Optional[str] = None
    especialidade_nome: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict) -> "Vaga":
        """Cria Vaga a partir de dict do banco."""
        # Extrair dados de joins se existirem
        hospital_nome = None
        especialidade_nome = None

        if "hospitais" in data and data["hospitais"]:
            hospital_nome = data["hospitais"].get("nome")
        if "especialidades" in data and data["especialidades"]:
            especialidade_nome = data["especialidades"].get("nome")

        return cls(
            id=data.get("id", ""),
            hospital_id=data.get("hospital_id", ""),
            especialidade_id=data.get("especialidade_id"),
            data_plantao=data.get("data_plantao"),
            hora_inicio=data.get("hora_inicio"),
            hora_fim=data.get("hora_fim"),
            valor=data.get("valor"),
            status=data.get("status", "aberta"),
            medico_id=data.get("medico_id"),
            descricao=data.get("descricao"),
            created_at=data.get("created_at"),
            hospital_nome=hospital_nome,
            especialidade_nome=especialidade_nome,
        )

    @property
    def is_disponivel(self) -> bool:
        """Verifica se vaga esta disponivel."""
        return self.status == "aberta"


class VagaRepository(BaseRepository[Vaga]):
    """
    Repository para operacoes de Vaga.

    Uso:
        repo = VagaRepository(supabase)
        vagas = await repo.listar_disponiveis(especialidade_id="123")
    """

    @property
    def table_name(self) -> str:
        return "vagas"

    async def buscar_por_id(self, id: str) -> Optional[Vaga]:
        """Busca vaga por ID com dados de hospital e especialidade."""
        try:
            response = (
                self.db.table(self.table_name)
                .select("*, hospitais(nome, endereco), especialidades(nome)")
                .eq("id", id)
                .execute()
            )
            if response.data:
                return Vaga.from_dict(response.data[0])
            return None
        except Exception as e:
            logger.error(f"Erro ao buscar vaga {id}: {e}")
            return None

    async def listar(
        self,
        limit: int = 100,
        offset: int = 0,
        **filters
    ) -> List[Vaga]:
        """Lista vagas com filtros."""
        try:
            query = self.db.table(self.table_name).select(
                "*, hospitais(nome, endereco), especialidades(nome)"
            )

            if "status" in filters:
                query = query.eq("status", filters["status"])
            if "hospital_id" in filters:
                query = query.eq("hospital_id", filters["hospital_id"])
            if "especialidade_id" in filters:
                query = query.eq("especialidade_id", filters["especialidade_id"])
            if "medico_id" in filters:
                query = query.eq("medico_id", filters["medico_id"])
            if "data_a_partir" in filters:
                query = query.gte("data_plantao", filters["data_a_partir"])

            response = (
                query
                .order("data_plantao", desc=False)
                .range(offset, offset + limit - 1)
                .execute()
            )
            return [Vaga.from_dict(item) for item in response.data or []]
        except Exception as e:
            logger.error(f"Erro ao listar vagas: {e}")
            return []

    async def criar(self, data: dict) -> Vaga:
        """Cria nova vaga."""
        try:
            response = (
                self.db.table(self.table_name)
                .insert(data)
                .execute()
            )
            if response.data:
                logger.info(f"Vaga criada: {response.data[0].get('id')}")
                return Vaga.from_dict(response.data[0])
            raise ValueError("Falha ao criar vaga")
        except Exception as e:
            logger.error(f"Erro ao criar vaga: {e}")
            raise

    async def atualizar(self, id: str, data: dict) -> Optional[Vaga]:
        """Atualiza vaga existente."""
        try:
            response = (
                self.db.table(self.table_name)
                .update(data)
                .eq("id", id)
                .execute()
            )
            if response.data:
                return Vaga.from_dict(response.data[0])
            return None
        except Exception as e:
            logger.error(f"Erro ao atualizar vaga {id}: {e}")
            return None

    async def deletar(self, id: str) -> bool:
        """Deleta vaga (cancela)."""
        result = await self.atualizar(id, {"status": "cancelada"})
        return result is not None

    # Metodos especificos de Vaga

    async def listar_disponiveis(
        self,
        especialidade_id: Optional[str] = None,
        hospital_id: Optional[str] = None,
        limit: int = 10
    ) -> List[Vaga]:
        """
        Lista vagas disponiveis (abertas).

        Args:
            especialidade_id: Filtrar por especialidade
            hospital_id: Filtrar por hospital
            limit: Maximo de resultados

        Returns:
            Lista de vagas abertas
        """
        filters = {"status": "aberta"}
        if especialidade_id:
            filters["especialidade_id"] = especialidade_id
        if hospital_id:
            filters["hospital_id"] = hospital_id

        return await self.listar(limit=limit, **filters)

    async def reservar(self, id: str, medico_id: str) -> Optional[Vaga]:
        """
        Reserva vaga para um medico.

        Args:
            id: ID da vaga
            medico_id: ID do medico

        Returns:
            Vaga reservada ou None se ja reservada
        """
        # Verificar se ainda esta aberta
        vaga = await self.buscar_por_id(id)
        if not vaga or vaga.status != "aberta":
            logger.warning(f"Vaga {id} nao esta aberta para reserva")
            return None

        return await self.atualizar(id, {
            "status": "reservada",
            "medico_id": medico_id,
        })

    async def confirmar(self, id: str) -> Optional[Vaga]:
        """Confirma vaga reservada (preenche)."""
        return await self.atualizar(id, {"status": "preenchida"})

    async def cancelar_reserva(self, id: str) -> Optional[Vaga]:
        """Cancela reserva e reabre vaga."""
        return await self.atualizar(id, {
            "status": "aberta",
            "medico_id": None,
        })

    async def listar_por_medico(self, medico_id: str) -> List[Vaga]:
        """Lista vagas de um medico."""
        return await self.listar(medico_id=medico_id)

    async def contar_por_status(self) -> dict:
        """Conta vagas agrupadas por status."""
        try:
            response = (
                self.db.table(self.table_name)
                .select("status")
                .execute()
            )
            counts = {}
            for row in response.data or []:
                status = row.get("status", "aberta")
                counts[status] = counts.get(status, 0) + 1
            return counts
        except Exception as e:
            logger.error(f"Erro ao contar vagas: {e}")
            return {}
```

2. Atualizar `__init__.py`:

```python
from .base import BaseRepository, QueryResult
from .cliente import ClienteRepository, Cliente
from .conversa import ConversaRepository, Conversa
from .vaga import VagaRepository, Vaga

__all__ = [
    "BaseRepository",
    "QueryResult",
    "ClienteRepository",
    "Cliente",
    "ConversaRepository",
    "Conversa",
    "VagaRepository",
    "Vaga",
]
```

**DoD:**
- [ ] `vaga.py` criado com VagaRepository
- [ ] Dataclass Vaga criada com suporte a joins
- [ ] Metodos especificos implementados
- [ ] Commit: `feat(repositories): implementa VagaRepository`

---

### S30.E3.5: Configurar Dependency Injection

**Objetivo:** Criar sistema de DI para injetar repositories nos endpoints.

**Arquivos:**
- `app/api/dependencies.py` (criar)
- `app/repositories/providers.py` (criar)

**Tarefas:**

1. Criar `app/repositories/providers.py`:

```python
"""
Providers de Repositories para Dependency Injection.

Sprint 30 - S30.E3.5

Uso:
    from app.repositories.providers import get_cliente_repo

    @router.get("/clientes/{id}")
    async def get_cliente(
        id: str,
        repo: ClienteRepository = Depends(get_cliente_repo)
    ):
        return await repo.buscar_por_id(id)
"""
from functools import lru_cache
from typing import Generator

from app.services.supabase import supabase
from .cliente import ClienteRepository
from .conversa import ConversaRepository
from .vaga import VagaRepository


# Factories para repositories
# Usamos o supabase singleton como default, mas permite override para testes

def get_cliente_repo() -> ClienteRepository:
    """Retorna instancia de ClienteRepository."""
    return ClienteRepository(supabase)


def get_conversa_repo() -> ConversaRepository:
    """Retorna instancia de ConversaRepository."""
    return ConversaRepository(supabase)


def get_vaga_repo() -> VagaRepository:
    """Retorna instancia de VagaRepository."""
    return VagaRepository(supabase)


# Para testes - permite injetar mock
class RepositoryOverrides:
    """
    Container para overrides de repositories em testes.

    Uso em testes:
        def override_cliente_repo():
            return ClienteRepository(mock_db)

        app.dependency_overrides[get_cliente_repo] = override_cliente_repo
    """
    _cliente: ClienteRepository = None
    _conversa: ConversaRepository = None
    _vaga: VagaRepository = None

    @classmethod
    def set_cliente(cls, repo: ClienteRepository):
        cls._cliente = repo

    @classmethod
    def set_conversa(cls, repo: ConversaRepository):
        cls._conversa = repo

    @classmethod
    def set_vaga(cls, repo: VagaRepository):
        cls._vaga = repo

    @classmethod
    def clear(cls):
        cls._cliente = None
        cls._conversa = None
        cls._vaga = None
```

2. Criar `app/api/dependencies.py`:

```python
"""
Dependencies para FastAPI - Injecao de Dependencias.

Sprint 30 - S30.E3.5

Este arquivo centraliza todas as dependencias injetaveis nos endpoints.

Uso:
    from app.api.dependencies import get_cliente_repo

    @router.get("/clientes/{id}")
    async def get_cliente(
        id: str,
        repo: ClienteRepository = Depends(get_cliente_repo)
    ):
        cliente = await repo.buscar_por_id(id)
        if not cliente:
            raise HTTPException(404, "Cliente nao encontrado")
        return cliente
"""
from app.repositories.providers import (
    get_cliente_repo,
    get_conversa_repo,
    get_vaga_repo,
)

# Re-exportar para uso nos endpoints
__all__ = [
    "get_cliente_repo",
    "get_conversa_repo",
    "get_vaga_repo",
]
```

3. Atualizar `app/repositories/__init__.py`:

```python
from .base import BaseRepository, QueryResult
from .cliente import ClienteRepository, Cliente
from .conversa import ConversaRepository, Conversa
from .vaga import VagaRepository, Vaga
from .providers import (
    get_cliente_repo,
    get_conversa_repo,
    get_vaga_repo,
)

__all__ = [
    # Base
    "BaseRepository",
    "QueryResult",
    # Entidades
    "ClienteRepository",
    "Cliente",
    "ConversaRepository",
    "Conversa",
    "VagaRepository",
    "Vaga",
    # Providers (DI)
    "get_cliente_repo",
    "get_conversa_repo",
    "get_vaga_repo",
]
```

**Como Testar:**

```python
# Teste de DI
from fastapi import Depends
from app.api.dependencies import get_cliente_repo

# Em um endpoint
@router.get("/test")
async def test_di(repo: ClienteRepository = Depends(get_cliente_repo)):
    return {"status": "ok"}
```

**DoD:**
- [ ] `providers.py` criado com factories
- [ ] `dependencies.py` criado com re-exports
- [ ] Imports funcionando
- [ ] Commit: `feat(repositories): configura dependency injection`

---

### S30.E3.6: Migrar Pipeline para Repositories

**Objetivo:** Atualizar o pipeline de processamento para usar repositories.

**Contexto:** O pipeline eh o maior consumidor de queries. Migrar gradualmente.

**Arquivos:** `app/pipeline/pre_processors.py`, `app/pipeline/core_processor.py`

**Tarefas:**

1. Identificar pontos de uso:
   ```bash
   grep -n "buscar_ou_criar_medico\|buscar_conversa_ativa\|supabase.table" app/pipeline/*.py
   ```

2. Estrategia de migracao gradual:

   **Fase 1:** Adicionar repositories como dependencia opcional
   ```python
   # app/pipeline/pre_processors.py
   from app.repositories import ClienteRepository, get_cliente_repo

   class LoadEntitiesProcessor(PreProcessor):
       def __init__(self, cliente_repo: ClienteRepository = None):
           self._cliente_repo = cliente_repo

       @property
       def cliente_repo(self) -> ClienteRepository:
           if self._cliente_repo is None:
               self._cliente_repo = get_cliente_repo()
           return self._cliente_repo

       async def process(self, context):
           # Usar repository em vez de funcao direta
           medico = await self.cliente_repo.buscar_ou_criar(
               context.telefone,
               context.primeiro_nome
           )
   ```

   **Fase 2:** Passar repositories via setup
   ```python
   # app/pipeline/setup.py
   from app.repositories import get_cliente_repo, get_conversa_repo

   def setup_pipeline():
       cliente_repo = get_cliente_repo()
       conversa_repo = get_conversa_repo()

       pipeline.add_pre_processor(
           LoadEntitiesProcessor(cliente_repo=cliente_repo)
       )
   ```

3. Migrar processors um por vez (listar aqui quais)

4. Rodar testes apos cada migracao

**DoD:**
- [ ] LoadEntitiesProcessor usando ClienteRepository
- [ ] Testes de pipeline passando
- [ ] Nenhuma regressao
- [ ] Commit: `refactor(pipeline): migra para repositories`

---

### S30.E3.7: Criar Testes com Repository Mockado

**Objetivo:** Demonstrar como testar com repositories injetados.

**Arquivo:** `tests/repositories/test_with_mock.py`

**Tarefas:**

1. Criar testes exemplo:

```python
# tests/repositories/test_with_mock.py
"""
Exemplo de testes usando repositories mockados.

Sprint 30 - S30.E3.7

Este arquivo demonstra como testar codigo que usa repositories
sem precisar de mocks de import complexos.
"""
import pytest
from unittest.mock import MagicMock, AsyncMock
from dataclasses import dataclass

from app.repositories import (
    ClienteRepository,
    Cliente,
    ConversaRepository,
    Conversa,
)


class MockDatabase:
    """
    Mock de banco de dados para testes.

    Uso:
        mock_db = MockDatabase()
        mock_db.set_response("clientes", [{"id": "123", "nome": "Teste"}])
        repo = ClienteRepository(mock_db)
    """

    def __init__(self):
        self._responses = {}
        self._calls = []

    def set_response(self, table: str, data: list):
        """Define resposta para uma tabela."""
        self._responses[table] = data

    def table(self, name: str):
        """Retorna builder mockado."""
        self._calls.append(("table", name))
        return MockQueryBuilder(self._responses.get(name, []))


class MockQueryBuilder:
    """Builder mockado para queries."""

    def __init__(self, data: list):
        self._data = data

    def select(self, *args, **kwargs):
        return self

    def eq(self, *args, **kwargs):
        return self

    def gte(self, *args, **kwargs):
        return self

    def order(self, *args, **kwargs):
        return self

    def range(self, *args, **kwargs):
        return self

    def limit(self, *args, **kwargs):
        return self

    def insert(self, data):
        # Simula insert retornando os dados com ID
        self._data = [{**data, "id": "new-uuid-123"}]
        return self

    def update(self, data):
        return self

    def execute(self):
        """Retorna resultado mockado."""
        result = MagicMock()
        result.data = self._data
        return result


class TestClienteRepositoryWithMock:
    """Testes do ClienteRepository com mock."""

    @pytest.mark.asyncio
    async def test_buscar_por_id_encontra(self):
        """Deve encontrar cliente por ID."""
        # Arrange
        mock_db = MockDatabase()
        mock_db.set_response("clientes", [{
            "id": "cliente-123",
            "telefone": "5511999999999",
            "nome": "Dr. Teste"
        }])
        repo = ClienteRepository(mock_db)

        # Act
        cliente = await repo.buscar_por_id("cliente-123")

        # Assert
        assert cliente is not None
        assert cliente.id == "cliente-123"
        assert cliente.nome == "Dr. Teste"

    @pytest.mark.asyncio
    async def test_buscar_por_id_nao_encontra(self):
        """Deve retornar None se nao encontrar."""
        # Arrange
        mock_db = MockDatabase()
        mock_db.set_response("clientes", [])  # Vazio
        repo = ClienteRepository(mock_db)

        # Act
        cliente = await repo.buscar_por_id("inexistente")

        # Assert
        assert cliente is None

    @pytest.mark.asyncio
    async def test_buscar_ou_criar_cria_novo(self):
        """Deve criar cliente se nao existir."""
        # Arrange
        mock_db = MockDatabase()
        mock_db.set_response("clientes", [])  # Nao existe
        repo = ClienteRepository(mock_db)

        # Act
        cliente = await repo.buscar_ou_criar("5511888888888", "Novo")

        # Assert
        assert cliente is not None
        assert cliente.id == "new-uuid-123"


class TestConversaRepositoryWithMock:
    """Testes do ConversaRepository com mock."""

    @pytest.mark.asyncio
    async def test_buscar_ativa_por_cliente(self):
        """Deve encontrar conversa ativa."""
        # Arrange
        mock_db = MockDatabase()
        mock_db.set_response("conversations", [{
            "id": "conv-123",
            "cliente_id": "cliente-456",
            "status": "ativa",
            "controlled_by": "ai"
        }])
        repo = ConversaRepository(mock_db)

        # Act
        conversa = await repo.buscar_ativa_por_cliente("cliente-456")

        # Assert
        assert conversa is not None
        assert conversa.status == "ativa"
        assert conversa.is_ai_controlled

    @pytest.mark.asyncio
    async def test_transferir_para_humano(self):
        """Deve transferir conversa para humano."""
        # Arrange
        mock_db = MockDatabase()
        mock_db.set_response("conversations", [{
            "id": "conv-123",
            "cliente_id": "cliente-456",
            "status": "ativa",
            "controlled_by": "human"  # Apos update
        }])
        repo = ConversaRepository(mock_db)

        # Act
        conversa = await repo.transferir_para_humano("conv-123")

        # Assert
        assert conversa is not None
        assert conversa.controlled_by == "human"


# Exemplo de teste de integracao com FastAPI
class TestEndpointWithMockedRepo:
    """Exemplo de teste de endpoint com DI mockado."""

    def test_endpoint_com_repo_mockado(self):
        """Demonstra override de dependencia."""
        from fastapi import FastAPI, Depends
        from fastapi.testclient import TestClient
        from app.repositories.providers import get_cliente_repo

        # Criar app de teste
        app = FastAPI()

        @app.get("/clientes/{id}")
        async def get_cliente(
            id: str,
            repo: ClienteRepository = Depends(get_cliente_repo)
        ):
            cliente = await repo.buscar_por_id(id)
            if not cliente:
                return {"error": "nao encontrado"}
            return {"id": cliente.id, "nome": cliente.nome}

        # Override com mock
        mock_db = MockDatabase()
        mock_db.set_response("clientes", [{
            "id": "test-id",
            "telefone": "123",
            "nome": "Mock Cliente"
        }])

        def override_repo():
            return ClienteRepository(mock_db)

        app.dependency_overrides[get_cliente_repo] = override_repo

        # Testar
        client = TestClient(app)
        response = client.get("/clientes/test-id")

        assert response.status_code == 200
        assert response.json()["nome"] == "Mock Cliente"
```

**DoD:**
- [ ] Arquivo de testes criado
- [ ] MockDatabase implementado
- [ ] Testes de ClienteRepository com mock
- [ ] Testes de ConversaRepository com mock
- [ ] Exemplo de teste de endpoint com DI
- [ ] Todos os testes passando
- [ ] Commit: `test(repositories): exemplos de testes com mock`

---

## Checklist do Epic

- [ ] **S30.E3.1** - Interface base criada
- [ ] **S30.E3.2** - ClienteRepository implementado
- [ ] **S30.E3.3** - ConversaRepository implementado
- [ ] **S30.E3.4** - VagaRepository implementado
- [ ] **S30.E3.5** - DI configurado
- [ ] **S30.E3.6** - Pipeline migrado (parcial OK)
- [ ] **S30.E3.7** - Testes exemplo criados
- [ ] Todos os testes passando

---

## Arquivos Criados

| Arquivo | Linhas |
|---------|--------|
| `app/repositories/__init__.py` | ~30 |
| `app/repositories/base.py` | ~80 |
| `app/repositories/cliente.py` | ~150 |
| `app/repositories/conversa.py` | ~150 |
| `app/repositories/vaga.py` | ~180 |
| `app/repositories/providers.py` | ~50 |
| `app/api/dependencies.py` | ~20 |
| `tests/repositories/test_with_mock.py` | ~180 |
| **Total** | **~840** |

---

## Tempo Estimado

| Story | Complexidade | Estimativa |
|-------|--------------|------------|
| S30.E3.1 | Baixa | 30min |
| S30.E3.2 | Media | 1.5h |
| S30.E3.3 | Media | 1.5h |
| S30.E3.4 | Media | 1.5h |
| S30.E3.5 | Media | 1h |
| S30.E3.6 | Alta | 2h |
| S30.E3.7 | Media | 1h |
| **Total** | | **~9h** |
