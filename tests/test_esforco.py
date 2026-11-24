import ctypes
import json
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

if not hasattr(ctypes, "windll"):
    ctypes.windll = MagicMock()
    ctypes.WinDLL = MagicMock()
    ctypes.WINFUNCTYPE = ctypes.CFUNCTYPE

from tools.armazenamento import ArmazenamentoJson
from tools.esforco import CatalogoEsforco, EstadoEsforco

SISTEMA = {"role": "system", "content": "sistema"}


# ---------------- catálogo ----------------

def test_catalogo_tem_cinco_niveis_em_ordem_crescente():
    perfis = CatalogoEsforco.listar()
    assert [p.chave for p in perfis] == ["baixo", "medio", "alto", "extra", "max"]
    assert [p.num_ctx for p in perfis] == sorted(p.num_ctx for p in perfis)
    assert [p.num_predict for p in perfis] == sorted(p.num_predict for p in perfis)


def test_so_o_nivel_baixo_nao_raciocina():
    assert [p.pensar for p in CatalogoEsforco.listar()] == [False, True, True, True, True]


def test_medio_e_o_padrao_recomendado():
    padrao = CatalogoEsforco.padrao()
    assert padrao.chave == "medio" and padrao.recomendado
    assert padrao.num_ctx == 11264 and padrao.num_predict == 2048 and padrao.max_rodadas == 8
    assert [p.chave for p in CatalogoEsforco.listar() if p.recomendado] == ["medio"]


def test_todo_nivel_deixa_espaco_para_o_prompt():
    for p in CatalogoEsforco.listar():
        assert p.tokens_para_prompt >= 6000
        assert p.num_predict < p.num_ctx


def test_niveis_pesados_avisam_do_custo_de_vram():
    avisos = {p.chave: bool(p.aviso) for p in CatalogoEsforco.listar()}
    assert avisos == {"baixo": False, "medio": False, "alto": False, "extra": True, "max": True}


@pytest.mark.parametrize("texto,chave", [
    ("médio", "medio"), (" MEDIO ", "medio"), ("Máx", "max"),
    ("max", "max"), ("Baixo", "baixo"), ("ALTO", "alto"),
])
def test_obter_ignora_acento_caixa_e_espacos(texto, chave):
    assert CatalogoEsforco.obter(texto).chave == chave


@pytest.mark.parametrize("texto", ["", "ultra", None, "médio alto"])
def test_obter_nivel_inexistente_devolve_none(texto):
    assert CatalogoEsforco.obter(texto) is None


def test_perfil_e_imutavel_e_resumo_descreve_os_parametros():
    p = CatalogoEsforco.obter("baixo")
    with pytest.raises(Exception):
        p.pensar = True
    assert "sem raciocínio" in p.resumo and "1024" in p.resumo
    assert "com raciocínio" in CatalogoEsforco.obter("alto").resumo


# ---------------- estado ----------------

def _estado(tmp_path, ambiente=None):
    return EstadoEsforco(
        armazenamento=ArmazenamentoJson(tmp_path / "cfg.json"),
        ambiente={} if ambiente is None else ambiente,
    )


def test_estado_comeca_no_padrao(tmp_path):
    assert _estado(tmp_path).perfil.chave == "medio"


def test_estado_usa_variavel_de_ambiente_quando_nada_foi_salvo(tmp_path):
    assert _estado(tmp_path, {"SHAULA_ESFORCO": "alto"}).perfil.chave == "alto"
    assert _estado(tmp_path, {"SHAULA_ESFORCO": "lixo"}).perfil.chave == "medio"


def test_escolha_salva_vence_a_variavel_de_ambiente(tmp_path):
    e = _estado(tmp_path)
    assert e.definir("baixo").chave == "baixo"
    outro = _estado(tmp_path, {"SHAULA_ESFORCO": "max"})
    assert outro.perfil.chave == "baixo"


def test_definir_persiste_sem_apagar_outras_configuracoes(tmp_path):
    (tmp_path / "cfg.json").write_text(json.dumps({"outra": 1}), encoding="utf-8")
    _estado(tmp_path).definir("extra")
    dados = json.loads((tmp_path / "cfg.json").read_text(encoding="utf-8"))
    assert dados == {"outra": 1, "esforco": "extra"}


def test_definir_nivel_invalido_nao_muda_nada(tmp_path):
    e = _estado(tmp_path)
    e.definir("alto")
    assert e.definir("ultra") is None
    assert e.perfil.chave == "alto"
    assert not (tmp_path / "x").exists()


def test_arquivo_corrompido_cai_no_padrao(tmp_path):
    (tmp_path / "cfg.json").write_bytes(b"\xff\xfe{")
    assert _estado(tmp_path).perfil.chave == "medio"
    (tmp_path / "cfg.json").write_text("[1,2]", encoding="utf-8")
    assert _estado(tmp_path).perfil.chave == "medio"
    e = _estado(tmp_path)
    e.definir("alto")           # recupera: reescreve o arquivo como dict
    assert json.loads((tmp_path / "cfg.json").read_text(encoding="utf-8"))["esforco"] == "alto"


# ---------------- uso pelo TrabalhadorIA ----------------

def _trabalhador(perfil, respostas):
    import interface

    registro = MagicMock()
    registro.estado_internet.ativa = False
    registro.schemas_openai.return_value = [{"type": "function"}]
    registro.executar.return_value = "feito"
    registro.obter.return_value = SimpleNamespace(precisa_de_sintese=True)
    t = interface.TrabalhadorIA(
        [SISTEMA, {"role": "user", "content": "oi"}], registro, perfil=perfil)
    fila = list(respostas)
    chamadas = []

    def conversar(**p):
        chamadas.append(p)
        return fila.pop(0) if len(fila) > 1 else fila[0]

    t._chat = SimpleNamespace(conversar=conversar, cancelar=lambda: None)
    saida = {"resp": [], "erro": []}
    t.resposta_pronta.connect(saida["resp"].append)
    t.erro.connect(saida["erro"].append)
    return t, saida, chamadas


def _resp(conteudo="", ferramenta=False):
    chamada = SimpleNamespace(function=SimpleNamespace(name="calcular", arguments={}))
    return SimpleNamespace(message=SimpleNamespace(
        content=conteudo, tool_calls=[chamada] if ferramenta else None,
        role="assistant", images=None))


@pytest.mark.parametrize("chave", ["baixo", "medio", "alto", "extra", "max"])
def test_cada_nivel_chega_ao_ollama_com_seus_parametros(chave):
    perfil = CatalogoEsforco.obter(chave)
    t, saida, chamadas = _trabalhador(perfil, [_resp("ok")])
    t.run()
    assert saida["resp"] == ["ok"]
    assert chamadas[0]["think"] is perfil.pensar
    assert chamadas[0]["options"] == {
        "num_ctx": perfil.num_ctx, "num_predict": perfil.num_predict}


@pytest.mark.parametrize("chave", ["baixo", "medio", "max"])
def test_limite_de_rodadas_segue_o_nivel(chave):
    perfil = CatalogoEsforco.obter(chave)
    t, saida, chamadas = _trabalhador(perfil, [_resp(ferramenta=True)])
    t.run()
    assert len(chamadas) == perfil.max_rodadas
    assert str(perfil.max_rodadas) in saida["erro"][0]


def test_orcamento_de_contexto_acompanha_o_nivel():
    perfil = CatalogoEsforco.obter("max")
    t, _, _ = _trabalhador(perfil, [_resp("ok")])
    assert t._orcamento.num_ctx == 18432
    assert t._orcamento.reserva_resposta == 6144
    assert t._orcamento.tokens_disponiveis == perfil.tokens_para_prompt


def test_sem_perfil_usa_o_padrao():
    t, _, chamadas = _trabalhador(None, [_resp("ok")])
    t.run()
    assert chamadas[0]["think"] is True and chamadas[0]["options"]["num_ctx"] == 11264


def test_mudar_o_estado_no_meio_nao_afeta_a_resposta_em_andamento(tmp_path):
    estado = _estado(tmp_path)
    t, _, chamadas = _trabalhador(estado.perfil, [_resp("ok")])
    estado.definir("max")          # depois de criar o trabalhador
    t.run()
    assert chamadas[0]["options"]["num_ctx"] == 11264


# ---------------- terminal (main.py) ----------------

def _terminal(tmp_path, linhas, respostas=None):
    import main

    saida = []
    it = iter(linhas)
    fila = list(respostas or [])
    chamadas = []

    def chat(**p):
        chamadas.append(p)
        return fila.pop(0)

    a = main.AssistenteTerminal(
        estado_esforco=_estado(tmp_path), funcao_chat=chat,
        entrada=lambda _p: next(it), saida=saida.append)
    return a, saida, chamadas


def test_terminal_comando_esforco_troca_o_nivel_sem_chamar_o_modelo(tmp_path):
    a, saida, chamadas = _terminal(tmp_path, ["esforço alto", "sair"])
    a.executar()
    assert a.estado_esforco.perfil.chave == "alto"
    assert chamadas == [] and any("Alto" in str(s) for s in saida)


def test_terminal_esforco_sem_argumento_lista_niveis(tmp_path):
    a, saida, _ = _terminal(tmp_path, ["esforco", "sair"])
    a.executar()
    texto = " ".join(map(str, saida))
    assert "Esforço atual: Médio" in texto and "Baixo, Médio, Alto, Extra, Máx" in texto


def test_terminal_nivel_invalido_e_avisado(tmp_path):
    a, saida, _ = _terminal(tmp_path, ["esforço ultra", "sair"])
    a.executar()
    assert any("desconhecido" in str(s) for s in saida)
    assert a.estado_esforco.perfil.chave == "medio"


def test_terminal_repassa_o_nivel_ao_modelo(tmp_path):
    msg = SimpleNamespace(message=SimpleNamespace(content="oi", tool_calls=None))
    a, _, chamadas = _terminal(tmp_path, ["esforço baixo", "olá", "sair"], [msg])
    a.executar()
    assert chamadas[0]["think"] is False
    assert chamadas[0]["options"] == {"num_ctx": 10240, "num_predict": 1024}


# Espaço fixo antes de qualquer conversa: prompt de sistema (~1.700 tokens)
# + schemas das 40 ferramentas (~4.100). Se o nível não deixar sobra para o
# histórico, a Shaula "esquece" a conversa (bug da 4.65.5: Médio sobrava ~180).
CUSTO_FIXO_TOKENS = 1680 + 4116 + 170


@pytest.mark.parametrize("chave", ["baixo", "medio", "alto", "extra", "max"])
def test_cada_nivel_deixa_espaco_real_para_o_historico(chave):
    perfil = CatalogoEsforco.obter(chave)
    sobra = perfil.tokens_para_prompt - CUSTO_FIXO_TOKENS
    assert sobra >= 3000
