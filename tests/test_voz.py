import importlib.util
import sys
import threading
import time
import types

import numpy as np
import pytest

from tools.voz import (
    TAXA_AMOSTRAGEM,
    FonteAudio,
    Gravador,
    GerenciadorVoz,
    LimpadorTranscricao,
    MicrofoneSounddevice,
    ReconhecedorFala,
    ReconhecedorFasterWhisper,
    VozIndisponivel,
    calcular_nivel,
    normalizar_volume,
)


BLOCO_MS = 30
AMOSTRAS_POR_BLOCO = int(TAXA_AMOSTRAGEM * BLOCO_MS / 1000)


def _bloco(amplitude):
    """Bloco int16 de uma senoide com a amplitude dada (0 a 1)."""

    t = np.arange(AMOSTRAS_POR_BLOCO)

    onda = np.sin(2 * np.pi * 220 * t / TAXA_AMOSTRAGEM)

    return (onda * amplitude * 32767).astype(np.int16)


def _blocos(amplitude, duracao_ms):

    return [
        _bloco(amplitude)
        for _ in range(int(duracao_ms / BLOCO_MS))
    ]


class FonteFalsa(FonteAudio):
    """
    Entrega uma lista de blocos prontos, na ordem. `ao_ler`, se
    passado, é chamado a cada leitura com o índice do bloco — os
    testes usam isso para "apertar parar" no meio da gravação.
    """

    def __init__(self, blocos, ao_ler=None):

        self.blocos = list(blocos)
        self.ao_ler = ao_ler
        self.indice = 0
        self.abriu = False
        self.fechou = False

    def abrir(self):
        self.abriu = True

    def ler_bloco(self):

        if self.indice >= len(self.blocos):
            raise AssertionError(
                "o gravador pediu mais áudio do que o teste tinha"
            )

        bloco = self.blocos[self.indice]

        if self.ao_ler is not None:
            self.ao_ler(self.indice)

        self.indice += 1

        return bloco

    def fechar(self):
        self.fechou = True


def _parar_no_bloco(numero_do_bloco):
    """Devolve (evento_parar, ao_ler) que aciona o evento no bloco N."""

    parar = threading.Event()

    def ao_ler(indice):

        if indice == numero_do_bloco:
            parar.set()

    return parar, ao_ler


class TestCalcularNivel:

    def test_silencio_e_zero(self):

        assert calcular_nivel(np.zeros(480, dtype=np.int16)) == 0.0

    def test_bloco_vazio_e_zero(self):

        assert calcular_nivel(np.array([], dtype=np.int16)) == 0.0

    def test_cresce_com_a_amplitude(self):

        assert calcular_nivel(_bloco(0.5)) > calcular_nivel(_bloco(0.05))

    def test_senoide_cheia_fica_perto_de_0_7(self):

        assert 0.65 < calcular_nivel(_bloco(1.0)) < 0.75


class TestNormalizarVolume:

    def test_amplifica_audio_baixo(self):

        audio = np.full(1000, 0.1, dtype=np.float32)

        resultado = normalizar_volume(audio)

        assert np.abs(resultado).max() == pytest.approx(0.8, abs=0.01)

    def test_nao_reduz_audio_alto(self):

        audio = np.full(1000, 0.95, dtype=np.float32)

        resultado = normalizar_volume(audio)

        assert np.array_equal(resultado, audio)

    def test_nao_mexe_quando_o_ganho_seria_irrelevante(self):

        audio = np.full(1000, 0.7, dtype=np.float32)

        assert np.array_equal(normalizar_volume(audio), audio)

    def test_limita_o_ganho_para_nao_explodir_ruido(self):

        audio = np.full(1000, 0.01, dtype=np.float32)

        resultado = normalizar_volume(audio)

        assert np.abs(resultado).max() == pytest.approx(0.08, abs=0.001)

    def test_silencio_total_fica_intacto(self):

        audio = np.zeros(1000, dtype=np.float32)

        assert np.array_equal(normalizar_volume(audio), audio)

    def test_nunca_passa_de_um(self):

        audio = np.array([0.3, -0.3, 0.1], dtype=np.float32)

        assert np.abs(normalizar_volume(audio)).max() <= 1.0


class TestGravador:

    def test_grava_ate_mandarem_parar(self):

        blocos = _blocos(0.4, 3000)

        parar, ao_ler = _parar_no_bloco(40)

        fonte = FonteFalsa(blocos, ao_ler)

        audio = Gravador(fonte).gravar(parar=parar)

        # O bloco 40 é lido e só então o gravador vê o pedido.
        assert len(audio) == 41 * AMOSTRAS_POR_BLOCO
        assert fonte.indice == 41

    def test_nao_para_sozinho_com_silencio_longo_no_meio(self):

        blocos = (
            _blocos(0.4, 1500)
            + _blocos(0.0, 5000)   # 5 s de pausa
            + _blocos(0.4, 1500)
        )

        parar, ao_ler = _parar_no_bloco(len(blocos) - 1)

        fonte = FonteFalsa(blocos, ao_ler)

        audio = Gravador(fonte).gravar(parar=parar)

        assert len(audio) == len(blocos) * AMOSTRAS_POR_BLOCO

    def test_nao_para_sozinho_com_silencio_no_fim(self):

        blocos = _blocos(0.4, 1000) + _blocos(0.0, 8000)

        parar, ao_ler = _parar_no_bloco(len(blocos) - 1)

        fonte = FonteFalsa(blocos, ao_ler)

        audio = Gravador(fonte).gravar(parar=parar)

        assert len(audio) == len(blocos) * AMOSTRAS_POR_BLOCO

    def test_devolve_float32_entre_menos_um_e_um(self):

        blocos = _blocos(0.4, 1000)

        parar, ao_ler = _parar_no_bloco(len(blocos) - 1)

        audio = Gravador(FonteFalsa(blocos, ao_ler)).gravar(parar=parar)

        assert audio.dtype == np.float32
        assert np.abs(audio).max() <= 1.0

    def test_sobe_o_volume_de_gravacao_baixa(self):

        blocos = _blocos(0.15, 1000)

        parar, ao_ler = _parar_no_bloco(len(blocos) - 1)

        audio = Gravador(FonteFalsa(blocos, ao_ler)).gravar(parar=parar)

        # Pico de 0,15 sobe até perto do alvo de 0,8.
        assert 0.75 < np.abs(audio).max() <= 0.8

    def test_informa_o_volume_de_cada_bloco(self):

        blocos = _blocos(0.4, 300) + _blocos(0.0, 300)

        parar, ao_ler = _parar_no_bloco(len(blocos) - 1)

        niveis = []

        Gravador(FonteFalsa(blocos, ao_ler)).gravar(
            parar=parar,
            ao_nivel=niveis.append
        )

        assert len(niveis) == len(blocos)
        assert niveis[0] > 0.2
        assert niveis[-1] == 0.0

    def test_abre_e_fecha_a_fonte(self):

        blocos = _blocos(0.4, 1000)

        parar, ao_ler = _parar_no_bloco(len(blocos) - 1)

        fonte = FonteFalsa(blocos, ao_ler)

        Gravador(fonte).gravar(parar=parar)

        assert fonte.abriu
        assert fonte.fechou

    def test_fecha_a_fonte_mesmo_se_a_leitura_falhar(self):

        class FonteQuebrada(FonteFalsa):

            def ler_bloco(self):
                raise OSError("microfone desconectado")

        fonte = FonteQuebrada([])

        with pytest.raises(OSError):
            Gravador(fonte).gravar()

        assert fonte.fechou

    def test_cancelamento_descarta_tudo(self):

        blocos = _blocos(0.4, 3000)

        cancelado = threading.Event()

        def ao_ler(indice):

            if indice == 20:
                cancelado.set()

        fonte = FonteFalsa(blocos, ao_ler)

        assert Gravador(fonte).gravar(cancelado=cancelado) is None
        assert fonte.fechou

    def test_cancelado_antes_de_comecar_nao_le_nada(self):

        fonte = FonteFalsa(_blocos(0.4, 1000))

        cancelado = threading.Event()
        cancelado.set()

        assert Gravador(fonte).gravar(cancelado=cancelado) is None
        assert fonte.indice == 0

    def test_ninguem_falou_devolve_none(self):

        blocos = _blocos(0.0, 2000)

        parar, ao_ler = _parar_no_bloco(len(blocos) - 1)

        assert (
            Gravador(FonteFalsa(blocos, ao_ler)).gravar(parar=parar)
            is None
        )

    def test_toque_acidental_curto_demais_devolve_none(self):

        blocos = _blocos(0.4, 120)

        parar, ao_ler = _parar_no_bloco(len(blocos) - 1)

        assert (
            Gravador(FonteFalsa(blocos, ao_ler)).gravar(parar=parar)
            is None
        )

    def test_teto_de_seguranca_de_tempo(self):

        blocos = _blocos(0.4, 5000)

        fonte = FonteFalsa(blocos)

        audio = Gravador(
            fonte,
            duracao_maxima_s=1.0
        ).gravar()

        duracao = len(audio) / TAXA_AMOSTRAGEM

        assert 1.0 <= duracao < 1.1
        assert fonte.fechou


class TestLimpadorTranscricao:

    def setup_method(self):

        self.limpador = LimpadorTranscricao()

    def test_texto_normal_passa(self):

        assert (
            self.limpador.limpar("Abre o Discord.")
            == "Abre o Discord."
        )

    def test_vazio_vira_none(self):

        assert self.limpador.limpar("") is None
        assert self.limpador.limpar("   ") is None
        assert self.limpador.limpar(None) is None

    def test_so_pontuacao_vira_none(self):

        assert self.limpador.limpar("...") is None
        assert self.limpador.limpar(" . ") is None

    def test_alucinacao_conhecida_vira_none(self):

        assert (
            self.limpador.limpar(
                "Legendas pela comunidade Amara.org"
            )
            is None
        )

        assert (
            self.limpador.limpar("Obrigado por assistir!")
            is None
        )

    def test_remove_alucinacao_misturada_com_fala_real(self):

        resultado = self.limpador.limpar(
            "Abre o bloco de notas. Obrigado por assistir"
        )

        assert resultado is not None
        assert "assistir" not in resultado.lower()
        assert "bloco de notas" in resultado.lower()

    def test_corrige_grafias_do_nome_da_assistente(self):

        assert (
            self.limpador.limpar("Xaula, abre o Chrome")
            == "Shaula, abre o Chrome"
        )

        assert (
            self.limpador.limpar("chaula pesquisa o clima")
            == "Shaula pesquisa o clima"
        )

    def test_rejeita_eco_do_prompt_inicial(self):

        prompt = (
            "Comandos para a assistente Shaula: abrir e fechar "
            "programas, pesquisar na internet."
        )

        assert (
            self.limpador.limpar(
                "abrir e fechar programas",
                prompt_inicial=prompt
            )
            is None
        )

    def test_nao_rejeita_comando_parecido_com_o_prompt(self):

        prompt = (
            "Comandos para a assistente Shaula: abrir e fechar "
            "programas, pesquisar na internet."
        )

        assert (
            self.limpador.limpar(
                "pesquisar o preço do dólar",
                prompt_inicial=prompt
            )
            == "pesquisar o preço do dólar"
        )


class ReconhecedorFalso(ReconhecedorFala):

    def __init__(
        self,
        texto="abre o discord",
        ja_carregado=True,
        ao_transcrever=None
    ):

        self.texto = texto
        self._carregado = ja_carregado
        self.ao_transcrever = ao_transcrever
        self.audios_recebidos = []
        self.cargas = []

    @property
    def carregado(self):
        return self._carregado

    def carregar_modelo(self, somente_local=False):

        self.cargas.append(somente_local)
        self._carregado = True

    def transcrever(
        self,
        audio,
        taxa=TAXA_AMOSTRAGEM
    ):

        self.audios_recebidos.append(audio)

        if self.ao_transcrever is not None:
            self.ao_transcrever()

        return self.texto


class GravadorFalso:

    def __init__(self, audio, niveis=()):

        self.audio = audio
        self.niveis = niveis
        self.recebeu = None

    def gravar(
        self,
        parar=None,
        cancelado=None,
        ao_nivel=None
    ):

        self.recebeu = (parar, cancelado, ao_nivel)

        if ao_nivel is not None:

            for nivel in self.niveis:
                ao_nivel(nivel)

        return self.audio


AUDIO_QUALQUER = np.ones(1000, dtype=np.float32) * 0.1


class TestGerenciadorVoz:

    def test_fluxo_completo_devolve_o_texto_limpo(self):

        gerenciador = GerenciadorVoz(
            gravador=GravadorFalso(AUDIO_QUALQUER),
            reconhecedor=ReconhecedorFalso("xaula abre o discord")
        )

        assert (
            gerenciador.escutar()
            == "Shaula abre o discord"
        )

    def test_repassa_parar_cancelado_e_nivel_ao_gravador(self):

        gravador = GravadorFalso(
            AUDIO_QUALQUER,
            niveis=(0.1, 0.2)
        )

        parar = threading.Event()
        cancelado = threading.Event()
        niveis = []

        GerenciadorVoz(
            gravador=gravador,
            reconhecedor=ReconhecedorFalso()
        ).escutar(
            parar=parar,
            cancelado=cancelado,
            notificar_nivel=niveis.append
        )

        assert gravador.recebeu[0] is parar
        assert gravador.recebeu[1] is cancelado
        assert niveis == [0.1, 0.2]

    def test_avisa_os_estados_na_ordem(self):

        estados = []

        gerenciador = GerenciadorVoz(
            gravador=GravadorFalso(AUDIO_QUALQUER),
            reconhecedor=ReconhecedorFalso()
        )

        gerenciador.escutar(
            notificar_estado=estados.append
        )

        assert estados == ["ouvindo", "transcrevendo"]

    def test_avisa_preparando_so_quando_o_modelo_nao_estava_carregado(self):

        estados = []

        reconhecedor = ReconhecedorFalso(
            ja_carregado=False
        )

        gerenciador = GerenciadorVoz(
            gravador=GravadorFalso(AUDIO_QUALQUER),
            reconhecedor=reconhecedor
        )

        gerenciador.escutar(
            notificar_estado=estados.append
        )

        # A carga acontece durante a gravação: "preparando" só
        # aparece se ela ainda não terminou quando a fala acaba.
        assert estados[0] == "ouvindo"
        assert estados[-1] == "transcrevendo"
        assert reconhecedor.cargas == [False]

        estados.clear()

        gerenciador.escutar(
            notificar_estado=estados.append
        )

        assert estados == ["ouvindo", "transcrevendo"]
        assert reconhecedor.cargas == [False]

    def test_ninguem_falou_devolve_none_sem_transcrever(self):

        reconhecedor = ReconhecedorFalso()

        gerenciador = GerenciadorVoz(
            gravador=GravadorFalso(None),
            reconhecedor=reconhecedor
        )

        assert gerenciador.escutar() is None
        assert reconhecedor.audios_recebidos == []

    def test_transcricao_alucinada_devolve_none(self):

        gerenciador = GerenciadorVoz(
            gravador=GravadorFalso(AUDIO_QUALQUER),
            reconhecedor=ReconhecedorFalso(
                "Legendas pela comunidade Amara.org"
            )
        )

        assert gerenciador.escutar() is None

    def test_cancelado_antes_de_comecar_nao_grava(self):

        gravador = GravadorFalso(AUDIO_QUALQUER)

        cancelado = threading.Event()
        cancelado.set()

        gerenciador = GerenciadorVoz(
            gravador=gravador,
            reconhecedor=ReconhecedorFalso()
        )

        assert gerenciador.escutar(cancelado=cancelado) is None
        assert gravador.recebeu is None

    def test_cancelado_durante_a_gravacao_nao_transcreve(self):

        cancelado = threading.Event()

        class GravadorQueCancela:

            def gravar(self, parar=None, cancelado=None, ao_nivel=None):

                cancelado_externo.set()

                return AUDIO_QUALQUER

        cancelado_externo = cancelado

        reconhecedor = ReconhecedorFalso()

        gerenciador = GerenciadorVoz(
            gravador=GravadorQueCancela(),
            reconhecedor=reconhecedor
        )

        assert gerenciador.escutar(cancelado=cancelado) is None
        assert reconhecedor.audios_recebidos == []

    def test_cancelado_durante_a_transcricao_descarta_o_resultado(self):

        cancelado = threading.Event()

        reconhecedor = ReconhecedorFalso(
            "abre o discord",
            ao_transcrever=cancelado.set
        )

        gerenciador = GerenciadorVoz(
            gravador=GravadorFalso(AUDIO_QUALQUER),
            reconhecedor=reconhecedor
        )

        assert gerenciador.escutar(cancelado=cancelado) is None
        assert len(reconhecedor.audios_recebidos) == 1

    def test_propaga_voz_indisponivel(self):

        class GravadorSemMicrofone:

            def gravar(self, parar=None, cancelado=None, ao_nivel=None):

                raise VozIndisponivel(
                    "sem microfone"
                )

        gerenciador = GerenciadorVoz(
            gravador=GravadorSemMicrofone(),
            reconhecedor=ReconhecedorFalso()
        )

        with pytest.raises(VozIndisponivel):
            gerenciador.escutar()


class TestPreAquecimento:

    def test_carrega_o_modelo_em_segundo_plano_so_com_arquivos_locais(self):

        reconhecedor = ReconhecedorFalso(ja_carregado=False)

        gerenciador = GerenciadorVoz(
            gravador=GravadorFalso(AUDIO_QUALQUER),
            reconhecedor=reconhecedor
        )

        gerenciador.pre_aquecer().join(2)

        assert reconhecedor.carregado
        assert reconhecedor.cargas == [True]

    def test_nao_bloqueia_quem_chamou(self):

        class ReconhecedorLento(ReconhecedorFalso):

            def carregar_modelo(self, somente_local=False):

                time.sleep(0.5)

                super().carregar_modelo(somente_local)

        gerenciador = GerenciadorVoz(
            gravador=GravadorFalso(AUDIO_QUALQUER),
            reconhecedor=ReconhecedorLento(ja_carregado=False)
        )

        inicio = time.time()

        fio = gerenciador.pre_aquecer()

        assert time.time() - inicio < 0.3

        fio.join(2)

    def test_engole_falha_de_modelo_ausente(self):

        class ReconhecedorSemModelo(ReconhecedorFalso):

            def carregar_modelo(self, somente_local=False):

                raise VozIndisponivel("modelo não está no disco")

        gerenciador = GerenciadorVoz(
            gravador=GravadorFalso(AUDIO_QUALQUER),
            reconhecedor=ReconhecedorSemModelo(ja_carregado=False)
        )

        # Não pode levantar nem derrubar a thread com traceback.
        gerenciador.pre_aquecer().join(2)


class TestReconhecedorFasterWhisper:

    def test_modelo_padrao_e_o_medium(self):

        assert ReconhecedorFasterWhisper().modelo == "medium"

    def test_acusa_biblioteca_faltando(self, monkeypatch):

        # None em sys.modules faz "import faster_whisper"
        # levantar ImportError, como se não estivesse instalado.
        monkeypatch.setitem(
            sys.modules,
            "faster_whisper",
            None
        )

        with pytest.raises(VozIndisponivel) as erro:
            ReconhecedorFasterWhisper().carregar_modelo()

        assert erro.value.pacote_pip == "faster-whisper"

    def _instalar_faster_whisper_falso(
        self,
        monkeypatch,
        textos
    ):

        chamadas = {
            "construtor": [],
            "transcribe": []
        }

        class Segmento:

            def __init__(self, text):
                self.text = text

        class ModeloFalso:

            def __init__(self, *args, **kwargs):

                chamadas["construtor"].append(
                    (args, kwargs)
                )

            def transcribe(self, audio, **kwargs):

                chamadas["transcribe"].append(kwargs)

                return (
                    iter(Segmento(t) for t in textos),
                    None
                )

        modulo = types.ModuleType("faster_whisper")
        modulo.WhisperModel = ModeloFalso

        monkeypatch.setitem(
            sys.modules,
            "faster_whisper",
            modulo
        )

        return chamadas

    def test_junta_os_segmentos_em_um_texto(self, monkeypatch):

        self._instalar_faster_whisper_falso(
            monkeypatch,
            [" abre o ", " discord "]
        )

        reconhecedor = ReconhecedorFasterWhisper()

        assert (
            reconhecedor.transcrever(AUDIO_QUALQUER)
            == "abre o discord"
        )

    def test_carrega_o_modelo_uma_unica_vez(self, monkeypatch):

        chamadas = self._instalar_faster_whisper_falso(
            monkeypatch,
            ["oi"]
        )

        reconhecedor = ReconhecedorFasterWhisper()

        reconhecedor.transcrever(AUDIO_QUALQUER)
        reconhecedor.transcrever(AUDIO_QUALQUER)

        assert len(chamadas["construtor"]) == 1
        assert len(chamadas["transcribe"]) == 2
        assert reconhecedor.carregado

    def test_transcreve_em_portugues_com_beam_5_vad_e_prompt(self, monkeypatch):

        chamadas = self._instalar_faster_whisper_falso(
            monkeypatch,
            ["oi"]
        )

        monkeypatch.setattr(
            ReconhecedorFasterWhisper,
            "onnxruntime_disponivel",
            staticmethod(lambda: True)
        )

        reconhecedor = ReconhecedorFasterWhisper()

        reconhecedor.transcrever(AUDIO_QUALQUER)

        opcoes = chamadas["transcribe"][0]

        assert opcoes["language"] == "pt"
        assert opcoes["beam_size"] == 5
        assert opcoes["vad_filter"] is True
        assert opcoes["condition_on_previous_text"] is False
        assert "Shaula" in opcoes["initial_prompt"]

    def test_sem_onnxruntime_transcreve_sem_o_filtro_de_silencio(
        self,
        monkeypatch
    ):

        # Em Pythons muito novos o onnxruntime não tem pacote: o
        # reconhecimento continua funcionando, só sem o VAD.
        chamadas = self._instalar_faster_whisper_falso(
            monkeypatch,
            ["oi"]
        )

        monkeypatch.setattr(
            ReconhecedorFasterWhisper,
            "onnxruntime_disponivel",
            staticmethod(lambda: False)
        )

        reconhecedor = ReconhecedorFasterWhisper()

        assert reconhecedor.vad_ativo is False
        assert reconhecedor.transcrever(AUDIO_QUALQUER) == "oi"
        assert chamadas["transcribe"][0]["vad_filter"] is False

    def test_vad_pode_ser_forcado(self, monkeypatch):

        monkeypatch.setattr(
            ReconhecedorFasterWhisper,
            "onnxruntime_disponivel",
            staticmethod(lambda: False)
        )

        assert ReconhecedorFasterWhisper(usar_vad=True).vad_ativo is True

        monkeypatch.setattr(
            ReconhecedorFasterWhisper,
            "onnxruntime_disponivel",
            staticmethod(lambda: True)
        )

        assert ReconhecedorFasterWhisper(usar_vad=False).vad_ativo is False

    def test_detecta_o_onnxruntime_instalado_de_verdade(self, monkeypatch):

        monkeypatch.setitem(sys.modules, "onnxruntime", types.ModuleType("onnxruntime"))
        monkeypatch.setattr(
            importlib.util,
            "find_spec",
            lambda nome: object() if nome == "onnxruntime" else None
        )

        assert ReconhecedorFasterWhisper.onnxruntime_disponivel() is True

        monkeypatch.setattr(importlib.util, "find_spec", lambda nome: None)

        assert ReconhecedorFasterWhisper.onnxruntime_disponivel() is False

    def test_erro_de_dependencia_mostra_o_motivo_real(self, monkeypatch):

        # faster-whisper instalado, mas uma dependência dele (av,
        # ctranslate2...) falha ao carregar: o aviso precisa dizer
        # qual, em vez de mandar reinstalar o que já está instalado.
        class ModuloQuebrado:
            def __getattr__(self, nome):
                raise ImportError("DLL load failed while importing ctranslate2")

        monkeypatch.setitem(sys.modules, "faster_whisper", ModuloQuebrado())

        with pytest.raises(VozIndisponivel) as erro:
            ReconhecedorFasterWhisper().carregar_modelo()

        assert "ctranslate2" in str(erro.value)
        assert "Instalador" in str(erro.value)
        assert erro.value.pacote_pip == "faster-whisper"

    def test_carrega_em_cpu_int8_com_varias_threads(self, monkeypatch):

        chamadas = self._instalar_faster_whisper_falso(
            monkeypatch,
            ["oi"]
        )

        ReconhecedorFasterWhisper().carregar_modelo()

        args, kwargs = chamadas["construtor"][0]

        assert args == ("medium",)
        assert kwargs["device"] == "cpu"
        assert kwargs["compute_type"] == "int8"
        assert kwargs["cpu_threads"] >= 1
        assert kwargs["local_files_only"] is False

    def test_somente_local_nao_baixa(self, monkeypatch):

        chamadas = self._instalar_faster_whisper_falso(
            monkeypatch,
            ["oi"]
        )

        ReconhecedorFasterWhisper().carregar_modelo(
            somente_local=True
        )

        _, kwargs = chamadas["construtor"][0]

        assert kwargs["local_files_only"] is True

    def test_falha_ao_carregar_modelo_vira_voz_indisponivel(
        self,
        monkeypatch
    ):

        class ModeloQueFalha:

            def __init__(self, *args, **kwargs):
                raise OSError("sem internet para baixar o modelo")

        modulo = types.ModuleType("faster_whisper")
        modulo.WhisperModel = ModeloQueFalha

        monkeypatch.setitem(
            sys.modules,
            "faster_whisper",
            modulo
        )

        with pytest.raises(VozIndisponivel) as erro:
            ReconhecedorFasterWhisper().carregar_modelo()

        assert "internet" in str(erro.value)


class TestMicrofoneSounddevice:

    def test_acusa_biblioteca_faltando(self, monkeypatch):

        monkeypatch.setitem(
            sys.modules,
            "sounddevice",
            None
        )

        with pytest.raises(VozIndisponivel) as erro:
            MicrofoneSounddevice().abrir()

        assert erro.value.pacote_pip == "sounddevice"

    def test_microfone_inacessivel_vira_voz_indisponivel(
        self,
        monkeypatch
    ):

        class InputStreamQuebrado:

            def __init__(self, *args, **kwargs):
                raise RuntimeError("Error querying device -1")

        modulo = types.ModuleType("sounddevice")
        modulo.InputStream = InputStreamQuebrado

        monkeypatch.setitem(
            sys.modules,
            "sounddevice",
            modulo
        )

        with pytest.raises(VozIndisponivel) as erro:
            MicrofoneSounddevice().abrir()

        assert "microfone" in str(erro.value).lower()

    def test_le_blocos_mono_do_fluxo(self, monkeypatch):

        class FluxoFalso:

            def __init__(self, **kwargs):
                self.config = kwargs
                self.parado = False

            def start(self):
                pass

            def read(self, quantidade):

                return (
                    np.ones((quantidade, 1), dtype=np.int16),
                    False
                )

            def stop(self):
                self.parado = True

            def close(self):
                pass

        modulo = types.ModuleType("sounddevice")
        modulo.InputStream = FluxoFalso

        monkeypatch.setitem(
            sys.modules,
            "sounddevice",
            modulo
        )

        microfone = MicrofoneSounddevice(
            duracao_bloco_ms=30
        )

        microfone.abrir()

        bloco = microfone.ler_bloco()

        assert bloco.shape == (AMOSTRAS_POR_BLOCO,)
        assert bloco.dtype == np.int16

        fluxo = microfone._fluxo

        microfone.fechar()

        assert fluxo.parado
        assert microfone._fluxo is None
