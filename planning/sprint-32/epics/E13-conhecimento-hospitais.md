# E13 - Conhecimento de Hospitais

**Sprint:** 32 - Redesign de Campanhas e Comportamento Julia
**Fase:** 4 - Arquitetura de Dados
**Dependências:** Nenhuma (E11 depende deste)
**Estimativa:** 3h

---

## Objetivo

Criar estrutura de dados para armazenar **conhecimento sobre hospitais** - informações factuais que Julia aprende e pode usar para responder médicos.

---

## Contexto

Médicos frequentemente perguntam sobre hospitais:
- "Tem estacionamento?"
- "Refeição é inclusa?"
- "Tem vestiário?"
- "Aceita carro na garagem?"
- "Qual o horário de entrada?"

Atualmente Julia não sabe essas informações e precisa perguntar ao gestor toda vez.

---

## Solução

Tabela `conhecimento_hospitais` que armazena atributos de hospitais com suas fontes (gestor, médico, sistema).

```
┌─────────────────────────────────────────────────────┐
│              conhecimento_hospitais                 │
├─────────────────────────────────────────────────────┤
│ hospital_id  │ atributo        │ valor             │
├──────────────┼─────────────────┼───────────────────┤
│ hospital-123 │ estacionamento  │ Sim, gratuito     │
│ hospital-123 │ refeicao        │ Refeitório 24h    │
│ hospital-123 │ vestiario       │ Sim, com armário  │
│ hospital-456 │ estacionamento  │ Não tem           │
│ hospital-456 │ refeicao        │ Não inclusa       │
└──────────────┴─────────────────┴───────────────────┘
```

---

## Tasks

### T1: Criar tabela conhecimento_hospitais (30min)

**Migration:** `criar_conhecimento_hospitais`

```sql
-- Migration: criar_conhecimento_hospitais
-- Armazena conhecimento factual sobre hospitais

CREATE TABLE conhecimento_hospitais (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Referência ao hospital
    hospital_id UUID NOT NULL REFERENCES hospitais(id) ON DELETE CASCADE,

    -- Atributo e valor
    atributo TEXT NOT NULL,
    valor TEXT NOT NULL,

    -- Metadados de origem
    fonte TEXT NOT NULL DEFAULT 'gestor'
        CHECK (fonte IN ('gestor', 'medico', 'sistema', 'importacao')),
    criado_por TEXT,  -- ID do gestor/médico que informou
    confianca DECIMAL(3, 2) DEFAULT 1.0,  -- 0.00 a 1.00

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    -- Constraint de unicidade
    UNIQUE(hospital_id, atributo)
);

-- Índices
CREATE INDEX idx_conhecimento_hospital ON conhecimento_hospitais(hospital_id);
CREATE INDEX idx_conhecimento_atributo ON conhecimento_hospitais(atributo);
CREATE INDEX idx_conhecimento_fonte ON conhecimento_hospitais(fonte);

-- Comentários
COMMENT ON TABLE conhecimento_hospitais IS 'Conhecimento factual sobre hospitais';
COMMENT ON COLUMN conhecimento_hospitais.atributo IS 'estacionamento, refeicao, vestiario, wifi, etc.';
COMMENT ON COLUMN conhecimento_hospitais.fonte IS 'Quem informou: gestor, medico, sistema ou importacao';
COMMENT ON COLUMN conhecimento_hospitais.confianca IS 'Nível de confiança de 0 a 1 (1 = certeza absoluta)';

-- Trigger para updated_at
CREATE OR REPLACE FUNCTION update_conhecimento_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_conhecimento_updated_at
    BEFORE UPDATE ON conhecimento_hospitais
    FOR EACH ROW
    EXECUTE FUNCTION update_conhecimento_timestamp();

-- RLS
ALTER TABLE conhecimento_hospitais ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Leitura para authenticated"
ON conhecimento_hospitais FOR SELECT
TO authenticated
USING (true);

CREATE POLICY "Escrita para service role"
ON conhecimento_hospitais FOR ALL
TO service_role
USING (true);
```

---

### T2: Criar enum de atributos conhecidos (30min)

Lista padronizada de atributos para consistência.

**Arquivo:** `app/services/conhecimento/atributos.py`

```python
"""
Atributos conhecidos para hospitais.

Manter lista padronizada para consistência e busca.
"""
from enum import Enum


class AtributoHospital(str, Enum):
    """Atributos que podem ser armazenados sobre hospitais."""

    # Infraestrutura
    ESTACIONAMENTO = "estacionamento"
    REFEICAO = "refeicao"
    VESTIARIO = "vestiario"
    DESCANSO = "descanso"
    WIFI = "wifi"
    AR_CONDICIONADO = "ar_condicionado"
    CAFE = "cafe"
    ARMARIO = "armario"

    # Acesso
    HORARIO_ENTRADA = "horario_entrada"
    PORTARIA = "portaria"
    ACESSO_FUNCIONARIOS = "acesso_funcionarios"

    # Contato
    TELEFONE_PLANTAO = "telefone_plantao"
    CONTATO_EMERGENCIA = "contato_emergencia"

    # Pagamento
    DIA_PAGAMENTO = "dia_pagamento"
    FORMA_PAGAMENTO = "forma_pagamento"

    # Operacional
    UNIFORME = "uniforme"
    DOCUMENTOS_NECESSARIOS = "documentos_necessarios"


# Mapeamento de sinônimos para busca
SINONIMOS_ATRIBUTOS = {
    AtributoHospital.ESTACIONAMENTO: [
        "estacionamento", "estacionar", "carro", "vaga carro",
        "garagem", "parking", "vaga de carro"
    ],
    AtributoHospital.REFEICAO: [
        "refeição", "refeicao", "comida", "almoço", "almoco",
        "jantar", "refeitório", "refeitorio", "alimentação",
        "alimentacao", "café da manhã", "lanche"
    ],
    AtributoHospital.VESTIARIO: [
        "vestiário", "vestiario", "trocar roupa", "armário",
        "armario", "trocar", "vestir"
    ],
    AtributoHospital.DESCANSO: [
        "descanso", "dormir", "repouso", "sala de descanso",
        "quarto de descanso", "descansar"
    ],
    AtributoHospital.WIFI: [
        "wifi", "wi-fi", "internet", "rede"
    ],
    AtributoHospital.AR_CONDICIONADO: [
        "ar condicionado", "ar-condicionado", "climatizado",
        "ar", "clima"
    ],
    AtributoHospital.CAFE: [
        "café", "cafe", "copa", "cafezinho"
    ],
    AtributoHospital.HORARIO_ENTRADA: [
        "horário de entrada", "horario de entrada",
        "que horas entrar", "hora de chegada"
    ],
}


def identificar_atributo(texto: str) -> AtributoHospital | None:
    """
    Identifica atributo a partir de texto livre.

    Args:
        texto: Texto contendo possível referência ao atributo

    Returns:
        AtributoHospital ou None se não identificado
    """
    texto_lower = texto.lower()

    for atributo, sinonimos in SINONIMOS_ATRIBUTOS.items():
        for sinonimo in sinonimos:
            if sinonimo in texto_lower:
                return atributo

    return None


def get_descricao_atributo(atributo: AtributoHospital) -> str:
    """
    Retorna descrição amigável do atributo.

    Args:
        atributo: Enum do atributo

    Returns:
        Descrição para exibição
    """
    descricoes = {
        AtributoHospital.ESTACIONAMENTO: "Estacionamento",
        AtributoHospital.REFEICAO: "Refeição",
        AtributoHospital.VESTIARIO: "Vestiário",
        AtributoHospital.DESCANSO: "Sala de descanso",
        AtributoHospital.WIFI: "Wi-Fi",
        AtributoHospital.AR_CONDICIONADO: "Ar-condicionado",
        AtributoHospital.CAFE: "Café/Copa",
        AtributoHospital.ARMARIO: "Armário",
        AtributoHospital.HORARIO_ENTRADA: "Horário de entrada",
        AtributoHospital.PORTARIA: "Portaria",
        AtributoHospital.ACESSO_FUNCIONARIOS: "Acesso funcionários",
        AtributoHospital.TELEFONE_PLANTAO: "Telefone do plantão",
        AtributoHospital.CONTATO_EMERGENCIA: "Contato de emergência",
        AtributoHospital.DIA_PAGAMENTO: "Dia do pagamento",
        AtributoHospital.FORMA_PAGAMENTO: "Forma de pagamento",
        AtributoHospital.UNIFORME: "Uniforme",
        AtributoHospital.DOCUMENTOS_NECESSARIOS: "Documentos necessários",
    }
    return descricoes.get(atributo, atributo.value)
```

---

### T3: Criar repositório CRUD (45min)

**Arquivo:** `app/services/conhecimento/repositorio.py`

```python
"""
Repositório para conhecimento de hospitais.
"""
from datetime import datetime
from app.services.supabase import supabase
from app.services.conhecimento.atributos import AtributoHospital, get_descricao_atributo
from app.core.logging import get_logger

logger = get_logger(__name__)


async def criar_conhecimento(
    hospital_id: str,
    atributo: str | AtributoHospital,
    valor: str,
    fonte: str = "gestor",
    criado_por: str | None = None,
    confianca: float = 1.0
) -> dict:
    """
    Cria ou atualiza conhecimento sobre hospital.

    Usa UPSERT - se atributo já existe para o hospital, atualiza.

    Args:
        hospital_id: ID do hospital
        atributo: Atributo (string ou enum)
        valor: Valor do atributo
        fonte: gestor, medico, sistema ou importacao
        criado_por: ID de quem informou
        confianca: Nível de confiança (0.0 a 1.0)

    Returns:
        Registro criado/atualizado
    """
    if isinstance(atributo, AtributoHospital):
        atributo = atributo.value

    dados = {
        "hospital_id": hospital_id,
        "atributo": atributo,
        "valor": valor,
        "fonte": fonte,
        "criado_por": criado_por,
        "confianca": confianca,
        "updated_at": datetime.utcnow().isoformat()
    }

    resultado = supabase.table("conhecimento_hospitais").upsert(
        dados,
        on_conflict="hospital_id,atributo"
    ).execute()

    if resultado.data:
        logger.info(
            f"Conhecimento salvo: hospital={hospital_id}, "
            f"atributo={atributo}, valor={valor}, fonte={fonte}"
        )
        return resultado.data[0]

    return None


async def buscar_conhecimento(
    hospital_id: str,
    atributo: str | AtributoHospital | None = None
) -> list[dict]:
    """
    Busca conhecimento de um hospital.

    Args:
        hospital_id: ID do hospital
        atributo: Atributo específico (opcional)

    Returns:
        Lista de conhecimentos
    """
    query = supabase.table("conhecimento_hospitais").select("*").eq(
        "hospital_id", hospital_id
    )

    if atributo:
        if isinstance(atributo, AtributoHospital):
            atributo = atributo.value
        query = query.eq("atributo", atributo)

    resultado = query.order("atributo").execute()
    return resultado.data or []


async def buscar_conhecimento_valor(
    hospital_id: str,
    atributo: str | AtributoHospital
) -> str | None:
    """
    Busca valor específico de um atributo.

    Retorna apenas o valor, ou None se não existir.

    Args:
        hospital_id: ID do hospital
        atributo: Atributo a buscar

    Returns:
        Valor do atributo ou None
    """
    conhecimentos = await buscar_conhecimento(hospital_id, atributo)

    if conhecimentos:
        return conhecimentos[0]["valor"]

    return None


async def listar_hospitais_com_atributo(
    atributo: str | AtributoHospital,
    valor_contem: str | None = None
) -> list[dict]:
    """
    Lista hospitais que têm determinado atributo.

    Args:
        atributo: Atributo a buscar
        valor_contem: Filtro opcional no valor

    Returns:
        Lista de hospitais com o atributo
    """
    if isinstance(atributo, AtributoHospital):
        atributo = atributo.value

    query = supabase.table("conhecimento_hospitais").select(
        "*, hospitais(id, nome, cidade)"
    ).eq("atributo", atributo)

    if valor_contem:
        query = query.ilike("valor", f"%{valor_contem}%")

    resultado = query.execute()
    return resultado.data or []


async def deletar_conhecimento(
    hospital_id: str,
    atributo: str | AtributoHospital
) -> bool:
    """
    Remove conhecimento específico.

    Args:
        hospital_id: ID do hospital
        atributo: Atributo a remover

    Returns:
        True se deletou, False se não existia
    """
    if isinstance(atributo, AtributoHospital):
        atributo = atributo.value

    resultado = supabase.table("conhecimento_hospitais").delete().eq(
        "hospital_id", hospital_id
    ).eq("atributo", atributo).execute()

    deletou = len(resultado.data or []) > 0

    if deletou:
        logger.info(f"Conhecimento deletado: hospital={hospital_id}, atributo={atributo}")

    return deletou


async def formatar_conhecimento_para_prompt(hospital_id: str) -> str:
    """
    Formata todo conhecimento do hospital para injeção no prompt.

    Args:
        hospital_id: ID do hospital

    Returns:
        String formatada para prompt
    """
    conhecimentos = await buscar_conhecimento(hospital_id)

    if not conhecimentos:
        return ""

    linhas = ["## INFORMAÇÕES CONHECIDAS SOBRE O HOSPITAL\n"]

    for c in conhecimentos:
        atributo_enum = None
        try:
            atributo_enum = AtributoHospital(c["atributo"])
        except ValueError:
            pass

        nome_atributo = (
            get_descricao_atributo(atributo_enum)
            if atributo_enum
            else c["atributo"].replace("_", " ").title()
        )

        linhas.append(f"- **{nome_atributo}:** {c['valor']}")

    return "\n".join(linhas)


async def contar_conhecimentos_por_hospital(hospital_id: str) -> int:
    """
    Conta quantos atributos conhecemos do hospital.

    Args:
        hospital_id: ID do hospital

    Returns:
        Quantidade de conhecimentos
    """
    resultado = supabase.table("conhecimento_hospitais").select(
        "id", count="exact"
    ).eq("hospital_id", hospital_id).execute()

    return resultado.count or 0


async def listar_hospitais_sem_conhecimento(
    atributos_obrigatorios: list[str] | None = None
) -> list[dict]:
    """
    Lista hospitais que não têm conhecimento registrado.

    Útil para identificar hospitais que precisam de enriquecimento.

    Args:
        atributos_obrigatorios: Lista de atributos que todo hospital deveria ter

    Returns:
        Lista de hospitais sem conhecimento completo
    """
    if not atributos_obrigatorios:
        atributos_obrigatorios = [
            AtributoHospital.ESTACIONAMENTO.value,
            AtributoHospital.REFEICAO.value,
        ]

    # Buscar todos os hospitais
    hospitais = supabase.table("hospitais").select("id, nome, cidade").execute()

    hospitais_incompletos = []

    for hospital in hospitais.data or []:
        conhecimentos = await buscar_conhecimento(hospital["id"])
        atributos_existentes = [c["atributo"] for c in conhecimentos]

        faltando = [a for a in atributos_obrigatorios if a not in atributos_existentes]

        if faltando:
            hospitais_incompletos.append({
                **hospital,
                "atributos_faltando": faltando
            })

    return hospitais_incompletos
```

---

### T4: Criar endpoints de API (30min)

**Arquivo:** `app/api/routes/conhecimento.py`

```python
"""
Endpoints para gestão de conhecimento de hospitais.
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from app.services.conhecimento.repositorio import (
    criar_conhecimento,
    buscar_conhecimento,
    deletar_conhecimento,
    listar_hospitais_com_atributo,
    listar_hospitais_sem_conhecimento
)
from app.services.conhecimento.atributos import AtributoHospital
from app.api.deps import get_current_user

router = APIRouter(prefix="/conhecimento", tags=["conhecimento"])


class CriarConhecimentoRequest(BaseModel):
    hospital_id: str
    atributo: str
    valor: str
    fonte: str = "gestor"


class CriarConhecimentoResponse(BaseModel):
    id: str
    hospital_id: str
    atributo: str
    valor: str


@router.post("/", response_model=CriarConhecimentoResponse)
async def api_criar_conhecimento(
    request: CriarConhecimentoRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Cria ou atualiza conhecimento sobre hospital.

    Se o atributo já existir para o hospital, atualiza o valor.
    """
    resultado = await criar_conhecimento(
        hospital_id=request.hospital_id,
        atributo=request.atributo,
        valor=request.valor,
        fonte=request.fonte,
        criado_por=current_user["id"]
    )

    if not resultado:
        raise HTTPException(status_code=500, detail="Erro ao salvar conhecimento")

    return resultado


@router.get("/hospital/{hospital_id}")
async def api_buscar_conhecimento_hospital(hospital_id: str):
    """
    Busca todo conhecimento de um hospital.
    """
    return await buscar_conhecimento(hospital_id)


@router.get("/hospital/{hospital_id}/{atributo}")
async def api_buscar_conhecimento_atributo(hospital_id: str, atributo: str):
    """
    Busca atributo específico de um hospital.
    """
    conhecimentos = await buscar_conhecimento(hospital_id, atributo)

    if not conhecimentos:
        raise HTTPException(status_code=404, detail="Conhecimento não encontrado")

    return conhecimentos[0]


@router.delete("/hospital/{hospital_id}/{atributo}")
async def api_deletar_conhecimento(
    hospital_id: str,
    atributo: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Remove conhecimento específico.
    """
    deletou = await deletar_conhecimento(hospital_id, atributo)

    if not deletou:
        raise HTTPException(status_code=404, detail="Conhecimento não encontrado")

    return {"deleted": True}


@router.get("/atributo/{atributo}")
async def api_listar_por_atributo(atributo: str):
    """
    Lista todos os hospitais que têm determinado atributo.
    """
    return await listar_hospitais_com_atributo(atributo)


@router.get("/atributos")
async def api_listar_atributos():
    """
    Lista todos os atributos conhecidos.
    """
    return [
        {"codigo": a.value, "nome": a.name}
        for a in AtributoHospital
    ]


@router.get("/incompletos")
async def api_listar_hospitais_incompletos():
    """
    Lista hospitais que não têm conhecimento básico.
    """
    return await listar_hospitais_sem_conhecimento()
```

---

### T5: Criar importação em massa (30min)

Script para importar conhecimento de hospitais existentes.

**Arquivo:** `app/scripts/importar_conhecimento.py`

```python
"""
Script para importar conhecimento de hospitais em massa.

Uso:
    python -m app.scripts.importar_conhecimento dados.csv
"""
import asyncio
import csv
import sys
from app.services.conhecimento.repositorio import criar_conhecimento
from app.core.logging import get_logger

logger = get_logger(__name__)


async def importar_de_csv(caminho_csv: str) -> dict:
    """
    Importa conhecimento de arquivo CSV.

    Formato esperado:
        hospital_id,atributo,valor
        uuid-123,estacionamento,Sim gratuito
        uuid-123,refeicao,Refeitório 24h
        uuid-456,estacionamento,Não tem

    Args:
        caminho_csv: Caminho para o arquivo CSV

    Returns:
        Estatísticas da importação
    """
    stats = {"total": 0, "sucesso": 0, "erro": 0}

    with open(caminho_csv, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        for row in reader:
            stats["total"] += 1

            try:
                await criar_conhecimento(
                    hospital_id=row["hospital_id"],
                    atributo=row["atributo"],
                    valor=row["valor"],
                    fonte="importacao"
                )
                stats["sucesso"] += 1

            except Exception as e:
                logger.error(f"Erro na linha {stats['total']}: {e}")
                stats["erro"] += 1

    return stats


async def importar_de_dict(dados: list[dict]) -> dict:
    """
    Importa conhecimento de lista de dicionários.

    Args:
        dados: Lista de {hospital_id, atributo, valor}

    Returns:
        Estatísticas da importação
    """
    stats = {"total": 0, "sucesso": 0, "erro": 0}

    for item in dados:
        stats["total"] += 1

        try:
            await criar_conhecimento(
                hospital_id=item["hospital_id"],
                atributo=item["atributo"],
                valor=item["valor"],
                fonte="importacao"
            )
            stats["sucesso"] += 1

        except Exception as e:
            logger.error(f"Erro ao importar {item}: {e}")
            stats["erro"] += 1

    return stats


# Dados de exemplo para importação inicial
CONHECIMENTO_INICIAL = [
    # Hospital São Luiz (exemplo)
    # {"hospital_id": "uuid-aqui", "atributo": "estacionamento", "valor": "Sim, gratuito no subsolo"},
    # {"hospital_id": "uuid-aqui", "atributo": "refeicao", "valor": "Refeitório 24h, refeição inclusa"},
]


if __name__ == "__main__":
    if len(sys.argv) > 1:
        caminho = sys.argv[1]
        resultado = asyncio.run(importar_de_csv(caminho))
    else:
        resultado = asyncio.run(importar_de_dict(CONHECIMENTO_INICIAL))

    print(f"Importação concluída: {resultado}")
```

---

### T6: Criar testes (30min)

**Arquivo:** `tests/conhecimento/test_repositorio.py`

```python
"""
Testes para repositório de conhecimento.
"""
import pytest
from app.services.conhecimento.repositorio import (
    criar_conhecimento,
    buscar_conhecimento,
    buscar_conhecimento_valor,
    deletar_conhecimento,
    formatar_conhecimento_para_prompt,
    contar_conhecimentos_por_hospital
)
from app.services.conhecimento.atributos import (
    AtributoHospital,
    identificar_atributo
)


class TestCriarConhecimento:
    """Testes para criação de conhecimento."""

    @pytest.mark.asyncio
    async def test_criar_conhecimento_novo(self, supabase_mock, hospital_fixture):
        """Cria conhecimento novo."""
        resultado = await criar_conhecimento(
            hospital_id=hospital_fixture["id"],
            atributo="estacionamento",
            valor="Sim, gratuito",
            fonte="gestor"
        )

        assert resultado is not None
        assert resultado["atributo"] == "estacionamento"
        assert resultado["valor"] == "Sim, gratuito"

    @pytest.mark.asyncio
    async def test_criar_conhecimento_com_enum(self, supabase_mock, hospital_fixture):
        """Cria conhecimento usando enum."""
        resultado = await criar_conhecimento(
            hospital_id=hospital_fixture["id"],
            atributo=AtributoHospital.REFEICAO,
            valor="Refeitório 24h",
            fonte="gestor"
        )

        assert resultado is not None
        assert resultado["atributo"] == "refeicao"

    @pytest.mark.asyncio
    async def test_upsert_atualiza_existente(self, supabase_mock, hospital_fixture):
        """Upsert atualiza valor existente."""
        # Criar
        await criar_conhecimento(
            hospital_id=hospital_fixture["id"],
            atributo="estacionamento",
            valor="Sim"
        )

        # Atualizar (mesmo hospital + atributo)
        resultado = await criar_conhecimento(
            hospital_id=hospital_fixture["id"],
            atributo="estacionamento",
            valor="Sim, gratuito no subsolo"
        )

        assert resultado["valor"] == "Sim, gratuito no subsolo"

        # Deve ter apenas 1 registro
        conhecimentos = await buscar_conhecimento(
            hospital_fixture["id"], "estacionamento"
        )
        assert len(conhecimentos) == 1


class TestBuscarConhecimento:
    """Testes para busca de conhecimento."""

    @pytest.mark.asyncio
    async def test_buscar_todos_do_hospital(self, supabase_mock, hospital_com_conhecimento):
        """Busca todos os conhecimentos de um hospital."""
        conhecimentos = await buscar_conhecimento(hospital_com_conhecimento["id"])

        assert len(conhecimentos) >= 2  # fixture tem pelo menos 2

    @pytest.mark.asyncio
    async def test_buscar_atributo_especifico(self, supabase_mock, hospital_com_conhecimento):
        """Busca atributo específico."""
        conhecimentos = await buscar_conhecimento(
            hospital_com_conhecimento["id"],
            "estacionamento"
        )

        assert len(conhecimentos) == 1
        assert conhecimentos[0]["atributo"] == "estacionamento"

    @pytest.mark.asyncio
    async def test_buscar_valor_direto(self, supabase_mock, hospital_com_conhecimento):
        """Busca apenas o valor."""
        valor = await buscar_conhecimento_valor(
            hospital_com_conhecimento["id"],
            AtributoHospital.ESTACIONAMENTO
        )

        assert valor is not None
        assert "estacionamento" not in valor.lower()  # retorna só o valor


class TestIdentificarAtributo:
    """Testes para identificação de atributos."""

    def test_identifica_estacionamento(self):
        assert identificar_atributo("tem estacionamento?") == AtributoHospital.ESTACIONAMENTO
        assert identificar_atributo("posso ir de carro?") == AtributoHospital.ESTACIONAMENTO
        assert identificar_atributo("tem garagem?") == AtributoHospital.ESTACIONAMENTO

    def test_identifica_refeicao(self):
        assert identificar_atributo("tem refeição?") == AtributoHospital.REFEICAO
        assert identificar_atributo("onde almoço?") == AtributoHospital.REFEICAO
        assert identificar_atributo("tem refeitório?") == AtributoHospital.REFEICAO

    def test_identifica_vestiario(self):
        assert identificar_atributo("tem vestiário?") == AtributoHospital.VESTIARIO
        assert identificar_atributo("onde troco de roupa?") == AtributoHospital.VESTIARIO

    def test_nao_identifica_pergunta_generica(self):
        assert identificar_atributo("como é o hospital?") is None
        assert identificar_atributo("é bom?") is None


class TestFormatarPrompt:
    """Testes para formatação de conhecimento."""

    @pytest.mark.asyncio
    async def test_formata_para_prompt(self, supabase_mock, hospital_com_conhecimento):
        """Formata conhecimento para prompt."""
        texto = await formatar_conhecimento_para_prompt(
            hospital_com_conhecimento["id"]
        )

        assert "INFORMAÇÕES CONHECIDAS" in texto
        assert "Estacionamento" in texto or "estacionamento" in texto

    @pytest.mark.asyncio
    async def test_hospital_sem_conhecimento(self, supabase_mock, hospital_fixture):
        """Hospital sem conhecimento retorna string vazia."""
        texto = await formatar_conhecimento_para_prompt(hospital_fixture["id"])

        assert texto == ""
```

---

## DoD (Definition of Done)

### Funcional
- [ ] Tabela `conhecimento_hospitais` criada com todos os campos
- [ ] Constraint UNIQUE(hospital_id, atributo) funcionando
- [ ] CRUD completo (criar, buscar, atualizar, deletar)
- [ ] Endpoint GET `/conhecimento/hospital/{id}` funcionando
- [ ] Endpoint POST `/conhecimento/` funcionando
- [ ] Endpoint GET `/conhecimento/atributos` listando enum

### Dados
- [ ] Enum `AtributoHospital` com atributos comuns
- [ ] Mapeamento de sinônimos para busca
- [ ] Função `identificar_atributo` funcionando

### Testes
- [ ] Testes de CRUD
- [ ] Testes de upsert
- [ ] Testes de identificação de atributos
- [ ] Testes de formatação para prompt

### Qualidade
- [ ] Índices criados para performance
- [ ] RLS configurado
- [ ] Trigger de updated_at funcionando

### Verificação Manual

1. **Criar conhecimento via API:**
   ```bash
   curl -X POST http://localhost:8000/conhecimento/ \
     -H "Content-Type: application/json" \
     -d '{"hospital_id": "UUID", "atributo": "estacionamento", "valor": "Sim, gratuito"}'
   ```

2. **Verificar no banco:**
   ```sql
   SELECT * FROM conhecimento_hospitais
   WHERE hospital_id = 'UUID';
   ```

3. **Buscar conhecimento:**
   ```bash
   curl http://localhost:8000/conhecimento/hospital/UUID
   ```

4. **Testar upsert (mesmo atributo):**
   ```bash
   curl -X POST http://localhost:8000/conhecimento/ \
     -H "Content-Type: application/json" \
     -d '{"hospital_id": "UUID", "atributo": "estacionamento", "valor": "Sim, gratuito no subsolo"}'
   ```
   Deve ter apenas 1 registro, com valor atualizado.

---

## Notas para Dev

1. **Consistência de atributos:** Sempre usar enum quando possível para evitar duplicatas ("estacionamento" vs "Estacionamento")
2. **Fonte:** Registrar fonte para rastreabilidade (gestor > medico > sistema)
3. **Confiança:** Usar campo `confianca` para priorizar informações mais confiáveis
4. **Performance:** Busca de conhecimento acontece em toda conversa - manter queries leves
5. **Integração E11:** Este épico cria a estrutura, E11 implementa o aprendizado automático

---

## Métricas de Sucesso

| Métrica | Meta |
|---------|------|
| Hospitais com conhecimento | > 80% dos hospitais ativos |
| Atributos por hospital | > 3 em média |
| Tempo de busca | < 50ms |
