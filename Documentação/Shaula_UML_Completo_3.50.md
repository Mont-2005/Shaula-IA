# UML da Shaula — versão 3.50

Este documento foi revisado contra o código-fonte presente no pacote **Shaula IA 3.50 docu**.

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
        +trabalhador: TrabalhadorIA
        +anexos_pendentes
        +enviar()
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
        +resposta_pronta
        +pensando
        +run()
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

    GerenciadorConversas --> HistoricoConversa : cria/carrega
    TrabalhadorIA --> RegistroFerramentas
    TrabalhadorIA --> Anexo : recebe anexos processados
```

---

## 2. Entrypoints e inicialização

```mermaid
flowchart TB
    USER[Usuário]
    INSTALL[Instalador Dependências Shaula.bat]
    BAT[Shaula.bat]
    GUI[interface.py]
    CLI[main.py]
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

**Importante:** `main.py` não importa nem inicia `interface.py`. Os dois são entrypoints independentes que reutilizam o mesmo subsistema de ferramentas.

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

    RegistroFerramentas o-- Ferramenta : 39 instâncias
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

### 3.2 Ferramentas de sistema, arquivos e interação — 29

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
```

Não existem no código as classes genéricas `CapturaTelaFerramenta`, `ClipboardFerramenta`, `LembretesFerramenta`, `NotificacoesFerramenta`, `ProcessosFerramenta`, `RedeFerramenta`, `MemoriaFerramenta` ou `ConversasFerramenta` que apareciam no UML anterior.

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
    T_CAP[tirar_print] --> CAP
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
        +LADO_MAXIMO_PX = 1568
        +processar(caminho)
    }

    class EstrategiaPDF {
        +PAGINAS_MAXIMAS_RENDERIZADAS = 8
        +CARACTERES_MAXIMOS_TEXTO = 12000
        +processar(caminho)
    }

    class EstrategiaVideo {
        +NUMERO_DE_FRAMES = 6
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

---

## 8. Conversas e persistência

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
```

Estrutura padrão:

```text
~/.shaula/conversas/
├── indice.json
└── <id>.json
```

O arquivo legado `~/.shaula/historico_conversa.json` só é usado no processo de migração quando ainda não existe o novo índice.

---

## 9. Sequência de uma mensagem na GUI

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

    T->>T: adiciona estado atual da internet
    T->>T: isola texto de anexos como referência

    opt Internet ON + pergunta factual
        T->>P: buscar(pergunta)
        P-->>T: resultados + URLs
        T->>T: adiciona RESULTADO DE PESQUISA AUTOMÁTICA
    end

    loop Até resposta final
        T->>O: chat(messages, tools, options)
        O-->>T: resposta / tool_calls

        alt Há tool_calls
            loop Para cada chamada
                T->>R: executar(nome, argumentos)
                R->>F: executar(argumentos)
                F-->>R: resultado
                R-->>T: resultado
                T->>H: mantém resultado tool em memória
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

    G->>H: adicionar(assistant, resposta)
    G->>H: salvar()
    G-->>U: exibir resposta
```

---

## 10. Interface gráfica

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
        +resposta_pronta
        +pensando
        +run()
    }

    ShaulaWindow *-- CampoMensagem
    ShaulaWindow --> TrabalhadorIA
    CampoMensagem --> ShaulaWindow : sinais
    TrabalhadorIA --> ShaulaWindow : resposta_pronta / pensando
```

---

## 11. Componentes externos e dependências

```mermaid
flowchart TB
    SHAULA[Shaula IA 3.50]

    PY[Python 3.x]
    QT[PySide6]
    OLCLIENT[ollama Python client]
    OLSERVER[Ollama server]
    QWEN[qwen3.5:9b]
    NUMPY[numpy]
    PSUTIL[psutil]
    FITZ[pymupdf]
    CV[opencv-python-headless]
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
    SHAULA --> WIN
    SHAULA --> PS
    SHAULA -. quando Internet ON .-> WEB
```

---

## 12. Estrutura de módulos e responsabilidades

```mermaid
flowchart TB
    IF[interface.py<br/>GUI + TrabalhadorIA]
    MAIN[main.py<br/>CLI independente]
    REG[registro.py<br/>composition root]
    BASE[ferramenta.py<br/>classe abstrata]

    CALC[calculadora.py<br/>Calculadora]
    FC[ferramentas_calculo.py<br/>10 ferramentas]
    FS[ferramentas_sistema.py<br/>29 ferramentas]

    CACHE[cache.py<br/>CacheComandos]
    ARQ[arquivos.py<br/>BuscadorArquivos]
    JAN[janelas.py<br/>GerenciadorJanelas]
    PROG[programas.py<br/>GerenciadorProgramas]
    PROC[processos.py<br/>GerenciadorProcessos]
    SIS[sistema.py<br/>InformacoesSistema]
    REDE[rede.py<br/>InformacoesRede]
    CLIP[clipboard.py<br/>GerenciadorClipboard]
    CAP[captura_tela.py<br/>CapturadorTela]
    LEM[lembretes.py<br/>GerenciadorLembretes]
    NOTI[notificacoes.py<br/>NotificadorToast]
    NET[internet.py<br/>EstadoInternet]
    PESQ[pesquisa.py<br/>PesquisaInternet + estratégias]
    MEM[memoria.py<br/>HistoricoConversa]
    CONV[conversas.py<br/>GerenciadorConversas]
    AN[anexos.py<br/>GerenciadorAnexos + estratégias]
    OLP[ollama_processo.py<br/>GerenciadorOllama]

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
    REG --> LEM
    REG --> NOTI
    REG --> NET
    REG --> PESQ
    REG --> FC
    REG --> FS

    IF --> MEM
    IF --> CONV
    IF --> AN
    IF --> OLP
    CONV --> MEM
    PROG --> PROC
    CAP --> JAN
    LEM --> NOTI
    PESQ --> NET
    ARQ --> CACHE
    JAN --> CACHE
```

---

## 13. Estrutura de arquivos da versão auditada

```text
Shaula IA 3.50 docu/
│
├── interface.py
├── main.py
├── Shaula.bat
├── Instalador Dependências Shaula.bat
├── Instruções Shaula.txt
├── README.md
├── Shaula.ico
├── desktop.ini
│
├── Documentação/
│   └── Shaula_UML_Completo_3.50.md
│
├── tests/
│   └── test_anexos.py
│
└── tools/
    ├── anexos.py
    ├── arquivos.py
    ├── cache.py
    ├── calculadora.py
    ├── captura_tela.py
    ├── clipboard.py
    ├── conftest.py
    ├── conversas.py
    ├── ferramenta.py
    ├── ferramentas_calculo.py
    ├── ferramentas_sistema.py
    ├── internet.py
    ├── janelas.py
    ├── lembretes.py
    ├── memoria.py
    ├── notificacoes.py
    ├── ollama_processo.py
    ├── pesquisa.py
    ├── processos.py
    ├── programas.py
    ├── rede.py
    ├── registro.py
    └── sistema.py
```

> `tools/conftest.py` é a localização observada no pacote. Pelo escopo do fixture, recomenda-se movê-lo para `tests/conftest.py`.

---

## 14. Testes presentes

```mermaid
classDiagram
    class TestEstrategiaImagem
    class TestEstrategiaTexto
    class TestEstrategiaPDF
    class TestEstrategiaVideo
    class TestGerenciadorAnexos

    TestEstrategiaImagem ..> EstrategiaImagem
    TestEstrategiaTexto ..> EstrategiaTexto
    TestEstrategiaPDF ..> EstrategiaPDF
    TestEstrategiaVideo ..> EstrategiaVideo
    TestGerenciadorAnexos ..> GerenciadorAnexos
```

`tests/test_anexos.py` contém 15 testes. A suíte dos demais serviços, mencionada em documentação anterior, não está presente no pacote 3.50 auditado.

---

## 15. Inconsistências do pacote que não são problemas de UML

Durante a conferência foram encontrados pontos que devem ser corrigidos no código/empacotamento, não apenas na documentação:

1. `tools/conftest.py` deveria estar em `tests/conftest.py` para corresponder ao propósito declarado.
2. `main.py` ainda mostra `Shaula v1.80` no banner.
3. `CacheComandos` usa `~/.Shaula`, enquanto os demais componentes usam `~/.shaula`.
4. O instalador não instala `pytest` explicitamente, apesar de o pacote incluir uma suíte pytest.

---

## 16. Resumo arquitetural

A Shaula 3.50 se divide em cinco blocos principais:

1. **Interface e execução da IA** — `ShaulaWindow`, `CampoMensagem`, `TrabalhadorIA`.
2. **Ferramentas e serviços** — `Ferramenta`, `RegistroFerramentas`, 39 ferramentas concretas e classes de serviço injetadas.
3. **Contexto e persistência** — `GerenciadorConversas`, `HistoricoConversa`, `CacheComandos`.
4. **Integrações e estratégias** — pesquisa (`MecanismoBusca`) e anexos (`EstrategiaAnexo`).
5. **Windows/Ollama** — controles locais, notificações, janelas, processos, captura de tela e comunicação com `qwen3.5:9b` via Ollama.

Esse desenho corresponde ao código-fonte auditado da versão 3.50 e substitui as representações legadas que tratavam classes atuais como módulos ou listavam ferramentas que não existem mais com aqueles nomes.
