# Epic 04: Refatorar Executor

## Objetivo

Criar `app/services/campanhas/executor.py` com logica de execucao de campanhas usando a arquitetura correta.

## Contexto

A funcao `criar_envios_campanha()` atual em `app/services/campanha.py` esta com logica misturada e usa nomes errados. Este epico separa a logica de execucao em um modulo dedicado.

---

## Story 4.1: Criar Executor Base

### Objetivo

Criar classe executor com metodo principal de execucao.

### Tarefas

1. **Criar arquivo** `app/services/campanhas/executor.py`:

```python
"""
Executor de campanhas.

Responsavel por:
- Buscar destinatarios elegíveis
- Gerar mensagens apropriadas por tipo
- Enfileirar envios em fila_mensagens
- Atualizar contadores
"""
import logging
from datetime import datetime
from typing import List, Optional

from app.services.campanhas.repository import campanha_repository
from app.services.campanhas.types import (
    CampanhaData,
    TipoCampanha,
    StatusCampanha,
    AudienceFilters,
)
from app.services.segmentacao import segmentacao_service
from app.services.fila import fila_service
from app.services.abertura import obter_abertura_texto

logger = logging.getLogger(__name__)


class CampanhaExecutor:
    """Executor de campanhas."""

    async def executar(self, campanha_id: int) -> bool:
        """
        Executa uma campanha.

        Args:
            campanha_id: ID da campanha a executar

        Returns:
            True se executada com sucesso
        """
        logger.info(f"Iniciando execucao da campanha {campanha_id}")

        # 1. Buscar campanha
        campanha = await campanha_repository.buscar_por_id(campanha_id)
        if not campanha:
            logger.error(f"Campanha {campanha_id} nao encontrada")
            return False

        # 2. Validar status
        if campanha.status not in (StatusCampanha.AGENDADA, StatusCampanha.ATIVA):
            logger.warning(
                f"Campanha {campanha_id} tem status {campanha.status.value}, "
                "nao pode ser executada"
            )
            return False

        # 3. Atualizar status para ativa
        await campanha_repository.atualizar_status(campanha_id, StatusCampanha.ATIVA)

        # 4. Buscar destinatarios
        destinatarios = await self._buscar_destinatarios(campanha)
        if not destinatarios:
            logger.warning(f"Campanha {campanha_id} nao tem destinatarios elegiveis")
            await campanha_repository.atualizar_status(campanha_id, StatusCampanha.CONCLUIDA)
            return True

        # 5. Atualizar total de destinatarios
        await campanha_repository.atualizar_total_destinatarios(campanha_id, len(destinatarios))

        # 6. Criar envios
        enviados = 0
        for dest in destinatarios:
            try:
                sucesso = await self._criar_envio(campanha, dest)
                if sucesso:
                    enviados += 1
            except Exception as e:
                logger.error(f"Erro ao criar envio para {dest.get('id')}: {e}")

        # 7. Atualizar contador de enviados
        await campanha_repository.incrementar_enviados(campanha_id, enviados)

        logger.info(f"Campanha {campanha_id}: {enviados}/{len(destinatarios)} envios criados")
        return True

    async def _buscar_destinatarios(self, campanha: CampanhaData) -> List[dict]:
        """
        Busca destinatarios elegiveis para a campanha.

        Args:
            campanha: Dados da campanha

        Returns:
            Lista de destinatarios
        """
        filtros = {}

        if campanha.audience_filters:
            # Mapear filtros para formato do segmentacao_service
            if campanha.audience_filters.especialidades:
                filtros["especialidade"] = campanha.audience_filters.especialidades[0]
            if campanha.audience_filters.regioes:
                filtros["regiao"] = campanha.audience_filters.regioes[0]

        limite = campanha.audience_filters.quantidade_alvo if campanha.audience_filters else 50

        try:
            return await segmentacao_service.buscar_segmento(filtros, limite=limite)
        except Exception as e:
            logger.error(f"Erro ao buscar destinatarios: {e}")
            return []

    async def _criar_envio(self, campanha: CampanhaData, destinatario: dict) -> bool:
        """
        Cria envio para um destinatario.

        Args:
            campanha: Dados da campanha
            destinatario: Dados do destinatario

        Returns:
            True se criado com sucesso
        """
        cliente_id = destinatario.get("id")
        nome = destinatario.get("primeiro_nome", "")

        # Gerar mensagem baseada no tipo
        mensagem = await self._gerar_mensagem(campanha, destinatario)

        if not mensagem:
            logger.warning(f"Nao foi possivel gerar mensagem para {cliente_id}")
            return False

        # Enfileirar
        await fila_service.enfileirar(
            cliente_id=cliente_id,
            conteudo=mensagem,
            tipo="campanha",
            prioridade=3,  # Prioridade baixa para campanhas
            metadata={
                "campanha_id": str(campanha.id),
                "tipo_campanha": campanha.tipo_campanha.value,
            }
        )

        return True

    async def _gerar_mensagem(
        self,
        campanha: CampanhaData,
        destinatario: dict,
    ) -> Optional[str]:
        """
        Gera mensagem para o destinatario baseada no tipo de campanha.

        Args:
            campanha: Dados da campanha
            destinatario: Dados do destinatario

        Returns:
            Mensagem gerada ou None
        """
        cliente_id = destinatario.get("id")
        nome = destinatario.get("primeiro_nome", "")
        especialidade = destinatario.get("especialidade_nome", "medico")

        if campanha.tipo_campanha == TipoCampanha.DISCOVERY:
            # Discovery: usar aberturas dinamicas
            return await obter_abertura_texto(cliente_id, nome)

        elif campanha.tipo_campanha == TipoCampanha.OFERTA:
            # Oferta: usar corpo como template
            if campanha.corpo:
                return self._formatar_template(campanha.corpo, nome, especialidade)
            return None

        elif campanha.tipo_campanha == TipoCampanha.REATIVACAO:
            # Reativacao: usar corpo ou template padrao
            if campanha.corpo:
                return self._formatar_template(campanha.corpo, nome, especialidade)
            return f"Oi Dr {nome}! Tudo bem? Faz tempo que a gente nao se fala..."

        elif campanha.tipo_campanha == TipoCampanha.FOLLOWUP:
            # Followup: usar corpo ou template padrao
            if campanha.corpo:
                return self._formatar_template(campanha.corpo, nome, especialidade)
            return f"Oi Dr {nome}! Lembrei de vc..."

        # Fallback
        if campanha.corpo:
            return self._formatar_template(campanha.corpo, nome, especialidade)

        return None

    def _formatar_template(
        self,
        template: str,
        nome: str,
        especialidade: str,
    ) -> str:
        """
        Formata template com variaveis.

        Args:
            template: Template com placeholders
            nome: Nome do destinatario
            especialidade: Especialidade

        Returns:
            Template formatado
        """
        try:
            # Suportar diferentes formatos de placeholder
            resultado = template
            resultado = resultado.replace("{nome}", nome)
            resultado = resultado.replace("{{nome}}", nome)
            resultado = resultado.replace("{especialidade}", especialidade)
            resultado = resultado.replace("{{especialidade}}", especialidade)
            return resultado
        except Exception as e:
            logger.warning(f"Erro ao formatar template: {e}")
            return template


# Instancia singleton
campanha_executor = CampanhaExecutor()
```

### DoD

- [ ] Arquivo `executor.py` criado
- [ ] Metodo `executar()` implementado
- [ ] Metodo `_buscar_destinatarios()` implementado
- [ ] Metodo `_criar_envio()` implementado
- [ ] Metodo `_gerar_mensagem()` implementado com suporte a todos os tipos
- [ ] Instancia singleton exportada

---

## Story 4.2: Integrar com Job de Campanhas

### Objetivo

Atualizar `app/services/jobs/campanhas.py` para usar o novo executor.

### Tarefas

1. **Atualizar imports** em `app/services/jobs/campanhas.py`:

```python
# ANTES
from app.services.campanha import criar_envios_campanha

# DEPOIS
from app.services.campanhas import campanha_executor, campanha_repository
from app.services.campanhas.types import StatusCampanha
```

2. **Atualizar funcao** `_iniciar_campanha()`:

```python
# ANTES
async def _iniciar_campanha(campanha_id: int) -> bool:
    try:
        await criar_envios_campanha(campanha_id)
        supabase.table("campanhas").update({
            "status": "ativa",
            "iniciada_em": agora
        }).eq("id", campanha_id).execute()
        logger.info(f"Campanha {campanha_id} iniciada")
        return True
    except Exception as e:
        logger.error(f"Erro ao iniciar campanha {campanha_id}: {e}")
        return False

# DEPOIS
async def _iniciar_campanha(campanha_id: int) -> bool:
    """
    Inicia execucao de uma campanha.

    Args:
        campanha_id: ID da campanha

    Returns:
        True se iniciada com sucesso
    """
    try:
        sucesso = await campanha_executor.executar(campanha_id)

        if sucesso:
            logger.info(f"Campanha {campanha_id} executada com sucesso")
        else:
            logger.warning(f"Campanha {campanha_id} executada com problemas")

        return sucesso

    except Exception as e:
        logger.error(f"Erro ao executar campanha {campanha_id}: {e}")
        return False
```

3. **Atualizar funcao** `processar_campanhas_agendadas()` se necessario:

```python
async def processar_campanhas_agendadas():
    """Processa campanhas agendadas para execucao."""
    agora = datetime.utcnow()

    # Usar repository para buscar campanhas
    campanhas = await campanha_repository.listar_agendadas(agora)

    for campanha in campanhas:
        logger.info(f"Processando campanha agendada: {campanha.id}")
        await _iniciar_campanha(campanha.id)
```

### DoD

- [ ] Imports atualizados
- [ ] `_iniciar_campanha()` usa `campanha_executor`
- [ ] `processar_campanhas_agendadas()` usa `campanha_repository`
- [ ] Codigo antigo de `criar_envios_campanha` nao e mais chamado

---

## Story 4.3: Criar Testes do Executor

### Objetivo

Criar testes unitarios para o executor.

### Tarefas

1. **Criar arquivo** `tests/services/campanhas/test_executor.py`:

```python
"""Testes do executor de campanhas."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from app.services.campanhas.executor import CampanhaExecutor
from app.services.campanhas.types import (
    CampanhaData,
    TipoCampanha,
    StatusCampanha,
    AudienceFilters,
)


@pytest.fixture
def executor():
    """Instancia do executor."""
    return CampanhaExecutor()


@pytest.fixture
def campanha_discovery():
    """Campanha discovery de teste."""
    return CampanhaData(
        id=16,
        nome_template="Piloto Discovery",
        tipo_campanha=TipoCampanha.DISCOVERY,
        corpo="[DISCOVERY] Usar aberturas dinamicas",
        status=StatusCampanha.AGENDADA,
        audience_filters=AudienceFilters(quantidade_alvo=2),
    )


@pytest.fixture
def campanha_oferta():
    """Campanha oferta de teste."""
    return CampanhaData(
        id=17,
        nome_template="Oferta Cardio",
        tipo_campanha=TipoCampanha.OFERTA,
        corpo="Oi Dr {nome}! Temos uma vaga de {especialidade} pra vc!",
        status=StatusCampanha.AGENDADA,
        audience_filters=AudienceFilters(especialidades=["cardiologia"]),
    )


@pytest.fixture
def destinatarios():
    """Lista de destinatarios de teste."""
    return [
        {"id": "uuid-1", "primeiro_nome": "Carlos", "especialidade_nome": "Cardiologia"},
        {"id": "uuid-2", "primeiro_nome": "Maria", "especialidade_nome": "Anestesiologia"},
    ]


@pytest.mark.asyncio
async def test_executar_campanha_discovery(executor, campanha_discovery, destinatarios):
    """Testa execucao de campanha discovery."""
    with patch("app.services.campanhas.executor.campanha_repository") as mock_repo, \
         patch("app.services.campanhas.executor.segmentacao_service") as mock_seg, \
         patch("app.services.campanhas.executor.fila_service") as mock_fila, \
         patch("app.services.campanhas.executor.obter_abertura_texto") as mock_abertura:

        # Setup mocks
        mock_repo.buscar_por_id = AsyncMock(return_value=campanha_discovery)
        mock_repo.atualizar_status = AsyncMock(return_value=True)
        mock_repo.atualizar_total_destinatarios = AsyncMock(return_value=True)
        mock_repo.incrementar_enviados = AsyncMock(return_value=True)
        mock_seg.buscar_segmento = AsyncMock(return_value=destinatarios)
        mock_fila.enfileirar = AsyncMock()
        mock_abertura.return_value = "Oi Dr Carlos! Tudo bem?"

        # Executar
        result = await executor.executar(16)

        # Verificar
        assert result is True
        assert mock_abertura.call_count == 2  # Uma vez por destinatario
        assert mock_fila.enfileirar.call_count == 2


@pytest.mark.asyncio
async def test_executar_campanha_oferta_com_template(executor, campanha_oferta, destinatarios):
    """Testa execucao de campanha oferta com template."""
    with patch("app.services.campanhas.executor.campanha_repository") as mock_repo, \
         patch("app.services.campanhas.executor.segmentacao_service") as mock_seg, \
         patch("app.services.campanhas.executor.fila_service") as mock_fila:

        # Setup mocks
        mock_repo.buscar_por_id = AsyncMock(return_value=campanha_oferta)
        mock_repo.atualizar_status = AsyncMock(return_value=True)
        mock_repo.atualizar_total_destinatarios = AsyncMock(return_value=True)
        mock_repo.incrementar_enviados = AsyncMock(return_value=True)
        mock_seg.buscar_segmento = AsyncMock(return_value=destinatarios)
        mock_fila.enfileirar = AsyncMock()

        # Executar
        result = await executor.executar(17)

        # Verificar
        assert result is True
        # Verificar que template foi formatado
        call_args = mock_fila.enfileirar.call_args_list[0]
        assert "Carlos" in call_args.kwargs["conteudo"]
        assert "Cardiologia" in call_args.kwargs["conteudo"]


@pytest.mark.asyncio
async def test_gerar_mensagem_discovery(executor, campanha_discovery):
    """Testa geracao de mensagem para discovery."""
    destinatario = {"id": "uuid-1", "primeiro_nome": "Carlos"}

    with patch("app.services.campanhas.executor.obter_abertura_texto") as mock_abertura:
        mock_abertura.return_value = "Oi Dr Carlos! Sou a Julia da Revoluna"

        mensagem = await executor._gerar_mensagem(campanha_discovery, destinatario)

        assert mensagem == "Oi Dr Carlos! Sou a Julia da Revoluna"
        mock_abertura.assert_called_once_with("uuid-1", "Carlos")


@pytest.mark.asyncio
async def test_gerar_mensagem_oferta(executor, campanha_oferta):
    """Testa geracao de mensagem para oferta."""
    destinatario = {"id": "uuid-1", "primeiro_nome": "Carlos", "especialidade_nome": "Cardio"}

    mensagem = await executor._gerar_mensagem(campanha_oferta, destinatario)

    assert "Carlos" in mensagem
    assert "Cardio" in mensagem


def test_formatar_template(executor):
    """Testa formatacao de template."""
    template = "Oi Dr {nome}! Voce e {especialidade}?"

    resultado = executor._formatar_template(template, "Carlos", "cardiologista")

    assert resultado == "Oi Dr Carlos! Voce e cardiologista?"


def test_formatar_template_chaves_duplas(executor):
    """Testa formatacao de template com chaves duplas."""
    template = "Oi Dr {{nome}}!"

    resultado = executor._formatar_template(template, "Maria", "")

    assert resultado == "Oi Dr Maria!"
```

2. **Rodar testes**:

```bash
uv run pytest tests/services/campanhas/test_executor.py -v
```

### DoD

- [ ] Testes criados
- [ ] Teste `test_executar_campanha_discovery` passa
- [ ] Teste `test_executar_campanha_oferta_com_template` passa
- [ ] Teste `test_gerar_mensagem_discovery` passa
- [ ] Teste `test_gerar_mensagem_oferta` passa
- [ ] Teste `test_formatar_template` passa

---

## Checklist do Epico

- [ ] **S35.E04.1** - Executor criado
- [ ] **S35.E04.2** - Job de campanhas atualizado
- [ ] **S35.E04.3** - Testes passando

### Arquivos Criados/Modificados

- `app/services/campanhas/executor.py` (NOVO)
- `app/services/jobs/campanhas.py` (MODIFICADO)
- `tests/services/campanhas/test_executor.py` (NOVO)

---

## Tempo Estimado

| Story | Tempo |
|-------|-------|
| 4.1 Executor base | 2h |
| 4.2 Integracao com job | 1h |
| 4.3 Testes | 1h |
| **Total** | **4h** |
