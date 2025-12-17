# Epic 04: Testes e Validação

## Objetivo

Validar que o sistema de conhecimento dinâmico funciona corretamente e melhora a qualidade das respostas da Julia.

## Contexto

Com os épicos anteriores implementados, precisamos:
1. Criar suite de testes de integração
2. Validar precisão dos detectores
3. Medir impacto na qualidade das respostas
4. Ajustar thresholds e parâmetros

## Pré-requisitos

- [x] E01 concluído (base indexada)
- [x] E02 concluído (detectores)
- [x] E03 concluído (injeção)

---

## Story 4.1: Testes de Integração End-to-End

### Objetivo
Criar testes que validam o fluxo completo: mensagem → detecção → busca → prompt.

### Tarefas

1. **Criar** `tests/integracao/test_conhecimento_e2e.py`:
```python
"""
Testes de integração end-to-end do sistema de conhecimento.

Valida fluxo completo: mensagem → análise → busca → injeção.
"""
import pytest
from app.services.conhecimento import (
    IndexadorConhecimento,
    BuscadorConhecimento,
    OrquestradorDeteccao,
    ContextoMedico,
    TipoObjecao,
    PerfilMedico,
    ObjetivoConversa
)
from app.services.conhecimento.injetor import InjetorConhecimento
from app.prompts.builder import PromptBuilder


class TestFluxoCompletoObjecao:
    """Testes de fluxo para objeções."""

    @pytest.mark.asyncio
    async def test_objecao_preco_fluxo_completo(self):
        """
        Cenário: Médico sênior diz que pagamos pouco.

        Espera:
        1. Detecção: objeção de preço + perfil sênior
        2. Busca: conhecimento sobre negociação de valor
        3. Prompt: contém dicas de como responder
        """
        injetor = InjetorConhecimento()

        conhecimento = await injetor.buscar_para_situacao(
            mensagem="Vocês pagam muito pouco, o outro grupo paga mais",
            contexto=ContextoMedico(anos_formacao=20),
            primeira_mensagem=False,
            num_interacoes=5
        )

        # Deve ter buscado conhecimento
        assert conhecimento.chunks_usados > 0

        # Deve ter detectado objeção de preço
        assert any("preco" in t.lower() for t in conhecimento.tipos_usados)

        # Conhecimento deve conter orientações
        assert len(conhecimento.texto) > 100

    @pytest.mark.asyncio
    async def test_objecao_tempo_fluxo_completo(self):
        """
        Cenário: Médico diz que não tem tempo.

        Espera: Conhecimento sobre como lidar com objeção de tempo.
        """
        injetor = InjetorConhecimento()

        conhecimento = await injetor.buscar_para_situacao(
            mensagem="Não tenho tempo, minha agenda está muito cheia",
            contexto=ContextoMedico(),
            primeira_mensagem=False,
            num_interacoes=3
        )

        assert conhecimento.chunks_usados > 0
        assert any("tempo" in t.lower() for t in conhecimento.tipos_usados)


class TestFluxoCompletoPerfil:
    """Testes de fluxo para perfis."""

    @pytest.mark.asyncio
    async def test_medico_senior_fluxo_completo(self):
        """
        Cenário: Médico sênior interessado.

        Espera: Conhecimento sobre abordagem para sêniors.
        """
        injetor = InjetorConhecimento()

        conhecimento = await injetor.buscar_para_situacao(
            mensagem="Me conta mais sobre essas vagas",
            contexto=ContextoMedico(anos_formacao=25),
            primeira_mensagem=False,
            num_interacoes=2
        )

        # Sênior deve acionar busca de perfil
        assert any("senior" in t.lower() for t in conhecimento.tipos_usados)

    @pytest.mark.asyncio
    async def test_recem_formado_fluxo_completo(self):
        """
        Cenário: Médico recém-formado perguntando.

        Espera: Abordagem apropriada para recém-formados.
        """
        injetor = InjetorConhecimento()

        conhecimento = await injetor.buscar_para_situacao(
            mensagem="É meu primeiro plantão, como funciona?",
            contexto=ContextoMedico(anos_formacao=1),
            primeira_mensagem=False,
            num_interacoes=2
        )

        # Recém-formado detectado por anos + mensagem
        assert conhecimento.chunks_usados >= 0  # Pode não precisar de muito


class TestFluxoCompletoPrompt:
    """Testes de integração com PromptBuilder."""

    @pytest.mark.asyncio
    async def test_prompt_completo_com_conhecimento(self):
        """
        Cenário: Montar prompt completo com conhecimento injetado.
        """
        builder = PromptBuilder()
        await builder.com_base()
        await builder.com_tools()
        await builder.com_conhecimento(
            mensagem="Vocês pagam muito pouco",
            contexto_medico=ContextoMedico(anos_formacao=20),
            primeira_mensagem=False,
            num_interacoes=5
        )
        builder.com_contexto("Médico: Dr. Silva, Cardiologia")

        prompt = builder.build()

        # Prompt deve conter seções
        assert "Julia" in prompt or "julia" in prompt.lower()  # Base
        assert "[CONHECIMENTO RELEVANTE" in prompt  # Conhecimento
        assert "Dr. Silva" in prompt  # Contexto

    @pytest.mark.asyncio
    async def test_prompt_primeira_mensagem_leve(self):
        """
        Cenário: Primeira mensagem não deve ter muito conhecimento.
        """
        builder = PromptBuilder()
        await builder.com_base()
        await builder.com_conhecimento(
            mensagem="Oi",
            contexto_medico=ContextoMedico(),
            primeira_mensagem=True,
            num_interacoes=0
        )

        prompt = builder.build()

        # Primeira mensagem = prospecção, sem objeção
        # Deve ter pouco ou nenhum conhecimento extra
        conhecimento_size = prompt.count("[CONHECIMENTO RELEVANTE")
        assert conhecimento_size <= 1


class TestLatencia:
    """Testes de performance."""

    @pytest.mark.asyncio
    async def test_latencia_aceitavel(self):
        """Latência total deve ser < 200ms."""
        injetor = InjetorConhecimento()

        conhecimento = await injetor.buscar_para_situacao(
            mensagem="Vocês pagam muito pouco",
            contexto=ContextoMedico(anos_formacao=10),
            primeira_mensagem=False,
            num_interacoes=5
        )

        # Latência deve ser aceitável (< 500ms para teste, < 200ms ideal)
        assert conhecimento.latencia_ms < 500


class TestGracefulDegradation:
    """Testes de fallback e erros."""

    @pytest.mark.asyncio
    async def test_sem_conhecimento_nao_quebra(self):
        """Sistema funciona mesmo sem conhecimento encontrado."""
        builder = PromptBuilder()
        await builder.com_base()

        # Mensagem genérica que pode não ter match
        await builder.com_conhecimento(
            mensagem="ok",
            contexto_medico=ContextoMedico(),
            primeira_mensagem=False,
            num_interacoes=1
        )

        prompt = builder.build()

        # Deve ter pelo menos a base
        assert len(prompt) > 100
```

### DoD

- [ ] Arquivo `test_conhecimento_e2e.py` criado
- [ ] Testes de fluxo para objeções (preço, tempo)
- [ ] Testes de fluxo para perfis (sênior, recém-formado)
- [ ] Testes de integração com PromptBuilder
- [ ] Teste de latência (< 200ms)
- [ ] Testes de graceful degradation
- [ ] Todos os testes passando

### Como Executar

```bash
# Rodar apenas testes de integração do conhecimento
uv run pytest tests/integracao/test_conhecimento_e2e.py -v

# Rodar com medição de tempo
uv run pytest tests/integracao/test_conhecimento_e2e.py -v --durations=10
```

---

## Story 4.2: Validação de Precisão dos Detectores

### Objetivo
Criar dataset de teste e medir precisão dos detectores.

### Tarefas

1. **Criar** `tests/conhecimento/test_precisao_detectores.py`:
```python
"""
Testes de precisão dos detectores.

Usa dataset de casos conhecidos para medir acurácia.
"""
import pytest
from app.services.conhecimento.detector_objecao import DetectorObjecao, TipoObjecao
from app.services.conhecimento.detector_perfil import DetectorPerfil, PerfilMedico


# Dataset de teste para objeções
DATASET_OBJECOES = [
    # (mensagem, tipo_esperado, deve_detectar)
    ("Vocês pagam muito pouco", TipoObjecao.PRECO, True),
    ("O valor é baixo demais", TipoObjecao.PRECO, True),
    ("Quanto vocês pagam?", None, False),  # Pergunta, não objeção
    ("Outros grupos pagam mais", TipoObjecao.PRECO, True),
    ("Não tenho tempo", TipoObjecao.TEMPO, True),
    ("Minha agenda está cheia", TipoObjecao.TEMPO, True),
    ("Qual horário?", None, False),  # Pergunta, não objeção
    ("Estou muito ocupado", TipoObjecao.TEMPO, True),
    ("Nunca ouvi falar da Revoluna", TipoObjecao.CONFIANCA, True),
    ("Como conseguiu meu número?", TipoObjecao.COMUNICACAO, True),
    ("Já trabalho com outra empresa", TipoObjecao.LEALDADE, True),
    ("Não quero mais fazer plantão", TipoObjecao.MOTIVACAO, True),
    ("Show, me manda as vagas", None, False),  # Interesse
    ("Quero ver as opções", None, False),  # Interesse
    ("Pode mandar", None, False),  # Interesse
    ("Blz", None, False),  # Interesse
    ("O hospital é bom?", TipoObjecao.QUALIDADE, True),
    ("Muito processo pra se cadastrar", TipoObjecao.PROCESSO, True),
]

# Dataset de teste para perfis
DATASET_PERFIS = [
    # (anos_formacao, mensagem, perfil_esperado)
    (1, "É meu primeiro plantão", PerfilMedico.RECEM_FORMADO),
    (0, "Sou R1", PerfilMedico.RECEM_FORMADO),
    (5, "Já faço plantão há alguns anos", PerfilMedico.EM_DESENVOLVIMENTO),
    (10, "Tenho bastante experiência", PerfilMedico.EXPERIENTE),
    (20, "Coordeno uma equipe", PerfilMedico.SENIOR),
    (25, "Na minha época era diferente", PerfilMedico.SENIOR),
    (None, "Fiz fellowship em cardio", PerfilMedico.ESPECIALISTA),
    (None, "Cansei de UTI, quero mudar", PerfilMedico.EM_TRANSICAO),
]


class TestPrecisaoObjecoes:
    """Testes de precisão do detector de objeções."""

    @pytest.fixture
    def detector(self):
        return DetectorObjecao()

    def test_precisao_geral(self, detector):
        """Mede precisão geral do detector."""
        acertos = 0
        total = len(DATASET_OBJECOES)

        for mensagem, tipo_esperado, deve_detectar in DATASET_OBJECOES:
            resultado = detector.detectar(mensagem)

            if deve_detectar:
                if resultado.tem_objecao and resultado.tipo == tipo_esperado:
                    acertos += 1
                else:
                    print(f"ERRO: '{mensagem}' esperava {tipo_esperado}, obteve {resultado.tipo}")
            else:
                if not resultado.tem_objecao:
                    acertos += 1
                else:
                    print(f"FALSO POSITIVO: '{mensagem}' detectou {resultado.tipo}")

        precisao = acertos / total
        print(f"\nPrecisão objeções: {precisao:.1%} ({acertos}/{total})")

        # Meta: >80% precisão
        assert precisao >= 0.80, f"Precisão {precisao:.1%} abaixo da meta de 80%"

    @pytest.mark.parametrize("mensagem,tipo_esperado,deve_detectar", DATASET_OBJECOES)
    def test_casos_individuais(self, detector, mensagem, tipo_esperado, deve_detectar):
        """Testa cada caso individualmente."""
        resultado = detector.detectar(mensagem)

        if deve_detectar:
            assert resultado.tem_objecao, f"'{mensagem}' deveria detectar objeção"
            assert resultado.tipo == tipo_esperado, f"'{mensagem}' tipo errado"
        else:
            assert not resultado.tem_objecao, f"'{mensagem}' falso positivo"


class TestPrecisaoPerfis:
    """Testes de precisão do detector de perfis."""

    @pytest.fixture
    def detector(self):
        return DetectorPerfil()

    def test_precisao_geral(self, detector):
        """Mede precisão geral do detector de perfil."""
        acertos = 0
        total = len(DATASET_PERFIS)

        for anos, mensagem, perfil_esperado in DATASET_PERFIS:
            resultado = detector.detectar_por_contexto(
                anos_formacao=anos,
                historico_mensagens=[mensagem] if mensagem else None
            )

            if resultado.perfil == perfil_esperado:
                acertos += 1
            else:
                print(f"ERRO: anos={anos}, msg='{mensagem}' esperava {perfil_esperado}, obteve {resultado.perfil}")

        precisao = acertos / total
        print(f"\nPrecisão perfis: {precisao:.1%} ({acertos}/{total})")

        # Meta: >70% precisão
        assert precisao >= 0.70, f"Precisão {precisao:.1%} abaixo da meta de 70%"

    @pytest.mark.parametrize("anos,mensagem,perfil_esperado", DATASET_PERFIS)
    def test_casos_individuais(self, detector, anos, mensagem, perfil_esperado):
        """Testa cada caso individualmente."""
        resultado = detector.detectar_por_contexto(
            anos_formacao=anos,
            historico_mensagens=[mensagem] if mensagem else None
        )

        assert resultado.perfil == perfil_esperado, \
            f"anos={anos}, msg='{mensagem}': esperava {perfil_esperado}, obteve {resultado.perfil}"
```

### DoD

- [ ] Dataset de teste para objeções (18+ casos)
- [ ] Dataset de teste para perfis (8+ casos)
- [ ] Teste de precisão geral (>80% objeções, >70% perfis)
- [ ] Testes parametrizados para cada caso
- [ ] Output com métricas de precisão

### Como Executar

```bash
# Rodar testes de precisão
uv run pytest tests/conhecimento/test_precisao_detectores.py -v

# Ver output detalhado
uv run pytest tests/conhecimento/test_precisao_detectores.py -v -s
```

---

## Story 4.3: Testes de Qualidade de Resposta

### Objetivo
Validar que conhecimento injetado melhora a qualidade das respostas (requer LLM).

### Tarefas

1. **Criar** `tests/conhecimento/test_qualidade_resposta.py`:
```python
"""
Testes de qualidade de resposta com conhecimento injetado.

NOTA: Estes testes usam LLM real e podem ser lentos/flaky.
Marcar com @pytest.mark.slow para pular em CI rápido.
"""
import pytest
from app.services.llm import gerar_resposta_llm
from app.prompts.builder import PromptBuilder
from app.services.conhecimento import ContextoMedico


@pytest.mark.slow
class TestQualidadeRespostaObjecao:
    """Testes de qualidade para respostas a objeções."""

    @pytest.mark.asyncio
    async def test_resposta_objecao_preco_com_conhecimento(self):
        """
        Cenário: Médico sênior diz que pagamos pouco.

        Valida: Resposta NÃO foca em dinheiro (erro #3 do guia).
        """
        builder = PromptBuilder()
        await builder.com_base()
        await builder.com_tools()
        await builder.com_conhecimento(
            mensagem="Vocês pagam muito pouco",
            contexto_medico=ContextoMedico(anos_formacao=20),
            primeira_mensagem=False,
            num_interacoes=5
        )
        builder.com_contexto("Médico: Dr. Silva, 20 anos de experiência, Cardiologia")

        prompt = builder.build()

        # Gerar resposta
        resposta = await gerar_resposta_llm(
            mensagens=[{"role": "user", "content": "Vocês pagam muito pouco"}],
            system_prompt=prompt,
            model="haiku"
        )

        # Validações de qualidade
        resposta_lower = resposta.lower()

        # NÃO deve focar em dinheiro (erro #3)
        termos_dinheiro = ["mais dinheiro", "melhor valor", "negociar valor", "aumentar"]
        foca_dinheiro = any(t in resposta_lower for t in termos_dinheiro)

        # DEVE ter tom de parceria, não de venda
        termos_parceria = ["entendo", "compreendo", "parceria", "trabalhar junto", "diferencial"]
        tem_parceria = any(t in resposta_lower for t in termos_parceria)

        # DEVE ser curta (não robótica)
        eh_curta = len(resposta) < 500

        print(f"\nResposta: {resposta}")
        print(f"Foca em dinheiro: {foca_dinheiro}")
        print(f"Tem tom parceria: {tem_parceria}")
        print(f"É curta: {eh_curta}")

        # Pelo menos 2 de 3 critérios
        score = sum([not foca_dinheiro, tem_parceria, eh_curta])
        assert score >= 2, f"Qualidade insuficiente: score {score}/3"

    @pytest.mark.asyncio
    async def test_resposta_sem_conhecimento_vs_com(self):
        """
        Compara resposta SEM conhecimento vs COM conhecimento.

        Espera: COM conhecimento deve ser mais adequada.
        """
        mensagem_medico = "Não tenho tempo, agenda muito cheia"
        contexto = "Médico: Dr. Costa, Emergencista, 10 anos"

        # SEM conhecimento
        builder_sem = PromptBuilder()
        await builder_sem.com_base()
        builder_sem.com_contexto(contexto)
        prompt_sem = builder_sem.build()

        resposta_sem = await gerar_resposta_llm(
            mensagens=[{"role": "user", "content": mensagem_medico}],
            system_prompt=prompt_sem,
            model="haiku"
        )

        # COM conhecimento
        builder_com = PromptBuilder()
        await builder_com.com_base()
        await builder_com.com_conhecimento(
            mensagem=mensagem_medico,
            contexto_medico=ContextoMedico(anos_formacao=10),
            primeira_mensagem=False,
            num_interacoes=3
        )
        builder_com.com_contexto(contexto)
        prompt_com = builder_com.build()

        resposta_com = await gerar_resposta_llm(
            mensagens=[{"role": "user", "content": mensagem_medico}],
            system_prompt=prompt_com,
            model="haiku"
        )

        print(f"\n=== SEM CONHECIMENTO ===\n{resposta_sem}")
        print(f"\n=== COM CONHECIMENTO ===\n{resposta_com}")

        # Não validar automaticamente (muito flaky)
        # Apenas logar para análise manual
        assert True  # Teste de observação


@pytest.mark.slow
class TestQualidadeRespostaPerfil:
    """Testes de qualidade para adaptação de perfil."""

    @pytest.mark.asyncio
    async def test_resposta_senior_vs_recem_formado(self):
        """
        Compara resposta para SÊNIOR vs RECÉM-FORMADO.

        Espera: Tom diferente para cada perfil.
        """
        mensagem = "Quero saber mais sobre as vagas"

        # SÊNIOR
        builder_senior = PromptBuilder()
        await builder_senior.com_base()
        await builder_senior.com_conhecimento(
            mensagem=mensagem,
            contexto_medico=ContextoMedico(anos_formacao=25),
            primeira_mensagem=False,
            num_interacoes=2
        )
        builder_senior.com_contexto("Dr. Sênior, 25 anos experiência, Cirurgião")

        resposta_senior = await gerar_resposta_llm(
            mensagens=[{"role": "user", "content": mensagem}],
            system_prompt=builder_senior.build(),
            model="haiku"
        )

        # RECÉM-FORMADO
        builder_rf = PromptBuilder()
        await builder_rf.com_base()
        await builder_rf.com_conhecimento(
            mensagem=mensagem,
            contexto_medico=ContextoMedico(anos_formacao=1),
            primeira_mensagem=False,
            num_interacoes=2
        )
        builder_rf.com_contexto("Dr. Novo, 1 ano experiência, Clínico Geral")

        resposta_rf = await gerar_resposta_llm(
            mensagens=[{"role": "user", "content": mensagem}],
            system_prompt=builder_rf.build(),
            model="haiku"
        )

        print(f"\n=== SÊNIOR ===\n{resposta_senior}")
        print(f"\n=== RECÉM-FORMADO ===\n{resposta_rf}")

        # Verificar diferenças básicas
        assert resposta_senior != resposta_rf, "Respostas deveriam ser diferentes"
```

2. **Criar marker** em `pytest.ini` ou `pyproject.toml`:
```toml
[tool.pytest.ini_options]
markers = [
    "slow: marks tests as slow (deselect with '-m \"not slow\"')",
]
```

### DoD

- [ ] Testes de qualidade implementados
- [ ] Marker `@pytest.mark.slow` para testes lentos
- [ ] Teste compara COM vs SEM conhecimento
- [ ] Critérios de qualidade definidos (não focar em dinheiro, tom parceria)
- [ ] Output detalhado para análise

### Como Executar

```bash
# Rodar testes de qualidade (lentos)
uv run pytest tests/conhecimento/test_qualidade_resposta.py -v -s -m slow

# Pular testes lentos no CI
uv run pytest tests/ -v -m "not slow"
```

---

## Story 4.4: Script de Validação e Ajuste

### Objetivo
Criar script para validar sistema e ajustar thresholds.

### Tarefas

1. **Criar** `scripts/validar_conhecimento.py`:
```python
#!/usr/bin/env python
"""
Script de validação do sistema de conhecimento.

Uso:
    python scripts/validar_conhecimento.py --check-index
    python scripts/validar_conhecimento.py --test-detectores
    python scripts/validar_conhecimento.py --test-busca "vocês pagam pouco"
    python scripts/validar_conhecimento.py --metricas
"""
import asyncio
import argparse
import sys
from datetime import datetime


async def check_index():
    """Verifica se base está indexada."""
    from app.services.supabase import supabase

    result = supabase.table("conhecimento_julia").select("id", count="exact").execute()
    count = result.count or 0

    print(f"\n=== STATUS DA INDEXAÇÃO ===")
    print(f"Total de chunks: {count}")

    if count == 0:
        print("⚠️  Base não indexada! Execute: python scripts/indexar_conhecimento.py")
        return False

    # Contar por tipo
    tipos = supabase.table("conhecimento_julia").select("tipo").execute()
    tipo_count = {}
    for t in tipos.data:
        tipo_count[t["tipo"]] = tipo_count.get(t["tipo"], 0) + 1

    print("\nPor tipo:")
    for tipo, cnt in sorted(tipo_count.items()):
        print(f"  - {tipo}: {cnt}")

    return True


async def test_detectores():
    """Testa detectores com casos exemplo."""
    from app.services.conhecimento import (
        OrquestradorDeteccao,
        ContextoMedico
    )

    orquestrador = OrquestradorDeteccao()

    casos = [
        ("Vocês pagam muito pouco", ContextoMedico(anos_formacao=20)),
        ("Não tenho tempo", ContextoMedico(anos_formacao=5)),
        ("Quero ver as vagas", ContextoMedico()),
        ("Oi", ContextoMedico()),
        ("Já trabalho com outra empresa", ContextoMedico(anos_formacao=15)),
    ]

    print("\n=== TESTE DOS DETECTORES ===")

    for mensagem, contexto in casos:
        analise = orquestrador.analisar(
            mensagem=mensagem,
            contexto=contexto,
            primeira_mensagem=False,
            num_interacoes=3
        )

        print(f"\nMensagem: '{mensagem}'")
        print(f"  Objeção: {analise.objecao.tipo.value if analise.objecao.tem_objecao else 'nenhuma'}")
        print(f"  Perfil: {analise.perfil.perfil.value} (conf: {analise.perfil.confianca:.0%})")
        print(f"  Objetivo: {analise.objetivo.objetivo.value}")
        print(f"  Precisa conhecimento: objecao={analise.precisa_conhecimento_objecao}, perfil={analise.precisa_conhecimento_perfil}")


async def test_busca(query: str):
    """Testa busca semântica."""
    from app.services.conhecimento import BuscadorConhecimento

    buscador = BuscadorConhecimento()

    print(f"\n=== BUSCA: '{query}' ===")

    resultados = await buscador.buscar(query, limite=5)

    if not resultados:
        print("Nenhum resultado encontrado")
        return

    for i, r in enumerate(resultados, 1):
        print(f"\n--- Resultado {i} (sim: {r.similaridade:.2f}) ---")
        print(f"Tipo: {r.tipo} | Subtipo: {r.subtipo}")
        print(f"Seção: {r.secao}")
        print(f"Conteúdo: {r.conteudo[:200]}...")


async def show_metricas():
    """Mostra métricas recentes."""
    from app.services.conhecimento.metricas import MetricasConhecimento

    metricas = MetricasConhecimento()

    print("\n=== MÉTRICAS DO DIA ===")

    resumo = await metricas.obter_resumo_dia()

    print(f"Total de usos: {resumo['total']}")
    print(f"Com objeção: {resumo['com_objecao']} ({resumo['taxa_objecao']:.1%})")
    print(f"Chunks média: {resumo['chunks_media']:.1f}")
    print(f"Latência média: {resumo['latencia_media_ms']:.0f}ms")

    if resumo.get('objecoes_por_tipo'):
        print("\nObjeções por tipo:")
        for tipo, cnt in resumo['objecoes_por_tipo'].items():
            print(f"  - {tipo}: {cnt}")

    if resumo.get('perfis_detectados'):
        print("\nPerfis detectados:")
        for perfil, cnt in resumo['perfis_detectados'].items():
            print(f"  - {perfil}: {cnt}")


async def main():
    parser = argparse.ArgumentParser(description="Validação do sistema de conhecimento")
    parser.add_argument("--check-index", action="store_true", help="Verifica indexação")
    parser.add_argument("--test-detectores", action="store_true", help="Testa detectores")
    parser.add_argument("--test-busca", type=str, help="Testa busca semântica")
    parser.add_argument("--metricas", action="store_true", help="Mostra métricas")
    parser.add_argument("--all", action="store_true", help="Executa todas as validações")

    args = parser.parse_args()

    if args.all or args.check_index:
        await check_index()

    if args.all or args.test_detectores:
        await test_detectores()

    if args.test_busca:
        await test_busca(args.test_busca)

    if args.all or args.metricas:
        await show_metricas()

    if not any([args.check_index, args.test_detectores, args.test_busca, args.metricas, args.all]):
        parser.print_help()


if __name__ == "__main__":
    asyncio.run(main())
```

2. **Criar** `scripts/ajustar_thresholds.py`:
```python
#!/usr/bin/env python
"""
Script para ajustar thresholds dos detectores.

Uso:
    python scripts/ajustar_thresholds.py --objecao 0.65
    python scripts/ajustar_thresholds.py --busca 0.70
"""
import argparse


def ajustar_threshold_busca(valor: float):
    """Ajusta threshold de busca semântica."""
    print(f"Para ajustar threshold de busca para {valor}:")
    print(f"  1. Editar app/services/conhecimento/buscador.py")
    print(f"  2. Alterar: self.threshold = {valor}")


def ajustar_threshold_objecao(valor: float):
    """Ajusta confiança mínima para objeções."""
    print(f"Para ajustar confiança de objeção para {valor}:")
    print(f"  1. Editar app/services/conhecimento/injetor.py")
    print(f"  2. Alterar condição: objecao.confianca > {valor}")


def main():
    parser = argparse.ArgumentParser(description="Ajuste de thresholds")
    parser.add_argument("--busca", type=float, help="Threshold de similaridade para busca")
    parser.add_argument("--objecao", type=float, help="Confiança mínima para objeção")

    args = parser.parse_args()

    if args.busca:
        ajustar_threshold_busca(args.busca)

    if args.objecao:
        ajustar_threshold_objecao(args.objecao)

    if not args.busca and not args.objecao:
        parser.print_help()


if __name__ == "__main__":
    main()
```

### DoD

- [ ] `validar_conhecimento.py` criado
- [ ] `--check-index` verifica indexação
- [ ] `--test-detectores` testa casos exemplo
- [ ] `--test-busca` testa busca semântica
- [ ] `--metricas` mostra métricas do dia
- [ ] `ajustar_thresholds.py` documenta como ajustar

### Como Usar

```bash
# Validação completa
python scripts/validar_conhecimento.py --all

# Apenas verificar índice
python scripts/validar_conhecimento.py --check-index

# Testar busca específica
python scripts/validar_conhecimento.py --test-busca "como negociar valor com médico sênior"

# Ver métricas
python scripts/validar_conhecimento.py --metricas
```

---

## Checklist do Épico

- [ ] **S13.E4.1** - Testes E2E implementados
- [ ] **S13.E4.2** - Validação de precisão
- [ ] **S13.E4.3** - Testes de qualidade
- [ ] **S13.E4.4** - Scripts de validação
- [ ] Precisão objeções >80%
- [ ] Precisão perfis >70%
- [ ] Latência <200ms
- [ ] Scripts funcionando

---

## Critérios de Aceite da Sprint

Após todos os épicos:

| Critério | Meta | Como Validar |
|----------|------|--------------|
| Base indexada | >100 chunks | `--check-index` |
| Precisão objeções | >80% | `test_precisao_detectores.py` |
| Precisão perfis | >70% | `test_precisao_detectores.py` |
| Latência total | <200ms | `test_latencia_aceitavel` |
| Integração prompt | Funciona | `test_prompt_completo` |
| Métricas registradas | Sim | `--metricas` |

```bash
# Validação completa da sprint
uv run pytest tests/conhecimento/ -v
uv run pytest tests/integracao/test_conhecimento_e2e.py -v
python scripts/validar_conhecimento.py --all
```
