import ctypes
from unittest.mock import MagicMock

import pytest

if not hasattr(ctypes, "windll"):
    ctypes.windll = MagicMock()
    ctypes.WinDLL = MagicMock()
    ctypes.WINFUNCTYPE = ctypes.CFUNCTYPE

from tools.confirmacao import ConfirmadorFixo
from tools.registro import RegistroFerramentas


def _registro(confirmador=None, permitidas=("finalizar_processo", "calcular")):
    return RegistroFerramentas(
        ferramentas_permitidas=set(permitidas),
        confirmador=confirmador,
    )


def test_parametro_obrigatorio_faltando_e_explicado():
    resposta = _registro().executar("calcular", {})
    assert "Faltou o parâmetro obrigatório 'expressao'" in resposta


def test_nao_pede_confirmacao_para_chamada_que_vai_falhar():
    perguntas = []

    class Confirmador:
        def confirmar(self, pedido):
            perguntas.append(pedido)
            return True

    resposta = _registro(Confirmador()).executar("finalizar_processo", {})
    assert "Faltou o parâmetro" in resposta
    assert perguntas == []                      # antes perguntava "finalizar ''?"


def test_keyerror_de_dentro_da_ferramenta_nao_vira_faltou_parametro(monkeypatch):
    registro = _registro()
    ferramenta = registro.obter("calcular")

    def quebrada(argumentos):
        return {}["chave_interna"]              # defeito da ferramenta, não do modelo

    monkeypatch.setattr(ferramenta, "executar", quebrada)

    with pytest.raises(KeyError):               # sobe como erro de execução, com a causa real
        registro.executar("calcular", {"expressao": "2+2"})


def test_chamada_normal_continua_funcionando():
    assert _registro().executar("calcular", {"expressao": "2+2"}) == "Resultado: 4"
