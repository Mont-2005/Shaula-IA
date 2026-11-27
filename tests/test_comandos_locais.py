import pytest

from tools.comandos_locais import ComandosLocais


@pytest.fixture
def comandos():
    return ComandosLocais()


@pytest.mark.parametrize("texto", [
    "sair", "Sair", "SAIR", "Sair.", "sair!", "Feche a Shaula.",
    "feche a shaula", "Encerrar.", "pode sair", "Pode sair.",
    "Pode fechar!", "Shaula, sair.", "Shaula pode encerrar",
    "  sair  ",
])
def test_comandos_de_saida_incluindo_os_falados_com_pontuacao(comandos, texto):
    assert comandos.eh_saida(texto)


@pytest.mark.parametrize("texto", [
    "", "shaula", "não saia", "saia daqui", "como faço para sair?",
    "feche o spotify", "feche a janela", "pode sair do chrome",
    "sair e abrir o chrome",
])
def test_nao_e_comando_de_saida(comandos, texto):
    assert not comandos.eh_saida(texto)


@pytest.mark.parametrize("texto", [
    "excluir conversa", "Apagar Conversa", "esquecer tudo",
    "Excluir histórico", "apagar memória", "  limpar conversa ",
])
def test_apagar_conversa_com_a_frase_exata(comandos, texto):
    assert comandos.eh_apagar_conversa(texto)


@pytest.mark.parametrize("texto", [
    "esquecer tudo.",              # com pontuação: pode ser voz mal reconhecida
    "Esquecer tudo!",
    "shaula, esquecer tudo",
    "pode esquecer tudo",
    "esquecer tudo sobre isso",
    "sair",
    "",
])
def test_apagar_conversa_nao_tolera_pontuacao_nem_palavras_a_mais(comandos, texto):
    assert not comandos.eh_apagar_conversa(texto)
