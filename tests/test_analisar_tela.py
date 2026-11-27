import ctypes
import json
import os
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

if not hasattr(ctypes, "windll"):
    ctypes.windll = MagicMock()
    ctypes.WinDLL = MagicMock()
    ctypes.WINFUNCTYPE = ctypes.CFUNCTYPE

from PySide6.QtGui import QColor, QImage
from PySide6.QtWidgets import QApplication

from tools.captura_tela import CapturadorTela
from tools.ferramentas_sistema import AnalisarTelaFerramenta
from tools.imagem_tela import (
    CapturaParaModelo,
    ImagemCapturada,
    ResultadoComImagens,
)
from tools.janelas_proprias import ApiJanelasWin32, OcultadorJanelasProprias
from tools.registro import RegistroFerramentas

SISTEMA = {"role": "system", "content": "sistema"}


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def _pixels_bgra_de_baixo_para_cima(largura, altura, cor_topo, cor_base):
    """Linhas de baixo para cima, como o GDI entrega: B, G, R, A."""

    def pixel(cor):
        return bytes([cor[2], cor[1], cor[0], 0])

    linhas = []
    for y in range(altura):            # y=0 é a linha de BAIXO no buffer
        cor = cor_base if y < altura // 2 else cor_topo
        linhas.append(pixel(cor) * largura)
    return b"".join(linhas)


# ---------------- ImagemCapturada ----------------

def test_imagem_fica_na_orientacao_certa(app):
    px = _pixels_bgra_de_baixo_para_cima(4, 4, cor_topo=(255, 0, 0), cor_base=(0, 0, 255))
    imagem = ImagemCapturada(4, 4, px).para_qimage()
    assert QColor(imagem.pixel(0, 0)).getRgb()[:3] == (255, 0, 0)    # topo vermelho
    assert QColor(imagem.pixel(3, 3)).getRgb()[:3] == (0, 0, 255)    # base azul


def test_salva_png_valido_e_menor_que_bmp(app, tmp_path):
    px = _pixels_bgra_de_baixo_para_cima(300, 200, (10, 20, 30), (200, 100, 50))
    caminho = tmp_path / "x.png"
    ImagemCapturada(300, 200, px).salvar_png(str(caminho))
    dados = caminho.read_bytes()
    assert dados[:8] == b"\x89PNG\r\n\x1a\n"
    assert len(dados) < len(px) / 10
    lida = QImage(str(caminho))
    assert (lida.width(), lida.height()) == (300, 200)
    assert QColor(lida.pixel(0, 0)).getRgb()[:3] == (10, 20, 30)


def test_salvar_png_em_pasta_inexistente_levanta_erro(app, tmp_path):
    imagem = ImagemCapturada(2, 2, bytes(16))
    with pytest.raises(OSError):
        imagem.salvar_png(str(tmp_path / "nao_existe" / "x.png"))


def test_jpeg_e_reduzido_para_o_lado_maximo(app):
    px = _pixels_bgra_de_baixo_para_cima(2000, 1000, (0, 255, 0), (0, 0, 0))
    jpeg = ImagemCapturada(2000, 1000, px).para_jpeg(1024)
    assert jpeg[:2] == b"\xff\xd8"
    img = QImage.fromData(jpeg)
    assert max(img.width(), img.height()) == 1024
    assert img.width() / img.height() == pytest.approx(2.0, rel=0.01)


def test_jpeg_pequeno_nao_e_ampliado(app):
    px = _pixels_bgra_de_baixo_para_cima(300, 200, (1, 2, 3), (4, 5, 6))
    img = QImage.fromData(ImagemCapturada(300, 200, px).para_jpeg(1024))
    assert (img.width(), img.height()) == (300, 200)


@pytest.mark.parametrize("l,a,n", [(0, 5, 20), (5, 0, 20), (-1, 5, 20), (4, 4, 10)])
def test_imagem_invalida_levanta_valueerror(l, a, n):
    with pytest.raises(ValueError):
        ImagemCapturada(l, a, bytes(n))


def test_resultado_com_imagens_e_uma_string_com_imagens():
    r = ResultadoComImagens("texto", [b"a", b"b"])
    assert isinstance(r, str) and r == "texto" and str(r) == "texto"
    assert r.imagens == [b"a", b"b"]
    assert ResultadoComImagens("x").imagens == []
    assert getattr("simples", "imagens", None) is None


# ---------------- ocultar as janelas da Shaula ----------------

class ApiFalsa:
    def __init__(self, janelas):
        self.janelas = janelas          # {hwnd: (l, t, r, b)}
        self.eventos = []

    def janelas_visiveis_do_processo(self, pid):
        self.eventos.append(("listar", pid))
        return list(self.janelas)

    def retangulo(self, hwnd):
        return self.janelas[hwnd]

    def minimizar(self, hwnd):
        self.eventos.append(("minimizar", hwnd))

    def restaurar(self, hwnd):
        self.eventos.append(("restaurar", hwnd))


MONITOR_1 = (0, 0, 1920, 1080)
MONITOR_2 = (1920, 0, 3840, 1080)


def _ocultador(api, esperas=None):
    return OcultadorJanelasProprias(
        api=api, pid=123, espera_s=0.4,
        dormir=(esperas.append if esperas is not None else (lambda _s: None)))


@pytest.mark.parametrize("a,b,esperado", [
    ((0, 0, 10, 10), (5, 5, 15, 15), True),
    ((0, 0, 10, 10), (10, 0, 20, 10), False),     # só encostam
    ((0, 0, 10, 10), (20, 20, 30, 30), False),
    ((0, 0, 100, 100), (10, 10, 20, 20), True),   # um dentro do outro
])
def test_intersecta(a, b, esperado):
    assert OcultadorJanelasProprias.intersecta(a, b) is esperado
    assert OcultadorJanelasProprias.intersecta(b, a) is esperado


def test_minimiza_so_as_janelas_que_cobrem_a_regiao_e_restaura_depois():
    api = ApiFalsa({1: (100, 100, 900, 700), 2: (2000, 100, 2800, 700)})
    esperas = []
    with _ocultador(api, esperas).ocultar(MONITOR_1) as quantas:
        assert quantas == 1
        assert ("minimizar", 1) in api.eventos and ("minimizar", 2) not in api.eventos
        assert api.eventos[-1] == ("minimizar", 1)
    assert api.eventos[-1] == ("restaurar", 1)
    assert esperas == [0.4]
    assert ("listar", 123) in api.eventos


def test_regiao_none_minimiza_todas_e_restaura_em_ordem_inversa():
    api = ApiFalsa({1: (0, 0, 10, 10), 2: (50, 50, 60, 60)})
    with _ocultador(api).ocultar(None):
        pass
    restauradas = [h for e, h in api.eventos if e == "restaurar"]
    assert restauradas == [2, 1]


def test_sem_janelas_para_ocultar_nao_espera_nada():
    api = ApiFalsa({1: (3000, 0, 3100, 10)})
    esperas = []
    with _ocultador(api, esperas).ocultar(MONITOR_1) as quantas:
        assert quantas == 0
    assert esperas == []


def test_restaura_mesmo_se_a_captura_falhar():
    api = ApiFalsa({1: (0, 0, 10, 10)})
    with pytest.raises(RuntimeError):
        with _ocultador(api).ocultar(MONITOR_1):
            raise RuntimeError("falhou")
    assert api.eventos[-1] == ("restaurar", 1)


def test_falha_da_api_nao_impede_a_captura(monkeypatch):
    class ApiQuebrada(ApiFalsa):
        def janelas_visiveis_do_processo(self, pid):
            raise OSError("sem user32")

    with _ocultador(ApiQuebrada({})).ocultar(MONITOR_1) as quantas:
        assert quantas == 0


def test_erro_ao_minimizar_uma_janela_nao_afeta_as_outras():
    class ApiTeimosa(ApiFalsa):
        def minimizar(self, hwnd):
            if hwnd == 1:
                raise OSError("recusou")
            super().minimizar(hwnd)

    api = ApiTeimosa({1: (0, 0, 10, 10), 2: (5, 5, 15, 15)})
    with _ocultador(api).ocultar(None) as quantas:
        assert quantas == 1
    assert ("restaurar", 2) in api.eventos and ("restaurar", 1) not in api.eventos


def test_fora_do_windows_vira_no_op(monkeypatch):
    def sem_windll(*_a, **_k):
        raise AttributeError("sem WinDLL")

    monkeypatch.setattr(ctypes, "WinDLL", sem_windll)
    with OcultadorJanelasProprias().ocultar(MONITOR_1) as quantas:
        assert quantas == 0


def test_api_win32_e_construida_com_argtypes():
    """Com WinDLL simulado, só confere que a configuração não quebra."""
    api = ApiJanelasWin32()
    assert api.janelas_visiveis_do_processo(1) == []


# ---------------- CapturadorTela ----------------

class JanelasFalsas:
    def __init__(self, monitores):
        self._monitores = monitores

    def obter_monitores(self):
        return self._monitores


DOIS_MONITORES = [
    {"left": 0, "top": 0, "right": 1920, "bottom": 1080, "primary": False},
    {"left": 1920, "top": 0, "right": 3840, "bottom": 1080, "primary": True},
]


def _capturador(tmp_path, monitores=None, ocultador=None):
    cap = CapturadorTela(
        JanelasFalsas(DOIS_MONITORES if monitores is None else monitores),
        pasta_destino=str(tmp_path), ocultador=ocultador)
    chamadas = []

    def falso(left, top, right, bottom):
        chamadas.append((left, top, right, bottom))
        largura, altura = right - left, bottom - top
        cab = SimpleNamespace(biWidth=largura, biHeight=altura)
        return cab, _pixels_bgra_de_baixo_para_cima(largura, altura, (9, 9, 9), (1, 1, 1))

    cap._capturar_pixels = falso
    return cap, chamadas


def test_captura_para_o_modelo_usa_o_monitor_principal_por_padrao(app, tmp_path):
    cap, chamadas = _capturador(tmp_path)
    captura = cap.capturar_para_modelo()
    assert isinstance(captura, CapturaParaModelo)
    assert captura.numero_monitor == 2 and chamadas == [(1920, 0, 3840, 1080)]
    assert (captura.largura, captura.altura) == (1920, 1080)
    img = QImage.fromData(captura.imagens[0])
    assert max(img.width(), img.height()) == CapturadorTela.LADO_MAXIMO_ANALISE_PX


def test_captura_de_monitor_escolhido(app, tmp_path):
    cap, chamadas = _capturador(tmp_path)
    assert cap.capturar_para_modelo(monitor=1).numero_monitor == 1
    assert chamadas == [(0, 0, 1920, 1080)]
    assert cap.capturar_para_modelo(monitor="2").numero_monitor == 2


@pytest.mark.parametrize("monitor,trecho", [(0, "Não existe o monitor 0"), (3, "Não existe o monitor 3"), ("x", "número inteiro")])
def test_monitor_invalido_levanta_valueerror(app, tmp_path, monitor, trecho):
    cap, _ = _capturador(tmp_path)
    with pytest.raises(ValueError, match=trecho):
        cap.capturar_para_modelo(monitor=monitor)


def test_sem_monitores_levanta_valueerror(app, tmp_path):
    cap, _ = _capturador(tmp_path, monitores=[])
    with pytest.raises(ValueError, match="nenhum monitor"):
        cap.capturar_para_modelo()


def test_esconde_a_shaula_so_sobre_o_monitor_capturado(app, tmp_path):
    api = ApiFalsa({1: (100, 100, 900, 700)})            # janela no monitor 1
    cap, _ = _capturador(tmp_path, ocultador=_ocultador(api))
    assert cap.capturar_para_modelo(monitor=1).shaula_ocultada is True
    assert ("minimizar", 1) in api.eventos and api.eventos[-1] == ("restaurar", 1)
    api.eventos.clear()
    assert cap.capturar_para_modelo(monitor=2).shaula_ocultada is False
    assert ("minimizar", 1) not in api.eventos


def test_ocultar_shaula_false_nao_mexe_nas_janelas(app, tmp_path):
    api = ApiFalsa({1: (100, 100, 900, 700)})
    cap, _ = _capturador(tmp_path, ocultador=_ocultador(api))
    cap.capturar_para_modelo(monitor=1, ocultar_shaula=False)
    assert api.eventos == []


def test_se_a_captura_falhar_a_janela_volta(app, tmp_path):
    api = ApiFalsa({1: (100, 100, 900, 700)})
    cap, _ = _capturador(tmp_path, ocultador=_ocultador(api))

    def quebrar(*_a):
        raise RuntimeError("recusado")

    cap._capturar_pixels = quebrar
    with pytest.raises(RuntimeError):
        cap.capturar_para_modelo(monitor=1)
    assert api.eventos[-1] == ("restaurar", 1)


# ---------------- prints agora em PNG ----------------

def test_tirar_print_salva_png(app, tmp_path):
    cap, _ = _capturador(tmp_path)
    resposta = cap.tirar_print(monitor=1)
    caminho = resposta.split("salvo em: ")[1].strip()
    assert caminho.endswith(".png") and os.path.isfile(caminho)
    assert open(caminho, "rb").read(8) == b"\x89PNG\r\n\x1a\n"
    assert not [f for f in os.listdir(tmp_path) if f.endswith(".bmp")]


def test_prints_de_todos_os_monitores_sao_png(app, tmp_path):
    cap, _ = _capturador(tmp_path)
    resposta = cap.tirar_print(todos=True)
    arquivos = sorted(os.listdir(tmp_path))
    assert len(arquivos) == 2 and all(a.endswith(".png") for a in arquivos)
    assert "2 print(s)" in resposta


def test_gerar_caminho_aceita_extensao_e_evita_colisao(tmp_path):
    cap, _ = _capturador(tmp_path)
    a = cap._gerar_caminho("m1")
    open(a, "wb").close()
    b = cap._gerar_caminho("m1")
    assert a.endswith(".png") and b != a and b.endswith("_2.png")
    assert cap._gerar_caminho("m1", "jpg").endswith(".jpg")


def test_falha_ao_gravar_png_vira_mensagem(app, tmp_path):
    cap, _ = _capturador(tmp_path)
    cap._pasta_destino = str(tmp_path / "arquivo_no_lugar_de_pasta")
    open(cap._pasta_destino, "w").close()
    assert "não consegui salvar" in cap.tirar_print(monitor=1)


# ---------------- ferramenta ----------------

class CapturadorFalso:
    def __init__(self, erro=None):
        self.erro = erro
        self.chamadas = []

    def capturar_para_modelo(self, monitor=None, ocultar_shaula=True):
        self.chamadas.append((monitor, ocultar_shaula))
        if self.erro:
            raise self.erro
        return CapturaParaModelo([b"jpeg"], 2, 1920, 1080, True)


def test_ferramenta_devolve_texto_com_a_imagem_anexada():
    cap = CapturadorFalso()
    r = AnalisarTelaFerramenta(cap).executar({"monitor": 2})
    assert isinstance(r, ResultadoComImagens) and r.imagens == [b"jpeg"]
    assert "monitor 2" in r and "1920x1080" in r
    assert cap.chamadas == [(2, True)]


def test_ferramenta_repassa_ocultar_shaula_false():
    cap = CapturadorFalso()
    AnalisarTelaFerramenta(cap).executar({"ocultar_shaula": False})
    assert cap.chamadas == [(None, False)]


def test_ferramenta_trata_erros_como_texto():
    assert AnalisarTelaFerramenta(CapturadorFalso(ValueError("Não existe o monitor 9."))).executar({"monitor": 9}) == "Não existe o monitor 9."
    r = AnalisarTelaFerramenta(CapturadorFalso(RuntimeError("recusado"))).executar({})
    assert "Não consegui capturar a tela: recusado" == r and not getattr(r, "imagens", None)


def test_ferramenta_precisa_de_sintese_e_tem_schema_valido():
    f = AnalisarTelaFerramenta(CapturadorFalso())
    assert f.precisa_de_sintese is True and f.nome == "analisar_tela"
    esquema = f.schema_openai()
    json.dumps(esquema)
    assert esquema["function"]["name"] == "analisar_tela"
    assert set(esquema["function"]["parameters"]["properties"]) == {"monitor", "ocultar_shaula"}
    assert esquema["function"]["parameters"]["required"] == []


def test_ferramenta_esta_no_registro():
    registro = RegistroFerramentas()
    assert registro.obter("analisar_tela") is not None
    assert "analisar_tela" in [s["function"]["name"] for s in registro.schemas_openai()]
    assert len(registro.schemas_openai()) == 40


def test_tirar_print_manda_usar_analisar_tela_para_o_modelo_ver():
    descricao = RegistroFerramentas().obter("tirar_print").descricao
    assert "analisar_tela" in descricao and "PNG" in descricao


# ---------------- fluxo da IA com imagens ----------------

def _trabalhador(respostas, resultado):
    import interface

    registro = MagicMock()
    registro.estado_internet.ativa = False
    registro.schemas_openai.return_value = [{"type": "function"}]
    registro.executar.return_value = resultado
    registro.obter.return_value = SimpleNamespace(precisa_de_sintese=True)
    historico = [SISTEMA, {"role": "user", "content": "o que tem na minha tela?"}]
    t = interface.TrabalhadorIA(historico, registro)
    fila = list(respostas)
    chamadas = []

    def conversar(**p):
        copia = dict(p)
        copia["messages"] = list(p["messages"])
        chamadas.append(copia)
        return fila.pop(0) if len(fila) > 1 else fila[0]

    t._chat = SimpleNamespace(conversar=conversar, cancelar=lambda: None)
    saida = {"resp": [], "erro": []}
    t.resposta_pronta.connect(saida["resp"].append)
    t.erro.connect(saida["erro"].append)
    return t, saida, chamadas, historico


def _resp(conteudo="", ferramenta=None):
    chamadas = None
    if ferramenta:
        chamadas = [SimpleNamespace(function=SimpleNamespace(name=ferramenta, arguments={}))]
    return SimpleNamespace(message=SimpleNamespace(
        content=conteudo, tool_calls=chamadas, role="assistant", images=None))


def test_imagem_da_ferramenta_chega_ao_modelo_sem_ferramentas():
    resultado = ResultadoComImagens("Captura obtida.", [b"JPEG-1"])
    t, saida, chamadas, historico = _trabalhador(
        [_resp(ferramenta="analisar_tela"), _resp("Vejo um editor de código.")], resultado)
    t.run()
    assert saida["resp"] == ["Vejo um editor de código."] and not saida["erro"]
    assert len(chamadas) == 2
    assert chamadas[0]["tools"] is not None
    assert chamadas[1]["tools"] is None
    ultima = chamadas[1]["messages"][-1]
    assert ultima["role"] == "user" and ultima["images"] == [b"JPEG-1"]
    assert "o que tem na minha tela?" in ultima["content"]
    assert [m for m in chamadas[1]["messages"] if isinstance(m, dict) and m["role"] == "tool"]


def test_imagem_da_ferramenta_nao_vai_para_o_historico_da_conversa():
    resultado = ResultadoComImagens("Captura obtida.", [b"JPEG-1"])
    t, _, _, historico = _trabalhador(
        [_resp(ferramenta="analisar_tela"), _resp("ok")], resultado)
    t.run()
    assert all("images" not in m for m in historico)
    assert all(m["role"] != "tool" for m in historico)


def test_ferramenta_sem_imagem_continua_igual():
    t, saida, chamadas, _ = _trabalhador(
        [_resp(ferramenta="pesquisar_internet"), _resp("pronto")], "texto simples")
    t.run()
    assert saida["resp"] == ["pronto"]
    assert chamadas[1]["tools"] is not None
    assert all("images" not in m for m in chamadas[1]["messages"] if isinstance(m, dict))
