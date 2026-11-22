import ctypes
import json
import os
import subprocess
import threading
import time
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

# Os módulos de janelas usam ctypes.windll (só existe no Windows);
# para importar interface.py/registro.py fora do Windows.
if not hasattr(ctypes, "windll"):
    ctypes.windll = MagicMock()
    ctypes.WinDLL = MagicMock()
    ctypes.WINFUNCTYPE = ctypes.CFUNCTYPE

from tools.armazenamento import ArmazenamentoJson
from tools.arquivos import BuscadorArquivos
from tools.cache import CacheComandos
from tools.calculadora import Calculadora
from tools.contexto import OrcamentoContexto
from tools.conversas import GerenciadorConversas
from tools.esforco import CatalogoEsforco
from tools.memoria import HistoricoConversa
from tools.pesquisa import DetectorPerguntaFactual
from tools.programas import GerenciadorProgramas
from tools.sistema import InformacoesSistema

SISTEMA = {"role": "system", "content": "sistema"}


# ---------------- armazenamento / persistência ----------------

def test_armazenamento_ler_arquivo_corrompido_e_nao_utf8(tmp_path):
    a = ArmazenamentoJson(tmp_path / "x.json")
    assert a.ler(padrao=[]) == []
    (tmp_path / "x.json").write_bytes(b"\xff\xfe\x00{")
    assert a.ler(padrao=["p"]) == ["p"]
    (tmp_path / "x.json").write_text("{cortado", encoding="utf-8")
    assert a.ler(padrao=[]) == []


def test_armazenamento_grava_atomico_sem_sobras(tmp_path):
    a = ArmazenamentoJson(tmp_path / "x.json")
    assert a.gravar({"a": "ç"})
    assert a.ler() == {"a": "ç"}
    assert os.listdir(tmp_path) == ["x.json"]


def test_historico_descarta_mensagens_de_ferramenta(tmp_path):
    caminho = tmp_path / "h.json"
    caminho.write_text(json.dumps([
        {"role": "user", "content": "oi"},
        {"role": "tool", "content": "lixo"},
        {"role": "assistant", "content": "olá"},
    ]), encoding="utf-8")
    h = HistoricoConversa(SISTEMA, str(caminho))
    assert [m["role"] for m in h.mensagens] == ["system", "user", "assistant"]
    h.mensagens.append({"role": "tool", "content": "x"})
    h.salvar()
    salvo = json.loads(caminho.read_text(encoding="utf-8"))
    assert [m["role"] for m in salvo] == ["user", "assistant"]


def test_historico_apagar(tmp_path):
    h = HistoricoConversa(SISTEMA, str(tmp_path / "h.json"))
    h.adicionar("user", "a")
    h.salvar()
    h.apagar()
    assert h.mensagens == [SISTEMA]
    assert not (tmp_path / "h.json").exists()


def test_conversas_concorrentes_nao_perdem_entradas(tmp_path):
    g = GerenciadorConversas(SISTEMA, pasta_base=str(tmp_path / "c"))
    ids = []

    def criar():
        for _ in range(10):
            ids.append(g.criar_conversa())

    ts = [threading.Thread(target=criar) for _ in range(4)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    assert len(g.listar_conversas()) == 40
    assert len(set(ids)) == 40


def test_cache_persistente(tmp_path):
    c = CacheComandos(str(tmp_path / "c.json"))
    c.definir("arquivos", "k", ["a", "b"])
    assert c.obter("arquivos", "k") == ["a", "b"]
    c.remover("arquivos", "k")
    assert c.obter("arquivos", "k") is None


def test_busca_de_arquivo_em_cache_devolve_todos_os_resultados(tmp_path):
    pasta = tmp_path / "u"
    pasta.mkdir()
    for n in ("relatorio1.txt", "relatorio2.txt", "relatorio3.txt"):
        (pasta / n).write_text("x")
    b = BuscadorArquivos(
        cache=CacheComandos(str(tmp_path / "c.json")),
        pasta_usuario=str(pasta),
    )
    primeira = b.buscar_arquivo("relatorio")
    segunda = b.buscar_arquivo("relatorio")
    assert "Encontrei 3" in primeira
    assert "Encontrei 3" in segunda and "memorizado" in segunda
    (pasta / "relatorio2.txt").unlink()
    assert "Encontrei 2" in b.buscar_arquivo("relatorio")


# ---------------- calculadora ----------------

@pytest.mark.parametrize("expr", [
    "7**(10**8)", "factorial(10**7)", "9**9**9", "1e308*10", "2^(10**9)",
])
def test_calculadora_recusa_expressoes_gigantes_rapido(expr):
    t = time.time()
    assert "grande demais" in Calculadora().calcular(expr)
    assert time.time() - t < 1


def test_calculadora_continua_funcionando():
    c = Calculadora()
    assert c.calcular("2**10") == "Resultado: 1024"
    assert c.calcular("5^3") == "Resultado: 125"
    assert c.calcular("factorial(20)") == "Resultado: 2432902008176640000"
    assert c.calcular("2**-2") == "Resultado: 0.25"
    assert "real" in c.calcular("(-8)**(1/3)")


# ---------------- segurança de comandos ----------------

@pytest.mark.parametrize("nome", ["calc&calc", "a|b", "x>y", "%COMSPEC%", 'x"y'])
def test_abrir_programa_recusa_metacaracteres(monkeypatch, nome):
    monkeypatch.setattr(
        subprocess, "Popen",
        lambda *a, **k: pytest.fail("não deveria executar"),
    )
    assert "Não vou abrir" in GerenciadorProgramas().abrir_programa(nome)


def test_abrir_programa_aceita_nomes_e_caminhos_legitimos(monkeypatch):
    chamadas = []
    monkeypatch.setattr(subprocess, "Popen", lambda *a, **k: chamadas.append(a))
    g = GerenciadorProgramas()
    for nome in ("firefox", r"C:\Program Files (x86)\App\a.exe", "notepad++"):
        assert "Comando enviado" in g.abrir_programa(nome)
    assert len(chamadas) == 3


@pytest.mark.parametrize("host", ["-t", "-n 100", "a b", "1.1.1.1 & dir"])
def test_ping_recusa_host_invalido(monkeypatch, host):
    monkeypatch.setattr(
        subprocess, "run",
        lambda *a, **k: pytest.fail("não deveria executar"),
    )
    assert "não parece" in InformacoesSistema().testar_ping(host)


def test_ping_aceita_ipv6_e_dns():
    P = InformacoesSistema.PADRAO_HOST_VALIDO
    assert P.match("::1") and P.match("google.com") and not P.match("-t")


# ---------------- detector de busca ----------------

@pytest.mark.parametrize("texto,esperado", [
    ("quanto é 25 vezes 18?", False),
    ("quem é você?", False),
    ("qual é o meu ip?", False),
    ("quantos processos estão abertos?", False),
    ("quanto é 7x8?", False),
    ("qual a capital da França?", True),
    ("quando foi a guerra de 1914-1918?", True),
    ("o que é um buraco negro?", True),
    ("abra o firefox", False),
])
def test_detector_factual(texto, esperado):
    assert DetectorPerguntaFactual.parece_factual(texto) is esperado


# ---------------- orçamento de contexto ----------------

def _conversa_grande():
    hist = []
    for i in range(40):
        hist.append({"role": "user", "content": f"p{i} " + "x" * 300})
        hist.append({"role": "assistant", "content": f"r{i} " + "y" * 300})
    return (
        [{"role": "system", "content": "s" * 5000}] + hist
        + [{"role": "user", "content": "oi"},
           {"role": "system", "content": "lembrete"},
           {"role": "system", "content": "BUSCA " + "z" * 9000}]
    )


def test_orcamento_cabe_e_preserva_pontas():
    o = OrcamentoContexto()
    msgs = _conversa_grande()
    copia = list(msgs)
    r = o.ajustar(msgs, tokens_ferramentas=3700)
    assert o.estimar_mensagens(r) <= o.tokens_disponiveis - 3700
    assert r[0] is msgs[0]
    assert r[-3]["content"] == "oi" and r[-2]["content"] == "lembrete"
    assert msgs == copia and len(msgs[-1]["content"]) > 9000
    assert o.descartadas > 0 and o.encurtadas >= 1
    assert any(m["content"].startswith("r39") for m in r[1:-3])


def test_orcamento_nao_mexe_quando_cabe():
    o = OrcamentoContexto()
    msgs = [SISTEMA, {"role": "user", "content": "oi"}]
    assert o.ajustar(msgs) == msgs and o.descartadas == 0


def test_orcamento_aceita_objetos_do_ollama():
    o = OrcamentoContexto()
    msg = SimpleNamespace(role="assistant", content="x", images=None)
    r = o.ajustar([SISTEMA, {"role": "user", "content": "a"}, msg])
    assert r[-1] is msg


# ---------------- TrabalhadorIA ----------------

def _trabalhador(respostas, mensagens=None, anexos=None, perfil=None):
    import interface

    registro = MagicMock()
    registro.estado_internet.ativa = False
    registro.schemas_openai.return_value = [{"type": "function"}]
    registro.executar.return_value = "feito"
    registro.obter.return_value = SimpleNamespace(precisa_de_sintese=True)

    t = interface.TrabalhadorIA(
        mensagens if mensagens is not None
        else [SISTEMA, {"role": "user", "content": "oi"}],
        registro, anexos=anexos, perfil=perfil,
    )
    fila = list(respostas)
    chamadas = []

    def conversar(**p):
        chamadas.append(p)
        r = fila.pop(0) if len(fila) > 1 else fila[0]
        if isinstance(r, Exception):
            raise r
        return r

    t._chat = SimpleNamespace(conversar=conversar, cancelar=lambda: None)
    saida = {"resp": [], "erro": []}
    t.resposta_pronta.connect(saida["resp"].append)
    t.erro.connect(saida["erro"].append)
    return t, saida, chamadas, registro


def _resp(conteudo="", ferramenta=False):
    chamada = SimpleNamespace(
        function=SimpleNamespace(name="calcular", arguments={})
    )
    return SimpleNamespace(message=SimpleNamespace(
        content=conteudo, tool_calls=[chamada] if ferramenta else None,
        role="assistant", images=None))


def test_trabalhador_envia_think_configurado_e_devolve_resposta():
    t, saida, chamadas, _ = _trabalhador([_resp("olá")])
    t.run()
    assert saida["resp"] == ["olá"] and not saida["erro"]
    assert chamadas[0]["think"] is CatalogoEsforco.padrao().pensar


def test_trabalhador_erro_nao_vira_resposta_persistida():
    t, saida, _, _ = _trabalhador([RuntimeError("ollama fora")])
    t.run()
    assert not saida["resp"] and "ollama fora" in saida["erro"][0]


def test_trabalhador_resposta_vazia_vira_erro():
    t, saida, _, _ = _trabalhador([_resp("  ")])
    t.run()
    assert not saida["resp"] and "vazia" in saida["erro"][0]


def test_trabalhador_limita_rodadas_e_nao_grava_tool_no_historico():
    mensagens = [SISTEMA, {"role": "user", "content": "oi"}]
    t, saida, chamadas, _ = _trabalhador([_resp(ferramenta=True)], mensagens)
    t.run()
    assert len(chamadas) == CatalogoEsforco.padrao().max_rodadas
    assert saida["erro"] and not saida["resp"]
    assert all(m["role"] != "tool" for m in mensagens)


def test_trabalhador_com_anexo_nao_envia_ferramentas():
    anexo = SimpleNamespace(imagens=[], texto="conteudo", nota_exibicao="a.txt")
    t, saida, chamadas, _ = _trabalhador([_resp("ok")], anexos=[anexo])
    t.run()
    assert chamadas[0]["tools"] is None
