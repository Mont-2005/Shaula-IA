import ctypes
from unittest.mock import MagicMock

import pytest

if not hasattr(ctypes, "windll"):
    ctypes.windll = MagicMock()
    ctypes.WinDLL = MagicMock()
    ctypes.WINFUNCTYPE = ctypes.CFUNCTYPE

from PySide6.QtWidgets import QApplication, QMainWindow

from tools.esforco import EstadoEsforco
from tools.internet import EstadoInternet
from tools.menu_principal import (
    CatalogoMenu,
    DialogoParametros,
    ItemFerramenta,
    MenuPrincipal,
    Submenu,
    TrabalhadorFerramenta,
    ler_matriz,
)
from tools.registro import RegistroFerramentas


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture(autouse=True)
def _pasta_do_usuario_isolada(tmp_path, monkeypatch):
    # Criar o RegistroFerramentas lê ~/.shaula (lembretes, cache...).
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))


# ------------------------------------------------------------
# ler_matriz
# ------------------------------------------------------------

def test_matriz_por_linhas():
    assert ler_matriz("2 1\n3 4") == [[2, 1], [3, 4]]


def test_matriz_com_virgulas_e_ponto_e_virgula():
    assert ler_matriz("1, 2; 3, 4") == [[1, 2], [3, 4]]


def test_matriz_json():
    assert ler_matriz("[[1, 2.5], [3, 4]]") == [[1, 2.5], [3, 4]]


def test_matriz_decimais_viram_float_e_inteiros_continuam_int():
    matriz = ler_matriz("1.5 2\n3 4")
    assert matriz == [[1.5, 2], [3, 4]]
    assert isinstance(matriz[0][1], int)


@pytest.mark.parametrize(
    "texto",
    [
        "",
        "   ",
        "1 2\n3",            # linhas de tamanhos diferentes
        "a b\nc d",          # não numérico
        "[[1, 2], [3, ]",    # JSON quebrado
        "[1, 2, 3]",         # não é lista de listas
        "[[true, 1]]",       # booleano não é número
        "[]",
    ],
)
def test_matriz_invalida_levanta_valueerror(texto):
    with pytest.raises(ValueError):
        ler_matriz(texto)


# ------------------------------------------------------------
# DialogoParametros
# ------------------------------------------------------------

ESQUEMA = {
    "type": "object",
    "properties": {
        "texto": {"type": "string"},
        "tempo": {"type": "number"},
        "quantidade": {"type": "integer"},
        "unidade": {"type": "string", "enum": ["segundos", "minutos"]},
        "ativo": {"type": "boolean"},
        "a": {"type": "array"},
    },
    "required": ["texto", "tempo"],
}


def _dialogo(app, campos=None):
    return DialogoParametros("Teste", ESQUEMA, campos)


def test_obrigatorio_vazio_mostra_erro_e_nao_aceita(app):
    dialogo = _dialogo(app)
    dialogo._validar()
    assert "Texto" in dialogo._rotulo_erro.text()
    assert dialogo.argumentos() == {}


def test_valores_validos_e_opcionais_omitidos(app):
    dialogo = _dialogo(app)
    dialogo._campos["texto"][1].setText("revisar")
    dialogo._campos["tempo"][1].setText("2,5")
    dialogo._validar()
    assert dialogo.argumentos() == {"texto": "revisar", "tempo": 2.5}


def test_numero_inteiro_digitado_vira_int(app):
    dialogo = _dialogo(app)
    dialogo._campos["texto"][1].setText("x")
    dialogo._campos["tempo"][1].setText("2")
    dialogo._validar()
    argumentos = dialogo.argumentos()
    assert argumentos["tempo"] == 2 and isinstance(argumentos["tempo"], int)


def test_inteiro_invalido_e_rejeitado(app):
    dialogo = _dialogo(app)
    dialogo._campos["texto"][1].setText("x")
    dialogo._campos["tempo"][1].setText("1")
    dialogo._campos["quantidade"][1].setText("abc")
    dialogo._validar()
    assert "inteiro" in dialogo._rotulo_erro.text()


def test_enum_e_booleano_opcionais_escolhidos(app):
    dialogo = _dialogo(app)
    dialogo._campos["texto"][1].setText("x")
    dialogo._campos["tempo"][1].setText("1")
    combo_unidade = dialogo._campos["unidade"][1]
    combo_unidade.setCurrentIndex(combo_unidade.findData("minutos"))
    combo_ativo = dialogo._campos["ativo"][1]
    combo_ativo.setCurrentIndex(combo_ativo.findData(False))
    dialogo._validar()
    argumentos = dialogo.argumentos()
    assert argumentos["unidade"] == "minutos"
    assert argumentos["ativo"] is False


def test_matriz_no_dialogo(app):
    dialogo = _dialogo(app)
    dialogo._campos["texto"][1].setText("x")
    dialogo._campos["tempo"][1].setText("1")
    dialogo._campos["a"][1].setPlainText("2 1\n3 4")
    dialogo._validar()
    assert dialogo.argumentos()["a"] == [[2, 1], [3, 4]]


def test_campos_restringe_o_formulario(app):
    dialogo = _dialogo(app, campos=["texto"])
    assert list(dialogo._campos) == ["texto"]


# ------------------------------------------------------------
# Catálogo
# ------------------------------------------------------------

def _nomes_do_catalogo():
    nomes = []

    def varrer(itens):
        for item in itens:
            if isinstance(item, ItemFerramenta):
                nomes.append(item.nome)
            elif isinstance(item, Submenu):
                varrer(item.itens)

    for _titulo, itens in CatalogoMenu.menus():
        varrer(itens)

    varrer(CatalogoMenu.rede())

    return nomes


def test_menu_alcanca_todas_as_ferramentas_do_registro():
    registro = RegistroFerramentas()
    esperadas = {ferramenta.nome for ferramenta in registro}

    assert len(esperadas) == 40
    assert CatalogoMenu.nomes_cobertos() == esperadas


def test_nenhuma_ferramenta_aparece_duas_vezes():
    nomes = _nomes_do_catalogo()
    assert len(nomes) == len(set(nomes))


# ------------------------------------------------------------
# TrabalhadorFerramenta
# ------------------------------------------------------------

def test_trabalhador_devolve_o_resultado_da_ferramenta(app):
    registro = MagicMock()
    registro.executar.return_value = "5"
    recebidos = []

    trabalhador = TrabalhadorFerramenta(registro, "matriz_determinante", {"a": [[1]]})
    trabalhador.concluido.connect(recebidos.append)
    trabalhador.run()

    registro.executar.assert_called_once_with("matriz_determinante", {"a": [[1]]})
    assert recebidos == ["5"]


def test_trabalhador_converte_excecao_em_mensagem(app):
    registro = MagicMock()
    registro.executar.side_effect = RuntimeError("falhou")
    recebidos = []

    trabalhador = TrabalhadorFerramenta(registro, "calcular", {})
    trabalhador.concluido.connect(recebidos.append)
    trabalhador.run()

    assert len(recebidos) == 1
    assert "calcular" in recebidos[0] and "falhou" in recebidos[0]


def test_trabalhador_tem_interromper_como_o_trabalhador_da_ia(app):
    TrabalhadorFerramenta(MagicMock(), "x", {}).interromper()


# ------------------------------------------------------------
# MenuPrincipal numa janela de mentira
# ------------------------------------------------------------

class _JanelaFalsa(QMainWindow):

    def __init__(self):
        super().__init__()
        self.registro = RegistroFerramentas(estado_internet=EstadoInternet())
        self.estado_esforco = EstadoEsforco()
        self.id_conversa_atual = "c1"
        self.gerenciador_conversas = MagicMock()
        self.gerenciador_conversas.listar_conversas.return_value = [
            {"id": "c1", "titulo": "A & B", "fixado": True},
            {"id": "c2", "titulo": "Outra", "fixado": False},
        ]
        for nome in (
            "criar_nova_conversa", "abrir_conversa_em_nova_janela",
            "abrir_dialogo_anexo", "fechar_shaula", "alternar_barra_lateral",
            "alternar_escuta", "definir_esforco", "renomear_conversa_ui",
            "apagar_conversa_ui", "atualizar_lista_conversas",
        ):
            setattr(self, nome, MagicMock())
        self.alternar_internet = lambda: self.registro.estado_internet.ativar()


def _titulos(menu):
    return [acao.text() for acao in menu.actions() if not acao.isSeparator()]


def test_menu_instalado_tem_os_menus_esperados(app):
    janela = _JanelaFalsa()
    MenuPrincipal(janela).instalar()

    titulos = [acao.text().replace("&", "") for acao in janela.menuBar().actions()]

    assert titulos == [
        "Arquivo", "Conversas", "Programas e arquivos", "Calculadora",
        "Lembretes", "Janelas e telas", "Sistema", "Rede e internet",
        "Configurações", "Ajuda",
    ]


def test_menu_arquivo_chama_a_janela(app):
    janela = _JanelaFalsa()
    MenuPrincipal(janela).instalar()

    menu_arquivo = janela.menuBar().actions()[0].menu()
    acoes = {acao.text(): acao for acao in menu_arquivo.actions()}

    acoes["Nova conversa"].trigger()
    acoes["Anexar arquivo…"].trigger()
    acoes["Sair da Shaula"].trigger()

    janela.criar_nova_conversa.assert_called_once()
    janela.abrir_dialogo_anexo.assert_called_once()
    janela.fechar_shaula.assert_called_once()


def test_ir_para_lista_as_conversas_e_marca_a_atual(app):
    janela = _JanelaFalsa()
    menu = MenuPrincipal(janela)
    menu.instalar()

    menu._preencher_ir_para()
    acoes = menu._menu_ir_para.actions()

    assert [acao.text() for acao in acoes] == ["📌 A && B", "Outra"]
    assert [acao.isChecked() for acao in acoes] == [True, False]


def test_esforco_marca_o_nivel_atual_e_troca_ao_clicar(app):
    janela = _JanelaFalsa()
    menu = MenuPrincipal(janela)
    menu.instalar()

    menu._preencher_esforco()
    acoes = menu._menu_esforco.actions()
    assert len(acoes) == 5
    assert sum(acao.isChecked() for acao in acoes) == 1

    acoes[0].trigger()
    janela.definir_esforco.assert_called_once()


def test_liga_desliga_internet_acompanha_o_estado(app):
    janela = _JanelaFalsa()
    menu = MenuPrincipal(janela)
    menu.instalar()

    menu_rede = [
        acao.menu() for acao in janela.menuBar().actions()
        if acao.text().replace("&", "") == "Rede e internet"
    ][0]

    menu_rede.aboutToShow.emit()
    assert menu._acao_internet.isChecked() is False

    janela.registro.estado_internet.ativar()
    menu_rede.aboutToShow.emit()
    assert menu._acao_internet.isChecked() is True
