# E05: Atualizacao das Slack Tools

## Objetivo

Atualizar os templates e ferramentas do Slack para exibir corretamente os tres tipos de valor em listagens e confirmacoes.

## Dependencias

- E01 (Migracao de Schema) completo
- E03 (Pipeline) completo

## Escopo

### Incluido
- Atualizar template de lista de vagas
- Atualizar template de confirmacao de reserva
- Atualizar formatador de valor
- Adicionar filtro opcional por tipo de valor

### Excluido
- Novos comandos de gestao de valor
- Relatorios avancados de valor

---

## Tarefas

### T01: Atualizar conversor de valor

**Arquivo:** `app/services/slack/formatter/converters.py`

**Funcao:** `formatar_valor` (verificar localizacao)

**Adicionar funcao:**
```python
def formatar_valor_completo(
    valor: int = None,
    valor_minimo: int = None,
    valor_maximo: int = None,
    valor_tipo: str = "fixo"
) -> str:
    """
    Formata valor baseado no tipo para exibicao no Slack.

    Args:
        valor: Valor fixo (quando tipo = fixo)
        valor_minimo: Valor minimo da faixa
        valor_maximo: Valor maximo da faixa
        valor_tipo: Tipo de valor (fixo, a_combinar, faixa)

    Returns:
        String formatada
    """
    if valor_tipo == "fixo" and valor:
        return f"R$ {valor:,.0f}".replace(",", ".")

    elif valor_tipo == "faixa":
        if valor_minimo and valor_maximo:
            return f"R$ {valor_minimo:,.0f} - {valor_maximo:,.0f}".replace(",", ".")
        elif valor_minimo:
            return f"A partir de R$ {valor_minimo:,.0f}".replace(",", ".")
        elif valor_maximo:
            return f"Ate R$ {valor_maximo:,.0f}".replace(",", ".")
        return "Faixa nao definida"

    elif valor_tipo == "a_combinar":
        return "_A combinar_"  # Italico no Slack

    # Fallback
    if valor:
        return f"R$ {valor:,.0f}".replace(",", ".")

    return "N/I"  # Nao informado
```

**DoD:**
- [ ] Funcao criada
- [ ] Exportada no __init__.py
- [ ] Testes unitarios

**Criterios de Aceite:**
1. Valor fixo: "R$ 1.800"
2. Faixa completa: "R$ 1.500 - 2.000"
3. A combinar: "_A combinar_" (italico)

---

### T02: Atualizar template de lista de vagas

**Arquivo:** `app/services/slack/formatter/templates.py`

**Funcao:** `template_lista_vagas` (linha 158-190)

**Codigo Atual:**
```python
def template_lista_vagas(vagas: list[dict]) -> str:
    # ...
    for i, v in enumerate(vagas[:7]):
        hospital = v.get("hospital", "?")
        data = formatar_data(v.get("data", ""))
        periodo = v.get("periodo", "")
        valor = v.get("valor", 0)

        linha = f"{i+1}. {bold(hospital)} - {data}"
        if periodo:
            linha += f" ({periodo})"
        if valor:
            linha += f" - {formatar_valor(valor)}"
```

**Codigo Novo:**
```python
def template_lista_vagas(vagas: list[dict]) -> str:
    """
    Formata lista de vagas.

    Args:
        vagas: Lista de dicts com hospital, data, periodo, valor, valor_tipo, etc

    Returns:
        Mensagem formatada
    """
    if not vagas:
        return "Nenhuma vaga encontrada"

    linhas = [f"*{len(vagas)} vagas:*", ""]

    for i, v in enumerate(vagas[:7]):  # Max 7
        hospital = v.get("hospital", "?")
        data = formatar_data(v.get("data", ""))
        periodo = v.get("periodo", "")

        # Usar formatador completo de valor
        valor_display = formatar_valor_completo(
            valor=v.get("valor"),
            valor_minimo=v.get("valor_minimo"),
            valor_maximo=v.get("valor_maximo"),
            valor_tipo=v.get("valor_tipo", "fixo")
        )

        linha = f"{i+1}. {bold(hospital)} - {data}"
        if periodo:
            linha += f" ({periodo})"
        linha += f" - {valor_display}"

        linhas.append(linha)

    if len(vagas) > 7:
        linhas.append(f"_...e mais {len(vagas) - 7}_")

    return "\n".join(linhas)
```

**DoD:**
- [ ] Template usa `formatar_valor_completo`
- [ ] Valor sempre exibido (incluindo "A combinar")
- [ ] Testes atualizados

**Criterios de Aceite:**
1. Vaga fixo: "1. *Hospital ABC* - 15/01 (Noturno) - R$ 1.800"
2. Vaga faixa: "1. *Hospital ABC* - 15/01 (Noturno) - R$ 1.500 - 2.000"
3. Vaga a_combinar: "1. *Hospital ABC* - 15/01 (Noturno) - _A combinar_"

---

### T03: Atualizar template de confirmacao de reserva

**Arquivo:** `app/services/slack/formatter/templates.py`

**Funcao:** `template_sucesso_reserva` (linha 289-307)

**Codigo Atual:**
```python
def template_sucesso_reserva(vaga: dict, medico: dict) -> str:
    # ...
    valor = vaga.get("valor", 0)
    # ...
    if valor:
        linhas.append(f"Valor: {formatar_valor(valor)}")
```

**Codigo Novo:**
```python
def template_sucesso_reserva(vaga: dict, medico: dict) -> str:
    """Formata confirmacao de reserva."""
    hospital = vaga.get("hospital", "?")
    data = formatar_data(vaga.get("data", ""))
    periodo = vaga.get("periodo", "")
    nome = medico.get("nome", "o medico")

    linhas = [
        f"Reservado pro {nome}!",
        "",
        f"*{hospital}*",
        f"Data: {data}" + (f" ({periodo})" if periodo else ""),
    ]

    # Formatar valor baseado no tipo
    valor_tipo = vaga.get("valor_tipo", "fixo")
    valor_display = formatar_valor_completo(
        valor=vaga.get("valor"),
        valor_minimo=vaga.get("valor_minimo"),
        valor_maximo=vaga.get("valor_maximo"),
        valor_tipo=valor_tipo
    )
    linhas.append(f"Valor: {valor_display}")

    # Nota adicional para valores nao fixos
    if valor_tipo == "a_combinar":
        linhas.append("")
        linhas.append("_Valor sera negociado com o medico_")
    elif valor_tipo == "faixa":
        linhas.append("")
        linhas.append("_Valor final dentro da faixa acordada_")

    return "\n".join(linhas)
```

**DoD:**
- [ ] Template usa `formatar_valor_completo`
- [ ] Nota adicional para valores nao fixos
- [ ] Gestor sabe quando precisa negociar

**Criterios de Aceite:**
1. Reserva fixo mostra valor sem nota
2. Reserva "a combinar" mostra nota sobre negociacao
3. Reserva faixa mostra nota sobre faixa

---

### T04: Atualizar tool de listar vagas

**Arquivo:** `app/tools/slack_tools.py` (verificar localizacao)

**Atualizacao na busca de vagas:**

Se existir uma tool que busca vagas para o Slack, atualizar para incluir os campos:

```python
# Ao buscar vagas do banco
response = (
    supabase.table("vagas")
    .select(
        "id, data, status, "
        "hospitais(nome, cidade), "
        "periodos(nome), "
        "especialidades(nome), "
        "valor, valor_minimo, valor_maximo, valor_tipo"  # Campos adicionais
    )
    .eq("status", "aberta")
    .order("data")
    .limit(limite)
    .execute()
)

# Ao formatar para o template
vagas_formatadas = []
for v in response.data:
    vagas_formatadas.append({
        "hospital": v.get("hospitais", {}).get("nome"),
        "data": v.get("data"),
        "periodo": v.get("periodos", {}).get("nome"),
        "valor": v.get("valor"),
        "valor_minimo": v.get("valor_minimo"),
        "valor_maximo": v.get("valor_maximo"),
        "valor_tipo": v.get("valor_tipo", "fixo"),
    })
```

**DoD:**
- [ ] Busca inclui campos de valor
- [ ] Formatacao passa campos para template
- [ ] Lista no Slack mostra todos os tipos de valor

---

### T05: Adicionar filtro por tipo de valor (Opcional)

**Arquivo:** `app/tools/slack_tools.py`

**Nova funcionalidade:**

Permitir que gestor filtre vagas por tipo de valor via Slack:

```python
# Exemplos de comandos NLP
# "mostra vagas a combinar"
# "vagas com valor fixo"
# "lista vagas sem valor definido"

async def handle_listar_vagas_slack(
    parametros: dict,
    sessao: dict
) -> dict:
    """
    Handler para listar vagas via Slack.

    Args:
        parametros: Incluindo filtro_valor_tipo opcional
        sessao: Sessao do Slack

    Returns:
        Resultado formatado
    """
    filtro_valor_tipo = parametros.get("valor_tipo")  # fixo, a_combinar, faixa

    query = supabase.table("vagas").select(
        "id, data, status, "
        "hospitais(nome, cidade), "
        "periodos(nome), "
        "valor, valor_minimo, valor_maximo, valor_tipo"
    ).eq("status", "aberta")

    # Aplicar filtro de tipo de valor se especificado
    if filtro_valor_tipo:
        query = query.eq("valor_tipo", filtro_valor_tipo)

    response = query.order("data").limit(10).execute()

    # Formatar e retornar
    # ...
```

**DoD:**
- [ ] Filtro implementado
- [ ] NLP reconhece "a combinar", "valor fixo", "faixa"
- [ ] Template mostra filtro aplicado

**Criterios de Aceite:**
1. "mostra vagas a combinar" lista apenas tipo a_combinar
2. "vagas com valor fixo" lista apenas tipo fixo
3. Sem filtro lista todas

---

## Arquivos Modificados

| Arquivo | Funcao | Acao | Descricao |
|---------|--------|------|-----------|
| `formatter/converters.py` | `formatar_valor_completo` | Criar | Formatacao por tipo |
| `formatter/templates.py` | `template_lista_vagas` | Modificar | Usar formatador completo |
| `formatter/templates.py` | `template_sucesso_reserva` | Modificar | Nota para valores nao fixos |
| `slack_tools.py` | queries de vagas | Modificar | Incluir campos de valor |
| `slack_tools.py` | filtro valor_tipo | Criar | Filtro opcional |

---

## Testes Necessarios

### Testes Unitarios

**Arquivo:** `tests/services/slack/formatter/test_converters_valor.py`

```python
import pytest
from app.services.slack.formatter.converters import formatar_valor_completo


class TestFormatarValorCompleto:
    """Testes para formatador de valor do Slack."""

    def test_valor_fixo(self):
        assert formatar_valor_completo(
            valor=1800,
            valor_tipo="fixo"
        ) == "R$ 1.800"

    def test_valor_faixa_completa(self):
        assert formatar_valor_completo(
            valor_minimo=1500,
            valor_maximo=2000,
            valor_tipo="faixa"
        ) == "R$ 1.500 - 2.000"

    def test_valor_faixa_so_minimo(self):
        assert formatar_valor_completo(
            valor_minimo=1500,
            valor_tipo="faixa"
        ) == "A partir de R$ 1.500"

    def test_valor_faixa_so_maximo(self):
        assert formatar_valor_completo(
            valor_maximo=2000,
            valor_tipo="faixa"
        ) == "Ate R$ 2.000"

    def test_valor_a_combinar(self):
        assert formatar_valor_completo(
            valor_tipo="a_combinar"
        ) == "_A combinar_"

    def test_valor_nao_informado(self):
        assert formatar_valor_completo() == "N/I"
```

**Arquivo:** `tests/services/slack/formatter/test_templates_valor.py`

```python
import pytest
from app.services.slack.formatter.templates import (
    template_lista_vagas,
    template_sucesso_reserva,
)


class TestTemplateListaVagasValor:
    """Testes para template de lista de vagas."""

    def test_lista_com_tipos_variados(self):
        vagas = [
            {"hospital": "Hospital A", "data": "2025-01-15", "valor": 1800, "valor_tipo": "fixo"},
            {"hospital": "Hospital B", "data": "2025-01-16", "valor_tipo": "a_combinar"},
            {"hospital": "Hospital C", "data": "2025-01-17", "valor_minimo": 1500, "valor_maximo": 2000, "valor_tipo": "faixa"},
        ]
        resultado = template_lista_vagas(vagas)

        assert "R$ 1.800" in resultado
        assert "_A combinar_" in resultado
        assert "R$ 1.500 - 2.000" in resultado


class TestTemplateSucessoReservaValor:
    """Testes para template de sucesso de reserva."""

    def test_reserva_valor_fixo(self):
        vaga = {"hospital": "Hospital ABC", "data": "2025-01-15", "valor": 1800, "valor_tipo": "fixo"}
        medico = {"nome": "Dr. Silva"}

        resultado = template_sucesso_reserva(vaga, medico)

        assert "R$ 1.800" in resultado
        assert "negociad" not in resultado.lower()

    def test_reserva_valor_a_combinar(self):
        vaga = {"hospital": "Hospital ABC", "data": "2025-01-15", "valor_tipo": "a_combinar"}
        medico = {"nome": "Dr. Silva"}

        resultado = template_sucesso_reserva(vaga, medico)

        assert "_A combinar_" in resultado
        assert "negociad" in resultado.lower()

    def test_reserva_valor_faixa(self):
        vaga = {
            "hospital": "Hospital ABC",
            "data": "2025-01-15",
            "valor_minimo": 1500,
            "valor_maximo": 2000,
            "valor_tipo": "faixa"
        }
        medico = {"nome": "Dr. Silva"}

        resultado = template_sucesso_reserva(vaga, medico)

        assert "R$ 1.500 - 2.000" in resultado
        assert "faixa" in resultado.lower()
```

---

## DoD do Epico

- [ ] T01 completa - Conversor de valor criado
- [ ] T02 completa - Template de lista atualizado
- [ ] T03 completa - Template de reserva atualizado
- [ ] T04 completa - Queries de vagas atualizadas
- [ ] T05 completa (opcional) - Filtro por tipo de valor
- [ ] Testes unitarios passando
- [ ] Slack mostra valores corretamente
- [ ] Gestor tem visibilidade de vagas "a combinar"

---

## Exemplos de Saida no Slack

### Lista de Vagas

```
*10 vagas:*

1. *Hospital ABC* - 15/01 (Noturno) - R$ 1.800
2. *Hospital XYZ* - 16/01 (Diurno) - _A combinar_
3. *Santa Casa* - 17/01 (12h) - R$ 1.500 - 2.000
4. *UPA Centro* - 18/01 (Noturno) - A partir de R$ 1.200
...
```

### Confirmacao de Reserva (A Combinar)

```
Reservado pro Dr. Silva!

*Hospital XYZ*
Data: 16/01 (Diurno)
Valor: _A combinar_

_Valor sera negociado com o medico_
```

### Confirmacao de Reserva (Faixa)

```
Reservado pro Dr. Silva!

*Santa Casa*
Data: 17/01 (12h)
Valor: R$ 1.500 - 2.000

_Valor final dentro da faixa acordada_
```
