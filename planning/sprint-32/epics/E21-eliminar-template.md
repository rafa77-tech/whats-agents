# E21 - Eliminar o Termo "Template"

**Sprint:** 32 - Redesign de Campanhas e Comportamento Julia
**Fase:** 6 - Limpeza e Polish
**Dependências:** E14 (Reestruturar Campanhas)
**Estimativa:** 4h

---

## Objetivo

Eliminar completamente o termo "template" do código, conceitos e documentação. Julia gera mensagens dinamicamente - não usa templates.

---

## Contexto

O sistema foi construído com mentalidade de templates:
- 424 ocorrências da palavra "template" no código
- Tabela `campanhas` tem campo `nome_template`
- Diretório `app/templates/` com fragmentos pré-escritos
- Conceitos como "template de abertura"

Isso é conceitualmente errado. Julia gera cada mensagem de forma única.

---

## Levantamento Atual

```bash
# Contagem por tipo
grep -r "template" app/ --include="*.py" | wc -l  # ~150
grep -r "Template" app/ --include="*.py" | wc -l  # ~200
grep -r "TEMPLATE" app/ --include="*.py" | wc -l  # ~50
```

**Principais locais:**
1. `app/templates/` - Diretório inteiro
2. `app/services/abertura.py` - Geração de abertura
3. `app/services/campanhas/` - Serviços de campanha
4. `app/api/routes/campanhas.py` - Endpoints
5. Testes em `tests/`

---

## Tasks

### T1: Mapear todas as ocorrências (30min)

**Script:** `scripts/mapear_templates.py`

```python
"""
Script para mapear todas as ocorrências de 'template' no código.

Gera relatório com arquivo, linha e contexto.
"""
import os
import re
from pathlib import Path

DIRETÓRIOS = ["app", "tests"]
EXTENSÕES = [".py", ".md"]
PADRÕES = [
    r"template",
    r"Template",
    r"TEMPLATE",
]


def buscar_ocorrencias():
    resultados = []

    for diretorio in DIRETÓRIOS:
        for root, _, files in os.walk(diretorio):
            for file in files:
                if not any(file.endswith(ext) for ext in EXTENSÕES):
                    continue

                filepath = Path(root) / file

                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        for i, linha in enumerate(f, 1):
                            for padrao in PADRÕES:
                                if re.search(padrao, linha):
                                    resultados.append({
                                        "arquivo": str(filepath),
                                        "linha": i,
                                        "conteudo": linha.strip()[:100],
                                        "padrao": padrao
                                    })
                except Exception as e:
                    print(f"Erro ao ler {filepath}: {e}")

    return resultados


def gerar_relatorio(resultados):
    print(f"Total de ocorrências: {len(resultados)}\n")

    # Agrupar por arquivo
    por_arquivo = {}
    for r in resultados:
        if r["arquivo"] not in por_arquivo:
            por_arquivo[r["arquivo"]] = []
        por_arquivo[r["arquivo"]].append(r)

    for arquivo, ocorrencias in sorted(por_arquivo.items()):
        print(f"\n{arquivo} ({len(ocorrencias)} ocorrências)")
        for o in ocorrencias[:5]:  # Mostrar até 5 por arquivo
            print(f"  L{o['linha']}: {o['conteudo']}")
        if len(ocorrencias) > 5:
            print(f"  ... e mais {len(ocorrencias) - 5}")


if __name__ == "__main__":
    resultados = buscar_ocorrencias()
    gerar_relatorio(resultados)
```

---

### T2: Renomear diretório app/templates (45min)

O diretório `app/templates/` contém fragmentos de abertura. Renomear para `app/fragmentos/` ou eliminar completamente.

**Antes:**
```
app/templates/
├── aberturas.py
├── saudacoes.py
└── apresentacoes.py
```

**Depois:**
```
app/fragmentos/  # Ou eliminar se não for mais usado
├── abertura_examples.py  # Apenas exemplos para LLM
```

**Comandos:**
```bash
# Renomear diretório
git mv app/templates app/fragmentos

# Atualizar imports em todos os arquivos
find app -name "*.py" -exec sed -i '' 's/from app\.templates/from app.fragmentos/g' {} \;
find app -name "*.py" -exec sed -i '' 's/import app\.templates/import app.fragmentos/g' {} \;
```

---

### T3: Renomear classes e funções (1h)

**Renomeações principais:**

| Antes | Depois |
|-------|--------|
| `TemplateAbertura` | `FragmentoAbertura` ou eliminar |
| `TemplateCampanha` | `ComportamentoCampanha` |
| `nome_template` | `nome` (já feito em E14) |
| `template_sid` | Remover (era Twilio) |
| `selecionar_template()` | `definir_comportamento()` |
| `aplicar_template()` | `aplicar_regras()` |

**Script de renomeação:**

```python
"""
Script para renomear ocorrências de template.
"""
import os
import re

RENOMEACOES = [
    # Classes
    (r"class TemplateAbertura", "class FragmentoAbertura"),
    (r"TemplateAbertura\(", "FragmentoAbertura("),
    (r"class TemplateCampanha", "class ComportamentoCampanha"),
    (r"TemplateCampanha\(", "ComportamentoCampanha("),

    # Variáveis
    (r"nome_template", "nome"),
    (r"template_id", "comportamento_id"),
    (r"template_sid", ""),  # Remover

    # Funções
    (r"def selecionar_template\(", "def definir_comportamento("),
    (r"selecionar_template\(", "definir_comportamento("),
    (r"def aplicar_template\(", "def aplicar_regras("),
    (r"aplicar_template\(", "aplicar_regras("),
]

def renomear_arquivo(filepath: str) -> int:
    """Renomeia ocorrências em um arquivo."""
    with open(filepath, "r", encoding="utf-8") as f:
        conteudo = f.read()

    conteudo_original = conteudo
    alteracoes = 0

    for padrao, substituto in RENOMEACOES:
        novo_conteudo = re.sub(padrao, substituto, conteudo)
        if novo_conteudo != conteudo:
            alteracoes += 1
            conteudo = novo_conteudo

    if conteudo != conteudo_original:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(conteudo)

    return alteracoes


def main():
    total = 0
    for root, _, files in os.walk("app"):
        for file in files:
            if file.endswith(".py"):
                filepath = os.path.join(root, file)
                alteracoes = renomear_arquivo(filepath)
                if alteracoes:
                    print(f"{filepath}: {alteracoes} alterações")
                    total += alteracoes

    print(f"\nTotal: {total} alterações")


if __name__ == "__main__":
    main()
```

---

### T4: Atualizar testes (1h)

Testes que referenciam "template" precisam ser atualizados.

**Arquivo:** `tests/campanhas/test_comportamento.py` (renomear de test_template.py)

```python
"""
Testes para comportamento de campanhas.

NOTA: Este arquivo foi renomeado de test_template.py
"""
import pytest
from app.services.campanhas.comportamento import (
    ComportamentoCampanha,
    definir_comportamento,
)


class TestComportamentoCampanha:
    """Testes para ComportamentoCampanha."""

    def test_comportamento_discovery(self):
        """Discovery não permite oferta proativa."""
        comportamento = ComportamentoCampanha(tipo="discovery")

        assert comportamento.pode_ofertar is False
        assert "vagas" not in comportamento.regras_str.lower()

    def test_comportamento_oferta(self):
        """Oferta permite oferta proativa."""
        comportamento = ComportamentoCampanha(tipo="oferta")

        assert comportamento.pode_ofertar is True


class TestDefinirComportamento:
    """Testes para definir_comportamento()."""

    def test_retorna_comportamento_correto(self):
        """Retorna comportamento baseado no tipo."""
        resultado = definir_comportamento(tipo="followup")

        assert resultado.tipo == "followup"
        assert len(resultado.regras) > 0
```

---

### T5: Atualizar documentação (45min)

Atualizar CLAUDE.md, docs/ e README.md.

**Alterações em CLAUDE.md:**

```markdown
# Remover seção "Templates de Campanha"
# Adicionar seção "Comportamentos de Campanha"

## Comportamentos de Campanha

Julia opera com 5 tipos de comportamento:

| Tipo | Descrição | Pode Ofertar |
|------|-----------|--------------|
| discovery | Conhecer médicos | Não |
| oferta | Apresentar vagas | Sim |
| followup | Manter relacionamento | Não |
| feedback | Coletar opinião | Não |
| reativacao | Retomar inativos | Não |

Cada comportamento define:
- Objetivo em linguagem natural
- Regras específicas
- Permissão de oferta
```

**Alterações em docs/:**

```bash
# Renomear arquivos
git mv docs/julia/templates.md docs/julia/comportamentos.md

# Atualizar referências
find docs -name "*.md" -exec sed -i '' 's/template/comportamento/g' {} \;
```

---

### T6: Verificação final (15min)

Rodar grep para garantir que não restou nenhum "template" indevido.

```bash
# Buscar ocorrências restantes
grep -r "template" app/ --include="*.py"

# Permitidos (não precisa alterar):
# - Comentários explicando a mudança
# - Strings que mencionam "template" historicamente
# - Nomes de bibliotecas externas (jinja2 template, etc.)

# Não permitidos:
# - Nome de classes
# - Nome de variáveis
# - Nome de funções
# - Nome de arquivos
```

---

## DoD (Definition of Done)

### Código
- [ ] Diretório `app/templates/` renomeado ou removido
- [ ] Classes renomeadas (Template* → Comportamento*/Fragmento*)
- [ ] Funções renomeadas (selecionar_template → definir_comportamento)
- [ ] Variáveis renomeadas (nome_template → nome)
- [ ] Imports atualizados em todos os arquivos

### Testes
- [ ] Arquivos de teste renomeados
- [ ] Referências atualizadas
- [ ] `uv run pytest` passando

### Documentação
- [ ] CLAUDE.md atualizado
- [ ] Arquivos em docs/ renomeados
- [ ] Referências em docs/ atualizadas

### Verificação
- [ ] `grep -r "template" app/ --include="*.py"` retorna apenas permitidos
- [ ] Nenhuma classe chamada `*Template*`
- [ ] Nenhuma função chamada `*_template*`

### Verificação Manual

1. **Buscar ocorrências:**
   ```bash
   grep -rn "template" app/ --include="*.py" | grep -v "#"
   ```
   Deve retornar vazio ou apenas comentários.

2. **Verificar imports:**
   ```bash
   grep -rn "from app.templates" app/
   ```
   Deve retornar vazio.

3. **Rodar testes:**
   ```bash
   uv run pytest tests/
   ```
   Todos devem passar.

---

## Notas para Dev

1. **Cuidado com dependências:** Verificar se alguma biblioteca externa usa "template"
2. **Commits incrementais:** Fazer commit após cada task para facilitar rollback
3. **Busca case-insensitive:** Usar `-i` no grep para pegar Template, TEMPLATE, etc.
4. **Testes antes de commitar:** Rodar pytest após cada mudança significativa

---

## Palavras Permitidas

Estas ocorrências de "template" são aceitáveis:

1. **Comentários explicativos:**
   ```python
   # NOTA: Anteriormente chamado de template, agora é comportamento
   ```

2. **Strings de log/erro:**
   ```python
   logger.info("Migrado de sistema de templates para comportamentos")
   ```

3. **Bibliotecas externas:**
   ```python
   from jinja2 import Template  # Biblioteca externa
   ```

4. **Referências históricas em docs:**
   ```markdown
   > Histórico: Sistema antigo usava templates (Sprint 1-31)
   ```

---

## Métricas de Sucesso

| Métrica | Meta |
|---------|------|
| Ocorrências de "template" em código | 0 |
| Classes com "Template" | 0 |
| Funções com "template" | 0 |
| Testes passando | 100% |
