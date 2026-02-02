"""
Servico de integracao com Google Docs e Drive.

Permite:
- Buscar conteudo de documentos
- Listar documentos em pasta
- Escrever em documentos (planos da Julia)

Sprint 11 - Briefing Conversacional

Requer:
- Service Account no Google Cloud Console
- APIs habilitadas: Google Docs, Google Drive
- Credenciais JSON
- Pasta/documentos compartilhados com o Service Account (Editor)
"""
import os
import json
import hashlib
import logging
import re
from datetime import datetime, timedelta
from typing import Optional
from dataclasses import dataclass

from app.core.config import DatabaseConfig
from app.core.timezone import agora_brasilia

logger = logging.getLogger(__name__)

# Configuracao
SCOPES = [
    'https://www.googleapis.com/auth/documents',  # Leitura e escrita em Docs
    'https://www.googleapis.com/auth/drive',  # Acesso completo ao Drive (necessário para ver compartilhados)
]
# Suporta duas formas de credenciais:
# 1. GOOGLE_APPLICATION_CREDENTIALS = caminho para arquivo JSON (dev local)
# 2. GOOGLE_CREDENTIALS_JSON = JSON inline como string (Railway/cloud)
CREDENTIALS_PATH = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
CREDENTIALS_JSON = os.getenv('GOOGLE_CREDENTIALS_JSON')
DOC_ID = os.getenv('BRIEFING_DOC_ID')  # Legado - doc unico
FOLDER_ID = os.getenv('GOOGLE_BRIEFINGS_FOLDER_ID')  # Novo - pasta de briefings

# Cache para evitar reimportar
_docs_service = None
_drive_service = None
_docs_cache: dict = {}
_docs_cache_time: Optional[datetime] = None
DOCS_CACHE_TTL_MINUTES = DatabaseConfig.CACHE_TTL_DOCS // 60  # Centralizado em config


@dataclass
class DocInfo:
    """Informacoes de um documento."""
    id: str
    nome: str
    ultima_modificacao: datetime
    url: str


@dataclass
class DocContent:
    """Conteudo de um documento."""
    info: DocInfo
    conteudo: str
    hash: str
    ja_processado: bool
    secao_plano_existente: Optional[str] = None


def _get_credentials():
    """
    Carrega credenciais do Service Account.

    Suporta duas formas:
    1. GOOGLE_CREDENTIALS_JSON - JSON inline (Railway/cloud)
    2. GOOGLE_APPLICATION_CREDENTIALS - caminho para arquivo (dev local)
    """
    from google.oauth2 import service_account

    # Prioridade 1: JSON inline (para Railway/cloud)
    if CREDENTIALS_JSON:
        try:
            credentials_info = json.loads(CREDENTIALS_JSON)
            logger.debug("Usando credenciais Google via GOOGLE_CREDENTIALS_JSON")
            return service_account.Credentials.from_service_account_info(
                credentials_info,
                scopes=SCOPES
            )
        except json.JSONDecodeError as e:
            raise ValueError(f"GOOGLE_CREDENTIALS_JSON invalido: {e}")

    # Prioridade 2: Arquivo (para dev local)
    if CREDENTIALS_PATH:
        if not os.path.exists(CREDENTIALS_PATH):
            raise FileNotFoundError(f"Arquivo de credenciais nao encontrado: {CREDENTIALS_PATH}")

        logger.debug("Usando credenciais Google via arquivo")
        return service_account.Credentials.from_service_account_file(
            CREDENTIALS_PATH,
            scopes=SCOPES
        )

    raise ValueError(
        "Credenciais Google nao configuradas. "
        "Defina GOOGLE_CREDENTIALS_JSON (JSON inline) ou "
        "GOOGLE_APPLICATION_CREDENTIALS (caminho do arquivo)"
    )


def _get_docs_service():
    """Retorna cliente da API do Google Docs."""
    global _docs_service

    if _docs_service is None:
        from googleapiclient.discovery import build
        credentials = _get_credentials()
        _docs_service = build('docs', 'v1', credentials=credentials)

    return _docs_service


def _get_drive_service():
    """Retorna cliente da API do Google Drive."""
    global _drive_service

    if _drive_service is None:
        from googleapiclient.discovery import build
        credentials = _get_credentials()
        _drive_service = build('drive', 'v3', credentials=credentials)

    return _drive_service


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


def _detectar_secao_plano(conteudo: str) -> Optional[str]:
    """Detecta se documento ja tem secao '## Plano da Julia'."""
    match = re.search(r'## Plano da Julia.*?(?=\n## |\Z)', conteudo, re.DOTALL)
    if match:
        return match.group(0)
    return None


# =============================================================================
# FUNCOES DE CRIACAO (Drive)
# =============================================================================


async def criar_pasta(nome: str, parent_id: Optional[str] = None) -> Optional[str]:
    """
    Cria uma pasta no Google Drive.

    Args:
        nome: Nome da pasta
        parent_id: ID da pasta pai (opcional)

    Returns:
        ID da pasta criada ou None se erro
    """
    try:
        service = _get_drive_service()

        file_metadata = {
            'name': nome,
            'mimeType': 'application/vnd.google-apps.folder'
        }

        if parent_id:
            file_metadata['parents'] = [parent_id]

        folder = service.files().create(
            body=file_metadata,
            fields='id, webViewLink'
        ).execute()

        folder_id = folder.get('id')
        logger.info(f"Pasta criada: {nome} (ID: {folder_id})")
        return folder_id

    except Exception as e:
        logger.error(f"Erro ao criar pasta {nome}: {e}")
        return None


async def criar_documento(nome: str, conteudo: str, parent_id: Optional[str] = None) -> Optional[str]:
    """
    Cria um documento no Google Drive com conteudo inicial.

    Args:
        nome: Nome do documento
        conteudo: Conteudo inicial (texto)
        parent_id: ID da pasta pai (opcional)

    Returns:
        ID do documento criado ou None se erro
    """
    try:
        drive_service = _get_drive_service()
        docs_service = _get_docs_service()

        # Criar documento vazio primeiro
        file_metadata = {
            'name': nome,
            'mimeType': 'application/vnd.google-apps.document'
        }

        if parent_id:
            file_metadata['parents'] = [parent_id]

        doc = drive_service.files().create(
            body=file_metadata,
            fields='id'
        ).execute()

        doc_id = doc.get('id')

        # Inserir conteudo
        if conteudo:
            requests = [{
                'insertText': {
                    'location': {'index': 1},
                    'text': conteudo
                }
            }]

            docs_service.documents().batchUpdate(
                documentId=doc_id,
                body={'requests': requests}
            ).execute()

        logger.info(f"Documento criado: {nome} (ID: {doc_id})")
        return doc_id

    except Exception as e:
        logger.error(f"Erro ao criar documento {nome}: {e}")
        return None


async def listar_subpastas(folder_id: str) -> list[dict]:
    """
    Lista subpastas de uma pasta.

    Args:
        folder_id: ID da pasta pai

    Returns:
        Lista de dicts com id e name das subpastas
    """
    try:
        service = _get_drive_service()

        query = f"'{folder_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"

        results = service.files().list(
            q=query,
            fields="files(id, name)",
            pageSize=50,
            supportsAllDrives=True,
            includeItemsFromAllDrives=True
        ).execute()

        return results.get('files', [])

    except Exception as e:
        logger.error(f"Erro ao listar subpastas de {folder_id}: {e}")
        return []


# =============================================================================
# FUNCOES DE LISTAGEM (Drive)
# =============================================================================

async def listar_documentos(folder_id: Optional[str] = None, force_refresh: bool = False) -> list[DocInfo]:
    """
    Lista documentos na pasta de briefings.

    Cache de 5 minutos para evitar rate limit.

    Args:
        folder_id: ID da pasta (usa GOOGLE_BRIEFINGS_FOLDER_ID se nao informado)
        force_refresh: Ignorar cache

    Returns:
        Lista de DocInfo
    """
    global _docs_cache, _docs_cache_time

    folder = folder_id or FOLDER_ID
    if not folder:
        logger.warning("GOOGLE_BRIEFINGS_FOLDER_ID nao configurado")
        return []

    # Verificar cache
    if not force_refresh and _docs_cache_time:
        if agora_brasilia() - _docs_cache_time < timedelta(minutes=DOCS_CACHE_TTL_MINUTES):
            if folder in _docs_cache:
                logger.debug(f"Usando cache de documentos ({len(_docs_cache[folder])} docs)")
                return _docs_cache[folder]

    try:
        service = _get_drive_service()

        # Buscar apenas Google Docs na pasta
        query = f"'{folder}' in parents and mimeType='application/vnd.google-apps.document' and trashed=false"

        results = service.files().list(
            q=query,
            fields="files(id, name, modifiedTime, webViewLink)",
            orderBy="modifiedTime desc",
            pageSize=50,
            supportsAllDrives=True,
            includeItemsFromAllDrives=True
        ).execute()

        files = results.get('files', [])

        docs = []
        for f in files:
            # Ignorar docs de referencia (prefixo _)
            if f['name'].startswith('_'):
                continue

            docs.append(DocInfo(
                id=f['id'],
                nome=f['name'],
                ultima_modificacao=datetime.fromisoformat(f['modifiedTime'].replace('Z', '+00:00')),
                url=f.get('webViewLink', f"https://docs.google.com/document/d/{f['id']}")
            ))

        # Atualizar cache
        _docs_cache[folder] = docs
        _docs_cache_time = agora_brasilia()

        logger.info(f"Listados {len(docs)} documentos na pasta de briefings")
        return docs

    except Exception as e:
        logger.error(f"Erro ao listar documentos: {e}")
        return []


async def buscar_documento_por_nome(nome_parcial: str, folder_id: Optional[str] = None) -> list[DocInfo]:
    """
    Busca documento por nome parcial.

    Args:
        nome_parcial: Parte do nome a buscar (case-insensitive)
        folder_id: ID da pasta

    Returns:
        Lista de matches (pode ser 0, 1 ou N)
    """
    docs = await listar_documentos(folder_id)
    nome_lower = nome_parcial.lower().strip()

    matches = []
    for doc in docs:
        doc_nome_lower = doc.nome.lower()

        # Match exato tem prioridade
        if doc_nome_lower == nome_lower:
            return [doc]

        # Match parcial
        if nome_lower in doc_nome_lower:
            matches.append(doc)

    # Ordenar por relevancia (match no inicio primeiro)
    matches.sort(key=lambda d: d.nome.lower().index(nome_lower) if nome_lower in d.nome.lower() else 999)

    return matches


# =============================================================================
# FUNCOES DE LEITURA (Docs)
# =============================================================================

async def ler_documento(doc_id: str) -> Optional[DocContent]:
    """
    Le conteudo completo de um documento.

    Args:
        doc_id: ID do documento

    Returns:
        DocContent ou None se erro
    """
    try:
        service = _get_docs_service()
        document = service.documents().get(documentId=doc_id).execute()

        conteudo = _extrair_texto(document)
        content_hash = hashlib.md5(conteudo.encode()).hexdigest()

        # Detectar se ja foi processado
        secao_plano = _detectar_secao_plano(conteudo)

        # Tentar buscar metadata do Drive, mas nao falhar se nao conseguir
        ultima_mod = agora_brasilia()
        url = f"https://docs.google.com/document/d/{doc_id}/edit"

        try:
            drive_service = _get_drive_service()
            file_meta = drive_service.files().get(
                fileId=doc_id,
                fields="modifiedTime, webViewLink"
            ).execute()
            ultima_mod = datetime.fromisoformat(
                file_meta['modifiedTime'].replace('Z', '+00:00')
            )
            url = file_meta.get('webViewLink', url)
        except Exception as drive_err:
            logger.debug(f"Drive API indisponivel para metadata: {drive_err}")

        info = DocInfo(
            id=doc_id,
            nome=document.get('title', 'Sem titulo'),
            ultima_modificacao=ultima_mod,
            url=url
        )

        logger.info(f"Documento lido: {info.nome}")

        return DocContent(
            info=info,
            conteudo=conteudo,
            hash=content_hash,
            ja_processado=secao_plano is not None,
            secao_plano_existente=secao_plano
        )

    except Exception as e:
        logger.error(f"Erro ao ler documento {doc_id}: {e}")
        return None


async def buscar_documento_briefing() -> dict:
    """
    Busca conteudo do documento de briefing.

    Suporta dois modos:
    1. DOC_ID (legado): busca documento unico pelo ID
    2. FOLDER_ID (novo): busca documento mais recente da pasta

    Returns:
        dict com:
        - success: bool
        - content: str (texto completo)
        - hash: str (hash do conteudo para comparacao)
        - title: str (titulo do documento)
        - doc_id: str
        - error: str (se falha)
    """
    # Modo 1: DOC_ID especifico (legado)
    if DOC_ID:
        return await _buscar_briefing_por_id(DOC_ID)

    # Modo 2: FOLDER_ID - buscar documento mais recente
    if FOLDER_ID:
        return await _buscar_briefing_mais_recente()

    return {
        "success": False,
        "error": "Nem BRIEFING_DOC_ID nem GOOGLE_BRIEFINGS_FOLDER_ID configurados"
    }


async def _buscar_briefing_por_id(doc_id: str) -> dict:
    """Busca briefing por ID especifico (modo legado)."""
    try:
        service = _get_docs_service()
        document = service.documents().get(documentId=doc_id).execute()

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
            "doc_id": doc_id
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


async def _buscar_briefing_mais_recente() -> dict:
    """
    Busca documento de briefing mais recente da pasta.

    Usa GOOGLE_BRIEFINGS_FOLDER_ID para listar documentos
    e retorna o mais recentemente modificado.
    """
    try:
        # Listar documentos da pasta (ja ordenados por modifiedTime desc)
        docs = await listar_documentos(FOLDER_ID, force_refresh=True)

        if not docs:
            return {
                "success": False,
                "error": f"Nenhum documento encontrado na pasta de briefings (ID: {FOLDER_ID})"
            }

        # Pegar o mais recente (primeiro da lista)
        doc_mais_recente = docs[0]
        logger.info(f"Briefing mais recente: {doc_mais_recente.nome} (modificado: {doc_mais_recente.ultima_modificacao})")

        # Ler conteudo completo
        doc_content = await ler_documento(doc_mais_recente.id)
        if not doc_content:
            return {
                "success": False,
                "error": f"Erro ao ler documento {doc_mais_recente.nome}"
            }

        return {
            "success": True,
            "content": doc_content.conteudo,
            "hash": doc_content.hash,
            "title": doc_content.info.nome,
            "doc_id": doc_mais_recente.id,
            "url": doc_mais_recente.url
        }

    except Exception as e:
        logger.error(f"Erro ao buscar briefing mais recente: {e}")
        return {
            "success": False,
            "error": str(e)
        }


# =============================================================================
# FUNCOES DE ESCRITA (Docs)
# =============================================================================

async def escrever_no_documento(doc_id: str, texto: str, posicao: str = "fim") -> bool:
    """
    Escreve texto em um documento.

    Args:
        doc_id: ID do documento
        texto: Texto a inserir
        posicao: "fim" ou "apos_briefing"

    Returns:
        True se sucesso
    """
    try:
        service = _get_docs_service()

        # Primeiro, obter documento para saber o tamanho
        document = service.documents().get(documentId=doc_id).execute()

        # Calcular indice final
        end_index = 1
        for element in document.get('body', {}).get('content', []):
            if 'endIndex' in element:
                end_index = element['endIndex']

        # Inserir no final (antes do ultimo caractere que e sempre newline)
        insert_index = max(1, end_index - 1)

        requests = [{
            'insertText': {
                'location': {'index': insert_index},
                'text': texto
            }
        }]

        service.documents().batchUpdate(
            documentId=doc_id,
            body={'requests': requests}
        ).execute()

        logger.info(f"Texto inserido no documento {doc_id}")
        return True

    except Exception as e:
        logger.error(f"Erro ao escrever no documento {doc_id}: {e}")
        return False


async def atualizar_secao_plano(doc_id: str, plano_formatado: str) -> bool:
    """
    Atualiza ou cria a secao '## Plano da Julia' no documento.

    Se ja existe, substitui. Se nao existe, adiciona no final.

    Args:
        doc_id: ID do documento
        plano_formatado: Texto formatado do plano (com headers markdown)

    Returns:
        True se sucesso
    """
    try:
        # Ler documento atual
        doc = await ler_documento(doc_id)
        if not doc:
            return False

        service = _get_docs_service()
        document = service.documents().get(documentId=doc_id).execute()

        # Se ja tem plano, precisamos encontrar e substituir
        if doc.ja_processado:
            # Encontrar inicio e fim da secao
            conteudo = doc.conteudo
            match = re.search(r'## Plano da Julia', conteudo)

            if match:
                # Encontrar fim da secao (proximo ## ou fim do doc)
                inicio_secao = match.start()
                fim_match = re.search(r'\n## (?!Plano da Julia)', conteudo[inicio_secao + 1:])

                if fim_match:
                    fim_secao = inicio_secao + 1 + fim_match.start()
                else:
                    # Vai ate o fim do documento
                    fim_secao = len(conteudo)

                # Calcular indices no documento (Google Docs usa indices de caracteres)
                # Nota: indice 1 e o inicio do body
                start_index = inicio_secao + 1  # +1 porque body comeca em 1
                end_index = fim_secao + 1

                # Deletar secao existente e inserir nova
                requests = [
                    {
                        'deleteContentRange': {
                            'range': {
                                'startIndex': start_index,
                                'endIndex': end_index
                            }
                        }
                    },
                    {
                        'insertText': {
                            'location': {'index': start_index},
                            'text': plano_formatado
                        }
                    }
                ]

                service.documents().batchUpdate(
                    documentId=doc_id,
                    body={'requests': requests}
                ).execute()

                logger.info(f"Secao de plano atualizada no documento {doc_id}")
                return True

        # Nao tem plano - adicionar no final
        # Primeiro adicionar separador
        texto_completo = "\n\n---\n\n" + plano_formatado

        return await escrever_no_documento(doc_id, texto_completo, "fim")

    except Exception as e:
        logger.error(f"Erro ao atualizar secao de plano no documento {doc_id}: {e}")
        return False


async def adicionar_linha_historico(doc_id: str, acao: str, resultado: str) -> bool:
    """
    Adiciona linha na tabela de historico do documento.

    Se nao existe tabela, cria uma.

    Args:
        doc_id: ID do documento
        acao: Descricao da acao
        resultado: Resultado da acao

    Returns:
        True se sucesso
    """
    try:
        agora = agora_brasilia()
        linha = f"| {agora.strftime('%d/%m')} | {agora.strftime('%H:%M')} | {acao} | {resultado} |\n"

        doc = await ler_documento(doc_id)
        if not doc:
            return False

        # Verificar se ja tem secao de historico
        if "## Historico de Execucao" in doc.conteudo or "## Histórico de Execução" in doc.conteudo:
            # Encontrar fim da tabela (ultima linha com |)
            conteudo = doc.conteudo
            match = re.search(r'## Hist[oó]rico de Execu[cç][aã]o.*?\n\|.*?\n\|[-|]+\|', conteudo, re.DOTALL)

            if match:
                # Encontrar ultima linha da tabela
                tabela_inicio = match.end()
                resto = conteudo[tabela_inicio:]

                # Encontrar onde a tabela termina (linha sem | no inicio)
                linhas = resto.split('\n')
                ultima_linha_tabela = tabela_inicio

                for i, l in enumerate(linhas):
                    if l.strip().startswith('|'):
                        ultima_linha_tabela = tabela_inicio + sum(len(x) + 1 for x in linhas[:i+1])
                    else:
                        break

                # Inserir nova linha
                return await escrever_no_documento(doc_id, linha, posicao="fim")

        # Nao tem historico - criar secao
        historico = f"""

## Historico de Execucao

| Data | Hora | Acao | Resultado |
|------|------|------|-----------|
{linha}"""

        return await escrever_no_documento(doc_id, historico, "fim")

    except Exception as e:
        logger.error(f"Erro ao adicionar linha de historico: {e}")
        return False


# =============================================================================
# VERIFICACAO
# =============================================================================

def verificar_configuracao() -> dict:
    """
    Verifica se a integracao com Google Docs esta configurada.

    Returns:
        dict com status da configuracao
    """
    status = {
        "configurado": False,
        "credentials_path": CREDENTIALS_PATH,
        "credentials_json_presente": bool(CREDENTIALS_JSON),
        "doc_id": DOC_ID,
        "folder_id": FOLDER_ID,
        "credentials_existe": False,
        "erros": []
    }

    # Verificar credenciais (aceita JSON inline OU arquivo)
    if CREDENTIALS_JSON:
        try:
            json.loads(CREDENTIALS_JSON)
            status["credentials_existe"] = True
        except json.JSONDecodeError:
            status["erros"].append("GOOGLE_CREDENTIALS_JSON invalido (JSON malformado)")
    elif CREDENTIALS_PATH:
        if os.path.exists(CREDENTIALS_PATH):
            status["credentials_existe"] = True
        else:
            status["erros"].append(f"Arquivo nao encontrado: {CREDENTIALS_PATH}")
    else:
        status["erros"].append(
            "Credenciais nao definidas. Use GOOGLE_CREDENTIALS_JSON ou GOOGLE_APPLICATION_CREDENTIALS"
        )

    if not DOC_ID and not FOLDER_ID:
        status["erros"].append("Nem BRIEFING_DOC_ID nem GOOGLE_BRIEFINGS_FOLDER_ID definidos")

    status["configurado"] = len(status["erros"]) == 0

    return status
