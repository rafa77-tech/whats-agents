# E07 - Gerador de Vagas

**Épico:** E07
**Nome:** Gerador de Vagas Atômicas
**Dependências:** E01-E06
**Prioridade:** Alta (crítico)

---

## Objetivo

Combinar os dados extraídos (hospitais, datas, valores, contato) para gerar as vagas atômicas. Este é o épico que faz o "join" de todos os componentes.

---

## Lógica de Geração

### Regra Principal

Para cada **hospital** × cada **data/período** = uma **vaga atômica** com valor associado.

### Exemplo

**Entrada:**
- 1 hospital: "Hospital Campo Limpo"
- 3 datas/períodos: 26/01 manhã, 27/01 noite, 28/01 tarde
- Regras de valor: seg-sex R$ 1.700, sáb-dom R$ 1.800
- Contato: Eloisa - wa.me/5511939050162

**Saída:** 3 vagas atômicas:

| Vaga | Data | Dia | Período | Valor |
|------|------|-----|---------|-------|
| 1 | 26/01 | segunda | manhã | 1700 |
| 2 | 27/01 | terça | noite | 1700 |
| 3 | 28/01 | quarta | tarde | 1700 |

Todas com mesmo hospital e contato.

---

## Entregáveis

### 1. Arquivo: `gerador_vagas.py`

```python
"""
Gerador de vagas atômicas.

Combina hospitais, datas, valores e contato para gerar vagas.
"""

from datetime import date
from typing import List, Optional
from uuid import UUID

from app.core.logging import get_logger
from app.services.grupos.extrator_v2.types import (
    VagaAtomica,
    HospitalExtraido,
    DataPeriodoExtraido,
    ValoresExtraidos,
    ContatoExtraido,
    EspecialidadeExtraida,
)
from app.services.grupos.extrator_v2.extrator_valores import obter_valor_para_dia

logger = get_logger(__name__)


def _calcular_confianca_geral(
    hospital: HospitalExtraido,
    data_periodo: DataPeriodoExtraido,
    valor: Optional[int],
    contato: Optional[ContatoExtraido]
) -> float:
    """
    Calcula confiança geral da vaga.

    Média ponderada das confianças dos componentes.
    """
    pesos = {
        "hospital": 3,
        "data": 3,
        "valor": 2,
        "contato": 1,
    }

    scores = {
        "hospital": hospital.confianca,
        "data": data_periodo.confianca,
        "valor": 1.0 if valor else 0.5,  # Sem valor = menos confiável
        "contato": contato.confianca if contato else 0.5,
    }

    total_peso = sum(pesos.values())
    soma = sum(scores[k] * pesos[k] for k in pesos)

    return round(soma / total_peso, 2)


def gerar_vagas_para_hospital(
    hospital: HospitalExtraido,
    datas_periodos: List[DataPeriodoExtraido],
    valores: ValoresExtraidos,
    contato: Optional[ContatoExtraido] = None,
    especialidades: Optional[List[EspecialidadeExtraida]] = None,
    mensagem_id: Optional[UUID] = None,
    grupo_id: Optional[UUID] = None,
) -> List[VagaAtomica]:
    """
    Gera vagas atômicas para um hospital.

    Args:
        hospital: Hospital extraído
        datas_periodos: Lista de datas e períodos
        valores: Valores e regras
        contato: Contato extraído (opcional)
        especialidades: Especialidades (opcional)
        mensagem_id: ID da mensagem origem
        grupo_id: ID do grupo origem

    Returns:
        Lista de VagaAtomica
    """
    vagas = []

    # Usar primeira especialidade se disponível
    especialidade = especialidades[0] if especialidades else None

    for dp in datas_periodos:
        # Obter valor para este dia/período
        valor = obter_valor_para_dia(valores, dp.dia_semana, dp.periodo)

        if valor is None:
            logger.warning(
                f"Sem valor para {dp.dia_semana.value}/{dp.periodo.value}, "
                f"usando valor_unico ou ignorando"
            )
            valor = valores.valor_unico
            if valor is None:
                # Sem valor conhecido - gerar vaga mesmo assim mas com observação
                pass

        # Calcular confiança
        confianca = _calcular_confianca_geral(hospital, dp, valor, contato)

        # Criar vaga atômica
        vaga = VagaAtomica(
            # Dados da data/período
            data=dp.data,
            dia_semana=dp.dia_semana,
            periodo=dp.periodo,
            hora_inicio=dp.hora_inicio,
            hora_fim=dp.hora_fim,

            # Valor
            valor=valor or 0,  # 0 indica valor não informado

            # Hospital
            hospital_raw=hospital.nome,
            endereco_raw=hospital.endereco,
            cidade=hospital.cidade,
            estado=hospital.estado,

            # Especialidade
            especialidade_raw=especialidade.nome if especialidade else None,

            # Contato
            contato_nome=contato.nome if contato else None,
            contato_whatsapp=contato.whatsapp if contato else None,

            # Metadados
            confianca_geral=confianca,
            observacoes="Valor não informado" if valor is None else None,

            # Rastreabilidade
            mensagem_id=mensagem_id,
            grupo_id=grupo_id,
        )

        vagas.append(vaga)

    return vagas


def gerar_vagas(
    hospitais: List[HospitalExtraido],
    datas_periodos: List[DataPeriodoExtraido],
    valores: ValoresExtraidos,
    contato: Optional[ContatoExtraido] = None,
    especialidades: Optional[List[EspecialidadeExtraida]] = None,
    mensagem_id: Optional[UUID] = None,
    grupo_id: Optional[UUID] = None,
) -> List[VagaAtomica]:
    """
    Gera todas as vagas atômicas a partir dos dados extraídos.

    Esta é a função principal do gerador.

    Lógica:
    - Para cada hospital
      - Para cada data/período
        - Cria uma vaga com valor associado ao dia da semana

    Args:
        hospitais: Lista de hospitais extraídos
        datas_periodos: Lista de datas e períodos
        valores: Valores e regras
        contato: Contato extraído
        especialidades: Especialidades extraídas
        mensagem_id: ID da mensagem origem
        grupo_id: ID do grupo origem

    Returns:
        Lista de VagaAtomica

    Example:
        >>> hospitais = [HospitalExtraido(nome="Hospital ABC")]
        >>> datas = [
        ...     DataPeriodoExtraido(data=date(2026,1,26), dia_semana=DiaSemana.SEGUNDA, periodo=Periodo.MANHA),
        ...     DataPeriodoExtraido(data=date(2026,1,27), dia_semana=DiaSemana.TERCA, periodo=Periodo.NOITE),
        ... ]
        >>> valores = ValoresExtraidos(valor_unico=1700)
        >>> vagas = gerar_vagas(hospitais, datas, valores)
        >>> len(vagas)
        2
    """
    if not hospitais:
        logger.warning("Nenhum hospital fornecido")
        return []

    if not datas_periodos:
        logger.warning("Nenhuma data/período fornecido")
        return []

    todas_vagas = []

    for hospital in hospitais:
        vagas_hospital = gerar_vagas_para_hospital(
            hospital=hospital,
            datas_periodos=datas_periodos,
            valores=valores,
            contato=contato,
            especialidades=especialidades,
            mensagem_id=mensagem_id,
            grupo_id=grupo_id,
        )
        todas_vagas.extend(vagas_hospital)

    logger.info(
        f"Geradas {len(todas_vagas)} vagas "
        f"({len(hospitais)} hospitais × {len(datas_periodos)} datas)"
    )

    return todas_vagas


def validar_vagas(vagas: List[VagaAtomica]) -> List[VagaAtomica]:
    """
    Valida e filtra vagas.

    Remove vagas com dados insuficientes ou inválidos.

    Args:
        vagas: Lista de vagas geradas

    Returns:
        Lista de vagas válidas
    """
    validas = []
    hoje = date.today()

    for vaga in vagas:
        # Verificar campos obrigatórios
        if not vaga.hospital_raw:
            logger.debug("Vaga sem hospital, ignorando")
            continue

        if not vaga.data:
            logger.debug("Vaga sem data, ignorando")
            continue

        # Verificar data futura
        if vaga.data < hoje:
            logger.debug(f"Vaga com data passada {vaga.data}, ignorando")
            continue

        # Verificar valor (0 é permitido - significa "a combinar")
        # Não filtrar por valor

        validas.append(vaga)

    logger.info(f"Validação: {len(validas)}/{len(vagas)} vagas válidas")
    return validas


def deduplicar_vagas(vagas: List[VagaAtomica]) -> List[VagaAtomica]:
    """
    Remove vagas duplicadas.

    Duas vagas são consideradas duplicadas se têm mesmo:
    - Hospital
    - Data
    - Período
    - Valor

    Args:
        vagas: Lista de vagas

    Returns:
        Lista sem duplicatas
    """
    vistas = set()
    unicas = []

    for vaga in vagas:
        chave = (
            vaga.hospital_raw.lower().strip(),
            vaga.data.isoformat(),
            vaga.periodo.value,
            vaga.valor,
        )

        if chave not in vistas:
            vistas.add(chave)
            unicas.append(vaga)
        else:
            logger.debug(f"Vaga duplicada removida: {chave}")

    if len(vagas) != len(unicas):
        logger.info(f"Deduplicação: {len(vagas)} -> {len(unicas)} vagas")

    return unicas
```

---

## Testes Obrigatórios

### Arquivo: `tests/services/grupos/extrator_v2/test_gerador_vagas.py`

```python
"""Testes para gerador de vagas."""
import pytest
from datetime import date, time
from uuid import uuid4

from app.services.grupos.extrator_v2.gerador_vagas import (
    gerar_vagas,
    gerar_vagas_para_hospital,
    validar_vagas,
    deduplicar_vagas,
)
from app.services.grupos.extrator_v2.types import (
    VagaAtomica,
    HospitalExtraido,
    DataPeriodoExtraido,
    ValoresExtraidos,
    ContatoExtraido,
    DiaSemana,
    Periodo,
    GrupoDia,
    RegraValor,
)


class TestGerarVagasParaHospital:
    """Testes para geração de vagas por hospital."""

    def test_uma_data_valor_unico(self):
        """Uma data com valor único."""
        hospital = HospitalExtraido(nome="Hospital ABC", confianca=0.9)
        datas = [
            DataPeriodoExtraido(
                data=date(2026, 1, 26),
                dia_semana=DiaSemana.SEGUNDA,
                periodo=Periodo.MANHA,
                confianca=0.9
            )
        ]
        valores = ValoresExtraidos(valor_unico=1700)

        vagas = gerar_vagas_para_hospital(hospital, datas, valores)

        assert len(vagas) == 1
        assert vagas[0].hospital_raw == "Hospital ABC"
        assert vagas[0].data == date(2026, 1, 26)
        assert vagas[0].valor == 1700

    def test_multiplas_datas_valor_unico(self):
        """Múltiplas datas com valor único."""
        hospital = HospitalExtraido(nome="Hospital ABC", confianca=0.9)
        datas = [
            DataPeriodoExtraido(
                data=date(2026, 1, 26),
                dia_semana=DiaSemana.SEGUNDA,
                periodo=Periodo.MANHA,
                confianca=0.9
            ),
            DataPeriodoExtraido(
                data=date(2026, 1, 27),
                dia_semana=DiaSemana.TERCA,
                periodo=Periodo.NOITE,
                confianca=0.9
            ),
        ]
        valores = ValoresExtraidos(valor_unico=1700)

        vagas = gerar_vagas_para_hospital(hospital, datas, valores)

        assert len(vagas) == 2
        assert all(v.valor == 1700 for v in vagas)

    def test_multiplas_datas_valores_diferentes(self):
        """Valores diferentes por dia da semana."""
        hospital = HospitalExtraido(nome="Hospital ABC", confianca=0.9)
        datas = [
            DataPeriodoExtraido(
                data=date(2026, 1, 26),
                dia_semana=DiaSemana.SEGUNDA,
                periodo=Periodo.MANHA,
                confianca=0.9
            ),
            DataPeriodoExtraido(
                data=date(2026, 1, 31),
                dia_semana=DiaSemana.SABADO,
                periodo=Periodo.DIURNO,
                confianca=0.9
            ),
        ]
        valores = ValoresExtraidos(regras=[
            RegraValor(grupo_dia=GrupoDia.SEG_SEX, valor=1700),
            RegraValor(grupo_dia=GrupoDia.SAB_DOM, valor=1800),
        ])

        vagas = gerar_vagas_para_hospital(hospital, datas, valores)

        assert len(vagas) == 2
        assert vagas[0].valor == 1700  # Segunda
        assert vagas[1].valor == 1800  # Sábado

    def test_com_contato(self):
        """Vaga com contato."""
        hospital = HospitalExtraido(nome="Hospital ABC", confianca=0.9)
        datas = [
            DataPeriodoExtraido(
                data=date(2026, 1, 26),
                dia_semana=DiaSemana.SEGUNDA,
                periodo=Periodo.MANHA,
                confianca=0.9
            )
        ]
        valores = ValoresExtraidos(valor_unico=1700)
        contato = ContatoExtraido(
            nome="Eloisa",
            whatsapp="5511939050162",
            confianca=0.95
        )

        vagas = gerar_vagas_para_hospital(hospital, datas, valores, contato=contato)

        assert len(vagas) == 1
        assert vagas[0].contato_nome == "Eloisa"
        assert vagas[0].contato_whatsapp == "5511939050162"


class TestGerarVagas:
    """Testes para geração completa de vagas."""

    def test_um_hospital_multiplas_datas(self):
        """Um hospital com múltiplas datas."""
        hospitais = [HospitalExtraido(nome="Hospital ABC", confianca=0.9)]
        datas = [
            DataPeriodoExtraido(
                data=date(2026, 1, 26),
                dia_semana=DiaSemana.SEGUNDA,
                periodo=Periodo.MANHA,
                confianca=0.9
            ),
            DataPeriodoExtraido(
                data=date(2026, 1, 27),
                dia_semana=DiaSemana.TERCA,
                periodo=Periodo.NOITE,
                confianca=0.9
            ),
        ]
        valores = ValoresExtraidos(valor_unico=1700)

        vagas = gerar_vagas(hospitais, datas, valores)

        assert len(vagas) == 2

    def test_multiplos_hospitais_multiplas_datas(self):
        """Múltiplos hospitais × múltiplas datas = produto cartesiano."""
        hospitais = [
            HospitalExtraido(nome="Hospital ABC", confianca=0.9),
            HospitalExtraido(nome="Hospital XYZ", confianca=0.8),
        ]
        datas = [
            DataPeriodoExtraido(
                data=date(2026, 1, 26),
                dia_semana=DiaSemana.SEGUNDA,
                periodo=Periodo.MANHA,
                confianca=0.9
            ),
            DataPeriodoExtraido(
                data=date(2026, 1, 27),
                dia_semana=DiaSemana.TERCA,
                periodo=Periodo.NOITE,
                confianca=0.9
            ),
        ]
        valores = ValoresExtraidos(valor_unico=1700)

        vagas = gerar_vagas(hospitais, datas, valores)

        # 2 hospitais × 2 datas = 4 vagas
        assert len(vagas) == 4

    def test_sem_hospitais(self):
        """Sem hospitais retorna lista vazia."""
        vagas = gerar_vagas([], [], ValoresExtraidos())
        assert vagas == []

    def test_sem_datas(self):
        """Sem datas retorna lista vazia."""
        hospitais = [HospitalExtraido(nome="Hospital ABC", confianca=0.9)]
        vagas = gerar_vagas(hospitais, [], ValoresExtraidos())
        assert vagas == []


class TestValidarVagas:
    """Testes para validação de vagas."""

    def test_vaga_valida(self):
        """Vaga válida passa na validação."""
        vagas = [
            VagaAtomica(
                data=date(2030, 1, 26),  # Data futura
                dia_semana=DiaSemana.SEGUNDA,
                periodo=Periodo.MANHA,
                valor=1700,
                hospital_raw="Hospital ABC"
            )
        ]

        validas = validar_vagas(vagas)
        assert len(validas) == 1

    def test_vaga_sem_hospital(self):
        """Vaga sem hospital é removida."""
        vagas = [
            VagaAtomica(
                data=date(2030, 1, 26),
                dia_semana=DiaSemana.SEGUNDA,
                periodo=Periodo.MANHA,
                valor=1700,
                hospital_raw=""  # Sem hospital
            )
        ]

        validas = validar_vagas(vagas)
        assert len(validas) == 0

    def test_vaga_data_passada(self):
        """Vaga com data passada é removida."""
        vagas = [
            VagaAtomica(
                data=date(2020, 1, 1),  # Passado
                dia_semana=DiaSemana.SEGUNDA,
                periodo=Periodo.MANHA,
                valor=1700,
                hospital_raw="Hospital ABC"
            )
        ]

        validas = validar_vagas(vagas)
        assert len(validas) == 0


class TestDeduplicarVagas:
    """Testes para deduplicação de vagas."""

    def test_sem_duplicatas(self):
        """Lista sem duplicatas permanece igual."""
        vagas = [
            VagaAtomica(
                data=date(2030, 1, 26),
                dia_semana=DiaSemana.SEGUNDA,
                periodo=Periodo.MANHA,
                valor=1700,
                hospital_raw="Hospital ABC"
            ),
            VagaAtomica(
                data=date(2030, 1, 27),
                dia_semana=DiaSemana.TERCA,
                periodo=Periodo.NOITE,
                valor=1700,
                hospital_raw="Hospital ABC"
            ),
        ]

        unicas = deduplicar_vagas(vagas)
        assert len(unicas) == 2

    def test_com_duplicatas(self):
        """Duplicatas são removidas."""
        vagas = [
            VagaAtomica(
                data=date(2030, 1, 26),
                dia_semana=DiaSemana.SEGUNDA,
                periodo=Periodo.MANHA,
                valor=1700,
                hospital_raw="Hospital ABC"
            ),
            VagaAtomica(
                data=date(2030, 1, 26),  # Mesma data
                dia_semana=DiaSemana.SEGUNDA,  # Mesmo dia
                periodo=Periodo.MANHA,  # Mesmo período
                valor=1700,  # Mesmo valor
                hospital_raw="Hospital ABC"  # Mesmo hospital
            ),
        ]

        unicas = deduplicar_vagas(vagas)
        assert len(unicas) == 1

    def test_mesmo_hospital_valores_diferentes(self):
        """Mesmo hospital, valores diferentes = não duplicata."""
        vagas = [
            VagaAtomica(
                data=date(2030, 1, 26),
                dia_semana=DiaSemana.SEGUNDA,
                periodo=Periodo.MANHA,
                valor=1700,
                hospital_raw="Hospital ABC"
            ),
            VagaAtomica(
                data=date(2030, 1, 26),
                dia_semana=DiaSemana.SEGUNDA,
                periodo=Periodo.MANHA,
                valor=1800,  # Valor diferente
                hospital_raw="Hospital ABC"
            ),
        ]

        unicas = deduplicar_vagas(vagas)
        assert len(unicas) == 2


class TestCenarioCompleto:
    """Testes de cenário completo (integração)."""

    def test_cenario_exemplo_readme(self):
        """Cenário do exemplo do README."""
        # Dados de entrada conforme exemplo
        hospitais = [
            HospitalExtraido(
                nome="Hospital Campo Limpo",
                endereco="Estrada Itapecirica, 1661 - SP",
                confianca=0.95
            )
        ]

        datas = [
            DataPeriodoExtraido(
                data=date(2026, 1, 26),
                dia_semana=DiaSemana.SEGUNDA,
                periodo=Periodo.TARDE,
                hora_inicio=time(13, 0),
                hora_fim=time(19, 0),
                confianca=0.9
            ),
            DataPeriodoExtraido(
                data=date(2026, 1, 27),
                dia_semana=DiaSemana.TERCA,
                periodo=Periodo.NOITE,
                hora_inicio=time(19, 0),
                hora_fim=time(7, 0),
                confianca=0.9
            ),
            DataPeriodoExtraido(
                data=date(2026, 1, 28),
                dia_semana=DiaSemana.QUARTA,
                periodo=Periodo.MANHA,
                hora_inicio=time(7, 0),
                hora_fim=time(13, 0),
                confianca=0.9
            ),
            DataPeriodoExtraido(
                data=date(2026, 2, 1),
                dia_semana=DiaSemana.DOMINGO,
                periodo=Periodo.DIURNO,
                hora_inicio=time(7, 0),
                hora_fim=time(19, 0),
                confianca=0.9
            ),
        ]

        valores = ValoresExtraidos(regras=[
            RegraValor(grupo_dia=GrupoDia.SEG_SEX, valor=1700),
            RegraValor(grupo_dia=GrupoDia.SAB_DOM, valor=1800),
        ])

        contato = ContatoExtraido(
            nome="Eloisa",
            whatsapp="5511939050162",
            confianca=0.95
        )

        # Gerar vagas
        vagas = gerar_vagas(
            hospitais=hospitais,
            datas_periodos=datas,
            valores=valores,
            contato=contato
        )

        # Validar quantidade
        assert len(vagas) == 4

        # Validar valores
        vagas_seg_sex = [v for v in vagas if v.dia_semana in {DiaSemana.SEGUNDA, DiaSemana.TERCA, DiaSemana.QUARTA}]
        vagas_sab_dom = [v for v in vagas if v.dia_semana in {DiaSemana.SABADO, DiaSemana.DOMINGO}]

        assert all(v.valor == 1700 for v in vagas_seg_sex)
        assert all(v.valor == 1800 for v in vagas_sab_dom)

        # Validar contato
        assert all(v.contato_nome == "Eloisa" for v in vagas)
        assert all(v.contato_whatsapp == "5511939050162" for v in vagas)
```

---

## Checklist de Conclusão

### Implementação
- [ ] Criar arquivo `gerador_vagas.py`
- [ ] Implementar `gerar_vagas_para_hospital()`
- [ ] Implementar `gerar_vagas()` (função principal)
- [ ] Implementar `validar_vagas()`
- [ ] Implementar `deduplicar_vagas()`
- [ ] Adicionar exports em `__init__.py`

### Testes
- [ ] Criar arquivo de testes
- [ ] Rodar testes
- [ ] 100% dos testes passando

### Qualidade
- [ ] Zero erros mypy
- [ ] Zero erros ruff

---

## Definition of Done (E07)

Este épico está **COMPLETO** quando:

1. ✅ Gera vagas para combinação hospital × data/período
2. ✅ Associa valor correto baseado no dia da semana
3. ✅ Inclui contato em todas as vagas
4. ✅ Valida vagas (remove inválidas)
5. ✅ Deduplica vagas
6. ✅ Teste de cenário completo passa
7. ✅ 100% dos testes passando
8. ✅ Zero erros mypy/ruff
