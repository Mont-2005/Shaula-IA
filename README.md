# Shaula IA 4.75 — Assistente Pessoal Local

A **Shaula** é uma assistente virtual desenvolvida para funcionar localmente no Windows. Utilizando o **Ollama** e o modelo `qwen3.5:9b`, ela consegue conversar com o usuário, interpretar solicitações e executar diversas tarefas diretamente no computador.

O projeto oferece duas formas de utilização: uma interface gráfica desenvolvida com PySide6 (`interface.py`) e uma versão independente para uso pelo terminal (`main.py`).

Este documento apresenta a organização e os recursos da versão **Shaula IA 4.75**, com base no código-fonte atual do projeto.

## O que mudou na versão 4.75

A versão 4.75 dá continuidade às melhorias introduzidas na versão 4.70 e traz novos recursos para facilitar o uso da Shaula, além de aprimorar sua organização interna.

As principais novidades são:

- **Armazenamento em SQLite:** as conversas deixaram de ser salvas em vários arquivos JSON e passaram a utilizar um único banco de dados (`shaula.db`). Isso facilita o gerenciamento dos históricos e permite trabalhar com várias janelas sem perder alterações.
- **Colagem de imagens com Ctrl+V:** agora é possível copiar uma imagem, um print ou arquivos do Explorador de Arquivos e colá-los diretamente no campo de mensagem.
- **Visualizador de imagens:** imagens anexadas podem ser abertas em tamanho maior diretamente pelo chat, facilitando a visualização.
- **Melhor tratamento de transparência:** imagens PNG e capturas com áreas transparentes recebem um fundo branco antes de serem enviadas ao modelo, evitando que essas regiões apareçam pretas.
- **Movimentação de janelas aprimorada:** o sistema passou a lidar melhor com janelas minimizadas ou maximizadas. Também verifica se o movimento realmente aconteceu e tenta novamente quando necessário.
- **Verificação de ações executadas:** a Shaula agora identifica respostas em que o modelo afirma ter realizado uma operação sem realmente chamar a ferramenta correspondente. Quando isso acontece, uma nova tentativa é feita ou um aviso é apresentado.
- **Melhorias no reconhecimento de voz:** o instalador passou a escolher versões compatíveis do Python, verificar as bibliotecas instaladas e oferecer uma alternativa quando o `onnxruntime` não está disponível.
- **Inicialização sem console:** o novo `Shaula.vbs` permite abrir a aplicação sem exibir a janela do terminal. O arquivo `Shaula.bat` continua disponível para quem prefere acompanhar a inicialização e possíveis erros.
- **Visualizador do banco de dados:** foi adicionado o `Ver Banco.bat`, que abre uma janela somente leitura para consultar as conversas e mensagens armazenadas.
- **Testes ampliados:** a suíte passou de 572 para 667 casos, distribuídos em 25 arquivos. Os arquivos de teste duplicados que ficavam em `tools/` também foram removidos.
- **Identificação da versão:** a janela Sobre e o banner do terminal passaram a exibir corretamente a versão 4.75.

## O que mudou na versão 4.70

A versão 4.70 trouxe uma reorganização importante para o projeto. As funcionalidades passaram a ter responsabilidades mais bem definidas, facilitando a manutenção do código e a inclusão de novos recursos.

Entre as principais mudanças estavam:

- **Melhoria do histórico:** a Shaula passou a compactar e resumir mensagens antigas quando o contexto se aproxima do limite, preservando as informações mais relevantes da conversa.
- **Novos níveis de esforço:** os limites de contexto, resposta e execução de ferramentas foram ampliados, permitindo que o modelo trabalhe com mais informações.
- **Atalho para desligamento:** pedidos diretos, como "desligue o computador", passaram a ser identificados antes de chegar ao modelo, garantindo que a ferramenta correspondente seja chamada.
- **Desligamento programado:** o usuário pode definir quanto tempo deve passar até o desligamento, incluindo a opção de desligar imediatamente.
- **Confirmações aprimoradas:** as caixas de autorização passaram a aparecer à frente das outras janelas, e também podem ser canceladas pelo botão de interrupção.
- **Correções gerais:** foram realizados ajustes na abertura de arquivos e programas, execução de comandos, lembretes, pesquisas, cálculos e gerenciamento de processos.
- **Menu principal:** a interface ganhou uma barra de menus que reúne as funcionalidades da aplicação, como conversas, anexos, lembretes, processos, janelas, monitores, rede, internet, calculadora e voz.
- **Documentação atualizada:** a estrutura de arquivos, os comandos e as informações técnicas foram revisados para acompanhar o código do projeto.

## Como executar

A Shaula pode ser aberta de duas maneiras, dependendo de como o usuário prefere acompanhar a inicialização.

| Forma de abertura | Comportamento |
|---|---|
| Atalho **Shaula** da Área de Trabalho ou `Shaula.vbs` | Inicia a aplicação sem exibir a janela do console. |
| `Shaula.bat` | Inicia a aplicação com o console visível, permitindo acompanhar as mensagens e possíveis erros. |

O atalho criado pelo instalador utiliza o `Shaula.vbs`, um pequeno script do Windows que executa o `Shaula.bat` em segundo plano.

Quando a inicialização oculta apresenta algum erro, o script exibe uma mensagem com as últimas linhas do registro e informa onde o arquivo completo foi salvo.

No modo oculto, as mensagens que normalmente apareceriam no terminal são gravadas em:

```text
%USERPROFILE%\.shaula\logs\shaula.log
```

Esse arquivo é substituído a cada nova abertura da aplicação.

Se quiser acompanhar o registro enquanto a Shaula estiver aberta, utilize o seguinte comando no PowerShell:

```powershell
Get-Content "$env:USERPROFILE\.shaula\logs\shaula.log" -Wait
```

Independentemente da forma escolhida, o `Shaula.bat` prepara o ambiente antes de abrir a interface:

1. Define a pasta do projeto como diretório de trabalho.
2. Verifica se o Ollama está respondendo em `http://127.0.0.1:11434/api/tags`.
3. Caso necessário, procura o executável `ollama.exe` no PATH ou na pasta padrão de instalação.
4. Inicia o servidor Ollama em segundo plano.
5. Aguarda a inicialização, realizando até 20 tentativas.
6. Verifica se o ambiente virtual `.venv` está disponível.
7. Inicia a interface gráfica por meio de `interface.py`.

Se o Ollama não iniciar dentro do tempo esperado, o processo é encerrado e uma mensagem de erro é apresentada.

A interface também identifica problemas de comunicação com o Ollama. Entretanto, ainda não possui um mecanismo próprio de reconexão automática para repetir uma solicitação que falhou.

### Configurações por variáveis de ambiente

Algumas opções podem ser definidas por variáveis de ambiente:

| Variável | Função |
|---|---|
| `SHAULA_CONFIRMAR` | Controla as confirmações de ações sensíveis. O padrão é `1` (ativado). O valor `0` desativa as confirmações. |
| `SHAULA_ESFORCO` | Define o nível de esforço inicial, caso ainda não exista uma configuração salva. Aceita `baixo`, `medio`, `alto`, `extra` ou `max`. |

A escolha feita pelo botão **Esforço** da interface ou pelo comando correspondente no terminal fica salva em `~/.shaula/configuracoes.json`. Essa configuração tem prioridade sobre a variável de ambiente.

### Níveis de esforço

A Shaula possui cinco níveis de esforço, que podem ser selecionados pelo botão **🧠 Esforço**, localizado na barra superior, ao lado do controle de Internet.

Cada nível define a quantidade de contexto disponível, o limite de resposta e o número máximo de rodadas de ferramentas que o modelo pode executar.

| Nível | Raciocínio | Contexto (`num_ctx`) | Resposta (`num_predict`) | Rodadas |
|---|---|---:|---:|---:|
| Baixo | Não | 10240 | 1024 | 4 |
| **Médio (padrão)** | Sim | 11264 | 2048 | 8 |
| Alto | Sim | 13312 | 3072 | 8 |
| Extra | Sim | 15360 | 4096 | 10 |
| Máx | Sim | 18432 | 6144 | 12 |

Alguns detalhes importantes:

- Níveis mais altos permitem utilizar mais informações durante o processamento, mas também aumentam o tempo de resposta e o consumo de memória.
- O limite de resposta inclui os tokens utilizados pelo raciocínio do modelo.
- Em placas com 8 GB de VRAM, os níveis Extra e Máx podem ultrapassar a memória disponível, fazendo com que parte do processamento seja transferida para a CPU.
- Nos níveis Baixo e Médio, sobram aproximadamente 3.200 tokens para o histórico. No nível Máx, esse espaço chega a aproximadamente 6.300 tokens.
- Ao mudar o nível, o Ollama precisa carregar novamente o modelo na próxima mensagem.
- A configuração é compartilhada entre as janelas e permanece salva entre as sessões.
- Se o raciocínio consumir todo o limite disponível para resposta, a Shaula informa o problema e sugere aumentar o nível.

Os valores foram definidos considerando o modelo `qwen3.5:9b` em uma GPU de 8 GB. Eles podem ser ajustados em `CatalogoEsforco.PERFIS`, no arquivo `tools/esforco.py`.

No terminal, também é possível consultar ou alterar o nível:

```text
esforço
esforço alto
```

### Instalação das dependências

O pacote inclui o arquivo `Instalador Dependências Shaula.bat`, responsável por preparar o ambiente virtual e instalar as bibliotecas necessárias.

Entre os principais componentes utilizados estão:

- Python entre 3.11 e 3.14;
- NumPy;
- psutil;
- PySide6;
- Ollama;
- requests;
- PyMuPDF;
- OpenCV;
- faster-whisper e sounddevice (opcionais, utilizados para reconhecimento de voz).

Também é necessário ter o Ollama instalado no Windows e o modelo `qwen3.5:9b` disponível.

O reconhecimento de voz é opcional. Caso alguma das bibliotecas necessárias não esteja disponível, a Shaula continua funcionando normalmente, mas sem essa funcionalidade.

#### Como o instalador escolhe o Python

O instalador procura uma versão compatível do Python por meio do launcher `py`, seguindo esta ordem:

1. Python 3.13;
2. Python 3.12;
3. Python 3.14;
4. Python 3.11.

A escolha é feita dessa forma porque algumas bibliotecas utilizadas no reconhecimento de voz, principalmente o `onnxruntime`, podem demorar para oferecer suporte a versões muito recentes do Python.

Se nenhuma versão compatível estiver instalada, o instalador tenta baixar o Python 3.13 pelo `winget`, sem remover a versão que já existe no computador.

Caso o ambiente virtual `.venv` tenha sido criado com uma versão incompatível, ele é recriado utilizando uma versão adequada, e as dependências são instaladas novamente.

#### Instalação do reconhecimento de voz

A instalação da voz também possui algumas verificações para evitar problemas com bibliotecas que precisam ser compiladas.

Primeiro, o instalador tenta utilizar pacotes prontos do `faster-whisper` e do `sounddevice`. Se essa instalação falhar, ele utiliza um procedimento alternativo, instalando as dependências separadamente e tentando incluir o `onnxruntime`.

Depois da instalação, o próprio script verifica se as bibliotecas realmente podem ser importadas e só então baixa o modelo de reconhecimento.

Ao final, apresenta o resultado da instalação, indicando se o comando por voz está disponível ou se houve alguma limitação.

**Observações:**

- O pacote não utiliza `requirements.txt`, pois esse arquivo não está presente no projeto.
- A biblioteca `requests` é instalada, mas não é utilizada diretamente pelo código.
- O `pytest` precisa ser instalado separadamente para executar os testes.
- O atalho criado pelo instalador utiliza o `Shaula.vbs` e o ícone `Shaula.ico`.

---

## Estrutura de arquivos

O projeto está dividido em três partes principais: os arquivos de inicialização, a documentação e os módulos responsáveis pelas funcionalidades.

```text
Shaula IA 4.75/
│
├── interface.py
├── main.py
├── Shaula.bat
├── Shaula.vbs
├── Ver Banco.bat
├── Instalador Dependências Shaula.bat
├── Instruções Shaula.txt
├── README.md
├── Shaula.ico
│
├── Documentação/
│   ├── Shaula_Casos_de_Uso_4.75.dot
│   ├── Shaula_Casos_de_Uso_4.75.md
│   ├── Shaula_Casos_de_Uso_4.75.png
│   ├── Shaula_Casos_de_Uso_4.75.svg
│   └── Shaula_UML_Completo_4.75.md
│
├── tests/
│   ├── test_acao_sem_ferramenta.py
│   ├── test_analisar_tela.py
│   ├── test_anexos.py
│   ├── test_banco_conversas.py
│   ├── test_blocos_codigo.py
│   ├── test_calculadora.py
│   ├── test_cartao_anexo.py
│   ├── test_colar_imagem.py
│   ├── test_comandos_locais.py
│   ├── test_confirmacao.py
│   ├── test_console.py
│   ├── test_correcoes.py
│   ├── test_correcoes_sistema.py
│   ├── test_desligar_atalho.py
│   ├── test_desligar_computador.py
│   ├── test_esforco.py
│   ├── test_janelas_mover.py
│   ├── test_lembretes.py
│   ├── test_memoria_contexto.py
│   ├── test_menu_principal.py
│   ├── test_nota_anexo.py
│   ├── test_ollama_chat.py
│   ├── test_pesquisa_factual.py
│   ├── test_registro_parametros.py
│   ├── test_ver_banco_gui.py
│   └── test_voz.py
│
└── tools/
    ├── acao_sem_ferramenta.py
    ├── anexos.py
    ├── area_transferencia.py
    ├── armazenamento.py
    ├── arquivos.py
    ├── banco_dados.py
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
    ├── internet.py
    ├── janelas.py
    ├── janelas_proprias.py
    ├── lembretes.py
    ├── memoria.py
    ├── menu_principal.py
    ├── nota_anexo.py
    ├── notificacoes.py
    ├── ollama_chat.py
    ├── ollama_processo.py
    ├── pesquisa.py
    ├── processos.py
    ├── programas.py
    ├── rede.py
    ├── registro.py
    ├── repositorio_conversas.py
    ├── sistema.py
    ├── visualizador_imagem.py
    └── voz.py
```

## Organização e funcionamento interno

A Shaula utiliza uma arquitetura baseada em classes. A proposta é manter cada parte do sistema responsável por uma função específica, separando a interface, o processamento das mensagens, as ferramentas e o armazenamento de dados.

Essa organização facilita a manutenção do projeto e permite adicionar novas funcionalidades sem precisar concentrar toda a lógica em um único arquivo.

### Interface gráfica

A classe `ShaulaWindow`, localizada em `interface.py`, controla a janela principal e conecta os diferentes componentes da aplicação.

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

A janela também cuida da barra lateral de conversas, dos anexos, do acesso à internet, da exibição do histórico e da abertura de conversas em novas janelas.

A barra de menus é criada por `MenuPrincipal`, em `tools/menu_principal.py`, logo depois da montagem da interface.

Para evitar que o processamento de uma mensagem deixe a janela sem responder, cada solicitação utiliza uma instância própria de `TrabalhadorIA`, executada em uma thread separada.

O campo de mensagem também possui recursos próprios: o `InterpretadorAreaTransferencia` identifica se o usuário está colando texto, imagens ou arquivos, enquanto o `VisualizadorImagem` permite abrir imagens anexadas diretamente pelo chat.

### Como uma mensagem é processada

Quando o usuário envia uma mensagem, a Shaula segue uma sequência de etapas até produzir a resposta.

1. `ShaulaWindow.enviar()` verifica o texto digitado e os anexos pendentes.
2. Comandos locais, como sair ou limpar a conversa atual, são identificados antes de consultar o modelo.
3. A mensagem é adicionada ao histórico da conversa selecionada.
4. Se houver anexos, o `GerenciadorAnexos` identifica o tipo de arquivo e realiza o processamento necessário.
5. Uma nova instância de `TrabalhadorIA` é criada para cuidar da solicitação.
6. Antes de consultar o modelo, o `DetectorDesligar` verifica se existe um pedido direto para desligar o computador. Se encontrar, chama a ferramenta correspondente e apresenta a confirmação.
7. A thread prepara o contexto, considerando o estado da internet e, quando necessário, o conteúdo extraído dos anexos.
8. Se a internet estiver ativada e não houver anexos, o `DetectorPerguntaFactual` pode iniciar uma pesquisa automática.
9. O `OrcamentoContexto` verifica o tamanho das informações e ajusta o histórico de acordo com o nível de esforço escolhido.
10. O Ollama recebe a mensagem, as configurações de raciocínio e os schemas das ferramentas disponíveis. Quando existem anexos, as ferramentas são omitidas para liberar espaço no contexto.
11. Se o modelo solicitar uma ferramenta, o `RegistroFerramentas` identifica sua implementação e executa a operação. A quantidade de rodadas respeita o limite do nível de esforço.
12. Ferramentas que não precisam de síntese têm seus resultados apresentados diretamente.
13. Quando uma ferramenta precisa de interpretação, como a pesquisa na internet, o resultado retorna ao modelo para que ele prepare a resposta final.
14. O `DetectorAcaoSemFerramenta` verifica se o modelo afirmou ter realizado alguma ação sem chamar a ferramenta correspondente. Se identificar esse comportamento, solicita uma nova tentativa ou apresenta um aviso.
15. Por fim, `ShaulaWindow.receber_resposta()` exibe a resposta e salva o conteúdo no histórico.

As mensagens internas utilizadas pelas ferramentas existem apenas durante o processamento da solicitação e não são salvas no histórico permanente.

Se ocorrer algum problema, como uma falha de comunicação com o Ollama ou o limite de rodadas ser atingido, a interface apresenta um aviso. Esse aviso não é registrado como resposta da assistente.

---

## Menu principal

A interface possui uma barra de menus criada pela classe `MenuPrincipal`, localizada em `tools/menu_principal.py`.

Ela reúne as funcionalidades da Shaula em um só lugar, permitindo acessar as **40 ferramentas** do `RegistroFerramentas`, além das ações relacionadas a conversas, anexos, esforço e voz.

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

As ferramentas `ativar_internet` e `desativar_internet` são controladas pela opção **Internet ligada**, que utiliza o mesmo método `alternar_internet()` do botão localizado na barra superior.

### Organização do menu

O módulo foi desenvolvido utilizando classes, herança e polimorfismo. Essa estrutura evita concentrar todas as decisões em uma sequência extensa de condições `if/elif`.

Os principais componentes são:

**Catálogo do menu — padrão Composite**

| Classe | Responsabilidade |
|---|---|
| `ItemMenu` | Classe abstrata que serve de base para os elementos dos menus. |
| `Separador` | Representa uma linha separadora. |
| `ItemFerramenta` | Conecta um item do menu a uma ferramenta do registro. |
| `ItemPeloChat` | Especializa os itens que precisam enviar uma mensagem pelo chat. |
| `ItemPesquisaInternet` | Monta a solicitação utilizada para pesquisar na internet. |
| `ItemAnalisarTela` | Monta a solicitação utilizada para analisar a tela. |
| `Submenu` | Reúne outros itens e pode conter novos submenus. |
| `CatalogoMenu` | Define onde cada ferramenta aparece e verifica se as 40 estão contempladas. |

**Formulários de parâmetros — Factory e Template Method**

| Classe | Responsabilidade |
|---|---|
| `CampoParametro` | Classe abstrata que define o comportamento dos campos. |
| `CampoTexto` | Recebe valores textuais. |
| `CampoInteiro` | Trata valores inteiros. |
| `CampoNumero` | Trata números decimais. |
| `CampoMatriz` | Recebe matrizes. |
| `CampoOpcoes` | Apresenta opções de escolha. |
| `CampoBooleano` | Recebe valores de verdadeiro ou falso. |
| `FabricaDeCampos` | Escolhe o tipo de campo de acordo com o esquema JSON. |
| `DialogoParametros` | Monta o formulário, valida os campos e devolve os argumentos. |
| `LeitorMatriz` | Converte o texto informado em uma matriz retangular de números. |

**Execução e montagem da barra**

| Classe | Responsabilidade |
|---|---|
| `MenuPrincipal` | Monta a barra de menus e conecta os itens à janela. |
| `ExecutorMenu` | Verifica se a Shaula está livre, abre formulários e inicia a execução. |
| `TrabalhadorFerramenta` | Executa a ferramenta em uma thread separada. |
| `SubmenuDinamico` | Classe abstrata para submenus atualizados a cada abertura. |
| `SubmenuConversas` | Atualiza a lista de conversas disponíveis. |
| `SubmenuEsforco` | Atualiza as opções de nível de esforço. |
| `AcoesDaConversaAtual` | Controla as ações de renomear, fixar e apagar a conversa atual. |
| `DialogoFerramentas` | Apresenta a lista de ferramentas na seção Ajuda. |

### Como uma ferramenta é executada pelo menu

Quando o usuário seleciona uma opção, o `ExecutorMenu.acionar()` verifica primeiro se a Shaula está disponível.

Se a ferramenta precisar de parâmetros, o `DialogoParametros` cria um formulário utilizando o mesmo esquema JSON enviado ao Ollama. Os campos obrigatórios são verificados antes da execução, e os campos numéricos também aceitam vírgula como separador decimal.

No caso das matrizes, é possível informar os valores em linhas separadas, utilizando espaços ou vírgulas, ou diretamente em formato JSON:

```text
[[2, 1], [3, 4]]
```

Depois que os parâmetros são preenchidos, o `ExecutorMenu` chama `item.executar()`. É nesse momento que o polimorfismo define qual caminho será utilizado:

- `ItemFerramenta` executa a operação diretamente.
- `ItemPeloChat` envia uma mensagem pelo fluxo normal da conversa.

Nas execuções diretas, a solicitação aparece no chat com a identificação `[Menu] Nome do item`, seguida dos parâmetros utilizados.

O `TrabalhadorFerramenta` executa a operação por meio de `RegistroFerramentas.executar()`. Assim, as confirmações de ações sensíveis continuam funcionando normalmente.

O resultado é apresentado por `ShaulaWindow.receber_resposta()` e salvo no histórico.

A maioria dos itens não precisa consultar o modelo, tornando a execução mais rápida e independente do nível de esforço.

### Ferramentas que precisam do modelo

Existem duas exceções: `pesquisar_internet` e `analisar_tela`.

A pesquisa precisa do modelo para organizar e sintetizar os resultados encontrados. Já a análise de tela depende da interpretação da imagem capturada.

Por isso, `ItemPesquisaInternet` e `ItemAnalisarTela` montam uma mensagem e a enviam pelo mesmo fluxo utilizado pelo chat.

Essa mensagem não é enviada quando existem anexos pendentes, pois solicitações com anexos são processadas sem ferramentas.

### Cuidados durante a execução

Enquanto a Shaula está respondendo, executando uma ferramenta pelo menu ou gravando uma mensagem de voz, algumas operações precisam aguardar a conclusão da atividade atual.

Isso evita conflitos ao enviar novas mensagens, trocar ou apagar conversas e fechar a janela durante uma execução.

O atalho `Ctrl+M` continua sendo controlado pela própria janela, evitando conflitos entre os atalhos do menu.

---

## Registro de ferramentas

O `RegistroFerramentas` organiza as ferramentas disponíveis e encaminha cada solicitação para sua implementação.

Ele também cria os serviços necessários e compartilha os componentes utilizados por diferentes ferramentas, evitando que cada operação precise criar suas próprias dependências.

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

Alguns desses serviços dependem de outros para funcionar corretamente:

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
| `MoverProgramaMonitorFerramenta` | `mover_program