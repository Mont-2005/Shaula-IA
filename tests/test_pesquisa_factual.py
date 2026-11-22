import pytest

from tools.pesquisa import DetectorPerguntaFactual


@pytest.mark.parametrize("texto", [
    "quem descobriu o Brasil?",
    "qual a capital da França?",
    "quanto custa um iPhone?",
    "como eu faço um bolo?",
    "existe vida em Marte?",
    "o que aconteceu antes da Segunda Guerra?",
    "quando foi a Revolução Francesa?",
])
def test_pergunta_factual_continua_pesquisando(texto):
    assert DetectorPerguntaFactual.parece_factual(texto) is True


@pytest.mark.parametrize("texto", [
    "e quando isso aconteceu?",
    "e o segundo?",
    "mas por que?",
    "então qual é a diferença?",
    "o que eu falei no começo?",
    "qual era o nome que mencionei?",
    "o que eu disse antes?",
    "por que isso acontece?",
    "como funciona isso?",
    "o que conversamos mais cedo?",
    "lembra do que combinamos?",
])
def test_acompanhamento_e_pergunta_sobre_a_conversa_nao_pesquisa_na_web(texto):
    assert DetectorPerguntaFactual.parece_factual(texto) is False
