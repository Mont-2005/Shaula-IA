# Shaula IA 4.70 — Assistente Pessoal Local

A **Shaula** é uma assistente virtual desenvolvida para funcionar localmente no Windows. Ela utiliza o **Ollama**, com o modelo `qwen3.5:9b`, para conversar, interpretar solicitações e executar diferentes tarefas no computador.

A aplicação possui uma interface gráfica desenvolvida com PySide6 (`interface.py`), mas também oferece uma versão independente para utilizar pelo terminal (`main.py`).

Esta documentação foi atualizada com base no código-fonte da versão **Shaula IA 4.70**, descrevendo os recursos e a organização que realmente fazem parte desta versão.

## O que mudou na versão 4.70

A versão 4.70 trouxe melhorias importantes na organização interna e no funcionamento da Shaula. O projeto passou a utilizar uma estrutura mais organizada em classes, separando melhor as responsabilidades de cada funcionalidade.

Entre as principais mudanças estão:

- **Melhoria da memória da conversa:** agora a Shaula consegue aproveitar melhor o histórico durante as respostas. Quando o contexto fica cheio, mensagens antigas são resumidas ou compactadas para preservar as informações mais importantes.
- **Novos níveis de esforço:** foram ampliados os limites de contexto e resposta, permitindo que a assistente utilize mais informações durante o raciocínio.
- **Atalho para desligar o computador:** pedidos diretos, como "desligue o computador", são reconhecidos antes de chegar ao modelo, garantindo que a caixa de confirmação seja apresentada.
- **Desligamento programado:** agora é possível informar o tempo até o desligamento. O padrão é 60 segundos, mas também é possível desligar imediatamente.
- **Melhorias nas confirmações:** as caixas de confirmação aparecem à frente das outras janelas, mesmo quando a Shaula está minimizada. Também é possível cancelar uma confirmação pendente pelo botão de interrupção.
- **Correções de segurança e funcionamento:** foram corrigidos problemas relacionados à abertura de arquivos e programas, execução de comandos, lembretes, pesquisas na internet, cálculos e gerenciamento de processos.
- **Barra de menus:** a janela ganhou um menu principal com acesso a todas as funcionalidades e a todos os dados do aplicativo (conversas, anexos, lembretes, processos, janelas e monitores, capturas, rede, internet, calculadora, esforço e voz). Veja a seção [Menu principal](#menu-principal).
- **Documentação atualizada:** a estrutura de arquivos, os comandos e as informações técnicas foram revisados para corresponder ao conteúdo real do pacote.

## Como executar

A maneira mais simples de iniciar a Shaula é dar dois cliques no arquivo `Shaula.bat`.

Esse arquivo prepara o ambiente antes de abrir a interface:

1. Define a pasta da própria Shaula como diretório de trabalho.
2. Verifica se o Ollama está funcionando em `http://127.0.0.1:11434/api/tags`.
3. Caso necessário, procura o executável `ollama.exe` no PATH ou na pasta de instalação padrão.
4. Inicia o servidor Ollama em segundo plano.
5. Aguarda a inicialização do servidor, realizando até 20 tentativas.
6. Verifica se o ambiente virtual `.venv` está disponível.
7. Inicia a interface gráfica por meio de `interface.py`.

Se o Ollama não iniciar dentro do tempo esperado, o processo é encerrado com uma mensagem de erro.

A interface também identifica problemas de comunicação com o Ollama, mas não possui um mecanismo próprio de reconexão automática para repetir uma chamada que falhou.

### Configurações por variáveis de ambiente

Algumas opções podem ser configuradas por meio de variáveis de ambiente:

| Variável | Função |
|---|---|
| `SHAULA_CONFIRMAR` | Controla as confirmações de ações sensíveis. O padrão é `1` (ativado). O valor `0` desativa as confirmações. |
| `SHAULA_ESFORCO` | Define o nível de esforço inicial, caso ainda não exista uma configuração salva. Aceita `baixo`, `medio`, `alto`, `extra` ou `max`. |

A escolha feita pelo botão **Esforço** da interface, ou pelo comando correspondente no terminal, fica salva em `~/.shaula/configuracoes.json` e tem prioridade sobre a variável de ambiente.

### Níveis de esforço

A Shaula possui cinco níveis de esforço, selecionados pelo botão **🧠 Esforço** na barra superior, ao lado do controle de Internet.

Cada nível define quanto contexto o modelo pode utilizar, o limite de resposta e a quantidade máxima de rodadas de ferramentas.

| Nível | Raciocínio | Contexto (`num_ctx`) | Resposta (`num_predict`) | Rodadas |
|---|---|---:|---:|---:|
| Baixo | Não | 10240 | 1024 | 4 |
| **Médio (padrão)** | Sim | 11264 | 2048 | 8 |
| Alto | Sim | 13312 | 3072 | 8 |
| Extra | Sim | 15360 | 4096 | 10 |
| Máx | Sim | 18432 | 6144 | 12 |

Alguns detalhes importantes sobre esses níveis:

- Quanto maior o esforço, mais informações podem ser utilizadas durante a resposta. Em contrapartida, o processamento demora mais e exige mais memória de vídeo.
- O limite de resposta também inclui os tokens utilizados pelo raciocínio do modelo.
- Os níveis Extra e Máx podem ultrapassar a memória disponível em placas de vídeo com 8 GB de VRAM, fazendo com que parte do modelo seja executada pela CPU.
- Nos níveis Baixo e Médio, sobram aproximadamente 3.200 tokens para o histórico. No nível Máx, esse espaço chega a aproximadamente 6.300 tokens.
- Quando o nível é alterado, o Ollama precisa carregar novamente o modelo na próxima mensagem.
- A configuração é compartilhada entre todas as janelas e permanece salva entre as sessões.
- Se o limite de resposta for consumido pelo raciocínio e não houver espaço para gerar uma resposta, a Shaula informa o problema e sugere aumentar o nível.

Os valores foram definidos pensando no modelo `qwen3.5:9b` em uma GPU de 8 GB. Eles podem ser ajustados em `CatalogoEsforco.PERFIS`, no arquivo `tools/esforco.py`.

No terminal, também é possível consultar ou alterar o nível utilizando:

```text
esforço
esforço alto
```

### Instalação das dependências

O pacote inclui o arquivo `Instalador Dependências Shaula.bat`, responsável por preparar o ambiente virtual e instalar as dependências necessárias.

Entre os componentes utilizados estão:

- Python 3.13;
- NumPy;
- psutil;
- PySide6;
- Ollama;
- requests;
- PyMuPDF;
- OpenCV;
- faster-whisper e sounddevice (opcionais, utilizados para reconhecimento de voz);
- Ollama para Windows;
- Modelo `qwen3.5:9b`.

O reconhecimento de voz é opcional. Caso alguma das bibliotecas necessárias não esteja disponível, a Shaula continua funcionando normalmente, apenas sem essa funcionalidade.

**Observações:** o instalador não utiliza `requirements.txt`, pois esse arquivo não existe no pacote. Além disso, `requests` é instalado, mas não é utilizado diretamente pelo código, e `pytest` precisa ser instalado separadamente caso queira executar os testes.

---

## Estrutura de arquivos

Abaixo está a organização encontrada no pacote da versão 4.70:

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
│   ├── test_menu_principal.py
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
    ├── menu_principal.py
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

## Organização e funcionamento interno

A Shaula utiliza uma arquitetura baseada em classes, procurando separar a interface, o processamento das mensagens, as ferramentas e o armazenamento de dados.

### Interface gráfica

A classe `ShaulaWindow`, localizada em `interface.py`, é responsável pela janela principal e pela comunicação entre os diferentes componentes.

Ela gerencia:

- `CacheComandos`;
- `RegistroFerramentas`;
- `GerenciadorOllama`;
- `GerenciadorConversas`;
- `HistoricoConversa`;
- `GerenciadorAnexos`;
- `ConfirmadorQt`;
- `DetectorDesligar`;
- `MenuPrincipal`;
- `TrabalhadorIA`.

Além disso, a janela controla a barra lateral de conversas, os anexos, a conexão com a internet, a exibição do histórico e a abertura de conversas em novas janelas.

A barra de menus é montada pela classe `MenuPrincipal`, de `tools/menu_principal.py`, logo depois de `criar_interface()`.

Cada mensagem processada utiliza uma instância própria de `TrabalhadorIA`, que executa o trabalho em uma thread separada para não bloquear a interface.

### Como uma mensagem é processada

Quando o usuário envia uma mensagem, ela passa por algumas etapas antes de chegar ao modelo.

1. `ShaulaWindow.enviar()` verifica o conteúdo da mensagem e os anexos.
2. Comandos locais, como sair ou limpar a conversa atual, são identificados antes de chamar o modelo.
3. A mensagem é adicionada ao histórico da conversa selecionada.
4. Se houver anexos, o `GerenciadorAnexos` identifica o tipo de arquivo e realiza o processamento necessário.
5. Uma nova `TrabalhadorIA` é criada para processar a solicitação.
6. Antes de consultar o modelo, o `DetectorDesligar` verifica se existe um pedido direto e claro para desligar o computador. Se encontrar, chama a ferramenta correspondente e apresenta a confirmação sem precisar consultar o modelo.
7. A thread prepara o contexto, incluindo o estado da internet e, quando necessário, o conteúdo extraído dos anexos.
8. Se a internet estiver ligada e não houver anexos, o `DetectorPerguntaFactual` pode realizar uma pesquisa automática antes da consulta ao modelo.
9. O `OrcamentoContexto` verifica o tamanho das informações e ajusta o histórico para que tudo caiba no limite definido pelo nível de esforço.
10. O Ollama recebe a mensagem, as configurações de raciocínio e os schemas das ferramentas disponíveis. Quando há anexos, as ferramentas são omitidas para liberar espaço no contexto.
11. Caso o modelo solicite alguma ferramenta, o `RegistroFerramentas` identifica a implementação correspondente e executa a operação. A quantidade de rodadas é limitada pelo nível de esforço.
12. Quando uma ferramenta não precisa de síntese, seu resultado é apresentado diretamente, sem uma nova chamada ao modelo.
13. Quando uma ferramenta precisa de interpretação, como a pesquisa na internet, o resultado volta ao modelo para a elaboração da resposta final.
14. Por último, `ShaulaWindow.receber_resposta()` apresenta a resposta e salva o conteúdo no histórico.

As mensagens internas das ferramentas não são salvas no histórico permanente. Elas existem apenas durante o processamento daquela solicitação.

Se ocorrer algum erro, como falha de comunicação com o Ollama ou limite de rodadas atingido, a interface apresenta um aviso, mas esse aviso não é registrado como resposta da assistente.

---

## Menu principal

A janela possui uma barra de menus, montada por `MenuPrincipal` (`tools/menu_principal.py`), que dá acesso pela interface a todas as funcionalidades da Shaula. Ela cobre as **40 ferramentas** do `RegistroFerramentas` e as ações sobre conversas, anexos, esforço e voz. Cada janela aberta possui a sua própria barra.

### Menus disponíveis

| Menu | Itens |
|---|---|
| **Arquivo** | Nova conversa (`Ctrl+N`), abrir a conversa atual em nova janela, anexar arquivo (`Ctrl+O`) e sair da Shaula (`Ctrl+Q`). |
| **Conversas** | Ir para a conversa (lista todas, com a atual marcada e as fixadas com 📌), renomear, fixar ou desafixar, apagar e mostrar ou ocultar a barra lateral (`Ctrl+B`). |
| **Programas e arquivos** | `abrir_programa`, `fechar_programa`, menu Iniciar, `buscar_arquivo` e `abrir_arquivo`. |
| **Calculadora** | `calcular`, `converter_base` e o submenu **Matrizes** (soma, subtração, multiplicação, escalar, transposta, determinante, inversa e potência). |
| **Lembretes** | Criar, listar e cancelar lembretes. |
| **Janelas e telas** | Listar monitores e janelas, controlar janela, mover programa para um monitor ou para outro monitor, tirar print e analisar a tela. |
| **Sistema** | Informações do hardware, listar processos (comuns e protegidos), finalizar processo, bloquear a tela, desligar o computador, cancelar o desligamento, copiar texto e colar da área de transferência. |
| **Rede e internet** | Chave **Internet ligada**, pesquisar na internet, IP local, Wi-Fi e ping. |
| **Configurações** | Nível de esforço (os cinco níveis, com o atual marcado) e **Falar um comando (`Ctrl+M`)**. |
| **Ajuda** | Lista das ferramentas disponíveis, gerada a partir do registro, e **Sobre a Shaula**. |

As ferramentas `ativar_internet` e `desativar_internet` são alcançadas pela chave **Internet ligada**, que usa o mesmo `alternar_internet()` do botão da barra superior.

### Como um item de menu é executado

1. Se a ferramenta tem parâmetros, o `DialogoParametros` monta um formulário a partir do esquema JSON dela (o mesmo que o Ollama recebe). Há campos de texto, número inteiro e decimal (aceita vírgula), lista de opções, sim/não e matriz. Os campos obrigatórios são validados antes de executar.
2. Matrizes podem ser digitadas com uma linha por linha e valores separados por espaço ou vírgula, ou no formato JSON (`[[2, 1], [3, 4]]`). A leitura é feita por `ler_matriz()`.
3. O pedido aparece no chat como mensagem do usuário, no formato `[Menu] Nome do item`, seguido dos parâmetros.
4. O `TrabalhadorFerramenta` executa a ferramenta em uma thread, pelo `RegistroFerramentas.executar()`. Por isso as **confirmações de ações sensíveis continuam valendo** (desligar, finalizar processo, fechar programa e fechar janela).
5. O resultado é apresentado por `ShaulaWindow.receber_resposta()` e salvo no histórico, como qualquer outra resposta.

Os itens do menu **não passam pelo modelo**, então a resposta é imediata e não depende do nível de esforço.

### Ferramentas que seguem pelo chat

`pesquisar_internet` e `analisar_tela` precisam do modelo (a primeira para sintetizar os resultados, a segunda para interpretar a imagem). Por isso, os itens correspondentes montam uma frase (como "Pesquise na internet: ...") e a enviam pelo mesmo fluxo da mensagem digitada. Essa frase não é enviada se houver anexos pendentes, pois mensagens com anexo são processadas sem ferramentas.

### Cuidados

- Enquanto a Shaula responde, executa um item do menu ou grava a voz, os itens que executam ferramentas avisam que é preciso esperar. O `TrabalhadorFerramenta` fica em `ShaulaWindow.trabalhador`, então enviar mensagens, trocar ou apagar conversas e fechar a janela também esperam a ferramenta terminar.
- O atalho `Ctrl+M` continua pertencendo à janela (`QShortcut`). No menu ele só aparece no texto, para não haver atalho ambíguo.
- O texto das conversas é protegido contra o caractere `&`, que o Qt interpretaria como atalho de menu.

### Componentes

| Classe ou função | Responsabilidade |
|---|---|
| `MenuPrincipal` | Monta a barra de menus e liga cada item à janela. |
| `CatalogoMenu` | Define em qual menu fica cada ferramenta e informa quais ferramentas o menu alcança. |
| `ItemFerramenta` e `Submenu` | Descrevem os itens e submenus do catálogo. |
| `DialogoParametros` | Formulário gerado a partir do esquema de parâmetros. |
| `TrabalhadorFerramenta` | Executa a ferramenta fora da thread da interface. |
| `ler_matriz()` | Converte o texto digitado em matriz retangular de números. |

---

## Registro de ferramentas

O `RegistroFerramentas` é responsável por organizar e disponibilizar as ferramentas que a Shaula pode utilizar.

Ele instancia os serviços necessários, compartilha objetos que precisam ser utilizados por diferentes ferramentas e encaminha cada solicitação para sua implementação correspondente.

### Serviços utilizados

Entre os principais serviços criados pelo registro estão:

- `EstadoInternet`;
- `CacheComandos`;
- `Calculadora`;
- `BuscadorArquivos`;
- `GerenciadorJanelas`;
- `GerenciadorProcessos`;
- `GerenciadorProgramas`;
- `GerenciadorClipboard`;
- `InformacoesRede`;
- `InformacoesSistema`;
- `PesquisaInternet`;
- `CapturadorTela`;
- `NotificadorToast`;
- `GerenciadorLembretes`.

Alguns serviços também dependem de outros para funcionar corretamente:

- `BuscadorArquivos` utiliza `CacheComandos`.
- `GerenciadorJanelas` também utiliza `CacheComandos`.
- `GerenciadorProgramas` recebe `GerenciadorProcessos`.
- `PesquisaInternet` utiliza `EstadoInternet`.
- `CapturadorTela` trabalha com `GerenciadorJanelas` e `OcultadorJanelasProprias`.
- `GerenciadorLembretes` utiliza `NotificadorToast` e `ArmazenamentoJson`.
- `RegistroFerramentas` recebe as configurações e o componente responsáveis pelas confirmações de ações sensíveis.

### Ferramentas disponíveis

A versão gráfica possui **40 ferramentas concretas**, divididas entre operações matemáticas e funções relacionadas ao sistema.

#### Ferramentas de cálculo — 10

| Classe | Ferramenta |
|---|---|
| `CalcularFerramenta` | `calcular` |
| `MatrizSomaFerramenta` | `matriz_soma` |
| `MatrizSubtracaoFerramenta` | `matriz_subtracao` |
| `MatrizMultiplicacaoFerramenta` | `matriz_multiplicacao` |
| `MatrizEscalarFerramenta` | `matriz_escalar` |
| `MatrizTranspostaFerramenta` | `matriz_transposta` |
| `MatrizDeterminanteFerramenta` | `matriz_determinante` |
| `MatrizInversaFerramenta` | `matriz_inversa` |
| `MatrizPotenciaFerramenta` | `matriz_potencia` |
| `ConverterBaseFerramenta` | `converter_base` |

#### Ferramentas do sistema — 30

| Classe | Ferramenta |
|---|---|
| `AbrirProgramaFerramenta` | `abrir_programa` |
| `FecharProgramaFerramenta` | `fechar_programa` |
| `BuscarArquivoFerramenta` | `buscar_arquivo` |
| `AbrirArquivoFerramenta` | `abrir_arquivo` |
| `DesligarComputadorFerramenta` | `desligar_computador` |
| `CancelarDesligamentoFerramenta` | `cancelar_desligamento` |
| `BloquearTelaFerramenta` | `bloquear_tela` |
| `TestarPingFerramenta` | `testar_ping` |
| `InformacoesHardwareFerramenta` | `informacoes_hardware` |
| `AbrirMenuIniciarFerramenta` | `abrir_menu_iniciar` |
| `AtivarInternetFerramenta` | `ativar_internet` |
| `DesativarInternetFerramenta` | `desativar_internet` |
| `PesquisarInternetFerramenta` | `pesquisar_internet` |
| `ListarMonitoresFerramenta` | `listar_monitores` |
| `ListarJanelasAbertasFerramenta` | `listar_janelas_abertas` |
| `MoverProgramaMonitorFerramenta` | `mover_programa_monitor` |
| `MoverParaOutroMonitorFerramenta` | `mover_para_outro_monitor` |
| `TirarPrintFerramenta` | `tirar_print` |
| `ControlarJanelaFerramenta` | `controlar_janela` |
| `CriarLembreteFerramenta` | `criar_lembrete` |
| `ListarLembretesFerramenta` | `listar_lembretes` |
| `CancelarLembreteFerramenta` | `cancelar_lembrete` |
| `ListarProcessosFerramenta` | `listar_processos` |
| `ListarProcessosProtegidosFerramenta` | `listar_processos_protegidos` |
| `FinalizarProcessoFerramenta` | `finalizar_processo` |
| `CopiarTextoFerramenta` | `copiar_texto` |
| `ColarTextoFerramenta` | `colar_texto` |
| `ObterIpLocalFerramenta` | `obter_ip_local` |
| `VerificarWifiFerramenta` | `verificar_wifi` |
| `AnalisarTelaFerramenta` | `analisar_tela` |

O registro também verifica se os parâmetros obrigatórios foram enviados. Caso o modelo esqueça algum deles, a Shaula informa qual informação está faltando, em vez de apresentar um erro genérico.

### Evitando chamadas desnecessárias ao modelo

Nem toda ferramenta precisa que o modelo interprete seu resultado.

Por isso, a classe `Ferramenta` possui a propriedade `precisa_de_sintese`, que é `False` por padrão.

A maioria das operações locais retorna seu resultado diretamente ao usuário. A exceção é a pesquisa na internet, que precisa passar novamente pelo modelo para transformar os resultados encontrados em uma resposta organizada.

---

## Modo de terminal — `main.py`

Além da interface gráfica, a Shaula também pode ser utilizada diretamente pelo terminal.

O arquivo `main.py` funciona de maneira independente e não inicia `interface.py` nem faz parte do processo executado por `Shaula.bat`.

Ele utiliza o mesmo `RegistroFerramentas`, mas disponibiliza um conjunto menor de funcionalidades.

A lógica principal está na classe `AssistenteTerminal`, que mantém o histórico, o registro de ferramentas e o controle do contexto.

O processamento só começa quando `AssistenteTerminal().executar()` é chamado, por meio da função `main()`.

O modo de terminal possui 13 ferramentas:

- `abrir_programa`;
- `buscar_arquivo`;
- `abrir_arquivo`;
- `calcular`;
- `matriz_soma`;
- `matriz_subtracao`;
- `matriz_multiplicacao`;
- `matriz_escalar`;
- `matriz_transposta`;
- `matriz_determinante`;
- `matriz_inversa`;
- `matriz_potencia`;
- `converter_base`.

Assim como na interface gráfica, ele utiliza os níveis de esforço, ajusta o contexto antes das chamadas ao Ollama e limita a quantidade de rodadas de ferramentas.

Para encerrar a execução, basta digitar `sair` ou utilizar `Ctrl+C` ou `Ctrl+D`.

---

## Pesquisa na internet — Strategy

A pesquisa na internet foi organizada utilizando o padrão de projeto **Strategy**, permitindo trabalhar com diferentes mecanismos de busca sem precisar alterar a lógica principal do sistema.

O controle de acesso à internet fica em `EstadoInternet`, que começa desativado.

A classe `PesquisaInternet` recebe esse estado e os mecanismos disponíveis. Atualmente, utiliza:

1. `DuckDuckGo` como mecanismo principal.
2. `Bing` como alternativa caso a primeira busca não seja suficiente.

Ambos implementam a abstração `MecanismoBusca`.

Também existem componentes auxiliares:

- `DuckParser`: interpreta os resultados do DuckDuckGo.
- `BingParser`: interpreta os resultados do Bing.
- `FormatadorTexto`: organiza links e extrai URLs.
- `DetectorPerguntaFactual`: identifica perguntas que podem precisar de uma pesquisa automática.

### Pesquisa automática

Quando a internet está ativada, a Shaula pode identificar que uma pergunta precisa de informações externas e realizar uma busca antes de consultar o modelo.

O `DetectorPerguntaFactual` considera, entre outros critérios:

- Mensagens terminadas em `?` ou `？`.
- Perguntas que começam com expressões como "quem", "quando", "onde", "como", "qual", "quanto" e "é verdade".

Entretanto, nem toda pergunta precisa de uma pesquisa na internet.

O sistema possui algumas exceções para evitar buscas desnecessárias, principalmente quando a mensagem envolve:

- A própria Shaula.
- Informações do usuário ou do computador.
- Processos, janelas, monitores e lembretes.
- Cálculos matemáticos e conversões.
- Matrizes e operações numéricas.

Nesses casos, a intenção é permitir que o modelo utilize as ferramentas locais disponíveis.

Também são identificadas perguntas que dependem do histórico da conversa, como "e quando isso aconteceu?", "e o segundo?" ou "o que eu falei?".

Isso evita que uma pergunta de acompanhamento seja interpretada como uma nova pesquisa sem relação com o assunto anterior.

Essa identificação é feita por padrões de texto, portanto não é infalível. O próprio modelo ainda pode solicitar uma pesquisa quando considerar necessário.

### Fontes das pesquisas

As URLs encontradas durante uma pesquisa são armazenadas durante o processamento da mensagem.

Caso a resposta final não apresente nenhuma dessas URLs, a Shaula acrescenta uma seção chamada `Fontes:` com os endereços encontrados.

---

## Anexos — Strategy

A Shaula também permite enviar arquivos junto com as mensagens.

O processamento fica concentrado em `GerenciadorAnexos`, que utiliza quatro estratégias diferentes, de acordo com o tipo de arquivo:

- `EstrategiaImagem`;
- `EstrategiaPDF`;
- `EstrategiaVideo`;
- `EstrategiaTexto`.

Todas seguem a interface `EstrategiaAnexo` e retornam um objeto `Anexo`, que contém o nome do arquivo, o conteúdo extraído, as imagens quando necessário e informações para exibição no chat.

### Tipos de arquivos aceitos

| Tipo | Extensões | Limite |
|---|---|---|
| Imagens | PNG, JPG, JPEG, WEBP, BMP e GIF | 25 MB |
| Documentos | PDF | 50 MB |
| Vídeos | MP4, MOV, AVI, MKV e WEBM | 300 MB |
| Textos e códigos | TXT, MD, LOG, CSV, JSON, YAML, XML, INI, CFG, PY, JS, TS, JAVA, C, CPP, H, CS, SQL, BAT, SH, HTML e CSS | 5 MB |

Além dos limites de tamanho, existem algumas restrições de processamento:

- **Imagens:** redimensionadas para no máximo 768 pixels no maior lado, respeitando a orientação EXIF.
- **PDFs:** o texto extraído é limitado a 12.000 caracteres. Quando o documento é escaneado, são renderizadas no máximo quatro páginas.
- **Vídeos:** são selecionados até quatro frames para análise. O áudio não é processado.
- **Textos e códigos:** o conteúdo é limitado a 12.000 caracteres e arquivos com BOM UTF-8 são tratados corretamente.

Esses limites foram definidos para evitar que os anexos ocupem espaço demais no contexto do modelo, especialmente em computadores com pouca VRAM.

### Como os PDFs são processados

A `EstrategiaPDF` utiliza a biblioteca `pymupdf` para tentar extrair o texto do documento.

Quando consegue encontrar texto suficiente, o conteúdo é enviado ao modelo como referência textual.

Se o PDF tiver pouco ou nenhum texto, ele é tratado como um documento provavelmente escaneado. Nesse caso, suas páginas são convertidas em imagens para análise.

### Como os vídeos são processados

A `EstrategiaVideo` utiliza `opencv-python-headless` para selecionar alguns frames distribuídos ao longo do vídeo.

O modelo recebe essas imagens estáticas, não o vídeo completo. Portanto, a Shaula consegue analisar elementos visuais, mas não realiza uma interpretação contínua do movimento nem do áudio.

### Como os anexos chegam ao modelo

O conteúdo textual dos anexos não é colocado diretamente dentro da mensagem escrita pelo usuário.

Em vez disso, a `TrabalhadorIA` cria uma mensagem de sistema separada, identificando o conteúdo como material de referência. Isso ajuda a evitar que instruções presentes dentro de um arquivo sejam confundidas com instruções do próprio sistema.

Os arquivos originais e seus conteúdos completos não são salvos no histórico. Apenas uma anotação indicando o envio permanece registrada.

Por exemplo:

```text
[1 arquivo(s) anexado(s): relatorio.pdf (3 página(s))]
```

O conteúdo completo é utilizado somente durante a solicitação atual.

### Exibição dos anexos no chat

Na interface, os arquivos aparecem em cartões próprios, posicionados acima da mensagem do usuário.

Cada cartão apresenta:

- Ícone correspondente ao tipo de arquivo.
- Nome do arquivo, com corte automático quando muito longo.
- Formato e informações adicionais, como a quantidade de páginas de um PDF.
- Miniatura da imagem quando um arquivo de imagem acabou de ser enviado.

Quando um PDF ultrapassa o limite de leitura, a interface informa que apenas parte do documento foi processada.

Ao reabrir uma conversa antiga, os cartões continuam aparecendo, mas as miniaturas das imagens são substituídas pelos ícones, pois os arquivos originais não são armazenados.

Os componentes responsáveis por essa funcionalidade são:

- `NotaAnexo`: cria e interpreta as anotações dos arquivos.
- `DescricaoAnexo`: organiza nome, formato e informações do arquivo.
- `IconeArquivo`: desenha o ícone correspondente.
- `CartaoAnexo`: monta o cartão exibido na interface.

---

## Comando por voz — Strategy

A Shaula também permite enviar mensagens por voz.

O reconhecimento utiliza o padrão Strategy para separar a gravação do áudio e sua conversão em texto.

Uma característica importante é que a voz utiliza o mesmo fluxo das mensagens digitadas. Depois que o áudio é transcrito, o texto é enviado normalmente para a Shaula, que pode utilizar qualquer uma de suas ferramentas disponíveis.

Assim, comandos como "abre o Discord", "cria um lembrete para daqui a 30 minutos" e "tira um print do monitor 2" também podem ser executados por voz.

### Como utilizar

1. Clique no botão de microfone ao lado do campo de mensagem ou pressione `Ctrl+M`.
2. A interface exibirá um painel de gravação com o indicador de volume.
3. Fale normalmente. A gravação continua até que você solicite seu encerramento.
4. Para finalizar e transcrever, clique novamente no botão ou pressione `Ctrl+M`.
5. Para cancelar a gravação, utilize o botão de cancelamento ou pressione `Esc`.

A gravação possui um limite de segurança de 10 minutos.

Por padrão, o texto reconhecido é enviado automaticamente. Entretanto, se já existir algum conteúdo digitado no campo de mensagem, a transcrição será adicionada ao texto e aguardará a revisão do usuário.

O microfone também fica desativado enquanto a Shaula está processando uma resposta.

### Componentes responsáveis pela voz

Os principais componentes estão em `tools/voz.py`:

| Classe ou função | Responsabilidade |
|---|---|
| `GerenciadorVoz` | Coordena a gravação, o reconhecimento e o carregamento do modelo. |
| `Gravador` | Captura o áudio até o usuário solicitar o encerramento. |
| `FonteAudio` | Define a interface utilizada para acessar a fonte de áudio. |
| `MicrofoneSounddevice` | Implementa a captura pelo microfone do computador. |
| `calcular_nivel()` | Calcula o volume do áudio capturado. |
| `normalizar_volume()` | Ajusta gravações com volume muito baixo. |
| `ReconhecedorFala` | Define a interface para reconhecimento de voz. |
| `ReconhecedorFasterWhisper` | Realiza a transcrição utilizando o Whisper local. |
| `LimpadorTranscricao` | Remove resultados incorretos e normaliza o texto reconhecido. |
| `VozIndisponivel` | Identifica problemas como bibliotecas ausentes ou microfone inacessível. |
| `TrabalhadorVoz` | Executa a gravação e transcrição em uma thread separada. |
| `MedidorNivelVoz` | Exibe visualmente o volume durante a gravação. |

O reconhecimento utiliza o `faster-whisper`, com o modelo `medium`, processamento em CPU, quantização `int8` e idioma português.

### Algumas decisões de implementação

- **Precisão:** o modelo `medium` foi escolhido por apresentar um reconhecimento melhor em português do que modelos menores. Também são utilizados busca em feixe de 5 e normalização de volume.
- **Funcionamento offline:** depois de baixar o modelo, a transcrição pode funcionar sem internet.
- **Carregamento sob demanda:** o modelo de voz não é carregado automaticamente por padrão. Ele é inicializado quando o microfone é utilizado.
- **Uso da CPU:** o Whisper trabalha na CPU para não disputar a memória da GPU com o modelo principal do Ollama.
- **Liberação de memória:** após 180 segundos sem utilização, o modelo de voz é descarregado da memória.
- **Dependências opcionais:** sem `faster-whisper` ou `sounddevice`, a interface continua funcionando normalmente, mas a gravação por voz fica indisponível.

O modelo `medium` ocupa aproximadamente 1,5 GB de memória RAM. Sua primeira utilização exige o download dos arquivos necessários.

Para alterar o comportamento do envio automático, basta modificar `ENVIAR_VOZ_AUTOMATICAMENTE` em `interface.py`.

Como os comandos reconhecidos podem executar ações reais, é possível desativar o envio automático para revisar a transcrição antes de executá-la.

---

## Blocos de código e botão Copiar

Quando a Shaula gera uma resposta que contém código, a interface identifica os trechos entre cercas de código e os apresenta em blocos separados.

Cada bloco possui um cabeçalho com a linguagem identificada e um botão **Copiar**, que envia o código completo para a área de transferência.

A exibição também conta com:

- Fonte monoespaçada (Consolas).
- Destaque de sintaxe para diferentes linguagens.
- Indentação preservada.
- Rolagem horizontal para linhas muito longas.
- Destaque de trechos escritos entre crases simples.
- Preservação do texto normal antes e depois dos blocos.

Entre as linguagens reconhecidas estão Python, JavaScript, TypeScript, C, C++, C#, Java, Kotlin, PHP, Go, Rust, SQL, shell e JSON.

Quando uma resposta contém um bloco de código que não foi fechado corretamente, a interface considera que ele continua até o final da mensagem.

Essa implementação também evita que operadores como `**`, utilizados em operações matemáticas do Python, sejam removidos durante a formatação.

Os componentes responsáveis estão em `tools/bloco_codigo.py`:

- `DivisorDeBlocos`;
- `FormatadorTextoMensagem`;
- `RealceSintaxe`;
- `CatalogoLinguagens`;
- `EditorCodigo`;
- `BlocoCodigo`;
- `ConteudoMensagemShaula`.

---

## Interromper a resposta da IA

Durante o processamento de uma mensagem, o botão de enviar é substituído por um botão vermelho de interrupção (■).

Também é possível interromper utilizando a tecla `Esc`.

Como o Ollama é chamado sem streaming, uma solicitação normalmente permanece aguardando até que o modelo termine de gerar toda a resposta.

Para permitir a interrupção, a Shaula utiliza a classe `ChatInterrompivel`, localizada em `tools/ollama_chat.py`.

Ela executa a chamada ao modelo em uma thread auxiliar e verifica periodicamente se o usuário solicitou o cancelamento.

Quando isso acontece:

1. A thread responsável pela resposta é liberada sem precisar esperar o modelo terminar.
2. A conexão HTTP com o Ollama é fechada, tentando interromper também a geração no servidor.
3. A interface informa que a resposta foi interrompida.
4. O botão volta ao estado normal.

Se existir uma confirmação de ação pendente, a interrupção também cancela a confirmação, considerando a ação como não autorizada.

**É importante lembrar que interromper uma resposta não desfaz ações que já foram executadas.** Se a Shaula já abriu um programa, por exemplo, ele continuará aberto.

O cancelamento impede que novas ferramentas sejam iniciadas e descarta os resultados que ainda não foram apresentados.

A mensagem do usuário permanece no histórico, mas a resposta interrompida não é salva.

---

## Conversas e histórico

A interface gráfica da versão 4.70 permite trabalhar com várias conversas independentes.

Esse gerenciamento é feito pela classe `GerenciadorConversas`, que mantém as informações de cada conversa e permite alternar entre elas sem perder o histórico.

Cada conversa possui:

- Identificador próprio.
- Título.
- Estado de fixação.
- Data de criação.
- Data da última atualização.
- Arquivo de histórico independente.

A conversa selecionada é representada pela classe `HistoricoConversa`.

### Recursos disponíveis

Na barra lateral, o usuário pode:

- Visualizar as conversas existentes.
- Alternar entre conversas.
- Criar uma nova conversa.
- Renomear conversas.
- Fixar ou desafixar conversas.
- Excluir conversas.
- Abrir uma conversa em uma nova janela.

O título também pode ser gerado automaticamente com base na primeira mensagem enviada.

Quando novas janelas são abertas pela própria interface, elas compartilham o mesmo `GerenciadorConversas`.

### Como o histórico é armazenado

O histórico possui um limite de 60 mensagens, definido por:

```python
HistoricoConversa.MAX_MENSAGENS_HISTORICO = 60
```

A mensagem de sistema não é armazenada em disco, pois é reconstruída pelo código atual sempre que necessário.

Somente mensagens do usuário e da assistente com conteúdo textual são persistidas. Mensagens internas de ferramentas não fazem parte do histórico permanente.

A gravação dos dados utiliza `ArmazenamentoJson`, que realiza a escrita em um arquivo temporário antes de substituir o arquivo definitivo.

Esse processo ajuda a evitar perda de dados caso ocorra um fechamento inesperado durante a gravação ou duas janelas tentem atualizar o mesmo arquivo simultaneamente.

### Limite de contexto e memória da conversa

Uma das melhorias importantes da versão 4.70 foi justamente a forma como o histórico chega ao modelo.

Embora até 60 mensagens possam permanecer salvas, isso não significa que todas serão enviadas integralmente ao Ollama em cada solicitação.

O espaço disponível depende do nível de esforço, do prompt de sistema, das ferramentas e do limite reservado para a resposta.

Para lidar com isso, a Shaula utiliza `OrcamentoContexto.ajustar()`.

Quando o contexto está próximo do limite, o sistema realiza três operações:

1. **Compactação:** respostas antigas e muito longas da Shaula são encurtadas. As mensagens do usuário permanecem intactas.
2. **Resumo:** se ainda faltar espaço, mensagens antigas são retiradas do contexto e substituídas por um resumo curto, criado por `ResumidorHistorico`.
3. **Redução de textos de apoio:** caso ainda seja necessário, conteúdos de pesquisas, anexos e resultados de ferramentas são reduzidos.

O resumo possui limite de 600 tokens e utiliza até 30% do espaço livre disponível, desde que haja espaço suficiente.

Na prática, isso permite que a Shaula mantenha melhor o contexto das conversas recentes, sem precisar enviar todo o histórico a cada mensagem.

Entretanto, informações muito antigas ou detalhes que estavam no meio de respostas extensas podem acabar sendo perdidos.

### Migração de históricos antigos

A versão atual também possui suporte à migração do histórico utilizado nas versões anteriores.

Se o arquivo abaixo existir e o novo índice de conversas ainda não tiver sido criado, o `GerenciadorConversas` tenta migrar os dados automaticamente:

```text
~/.shaula/historico_conversa.json
```

---

## Onde os dados ficam armazenados

A Shaula utiliza a pasta `.shaula`, localizada no diretório pessoal do usuário, para guardar suas informações.

### Conversas

Por padrão, os arquivos ficam em:

```text
%USERPROFILE%\.shaula\conversas\
│
├── indice.json
├── <id_conversa_1>.json
├── <id_conversa_2>.json
└── ...
```

O arquivo `indice.json` mantém as informações gerais das conversas, enquanto cada arquivo individual armazena o histórico correspondente.

### Cache

O `CacheComandos` utiliza o arquivo:

```text
~/.shaula/cache_comandos.json
```

Esse cache é utilizado principalmente para evitar pesquisas repetidas de arquivos.

Quando os resultados são reaproveitados, o sistema verifica se os arquivos ainda existem. Caso algum tenha sido removido, a busca é realizada novamente.

### Notificações

Os registros utilizados para diagnóstico das notificações ficam em:

```text
%USERPROFILE%\.shaula\notificacoes.log
```

O script temporário utilizado para exibir notificações é armazenado em:

```text
%TEMP%\shaula\toast.ps1
```

### Capturas de tela

As capturas realizadas pela ferramenta `tirar_print` são salvas em formato PNG, dentro de uma pasta chamada `Shaula`, localizada na pasta Imagens do Windows.

O caminho é obtido pela API `SHGetKnownFolderPath`. Se não for possível localizar a pasta, o sistema utiliza `~/Pictures/Shaula` como alternativa.

A conversão da captura para PNG ou JPEG é realizada pela classe `ImagemCapturada`, em `tools/imagem_tela.py`.

---

## Outros comportamentos importantes

### Internet desativada por padrão

Por segurança, a Shaula inicia com o acesso à internet desativado.

Essa configuração é controlada por `EstadoInternet`, que mantém o estado compartilhado entre a interface e as ferramentas.

O usuário pode ativar ou desativar o acesso quando desejar.

### Comando para sair

A Shaula reconhece comandos diretos para encerrar a aplicação, como:

- `sair`;
- `fechar`;
- `feche`;
- `encerre`;
- `encerrar`;
- `fechar shaula`;
- `feche a shaula`;
- `encerre a shaula`;
- `sair da shaula`;
- `pode sair`;
- `pode fechar`;
- `pode encerrar`.

O reconhecimento ignora diferenças entre letras maiúsculas, minúsculas, acentos e pontuação.

Também aceita o nome da assistente antes do comando, como "Shaula, sair".

Entretanto, se a mensagem contiver outras instruções, ela será encaminhada normalmente ao modelo.

O comando `sair` encerra todas as janelas abertas, interrompe os trabalhos em andamento e tenta finalizar o Ollama.

Já o fechamento normal de uma janela secundária não encerra o Ollama enquanto outras janelas ainda estiverem abertas.

### Limpar ou excluir a conversa

A Shaula também reconhece comandos para apagar o histórico da conversa atual, como:

- Excluir conversa.
- Apagar conversa.
- Limpar memória.
- Esquecer tudo.
- Excluir histórico.

Esses comandos exigem uma frase exata, sem palavras adicionais, para reduzir o risco de uma transcrição incorreta apagar informações por engano.

A exclusão afeta somente a conversa selecionada. As demais permanecem intactas.

Também não é permitido excluir pelo menu uma conversa enquanto a IA ainda está respondendo.

### Links clicáveis

A classe `FormatadorTexto`, por meio de `linkificar_html()`, identifica links escritos em Markdown ou como URLs simples e os transforma em links clicáveis na interface.

### Arrastar e soltar arquivos

A interface permite adicionar arquivos aos anexos utilizando o recurso de arrastar e soltar.

Tanto `CampoMensagem` quanto `ShaulaWindow` aceitam esse tipo de interação.

Os arquivos adicionados ficam em `anexos_pendentes` até que a próxima mensagem seja enviada.

---

## Proteções das ferramentas

Como a Shaula pode executar operações diretamente no computador, algumas ferramentas possuem verificações adicionais para evitar comandos perigosos ou execuções acidentais.

| Ferramenta | Proteção implementada |
|---|---|
| `calcular` | Limita operações matemáticas muito grandes, evita cálculos que poderiam travar a thread e trata erros de domínio, fatorial e resultados inválidos. |
| `abrir_programa` | Valida os nomes recebidos e exige confirmação quando o destino é um caminho, endereço ou script. |
| `testar_ping` | Valida o endereço informado e limita o tempo de execução a 20 segundos. |
| `finalizar_processo` | Impede o encerramento de processos protegidos do Windows e do próprio Ollama. |
| `desligar_computador` | Valida o tempo solicitado e exige confirmação antes de executar o desligamento. |
| `criar_lembrete` | Limita os lembretes a um período máximo de um ano e rejeita valores inválidos. |
| `analisar_tela` | Envia a captura somente ao modelo local e oculta temporariamente as janelas da Shaula quando necessário. |
| `tirar_print` e `bloquear_tela` | Limitam atrasos a 60 segundos e tratam falhas de captura. |
| Comandos externos | Utilizam limite de execução de 20 segundos. |
| Janelas e monitores | Permitem identificar janelas semelhantes utilizando números, como `chrome 2` ou `Discord 1`. |

A calculadora também possui verificações específicas para impedir que expressões excessivamente grandes ocupem a thread por tempo indeterminado.

No caso de `finalizar_processo`, a proteção considera o nome real do processo, evitando que pequenas alterações no nome sejam utilizadas para contornar a restrição.

---

## Confirmação de ações sensíveis

Algumas operações podem causar alterações importantes no computador e, por isso, exigem autorização antes de serem executadas.

A Shaula apresenta uma caixa de diálogo com as opções **Sim, autorizar** e **Não**.

As confirmações são utilizadas nas seguintes situações:

| Ferramenta | Quando solicita confirmação |
|---|---|
| `desligar_computador` | Sempre. |
| `finalizar_processo` | Sempre. |
| `fechar_programa` | Sempre. |
| `controlar_janela` | Quando a ação solicitada é fechar. |
| `abrir_arquivo` | Quando o arquivo é um programa, script ou documento com macros. |
| `abrir_programa` | Quando o destino é um caminho, endereço, script ou atalho. |

### Como funciona a confirmação

A verificação acontece dentro de `RegistroFerramentas.executar()`, que consulta a `PoliticaConfirmacao` antes de permitir a execução.

Dessa forma, as regras ficam centralizadas, sem precisar implementar uma confirmação separada dentro de cada ferramenta.

O sistema também verifica os parâmetros obrigatórios antes de apresentar a caixa de diálogo.

Por padrão, a resposta é sempre negativa caso:

- O usuário escolha não autorizar.
- A caixa seja fechada.
- A tecla `Esc` seja pressionada.
- O tempo limite de 120 segundos seja atingido.
- A resposta seja interrompida pelo botão ■.
- A janela seja fechada.
- Não exista um componente de confirmação configurado.

Na interface gráfica, a caixa é exibida pela classe `ConfirmadorQt`. Ela é apresentada à frente das outras janelas, restaurando a janela principal quando necessário e destacando seu ícone na barra de tarefas.

No terminal, a confirmação é feita pela classe `ConfirmadorTerminal`, que apresenta:

```text
Autorizar? [s/N]
```

A variável `SHAULA_CONFIRMAR=0` permite desativar todas as confirmações, mas isso não é recomendado.

### Atalho para pedidos diretos de desligamento

Uma melhoria importante da versão 4.70 foi a criação do `DetectorDesligar`, localizado em `tools/intencao_desligar.py`.

O objetivo é evitar situações em que o modelo recebe um pedido direto para desligar o computador, mas responde apenas em texto, sem chamar a ferramenta responsável pela operação.

Agora, pedidos claros são identificados antes da consulta ao modelo.

Alguns exemplos:

| Mensagem | Comportamento |
|---|---|
| "Desligue o computador." | Utiliza o padrão de 60 segundos. |
| "Desliga o PC agora." | Utiliza 0 segundos. |
| "Desligue o PC em 30 segundos." | Utiliza 30 segundos. |
| "Desligue o notebook daqui a 2 minutos." | Utiliza 120 segundos. |
| "Desligue o notebook em 1 hora." | Utiliza 3600 segundos. |

O detector também verifica se a mensagem não é uma pergunta, negação ou solicitação composta.

Por exemplo, frases como "desligue o PC depois de baixar o arquivo" não ativam o atalho.

O objetivo é garantir que apenas pedidos diretos sejam tratados dessa maneira.

**Esse atalho não elimina a confirmação.** Ele apenas garante que a ferramenta seja chamada e que o usuário tenha a oportunidade de autorizar ou cancelar a operação.

---

## Lembretes persistentes

Os lembretes criados pela Shaula são armazenados em:

```text
~/.shaula/lembretes.json
```

A persistência é feita por `ArmazenamentoJson`, e o arquivo é a principal referência para determinar quais lembretes ainda estão ativos.

Os temporizadores (`Timer`) são utilizados apenas para controlar o momento em que cada lembrete deve ser apresentado.

O funcionamento inclui:

- Lembretes pendentes continuam ativos depois de fechar e abrir a Shaula.
- Lembretes que venceram enquanto a aplicação estava fechada são apresentados como atrasados quando ela é aberta novamente.
- Se a Shaula estiver fechada no horário programado, a notificação não aparece naquele momento.
- As operações de listar e cancelar lembretes consultam o arquivo compartilhado entre as janelas.
- Antes de entregar uma notificação, o lembrete é removido do arquivo para evitar que duas janelas apresentem o mesmo aviso.
- Os identificadores dos lembretes continuam sendo utilizados entre sessões.
- Caso não seja possível salvar um lembrete em disco, ele ainda funciona durante a sessão atual, e a interface informa a situação.

Também existe uma verificação do horário antes da entrega, evitando que temporizadores antigos apresentem lembretes cancelados ou antecipem a execução de um novo lembrete com o mesmo identificador.

---

## Analisar a tela do computador

A ferramenta `analisar_tela` permite que o usuário faça perguntas sobre o que está aparecendo no monitor.

Alguns exemplos:

- "O que tem na minha tela?"
- "Leia esse erro."
- "Que programa é esse?"

Diferentemente de `tirar_print`, que salva uma captura no computador, essa ferramenta envia uma imagem ao modelo local para análise.

### Funcionamento

- Por padrão, utiliza o monitor principal, mas também permite informar outro monitor.
- A Shaula pode ocultar temporariamente suas próprias janelas para não atrapalhar a captura.
- A imagem é convertida para JPEG e limitada a 1024 pixels no maior lado.
- O conteúdo é enviado ao Ollama local.
- A imagem não é salva no histórico da conversa.

A ferramenta utiliza `CapturadorTela`, `GerenciadorJanelas` e `OcultadorJanelasProprias`.

Como o Ollama não aceita imagens diretamente em mensagens de ferramenta, a Shaula utiliza um fluxo próprio para enviar a imagem em uma mensagem de usuário logo após o resultado da ferramenta.

Depois da captura, as chamadas seguintes daquela solicitação são realizadas sem ferramentas, liberando espaço no contexto para a análise visual.

---

## Dependências de plataforma

A Shaula foi desenvolvida principalmente para o Windows e utiliza recursos específicos desse sistema operacional.

Entre os módulos que dependem dessas funcionalidades estão:

| Módulo | Recurso utilizado |
|---|---|
| `janelas.py` | API `user32` do Windows. |
| `captura_tela.py` | GDI, User32, Shell32 e Kernel32. |
| `clipboard.py` | Área de transferência do Windows. |
| `arquivos.py` | Unidades do Windows e `os.startfile`. |
| `programas.py` | Comando `start`. |
| `sistema.py` | PowerShell e `LockWorkStation`. |
| `rede.py` | `netsh` para gerenciamento de Wi-Fi. |
| `notificacoes.py` | PowerShell e WinRT Toast. |
| `lembretes.py` | `MessageBoxW` como alternativa de notificação. |
| `janelas_proprias.py` | Funções de gerenciamento de janelas do Windows. |
| `ollama_processo.py` | `tasklist` e `taskkill`. |
| `voz.py` | Microfone padrão do Windows por meio do sounddevice. |

O gerenciamento de processos também utiliza `psutil`, mas as regras de proteção são direcionadas especificamente ao Windows.

---

## Testes do projeto

A versão 4.70 possui uma suíte com **553 casos de teste**, distribuídos em 21 arquivos dentro da pasta `tests/`.

Os testes verificam desde operações matemáticas e gerenciamento de arquivos até recursos mais complexos, como reconhecimento de voz, interrupção de respostas, confirmações e persistência de conversas.

### Distribuição dos testes

| Arquivo | Casos | Principal funcionalidade testada |
|---|---:|---|
| `test_analisar_tela.py` | 44 | Captura e análise de tela. |
| `test_anexos.py` | 17 | Processamento de imagens, PDFs, vídeos e textos. |
| `test_voz.py` | 55 | Gravação, reconhecimento e tratamento de áudio. |
| `test_lembretes.py` | 19 | Persistência e gerenciamento de lembretes. |
| `test_menu_principal.py` | 29 | Menu principal, formulário de parâmetros, leitura de matrizes e cobertura das 40 ferramentas. |
| `test_ollama_chat.py` | 10 | Interrupção das chamadas ao Ollama. |
| `test_blocos_codigo.py` | 36 | Formatação e exibição de blocos de código. |
| `test_confirmacao.py` | 76 | Confirmações e autorização de ações sensíveis. |
| `test_desligar_atalho.py` | 19 | Reconhecimento de pedidos diretos de desligamento. |
| `test_memoria_contexto.py` | 12 | Compactação, resumo e controle do contexto. |
| `test_calculadora.py` | 25 | Operações matemáticas e conversões. |
| `test_comandos_locais.py` | 36 | Comandos locais e encerramento da aplicação. |
| `test_console.py` | 3 | Codificação e leitura de saída do console. |
| `test_desligar_computador.py` | 6 | Desligamento programado e tratamento de erros. |
| `test_pesquisa_factual.py` | 18 | Identificação de perguntas que precisam de pesquisa. |
| `test_registro_parametros.py` | 4 | Validação dos parâmetros das ferramentas. |
| `test_nota_anexo.py` | 19 | Organização das informações dos anexos. |
| `test_cartao_anexo.py` | 13 | Exibição dos cartões de arquivos na interface. |
| `test_correcoes.py` | 41 | Persistência, histórico, cache e correções gerais. |
| `test_correcoes_sistema.py` | 29 | Processos, janelas, lembretes e recursos do sistema. |
| `test_esforco.py` | 42 | Níveis de esforço e gerenciamento do contexto. |

A contagem considera os casos parametrizados expandidos e foi obtida por análise estática dos testes.

### O que os testes verificam

Além das funcionalidades principais, a suíte também verifica situações específicas, como:

- Arquivos corrompidos e anexos acima do limite permitido.
- PDFs com texto e documentos escaneados.
- Falhas de acesso ao microfone.
- Cancelamento de gravações de voz.
- Mensagens com erros que não devem ser salvas no histórico.
- Limites de execução de ferramentas.
- Confirmações negadas ou expiradas.
- Lembretes cancelados em outras janelas.
- Problemas de codificação de caracteres.
- Proteção de processos importantes do Windows.
- Interrupção de chamadas ao Ollama.

Os testes de voz utilizam fontes de áudio e mecanismos de reconhecimento simulados, evitando a necessidade de um microfone real durante sua execução.

### Como executar os testes

O instalador não inclui o pytest. Portanto, antes de executar a suíte, é necessário instalar essa dependência no ambiente virtual:

```bash
pip install pytest
```

Depois, execute:

```bash
python -m pytest tests
```

Em ambientes Linux, quando necessário, utilize:

```bash
QT_QPA_PLATFORM=offscreen python -m pytest tests
```

### Validação realizada na versão 4.70

Durante a revisão do pacote:

- Todos os arquivos Python passaram pela compilação.
- Foram conferidas as 40 ferramentas da interface gráfica e as 13 disponíveis no terminal.
- Foram executados 216 casos de teste em ambiente Linux, sem PySide6, utilizando um executor compatível com pytest. Todos passaram.
- Também foram realizadas 4.000 conversas aleatórias para verificar o funcionamento do `OrcamentoContexto`.
- Os nomes de classes, funções, arquivos e variáveis citados nesta documentação foram conferidos com o código-fonte.
- O menu principal foi aberto numa `ShaulaWindow` real, em modo invisível (`QT_QPA_PLATFORM=offscreen`) e com as chamadas do Windows simuladas. Foram percorridos todos os menus e conferido que as 40 ferramentas do registro são alcançadas. Uma ferramenta foi executada pelo menu e a troca de conversas, o nível de esforço e a chave de internet foram exercitados. Os 29 testes de `test_menu_principal.py` passaram, e o restante da suíte manteve o resultado anterior.

É importante destacar que a suíte completa da versão 4.70 e a interface gráfica não foram executadas durante essa revisão, devido à ausência de PySide6, Ollama e Windows no ambiente de validação.

Portanto, ainda é necessário executar os testes no ambiente Windows antes de considerar a versão totalmente validada.

---

## Limitações conhecidas

Apesar das melhorias, existem algumas limitações que devem ser consideradas ao utilizar a Shaula.

### Desempenho e memória

- O desempenho do `qwen3.5:9b` depende bastante da GPU disponível.
- Em placas com 8 GB de VRAM, os níveis Baixo e Médio são os mais indicados.
- Se parte do modelo precisar ser executada pela CPU, a velocidade de resposta pode diminuir consideravelmente.
- Os níveis mais altos utilizam mais memória e podem deixar o processamento muito lento.
- O raciocínio melhora a qualidade das respostas, mas aumenta o tempo necessário para gerá-las.

É possível verificar a distribuição do modelo entre CPU e GPU utilizando:

```bash
ollama ps
```

### Contexto e histórico

- O prompt de sistema e os schemas das ferramentas ocupam uma parte considerável do contexto.
- Mensagens com anexos são enviadas sem as ferramentas para liberar espaço.
- Históricos antigos podem ser resumidos ou removidos do contexto.
- O resumo é criado por regras simples, sem utilizar o próprio modelo, portanto alguns detalhes podem ser perdidos.

### Pesquisa na internet

- A identificação automática de perguntas utiliza heurísticas e pode realizar pesquisas desnecessárias ou deixar passar algumas perguntas.
- Perguntas que dependem do histórico podem não disparar uma pesquisa automática.
- O modelo ainda pode solicitar pesquisas por conta própria.

### Anexos

- Vídeos são analisados por até quatro imagens estáticas e não possuem processamento de áudio.
- Não existe uma estratégia para anexos de áudio.
- PDFs escaneados são limitados a quatro páginas renderizadas.
- Textos de PDFs e arquivos comuns são limitados a 12.000 caracteres.
- Em documentos longos, apenas o início do conteúdo é enviado ao modelo.

### Reconhecimento de voz

- A primeira utilização exige internet para baixar o modelo `medium`, com aproximadamente 1,5 GB.
- O reconhecimento é realizado pela CPU e pode levar alguns segundos depois que a gravação termina.
- Não existe palavra de ativação nem escuta contínua.
- A Shaula não possui síntese de voz para responder falando.
- O modelo é descarregado após três minutos de inatividade e precisa ser carregado novamente no próximo uso.
- O funcionamento com microfone real e o desempenho do reconhecimento ainda precisam ser validados no Windows.

### Interrupção das respostas

- A interrupção cancela a chamada ao modelo, mas não desfaz ferramentas que já foram executadas.
- Como não existe streaming, não é possível aproveitar uma resposta parcialmente gerada.
- O encerramento da geração no servidor Ollama depende do comportamento do próprio servidor após o fechamento da conexão.

### Menu principal

- Os itens do menu executam as ferramentas diretamente, sem o modelo. Já `pesquisar_internet` e `analisar_tela` dependem do modelo e seguem pelo chat.
- Uma ferramenta iniciada pelo menu não pode ser interrompida, assim como acontece com as chamadas feitas pelo modelo.
- Enquanto uma ferramenta do menu executa, não é possível enviar mensagens nem trocar de conversa.
- O funcionamento do menu com as APIs reais do Windows (captura de tela, janelas, notificações) ainda precisa ser validado em um ambiente Windows.

### Recursos do Windows

- A aplicação depende de APIs e comandos específicos do Windows.
- Recursos como captura de tela, gerenciamento de janelas, bloqueio da sessão, notificações e microfone precisam ser validados em um ambiente Windows real.
- A interrupção de ferramentas em execução ainda possui limitações.

### Confirmações e segurança

- As confirmações dependem de as operações passarem pelo `RegistroFerramentas`.
- O tempo limite para responder a uma confirmação é de 120 segundos.
- O atalho de desligamento reconhece apenas solicitações curtas e diretas.
- Outras operações sensíveis dependem de o modelo chamar corretamente a ferramenta correspondente.
- Desativar `SHAULA_CONFIRMAR` remove a proteção de confirmação.

---

## Inconsistências encontradas no pacote 4.70

Durante a revisão do código, algumas questões foram identificadas e merecem atenção em futuras atualizações.

Elas não impedem o funcionamento normal da Shaula, mas podem causar problemas durante o desenvolvimento e a execução dos testes.

1. **Localização do `conftest.py`:** o arquivo responsável por isolar a pasta pessoal durante os testes está em `tools/conftest.py`, e não em `tests/conftest.py`. Por isso, os testes da pasta `tests/` podem acessar os dados reais de `~/.shaula`. O ideal seria mover esse arquivo para a pasta correta.

2. **Arquivos antigos dentro de `tools/`:** existem cópias antigas de `interface.py` e alguns arquivos de testes que também aparecem na pasta `tests/`. Eles podem gerar confusão durante a manutenção e poderiam ser removidos.

3. **Dependência requests:** o instalador instala e verifica `requests`, mas nenhum módulo do projeto utiliza essa biblioteca. A pesquisa na internet utiliza `urllib`.

4. **Pytest não incluído no instalador:** embora o projeto possua uma suíte de testes, o instalador não instala o pytest automaticamente.

5. **Exclusão de conversas sem confirmação:** os comandos para apagar o histórico exigem frases exatas, mas ainda não apresentam uma caixa de confirmação. Adicionar essa proteção seria uma melhoria interessante.

6. **Ferramentas não interrompíveis:** o botão de interrupção cancela a chamada ao modelo, mas não consegue interromper imediatamente uma ferramenta que já esteja executando. Algumas operações podem levar bastante tempo e causar problemas ao fechar a janela.

7. **Caixas de confirmação:** as instâncias de `QMessageBox` permanecem como filhas da janela depois de utilizadas, podendo acumular objetos durante o uso prolongado.

---

## UML e casos de uso

A documentação da arquitetura e das funcionalidades da Shaula está disponível na pasta `Documentação/`.

Os arquivos correspondentes são:

```text
Documentação/
│
├── Shaula_UML_Completo_4.70.md
│
└── Shaula_Casos_de_Uso_4.70.md
```

O diagrama UML representa a estrutura interna da versão 4.70, incluindo as classes, seus relacionamentos, serviços, ferramentas e padrões de projeto utilizados.

Já a documentação dos casos de uso apresenta as funcionalidades disponíveis para o usuário e as interações realizadas com os sistemas externos.

Ambos foram atualizados para acompanhar a versão atual do projeto.
