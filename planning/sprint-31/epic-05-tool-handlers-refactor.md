# Epic 05: Tool Handlers Refactor

## Severidade: P1 - MÉDIO

## Objetivo

Separar responsabilidades dos tool handlers em camadas: Handler (fino) → Service (lógica) → Repository (dados).

---

## Problema Atual

`handle_buscar_vagas()` em `app/tools/vagas.py` tem ~270 linhas e faz:

1. **Parsing de input** (linhas 168-180) - Limpa JSON malformado
2. **Queries ao banco** (linhas 195-260) - Múltiplas queries diretas
3. **Lógica de negócio** (linhas 261-350) - Filtragem, priorização
4. **Formatação de output** (linhas 351-400) - Monta resposta para LLM

### Impacto

- Impossível testar lógica de negócio sem mock do banco
- Formatação acoplada à busca
- Reutilização zero (precisa de tudo ou nada)

---

## Solução

```
Tool Handler (fino)     → VagaService (lógica)     → VagaRepository (dados)
     │                         │                           │
     │  parse input            │  buscar_compativeis()     │  listar()
     │  chama service          │  filtrar_por_medico()     │  buscar_por_id()
     │  formata output         │  priorizar()              │  ...
     │                         │                           │
```

---

## Stories

### S31.E5.1: Criar VagaService

**Arquivo:** `app/services/vaga_service.py`

```python
"""
Vaga Service - Lógica de negócio de vagas.

Sprint 31 - S31.E5.1
"""
import logging
from typing import Optional, List, Dict, Any
from datetime import date

from app.repositories import VagaRepository, Vaga, get_vaga_repo

logger = logging.getLogger(__name__)


class VagaService:
    """
    Serviço de lógica de negócio para vagas.

    Separado do handler para permitir testes isolados.
    """

    def __init__(self, repo: VagaRepository = None):
        self._repo = repo or get_vaga_repo()

    async def buscar_vagas_compativeis(
        self,
        medico_id: str,
        especialidade_id: Optional[str] = None,
        regiao: Optional[str] = None,
        data_minima: Optional[date] = None,
        limit: int = 10,
    ) -> List[Vaga]:
        """
        Busca vagas compatíveis com o perfil do médico.

        Args:
            medico_id: ID do médico
            especialidade_id: Filtrar por especialidade
            regiao: Filtrar por região
            data_minima: Data mínima do plantão
            limit: Máximo de resultados

        Returns:
            Lista de vagas ordenadas por relevância
        """
        # Buscar vagas disponíveis
        vagas = await self._repo.listar_disponiveis(
            especialidade_id=especialidade_id,
            limit=limit * 2,  # Buscar mais para filtrar depois
        )

        # Filtrar por região se especificado
        if regiao:
            vagas = self._filtrar_por_regiao(vagas, regiao)

        # Filtrar por data se especificado
        if data_minima:
            vagas = [v for v in vagas if v.data_plantao and v.data_plantao >= str(data_minima)]

        # Ordenar por relevância
        vagas = self._ordenar_por_relevancia(vagas, medico_id)

        return vagas[:limit]

    def _filtrar_por_regiao(
        self,
        vagas: List[Vaga],
        regiao: str,
    ) -> List[Vaga]:
        """Filtra vagas por região."""
        regiao_lower = regiao.lower()
        return [
            v for v in vagas
            if v.hospital_nome and regiao_lower in v.hospital_nome.lower()
        ]

    def _ordenar_por_relevancia(
        self,
        vagas: List[Vaga],
        medico_id: str,
    ) -> List[Vaga]:
        """
        Ordena vagas por relevância para o médico.

        Critérios:
        1. Vagas com maior valor primeiro
        2. Vagas mais próximas da data atual
        """
        def score(vaga: Vaga) -> float:
            s = 0.0
            if vaga.valor:
                s += vaga.valor / 1000  # Normaliza valor
            return s

        return sorted(vagas, key=score, reverse=True)

    async def verificar_disponibilidade(
        self,
        vaga_id: str,
    ) -> bool:
        """Verifica se vaga ainda está disponível."""
        vaga = await self._repo.buscar_por_id(vaga_id)
        return vaga is not None and vaga.is_disponivel

    async def resumir_vagas_para_llm(
        self,
        vagas: List[Vaga],
    ) -> List[Dict[str, Any]]:
        """
        Resume vagas no formato esperado pelo LLM.

        Formato otimizado para o Claude entender e apresentar.
        """
        return [
            {
                "VAGA_ID_PARA_HANDOFF": v.id,
                "hospital": v.hospital_nome or "Hospital",
                "especialidade": v.especialidade_nome or "Geral",
                "data": v.data_plantao,
                "horario": f"{v.hora_inicio} às {v.hora_fim}" if v.hora_inicio else "A definir",
                "valor": f"R$ {v.valor:,.2f}" if v.valor else "A combinar",
            }
            for v in vagas
        ]


# Factory
_vaga_service: Optional[VagaService] = None


def get_vaga_service() -> VagaService:
    """Retorna instância do VagaService."""
    global _vaga_service
    if _vaga_service is None:
        _vaga_service = VagaService()
    return _vaga_service
```

**DoD:**
- [ ] VagaService criado
- [ ] `buscar_vagas_compativeis()` implementado
- [ ] `_filtrar_por_regiao()` extraído
- [ ] `_ordenar_por_relevancia()` extraído
- [ ] `resumir_vagas_para_llm()` implementado
- [ ] Commit: `feat(vaga): cria VagaService`

---

### S31.E5.2: Criar ToolResponseFormatter

**Arquivo:** `app/tools/formatters.py`

```python
"""
Tool Response Formatters.

Sprint 31 - S31.E5.2

Formatadores de resposta para tools.
"""
from typing import List, Dict, Any
from app.repositories import Vaga


class ToolResponseFormatter:
    """Formata respostas de tools para o LLM."""

    @staticmethod
    def format_vagas(
        vagas: List[Dict],
        mensagem_vazia: str = "Não encontrei vagas com esses critérios no momento.",
    ) -> Dict[str, Any]:
        """
        Formata lista de vagas para resposta de tool.

        Args:
            vagas: Lista de vagas resumidas
            mensagem_vazia: Mensagem se não houver vagas

        Returns:
            Dict no formato de resposta de tool
        """
        if not vagas:
            return {
                "success": True,
                "encontrou_vagas": False,
                "mensagem": mensagem_vazia,
                "vagas": [],
            }

        return {
            "success": True,
            "encontrou_vagas": True,
            "total": len(vagas),
            "vagas": vagas,
            "instrucao": (
                "Apresente essas vagas de forma natural e conversacional. "
                "Não liste todas de uma vez, comece pelas mais relevantes."
            ),
        }

    @staticmethod
    def format_memoria_salva(
        memoria_id: str,
        tipo: str,
        conteudo: str,
    ) -> Dict[str, Any]:
        """Formata resposta de memória salva."""
        return {
            "success": True,
            "memoria_id": memoria_id,
            "tipo": tipo,
            "resumo": conteudo[:100] + "..." if len(conteudo) > 100 else conteudo,
        }

    @staticmethod
    def format_error(
        mensagem: str,
        retryable: bool = False,
    ) -> Dict[str, Any]:
        """Formata erro de tool."""
        return {
            "success": False,
            "error": mensagem,
            "retryable": retryable,
        }
```

**DoD:**
- [ ] ToolResponseFormatter criado
- [ ] `format_vagas()` implementado
- [ ] `format_memoria_salva()` implementado
- [ ] `format_error()` implementado
- [ ] Commit: `feat(tools): cria ToolResponseFormatter`

---

### S31.E5.3: Refatorar handle_buscar_vagas

**Arquivo:** `app/tools/vagas.py`

**ANTES (~270 linhas):**
```python
async def handle_buscar_vagas(tool_input, medico, conversa):
    # 100 linhas de parsing
    # 80 linhas de queries
    # 50 linhas de filtros
    # 40 linhas de formatação
```

**DEPOIS (~50 linhas):**
```python
from app.services.vaga_service import get_vaga_service
from app.tools.formatters import ToolResponseFormatter


async def handle_buscar_vagas(
    tool_input: Dict[str, Any],
    medico: Dict[str, Any],
    conversa: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Handler para tool buscar_vagas.

    Agora é apenas um adaptador fino entre o LLM e o VagaService.
    """
    # 1. Parse input
    params = _parse_buscar_vagas_input(tool_input)

    # 2. Chamar service
    service = get_vaga_service()
    vagas = await service.buscar_vagas_compativeis(
        medico_id=medico.get("id"),
        especialidade_id=params.get("especialidade_id"),
        regiao=params.get("regiao"),
        limit=params.get("limit", 5),
    )

    # 3. Resumir para LLM
    vagas_resumidas = await service.resumir_vagas_para_llm(vagas)

    # 4. Formatar resposta
    return ToolResponseFormatter.format_vagas(vagas_resumidas)


def _parse_buscar_vagas_input(tool_input: Dict) -> Dict:
    """Parse e valida input da tool."""
    # Extrair e limpar parâmetros
    regiao = tool_input.get("regiao", "").strip()
    especialidade = tool_input.get("especialidade", "").strip()

    # Limpar JSON malformado (problema comum do LLM)
    if especialidade.startswith("["):
        try:
            import json
            parsed = json.loads(especialidade)
            especialidade = parsed[0] if parsed else ""
        except:
            pass

    return {
        "regiao": regiao or None,
        "especialidade": especialidade or None,
        "limit": tool_input.get("limit", 5),
    }
```

**DoD:**
- [ ] `handle_buscar_vagas()` reduzido para < 60 linhas
- [ ] Usa VagaService para lógica
- [ ] Usa ToolResponseFormatter para output
- [ ] `_parse_buscar_vagas_input()` extraído
- [ ] Testes existentes continuam passando
- [ ] Commit: `refactor(tools): simplifica handle_buscar_vagas`

---

### S31.E5.4: Refatorar handle_salvar_memoria

**Arquivo:** `app/tools/memoria.py`

Aplicar mesmo padrão:
1. Parse input
2. Chamar MemoriaService (se não existir, criar)
3. Formatar resposta

**DoD:**
- [ ] Handler reduzido
- [ ] Service criado se necessário
- [ ] Formatter usado
- [ ] Commit: `refactor(tools): simplifica handle_salvar_memoria`

---

### S31.E5.5: Criar Testes do VagaService

**Arquivo:** `tests/services/test_vaga_service.py`

```python
"""
Testes do VagaService.

Sprint 31 - S31.E5.5
"""
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.services.vaga_service import VagaService
from app.repositories import Vaga


class TestVagaService:
    """Testes do VagaService isolado."""

    @pytest.fixture
    def mock_repo(self):
        """Cria mock do repository."""
        repo = MagicMock()
        repo.listar_disponiveis = AsyncMock(return_value=[])
        repo.buscar_por_id = AsyncMock(return_value=None)
        return repo

    @pytest.fixture
    def service(self, mock_repo):
        """Cria service com repo mockado."""
        return VagaService(repo=mock_repo)

    @pytest.mark.asyncio
    async def test_buscar_vagas_compativeis_vazio(self, service, mock_repo):
        """Deve retornar lista vazia se não há vagas."""
        mock_repo.listar_disponiveis.return_value = []

        resultado = await service.buscar_vagas_compativeis(
            medico_id="123",
            limit=5,
        )

        assert resultado == []
        mock_repo.listar_disponiveis.assert_called_once()

    @pytest.mark.asyncio
    async def test_buscar_vagas_compativeis_filtra_regiao(self, service, mock_repo):
        """Deve filtrar por região."""
        vagas = [
            Vaga(id="1", hospital_id="h1", hospital_nome="Hospital SP"),
            Vaga(id="2", hospital_id="h2", hospital_nome="Hospital RJ"),
        ]
        mock_repo.listar_disponiveis.return_value = vagas

        resultado = await service.buscar_vagas_compativeis(
            medico_id="123",
            regiao="SP",
        )

        assert len(resultado) == 1
        assert resultado[0].id == "1"

    @pytest.mark.asyncio
    async def test_verificar_disponibilidade_true(self, service, mock_repo):
        """Deve retornar True se vaga está disponível."""
        mock_repo.buscar_por_id.return_value = Vaga(
            id="1",
            hospital_id="h1",
            status="aberta",
        )

        disponivel = await service.verificar_disponibilidade("1")

        assert disponivel is True

    @pytest.mark.asyncio
    async def test_verificar_disponibilidade_false(self, service, mock_repo):
        """Deve retornar False se vaga não está disponível."""
        mock_repo.buscar_por_id.return_value = Vaga(
            id="1",
            hospital_id="h1",
            status="reservada",
        )

        disponivel = await service.verificar_disponibilidade("1")

        assert disponivel is False

    @pytest.mark.asyncio
    async def test_resumir_vagas_para_llm(self, service):
        """Deve resumir vagas no formato correto."""
        vagas = [
            Vaga(
                id="1",
                hospital_id="h1",
                hospital_nome="Hospital Test",
                especialidade_nome="Cardiologia",
                data_plantao="2025-01-20",
                hora_inicio="19:00",
                hora_fim="07:00",
                valor=2500.00,
            )
        ]

        resumo = await service.resumir_vagas_para_llm(vagas)

        assert len(resumo) == 1
        assert resumo[0]["VAGA_ID_PARA_HANDOFF"] == "1"
        assert resumo[0]["hospital"] == "Hospital Test"
        assert "R$ 2" in resumo[0]["valor"]
```

**DoD:**
- [ ] Testes criados
- [ ] Testa com repository mockado
- [ ] Testa filtros isoladamente
- [ ] Todos os testes passando
- [ ] Commit: `test(vaga): testes do VagaService`

---

## Checklist Final

- [ ] **S31.E5.1** - VagaService criado
- [ ] **S31.E5.2** - ToolResponseFormatter criado
- [ ] **S31.E5.3** - handle_buscar_vagas refatorado
- [ ] **S31.E5.4** - handle_salvar_memoria refatorado
- [ ] **S31.E5.5** - Testes criados
- [ ] Handlers têm < 60 linhas cada

---

## Arquivos Criados/Modificados

| Arquivo | Ação |
|---------|------|
| `app/services/vaga_service.py` | Criar |
| `app/tools/formatters.py` | Criar |
| `app/tools/vagas.py` | Modificar (reduzir) |
| `app/tools/memoria.py` | Modificar (reduzir) |
| `tests/services/test_vaga_service.py` | Criar |
