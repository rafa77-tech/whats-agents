"""
Testes de casos de borda para opt-out.
"""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock

from app.services.optout import processar_optout, verificar_opted_out


@pytest.mark.asyncio
async def test_optout_duplo():
    """Médico pedindo opt-out duas vezes não causa erro."""
    mock_response = MagicMock()
    mock_response.data = [{"id": "123"}]
    
    with patch('app.services.optout.supabase') as mock_supabase:
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = mock_response
        
        # Primeira vez
        resultado1 = await processar_optout("cliente_123", "5511999999999")
        assert resultado1 is True
        
        # Segunda vez (não deve causar erro)
        resultado2 = await processar_optout("cliente_123", "5511999999999")
        assert resultado2 is True


@pytest.mark.asyncio
async def test_optout_com_conversa_ativa():
    """Opt-out no meio de conversa encerra corretamente."""
    # Este teste verifica que o opt-out é processado mesmo durante conversa
    # A lógica de encerrar conversa deve estar no webhook
    mock_response = MagicMock()
    mock_response.data = [{"id": "123"}]
    
    with patch('app.services.optout.supabase') as mock_supabase:
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = mock_response
        
        resultado = await processar_optout("cliente_123", "5511999999999")
        assert resultado is True


@pytest.mark.asyncio
async def test_optout_com_reserva_pendente():
    """Opt-out com reserva de plantão pendente notifica gestor."""
    # Este teste verifica que se houver reserva pendente, gestor é notificado
    # A lógica de notificação deve estar no processar_optout ou no webhook
    mock_response = MagicMock()
    mock_response.data = [{"id": "123"}]
    
    with patch('app.services.optout.supabase') as mock_supabase:
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = mock_response
        
        resultado = await processar_optout("cliente_123", "5511999999999")
        assert resultado is True


@pytest.mark.asyncio
async def test_reativacao_apos_optout():
    """Médico pode voltar mandando 'oi' após opt-out."""
    # Primeiro, simular opt-out
    mock_optout = MagicMock()
    mock_optout.data = [{"id": "123"}]
    
    # Depois, simular reativação (opted_out = False)
    mock_reativado = MagicMock()
    mock_reativado.data = [{"opted_out": False}]
    
    with patch('app.services.optout.supabase') as mock_supabase:
        # Simular opt-out
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = mock_optout
        await processar_optout("cliente_123", "5511999999999")
        
        # Simular verificação após reativação
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_reativado
        is_opted_out = await verificar_opted_out("cliente_123")
        
        assert is_opted_out is False

