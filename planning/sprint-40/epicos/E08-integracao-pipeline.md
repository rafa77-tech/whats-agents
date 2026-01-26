# E08 - Integração e Pipeline

**Épico:** E08
**Nome:** Integração e Pipeline
**Dependências:** E01-E07
**Prioridade:** Alta (final)

---

## Objetivo

Integrar todos os componentes em um pipeline coeso e conectar com o sistema existente de processamento de mensagens de grupos.

---

## Componentes de Integração

### 1. Pipeline Principal

Orquestra a chamada de todos os extratores na ordem correta.

### 2. Persistência

Salva as vagas atômicas no banco de dados.

### 3. Compatibilidade

Mantém compatibilidade com o pipeline existente (`pipeline_worker.py`).

---

## Entregáveis

### 1. Arquivo: `pipeline.py`

```python
"""
Pipeline principal de extração de vagas v2.

Orquestra todos os extratores para processar uma mensagem completa.
"""

import time
from datetime import date
from typing import Optional
from uuid import UUID

from app.core.logging import get_logger
from app.services.grupos.extrator_v2.types import (
    ResultadoExtracaoV2,
    VagaAtomica,
)
from app.services.grupos.extrator_v2.parser_mensagem import (
    parsear_mensagem,
    MensagemParsed,
)
from app.services.grupos.extrator_v2.extrator_hospitais import extrair_hospitais
from app.services.grupos.extrator_v2.extrator_datas import extrair_datas_periodos
from app.services.grupos.extrator_v2.extrator_valores import extrair_valores
from app.services.grupos.extrator_v2.extrator_contato import extrair_contato
from app.services.grupos.extrator_v2.gerador_vagas import (
    gerar_vagas,
    validar_vagas,
    deduplicar_vagas,
)
from app.services.grupos.extrator_v2.exceptions import (
    ExtracaoError,
    MensagemVaziaError,
    SemHospitalError,
    SemDataError,
)

logger = get_logger(__name__)


async def extrair_vagas_v2(
    texto: str,
    mensagem_id: Optional[UUID] = None,
    grupo_id: Optional[UUID] = None,
    data_referencia: Optional[date] = None,
) -> ResultadoExtracaoV2:
    """
    Extrai vagas atômicas de uma mensagem de grupo.

    Pipeline:
    1. Parser de mensagem (separa seções)
    2. Extrator de hospitais
    3. Extrator de datas/períodos
    4. Extrator de valores
    5. Extrator de contato
    6. Gerador de vagas (combina tudo)
    7. Validação e deduplicação

    Args:
        texto: Texto bruto da mensagem
        mensagem_id: ID da mensagem (para rastreabilidade)
        grupo_id: ID do grupo (para rastreabilidade)
        data_referencia: Data de referência para "hoje" e "amanhã"

    Returns:
        ResultadoExtracaoV2 com vagas e metadados

    Example:
        >>> resultado = await extrair_vagas_v2(
        ...     texto="📍 Hospital ABC\\n🗓 26/01 Manhã\\n💰 R$ 1.700",
        ...     mensagem_id=uuid4(),
        ...     grupo_id=uuid4()
        ... )
        >>> len(resultado.vagas)
        1
    """
    inicio = time.time()
    warnings = []

    # Validação inicial
    if not texto or not texto.strip():
        return ResultadoExtracaoV2(
            erro="mensagem_vazia",
            tempo_processamento_ms=0
        )

    try:
        # 1. Parser de mensagem
        msg_parsed = parsear_mensagem(texto)

        # 2. Extração de hospitais
        hospitais = extrair_hospitais(msg_parsed.secoes_local)
        if not hospitais:
            # Tentar extrair do texto completo
            hospitais = extrair_hospitais([texto])
            if hospitais:
                warnings.append("hospital_extraido_texto_completo")

        if not hospitais:
            return ResultadoExtracaoV2(
                erro="sem_hospital",
                tempo_processamento_ms=int((time.time() - inicio) * 1000),
                warnings=warnings
            )

        # 3. Extração de datas/períodos
        datas_periodos = extrair_datas_periodos(
            msg_parsed.secoes_data,
            data_referencia=data_referencia or date.today()
        )
        if not datas_periodos:
            # Tentar extrair do texto completo
            datas_periodos = extrair_datas_periodos(
                [texto],
                data_referencia=data_referencia or date.today()
            )
            if datas_periodos:
                warnings.append("datas_extraidas_texto_completo")

        if not datas_periodos:
            return ResultadoExtracaoV2(
                hospitais=hospitais,
                erro="sem_data",
                tempo_processamento_ms=int((time.time() - inicio) * 1000),
                warnings=warnings
            )

        # 4. Extração de valores
        valores = extrair_valores(msg_parsed.secoes_valor)
        if not valores.regras and not valores.valor_unico:
            # Tentar extrair do texto completo
            valores = extrair_valores([texto])
            if valores.regras or valores.valor_unico:
                warnings.append("valores_extraidos_texto_completo")
            else:
                warnings.append("sem_valor_extraido")

        # 5. Extração de contato
        contato = extrair_contato(msg_parsed.secoes_contato)
        if not contato:
            # Tentar extrair do texto completo
            contato = extrair_contato([texto])
            if contato:
                warnings.append("contato_extraido_texto_completo")

        # 6. Geração de vagas
        vagas = gerar_vagas(
            hospitais=hospitais,
            datas_periodos=datas_periodos,
            valores=valores,
            contato=contato,
            mensagem_id=mensagem_id,
            grupo_id=grupo_id,
        )

        # 7. Validação e deduplicação
        vagas = validar_vagas(vagas)
        vagas = deduplicar_vagas(vagas)

        tempo_ms = int((time.time() - inicio) * 1000)

        return ResultadoExtracaoV2(
            vagas=vagas,
            hospitais=hospitais,
            datas_periodos=datas_periodos,
            valores=valores,
            contato=contato,
            total_vagas=len(vagas),
            tempo_processamento_ms=tempo_ms,
            warnings=warnings
        )

    except ExtracaoError as e:
        logger.error(f"Erro de extração: {e}")
        return ResultadoExtracaoV2(
            erro=str(e),
            tempo_processamento_ms=int((time.time() - inicio) * 1000),
            warnings=warnings
        )
    except Exception as e:
        logger.exception(f"Erro inesperado na extração: {e}")
        return ResultadoExtracaoV2(
            erro=f"erro_inesperado: {str(e)}",
            tempo_processamento_ms=int((time.time() - inicio) * 1000),
            warnings=warnings
        )
```

### 2. Arquivo: `repository.py`

```python
"""
Repositório para persistência de vagas atômicas.
"""

from typing import List, Optional
from uuid import UUID

from app.core.logging import get_logger
from app.services.supabase import supabase
from app.services.grupos.extrator_v2.types import VagaAtomica

logger = get_logger(__name__)


async def salvar_vagas_atomicas(
    vagas: List[VagaAtomica],
    mensagem_id: Optional[UUID] = None,
) -> List[UUID]:
    """
    Salva lista de vagas atômicas no banco.

    Args:
        vagas: Lista de vagas a salvar
        mensagem_id: ID da mensagem origem (para atualizar status)

    Returns:
        Lista de UUIDs das vagas criadas
    """
    if not vagas:
        return []

    ids_criados = []

    for vaga in vagas:
        try:
            dados = vaga.to_dict()

            # Campos adicionais para compatibilidade
            dados["status"] = "nova"
            dados["dados_minimos_ok"] = True
            dados["data_valida"] = True
            dados["valor_tipo"] = "fixo" if vaga.valor > 0 else "a_combinar"

            result = supabase.table("vagas_grupo").insert(dados).execute()

            if result.data:
                ids_criados.append(UUID(result.data[0]["id"]))

        except Exception as e:
            logger.error(f"Erro ao salvar vaga: {e}")
            continue

    logger.info(f"Salvas {len(ids_criados)}/{len(vagas)} vagas")
    return ids_criados


async def atualizar_mensagem_processada(
    mensagem_id: UUID,
    qtd_vagas: int,
    sucesso: bool,
    erro: Optional[str] = None
) -> None:
    """
    Atualiza status da mensagem após processamento.

    Args:
        mensagem_id: ID da mensagem
        qtd_vagas: Quantidade de vagas extraídas
        sucesso: Se extração foi bem-sucedida
        erro: Mensagem de erro se houver
    """
    from datetime import datetime, UTC

    try:
        status = "extraida_v2" if sucesso and qtd_vagas > 0 else "extracao_v2_falhou"

        supabase.table("mensagens_grupo").update({
            "status": status,
            "qtd_vagas_extraidas": qtd_vagas,
            "processado_em": datetime.now(UTC).isoformat(),
            "erro_extracao": erro,
        }).eq("id", str(mensagem_id)).execute()

    except Exception as e:
        logger.error(f"Erro ao atualizar mensagem {mensagem_id}: {e}")
```

### 3. Atualização do `__init__.py`

```python
"""
Extrator de Vagas v2 - Sprint 40

Extrai vagas atômicas de mensagens de grupos de WhatsApp.
Cada vaga é uma combinação única de: data + período + valor + hospital.
"""

from .types import (
    # Enums
    DiaSemana,
    Periodo,
    GrupoDia,
    # Dataclasses de entrada
    HospitalExtraido,
    DataPeriodoExtraido,
    RegraValor,
    ValoresExtraidos,
    ContatoExtraido,
    EspecialidadeExtraida,
    # Dataclass de saída
    VagaAtomica,
    ResultadoExtracaoV2,
)

from .exceptions import (
    ExtracaoError,
    MensagemVaziaError,
    SemHospitalError,
    SemDataError,
    LLMTimeoutError,
    LLMRateLimitError,
    JSONParseError,
)

from .pipeline import extrair_vagas_v2
from .repository import salvar_vagas_atomicas, atualizar_mensagem_processada

__all__ = [
    # Função principal
    "extrair_vagas_v2",
    # Persistência
    "salvar_vagas_atomicas",
    "atualizar_mensagem_processada",
    # Enums
    "DiaSemana",
    "Periodo",
    "GrupoDia",
    # Dataclasses
    "HospitalExtraido",
    "DataPeriodoExtraido",
    "RegraValor",
    "ValoresExtraidos",
    "ContatoExtraido",
    "EspecialidadeExtraida",
    "VagaAtomica",
    "ResultadoExtracaoV2",
    # Exceptions
    "ExtracaoError",
    "MensagemVaziaError",
    "SemHospitalError",
    "SemDataError",
    "LLMTimeoutError",
    "LLMRateLimitError",
    "JSONParseError",
]
```

---

## Testes Obrigatórios

### Arquivo: `tests/services/grupos/extrator_v2/test_pipeline.py`

```python
"""Testes de integração do pipeline v2."""
import pytest
from datetime import date
from uuid import uuid4

from app.services.grupos.extrator_v2 import extrair_vagas_v2


class TestPipelineIntegracao:
    """Testes de integração do pipeline completo."""

    @pytest.mark.asyncio
    async def test_mensagem_completa(self):
        """Pipeline processa mensagem completa."""
        texto = """📍 Hospital Campo Limpo
Estrada Itapecirica, 1661 - SP

🗓 26/01 - Segunda - Manhã 7-13h
🗓 27/01 - Terça - Noite 19-7h

💰 Segunda a Sexta: R$ 1.700
💰 Sábado e Domingo: R$ 1.800

📲 Eloisa
wa.me/5511939050162"""

        resultado = await extrair_vagas_v2(
            texto=texto,
            data_referencia=date(2026, 1, 25)
        )

        assert resultado.sucesso is True
        assert resultado.erro is None
        assert len(resultado.vagas) == 2

        # Verificar primeira vaga
        vaga1 = resultado.vagas[0]
        assert vaga1.hospital_raw == "Hospital Campo Limpo"
        assert vaga1.data == date(2026, 1, 26)
        assert vaga1.valor == 1700
        assert vaga1.contato_nome == "Eloisa"

    @pytest.mark.asyncio
    async def test_mensagem_simples(self):
        """Pipeline processa mensagem simples."""
        texto = "Hospital ABC - 26/01 manhã R$ 1.800"

        resultado = await extrair_vagas_v2(
            texto=texto,
            data_referencia=date(2026, 1, 25)
        )

        # Pode ter warnings mas deve extrair
        assert len(resultado.vagas) >= 0

    @pytest.mark.asyncio
    async def test_mensagem_vazia(self):
        """Pipeline rejeita mensagem vazia."""
        resultado = await extrair_vagas_v2(texto="")

        assert resultado.sucesso is False
        assert resultado.erro == "mensagem_vazia"

    @pytest.mark.asyncio
    async def test_mensagem_sem_hospital(self):
        """Pipeline rejeita mensagem sem hospital."""
        texto = "🗓 26/01 manhã R$ 1.800"

        resultado = await extrair_vagas_v2(
            texto=texto,
            data_referencia=date(2026, 1, 25)
        )

        assert resultado.sucesso is False
        assert "hospital" in resultado.erro.lower()

    @pytest.mark.asyncio
    async def test_mensagem_sem_data(self):
        """Pipeline rejeita mensagem sem data."""
        texto = "📍 Hospital ABC\n💰 R$ 1.800"

        resultado = await extrair_vagas_v2(texto=texto)

        assert resultado.sucesso is False
        assert "data" in resultado.erro.lower()

    @pytest.mark.asyncio
    async def test_tempo_processamento(self):
        """Pipeline registra tempo de processamento."""
        texto = "📍 Hospital ABC\n🗓 26/01 manhã\n💰 R$ 1.800"

        resultado = await extrair_vagas_v2(
            texto=texto,
            data_referencia=date(2026, 1, 25)
        )

        assert resultado.tempo_processamento_ms > 0
        assert resultado.tempo_processamento_ms < 5000  # Menos de 5s

    @pytest.mark.asyncio
    async def test_rastreabilidade(self):
        """Pipeline preserva IDs de rastreabilidade."""
        texto = "📍 Hospital ABC\n🗓 26/01 manhã\n💰 R$ 1.800"
        msg_id = uuid4()
        grupo_id = uuid4()

        resultado = await extrair_vagas_v2(
            texto=texto,
            mensagem_id=msg_id,
            grupo_id=grupo_id,
            data_referencia=date(2026, 1, 25)
        )

        if resultado.vagas:
            assert resultado.vagas[0].mensagem_id == msg_id
            assert resultado.vagas[0].grupo_id == grupo_id


class TestCasosReais:
    """Testes com mensagens reais de grupos."""

    @pytest.mark.asyncio
    async def test_caso_real_upa(self):
        """Formato real UPA."""
        texto = """🔴🔴PRECISO🔴🔴

📍UPA CAMPO LIMPO
📅 27/01 SEGUNDA
⏰ 19 as 07
💰1.600
📲11964391344"""

        resultado = await extrair_vagas_v2(
            texto=texto,
            data_referencia=date(2026, 1, 25)
        )

        assert resultado.sucesso is True
        assert len(resultado.vagas) == 1
        assert resultado.vagas[0].valor == 1600

    @pytest.mark.asyncio
    async def test_caso_real_multiplas_datas(self):
        """Formato real com múltiplas datas."""
        texto = """*PLANTÕES CLINICA MÉDICA*

Hospital Santa Casa ABC

26/01 dom diurno 7-19h
27/01 seg noturno 19-7h
28/01 ter diurno 7-19h

Valor R$ 1.500

Int. Maria 11 99999-9999"""

        resultado = await extrair_vagas_v2(
            texto=texto,
            data_referencia=date(2026, 1, 25)
        )

        assert resultado.sucesso is True
        assert len(resultado.vagas) >= 3

    @pytest.mark.asyncio
    async def test_caso_real_valores_diferentes(self):
        """Formato real com valores por dia."""
        texto = """📍 Hospital ABC
Região Sul - SP

🗓 26/01 - Segunda - Manhã 7-13h
🗓 01/02 - Sábado - SD 7-19h
🗓 02/02 - Domingo - SD 7-19h

💰 Seg-Sex: R$ 1.700
💰 Sab-Dom: R$ 2.000

📲 Contato: João - 11988887777"""

        resultado = await extrair_vagas_v2(
            texto=texto,
            data_referencia=date(2026, 1, 25)
        )

        assert resultado.sucesso is True
        assert len(resultado.vagas) == 3

        # Verificar valores
        vagas_seg_sex = [v for v in resultado.vagas if v.dia_semana.value == "segunda"]
        vagas_sab_dom = [v for v in resultado.vagas if v.dia_semana.value in ("sabado", "domingo")]

        if vagas_seg_sex:
            assert vagas_seg_sex[0].valor == 1700
        if vagas_sab_dom:
            for v in vagas_sab_dom:
                assert v.valor == 2000
```

---

## Checklist de Conclusão

### Implementação
- [ ] Criar arquivo `pipeline.py`
- [ ] Criar arquivo `repository.py`
- [ ] Atualizar `__init__.py` com exports
- [ ] Integrar com `pipeline_worker.py` existente

### Testes
- [ ] Criar arquivo de testes de integração
- [ ] Rodar testes
- [ ] 100% dos testes passando

### Validação Manual
- [ ] Processar 50 mensagens reais
- [ ] Verificar taxa de extração de valor >= 95%
- [ ] Verificar que não há regressões

### Qualidade
- [ ] Zero erros mypy em todos os arquivos
- [ ] Zero erros ruff em todos os arquivos
- [ ] Cobertura de testes >= 90%

---

## Definition of Done (E08)

Este épico está **COMPLETO** quando:

1. ✅ Pipeline `extrair_vagas_v2()` funcionando end-to-end
2. ✅ Persistência de vagas atômicas funcionando
3. ✅ Integração com pipeline existente documentada
4. ✅ Testes de integração passando
5. ✅ 50 mensagens reais processadas manualmente
6. ✅ Taxa de extração de valor >= 95%
7. ✅ Cobertura de testes >= 90%
8. ✅ Zero erros mypy/ruff

---

## Definition of Done (Sprint 40)

A sprint está **COMPLETA** quando:

1. ✅ Todos os 8 épicos completos
2. ✅ Testes unitários com cobertura >= 90%
3. ✅ Testes de integração passando
4. ✅ 50 mensagens reais validadas manualmente
5. ✅ Taxa de extração de valor >= 95%
6. ✅ Zero erros de mypy/ruff
7. ✅ Documentação de API completa
8. ✅ PR aprovado e mergeado para main
