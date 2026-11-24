"""
Visualizador do banco da Shaula (somente leitura).

Mostra, em duas tabelas, o que está gravado em
~/.shaula/conversas/shaula.db e se atualiza sozinho a cada segundo.
Só executa SELECT: não altera nada no banco.

Fica na pasta tests/ e é aberto pelo "Ver Banco.bat", na raiz do projeto.
Não depende de nenhum outro arquivo do projeto, então pode rodar de qualquer pasta.
"""
import os
import sqlite3
import sys

CAMINHO_BANCO = os.path.expanduser("~/.shaula/conversas/shaula.db")

SQL_CONVERSAS = (
    "SELECT id, titulo, fixado, atualizado_em "
    "FROM conversas ORDER BY atualizado_em DESC"
)
SQL_MENSAGENS = (
    "SELECT id, conversa_id, papel, substr(conteudo, 1, 60) "
    "FROM mensagens ORDER BY id"
)


def ler_banco(caminho=CAMINHO_BANCO):
    """Devolve (conversas, mensagens) ou (None, None) se o banco ainda
    não existe / não tem as tabelas."""
    if not os.path.exists(caminho):
        return None, None
    try:
        con = sqlite3.connect(caminho, timeout=5)
        try:
            con.execute("PRAGMA query_only = ON")
            conversas = [tuple(l) for l in con.execute(SQL_CONVERSAS)]
            mensagens = [tuple(l) for l in con.execute(SQL_MENSAGENS)]
        finally:
            con.close()
        return conversas, mensagens
    except sqlite3.Error:
        return None, None


def main():
    from PySide6.QtCore import QTimer
    from PySide6.QtGui import QFont
    from PySide6.QtWidgets import (
        QApplication, QHeaderView, QLabel, QTableWidget,
        QTableWidgetItem, QVBoxLayout, QWidget,
    )

    app = QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", 13))

    janela = QWidget()
    janela.setWindowTitle("Shaula - Banco de dados (somente leitura)")
    janela.resize(980, 640)
    layout = QVBoxLayout(janela)

    def criar_tabela(titulo, colunas):
        layout.addWidget(QLabel(f"<b>{titulo}</b>"))
        tabela = QTableWidget(0, len(colunas))
        tabela.setHorizontalHeaderLabels(colunas)
        tabela.setEditTriggers(QTableWidget.NoEditTriggers)
        tabela.setSelectionBehavior(QTableWidget.SelectRows)
        tabela.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeToContents
        )
        tabela.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(tabela)
        return tabela

    tab_conversas = criar_tabela(
        "Tabela conversas", ["id", "titulo", "fixado", "atualizado_em"]
    )
    tab_mensagens = criar_tabela(
        "Tabela mensagens", ["id", "conversa_id", "papel", "conteudo"]
    )
    aviso = QLabel("")
    layout.addWidget(aviso)

    ultimo = {"dados": object()}

    def preencher(tabela, linhas):
        tabela.setRowCount(len(linhas))
        for i, linha in enumerate(linhas):
            for j, valor in enumerate(linha):
                tabela.setItem(i, j, QTableWidgetItem(str(valor)))

    def atualizar():
        conversas, mensagens = ler_banco()
        if conversas is None:
            aviso.setText(
                "Banco ainda não criado: abra a Shaula e crie uma conversa."
            )
            dados = None
        else:
            aviso.setText(
                f"{len(conversas)} conversa(s) · {len(mensagens)} mensagem(ns)"
            )
            dados = (conversas, mensagens)
        if dados == ultimo["dados"]:
            return  # nada mudou: evita piscar a tela
        ultimo["dados"] = dados
        preencher(tab_conversas, dados[0] if dados else [])
        preencher(tab_mensagens, dados[1] if dados else [])

    atualizar()
    timer = QTimer(janela)
    timer.timeout.connect(atualizar)
    timer.start(1000)

    janela.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
