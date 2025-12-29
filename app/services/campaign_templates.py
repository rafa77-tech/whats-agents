"""
Serviço de templates de campanha via Google Drive.

Sprint 19 - Templates por tipo de campanha.

Estrutura esperada no Google Drive:
    📁 Templates/
    ├── 📁 Discovery/
    │   ├── discovery_2025-01-15.md
    │   └── discovery_2025-01-08.md
    ├── 📁 Oferta/
    │   └── oferta_2025-01-14.md
    ├── 📁 Reativacao/
    │   └── reativacao_2025-01-10.md
    ├── 📁 Followup/
    │   └── followup_2025-01-12.md
    └── 📁 Feedback/
        └── feedback_2025-01-05.md

A Julia busca diariamente o arquivo mais recente de cada pasta.
"""
import os
import re
import logging
from datetime import datetime, timezone
from typing import Optional
from dataclasses import dataclass, field

from app.services.supabase import supabase

logger = logging.getLogger(__name__)

# ID da pasta de templates (subpasta de Briefings)
TEMPLATES_FOLDER_ID = os.getenv("GOOGLE_TEMPLATES_FOLDER_ID")

# Tipos de campanha suportados
CAMPAIGN_TYPES = ["discovery", "oferta", "reativacao", "followup", "feedback"]


@dataclass
class CampaignTemplate:
    """Template de campanha parseado."""
    tipo: str
    nome_arquivo: str
    data_arquivo: Optional[datetime]
    ultima_sync: datetime

    # Conteúdo parseado
    objetivo: str = ""
    tom: str = ""
    informacoes_importantes: list = field(default_factory=list)
    o_que_nao_fazer: list = field(default_factory=list)
    exemplo_abertura: str = ""
    regras_followup: str = ""
    margem_negociacao: Optional[int] = None

    # Raw
    conteudo_raw: str = ""


async def listar_pastas_templates() -> list[dict]:
    """
    Lista subpastas dentro da pasta Templates.

    Returns:
        Lista de dicts com id, nome da pasta
    """
    if not TEMPLATES_FOLDER_ID:
        logger.warning("GOOGLE_TEMPLATES_FOLDER_ID não configurado")
        return []

    try:
        from app.services.google_docs import _get_drive_service

        service = _get_drive_service()

        # Buscar subpastas
        query = f"'{TEMPLATES_FOLDER_ID}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"

        results = service.files().list(
            q=query,
            fields="files(id, name)",
            pageSize=20,
            supportsAllDrives=True,
            includeItemsFromAllDrives=True
        ).execute()

        folders = results.get('files', [])
        logger.info(f"Encontradas {len(folders)} pastas de templates")

        return [{"id": f["id"], "nome": f["name"]} for f in folders]

    except Exception as e:
        logger.error(f"Erro ao listar pastas de templates: {e}")
        return []


async def buscar_arquivo_mais_recente(folder_id: str, folder_name: str) -> Optional[dict]:
    """
    Busca o arquivo mais recente dentro de uma pasta de template.

    Ordena por:
    1. Data no nome do arquivo (template_YYYY-MM-DD.md)
    2. Se não tiver data no nome, usa modifiedTime

    Args:
        folder_id: ID da pasta no Drive
        folder_name: Nome da pasta (para logs)

    Returns:
        Dict com id, nome, conteudo ou None
    """
    try:
        from app.services.google_docs import _get_drive_service, ler_documento

        service = _get_drive_service()

        # Buscar arquivos Google Docs na pasta
        query = f"'{folder_id}' in parents and mimeType='application/vnd.google-apps.document' and trashed=false"

        results = service.files().list(
            q=query,
            fields="files(id, name, modifiedTime)",
            orderBy="modifiedTime desc",
            pageSize=20,
            supportsAllDrives=True,
            includeItemsFromAllDrives=True
        ).execute()

        files = results.get('files', [])

        if not files:
            logger.warning(f"Nenhum arquivo encontrado na pasta {folder_name}")
            return None

        # Tentar ordenar por data no nome do arquivo
        def extrair_data_nome(nome: str) -> Optional[datetime]:
            """Extrai data do nome do arquivo (ex: discovery_2025-01-15.md)"""
            match = re.search(r'(\d{4}-\d{2}-\d{2})', nome)
            if match:
                try:
                    return datetime.strptime(match.group(1), "%Y-%m-%d")
                except ValueError:
                    pass
            return None

        # Ordenar: primeiro por data no nome, depois por modifiedTime
        files_com_data = []
        for f in files:
            data_nome = extrair_data_nome(f['name'])
            modified = datetime.fromisoformat(f['modifiedTime'].replace('Z', '+00:00'))
            files_com_data.append({
                **f,
                'data_nome': data_nome,
                'modified': modified
            })

        # Ordenar: data_nome desc (None vai pro fim), depois modified desc
        files_ordenados = sorted(
            files_com_data,
            key=lambda x: (x['data_nome'] or datetime.min, x['modified']),
            reverse=True
        )

        arquivo_mais_recente = files_ordenados[0]

        # Ler conteúdo
        doc = await ler_documento(arquivo_mais_recente['id'])

        if not doc:
            logger.error(f"Erro ao ler documento {arquivo_mais_recente['name']}")
            return None

        logger.info(f"Template mais recente de {folder_name}: {arquivo_mais_recente['name']}")

        return {
            "id": arquivo_mais_recente['id'],
            "nome": arquivo_mais_recente['name'],
            "data_nome": arquivo_mais_recente['data_nome'],
            "conteudo": doc.conteudo
        }

    except Exception as e:
        logger.error(f"Erro ao buscar arquivo mais recente em {folder_name}: {e}")
        return None


def parsear_template(conteudo: str, tipo: str, nome_arquivo: str) -> CampaignTemplate:
    """
    Parseia conteúdo de um template de campanha.

    Extrai seções:
    - ## Objetivo
    - ## Tom
    - ## Informações Importantes
    - ## O que NÃO fazer
    - ## Exemplo de Abertura
    - ## Follow-up
    - ## Margem de Negociação (se houver)

    Args:
        conteudo: Texto raw do documento
        tipo: Tipo da campanha (discovery, oferta, etc)
        nome_arquivo: Nome do arquivo

    Returns:
        CampaignTemplate parseado
    """
    template = CampaignTemplate(
        tipo=tipo,
        nome_arquivo=nome_arquivo,
        data_arquivo=_extrair_data_nome(nome_arquivo),
        ultima_sync=datetime.now(timezone.utc),
        conteudo_raw=conteudo
    )

    # Extrair seções usando regex
    secoes = re.split(r'\n##\s+', conteudo)

    for secao in secoes:
        linhas = secao.strip().split('\n')
        if not linhas:
            continue

        titulo = linhas[0].lower().strip()
        corpo = '\n'.join(linhas[1:]).strip()

        if 'objetivo' in titulo:
            template.objetivo = corpo

        elif 'tom' in titulo:
            template.tom = corpo

        elif 'informa' in titulo and 'importante' in titulo:
            # Extrair itens (linhas com - ou *)
            itens = re.findall(r'^[-*]\s*(.+)$', corpo, re.MULTILINE)
            template.informacoes_importantes = itens if itens else [corpo]

        elif 'n[aã]o fazer' in titulo or 'nao fazer' in titulo:
            itens = re.findall(r'^[-*]\s*(.+)$', corpo, re.MULTILINE)
            template.o_que_nao_fazer = itens if itens else [corpo]

        elif 'exemplo' in titulo and 'abertura' in titulo:
            template.exemplo_abertura = corpo

        elif 'follow' in titulo:
            template.regras_followup = corpo

        elif 'margem' in titulo or 'negoci' in titulo:
            # Tentar extrair percentual
            match = re.search(r'(\d+)\s*%', corpo)
            if match:
                template.margem_negociacao = int(match.group(1))

    return template


def _extrair_data_nome(nome: str) -> Optional[datetime]:
    """Extrai data do nome do arquivo."""
    match = re.search(r'(\d{4}-\d{2}-\d{2})', nome)
    if match:
        try:
            return datetime.strptime(match.group(1), "%Y-%m-%d")
        except ValueError:
            pass
    return None


async def sincronizar_templates() -> dict:
    """
    Sincroniza todos os templates do Google Drive para o banco.

    Deve ser chamado diariamente pelo scheduler.

    Returns:
        Dict com estatísticas de sync
    """
    resultado = {
        "success": True,
        "templates_atualizados": 0,
        "erros": [],
        "detalhes": []
    }

    # Listar pastas de templates
    pastas = await listar_pastas_templates()

    if not pastas:
        resultado["success"] = False
        resultado["erros"].append("Nenhuma pasta de templates encontrada")
        return resultado

    for pasta in pastas:
        tipo = pasta["nome"].lower().replace(" ", "_")

        # Validar tipo conhecido
        if tipo not in CAMPAIGN_TYPES:
            logger.warning(f"Tipo de campanha desconhecido: {tipo}")
            continue

        # Buscar arquivo mais recente
        arquivo = await buscar_arquivo_mais_recente(pasta["id"], pasta["nome"])

        if not arquivo:
            resultado["erros"].append(f"Sem arquivo em {pasta['nome']}")
            continue

        # Parsear template
        template = parsear_template(arquivo["conteudo"], tipo, arquivo["nome"])

        # Salvar no banco
        try:
            await _salvar_template_banco(template)
            resultado["templates_atualizados"] += 1
            resultado["detalhes"].append({
                "tipo": tipo,
                "arquivo": arquivo["nome"],
                "objetivo": template.objetivo[:100] + "..." if len(template.objetivo) > 100 else template.objetivo
            })
        except Exception as e:
            resultado["erros"].append(f"Erro ao salvar {tipo}: {e}")

    logger.info(
        f"Sync de templates concluído: {resultado['templates_atualizados']} atualizados, "
        f"{len(resultado['erros'])} erros"
    )

    return resultado


async def _salvar_template_banco(template: CampaignTemplate) -> None:
    """
    Salva template no banco de dados (tabela diretrizes).

    Usa tipo = 'template_{tipo_campanha}' para diferenciar de outras diretrizes.
    """
    # Serializar template para JSON
    import json

    template_json = json.dumps({
        "objetivo": template.objetivo,
        "tom": template.tom,
        "informacoes_importantes": template.informacoes_importantes,
        "o_que_nao_fazer": template.o_que_nao_fazer,
        "exemplo_abertura": template.exemplo_abertura,
        "regras_followup": template.regras_followup,
        "margem_negociacao": template.margem_negociacao,
        "nome_arquivo": template.nome_arquivo,
        "data_arquivo": template.data_arquivo.isoformat() if template.data_arquivo else None,
    }, ensure_ascii=False)

    # Upsert na tabela diretrizes
    supabase.table("diretrizes").upsert({
        "tipo": f"template_{template.tipo}",
        "conteudo": template_json,
        "prioridade": 5,  # Templates têm prioridade média
        "ativo": True,
        "updated_at": datetime.now(timezone.utc).isoformat()
    }, on_conflict="tipo").execute()

    logger.debug(f"Template {template.tipo} salvo no banco")


async def buscar_template(tipo: str) -> Optional[CampaignTemplate]:
    """
    Busca template do banco de dados.

    Args:
        tipo: Tipo da campanha (discovery, oferta, etc)

    Returns:
        CampaignTemplate ou None se não encontrado
    """
    import json

    try:
        response = supabase.table("diretrizes").select("*").eq(
            "tipo", f"template_{tipo}"
        ).eq("ativo", True).single().execute()

        if not response.data:
            return None

        data = json.loads(response.data["conteudo"])

        return CampaignTemplate(
            tipo=tipo,
            nome_arquivo=data.get("nome_arquivo", ""),
            data_arquivo=datetime.fromisoformat(data["data_arquivo"]) if data.get("data_arquivo") else None,
            ultima_sync=datetime.fromisoformat(response.data["updated_at"].replace("Z", "+00:00")),
            objetivo=data.get("objetivo", ""),
            tom=data.get("tom", ""),
            informacoes_importantes=data.get("informacoes_importantes", []),
            o_que_nao_fazer=data.get("o_que_nao_fazer", []),
            exemplo_abertura=data.get("exemplo_abertura", ""),
            regras_followup=data.get("regras_followup", ""),
            margem_negociacao=data.get("margem_negociacao"),
        )

    except Exception as e:
        logger.error(f"Erro ao buscar template {tipo}: {e}")
        return None


async def buscar_todos_templates() -> list[CampaignTemplate]:
    """
    Busca todos os templates ativos do banco.

    Returns:
        Lista de CampaignTemplate
    """
    import json

    try:
        response = supabase.table("diretrizes").select("*").like(
            "tipo", "template_%"
        ).eq("ativo", True).execute()

        templates = []
        for row in response.data or []:
            tipo = row["tipo"].replace("template_", "")
            data = json.loads(row["conteudo"])

            templates.append(CampaignTemplate(
                tipo=tipo,
                nome_arquivo=data.get("nome_arquivo", ""),
                data_arquivo=datetime.fromisoformat(data["data_arquivo"]) if data.get("data_arquivo") else None,
                ultima_sync=datetime.fromisoformat(row["updated_at"].replace("Z", "+00:00")),
                objetivo=data.get("objetivo", ""),
                tom=data.get("tom", ""),
                informacoes_importantes=data.get("informacoes_importantes", []),
                o_que_nao_fazer=data.get("o_que_nao_fazer", []),
                exemplo_abertura=data.get("exemplo_abertura", ""),
                regras_followup=data.get("regras_followup", ""),
                margem_negociacao=data.get("margem_negociacao"),
            ))

        return templates

    except Exception as e:
        logger.error(f"Erro ao buscar templates: {e}")
        return []


def formatar_template_para_prompt(template: CampaignTemplate) -> str:
    """
    Formata template para injeção no prompt da Julia.

    Args:
        template: CampaignTemplate

    Returns:
        String formatada para prompt
    """
    partes = [f"## Campanha: {template.tipo.title()}"]

    if template.objetivo:
        partes.append(f"\n**Objetivo:** {template.objetivo}")

    if template.tom:
        partes.append(f"\n**Tom:** {template.tom}")

    if template.informacoes_importantes:
        partes.append("\n**Informações Importantes:**")
        for info in template.informacoes_importantes:
            partes.append(f"- {info}")

    if template.o_que_nao_fazer:
        partes.append("\n**NÃO fazer:**")
        for item in template.o_que_nao_fazer:
            partes.append(f"- {item}")

    if template.exemplo_abertura:
        partes.append(f"\n**Exemplo de mensagem:**\n{template.exemplo_abertura}")

    if template.margem_negociacao:
        partes.append(f"\n**Margem de negociação:** até {template.margem_negociacao}%")

    return '\n'.join(partes)
