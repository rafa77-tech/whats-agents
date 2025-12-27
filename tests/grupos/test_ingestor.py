"""
Testes para o módulo de ingestão de grupos.

Sprint 14 - E02 - S02.6
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from uuid import uuid4
from datetime import datetime

from app.services.grupos.ingestor import (
    obter_ou_criar_grupo,
    obter_ou_criar_contato,
    salvar_mensagem_grupo,
    ingerir_mensagem_grupo,
    extrair_telefone_do_jid,
)
from app.schemas.mensagem import MensagemRecebida


class TestExtrairTelefoneDoJid:
    """Testes para extrair_telefone_do_jid."""

    def test_jid_whatsapp_normal(self):
        """Deve extrair telefone de JID normal."""
        assert extrair_telefone_do_jid("5511999999999@s.whatsapp.net") == "5511999999999"

    def test_jid_grupo(self):
        """Deve extrair ID de JID de grupo."""
        assert extrair_telefone_do_jid("120363123456789@g.us") == "120363123456789"

    def test_jid_vazio(self):
        """Deve retornar None para JID vazio."""
        assert extrair_telefone_do_jid("") is None
        assert extrair_telefone_do_jid(None) is None

    def test_jid_sem_arroba(self):
        """Deve retornar None para JID sem @."""
        assert extrair_telefone_do_jid("5511999999999") is None


class TestObterOuCriarGrupo:
    """Testes para obter_ou_criar_grupo."""

    @pytest.mark.asyncio
    async def test_grupo_existente(self, mock_supabase, grupo_id):
        """Deve retornar ID de grupo existente."""
        mock_supabase.execute.return_value.data = [{"id": str(grupo_id)}]

        result = await obter_ou_criar_grupo("123@g.us")

        assert result == grupo_id
        mock_supabase.table.assert_called_with("grupos_whatsapp")

    @pytest.mark.asyncio
    async def test_criar_novo_grupo(self, mock_supabase, grupo_id):
        """Deve criar novo grupo se não existir."""
        # Primeiro select retorna vazio
        mock_supabase.execute.return_value.data = []

        # Configurar insert para retornar novo ID
        mock_insert = MagicMock()
        mock_insert.execute.return_value.data = [{"id": str(grupo_id)}]
        mock_supabase.insert.return_value = mock_insert

        result = await obter_ou_criar_grupo("123@g.us", "Grupo Teste")

        assert result == grupo_id

    @pytest.mark.asyncio
    async def test_criar_grupo_com_nome(self, mock_supabase, grupo_id):
        """Deve criar grupo com nome quando fornecido."""
        mock_supabase.execute.return_value.data = []

        mock_insert = MagicMock()
        mock_insert.execute.return_value.data = [{"id": str(grupo_id)}]
        mock_supabase.insert.return_value = mock_insert

        await obter_ou_criar_grupo("123@g.us", "Vagas Médicas SP")

        # Verificar que insert foi chamado com nome
        call_args = mock_supabase.insert.call_args
        dados = call_args[0][0]
        assert dados["nome"] == "Vagas Médicas SP"
        assert dados["jid"] == "123@g.us"


class TestObterOuCriarContato:
    """Testes para obter_ou_criar_contato."""

    @pytest.mark.asyncio
    async def test_contato_existente_atualiza_nome(self, mock_supabase, contato_id):
        """Deve atualizar nome de contato existente."""
        mock_supabase.execute.return_value.data = [{"id": str(contato_id)}]

        result = await obter_ou_criar_contato(
            "5511999@s.whatsapp.net",
            "Novo Nome"
        )

        assert result == contato_id
        # Verificar que update foi chamado
        mock_supabase.update.assert_called_once()

    @pytest.mark.asyncio
    async def test_criar_novo_contato(self, mock_supabase, contato_id):
        """Deve criar novo contato se não existir."""
        mock_supabase.execute.return_value.data = []

        mock_insert = MagicMock()
        mock_insert.execute.return_value.data = [{"id": str(contato_id)}]
        mock_supabase.insert.return_value = mock_insert

        result = await obter_ou_criar_contato(
            "5511999@s.whatsapp.net",
            "Dr. João",
            "5511999999999"
        )

        assert result == contato_id

    @pytest.mark.asyncio
    async def test_contato_existente_sem_nome(self, mock_supabase, contato_id):
        """Não deve atualizar se nome não for fornecido."""
        mock_supabase.execute.return_value.data = [{"id": str(contato_id)}]

        result = await obter_ou_criar_contato("5511999@s.whatsapp.net")

        assert result == contato_id
        # Update não deve ter sido chamado
        mock_supabase.update.assert_not_called()


class TestSalvarMensagemGrupo:
    """Testes para salvar_mensagem_grupo."""

    @pytest.mark.asyncio
    async def test_salvar_mensagem_texto(
        self, mock_supabase, grupo_id, contato_id, mensagem_id, mensagem_texto_grupo
    ):
        """Deve salvar mensagem de texto com status pendente."""
        mock_insert = MagicMock()
        mock_insert.execute.return_value.data = [{"id": str(mensagem_id)}]
        mock_supabase.insert.return_value = mock_insert

        dados_raw = {"key": {"participant": "5511999@s.whatsapp.net"}}

        result = await salvar_mensagem_grupo(
            grupo_id=grupo_id,
            contato_id=contato_id,
            mensagem=mensagem_texto_grupo,
            dados_raw=dados_raw
        )

        assert result == mensagem_id

        # Verificar dados inseridos
        call_args = mock_supabase.insert.call_args
        dados = call_args[0][0]
        assert dados["status"] == "pendente"
        assert dados["tipo_midia"] == "texto"
        assert dados["tem_midia"] is False

    @pytest.mark.asyncio
    async def test_salvar_mensagem_imagem_ignorada(
        self, mock_supabase, grupo_id, contato_id, mensagem_id, mensagem_imagem_grupo
    ):
        """Deve salvar imagem com status ignorada_midia."""
        mock_insert = MagicMock()
        mock_insert.execute.return_value.data = [{"id": str(mensagem_id)}]
        mock_supabase.insert.return_value = mock_insert

        result = await salvar_mensagem_grupo(
            grupo_id=grupo_id,
            contato_id=contato_id,
            mensagem=mensagem_imagem_grupo,
            dados_raw={"key": {}}
        )

        call_args = mock_supabase.insert.call_args
        dados = call_args[0][0]
        assert dados["status"] == "ignorada_midia"
        assert dados["tipo_midia"] == "imagem"
        assert dados["tem_midia"] is True

    @pytest.mark.asyncio
    async def test_salvar_mensagem_curta_ignorada(
        self, mock_supabase, grupo_id, contato_id, mensagem_id, mensagem_curta_grupo
    ):
        """Deve ignorar mensagens muito curtas."""
        mock_insert = MagicMock()
        mock_insert.execute.return_value.data = [{"id": str(mensagem_id)}]
        mock_supabase.insert.return_value = mock_insert

        result = await salvar_mensagem_grupo(
            grupo_id=grupo_id,
            contato_id=contato_id,
            mensagem=mensagem_curta_grupo,
            dados_raw={"key": {}}
        )

        call_args = mock_supabase.insert.call_args
        dados = call_args[0][0]
        assert dados["status"] == "ignorada_curta"


class TestIngerirMensagemGrupo:
    """Testes de integração para ingerir_mensagem_grupo."""

    @pytest.mark.asyncio
    async def test_fluxo_completo(self, mock_supabase, mensagem_texto_grupo, dados_webhook_grupo):
        """Deve executar fluxo completo de ingestão."""
        grupo_id = uuid4()
        contato_id = uuid4()
        mensagem_id = uuid4()

        # Mock para grupo não existir e ser criado
        select_mock = MagicMock()
        select_mock.execute.return_value.data = []
        mock_supabase.select.return_value.eq.return_value = select_mock

        # Mock para inserts
        insert_mock = MagicMock()
        insert_mock.execute.return_value.data = [{"id": str(grupo_id)}]
        mock_supabase.insert.return_value = insert_mock

        result = await ingerir_mensagem_grupo(mensagem_texto_grupo, dados_webhook_grupo)

        assert result is not None

    @pytest.mark.asyncio
    async def test_jid_grupo_ausente(self, mock_supabase, mensagem_texto_grupo):
        """Deve retornar None se JID do grupo estiver ausente."""
        dados_raw = {"key": {}}  # Sem remoteJid

        result = await ingerir_mensagem_grupo(mensagem_texto_grupo, dados_raw)

        assert result is None

    @pytest.mark.asyncio
    async def test_erro_no_banco(self, mock_supabase, mensagem_texto_grupo, dados_webhook_grupo):
        """Deve retornar None em caso de erro no banco."""
        mock_supabase.execute.side_effect = Exception("Erro de conexão")

        result = await ingerir_mensagem_grupo(mensagem_texto_grupo, dados_webhook_grupo)

        assert result is None


class TestIngestaoGrupoProcessor:
    """Testes para o pre-processor de ingestão."""

    @pytest.mark.asyncio
    async def test_nao_processa_mensagem_dm(self):
        """Não deve processar mensagens de DM."""
        from app.pipeline.pre_processors import IngestaoGrupoProcessor
        from app.pipeline.base import ProcessorContext

        processor = IngestaoGrupoProcessor()
        context = ProcessorContext(
            mensagem_raw={
                "key": {
                    "remoteJid": "5511999999999@s.whatsapp.net",  # DM, não grupo
                    "id": "123"
                }
            }
        )

        result = await processor.process(context)

        assert result.success is True
        assert result.should_continue is True  # Deve continuar para outros processors

    @pytest.mark.asyncio
    async def test_processa_mensagem_grupo(self):
        """Deve processar mensagens de grupo e parar pipeline."""
        from app.pipeline.pre_processors import IngestaoGrupoProcessor
        from app.pipeline.base import ProcessorContext

        processor = IngestaoGrupoProcessor()
        context = ProcessorContext(
            mensagem_raw={
                "key": {
                    "remoteJid": "120363123456789@g.us",  # Grupo
                    "participant": "5511999999999@s.whatsapp.net",
                    "id": "123"
                },
                "pushName": "Teste",
                "messageTimestamp": 1703779200,
                "message": {"conversation": "Vaga disponível"}
            }
        )

        with patch("app.services.grupos.ingestor.supabase") as mock_sb:
            # Configurar mocks
            mock_sb.table.return_value = mock_sb
            mock_sb.select.return_value = mock_sb
            mock_sb.insert.return_value = mock_sb
            mock_sb.update.return_value = mock_sb
            mock_sb.eq.return_value = mock_sb
            mock_sb.rpc.return_value = mock_sb

            mock_sb.execute.return_value.data = [{"id": str(uuid4())}]

            result = await processor.process(context)

        assert result.success is True
        assert result.should_continue is False  # Não deve continuar
        assert result.metadata.get("motivo") == "mensagem_grupo_ingerida"
