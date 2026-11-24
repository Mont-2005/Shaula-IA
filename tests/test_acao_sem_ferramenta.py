import ctypes
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

if not hasattr(ctypes, "windll"):
    ctypes.windll = MagicMock()
    ctypes.WinDLL = MagicMock()
    ctypes.WINFUNCTYPE = ctypes.CFUNCTYPE

from tools.acao_sem_ferramenta import DetectorAcaoSemFerramenta

SISTEMA = {"role": "system", "content": "sistema"}


# ---------------- detector ----------------

@pytest.mark.parametrize("texto", [
    "Firefox movido para o monitor 1.",
    "Janela do Firefox movida para o monitor 1.",
    "Abrindo Firefox...",
    "O Chrome foi fechado.",
    "Pronto, minimizei... a janela foi minimizada!",
    "Processo Firefox finalizado.",
    "Processo Firefox finalizado novamente.",
    "Volume aumentado para 40%.",
    "Arquivo excluído.",
    "O Discord foi encerrado.",
])
def test_detecta_resposta_que_afirma_acao(texto):
    assert DetectorAcaoSemFerramenta().afirma_acao(texto)


@pytest.mark.parametrize("texto", [
    "",
    None,
    "Olá! Como posso ajudar você hoje?",
    "Não consegui encontrar essa janela.",
    "Qual monitor você quer? O 1 ou o 2?",
    "Não encontrei nenhum processo chamado 'firefox'.",
    "Para mover uma janela de monitor use Win+Shift+Seta. " + "x" * 300 + " movida",
])
def test_nao_marca_conversa_comum_nem_texto_longo(texto):
    assert not DetectorAcaoSemFerramenta().afirma_acao(texto)


# ---------------- dentro do TrabalhadorIA ----------------

def _trabalhador(respostas, com_ferramentas=True, sintese=False):
    import interface

    registro = MagicMock()
    registro.estado_internet.ativa = False
    registro.schemas_openai.return_value = [{"type": "function"}] if com_ferramentas else []
    registro.executar.return_value = "Janela movida para o monitor 1."
    registro.obter.return_value = SimpleNamespace(precisa_de_sintese=sintese)

    t = interface.TrabalhadorIA(
        [SISTEMA, {"role": "user", "content": "mova o firefox para o monitor 1"}],
        registro,
    )
    fila = list(respostas)
    chamadas = []

    def conversar(**p):
        chamadas.append([dict(m) if isinstance(m, dict) else m for m in p["messages"]])
        return fila.pop(0) if len(fila) > 1 else fila[0]

    t._chat = SimpleNamespace(conversar=conversar, cancelar=lambda: None)
    saida = {"resp": [], "erro": []}
    t.resposta_pronta.connect(saida["resp"].append)
    t.erro.connect(saida["erro"].append)
    return t, saida, chamadas, registro


def _resp(conteudo="", ferramenta=False):
    chamada = SimpleNamespace(function=SimpleNamespace(name="mover_programa_monitor", arguments={"nome": "firefox", "numero_monitor": 1}))
    return SimpleNamespace(message=SimpleNamespace(
        content=conteudo, tool_calls=[chamada] if ferramenta else None,
        role="assistant", images=None))


def test_resposta_falsa_e_refeita_e_a_ferramenta_roda():
    t, saida, chamadas, registro = _trabalhador([
        _resp("Firefox movido para o monitor 1."),   # mentira, sem ferramenta
        _resp(ferramenta=True),                      # refaz chamando a ferramenta
    ])
    t.run()
    assert registro.executar.call_count == 1
    # a saída da ferramenta (sem síntese) é a resposta final, sem aviso
    assert saida["resp"] == ["Janela movida para o monitor 1."]
    # a frase falsa não fica no contexto da nova tentativa, a correção sim
    segunda = chamadas[1]
    assert not any("Firefox movido" in str(getattr(m, "content", m.get("content", "") if isinstance(m, dict) else "")) for m in segunda)
    assert any(isinstance(m, dict) and "NÃO chamou nenhuma ferramenta" in m["content"] for m in segunda)


def test_se_o_modelo_insiste_sem_ferramenta_a_resposta_sai_com_aviso():
    t, saida, chamadas, registro = _trabalhador([_resp("Firefox movido para o monitor 1.")])
    t.run()
    assert registro.executar.call_count == 0
    assert len(chamadas) == 2  # uma correção só, sem laço
    assert saida["resp"][0].startswith("Firefox movido para o monitor 1.")
    assert "Não chamei nenhuma ferramenta" in saida["resp"][0]


def test_resposta_depois_de_ferramenta_executada_nao_e_questionada():
    t, saida, chamadas, _ = _trabalhador(
        [_resp(ferramenta=True), _resp("Firefox movido para o monitor 1.")], sintese=True)
    t.run()
    assert saida["resp"] == ["Firefox movido para o monitor 1."]
    assert len(chamadas) == 2


def test_conversa_comum_passa_direto():
    t, saida, chamadas, _ = _trabalhador([_resp("Olá! Tudo bem?")])
    t.run()
    assert saida["resp"] == ["Olá! Tudo bem?"] and len(chamadas) == 1


def test_sem_ferramentas_disponiveis_nao_interfere():
    # mensagem com anexo vai sem schemas: não há ferramenta para cobrar
    t, saida, chamadas, _ = _trabalhador([_resp("Arquivo aberto e resumido.")], com_ferramentas=False)
    t.run()
    assert saida["resp"] == ["Arquivo aberto e resumido."] and len(chamadas) == 1
