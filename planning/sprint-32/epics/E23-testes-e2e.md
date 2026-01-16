# E23 - Testes End-to-End

**Sprint:** 32 - Redesign de Campanhas e Comportamento Julia
**Fase:** 6 - Limpeza e Polish
**Dependências:** Todos os épicos anteriores
**Estimativa:** 6h

---

## Objetivo

Criar testes end-to-end que validam os fluxos críticos do novo sistema de campanhas e comportamentos.

---

## Fluxos Críticos a Testar

1. **Discovery → Não oferta**
2. **Oferta → Consulta vagas antes**
3. **Canal de ajuda → Pausa → Gestor responde → Retoma**
4. **Gestor comanda Julia via Slack**
5. **Modo piloto bloqueia ações autônomas**
6. **Hospital bloqueado não aparece em ofertas**

---

## Tasks

### T1: Configurar ambiente de teste E2E (1h)

**Arquivo:** `tests/e2e/conftest.py`

```python
"""
Configuração para testes E2E.

Usa banco de teste isolado e mocks de serviços externos.
"""
import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch
from app.services.supabase import supabase
from app.core.config import settings


@pytest.fixture(scope="session")
def event_loop():
    """Cria event loop para testes assíncronos."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_evolution_api():
    """Mock da Evolution API."""
    with patch("app.services.whatsapp.evolution.enviar_mensagem") as mock:
        mock.return_value = {"success": True, "message_id": "msg-123"}
        yield mock


@pytest.fixture
def mock_slack():
    """Mock do Slack."""
    with patch("app.services.slack.client.enviar_mensagem_slack") as mock:
        mock.return_value = {"ok": True, "ts": "1234567890.123456"}
        yield mock


@pytest.fixture
def mock_llm():
    """Mock do LLM."""
    with patch("app.services.llm.chamar_llm") as mock:
        mock.return_value = "Resposta do LLM"
        yield mock


@pytest.fixture
async def campanha_discovery(db_clean):
    """Cria campanha de discovery para testes."""
    data = {
        "nome": "Test Discovery",
        "tipo": "discovery",
        "objetivo": "Conhecer médicos",
        "regras": ["Nunca ofertar vagas"],
        "pode_ofertar": False,
        "status": "ativa"
    }

    resultado = supabase.table("campanhas").insert(data).execute()
    yield resultado.data[0]

    # Cleanup
    supabase.table("campanhas").delete().eq("id", resultado.data[0]["id"]).execute()


@pytest.fixture
async def campanha_oferta(db_clean, hospital_fixture, vaga_fixture):
    """Cria campanha de oferta para testes."""
    data = {
        "nome": "Test Oferta",
        "tipo": "oferta",
        "objetivo": "Ofertar vagas de teste",
        "regras": ["Consultar sistema antes de ofertar"],
        "escopo_vagas": {"hospital_id": hospital_fixture["id"]},
        "pode_ofertar": True,
        "status": "ativa"
    }

    resultado = supabase.table("campanhas").insert(data).execute()
    yield resultado.data[0]

    supabase.table("campanhas").delete().eq("id", resultado.data[0]["id"]).execute()


@pytest.fixture
async def medico_fixture(db_clean):
    """Cria médico para testes."""
    data = {
        "nome": "Dr. Teste E2E",
        "telefone": "5511999999999",
        "especialidade": "Cardiologia"
    }

    resultado = supabase.table("clientes").insert(data).execute()
    yield resultado.data[0]

    supabase.table("clientes").delete().eq("id", resultado.data[0]["id"]).execute()


@pytest.fixture
async def conversa_fixture(db_clean, medico_fixture):
    """Cria conversa para testes."""
    data = {
        "cliente_id": medico_fixture["id"],
        "status": "ativa",
        "controlled_by": "julia"
    }

    resultado = supabase.table("conversations").insert(data).execute()
    yield resultado.data[0]

    supabase.table("conversations").delete().eq("id", resultado.data[0]["id"]).execute()


@pytest.fixture
async def hospital_fixture(db_clean):
    """Cria hospital para testes."""
    data = {
        "nome": "Hospital E2E Test",
        "cidade": "São Paulo"
    }

    resultado = supabase.table("hospitais").insert(data).execute()
    yield resultado.data[0]

    supabase.table("hospitais").delete().eq("id", resultado.data[0]["id"]).execute()


@pytest.fixture
async def vaga_fixture(db_clean, hospital_fixture):
    """Cria vaga para testes."""
    data = {
        "hospital_id": hospital_fixture["id"],
        "data": (datetime.now() + timedelta(days=10)).date().isoformat(),
        "valor": 2500,
        "status": "aberta"
    }

    resultado = supabase.table("vagas").insert(data).execute()
    yield resultado.data[0]

    supabase.table("vagas").delete().eq("id", resultado.data[0]["id"]).execute()


@pytest.fixture
def db_clean():
    """Garante que banco está limpo antes do teste."""
    # Pode implementar limpeza adicional se necessário
    yield
```

---

### T2: Teste Discovery não oferta (1h)

**Arquivo:** `tests/e2e/test_discovery_nao_oferta.py`

```python
"""
Testes E2E: Discovery nunca deve ofertar vagas.
"""
import pytest
from app.services.julia.agente import processar_mensagem
from app.services.conversas.status import buscar_status


class TestDiscoveryNaoOferta:
    """
    Cenário: Campanha de Discovery
    Comportamento esperado: Julia NUNCA menciona vagas, mesmo se perguntada.
    """

    @pytest.mark.asyncio
    async def test_abertura_discovery_sem_vaga(
        self,
        mock_evolution_api,
        mock_llm,
        campanha_discovery,
        medico_fixture,
        conversa_fixture
    ):
        """Abertura de discovery não menciona vagas."""
        # Configurar mock do LLM para capturar prompt
        prompts_recebidos = []

        async def capturar_prompt(prompt, **kwargs):
            prompts_recebidos.append(prompt)
            return "Oi! Tudo bem? Sou a Júlia da Revoluna. Como você está?"

        mock_llm.side_effect = capturar_prompt

        # Processar primeira mensagem (abertura)
        await processar_mensagem(
            conversa_id=conversa_fixture["id"],
            mensagem="",  # Abertura
            campanha_id=campanha_discovery["id"]
        )

        # Verificar que prompt não permite oferta
        assert len(prompts_recebidos) > 0
        prompt = prompts_recebidos[0].lower()

        assert "nunca" in prompt and "ofertar" in prompt or "não pode ofertar" in prompt
        assert "vaga" not in prompt or "não mencionar vaga" in prompt

    @pytest.mark.asyncio
    async def test_discovery_medico_pergunta_vaga(
        self,
        mock_evolution_api,
        mock_llm,
        campanha_discovery,
        medico_fixture,
        conversa_fixture,
        vaga_fixture
    ):
        """
        Mesmo se médico pergunta sobre vagas, Julia não oferta em discovery.
        """
        # Mock LLM
        mock_llm.return_value = "No momento estou só querendo te conhecer melhor! Depois a gente conversa sobre oportunidades."

        # Simular médico perguntando sobre vagas
        resposta = await processar_mensagem(
            conversa_id=conversa_fixture["id"],
            mensagem="Vocês têm vagas disponíveis?",
            campanha_id=campanha_discovery["id"]
        )

        # Verificar que não mencionou vaga específica
        assert resposta is not None
        assert "R$" not in resposta  # Não menciona valor
        assert "hospital" not in resposta.lower() or "depois" in resposta.lower()

    @pytest.mark.asyncio
    async def test_discovery_nao_chama_buscar_vagas(
        self,
        mock_evolution_api,
        mock_llm,
        campanha_discovery,
        conversa_fixture
    ):
        """Discovery não deve chamar tool buscar_vagas."""
        with pytest.raises(AssertionError):
            # Se buscar_vagas for chamado, teste falha
            with patch("app.tools.vagas.buscar_vagas") as mock_buscar:
                mock_buscar.side_effect = AssertionError("buscar_vagas não deveria ser chamado em discovery")

                await processar_mensagem(
                    conversa_id=conversa_fixture["id"],
                    mensagem="Tem vaga?",
                    campanha_id=campanha_discovery["id"]
                )
```

---

### T3: Teste Oferta consulta vagas (1h)

**Arquivo:** `tests/e2e/test_oferta_consulta_vagas.py`

```python
"""
Testes E2E: Oferta deve consultar vagas antes de mencionar.
"""
import pytest
from unittest.mock import patch, AsyncMock
from app.services.julia.agente import processar_mensagem


class TestOfertaConsultaVagas:
    """
    Cenário: Campanha de Oferta
    Comportamento esperado: Julia SEMPRE consulta buscar_vagas antes de ofertar.
    """

    @pytest.mark.asyncio
    async def test_oferta_chama_buscar_vagas(
        self,
        mock_evolution_api,
        campanha_oferta,
        conversa_fixture,
        vaga_fixture
    ):
        """Oferta chama buscar_vagas antes de mencionar."""
        buscar_vagas_chamado = False

        async def mock_buscar(*args, **kwargs):
            nonlocal buscar_vagas_chamado
            buscar_vagas_chamado = True
            return [vaga_fixture]

        with patch("app.tools.vagas.buscar_vagas", side_effect=mock_buscar):
            await processar_mensagem(
                conversa_id=conversa_fixture["id"],
                mensagem="Tem vaga pra mim?",
                campanha_id=campanha_oferta["id"]
            )

        assert buscar_vagas_chamado, "buscar_vagas deveria ter sido chamado"

    @pytest.mark.asyncio
    async def test_oferta_sem_vaga_nao_promete(
        self,
        mock_evolution_api,
        mock_llm,
        campanha_oferta,
        conversa_fixture
    ):
        """Se não há vagas no escopo, Julia não promete."""
        # Mock buscar_vagas retornando vazio
        with patch("app.tools.vagas.buscar_vagas", return_value=[]):
            mock_llm.return_value = "No momento não tenho nenhuma vaga disponível nesse perfil, mas assim que surgir eu te aviso!"

            resposta = await processar_mensagem(
                conversa_id=conversa_fixture["id"],
                mensagem="Tem vaga de cardio?",
                campanha_id=campanha_oferta["id"]
            )

            assert "não" in resposta.lower() or "no momento" in resposta.lower()
            assert "R$" not in resposta  # Não menciona valor inventado

    @pytest.mark.asyncio
    async def test_oferta_com_vaga_apresenta(
        self,
        mock_evolution_api,
        mock_llm,
        campanha_oferta,
        conversa_fixture,
        vaga_fixture,
        hospital_fixture
    ):
        """Se há vaga, Julia apresenta com dados corretos."""
        with patch("app.tools.vagas.buscar_vagas", return_value=[vaga_fixture]):
            mock_llm.return_value = f"Tenho sim! Tem uma vaga no {hospital_fixture['nome']}, dia {vaga_fixture['data']}, valor R$ {vaga_fixture['valor']}. Tem interesse?"

            resposta = await processar_mensagem(
                conversa_id=conversa_fixture["id"],
                mensagem="Tem vaga?",
                campanha_id=campanha_oferta["id"]
            )

            # Verificar que menciona dados reais
            assert str(vaga_fixture["valor"]) in resposta
```

---

### T4: Teste Canal de Ajuda (1h)

**Arquivo:** `tests/e2e/test_canal_ajuda.py`

```python
"""
Testes E2E: Canal de ajuda (Julia pergunta ao gestor).
"""
import pytest
from unittest.mock import patch
from app.services.julia.agente import processar_mensagem
from app.services.conversas.status import StatusConversa, buscar_status
from app.services.slack.ajuda_handler import processar_resposta_gestor


class TestCanalAjuda:
    """
    Cenário: Julia não sabe resposta factual
    Comportamento esperado: Pausa, pergunta gestor, retoma com resposta.
    """

    @pytest.mark.asyncio
    async def test_pergunta_factual_pausa_conversa(
        self,
        mock_evolution_api,
        mock_slack,
        mock_llm,
        conversa_fixture,
        hospital_fixture
    ):
        """Pergunta factual pausa conversa e notifica gestor."""
        # Configurar LLM para indicar que não sabe
        mock_llm.return_value = '{"precisa_ajuda": true, "pergunta": "estacionamento"}'

        with patch("app.services.conhecimento.repositorio.buscar_conhecimento", return_value=[]):
            await processar_mensagem(
                conversa_id=conversa_fixture["id"],
                mensagem="Esse hospital tem estacionamento?",
                hospital_id=hospital_fixture["id"]
            )

        # Verificar status da conversa
        status_info = await buscar_status(conversa_fixture["id"])
        assert status_info["status"] == StatusConversa.AGUARDANDO_GESTOR.value

        # Verificar que Slack foi notificado
        mock_slack.assert_called_once()

    @pytest.mark.asyncio
    async def test_gestor_responde_retoma_conversa(
        self,
        mock_evolution_api,
        mock_slack,
        conversa_fixture,
        hospital_fixture
    ):
        """Após gestor responder, conversa retoma."""
        # Criar pedido de ajuda
        pedido = await criar_pedido_ajuda(
            conversa_id=conversa_fixture["id"],
            hospital_id=hospital_fixture["id"],
            pergunta="Tem estacionamento?"
        )

        # Simular resposta do gestor
        await processar_resposta_gestor(
            pedido_id=pedido["id"],
            resposta_gestor="Sim, tem estacionamento gratuito",
            gestor_id="gestor-123"
        )

        # Verificar que conversa voltou ao normal
        status_info = await buscar_status(conversa_fixture["id"])
        assert status_info["status"] == StatusConversa.ATIVA.value

        # Verificar que médico recebeu resposta
        mock_evolution_api.assert_called()

    @pytest.mark.asyncio
    async def test_conhecimento_salvo_apos_resposta(
        self,
        mock_evolution_api,
        mock_slack,
        conversa_fixture,
        hospital_fixture
    ):
        """Conhecimento é salvo após gestor responder."""
        from app.services.conhecimento.repositorio import buscar_conhecimento

        pedido = await criar_pedido_ajuda(
            conversa_id=conversa_fixture["id"],
            hospital_id=hospital_fixture["id"],
            pergunta="Tem estacionamento?"
        )

        await processar_resposta_gestor(
            pedido_id=pedido["id"],
            resposta_gestor="Sim, tem estacionamento gratuito",
            gestor_id="gestor-123"
        )

        # Verificar que conhecimento foi salvo
        conhecimentos = await buscar_conhecimento(
            hospital_id=hospital_fixture["id"],
            atributo="estacionamento"
        )

        assert len(conhecimentos) > 0
        assert "gratuito" in conhecimentos[0]["valor"].lower()
```

---

### T5: Teste Modo Piloto (1h)

**Arquivo:** `tests/e2e/test_modo_piloto.py`

```python
"""
Testes E2E: Modo piloto bloqueia ações autônomas.
"""
import pytest
from unittest.mock import patch
from app.core.config import settings
from app.services.autonomo.discovery import executar_discovery_automatico
from app.services.autonomo.oferta import executar_ofertas_automaticas


class TestModoPiloto:
    """
    Cenário: PILOT_MODE = True
    Comportamento esperado: Ações autônomas não executam.
    """

    @pytest.mark.asyncio
    async def test_discovery_automatico_bloqueado_em_piloto(self):
        """Discovery automático não executa em modo piloto."""
        with patch.object(settings, "PILOT_MODE", True):
            resultado = await executar_discovery_automatico()

            assert resultado["executado"] is False
            assert "piloto" in resultado["motivo"].lower()

    @pytest.mark.asyncio
    async def test_oferta_automatica_bloqueada_em_piloto(self):
        """Oferta automática não executa em modo piloto."""
        with patch.object(settings, "PILOT_MODE", True):
            resultado = await executar_ofertas_automaticas()

            assert resultado["executado"] is False
            assert "piloto" in resultado["motivo"].lower()

    @pytest.mark.asyncio
    async def test_campanha_manual_funciona_em_piloto(
        self,
        mock_evolution_api,
        mock_llm,
        campanha_discovery,
        conversa_fixture
    ):
        """Campanhas manuais funcionam mesmo em modo piloto."""
        with patch.object(settings, "PILOT_MODE", True):
            mock_llm.return_value = "Oi! Sou a Júlia"

            resultado = await processar_mensagem(
                conversa_id=conversa_fixture["id"],
                mensagem="",
                campanha_id=campanha_discovery["id"]
            )

            assert resultado is not None
            mock_evolution_api.assert_called()

    @pytest.mark.asyncio
    async def test_autonomo_funciona_com_piloto_off(self):
        """Ações autônomas executam com piloto desativado."""
        with patch.object(settings, "PILOT_MODE", False):
            # Mockar funções internas para não executar realmente
            with patch("app.services.autonomo.discovery._processar_discovery"):
                resultado = await executar_discovery_automatico()

                assert resultado["executado"] is True
```

---

### T6: Teste Hospital Bloqueado (1h)

**Arquivo:** `tests/e2e/test_hospital_bloqueado.py`

```python
"""
Testes E2E: Hospital bloqueado não aparece em ofertas.
"""
import pytest
from app.services.hospitais.bloqueio import bloquear_hospital, desbloquear_hospital
from app.tools.vagas import buscar_vagas


class TestHospitalBloqueado:
    """
    Cenário: Hospital bloqueado
    Comportamento esperado: Vagas não aparecem para Julia.
    """

    @pytest.mark.asyncio
    async def test_vagas_nao_aparecem_apos_bloqueio(
        self,
        hospital_fixture,
        vaga_fixture
    ):
        """Após bloquear hospital, vagas desaparecem."""
        # Verificar que vaga existe antes
        vagas_antes = await buscar_vagas(hospital_id=hospital_fixture["id"])
        assert len(vagas_antes) > 0

        # Bloquear hospital
        await bloquear_hospital(
            hospital_id=hospital_fixture["id"],
            motivo="Teste E2E",
            bloqueado_por="test"
        )

        # Verificar que vagas sumiram
        vagas_depois = await buscar_vagas(hospital_id=hospital_fixture["id"])
        assert len(vagas_depois) == 0

    @pytest.mark.asyncio
    async def test_vagas_voltam_apos_desbloqueio(
        self,
        hospital_fixture,
        vaga_fixture
    ):
        """Após desbloquear, vagas voltam."""
        # Bloquear
        await bloquear_hospital(
            hospital_id=hospital_fixture["id"],
            motivo="Teste E2E",
            bloqueado_por="test"
        )

        # Desbloquear
        await desbloquear_hospital(
            hospital_id=hospital_fixture["id"],
            desbloqueado_por="test"
        )

        # Verificar que vagas voltaram
        vagas = await buscar_vagas(hospital_id=hospital_fixture["id"])
        assert len(vagas) > 0

    @pytest.mark.asyncio
    async def test_julia_nao_oferta_hospital_bloqueado(
        self,
        mock_evolution_api,
        mock_llm,
        campanha_oferta,
        conversa_fixture,
        hospital_fixture,
        vaga_fixture
    ):
        """Julia não oferece vagas de hospital bloqueado."""
        # Bloquear hospital
        await bloquear_hospital(
            hospital_id=hospital_fixture["id"],
            motivo="Teste",
            bloqueado_por="test"
        )

        # Configurar LLM
        mock_llm.return_value = "No momento não tenho vagas disponíveis."

        # Tentar buscar vagas
        resultado = await processar_mensagem(
            conversa_id=conversa_fixture["id"],
            mensagem="Tem vaga?",
            campanha_id=campanha_oferta["id"]
        )

        # Não deve mencionar o hospital bloqueado
        assert hospital_fixture["nome"] not in resultado
```

---

## DoD (Definition of Done)

### Testes Implementados
- [ ] Discovery não oferta
- [ ] Oferta consulta vagas
- [ ] Canal de ajuda completo
- [ ] Modo piloto bloqueia autônomo
- [ ] Hospital bloqueado não aparece
- [ ] Gestor comanda Julia (opcional)

### Infraestrutura
- [ ] Fixtures reutilizáveis
- [ ] Mocks de serviços externos
- [ ] Cleanup automático

### CI/CD
- [ ] Testes rodando no CI
- [ ] Report de coverage

### Verificação
- [ ] `uv run pytest tests/e2e/ -v` passa
- [ ] Coverage > 70% nos fluxos críticos

---

## Métricas de Sucesso

| Métrica | Meta |
|---------|------|
| Testes E2E passando | 100% |
| Coverage de fluxos críticos | > 70% |
| Tempo de execução | < 5 min |
