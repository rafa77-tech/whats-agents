# E04: Adaptacao da Julia para Oferta de Vagas

## Objetivo

Atualizar os templates e formatadores usados pela Julia para comunicar corretamente os tres tipos de valor ao oferecer vagas aos medicos.

## Dependencias

- E01 (Migracao de Schema) completo
- E03 (Pipeline) completo

## Escopo

### Incluido
- Atualizar formatador de vagas para mensagem
- Atualizar formatador de contexto do LLM
- Atualizar resposta da tool `buscar_vagas`
- Atualizar resposta da tool `reservar_plantao`

### Excluido
- Alteracoes no Slack (proximo epico)
- Novos fluxos de negociacao de valor

---

## Tarefas

### T01: Atualizar formatador para mensagem

**Arquivo:** `app/services/vagas/formatters.py`

**Funcao:** `formatar_para_mensagem` (linha 11-47)

**Codigo Atual:**
```python
def formatar_para_mensagem(vaga: dict) -> str:
    # ...
    valor = vaga.get("valor") or 0
    # ...
    if valor:
        partes.append(f"R$ {valor:,.0f}".replace(",", "."))
```

**Codigo Novo:**
```python
def formatar_para_mensagem(vaga: dict) -> str:
    """
    Formata vaga para mensagem natural da Julia.

    Args:
        vaga: Dados da vaga com relacionamentos

    Returns:
        String formatada para mensagem
    """
    hospital = vaga.get("hospitais", {}).get("nome", "Hospital")
    data = vaga.get("data", "")
    periodo = vaga.get("periodos", {}).get("nome", "")
    setor = vaga.get("setores", {}).get("nome", "")

    # Formatar data para PT-BR
    if data:
        try:
            data_obj = datetime.strptime(data, "%Y-%m-%d")
            dias_semana = ["segunda", "terca", "quarta", "quinta", "sexta", "sabado", "domingo"]
            dia_semana = dias_semana[data_obj.weekday()]
            data = f"{dia_semana}, {data_obj.strftime('%d/%m')}"
        except ValueError:
            pass

    partes = [hospital]
    if data:
        partes.append(data)
    if periodo:
        partes.append(periodo.lower())
    if setor:
        partes.append(setor)

    # Formatar valor baseado no tipo
    valor_str = formatar_valor_para_mensagem(vaga)
    if valor_str:
        partes.append(valor_str)

    return ", ".join(partes)


def formatar_valor_para_mensagem(vaga: dict) -> str:
    """
    Formata valor da vaga para mensagem natural.

    Args:
        vaga: Dados da vaga

    Returns:
        String formatada ou vazio
    """
    valor_tipo = vaga.get("valor_tipo", "fixo")
    valor = vaga.get("valor")
    valor_minimo = vaga.get("valor_minimo")
    valor_maximo = vaga.get("valor_maximo")

    if valor_tipo == "fixo" and valor:
        return f"R$ {valor:,.0f}".replace(",", ".")

    elif valor_tipo == "faixa":
        if valor_minimo and valor_maximo:
            return f"R$ {valor_minimo:,.0f} a {valor_maximo:,.0f}".replace(",", ".")
        elif valor_minimo:
            return f"a partir de R$ {valor_minimo:,.0f}".replace(",", ".")
        elif valor_maximo:
            return f"ate R$ {valor_maximo:,.0f}".replace(",", ".")

    elif valor_tipo == "a_combinar":
        return "valor a combinar"

    # Fallback: valor sem tipo definido
    if valor:
        return f"R$ {valor:,.0f}".replace(",", ".")

    return ""
```

**DoD:**
- [ ] Funcao `formatar_valor_para_mensagem` criada
- [ ] `formatar_para_mensagem` usa nova funcao
- [ ] Testes unitarios passando

**Criterios de Aceite:**
1. Vaga com `valor_tipo='fixo'` e `valor=1800` -> "R$ 1.800"
2. Vaga com `valor_tipo='faixa'` e min/max -> "R$ 1.500 a 2.000"
3. Vaga com `valor_tipo='faixa'` so minimo -> "a partir de R$ 1.500"
4. Vaga com `valor_tipo='faixa'` so maximo -> "ate R$ 2.000"
5. Vaga com `valor_tipo='a_combinar'` -> "valor a combinar"

---

### T02: Atualizar formatador de contexto LLM

**Arquivo:** `app/services/vagas/formatters.py`

**Funcao:** `formatar_para_contexto` (linha 50-83)

**Codigo Atual:**
```python
def formatar_para_contexto(vagas: list[dict], especialidade: str = None) -> str:
    # ...
    texto += f"""**Vaga {i}:**
- Hospital: {hospital.get('nome', 'N/A')}
# ...
- Valor: R$ {v.get('valor', 'N/A')}
```

**Codigo Novo:**
```python
def formatar_para_contexto(vagas: list[dict], especialidade: str = None) -> str:
    """
    Formata vagas para incluir no contexto do LLM.

    Args:
        vagas: Lista de vagas
        especialidade: Nome da especialidade (opcional)

    Returns:
        String formatada com vagas
    """
    if not vagas:
        return "Nao ha vagas disponiveis no momento para esta especialidade."

    config = obter_config_especialidade(especialidade) if especialidade else {}
    nome_display = config.get("nome_display", "medico") if config else "medico"

    texto = f"## Vagas Disponiveis para {nome_display}:\n\n"

    for i, v in enumerate(vagas[:5], 1):
        hospital = v.get("hospitais", {})
        periodo = v.get("periodos", {})
        setor = v.get("setores", {})

        # Formatar valor baseado no tipo
        valor_display = _formatar_valor_contexto(v)

        texto += f"""**Vaga {i}:**
- Hospital: {hospital.get('nome', 'N/A')} ({hospital.get('cidade', 'N/A')})
- Data: {v.get('data', 'N/A')}
- Periodo: {periodo.get('nome', 'N/A')} ({periodo.get('hora_inicio', '')}-{periodo.get('hora_fim', '')})
- Setor: {setor.get('nome', 'N/A')}
- Valor: {valor_display}
- ID: {v.get('id', 'N/A')}
"""

    return texto


def _formatar_valor_contexto(vaga: dict) -> str:
    """
    Formata valor para contexto do LLM.

    Args:
        vaga: Dados da vaga

    Returns:
        String formatada para contexto
    """
    valor_tipo = vaga.get("valor_tipo", "fixo")
    valor = vaga.get("valor")
    valor_minimo = vaga.get("valor_minimo")
    valor_maximo = vaga.get("valor_maximo")

    if valor_tipo == "fixo" and valor:
        return f"R$ {valor} (fixo)"

    elif valor_tipo == "faixa":
        if valor_minimo and valor_maximo:
            return f"R$ {valor_minimo} a R$ {valor_maximo} (faixa)"
        elif valor_minimo:
            return f"A partir de R$ {valor_minimo}"
        elif valor_maximo:
            return f"Ate R$ {valor_maximo}"
        return "Faixa nao definida"

    elif valor_tipo == "a_combinar":
        return "A COMBINAR - informar medico que valor sera negociado"

    # Fallback
    if valor:
        return f"R$ {valor}"

    return "N/A"
```

**DoD:**
- [ ] Funcao `_formatar_valor_contexto` criada
- [ ] `formatar_para_contexto` usa nova funcao
- [ ] Contexto inclui informacao clara sobre tipo de valor

**Criterios de Aceite:**
1. Contexto com valor fixo mostra "(fixo)"
2. Contexto com faixa mostra "(faixa)"
3. Contexto com "a combinar" mostra instrucao explicita para LLM

---

### T03: Atualizar resposta da tool buscar_vagas

**Arquivo:** `app/tools/vagas.py`

**Funcao:** `handle_buscar_vagas` (linha 144-363)

**Atualizacao no resumo de vagas (linhas 312-324):**
```python
# Preparar lista simplificada para resposta
vagas_resumo = []
for v in vagas_final:
    vagas_resumo.append({
        "id": v.get("id"),
        "hospital": v.get("hospitais", {}).get("nome"),
        "cidade": v.get("hospitais", {}).get("cidade"),
        "data": v.get("data"),
        "periodo": v.get("periodos", {}).get("nome"),
        # Campos de valor expandidos
        "valor": v.get("valor"),
        "valor_minimo": v.get("valor_minimo"),
        "valor_maximo": v.get("valor_maximo"),
        "valor_tipo": v.get("valor_tipo", "fixo"),
        "valor_display": _formatar_valor_display(v),  # Novo campo
        "setor": v.get("setores", {}).get("nome"),
        "especialidade": v.get("especialidades", {}).get("nome") or especialidade_nome,
    })
```

**Nova funcao auxiliar:**
```python
def _formatar_valor_display(vaga: dict) -> str:
    """
    Formata valor para exibicao na resposta da tool.

    Args:
        vaga: Dados da vaga

    Returns:
        String formatada para exibicao
    """
    valor_tipo = vaga.get("valor_tipo", "fixo")
    valor = vaga.get("valor")
    valor_minimo = vaga.get("valor_minimo")
    valor_maximo = vaga.get("valor_maximo")

    if valor_tipo == "fixo" and valor:
        return f"R$ {valor:,.0f}".replace(",", ".")

    elif valor_tipo == "faixa":
        if valor_minimo and valor_maximo:
            return f"R$ {valor_minimo:,.0f} a R$ {valor_maximo:,.0f}".replace(",", ".")
        elif valor_minimo:
            return f"a partir de R$ {valor_minimo:,.0f}".replace(",", ".")
        elif valor_maximo:
            return f"ate R$ {valor_maximo:,.0f}".replace(",", ".")

    elif valor_tipo == "a_combinar":
        return "a combinar"

    if valor:
        return f"R$ {valor:,.0f}".replace(",", ".")

    return "nao informado"
```

**Atualizacao na instrucao (linhas 327-333):**
```python
# Construir instrucao baseada no contexto
instrucao_base = (
    f"Estas vagas sao de {especialidade_nome}. "
    "Apresente as vagas de forma natural, uma por vez. "
    "SEMPRE mencione a DATA do plantao (dia/mes) pois sera usada para reservar. "
    "Quando o medico aceitar, use a tool reservar_plantao com a DATA no formato YYYY-MM-DD. "
    "IMPORTANTE: Para vagas 'a combinar', informe naturalmente que o valor sera negociado. "
    "Nao invente valores - use apenas o que esta nos dados da vaga."
)
```

**DoD:**
- [ ] Resumo de vagas inclui campos de valor expandidos
- [ ] Campo `valor_display` formatado corretamente
- [ ] Instrucao orienta Julia sobre vagas "a combinar"

---

### T04: Atualizar resposta da tool reservar_plantao

**Arquivo:** `app/tools/vagas.py`

**Funcao:** `handle_reservar_plantao` (linhas 607-627)

**Atualizacao no retorno:**
```python
return {
    "success": True,
    "message": f"Plantao reservado com sucesso: {vaga_formatada}",
    "vaga": {
        "id": vaga_atualizada["id"],
        "hospital": hospital_data.get("nome"),
        "endereco": hospital_data.get("endereco_formatado"),
        "bairro": hospital_data.get("bairro"),
        "cidade": hospital_data.get("cidade"),
        "data": vaga_atualizada.get("data"),
        "periodo": vaga.get("periodos", {}).get("nome"),
        # Campos de valor expandidos
        "valor": vaga.get("valor"),
        "valor_minimo": vaga.get("valor_minimo"),
        "valor_maximo": vaga.get("valor_maximo"),
        "valor_tipo": vaga.get("valor_tipo", "fixo"),
        "valor_display": _formatar_valor_display(vaga),
        "status": vaga_atualizada.get("status")
    },
    "instrucao": _construir_instrucao_confirmacao(vaga, hospital_data)
}


def _construir_instrucao_confirmacao(vaga: dict, hospital_data: dict) -> str:
    """
    Constroi instrucao de confirmacao baseada no tipo de valor.

    Args:
        vaga: Dados da vaga
        hospital_data: Dados do hospital

    Returns:
        Instrucao para o LLM
    """
    valor_tipo = vaga.get("valor_tipo", "fixo")
    endereco = hospital_data.get("endereco_formatado") or "endereco nao disponivel"

    instrucao = "Confirme a reserva mencionando o hospital, data e periodo. "

    if valor_tipo == "fixo":
        instrucao += f"Mencione o valor de R$ {vaga.get('valor')}. "
    elif valor_tipo == "faixa":
        instrucao += "Mencione que o valor sera dentro da faixa acordada. "
    elif valor_tipo == "a_combinar":
        instrucao += (
            "Informe que o valor sera combinado diretamente com o hospital/gestor. "
            "Pergunte se o medico tem alguma expectativa de valor para repassar. "
        )

    instrucao += f"Se o medico perguntar o endereco, use: {endereco}"

    return instrucao
```

**DoD:**
- [ ] Resposta inclui campos de valor expandidos
- [ ] Instrucao adaptada por tipo de valor
- [ ] Julia pergunta expectativa quando "a combinar"

**Criterios de Aceite:**
1. Reserva de vaga fixa menciona valor exato
2. Reserva de vaga "a combinar" orienta Julia a perguntar expectativa
3. Reserva de vaga faixa menciona faixa acordada

---

### T05: Atualizar busca de vaga por data

**Arquivo:** `app/tools/vagas.py`

**Funcao:** `_buscar_vaga_por_data` (linha 478-514)

**Atualizacao no select:**
```python
async def _buscar_vaga_por_data(data: str, especialidade_id: str) -> dict | None:
    """
    Busca vaga pela data e especialidade.

    Args:
        data: Data no formato YYYY-MM-DD
        especialidade_id: ID da especialidade do medico

    Returns:
        Vaga encontrada ou None
    """
    logger.info(f"_buscar_vaga_por_data: data={data}, especialidade_id={especialidade_id}")

    try:
        response = (
            supabase.table("vagas")
            .select(
                "*, hospitais(*), periodos(*), setores(*), "
                "valor, valor_minimo, valor_maximo, valor_tipo"  # Campos explicitados
            )
            .eq("data", data)
            .eq("especialidade_id", especialidade_id)
            .eq("status", "aberta")
            .limit(1)
            .execute()
        )

        logger.info(f"_buscar_vaga_por_data: encontradas {len(response.data) if response.data else 0} vagas")

        if response.data:
            vaga = response.data[0]
            logger.info(
                f"_buscar_vaga_por_data: vaga encontrada id={vaga.get('id')}, "
                f"valor_tipo={vaga.get('valor_tipo')}"
            )
            return vaga

        logger.warning(f"_buscar_vaga_por_data: nenhuma vaga encontrada para data={data}")
        return None

    except Exception as e:
        logger.error(f"Erro ao buscar vaga por data: {e}", exc_info=True)
        return None
```

**DoD:**
- [ ] Select inclui campos de valor
- [ ] Log inclui valor_tipo
- [ ] Vaga retornada tem todos os campos

---

## Arquivos Modificados

| Arquivo | Funcao | Acao | Descricao |
|---------|--------|------|-----------|
| `vagas/formatters.py` | `formatar_para_mensagem` | Modificar | Usar nova funcao de valor |
| `vagas/formatters.py` | `formatar_valor_para_mensagem` | Criar | Formatacao por tipo |
| `vagas/formatters.py` | `formatar_para_contexto` | Modificar | Usar nova funcao de valor |
| `vagas/formatters.py` | `_formatar_valor_contexto` | Criar | Formatacao para LLM |
| `tools/vagas.py` | `handle_buscar_vagas` | Modificar | Incluir campos de valor |
| `tools/vagas.py` | `_formatar_valor_display` | Criar | Formatacao para tool |
| `tools/vagas.py` | `handle_reservar_plantao` | Modificar | Incluir campos e instrucao |
| `tools/vagas.py` | `_construir_instrucao_confirmacao` | Criar | Instrucao por tipo |
| `tools/vagas.py` | `_buscar_vaga_por_data` | Modificar | Incluir campos no select |

---

## Testes Necessarios

### Testes Unitarios

**Arquivo:** `tests/services/vagas/test_formatters_valor.py`

```python
import pytest
from app.services.vagas.formatters import (
    formatar_para_mensagem,
    formatar_valor_para_mensagem,
    formatar_para_contexto,
)


class TestFormatarValorParaMensagem:
    """Testes para formatacao de valor em mensagens."""

    def test_valor_fixo(self):
        vaga = {"valor": 1800, "valor_tipo": "fixo"}
        assert formatar_valor_para_mensagem(vaga) == "R$ 1.800"

    def test_valor_faixa_completa(self):
        vaga = {"valor_minimo": 1500, "valor_maximo": 2000, "valor_tipo": "faixa"}
        assert formatar_valor_para_mensagem(vaga) == "R$ 1.500 a 2.000"

    def test_valor_faixa_so_minimo(self):
        vaga = {"valor_minimo": 1500, "valor_tipo": "faixa"}
        assert formatar_valor_para_mensagem(vaga) == "a partir de R$ 1.500"

    def test_valor_faixa_so_maximo(self):
        vaga = {"valor_maximo": 2000, "valor_tipo": "faixa"}
        assert formatar_valor_para_mensagem(vaga) == "ate R$ 2.000"

    def test_valor_a_combinar(self):
        vaga = {"valor_tipo": "a_combinar"}
        assert formatar_valor_para_mensagem(vaga) == "valor a combinar"

    def test_valor_sem_tipo_com_valor(self):
        vaga = {"valor": 1500}
        assert formatar_valor_para_mensagem(vaga) == "R$ 1.500"

    def test_valor_sem_tipo_sem_valor(self):
        vaga = {}
        assert formatar_valor_para_mensagem(vaga) == ""


class TestFormatarParaMensagem:
    """Testes para formatacao completa de vaga."""

    def test_vaga_completa_valor_fixo(self):
        vaga = {
            "hospitais": {"nome": "Hospital ABC"},
            "data": "2025-01-15",
            "periodos": {"nome": "Noturno"},
            "setores": {"nome": "UTI"},
            "valor": 2000,
            "valor_tipo": "fixo",
        }
        resultado = formatar_para_mensagem(vaga)
        assert "Hospital ABC" in resultado
        assert "15/01" in resultado
        assert "R$ 2.000" in resultado

    def test_vaga_completa_valor_a_combinar(self):
        vaga = {
            "hospitais": {"nome": "Hospital ABC"},
            "data": "2025-01-15",
            "periodos": {"nome": "Noturno"},
            "valor_tipo": "a_combinar",
        }
        resultado = formatar_para_mensagem(vaga)
        assert "Hospital ABC" in resultado
        assert "valor a combinar" in resultado


class TestFormatarParaContexto:
    """Testes para formatacao de contexto LLM."""

    def test_contexto_valor_a_combinar(self):
        vagas = [{
            "hospitais": {"nome": "Hospital ABC", "cidade": "SP"},
            "periodos": {"nome": "Noturno", "hora_inicio": "19:00", "hora_fim": "07:00"},
            "setores": {"nome": "UTI"},
            "data": "2025-01-15",
            "valor_tipo": "a_combinar",
            "id": "123",
        }]
        resultado = formatar_para_contexto(vagas)
        assert "A COMBINAR" in resultado
        assert "informar medico" in resultado
```

### Testes de Integracao

**Arquivo:** `tests/tools/test_vagas_valor.py`

```python
import pytest
from unittest.mock import AsyncMock, patch
from app.tools.vagas import handle_buscar_vagas, handle_reservar_plantao


class TestToolBuscarVagasValor:
    """Testes de integracao para buscar_vagas com valor flexivel."""

    @pytest.fixture
    def medico_mock(self):
        return {
            "id": "123",
            "especialidade_id": "456",
            "especialidade": "Cardiologia",
        }

    @pytest.fixture
    def conversa_mock(self):
        return {"id": "789"}

    @pytest.mark.asyncio
    async def test_vagas_incluem_campos_valor(self, medico_mock, conversa_mock):
        # Setup mock
        with patch("app.tools.vagas.buscar_vagas_compativeis") as mock_buscar:
            mock_buscar.return_value = [{
                "id": "vaga-1",
                "hospitais": {"nome": "Hospital ABC", "cidade": "SP"},
                "periodos": {"nome": "Noturno"},
                "setores": {"nome": "UTI"},
                "data": "2025-01-15",
                "valor": None,
                "valor_minimo": 1500,
                "valor_maximo": 2000,
                "valor_tipo": "faixa",
            }]

            resultado = await handle_buscar_vagas(
                {"limite": 5},
                medico_mock,
                conversa_mock
            )

            assert resultado["success"] is True
            assert len(resultado["vagas"]) == 1
            vaga = resultado["vagas"][0]
            assert vaga["valor_tipo"] == "faixa"
            assert vaga["valor_minimo"] == 1500
            assert vaga["valor_maximo"] == 2000
            assert "valor_display" in vaga


class TestToolReservarPlantaoValor:
    """Testes de integracao para reservar_plantao com valor flexivel."""

    @pytest.mark.asyncio
    async def test_instrucao_valor_a_combinar(self):
        # Mock de vaga com valor a combinar
        vaga = {
            "id": "vaga-1",
            "hospitais": {"nome": "Hospital ABC", "endereco_formatado": "Rua X, 123"},
            "valor_tipo": "a_combinar",
        }

        from app.tools.vagas import _construir_instrucao_confirmacao
        instrucao = _construir_instrucao_confirmacao(vaga, vaga.get("hospitais", {}))

        assert "combinar" in instrucao.lower() or "combinado" in instrucao.lower()
        assert "expectativa" in instrucao.lower()
```

---

## DoD do Epico

- [ ] T01 completa - Formatador de mensagem atualizado
- [ ] T02 completa - Formatador de contexto atualizado
- [ ] T03 completa - Tool buscar_vagas atualizado
- [ ] T04 completa - Tool reservar_plantao atualizado
- [ ] T05 completa - Busca por data atualizada
- [ ] Testes unitarios passando
- [ ] Testes de integracao passando
- [ ] Julia oferece vagas "a combinar" corretamente
- [ ] Julia menciona faixa quando aplicavel

---

## Exemplos de Comportamento Esperado

### Cenario 1: Oferta de vaga com valor fixo

**Antes:**
> Hospital ABC, quarta, 15/01, noturno, R$ 1.800

**Depois (sem mudanca):**
> Hospital ABC, quarta, 15/01, noturno, R$ 1.800

### Cenario 2: Oferta de vaga "a combinar"

**Antes:**
> Hospital ABC, quarta, 15/01, noturno (sem valor)

**Depois:**
> Hospital ABC, quarta, 15/01, noturno, valor a combinar

**Julia deve dizer algo como:**
> "Oi Dr! Surgiu uma vaga no Hospital ABC pra quarta, 15/01, noturno. O valor ainda ta em aberto, vc tem alguma expectativa?"

### Cenario 3: Oferta de vaga com faixa

**Antes:**
> (nao suportado)

**Depois:**
> Hospital ABC, quarta, 15/01, noturno, R$ 1.500 a 2.000

**Julia deve dizer algo como:**
> "Oi Dr! Tem um plantao no Hospital ABC pra quarta, noturno. O valor fica entre R$ 1.500 e R$ 2.000, dependendo da negociacao. Tem interesse?"
