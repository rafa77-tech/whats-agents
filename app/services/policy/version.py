"""
Versionamento do Policy Engine.

REGRAS DE VERSIONAMENTO (SemVer):
- MAJOR (X.0.0): Mudança de comportamento que quebra compatibilidade
- MINOR (1.X.0): Nova regra ou mudança significativa de lógica
- PATCH (1.0.X): Ajuste fino, bugfix, threshold

Sprint 15 - Policy Engine
"""

# Versão atual das regras de decisão
# Incrementar a cada mudança nas regras
POLICY_VERSION = "1.0.0"

# Changelog (para referência)
POLICY_CHANGELOG = {
    "1.0.0": {
        "date": "2025-12-27",
        "changes": [
            "Versão inicial do Policy Engine",
            "9 regras de produção implementadas",
            "rule_opted_out, rule_cooling_off, rule_grave_objection",
            "rule_high_objection, rule_medium_objection",
            "rule_new_doctor_first_contact, rule_silence_reactivation",
            "rule_cold_temperature, rule_hot_temperature, rule_default",
        ],
    },
}


def get_policy_version() -> str:
    """Retorna versão atual da policy."""
    return POLICY_VERSION
