import ctypes
import os
from unittest.mock import MagicMock

import pytest

if not hasattr(ctypes, "windll"):
    ctypes.windll = MagicMock()
    ctypes.WinDLL = MagicMock()
    ctypes.WINFUNCTYPE = ctypes.CFUNCTYPE

from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QMimeData, QPoint, QUrl, Qt
from PySide6.QtGui import QColor, QImage
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QLabel

from tools.anexos import Anexo, EstrategiaImagem, GerenciadorAnexos
from tools.area_transferencia import ConteudoColado, InterpretadorAreaTransferencia
from tools.cartao_anexo import CartaoAnexo
from tools.nota_anexo import NotaAnexo
from tools.visualizador_imagem import VisualizadorImagem


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def _imagem(largura=30, altura=20, cor="#336699"):
    imagem = QImage(largura, altura, QImage.Format_RGB32)
    imagem.fill(QColor(cor))
    return imagem


def _bytes(imagem, formato="PNG"):
    dados = QByteArray()
    buffer = QBuffer(dados)
    buffer.open(QIODevice.WriteOnly)
    imagem.save(buffer, formato)
    return bytes(dados)


def _mime_imagem(imagem=None, texto=None, html=None):
    mime = QMimeData()
    mime.setImageData(imagem or _imagem())
    if texto is not None:
        mime.setText(texto)
    if html is not None:
        mime.setHtml(html)
    return mime


# ---------------- InterpretadorAreaTransferencia ----------------

def test_so_imagem_vira_imagem(app):
    conteudo = InterpretadorAreaTransferencia().interpretar(_mime_imagem())
    assert conteudo.eh_imagem and not conteudo.imagem.isNull()


def test_so_texto_continua_texto(app):
    mime = QMimeData()
    mime.setText("olá")
    assert InterpretadorAreaTransferencia().interpretar(mime).eh_texto


def test_texto_com_imagem_de_tabela_cola_o_texto(app):
    # Copiar células do Excel traz texto + html de tabela + uma imagem.
    mime = _mime_imagem(texto="a\tb", html="<table><tr><td>a</td></tr></table>")
    assert InterpretadorAreaTransferencia().interpretar(mime).eh_texto


def test_copiar_imagem_do_navegador_anexa_mesmo_com_texto(app):
    mime = _mime_imagem(texto="https://x.com/a.png", html='<img src="https://x.com/a.png">')
    assert InterpretadorAreaTransferencia().interpretar(mime).eh_imagem


def test_arquivos_copiados_no_explorer_viram_arquivos(app, tmp_path):
    arquivo = tmp_path / "a.png"
    arquivo.write_bytes(_bytes(_imagem()))
    mime = QMimeData()
    mime.setUrls([QUrl.fromLocalFile(str(arquivo))])
    conteudo = InterpretadorAreaTransferencia().interpretar(mime)
    assert conteudo.eh_arquivos and conteudo.caminhos == [str(arquivo)]


def test_link_da_web_e_pasta_nao_viram_arquivos(app, tmp_path):
    mime = QMimeData()
    mime.setUrls([QUrl("https://exemplo.com/a.png"), QUrl.fromLocalFile(str(tmp_path))])
    assert InterpretadorAreaTransferencia().interpretar(mime).eh_texto


# ---------------- GerenciadorAnexos.carregar_imagem ----------------

def test_imagem_colada_vira_anexo_com_versao_pequena_e_grande(app):
    anexo = GerenciadorAnexos().carregar_imagem(_imagem(3000, 1500))
    pequena, grande = QImage(), QImage()
    pequena.loadFromData(anexo.imagens[0])
    grande.loadFromData(anexo.imagem_completa)
    assert max(pequena.width(), pequena.height()) == EstrategiaImagem.LADO_MAXIMO_PX
    assert max(grande.width(), grande.height()) == EstrategiaImagem.LADO_MAXIMO_VISUALIZACAO_PX
    assert anexo.eh_imagem


def test_imagem_pequena_nao_e_ampliada(app):
    anexo = GerenciadorAnexos().carregar_imagem(_imagem(200, 100))
    grande = QImage()
    grande.loadFromData(anexo.imagem_completa)
    assert (grande.width(), grande.height()) == (200, 100)


def test_imagens_coladas_sao_numeradas_e_a_nota_reconhece_o_nome(app):
    gerenciador = GerenciadorAnexos()
    nomes = [gerenciador.carregar_imagem(_imagem()).nome_arquivo for _ in range(2)]
    assert nomes == ["Imagem colada 1.png", "Imagem colada 2.png"]
    nota = NotaAnexo().anexar_ao_texto("", nomes)
    _, descricoes = NotaAnexo().separar(nota)
    assert [d.nome for d in descricoes] == nomes
    assert all(d.tipo == "imagem" for d in descricoes)


def test_imagem_nula_nao_vira_anexo(app):
    assert GerenciadorAnexos().carregar_imagem(QImage()) is None


def test_transparencia_vira_branco_e_nao_preto(app):
    imagem = QImage(10, 10, QImage.Format_ARGB32)
    imagem.fill(Qt.transparent)
    anexo = GerenciadorAnexos().carregar_imagem(imagem)
    resultado = QImage()
    resultado.loadFromData(anexo.imagens[0])
    assert resultado.pixelColor(5, 5).red() > 240


def test_imagem_de_arquivo_tambem_ganha_versao_completa(app, tmp_path):
    arquivo = tmp_path / "foto.png"
    arquivo.write_bytes(_bytes(_imagem(50, 40)))
    anexo = GerenciadorAnexos().carregar(str(arquivo))
    assert anexo.imagem_completa


def test_anexo_que_nao_e_imagem_nao_tem_versao_completa():
    assert Anexo("a.txt", texto="oi").imagem_completa is None


# ---------------- VisualizadorImagem ----------------

def test_visualizador_recusa_bytes_que_nao_sao_imagem(app):
    assert VisualizadorImagem.abrir("x.png", b"lixo") is False
    assert VisualizadorImagem.abrir("x.png", None) is False


def _visualizador(app, largura=1000, altura=700, imagem=None):
    from PySide6.QtGui import QPixmap

    pixmap = QPixmap.fromImage(imagem or _imagem(4000, 2000))
    v = VisualizadorImagem("foto.png", pixmap)
    v.resize(largura, altura)
    v.show()
    app.processEvents()
    return v


def test_visualizador_reduz_para_caber_e_mostra_o_nome(app):
    v = _visualizador(app)
    pixmap = v.rotulo_imagem.pixmap()
    area = v._area_disponivel()
    largura = pixmap.width() / pixmap.devicePixelRatio()
    altura = pixmap.height() / pixmap.devicePixelRatio()
    assert largura <= area.width() and altura <= area.height()
    assert abs(largura / altura - 2.0) < 0.02
    assert v.rotulo_nome.text() == "foto.png"
    v.close()


def test_visualizador_reajusta_ao_redimensionar(app):
    v = _visualizador(app)
    antes = v.rotulo_imagem.pixmap().width()
    v.resize(500, 400)
    app.processEvents()
    assert v.rotulo_imagem.pixmap().width() < antes
    v.close()


def test_visualizador_nao_amplia_imagem_pequena(app):
    v = _visualizador(app, imagem=_imagem(120, 80))
    assert v.rotulo_imagem.pixmap().width() == 120
    v.close()


def test_clique_no_fundo_fecha_e_clique_na_imagem_nao(app):
    v = _visualizador(app)
    QTest.mouseClick(v, Qt.LeftButton, Qt.NoModifier, v._retangulo_imagem.center())
    assert v.isVisible()
    QTest.mouseClick(v, Qt.LeftButton, Qt.NoModifier, QPoint(3, 3))
    assert not v.isVisible()


def test_esc_e_o_botao_x_fecham(app):
    v = _visualizador(app)
    QTest.keyClick(v, Qt.Key_Escape)
    assert not v.isVisible()
    v = _visualizador(app)
    v.botao_fechar.click()
    assert not v.isVisible()


# ---------------- CartaoAnexo clicável ----------------

def test_cartao_de_imagem_emite_o_sinal_ao_clicar(app):
    from tools.cartao_anexo import IconeArquivo
    from tools.nota_anexo import DescricaoAnexo

    dados = _bytes(_imagem())
    cartao = CartaoAnexo(DescricaoAnexo("foto.png"), IconeArquivo(), dados, dados)
    cartao.show()
    recebidos = []
    cartao.imagem_clicada.connect(lambda nome, d: recebidos.append((nome, d)))
    QTest.mouseClick(cartao, Qt.LeftButton)
    # clique em cima do nome (um QLabel filho) também vale
    rotulo = next(r for r in cartao.findChildren(QLabel) if r.objectName() == "cartao_anexo_nome")
    QTest.mouseClick(rotulo, Qt.LeftButton)
    assert recebidos == [("foto.png", dados)] * 2
    assert cartao.cursor().shape() == Qt.PointingHandCursor


def test_cartao_sem_imagem_completa_nao_e_clicavel(app):
    from tools.cartao_anexo import IconeArquivo
    from tools.nota_anexo import DescricaoAnexo

    cartao = CartaoAnexo(DescricaoAnexo("a.pdf"), IconeArquivo())
    cartao.show()
    recebidos = []
    cartao.imagem_clicada.connect(lambda *a: recebidos.append(a))
    QTest.mouseClick(cartao, Qt.LeftButton)
    assert recebidos == []


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
    app.clipboard().clear()


def test_ctrl_v_no_campo_com_print_anexa_a_imagem(app, janela):
    app.clipboard().setImage(_imagem(800, 600))
    janela.entrada.setFocus()
    QTest.keyClick(janela.entrada, Qt.Key_V, Qt.ControlModifier)
    assert len(janela.anexos_pendentes) == 1
    assert janela.anexos_pendentes[0].nome_arquivo == "Imagem colada 1.png"
    assert janela.entrada.toPlainText() == ""
    assert not janela.area_anexos.isHidden()


def test_ctrl_v_com_texto_continua_colando_texto(app, janela):
    app.clipboard().setText("um texto qualquer")
    janela.entrada.setFocus()
    QTest.keyClick(janela.entrada, Qt.Key_V, Qt.ControlModifier)
    assert janela.entrada.toPlainText() == "um texto qualquer"
    assert janela.anexos_pendentes == []


def test_duas_colagens_geram_dois_anexos(app, janela):
    app.clipboard().setImage(_imagem())
    janela.entrada.setFocus()
    QTest.keyClick(janela.entrada, Qt.Key_V, Qt.ControlModifier)
    QTest.keyClick(janela.entrada, Qt.Key_V, Qt.ControlModifier)
    assert [a.nome_arquivo for a in janela.anexos_pendentes] == [
        "Imagem colada 1.png",
        "Imagem colada 2.png",
    ]


def test_ctrl_v_com_o_foco_fora_do_campo_tambem_anexa(app, janela):
    app.clipboard().setImage(_imagem())
    janela.botao_anexar.setFocus()
    app.processEvents()
    QTest.keyClick(janela.botao_anexar, Qt.Key_V, Qt.ControlModifier)
    assert len(janela.anexos_pendentes) == 1
    assert janela.entrada.hasFocus()


def test_menu_de_contexto_colar_tambem_anexa(app, janela):
    app.clipboard().setImage(_imagem())
    janela.entrada.paste()
    assert len(janela.anexos_pendentes) == 1


def test_miniatura_pendente_abre_o_visualizador(app, janela, monkeypatch):
    abertos = []
    monkeypatch.setattr(VisualizadorImagem, "abrir", classmethod(lambda cls, n, d, p=None: abertos.append((n, d)) or True))
    app.clipboard().setImage(_imagem())
    janela.entrada.setFocus()
    QTest.keyClick(janela.entrada, Qt.Key_V, Qt.ControlModifier)
    from tools.cartao_anexo import MiniaturaClicavel

    miniatura = janela.area_anexos.findChildren(MiniaturaClicavel)[0]
    QTest.mouseClick(miniatura, Qt.LeftButton)
    anexo = janela.anexos_pendentes[0]
    assert abertos == [(anexo.nome_arquivo, anexo.imagem_completa)]


def test_miniatura_enviada_abre_a_imagem_inteira(app, janela, monkeypatch):
    abertos = []
    monkeypatch.setattr(VisualizadorImagem, "abrir", classmethod(lambda cls, n, d, p=None: abertos.append((n, d)) or True))
    anexo = GerenciadorAnexos().carregar_imagem(_imagem(3000, 2000))
    nota = NotaAnexo().anexar_ao_texto("", [anexo.nota_exibicao])
    janela.adicionar_mensagem("Você", nota, anexos=[anexo])
    cartao = janela.findChildren(CartaoAnexo)[0]
    QTest.mouseClick(cartao, Qt.LeftButton)
    assert abertos == [("Imagem colada 1.png", anexo.imagem_completa)]


def test_cartao_de_conversa_reaberta_nao_abre_nada(app, janela, monkeypatch):
    abertos = []
    monkeypatch.setattr(VisualizadorImagem, "abrir", classmethod(lambda cls, n, d, p=None: abertos.append(1) or True))
    janela.adicionar_mensagem("Você", NotaAnexo().anexar_ao_texto("", ["foto.png"]))
    QTest.mouseClick(janela.findChildren(CartaoAnexo)[0], Qt.LeftButton)
    assert abertos == []
