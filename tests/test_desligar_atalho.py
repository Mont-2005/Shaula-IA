import pytest

from tools.intencao_desligar import DetectorDesligar


@pytest.fixture
def detector():
    return DetectorDesligar()


@pytest.mark.parametrize("texto,esperado", [
    ("desligue o computador", {}),
    ("Shaula, desliga o PC agora", {"segundos": 0}),
    ("desligar o computador em 30 segundos", {"segundos": 30}),
    ("desligue o pc daqui a 2 minutos", {"segundos": 120}),
    ("desligue o notebook em 1 hora", {"segundos": 3600}),
    ("você pode desligar o pc?", {}),
])
def test_pedidos_claros(detector, texto, esperado):
    assert detector.argumentos(texto) == esperado


@pytest.mark.parametrize("texto", [
    "desligar o computador é perigoso?",
    "desligue o computador depois de baixar o arquivo",
    "desligue o pc e abra o chrome",
    "abra o chrome e depois desligue o computador",
    "se der erro desligue o computador",
    "desligue o computador em 5 minutos e 30 segundos",
    "como desligar o computador?",
    "não desligue o computador",
    "cancela o desligamento do pc",
    "o que acontece se eu desligar o computador",
    "abre o chrome",
    "",
])
def test_nao_dispara(detector, texto):
    assert detector.argumentos(texto) is None


def test_colaboradores_sao_injetaveis():

    class InterpretadorFixo:
        def interpretar(self, texto_normalizado):
            return {"segundos": 7}

        def sem_tempo(self, texto_normalizado):
            return texto_normalizado

    detector = DetectorDesligar(interpretador=InterpretadorFixo())

    assert detector.argumentos("desligue o computador") == {"segundos": 7}
