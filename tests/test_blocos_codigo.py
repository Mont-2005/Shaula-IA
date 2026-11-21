import ctypes
import time
from unittest.mock import MagicMock

import pytest

if not hasattr(ctypes, "windll"):
    ctypes.windll = MagicMock()
    ctypes.WinDLL = MagicMock()
    ctypes.WINFUNCTYPE = ctypes.CFUNCTYPE

from PySide6.QtGui import QTextDocument
from PySide6.QtWidgets import QApplication, QLabel

from tools.bloco_codigo import (
    BlocoCodigo,
    CatalogoLinguagens,
    ConteudoMensagemShaula,
    DivisorDeBlocos,
    EditorCodigo,
    FormatadorTextoMensagem,
    RealceSintaxe,
)


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def _tipos(texto):
    return [(s.tipo, s.linguagem) for s in DivisorDeBlocos.dividir(texto)]


# ---------------- divisão em segmentos ----------------

def test_texto_sem_codigo_vira_um_segmento_de_texto():
    segs = DivisorDeBlocos.dividir("Olá!\nTudo bem?")
    assert [(s.tipo, s.conteudo) for s in segs] == [("texto", "Olá!\nTudo bem?")]
    assert not DivisorDeBlocos.tem_codigo("Olá!")


def test_bloco_simples_com_texto_antes_e_depois():
    texto = "Veja:\n\n```python\nprint(1)\n```\n\nPronto."
    segs = DivisorDeBlocos.dividir(texto)
    assert [(s.tipo, s.conteudo, s.linguagem) for s in segs] == [
        ("texto", "Veja:", ""),
        ("codigo", "print(1)", "python"),
        ("texto", "Pronto.", ""),
    ]
    assert DivisorDeBlocos.tem_codigo(texto)


def test_indentacao_e_linhas_em_branco_do_codigo_sao_preservadas():
    codigo = "def f():\n    x = 1\n\n    if x:\n        return x"
    seg = DivisorDeBlocos.dividir(f"```python\n{codigo}\n```")[0]
    assert seg.conteudo == codigo


def test_dois_blocos_em_sequencia():
    texto = "```js\na()\n```\nentre\n```sh\nls\n```"
    assert _tipos(texto) == [("codigo", "js"), ("texto", ""), ("codigo", "sh")]


def test_bloco_sem_linguagem_e_linguagem_em_minusculas():
    assert _tipos("```\nx\n```") == [("codigo", "")]
    assert _tipos("```Python\nx\n```") == [("codigo", "python")]
    assert _tipos("```c++\nx\n```") == [("codigo", "c++")]
    assert _tipos("```c#\nx\n```") == [("codigo", "c#")]


def test_bloco_nao_fechado_vai_ate_o_fim():
    segs = DivisorDeBlocos.dividir("Resposta:\n```python\nprint(1)\nprint(2)")
    assert segs[-1].eh_codigo and segs[-1].conteudo == "print(1)\nprint(2)"


def test_til_e_cerca_mais_longa():
    segs = DivisorDeBlocos.dividir("~~~\na\n~~~")
    assert segs[0].conteudo == "a"
    # cerca de 4 crases pode conter uma linha com 3 crases
    segs = DivisorDeBlocos.dividir("````md\n```\ninterno\n```\n````")
    assert len(segs) == 1 and segs[0].conteudo == "```\ninterno\n```"


def test_cerca_de_tipo_diferente_nao_fecha():
    segs = DivisorDeBlocos.dividir("```\na\n~~~\nb\n```")
    assert segs[0].conteudo == "a\n~~~\nb"


def test_bloco_dentro_de_lista_perde_o_recuo_da_cerca():
    texto = "1. Rode:\n   ```bash\n   ls -la\n     indentado\n   ```\n2. Fim"
    cod = [s for s in DivisorDeBlocos.dividir(texto) if s.eh_codigo][0]
    assert cod.conteudo == "ls -la\n  indentado"


def test_bloco_vazio_e_descartado():
    assert DivisorDeBlocos.dividir("```python\n\n```") == []
    assert not DivisorDeBlocos.tem_codigo("```\n```")


def test_crases_no_meio_da_linha_nao_abrem_bloco():
    texto = "Use ``` para delimitar e ```python x``` assim."
    assert not DivisorDeBlocos.tem_codigo(texto)


def test_quebras_de_linha_do_windows():
    segs = DivisorDeBlocos.dividir("a\r\n```\r\nb\r\n```\r\nc")
    assert [s.conteudo for s in segs] == ["a", "b", "c"]


def test_codigo_com_asteriscos_duplos_nao_e_alterado():
    seg = DivisorDeBlocos.dividir("```python\nx = 2 ** 10\n```")[0]
    assert "2 ** 10" in seg.conteudo


# ---------------- texto -> html ----------------

def test_codigo_embutido_e_destacado_e_escapado():
    html = FormatadorTextoMensagem.para_html("Use `a < b` aqui")
    assert "a &lt; b" in html and "background-color" in html and "`" not in html


def test_negrito_so_e_removido_fora_das_crases():
    html = FormatadorTextoMensagem.para_html("**oi** `x ** 2`", remover_negrito=True)
    assert "oi" in html and "**oi" not in html
    assert "x ** 2" in html
    mantido = FormatadorTextoMensagem.para_html("**oi**", remover_negrito=False)
    assert "**oi**" in mantido


def test_html_e_escapado_e_links_continuam_funcionando():
    html = FormatadorTextoMensagem.para_html("<b>x</b> veja https://exemplo.com\nlinha 2")
    assert "&lt;b&gt;" in html and "<br>" in html
    assert 'href="https://exemplo.com"' in html


# ---------------- realce de sintaxe ----------------

def _formatos(linguagem, texto):
    doc = QTextDocument()
    doc.setPlainText(texto)
    realce = RealceSintaxe(doc, linguagem)
    realce.rehighlight()   # o realce automático é adiado; aqui forçamos
    resultado = []
    bloco = doc.firstBlock()
    while bloco.isValid():
        resultado.append([
            (f.start, f.length, f.format.foreground().color().name().upper())
            for f in bloco.layout().formats()
        ])
        bloco = bloco.next()
    return resultado


def test_python_colore_palavra_chave_string_numero_e_comentario(app):
    texto = 'def f(): return "a" + 12  # fim'
    cores = {(i, n): c for i, n, c in _formatos("python", texto)[0]}
    assert cores[(texto.index("def"), 3)] == "#C792EA"
    assert cores[(texto.index("return"), 6)] == "#C792EA"
    assert cores[(texto.index('"a"'), 3)] == "#C3E88D"
    assert cores[(texto.index("12"), 2)] == "#F78C6C"
    assert cores[(texto.index("#"), len("# fim"))] == "#7F8CB0"


def test_comentario_nao_colore_o_que_esta_dentro_de_string(app):
    linha = _formatos("python", 'x = "# nao e comentario"')[0]
    assert all(c != "#7F8CB0" for _, _, c in linha)


def test_aspas_triplas_atravessam_linhas(app):
    blocos = _formatos("python", 'a = """um\ndois\ntres""" + 1')
    assert blocos[1] and blocos[1][0][2] == "#C3E88D"
    assert blocos[2][0][2] == "#C3E88D"


def test_comentario_de_bloco_c_atravessa_linhas(app):
    blocos = _formatos("c", "int a; /* x\n y */ int b;")
    assert blocos[1][0][2] == "#7F8CB0"
    assert any(c == "#C792EA" for _, _, c in blocos[1])  # 'int' depois do */


def test_sql_ignora_caixa_e_json_tem_literais(app):
    assert any(c == "#C792EA" for _, _, c in _formatos("sql", "SELECT * FROM t")[0])
    assert any(c == "#C792EA" for _, _, c in _formatos("json", '{"a": true}')[0])


def test_linguagem_desconhecida_ou_vazia_so_colore_strings_e_numeros(app):
    linha = _formatos("brainfuck", 'def x = "a" 3')[0]
    assert all(c in ("#C3E88D", "#F78C6C") for _, _, c in linha)
    assert _formatos("", "texto qualquer")[0] == []


def test_realce_nao_quebra_com_emoji_e_linha_vazia(app):
    _formatos("python", 'print("😀")\n\n')


def test_catalogo_resolve_apelidos():
    assert CatalogoLinguagens.perfil("PY").nome == "python"
    assert CatalogoLinguagens.perfil("ts").nome == "javascript"
    assert CatalogoLinguagens.perfil(None).nome == "generico"


# ---------------- widgets ----------------

def test_botao_copiar_coloca_o_codigo_inteiro_na_area_de_transferencia(app):
    codigo = "def f():\n    return 2 ** 10"
    bloco = BlocoCodigo(codigo, "python")
    bloco.botao_copiar.click()
    assert QApplication.clipboard().text() == codigo
    assert bloco.botao_copiar.text() == BlocoCodigo.TEXTO_COPIADO


def test_botao_volta_para_copiar_depois_de_um_instante(app, monkeypatch):
    monkeypatch.setattr(BlocoCodigo, "DURACAO_AVISO_MS", 30)
    bloco = BlocoCodigo("x", "python")
    bloco.botao_copiar.click()
    fim = time.time() + 2
    while time.time() < fim and bloco.botao_copiar.text() != BlocoCodigo.TEXTO_COPIAR:
        app.processEvents()
        time.sleep(0.01)
    assert bloco.botao_copiar.text() == BlocoCodigo.TEXTO_COPIAR


def test_botao_tem_largura_para_os_dois_textos(app):
    bloco = BlocoCodigo("x")
    fm = bloco.botao_copiar.fontMetrics()
    assert bloco.botao_copiar.minimumWidth() >= fm.horizontalAdvance(BlocoCodigo.TEXTO_COPIADO)


def test_rotulo_mostra_linguagem_ou_codigo(app):
    assert BlocoCodigo("x", "python").rotulo_linguagem.text() == "python"
    assert BlocoCodigo("x", "").rotulo_linguagem.text() == "código"


def test_editor_mostra_todas_as_linhas_sem_cortar(app):
    codigo = "\n".join(f"linha {i}" for i in range(40))
    editor = EditorCodigo(codigo, "python")
    editor.resize(600, editor.height())
    editor.show()
    app.processEvents()
    linha = editor._altura_de_uma_linha()
    assert editor.height() >= 40 * linha
    assert editor.toPlainText() == codigo
    assert editor.isReadOnly()


def test_linha_muito_longa_ganha_rolagem_horizontal_sem_cortar_a_ultima_linha(app):
    codigo = "x = 1\n" + "y = '" + "a" * 400 + "'\nfim = 3"
    editor = EditorCodigo(codigo, "python")
    editor.setFixedWidth(300)
    editor.show()
    app.processEvents()
    app.processEvents()
    assert editor.horizontalScrollBar().maximum() > 0
    minimo = 3 * editor._altura_de_uma_linha() + editor.horizontalScrollBar().sizeHint().height()
    assert editor.height() >= minimo


def test_conteudo_da_mensagem_alterna_texto_e_blocos(app):
    c = ConteudoMensagemShaula("Antes\n```python\na=1\n```\nDepois `x`")
    assert len(c.blocos) == 1 and c.blocos[0].codigo == "a=1"
    rotulos = c.findChildren(QLabel, options=__import__("PySide6.QtCore", fromlist=["Qt"]).Qt.FindChildrenRecursively)
    textos = [r.text() for r in rotulos if "Shaula:" in r.text() or "Depois" in r.text()]
    assert any("Shaula:" in t and "Antes" in t for t in textos)
    assert any("Depois" in t for t in textos)


def test_prefixo_vai_sozinho_quando_a_resposta_comeca_por_codigo(app):
    c = ConteudoMensagemShaula("```python\na=1\n```")
    assert any("Shaula:" in r.text() for r in c.findChildren(QLabel))


# ---------------- integração com a janela ----------------

@pytest.fixture
def janela(app, tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    import interface

    w = interface.ShaulaWindow()
    w.resize(1000, 700)
    w.show()
    app.processEvents()
    yield w
    w.encerrando = True
    for j in list(interface._janelas_abertas):
        j.encerrando = True
    w.deleteLater()


def test_resposta_com_codigo_vira_bloco_com_botao_copiar(janela, app):
    janela.adicionar_mensagem("Shaula", "Veja:\n```python\nprint(2 ** 3)\n```")
    blocos = janela.findChildren(BlocoCodigo)
    assert len(blocos) == 1
    blocos[0].botao_copiar.click()
    assert QApplication.clipboard().text() == "print(2 ** 3)"


def test_resposta_sem_codigo_continua_sendo_um_rotulo(janela):
    janela.adicionar_mensagem("Shaula", "Só texto com `inline` e **negrito**.")
    assert not janela.findChildren(BlocoCodigo)
    ultimo = janela.labels_shaula[-1]
    assert isinstance(ultimo, QLabel)
    assert "negrito" in ultimo.text() and "**" not in ultimo.text()


def test_mensagem_do_usuario_com_cercas_nao_vira_bloco(janela):
    janela.adicionar_mensagem("Você", "```python\nx=1\n```")
    assert not janela.findChildren(BlocoCodigo)


def test_bloco_ocupa_a_largura_maxima_e_acompanha_o_redimensionamento(janela, app):
    janela.adicionar_mensagem("Shaula", "```python\nx=1\n```")
    conteudo = janela.labels_shaula[-1]
    assert isinstance(conteudo, ConteudoMensagemShaula)
    assert conteudo.minimumWidth() == conteudo.maximumWidth() == janela.largura_maxima_mensagem()
    janela.resize(700, 700)
    app.processEvents()
    janela.aplicar_redimensionamento()
    assert conteudo.minimumWidth() == conteudo.maximumWidth() == janela.largura_maxima_mensagem()
