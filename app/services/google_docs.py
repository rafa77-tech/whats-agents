"""
Servico de integracao com Google Docs.

Permite buscar conteudo de documentos do Google Docs
para configuracao de briefing da Julia.

Requer:
- Service Account no Google Cloud Console
- API do Google Docs habilitada
- Credenciais JSON
- Documento compartilhado com o Service Account
"""
import os
import hashlib
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Configuracao
SCOPES = ['https://www.googleapis.com/auth/documents.readonly']
CREDENTIALS_PATH = os.getenv('GOOGLE_DOCS_CREDENTIALS_PATH')
DOC_ID = os.getenv('GOOGLE_BRIEFING_DOC_ID')

# Cache para evitar reimportar
_docs_service = None


def _get_credentials():
    """Carrega credenciais do Service Account."""
    if not CREDENTIALS_PATH:
        raise ValueError("GOOGLE_DOCS_CREDENTIALS_PATH nao configurado")

    if not os.path.exists(CREDENTIALS_PATH):
        raise FileNotFoundError(f"Arquivo de credenciais nao encontrado: {CREDENTIALS_PATH}")

    from google.oauth2 import service_account
    return service_account.Credentials.from_service_account_file(
        CREDENTIALS_PATH,
        scopes=SCOPES
    )


def _get_docs_service():
    """Retorna cliente da API do Google Docs."""
    global _docs_service

    if _docs_service is None:
        from googleapiclient.discovery import build
        credentials = _get_credentials()
        _docs_service = build('docs', 'v1', credentials=credentials)

    return _docs_service


def _extrair_texto(document: dict) -> str:
    """Extrai texto plano de um documento do Google Docs."""
    content = document.get('body', {}).get('content', [])
    text_parts = []

    for element in content:
        if 'paragraph' in element:
            for text_run in element['paragraph'].get('elements', []):
                if 'textRun' in text_run:
                    text_parts.append(text_run['textRun'].get('content', ''))

    return ''.join(text_parts)


async def buscar_documento_briefing() -> dict:
    """
    Busca conteudo do documento de briefing.

    Returns:
        dict com:
        - success: bool
        - content: str (texto completo)
        - hash: str (hash do conteudo para comparacao)
        - title: str (titulo do documento)
        - doc_id: str
        - error: str (se falha)
    """
    if not DOC_ID:
        return {
            "success": False,
            "error": "GOOGLE_BRIEFING_DOC_ID nao configurado"
        }

    try:
        service = _get_docs_service()
        document = service.documents().get(documentId=DOC_ID).execute()

        # Extrair texto de todos os elementos
        content = _extrair_texto(document)

        # Calcular hash para detectar mudancas
        content_hash = hashlib.md5(content.encode()).hexdigest()

        logger.info(f"Documento Google Docs buscado: {document.get('title', 'N/A')}")

        return {
            "success": True,
            "content": content,
            "hash": content_hash,
            "title": document.get('title', 'Briefing'),
            "doc_id": DOC_ID
        }

    except FileNotFoundError as e:
        logger.warning(f"Credenciais Google Docs nao encontradas: {e}")
        return {
            "success": False,
            "error": str(e)
        }

    except ValueError as e:
        logger.warning(f"Configuracao Google Docs incompleta: {e}")
        return {
            "success": False,
            "error": str(e)
        }

    except Exception as e:
        logger.error(f"Erro ao buscar documento Google Docs: {e}")
        return {
            "success": False,
            "error": str(e)
        }


def verificar_configuracao() -> dict:
    """
    Verifica se a integracao com Google Docs esta configurada.

    Returns:
        dict com status da configuracao
    """
    status = {
        "configurado": False,
        "credentials_path": CREDENTIALS_PATH,
        "doc_id": DOC_ID,
        "credentials_existe": False,
        "erros": []
    }

    if not CREDENTIALS_PATH:
        status["erros"].append("GOOGLE_DOCS_CREDENTIALS_PATH nao definido")
    elif os.path.exists(CREDENTIALS_PATH):
        status["credentials_existe"] = True
    else:
        status["erros"].append(f"Arquivo nao encontrado: {CREDENTIALS_PATH}")

    if not DOC_ID:
        status["erros"].append("GOOGLE_BRIEFING_DOC_ID nao definido")

    status["configurado"] = len(status["erros"]) == 0

    return status
