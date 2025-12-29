# E03: Atualizacao da Pipeline

## Objetivo

Atualizar os componentes da pipeline (pipeline_worker, importador, deduplicador) para propagar os novos campos de valor flexivel.

## Dependencias

- E01 (Migracao de Schema) completo
- E02 (Extracao LLM) completo

## Escopo

### Incluido
- Atualizar pipeline_worker para salvar novos campos
- Atualizar importador para copiar campos para tabela vagas
- Atualizar calculo de confianca para considerar valor_tipo
- Atualizar deduplicacao (hash nao muda)

### Excluido
- Alteracoes na Julia (proximo epico)
- Alteracoes no Slack (epico posterior)

---

## Tarefas

### T01: Atualizar pipeline_worker - criacao de vaga_grupo

**Arquivo:** `app/services/grupos/pipeline_worker.py`

**Funcao:** `_criar_vaga_grupo` (linha ~240-280)

**Codigo Atual:**
```python
async def _criar_vaga_grupo(
    self,
    mensagem_id: UUID,
    vaga,
    msg_data: dict
) -> UUID:
    # ...
    dados = {
        # ...
        "valor": vaga.dados.valor if vaga.dados else None,
        # ...
    }
```

**Codigo Novo:**
```python
async def _criar_vaga_grupo(
    self,
    mensagem_id: UUID,
    vaga,
    msg_data: dict
) -> UUID:
    """
    Cria registro de vaga_grupo a partir de extracao.

    Args:
        mensagem_id: ID da mensagem original
        vaga: Dados extraidos da vaga
        msg_data: Dados completos da mensagem

    Returns:
        ID da vaga_grupo criada
    """
    # Serializar data se existir
    data_extraida = None
    if vaga.dados and vaga.dados.data:
        data_extraida = vaga.dados.data.isoformat() if hasattr(vaga.dados.data, 'isoformat') else str(vaga.dados.data)

    dados = {
        "mensagem_id": str(mensagem_id),
        "grupo_origem_id": msg_data.get("grupo_id"),
        "hospital_raw": vaga.dados.hospital if vaga.dados else None,
        "especialidade_raw": vaga.dados.especialidade if vaga.dados else None,
        "data": data_extraida,
        "hora_inicio": vaga.dados.hora_inicio if vaga.dados else None,
        "hora_fim": vaga.dados.hora_fim if vaga.dados else None,
        # Campos de valor flexivel
        "valor": vaga.dados.valor if vaga.dados else None,
        "valor_minimo": vaga.dados.valor_minimo if vaga.dados else None,
        "valor_maximo": vaga.dados.valor_maximo if vaga.dados else None,
        "valor_tipo": vaga.dados.valor_tipo if vaga.dados else "a_combinar",
        # Outros campos
        "periodo_raw": vaga.dados.periodo if vaga.dados else None,
        "setor_raw": vaga.dados.setor if vaga.dados else None,
        "tipo_vaga_raw": vaga.dados.tipo_vaga if vaga.dados else None,
        "forma_pagamento_raw": vaga.dados.forma_pagamento if vaga.dados else None,
        "observacoes_raw": vaga.dados.observacoes if vaga.dados else None,
        "confianca_geral": vaga.confianca.media_ponderada() if vaga.confianca else None,
        "status": "extraido",
    }

    result = supabase.table("vagas_grupo") \
        .insert(dados) \
        .execute()

    return UUID(result.data[0]["id"])
```

**DoD:**
- [ ] Novos campos incluidos no insert
- [ ] Default "a_combinar" quando nao especificado
- [ ] Teste de integracao passando

**Criterios de Aceite:**
1. Vaga extraida com valor fixo salva `valor_tipo='fixo'` e `valor=X`
2. Vaga extraida sem valor salva `valor_tipo='a_combinar'`
3. Vaga extraida com faixa salva `valor_tipo='faixa'` com minimo/maximo

---

### T02: Atualizar importador - criacao de vaga principal

**Arquivo:** `app/services/grupos/importador.py`

**Funcao:** `criar_vaga_principal` (linha ~189-224)

**Codigo Atual:**
```python
async def criar_vaga_principal(vaga_grupo: dict) -> UUID:
    dados_vaga = {
        # ...
        "valor": vaga_grupo.get("valor"),
        # ...
    }
```

**Codigo Novo:**
```python
async def criar_vaga_principal(vaga_grupo: dict) -> UUID:
    """
    Cria vaga na tabela principal a partir de vaga do grupo.

    Args:
        vaga_grupo: Dados da vaga_grupo normalizada

    Returns:
        UUID da vaga criada
    """
    # Mapear campos
    dados_vaga = {
        "hospital_id": vaga_grupo["hospital_id"],
        "especialidade_id": vaga_grupo["especialidade_id"],
        "data": vaga_grupo["data"],
        "periodo_id": vaga_grupo.get("periodo_id"),
        "setor_id": vaga_grupo.get("setor_id"),
        "tipos_vaga_id": vaga_grupo.get("tipo_vaga_id"),
        # Campos de valor flexivel
        "valor": vaga_grupo.get("valor"),
        "valor_minimo": vaga_grupo.get("valor_minimo"),
        "valor_maximo": vaga_grupo.get("valor_maximo"),
        "valor_tipo": vaga_grupo.get("valor_tipo", "a_combinar"),
        # Outros campos
        "hora_inicio": vaga_grupo.get("hora_inicio"),
        "hora_fim": vaga_grupo.get("hora_fim"),
        "status": "aberta",
        "origem": "grupo_whatsapp",
        "vaga_grupo_id": vaga_grupo["id"],
    }

    # Remover campos None
    dados_vaga = {k: v for k, v in dados_vaga.items() if v is not None}

    result = supabase.table("vagas").insert(dados_vaga).execute()
    vaga_id = UUID(result.data[0]["id"])

    logger.info(f"Vaga criada: {vaga_id} (origem: grupo {vaga_grupo['id']}, valor_tipo: {vaga_grupo.get('valor_tipo')})")

    return vaga_id
```

**DoD:**
- [ ] Campos de valor propagados para tabela vagas
- [ ] Log inclui valor_tipo
- [ ] Teste de integracao passando

---

### T03: Atualizar calculo de confianca

**Arquivo:** `app/services/grupos/importador.py`

**Funcao:** `calcular_confianca_geral` (linha ~45-106)

**Atualizacao:**
```python
def calcular_confianca_geral(vaga: dict) -> ScoreConfianca:
    """
    Calcula score de confianca consolidado.

    Pesos:
    - Hospital: 30%
    - Especialidade: 30%
    - Data: 25%
    - Periodo: 10%
    - Valor: 5%

    Args:
        vaga: Dados da vaga do grupo

    Returns:
        ScoreConfianca com todos os scores calculados
    """
    scores = ScoreConfianca()

    # Hospital (30%)
    scores.hospital = vaga.get("hospital_match_score") or vaga.get("confianca_hospital") or 0.0
    scores.detalhes["hospital"] = scores.hospital

    # Especialidade (30%)
    scores.especialidade = vaga.get("especialidade_match_score") or vaga.get("confianca_especialidade") or 0.0
    scores.detalhes["especialidade"] = scores.especialidade

    # Data (25%)
    if vaga.get("data"):
        scores.data = vaga.get("confianca_data") or 0.8
    else:
        scores.data = 0.0
    scores.detalhes["data"] = scores.data

    # Periodo (10%)
    if vaga.get("periodo_id"):
        scores.periodo = 1.0
    else:
        scores.periodo = 0.5
    scores.detalhes["periodo"] = scores.periodo

    # Valor (5%) - Atualizado para considerar valor_tipo
    valor_tipo = vaga.get("valor_tipo", "a_combinar")
    valor = vaga.get("valor")
    valor_minimo = vaga.get("valor_minimo")
    valor_maximo = vaga.get("valor_maximo")

    if valor_tipo == "fixo" and valor and 100 <= valor <= 10000:
        scores.valor = 1.0  # Valor fixo valido
    elif valor_tipo == "faixa" and (valor_minimo or valor_maximo):
        scores.valor = 0.9  # Faixa definida
    elif valor_tipo == "a_combinar":
        scores.valor = 0.7  # A combinar e aceitavel, nao penalizar muito
    else:
        scores.valor = 0.3  # Inconsistente

    scores.detalhes["valor"] = scores.valor
    scores.detalhes["valor_tipo"] = valor_tipo

    # Calculo ponderado
    scores.geral = (
        scores.hospital * 0.30 +
        scores.especialidade * 0.30 +
        scores.data * 0.25 +
        scores.periodo * 0.10 +
        scores.valor * 0.05
    )

    return scores
```

**DoD:**
- [ ] Confianca considera valor_tipo
- [ ] "a_combinar" nao penaliza excessivamente (0.7)
- [ ] Detalhes incluem valor_tipo

**Criterios de Aceite:**
1. Vaga com `valor_tipo='fixo'` e valor valido: score_valor = 1.0
2. Vaga com `valor_tipo='faixa'` com limites: score_valor = 0.9
3. Vaga com `valor_tipo='a_combinar'`: score_valor = 0.7
4. Score geral nao cai drasticamente para vagas "a combinar"

---

### T04: Atualizar validacao para importacao

**Arquivo:** `app/services/grupos/importador.py`

**Funcao:** `validar_para_importacao` (linha ~121-182)

**Atualizacao:**
```python
def validar_para_importacao(vaga: dict) -> ResultadoValidacao:
    """
    Valida se vaga pode ser importada.

    Requisitos obrigatorios:
    - hospital_id
    - especialidade_id
    - data (futuro)

    Avisos (nao bloqueiam):
    - Sem periodo
    - valor_tipo = a_combinar (apenas aviso, nao bloqueia)
    - Data muito distante

    Args:
        vaga: Dados da vaga do grupo

    Returns:
        ResultadoValidacao com erros e avisos
    """
    erros = []
    avisos = []

    # Obrigatorios
    if not vaga.get("hospital_id"):
        erros.append("hospital_id ausente")

    if not vaga.get("especialidade_id"):
        erros.append("especialidade_id ausente")

    if not vaga.get("data"):
        erros.append("data ausente")
    else:
        # Validar data
        try:
            if isinstance(vaga["data"], str):
                data_vaga = datetime.strptime(vaga["data"], "%Y-%m-%d").date()
            else:
                data_vaga = vaga["data"]

            hoje = datetime.now(UTC).date()

            if data_vaga < hoje:
                erros.append("data no passado")
            elif data_vaga > hoje + timedelta(days=90):
                avisos.append("data muito distante (>90 dias)")

        except (ValueError, TypeError):
            erros.append("data em formato invalido")

    # Avisos (nao bloqueiam)
    if not vaga.get("periodo_id"):
        avisos.append("periodo nao identificado")

    # Avisos de valor - ATUALIZADO
    valor_tipo = vaga.get("valor_tipo", "a_combinar")
    if valor_tipo == "a_combinar":
        avisos.append("valor a combinar (sera informado ao medico)")
    elif valor_tipo == "faixa":
        valor_min = vaga.get("valor_minimo")
        valor_max = vaga.get("valor_maximo")
        if valor_min and valor_max:
            avisos.append(f"valor em faixa: R$ {valor_min} - R$ {valor_max}")
        elif valor_min:
            avisos.append(f"valor a partir de R$ {valor_min}")
        elif valor_max:
            avisos.append(f"valor ate R$ {valor_max}")
    elif not vaga.get("valor"):
        avisos.append("valor nao informado")

    return ResultadoValidacao(
        valido=len(erros) == 0,
        erros=erros,
        avisos=avisos
    )
```

**DoD:**
- [ ] Validacao nao bloqueia por valor_tipo
- [ ] Avisos informativos sobre tipo de valor
- [ ] Testes passando

---

### T05: Verificar deduplicacao (sem alteracao necessaria)

**Arquivo:** `app/services/grupos/deduplicador.py`

**Analise:**
O hash de deduplicacao usa: `hospital_id + data + periodo_id + especialidade_id`

O valor NAO faz parte do hash, portanto:
- Duas vagas com mesmo hospital/data/periodo/especialidade sao duplicatas
- Mesmo que uma tenha valor fixo e outra "a combinar"
- Isso e o comportamento correto

**Verificacao:**
```python
def calcular_hash_dedup(
    hospital_id: UUID,
    data: Optional[str],
    periodo_id: Optional[UUID],
    especialidade_id: UUID
) -> str:
    # valor NAO faz parte do hash - correto!
    componentes = [
        str(hospital_id),
        data or "sem_data",
        str(periodo_id) if periodo_id else "sem_periodo",
        str(especialidade_id),
    ]
    texto = "|".join(componentes)
    return hashlib.md5(texto.encode()).hexdigest()
```

**DoD:**
- [ ] Confirmar que hash nao inclui valor (correto)
- [ ] Documentar decisao
- [ ] Nenhuma alteracao necessaria

---

## Arquivos Modificados

| Arquivo | Funcao | Acao | Descricao |
|---------|--------|------|-----------|
| `pipeline_worker.py` | `_criar_vaga_grupo` | Modificar | Adicionar campos valor_* |
| `importador.py` | `criar_vaga_principal` | Modificar | Propagar campos valor_* |
| `importador.py` | `calcular_confianca_geral` | Modificar | Considerar valor_tipo |
| `importador.py` | `validar_para_importacao` | Modificar | Avisos por tipo de valor |
| `deduplicador.py` | - | Verificar | Confirmar hash sem valor |

---

## Testes Necessarios

### Testes de Integracao

**Arquivo:** `tests/grupos/test_pipeline_valor.py`

```python
import pytest
from uuid import uuid4
from app.services.grupos.pipeline_worker import PipelineGrupos
from app.services.grupos.importador import (
    calcular_confianca_geral,
    validar_para_importacao,
    criar_vaga_principal
)


class TestPipelineValorFlexivel:
    """Testes de integracao para valor flexivel na pipeline."""

    @pytest.fixture
    def vaga_fixo(self):
        return {
            "id": str(uuid4()),
            "hospital_id": str(uuid4()),
            "especialidade_id": str(uuid4()),
            "data": "2025-01-15",
            "valor": 1800,
            "valor_minimo": None,
            "valor_maximo": None,
            "valor_tipo": "fixo",
        }

    @pytest.fixture
    def vaga_a_combinar(self):
        return {
            "id": str(uuid4()),
            "hospital_id": str(uuid4()),
            "especialidade_id": str(uuid4()),
            "data": "2025-01-15",
            "valor": None,
            "valor_minimo": None,
            "valor_maximo": None,
            "valor_tipo": "a_combinar",
        }

    @pytest.fixture
    def vaga_faixa(self):
        return {
            "id": str(uuid4()),
            "hospital_id": str(uuid4()),
            "especialidade_id": str(uuid4()),
            "data": "2025-01-15",
            "valor": None,
            "valor_minimo": 1500,
            "valor_maximo": 2000,
            "valor_tipo": "faixa",
        }

    def test_confianca_valor_fixo(self, vaga_fixo):
        scores = calcular_confianca_geral(vaga_fixo)
        assert scores.valor == 1.0
        assert scores.detalhes["valor_tipo"] == "fixo"

    def test_confianca_valor_a_combinar(self, vaga_a_combinar):
        scores = calcular_confianca_geral(vaga_a_combinar)
        assert scores.valor == 0.7  # Nao penaliza muito
        assert scores.detalhes["valor_tipo"] == "a_combinar"

    def test_confianca_valor_faixa(self, vaga_faixa):
        scores = calcular_confianca_geral(vaga_faixa)
        assert scores.valor == 0.9
        assert scores.detalhes["valor_tipo"] == "faixa"

    def test_validacao_aceita_a_combinar(self, vaga_a_combinar):
        result = validar_para_importacao(vaga_a_combinar)
        assert result.valido is True  # Nao bloqueia
        assert any("a combinar" in aviso for aviso in result.avisos)

    def test_validacao_aceita_faixa(self, vaga_faixa):
        result = validar_para_importacao(vaga_faixa)
        assert result.valido is True
        assert any("faixa" in aviso or "1500" in aviso for aviso in result.avisos)
```

**DoD:**
- [ ] Todos os testes passando
- [ ] Cobertura das 3 situacoes (fixo, a_combinar, faixa)

---

## DoD do Epico

- [ ] T01 completa - pipeline_worker atualizado
- [ ] T02 completa - importador propaga campos
- [ ] T03 completa - confianca considera valor_tipo
- [ ] T04 completa - validacao com avisos
- [ ] T05 completa - deduplicacao verificada
- [ ] Testes de integracao passando
- [ ] Pipeline processando vagas "a combinar" sem erros

---

## Checklist de Validacao

```python
# Processar uma mensagem real com "a combinar"
# 1. Inserir mensagem de teste
# 2. Rodar pipeline
# 3. Verificar vaga_grupo criada

from app.services.supabase import supabase

# Verificar vagas_grupo com valor_tipo
result = supabase.table("vagas_grupo") \
    .select("id, valor, valor_tipo, valor_minimo, valor_maximo, status") \
    .order("created_at", desc=True) \
    .limit(10) \
    .execute()

for vaga in result.data:
    print(f"ID: {vaga['id']}")
    print(f"  valor_tipo: {vaga['valor_tipo']}")
    print(f"  valor: {vaga['valor']}")
    print(f"  faixa: {vaga['valor_minimo']} - {vaga['valor_maximo']}")
    print(f"  status: {vaga['status']}")
    print()
```
