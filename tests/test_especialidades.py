"""
Testes para múltiplas especialidades.
"""
import pytest
from app.config.especialidades import CONFIGURACOES_ESPECIALIDADE, obter_config_especialidade
from app.services.contexto import montar_contexto_especialidade


@pytest.mark.parametrize("especialidade", CONFIGURACOES_ESPECIALIDADE.keys())
def test_config_especialidade_existe(especialidade):
    """Testa que configuração existe para cada especialidade."""
    config = obter_config_especialidade(especialidade)
    assert config, f"Configuração não encontrada para {especialidade}"
    assert "nome_display" in config
    assert "tipo_plantao" in config
    assert "vocabulario" in config


def test_contexto_especialidade():
    """Testa que contexto de especialidade é gerado corretamente."""
    medico = {
        "especialidade_nome": "anestesiologia"
    }
    
    contexto = montar_contexto_especialidade(medico)
    
    assert contexto
    assert "anestesista" in contexto.lower()
    assert "centro cirúrgico" in contexto.lower()


def test_contexto_especialidade_inexistente():
    """Testa que retorna vazio para especialidade sem configuração."""
    medico = {
        "especialidade_nome": "especialidade_inexistente"
    }
    
    contexto = montar_contexto_especialidade(medico)
    assert contexto == ""


def test_vocabulario_especialidade():
    """Testa que vocabulário está presente na configuração."""
    for especialidade, config in CONFIGURACOES_ESPECIALIDADE.items():
        assert "vocabulario" in config
        assert "setores" in config["vocabulario"]
        assert "procedimentos" in config["vocabulario"]
        assert len(config["vocabulario"]["setores"]) > 0

