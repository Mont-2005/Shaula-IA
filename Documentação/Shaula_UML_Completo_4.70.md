# UML da Shaula — versão 4.70

Este documento foi revisado contra o código-fonte presente no pacote **Shaula IA 4.70**.

Ele representa classes e componentes arquiteturais reais da versão auditada. Funções auxiliares internas e `ctypes.Structure` usados apenas como detalhes de implementação não são expandidos em todos os diagramas quando isso não acrescenta clareza arquitetural.

---

## 1. Visão geral da arquitetura

```mermaid
classDiagram
    direction TB

    class ShaulaWindow {
        <<PySide6 QMainWindow>>
        +id_conversa_atual
        +historico: HistoricoConversa
        +cache: CacheComandos
        +registro: RegistroFerramentas
        +gerenciador_conversas: GerenciadorConversas
        +gerenciador_ollama: GerenciadorOllama
        +gerenciador_anexos: GerenciadorAnexos
        +gerenciador_voz: GerenciadorVoz
        +trabalhador: TrabalhadorIA
        +trabalhador_voz: TrabalhadorVoz
        +anexos_pendentes
        +enviar()
        +interromper_resposta()
        +alternar_escuta()
        +cancelar_escuta()
        +receber_resposta()
        +selecionar_conversa()
        +criar_nova_conversa()
        +alternar_internet()
        +fechar_shaula()
    }

    class CampoMensagem {
        <<PySide6 QTextEdit>>
        +enviar_mensagem
        +arquivos_soltos
        +ajustar_altura()
        +keyPressEvent()
        +dragEnterEvent()
        +dropEvent()
    }

    class TrabalhadorIA {
        <<PySide6 QThread>>
        +mensagens
        +registro: RegistroFerramentas
        +anexos
        +detector_desligar: DetectorDesligar
        +resposta_pronta
        +erro
        +pensando
        +interrompido
        -_orcamento: OrcamentoContexto
        +interromper()
        +run()
    }

    class OrcamentoContexto {
        +num_ctx
        +reserva_resposta
        +ajustar(mensagens, tokens_ferramentas)
        +estimar_schemas(schemas)
    }

    class DetectorDesligar {
        +argumentos(texto)
    }

    class PerfilEsforco {
        <<dataclass>>
        +pensar
        +num_ctx
        +num_predict
        +max_rodadas
    }

    class EstadoEsforco {
        +perfil
        +definir(chave)
    }

    class ChatInterrompivel {
        +conversar(parametros)
        +cancelar()
    }

    class RegistroFerramentas {
        -_ferramentas
        +estado_internet: EstadoInternet
        +pesquisa_internet: PesquisaInternet
        +cache: CacheComandos
        +obter(nome)
        +executar(nome, argumentos)
        +schemas_openai()
    }

    class GerenciadorConversas {
        +listar_conversas()
        +criar_conversa()
        +obter_historico(id)
        +renomear_conversa()
        +alternar_fixado()
        +apagar_conversa()
        +marcar_atualizada()
    }

    class HistoricoConversa {
        +MAX_MENSAGENS_HISTORICO = 60
        +mensagens
        +adicionar()
        +salvar()
        +apagar()
    }

    class CacheComandos {
        +obter()
        +definir()
        +remover()
        +limpar_categoria()
        +limpar_tudo()
    }

    class GerenciadorAnexos {
        +estrategias
        +caminho_valido()
        +filtro_dialogo()
        +carregar()
    }

    class GerenciadorOllama {
        +processo_existe()
        +encerrar_processo()
        +encerrar_tudo()
    }

    class TrabalhadorVoz {
        <<PySide6 QThread>>
        +estado
        +texto_reconhecido
        +nivel
        +nada_reconhecido
        +erro
        +finalizar()
        +cancelar()
        +run()
    }

    class GerenciadorVoz {
        +tempo_ocioso_s
        +pre_aquecer()
        +escutar(parar, cancelado, notificar_estado, notificar_nivel)
    }

    class Anexo {
        +nome_arquivo
        +imagens
        +texto
        +nota_exibicao
    }

    ShaulaWindow *-- CampoMensagem
    ShaulaWindow --> TrabalhadorIA : cria por envio
    ShaulaWindow *-- CacheComandos
    ShaulaWindow *-- RegistroFerramentas
    ShaulaWindow *-- GerenciadorAnexos
    ShaulaWindow *-- GerenciadorOllama
    ShaulaWindow --> GerenciadorConversas
    ShaulaWindow --> HistoricoConversa : conversa atual
    ShaulaWindow o-- GerenciadorVoz : compartilhado entre janelas
    ShaulaWindow --> TrabalhadorVoz : cria por escuta

    GerenciadorConversas --> HistoricoConversa : cria/carrega
    TrabalhadorIA --> RegistroFerramentas
    TrabalhadorIA --> Anexo : recebe anexos processados
    TrabalhadorVoz --> GerenciadorVoz
    TrabalhadorIA *-- ChatInterrompivel
    TrabalhadorIA *-- OrcamentoContexto
    TrabalhadorIA o-- DetectorDesligar : injetado
    ShaulaWindow *-- DetectorDesligar
    TrabalhadorIA --> PerfilEsforco
    ShaulaWindow *-- EstadoEsforco
```

---

## 2. Entrypoints e inicialização

```mermaid
flowchart TB
    USER[Usuário]
    INSTALL[Instalador Dependências Shaula.bat]
    BAT[Shaula.bat]
    GUI[interface.py]
    CLI[main.py<br/>AssistenteTerminal]
    REG[tools/registro.py]
    OLLAMA[Ollama server]
    MODEL[qwen3.5:9b]

    INSTALL --> OLLAMA
    INSTALL --> MODEL
    USER --> BAT
    BAT --> OLLAMA
    BAT --> GUI
    USER -. execução manual .-> CLI
    GUI --> REG
    CLI --> REG
    GUI --> OLLAMA
    CLI --> OLLAMA
    OLLAMA --> MODEL
```

**Importante:** `main.py` não importa nem inicia `interface.py`. Os dois são entrypoints independentes que reutilizam o mesmo subsistema de ferramentas (e o mesmo `OrcamentoContexto`). Em `main.py` a lógica vive na classe `AssistenteTerminal`; nada executa no `import`.

---

## 3. Núcleo de ferramentas

```mermaid
classDiagram
    direction TB

    class Ferramenta {
        <<abstract>>
        +nome
        +descricao
        +parametros
        +precisa_de_sintese
        +executar(argumentos)*
        +schema_openai()
    }

    class RegistroFerramentas {
        -_ferramentas
        +obter(nome)
        +executar(nome, argumentos)
        +schemas_openai()
        +__contains__()
        +__iter__()
    }

    RegistroFerramentas o-- Ferramenta : 40 instâncias
```

### 3.1 Ferramentas de cálculo — 10

```mermaid
classDiagram
    Ferramenta <|-- CalcularFerramenta
    Ferramenta <|-- MatrizSomaFerramenta
    Ferramenta <|-- MatrizSubtracaoFerramenta
    Ferramenta <|-- MatrizMultiplicacaoFerramenta
    Ferramenta <|-- MatrizEscalarFerramenta
    Ferramenta <|-- MatrizTranspostaFerramenta
    Ferramenta <|-- MatrizDeterminanteFerramenta
    Ferramenta <|-- MatrizInversaFerramenta
    Ferramenta <|-- MatrizPotenciaFerramenta
    Ferramenta <|-- ConverterBaseFerramenta
```

### 3.2 Ferramentas de sistema, arquivos e interação — 30

```mermaid
classDiagram
    Ferramenta <|-- AbrirProgramaFerramenta
    Ferramenta <|-- FecharProgramaFerramenta
    Ferramenta <|-- BuscarArquivoFerramenta
    Ferramenta <|-- AbrirArquivoFerramenta
    Ferramenta <|-- DesligarComputadorFerramenta
    Ferramenta <|-- CancelarDesligamentoFerramenta
    Ferramenta <|-- BloquearTelaFerramenta
    Ferramenta <|-- TestarPingFerramenta
    Ferramenta <|-- InformacoesHardwareFerramenta
    Ferramenta <|-- AbrirMenuIniciarFerramenta
    Ferramenta <|-- AtivarInternetFerramenta
    Ferramenta <|-- DesativarInternetFerramenta
    Ferramenta <|-- PesquisarInternetFerramenta
    Ferramenta <|-- ListarMonitoresFerramenta
    Ferramenta <|-- ListarJanelasAbertasFerramenta
    Ferramenta <|-- MoverProgramaMonitorFerramenta
    Ferramenta <|-- MoverParaOutroMonitorFerramenta
    Ferramenta <|-- TirarPrintFerramenta
    Ferramenta <|-- ControlarJanelaFerramenta
    Ferramenta <|-- CriarLembreteFerramenta
    Ferramenta <|-- ListarLembretesFerramenta
    Ferramenta <|-- CancelarLembreteFerramenta
    Ferramenta <|-- ListarProcessosFerramenta
    Ferramenta <|-- ListarProcessosProtegidosFerramenta
    Ferramenta <|-- FinalizarProcessoFerramenta
    Ferramenta <|-- CopiarTextoFerramenta
    Ferramenta <|-- ColarTextoFerramenta
    Ferramenta <|-- ObterIpLocalFerramenta
    Ferramenta <|-- VerificarWifiFerramenta
    Ferramenta <|-- AnalisarTelaFerramenta
```

---

## 4. Serviços e injeção de dependência

```mermaid
classDiagram
    direction LR

    class RegistroFerramentas
    class CacheComandos
    class Calculadora
    class BuscadorArquivos
    class GerenciadorJanelas
    class GerenciadorProcessos
    class GerenciadorProgramas
    class GerenciadorClipboard
    class InformacoesRede
    class InformacoesSistema
    class EstadoInternet
    class PesquisaInternet
    class CapturadorTela
    class NotificadorToast
    class GerenciadorLembretes

    RegistroFerramentas *-- CacheComandos
    RegistroFerramentas *-- Calculadora
    RegistroFerramentas *-- BuscadorArquivos
    RegistroFerramentas *-- GerenciadorJanelas
    RegistroFerramentas *-- GerenciadorProcessos
    RegistroFerramentas *-- GerenciadorProgramas
    RegistroFerramentas *-- GerenciadorClipboard
    RegistroFerramentas *-- InformacoesRede
    RegistroFerramentas *-- InformacoesSistema
    RegistroFerramentas *-- EstadoInternet
    RegistroFerramentas *-- PesquisaInternet
    RegistroFerramentas *-- CapturadorTela
    RegistroFerramentas *-- NotificadorToast
    RegistroFerramentas *-- GerenciadorLembretes

    BuscadorArquivos --> CacheComandos
    GerenciadorJanelas --> CacheComandos
    GerenciadorProgramas --> GerenciadorProcessos
    PesquisaInternet --> EstadoInternet
    CapturadorTela --> GerenciadorJanelas
    GerenciadorLembretes --> NotificadorToast
```

As ferramentas concretas recebem essas instâncias de serviço no construtor; elas não contêm a lógica principal do domínio.

---

## 5. Mapeamento ferramenta → serviço

```mermaid
flowchart LR
    CALC[Calculadora]
    ARQ[BuscadorArquivos]
    PROG[GerenciadorProgramas]
    SIS[InformacoesSistema]
    WIN[GerenciadorJanelas]
    NETSTATE[EstadoInternet]
    SEARCH[PesquisaInternet]
    CAP[CapturadorTela]
    REM[GerenciadorLembretes]
    PROC[GerenciadorProcessos]
    CLIP[GerenciadorClipboard]
    REDE[InformacoesRede]

    T_CALC[10 ferramentas de cálculo] --> CALC
    T_ARQ[buscar_arquivo / abrir_arquivo] --> ARQ
    T_PROG[abrir_programa / fechar_programa] --> PROG
    T_SIS[desligar / cancelar / bloquear / ping / hardware] --> SIS
    T_WIN[menu / monitores / janelas / mover / controlar] --> WIN
    T_NET[ativar_internet / desativar_internet] --> NETSTATE
    T_SEARCH[pesquisar_internet] --> SEARCH
    T_CAP[tirar_print / analisar_tela] --> CAP
    T_REM[criar / listar / cancelar lembrete] --> REM
    T_PROC[listar / protegidos / finalizar processo] --> PROC
    T_CLIP[copiar_texto / colar_texto] --> CLIP
    T_REDE[obter_ip_local / verificar_wifi] --> REDE
```

---

## 6. Pesquisa na internet — Strategy

```mermaid
classDiagram
    direction TB

    class EstadoInternet {
        -_ativa
        +ativa
        +ativar()
        +desativar()
    }

    class DetectorPerguntaFactual {
        <<utility>>
        +PALAVRAS_INTERROGATIVAS
        +parece_factual(texto)
    }

    class FormatadorTexto {
        <<utility>>
        +linkificar_html(texto_html)
        +extrair_urls(texto)
    }

    class MecanismoBusca {
        <<abstract>>
        +nome
        +buscar(consulta)*
        #_requisitar_html(url)
    }

    class DuckDuckGo {
        +nome
        +buscar(consulta)
    }

    class Bing {
        +nome
        +buscar(consulta)
    }

    class DuckParser {
        <<HTMLParser>>
        +resultados
        +finalizar()
    }

    class BingParser {
        <<HTMLParser>>
        +resultados
    }

    class PesquisaInternet {
        +estado_internet
        +mecanismos
        +buscar(consulta)
    }

    MecanismoBusca <|-- DuckDuckGo
    MecanismoBusca <|-- Bing
    DuckDuckGo --> DuckParser
    Bing --> BingParser
    PesquisaInternet --> EstadoInternet
    PesquisaInternet o-- MecanismoBusca
    TrabalhadorIA ..> DetectorPerguntaFactual
    TrabalhadorIA ..> FormatadorTexto
    TrabalhadorIA --> PesquisaInternet
```

Ordem padrão de fallback: `DuckDuckGo()` e depois `Bing()`.

---

## 7. Anexos — Strategy

```mermaid
classDiagram
    direction TB

    class DependenciaFaltando {
        <<Exception>>
        +pacote_pip
        +caminho
    }

    class Anexo {
        +nome_arquivo
        +imagens
        +texto
        +nota_exibicao
        +eh_imagem
    }

    class EstrategiaAnexo {
        +EXTENSOES
        +TAMANHO_MAXIMO_MB
        +suporta(caminho)
        +dentro_do_limite(caminho)
        +processar(caminho)
    }

    class EstrategiaImagem {
        +LADO_MAXIMO_PX = 768
        +processar(caminho)
    }

    class EstrategiaPDF {
        +PAGINAS_MAXIMAS_RENDERIZADAS = 4
        +CARACTERES_MAXIMOS_TEXTO = 12000
        +processar(caminho)
    }

    class EstrategiaVideo {
        +NUMERO_DE_FRAMES = 4
        +processar(caminho)
    }

    class EstrategiaTexto {
        +CARACTERES_MAXIMOS = 12000
        +processar(caminho)
    }

    class GerenciadorAnexos {
        +estrategias
        +caminho_valido(caminho)
        +filtro_dialogo()
        +carregar(caminho)
    }

    class DescricaoAnexo {
        +nome
        +detalhe
        +extensao
        +formato
        +tipo
        +linha_detalhe
    }

    class NotaAnexo {
        +montar(notas_exibicao)
        +anexar_ao_texto(texto, notas)
        +separar(texto)
    }

    class IconeArquivo {
        <<Qt>>
        +CORES
        +pixmap(descricao)
        +miniatura(dados, lado)
    }

    class CartaoAnexo {
        <<QFrame>>
    }

    NotaAnexo ..> DescricaoAnexo : separa a nota em
    CartaoAnexo --> DescricaoAnexo
    CartaoAnexo --> IconeArquivo
    ShaulaWindow *-- NotaAnexo
    ShaulaWindow *-- IconeArquivo
    ShaulaWindow ..> CartaoAnexo : um por arquivo enviado

    EstrategiaAnexo <|-- EstrategiaImagem
    EstrategiaAnexo <|-- EstrategiaPDF
    EstrategiaAnexo <|-- EstrategiaVideo
    EstrategiaAnexo <|-- EstrategiaTexto

    GerenciadorAnexos o-- EstrategiaAnexo
    GerenciadorAnexos --> Anexo
    EstrategiaImagem --> Anexo
    EstrategiaPDF --> Anexo
    EstrategiaVideo --> Anexo
    EstrategiaTexto --> Anexo
    EstrategiaPDF ..> DependenciaFaltando
    EstrategiaVideo ..> DependenciaFaltando
    TrabalhadorIA --> Anexo
```

A nota `[N arquivo(s) anexado(s): ...]` é o que o modelo lê no histórico; a tela mostra, no lugar dela, um `CartaoAnexo` por arquivo (ícone, nome e formato). `NotaAnexo.separar()` tira a nota do texto, tanto na hora do envio quanto ao reabrir uma conversa antiga. `NotaAnexo` e `DescricaoAnexo` não dependem de Qt (`tools/nota_anexo.py`); `IconeArquivo` e `CartaoAnexo` ficam em `tools/cartao_anexo.py`.

---

## 8. Comando por voz — Strategy

A voz não tem um "interpretador de comandos" próprio: o texto reconhecido segue o mesmo caminho de uma mensagem digitada (`enviar()` → `TrabalhadorIA` → tool-calling do modelo → `RegistroFerramentas`). Por isso o subsistema termina em texto.

A gravação **não encerra sozinha**: vai até a pessoa mandar parar (clique no microfone ou `Ctrl+M`), como num ditado. Só há dois controles: `finalizar()` (para e transcreve) e `cancelar()` (descarta). O único corte automático é um teto de segurança de 10 minutos.

```mermaid
classDiagram
    direction TB

    class VozIndisponivel {
        <<Exception>>
        +pacote_pip
    }

    class FonteAudio {
        <<interface>>
        +taxa = 16000
        +abrir()
        +ler_bloco()
        +fechar()
    }

    class MicrofoneSounddevice {
        +duracao_bloco_ms
        +dispositivo
        +abrir()
        +ler_bloco()
        +fechar()
    }

    class UtilitariosDeAudio {
        <<funções do módulo>>
        +calcular_nivel(bloco)
        +normalizar_volume(audio)
    }

    class Gravador {
        +DURACAO_MAXIMA_S = 600
        +DURACAO_MINIMA_S = 0.4
        +NIVEL_MINIMO_DE_VOZ
        +gravar(parar, cancelado, ao_nivel)
    }

    class ReconhecedorFala {
        <<interface>>
        +prompt_inicial
        +carregado
        +carregar_modelo(somente_local)
        +descarregar_modelo()
        +transcrever(audio, taxa)
    }

    class ReconhecedorFasterWhisper {
        +MODELO_PADRAO = medium
        +dispositivo = cpu
        +tipo_computacao = int8
        +beam_size = 5
        +cpu_threads
        +carregar_modelo(somente_local)
        +descarregar_modelo()
        +transcrever(audio, taxa)
    }

    class LimpadorTranscricao {
        +FRASES_ALUCINADAS
        +VARIACOES_NOME
        +MIN_PALAVRAS_ECO = 4
        +limpar(texto, prompt_inicial)
    }

    class GerenciadorVoz {
        +gravador: Gravador
        +reconhecedor: ReconhecedorFala
        +limpador: LimpadorTranscricao
        +tempo_ocioso_s = 180
        +pre_aquecer()
        +escutar(parar, cancelado, notificar_estado, notificar_nivel)
    }

    class CargaEmSegundoPlano {
        <<_CargaEmSegundoPlano>>
        +concluida
        +iniciar()
        +aguardar(timeout)
    }

    class TrabalhadorVoz {
        <<PySide6 QThread>>
        +estado
        +nivel
        +texto_reconhecido
        +nada_reconhecido
        +erro
        +finalizar()
        +cancelar()
        +run()
    }

    class MedidorNivelVoz {
        <<QWidget>>
        +NUMERO_DE_BARRAS = 64
        +adicionar_nivel(rms)
        +limpar()
        +paintEvent()
    }

    FonteAudio <|-- MicrofoneSounddevice
    ReconhecedorFala <|-- ReconhecedorFasterWhisper

    GerenciadorVoz *-- Gravador
    GerenciadorVoz o-- ReconhecedorFala
    GerenciadorVoz *-- LimpadorTranscricao
    GerenciadorVoz ..> CargaEmSegundoPlano : carrega o modelo durante a gravação
    CargaEmSegundoPlano --> ReconhecedorFala
    Gravador o-- FonteAudio
    Gravador ..> UtilitariosDeAudio

    MicrofoneSounddevice ..> VozIndisponivel
    ReconhecedorFasterWhisper ..> VozIndisponivel
    TrabalhadorVoz --> GerenciadorVoz
    TrabalhadorVoz ..> VozIndisponivel
    ShaulaWindow --> TrabalhadorVoz : cria por escuta
    ShaulaWindow o-- GerenciadorVoz : compartilhado entre janelas
    ShaulaWindow *-- MedidorNivelVoz : mostra o volume enquanto grava
```

Pontos de polimorfismo: `Gravador` chama `fonte.ler_bloco()` sem saber se é um microfone real ou uma fonte falsa de teste, e `GerenciadorVoz` chama `reconhecedor.transcrever()` sem saber qual motor há por baixo — trocar o Whisper por outro motor (por exemplo, Vosk) é criar uma nova subclasse de `ReconhecedorFala`.

Fases da escuta na interface (`ShaulaWindow._fase_voz`): `None` → `iniciando` → `gravando` → (`preparando`, **só se o modelo ainda estiver carregando quando a fala termina**) → `transcrevendo` → `None`. O modelo é carregado em segundo plano (`_CargaEmSegundoPlano`) **enquanto a pessoa fala**; se a biblioteca faltar, o erro é avisado logo no início, antes da gravação. O pré-carregamento (`GerenciadorVoz.pre_aquecer()`, ~2 s depois de abrir a janela) está desligado por padrão (`PRE_AQUECER_VOZ = False`) e, quando ligado, só usa um modelo que já esteja no disco. Depois de `tempo_ocioso_s` (180 s) sem uso, `GerenciadorVoz` chama `descarregar_modelo()` para liberar a RAM; um novo uso cancela essa liberação agendada.

---

## 9. Interromper a resposta da IA — ChatInterrompivel

A Shaula usa `chat()` sem streaming (ver limitações no README): uma chamada assim bloqueia até o modelo terminar a resposta inteira, sem ponto intermediário para checar "o usuário mandou parar?". `ChatInterrompivel` resolve isso rodando a chamada de verdade numa thread auxiliar, enquanto quem chamou espera em intervalos de 50 ms conferindo o pedido de cancelamento.

```mermaid
classDiagram
    direction LR

    class TrabalhadorIA {
        <<PySide6 QThread>>
        +interrompido
        +erro
        +interromper()
        -_conferir_interrupcao()
        +run()
    }

    class ChatInterrompivel {
        +INTERVALO_DE_CONFERENCIA_S = 0.05
        +foi_cancelado
        +conversar(parametros)
        +cancelar()
    }

    class ChamadaCancelada {
        <<Exception>>
    }

    class OllamaClient {
        <<ollama.Client>>
        +chat()
    }

    class ShaulaWindow {
        +interromper_resposta()
        +_ao_clicar_enviar()
        +_ao_pressionar_esc()
        +_ao_resposta_interrompida()
    }

    TrabalhadorIA *-- ChatInterrompivel
    ChatInterrompivel --> OllamaClient : cria e fecha a conexão
    ChatInterrompivel ..> ChamadaCancelada
    TrabalhadorIA ..> ChamadaCancelada
    ShaulaWindow --> TrabalhadorIA : interromper()
    TrabalhadorIA --> ShaulaWindow : interrompido
```

```mermaid
sequenceDiagram
    actor U as Usuário
    participant J as ShaulaWindow
    participant T as TrabalhadorIA
    participant C as ChatInterrompivel
    participant H as Thread auxiliar
    participant O as Ollama

    T->>C: conversar(messages, tools)
    C->>H: inicia a chamada
    H->>O: chat() (bloqueia)
    U->>J: clica em ■ ou pressiona Esc
    J->>T: interromper()
    T->>C: cancelar()
    C-->>H: fecha a conexão HTTP
    C-->>T: ChamadaCancelada
    T-->>J: interrompido
    J->>J: mostra "Resposta interrompida"
    T-->>J: pensando(False)
    O--xH: leitura abortada (resultado descartado)
```

O botão de enviar (➤) vira "interromper" (■) enquanto a IA responde; `Esc` faz o mesmo (ou cancela a gravação de voz, se houver uma). O que interromper **não** faz: desfazer uma ferramenta que já executou — ela termina, o que devolveu é descartado e nenhuma outra é iniciada. A mensagem do usuário permanece no histórico; nenhuma resposta da IA é gravada (resultados de ferramentas nunca são gravados no histórico — existem só no contexto da troca).

### 9.1 Controle de contexto — OrcamentoContexto

O prompt de sistema (~1.700 tokens) e os 40 schemas (~4.100) ocupam cerca de 5.900 tokens antes de qualquer conversa, e a reserva de resposta sai do mesmo `num_ctx`. Se o total passar do `num_ctx`, o Ollama descarta o começo do prompt em silêncio. `OrcamentoContexto` evita isso antes de cada chamada: encurta respostas antigas longas (`CompactadorHistorico`), descarta as mais antigas e deixa um resumo do que saiu (`ResumidorHistorico`), para o histórico não sumir do contexto. Os dois colaboradores são injetados no construtor.

```mermaid
classDiagram
    direction LR

    class OrcamentoContexto {
        +CARACTERES_POR_TOKEN = 3
        +TOKENS_POR_IMAGEM = 800
        +FRACAO_MAXIMA_APOIO = 0.35
        +FRACAO_MAXIMA_RESUMO = 0.30
        +MINIMO_RESUMO_TOKENS = 120
        +num_ctx
        +reserva_resposta
        +descartadas
        +encurtadas
        +compactadas
        +resumiu
        +tokens_disponiveis
        +estimar_texto(texto)
        +estimar_schemas(schemas)
        +estimar_mensagem(mensagem)
        +ajustar(mensagens, tokens_ferramentas)
    }

    class CompactadorHistorico {
        +LIMITE_CARACTERES = 600
        +compactar(mensagem)
    }

    class ResumidorHistorico {
        +LIMITE_TOKENS = 600
        +resumir(removidas, limite_tokens)
    }

    class TrabalhadorIA {
        <<QThread>>
        +run()
    }

    class AssistenteTerminal {
        +executar()
        +responder(texto)
    }

    OrcamentoContexto *-- CompactadorHistorico : injetado
    OrcamentoContexto *-- ResumidorHistorico : injetado
    TrabalhadorIA *-- OrcamentoContexto : reserva = num_predict do nível
    AssistenteTerminal *-- OrcamentoContexto
```

`ajustar()` devolve uma **nova** lista: preserva a mensagem de sistema do topo e tudo a partir da última mensagem do usuário; limita cada texto de apoio (`system`/`tool`) a 35% do orçamento; descarta as mensagens mais antigas do histórico até caber; e, se ainda faltar, encurta o maior texto de apoio.

Os parâmetros que variam com o nível de esforço (`think`, `num_ctx`, `num_predict` e o máximo de rodadas de ferramentas) vêm do `PerfilEsforco` (seção 9.2). Para mensagens com anexo, `tools` é omitido.

### 9.2 Nível de esforço — PerfilEsforco, CatalogoEsforco e EstadoEsforco

O botão **Esforço** da barra superior escolhe um de cinco perfis. `EstadoEsforco` é compartilhado por todas as janelas (como o `EstadoInternet`), é lembrado em `~/.shaula/configuracoes.json` (via `ArmazenamentoJson`) e, na primeira vez, pode ser iniciado pela variável `SHAULA_ESFORCO`.

```mermaid
classDiagram
    direction LR

    class PerfilEsforco {
        <<dataclass frozen>>
        +chave
        +nome
        +descricao
        +pensar
        +num_ctx
        +num_predict
        +max_rodadas
        +recomendado
        +aviso
        +tokens_para_prompt
        +resumo
    }

    class CatalogoEsforco {
        +PADRAO = medio
        +PERFIS
        +listar()
        +obter(chave)
        +padrao()
    }

    class EstadoEsforco {
        +VARIAVEL_AMBIENTE = SHAULA_ESFORCO
        +perfil
        +definir(chave)
    }

    class ShaulaWindow {
        <<PySide6 QMainWindow>>
        +estado_esforco
        +atualizar_botao_esforco()
        +abrir_menu_esforco()
        +definir_esforco(chave)
    }

    class TrabalhadorIA {
        <<QThread>>
        +perfil
    }

    class AssistenteTerminal {
        +estado_esforco
    }

    class OrcamentoContexto {
        +num_ctx
        +reserva_resposta
    }

    class ArmazenamentoJson

    CatalogoEsforco o-- PerfilEsforco : 5 perfis
    EstadoEsforco --> CatalogoEsforco : valida o nível
    EstadoEsforco *-- ArmazenamentoJson : configuracoes.json
    ShaulaWindow *-- EstadoEsforco : compartilhado entre janelas
    ShaulaWindow ..> TrabalhadorIA : cria com o perfil atual
    AssistenteTerminal *-- EstadoEsforco
    TrabalhadorIA --> PerfilEsforco : foto no envio
    TrabalhadorIA *-- OrcamentoContexto : num_ctx e reserva = num_predict
```

| Nível | `think` | `num_ctx` | `num_predict` | Rodadas |
|---|---|---|---|---|
| Baixo | não | 10240 | 1024 | 4 |
| Médio (recomendado) | sim | 11264 | 2048 | 8 |
| Alto | sim | 13312 | 3072 | 8 |
| Extra | sim | 15360 | 4096 | 10 |
| Máx | sim | 18432 | 6144 | 12 |

`TrabalhadorIA` recebe o perfil no momento do envio (uma "foto"): trocar o nível durante a resposta só vale para a próxima mensagem. Mudar o `num_ctx` faz o Ollama recarregar o modelo. Extra e Máx têm `aviso` de custo de VRAM para placas de 8 GB.

### 9.3 Blocos de código — DivisorDeBlocos, BlocoCodigo e ConteudoMensagemShaula

Respostas da Shaula com cercas ``` são exibidas como uma coluna de texto e blocos de código, cada bloco com cabeçalho (linguagem), botão **Copiar** e realce de sintaxe.

```mermaid
classDiagram
    direction LR

    class SegmentoMensagem {
        <<dataclass frozen>>
        +tipo
        +conteudo
        +linguagem
        +eh_codigo
    }

    class DivisorDeBlocos {
        +dividir(texto)
        +tem_codigo(texto)
    }

    class FormatadorTextoMensagem {
        +escapar(texto)
        +para_html(texto, remover_negrito)
    }

    class ConteudoMensagemShaula {
        <<QWidget>>
        +ocupa_largura_maxima = True
        +blocos
    }

    class BlocoCodigo {
        <<QFrame>>
        +TEXTO_COPIAR
        +TEXTO_COPIADO
        +codigo
        +copiar()
    }

    class EditorCodigo {
        <<QPlainTextEdit>>
        -_ajustar_altura()
    }

    class RealceSintaxe {
        <<QSyntaxHighlighter>>
        +highlightBlock(texto)
    }

    class CatalogoLinguagens {
        +perfil(linguagem)
    }

    class PerfilLinguagem {
        <<dataclass frozen>>
        +palavras_chave
        +comentario_linha
        +comentario_bloco
        +aspas_triplas
    }

    class ShaulaWindow {
        <<PySide6 QMainWindow>>
        +adicionar_mensagem(autor, texto, imagens)
    }

    ShaulaWindow ..> DivisorDeBlocos : tem_codigo(texto)
    ShaulaWindow ..> ConteudoMensagemShaula : cria quando há código
    ShaulaWindow ..> FormatadorTextoMensagem : texto comum
    DivisorDeBlocos --> SegmentoMensagem : produz
    ConteudoMensagemShaula ..> DivisorDeBlocos
    ConteudoMensagemShaula ..> FormatadorTextoMensagem
    ConteudoMensagemShaula *-- BlocoCodigo : 1 por bloco
    BlocoCodigo *-- EditorCodigo
    EditorCodigo *-- RealceSintaxe
    RealceSintaxe --> CatalogoLinguagens
    CatalogoLinguagens o-- PerfilLinguagem
```

Pontos de projeto:

- `DivisorDeBlocos` não depende do Qt. Abre o bloco numa linha que começa com ``` ou ~~~ (até 8 espaços de recuo, que são removidos do código) e fecha com a mesma cerca; um bloco não fechado vai até o fim da mensagem, e um bloco vazio é descartado.
- O botão **Copiar** (`BlocoCodigo.copiar()`) usa `QGuiApplication.clipboard()` e mostra "✓ Copiado" por 1,8 s.
- `EditorCodigo` calcula a altura pelo layout real do documento (`blockBoundingRect`), não por `fontMetrics().lineSpacing()`, que cortava as últimas linhas; reserva a altura da barra horizontal quando ela aparece.
- O texto comum só tem `**` removido fora de crases (`FormatadorTextoMensagem`); o código nunca é alterado.
- `ConteudoMensagemShaula.ocupa_largura_maxima` faz `ShaulaWindow` usar a largura máxima (em vez de 45% da janela) para esse balão, inclusive em `aplicar_redimensionamento()`.

---

### 9.4 Confirmação de ações sensíveis — PoliticaConfirmacao e Confirmador

Antes de executar uma ferramenta, `RegistroFerramentas.executar()` pergunta à `PoliticaConfirmacao` se a chamada precisa de confirmação; se precisar, delega a um `Confirmador`. A resposta padrão é **não**.

```mermaid
classDiagram
    direction LR

    class PedidoConfirmacao {
        <<dataclass frozen>>
        +ferramenta
        +titulo
        +descricao
        +mensagem_negada
    }

    class RegraConfirmacao {
        <<abstract>>
        +ferramenta
        +avaliar(argumentos)
    }

    class PoliticaConfirmacao {
        +ativa
        +VARIAVEL_AMBIENTE = SHAULA_CONFIRMAR
        +ferramentas_cobertas
        +avaliar(ferramenta, argumentos)
        +padrao(ambiente)
    }

    class Confirmador {
        <<abstract>>
        +confirmar(pedido)
    }

    class ConfirmadorTerminal {
        +confirmar(pedido)
    }

    class ConfirmadorFixo {
        +confirmar(pedido)
    }

    class ConfirmadorQt {
        <<QObject>>
        +TEMPO_LIMITE_S = 120
        +confirmar(pedido)
        +cancelar_pendentes()
    }

    class RegistroFerramentas {
        +politica_confirmacao
        +confirmador
        +executar(nome, argumentos)
    }

    class ShaulaWindow {
        <<QMainWindow>>
        +confirmador
        +detector_desligar
        +interromper_resposta()
        -_interromper_ia()
    }

    class AtrasoDesligamento {
        <<objeto-valor>>
        +PADRAO = 60
        +segundos
        +imediato
        +descricao
    }

    class NormalizadorTexto {
        +normalizar(texto)
    }

    class InterpretadorTempo {
        +interpretar(texto_normalizado)
    }

    class DetectorDesligar {
        +TAMANHO_MAXIMO = 200
        +argumentos(texto)
    }

    class CaminhoExecutavel {
        +EXTENSOES
        +texto
        +normalizado
        +extensao
        +eh_executavel
    }

    class RegraAbrirPrograma {
        +SEPARADORES
        +avaliar(argumentos)
    }

    class ComandosLocais {
        +FRASES_SAIDA
        +FRASES_APAGAR_CONVERSA
        +eh_saida(texto)
        +eh_apagar_conversa(texto)
    }

    class TrabalhadorIA {
        <<QThread>>
        +detector_desligar
        +run()
    }

    RegraConfirmacao <|-- RegraDesligarComputador
    RegraConfirmacao <|-- RegraFinalizarProcesso
    RegraConfirmacao <|-- RegraFecharPrograma
    RegraConfirmacao <|-- RegraFecharJanela
    RegraConfirmacao <|-- RegraAbrirExecutavel
    RegraConfirmacao <|-- RegraAbrirPrograma
    RegraAbrirExecutavel ..> CaminhoExecutavel
    RegraAbrirPrograma ..> CaminhoExecutavel
    ShaulaWindow *-- ComandosLocais
    ComandosLocais *-- NormalizadorTexto
    PoliticaConfirmacao o-- RegraConfirmacao : uma por ferramenta
    PoliticaConfirmacao ..> PedidoConfirmacao : produz
    Confirmador <|-- ConfirmadorTerminal
    Confirmador <|-- ConfirmadorFixo
    Confirmador <|.. ConfirmadorQt : registro virtual
    RegistroFerramentas *-- PoliticaConfirmacao
    RegistroFerramentas o-- Confirmador
    ShaulaWindow *-- ConfirmadorQt
    ShaulaWindow ..> RegistroFerramentas : injeta o confirmador
    ShaulaWindow *-- DetectorDesligar
    DetectorDesligar *-- NormalizadorTexto
    DetectorDesligar *-- InterpretadorTempo
    TrabalhadorIA o-- DetectorDesligar : injetado
    TrabalhadorIA ..> RegistroFerramentas : executar("desligar_computador")
    RegraDesligarComputador ..> AtrasoDesligamento
    DesligarComputadorFerramenta ..> AtrasoDesligamento
```

```mermaid
sequenceDiagram
    participant T as TrabalhadorIA (thread da IA)
    participant R as RegistroFerramentas
    participant P as PoliticaConfirmacao
    participant C as ConfirmadorQt
    participant J as Thread da interface
    participant U as Usuário
    participant F as Ferramenta

    T->>R: executar("fechar_programa", {nome})
    R->>P: avaliar(nome, argumentos)
    P-->>R: PedidoConfirmacao
    R->>C: confirmar(pedido)
    C->>J: sinal (fila) com o pedido
    Note over T,C: a thread da IA espera (máx. 120 s)
    J->>U: caixa "Sim, autorizar" / "Não"
    alt Sim
        U-->>J: Sim
        J-->>C: resposta = True
        C-->>R: True
        R->>F: executar(argumentos)
        F-->>T: resultado
    else Não, fechar, Esc, ■, janela fechada ou tempo esgotado
        J-->>C: resposta = False
        C-->>R: False
        R-->>T: "Ação cancelada: você não autorizou…"
    end
```

Atalho para o pedido direto de desligar (sem passar pelo modelo):

```mermaid
sequenceDiagram
    participant T as TrabalhadorIA
    participant D as DetectorDesligar
    participant R as RegistroFerramentas
    participant C as ConfirmadorQt
    participant U as Usuário

    T->>D: argumentos("desligue o computador")
    D-->>T: {}  (ou None se não for um pedido claro)
    T->>R: executar("desligar_computador", {})
    R->>C: confirmar(pedido: "em 60 segundo(s)")
    C->>U: caixa à frente (restaura a janela, topo, pisca)
    U-->>C: Sim / Não
    C-->>R: resposta
    R-->>T: resultado ou "Ação cancelada…"
    T-->>T: devolve direto, sem chamar o modelo
```

Pontos de projeto:

- Cobertura: `desligar_computador`, `finalizar_processo`, `fechar_programa`, `controlar_janela` (só com `acao = fechar`) e `abrir_arquivo` (só para extensões de programa ou script).
- Sem confirmador configurado, a ação sensível é **recusada**. `SHAULA_CONFIRMAR=0` desliga a política.
- `ConfirmadorQt` não herda de `Confirmador`, porque a metaclasse do `QObject` não se combina com a ABC; é registrado como subclasse virtual. `ShaulaWindow.interromper_resposta()` (botão ■) e `_interromper_ia()` (fechamento da janela) chamam `cancelar_pendentes()` para não ficarem presos à caixa.
- **Atalho `DetectorDesligar`** (`tools/intencao_desligar.py`): o modelo local às vezes não chama a ferramenta, e sem chamada não há confirmação. O detector reconhece frases curtas e inequívocas sobre desligar o computador e o `TrabalhadorIA` chama o registro direto, antes do modelo. Não dispara com perguntas, negações, textos longos ou mensagens com anexo. O atalho não pula a confirmação: só garante que ela aconteça. Os outros pedidos sensíveis não têm atalho. Os colaboradores (`NormalizadorTexto`, `InterpretadorTempo`) são injetáveis.
- `desligar_computador` tem `segundos` opcional: `AtrasoDesligamento` (ausente/inválido → 60; `0` → agora) é usada tanto pela regra de confirmação quanto pela ferramenta, para a pergunta bater com a ação.
- `ConfirmadorQt._exibir()` traz a caixa para a frente (restaura a janela minimizada, `WindowStaysOnTopHint`, `activateWindow`, `QApplication.alert`).
- A caixa tem estilo próprio (`ESTILO_CAIXA`): o `QWidget { color }` da janela pintaria o texto de branco sobre o fundo claro do sistema.

### 9.5 Captura para o modelo — analisar_tela

```mermaid
classDiagram
    direction LR

    class AnalisarTelaFerramenta {
        +nome = analisar_tela
        +precisa_de_sintese = True
        +executar(argumentos)
    }

    class CapturadorTela {
        +LADO_MAXIMO_ANALISE_PX = 1024
        +tirar_print(...)
        +capturar_para_modelo(monitor, ocultar_shaula)
        -_salvar_imagem(cabecalho, pixels, sufixo)
    }

    class ImagemCapturada {
        +largura
        +altura
        +para_qimage()
        +salvar_png(caminho)
        +para_jpeg(lado_maximo)
    }

    class CapturaParaModelo {
        <<dataclass frozen>>
        +imagens
        +numero_monitor
        +largura
        +altura
        +shaula_ocultada
    }

    class ResultadoComImagens {
        <<str>>
        +imagens
    }

    class OcultadorJanelasProprias {
        +ESPERA_PADRAO_S = 0.4
        +intersecta(a, b)
        +ocultar(regiao)
    }

    class ApiJanelasWin32 {
        +janelas_visiveis_do_processo(pid)
        +retangulo(hwnd)
        +minimizar(hwnd)
        +restaurar(hwnd)
    }

    class TrabalhadorIA {
        <<QThread>>
        +run()
    }

    AnalisarTelaFerramenta --> CapturadorTela
    AnalisarTelaFerramenta ..> ResultadoComImagens : devolve
    CapturadorTela *-- OcultadorJanelasProprias
    CapturadorTela ..> ImagemCapturada
    CapturadorTela ..> CapturaParaModelo
    OcultadorJanelasProprias o-- ApiJanelasWin32
    TrabalhadorIA ..> ResultadoComImagens : lê .imagens
```

- `ImagemCapturada` converte o buffer do GDI (BGRA, linhas de baixo para cima) em `QImage` já na orientação certa e a salva em **PNG** (os prints deixaram de ser BMP) ou a codifica em **JPEG** reduzido. Usa só `QImage`, seguro em qualquer thread.
- `OcultadorJanelasProprias.ocultar(regiao)` minimiza só as janelas do próprio processo que **intersectam** o monitor capturado e as restaura num `finally`. `ApiJanelasWin32` usa uma instância própria da `user32` com `argtypes`/`restype`; fora do Windows tudo vira no-op.
- O Ollama não aceita imagens em mensagens de ferramenta. `TrabalhadorIA` lê `.imagens` do `ResultadoComImagens`, adiciona uma mensagem de **usuário** com a imagem e o pedido original, e remove os schemas nas chamadas seguintes da troca (`schemas = []`), para a imagem caber no contexto. A imagem nunca é persistida no histórico.

---

## 10. Conversas e persistência

```mermaid
classDiagram
    direction TB

    class ShaulaWindow {
        +id_conversa_atual
        +historico
        +selecionar_conversa()
        +criar_nova_conversa()
        +renomear_conversa_ui()
        +apagar_conversa_ui()
        +abrir_conversa_em_nova_janela()
    }

    class GerenciadorConversas {
        +TITULO_PADRAO
        +TAMANHO_TITULO_AUTOMATICO
        -_pasta_base
        -_caminho_indice
        +listar_conversas()
        +criar_conversa()
        +obter_historico(id)
        +renomear_conversa()
        +alternar_fixado()
        +apagar_conversa()
        +resetar_titulo()
        +marcar_atualizada()
        +atualizar_titulo_automatico()
    }

    class HistoricoConversa {
        +MAX_MENSAGENS_HISTORICO = 60
        +mensagem_sistema
        +caminho_arquivo
        +mensagens
        +adicionar()
        +salvar()
        +apagar()
    }

    class ArmazenamentoJson {
        +trava
        +ler(padrao)
        +gravar(dados)
        +remover()
    }

    class IndiceConversas {
        <<JSON>>
        +indice.json
    }

    class ArquivoConversa {
        <<JSON>>
        +id_conversa.json
    }

    class HistoricoLegado {
        <<JSON legado>>
        +historico_conversa.json
    }

    ShaulaWindow --> GerenciadorConversas
    ShaulaWindow --> HistoricoConversa : atual
    GerenciadorConversas --> HistoricoConversa : obter_historico()
    GerenciadorConversas --> IndiceConversas
    HistoricoConversa --> ArquivoConversa
    GerenciadorConversas ..> HistoricoLegado : migra se necessário
    GerenciadorConversas *-- ArmazenamentoJson : índice
    HistoricoConversa *-- ArmazenamentoJson : arquivo da conversa
    CacheComandos *-- ArmazenamentoJson
```

Estrutura padrão:

```text
~/.shaula/conversas/
├── indice.json
└── <id>.json
```

O arquivo legado `~/.shaula/historico_conversa.json` só é usado no processo de migração quando ainda não existe o novo índice.

`ArmazenamentoJson` grava de forma **atômica** (arquivo temporário + `os.replace`, com novas tentativas no Windows) e mantém uma trava reentrante por caminho, compartilhada por todas as janelas do processo. Leituras de arquivo ausente, corrompido ou com bytes inválidos devolvem o valor padrão. Os métodos do `GerenciadorConversas` que alteram o índice (`criar_conversa`, `renomear_conversa`, `alternar_fixado`, `apagar_conversa`, `resetar_titulo`, `marcar_atualizada`, `atualizar_titulo_automatico`) rodam dentro dessa trava (decorador `_transacional`). `HistoricoConversa` persiste só mensagens `user`/`assistant`; `CacheComandos` e a busca de arquivos usam o mesmo mecanismo.


### 10.1 Lembretes persistentes

`GerenciadorLembretes` grava os lembretes pendentes em `~/.shaula/lembretes.json` com `ArmazenamentoJson`; **o arquivo é a fonte da verdade e os `threading.Timer` são só despertadores**.

```mermaid
classDiagram
    direction LR

    class GerenciadorLembretes {
        +ATRASO_INICIAL_ENTREGA_S = 2.0
        +INTERVALO_ENTRE_ATRASADOS_S = 1.5
        +criar_lembrete(texto, tempo, unidade)
        +listar_lembretes()
        +cancelar_lembrete(id)
        +restaurar()
        -_disparar(id, atrasado)
        -_agendar(id, segundos, atrasado)
    }

    class ArmazenamentoJson {
        +trava
        +ler(padrao)
        +gravar(dados)
    }

    class NotificadorToast {
        +notificar(titulo, texto)
    }

    GerenciadorLembretes *-- ArmazenamentoJson : lembretes.json
    GerenciadorLembretes *-- NotificadorToast
```

- **Restaurar (ao abrir):** o que ainda vai acontecer é reagendado; o que venceu com a Shaula fechada é entregue **uma vez**, como "(atrasado)", escalonado e depois de a janela subir.
- **Disparar:** dentro da trava do arquivo, o lembrete é removido **antes** de ser entregue. Duas janelas com um `Timer` para o mesmo lembrete entregam uma só vez, e um lembrete cancelado em outra janela não dispara.
- **Listar e cancelar** leem/alteram o arquivo, então valem para todas as janelas. Os ids continuam de onde o arquivo parou.
- O horário é gravado com precisão total (guardar só os segundos fazia lembretes curtos nascerem atrasados).

---

## 11. Sequência de uma mensagem na GUI

```mermaid
sequenceDiagram
    participant U as Usuário
    participant G as ShaulaWindow
    participant A as GerenciadorAnexos
    participant H as HistoricoConversa
    participant T as TrabalhadorIA
    participant P as PesquisaInternet
    participant O as Ollama/Qwen
    participant R as RegistroFerramentas
    participant F as Ferramenta

    U->>G: enviar texto/anexos
    G->>A: carregar anexos pendentes
    A-->>G: Anexo(s)
    G->>H: adicionar(user, texto + nota de anexos)
    G->>T: cria e inicia thread

    opt Pedido claro de desligar (sem anexo)
        T->>T: DetectorDesligar.argumentos(texto)
        T->>R: executar("desligar_computador", argumentos) com confirmação
        R-->>T: resultado
        T-->>G: resultado direto (o modelo não é chamado)
    end

    T->>T: adiciona estado atual da internet
    T->>T: isola texto de anexos como referência

    opt Internet ON + pergunta factual + sem anexos
        T->>P: buscar(pergunta)
        P-->>T: resultados + URLs
        T->>T: adiciona RESULTADO DE PESQUISA AUTOMÁTICA
    end

    loop Até resposta final (no máx. 8 rodadas)
        T->>T: OrcamentoContexto.ajustar(messages)
        T->>O: chat(messages, tools*, options, think)
        Note over T,O: *tools omitido quando há anexo
        O-->>T: resposta / tool_calls

        alt Há tool_calls
            loop Para cada chamada
                T->>R: executar(nome, argumentos)
                R->>F: executar(argumentos)
                F-->>R: resultado
                R-->>T: resultado
                T->>T: resultado tool fica só no contexto da troca
            end

            alt nenhuma ferramenta precisa de síntese
                T-->>G: resultados diretos
            else alguma precisa de síntese
                T->>O: próxima rodada com resultado tool
            end
        else Sem tool_call
            T->>T: garante fontes quando aplicável
            T-->>G: resposta final
        end
    end

    alt resposta final
        G->>H: adicionar(assistant, resposta)
        G->>H: salvar()
    else falha / resposta vazia / limite de rodadas
        T-->>G: erro (sinal separado)
        Note over G,H: exibido com ⚠, não vai ao histórico
    end
    G-->>U: exibir resposta
```

---

## 12. Interface gráfica

```mermaid
classDiagram
    direction TB

    class ShaulaWindow {
        <<QMainWindow>>
        +criar_interface()
        +renderizar_historico_salvo()
        +atualizar_lista_conversas()
        +selecionar_conversa()
        +criar_nova_conversa()
        +abrir_dialogo_anexo()
        +anexar_caminhos()
        +enviar()
        +alternar_escuta()
        +receber_resposta()
        +alternar_internet()
        +fechar_shaula()
    }

    class CampoMensagem {
        <<QTextEdit>>
        +enviar_mensagem
        +arquivos_soltos
        +ajustar_altura()
        +keyPressEvent()
        +dragEnterEvent()
        +dropEvent()
    }

    class TrabalhadorIA {
        <<QThread>>
        +detector_desligar
        +resposta_pronta
        +erro
        +pensando
        +interrompido
        +interromper()
        +run()
    }

    class TrabalhadorVoz {
        <<QThread>>
        +estado
        +nivel
        +texto_reconhecido
        +nada_reconhecido
        +erro
        +finalizar()
        +cancelar()
        +run()
    }

    class MedidorNivelVoz {
        <<QWidget>>
        +adicionar_nivel(rms)
        +limpar()
    }

    ShaulaWindow *-- CampoMensagem
    ShaulaWindow --> TrabalhadorIA
    ShaulaWindow --> TrabalhadorVoz
    ShaulaWindow *-- MedidorNivelVoz
    CampoMensagem --> ShaulaWindow : sinais
    TrabalhadorIA --> ShaulaWindow : resposta_pronta / erro / pensando / interrompido
    TrabalhadorVoz --> ShaulaWindow : texto_reconhecido / estado / nivel / erro
```

---

## 13. Componentes externos e dependências

```mermaid
flowchart TB
    SHAULA[Shaula IA 4.70]

    PY[Python 3.x]
    QT[PySide6]
    OLCLIENT[ollama Python client]
    OLSERVER[Ollama server]
    QWEN[qwen3.5:9b]
    NUMPY[numpy]
    PSUTIL[psutil]
    FITZ[pymupdf]
    CV[opencv-python-headless]
    FW[faster-whisper]
    SD[sounddevice]
    WIN[Windows APIs / comandos]
    PS[PowerShell / WinRT Toast]
    WEB[DuckDuckGo / Bing]

    SHAULA --> PY
    SHAULA --> QT
    SHAULA --> OLCLIENT
    OLCLIENT --> OLSERVER
    OLSERVER --> QWEN
    SHAULA --> NUMPY
    SHAULA --> PSUTIL
    SHAULA -. PDF .-> FITZ
    SHAULA -. vídeo .-> CV
    SHAULA -. voz: reconhecimento .-> FW
    SHAULA -. voz: microfone .-> SD
    SHAULA --> WIN
    SHAULA --> PS
    SHAULA -. quando Internet ON .-> WEB
```

---

## 14. Estrutura de módulos e responsabilidades

```mermaid
flowchart TB
    IF[interface.py<br/>GUI + TrabalhadorIA]
    MAIN[main.py<br/>AssistenteTerminal]
    REG[registro.py<br/>composition root]
    BASE[ferramenta.py<br/>classe abstrata]

    CALC[calculadora.py<br/>Calculadora]
    FC[ferramentas_calculo.py<br/>10 ferramentas]
    FS[ferramentas_sistema.py<br/>30 ferramentas]

    CACHE[cache.py<br/>CacheComandos]
    ARQ[arquivos.py<br/>BuscadorArquivos]
    JAN[janelas.py<br/>GerenciadorJanelas]
    PROG[programas.py<br/>GerenciadorProgramas]
    PROC[processos.py<br/>GerenciadorProcessos]
    SIS[sistema.py<br/>InformacoesSistema]
    REDE[rede.py<br/>InformacoesRede]
    CLIP[clipboard.py<br/>GerenciadorClipboard]
    CAP[captura_tela.py<br/>CapturadorTela]
    IMGT[imagem_tela.py<br/>ImagemCapturada / ResultadoComImagens]
    JPR[janelas_proprias.py<br/>OcultadorJanelasProprias]
    CNF[confirmacao.py / confirmacao_qt.py<br/>PoliticaConfirmacao / CaminhoExecutavel / AtrasoDesligamento / ConfirmadorQt]
    INT[intencao_desligar.py<br/>DetectorDesligar]
    CMD[comandos_locais.py<br/>ComandosLocais]
    CON[console.py<br/>CodificacaoConsole]
    LEM[lembretes.py<br/>GerenciadorLembretes]
    NOTI[notificacoes.py<br/>NotificadorToast]
    NET[internet.py<br/>EstadoInternet]
    PESQ[pesquisa.py<br/>PesquisaInternet + estratégias]
    MEM[memoria.py<br/>HistoricoConversa]
    CONV[conversas.py<br/>GerenciadorConversas]
    AN[anexos.py<br/>GerenciadorAnexos + estratégias]
    NOTA[nota_anexo.py<br/>NotaAnexo / DescricaoAnexo]
    CART[cartao_anexo.py<br/>IconeArquivo / CartaoAnexo]
    OLP[ollama_processo.py<br/>GerenciadorOllama]
    OLC[ollama_chat.py<br/>ChatInterrompivel]
    CTX[contexto.py<br/>OrcamentoContexto / CompactadorHistorico / ResumidorHistorico]
    ESF[esforco.py<br/>PerfilEsforco / EstadoEsforco]
    BLC[bloco_codigo.py<br/>BlocoCodigo / DivisorDeBlocos]
    ARM[armazenamento.py<br/>ArmazenamentoJson]
    VOZ[voz.py<br/>GerenciadorVoz + reconhecedores]

    IF --> REG
    MAIN --> REG
    REG --> BASE
    REG --> CALC
    REG --> CACHE
    REG --> ARQ
    REG --> JAN
    REG --> PROG
    REG --> PROC
    REG --> SIS
    REG --> REDE
    REG --> CLIP
    REG --> CAP
    REG --> CNF
    CAP --> IMGT
    CAP --> JPR
    IF --> CNF
    IF --> INT
    IF --> CMD
    CMD --> INT
    NET2[rede.py / ollama_processo.py] --> CON
    REG --> LEM
    REG --> NOTI
    REG --> NET
    REG --> PESQ
    REG --> FC
    REG --> FS

    IF --> MEM
    IF --> CONV
    IF --> AN
    IF --> NOTA
    IF --> CART
    CART --> NOTA
    IF --> OLP
    IF --> OLC
    IF --> CTX
    IF --> ESF
    IF --> BLC
    MAIN --> ESF
    ESF --> ARM
    MAIN --> CTX
    IF --> VOZ
    CONV --> MEM
    CONV --> ARM
    MEM --> ARM
    CACHE --> ARM
    PROG --> PROC
    CAP --> JAN
    LEM --> NOTI
    PESQ --> NET
    ARQ --> CACHE
    JAN --> CACHE
```

---

## 15. Estrutura de arquivos da versão auditada

```text
Shaula IA 4.70/
│
├── interface.py
├── main.py
├── Shaula.bat
├── Instalador Dependências Shaula.bat
├── Instruções Shaula.txt
├── README.md
├── Shaula.ico
│
├── Documentação/
│   ├── Shaula_Casos_de_Uso_4.70.dot
│   ├── Shaula_Casos_de_Uso_4.70.md
│   ├── Shaula_Casos_de_Uso_4.70.png
│   ├── Shaula_Casos_de_Uso_4.70.svg
│   └── Shaula_UML_Completo_4.70.md
│
├── tests/
│   ├── test_analisar_tela.py
│   ├── test_anexos.py
│   ├── test_blocos_codigo.py
│   ├── test_calculadora.py
│   ├── test_cartao_anexo.py
│   ├── test_comandos_locais.py
│   ├── test_confirmacao.py
│   ├── test_console.py
│   ├── test_correcoes.py
│   ├── test_correcoes_sistema.py
│   ├── test_desligar_atalho.py
│   ├── test_desligar_computador.py
│   ├── test_esforco.py
│   ├── test_lembretes.py
│   ├── test_memoria_contexto.py
│   ├── test_nota_anexo.py
│   ├── test_ollama_chat.py
│   ├── test_pesquisa_factual.py
│   ├── test_registro_parametros.py
│   └── test_voz.py
│
└── tools/
    ├── anexos.py
    ├── armazenamento.py
    ├── arquivos.py
    ├── bloco_codigo.py
    ├── cache.py
    ├── calculadora.py
    ├── captura_tela.py
    ├── cartao_anexo.py
    ├── clipboard.py
    ├── comandos_locais.py
    ├── confirmacao.py
    ├── confirmacao_qt.py
    ├── conftest.py
    ├── console.py
    ├── contexto.py
    ├── conversas.py
    ├── esforco.py
    ├── ferramenta.py
    ├── ferramentas_calculo.py
    ├── ferramentas_sistema.py
    ├── imagem_tela.py
    ├── intencao_desligar.py
    ├── interface.py
    ├── internet.py
    ├── janelas.py
    ├── janelas_proprias.py
    ├── lembretes.py
    ├── memoria.py
    ├── nota_anexo.py
    ├── notificacoes.py
    ├── ollama_chat.py
    ├── ollama_processo.py
    ├── pesquisa.py
    ├── processos.py
    ├── programas.py
    ├── rede.py
    ├── registro.py
    ├── sistema.py
    ├── test_correcoes.py
    ├── test_correcoes_sistema.py
    ├── test_esforco.py
    └── voz.py
```

> `tools/conftest.py` é a localização observada no pacote. Pelo escopo do fixture, recomenda-se movê-lo para `tests/conftest.py`.

---

## 16. Testes presentes

```mermaid
classDiagram
    class TestEstrategiaImagem
    class TestEstrategiaTexto
    class TestEstrategiaPDF
    class TestEstrategiaVideo
    class TestGerenciadorAnexos
    class TestCalcularNivel
    class TestNormalizarVolume
    class TestGravador
    class TestLimpadorTranscricao
    class TestGerenciadorVoz
    class TestPreAquecimento
    class TestReconhecedorFasterWhisper
    class TestMicrofoneSounddevice
    class TestChatInterrompivel
    class TestComOllamaClientReal

    TestEstrategiaImagem ..> EstrategiaImagem
    TestEstrategiaTexto ..> EstrategiaTexto
    TestEstrategiaPDF ..> EstrategiaPDF
    TestEstrategiaVideo ..> EstrategiaVideo
    TestGerenciadorAnexos ..> GerenciadorAnexos
    TestCalcularNivel ..> UtilitariosDeAudio
    TestNormalizarVolume ..> UtilitariosDeAudio
    TestGravador ..> Gravador
    TestLimpadorTranscricao ..> LimpadorTranscricao
    TestGerenciadorVoz ..> GerenciadorVoz
    TestPreAquecimento ..> GerenciadorVoz
    TestReconhecedorFasterWhisper ..> ReconhecedorFasterWhisper
    TestMicrofoneSounddevice ..> MicrofoneSounddevice
    TestChatInterrompivel ..> ChatInterrompivel
    TestComOllamaClientReal ..> ChatInterrompivel
```

A suíte tem **524 testes** em vinte arquivos (contagem estática, com os casos de `parametrize` expandidos): `tests/test_analisar_tela.py` (44), `tests/test_anexos.py` (17), `tests/test_blocos_codigo.py` (36, blocos de código), `tests/test_calculadora.py` (25, `Calculadora`), `tests/test_cartao_anexo.py` (13, `IconeArquivo`, `CartaoAnexo` e a integração com a janela), `tests/test_comandos_locais.py` (36, `ComandosLocais`), `tests/test_confirmacao.py` (76, política, registro, terminal, caixa do Qt, `AtrasoDesligamento` e contornos de executáveis), `tests/test_console.py` (3, `CodificacaoConsole`), `tests/test_correcoes.py` (41), `tests/test_correcoes_sistema.py` (29), `tests/test_desligar_atalho.py` (19, `DetectorDesligar`), `tests/test_desligar_computador.py` (6, `desligar_computador`), `tests/test_esforco.py` (42, níveis de esforço), `tests/test_lembretes.py` (19), `tests/test_memoria_contexto.py` (12, `CompactadorHistorico`, `ResumidorHistorico` e o orçamento com resumo), `tests/test_nota_anexo.py` (19, `NotaAnexo` e `DescricaoAnexo`), `tests/test_ollama_chat.py` (10, incluindo o `ollama.Client` real contra um servidor HTTP local lento), `tests/test_pesquisa_factual.py` (18, `DetectorPerguntaFactual`), `tests/test_registro_parametros.py` (4, `RegistroFerramentas`), `tests/test_voz.py` (55, todos com fontes e motores falsos, sem microfone nem modelo). Só `test_anexos`, `test_voz` e `test_ollama_chat` usam classes `Test…` (diagrama acima); os demais são funções. Fora do Windows, os testes que importam `interface.py` simulam `ctypes.windll`.

---

## 17. Inconsistências do pacote que não são problemas de UML

Ainda presentes, para corrigir no código/empacotamento:

1. Não existe `tests/conftest.py`: o fixture que isola a pasta pessoal está em `tools/conftest.py` e, pelo escopo do pytest, não vale para os testes de `tests/`.
2. `tools/interface.py` (cópia antiga de `interface.py`; nada a importa) e `tools/test_correcoes.py`, `tools/test_correcoes_sistema.py` e `tools/test_esforco.py` (duplicatas de `tests/`) existem no pacote e devem ser apagados.
3. O instalador instala e verifica `requests`, que nenhum módulo usa, e não instala `pytest`, apesar de o pacote incluir uma suíte pytest.
4. `ComandosLocais.eh_apagar_conversa()` apaga o histórico sem pedir confirmação (a frase exata é a única proteção).
5. As ferramentas não são interrompíveis, e `closeEvent` espera só 3 s pela thread da IA.
6. `ConfirmadorQt` não chama `deleteLater()` na caixa depois de usada.

---

## 18. Resumo arquitetural

A Shaula 4.70 se divide em cinco blocos principais:

1. **Interface e execução da IA** — `ShaulaWindow`, `CampoMensagem`, `TrabalhadorIA`.
2. **Ferramentas e serviços** — `Ferramenta`, `RegistroFerramentas`, 40 ferramentas concretas e classes de serviço injetadas.
3. **Contexto e persistência** — `GerenciadorConversas`, `HistoricoConversa`, `CacheComandos`, `ArmazenamentoJson` (gravação atômica) e `OrcamentoContexto` (limite de tokens por chamada, com `CompactadorHistorico` e `ResumidorHistorico` para a conversa antiga não sumir do contexto).
4. **Integrações e estratégias** — pesquisa (`MecanismoBusca`), anexos (`EstrategiaAnexo`) voz (`ReconhecedorFala`, `FonteAudio`) e interrupção da resposta (`ChatInterrompivel`).
5. **Windows/Ollama** — controles locais, notificações, janelas, processos, captura de tela e comunicação com `qwen3.5:9b` via Ollama.

Esse desenho corresponde ao código-fonte auditado da versão 4.70.
