# E02: Atualizacao da Extracao LLM

## Objetivo

Atualizar o prompt de extracao e o parsing para suportar valores flexiveis (fixo, a combinar, faixa).

## Dependencias

- E01 (Migracao de Schema) deve estar completo

## Escopo

### Incluido
- Atualizar prompt de extracao
- Atualizar dataclasses de resposta
- Atualizar parsing de JSON
- Validacao de dados antes do insert

### Excluido
- Alteracoes na pipeline (proximo epico)
- Retroprocessar mensagens antigas

---

## Tarefas

### T01: Atualizar dataclasses de valor

**Arquivo:** `app/services/grupos/extrator.py`

**Codigo Atual (linha ~30-45):**
```python
@dataclass
class DadosVagaExtraida:
    hospital: Optional[str] = None
    especialidade: Optional[str] = None
    data: Optional[date] = None
    hora_inicio: Optional[str] = None
    hora_fim: Optional[str] = None
    valor: Optional[int] = None  # <-- Problema aqui
    # ...
```

**Codigo Novo:**
```python
@dataclass
class DadosVagaExtraida:
    """Dados extraidos de uma vaga."""
    hospital: Optional[str] = None
    especialidade: Optional[str] = None
    data: Optional[date] = None
    hora_inicio: Optional[str] = None
    hora_fim: Optional[str] = None
    # Campos de valor flexivel
    valor: Optional[int] = None           # Valor exato (quando fixo)
    valor_minimo: Optional[int] = None    # Faixa minima
    valor_maximo: Optional[int] = None    # Faixa maxima
    valor_tipo: str = "fixo"              # 'fixo', 'a_combinar', 'faixa'
    periodo: Optional[str] = None
    setor: Optional[str] = None
    tipo_vaga: Optional[str] = None
    forma_pagamento: Optional[str] = None
    observacoes: Optional[str] = None
```

**DoD:**
- [ ] Dataclass atualizada
- [ ] Campos documentados
- [ ] Sem quebra de compatibilidade (campos opcionais)

---

### T02: Atualizar prompt de extracao

**Arquivo:** `app/services/grupos/prompts.py`

**Secao do Prompt a Atualizar (PROMPT_EXTRACAO):**

```python
PROMPT_EXTRACAO = """
Voce e um extrator de dados de ofertas de plantao medico.
Analise a mensagem e extraia os dados estruturados de TODAS as vagas mencionadas.

IMPORTANTE:
- Uma mensagem pode conter MULTIPLAS vagas (ex: lista de escalas)
- Retorne um ARRAY de vagas, mesmo que seja apenas uma
- Se um campo nao puder ser extraido, use null
- Inclua score de confianca (0-1) para cada campo

Data de hoje: {data_hoje}

CAMPOS A EXTRAIR:
- hospital: Nome do hospital/clinica/UPA
- especialidade: Especialidade medica requerida
- data: Data no formato YYYY-MM-DD
- hora_inicio: Horario de inicio HH:MM
- hora_fim: Horario de fim HH:MM

VALOR (IMPORTANTE - campos de valor flexivel):
- valor_tipo: Tipo de valor, DEVE ser um de:
  * "fixo" - valor exato conhecido (ex: "R$ 1.800")
  * "a_combinar" - valor nao informado ou negociavel (ex: "a combinar", "a tratar", sem mencao de valor)
  * "faixa" - valor em faixa (ex: "entre 1.500 e 2.000", "a partir de 1.500")
- valor: Valor exato em reais (apenas numero inteiro, sem centavos). Use APENAS se valor_tipo = "fixo"
- valor_minimo: Valor minimo da faixa (apenas numero inteiro). Use APENAS se valor_tipo = "faixa"
- valor_maximo: Valor maximo da faixa (apenas numero inteiro). Use APENAS se valor_tipo = "faixa"

REGRAS DE VALOR:
1. Se a mensagem diz "R$ 1.800" ou "1800 reais" -> valor_tipo: "fixo", valor: 1800
2. Se a mensagem diz "a combinar", "a tratar", "negociavel" -> valor_tipo: "a_combinar", valor: null
3. Se NAO menciona valor algum -> valor_tipo: "a_combinar", valor: null
4. Se a mensagem diz "entre 1.500 e 2.000" -> valor_tipo: "faixa", valor_minimo: 1500, valor_maximo: 2000
5. Se a mensagem diz "a partir de 1.500" -> valor_tipo: "faixa", valor_minimo: 1500, valor_maximo: null
6. Se a mensagem diz "ate 2.000" -> valor_tipo: "faixa", valor_minimo: null, valor_maximo: 2000
7. NUNCA retorne string no campo valor - apenas numeros inteiros ou null

- periodo: Um de [Diurno, Vespertino, Noturno, Cinderela]
- setor: Um de [Pronto atendimento, RPA, Hospital, C. Cirurgico, SADT]
- tipo_vaga: Um de [Cobertura, Fixo, Ambulatorial, Mensal]
- forma_pagamento: Um de [Pessoa fisica, Pessoa juridica, CLT, SCP]
- observacoes: Outras informacoes relevantes

OUTRAS REGRAS:
1. Se a data for ANTERIOR a hoje, marque "data_valida": false
2. Se nao conseguir identificar hospital OU especialidade, nao inclua a vaga
3. "Amanha" = {data_amanha}, "hoje" = {data_hoje}
4. Dias da semana devem ser convertidos para a data correta

MENSAGEM:
{texto}

CONTEXTO:
- Grupo: {nome_grupo}
- Regiao do grupo: {regiao_grupo}
- Quem postou: {nome_contato}

Responda APENAS com JSON no formato:
{{
  "vagas": [
    {{
      "dados": {{
        "hospital": "Hospital Sao Luiz ABC",
        "especialidade": "Clinica Medica",
        "data": "2024-12-28",
        "hora_inicio": "19:00",
        "hora_fim": "07:00",
        "valor_tipo": "fixo",
        "valor": 1800,
        "valor_minimo": null,
        "valor_maximo": null,
        "periodo": "Noturno",
        "setor": "Pronto atendimento",
        "tipo_vaga": "Cobertura",
        "forma_pagamento": "Pessoa juridica",
        "observacoes": "Necessario RQE"
      }},
      "confianca": {{
        "hospital": 0.95,
        "especialidade": 0.90,
        "data": 1.0,
        "hora_inicio": 0.95,
        "hora_fim": 0.95,
        "valor": 0.90
      }},
      "data_valida": true
    }}
  ],
  "total_vagas": 1
}}

EXEMPLOS DE VALOR:

Exemplo 1 - Valor fixo:
Mensagem: "Plantao CM Hospital ABC dia 28/12 noturno R$ 1.800 PJ"
Resposta valor: {{"valor_tipo": "fixo", "valor": 1800, "valor_minimo": null, "valor_maximo": null}}

Exemplo 2 - A combinar:
Mensagem: "Plantao CM Hospital ABC dia 28/12 noturno - valor a combinar"
Resposta valor: {{"valor_tipo": "a_combinar", "valor": null, "valor_minimo": null, "valor_maximo": null}}

Exemplo 3 - Sem mencao de valor:
Mensagem: "Plantao CM Hospital ABC dia 28/12 noturno"
Resposta valor: {{"valor_tipo": "a_combinar", "valor": null, "valor_minimo": null, "valor_maximo": null}}

Exemplo 4 - Faixa:
Mensagem: "Plantao CM Hospital ABC dia 28/12 noturno entre 1.500 e 2.000"
Resposta valor: {{"valor_tipo": "faixa", "valor": null, "valor_minimo": 1500, "valor_maximo": 2000}}

Exemplo 5 - A partir de:
Mensagem: "Plantao CM Hospital ABC dia 28/12 noturno a partir de 1.500"
Resposta valor: {{"valor_tipo": "faixa", "valor": null, "valor_minimo": 1500, "valor_maximo": null}}
"""
```

**DoD:**
- [ ] Prompt atualizado com regras de valor
- [ ] Exemplos claros incluidos
- [ ] Formato JSON atualizado

**Criterios de Aceite:**
1. LLM retorna `valor_tipo` corretamente para mensagens de teste
2. Nunca retorna string no campo `valor`
3. `a_combinar` quando nao ha mencao de valor

---

### T03: Atualizar parsing de resposta

**Arquivo:** `app/services/grupos/extrator.py`

**Funcao:** `_parsear_resposta_extracao`

**Codigo Novo:**
```python
def _parsear_resposta_extracao(texto: str) -> ResultadoExtracao:
    """Parseia resposta do LLM."""
    texto = texto.strip()

    # Extrair JSON
    if not texto.startswith("{"):
        match = re.search(r'\{[\s\S]+\}', texto)
        if match:
            texto = match.group()
        else:
            raise json.JSONDecodeError("JSON nao encontrado", texto, 0)

    dados = json.loads(texto)

    vagas = []
    for vaga_json in dados.get("vagas", []):
        dados_vaga = vaga_json.get("dados", {})
        confianca_json = vaga_json.get("confianca", {})

        # Converter data string para date
        data_str = dados_vaga.get("data")
        data_obj = None
        if data_str:
            try:
                data_obj = datetime.strptime(data_str, "%Y-%m-%d").date()
            except ValueError:
                pass

        # Parsear valor com validacao
        valor_tipo = dados_vaga.get("valor_tipo", "fixo")
        valor = _parsear_valor_seguro(dados_vaga.get("valor"))
        valor_minimo = _parsear_valor_seguro(dados_vaga.get("valor_minimo"))
        valor_maximo = _parsear_valor_seguro(dados_vaga.get("valor_maximo"))

        # Validar consistencia
        valor_tipo, valor, valor_minimo, valor_maximo = _validar_valor(
            valor_tipo, valor, valor_minimo, valor_maximo
        )

        vaga = VagaExtraida(
            dados=DadosVagaExtraida(
                hospital=dados_vaga.get("hospital"),
                especialidade=dados_vaga.get("especialidade"),
                data=data_obj,
                hora_inicio=dados_vaga.get("hora_inicio"),
                hora_fim=dados_vaga.get("hora_fim"),
                valor=valor,
                valor_minimo=valor_minimo,
                valor_maximo=valor_maximo,
                valor_tipo=valor_tipo,
                periodo=dados_vaga.get("periodo"),
                setor=dados_vaga.get("setor"),
                tipo_vaga=dados_vaga.get("tipo_vaga"),
                forma_pagamento=dados_vaga.get("forma_pagamento"),
                observacoes=dados_vaga.get("observacoes"),
            ),
            confianca=ConfiancaExtracao(
                hospital=confianca_json.get("hospital", 0.0),
                especialidade=confianca_json.get("especialidade", 0.0),
                data=confianca_json.get("data", 0.0),
                hora_inicio=confianca_json.get("hora_inicio", 0.0),
                hora_fim=confianca_json.get("hora_fim", 0.0),
                valor=confianca_json.get("valor", 0.0),
            ),
            data_valida=vaga_json.get("data_valida", True),
        )

        # Identificar campos faltando
        if not vaga.dados.hospital:
            vaga.campos_faltando.append("hospital")
        if not vaga.dados.especialidade:
            vaga.campos_faltando.append("especialidade")
        if not vaga.dados.data:
            vaga.campos_faltando.append("data")

        vagas.append(vaga)

    return ResultadoExtracao(
        vagas=vagas,
        total_vagas=len(vagas)
    )


def _parsear_valor_seguro(valor_raw) -> Optional[int]:
    """
    Parseia valor de forma segura, tratando strings.

    Args:
        valor_raw: Valor bruto do JSON (pode ser int, str, None)

    Returns:
        int ou None
    """
    if valor_raw is None:
        return None

    if isinstance(valor_raw, int):
        return valor_raw if valor_raw > 0 else None

    if isinstance(valor_raw, float):
        return int(valor_raw) if valor_raw > 0 else None

    if isinstance(valor_raw, str):
        # Tentar extrair numero da string
        # Ex: "1.800", "1800", "R$ 1.800", "1800 reais"
        numeros = re.sub(r'[^\d]', '', valor_raw)
        if numeros:
            try:
                valor_int = int(numeros)
                # Validar range razoavel (100 a 50000)
                if 100 <= valor_int <= 50000:
                    return valor_int
            except ValueError:
                pass

    return None


def _validar_valor(
    valor_tipo: str,
    valor: Optional[int],
    valor_minimo: Optional[int],
    valor_maximo: Optional[int]
) -> tuple:
    """
    Valida e corrige consistencia dos campos de valor.

    Returns:
        Tupla (valor_tipo, valor, valor_minimo, valor_maximo) validados
    """
    # Normalizar valor_tipo
    valor_tipo = valor_tipo.lower().strip() if valor_tipo else "a_combinar"

    # Mapear variacoes comuns
    if valor_tipo in ("a combinar", "a_combinar", "negociavel", "a tratar"):
        valor_tipo = "a_combinar"
    elif valor_tipo in ("faixa", "range", "entre"):
        valor_tipo = "faixa"
    elif valor_tipo in ("fixo", "exato", "definido"):
        valor_tipo = "fixo"
    else:
        # Tipo desconhecido - inferir do contexto
        if valor and valor > 0:
            valor_tipo = "fixo"
        elif valor_minimo or valor_maximo:
            valor_tipo = "faixa"
        else:
            valor_tipo = "a_combinar"

    # Validar consistencia
    if valor_tipo == "fixo":
        if not valor or valor <= 0:
            # Sem valor valido - mudar para a_combinar
            valor_tipo = "a_combinar"
            valor = None
        valor_minimo = None
        valor_maximo = None

    elif valor_tipo == "a_combinar":
        valor = None
        valor_minimo = None
        valor_maximo = None

    elif valor_tipo == "faixa":
        valor = None  # Faixa nao tem valor exato
        # Validar que pelo menos um limite existe
        if not valor_minimo and not valor_maximo:
            valor_tipo = "a_combinar"
        # Validar ordem
        if valor_minimo and valor_maximo and valor_minimo > valor_maximo:
            valor_minimo, valor_maximo = valor_maximo, valor_minimo

    return valor_tipo, valor, valor_minimo, valor_maximo
```

**DoD:**
- [ ] Funcao `_parsear_valor_seguro` criada
- [ ] Funcao `_validar_valor` criada
- [ ] Funcao `_parsear_resposta_extracao` atualizada
- [ ] Tratamento de strings no campo valor
- [ ] Validacao de consistencia

**Criterios de Aceite:**
1. `_parsear_valor_seguro("A combinar")` retorna `None`
2. `_parsear_valor_seguro("1.800")` retorna `1800`
3. `_parsear_valor_seguro(1800)` retorna `1800`
4. `_validar_valor("fixo", None, None, None)` retorna `("a_combinar", None, None, None)`
5. `_validar_valor("faixa", None, 2000, 1500)` retorna `("faixa", None, 1500, 2000)` (ordem corrigida)

---

### T04: Atualizar confianca para incluir tipo de valor

**Arquivo:** `app/services/grupos/extrator.py`

**Atualizar `ConfiancaExtracao`:**
```python
@dataclass
class ConfiancaExtracao:
    """Scores de confianca por campo."""
    hospital: float = 0.0
    especialidade: float = 0.0
    data: float = 0.0
    hora_inicio: float = 0.0
    hora_fim: float = 0.0
    valor: float = 0.0

    def media_ponderada(self) -> float:
        """Calcula media ponderada (hospital e especialidade tem peso maior)."""
        pesos = {
            "hospital": 3,
            "especialidade": 3,
            "data": 2,
            "hora_inicio": 1,
            "hora_fim": 1,
            "valor": 2,
        }
        total_peso = sum(pesos.values())
        soma = (
            self.hospital * pesos["hospital"] +
            self.especialidade * pesos["especialidade"] +
            self.data * pesos["data"] +
            self.hora_inicio * pesos["hora_inicio"] +
            self.hora_fim * pesos["hora_fim"] +
            self.valor * pesos["valor"]
        )
        return soma / total_peso
```

**Nota:** Manter estrutura existente - confianca de valor aplica ao conjunto (tipo + valores).

**DoD:**
- [ ] Confianca funcionando para novos campos
- [ ] Media ponderada calculando corretamente

---

## Arquivos Modificados

| Arquivo | Linha | Acao | Descricao |
|---------|-------|------|-----------|
| `app/services/grupos/extrator.py` | 30-45 | Modificar | Atualizar DadosVagaExtraida |
| `app/services/grupos/extrator.py` | 100-170 | Modificar | Atualizar _parsear_resposta_extracao |
| `app/services/grupos/extrator.py` | +nova | Criar | _parsear_valor_seguro |
| `app/services/grupos/extrator.py` | +nova | Criar | _validar_valor |
| `app/services/grupos/prompts.py` | 65-135 | Modificar | Atualizar PROMPT_EXTRACAO |

---

## Testes Necessarios

### Testes Unitarios

**Arquivo:** `tests/grupos/test_extrator.py`

```python
class TestParsearValorSeguro:
    def test_valor_inteiro(self):
        assert _parsear_valor_seguro(1800) == 1800

    def test_valor_string_numero(self):
        assert _parsear_valor_seguro("1800") == 1800

    def test_valor_string_formatado(self):
        assert _parsear_valor_seguro("1.800") == 1800

    def test_valor_string_com_prefixo(self):
        assert _parsear_valor_seguro("R$ 1.800") == 1800

    def test_valor_a_combinar(self):
        assert _parsear_valor_seguro("A combinar") is None

    def test_valor_none(self):
        assert _parsear_valor_seguro(None) is None

    def test_valor_zero(self):
        assert _parsear_valor_seguro(0) is None

    def test_valor_negativo(self):
        assert _parsear_valor_seguro(-100) is None


class TestValidarValor:
    def test_fixo_valido(self):
        result = _validar_valor("fixo", 1800, None, None)
        assert result == ("fixo", 1800, None, None)

    def test_fixo_sem_valor_vira_a_combinar(self):
        result = _validar_valor("fixo", None, None, None)
        assert result == ("a_combinar", None, None, None)

    def test_a_combinar(self):
        result = _validar_valor("a_combinar", None, None, None)
        assert result == ("a_combinar", None, None, None)

    def test_faixa_completa(self):
        result = _validar_valor("faixa", None, 1500, 2000)
        assert result == ("faixa", None, 1500, 2000)

    def test_faixa_so_minimo(self):
        result = _validar_valor("faixa", None, 1500, None)
        assert result == ("faixa", None, 1500, None)

    def test_faixa_invertida_corrige(self):
        result = _validar_valor("faixa", None, 2000, 1500)
        assert result == ("faixa", None, 1500, 2000)

    def test_faixa_sem_limites_vira_a_combinar(self):
        result = _validar_valor("faixa", None, None, None)
        assert result == ("a_combinar", None, None, None)
```

**DoD:**
- [ ] Todos os testes unitarios passando
- [ ] Cobertura >= 90% nas funcoes novas

---

## DoD do Epico

- [ ] T01 completa - Dataclass atualizada
- [ ] T02 completa - Prompt atualizado
- [ ] T03 completa - Parsing seguro
- [ ] T04 completa - Confianca funcionando
- [ ] Testes unitarios passando
- [ ] Nenhuma regressao em vagas fixas
- [ ] Testado com mensagens reais de "a combinar"

---

## Checklist de Validacao

```python
# Testar extracao com mensagens reais
from app.services.grupos.extrator import extrair_dados_mensagem

# Teste 1: Valor fixo
msg1 = "Plantao CM Hospital ABC dia 30/12 noturno R$ 1.800 PJ"
result1 = await extrair_dados_mensagem(msg1)
assert result1.vagas[0].dados.valor_tipo == "fixo"
assert result1.vagas[0].dados.valor == 1800

# Teste 2: A combinar
msg2 = "Plantao CM Hospital ABC dia 30/12 noturno - valor a combinar"
result2 = await extrair_dados_mensagem(msg2)
assert result2.vagas[0].dados.valor_tipo == "a_combinar"
assert result2.vagas[0].dados.valor is None

# Teste 3: Sem mencao de valor
msg3 = "Plantao CM Hospital ABC dia 30/12 noturno"
result3 = await extrair_dados_mensagem(msg3)
assert result3.vagas[0].dados.valor_tipo == "a_combinar"

# Teste 4: Faixa
msg4 = "Plantao CM Hospital ABC dia 30/12 noturno entre 1.500 e 2.000"
result4 = await extrair_dados_mensagem(msg4)
assert result4.vagas[0].dados.valor_tipo == "faixa"
assert result4.vagas[0].dados.valor_minimo == 1500
assert result4.vagas[0].dados.valor_maximo == 2000
```
