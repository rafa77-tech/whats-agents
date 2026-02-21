"""
Bounded Context: Campanhas Outbound

Responsabilidade: Segmentação, execução e enfileiramento de campanhas
proativas de comunicação com médicos.

Camadas:
- application.py: Application Service (orquestração dos casos de uso)
- Repositório: app/services/campanhas/repository.py (fonte única de persistência)
- Tipos de domínio: app/services/campanhas/types.py

Referência: ADR-006, ADR-007, ADR-008
"""
