# E04: Job checkNumberStatus

**Fase:** 1 - Foundation
**Estimativa:** 4h
**Prioridade:** Alta
**Dependências:** Nenhuma

---

## Objetivo

Implementar job contínuo que valida números de telefone via Evolution API antes de Julia tentar enviar mensagens, evitando desperdício de mensagens em números inválidos.

## Problema Atual

- 28k médicos não-enriquecidos no banco
- Muitos podem ter número inválido (WhatsApp não existe)
- Enviar mensagem para número inválido = desperdício
- Sem validação prévia, Julia descobre que número é inválido só na hora do envio

---

## Solução

Usar `checkNumberStatus` da Evolution API como job contínuo de pré-validação.

```
FLUXO:
1. Médico entra no banco (só telefone)
2. status_telefone = "pendente"
3. Job contínuo valida via checkNumberStatus
4. Se válido → status_telefone = "validado"
5. Se inválido → status_telefone = "invalido"
6. Julia só contata médicos com status_telefone = "validado"
```

---

## Tarefas

### T1: Adicionar coluna status_telefone na tabela clientes (30min)

**Migration:** `add_status_telefone_to_clientes`

```sql
-- Migration: add_status_telefone_to_clientes
-- Sprint 32 E04: Validação de telefone via checkNumberStatus

-- Adicionar coluna status_telefone
ALTER TABLE clientes
ADD COLUMN IF NOT EXISTS status_telefone TEXT DEFAULT 'pendente';

-- Adicionar coluna para timestamp da última validação
ALTER TABLE clientes
ADD COLUMN IF NOT EXISTS telefone_validado_em TIMESTAMPTZ;

-- Adicionar coluna para erro (se inválido)
ALTER TABLE clientes
ADD COLUMN IF NOT EXISTS telefone_erro TEXT;

-- Criar índice para buscar pendentes
CREATE INDEX IF NOT EXISTS idx_clientes_status_telefone
ON clientes (status_telefone)
WHERE status_telefone = 'pendente';

-- Criar índice para buscar validados
CREATE INDEX IF NOT EXISTS idx_clientes_telefone_validado
ON clientes (status_telefone)
WHERE status_telefone = 'validado';

-- Constraint para valores válidos
ALTER TABLE clientes
ADD CONSTRAINT chk_status_telefone
CHECK (status_telefone IN ('pendente', 'validando', 'validado', 'invalido', 'erro'));

-- Comentário na coluna
COMMENT ON COLUMN clientes.status_telefone IS 'Status da validação do telefone: pendente, validando, validado, invalido, erro';
```

**Estados possíveis:**
| Estado | Significado |
|--------|-------------|
| `pendente` | Ainda não validado |
| `validando` | Em processo de validação (evita duplicata) |
| `validado` | WhatsApp existe e está ativo |
| `invalido` | WhatsApp não existe neste número |
| `erro` | Erro na validação (tentar novamente) |

### T2: Implementar chamada checkNumberStatus no cliente Evolution (45min)

**Arquivo:** `app/services/whatsapp.py`

**Adicionar método:**

```python
async def check_number_status(self, phone: str) -> dict:
    """
    Verifica se número tem WhatsApp via Evolution API.

    Args:
        phone: Número no formato 5511999999999 (sem +)

    Returns:
        {
            "exists": True/False,
            "jid": "5511999999999@s.whatsapp.net" (se existe),
            "error": "mensagem" (se erro)
        }

    Docs Evolution API:
        POST /chat/whatsappNumbers/{instance}
        Body: {"numbers": ["5511999999999"]}
    """
    try:
        # Normalizar número (remover +, espaços, etc.)
        numero_limpo = "".join(filter(str.isdigit, phone))

        # Garantir que tem código do país
        if not numero_limpo.startswith("55"):
            numero_limpo = f"55{numero_limpo}"

        url = f"{self.base_url}/chat/whatsappNumbers/{self.instance}"

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                url,
                headers={"apikey": self.api_key},
                json={"numbers": [numero_limpo]}
            )

            if response.status_code != 200:
                logger.warning(f"checkNumberStatus erro HTTP: {response.status_code}")
                return {"exists": False, "error": f"HTTP {response.status_code}"}

            data = response.json()

            # Resposta da Evolution API:
            # [{"exists": true, "jid": "5511999999999@s.whatsapp.net", "number": "5511999999999"}]
            if data and len(data) > 0:
                resultado = data[0]
                return {
                    "exists": resultado.get("exists", False),
                    "jid": resultado.get("jid"),
                    "number": resultado.get("number"),
                }

            return {"exists": False, "error": "Resposta vazia"}

    except httpx.TimeoutException:
        logger.warning(f"checkNumberStatus timeout para {phone}")
        return {"exists": False, "error": "timeout"}

    except Exception as e:
        logger.error(f"checkNumberStatus erro: {e}")
        return {"exists": False, "error": str(e)}
```

### T3: Criar serviço de validação de telefones (45min)

**Arquivo:** `app/services/validacao_telefone.py`

```python
"""
Serviço de validação de telefones via Evolution API.

Sprint 32 E04 - Validação prévia evita desperdício de mensagens.
"""
import logging
from datetime import datetime, timezone
from typing import Optional

from app.services.supabase import supabase
from app.services.whatsapp import evolution

logger = logging.getLogger(__name__)


async def buscar_telefones_pendentes(limit: int = 100) -> list[dict]:
    """
    Busca médicos com telefone pendente de validação.

    Args:
        limit: Máximo de registros a retornar

    Returns:
        Lista de dicts com id e telefone
    """
    response = (
        supabase.table("clientes")
        .select("id, telefone, nome")
        .eq("status_telefone", "pendente")
        .not_.is_("telefone", "null")
        .limit(limit)
        .execute()
    )

    return response.data or []


async def marcar_como_validando(cliente_id: str) -> bool:
    """
    Marca cliente como 'validando' para evitar processamento duplicado.

    Args:
        cliente_id: ID do cliente

    Returns:
        True se marcou, False se já estava em outro estado
    """
    try:
        response = (
            supabase.table("clientes")
            .update({"status_telefone": "validando"})
            .eq("id", cliente_id)
            .eq("status_telefone", "pendente")  # Só atualiza se ainda pendente
            .execute()
        )

        # Se não atualizou nenhum registro, já estava em outro estado
        return len(response.data or []) > 0

    except Exception as e:
        logger.error(f"Erro ao marcar como validando: {e}")
        return False


async def atualizar_status_telefone(
    cliente_id: str,
    status: str,
    erro: Optional[str] = None
) -> bool:
    """
    Atualiza status do telefone após validação.

    Args:
        cliente_id: ID do cliente
        status: validado | invalido | erro
        erro: Mensagem de erro (se aplicável)

    Returns:
        True se atualizou
    """
    try:
        dados = {
            "status_telefone": status,
            "telefone_validado_em": datetime.now(timezone.utc).isoformat(),
        }

        if erro:
            dados["telefone_erro"] = erro[:500]  # Limitar tamanho

        response = (
            supabase.table("clientes")
            .update(dados)
            .eq("id", cliente_id)
            .execute()
        )

        return len(response.data or []) > 0

    except Exception as e:
        logger.error(f"Erro ao atualizar status telefone: {e}")
        return False


async def validar_telefone(cliente_id: str, telefone: str) -> str:
    """
    Valida um telefone específico via Evolution API.

    Args:
        cliente_id: ID do cliente
        telefone: Número a validar

    Returns:
        Status final: validado | invalido | erro
    """
    # Marcar como validando
    if not await marcar_como_validando(cliente_id):
        logger.debug(f"Cliente {cliente_id} já em processamento")
        return "skip"

    try:
        # Chamar Evolution API
        resultado = await evolution.check_number_status(telefone)

        if resultado.get("exists"):
            await atualizar_status_telefone(cliente_id, "validado")
            logger.debug(f"Telefone {telefone} validado - WhatsApp existe")
            return "validado"

        elif resultado.get("error"):
            # Erro de API - tentar novamente depois
            await atualizar_status_telefone(
                cliente_id,
                "erro",
                erro=resultado.get("error")
            )
            logger.warning(f"Erro ao validar {telefone}: {resultado.get('error')}")
            return "erro"

        else:
            # WhatsApp não existe
            await atualizar_status_telefone(cliente_id, "invalido")
            logger.debug(f"Telefone {telefone} inválido - WhatsApp não existe")
            return "invalido"

    except Exception as e:
        await atualizar_status_telefone(cliente_id, "erro", erro=str(e))
        logger.error(f"Exceção ao validar {telefone}: {e}")
        return "erro"


async def processar_lote_validacao(limit: int = 50) -> dict:
    """
    Processa um lote de telefones pendentes.

    Args:
        limit: Máximo de telefones a processar

    Returns:
        Dict com estatísticas do processamento
    """
    stats = {
        "processados": 0,
        "validados": 0,
        "invalidos": 0,
        "erros": 0,
        "skips": 0,
    }

    pendentes = await buscar_telefones_pendentes(limit)

    if not pendentes:
        logger.debug("Nenhum telefone pendente para validar")
        return stats

    logger.info(f"Processando {len(pendentes)} telefones pendentes")

    for cliente in pendentes:
        resultado = await validar_telefone(
            cliente["id"],
            cliente["telefone"]
        )

        stats["processados"] += 1

        if resultado == "validado":
            stats["validados"] += 1
        elif resultado == "invalido":
            stats["invalidos"] += 1
        elif resultado == "erro":
            stats["erros"] += 1
        elif resultado == "skip":
            stats["skips"] += 1

    logger.info(
        f"Validação concluída: {stats['validados']} válidos, "
        f"{stats['invalidos']} inválidos, {stats['erros']} erros"
    )

    return stats


async def obter_estatisticas_validacao() -> dict:
    """
    Retorna estatísticas de validação de telefones.

    Returns:
        Dict com contagens por status
    """
    try:
        # Query agregada por status
        response = supabase.rpc(
            "count_by_status_telefone"
        ).execute()

        if response.data:
            return response.data

        # Fallback: queries separadas
        stats = {}
        for status in ["pendente", "validando", "validado", "invalido", "erro"]:
            count = (
                supabase.table("clientes")
                .select("id", count="exact")
                .eq("status_telefone", status)
                .execute()
            )
            stats[status] = count.count or 0

        return stats

    except Exception as e:
        logger.error(f"Erro ao obter estatísticas: {e}")
        return {}
```

### T4: Criar job no scheduler (45min)

**Arquivo:** `app/workers/scheduler.py`

**Adicionar job:**

```python
from app.services.validacao_telefone import processar_lote_validacao

async def job_validar_telefones():
    """
    Job de validação de telefones via checkNumberStatus.

    Roda a cada 5 minutos durante horário comercial.
    Processa 50 números por execução.

    Sprint 32 E04.
    """
    # Verificar horário comercial
    from datetime import datetime
    hora_atual = datetime.now().hour

    if hora_atual < 8 or hora_atual >= 20:
        logger.debug("Fora do horário comercial - pulando validação")
        return {"status": "skipped", "reason": "fora_horario"}

    try:
        stats = await processar_lote_validacao(limit=50)

        return {
            "status": "success",
            "stats": stats,
        }

    except Exception as e:
        logger.error(f"Erro no job de validação: {e}")
        return {
            "status": "error",
            "error": str(e),
        }


# Adicionar ao agendamento (cron)
JOBS = [
    # ... jobs existentes ...

    # Validação de telefones (Sprint 32 E04)
    # A cada 5 minutos, das 8h às 20h
    {
        "name": "validar_telefones",
        "function": job_validar_telefones,
        "cron": "*/5 8-19 * * *",  # A cada 5 min, das 8h às 19:59
        "description": "Valida telefones via checkNumberStatus",
    },
]
```

### T5: Criar endpoint de status (30min)

**Arquivo:** `app/api/routes/health.py`

**Adicionar:**

```python
from app.services.validacao_telefone import obter_estatisticas_validacao

@router.get("/health/telefones")
async def telefones_status():
    """
    Retorna estatísticas de validação de telefones.

    Útil para monitorar:
    - Quantos pendentes (backlog)
    - Taxa de válidos vs inválidos
    - Erros de validação
    """
    stats = await obter_estatisticas_validacao()

    total = sum(stats.values()) if stats else 0
    validados = stats.get("validado", 0)
    invalidos = stats.get("invalido", 0)

    taxa_validos = round(validados / total * 100, 2) if total > 0 else 0
    taxa_invalidos = round(invalidos / total * 100, 2) if total > 0 else 0

    return {
        "stats": stats,
        "total": total,
        "taxa_validos_pct": taxa_validos,
        "taxa_invalidos_pct": taxa_invalidos,
        "timestamp": datetime.utcnow().isoformat(),
    }
```

### T6: Criar RPC para contagem (20min)

**Migration:** `create_count_by_status_telefone_rpc`

```sql
-- Migration: create_count_by_status_telefone_rpc
-- Sprint 32 E04: Função para contar clientes por status_telefone

CREATE OR REPLACE FUNCTION count_by_status_telefone()
RETURNS TABLE (
    status TEXT,
    count BIGINT
)
LANGUAGE sql
STABLE
AS $$
    SELECT
        status_telefone as status,
        COUNT(*) as count
    FROM clientes
    WHERE status_telefone IS NOT NULL
    GROUP BY status_telefone
    ORDER BY count DESC;
$$;

COMMENT ON FUNCTION count_by_status_telefone() IS 'Conta clientes agrupados por status_telefone para estatísticas';
```

### T7: Atualizar filtros de campanha (30min)

**Arquivo:** `app/services/campanhas.py` (ou equivalente)

**Modificar filtros para só incluir telefones validados:**

```python
async def buscar_medicos_para_campanha(
    filtros: dict,
    limit: int = 100
) -> list[dict]:
    """
    Busca médicos elegíveis para uma campanha.

    IMPORTANTE: Só retorna médicos com telefone validado.
    """
    query = supabase.table("clientes").select("*")

    # CRÍTICO: Só telefones validados
    query = query.eq("status_telefone", "validado")

    # Aplicar outros filtros...
    if filtros.get("especialidade"):
        query = query.eq("especialidade", filtros["especialidade"])

    if filtros.get("opt_out") is False:
        query = query.eq("opt_out", False)

    # ...

    response = query.limit(limit).execute()
    return response.data or []
```

### T8: Criar testes (45min)

**Arquivo:** `tests/unit/test_validacao_telefone.py`

```python
import pytest
from unittest.mock import patch, AsyncMock
from app.services.validacao_telefone import (
    validar_telefone,
    processar_lote_validacao,
    buscar_telefones_pendentes,
)


class TestValidacaoTelefone:
    """Testes para serviço de validação de telefone."""

    @pytest.mark.asyncio
    async def test_validar_telefone_existe(self):
        """Deve marcar como validado quando WhatsApp existe."""
        with patch("app.services.validacao_telefone.evolution") as mock_evolution:
            mock_evolution.check_number_status = AsyncMock(
                return_value={"exists": True, "jid": "5511999999999@s.whatsapp.net"}
            )

            with patch("app.services.validacao_telefone.marcar_como_validando") as mock_marcar:
                mock_marcar.return_value = True

                with patch("app.services.validacao_telefone.atualizar_status_telefone") as mock_atualizar:
                    mock_atualizar.return_value = True

                    resultado = await validar_telefone("uuid-123", "5511999999999")

                    assert resultado == "validado"
                    mock_atualizar.assert_called_with("uuid-123", "validado")

    @pytest.mark.asyncio
    async def test_validar_telefone_nao_existe(self):
        """Deve marcar como inválido quando WhatsApp não existe."""
        with patch("app.services.validacao_telefone.evolution") as mock_evolution:
            mock_evolution.check_number_status = AsyncMock(
                return_value={"exists": False}
            )

            with patch("app.services.validacao_telefone.marcar_como_validando") as mock_marcar:
                mock_marcar.return_value = True

                with patch("app.services.validacao_telefone.atualizar_status_telefone") as mock_atualizar:
                    mock_atualizar.return_value = True

                    resultado = await validar_telefone("uuid-123", "5511999999999")

                    assert resultado == "invalido"
                    mock_atualizar.assert_called_with("uuid-123", "invalido")

    @pytest.mark.asyncio
    async def test_validar_telefone_erro_api(self):
        """Deve marcar como erro quando API falha."""
        with patch("app.services.validacao_telefone.evolution") as mock_evolution:
            mock_evolution.check_number_status = AsyncMock(
                return_value={"exists": False, "error": "timeout"}
            )

            with patch("app.services.validacao_telefone.marcar_como_validando") as mock_marcar:
                mock_marcar.return_value = True

                with patch("app.services.validacao_telefone.atualizar_status_telefone") as mock_atualizar:
                    mock_atualizar.return_value = True

                    resultado = await validar_telefone("uuid-123", "5511999999999")

                    assert resultado == "erro"

    @pytest.mark.asyncio
    async def test_skip_se_ja_validando(self):
        """Deve pular se cliente já está sendo validado."""
        with patch("app.services.validacao_telefone.marcar_como_validando") as mock_marcar:
            mock_marcar.return_value = False  # Já em outro estado

            resultado = await validar_telefone("uuid-123", "5511999999999")

            assert resultado == "skip"


class TestProcessarLote:
    """Testes para processamento em lote."""

    @pytest.mark.asyncio
    async def test_processar_lote_vazio(self):
        """Deve retornar stats zeradas se não há pendentes."""
        with patch("app.services.validacao_telefone.buscar_telefones_pendentes") as mock_buscar:
            mock_buscar.return_value = []

            stats = await processar_lote_validacao()

            assert stats["processados"] == 0
            assert stats["validados"] == 0

    @pytest.mark.asyncio
    async def test_processar_lote_com_pendentes(self):
        """Deve processar todos os pendentes do lote."""
        with patch("app.services.validacao_telefone.buscar_telefones_pendentes") as mock_buscar:
            mock_buscar.return_value = [
                {"id": "1", "telefone": "5511111111111"},
                {"id": "2", "telefone": "5522222222222"},
            ]

            with patch("app.services.validacao_telefone.validar_telefone") as mock_validar:
                mock_validar.side_effect = ["validado", "invalido"]

                stats = await processar_lote_validacao()

                assert stats["processados"] == 2
                assert stats["validados"] == 1
                assert stats["invalidos"] == 1
```

---

## Definition of Done (DoD)

### Critérios Obrigatórios

- [ ] **Migration aplicada**
  - [ ] Coluna `status_telefone` existe em `clientes`
  - [ ] Coluna `telefone_validado_em` existe
  - [ ] Coluna `telefone_erro` existe
  - [ ] Índices criados
  - [ ] Constraint de valores válidos funciona

- [ ] **Método checkNumberStatus funciona**
  - [ ] `evolution.check_number_status()` implementado
  - [ ] Retorna `{"exists": True}` para números válidos
  - [ ] Retorna `{"exists": False}` para números inválidos
  - [ ] Trata timeout e erros

- [ ] **Serviço de validação funciona**
  - [ ] `buscar_telefones_pendentes()` retorna lista
  - [ ] `validar_telefone()` atualiza status corretamente
  - [ ] `processar_lote_validacao()` processa múltiplos

- [ ] **Job agendado**
  - [ ] Job roda a cada 5 minutos
  - [ ] Só roda em horário comercial (8h-20h)
  - [ ] Processa 50 números por execução

- [ ] **Endpoint de status**
  - [ ] `GET /health/telefones` retorna estatísticas
  - [ ] Mostra taxa de válidos/inválidos

- [ ] **Filtros atualizados**
  - [ ] Campanhas só incluem `status_telefone = 'validado'`

- [ ] **Testes passando**
  - [ ] `uv run pytest tests/unit/test_validacao_telefone.py -v` = OK

### Verificação Manual

```bash
# 1. Verificar coluna existe
curl -X POST "https://[supabase-url]/rest/v1/rpc/count_by_status_telefone" \
  -H "apikey: [key]" \
  -H "Authorization: Bearer [key]"

# 2. Testar checkNumberStatus manualmente
curl -X POST "http://[evolution-url]/chat/whatsappNumbers/[instance]" \
  -H "apikey: [key]" \
  -H "Content-Type: application/json" \
  -d '{"numbers": ["5511999999999"]}'

# 3. Verificar endpoint de status
curl http://localhost:8000/health/telefones
```

---

## Notas para o Desenvolvedor

1. **Rate limiting da Evolution API:**
   - Não bombardear com muitas requests
   - 50 números por ciclo de 5 min = 600/hora = ~14k/dia
   - Suficiente para limpar backlog aos poucos

2. **Estado "validando":**
   - Evita que dois workers processem o mesmo número
   - Se ficar travado em "validando", job de limpeza deve resetar

3. **Horário comercial:**
   - Job só roda das 8h às 20h
   - Evita chamar Evolution API fora do horário

4. **Ordem de prioridade:**
   - Validar números mais recentes primeiro? Ou mais antigos?
   - Considerar adicionar ORDER BY created_at na busca

5. **Monitoramento:**
   - Alertar se taxa de inválidos > 50%
   - Alertar se muitos erros de API
