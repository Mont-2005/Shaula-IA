import ctypes
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

if not hasattr(ctypes, "windll"):
    ctypes.windll = MagicMock()
    ctypes.WinDLL = MagicMock()
    ctypes.WINFUNCTYPE = ctypes.CFUNCTYPE

from PySide6.QtCore import QBuffer, QByteArray, QIODevice
from PySide6.QtGui import QColor, QImage
from PySide6.QtWidgets import QApplication, QLabel

from tools.cartao_anexo import CartaoAnexo, IconeArquivo
from tools.nota_anexo import DescricaoAnexo, NotaAnexo


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def _png_bytes():
    imagem = QImage(30, 20, QImage.Format_RGB32)
    imagem.fill(QColor("#336699"))
    dados = QByteArray()
    buffer = QBuffer(dados)
    buffer.open(QIODevice.WriteOnly)
    imagem.save(buffer, "PNG")
    return bytes(dados)


def _textos(cartao):
    return [r.text() for r in cartao.findChildren(QLabel) if r.text()]


# ---------------- IconeArquivo ----------------

@pytest.mark.parametrize("nome", ["a.pdf", "a.png", "a.mp4", "a.py", "a.txt", "Makefile"])
def test_icone_tem_o_tamanho_da_folha(app, nome):
    icone = IconeArquivo().pixmap(DescricaoAnexo(nome))
    assert not icone.isNull()
    assert icone.width() == IconeArquivo.LARGURA * IconeArquivo.ESCALA
    assert icone.height() == IconeArquivo.ALTURA * IconeArquivo.ESCALA


def test_miniatura_recorta_quadrado_e_recusa_lixo(app):
    miniatura = IconeArquivo().miniatura(_png_bytes(), 42)
    assert miniatura.width() == 42 and miniatura.height() == 42
    assert IconeArquivo().miniatura(b"isto nao e uma imagem") is None


# ---------------- CartaoAnexo ----------------

def test_cartao_mostra_nome_formato_e_detalhe(app):
    cartao = CartaoAnexo(DescricaoAnexo("A Arte da Guerra.pdf", "128 página(s)"), IconeArquivo())
    textos = _textos(cartao)
    assert "A Arte da Guerra.pdf" in textos
    assert "PDF · 128 página(s)" in textos


def test_nome_comprido_e_cortado_no_meio_e_a_dica_tem_o_nome_inteiro(app):
    nome = "um-nome-de-arquivo-realmente-muito-mas-muito-comprido-para-caber-no-cartao.pdf"
    cartao = CartaoAnexo(DescricaoAnexo(nome), IconeArquivo())
    rotulo = next(r for r in cartao.findChildren(QLabel) if r.objectName() == "cartao_anexo_nome")
    assert rotulo.text() != nome and "…" in rotulo.text()
    assert rotulo.toolTip() == nome


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


def _cartoes(janela):
    return janela.findChildren(CartaoAnexo)


def _balao_mostra_a_nota(janela):
    return any("arquivo(s) anexado(s)" in r.text() for r in janela.findChildren(QLabel))


def test_mensagem_so_com_arquivo_vira_cartao_sem_balao_de_texto(janela):
    nota = NotaAnexo().anexar_ao_texto("", ["A Arte da Guerra.pdf (128 página(s))"])
    janela.adicionar_mensagem("Você", nota)
    assert len(_cartoes(janela)) == 1
    assert not _balao_mostra_a_nota(janela)


def test_texto_e_arquivos_viram_cartoes_mais_balao_sem_a_nota(janela):
    nota = NotaAnexo().anexar_ao_texto("resuma isto", ["a.pdf (3 página(s))", "b.png"])
    janela.adicionar_mensagem("Você", nota)
    assert len(_cartoes(janela)) == 2
    assert not _balao_mostra_a_nota(janela)
    assert any("resuma isto" in r.text() for r in janela.findChildren(QLabel))


def test_imagem_recem_enviada_mostra_miniatura_no_cartao(janela):
    anexo = SimpleNamespace(imagens=[_png_bytes()], eh_imagem=True)
    nota = NotaAnexo().anexar_ao_texto("", ["foto.png"])
    janela.adicionar_mensagem("Você", nota, anexos=[anexo])
    icone = next(r for r in _cartoes(janela)[0].findChildren(QLabel) if r.objectName() == "cartao_anexo_icone")
    assert icone.pixmap().width() == 42


def test_mensagem_da_shaula_nunca_vira_cartao(janela):
    janela.adicionar_mensagem("Shaula", "[1 arquivo(s) anexado(s): a.pdf]")
    assert not _cartoes(janela)
