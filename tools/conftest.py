import pytest


@pytest.fixture(autouse=True)
def _isolar_pasta_do_usuario(tmp_path_factory, monkeypatch):
    """
    Nenhum teste pode tocar a pasta real ~/.shaula (conversas, cache,
    nível de esforço, lembretes...). Sem isto, testes que criam um
    RegistroFerramentas ou uma janela leriam — e, no caso dos
    lembretes, até ENTREGARIAM — dados de verdade do usuário.
    """

    # Pasta própria (e não o tmp_path do teste), para não aparecer
    # dentro do diretório que o teste inspeciona.
    pasta = tmp_path_factory.mktemp("home_isolada")

    monkeypatch.setenv("HOME", str(pasta))

    monkeypatch.setenv("USERPROFILE", str(pasta))
