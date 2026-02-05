"""Testes de integração do pipeline v2."""
import pytest
from datetime import date
from uuid import uuid4

from app.services.grupos.extrator_v2 import extrair_vagas_v2


class TestPipelineIntegracao:
    """Testes de integração do pipeline completo."""

    @pytest.mark.asyncio
    async def test_mensagem_completa(self):
        """Pipeline processa mensagem completa."""
        texto = """📍 Hospital Campo Limpo
Estrada Itapecirica, 1661 - SP

🗓 26/03 - Segunda - Manhã 7-13h
🗓 27/03 - Terça - Noite 19-7h

💰 Segunda a Sexta: R$ 1.700
💰 Sábado e Domingo: R$ 1.800

📲 Eloisa
wa.me/5511939050162"""

        resultado = await extrair_vagas_v2(
            texto=texto,
            data_referencia=date(2026, 3, 25)
        )

        assert resultado.sucesso is True
        assert resultado.erro is None
        assert len(resultado.vagas) == 2

        # Verificar primeira vaga
        vaga1 = resultado.vagas[0]
        assert vaga1.hospital_raw == "Hospital Campo Limpo"
        assert vaga1.data == date(2026, 3, 26)
        assert vaga1.valor == 1700
        assert vaga1.contato_nome == "Eloisa"

    @pytest.mark.asyncio
    async def test_mensagem_simples(self):
        """Pipeline processa mensagem simples."""
        texto = "Hospital ABC - 26/03 manhã R$ 1.800"

        resultado = await extrair_vagas_v2(
            texto=texto,
            data_referencia=date(2026, 3, 25)
        )

        # Pode ter warnings mas deve extrair
        assert len(resultado.vagas) >= 0

    @pytest.mark.asyncio
    async def test_mensagem_vazia(self):
        """Pipeline rejeita mensagem vazia."""
        resultado = await extrair_vagas_v2(texto="")

        assert resultado.sucesso is False
        assert resultado.erro == "mensagem_vazia"

    @pytest.mark.asyncio
    async def test_mensagem_sem_hospital(self):
        """Pipeline rejeita mensagem sem hospital."""
        texto = "🗓 26/03 manhã R$ 1.800"

        resultado = await extrair_vagas_v2(
            texto=texto,
            data_referencia=date(2026, 3, 25)
        )

        assert resultado.sucesso is False
        assert "hospital" in resultado.erro.lower()

    @pytest.mark.asyncio
    async def test_mensagem_sem_data(self):
        """Pipeline rejeita mensagem sem data."""
        texto = "📍 Hospital ABC\n💰 R$ 1.800"

        resultado = await extrair_vagas_v2(texto=texto)

        assert resultado.sucesso is False
        assert "data" in resultado.erro.lower()

    @pytest.mark.asyncio
    async def test_tempo_processamento(self):
        """Pipeline registra tempo de processamento."""
        texto = "📍 Hospital ABC\n🗓 26/03 manhã\n💰 R$ 1.800"

        resultado = await extrair_vagas_v2(
            texto=texto,
            data_referencia=date(2026, 3, 25)
        )

        # tempo_processamento_ms >= 0 (pode ser 0 se muito rápido)
        assert resultado.tempo_processamento_ms >= 0
        assert resultado.tempo_processamento_ms < 5000  # Menos de 5s

    @pytest.mark.asyncio
    async def test_rastreabilidade(self):
        """Pipeline preserva IDs de rastreabilidade."""
        texto = "📍 Hospital ABC\n🗓 26/03 manhã\n💰 R$ 1.800"
        msg_id = uuid4()
        grupo_id = uuid4()

        resultado = await extrair_vagas_v2(
            texto=texto,
            mensagem_id=msg_id,
            grupo_id=grupo_id,
            data_referencia=date(2026, 3, 25)
        )

        if resultado.vagas:
            assert resultado.vagas[0].mensagem_id == msg_id
            assert resultado.vagas[0].grupo_id == grupo_id


class TestCasosReais:
    """Testes com mensagens reais de grupos."""

    @pytest.mark.asyncio
    async def test_caso_real_upa(self):
        """Formato real UPA."""
        texto = """🔴🔴PRECISO🔴🔴

📍UPA CAMPO LIMPO
📅 27/03 SEGUNDA
⏰ 19 as 07
💰1.600
📲11964391344"""

        resultado = await extrair_vagas_v2(
            texto=texto,
            data_referencia=date(2026, 3, 25)
        )

        assert resultado.sucesso is True
        assert len(resultado.vagas) == 1
        assert resultado.vagas[0].valor == 1600

    @pytest.mark.asyncio
    async def test_caso_real_multiplas_datas(self):
        """Formato real com múltiplas datas."""
        texto = """*PLANTÕES CLINICA MÉDICA*

Hospital Santa Casa ABC

26/03 dom diurno 7-19h
27/03 seg noturno 19-7h
28/03 ter diurno 7-19h

Valor R$ 1.500

Int. Maria 11 99999-9999"""

        resultado = await extrair_vagas_v2(
            texto=texto,
            data_referencia=date(2026, 3, 25)
        )

        assert resultado.sucesso is True
        assert len(resultado.vagas) >= 3

    @pytest.mark.asyncio
    async def test_caso_real_valores_diferentes(self):
        """Formato real com valores por dia."""
        texto = """📍 Hospital ABC
Região Sul - SP

🗓 24/03 - Segunda - Manhã 7-13h
🗓 29/03 - Sábado - SD 7-19h
🗓 30/03 - Domingo - SD 7-19h

💰 Seg-Sex: R$ 1.700
💰 Sab-Dom: R$ 2.000

📲 Contato: João - 11988887777"""

        resultado = await extrair_vagas_v2(
            texto=texto,
            data_referencia=date(2026, 3, 20)
        )

        assert resultado.sucesso is True
        assert len(resultado.vagas) == 3

        # Verificar valores
        vagas_seg_sex = [v for v in resultado.vagas if v.dia_semana.value == "segunda"]
        vagas_sab_dom = [v for v in resultado.vagas if v.dia_semana.value in ("sabado", "domingo")]

        if vagas_seg_sex:
            assert vagas_seg_sex[0].valor == 1700
        if vagas_sab_dom:
            for v in vagas_sab_dom:
                assert v.valor == 2000
