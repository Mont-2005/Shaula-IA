import os

import pytest
from PySide6.QtGui import QImage, qRgb

from tools.anexos import (
    GerenciadorAnexos,
    DependenciaFaltando,
    EstrategiaImagem,
)


@pytest.fixture
def gerenciador():
    return GerenciadorAnexos()


def _criar_imagem_jpg(
    caminho,
    largura=800,
    altura=600
):

    imagem = QImage(
        largura,
        altura,
        QImage.Format_RGB32
    )

    imagem.fill(
        qRgb(20, 130, 210)
    )

    imagem.save(
        str(caminho),
        "JPG"
    )


class TestEstrategiaImagem:

    def test_carrega_imagem_valida(
        self,
        gerenciador,
        tmp_path
    ):

        caminho = tmp_path / "foto.jpg"

        _criar_imagem_jpg(
            caminho
        )

        anexo = gerenciador.carregar(
            str(caminho)
        )

        assert anexo is not None
        assert anexo.eh_imagem
        assert anexo.texto is None
        assert len(anexo.imagens) == 1
        assert anexo.nome_arquivo == "foto.jpg"

    def test_redimensiona_imagem_grande(
        self,
        gerenciador,
        tmp_path
    ):

        caminho = tmp_path / "grande.jpg"

        _criar_imagem_jpg(
            caminho,
            largura=4000,
            altura=3000
        )

        anexo = gerenciador.carregar(
            str(caminho)
        )

        resultado = QImage()

        resultado.loadFromData(
            anexo.imagens[0]
        )

        assert (
            max(resultado.width(), resultado.height())
            <= EstrategiaImagem.LADO_MAXIMO_PX
        )

    def test_rejeita_arquivo_corrompido(
        self,
        gerenciador,
        tmp_path
    ):

        caminho = tmp_path / "falso.png"

        caminho.write_bytes(
            b"isso nao e uma imagem de verdade"
        )

        assert gerenciador.carregar(str(caminho)) is None

    def test_respeita_limite_de_tamanho(
        self,
        gerenciador,
        tmp_path,
        monkeypatch
    ):

        caminho = tmp_path / "foto.jpg"

        _criar_imagem_jpg(
            caminho
        )

        monkeypatch.setattr(
            EstrategiaImagem,
            "TAMANHO_MAXIMO_MB",
            0
        )

        assert gerenciador.carregar(str(caminho)) is None


class TestEstrategiaTexto:

    def test_le_arquivo_de_codigo(
        self,
        gerenciador,
        tmp_path
    ):

        caminho = tmp_path / "script.py"

        caminho.write_text(
            "def soma(a, b):\n    return a + b\n",
            encoding="utf-8"
        )

        anexo = gerenciador.carregar(
            str(caminho)
        )

        assert anexo is not None
        assert not anexo.eh_imagem
        assert "def soma" in anexo.texto

    def test_trunca_arquivo_muito_longo(
        self,
        gerenciador,
        tmp_path
    ):

        from tools.anexos import EstrategiaTexto

        caminho = tmp_path / "gigante.txt"

        caminho.write_text(
            "x" * (EstrategiaTexto.CARACTERES_MAXIMOS + 5000),
            encoding="utf-8"
        )

        anexo = gerenciador.carregar(
            str(caminho)
        )

        assert "truncado" in anexo.texto

    def test_le_com_codificacao_latin1(
        self,
        gerenciador,
        tmp_path
    ):

        caminho = tmp_path / "acentos.txt"

        caminho.write_bytes(
            "café com açúcar".encode("latin-1")
        )

        anexo = gerenciador.carregar(
            str(caminho)
        )

        assert anexo is not None
        assert "café" in anexo.texto


class TestEstrategiaPDF:

    def test_pdf_de_texto_vira_texto(
        self,
        gerenciador,
        tmp_path
    ):

        import pymupdf as fitz

        caminho = tmp_path / "artigo.pdf"

        documento = fitz.open()

        pagina = documento.new_page()

        pagina.insert_text(
            (72, 72),
            "Conteúdo de teste bem extenso para simular um "
            "PDF de texto de verdade, não escaneado. " * 5
        )

        documento.save(str(caminho))
        documento.close()

        anexo = gerenciador.carregar(
            str(caminho)
        )

        assert anexo is not None
        assert not anexo.eh_imagem
        assert "Conteúdo de teste" in anexo.texto

    def test_pdf_escaneado_vira_imagem(
        self,
        gerenciador,
        tmp_path
    ):

        import pymupdf as fitz

        caminho = tmp_path / "escaneado.pdf"

        documento = fitz.open()

        pagina = documento.new_page()

        pixmap_cor = fitz.Pixmap(
            fitz.csRGB,
            fitz.IRect(0, 0, 200, 200)
        )

        pixmap_cor.set_rect(
            pixmap_cor.irect,
            (200, 50, 50)
        )

        pagina.insert_image(
            pagina.rect,
            pixmap=pixmap_cor
        )

        documento.save(str(caminho))
        documento.close()

        anexo = gerenciador.carregar(
            str(caminho)
        )

        assert anexo is not None
        assert anexo.eh_imagem
        assert len(anexo.imagens) >= 1

    def test_acusa_dependencia_faltando(
        self,
        gerenciador,
        tmp_path,
        monkeypatch
    ):

        caminho = tmp_path / "qualquer.pdf"

        caminho.write_bytes(
            b"%PDF-1.4 conteudo irrelevante para este teste"
        )

        import builtins

        importar_de_verdade = builtins.__import__

        def importar_falso(
            nome,
            *args,
            **kwargs
        ):

            if nome == "pymupdf":
                raise ImportError("simulado no teste")

            return importar_de_verdade(
                nome,
                *args,
                **kwargs
            )

        monkeypatch.setattr(
            builtins,
            "__import__",
            importar_falso
        )

        with pytest.raises(DependenciaFaltando) as erro:
            gerenciador.carregar(str(caminho))

        assert erro.value.pacote_pip == "pymupdf"


class TestEstrategiaVideo:

    def test_extrai_frames_do_video(
        self,
        gerenciador,
        tmp_path
    ):

        cv2 = pytest.importorskip("cv2")
        import numpy as np

        caminho = tmp_path / "clipe.mp4"

        codec = cv2.VideoWriter_fourcc(*"mp4v")

        gravador = cv2.VideoWriter(
            str(caminho),
            codec,
            10.0,
            (320, 240)
        )

        for indice in range(30):

            quadro = np.full(
                (240, 320, 3),
                (indice * 8) % 255,
                dtype=np.uint8
            )

            gravador.write(quadro)

        gravador.release()

        anexo = gerenciador.carregar(
            str(caminho)
        )

        assert anexo is not None
        assert anexo.eh_imagem
        assert 1 <= len(anexo.imagens) <= 6
        assert "frame" in anexo.nota_exibicao


class TestGerenciadorAnexos:

    def test_recusa_arquivo_de_tipo_desconhecido(
        self,
        gerenciador,
        tmp_path
    ):

        caminho = tmp_path / "pacote.zip"

        caminho.write_bytes(
            b"PK\x03\x04 nao e nada que a shaula entenda"
        )

        assert gerenciador.carregar(str(caminho)) is None

    def test_recusa_caminho_inexistente(
        self,
        gerenciador
    ):

        assert gerenciador.carregar(
            "/caminho/que/nao/existe.png"
        ) is None

    def test_filtro_dialogo_inclui_todos_os_tipos(
        self,
        gerenciador
    ):

        filtro = gerenciador.filtro_dialogo()

        for extensao in (
            "*.png", "*.pdf", "*.mp4", "*.py", "*.txt"
        ):
            assert extensao in filtro

    def test_caminho_valido(
        self,
        gerenciador,
        tmp_path
    ):

        assert gerenciador.caminho_valido("foto.png")
        assert gerenciador.caminho_valido("relatorio.pdf")
        assert gerenciador.caminho_valido("clipe.mp4")
        assert gerenciador.caminho_valido("script.py")
        assert not gerenciador.caminho_valido("pacote.zip")
