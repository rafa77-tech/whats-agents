"""
Testes exaustivos de detecção de opt-out.
Cobre todos os casos positivos e negativos.
"""
import pytest
from app.services.optout import detectar_optout

# Mensagens que DEVEM ser detectadas como opt-out
CASOS_OPTOUT_POSITIVO = [
    # Variações diretas
    "Para de me mandar mensagem",
    "para de mandar msg",
    "PARA DE ME MANDAR MENSAGEM",
    "Para de me mandar essas mensagens por favor",
    
    # "Não quero"
    "Não quero mais receber mensagens",
    "nao quero receber isso",
    "não quero mais nada",
    
    # "Remove da lista"
    "Me remove da lista",
    "me tira dessa lista",
    "exclui meu numero",
    "remove meu contato",
    
    # Comandos curtos
    "STOP",
    "stop",
    "SAIR",
    "parar",
    "cancelar",
    
    # Variações com grosseria
    "Sai fora",
    "SAI FORA",
    "chega",
    "bloqueia",
    
    # Com contexto
    "olha, não quero mais receber mensagem nenhuma",
    "por favor para de me mandar essas coisas",
    "já falei pra parar de mandar",
]

# Mensagens que NÃO devem ser detectadas como opt-out
CASOS_OPTOUT_NEGATIVO = [
    # Mensagens normais
    "Oi, tudo bem?",
    "Tenho interesse em plantão",
    "Qual o valor?",
    
    # Falsos positivos potenciais
    "Para quando é o plantão?",
    "Vou parar de trabalhar amanhã",
    "Quero parar pra almoçar",
    "Não quero esse horário, tem outro?",
    "Remove a vaga de sábado, peguei outra",
    "Me manda mais informações",
    "Para mim tá bom",
    "Quero sair mais cedo do plantão",
    "Vou sair às 19h",
    "Cancela a reserva de sexta",  # Cancelar vaga, não opt-out
    "Bloqueia minha agenda dia 15",  # Bloquear data, não opt-out
]


@pytest.mark.parametrize("mensagem", CASOS_OPTOUT_POSITIVO)
def test_detecta_optout(mensagem):
    """Cada mensagem de opt-out deve ser detectada."""
    resultado, _ = detectar_optout(mensagem)
    assert resultado == True, f"Não detectou opt-out em: '{mensagem}'"


@pytest.mark.parametrize("mensagem", CASOS_OPTOUT_NEGATIVO)
def test_nao_detecta_falso_positivo(mensagem):
    """Mensagens normais não devem ser detectadas como opt-out."""
    resultado, _ = detectar_optout(mensagem)
    assert resultado == False, f"Falso positivo em: '{mensagem}'"

