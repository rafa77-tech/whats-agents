# Epic 1: Múltiplas Especialidades

## Objetivo

> **Expandir Júlia para atender múltiplas especialidades médicas.**

---

## Stories

---

# S5.E1.1 - Adaptar prompt por especialidade

## Objetivo

> **Personalizar comportamento da Júlia por especialidade.**

**Resultado esperado:** Júlia usa vocabulário e contexto correto para cada especialidade.

## Contexto

Cada especialidade tem:
- Vocabulário específico
- Tipos de plantão diferentes
- Faixa de valor diferente
- Demanda por região diferente

## Tarefas

### 1. Criar configuração por especialidade

```python
# app/config/especialidades.py

CONFIGURACOES_ESPECIALIDADE = {
    "anestesiologia": {
        "nome_display": "anestesista",
        "tipo_plantao": ["cirúrgico", "obstétrico", "UTI"],
        "valor_medio": "R$ 2.000 - R$ 3.500",
        "vocabulario": {
            "procedimentos": ["anestesia geral", "raqui", "peridural"],
            "setores": ["centro cirúrgico", "sala de parto", "UTI"],
        },
        "contexto_extra": "Anestesistas geralmente preferem plantões de 12h ou 24h.",
    },
    "cardiologia": {
        "nome_display": "cardiologista",
        "tipo_plantao": ["emergência", "UTI coronariana", "consultório"],
        "valor_medio": "R$ 1.800 - R$ 3.000",
        "vocabulario": {
            "procedimentos": ["eco", "eletro", "cateterismo"],
            "setores": ["UTI cardio", "emergência", "hemodinâmica"],
        },
        "contexto_extra": "Cardiologistas têm alta demanda em UTIs e emergências.",
    },
    "clinica_medica": {
        "nome_display": "clínico",
        "tipo_plantao": ["PS", "enfermaria", "UTI"],
        "valor_medio": "R$ 1.200 - R$ 2.000",
        "vocabulario": {
            "procedimentos": ["prescrição", "evolução", "alta"],
            "setores": ["PS", "enfermaria", "UTI geral"],
        },
        "contexto_extra": "Clínicos são muito requisitados em PS e enfermarias.",
    },
    "pediatria": {
        "nome_display": "pediatra",
        "tipo_plantao": ["PS pediátrico", "UTI neo", "berçário"],
        "valor_medio": "R$ 1.500 - R$ 2.500",
        "vocabulario": {
            "procedimentos": ["puericultura", "emergência pediátrica"],
            "setores": ["PS pediátrico", "UTI neo", "alojamento conjunto"],
        },
        "contexto_extra": "Pediatras têm alta demanda em maternidades.",
    },
    "ortopedia": {
        "nome_display": "ortopedista",
        "tipo_plantao": ["emergência", "centro cirúrgico", "ambulatório"],
        "valor_medio": "R$ 1.800 - R$ 3.000",
        "vocabulario": {
            "procedimentos": ["redução", "imobilização", "cirurgia"],
            "setores": ["ortopedia", "trauma", "centro cirúrgico"],
        },
        "contexto_extra": "Ortopedistas são muito procurados para trauma.",
    },
}


def obter_config_especialidade(especialidade_nome: str) -> dict:
    """Retorna configuração da especialidade."""
    nome_normalizado = especialidade_nome.lower().replace(" ", "_")
    return CONFIGURACOES_ESPECIALIDADE.get(nome_normalizado, {})
```

### 2. Injetar contexto no prompt

```python
# app/services/contexto.py (atualizar)

def montar_contexto_especialidade(medico: dict) -> str:
    """Monta contexto específico da especialidade."""
    especialidade = medico.get("especialidade_nome", "").lower()
    config = obter_config_especialidade(especialidade)

    if not config:
        return ""

    return f"""
## Informações da Especialidade ({config['nome_display']})

- Tipos de plantão comuns: {', '.join(config['tipo_plantao'])}
- Faixa de valor: {config['valor_medio']}
- Setores: {', '.join(config['vocabulario']['setores'])}
- Contexto: {config['contexto_extra']}
"""


async def montar_contexto_completo(medico: dict, conversa: dict) -> dict:
    """Monta contexto completo incluindo especialidade."""
    contexto = {
        "medico": formatar_contexto_medico(medico),
        "especialidade": montar_contexto_especialidade(medico),
        # ... outros contextos ...
    }

    return contexto
```

### 3. Adaptar saudação por especialidade

```python
# app/templates/mensagens.py (atualizar)

SAUDACOES_ESPECIALIDADE = {
    "anestesiologia": "Vi que vc é anestesista, certo? Temos umas vagas bem interessantes em centro cirúrgico",
    "cardiologia": "Vi que vc é cardio, certo? Temos vagas em UTI e emergência que podem te interessar",
    "clinica_medica": "Vi que vc é clínico, né? Sempre tem vaga boa de PS e enfermaria",
    "pediatria": "Vi que vc é pediatra! Temos vagas legais em PS pediátrico e maternidade",
    "ortopedia": "Vi que vc é ortopedista! Sempre surge vaga boa de trauma e centro cirúrgico",
}

def obter_saudacao_especialidade(especialidade: str) -> str:
    """Retorna saudação personalizada para especialidade."""
    nome_normalizado = especialidade.lower().replace(" ", "_")
    return SAUDACOES_ESPECIALIDADE.get(
        nome_normalizado,
        "Vi que você é médico, certo? Temos umas vagas interessantes"
    )
```

## DoD

- [ ] Configuração de 5+ especialidades
- [ ] Contexto injetado no prompt
- [ ] Saudação personalizada por especialidade
- [ ] Vocabulário correto usado
- [ ] Testes com cada especialidade

---

# S5.E1.2 - Carregar vagas por especialidade

## Objetivo

> **Filtrar e apresentar vagas corretas para cada especialidade.**

**Resultado esperado:** Médico só vê vagas da sua especialidade.

## Tarefas

### 1. Atualizar busca de vagas

```python
# app/services/vaga.py (atualizar)

async def buscar_vagas_compativeis(
    medico: dict,
    limite: int = 5
) -> list[dict]:
    """
    Busca vagas compatíveis com o médico.

    Filtros:
    - Especialidade do médico
    - Região preferida (se houver)
    - Hospitais não bloqueados
    - Status = aberta
    - Data >= hoje
    """
    especialidade_id = medico.get("especialidade_id")
    if not especialidade_id:
        return []

    # Query base
    query = (
        supabase.table("vagas")
        .select("""
            *,
            hospitais(id, nome, endereco, cidade),
            periodos(id, nome, hora_inicio, hora_fim),
            setores(id, nome)
        """)
        .eq("especialidade_id", especialidade_id)
        .eq("status", "aberta")
        .gte("data_plantao", date.today().isoformat())
        .order("prioridade", desc=True)
        .order("data_plantao")
        .limit(limite * 2)  # Buscar mais para filtrar
    )

    response = query.execute()
    vagas = response.data

    # Aplicar filtros do médico
    preferencias = medico.get("preferencias", {})
    vagas_filtradas = filtrar_por_preferencias(vagas, preferencias)

    return vagas_filtradas[:limite]
```

### 2. Formatar vagas para contexto

```python
def formatar_vagas_contexto(vagas: list, especialidade: str) -> str:
    """Formata vagas para incluir no contexto do LLM."""
    if not vagas:
        return "Não há vagas disponíveis no momento para esta especialidade."

    config = obter_config_especialidade(especialidade)
    texto = f"## Vagas Disponíveis para {config.get('nome_display', 'médico')}:\n\n"

    for i, v in enumerate(vagas[:5], 1):
        hospital = v.get("hospitais", {})
        periodo = v.get("periodos", {})
        setor = v.get("setores", {})

        texto += f"""
**Vaga {i}:**
- Hospital: {hospital.get('nome', 'N/A')} ({hospital.get('cidade', 'N/A')})
- Data: {v.get('data_plantao')}
- Período: {periodo.get('nome', 'N/A')} ({periodo.get('hora_inicio')}-{periodo.get('hora_fim')})
- Setor: {setor.get('nome', 'N/A')}
- Valor: R$ {v.get('valor_min', 'N/A')} - R$ {v.get('valor_max', 'N/A')}
- ID: {v.get('id')}
"""

    return texto
```

## DoD

- [ ] Busca filtra por especialidade
- [ ] Vagas formatadas no contexto
- [ ] Preferências do médico aplicadas
- [ ] Ordenação por prioridade
- [ ] Testes por especialidade

---

# S5.E1.3 - Cadastrar hospitais por região

## Objetivo

> **Expandir base de hospitais para múltiplas regiões.**

**Resultado esperado:** Hospitais de SP, ABC, Campinas e outras regiões cadastrados.

## Tarefas

### 1. Estrutura de dados de região

```python
# app/config/regioes.py

REGIOES = {
    "abc": {
        "nome": "ABC Paulista",
        "cidades": ["Santo André", "São Bernardo do Campo", "São Caetano do Sul", "Diadema", "Mauá", "Ribeirão Pires", "Rio Grande da Serra"],
        "ddds": ["11"],
    },
    "sp_capital": {
        "nome": "São Paulo Capital",
        "cidades": ["São Paulo"],
        "ddds": ["11"],
    },
    "campinas": {
        "nome": "Região de Campinas",
        "cidades": ["Campinas", "Sumaré", "Hortolândia", "Indaiatuba", "Valinhos"],
        "ddds": ["19"],
    },
    "baixada_santista": {
        "nome": "Baixada Santista",
        "cidades": ["Santos", "São Vicente", "Guarujá", "Praia Grande"],
        "ddds": ["13"],
    },
}
```

### 2. Script de importação de hospitais

```python
# scripts/importar_hospitais.py

async def importar_hospitais_regiao(regiao: str, hospitais: list[dict]):
    """
    Importa lista de hospitais para uma região.

    Formato esperado:
    [{
        "nome": "Hospital ABC",
        "endereco": "Rua X, 123",
        "cidade": "Santo André",
        "cnpj": "00.000.000/0001-00",
        "contato": "contato@hospital.com",
        "especialidades": ["anestesiologia", "cardiologia"]
    }]
    """
    for hosp in hospitais:
        # Verificar se já existe
        existente = (
            supabase.table("hospitais")
            .select("id")
            .eq("cnpj", hosp.get("cnpj"))
            .execute()
        ).data

        if existente:
            print(f"Hospital já existe: {hosp['nome']}")
            continue

        # Inserir hospital
        hospital = (
            supabase.table("hospitais")
            .insert({
                "nome": hosp["nome"],
                "endereco": hosp.get("endereco"),
                "cidade": hosp["cidade"],
                "estado": "SP",
                "cnpj": hosp.get("cnpj"),
                "contato_email": hosp.get("contato"),
                "regiao": regiao,
                "status": "ativo"
            })
            .execute()
        ).data[0]

        # Associar especialidades
        for esp_nome in hosp.get("especialidades", []):
            especialidade = (
                supabase.table("especialidades")
                .select("id")
                .eq("nome", esp_nome)
                .single()
                .execute()
            ).data

            if especialidade:
                supabase.table("hospital_especialidades").insert({
                    "hospital_id": hospital["id"],
                    "especialidade_id": especialidade["id"]
                }).execute()

        print(f"✅ Importado: {hosp['nome']}")
```

### 3. Filtro de vagas por região do médico

```python
# app/services/vaga.py (adicionar)

async def buscar_vagas_por_regiao(
    medico: dict,
    limite: int = 5
) -> list[dict]:
    """Busca vagas priorizando região do médico."""

    # Detectar região pelo telefone
    telefone = medico.get("telefone", "")
    ddd = telefone[3:5] if len(telefone) > 5 else "11"

    regiao_medico = None
    for regiao, config in REGIOES.items():
        if ddd in config["ddds"]:
            regiao_medico = regiao
            break

    # Buscar vagas priorizando região
    vagas = await buscar_vagas_compativeis(medico, limite * 2)

    # Ordenar: vagas da região primeiro
    def prioridade_regiao(vaga):
        hospital = vaga.get("hospitais", {})
        if hospital.get("regiao") == regiao_medico:
            return 0  # Alta prioridade
        return 1

    vagas_ordenadas = sorted(vagas, key=prioridade_regiao)
    return vagas_ordenadas[:limite]
```

## DoD

- [ ] Estrutura de regiões definida
- [ ] Script de importação funciona
- [ ] Hospitais associados a especialidades
- [ ] Filtro por região do médico
- [ ] Pelo menos 20 hospitais cadastrados

---

# S5.E1.4 - Testar com novas especialidades

## Objetivo

> **Validar que Júlia funciona bem com todas as especialidades.**

**Resultado esperado:** Testes passando para 5+ especialidades.

## Tarefas

### 1. Criar suite de testes por especialidade

```python
# tests/test_especialidades.py

import pytest
from app.config.especialidades import CONFIGURACOES_ESPECIALIDADE
from tests.persona.test_runner import PersonaTestRunner

CENARIOS_POR_ESPECIALIDADE = {
    "anestesiologia": [
        "Oi, sou anestesista e tô procurando plantão",
        "Tem vaga de anestesia em centro cirúrgico?",
        "Quanto tá pagando o plantão de 24h?",
    ],
    "cardiologia": [
        "Olá, sou cardiologista, tem vaga?",
        "Procuro plantão em UTI coronariana",
        "Tem algo em hemodinâmica?",
    ],
    "clinica_medica": [
        "Oi, sou clínico geral",
        "Tem vaga de PS ou enfermaria?",
        "Quanto paga o plantão de 12h?",
    ],
    "pediatria": [
        "Oi! Sou pediatra",
        "Tem vaga em PS pediátrico?",
        "Vocês tem algo em maternidade?",
    ],
    "ortopedia": [
        "E aí, sou ortopedista",
        "Tem plantão de trauma?",
        "Procuro vaga em centro cirúrgico",
    ],
}


@pytest.mark.asyncio
@pytest.mark.parametrize("especialidade", CONFIGURACOES_ESPECIALIDADE.keys())
async def test_contexto_especialidade(especialidade):
    """Testa que contexto correto é carregado para cada especialidade."""
    from app.services.contexto import montar_contexto_especialidade

    medico = {
        "especialidade_nome": especialidade,
        "primeiro_nome": "Dr. Teste"
    }

    contexto = montar_contexto_especialidade(medico)

    config = CONFIGURACOES_ESPECIALIDADE[especialidade]
    assert config["nome_display"] in contexto.lower()


@pytest.mark.asyncio
@pytest.mark.parametrize("especialidade", CENARIOS_POR_ESPECIALIDADE.keys())
async def test_respostas_especialidade(especialidade):
    """Testa respostas para cenários de cada especialidade."""
    runner = PersonaTestRunner()

    medico_contexto = {
        "medico": {
            "primeiro_nome": "Carlos",
            "especialidade_nome": especialidade
        }
    }

    for mensagem in CENARIOS_POR_ESPECIALIDADE[especialidade]:
        resultado = await runner.testar_resposta(
            mensagem_medico=mensagem,
            contexto=medico_contexto
        )
        assert resultado["passou"], f"Falhou em {especialidade}: {mensagem}"
```

### 2. Teste de consistência de vocabulário

```python
@pytest.mark.asyncio
async def test_vocabulario_correto():
    """Verifica que Júlia usa vocabulário da especialidade."""
    runner = PersonaTestRunner()

    for especialidade, config in CONFIGURACOES_ESPECIALIDADE.items():
        medico_contexto = {
            "medico": {
                "primeiro_nome": "Maria",
                "especialidade_nome": especialidade
            }
        }

        resultado = await runner.testar_resposta(
            mensagem_medico="Me conta sobre as vagas",
            contexto=medico_contexto
        )

        resposta = resultado["resposta"].lower()

        # Verificar que menciona algo relevante
        menciona_relevante = any(
            termo.lower() in resposta
            for termo in config["vocabulario"]["setores"]
        )

        # Não é crítico, mas desejável
        if not menciona_relevante:
            print(f"⚠️ {especialidade}: não mencionou termos específicos")
```

### 3. Teste de vagas por especialidade

```python
@pytest.mark.asyncio
async def test_vagas_filtradas_por_especialidade():
    """Verifica que vagas são filtradas corretamente."""
    from app.services.vaga import buscar_vagas_compativeis

    for especialidade in ["anestesiologia", "cardiologia", "pediatria"]:
        # Criar médico mock
        medico = {
            "id": "test-" + especialidade,
            "especialidade_id": await obter_especialidade_id(especialidade),
            "especialidade_nome": especialidade
        }

        vagas = await buscar_vagas_compativeis(medico, limite=10)

        # Todas as vagas devem ser da especialidade
        for vaga in vagas:
            assert vaga["especialidade_id"] == medico["especialidade_id"], \
                f"Vaga de especialidade errada retornada para {especialidade}"
```

## DoD

- [ ] Testes para 5 especialidades
- [ ] Contexto correto para cada uma
- [ ] Vocabulário adequado
- [ ] Vagas filtradas corretamente
- [ ] Taxa de aprovação > 90%
