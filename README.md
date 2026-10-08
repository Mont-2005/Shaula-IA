# Shaula IA 3.50 — assistente pessoal local

Shaula é uma IA local feita para rodar no Windows, usando **Ollama** com o modelo `qwen3.5:9b` para conversa, raciocínio e tool-calling. A aplicação principal possui interface gráfica em PySide6 (`interface.py`) e existe também um modo de linha de comando independente (`main.py`).

O README foi feito com o código atual, utilizando a estrutura e o código-fonte presentes no pacote **Shaula IA 3.50**. O objetivo é documentar o que a versão atual contém.

> **Arquitetura da 3.50:** o núcleo foi organizado em classes. O despacho de ferramentas é feito por `RegistroFerramentas`, a lógica de cada domínio vive em classes de serviço, a pesquisa e os anexos usam Strategy, e a interface gerencia múltiplas conversas persistentes por meio de `GerenciadorConversas` + `HistoricoConversa`.

---

## Como rodar

A forma normal de iniciar é dar dois cliques em `Shaula.bat`.

O launcher:

1. Muda o diretório de trabalho para a pasta da própria Shaula;
2. Verifica se o Ollama responde em `http://127.0.0.1:11434/api/tags`;
3. Se necessário, procura `ollama.exe` no PATH ou em `%LOCALAPPDATA%\Programs\Ollama`;
4. Inicia `ollama serve` em segundo plano;
5. Espera até 20 tentativas, com intervalo de aproximadamente 1 segundo, até o servidor responder;
6. Verifica se `.venv\Scripts\python.exe` existe;
7. Executa `.venv\Scripts\python.exe interface.py`.

Se o Ollama não responder dentro do limite, o launcher encerra com erro. `interface.py` captura erros de comunicação com o Ollama, mas **não implementa um mecanismo próprio de várias tentativas de reconexão** para a mesma chamada.

### Instalação de dependências

O pacote contém `Instalador Dependências Shaula.bat`. Esse instalador prepara o ambiente virtual e instala/verifica, entre outros componentes:

- Python 3.13;
- `numpy`;
- `psutil`;
- `PySide6`;
- `ollama`;
- `requests`;
- `pymupdf`;
- `opencv-python-headless`;
- Ollama para Windows;
- modelo `qwen3.5:9b`.

---

## Estrutura de arquivos observada no pacote

```text
Shaula IA 3.50 Documentação/
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

## Visão geral da arquitetura

### Interface gráfica

`ShaulaWindow` é a janela principal e instancia/possui:

- `CacheComandos`;
- `RegistroFerramentas`;
- `GerenciadorOllama`;
- `GerenciadorConversas`;
- o `HistoricoConversa` da conversa selecionada;
- `GerenciadorAnexos`;
- uma `TrabalhadorIA` por mensagem em processamento.

A janela também gerencia a barra lateral de conversas, criação/seleção/renomeação/fixação/exclusão de conversas, anexos pendentes, internet, renderização do histórico e abertura de uma conversa em nova janela.

### Fluxo de uma mensagem

1. `ShaulaWindow.enviar()` valida texto e anexos.
2. Comandos locais especiais, como sair ou limpar a conversa atual, são interceptados antes do modelo.
3. A mensagem do usuário é adicionada ao `HistoricoConversa` atual.
4. Anexos são processados por `GerenciadorAnexos`; no histórico fica somente uma nota textual sobre os arquivos.
5. A janela cria uma nova `TrabalhadorIA` (`QThread`) com mensagens, registro e anexos desta troca.
6. `TrabalhadorIA.run()` adiciona ao contexto um lembrete de estado da internet e, quando necessário, conteúdo textual extraído de anexos.
7. Com internet ligada, `DetectorPerguntaFactual` pode disparar uma pesquisa automática antes da primeira chamada ao modelo.
8. O Ollama é chamado com `registro.schemas_openai()`.
9. Se o modelo solicitar ferramentas, `RegistroFerramentas.executar()` encontra a instância pelo nome e delega a execução.
10. Se nenhuma ferramenta chamada exigir síntese, o resultado é devolvido diretamente, evitando uma nova inferência.
11. Se uma ferramenta exigir síntese — atualmente `PesquisarInternetFerramenta` — o resultado volta ao modelo para geração da resposta final.
12. `ShaulaWindow.receber_resposta()` exibe e persiste a resposta do assistente na conversa atual.

---

## `RegistroFerramentas`

`RegistroFerramentas` é o composition root do subsistema de ferramentas. Ele cria ou recebe o estado/cache compartilhados, instancia os serviços e injeta esses serviços nas ferramentas concretas.

### Serviços criados pelo registro

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

Alguns serviços dependem de outros:

- `BuscadorArquivos` recebe `CacheComandos`;
- `GerenciadorJanelas` recebe `CacheComandos`;
- `GerenciadorProgramas` recebe `GerenciadorProcessos`;
- `PesquisaInternet` recebe `EstadoInternet`;
- `CapturadorTela` recebe `GerenciadorJanelas`;
- `GerenciadorLembretes` recebe `NotificadorToast`.

### Quantidade real de ferramentas

A versão gráfica registra **39 ferramentas concretas**, e não 24.

#### Cálculo — 10

1. `CalcularFerramenta` → `calcular`
2. `MatrizSomaFerramenta` → `matriz_soma`
3. `MatrizSubtracaoFerramenta` → `matriz_subtracao`
4. `MatrizMultiplicacaoFerramenta` → `matriz_multiplicacao`
5. `MatrizEscalarFerramenta` → `matriz_escalar`
6. `MatrizTranspostaFerramenta` → `matriz_transposta`
7. `MatrizDeterminanteFerramenta` → `matriz_determinante`
8. `MatrizInversaFerramenta` → `matriz_inversa`
9. `MatrizPotenciaFerramenta` → `matriz_potencia`
10. `ConverterBaseFerramenta` → `converter_base`

#### Sistema, arquivos e interação — 29

1. `AbrirProgramaFerramenta` → `abrir_programa`
2. `FecharProgramaFerramenta` → `fechar_programa`
3. `BuscarArquivoFerramenta` → `buscar_arquivo`
4. `AbrirArquivoFerramenta` → `abrir_arquivo`
5. `DesligarComputadorFerramenta` → `desligar_computador`
6. `CancelarDesligamentoFerramenta` → `cancelar_desligamento`
7. `BloquearTelaFerramenta` → `bloquear_tela`
8. `TestarPingFerramenta` → `testar_ping`
9. `InformacoesHardwareFerramenta` → `informacoes_hardware`
10. `AbrirMenuIniciarFerramenta` → `abrir_menu_iniciar`
11. `AtivarInternetFerramenta` → `ativar_internet`
12. `DesativarInternetFerramenta` → `desativar_internet`
13. `PesquisarInternetFerramenta` → `pesquisar_internet`
14. `ListarMonitoresFerramenta` → `listar_monitores`
15. `ListarJanelasAbertasFerramenta` → `listar_janelas_abertas`
16. `MoverProgramaMonitorFerramenta` → `mover_programa_monitor`
17. `MoverParaOutroMonitorFerramenta` → `mover_para_outro_monitor`
18. `TirarPrintFerramenta` → `tirar_print`
19. `ControlarJanelaFerramenta` → `controlar_janela`
20. `CriarLembreteFerramenta` → `criar_lembrete`
21. `ListarLembretesFerramenta` → `listar_lembretes`
22. `CancelarLembreteFerramenta` → `cancelar_lembrete`
23. `ListarProcessosFerramenta` → `listar_processos`
24. `ListarProcessosProtegidosFerramenta` → `listar_processos_protegidos`
25. `FinalizarProcessoFerramenta` → `finalizar_processo`
26. `CopiarTextoFerramenta` → `copiar_texto`
27. `ColarTextoFerramenta` → `colar_texto`
28. `ObterIpLocalFerramenta` → `obter_ip_local`
29. `VerificarWifiFerramenta` → `verificar_wifi`

### Atalho de velocidade

`Ferramenta.precisa_de_sintese` retorna `False` por padrão. Assim, a maioria das ações locais retorna seu resultado diretamente ao usuário sem uma segunda chamada ao Qwen.

`PesquisarInternetFerramenta` sobrescreve essa propriedade para `True`, porque o texto bruto da busca precisa ser interpretado/sintetizado.

---

## `main.py` — modo de linha de comando

`main.py` **não chama `interface.py`** e não faz parte do fluxo iniciado por `Shaula.bat`. É um entrypoint independente que usa o mesmo `RegistroFerramentas`.

Ele restringe o registro a 13 ferramentas:

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

> **Inconsistência de código:** embora pertença ao pacote 3.50 e use `qwen3.5:9b`, o banner de `main.py` ainda imprime `Shaula v1.80`.

---

## Pesquisa na internet — Padrão Strategy

A autorização para acessar a internet fica em `EstadoInternet`, que começa desligado.

`PesquisaInternet` recebe esse objeto e uma lista de mecanismos. Por padrão:

1. `DuckDuckGo`;
2. `Bing` como fallback.

Ambos implementam a abstração `MecanismoBusca`.

Parsers auxiliares:

- `DuckParser` para o HTML do DuckDuckGo;
- `BingParser` para o HTML do Bing.

`FormatadorTexto` fornece utilidades de linkificação e extração de URLs. `DetectorPerguntaFactual` implementa a heurística que decide quando antecipar uma pesquisa automática.

### Busca automática

Quando a internet está ligada, `DetectorPerguntaFactual.parece_factual()` considera factual uma mensagem que, entre outros casos:

- termina com `?`/`？`; ou
- começa com palavras/expressões interrogativas previstas no código (`quem`, `quando`, `onde`, `como`, `qual`, `quanto`, `é verdade`, etc.).

Se a heurística disparar, `TrabalhadorIA` executa `PesquisaInternet.buscar()` antes de chamar o modelo e coloca o resultado no contexto como `RESULTADO DE PESQUISA AUTOMÁTICA`.

### Garantia de fontes

Todas as URLs encontradas durante pesquisas da troca são acumuladas. Se a resposta final do modelo não contiver **nenhuma** dessas URLs, `TrabalhadorIA` acrescenta uma seção `Fontes:` com as URLs encontradas.

---

## Anexos — Strategy

`GerenciadorAnexos` é a fachada usada pela interface e possui quatro estratégias:

- `EstrategiaImagem`;
- `EstrategiaPDF`;
- `EstrategiaVideo`;
- `EstrategiaTexto`.

Todas seguem a interface comportamental de `EstrategiaAnexo`.

Cada estratégia devolve um `Anexo`, que contém:

- `nome_arquivo`;
- `imagens` — lista de JPEGs em bytes; ou
- `texto` — conteúdo textual extraído;
- `nota_exibicao`;
- propriedade `eh_imagem`.

### Tipos e limites implementados

| Estratégia | Extensões | Limite principal |
|---|---|---|
| Imagem | `.png`, `.jpg`, `.jpeg`, `.webp`, `.bmp`, `.gif` | 25 MB; lado máximo 1568 px após redimensionamento |
| PDF | `.pdf` | 50 MB; texto truncado em 12.000 caracteres; PDF escaneado renderiza no máximo 8 páginas |
| Vídeo | `.mp4`, `.mov`, `.avi`, `.mkv`, `.webm` | 300 MB; até 6 frames amostrados; sem áudio |
| Texto/código | `.txt`, `.md`, `.markdown`, `.log`, `.csv`, `.json`, `.yaml`, `.yml`, `.xml`, `.ini`, `.cfg`, `.py`, `.js`, `.ts`, `.java`, `.c`, `.cpp`, `.h`, `.cs`, `.sql`, `.bat`, `.sh`, `.html`, `.css` | 5 MB; conteúdo truncado em 12.000 caracteres |

### PDFs

`EstrategiaPDF` tenta extrair texto com `pymupdf`. Se houver texto suficiente, o PDF vira referência textual. Se a média de texto for muito baixa, o documento é tratado como provavelmente escaneado e as páginas são renderizadas como imagens.

### Vídeos

`EstrategiaVideo` usa `opencv-python-headless`, escolhe frames espaçados ao longo do arquivo e envia apenas imagens estáticas ao modelo. Não existe leitura de áudio nem de movimento contínuo.

### Texto isolado como referência

Conteúdo textual de anexos não é colado dentro da mensagem do usuário. `TrabalhadorIA` cria uma mensagem de sistema separada, rotulada como dado de referência, para reduzir o risco de o modelo confundir conteúdo do arquivo com instruções.

### Anexos e histórico

Os bytes e o texto integral dos anexos não são persistidos. No histórico fica apenas uma nota como:

```text
[1 arquivo(s) anexado(s): relatorio.pdf (3 página(s))]
```

O conteúdo completo do anexo só participa da chamada atual ao Ollama.

---

## Conversas e histórico

A versão gráfica atual suporta **múltiplas conversas**.

`GerenciadorConversas` mantém:

- um índice compartilhado de conversas;
- título;
- estado fixado/desafixado;
- timestamps de criação/atualização;
- um arquivo de histórico independente para cada conversa.

A conversa atual é representada por `HistoricoConversa`.

### Recursos da barra lateral

O código implementa:

- listar conversas;
- selecionar conversa;
- criar nova conversa;
- renomear;
- fixar/desafixar;
- apagar conversa;
- abrir conversa em nova janela;
- título automático baseado na primeira mensagem.

Múltiplas janelas compartilham uma instância de `GerenciadorConversas` quando abertas a partir da interface principal.

### Limite do histórico

`HistoricoConversa.MAX_MENSAGENS_HISTORICO = 60`.

A mensagem de sistema não é salva em disco; ela é sempre fornecida pelo código atual.

Mensagens persistidas são filtradas para dicionários simples com `role` e `content` textuais.

### Migração do histórico antigo

Se ainda existir o arquivo legado:

```text
~/.shaula/historico_conversa.json
```

E o novo índice ainda não existir, `GerenciadorConversas` tenta migrá-lo para a estrutura de múltiplas conversas.

---

## Onde os dados ficam guardados

### Conversas

Por padrão:

```text
%USERPROFILE%\.shaula\conversas\
├── indice.json
├── <id_conversa_1>.json
├── <id_conversa_2>.json
└── ...
```

`indice.json` guarda metadados. Cada `<id>.json` guarda as últimas mensagens persistidas daquela conversa.

### Cache

`CacheComandos` salva `cache_comandos.json`.

> **Inconsistência de código:** o construtor de `CacheComandos` usa literalmente `~/.Shaula/cache_comandos.json` (S maiúsculo), enquanto os demais componentes usam `~/.shaula`. Em instalações Windows normais isso tende a apontar para o mesmo diretório devido à insensibilidade a maiúsculas/minúsculas, mas o código deveria ser padronizado.

### Log de notificações

`NotificadorToast` grava diagnóstico em:

```text
%USERPROFILE%\.shaula\notificacoes.log
```

### Script temporário de toast

O PowerShell usado para notificações é gravado em pasta temporária:

```text
%TEMP%\shaula\toast.ps1
```

### Capturas de tela

`CapturadorTela` salva BMPs em uma pasta `Shaula` dentro da pasta **Imagens** real do Windows, obtida pela API `SHGetKnownFolderPath`; se isso falhar, usa `~/Pictures/Shaula` como fallback.

---

## Comportamentos importantes

### Internet desligada por padrão

`EstadoInternet` inicia com `_ativa = False`. A interface e as ferramentas compartilham a mesma instância criada pelo registro.

### Comando para sair

`ShaulaWindow.enviar()` intercepta comandos exatos como `sair`, `fechar`, `encerrar`, `feche a Shaula` etc. e chama o fluxo de fechamento.

Ao fechar a interface, `GerenciadorOllama.encerrar_tudo()` tenta terminar `ollama app.exe` e `ollama.exe`.

### Comando para limpar a conversa atual

Variações de `excluir conversa`, `apagar conversa`, `limpar memória` etc. chamam `HistoricoConversa.apagar()` **apenas para a conversa atual** e resetam seu título automático. As outras conversas permanecem intactas.

### Links clicáveis

`FormatadorTexto.linkificar_html()` converte links markdown e URLs brutas em `<a>` para as labels Qt, que usam abertura externa de links.

### Arrastar e soltar

`CampoMensagem` e a própria `ShaulaWindow` aceitam drag-and-drop de arquivos. A janela mantém `anexos_pendentes` até o próximo envio.

---

## Dependências de plataforma

A aplicação é projetada para Windows. Vários módulos utilizam APIs, comandos ou comportamentos específicos do sistema:

- `janelas.py` — `ctypes.windll.user32`;
- `captura_tela.py` — GDI/User32/Shell32/Kernel32;
- `clipboard.py` — clipboard Win32;
- `arquivos.py` — unidades do Windows e `os.startfile`;
- `programas.py` — comando `start`;
- `sistema.py` — PowerShell e `LockWorkStation`;
- `rede.py` — `netsh` para Wi-Fi;
- `notificacoes.py` — PowerShell + WinRT Toast;
- `lembretes.py` — fallback com `MessageBoxW`;
- `ollama_processo.py` — `tasklist`/`taskkill`.

`GerenciadorProcessos` usa `psutil`, embora sua lista de processos protegidos seja especificamente orientada ao Windows.

---

## Testes presentes no pacote

O pacote contém `tests/test_anexos.py` com **15 testes** cobrindo:

- imagem válida;
- redimensionamento de imagem grande;
- arquivo de imagem corrompido;
- limite de tamanho;
- leitura de texto/código;
- truncamento de texto longo;
- fallback Latin-1;
- PDF de texto;
- PDF escaneado;
- falta de `pymupdf`;
- extração de frames de vídeo;
- tipo de arquivo desconhecido;
- caminho inexistente;
- filtro de diálogo;
- `caminho_valido()`.

O arquivo `tools/conftest.py` cria uma `QGuiApplication` de sessão em modo `offscreen`, mas, como observado acima, sua localização não corresponde à suíte em `tests/`.

### O que foi possível validar nesta auditoria

- todos os arquivos `.py` do pacote passam por compilação sintática (`compileall`);
- a estrutura de classes, heranças e métodos foi comparada estaticamente com README/UML;
- `RegistroFerramentas` contém 39 instâncias concretas;
- `test_anexos.py` contém 15 funções de teste.

A execução ponta a ponta dos testes não foi concluída no ambiente desta auditoria porque PySide6 não está instalado nele. Isso não substitui a execução da suíte no `.venv` do Windows da Shaula.

> O instalador atual também não instala `pytest` explicitamente. Para executar a suíte em uma instalação nova, é necessário ter `pytest` disponível no ambiente virtual.

---

## Limitações conhecidas

- Desempenho do `qwen3.5:9b` pode ser muito baixo sem GPU dedicada suficiente.
- A heurística de `DetectorPerguntaFactual` é propositalmente simples e pode pesquisar demais ou deixar passar formulações incomuns.
- Vídeos são representados por no máximo 6 frames e não incluem áudio.
- Não existe estratégia de anexo de áudio.
- PDFs escaneados são limitados a 8 páginas renderizadas por anexo.
- Texto de PDF e arquivos de texto é truncado em 12.000 caracteres.
- A implementação é fortemente dependente de Windows em vários serviços.
- Testes automatizados presentes no pacote cobrem somente o subsistema de anexos; testes mencionados em versões anteriores para outros serviços não estão incluídos aqui.

---

## Inconsistências encontradas no pacote 3.50

Estas não são apenas erros de documentação; são diferenças presentes no próprio pacote auditado:

1. **`tools/conftest.py`** — pela finalidade, deveria estar em `tests/conftest.py`.
2. **Capitalização da pasta de cache** — `CacheComandos` usa `.Shaula`; conversas, memória e notificações usam `.shaula`.
3. **`pytest` ausente do instalador** — a suíte existe, mas o instalador não instala explicitamente o runner de testes.

Esses quatro pontos devem ser corrigidos no código/empacotamento se a intenção for deixar a 3.50 completamente consistente.

---

## UML

A arquitetura correspondente a este README está em:

```text
Documentação/Shaula_UML_Completo_3.50.md
```

O UML revisado representa as classes e relações realmente presentes na versão 3.50, incluindo múltiplas conversas, os 39 tools registrados, serviços, Strategy de pesquisa, Strategy de anexos e persistência.
