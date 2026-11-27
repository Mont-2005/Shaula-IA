import sqlite3
import threading

import pytest

from tools.banco_dados import BancoSqlite
from tools.conversas import GerenciadorConversas
from tools.memoria import HistoricoConversa
from tools.repositorio_conversas import RepositorioConversas

SISTEMA = {"role": "system", "content": "sistema"}


@pytest.fixture
def banco(tmp_path):
    return BancoSqlite(tmp_path / "pasta" / "shaula.db")


@pytest.fixture
def repo(banco):
    return RepositorioConversas(banco)


@pytest.fixture
def g(tmp_path):
    return GerenciadorConversas(SISTEMA, pasta_base=str(tmp_path / "c"))


def _tabelas(banco):
    with banco.leitura() as c:
        return {l[0] for l in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}


# ---------------- BancoSqlite ----------------

def test_cria_pasta_arquivo_e_esquema(banco):
    assert banco.caminho.endswith("shaula.db")
    assert {"conversas", "mensagens"} <= _tabelas(banco)
    with banco.leitura() as c:
        assert c.execute("PRAGMA user_version").fetchone()[0] == BancoSqlite.VERSAO_ESQUEMA
        assert c.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
        assert c.execute("PRAGMA foreign_keys").fetchone()[0] == 1


def test_reabrir_nao_recria_nem_apaga_dados(tmp_path):
    caminho = tmp_path / "x.db"
    RepositorioConversas(BancoSqlite(caminho)).inserir("a", "Primeira")
    assert [e["id"] for e in RepositorioConversas(BancoSqlite(caminho)).listar()] == ["a"]


def test_transacao_desfaz_tudo_se_der_erro(banco):
    with pytest.raises(RuntimeError):
        with banco.transacao() as c:
            c.execute("INSERT INTO conversas VALUES ('z','t',1,0,'a','b')")
            raise RuntimeError("falhou no meio")
    with banco.leitura() as c:
        assert c.execute("SELECT COUNT(*) FROM conversas").fetchone()[0] == 0


# ---------------- RepositorioConversas: conversas ----------------

def test_inserir_listar_obter(repo):
    repo.inserir("a", "Nova conversa")
    e = repo.obter("a")
    assert e["titulo"] == "Nova conversa" and e["titulo_automatico"] is True
    assert e["fixado"] is False and e["criado_em"] == e["atualizado_em"]
    assert repo.obter("nao-existe") is None


def test_id_duplicado_e_recusado(repo):
    repo.inserir("a", "x")
    with pytest.raises(sqlite3.IntegrityError):
        repo.inserir("a", "y")


def test_ordem_fixadas_primeiro_depois_mais_recentes(repo):
    for i in "abc":
        repo.inserir(i, i)
    repo.marcar_atualizada("a")          # a é a mais recente
    assert [e["id"] for e in repo.listar()] == ["a", "c", "b"]
    repo.alternar_fixado("b")            # b fixada sobe
    assert [e["id"] for e in repo.listar()] == ["b", "a", "c"]


def test_alternar_fixado_vai_e_volta_e_none_se_nao_existe(repo):
    repo.inserir("a", "a")
    assert repo.alternar_fixado("a") is True
    assert repo.alternar_fixado("a") is False
    assert repo.alternar_fixado("x") is None


def test_renomear_desliga_titulo_automatico(repo):
    repo.inserir("a", "a")
    assert repo.renomear("a", "Meu título") is True
    e = repo.obter("a")
    assert e["titulo"] == "Meu título" and e["titulo_automatico"] is False
    assert repo.renomear("x", "y") is False


def test_titulo_automatico_so_vale_se_nunca_renomeada(repo):
    repo.inserir("a", "Nova conversa")
    repo.definir_titulo_automatico("a", "Gerado")
    assert repo.obter("a")["titulo"] == "Gerado"
    repo.renomear("a", "Do usuário")
    repo.definir_titulo_automatico("a", "Outro gerado")
    assert repo.obter("a")["titulo"] == "Do usuário"
    repo.redefinir_titulo("a", "Nova conversa")
    assert repo.obter("a")["titulo_automatico"] is True
    repo.definir_titulo_automatico("a", "Depois do reset")
    assert repo.obter("a")["titulo"] == "Depois do reset"


def test_texto_perigoso_e_so_texto(repo):
    sujo = "'); DROP TABLE conversas;-- \" ' %"
    repo.inserir("a", sujo)
    repo.renomear("a", sujo + "2")
    assert repo.obter("a")["titulo"] == sujo + "2"
    repo.gravar_mensagens("a", [{"role": "user", "content": sujo}])
    assert repo.carregar_mensagens("a")[0]["content"] == sujo


# ---------------- RepositorioConversas: mensagens ----------------

def test_mensagens_ida_e_volta_com_unicode_e_quebras_de_linha(repo):
    repo.inserir("a", "a")
    msgs = [
        {"role": "user", "content": "olá 😀\nsegunda linha\t\"aspas\""},
        {"role": "assistant", "content": "ação ✓ — ünïcode"},
    ]
    assert repo.gravar_mensagens("a", msgs) is True
    assert repo.carregar_mensagens("a") == msgs


def _ids(banco, conv="a"):
    with banco.leitura() as c:
        return [l[0] for l in c.execute("SELECT id FROM mensagens WHERE conversa_id=? ORDER BY id", (conv,))]


def test_so_insere_o_que_e_novo_e_mantem_os_ids_antigos(repo, banco):
    repo.inserir("a", "a")
    m = [{"role": "user", "content": "1"}]
    repo.gravar_mensagens("a", m)
    antes = _ids(banco)
    m.append({"role": "assistant", "content": "2"})
    repo.gravar_mensagens("a", m)
    depois = _ids(banco)
    assert depois[:1] == antes and len(depois) == 2


def test_regrava_tudo_quando_a_lista_mudou_de_outro_jeito(repo):
    repo.inserir("a", "a")
    repo.gravar_mensagens("a", [{"role": "user", "content": str(i)} for i in range(5)])
    novas = [{"role": "user", "content": str(i)} for i in range(2, 7)]  # descartou as 2 mais antigas
    repo.gravar_mensagens("a", novas)
    assert repo.carregar_mensagens("a") == novas


def test_lista_vazia_limpa_a_conversa(repo):
    repo.inserir("a", "a")
    repo.gravar_mensagens("a", [{"role": "user", "content": "x"}])
    repo.gravar_mensagens("a", [])
    assert repo.carregar_mensagens("a") == []


def test_gravar_em_conversa_inexistente_devolve_false_e_nao_cria_nada(repo, banco):
    assert repo.gravar_mensagens("fantasma", [{"role": "user", "content": "x"}]) is False
    with banco.leitura() as c:
        assert c.execute("SELECT COUNT(*) FROM mensagens").fetchone()[0] == 0


def test_papel_invalido_desfaz_a_gravacao_inteira(repo):
    repo.inserir("a", "a")
    repo.gravar_mensagens("a", [{"role": "user", "content": "ok"}])
    with pytest.raises(sqlite3.IntegrityError):
        repo.gravar_mensagens("a", [
            {"role": "user", "content": "ok"},
            {"role": "tool", "content": "lixo"},
        ])
    assert repo.carregar_mensagens("a") == [{"role": "user", "content": "ok"}]


def test_apagar_conversa_leva_as_mensagens_junto(repo, banco):
    repo.inserir("a", "a")
    repo.inserir("b", "b")
    repo.gravar_mensagens("a", [{"role": "user", "content": "x"}])
    repo.gravar_mensagens("b", [{"role": "user", "content": "y"}])
    repo.apagar("a")
    assert repo.obter("a") is None and repo.carregar_mensagens("a") == []
    assert repo.carregar_mensagens("b") == [{"role": "user", "content": "y"}]


def test_apagar_mensagens_mantem_a_conversa(repo):
    repo.inserir("a", "a")
    repo.gravar_mensagens("a", [{"role": "user", "content": "x"}])
    repo.apagar_mensagens("a")
    assert repo.obter("a") is not None and repo.carregar_mensagens("a") == []


# ---------------- HistoricoConversa sobre o banco ----------------

def test_historico_persiste_e_recarrega(g):
    id_ = g.criar_conversa()
    h = g.obter_historico(id_)
    assert h.mensagens == [SISTEMA]
    h.adicionar("user", "oi")
    h.adicionar("assistant", "olá")
    assert h.salvar() is True
    h2 = g.obter_historico(id_)
    assert h2.mensagens == [SISTEMA, {"role": "user", "content": "oi"}, {"role": "assistant", "content": "olá"}]


def test_historico_descarta_mensagens_de_ferramenta_ao_salvar(g):
    id_ = g.criar_conversa()
    h = g.obter_historico(id_)
    h.adicionar("user", "a")
    h.mensagens.append({"role": "tool", "content": "x"})
    h.salvar()
    assert [m["role"] for m in g.obter_historico(id_).mensagens] == ["system", "user"]


def test_historico_respeita_o_limite_de_mensagens(g):
    id_ = g.criar_conversa()
    h = g.obter_historico(id_)
    for i in range(HistoricoConversa.MAX_MENSAGENS_HISTORICO + 10):
        h.adicionar("user", str(i))
        h.salvar()
    salvas = g.obter_historico(id_).mensagens[1:]
    assert len(salvas) == HistoricoConversa.MAX_MENSAGENS_HISTORICO
    assert salvas[-1]["content"] == str(HistoricoConversa.MAX_MENSAGENS_HISTORICO + 9)


def test_historico_apagar_limpa_mensagens_mas_a_conversa_continua(g):
    id_ = g.criar_conversa()
    h = g.obter_historico(id_)
    h.adicionar("user", "x")
    h.salvar()
    h.apagar()
    assert h.mensagens == [SISTEMA]
    assert g.obter_historico(id_).mensagens == [SISTEMA]
    assert g.obter_entrada(id_) is not None


def test_salvar_apos_a_conversa_ser_apagada_em_outra_janela_nao_ressuscita(g):
    id_ = g.criar_conversa()
    h = g.obter_historico(id_)
    g.apagar_conversa(id_)
    h.adicionar("user", "tarde demais")
    assert h.salvar() is False
    assert g.listar_conversas() == []


def test_historico_continua_funcionando_com_arquivo_json(tmp_path):
    h = HistoricoConversa(SISTEMA, str(tmp_path / "h.json"))
    h.adicionar("user", "a")
    h.salvar()
    assert HistoricoConversa(SISTEMA, str(tmp_path / "h.json")).mensagens[-1]["content"] == "a"


# ---------------- GerenciadorConversas ----------------

def test_fluxo_completo_da_barra_lateral(g):
    a, b = g.criar_conversa(), g.criar_conversa()
    assert {e["titulo"] for e in g.listar_conversas()} == {"Nova conversa"}
    g.atualizar_titulo_automatico(a, "x" * 100)
    assert g.obter_entrada(a)["titulo"] == "x" * 40 + "..."
    assert g.renomear_conversa(b, "  Física  ") is True
    assert g.renomear_conversa(b, "   ") is False
    g.atualizar_titulo_automatico(b, "não deve trocar")
    assert g.obter_entrada(b)["titulo"] == "Física"
    assert g.alternar_fixado(b) is True
    assert g.listar_conversas()[0]["id"] == b
    g.resetar_titulo(b)
    assert g.obter_entrada(b)["titulo"] == "Nova conversa"
    g.apagar_conversa(a)
    assert [e["id"] for e in g.listar_conversas()] == [b]


def test_titulo_com_quebra_de_linha_vira_uma_linha(g):
    a = g.criar_conversa()
    g.atualizar_titulo_automatico(a, "linha1\nlinha2")
    assert g.obter_entrada(a)["titulo"] == "linha1 linha2"


def test_duas_janelas_veem_o_mesmo_banco(tmp_path):
    pasta = str(tmp_path / "c")
    g1, g2 = GerenciadorConversas(SISTEMA, pasta_base=pasta), GerenciadorConversas(SISTEMA, pasta_base=pasta)
    id_ = g1.criar_conversa()
    g1.renomear_conversa(id_, "Compartilhada")
    assert g2.obter_entrada(id_)["titulo"] == "Compartilhada"
    h = g1.obter_historico(id_)
    h.adicionar("user", "da janela 1")
    h.salvar()
    assert g2.obter_historico(id_).mensagens[-1]["content"] == "da janela 1"


def test_dados_sobrevivem_a_reiniciar_o_programa(tmp_path):
    pasta = str(tmp_path / "c")
    g1 = GerenciadorConversas(SISTEMA, pasta_base=pasta)
    id_ = g1.criar_conversa()
    h = g1.obter_historico(id_)
    h.adicionar("user", "persistida")
    h.salvar()
    del g1, h
    g2 = GerenciadorConversas(SISTEMA, pasta_base=pasta)
    assert g2.obter_historico(id_).mensagens[-1]["content"] == "persistida"


def test_gravacoes_concorrentes_em_varias_conversas_nao_se_perdem(g):
    ids = [g.criar_conversa() for _ in range(4)]
    erros = []

    def escrever(id_):
        try:
            h = g.obter_historico(id_)
            for i in range(15):
                h.adicionar("user", f"{id_}-{i}")
                assert h.salvar() is True
                g.marcar_atualizada(id_)
        except Exception as e:  # noqa
            erros.append(e)

    ts = [threading.Thread(target=escrever, args=(i,)) for i in ids]
    [t.start() for t in ts]
    [t.join() for t in ts]
    assert not erros
    for id_ in ids:
        assert [m["content"] for m in g.obter_historico(id_).mensagens[1:]] == [f"{id_}-{i}" for i in range(15)]


def test_renomear_e_fixar_ao_mesmo_tempo_nao_se_atropelam(g):
    id_ = g.criar_conversa()
    erros = []

    def renomear():
        try:
            for i in range(20):
                g.renomear_conversa(id_, f"t{i}")
        except Exception as e:  # noqa
            erros.append(e)

    def fixar():
        try:
            for _ in range(20):
                g.alternar_fixado(id_)
        except Exception as e:  # noqa
            erros.append(e)

    ts = [threading.Thread(target=renomear), threading.Thread(target=fixar)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    assert not erros
    e = g.obter_entrada(id_)
    assert e["titulo"] == "t19" and e["fixado"] is False   # 20 alternâncias: par volta ao início
