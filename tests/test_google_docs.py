"""
Testes do servico de integracao com Google Docs.

Sprint 11 - Epic 03: Escrita no Documento
"""
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.google_docs import (
    DocInfo,
    DocContent,
    _extrair_texto,
    _detectar_secao_plano,
    verificar_configuracao,
)


class TestDocInfo:
    """Testes do dataclass DocInfo."""

    def test_cria_doc_info(self):
        """Cria DocInfo corretamente."""
        info = DocInfo(
            id="doc123",
            nome="briefing-teste",
            ultima_modificacao=datetime(2025, 12, 15, 14, 30),
            url="https://docs.google.com/document/d/doc123"
        )
        assert info.id == "doc123"
        assert info.nome == "briefing-teste"
        assert "doc123" in info.url


class TestDocContent:
    """Testes do dataclass DocContent."""

    def test_cria_doc_content(self):
        """Cria DocContent corretamente."""
        info = DocInfo(
            id="doc1",
            nome="teste",
            ultima_modificacao=datetime.now(),
            url="https://..."
        )
        content = DocContent(
            info=info,
            conteudo="Conteudo do documento",
            hash="abc123",
            ja_processado=False
        )
        assert content.conteudo == "Conteudo do documento"
        assert content.ja_processado is False
        assert content.secao_plano_existente is None

    def test_doc_content_ja_processado(self):
        """DocContent com secao de plano existente."""
        info = DocInfo(id="doc1", nome="teste", ultima_modificacao=datetime.now(), url="...")
        content = DocContent(
            info=info,
            conteudo="Briefing...\n## Plano da Julia\nPassos...",
            hash="abc123",
            ja_processado=True,
            secao_plano_existente="## Plano da Julia\nPassos..."
        )
        assert content.ja_processado is True
        assert "Plano da Julia" in content.secao_plano_existente


class TestExtrairTexto:
    """Testes da funcao _extrair_texto."""

    def test_extrai_texto_simples(self):
        """Extrai texto de documento simples."""
        document = {
            "body": {
                "content": [
                    {
                        "paragraph": {
                            "elements": [
                                {"textRun": {"content": "Hello "}}
                            ]
                        }
                    },
                    {
                        "paragraph": {
                            "elements": [
                                {"textRun": {"content": "World!"}}
                            ]
                        }
                    }
                ]
            }
        }
        resultado = _extrair_texto(document)
        assert resultado == "Hello World!"

    def test_extrai_texto_multiplos_elementos(self):
        """Extrai texto com multiplos elementos por paragrafo."""
        document = {
            "body": {
                "content": [
                    {
                        "paragraph": {
                            "elements": [
                                {"textRun": {"content": "Parte 1 "}},
                                {"textRun": {"content": "Parte 2"}},
                            ]
                        }
                    }
                ]
            }
        }
        resultado = _extrair_texto(document)
        assert resultado == "Parte 1 Parte 2"

    def test_extrai_texto_documento_vazio(self):
        """Documento vazio retorna string vazia."""
        document = {"body": {"content": []}}
        resultado = _extrair_texto(document)
        assert resultado == ""

    def test_extrai_texto_sem_body(self):
        """Documento sem body retorna string vazia."""
        document = {}
        resultado = _extrair_texto(document)
        assert resultado == ""

    def test_ignora_elementos_sem_text_run(self):
        """Ignora elementos que nao sao textRun."""
        document = {
            "body": {
                "content": [
                    {
                        "paragraph": {
                            "elements": [
                                {"textRun": {"content": "Texto "}},
                                {"inlineObjectElement": {"inlineObjectId": "obj1"}},  # imagem
                                {"textRun": {"content": "visivel"}},
                            ]
                        }
                    }
                ]
            }
        }
        resultado = _extrair_texto(document)
        assert resultado == "Texto visivel"


class TestDetectarSecaoPlano:
    """Testes da funcao _detectar_secao_plano."""

    def test_detecta_secao_plano(self):
        """Detecta secao de plano existente."""
        conteudo = """# Briefing

Quero preencher 5 vagas...

## Plano da Julia

1. Buscar medicos
2. Enviar mensagens

## Historico

| Data | Acao |
"""
        resultado = _detectar_secao_plano(conteudo)
        assert resultado is not None
        assert "## Plano da Julia" in resultado
        assert "Buscar medicos" in resultado

    def test_nao_detecta_se_nao_existe(self):
        """Retorna None se nao existe secao."""
        conteudo = """# Briefing

Quero preencher 5 vagas...

## Contexto

Algumas informacoes...
"""
        resultado = _detectar_secao_plano(conteudo)
        assert resultado is None

    def test_detecta_ate_proxima_secao(self):
        """Detecta ate proxima secao h2."""
        conteudo = """## Plano da Julia

Conteudo do plano

## Outra Secao

Outro conteudo
"""
        resultado = _detectar_secao_plano(conteudo)
        assert resultado is not None
        assert "Conteudo do plano" in resultado
        assert "Outra Secao" not in resultado

    def test_detecta_ate_fim_se_ultima_secao(self):
        """Detecta ate fim se for ultima secao."""
        conteudo = """# Briefing

Introducao

## Plano da Julia

1. Passo 1
2. Passo 2
"""
        resultado = _detectar_secao_plano(conteudo)
        assert resultado is not None
        assert "Passo 2" in resultado


class TestVerificarConfiguracao:
    """Testes da funcao verificar_configuracao."""

    def test_sem_credentials(self):
        """Retorna erro se sem credenciais."""
        with patch("app.services.google_docs.CREDENTIALS_PATH", None):
            with patch("app.services.google_docs.DOC_ID", "doc123"):
                with patch("app.services.google_docs.FOLDER_ID", None):
                    resultado = verificar_configuracao()

        assert resultado["configurado"] is False
        assert len(resultado["erros"]) > 0
        assert "GOOGLE_APPLICATION_CREDENTIALS" in resultado["erros"][0]

    def test_arquivo_nao_existe(self):
        """Retorna erro se arquivo de credenciais nao existe."""
        with patch("app.services.google_docs.CREDENTIALS_PATH", "/caminho/inexistente.json"):
            with patch("app.services.google_docs.DOC_ID", "doc123"):
                with patch("app.services.google_docs.FOLDER_ID", None):
                    with patch("os.path.exists", return_value=False):
                        resultado = verificar_configuracao()

        assert resultado["configurado"] is False
        assert resultado["credentials_existe"] is False

    def test_sem_doc_e_folder(self):
        """Retorna erro se nem DOC_ID nem FOLDER_ID definidos."""
        with patch("app.services.google_docs.CREDENTIALS_PATH", "/path/creds.json"):
            with patch("app.services.google_docs.DOC_ID", None):
                with patch("app.services.google_docs.FOLDER_ID", None):
                    with patch("os.path.exists", return_value=True):
                        resultado = verificar_configuracao()

        assert resultado["configurado"] is False
        assert any("DOC_ID" in e or "FOLDER_ID" in e for e in resultado["erros"])

    def test_configuracao_valida(self):
        """Retorna sucesso se tudo configurado."""
        with patch("app.services.google_docs.CREDENTIALS_PATH", "/path/creds.json"):
            with patch("app.services.google_docs.DOC_ID", "doc123"):
                with patch("app.services.google_docs.FOLDER_ID", "folder456"):
                    with patch("os.path.exists", return_value=True):
                        resultado = verificar_configuracao()

        assert resultado["configurado"] is True
        assert resultado["credentials_existe"] is True
        assert len(resultado["erros"]) == 0


class TestListarDocumentos:
    """Testes da funcao listar_documentos."""

    @pytest.mark.asyncio
    async def test_lista_documentos(self):
        """Lista documentos da pasta."""
        mock_drive = MagicMock()
        mock_drive.files().list().execute.return_value = {
            "files": [
                {
                    "id": "doc1",
                    "name": "briefing-dezembro",
                    "modifiedTime": "2025-12-15T14:30:00Z",
                    "webViewLink": "https://docs.google.com/document/d/doc1"
                },
                {
                    "id": "doc2",
                    "name": "_template",  # Deve ser ignorado (prefixo _)
                    "modifiedTime": "2025-12-14T10:00:00Z",
                    "webViewLink": "https://docs.google.com/document/d/doc2"
                },
            ]
        }

        with patch("app.services.google_docs._get_drive_service", return_value=mock_drive):
            with patch("app.services.google_docs.FOLDER_ID", "folder123"):
                # Limpar cache
                import app.services.google_docs as gd
                gd._docs_cache = {}
                gd._docs_cache_time = None

                from app.services.google_docs import listar_documentos
                resultado = await listar_documentos()

        # Deve retornar apenas o briefing (nao o _template)
        assert len(resultado) == 1
        assert resultado[0].nome == "briefing-dezembro"

    @pytest.mark.asyncio
    async def test_lista_vazia_sem_folder(self):
        """Retorna lista vazia se FOLDER_ID nao configurado."""
        with patch("app.services.google_docs.FOLDER_ID", None):
            from app.services.google_docs import listar_documentos
            resultado = await listar_documentos()

        assert resultado == []


class TestBuscarDocumentoPorNome:
    """Testes da funcao buscar_documento_por_nome."""

    @pytest.mark.asyncio
    async def test_match_exato(self):
        """Match exato retorna apenas um documento."""
        docs = [
            DocInfo(id="doc1", nome="campanha-sao-luiz", ultima_modificacao=datetime.now(), url="..."),
            DocInfo(id="doc2", nome="campanha-sao-luiz-dezembro", ultima_modificacao=datetime.now(), url="..."),
        ]

        with patch("app.services.google_docs.listar_documentos", new_callable=AsyncMock) as mock:
            mock.return_value = docs

            from app.services.google_docs import buscar_documento_por_nome
            resultado = await buscar_documento_por_nome("campanha-sao-luiz")

        assert len(resultado) == 1
        assert resultado[0].id == "doc1"

    @pytest.mark.asyncio
    async def test_match_parcial(self):
        """Match parcial retorna multiplos documentos."""
        docs = [
            DocInfo(id="doc1", nome="campanha-sao-luiz-nov", ultima_modificacao=datetime.now(), url="..."),
            DocInfo(id="doc2", nome="campanha-sao-luiz-dez", ultima_modificacao=datetime.now(), url="..."),
            DocInfo(id="doc3", nome="outro-briefing", ultima_modificacao=datetime.now(), url="..."),
        ]

        with patch("app.services.google_docs.listar_documentos", new_callable=AsyncMock) as mock:
            mock.return_value = docs

            from app.services.google_docs import buscar_documento_por_nome
            resultado = await buscar_documento_por_nome("sao-luiz")

        assert len(resultado) == 2
        ids = [d.id for d in resultado]
        assert "doc1" in ids
        assert "doc2" in ids

    @pytest.mark.asyncio
    async def test_sem_match(self):
        """Sem match retorna lista vazia."""
        docs = [
            DocInfo(id="doc1", nome="briefing-abc", ultima_modificacao=datetime.now(), url="..."),
        ]

        with patch("app.services.google_docs.listar_documentos", new_callable=AsyncMock) as mock:
            mock.return_value = docs

            from app.services.google_docs import buscar_documento_por_nome
            resultado = await buscar_documento_por_nome("xyz")

        assert resultado == []

    @pytest.mark.asyncio
    async def test_case_insensitive(self):
        """Busca eh case insensitive."""
        docs = [
            DocInfo(id="doc1", nome="Campanha-SAO-LUIZ", ultima_modificacao=datetime.now(), url="..."),
        ]

        with patch("app.services.google_docs.listar_documentos", new_callable=AsyncMock) as mock:
            mock.return_value = docs

            from app.services.google_docs import buscar_documento_por_nome
            resultado = await buscar_documento_por_nome("sao-luiz")

        assert len(resultado) == 1


class TestLerDocumento:
    """Testes da funcao ler_documento."""

    @pytest.mark.asyncio
    async def test_le_documento(self):
        """Le documento corretamente."""
        mock_docs = MagicMock()
        mock_docs.documents().get().execute.return_value = {
            "title": "Briefing Teste",
            "body": {
                "content": [
                    {"paragraph": {"elements": [{"textRun": {"content": "Conteudo aqui"}}]}}
                ]
            }
        }

        mock_drive = MagicMock()
        mock_drive.files().get().execute.return_value = {
            "modifiedTime": "2025-12-15T14:30:00Z",
            "webViewLink": "https://docs.google.com/document/d/doc123"
        }

        with patch("app.services.google_docs._get_docs_service", return_value=mock_docs):
            with patch("app.services.google_docs._get_drive_service", return_value=mock_drive):
                from app.services.google_docs import ler_documento
                resultado = await ler_documento("doc123")

        assert resultado is not None
        assert resultado.info.nome == "Briefing Teste"
        assert resultado.conteudo == "Conteudo aqui"
        assert resultado.ja_processado is False

    @pytest.mark.asyncio
    async def test_le_documento_com_plano(self):
        """Detecta se documento ja tem plano."""
        mock_docs = MagicMock()
        mock_docs.documents().get().execute.return_value = {
            "title": "Briefing",
            "body": {
                "content": [
                    {"paragraph": {"elements": [{"textRun": {"content": "Briefing\n\n## Plano da Julia\n\nPassos..."}}]}}
                ]
            }
        }

        mock_drive = MagicMock()
        mock_drive.files().get().execute.return_value = {
            "modifiedTime": "2025-12-15T14:30:00Z",
            "webViewLink": "https://..."
        }

        with patch("app.services.google_docs._get_docs_service", return_value=mock_docs):
            with patch("app.services.google_docs._get_drive_service", return_value=mock_drive):
                from app.services.google_docs import ler_documento
                resultado = await ler_documento("doc123")

        assert resultado.ja_processado is True
        assert resultado.secao_plano_existente is not None
