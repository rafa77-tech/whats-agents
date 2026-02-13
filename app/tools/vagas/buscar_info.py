"""
Tool handler: buscar_info_hospital.

Processa busca de informacoes de hospitais.

Sprint 58 - E5: Extraido de vagas.py monolitico.
"""

import logging

logger = logging.getLogger(__name__)


async def handle_buscar_info_hospital(tool_input: dict, medico: dict, conversa: dict) -> dict:
    """
    Busca informacoes de um hospital pelo nome.

    Args:
        tool_input: Input da tool (nome_hospital)
        medico: Dados do medico (nao usado aqui)
        conversa: Dados da conversa (nao usado aqui)

    Returns:
        Dict com informacoes do hospital ou erro
    """
    # Import lazy para manter patch path via app.tools.vagas (package __init__)
    from app.tools.vagas import supabase

    nome_hospital = tool_input.get("nome_hospital", "").strip()

    if not nome_hospital:
        return {
            "success": False,
            "error": "Nome do hospital nao informado",
            "mensagem_sugerida": "Qual hospital voce quer saber o endereco?",
        }

    logger.info(f"Buscando info do hospital: {nome_hospital}")

    try:
        response = (
            supabase.table("hospitais")
            .select("*")
            .ilike("nome", f"%{nome_hospital}%")
            .limit(1)
            .execute()
        )

        if not response.data:
            logger.warning(f"Hospital '{nome_hospital}' nao encontrado")
            return {
                "success": False,
                "error": f"Hospital '{nome_hospital}' nao encontrado",
                "mensagem_sugerida": f"Nao encontrei o hospital '{nome_hospital}' no nosso sistema. Pode me dar o nome completo?",
            }

        hospital = response.data[0]
        logger.info(f"Hospital encontrado: {hospital.get('nome')}")

        return {
            "success": True,
            "hospital": {
                "nome": hospital.get("nome"),
                "endereco": hospital.get("endereco_formatado"),
                "logradouro": hospital.get("logradouro"),
                "numero": hospital.get("numero"),
                "bairro": hospital.get("bairro"),
                "cidade": hospital.get("cidade"),
                "estado": hospital.get("estado"),
                "cep": hospital.get("cep"),
            },
            "instrucao": f"Informe o endereco ao medico: {hospital.get('endereco_formatado') or 'endereco nao disponivel'}",
        }

    except Exception as e:
        logger.error(f"Erro ao buscar hospital: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "mensagem_sugerida": "Tive um probleminha pra buscar o endereco. Deixa eu verificar aqui e ja te mando",
        }
