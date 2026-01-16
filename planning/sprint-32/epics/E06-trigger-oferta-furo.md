# E06: Trigger de Oferta por Furo de Escala

**Fase:** 2 - Julia Autônoma
**Estimativa:** 4h
**Prioridade:** Alta
**Dependências:** E05 (Gatilhos Automáticos)

---

## Objetivo

Implementar gatilho automático que detecta vagas sem médico confirmado próximas da data (< 20 dias) e cria ofertas direcionadas para médicos compatíveis.

## Cenário

```
1. Vaga no Hospital São Luiz dia 05/02 (daqui 15 dias)
2. Ainda não tem médico confirmado
3. Julia detecta automaticamente
4. Busca médicos compatíveis (cardiologia, região SP)
5. Cria oferta direcionada para os top 5
```

---

## Tarefas

### T1: Criar função de detecção de vagas urgentes (45min)

**Arquivo:** `app/services/gatilhos/oferta.py`

```python
"""
Gatilho de Oferta automática por furo de escala.

Detecta vagas sem médico confirmado próximas da data.
"""
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from app.services.supabase import supabase
from app.services.gatilhos.base import criar_gatilho
from app.workers.pilot_mode import skip_if_pilot, AutonomousFeature

logger = logging.getLogger(__name__)

# Threshold: vagas com menos de X dias são consideradas urgentes
THRESHOLD_DIAS_URGENTE = 20


async def buscar_vagas_urgentes(limit: int = 50) -> list[dict]:
    """
    Busca vagas urgentes sem médico confirmado.

    Critérios:
    - Data da vaga < 20 dias a partir de hoje
    - status = 'aberta' (sem médico)
    - Hospital não bloqueado (vagas bloqueadas não aparecem)

    Returns:
        Lista de vagas urgentes ordenadas por data (mais urgente primeiro)
    """
    data_limite = (
        datetime.now(timezone.utc) + timedelta(days=THRESHOLD_DIAS_URGENTE)
    ).date().isoformat()

    response = (
        supabase.table("vagas")
        .select(
            "id, hospital_id, especialidade, data_plantao, turno, valor, "
            "hospitais(nome, regiao)"
        )
        .eq("status", "aberta")
        .lte("data_plantao", data_limite)
        .gte("data_plantao", datetime.now(timezone.utc).date().isoformat())
        .order("data_plantao", desc=False)
        .limit(limit)
        .execute()
    )

    vagas = response.data or []

    if vagas:
        logger.info(f"Encontradas {len(vagas)} vagas urgentes (< {THRESHOLD_DIAS_URGENTE} dias)")

    return vagas


async def calcular_urgencia(vaga: dict) -> int:
    """
    Calcula score de urgência da vaga.

    Quanto mais próxima a data, maior a urgência (maior prioridade).

    Returns:
        Score de 0-100 (100 = amanhã)
    """
    data_plantao = datetime.fromisoformat(vaga["data_plantao"]).date()
    hoje = datetime.now(timezone.utc).date()

    dias_restantes = (data_plantao - hoje).days

    if dias_restantes <= 0:
        return 100  # Máxima urgência (hoje ou atrasado)
    elif dias_restantes <= 3:
        return 90
    elif dias_restantes <= 7:
        return 70
    elif dias_restantes <= 14:
        return 50
    else:
        return 30


async def buscar_medicos_compativeis(
    vaga: dict,
    limit: int = 10
) -> list[dict]:
    """
    Busca médicos compatíveis com a vaga.

    Critérios:
    - Mesma especialidade da vaga
    - Região compatível (se especificado)
    - Telefone validado
    - Não está em opt-out
    - Não recebeu oferta para esta vaga ainda

    Args:
        vaga: Dados da vaga
        limit: Máximo de médicos a retornar

    Returns:
        Lista de médicos compatíveis
    """
    query = (
        supabase.table("clientes")
        .select("id, nome, telefone, especialidade, regiao, score_engajamento")
        .eq("status_telefone", "validado")
        .eq("opt_out", False)
    )

    # Filtrar por especialidade
    if vaga.get("especialidade"):
        query = query.eq("especialidade", vaga["especialidade"])

    # Filtrar por região (se disponível)
    hospital_info = vaga.get("hospitais")
    if hospital_info and hospital_info.get("regiao"):
        # Pode ser mais flexível no futuro (regiões adjacentes)
        query = query.eq("regiao", hospital_info["regiao"])

    # Ordenar por score de engajamento (médicos que mais respondem primeiro)
    query = query.order("score_engajamento", desc=True)

    response = query.limit(limit * 2).execute()  # Busca mais para filtrar

    medicos = response.data or []

    if not medicos:
        logger.debug(f"Nenhum médico compatível para vaga {vaga['id']}")
        return []

    # Filtrar médicos que já receberam oferta para esta vaga
    medicos_ids = [m["id"] for m in medicos]
    ofertas_existentes = (
        supabase.table("gatilhos_automaticos")
        .select("cliente_id")
        .eq("tipo", "oferta")
        .eq("vaga_id", vaga["id"])
        .in_("cliente_id", medicos_ids)
        .execute()
    )

    ids_com_oferta = {o["cliente_id"] for o in (ofertas_existentes.data or [])}

    # Filtrar e limitar
    medicos_filtrados = [m for m in medicos if m["id"] not in ids_com_oferta][:limit]

    logger.debug(f"Vaga {vaga['id']}: {len(medicos_filtrados)} médicos compatíveis")

    return medicos_filtrados


@skip_if_pilot(AutonomousFeature.OFERTA)
async def executar_deteccao_oferta() -> dict:
    """
    Detecta vagas urgentes e cria gatilhos de oferta.

    Fluxo:
    1. Busca vagas urgentes (< 20 dias)
    2. Para cada vaga, busca médicos compatíveis
    3. Cria gatilho de oferta para cada par (vaga, médico)
    """
    stats = {
        "vagas_analisadas": 0,
        "gatilhos_criados": 0,
        "medicos_alcancados": 0,
    }

    vagas = await buscar_vagas_urgentes(limit=20)
    stats["vagas_analisadas"] = len(vagas)

    if not vagas:
        return stats

    for vaga in vagas:
        urgencia = await calcular_urgencia(vaga)
        medicos = await buscar_medicos_compativeis(vaga, limit=5)

        for medico in medicos:
            gatilho_id = await criar_gatilho(
                tipo="oferta",
                cliente_id=medico["id"],
                vaga_id=vaga["id"],
                prioridade=urgencia,  # Vagas mais urgentes têm maior prioridade
                dados={
                    "vaga_especialidade": vaga.get("especialidade"),
                    "vaga_data": vaga.get("data_plantao"),
                    "vaga_valor": vaga.get("valor"),
                    "hospital_nome": vaga.get("hospitais", {}).get("nome"),
                    "medico_nome": medico.get("nome"),
                },
            )

            if gatilho_id:
                stats["gatilhos_criados"] += 1

        stats["medicos_alcancados"] += len(medicos)

    logger.info(
        f"Oferta: {stats['vagas_analisadas']} vagas, "
        f"{stats['gatilhos_criados']} gatilhos criados"
    )

    return stats
```

### T2: Implementar handler de execução do gatilho (45min)

**Arquivo:** `app/services/gatilhos/oferta.py` (continuação)

```python
from app.services.gatilhos.base import (
    GatilhoBase,
    marcar_gatilho_executado,
    marcar_gatilho_erro,
)


class GatilhoOferta(GatilhoBase):
    """
    Gatilho para Oferta automática por furo de escala.

    Condição: Vaga sem médico < 20 dias.
    Ação: Criar campanha de oferta direcionada.
    """

    tipo = "oferta"
    feature = AutonomousFeature.OFERTA

    async def detectar(self) -> list[dict]:
        """Detecção é feita por executar_deteccao_oferta()."""
        return []

    async def executar(self, gatilho: dict) -> bool:
        """
        Executa gatilho de Oferta.

        Cria campanha de oferta para o médico específico
        com escopo da vaga específica.
        """
        cliente_id = gatilho.get("cliente_id")
        vaga_id = gatilho.get("vaga_id")
        dados = gatilho.get("dados", {})

        if not cliente_id or not vaga_id:
            await marcar_gatilho_erro(gatilho["id"], "cliente_id ou vaga_id ausente")
            return False

        try:
            # Verificar se vaga ainda está aberta
            vaga = (
                supabase.table("vagas")
                .select("id, status, data_plantao, valor, especialidade")
                .eq("id", vaga_id)
                .single()
                .execute()
            )

            if not vaga.data or vaga.data.get("status") != "aberta":
                await marcar_gatilho_executado(gatilho["id"])  # Vaga já preenchida
                logger.info(f"Vaga {vaga_id} já não está aberta - gatilho cancelado")
                return True

            # Criar campanha de oferta
            campanha_data = {
                "nome": f"Oferta Auto - {dados.get('hospital_nome')} {dados.get('vaga_data')}",
                "tipo": "oferta",
                "objetivo": f"Oferecer vaga de {dados.get('vaga_especialidade')} no {dados.get('hospital_nome')}",
                "status": "ativa",
                "escopo_vagas": {
                    "vaga_id": vaga_id,
                },
                "filtros_medicos": {
                    "cliente_id": cliente_id,
                },
            }

            response = supabase.table("campanhas").insert(campanha_data).execute()

            if response.data:
                campanha = response.data[0]

                # Enfileirar mensagem
                supabase.table("fila_mensagens").insert({
                    "cliente_id": cliente_id,
                    "campaign_id": campanha["id"],
                    "send_type": "oferta",
                    "queue_status": "queued",
                    "metadata": {
                        "vaga_id": vaga_id,
                        "auto_generated": True,
                    },
                }).execute()

                await marcar_gatilho_executado(gatilho["id"], campanha["id"])
                logger.info(
                    f"Oferta criada: {dados.get('medico_nome')} ← "
                    f"{dados.get('hospital_nome')} {dados.get('vaga_data')}"
                )
                return True

            await marcar_gatilho_erro(gatilho["id"], "Falha ao criar campanha")
            return False

        except Exception as e:
            await marcar_gatilho_erro(gatilho["id"], str(e))
            logger.error(f"Erro ao executar Oferta: {e}")
            return False
```

### T3: Adicionar ao mapeamento de handlers (15min)

**Arquivo:** `app/workers/gatilhos_worker.py`

**Modificar:**

```python
from app.services.gatilhos.oferta import GatilhoOferta

GATILHO_HANDLERS = {
    "discovery": GatilhoDiscovery(),
    "reativacao": GatilhoReativacao(),
    "oferta": GatilhoOferta(),  # ADICIONAR
}
```

### T4: Adicionar detecção de oferta ao ciclo (15min)

**Arquivo:** `app/workers/gatilhos_worker.py`

**Modificar `executar_ciclo_gatilhos()`:**

```python
from app.services.gatilhos.oferta import executar_deteccao_oferta

async def executar_ciclo_gatilhos():
    # ... código existente ...

    # Adicionar detecção de oferta
    try:
        deteccoes["oferta"] = await executar_deteccao_oferta()
    except Exception as e:
        logger.error(f"Erro na detecção de Oferta: {e}")

    # ... resto do código ...
```

### T5: Criar testes (45min)

**Arquivo:** `tests/unit/test_gatilho_oferta.py`

```python
import pytest
from unittest.mock import patch, AsyncMock
from datetime import datetime, timedelta
from app.services.gatilhos.oferta import (
    buscar_vagas_urgentes,
    buscar_medicos_compativeis,
    calcular_urgencia,
    executar_deteccao_oferta,
)


class TestBuscarVagasUrgentes:
    """Testes para busca de vagas urgentes."""

    @pytest.mark.asyncio
    async def test_retorna_vagas_proximas(self):
        """Deve retornar vagas com data < 20 dias."""
        with patch("app.services.gatilhos.oferta.supabase") as mock_supabase:
            mock_supabase.table.return_value.select.return_value.eq.return_value.lte.return_value.gte.return_value.order.return_value.limit.return_value.execute.return_value.data = [
                {
                    "id": "vaga-1",
                    "especialidade": "cardiologia",
                    "data_plantao": (datetime.now() + timedelta(days=10)).isoformat(),
                    "hospitais": {"nome": "São Luiz", "regiao": "sp"},
                }
            ]

            vagas = await buscar_vagas_urgentes()

            assert len(vagas) == 1
            assert vagas[0]["especialidade"] == "cardiologia"


class TestCalcularUrgencia:
    """Testes para cálculo de urgência."""

    @pytest.mark.asyncio
    async def test_urgencia_maxima_para_hoje(self):
        """Vaga para hoje deve ter urgência máxima."""
        vaga = {"data_plantao": datetime.now().date().isoformat()}
        urgencia = await calcular_urgencia(vaga)
        assert urgencia == 100

    @pytest.mark.asyncio
    async def test_urgencia_alta_para_3_dias(self):
        """Vaga em 3 dias deve ter urgência alta."""
        vaga = {"data_plantao": (datetime.now() + timedelta(days=2)).date().isoformat()}
        urgencia = await calcular_urgencia(vaga)
        assert urgencia == 90

    @pytest.mark.asyncio
    async def test_urgencia_media_para_2_semanas(self):
        """Vaga em 2 semanas deve ter urgência média."""
        vaga = {"data_plantao": (datetime.now() + timedelta(days=14)).date().isoformat()}
        urgencia = await calcular_urgencia(vaga)
        assert urgencia == 50


class TestBuscarMedicosCompativeis:
    """Testes para busca de médicos compatíveis."""

    @pytest.mark.asyncio
    async def test_filtra_por_especialidade(self):
        """Deve filtrar médicos por especialidade da vaga."""
        vaga = {
            "id": "vaga-1",
            "especialidade": "cardiologia",
            "hospitais": {"regiao": "sp"},
        }

        with patch("app.services.gatilhos.oferta.supabase") as mock_supabase:
            # Mock da busca de médicos
            mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = [
                {"id": "med-1", "nome": "Dr João", "especialidade": "cardiologia"},
            ]

            # Mock de ofertas existentes (vazia)
            mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.in_.return_value.execute.return_value.data = []

            medicos = await buscar_medicos_compativeis(vaga)

            assert len(medicos) == 1


class TestExecutarDeteccaoOferta:
    """Testes para detecção de ofertas."""

    @pytest.mark.asyncio
    async def test_pulado_em_modo_piloto(self):
        """Deve pular em modo piloto."""
        with patch("app.services.gatilhos.oferta.is_pilot_mode") as mock_pilot:
            mock_pilot.return_value = True

            with patch("app.workers.pilot_mode.settings") as mock_settings:
                mock_settings.is_pilot_mode = True

                resultado = await executar_deteccao_oferta()

                assert resultado is None
```

### T6: Adicionar coluna score_engajamento (30min)

**Migration:** `add_score_engajamento_to_clientes`

```sql
-- Migration: add_score_engajamento_to_clientes
-- Sprint 32 E06: Score de engajamento para priorização

-- Adicionar coluna para score de engajamento
ALTER TABLE clientes
ADD COLUMN IF NOT EXISTS score_engajamento NUMERIC(5,2) DEFAULT 50.0;

-- Comentário
COMMENT ON COLUMN clientes.score_engajamento IS 'Score de engajamento (0-100). Maior = médico mais responsivo. Usado para priorizar ofertas.';

-- Índice para ordenação
CREATE INDEX IF NOT EXISTS idx_clientes_score_engajamento
ON clientes (score_engajamento DESC)
WHERE status_telefone = 'validado' AND opt_out = false;
```

---

## Definition of Done (DoD)

### Critérios Obrigatórios

- [ ] **Detecção de vagas urgentes funciona**
  - [ ] Busca vagas < 20 dias sem médico
  - [ ] Calcula urgência corretamente
  - [ ] Ordena por data (mais urgente primeiro)

- [ ] **Busca de médicos compatíveis funciona**
  - [ ] Filtra por especialidade
  - [ ] Filtra por região (se disponível)
  - [ ] Exclui quem já recebeu oferta para esta vaga
  - [ ] Ordena por score de engajamento

- [ ] **Gatilhos são criados corretamente**
  - [ ] Prioridade baseada na urgência
  - [ ] Dados completos (vaga, hospital, médico)
  - [ ] Unique constraint impede duplicatas

- [ ] **Handler de execução funciona**
  - [ ] Verifica se vaga ainda está aberta
  - [ ] Cria campanha de oferta
  - [ ] Enfileira mensagem

- [ ] **Integração com worker**
  - [ ] Handler registrado em GATILHO_HANDLERS
  - [ ] Detecção no ciclo de gatilhos

- [ ] **Testes passando**
  - [ ] `uv run pytest tests/unit/test_gatilho_oferta.py -v` = OK

### Verificação Manual

```sql
-- Verificar vagas urgentes
SELECT id, especialidade, data_plantao,
       (data_plantao - CURRENT_DATE) as dias_restantes
FROM vagas
WHERE status = 'aberta'
  AND data_plantao <= CURRENT_DATE + INTERVAL '20 days'
ORDER BY data_plantao;

-- Verificar gatilhos de oferta criados
SELECT g.*, c.nome as medico_nome
FROM gatilhos_automaticos g
JOIN clientes c ON c.id = g.cliente_id
WHERE g.tipo = 'oferta'
ORDER BY g.prioridade DESC, g.criado_em DESC
LIMIT 20;
```

---

## Notas para o Desenvolvedor

1. **Threshold configurável:**
   - 20 dias é o default
   - Pode ser ajustado via config se necessário

2. **Limite de ofertas por vaga:**
   - Máximo 5 médicos por vaga
   - Evita spam se vaga popular

3. **Prioridade dinâmica:**
   - Vaga para amanhã = 100
   - Vaga para 2 semanas = 50
   - Permite processar urgentes primeiro

4. **Score de engajamento:**
   - Médicos que respondem mais têm maior chance
   - Será atualizado em outro épico (analytics)
