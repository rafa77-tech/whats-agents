"""
Testes para FlowBuilder.

Sprint 68 — Epic 68.2, Chunk 5.
"""

import pytest


class TestFlowBuilder:

    def test_construir_flow_onboarding(self):
        from app.services.meta.flow_builder import FlowBuilder

        builder = FlowBuilder()
        flow = builder.construir_flow_onboarding()
        assert flow["version"] == "7.0"
        assert len(flow["screens"]) == 2
        assert flow["screens"][0]["id"] == "SCREEN_1"
        assert flow["screens"][1]["id"] == "SCREEN_2"

    def test_construir_flow_confirmacao_plantao(self):
        from app.services.meta.flow_builder import FlowBuilder

        builder = FlowBuilder()
        vaga = {"hospital": "São Luiz", "data": "15/03", "horario": "19h-7h", "valor": "2500"}
        flow = builder.construir_flow_confirmacao_plantao(vaga)
        assert flow["version"] == "7.0"
        assert len(flow["screens"]) == 1
        assert flow["screens"][0]["id"] == "SCREEN_CONFIRM"

    def test_construir_flow_avaliacao(self):
        from app.services.meta.flow_builder import FlowBuilder

        builder = FlowBuilder()
        vaga = {"hospital": "Albert Einstein"}
        flow = builder.construir_flow_avaliacao_pos_plantao(vaga)
        assert flow["version"] == "7.0"
        assert "Albert Einstein" in flow["screens"][0]["title"]

    def test_construir_screen_terminal(self):
        from app.services.meta.flow_builder import FlowBuilder

        builder = FlowBuilder()
        screen = builder._construir_screen(
            screen_id="S1", title="Test", children=[], cta_text="OK", is_terminal=True
        )
        assert screen["terminal"] is True
        assert screen["id"] == "S1"

    def test_construir_componente_text_input(self):
        from app.services.meta.flow_builder import FlowBuilder

        builder = FlowBuilder()
        comp = builder._construir_componente_text_input("nome", "Nome completo", helper_text="Ex: Dr João")
        assert comp["type"] == "TextInput"
        assert comp["name"] == "nome"
        assert comp["helper-text"] == "Ex: Dr João"

    def test_construir_componente_dropdown(self):
        from app.services.meta.flow_builder import FlowBuilder

        builder = FlowBuilder()
        comp = builder._construir_componente_dropdown(
            "esp", "Especialidade", [{"id": "1", "title": "Cardio"}]
        )
        assert comp["type"] == "Dropdown"
        assert len(comp["data-source"]) == 1

    def test_construir_componente_radio(self):
        from app.services.meta.flow_builder import FlowBuilder

        builder = FlowBuilder()
        comp = builder._construir_componente_radio(
            "opcao", "Escolha", [{"id": "a", "title": "A"}, {"id": "b", "title": "B"}]
        )
        assert comp["type"] == "RadioButtonsGroup"

    def test_construir_componente_checkbox(self):
        from app.services.meta.flow_builder import FlowBuilder

        builder = FlowBuilder()
        comp = builder._construir_componente_checkbox(
            "items", "Selecione", [{"id": "x", "title": "X"}]
        )
        assert comp["type"] == "CheckboxGroup"
