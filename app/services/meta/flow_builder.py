"""
WhatsApp Flow Builder — Construtor de flows JSON v7.0.

Sprint 68 — Epic 68.2, Chunk 5.

Cria definições JSON para flows pré-definidos:
- Onboarding de médicos
- Confirmação de plantão
- Avaliação pós-plantão
"""

import logging
from typing import Optional, List

logger = logging.getLogger(__name__)


class FlowBuilder:
    """
    Construtor de WhatsApp Flows (JSON v7.0).

    Gera definições JSON para os flows pré-definidos da Julia.
    """

    FLOW_VERSION = "7.0"

    def construir_flow_onboarding(self) -> dict:
        """
        Constrói flow de onboarding para novos médicos.

        Coleta: nome completo, CRM, especialidade, região de atuação.

        Returns:
            Dict com definição JSON do flow
        """
        return {
            "version": self.FLOW_VERSION,
            "data_api_version": "3.0",
            "routing_model": {"SCREEN_1": ["SCREEN_2"], "SCREEN_2": []},
            "screens": [
                self._construir_screen(
                    screen_id="SCREEN_1",
                    title="Cadastro Revoluna",
                    children=[
                        self._construir_componente_text_input(
                            name="nome_completo",
                            label="Nome completo",
                            required=True,
                        ),
                        self._construir_componente_text_input(
                            name="crm",
                            label="CRM (com UF)",
                            required=True,
                            helper_text="Ex: 123456/SP",
                        ),
                        self._construir_componente_dropdown(
                            name="especialidade",
                            label="Especialidade principal",
                            options=[
                                {"id": "clinica_medica", "title": "Clínica Médica"},
                                {"id": "cardiologia", "title": "Cardiologia"},
                                {"id": "pediatria", "title": "Pediatria"},
                                {"id": "ortopedia", "title": "Ortopedia"},
                                {"id": "cirurgia_geral", "title": "Cirurgia Geral"},
                                {"id": "anestesiologia", "title": "Anestesiologia"},
                                {"id": "outra", "title": "Outra"},
                            ],
                            required=True,
                        ),
                    ],
                    cta_text="Próximo",
                    next_screen="SCREEN_2",
                ),
                self._construir_screen(
                    screen_id="SCREEN_2",
                    title="Região de Atuação",
                    children=[
                        self._construir_componente_checkbox(
                            name="regioes",
                            label="Regiões de interesse",
                            options=[
                                {"id": "sp_capital", "title": "SP - Capital"},
                                {"id": "sp_abc", "title": "SP - ABC"},
                                {"id": "sp_interior", "title": "SP - Interior"},
                                {"id": "rj_capital", "title": "RJ - Capital"},
                                {"id": "outra", "title": "Outra região"},
                            ],
                        ),
                        self._construir_componente_radio(
                            name="disponibilidade",
                            label="Disponibilidade para plantões",
                            options=[
                                {"id": "imediata", "title": "Imediata"},
                                {"id": "proxima_semana", "title": "Próxima semana"},
                                {"id": "proximo_mes", "title": "Próximo mês"},
                            ],
                        ),
                    ],
                    cta_text="Finalizar",
                    is_terminal=True,
                ),
            ],
        }

    def construir_flow_confirmacao_plantao(self, vaga: dict) -> dict:
        """
        Constrói flow de confirmação de plantão.

        Args:
            vaga: Dict com dados da vaga (hospital, data, horario, valor)

        Returns:
            Dict com definição JSON do flow
        """
        hospital = vaga.get("hospital", "Hospital")
        data_plantao = vaga.get("data", "")
        horario = vaga.get("horario", "")
        valor = vaga.get("valor", "")

        return {
            "version": self.FLOW_VERSION,
            "data_api_version": "3.0",
            "routing_model": {"SCREEN_CONFIRM": []},
            "screens": [
                self._construir_screen(
                    screen_id="SCREEN_CONFIRM",
                    title="Confirmar Plantão",
                    children=[
                        {
                            "type": "TextBody",
                            "text": (
                                f"🏥 {hospital}\n📅 {data_plantao}\n⏰ {horario}\n💰 R$ {valor}"
                            ),
                        },
                        self._construir_componente_radio(
                            name="confirmacao",
                            label="Confirma presença?",
                            options=[
                                {"id": "confirmo", "title": "Sim, confirmo!"},
                                {"id": "nao_posso", "title": "Não posso mais"},
                                {"id": "reagendar", "title": "Preciso reagendar"},
                            ],
                        ),
                        self._construir_componente_text_input(
                            name="observacao",
                            label="Observação (opcional)",
                            required=False,
                        ),
                    ],
                    cta_text="Enviar",
                    is_terminal=True,
                ),
            ],
        }

    def construir_flow_avaliacao_pos_plantao(self, vaga: dict) -> dict:
        """
        Constrói flow de avaliação pós-plantão.

        Args:
            vaga: Dict com dados da vaga

        Returns:
            Dict com definição JSON do flow
        """
        hospital = vaga.get("hospital", "Hospital")

        return {
            "version": self.FLOW_VERSION,
            "data_api_version": "3.0",
            "routing_model": {"SCREEN_EVAL": []},
            "screens": [
                self._construir_screen(
                    screen_id="SCREEN_EVAL",
                    title=f"Avaliação - {hospital}",
                    children=[
                        self._construir_componente_radio(
                            name="nota_geral",
                            label="Como foi o plantão?",
                            options=[
                                {"id": "5", "title": "⭐⭐⭐⭐⭐ Excelente"},
                                {"id": "4", "title": "⭐⭐⭐⭐ Bom"},
                                {"id": "3", "title": "⭐⭐⭐ Regular"},
                                {"id": "2", "title": "⭐⭐ Ruim"},
                                {"id": "1", "title": "⭐ Péssimo"},
                            ],
                        ),
                        self._construir_componente_checkbox(
                            name="aspectos_positivos",
                            label="Pontos positivos",
                            options=[
                                {"id": "estrutura", "title": "Boa estrutura"},
                                {"id": "equipe", "title": "Equipe acolhedora"},
                                {"id": "organizacao", "title": "Bem organizado"},
                                {"id": "pagamento", "title": "Pagamento em dia"},
                            ],
                        ),
                        self._construir_componente_text_input(
                            name="comentario",
                            label="Comentário adicional",
                            required=False,
                        ),
                    ],
                    cta_text="Enviar avaliação",
                    is_terminal=True,
                ),
            ],
        }

    def _construir_screen(
        self,
        screen_id: str,
        title: str,
        children: list,
        cta_text: str = "Próximo",
        next_screen: Optional[str] = None,
        is_terminal: bool = False,
    ) -> dict:
        """Constrói definição de uma screen."""
        screen = {
            "id": screen_id,
            "title": title,
            "layout": {"type": "SingleColumnLayout", "children": children},
        }
        if is_terminal:
            screen["terminal"] = True
        if cta_text:
            footer = {"type": "Footer", "label": cta_text}
            if next_screen:
                footer["on-click-action"] = {
                    "name": "navigate",
                    "next": {"type": "screen", "name": next_screen},
                }
            else:
                footer["on-click-action"] = {"name": "complete"}
            screen["layout"]["children"].append(footer)
        return screen

    def _construir_componente_text_input(
        self,
        name: str,
        label: str,
        required: bool = True,
        helper_text: Optional[str] = None,
        input_type: str = "text",
    ) -> dict:
        """Constrói componente TextInput."""
        component = {
            "type": "TextInput",
            "name": name,
            "label": label,
            "required": required,
            "input-type": input_type,
        }
        if helper_text:
            component["helper-text"] = helper_text
        return component

    def _construir_componente_dropdown(
        self,
        name: str,
        label: str,
        options: List[dict],
        required: bool = True,
    ) -> dict:
        """Constrói componente Dropdown."""
        return {
            "type": "Dropdown",
            "name": name,
            "label": label,
            "required": required,
            "data-source": options,
        }

    def _construir_componente_radio(
        self,
        name: str,
        label: str,
        options: List[dict],
    ) -> dict:
        """Constrói componente RadioButtonsGroup."""
        return {
            "type": "RadioButtonsGroup",
            "name": name,
            "label": label,
            "data-source": options,
        }

    def _construir_componente_checkbox(
        self,
        name: str,
        label: str,
        options: List[dict],
    ) -> dict:
        """Constrói componente CheckboxGroup."""
        return {
            "type": "CheckboxGroup",
            "name": name,
            "label": label,
            "data-source": options,
        }


# Singleton
flow_builder = FlowBuilder()
