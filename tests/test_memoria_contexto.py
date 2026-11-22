import pytest

from tools.contexto import (
    CompactadorHistorico,
    OrcamentoContexto,
    ResumidorHistorico,
)

SISTEMA = {"role": "system", "content": "s" * 5000}


def _user(texto):
    return {"role": "user", "content": texto}


def _ia(texto):
    return {"role": "assistant", "content": texto}


# ---------------- CompactadorHistorico ----------------

def test_compactador_encurta_resposta_longa_da_shaula():
    c = CompactadorHistorico()
    longa = _ia("y" * 2000)
    curta = c.compactar(longa)
    assert curta is not longa
    assert len(curta["content"]) < 700 and "encurtada" in curta["content"]
    assert len(longa["content"]) == 2000          # original intacta


@pytest.mark.parametrize("mensagem", [
    _ia("resposta curta"),
    _user("x" * 2000),                            # fala do usuário nunca é cortada
    {"role": "system", "content": "z" * 2000},
    {"role": "assistant", "content": None},
])
def test_compactador_nao_mexe_no_resto(mensagem):
    assert CompactadorHistorico().compactar(mensagem) is mensagem


# ---------------- ResumidorHistorico ----------------

def test_resumo_traz_o_que_foi_dito_em_ordem():
    r = ResumidorHistorico()
    resumo = r.resumir([
        _user("meu cachorro se chama Thor"),
        _ia("Que nome legal!"),
        _user("moro em Brasília"),
    ])
    assert resumo["role"] == "system"
    texto = resumo["content"]
    assert "Thor" in texto and "Brasília" in texto
    assert texto.index("Thor") < texto.index("Brasília")


def test_resumo_respeita_o_limite_e_prefere_as_mais_recentes():
    r = ResumidorHistorico()
    removidas = [_user(f"fato{i} " + "x" * 200) for i in range(200)]
    resumo = r.resumir(removidas)
    assert len(resumo["content"]) <= r.LIMITE_TOKENS * r.CARACTERES_POR_TOKEN
    assert "fato199" in resumo["content"] and "fato0 " not in resumo["content"]


def test_resumo_vazio_devolve_none():
    assert ResumidorHistorico().resumir([]) is None
    assert ResumidorHistorico().resumir([{"role": "tool", "content": "x"}]) is None


# ---------------- OrcamentoContexto com memória ----------------

def _conversa(n_trocas, tamanho_resposta=300):
    msgs = [SISTEMA]
    for i in range(n_trocas):
        msgs.append(_user(f"p{i} " + "x" * 200))
        msgs.append(_ia(f"r{i} " + "y" * tamanho_resposta))
    msgs.append(_user("o que eu falei no começo?"))
    return msgs


def test_o_que_sai_do_contexto_vira_resumo():
    o = OrcamentoContexto(num_ctx=11264, reserva_resposta=2048)
    msgs = _conversa(40)
    r = o.ajustar(msgs, tokens_ferramentas=4116)
    assert o.descartadas > 0 and o.resumiu
    assert r[0] is msgs[0]
    assert r[1]["role"] == "system" and "RESUMO" in r[1]["content"]
    # a fala do usuário mais recente que saiu do contexto continua visível no resumo
    literais = {m["content"] for m in r}
    saiu = [m["content"] for m in msgs if m["role"] == "user"
            and m["content"] not in literais]
    assert saiu and saiu[-1][:6] in r[1]["content"]
    assert r[-1]["content"] == "o que eu falei no começo?"
    assert o.estimar_mensagens(r) <= o.tokens_disponiveis - 4116


def test_respostas_longas_sao_encurtadas_antes_de_descartar_mensagens():
    o = OrcamentoContexto(num_ctx=11264, reserva_resposta=2048)
    msgs = [SISTEMA]
    for i in range(6):
        msgs.append(_user(f"pergunta{i}"))
        msgs.append(_ia(f"resposta{i} " + "y" * 3000))
    msgs.append(_user("e a primeira pergunta?"))
    r = o.ajustar(msgs, tokens_ferramentas=4116)
    assert o.compactadas > 0
    falas = [m["content"] for m in r if m["role"] == "user"]
    assert "pergunta0" in falas                    # a fala do usuário sobreviveu


def test_nao_cria_resumo_quando_tudo_cabe():
    o = OrcamentoContexto()
    msgs = [SISTEMA, _user("oi")]
    assert o.ajustar(msgs) == msgs
    assert not o.resumiu and o.compactadas == 0


def test_colaboradores_do_orcamento_sao_injetaveis():
    class ResumidorFixo:
        LIMITE_TOKENS = 300
        def resumir(self, removidas, limite_tokens=None):
            return {"role": "system", "content": "RESUMO FIXO"}

    o = OrcamentoContexto(
        num_ctx=11264, reserva_resposta=2048, resumidor=ResumidorFixo()
    )
    r = o.ajustar(_conversa(40), tokens_ferramentas=4116)
    assert r[1]["content"] == "RESUMO FIXO"
