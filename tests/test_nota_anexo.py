import pytest

from tools.nota_anexo import DescricaoAnexo, NotaAnexo


@pytest.fixture
def nota():
    return NotaAnexo()


# ---------------- DescricaoAnexo ----------------

@pytest.mark.parametrize("nome,formato,tipo", [
    ("A Arte da Guerra.pdf", "PDF", "pdf"),
    ("foto.PNG", "PNG", "imagem"),
    ("aula.mp4", "MP4", "video"),
    ("main.py", "PY", "codigo"),
    ("notas.txt", "TXT", "texto"),
    ("Makefile", "ARQ", "outro"),
    ("arquivo.xyz", "XYZ", "outro"),
])
def test_formato_e_tipo(nome, formato, tipo):
    d = DescricaoAnexo(nome)
    assert d.formato == formato and d.tipo == tipo


def test_linha_de_detalhe():
    assert DescricaoAnexo("a.pdf").linha_detalhe == "PDF"
    assert DescricaoAnexo("a.pdf", "128 página(s)").linha_detalhe == "PDF · 128 página(s)"


# ---------------- NotaAnexo ----------------

def test_montar_mantem_o_formato_lido_pelo_modelo(nota):
    assert nota.montar(["a.pdf (12 página(s))", "b.png"]) == (
        "[2 arquivo(s) anexado(s): a.pdf (12 página(s)), b.png]"
    )


def test_anexar_ao_texto(nota):
    assert nota.anexar_ao_texto("resuma", ["a.pdf"]) == (
        "resuma\n\n[1 arquivo(s) anexado(s): a.pdf]"
    )
    assert nota.anexar_ao_texto("", ["a.pdf"]) == "[1 arquivo(s) anexado(s): a.pdf]"
    assert nota.anexar_ao_texto("oi", []) == "oi"


def test_separar_o_caso_da_captura_de_tela(nota):
    texto, itens = nota.separar(
        "[1 arquivo(s) anexado(s): A Arte da Guerra.pdf (128 página(s))]"
    )
    assert texto == ""
    assert [(i.nome, i.detalhe) for i in itens] == [
        ("A Arte da Guerra.pdf", "128 página(s)")
    ]


def test_separar_texto_e_varios_arquivos(nota):
    original = nota.anexar_ao_texto(
        "compare os dois",
        [
            "contrato.pdf (PDF escaneado, 3 página(s) lida(s), 2 ignorada(s) por limite)",
            "foto.png",
            "aula.mp4 (vídeo — 4 frame(s) de amostra, sem áudio)",
        ],
    )
    texto, itens = nota.separar(original)
    assert texto == "compare os dois"
    assert [i.nome for i in itens] == ["contrato.pdf", "foto.png", "aula.mp4"]
    assert itens[0].detalhe == "escaneado, 3 página(s) lida(s), 2 ignorada(s) por limite"
    assert itens[1].detalhe is None
    assert itens[2].detalhe == "vídeo — 4 frame(s) de amostra, sem áudio"


@pytest.mark.parametrize("nome", [
    "relatorio (1).pdf",
    "v1.2 final.pdf",
    "Relatório, versão final.pdf",
])
def test_nomes_dificeis(nota, nome):
    texto, itens = nota.separar(
        nota.anexar_ao_texto("", [f"{nome} (5 página(s))", "b.txt"])
    )
    assert [i.nome for i in itens] == [nome, "b.txt"]
    assert itens[0].detalhe == "5 página(s)"


def test_arquivo_sem_extensao_nao_quebra(nota):
    _, itens = nota.separar("[1 arquivo(s) anexado(s): Makefile]")
    assert itens[0].nome == "Makefile" and itens[0].formato == "ARQ"


@pytest.mark.parametrize("texto", [
    "oi, tudo bem?",
    "",
    "[1 arquivo(s) anexado(s): a.pdf] e depois mais texto",
])
def test_sem_nota_no_fim_nao_muda_nada(nota, texto):
    assert nota.separar(texto) == (texto, [])
