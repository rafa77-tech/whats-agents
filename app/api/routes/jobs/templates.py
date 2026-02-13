"""
Jobs de sincronizacao e setup de templates de campanha.

Sprint 58 - Epic 1: Decomposicao de jobs.py
"""

import logging
import os

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.core.timezone import agora_brasilia

from ._helpers import job_endpoint

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/sync-templates")
@job_endpoint("sync-templates")
async def job_sync_templates():
    """
    Sincroniza templates de campanha do Google Drive.

    Busca a pasta configurada em GOOGLE_TEMPLATES_FOLDER_ID,
    procura subpastas para cada tipo de campanha (Discovery, Oferta, etc),
    e sincroniza o arquivo mais recente de cada pasta para o banco.
    """
    from app.services.campaign_behaviors import sincronizar_behaviors as sincronizar_templates

    resultado = await sincronizar_templates()
    return JSONResponse(resultado)


@router.post("/setup-templates")
async def job_setup_templates(parent_folder_id: str):
    """
    Cria estrutura de pastas e templates iniciais no Google Drive.

    Args:
        parent_folder_id: ID da pasta onde criar a estrutura (ex: pasta de Briefings)

    Estrutura criada:
        Templates/
        |-- Discovery/
        |   |-- discovery_2025-01-01
        |-- Oferta/
        |   |-- oferta_2025-01-01
        |-- Reativacao/
        |   |-- reativacao_2025-01-01
        |-- Followup/
        |   |-- followup_2025-01-01
        |-- Feedback/
            |-- feedback_2025-01-01
    """
    from app.services.google_docs import criar_pasta, criar_documento, listar_subpastas

    try:
        # Verificar se ja existe pasta Templates
        subpastas = await listar_subpastas(parent_folder_id)
        templates_folder = next((p for p in subpastas if p["name"] == "Templates"), None)

        if templates_folder:
            templates_id = templates_folder["id"]
            logger.info(f"Pasta Templates ja existe: {templates_id}")
        else:
            # Criar pasta principal Templates
            templates_id = await criar_pasta("Templates", parent_folder_id)
            if not templates_id:
                return JSONResponse(
                    {"status": "error", "message": "Falha ao criar pasta Templates"},
                    status_code=500,
                )

        # Estrutura de templates
        templates_config = [
            ("Discovery", "discovery"),
            ("Oferta", "oferta"),
            ("Reativacao", "reativacao"),
            ("Followup", "followup"),
            ("Feedback", "feedback"),
        ]

        data_hoje = agora_brasilia().strftime("%Y-%m-%d")
        resultado = {"pastas": [], "documentos": [], "templates_folder_id": templates_id}

        # Verificar subpastas existentes
        subpastas_templates = await listar_subpastas(templates_id)
        subpastas_existentes = {p["name"]: p["id"] for p in subpastas_templates}

        for pasta_nome, template_tipo in templates_config:
            # Criar subpasta se nao existe
            if pasta_nome in subpastas_existentes:
                pasta_id = subpastas_existentes[pasta_nome]
                logger.info(f"Subpasta {pasta_nome} ja existe: {pasta_id}")
            else:
                pasta_id = await criar_pasta(pasta_nome, templates_id)
                if pasta_id:
                    resultado["pastas"].append({"nome": pasta_nome, "id": pasta_id})

            if not pasta_id:
                continue

            # Ler template do arquivo local
            template_path = f"docs/templates/{template_tipo}_2025-01-01.md"
            if os.path.exists(template_path):
                with open(template_path, "r", encoding="utf-8") as f:
                    conteudo = f.read()

                # Criar documento
                doc_nome = f"{template_tipo}_{data_hoje}"
                doc_id = await criar_documento(doc_nome, conteudo, pasta_id)
                if doc_id:
                    resultado["documentos"].append(
                        {"nome": doc_nome, "id": doc_id, "tipo": template_tipo}
                    )

        return JSONResponse(
            {
                "status": "ok",
                "message": f"Estrutura criada com {len(resultado['pastas'])} pastas e {len(resultado['documentos'])} documentos",
                **resultado,
            }
        )

    except Exception as e:
        logger.error(f"Erro ao criar estrutura de templates: {e}")
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)
