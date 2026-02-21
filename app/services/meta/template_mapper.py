"""
Template Variable Mapper — Mapeia variáveis de template Meta.

Sprint 66 — Converte dados do destinatário/campanha para formato Graph API.
"""

import logging
from typing import Optional, List

logger = logging.getLogger(__name__)


class TemplateMapper:
    """Mapeia variáveis de template para formato Meta Graph API."""

    # Variáveis suportadas e seus campos correspondentes
    VARIABLE_SOURCES = {
        "nome": ["nome", "primeiro_nome", "name"],
        "especialidade": ["especialidade_nome", "especialidade", "specialty"],
        "hospital": ["hospital_nome", "hospital", "hospital_name"],
        "data_plantao": ["data_plantao", "data", "date"],
        "valor": ["valor", "valor_plantao", "value"],
        "horario": ["horario", "periodo_horario", "time"],
        "periodo": ["periodo", "periodo_nome", "period"],
        "setor": ["setor", "setor_nome", "sector"],
    }

    def mapear_variaveis(
        self,
        template: dict,
        destinatario: dict,
        campanha: Optional[dict] = None,
    ) -> List[dict]:
        """
        Mapeia variáveis do template para formato Graph API components.

        Args:
            template: Dict do template (da tabela meta_templates)
            destinatario: Dict com dados do destinatário
            campanha: Dict com dados da campanha (opcional)

        Returns:
            Lista de components para o Graph API
            Ex: [{"type":"body","parameters":[{"type":"text","text":"Carlos"}]}]
        """
        variable_mapping = template.get("variable_mapping", {})
        if not variable_mapping:
            return []

        # Merge de dados: destinatário + campanha
        dados = {**destinatario}
        if campanha:
            # Campos da campanha (escopo_vagas, regras, etc)
            escopo = campanha.get("escopo_vagas") or {}
            dados.update(escopo)
            # Campos diretos da campanha
            for key in (
                "hospital",
                "hospital_nome",
                "data_plantao",
                "valor",
                "horario",
                "periodo",
                "setor",
            ):
                if key in campanha and campanha[key]:
                    dados[key] = campanha[key]

        # Montar parâmetros na ordem do variable_mapping
        # variable_mapping: {"1": "nome", "2": "especialidade", ...}
        parameters = []
        for idx in sorted(variable_mapping.keys(), key=lambda x: int(x)):
            var_name = variable_mapping[idx]
            value = self._resolver_variavel(var_name, dados)
            parameters.append({"type": "text", "text": value})

        if not parameters:
            return []

        return [{"type": "body", "parameters": parameters}]

    def _resolver_variavel(self, var_name: str, dados: dict) -> str:
        """
        Resolve valor de uma variável buscando em múltiplos campos.

        Args:
            var_name: Nome da variável (ex: "nome", "especialidade")
            dados: Dict com dados disponíveis

        Returns:
            Valor encontrado ou string vazia
        """
        # Buscar nos campos conhecidos
        sources = self.VARIABLE_SOURCES.get(var_name, [var_name])
        for field in sources:
            value = dados.get(field)
            if value:
                return str(value)

        logger.debug(f"[TemplateMapper] Variável '{var_name}' não encontrada")
        return ""

    def mapear_variaveis_com_media(
        self,
        template: dict,
        destinatario: dict,
        campanha: Optional[dict] = None,
        media_id: Optional[str] = None,
    ) -> List[dict]:
        """
        Mapeia variáveis com suporte a header de mídia.

        Args:
            template: Dict do template
            destinatario: Dict com dados do destinatário
            campanha: Dict com dados da campanha
            media_id: ID da mídia uploadada (handle)

        Returns:
            Lista de components incluindo header de mídia
        """
        components = self.mapear_variaveis(template, destinatario, campanha)

        if media_id:
            header_format = template.get("header_format", "IMAGE").upper()
            header_component = self._construir_header_parameter(header_format, media_id)
            if header_component:
                components.insert(0, header_component)

        return components

    def _construir_header_parameter(
        self,
        format_type: str,
        media_id: str,
    ) -> Optional[dict]:
        """
        Constrói componente header com mídia.

        Args:
            format_type: IMAGE, VIDEO ou DOCUMENT
            media_id: ID da mídia

        Returns:
            Dict com componente header ou None
        """
        media_type_map = {
            "IMAGE": "image",
            "VIDEO": "video",
            "DOCUMENT": "document",
        }
        media_type = media_type_map.get(format_type.upper())
        if not media_type:
            logger.warning("[TemplateMapper] Format type desconhecido: %s", format_type)
            return None

        return {
            "type": "header",
            "parameters": [
                {
                    "type": media_type,
                    media_type: {"id": media_id},
                }
            ],
        }


# Singleton
template_mapper = TemplateMapper()
