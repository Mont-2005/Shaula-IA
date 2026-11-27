import ctypes
import os
from unittest.mock import MagicMock

import psutil
import pytest

if not hasattr(ctypes, "windll"):
    ctypes.windll = MagicMock()
    ctypes.WinDLL = MagicMock()
    ctypes.WINFUNCTYPE = ctypes.CFUNCTYPE

from tools.captura_tela import CapturadorTela
from tools.janelas import GerenciadorJanelas
from tools.lembretes import GerenciadorLembretes
from tools.processos import GerenciadorProcessos
from tools.registro import RegistroFerramentas
from tools.voz import GerenciadorVoz, LimpadorTranscricao


# ---------------- processos ----------------

class ProcFalso:
    def __init__(self, pid, nome):
        self.pid = pid
        self.info = {"pid": pid, "name": nome}
        self.encerrado = False

    def name(self):
        return self.info["name"]

    def terminate(self):
        self.encerrado = True

    def kill(self):
        self.encerrado = True


@pytest.fixture
def processos_falsos(monkeypatch):
    lista = [
        ProcFalso(10, "svchost.exe"), ProcFalso(11, "explorer.exe"),
        ProcFalso(12, "chrome.exe"), ProcFalso(13, "chrome.exe"),
        ProcFalso(14, "python.exe"), ProcFalso(15, "chromedriver.exe"),
    ]
    monkeypatch.setattr(psutil, "process_iter", lambda attrs=None: iter(lista))
    monkeypatch.setattr(psutil, "wait_procs", lambda procs, timeout=None: (procs, []))
    return lista


@pytest.mark.parametrize("alvo", ["svchost", "explorer", "System", "csrss"])
def test_finalizar_nao_burla_protegidos_sem_extensao(processos_falsos, alvo):
    resposta = GerenciadorProcessos().finalizar_processo(alvo)
    assert "Não vou finalizar" in resposta
    assert not any(p.encerrado for p in processos_falsos)


def test_finalizar_por_trecho_ignora_protegidos_e_a_propria_shaula(processos_falsos):
    # "e" curto demais; "ho" também
    g = GerenciadorProcessos()
    assert "curto demais" in g.finalizar_processo("ho")
    # "py" também é curto; "pyth" casaria python.exe (protegido)
    resposta = g.finalizar_processo("pyth")
    assert "essenciais" in resposta
    assert not processos_falsos[4].encerrado


def test_finalizar_por_nome_mata_todas_as_instancias(processos_falsos):
    resposta = GerenciadorProcessos().finalizar_processo("chrome")
    assert "3 processo(s) finalizado(s)" in resposta  # chrome x2 + chromedriver
    assert [p.encerrado for p in processos_falsos] == [
        False, False, True, True, False, True]


def test_finalizar_pid_da_propria_shaula_e_recusado():
    resposta = GerenciadorProcessos().finalizar_processo(str(os.getpid()))
    assert "Não vou finalizar" in resposta


# ---------------- lembretes ----------------

@pytest.mark.parametrize("tempo", ["nan", "inf", "-1", "0", 10**9, "abc"])
def test_lembrete_recusa_tempos_invalidos(tempo):
    g = GerenciadorLembretes(notificador=MagicMock())
    resposta = g.criar_lembrete("x", tempo, "horas")
    assert "criado" not in resposta


def test_lembrete_valido_e_cancelavel():
    g = GerenciadorLembretes(notificador=MagicMock())
    assert "criado" in g.criar_lembrete("água", 10, "minutos")
    assert "cancelado" in g.cancelar_lembrete(1)


# ---------------- janelas ----------------

def _janelas_com(monkeypatch, titulos):
    g = GerenciadorJanelas(cache=MagicMock())
    monkeypatch.setattr(
        g, "_enumerar_janelas_visiveis",
        lambda: [{"hwnd": i, "titulo": t} for i, t in enumerate(titulos, 1)])
    return g


def test_nome_com_indice_escolhe_a_janela(monkeypatch):
    g = _janelas_com(monkeypatch, ["Chrome - A", "Chrome - B", "Bloco"])
    janela, erro = g._resolver_janela("chrome 2")
    assert erro is None and janela["titulo"] == "Chrome - B"


def test_nome_ambiguo_lista_opcoes(monkeypatch):
    g = _janelas_com(monkeypatch, ["Chrome - A", "Chrome - B"])
    janela, erro = g._resolver_janela("chrome")
    assert janela is None and "várias janelas" in erro


def test_indice_fora_do_intervalo_cai_na_lista(monkeypatch):
    g = _janelas_com(monkeypatch, ["Chrome - A", "Chrome - B"])
    janela, erro = g._resolver_janela("chrome 9")
    assert janela is None and "várias janelas" in erro


def test_titulo_que_ja_termina_em_numero_continua_funcionando(monkeypatch):
    g = _janelas_com(monkeypatch, ["Relatório 2", "Bloco"])
    janela, erro = g._resolver_janela("relatório 2")
    assert erro is None and janela["titulo"] == "Relatório 2"


# ---------------- captura de tela ----------------

def test_prints_no_mesmo_segundo_nao_se_sobrescrevem(tmp_path):
    c = CapturadorTela(MagicMock(), pasta_destino=str(tmp_path))
    caminhos = set()
    for _ in range(3):
        caminho = c._gerar_caminho("monitor1")
        open(caminho, "wb").close()
        caminhos.add(caminho)
    assert len(caminhos) == 3


@pytest.mark.parametrize("atraso", ["nan", "inf", 9999])
def test_print_recusa_atraso_absurdo(tmp_path, atraso):
    c = CapturadorTela(MagicMock(), pasta_destino=str(tmp_path))
    assert "atraso" in c.tirar_print(atraso=atraso).lower() or \
        "espera" in c.tirar_print(atraso=atraso).lower()


# ---------------- voz ----------------

def test_comando_curto_que_aparece_no_prompt_nao_e_descartado():
    prompt = ("Comandos: abrir e fechar programas, pesquisar na "
              "internet, criar lembretes, tirar print, calcular.")
    limpador = LimpadorTranscricao()
    for fala in ("Tirar print.", "Calcular", "criar lembretes"):
        assert limpador.limpar(fala, prompt_inicial=prompt) == fala.strip()
    assert limpador.limpar(
        "abrir e fechar programas", prompt_inicial=prompt) is None


def test_voz_descarrega_modelo_ao_terminar_mesmo_com_erro():
    reconhecedor = MagicMock()
    reconhecedor.carregado = True
    gravador = MagicMock()
    gravador.gravar.side_effect = RuntimeError("mic")
    g = GerenciadorVoz(gravador=gravador, reconhecedor=reconhecedor,
                       tempo_ocioso_s=0)
    with pytest.raises(RuntimeError):
        g.escutar()
    reconhecedor.descarregar_modelo.assert_called_once()


def test_voz_pode_manter_modelo_carregado_se_pedido():
    reconhecedor = MagicMock()
    reconhecedor.carregado = True
    gravador = MagicMock()
    gravador.gravar.return_value = None
    g = GerenciadorVoz(gravador=gravador, reconhecedor=reconhecedor,
                       tempo_ocioso_s=None)
    g.escutar()
    reconhecedor.descarregar_modelo.assert_not_called()


# ---------------- registro ----------------

def test_registro_explica_parametro_faltando():
    registro = RegistroFerramentas(ferramentas_permitidas=["abrir_programa"])
    resposta = registro.executar("abrir_programa", {})
    assert "Faltou o parâmetro" in resposta and "nome" in resposta


def test_voz_libera_modelo_so_depois_do_tempo_ocioso():
    import time
    reconhecedor = MagicMock()
    reconhecedor.carregado = True
    gravador = MagicMock()
    gravador.gravar.return_value = None
    g = GerenciadorVoz(gravador=gravador, reconhecedor=reconhecedor,
                       tempo_ocioso_s=0.2)
    g.escutar()
    reconhecedor.descarregar_modelo.assert_not_called()
    time.sleep(0.5)
    reconhecedor.descarregar_modelo.assert_called_once()


def test_voz_novo_uso_cancela_a_liberacao_agendada():
    import time
    reconhecedor = MagicMock()
    reconhecedor.carregado = True
    gravador = MagicMock()
    gravador.gravar.return_value = None
    g = GerenciadorVoz(gravador=gravador, reconhecedor=reconhecedor,
                       tempo_ocioso_s=0.3)
    g.escutar()
    time.sleep(0.15)
    g.escutar()          # reinicia a contagem
    time.sleep(0.2)
    reconhecedor.descarregar_modelo.assert_not_called()


def test_voz_falha_de_carga_imediata_vira_erro_antes_de_gravar():
    from tools.voz import VozIndisponivel
    reconhecedor = MagicMock()
    reconhecedor.carregado = False
    reconhecedor.carregar_modelo.side_effect = VozIndisponivel("sem lib")
    gravador = MagicMock()
    g = GerenciadorVoz(gravador=gravador, reconhecedor=reconhecedor,
                       tempo_ocioso_s=None)
    with pytest.raises(VozIndisponivel):
        g.escutar()
    gravador.gravar.assert_not_called()
