"""
Testes do parser de markdown.
"""
import pytest
from pathlib import Path
from app.services.conhecimento.indexador import ParserMarkdown, ChunkConhecimento


@pytest.fixture
def parser():
    return ParserMarkdown()


class TestParserMarkdown:
    """Testes do parser."""

    def test_tipo_por_arquivo(self, parser):
        """Mapeia arquivo para tipo correto."""
        assert parser.TIPO_POR_ARQUIVO["guia_adaptacao_perfis_medicos.md"] == "perfil"
        assert parser.TIPO_POR_ARQUIVO["julia_catalogo_objecoes_respostas.md"] == "objecao"
        assert parser.TIPO_POR_ARQUIVO["3_erros_criticos_medicos_senior.md"] == "erro"

    def test_dividir_por_secoes(self, parser):
        """Divide conteúdo por headers H2."""
        conteudo = """# Título

Introdução aqui.

## Seção 1

Conteúdo da seção 1.

## Seção 2

Conteúdo da seção 2.
"""
        secoes = parser._dividir_por_secoes(conteudo)

        assert len(secoes) >= 2
        titulos = [s[0] for s in secoes]
        assert "Seção 1" in titulos
        assert "Seção 2" in titulos

    def test_dividir_em_chunks_pequeno(self, parser):
        """Texto pequeno não é dividido."""
        texto = "Texto curto que cabe em um chunk."
        chunks = parser._dividir_em_chunks(texto)

        assert len(chunks) == 1
        assert chunks[0] == texto

    def test_dividir_em_chunks_grande(self, parser):
        """Texto grande é dividido em partes."""
        # Criar texto grande com múltiplos parágrafos menores
        paragrafo = "Este é um parágrafo de teste com conteúdo suficiente. " * 10
        # 10 parágrafos separados por \n\n
        texto = "\n\n".join([paragrafo for _ in range(10)])

        chunks = parser._dividir_em_chunks(texto)

        # Deve dividir em mais de 1 chunk
        assert len(chunks) > 1
        # E produzir chunks razoáveis (não valida max porque parágrafos individuais podem ser grandes)

    def test_detectar_subtipo_perfil_senior(self, parser):
        """Detecta perfil sênior."""
        subtipo = parser._detectar_subtipo(
            "PERFIL 4: MÉDICO SÊNIOR (15+ anos)",
            "Médicos sênior têm autonomia...",
            "perfil",
        )
        assert subtipo == "senior"

    def test_detectar_subtipo_perfil_recem_formado(self, parser):
        """Detecta perfil recém-formado."""
        subtipo = parser._detectar_subtipo(
            "PERFIL 1: RECÉM-FORMADO",
            "Médicos com 0-2 anos de experiência...",
            "perfil",
        )
        assert subtipo == "recem_formado"

    def test_detectar_subtipo_objecao_preco(self, parser):
        """Detecta objeção de preço."""
        subtipo = parser._detectar_subtipo(
            "Objeção 1: Valor baixo",
            "O médico reclama do valor pago...",
            "objecao",
        )
        assert subtipo == "preco"

    def test_detectar_subtipo_objecao_tempo(self, parser):
        """Detecta objeção de tempo."""
        subtipo = parser._detectar_subtipo(
            "Objeção: Agenda cheia",
            "Médico diz que está ocupado e não tem tempo...",
            "objecao",
        )
        assert subtipo == "tempo"

    def test_extrair_tags(self, parser):
        """Extrai tags do conteúdo."""
        tags = parser._extrair_tags(
            "Como negociar", "✅ CORRETO: Exemplo de negociação...", "objecao"
        )

        assert "objecao" in tags
        assert "negociacao" in tags
        assert "bom_exemplo" in tags

    def test_extrair_tags_senior(self, parser):
        """Extrai tag senior do conteúdo."""
        tags = parser._extrair_tags(
            "Abordagem", "Médicos sênior precisam de respeito...", "perfil"
        )

        assert "perfil" in tags
        assert "senior" in tags


class TestParserArquivoReal:
    """Testes com arquivos reais (se existirem)."""

    @pytest.fixture
    def parser(self):
        return ParserMarkdown()

    def test_parsear_arquivo_abertura(self, parser):
        """Parseia arquivo de mensagens de abertura."""
        path = Path("docs/julia/MENSAGENS_ABERTURA.md")
        if not path.exists():
            pytest.skip("Arquivo não encontrado")

        chunks = parser.parsear_arquivo(path)

        assert len(chunks) > 0
        assert all(isinstance(c, ChunkConhecimento) for c in chunks)
        assert all(c.tipo == "abertura" for c in chunks)

    def test_parsear_arquivo_objecoes(self, parser):
        """Parseia catálogo de objeções."""
        path = Path("docs/julia/julia_catalogo_objecoes_respostas.md")
        if not path.exists():
            pytest.skip("Arquivo não encontrado")

        chunks = parser.parsear_arquivo(path)

        assert len(chunks) > 10  # Arquivo grande
        assert all(c.tipo == "objecao" for c in chunks)
        # Deve ter alguns com subtipo detectado
        subtipos = [c.subtipo for c in chunks if c.subtipo]
        assert len(subtipos) > 0

    def test_chunks_tem_tamanho_adequado(self, parser):
        """Chunks respeitam limites de tamanho."""
        path = Path("docs/julia/julia_catalogo_objecoes_respostas.md")
        if not path.exists():
            pytest.skip("Arquivo não encontrado")

        chunks = parser.parsear_arquivo(path)

        for chunk in chunks:
            assert len(chunk.conteudo) >= parser.CHUNK_SIZE_MIN
            # Margem de 200 chars para casos edge
            assert len(chunk.conteudo) <= parser.CHUNK_SIZE_MAX + 200
