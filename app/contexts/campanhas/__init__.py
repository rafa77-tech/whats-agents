"""
Bounded Context: Campanhas Outbound

Responsabilidade: Segmentação, execução e enfileiramento de campanhas
proativas de comunicação com médicos.

Camadas:
- domain.py: Modelos de domínio (CampanhaData, AudienceFilters, etc.)
- application.py: Application Service (orquestração dos casos de uso)
- repositories.py: Repositórios (acesso isolado ao Supabase)

Referência: ADR-006, ADR-007, ADR-008
"""
