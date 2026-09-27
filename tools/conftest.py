import os

# Roda sem precisar de um display de verdade (funciona tanto no
# Windows do Gabriel quanto num ambiente de CI sem tela). Só é
# aplicado se a variável não tiver sido definida por fora —
# assim quem quiser rodar com uma plataforma diferente ainda
# pode.
os.environ.setdefault(
    "QT_QPA_PLATFORM",
    "offscreen"
)

import pytest

from PySide6.QtGui import QGuiApplication


@pytest.fixture(scope="session", autouse=True)
def aplicativo_qt():
    """
    QImage/QBuffer (usados por GerenciadorAnexos) exigem uma
    QGuiApplication viva no processo, mesmo sem abrir nenhuma
    janela. Uma instância por sessão de testes é suficiente —
    criar mais de uma no mesmo processo não é suportado pelo Qt.
    """

    aplicativo = (
        QGuiApplication.instance()
        or QGuiApplication([])
    )

    yield aplicativo
