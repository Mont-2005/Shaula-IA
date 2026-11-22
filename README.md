# Shaula IA 4.70 — Assistente Pessoal Local

A **Shaula** é uma assistente virtual desenvolvida para funcionar localmente no Windows. Ela utiliza o **Ollama**, com o modelo `qwen3.5:9b`, para conversar, entender solicitações e executar diferentes tarefas no computador.

O projeto oferece duas formas de utilização: uma interface gráfica, desenvolvida com PySide6 (`interface.py`), e uma versão independente para uso pelo terminal (`main.py`).

Este README apresenta a organização e os recursos da versão **Shaula IA 4.70**, com informações baseadas na implementação atual do projeto.

## O que mudou na versão 4.70

A versão 4.70 trouxe melhorias na organização do código, no gerenciamento das conversas e na execução das ferramentas. O projeto passou a separar melhor as responsabilidades de cada componente, facilitando a manutenção e a evolução das funcionalidades.

Entre as principais mudanças estão:

- **Melhoria do histórico:** a Shaula passou a gerenciar melhor o contexto das conversas. Quando ele se aproxima do limite, mensagens antigas podem ser compactadas ou resumidas para preservar as informações mais relevantes.
- **Novos níveis de esforço:** foram ampliados os limites de contexto, resposta e execução de ferramentas, permitindo que o modelo trabalhe com mais informações.
- **Atalho para desligamento:** pedidos diretos para desligar o computador são identificados antes de chegar ao modelo, garantindo que a ferramenta correspondente seja chamada.
- **Desligamento programado:** agora é possível definir quanto tempo deve passar até o computador ser desligado, inclusive solicitando o desligamento imediato.
- **Confirmações aprimoradas:** as caixas de autorização passaram a aparecer à frente das outras janelas, e uma confirmação pendente também pode ser cancelada pelo botão de interrupção.
- **Correções gerais:** foram realizados ajustes na abertura de arquivos e programas, execução de comandos, lembretes, pesquisas, cálculos e gerenciamento de processos.
- **Novo menu principal:** a interface ganhou uma barra de menus que reúne os recursos do aplicativo, incluindo conversas, anexos, lembretes, processos, janelas, monitores, rede, internet, calculadora e voz.
- **Documentação revisada:** os arquivos, comandos e detalhes técnicos foram atualizados para acompanhar o código da versão 4.70.

## Como executar

A maneira mais simples de iniciar a Shaula é executar o arquivo `Shaula.bat`.

Antes de abrir a interface, esse arquivo prepara o ambiente:

1. Define a pasta do projeto como diretório de trabalho.
2. Verifica se o Ollama está respondendo em `http://127.0.0.1:11434/api/tags`.
3. Caso necessário, procura o `ollama.exe` no PATH ou na pasta padrão de instalação.
4. Inicia o servidor Ollama em segundo plano.
5. Aguarda a inicialização, realizando até 20 tentativas.
6. Verifica se o ambiente virtual `.venv` está disponível.
7. Inicia a interface gráfica por meio de `interface.py`.

Se o Ollama não iniciar dentro do tempo esperado, o processo é encerrado e uma mensagem de erro é apresentada.

A interface também identifica falhas de comunicação com o Ollama. Entretanto, ainda não possui um mecanismo próprio de reconexão automática para repetir uma solicitação que falhou.

### Configurações

Algumas opções podem ser definidas por variáveis de ambiente:

| Variável | Função |
|---|---|
| `SHAULA_CONFIRMAR` | Controla as confirmações de ações sensíveis. O padrão é `1` (ativado). O valor `0` desativa as confirmações. |
| `SHAULA_ESFORCO` | Define o nível de esforço inicial, caso ainda não exista uma configuração salva. Aceita `baixo`, `medio`, `alto`, `extra` ou `max`. |

O nível escolhido pela interface ou pelo comando do terminal é salvo em `~/.shaula/configuracoes.json`. Essa configuração tem prioridade sobre a variável de ambiente.

### Níveis de esforço

A Shaula possui cinco níveis de esforço, selecionados pelo botão **🧠 Esforço**, localizado na barra superior, ao lado do controle de Internet.

Cada nível determina quanto contexto o modelo pode utilizar, o limite de resposta e quantas rodadas de ferramentas podem ser executadas.

| Nível | Raciocínio | Contexto (`num_ctx`) | Resposta (`num_predict`) | Rodadas |
|---|---|---:|---:|---:|
| Baixo | Não | 10240 | 1024 | 4 |
| **Médio (padrão)** | Sim | 11264 | 2048 | 8 |
| Alto | Sim | 13312 | 3072 | 8 |
| Extra | Sim | 15360 | 4096 | 10 |
| Máx | Sim | 18432 | 6144 | 12 |

Alguns pontos importantes:

- Níveis mais altos permitem utilizar mais informações, mas também aumentam o tempo de processamento e o consumo de memória.
- O limite de resposta inclui os tokens utilizados pelo raciocínio do modelo.
- Em placas com 8 GB de VRAM, os níveis Extra e Máx podem ultrapassar a memória disponível, fazendo com que parte do processamento seja transferida para a CPU.
- Nos níveis Baixo e Médio, sobram aproximadamente 3.200 tokens para o histórico. No nível Máx, esse espaço chega a aproximadamente 6.300 tokens.
- Ao mudar o nível, o Ollama precisa carregar novamente o modelo na próxima mensagem.
- A configuração é compartilhada entre as janelas e permanece salva entre as sessões.
- Se o raciocínio consumir todo o limite disponível para resposta, a Shaula informa o problema e sugere aumentar o nível.

Os valores foram definidos considerando o modelo `qwen3.5:9b` em uma GPU de 8 GB. Eles podem ser modificados em `CatalogoEsforco.PERFIS`, no arquivo `tools/esforco.py`.

No terminal, também é possível consultar ou alterar o nível:

```text
esforço
esforço alto
```

### Instalação das dependências

O pacote inclui o arquivo `Instalador Dependências Shaula.bat`, que prepara o ambiente virtual e instala os componentes necessários.

Entre as principais dependências estão:

- Python 3.13;
- NumPy;
- psutil;
- PySide6;
- Ollama;
- requests;
- PyMuPDF;
- OpenCV;
- faster-whisper e sounddevice (opcionais, utilizados para reconhecimento de voz).

Também é necessário ter o Ollama instalado no Windows e o modelo `qwen3.5:9b` disponível.

O reconhecimento de voz é opcional. Se as bibliotecas necessárias não estiverem instaladas, a Shaula continua funcionando normalmente, mas sem esse recurso.

**Observações:** o pacote não possui um `requirements.txt`. Além disso, `requests` é instalado, mas não é utilizado diretamente pelo código, que utiliza `urllib` nas pesquisas. O `pytest` também precisa ser instalado separadamente para executar os testes.

---

## Estrutura de arquivos

A organização do projeto na versão 4.70 está dividida entre os arquivos principais, a documentação, os testes e os módulos responsáveis pelas ferramentas.

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

A Shaula utiliza uma arquitetura baseada em classes. A ideia é manter a interface, o processamento das mensagens, as ferramentas e o armazenamento separados, facilitando a manutenção do projeto.

### Interface gráfica

A classe `ShaulaWindow`, localizada em `interface.py`, controla a janela principal e conecta os diferentes componentes do sistema.

Entre os componentes gerenciados por ela estão:

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

A janela também controla a barra lateral de conversas, os anexos, o acesso à internet, a exibição do histórico e a abertura de conversas em novas janelas.

O menu principal é montado por `MenuPrincipal`, em `tools/menu_principal.py`, logo após a criação da interface.

Para evitar que o processamento de uma mensagem trave a janela, cada solicitação utiliza uma instância própria de `TrabalhadorIA`, executada em uma thread separada.

### Como uma mensagem é processada

Quando o usuário envia uma mensagem, ela passa por algumas etapas até chegar ao Ollama:

1. `ShaulaWindow.enviar()` verifica o conteúdo da mensagem e os anexos.
2. Comandos locais, como sair ou limpar a conversa atual, são identificados antes de consultar o modelo.
3. A mensagem é adicionada ao histórico da conversa selecionada.
4. Se houver anexos, o `GerenciadorAnexos` identifica o tipo de arquivo e realiza o processamento necessário.
5. Uma nova instância de `TrabalhadorIA` é criada para cuidar da solicitação.
6. Antes de consultar o modelo, o `DetectorDesligar` verifica se existe um pedido direto para desligar o computador. Se encontrar, chama a ferramenta correspondente e apresenta a confirmação.
7. A thread prepara o contexto, considerando o estado da internet e, quando necessário, o conteúdo extraído dos anexos.
8. Se a internet estiver ligada e não houver anexos, o `DetectorPerguntaFactual` pode realizar uma pesquisa automática.
9. O `OrcamentoContexto` verifica o tamanho das informações e ajusta o histórico de acordo com o nível de esforço.
10. O Ollama recebe a mensagem, as configurações de raciocínio e os schemas das ferramentas disponíveis. Quando existem anexos, as ferramentas são omitidas para liberar espaço no contexto.
11. Se o modelo solicitar uma ferramenta, o `RegistroFerramentas` identifica e executa a implementação correspondente. A quantidade de rodadas respeita o limite do nível de esforço.
12. Ferramentas que não precisam de síntese têm seus resultados apresentados diretamente.
13. Quando uma ferramenta precisa de interpretação, como a pesquisa na internet, o resultado volta ao modelo para a elaboração da resposta final.
14. Por fim, `ShaulaWindow.receber_resposta()` apresenta a resposta e salva o conteúdo no histórico.

As mensagens internas utilizadas pelas ferramentas existem apenas durante o processamento e não são salvas no histórico permanente.

Caso ocorra algum problema, como uma falha de comunicação com o Ollama ou o limite de rodadas ser atingido, a interface apresenta um aviso. Esse aviso não é registrado como resposta da assistente.

---

## Menu principal

A interface possui uma barra de menus criada pela classe `MenuPrincipal`, localizada em `tools/menu_principal.py`.

Ela reúne as funcionalidades da Shaula em um só lugar, dando acesso às **40 ferramentas** disponíveis no `RegistroFerramentas`, além das ações relacionadas a conversas, anexos, esforço e voz.

Cada janela aberta possui sua própria barra de menus.

### Menus disponíveis

| Menu | Funcionalidades |
|---|---|
| **Arquivo** | Criar conversa (`Ctrl+N`), abrir a conversa atual em outra janela, anexar arquivo (`Ctrl+O`) e sair (`Ctrl+Q`). |
| **Conversas** | Alternar entre conversas, renomear, fixar, desafixar, apagar e mostrar ou ocultar a barra lateral (`Ctrl+B`). |
| **Programas e arquivos** | Abrir e fechar programas, acessar o menu Iniciar, buscar e abrir arquivos. |
| **Calculadora** | Realizar cálculos, converter bases e executar operações com matrizes. |
| **Lembretes** | Criar, listar e cancelar lembretes. |
| **Janelas e telas** | Listar monitores e janelas, controlar janelas, mover programas entre monitores, tirar prints e analisar a tela. |
| **Sistema** | Consultar informações do hardware, listar e finalizar processos, bloquear a tela, desligar o computador, cancelar desligamentos e utilizar a área de transferência. |
| **Rede e internet** | Ativar ou desativar a internet, pesquisar, consultar o IP local, verificar o Wi-Fi e testar ping. |
| **Configurações** | Alterar o nível de esforço e utilizar o comando por voz (`Ctrl+M`). |
| **Ajuda** | Consultar a lista de ferramentas disponíveis e as informações sobre a Shaula. |

As operações de ativar e desativar a internet são controladas pela opção **Internet ligada**, que utiliza o mesmo método `alternar_internet()` do botão localizado na barra superior.

### Como os itens do menu funcionam

Quando o usuário seleciona uma ferramenta, a interface verifica se ela precisa de parâmetros.

Se precisar, o `DialogoParametros` cria um formulário automaticamente a partir do esquema JSON da ferramenta, utilizando os mesmos parâmetros enviados ao Ollama.

O formulário pode apresentar campos de texto, números inteiros e decimais, opções, respostas de sim ou não e matrizes. Os campos obrigatórios são verificados antes da execução.

As matrizes podem ser preenchidas com valores separados por espaço ou vírgula, utilizando uma linha para cada linha da matriz. Também é possível informar os valores em formato JSON, por exemplo:

```text
[[2, 1], [3, 4]]
```

Depois de preenchidos os parâmetros:

1. O pedido aparece no chat como uma mensagem do usuário, identificada por `[Menu] Nome do item`.
2. O `TrabalhadorFerramenta` executa a operação em uma thread separada.
3. O `RegistroFerramentas.executar()` encaminha a solicitação para a ferramenta correspondente.
4. As confirmações de ações sensíveis continuam funcionando normalmente.
5. O resultado é apresentado por `ShaulaWindow.receber_resposta()` e salvo no histórico.

Uma característica importante é que os itens do menu executam as ferramentas diretamente, sem passar pelo modelo. Por isso, suas respostas são imediatas e não dependem do nível de esforço.

Existem duas exceções: `pesquisar_internet` e `analisar_tela`. Como essas operações precisam da interpretação do modelo, elas enviam uma mensagem pelo mesmo fluxo utilizado pelo chat.

### Componentes do menu

| Classe ou função | Responsabilidade |
|---|---|
| `MenuPrincipal` | Monta a barra de menus e conecta seus itens à janela. |
| `CatalogoMenu` | Define a organização das ferramentas nos menus. |
| `ItemFerramenta` e `Submenu` | Representam os itens e submenus disponíveis. |
| `DialogoParametros` | Cria os formulários de parâmetros. |
| `TrabalhadorFerramenta` | Executa as ferramentas fora da thread da interface. |
| `ler_matriz()` | Converte os valores digitados em uma matriz numérica. |

Enquanto uma ferramenta está em execução, a interface impede o envio de novas mensagens e a troca ou exclusão de conversas até que a operação termine.

O atalho `Ctrl+M` continua sendo controlado pela própria janela, evitando conflitos entre os atalhos da interface e os itens do menu.

---

## Registro de ferramentas

O `RegistroFerramentas` é responsável por organizar as ferramentas disponíveis e encaminhar cada solicitação para sua implementação.

Ele também cria os serviços necessários e compartilha os componentes utilizados por diferentes ferramentas.

### Serviços utilizados

Entre os principais serviços gerenciados pelo registro estão:

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

Alguns serviços dependem de outros para funcionar corretamente:

- `BuscadorArquivos` e `GerenciadorJanelas` utilizam `CacheComandos`.
- `GerenciadorProgramas` recebe `GerenciadorProcessos`.
- `PesquisaInternet` utiliza `EstadoInternet`.
- `CapturadorTela` trabalha com `GerenciadorJanelas` e `OcultadorJanelasProprias`.
- `GerenciadorLembretes` utiliza `NotificadorToast` e `ArmazenamentoJson`.
- `RegistroFerramentas` também recebe as configurações e o componente responsáveis pelas confirmações de ações sensíveis.

### Ferramentas disponíveis

A interface gráfica possui **40 ferramentas concretas**, divididas em duas categorias.

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

O registro também valida os parâmetros obrigatórios. Se o modelo solicitar uma ferramenta sem informar algum dado necessário, a Shaula identifica qual informação está faltando e apresenta uma mensagem mais clara.

### Evitando chamadas desnecessárias ao modelo

Nem toda operação precisa que o modelo interprete o resultado de uma ferramenta.

Por isso, a classe `Ferramenta` possui a propriedade `precisa_de_sintese`, que utiliza `False` como padrão.

A maioria das ferramentas locais retorna o resultado diretamente ao usuário. A principal exceção é `pesquisar_internet`, pois os resultados encontrados precisam voltar ao modelo para serem organizados em uma resposta.

---

## Modo de terminal — `main.py`

Além da interface gráfica, a Shaula pode ser utilizada diretamente pelo terminal.

O arquivo `main.py` funciona de maneira independente: ele não inicia `interface.py` e também não faz parte do processo executado pelo `Shaula.bat`.

Essa versão utiliza o mesmo `RegistroFerramentas`, mas oferece um conjunto menor de operações.

A lógica principal está na classe `AssistenteTerminal`, responsável pelo histórico, registro de ferramentas e controle do contexto.

O processamento começa quando `AssistenteTerminal().executar()` é chamado por meio da função `main()`.

As 13 ferramentas disponíveis no terminal são:

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

Assim como na interface gráfica, o terminal utiliza os níveis de esforço, ajusta o contexto antes das chamadas ao Ollama e limita a quantidade de rodadas de ferramentas.

Para encerrar a execução, basta digitar `sair` ou utilizar `Ctrl+C` ou `Ctrl+D`.

---

## Pesquisa na internet — Strategy

A pesquisa na internet utiliza o padrão de projeto **Strategy**, permitindo trabalhar com diferentes mecanismos de busca sem precisar alterar a lógica principal do sistema.

O acesso à internet é controlado por `EstadoInternet`, que começa desativado.

A classe `PesquisaInternet` recebe esse estado e os mecanismos de busca disponíveis. Atualmente, utiliza:

1. `DuckDuckGo` como mecanismo principal.
2. `Bing` como alternativa quando a primeira busca não apresenta resultados suficientes.

Ambos implementam a abstração `MecanismoBusca`.

Também existem alguns componentes auxiliares:

- `DuckParser`: interpreta os resultados do DuckDuckGo.
- `BingParser`: interpreta os resultados do Bing.
- `FormatadorTexto`: organiza os links e extrai URLs.
- `DetectorPerguntaFactual`: identifica perguntas que podem precisar de uma pesquisa automática.

### Pesquisa automática

Quando a internet está ativada, a Shaula pode identificar perguntas que dependem de informações externas e realizar uma pesquisa antes de consultar o modelo.

O `DetectorPerguntaFactual` utiliza alguns critérios para reconhecer essas perguntas, como:

- Mensagens terminadas em `?` ou `？`.
- Perguntas iniciadas por expressões como "quem", "quando", "onde", "como", "qual", "quanto" e "é verdade".

Nem toda pergunta, porém, precisa de uma pesquisa na internet.

Para evitar buscas desnecessárias, o sistema considera algumas exceções, principalmente quando a mensagem envolve:

- A própria Shaula.
- Informações do usuário ou do computador.
- Processos, janelas, monitores e lembretes.
- Cálculos matemáticos e conversões.
- Matrizes e outras operações numéricas.

Nesses casos, a intenção é permitir que o modelo utilize as ferramentas locais disponíveis.

O detector também procura reconhecer perguntas que dependem de mensagens anteriores, como "e quando isso aconteceu?", "e o segundo?" ou "o que eu falei?". Assim, uma pergunta de acompanhamento não é tratada automaticamente como uma nova pesquisa sem relação com o assunto anterior.

Essa identificação utiliza padrões de texto e, portanto, não é infalível. O próprio modelo ainda pode solicitar uma pesquisa quando considerar necessário.

### Fontes das pesquisas

Durante uma pesquisa, as URLs encontradas são armazenadas para utilização naquela solicitação.

Se a resposta final não apresentar nenhuma dessas URLs, a Shaula acrescenta uma seção chamada `Fontes:`, contendo os endereços encontrados.

---

## Anexos — Strategy

A Shaula permite enviar arquivos junto com as mensagens, facilitando a análise de documentos, imagens, vídeos e códigos.

O processamento é centralizado em `GerenciadorAnexos`, que utiliza quatro estratégias, de acordo com o tipo de arquivo:

- `EstrategiaImagem`;
- `EstrategiaPDF`;
- `EstrategiaVideo`;
- `EstrategiaTexto`.

Todas seguem a interface `EstrategiaAnexo` e retornam um objeto `Anexo`, que reúne o nome do arquivo, o conteúdo extraído, as imagens necessárias e as informações utilizadas na exibição do chat.

### Tipos de arquivos aceitos

| Tipo | Extensões | Limite |
|---|---|---|
| Imagens | PNG, JPG, JPEG, WEBP, BMP e GIF | 25 MB |
| Documentos | PDF | 50 MB |
| Vídeos | MP4, MOV, AVI, MKV e WEBM | 300 MB |
| Textos e códigos | TXT, MD, LOG, CSV, JSON, YAML, XML, INI, CFG, PY, JS, TS, JAVA, C, CPP, H, CS, SQL, BAT, SH, HTML e CSS | 5 MB |

Além do tamanho dos arquivos, existem limites para o processamento:

- **Imagens:** são redimensionadas para até 768 pixels no maior lado, respeitando a orientação EXIF.
- **PDFs:** o texto extraído é limitado a 12.000 caracteres. Quando o documento é escaneado, são renderizadas no máximo quatro páginas.
- **Vídeos:** são selecionados até quatro frames para análise. O áudio não é processado.
- **Textos e códigos:** o conteúdo é limitado a 12.000 caracteres, e arquivos com BOM UTF-8 são tratados corretamente.

Esses limites ajudam a evitar que os anexos ocupem espaço demais no contexto do modelo, especialmente em computadores com pouca memória de vídeo.

### Processamento de PDFs

A `EstrategiaPDF` utiliza a biblioteca `pymupdf` para extrair o texto dos documentos.

Quando encontra texto suficiente, o conteúdo é enviado ao modelo como material de referência.

Se o PDF tiver pouco ou nenhum texto, ele é tratado como um documento provavelmente escaneado. Nesse caso, suas páginas são convertidas em imagens para análise.

### Processamento de vídeos

A `EstrategiaVideo` utiliza `opencv-python-headless` para selecionar até quatro frames distribuídos ao longo do vídeo.

O modelo recebe essas imagens estáticas, e não o vídeo completo. Por isso, a Shaula consegue analisar o conteúdo visual, mas não interpreta continuamente os movimentos nem processa o áudio.

### Como os anexos chegam ao modelo

O conteúdo dos anexos não é inserido diretamente na mensagem escrita pelo usuário.

Em vez disso, a `TrabalhadorIA` cria uma mensagem de sistema separada, identificando o material como referência. Isso ajuda a evitar que instruções presentes dentro de um arquivo sejam confundidas com instruções do próprio sistema.

Os arquivos originais e seus conteúdos completos não são armazenados no histórico. Apenas uma anotação indicando o envio permanece registrada.

Por exemplo:

```text
[1 arquivo(s) anexado(s): relatorio.pdf (3 página(s))]
```

O conteúdo completo é utilizado somente durante a solicitação atual.

### Exibição dos anexos

Na interface, os arquivos aparecem em cartões posicionados acima da mensagem do usuário.

Cada cartão apresenta:

- Ícone correspondente ao tipo de arquivo.
- Nome do arquivo, com corte automático quando muito longo.
- Formato e informações adicionais, como a quantidade de páginas de um PDF.
- Miniatura da imagem quando um arquivo de imagem acabou de ser enviado.

Quando um PDF ultrapassa o limite de leitura, a interface informa que somente parte do documento foi processada.

Ao abrir uma conversa antiga, os cartões continuam aparecendo, mas as miniaturas são substituídas pelos ícones. Isso acontece porque os arquivos originais não são armazenados.

Os principais componentes responsáveis por essa funcionalidade são:

- `NotaAnexo`: cria e interpreta as anotações dos arquivos.
- `DescricaoAnexo`: organiza o nome, formato e informações do arquivo.
- `IconeArquivo`: desenha o ícone correspondente.
- `CartaoAnexo`: monta o cartão exibido na interface.

---

## Comando por voz — Strategy

A Shaula também permite enviar mensagens por voz.

O reconhecimento utiliza o padrão Strategy para separar a captura do áudio de sua conversão em texto.

Depois que a gravação é transcrita, o texto segue o mesmo fluxo das mensagens digitadas. Isso significa que a Shaula pode utilizar suas ferramentas normalmente, mesmo quando o comando é enviado por voz.

Por exemplo, é possível solicitar ações como:

- "Abre o Discord."
- "Cria um lembrete para daqui a 30 minutos."
- "Tira um print do monitor 2."

### Como utilizar

1. Clique no botão de microfone ao lado do campo de mensagem ou pressione `Ctrl+M`.
2. A interface apresenta um painel de gravação com um indicador de volume.
3. Fale normalmente. A gravação continua até que você solicite seu encerramento.
4. Para finalizar e transcrever, clique novamente no botão ou pressione `Ctrl+M`.
5. Para cancelar a gravação, utilize o botão de cancelamento ou pressione `Esc`.

A gravação possui um limite de segurança de 10 minutos.

Por padrão, o texto reconhecido é enviado automaticamente. Entretanto, se já houver conteúdo digitado no campo de mensagem, a transcrição é adicionada ao texto e aguarda a revisão do usuário.

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

### Decisões de implementação

- **Precisão:** o modelo `medium` foi escolhido por apresentar um reconhecimento melhor em português do que modelos menores. Também são utilizados busca em feixe de 5 e normalização de volume.
- **Funcionamento offline:** depois de baixar o modelo, a transcrição pode funcionar sem internet.
- **Carregamento sob demanda:** o modelo de voz não é carregado automaticamente. Ele é inicializado quando o microfone é utilizado.
- **Uso da CPU:** o Whisper trabalha na CPU para não disputar a memória da GPU com o modelo principal do Ollama.
- **Liberação de memória:** após 180 segundos sem utilização, o modelo de voz é descarregado da memória.
- **Dependências opcionais:** sem `faster-whisper` ou `sounddevice`, a interface continua funcionando, mas a gravação por voz fica indisponível.

O modelo `medium` ocupa aproximadamente 1,5 GB de memória RAM. Na primeira utilização, é necessário baixar os arquivos correspondentes.

O envio automático da transcrição pode ser alterado pela configuração `ENVIAR_VOZ_AUTOMATICAMENTE`, localizada em `interface.py`.

Como os comandos reconhecidos podem executar ações reais no computador, também é possível desativar o envio automático e revisar a transcrição antes de executá-la.

---

## Blocos de código e botão Copiar

Quando a Shaula gera uma resposta com código, a interface identifica os trechos delimitados por cercas de código e os apresenta em blocos separados.

Cada bloco possui um cabeçalho com a linguagem identificada e um botão **Copiar**, que envia o código completo para a área de transferência.

A exibição também oferece:

- Fonte monoespaçada (Consolas).
- Destaque de sintaxe para diferentes linguagens.
- Indentação preservada.
- Rolagem horizontal para linhas muito longas.
- Destaque de trechos escritos entre crases simples.
- Preservação do texto normal antes e depois dos blocos.

Entre as linguagens reconhecidas estão Python, JavaScript, TypeScript, C, C++, C#, Java, Kotlin, PHP, Go, Rust, SQL, shell e JSON.

Se uma resposta contiver um bloco de código que não foi fechado corretamente, a interface considera que ele continua até o final da mensagem.

A implementação também evita que operadores como `**`, utilizados em operações matemáticas do Python, sejam removidos durante a formatação.

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

Enquanto a Shaula está processando uma mensagem, o botão de enviar é substituído por um botão vermelho de interrupção (■).

Também é possível interromper a resposta pressionando `Esc`.

Como o Ollama é chamado sem streaming, a interface normalmente aguarda até que o modelo termine de gerar toda a resposta. Para permitir o cancelamento durante esse processo, a Shaula utiliza a classe `ChatInterrompivel`, localizada em `tools/ollama_chat.py`.

Ela executa a chamada ao modelo em uma thread auxiliar e verifica periodicamente se o usuário solicitou a interrupção.

Quando isso acontece:

1. A thread responsável pela resposta é liberada sem precisar aguardar o modelo terminar.
2. A conexão HTTP com o Ollama é fechada, tentando interromper também a geração no servidor.
3. A interface informa que a resposta foi interrompida.
4. O botão volta ao estado normal.

Se houver uma confirmação de ação pendente, a interrupção também cancela a confirmação, considerando a ação como não autorizada.

**É importante lembrar que interromper uma resposta não desfaz ações que já foram executadas.** Se a Shaula já abriu um programa, por exemplo, ele continuará aberto.

O cancelamento impede que novas ferramentas sejam iniciadas e descarta os resultados que ainda não foram apresentados.

A mensagem do usuário permanece no histórico, mas a resposta interrompida não é salva.

---

## Conversas e histórico

A interface gráfica permite trabalhar com várias conversas independentes.

Esse gerenciamento é realizado pela classe `GerenciadorConversas`, responsável por manter as informações de cada conversa e permitir a troca entre elas sem perder o histórico.

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

### Armazenamento do histórico

O histórico possui um limite de 60 mensagens, definido por:

```python
HistoricoConversa.MAX_MENSAGENS_HISTORICO = 60
```

A mensagem de sistema não é armazenada em disco, pois é reconstruída pelo código atual sempre que necessário.

Somente mensagens textuais do usuário e da assistente são persistidas. As mensagens internas utilizadas pelas ferramentas não fazem parte do histórico permanente.

A gravação dos dados utiliza `ArmazenamentoJson`, que primeiro escreve as informações em um arquivo temporário e depois substitui o arquivo definitivo.

Esse processo ajuda a evitar a perda de dados em caso de fechamento inesperado durante a gravação ou quando duas janelas tentam atualizar o mesmo arquivo simultaneamente.

### Gerenciamento do contexto

Uma das melhorias importantes da versão 4.70 foi a forma como o histórico é preparado antes de ser enviado ao modelo.

Embora até 60 mensagens possam permanecer salvas, isso não significa que todas serão enviadas integralmente ao Ollama em cada solicitação.

O espaço disponível depende do nível de esforço, do prompt de sistema, das ferramentas e do limite reservado para a resposta.

Para controlar esse espaço, a Shaula utiliza `OrcamentoContexto.ajustar()`.

Quando o contexto se aproxima do limite, o sistema pode realizar três operações:

1. **Compactação:** respostas antigas e muito longas da Shaula são encurtadas. As mensagens do usuário permanecem intactas.
2. **Resumo:** se ainda faltar espaço, mensagens antigas são retiradas do contexto e substituídas por um resumo criado por `ResumidorHistorico`.
3. **Redução de textos de apoio:** se necessário, conteúdos de pesquisas, anexos e resultados de ferramentas também são reduzidos.

O resumo possui limite de 600 tokens e utiliza até 30% do espaço livre disponível, desde que haja espaço suficiente.

Na prática, esse processo ajuda a manter as informações mais recentes da conversa sem precisar enviar todo o histórico a cada mensagem.

Entretanto, detalhes muito antigos ou informações que estavam no meio de respostas extensas podem acabar sendo perdidos.

### Migração de históricos antigos

A versão 4.70 também permite migrar históricos utilizados em versões anteriores.

Se o arquivo abaixo existir e o novo índice de conversas ainda não tiver sido criado, o `GerenciadorConversas` tenta realizar a migração automaticamente:

```text
~/.shaula/historico_conversa.json
```

---

## Onde os dados ficam armazenados

A Shaula utiliza a pasta `.shaula`, localizada no diretório pessoal do usuário, para armazenar suas informações.

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

O arquivo `indice.json` reúne as informações gerais das conversas, enquanto cada arquivo individual armazena o histórico correspondente.

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

As capturas realizadas pela ferramenta `tirar_print` são salvas em PNG dentro de uma pasta chamada `Shaula`, localizada na pasta Imagens do Windows.

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

Se a mensagem contiver outras instruções, ela será encaminhada normalmente ao modelo.

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

Também não é permitido excluir uma conversa pelo menu enquanto a IA ainda está respondendo.

### Links clicáveis

A classe `FormatadorTexto`, por meio de `linkificar_html()`, identifica links escritos em Markdown ou como URLs simples e os transforma em links clicáveis na interface.

### Arrastar e soltar arquivos

A interface permite adicionar arquivos aos anexos utilizando o recurso de arrastar e soltar.

Tanto `CampoMensagem` quanto `ShaulaWindow` aceitam essa interação.

Os arquivos adicionados ficam em `anexos_pendentes` até que a próxima mensagem seja enviada.

---

## Proteções das ferramentas

Como a Shaula pode executar operações diretamente no computador, algumas ferramentas possuem verificações adicionais para evitar comandos perigosos ou execuções acidentais.

| Ferramenta | Proteção implementada |
|---|---|
| `calcular` | Limita operações matemáticas muito grandes e trata erros de domínio, fatorial e resultados inválidos. |
| `abrir_programa` | Valida os nomes recebidos e exige confirmação quando o destino é um caminho, endereço ou script. |
| `testar_ping` | Valida o endereço informado e limita o tempo de execução a 20 segundos. |
| `finalizar_processo` | Impede o encerramento de processos protegidos do Windows e do próprio Ollama. |
| `desligar_computador` | Valida o tempo solicitado e exige confirmação antes de executar o desligamento. |
| `criar_lembrete` | Limita os lembretes a um período máximo de um ano e rejeita valores inválidos. |
| `analisar_tela` | Envia a captura somente ao modelo local e oculta temporariamente as janelas da Shaula quando necessário. |
| `tirar_print` e `bloquear_tela` | Limitam atrasos a 60 segundos e tratam falhas de captura. |
| Comandos externos | Utilizam limite de execução de 20 segundos. |
| Janelas e monitores | Permitem identificar janelas semelhantes utilizando números, como `chrome 2` ou `Discord 1`. |

A calculadora também possui verificações para impedir que expressões excessivamente grandes ocupem a thread por tempo indeterminado.

No caso de `finalizar_processo`, a proteção considera o nome real do processo, evitando que pequenas alterações no nome sejam utilizadas para contornar a restrição.

---

## Confirmação de ações sensíveis

Algumas operações podem provocar alterações importantes no computador. Por isso, a Shaula solicita autorização antes de executá-las.

A interface apresenta uma caixa de diálogo com as opções **Sim, autorizar** e **Não**.

As confirmações são utilizadas nas seguintes situações:

| Ferramenta | Quando solicita confirmação |
|---|---|
| `desligar_computador` | Sempre. |
| `finalizar_processo` | Sempre. |
| `fechar_programa` | Sempre. |
| `controlar_janela` | Quando a ação solicitada é fechar. |
| `abrir_arquivo` | Quando o arquivo é um programa, script ou documento com macros. |
| `abrir_programa` | Quando o destino é um caminho, endereço, script ou atalho. |

### Como funciona

A verificação acontece dentro de `RegistroFerramentas.executar()`, que consulta a `PoliticaConfirmacao` antes de permitir a execução.

Assim, as regras ficam centralizadas, sem a necessidade de implementar uma confirmação separada em cada ferramenta.

O sistema também verifica os parâmetros obrigatórios antes de apresentar a caixa de diálogo.

A autorização é considerada negativa nas seguintes situações:

- O usuário escolhe não autorizar.
- A caixa de diálogo é fechada.
- A tecla `Esc` é pressionada.
- O limite de 120 segundos é atingido.
- A resposta é interrompida pelo botão ■.
- A janela é fechada.
- Não existe um componente de confirmação configurado.

Na interface gráfica, a caixa é exibida pela classe `ConfirmadorQt`. Ela aparece à frente das outras janelas, restaurando a janela principal quando necessário e destacando seu ícone na barra de tarefas.

No terminal, a confirmação é realizada pela classe `ConfirmadorTerminal`, que apresenta:

```text
Autorizar? [s/N]
```

A variável `SHAULA_CONFIRMAR=0` permite desativar todas as confirmações, mas essa opção não é recomendada.

### Atalho para pedidos diretos de desligamento

A versão 4.70 introduziu o `DetectorDesligar`, localizado em `tools/intencao_desligar.py`.

Ele foi criado para evitar que um pedido direto para desligar o computador seja tratado apenas como uma mensagem comum pelo modelo, sem que a ferramenta correspondente seja chamada.

Agora, pedidos claros são identificados antes da consulta ao Ollama.

Alguns exemplos:

| Mensagem | Comportamento |
|---|---|
| "Desligue o computador." | Utiliza o padrão de 60 segundos. |
| "Desliga o PC agora." | Utiliza 0 segundos. |
| "Desligue o PC em 30 segundos." | Utiliza 30 segundos. |
| "Desligue o notebook daqui a 2 minutos." | Utiliza 120 segundos. |
| "Desligue o notebook em 1 hora." | Utiliza 3600 segundos. |

O detector também verifica se a mensagem não é uma pergunta, negação ou solicitação composta.

Por exemplo, uma frase como "desligue o PC depois de baixar o arquivo" não ativa o atalho.

**O atalho não elimina a confirmação.** Ele apenas garante que a ferramenta seja chamada, permitindo que o usuário autorize ou cancele a operação.

---

## Lembretes persistentes

Os lembretes criados pela Shaula são armazenados em:

```text
~/.shaula/lembretes.json
```

A persistência é feita por `ArmazenamentoJson`. O arquivo é a principal referência para determinar quais lembretes continuam ativos.

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

A ferramenta `analisar_tela` permite fazer perguntas sobre o que está aparecendo no monitor.

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

Como o Ollama não aceita imagens diretamente em mensagens de ferramenta, a Shaula utiliza um fluxo próprio: depois do resultado da ferramenta, a imagem é enviada em uma mensagem de usuário.

Após a captura, as chamadas seguintes daquela solicitação são realizadas sem ferramentas, liberando espaço no contexto para a análise visual.

---

## Dependências de plataforma

A Shaula foi desenvolvida principalmente para o Windows e utiliza recursos específicos desse sistema operacional.

Alguns módulos dependem diretamente dessas funcionalidades:

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

Os testes cobrem desde operações matemáticas e gerenciamento de arquivos até funcionalidades mais complexas, como reconhecimento de voz, interrupção de respostas, confirmações e persistência das conversas.

### Distribuição dos testes

| Arquivo | Casos | Principal funcionalidade testada |
|---|---:|---|
| `test_analisar_tela.py` | 44 | Captura e análise de tela. |
| `test_anexos.py` | 17 | Processamento de imagens, PDFs, vídeos e textos. |
| `test_voz.py` | 55 | Gravação, reconhecimento e tratamento de áudio. |
| `test_lembretes.py` | 19 | Persistência e gerenciamento de lembretes. |
| `test_menu_principal.py` | 29 | Menu principal, formulários, matrizes e cobertura das ferramentas. |
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

Além do funcionamento normal, a suíte verifica situações que podem causar problemas durante o uso, como:

- Arquivos corrompidos e anexos acima do limite permitido.
- PDFs com texto e documentos escaneados.
- Falhas de acesso ao microfone.
- Cancelamento de gravações de voz.
- Mensagens com erros que não devem ser salvas no histórico.
- Limites de execução das ferramentas.
- Confirmações negadas ou expiradas.
- Lembretes cancelados em outras janelas.
- Problemas de codificação de caracteres.
- Proteção de processos importantes do Windows.
- Interrupção de chamadas ao Ollama.

Os testes de voz utilizam fontes de áudio e mecanismos de reconhecimento simulados. Dessa forma, não é necessário utilizar um microfone real para executar essa parte da suíte.

### Como executar os testes

O instalador não inclui o `pytest`. Portanto, primeiro é necessário instalar essa dependência no ambiente virtual:

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

Durante a revisão do pacote, foram realizadas as seguintes verificações:

- Todos os arquivos Python passaram pela compilação.
- Foram conferidas as 40 ferramentas da interface gráfica e as 13 disponíveis no terminal.
- Foram executados 216 casos de teste em ambiente Linux, sem PySide6, utilizando um executor compatível com pytest. Todos passaram.
- Também foram realizadas 4.000 conversas aleatórias para verificar o funcionamento do `OrcamentoContexto`.
- Os nomes de classes, funções, arquivos e variáveis citados na documentação foram conferidos com o código-fonte.
- O menu principal foi aberto em uma `ShaulaWindow` real, em modo invisível (`QT_QPA_PLATFORM=offscreen`) e com as chamadas do Windows simuladas.
- Todos os menus foram percorridos e foi verificado que as 40 ferramentas do registro podem ser acessadas.
- Uma ferramenta foi executada pelo menu, e também foram exercitadas a troca de conversas, a alteração do nível de esforço e a chave de internet.
- Os 29 testes de `test_menu_principal.py` passaram, mantendo-se também o resultado anterior do restante da suíte.

É importante destacar que a suíte completa da versão 4.70 e a interface gráfica não foram executadas durante essa revisão, devido à ausência de PySide6, Ollama e Windows no ambiente de validação.

Portanto, ainda é necessário executar os testes no ambiente Windows antes de considerar a versão totalmente validada.

---

## Limitações conhecidas

Apesar das melhorias, a Shaula ainda possui algumas limitações que devem ser consideradas durante o uso.

### Desempenho e memória

- O desempenho do `qwen3.5:9b` depende bastante da GPU disponível.
- Em placas com 8 GB de VRAM, os níveis Baixo e Médio são os mais indicados.
- Se parte do modelo precisar ser executada pela CPU, a velocidade de resposta pode diminuir consideravelmente.
- Os níveis mais altos utilizam mais memória e podem deixar o processamento lento.
- O raciocínio melhora a qualidade das respostas, mas aumenta o tempo necessário para gerá-las.

Para verificar como o modelo está distribuído entre CPU e GPU, utilize:

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
- Perguntas que dependem do histórico podem não iniciar uma pesquisa automática.
- O próprio modelo ainda pode solicitar pesquisas quando considerar necessário.

### Anexos

- Vídeos são analisados por até quatro imagens estáticas e não possuem processamento de áudio.
- Não existe uma estratégia para anexos de áudio.
- PDFs escaneados são limitados a quatro páginas renderizadas.
- Textos de PDFs e arquivos comuns são limitados a 12.000 caracteres.
- Em documentos longos, apenas o início do conteúdo é enviado ao modelo.

### Reconhecimento de voz

- A primeira utilização exige internet para baixar o modelo `medium`, com aproximadamente 1,5 GB.
- O reconhecimento é realizado pela CPU e pode levar alguns segundos após o término da gravação.
- Não existe palavra de ativação nem escuta contínua.
- A Shaula não possui síntese de voz para responder falando.
- O modelo é descarregado após três minutos de inatividade e precisa ser carregado novamente no próximo uso.
- O funcionamento com microfone real e o desempenho do reconhecimento ainda precisam ser validados no Windows.

### Interrupção das respostas

- A interrupção cancela a chamada ao modelo, mas não desfaz ferramentas que já foram executadas.
- Como não existe streaming, não é possível aproveitar uma resposta parcialmente gerada.
- O encerramento da geração no servidor Ollama depende do comportamento do próprio servidor após o fechamento da conexão.

### Menu principal

- Os itens do menu executam as ferramentas diretamente, sem passar pelo modelo. Já `pesquisar_internet` e `analisar_tela` dependem do modelo e seguem pelo chat.
- Uma ferramenta iniciada pelo menu não pode ser interrompida imediatamente.
- Enquanto uma ferramenta do menu está em execução, não é possível enviar mensagens nem trocar de conversa.
- O funcionamento do menu com as APIs reais do Windows, como captura de tela, gerenciamento de janelas e notificações, ainda precisa ser validado em um ambiente Windows.

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

Durante a revisão do código, alguns pontos foram identificados e merecem atenção em futuras atualizações.

Eles não impedem necessariamente o funcionamento normal da Shaula, mas podem causar problemas durante a manutenção e a execução dos testes.

1. **Localização do `conftest.py`:** o arquivo responsável por isolar a pasta pessoal durante os testes está em `tools/conftest.py`, e não em `tests/conftest.py`. Por isso, os testes da pasta `tests/` podem acessar os dados reais de `~/.shaula`. O ideal seria mover esse arquivo para a pasta correta.

2. **Arquivos antigos dentro de `tools/`:** existem cópias antigas de `interface.py` e alguns arquivos de testes que também aparecem na pasta `tests/`. Esses arquivos podem causar confusão durante a manutenção e poderiam ser removidos.

3. **Dependência `requests`:** o instalador instala e verifica essa biblioteca, mas nenhum módulo do projeto a utiliza diretamente. A pesquisa na internet utiliza `urllib`.

4. **Pytest não incluído no instalador:** embora o projeto possua uma suíte de testes, o instalador não instala o `pytest` automaticamente.

5. **Exclusão de conversas sem confirmação:** os comandos para apagar o histórico exigem frases exatas, mas ainda não apresentam uma caixa de confirmação. Adicionar essa proteção seria uma melhoria interessante.

6. **Ferramentas não interrompíveis:** o botão de interrupção cancela a chamada ao modelo, mas não consegue interromper imediatamente uma ferramenta que já esteja em execução. Algumas operações podem levar bastante tempo e causar problemas ao fechar a janela.

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

O diagrama UML apresenta a estrutura interna da versão 4.70, incluindo classes, relacionamentos, serviços, ferramentas e padrões de projeto utilizados.

Já a documentação dos casos de uso descreve as funcionalidades disponíveis para o usuário e as interações realizadas com os sistemas externos.

Os dois documentos foram atualizados para acompanhar a organização e os recursos da versão atual do projeto.
