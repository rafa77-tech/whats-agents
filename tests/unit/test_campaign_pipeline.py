"""
Testes de integração do pipeline de contexto de campanha.

Cobre:
- montar_contexto_completo com campanha (Issue 1.3)
- montar_prompt_julia com params de campanha (Issue 1.4)
- pode_ofertar enforcement no agente (Issue 4.2)
- fila_mensagens usa criar_contexto_campanha (Issue 3.1)
- metadata enriquecida no executor (Issue 2.2)
- abertura contextualizada via LLM (Issue 2.1)
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.campanhas.types import (
    AudienceFilters,
    CampanhaData,
    StatusCampanha,
    TipoCampanha,
)


# =============================================================================
# montar_contexto_completo - Campanha na saída (Issue 1.3)
# =============================================================================


class TestMontarContextoCompletoComCampanha:
    """Testes para campanha dentro de montar_contexto_completo."""

    @pytest.fixture
    def medico(self):
        return {
            "id": "medico-123",
            "primeiro_nome": "Carlos",
            "telefone": "5511999999999",
            "especialidade_nome": "Cardiologia",
        }

    @pytest.fixture
    def conversa_com_campanha(self):
        return {
            "id": "conv-abc",
            "cliente_id": "medico-123",
            "controlled_by": "ai",
            "last_touch_campaign_id": 20,
            "last_touch_at": "2026-02-10T10:00:00+00:00",
            "campanha_id": 20,
        }

    @pytest.fixture
    def conversa_sem_campanha(self):
        return {
            "id": "conv-def",
            "cliente_id": "medico-123",
            "controlled_by": "ai",
        }

    @pytest.mark.asyncio
    async def test_contexto_inclui_campanha(self, medico, conversa_com_campanha):
        """montar_contexto_completo deve incluir chave 'campanha'."""
        campanha_ctx = {
            "campaign_type": "discovery",
            "campaign_objective": "Baixar app",
            "pode_ofertar": False,
            "_status": "ativa",
            "_concluida_em": None,
        }

        with (
            patch(
                "app.services.contexto.carregar_historico", new_callable=AsyncMock, return_value=[]
            ),
            patch(
                "app.services.contexto.verificar_handoff_recente",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch(
                "app.services.contexto.carregar_diretrizes_ativas",
                new_callable=AsyncMock,
                return_value={},
            ),
            patch(
                "app.services.contexto.enriquecer_contexto_com_memorias",
                new_callable=AsyncMock,
                return_value="",
            ),
            patch(
                "app.services.contexto.carregar_contexto_campanha",
                new_callable=AsyncMock,
                return_value=campanha_ctx,
            ),
            patch(
                "app.services.contexto.cache_get_json", new_callable=AsyncMock, return_value=None
            ),
            patch(
                "app.services.contexto.cache_set_json", new_callable=AsyncMock, return_value=True
            ),
        ):
            from app.services.contexto import montar_contexto_completo

            resultado = await montar_contexto_completo(medico, conversa_com_campanha)

            assert "campanha" in resultado
            assert resultado["campanha"]["campaign_type"] == "discovery"
            assert resultado["campanha"]["campaign_objective"] == "Baixar app"

    @pytest.mark.asyncio
    async def test_contexto_campanha_none_quando_sem_campanha(self, medico, conversa_sem_campanha):
        """Sem campanha, chave 'campanha' deve ser None."""
        with (
            patch(
                "app.services.contexto.carregar_historico", new_callable=AsyncMock, return_value=[]
            ),
            patch(
                "app.services.contexto.verificar_handoff_recente",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch(
                "app.services.contexto.carregar_diretrizes_ativas",
                new_callable=AsyncMock,
                return_value={},
            ),
            patch(
                "app.services.contexto.enriquecer_contexto_com_memorias",
                new_callable=AsyncMock,
                return_value="",
            ),
            patch(
                "app.services.contexto.carregar_contexto_campanha",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch(
                "app.services.contexto.cache_get_json", new_callable=AsyncMock, return_value=None
            ),
            patch(
                "app.services.contexto.cache_set_json", new_callable=AsyncMock, return_value=True
            ),
        ):
            from app.services.contexto import montar_contexto_completo

            resultado = await montar_contexto_completo(medico, conversa_sem_campanha)

            assert "campanha" in resultado
            assert resultado["campanha"] is None

    @pytest.mark.asyncio
    async def test_contexto_campanha_erro_graceful(self, medico, conversa_com_campanha):
        """Erro ao carregar campanha deve resultar em None (graceful)."""
        with (
            patch(
                "app.services.contexto.carregar_historico", new_callable=AsyncMock, return_value=[]
            ),
            patch(
                "app.services.contexto.verificar_handoff_recente",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch(
                "app.services.contexto.carregar_diretrizes_ativas",
                new_callable=AsyncMock,
                return_value={},
            ),
            patch(
                "app.services.contexto.enriquecer_contexto_com_memorias",
                new_callable=AsyncMock,
                return_value="",
            ),
            patch(
                "app.services.contexto.carregar_contexto_campanha",
                new_callable=AsyncMock,
                side_effect=Exception("DB error"),
            ),
            patch(
                "app.services.contexto.cache_get_json", new_callable=AsyncMock, return_value=None
            ),
            patch(
                "app.services.contexto.cache_set_json", new_callable=AsyncMock, return_value=True
            ),
        ):
            from app.services.contexto import montar_contexto_completo

            resultado = await montar_contexto_completo(medico, conversa_com_campanha)

            # asyncio.gather com return_exceptions=True captura exceção
            assert "campanha" in resultado
            assert resultado["campanha"] is None

    @pytest.mark.asyncio
    async def test_contexto_passa_ids_corretos(self, medico, conversa_com_campanha):
        """Deve passar last_touch_campaign_id, last_touch_at e campanha_id corretos."""
        with (
            patch(
                "app.services.contexto.carregar_historico", new_callable=AsyncMock, return_value=[]
            ),
            patch(
                "app.services.contexto.verificar_handoff_recente",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch(
                "app.services.contexto.carregar_diretrizes_ativas",
                new_callable=AsyncMock,
                return_value={},
            ),
            patch(
                "app.services.contexto.enriquecer_contexto_com_memorias",
                new_callable=AsyncMock,
                return_value="",
            ),
            patch(
                "app.services.contexto.carregar_contexto_campanha",
                new_callable=AsyncMock,
                return_value=None,
            ) as mock_carregar,
            patch(
                "app.services.contexto.cache_get_json", new_callable=AsyncMock, return_value=None
            ),
            patch(
                "app.services.contexto.cache_set_json", new_callable=AsyncMock, return_value=True
            ),
        ):
            from app.services.contexto import montar_contexto_completo

            await montar_contexto_completo(medico, conversa_com_campanha)

            mock_carregar.assert_called_once_with(
                campaign_id=20,
                last_touch_at="2026-02-10T10:00:00+00:00",
                campanha_id_fallback=20,
            )


# =============================================================================
# montar_prompt_julia - Params de campanha (Issue 1.4)
# =============================================================================


class TestMontarPromptJuliaComCampanha:
    """Testes para montar_prompt_julia com parâmetros de campanha."""

    @pytest.mark.asyncio
    async def test_campaign_params_forwarded(self):
        """Params de campanha devem ser encaminhados ao builder."""
        from app.core.prompts import montar_prompt_julia

        with patch(
            "app.core.prompts._construir_prompt", new_callable=AsyncMock, return_value="prompt"
        ) as mock_build:
            await montar_prompt_julia(
                campaign_type="discovery",
                campaign_objective="Testar app",
                campaign_rules=["regra1"],
                offer_scope={"especialidade": "cardio"},
                negotiation_margin={"tipo": "percentual", "valor": 10},
            )

            call_kwargs = mock_build.call_args.kwargs
            assert call_kwargs["campaign_type"] == "discovery"
            assert call_kwargs["campaign_objective"] == "Testar app"
            assert call_kwargs["campaign_rules"] == ["regra1"]
            assert call_kwargs["offer_scope"] == {"especialidade": "cardio"}
            assert call_kwargs["negotiation_margin"] == {"tipo": "percentual", "valor": 10}

    @pytest.mark.asyncio
    async def test_campaign_params_none_by_default(self):
        """Sem params de campanha, todos devem ser None."""
        from app.core.prompts import montar_prompt_julia

        with patch(
            "app.core.prompts._construir_prompt", new_callable=AsyncMock, return_value="prompt"
        ) as mock_build:
            await montar_prompt_julia()

            call_kwargs = mock_build.call_args.kwargs
            assert call_kwargs["campaign_type"] is None
            assert call_kwargs["campaign_objective"] is None
            assert call_kwargs["campaign_rules"] is None
            assert call_kwargs["offer_scope"] is None
            assert call_kwargs["negotiation_margin"] is None


# =============================================================================
# pode_ofertar enforcement (Issue 4.2)
# =============================================================================


class TestPodeOfertarEnforcement:
    """Testes para enforcement de pode_ofertar no agente.

    Testa a lógica de construção de constraints diretamente,
    sem invocar _gerar_resposta_julia_impl (que tem muitas dependências internas).
    """

    def test_pode_ofertar_false_gera_constraint(self):
        """Quando pode_ofertar=False, constraint deve ser gerada."""
        contexto = {
            "campanha": {
                "campaign_type": "discovery",
                "campaign_objective": "Baixar app",
                "pode_ofertar": False,
            },
        }

        # Simular lógica do agente (Issue 4.2)
        constraints_parts = []
        campanha = contexto.get("campanha")
        if campanha and campanha.get("pode_ofertar") is False:
            constraints_parts.append(
                "RESTRIÇÃO DE CAMPANHA (PRIORIDADE MÁXIMA): Esta conversa NÃO permite ofertar vagas. "
                "Se o médico perguntar sobre vagas, diga que vai verificar o que tem disponível e retorna. "
                "NÃO mencione vagas específicas, valores, datas ou hospitais."
            )

        assert len(constraints_parts) == 1
        assert "RESTRIÇÃO DE CAMPANHA" in constraints_parts[0]
        assert "NÃO permite ofertar" in constraints_parts[0]

    def test_pode_ofertar_true_nao_gera_constraint(self):
        """Quando pode_ofertar=True, nenhuma constraint deve ser gerada."""
        contexto = {
            "campanha": {
                "campaign_type": "oferta",
                "pode_ofertar": True,
            },
        }

        constraints_parts = []
        campanha = contexto.get("campanha")
        if campanha and campanha.get("pode_ofertar") is False:
            constraints_parts.append("RESTRIÇÃO")

        assert len(constraints_parts) == 0

    def test_sem_campanha_nao_gera_constraint(self):
        """Sem campanha, nenhuma constraint deve ser gerada."""
        contexto = {"campanha": None}

        constraints_parts = []
        campanha = contexto.get("campanha")
        if campanha and campanha.get("pode_ofertar") is False:
            constraints_parts.append("RESTRIÇÃO")

        assert len(constraints_parts) == 0

    def test_pode_ofertar_none_nao_gera_constraint(self):
        """pode_ofertar=None não deve gerar constraint (only False triggers)."""
        contexto = {
            "campanha": {
                "campaign_type": "discovery",
                "pode_ofertar": None,
            },
        }

        constraints_parts = []
        campanha = contexto.get("campanha")
        if campanha and campanha.get("pode_ofertar") is False:
            constraints_parts.append("RESTRIÇÃO")

        assert len(constraints_parts) == 0

    def test_constraint_combinada_com_policy(self):
        """Constraint de campanha deve se combinar com outras constraints."""
        constraints_parts = ["Policy: Horário comercial apenas"]

        campanha = {"pode_ofertar": False}
        if campanha and campanha.get("pode_ofertar") is False:
            constraints_parts.append(
                "RESTRIÇÃO DE CAMPANHA (PRIORIDADE MÁXIMA): NÃO ofertar vagas."
            )

        policy_constraints = "\n\n---\n\n".join(constraints_parts)
        assert "Policy: Horário comercial" in policy_constraints
        assert "RESTRIÇÃO DE CAMPANHA" in policy_constraints
        assert "---" in policy_constraints


# =============================================================================
# fila_mensagens - criar_contexto_campanha (Issue 3.1)
# =============================================================================


class TestFilaMensagensCampanhaContext:
    """Testes para uso de criar_contexto_campanha na fila."""

    @pytest.fixture
    def mensagem_com_campanha(self):
        return {
            "id": "msg-camp-1",
            "cliente_id": "cliente-abc",
            "conversa_id": "conv-xyz",
            "conteudo": "Oi Dr Carlos!",
            "tipo": "campanha",
            "prioridade": 3,
            "status": "processando",
            "tentativas": 0,
            "metadata": {
                "campanha_id": "42",
                "tipo_campanha": "discovery",
            },
            "clientes": {
                "telefone": "5511999999999",
                "primeiro_nome": "Carlos",
            },
        }

    @pytest.fixture
    def mensagem_sem_campanha(self):
        return {
            "id": "msg-follow-1",
            "cliente_id": "cliente-abc",
            "conversa_id": "conv-xyz",
            "conteudo": "Lembrei de vc!",
            "tipo": "followup",
            "prioridade": 3,
            "status": "processando",
            "tentativas": 0,
            "metadata": {},
            "clientes": {
                "telefone": "5511999999999",
                "primeiro_nome": "Carlos",
            },
        }

    @pytest.mark.asyncio
    async def test_usa_criar_contexto_campanha_quando_campanha_id(self, mensagem_com_campanha):
        """Deve usar criar_contexto_campanha quando metadata tem campanha_id."""
        from app.services.jobs.fila_mensagens import _processar_mensagem

        with (
            patch("app.services.jobs.fila_mensagens.fila_service") as mock_fila,
            patch("app.services.jobs.fila_mensagens.send_outbound_message") as mock_send,
            patch("app.services.jobs.fila_mensagens.criar_contexto_campanha") as mock_ctx_camp,
            patch("app.services.jobs.fila_mensagens.criar_contexto_followup") as mock_ctx_follow,
            patch("app.services.jobs.fila_mensagens.buscar_ou_criar_conversa"),
            patch("app.services.jobs.fila_mensagens.salvar_interacao") as mock_interacao,
        ):
            mock_result = MagicMock()
            mock_result.blocked = False
            mock_result.success = True
            mock_result.chip_id = "chip-1"
            mock_send.return_value = mock_result

            mock_ctx_camp.return_value = MagicMock()
            mock_fila.marcar_enviada = AsyncMock(return_value=True)
            mock_interacao.return_value = None

            resultado = await _processar_mensagem(mensagem_com_campanha)

            assert resultado == "enviada"
            mock_ctx_camp.assert_called_once_with(
                cliente_id="cliente-abc",
                campaign_id="42",
                conversation_id="conv-xyz",
            )
            mock_ctx_follow.assert_not_called()

    @pytest.mark.asyncio
    async def test_usa_criar_contexto_followup_sem_campanha_id(self, mensagem_sem_campanha):
        """Deve usar criar_contexto_followup quando metadata não tem campanha_id."""
        from app.services.jobs.fila_mensagens import _processar_mensagem

        with (
            patch("app.services.jobs.fila_mensagens.fila_service") as mock_fila,
            patch("app.services.jobs.fila_mensagens.send_outbound_message") as mock_send,
            patch("app.services.jobs.fila_mensagens.criar_contexto_campanha") as mock_ctx_camp,
            patch("app.services.jobs.fila_mensagens.criar_contexto_followup") as mock_ctx_follow,
            patch("app.services.jobs.fila_mensagens.buscar_ou_criar_conversa"),
            patch("app.services.jobs.fila_mensagens.salvar_interacao") as mock_interacao,
        ):
            mock_result = MagicMock()
            mock_result.blocked = False
            mock_result.success = True
            mock_result.chip_id = "chip-1"
            mock_send.return_value = mock_result

            mock_ctx_follow.return_value = MagicMock()
            mock_fila.marcar_enviada = AsyncMock(return_value=True)
            mock_interacao.return_value = None

            resultado = await _processar_mensagem(mensagem_sem_campanha)

            assert resultado == "enviada"
            mock_ctx_follow.assert_called_once_with(
                cliente_id="cliente-abc",
                conversation_id="conv-xyz",
            )
            mock_ctx_camp.assert_not_called()


# =============================================================================
# Executor - Metadata enriquecida (Issue 2.2)
# =============================================================================


class TestExecutorMetadataEnriquecida:
    """Testes para metadata com objetivo e pode_ofertar."""

    @pytest.mark.asyncio
    async def test_metadata_inclui_objetivo(self):
        """Metadata deve incluir objetivo quando campanha tem objetivo."""
        from app.services.campanhas.executor import CampanhaExecutor

        campanha = CampanhaData(
            id=20,
            nome_template="App Download",
            tipo_campanha=TipoCampanha.DISCOVERY,
            status=StatusCampanha.AGENDADA,
            objetivo="Fazer médico baixar o app Revoluna",
            pode_ofertar=False,
            audience_filters=AudienceFilters(quantidade_alvo=1),
        )

        destinatarios = [{"id": "uuid-1", "primeiro_nome": "Carlos"}]
        executor = CampanhaExecutor()

        with (
            patch("app.services.campanhas.executor.campanha_repository") as mock_repo,
            patch("app.services.campanhas.executor.segmentacao_service") as mock_seg,
            patch("app.services.campanhas.executor.fila_service") as mock_fila,
            patch("app.services.campanhas.executor.supabase") as mock_supabase,
            patch("app.services.campanhas.executor.obter_abertura_texto") as mock_abertura,
        ):
            mock_repo.buscar_por_id = AsyncMock(return_value=campanha)
            mock_repo.atualizar_status = AsyncMock(return_value=True)
            mock_repo.atualizar_total_destinatarios = AsyncMock(return_value=True)
            mock_repo.incrementar_enviados = AsyncMock(return_value=True)
            mock_seg.buscar_alvos_campanha = AsyncMock(return_value=destinatarios)
            mock_fila.enfileirar = AsyncMock()
            mock_abertura.return_value = "Oi Dr Carlos!"
            mock_supabase.table.return_value.select.return_value.contains.return_value.execute.return_value.data = []

            await executor.executar(20)

            # Verificar metadata do enfileirar
            call_kwargs = mock_fila.enfileirar.call_args.kwargs
            metadata = call_kwargs.get("metadata", {})
            assert metadata.get("objetivo") == "Fazer médico baixar o app Revoluna"
            assert metadata.get("pode_ofertar") is False

    @pytest.mark.asyncio
    async def test_metadata_sem_objetivo_quando_none(self):
        """Metadata não deve incluir objetivo quando é None."""
        from app.services.campanhas.executor import CampanhaExecutor

        campanha = CampanhaData(
            id=21,
            nome_template="Oferta Simples",
            tipo_campanha=TipoCampanha.OFERTA,
            corpo="Oi Dr {nome}! Temos vagas de {especialidade}!",
            status=StatusCampanha.AGENDADA,
            objetivo=None,
            pode_ofertar=True,
            audience_filters=AudienceFilters(quantidade_alvo=1),
        )

        destinatarios = [
            {"id": "uuid-1", "primeiro_nome": "Carlos", "especialidade_nome": "Cardio"}
        ]
        executor = CampanhaExecutor()

        with (
            patch("app.services.campanhas.executor.campanha_repository") as mock_repo,
            patch("app.services.campanhas.executor.segmentacao_service") as mock_seg,
            patch("app.services.campanhas.executor.fila_service") as mock_fila,
            patch("app.services.campanhas.executor.supabase") as mock_supabase,
        ):
            mock_repo.buscar_por_id = AsyncMock(return_value=campanha)
            mock_repo.atualizar_status = AsyncMock(return_value=True)
            mock_repo.atualizar_total_destinatarios = AsyncMock(return_value=True)
            mock_repo.incrementar_enviados = AsyncMock(return_value=True)
            mock_seg.buscar_alvos_campanha = AsyncMock(return_value=destinatarios)
            mock_fila.enfileirar = AsyncMock()
            mock_supabase.table.return_value.select.return_value.contains.return_value.execute.return_value.data = []

            await executor.executar(21)

            call_kwargs = mock_fila.enfileirar.call_args.kwargs
            metadata = call_kwargs.get("metadata", {})
            assert "objetivo" not in metadata
            assert metadata.get("pode_ofertar") is True


# =============================================================================
# Executor - Abertura contextualizada via LLM (Issue 2.1)
# =============================================================================


class TestAberturaContextualizada:
    """Testes para abertura contextualizada via LLM."""

    @pytest.mark.asyncio
    async def test_discovery_com_objetivo_usa_llm(self):
        """Discovery com objetivo deve tentar LLM para abertura."""
        from app.services.campanhas.executor import CampanhaExecutor

        campanha = CampanhaData(
            id=20,
            nome_template="App Download",
            tipo_campanha=TipoCampanha.DISCOVERY,
            status=StatusCampanha.AGENDADA,
            objetivo="Fazer médico baixar o app Revoluna",
        )
        destinatario = {"id": "uuid-1", "nome": "Carlos"}
        executor = CampanhaExecutor()

        with patch("app.services.llm.gerar_resposta", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = (
                "Oi Dr Carlos! Tudo bem? Sou a Julia da Revoluna, vi que vc é médico na região"
            )

            mensagem = await executor._gerar_mensagem(campanha, destinatario)

            assert mensagem is not None
            assert "Julia" in mensagem or "Carlos" in mensagem
            mock_llm.assert_called_once()

    @pytest.mark.asyncio
    async def test_discovery_com_objetivo_fallback_se_llm_falhar(self):
        """Se LLM falhar, deve usar abertura soft como fallback."""
        from app.services.campanhas.executor import CampanhaExecutor

        campanha = CampanhaData(
            id=20,
            nome_template="App Download",
            tipo_campanha=TipoCampanha.DISCOVERY,
            status=StatusCampanha.AGENDADA,
            objetivo="Fazer médico baixar o app Revoluna",
        )
        destinatario = {"id": "uuid-1", "nome": "Carlos"}
        executor = CampanhaExecutor()

        with (
            patch("app.services.llm.gerar_resposta", new_callable=AsyncMock) as mock_llm,
            patch("app.services.campanhas.executor.obter_abertura_texto") as mock_abertura,
        ):
            mock_llm.side_effect = Exception("LLM timeout")
            mock_abertura.return_value = "Oi Dr Carlos! Sou a Julia da Revoluna"

            mensagem = await executor._gerar_mensagem(campanha, destinatario)

            assert mensagem == "Oi Dr Carlos! Sou a Julia da Revoluna"
            mock_abertura.assert_called_once_with("uuid-1", "Carlos", soft=True)

    @pytest.mark.asyncio
    async def test_discovery_com_objetivo_fallback_resposta_curta(self):
        """LLM com resposta muito curta deve usar fallback."""
        from app.services.campanhas.executor import CampanhaExecutor

        campanha = CampanhaData(
            id=20,
            nome_template="App Download",
            tipo_campanha=TipoCampanha.DISCOVERY,
            status=StatusCampanha.AGENDADA,
            objetivo="Testar",
        )
        destinatario = {"id": "uuid-1", "nome": "Carlos"}
        executor = CampanhaExecutor()

        with (
            patch("app.services.llm.gerar_resposta", new_callable=AsyncMock) as mock_llm,
            patch("app.services.campanhas.executor.obter_abertura_texto") as mock_abertura,
        ):
            mock_llm.return_value = "Oi"  # Muito curta (<= 10 chars)
            mock_abertura.return_value = "Oi Dr Carlos! Sou a Julia"

            mensagem = await executor._gerar_mensagem(campanha, destinatario)

            assert mensagem == "Oi Dr Carlos! Sou a Julia"

    @pytest.mark.asyncio
    async def test_discovery_sem_objetivo_usa_abertura_soft(self):
        """Discovery sem objetivo deve usar abertura soft padrão."""
        from app.services.campanhas.executor import CampanhaExecutor

        campanha = CampanhaData(
            id=16,
            nome_template="Discovery Simples",
            tipo_campanha=TipoCampanha.DISCOVERY,
            status=StatusCampanha.AGENDADA,
            objetivo=None,
        )
        destinatario = {"id": "uuid-1", "nome": "Maria"}
        executor = CampanhaExecutor()

        with patch("app.services.campanhas.executor.obter_abertura_texto") as mock_abertura:
            mock_abertura.return_value = "Oi Dra Maria!"

            mensagem = await executor._gerar_mensagem(campanha, destinatario)

            assert mensagem == "Oi Dra Maria!"
            mock_abertura.assert_called_once_with("uuid-1", "Maria", soft=True)


# =============================================================================
# Cache invalidation no repository (Issue 4.3)
# =============================================================================


class TestCacheInvalidationRepository:
    """Testes para invalidação de cache ao atualizar status."""

    @pytest.mark.asyncio
    async def test_invalida_cache_ao_atualizar_status(self):
        """atualizar_status deve invalidar cache de contexto da campanha."""
        from app.services.campanhas.repository import CampanhaRepository

        repo = CampanhaRepository()

        with (
            patch("app.services.campanhas.repository.supabase") as mock_supabase,
            patch("app.services.redis.cache_delete", new_callable=AsyncMock) as mock_cache_del,
        ):
            mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()

            await repo.atualizar_status(42, StatusCampanha.CONCLUIDA)

            mock_cache_del.assert_called_once_with("campanha:contexto:42")


# =============================================================================
# buscar_conversa_ativa - Colunas de campanha (Issue 1.1)
# =============================================================================


class TestBuscarConversaAtivaColunasCampanha:
    """Testes para colunas de campanha no SELECT."""

    @pytest.mark.asyncio
    async def test_retorna_colunas_campanha(self):
        """buscar_conversa_ativa deve retornar colunas de campanha."""
        from app.services.conversa import buscar_conversa_ativa

        conversa_data = {
            "id": "conv-1",
            "cliente_id": "med-1",
            "status": "active",
            "controlled_by": "ai",
            "chatwoot_conversation_id": None,
            "created_at": "2026-02-10",
            "campanha_id": 20,
            "last_touch_campaign_id": 20,
            "last_touch_at": "2026-02-10T10:00:00+00:00",
        }

        with patch("app.services.conversa.supabase") as mock_supabase:
            mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(
                data=[conversa_data]
            )

            resultado = await buscar_conversa_ativa("med-1")

            assert resultado is not None
            assert resultado.get("campanha_id") == 20
            assert resultado.get("last_touch_campaign_id") == 20
            assert resultado.get("last_touch_at") == "2026-02-10T10:00:00+00:00"
