"""
Pacote de Bounded Contexts do Projeto Julia.

Este pacote organiza o código por contexto de domínio, seguindo os
princípios do Domain-Driven Design (DDD). Cada subpacote representa
um Bounded Context com suas próprias camadas de:

- application.py: Application Services (orquestração de casos de uso)
- Repositórios: reutiliza os existentes em app/services/*/repository.py
- Tipos de domínio: reutiliza os existentes em app/services/*/types.py

Referência: ADR-006 (Bounded Contexts) e ADR-007 (Sem SQL em Rotas)
"""
