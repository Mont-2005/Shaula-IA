# Shaula IA 4.70 — assistente pessoal local

Shaula é uma IA local feita para rodar no Windows, usando **Ollama** com o modelo `qwen3.5:9b` para conversa, raciocínio e tool-calling. A aplicação principal possui interface gráfica em PySide6 (`interface.py`) e existe também um modo de linha de comando independente (`main.py`).

O README foi feito com o código atual, utilizando a estrutura e o código-fonte presentes no pacote **Shaula IA 4.70**. O objetivo é documentar o que a versão atual contém.

> **Arquitetura da 4.70:** o núcleo foi organizado em classes. O despacho de ferramentas é feito por `RegistroFerramentas`, a lógica de cada domínio vive em classes de serviço, a pesquisa e os anexos usam Strategy, e a interface gerencia múltiplas conversas persistentes por meio de `GerenciadorConversas` + `HistoricoConversa`. A persistência (conversas, histórico e cache) passa por `ArmazenamentoJson` (gravação atômica e com trava), e o tamanho do que vai ao modelo é controlado por `OrcamentoContexto`.

> **Novidades da 4.70**
>
> - **Memória da conversa.** Até a 4.65.5 o histórico ficava salvo e visível no chat, mas quase nada dele chegava ao modelo: o prompt de sistema e os 40 schemas ocupam ~5.900 tokens do contexto e, no nível Médio, sobravam ~180 tokens para a conversa. Agora cada nível de esforço tem mais contexto (10240 a 18432) e o `OrcamentoContexto` encurta respostas antigas longas (`CompactadorHistorico`) e deixa um resumo do que foi descartado (`ResumidorHistorico`).
> - **Pedido direto de desligar sempre abre a caixa de confirmação.** `DetectorDesligar` (`tools/intencao_desligar.py`) reconhece "desligue o computador" e chama a ferramenta sem depender de o modelo lembrar.
> - **`desligar_computador` com `segundos` opcional** (padrão 60 s; `0` = agora), via `AtrasoDesligamento`.
> - **A caixa de confirmação vem para a frente** (restaura a janela minimizada, fica por cima e pisca na barra de tarefas), e o botão ■ cancela uma confirmação pendente.
> - **Revisão de bugs.** Corrigidos: `abrir_programa` executava caminhos, endereços e scripts sem confirmação; a confirmação de `abrir_arquivo` era contornável com `run.bat.` (ponto final); com a internet ligada, perguntas de acompanhamento ("e quando isso aconteceu?") e perguntas sobre a conversa ("o que eu falei?") disparavam uma pesquisa na web sem contexto, que ocupava o contexto e empurrava a conversa para fora; o comando de saída por voz ("Sair.") nunca funcionava, por causa da pontuação; um lembrete podia ser entregue horas antes da hora quando outra janela guardava o despertador de um lembrete cancelado de mesmo número; o atalho de desligar disparava em perguntas e em frases compostas; PDFs longos pareciam lidos por inteiro; `converter_base` devolvia lixo para números negativos; `log(8, base=2)` respondia errado em silêncio; o determinante de matrizes de valores pequenos dava 0; a leitura da saída de `netsh`/`tasklist` podia falhar com acentos; e a lista de processos protegidos não incluía o Ollama.
> - **Documentação revisada contra o código:** saíram da árvore de arquivos itens que não existem (`desktop.ini`, `tests/conftest.py`), o comando de saída foi corrigido e as inconsistências do pacote foram atualizadas.

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

### Configuração por variável de ambiente

| Variável | Efeito |
|---|---|
| `SHAULA_CONFIRMAR` | `1` (padrão): as ações sensíveis pedem confirmação. `0`: desliga as confirmações (não recomendado). |
| `SHAULA_ESFORCO` | Nível de esforço inicial (`baixo`, `medio`, `alto`, `extra` ou `max`) quando ainda não há uma escolha salva. A escolha feita no botão **Esforço** da interface (ou pelo comando `esforço` do terminal) fica salva em `~/.shaula/configuracoes.json` e tem prioridade sobre esta variável. |

O raciocínio (`think`) é um dos parâmetros de cada nível de esforço (ver abaixo).

### Nível de esforço

Um seletor na barra superior (botão **🧠 Esforço: Médio ▾**, ao lado de **Internet**) escolhe quanto a Shaula raciocina e quanto contexto usa. Cada nível é um `PerfilEsforco` (`tools/esforco.py`):

| Nível | Raciocínio (`think`) | Contexto (`num_ctx`) | Limite de resposta (`num_predict`) | Rodadas de ferramentas |
|---|---|---|---|---|
| Baixo | não | 10240 | 1024 | 4 |
| **Médio** (recomendado, padrão) | sim | 11264 | 2048 | 8 |
| Alto | sim | 13312 | 3072 | 8 |
| Extra ⚠ | sim | 15360 | 4096 | 10 |
| Máx ⚠ | sim | 18432 | 6144 | 12 |

- **Mais esforço** significa respostas mais completas e mais contexto (cabem mais histórico e anexos), mas leva mais tempo e usa mais VRAM.
- O limite de resposta (`num_predict`) inclui o raciocínio; ele também é a reserva que `OrcamentoContexto` separa dentro do contexto.
- **Extra e Máx** podem passar da VRAM de uma placa de 8 GB: parte do modelo vai para a CPU e a resposta fica bem mais lenta. Confira com `ollama ps` (a coluna PROCESSOR deve mostrar `100% GPU`).
- O que sobra do contexto para a conversa, depois do prompt de sistema, dos 40 schemas e da reserva de resposta, é de ~3.200 tokens no Baixo e no Médio e chega a ~6.300 no Máx (ver [Limite do histórico](#limite-do-histórico)).
- Trocar para um nível com outro `num_ctx` faz o Ollama **recarregar o modelo** na próxima mensagem (alguns segundos).
- O nível vale para todas as janelas e é lembrado entre sessões. Trocar o nível durante uma resposta só vale a partir da próxima mensagem.
- Se o limite de resposta for consumido pelo raciocínio e a resposta vier vazia, a Shaula avisa e sugere aumentar o nível.
- Os valores foram escolhidos para o `qwen3.5:9b` em uma GPU de 8 GB. Eles estão em `CatalogoEsforco.PERFIS` e podem ser ajustados.
- No terminal (`main.py`): `esforço` mostra o nível atual e `esforço alto` troca.

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
- `faster-whisper` e `sounddevice` (**opcionais** — comando por voz; se falharem, a Shaula funciona normalmente sem o microfone);
- Ollama para Windows;
- modelo `qwen3.5:9b`.

O instalador não usa `requirements.txt` (não existe no pacote). Duas observações: `requests` é instalado e verificado, mas nenhum módulo o usa (a pesquisa usa `urllib`); e `pytest` não é instalado (ver [Inconsistências](#inconsistências-do-pacote-470)).

---

## Estrutura de arquivos observada no pacote

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

## Visão geral da arquitetura

### Interface gráfica

`ShaulaWindow` é a janela principal e instancia/possui:

- `CacheComandos`;
- `RegistroFerramentas`;
- `GerenciadorOllama`;
- `GerenciadorConversas`;
- o `HistoricoConversa` da conversa selecionada;
- `GerenciadorAnexos`;
- um `ConfirmadorQt` e um `DetectorDesligar` (este é repassado a cada `TrabalhadorIA`);
- uma `TrabalhadorIA` por mensagem em processamento (que usa um `OrcamentoContexto` próprio).

A janela também gerencia a barra lateral de conversas, criação/seleção/renomeação/fixação/exclusão de conversas, anexos pendentes, internet, renderização do histórico e abertura de uma conversa em nova janela.

### Fluxo de uma mensagem

> Mensagens por voz entram neste mesmo fluxo: o botão do microfone (ou `Ctrl+M`) grava, transcreve e coloca o texto no campo de mensagem — ver [Comando por voz](#comando-por-voz--strategy). A partir daí, é uma mensagem digitada como qualquer outra.

1. `ShaulaWindow.enviar()` valida texto e anexos.
2. Comandos locais especiais, como sair ou limpar a conversa atual, são interceptados antes do modelo.
3. A mensagem do usuário é adicionada ao `HistoricoConversa` atual.
4. Anexos são processados por `GerenciadorAnexos`; no histórico fica somente uma nota textual sobre os arquivos.
5. A janela cria uma nova `TrabalhadorIA` (`QThread`) com mensagens, registro e anexos desta troca.
6. **Atalho de desligar.** No início de `TrabalhadorIA.run()`, se a mensagem não tem anexo, `DetectorDesligar.argumentos()` verifica se ela é um pedido claro de desligar o computador ("desligue o computador", "desliga o pc em 30 segundos"). Se for, chama `RegistroFerramentas.executar("desligar_computador", ...)` direto — que mostra a caixa de confirmação — e devolve o resultado **sem chamar o modelo**. Ver [Pedidos diretos de desligar](#pedidos-diretos-de-desligar-atalho-sem-o-modelo).
7. `TrabalhadorIA.run()` adiciona ao contexto um lembrete de estado da internet e, quando necessário, conteúdo textual extraído de anexos (em mensagem de sistema separada).
8. Com internet ligada **e sem anexos nesta troca**, `DetectorPerguntaFactual` pode disparar uma pesquisa automática antes da primeira chamada ao modelo. Perguntas sobre a própria Shaula, sobre o computador do usuário ou contas de matemática não disparam.
9. Antes de **cada** chamada ao modelo, `OrcamentoContexto.ajustar()` faz o prompt caber no `num_ctx` do nível de esforço atual: limita cada texto de apoio (pesquisa, anexo, saída de ferramenta) a 35% do orçamento, encurta respostas antigas e longas da Shaula (`CompactadorHistorico`; as falas do usuário ficam intactas), descarta as mensagens mais antigas e deixa no lugar um resumo curto do que saiu (`ResumidorHistorico`, no máximo 600 tokens e 30% do espaço livre) e, se ainda faltar, encurta o maior texto de apoio. O orçamento desconta os schemas das ferramentas e a reserva para a resposta (`num_predict` do nível).
10. O Ollama é chamado, via `ChatInterrompivel`, com `think` e `options` (`num_ctx`, `num_predict`) do nível de esforço atual e `registro.schemas_openai()` — **exceto quando a troca tem anexo**: nesse caso vai sem ferramentas (os 40 schemas custam cerca de 4.100 tokens, que fariam falta ao conteúdo do arquivo). Em qualquer ponto daqui até a resposta, o botão ■ (ou `Esc`) interrompe — ver [Interromper a resposta da IA](#interromper-a-resposta-da-ia).
11. Se o modelo solicitar ferramentas, `RegistroFerramentas.executar()` encontra a instância pelo nome e delega a execução. Há um máximo de idas e vindas por mensagem definido pelo nível de esforço (4 a 12; 8 no Médio); se passar disso, a troca termina com um aviso, em vez de ficar em laço.
12. Se nenhuma ferramenta chamada exigir síntese, o resultado é devolvido diretamente, evitando uma nova inferência.
13. Se uma ferramenta exigir síntese — atualmente `PesquisarInternetFerramenta` — o resultado volta ao modelo para geração da resposta final. As mensagens de ferramenta existem **só no contexto da troca**: não são gravadas no histórico da conversa.
14. `ShaulaWindow.receber_resposta()` exibe e persiste a resposta do assistente na conversa atual. Falhas (Ollama fora do ar, resposta vazia, limite de rodadas) chegam por um sinal separado (`TrabalhadorIA.erro`): aparecem na tela com "⚠", mas **não entram no histórico**.

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
- `CapturadorTela` recebe `GerenciadorJanelas` e `OcultadorJanelasProprias`;
- `GerenciadorLembretes` recebe `NotificadorToast` e um `ArmazenamentoJson` (`~/.shaula/lembretes.json`);
- `RegistroFerramentas` recebe uma `PoliticaConfirmacao` e um `Confirmador` (ver *Confirmação de ações sensíveis*).

### Quantidade real de ferramentas

A versão gráfica registra **40 ferramentas concretas**, e não 24.

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

#### Sistema, arquivos e interação — 30

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
30. `AnalisarTelaFerramenta` → `analisar_tela`

Quando o modelo esquece um parâmetro obrigatório, `RegistroFerramentas.executar()` responde dizendo qual faltou (antes o erro virava apenas `'nome'`).

### Atalho de velocidade

`Ferramenta.precisa_de_sintese` retorna `False` por padrão. Assim, a maioria das ações locais retorna seu resultado diretamente ao usuário sem uma segunda chamada ao Qwen.

`PesquisarInternetFerramenta` sobrescreve essa propriedade para `True`, porque o texto bruto da busca precisa ser interpretado/sintetizado.

---

## `main.py` — modo de linha de comando

`main.py` **não chama `interface.py`** e não faz parte do fluxo iniciado por `Shaula.bat`. É um entrypoint independente que usa o mesmo `RegistroFerramentas`.

A lógica vive na classe `AssistenteTerminal` (estado: histórico, registro de ferramentas e `OrcamentoContexto`). Nada executa no `import`; só `AssistenteTerminal().executar()` (chamado por `main()` sob `if __name__ == "__main__"`) abre o laço de conversa. Dependências como a função de chat, a entrada e a saída são injetáveis, o que facilita testar. Como na interface gráfica, usa o mesmo nível de esforço (`EstadoEsforco`, com o comando `esforço [nível]`), ajusta o contexto antes de cada chamada, limita as rodadas de ferramentas conforme o nível e trata o Ollama fora do ar com uma mensagem em vez de um traceback.

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

Digite `sair` (ou `Ctrl+C`/`Ctrl+D`) para encerrar. O banner exibe `Shaula 4.70 (terminal)`.

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

**Exceções (`PADRAO_ASSUNTO_LOCAL`).** Não é considerada factual — e portanto não dispara pesquisa — uma mensagem que trate de a própria Shaula (`você`, `seu`, `sua`), do usuário (`meu`, `minha`, `tenho`), de coisas do computador (`processos`, `janelas`, `monitores`, `lembretes`, `área de transferência`), de conversões e matrizes (`converta`, `binário`, `determinante`…) ou que contenha uma conta (`25 vezes 18`, `7x8`, `2+2`). Para essas, o modelo usa a ferramenta local certa. Isso é uma heurística: o modelo ainda pode chamar `pesquisar_internet` por conta própria.

**Mensagens que dependem da conversa (`PADRAO_REFERE_CONVERSA`).** Também não dispara pesquisa uma mensagem que só faz sentido dentro da conversa: as que começam com `e`, `mas`, `então` ou `ou` ("e quando isso aconteceu?", "e o segundo?") ou que falam do que já foi dito (`falei`, `disse`, `mencionei`, `conversamos`, `lembra`…) ou apontam para algo anterior (`isso`, `isto`, `aquilo`, `desse`, `nesse`, `dele`, `dela`, `acima`, `agora pouco`…). Antes, qualquer frase terminada em `?` que não citasse "você" ou "meu" virava uma pesquisa solta na web: o resultado, sem relação com o assunto, ocupava até 35% do contexto e levava o modelo a responder com ele em vez de usar a memória da conversa.

Se a heurística disparar (e não houver anexos na troca), `TrabalhadorIA` executa `PesquisaInternet.buscar()` antes de chamar o modelo e coloca o resultado no contexto como `RESULTADO DE PESQUISA AUTOMÁTICA`.

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
| Imagem | `.png`, `.jpg`, `.jpeg`, `.webp`, `.bmp`, `.gif` | 25 MB; lado máximo 768 px após redimensionamento; respeita a orientação EXIF |
| PDF | `.pdf` | 50 MB; texto truncado em 12.000 caracteres; PDF escaneado renderiza no máximo 4 páginas |
| Vídeo | `.mp4`, `.mov`, `.avi`, `.mkv`, `.webm` | 300 MB; até 4 frames amostrados; sem áudio |
| Texto/código | `.txt`, `.md`, `.markdown`, `.log`, `.csv`, `.json`, `.yaml`, `.yml`, `.xml`, `.ini`, `.cfg`, `.py`, `.js`, `.ts`, `.java`, `.c`, `.cpp`, `.h`, `.cs`, `.sql`, `.bat`, `.sh`, `.html`, `.css` | 5 MB; conteúdo truncado em 12.000 caracteres; BOM UTF-8 é tratado |

> **Por que 768 px, 4 páginas e 4 frames?** Estimativa: uma imagem custa cerca de 1 token por bloco de 28×28 px. Com 1568 px isso chegava a ~3.000 tokens por imagem, e um PDF escaneado de 8 páginas ou um vídeo de 6 frames não cabiam no `num_ctx` de 8192 — nem, numa placa de 8 GB, na VRAM. Com 768 px uma imagem custa em torno de 750 tokens (`OrcamentoContexto` estima 800).

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

### Como o anexo aparece no chat

A nota acima é o que o **modelo** lê (é como ele sabe que um arquivo foi enviado naquele ponto da conversa), e o formato dela não muda. Na **tela** ela não aparece como texto: vira um **cartão por arquivo**, como no chat do Claude, alinhado à direita acima do balão da mensagem:

- um **ícone** do tipo do arquivo (folha com o canto dobrado, na cor do tipo — PDF, imagem, vídeo, código, texto — e com o formato escrito nela); nas imagens recém-enviadas, a miniatura da foto no lugar do ícone;
- o **nome** do arquivo (nomes longos são cortados no meio, e a dica mostra o nome inteiro);
- o **formato** e o detalhe, por exemplo `PDF · 128 página(s)`; num PDF longo, que só é lido até 12.000 caracteres, o detalhe diz até onde foi: `PDF · 128 página(s), só as primeiras ~6 foram lidas` (o modelo recebe o mesmo aviso no texto). Antes, a nota mostrava só "128 página(s)", como se o livro inteiro tivesse sido lido.

Os mesmos cartões aparecem ao reabrir uma conversa antiga, porque a interface lê a nota do histórico (`NotaAnexo.separar()`); como os bytes não são guardados, nesse caso as imagens mostram o ícone em vez da miniatura. Uma mensagem que leva só arquivos não tem balão de texto. A bandeja de anexos pendentes (acima do campo de texto) não mudou.

As peças são quatro classes: `NotaAnexo` (monta a nota e a separa do texto) e `DescricaoAnexo` (nome, formato, tipo e detalhe), ambas em `tools/nota_anexo.py` e sem Qt; `IconeArquivo` (desenha o ícone) e `CartaoAnexo` (o cartão), em `tools/cartao_anexo.py`.

---

## Comando por voz — Strategy

Falar com a Shaula usa **o mesmo caminho** de escrever: não existe um interpretador de comandos de voz separado. O áudio vira texto, o texto vai para `enviar()`, e o tool-calling do modelo escolhe a ferramenta — então qualquer coisa que já funciona digitando ("abre o Discord", "cria um lembrete para daqui a 30 minutos", "tira um print do monitor 2") funciona falando.

### Como usar

- Clique no botão de microfone ao lado do campo de mensagem (ou `Ctrl+M`). O campo de texto dá lugar a um painel "Ouvindo... 0:07" com um medidor de volume (barrinhas) e um ✕; o botão do microfone vira um ■ vermelho.
- Fale o tempo que quiser. **A gravação não termina sozinha** — como num ditado, ela vai até você mandar parar (um teto de segurança de 10 minutos evita um microfone esquecido ligado encher a memória).
- Para terminar e transcrever: clique no ■ de novo ou `Ctrl+M`. Para descartar: clique no ✕ ou `Esc`.
- Por padrão (`ENVIAR_VOZ_AUTOMATICAMENTE = True` em `interface.py`), o texto reconhecido é enviado na hora. **Se o campo de texto já tinha algo digitado**, a voz apenas acrescenta ao texto e espera você revisar — para um reconhecimento errado não disparar junto o que você estava escrevendo.
- Se ninguém falou (microfone mudo, gravação curta demais), aparece "Não entendi — tente de novo".
- O microfone fica desativado enquanto a Shaula está respondendo.
- Ao ser enviado, o texto reconhecido aparece no chat como mensagem do usuário, então dá para conferir o que foi entendido.

### Classes (`tools/voz.py`)

| Classe / função | Papel |
|---|---|
| `GerenciadorVoz` | Fachada: `escutar(parar, cancelado, notificar_estado, notificar_nivel)` grava até mandarem parar, transcreve e devolve o texto (ou `None`). `pre_aquecer()` carrega o modelo em segundo plano. `tempo_ocioso_s` (padrão 180) define em quanto tempo sem uso o modelo é liberado da memória (`None` = nunca; `0` = após cada uso). Se o modelo não está carregado, ele carrega **enquanto você fala** (`_CargaEmSegundoPlano`). Aceita gravador, reconhecedor e limpador por injeção. |
| `Gravador` | Abre a `FonteAudio` e grava **tudo** até o evento `parar`; descarta gravações curtas demais ou sem voz nenhuma; informa o volume de cada bloco (alimenta o medidor); sobe o volume de gravações baixas; devolve áudio `float32` 16 kHz. |
| `FonteAudio` → `MicrofoneSounddevice` | Interface e implementação do microfone (mono, 16 kHz, `int16`, blocos de 30 ms). |
| `calcular_nivel()` / `normalizar_volume()` | Volume (RMS) de um bloco; amplificação limitada (até 8x, alvo de pico 0,8) de gravação baixa — reconhecimento erra mais com áudio fraco. |
| `ReconhecedorFala` → `ReconhecedorFasterWhisper` | Strategy do motor de fala-para-texto. Whisper local (`faster-whisper`), CPU, `int8`, modelo `medium`, busca em feixe de 5, idioma `pt`. `descarregar_modelo()` libera o modelo da memória. |
| `LimpadorTranscricao` | Remove "alucinações" típicas do Whisper em silêncio (legendas, "obrigado por assistir"), rejeita quando o motor só repete o prompt de contexto (apenas trechos de 4 ou mais palavras — comandos curtos como "tirar print" passam) e normaliza grafias do nome ("Xaula", "Chaula" → "Shaula"). |
| `VozIndisponivel` | Exceção para o que o usuário precisa resolver: biblioteca faltando, microfone inacessível, modelo não baixado. |
| `TrabalhadorVoz` (`interface.py`) | `QThread` que roda `escutar()` fora da thread da interface e devolve estado/volume/texto/erro por sinais. Dois controles: `finalizar()` (para e transcreve) e `cancelar()` (descarta). |
| `MedidorNivelVoz` (`interface.py`) | Widget que desenha as barrinhas de volume enquanto grava. |

`GerenciadorVoz` é criado uma vez por processo e **compartilhado** entre janelas (inclusive as abertas por "abrir em nova janela"), para o modelo de voz não ser carregado uma vez por janela.

### Decisões de projeto

- **Precisão.** O reconhecimento usa o modelo `medium` (bem mais preciso que `small` em português), busca em feixe de 5 (em vez da busca gulosa), volume normalizado, o nome da assistente e verbos de comando como contexto, e gravação contínua (sem cortar frases nas pausas). Para precisão máxima, `ReconhecedorFasterWhisper(modelo="large-v3-turbo")`; para velocidade em máquina fraca, `"small"` ou `"base"`.
- **Offline depois da primeira vez.** O modelo é baixado uma única vez para `~/.shaula/modelos_voz` (cerca de 1,5 GB para `medium`) — o instalador já faz isso (`python -m tools.voz`). Depois, o reconhecimento funciona sem internet.
- **Carga sob demanda.** O modelo de voz **não** é pré-carregado por padrão (`PRE_AQUECER_VOZ = False` em `interface.py`): ele só carrega quando o microfone é ativado, e a carga acontece **durante a gravação**, sem fazer a pessoa esperar. O aviso "Carregando o reconhecimento de voz..." só aparece se a carga ainda não terminou quando você para de falar. Se faltar a biblioteca, o erro aparece antes de você gastar tempo falando. Depois de 180 s sem uso o modelo é liberado (o `medium` ocupa ~1,5 GB de RAM e várias threads de CPU, que fazem falta ao Ollama); o próximo uso recarrega. Com `PRE_AQUECER_VOZ = True`, cerca de 2 s depois de abrir a janela o modelo é carregado em segundo plano **se já estiver no disco** (nunca baixa nada sozinho).
- **CPU, não GPU.** A GPU já está ocupada pelo `qwen3.5:9b`; o Whisper roda em CPU com quantização `int8`. A transcrição só começa quando você para de falar; em CPU, o `medium` leva alguns segundos por frase.
- **Bibliotecas opcionais, importadas só ao usar.** Sem `faster-whisper` ou `sounddevice` a Shaula abre normalmente; ao clicar no microfone aparece um aviso com o `pip install` necessário (mesmo princípio de `DependenciaFaltando` nos anexos).
- **Comandos sensíveis.** Como o envio é automático, um reconhecimento errado pode executar uma ferramenta de verdade (por exemplo, desligar o computador ou finalizar um processo). Para exigir revisão antes de enviar, defina `ENVIAR_VOZ_AUTOMATICAMENTE = False`.

---

## Blocos de código e botão Copiar

Quando uma resposta da Shaula contém código entre cercas (```` ```python … ``` ````), ela deixa de ser exibida como texto cru e passa a mostrar **um bloco por trecho de código**, como nos chats de IA:

- **Cabeçalho** com o nome da linguagem e o botão **Copiar**. O botão copia o código **inteiro** (sem as cercas e sem o recuo do bloco) para a área de transferência e mostra "✓ Copiado" por cerca de 2 segundos.
- **Indentação preservada**, fonte monoespaçada (Consolas) e cores para palavras-chave, strings, números e comentários (Python, JavaScript/TypeScript, C/C++/C#/Java/Kotlin/PHP, Go, Rust, SQL, shell e JSON; outras linguagens recebem só strings e números).
- **Sem quebra de linha**: linhas longas ganham uma barra de rolagem horizontal no próprio bloco. A rolagem vertical continua sendo a da conversa.
- O texto da resposta que vem antes, entre e depois dos blocos aparece normalmente, e trechos entre crases simples (`` `assim` ``) aparecem destacados.
- Um bloco que o modelo abriu e **não fechou** (resposta cortada) vai até o fim da mensagem, em vez de engolir o resto da conversa.
- Como o bloco é um componente próprio, o código **não passa mais** pela remoção de `**` aplicada ao texto das respostas: antes, uma potência como `x ** 2` perdia o operador.

Respostas sem código continuam sendo um texto simples. Mensagens do próprio usuário não viram blocos.

As classes ficam em `tools/bloco_codigo.py`: `DivisorDeBlocos` (separa texto e código, sem depender do Qt), `FormatadorTextoMensagem` (texto → HTML), `RealceSintaxe` e `CatalogoLinguagens` (cores), `EditorCodigo`, `BlocoCodigo` (cabeçalho, botão e editor) e `ConteudoMensagemShaula` (a coluna de texto e blocos). Na janela, `adicionar_mensagem` usa `ConteudoMensagemShaula` quando `DivisorDeBlocos.tem_codigo()` é verdadeiro; esse componente ocupa a largura máxima permitida e acompanha o redimensionamento da janela.

---

## Interromper a resposta da IA

Enquanto a Shaula responde, o botão de enviar (➤) vira um botão de **interromper** (■ vermelho). `Esc` faz o mesmo (e, se houver uma gravação de voz em andamento, `Esc` cancela a gravação em vez disso).

A Shaula usa `chat()` sem streaming, e uma chamada assim bloqueia a thread até o modelo terminar a resposta inteira. Por isso a chamada passa por `ChatInterrompivel` (`tools/ollama_chat.py`): a chamada de verdade roda numa thread auxiliar, e quem chamou espera em intervalos de 50 ms conferindo o pedido de parar. Ao interromper:

1. a `TrabalhadorIA` é liberada na hora (`ChamadaCancelada`), sem esperar o modelo terminar;
2. a conexão HTTP com o Ollama é fechada — o servidor percebe que o cliente foi embora e deixa de gerar (melhor esforço; no Windows o fechamento do socket interrompe a leitura pendente);
3. aparece "⏹ Resposta interrompida." na conversa (só na tela, não vai para o histórico salvo) e o botão volta a ser ➤.

Se a IA estiver esperando uma resposta Sim/Não de uma confirmação, interromper também **nega** a ação e fecha a caixa (`ConfirmadorQt.cancelar_pendentes()`), em vez de deixar a thread presa até o tempo limite.

O que interromper **não** faz: desfazer uma ferramenta que já executou. Se a Shaula já tinha aberto um programa, por exemplo, ele continua aberto — a ferramenta em andamento termina, o que ela devolveu é descartado, e nenhuma outra é iniciada (inclusive as seguintes da mesma rodada). A mensagem do usuário permanece no histórico; nenhuma resposta da IA é gravada (e os resultados de ferramentas nunca são gravados no histórico — só existem no contexto da troca). Fechar a janela com a IA respondendo também interrompe a chamada, em vez de esperar o modelo terminar.

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

Só mensagens com `role` `user` ou `assistant` e `content` textual são persistidas (`HistoricoConversa.PAPEIS_PERSISTIDOS`). Mensagens de ferramenta, gravadas por versões antigas, são descartadas ao carregar. Se o arquivo estiver corrompido, a conversa abre vazia em vez de travar.

A gravação de histórico, índice de conversas e cache passa por `ArmazenamentoJson`: escreve num arquivo temporário e só então troca pelo definitivo (`os.replace`), com uma trava por arquivo — antes, um fechamento no meio da gravação, ou duas janelas alterando o índice juntas, podiam deixar o arquivo cortado e as conversas sumirem da barra lateral. Operações de ler-alterar-gravar do índice (criar, renomear, fixar, apagar…) rodam dentro dessa trava.

**Salvo não é o mesmo que enviado ao modelo.** O arquivo guarda até 60 mensagens, mas o que vai ao Ollama em cada chamada é limitado pelo `num_ctx` do nível de esforço. `OrcamentoContexto.ajustar()` faz o histórico caber assim, nesta ordem:

1. respostas antigas e longas da Shaula (acima de 600 caracteres) são encurtadas por `CompactadorHistorico`, da mais velha para a mais nova; as falas do usuário nunca são encurtadas;
2. se ainda não couber, as mensagens mais antigas são descartadas, e no lugar entra uma mensagem de sistema com um **resumo** (`ResumidorHistorico`): o começo de cada fala descartada, privilegiando as mais recentes, com no máximo 600 tokens e 30% do espaço livre (e só se couberem 120 tokens);
3. se ainda faltar, o maior texto de apoio (pesquisa, anexo, saída de ferramenta) é encurtado.

Assim, o que foi dito há pouco chega ao modelo por inteiro e o que foi dito há mais tempo chega resumido. Detalhes que só existiam no meio de uma resposta longa e antiga podem se perder. Para lembrar mais, use um nível de esforço mais alto.

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

O cache usa `~/.shaula/cache_comandos.json`, como os demais componentes (a grafia `.Shaula` das versões anteriores foi padronizada). A busca de arquivos memoriza **todos** os resultados encontrados; ao reaproveitar, confere se os arquivos ainda existem e refaz a busca se algum sumiu.

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

`CapturadorTela` salva **PNGs** (sem perdas, e bem menores que os BMPs usados antes: um print 4K passa de ~33 MB para poucos MB) em uma pasta `Shaula` dentro da pasta **Imagens** real do Windows, obtida pela API `SHGetKnownFolderPath`; se isso falhar, usa `~/Pictures/Shaula` como fallback. A conversão dos pixels do GDI (BGRA, linhas de baixo para cima) para PNG/JPEG é feita por `ImagemCapturada` (`tools/imagem_tela.py`), só com `QImage`, que é seguro na thread da IA. A área de transferência continua recebendo o DIB.

---

## Comportamentos importantes

### Internet desligada por padrão

`EstadoInternet` inicia com `_ativa = False`. A interface e as ferramentas compartilham a mesma instância criada pelo registro.

### Comando para sair

`ShaulaWindow.enviar()` pergunta a `ComandosLocais.eh_saida()` (`tools/comandos_locais.py`) se a mensagem é um pedido para fechar a Shaula. A comparação ignora maiúsculas, acentos e **pontuação** (a transcrição de voz devolve "Sair." e antes o comando falado nunca funcionava) e aceita o nome dela na frente ("Shaula, sair."). As frases são: `sair`, `fechar`, `feche`, `encerre`, `encerrar`, `fechar shaula`, `feche a shaula`, `encerre a shaula`, `sair da shaula`, `pode sair`, `pode fechar` e `pode encerrar`. Qualquer palavra a mais ("pode sair do chrome", "sair e abrir o chrome") faz a mensagem seguir para o modelo.

Os comandos de **apagar a conversa** (`excluir/apagar/limpar/esquecer conversa`, `excluir/apagar histórico`, `esquecer tudo`, `limpar/apagar memória`) continuam exigindo a frase **exata**, sem pontuação nem palavras a mais (`ComandosLocais.eh_apagar_conversa()`): são irreversíveis e não pedem confirmação, então uma frase falada e mal reconhecida não pode apagar o histórico.

O comando `sair` encerra a Shaula inteira: para a IA e a voz de cada janela, fecha **todas** as janelas abertas e tenta terminar o Ollama. Já fechar uma janela comum só encerra o Ollama (`GerenciadorOllama.encerrar_tudo()`, que tenta terminar `ollama app.exe` e `ollama.exe`) se for a **última** janela aberta: fechar uma janela secundária não derruba o modelo das outras.

### Comando para limpar a conversa atual

Variações de `excluir conversa`, `apagar conversa`, `limpar memória` etc. chamam `HistoricoConversa.apagar()` **apenas para a conversa atual** e resetam seu título automático. As outras conversas permanecem intactas.

Não é possível apagar pelo menu a conversa em que a IA ainda está respondendo (a resposta cairia na conversa errada): a Shaula pede para esperar o fim.

### Links clicáveis

`FormatadorTexto.linkificar_html()` converte links markdown e URLs brutas em `<a>` para as labels Qt, que usam abertura externa de links.

### Arrastar e soltar

`CampoMensagem` e a própria `ShaulaWindow` aceitam drag-and-drop de arquivos. A janela mantém `anexos_pendentes` até o próximo envio.

---

### Proteções e limites das ferramentas

Estas verificações existem porque as ferramentas executam ações reais e porque o texto que chega a elas pode vir do modelo (ou de uma página pesquisada que ele repetiu):

| Ferramenta / serviço | Proteção |
|---|---|
| `calcular` | Recusa argumentos nomeados (`log(8, base=2)` antes ignorava `base` e respondia `ln(8)`); aceita `factorial(5.0)`; traduz "math domain error" e erros de fatorial. Recusa, **antes** de calcular, potências inteiras que passem de ~20.000 bits (ex.: `7**(10**8)`, `9**9**9`) e `factorial` acima de 1.500; resultado infinito vira "grande demais" e resultado complexo vira "não é um número real". Sem isso a thread da IA ficava presa e o botão ■ não interrompe uma ferramenta em execução. |
| `abrir_programa` | Pede confirmação quando o nome é um caminho, endereço ou script (ver [Confirmação](#confirmação-de-ações-sensíveis)). O nome só pode conter letras, dígitos, espaço e `. - + @ : \ / ( )`. Caracteres como `& | < > ^ % "` são recusados, porque o `cmd /c start` os interpretaria (ex.: `calc&calc` abriria dois programas). |
| `testar_ping` | O host deve ser um nome DNS, IPv4 ou IPv6 e não pode começar com `-` (seria lido como opção do `ping`); há timeout de 20 s. A leitura do tempo aceita `tempo=` e `time=`. |
| `finalizar_processo` | A lista de protegidos inclui o Ollama (finalizá-lo derruba a própria Shaula) e processos de sessão e de segurança do Windows (`sihost`, `ctfmon`, `audiodg`, `msmpeng`…). Ela vale para o nome **real** de cada processo encontrado (pedir `svchost` sem `.exe` não a burla); a própria Shaula e os processos acima dela nunca são finalizados; o nome por trecho precisa ter ao menos 3 letras; as instâncias são finalizadas de uma vez só. |
| `desligar_computador` | `segundos` é opcional: ausente, `null` ou texto inválido vira **60**; `0` desliga agora; negativo é recusado. A caixa de confirmação e a ferramenta usam a mesma classe (`AtrasoDesligamento`), então o texto da pergunta sempre bate com o que será feito. Se o Windows já tiver um desligamento agendado (código 1190), a resposta diz isso e como cancelar. |
| `criar_lembrete` | Aceita no máximo 1 ano; `nan`, `inf` e valores não positivos são recusados. |
| `desligar_computador`, `finalizar_processo`, `fechar_programa`, `controlar_janela` (fechar), `abrir_arquivo` (programas e scripts) | Pedem confirmação em caixa de diálogo (ver acima). |
| `analisar_tela` | A imagem só vai para o modelo local; a Shaula se esconde só durante a captura e sempre volta. |
| `tirar_print`, `bloquear_tela` | O atraso máximo é de 60 s (um atraso maior prenderia a thread da IA). Prints no mesmo segundo não se sobrescrevem (`_2`, `_3`…), e falhas do Windows na captura viram mensagem em vez de imagem preta. |
| Comandos externos (PowerShell, `nvidia-smi`, `ping`) | Timeout de 20 s. |
| Janelas e monitores | Para escolher entre várias janelas parecidas, use o número: `"chrome 2"`, `"Discord 1"` (a ordem é a da lista de janelas abertas). |

---

### Confirmação de ações sensíveis

Algumas ferramentas fazem algo que não se desfaz com facilidade, e o pedido pode vir de um comando de voz mal reconhecido ou de um texto malicioso numa página pesquisada. Antes delas, a Shaula **pergunta numa caixa de diálogo** ("Sim, autorizar" / "Não"). A pergunta aparece para:

| Ferramenta | Quando |
|---|---|
| `desligar_computador` | sempre |
| `finalizar_processo` | sempre |
| `fechar_programa` | sempre |
| `controlar_janela` | só com a ação `fechar` |
| `abrir_arquivo` | só se for programa ou script (`.exe`, `.bat`, `.cmd`, `.ps1`, `.vbs`, `.msi`, `.lnk`, `.url`, `.cpl`, `.msc`, `.py`, documentos com macro `.docm`/`.xlsm`/`.pptm`…) |
| `abrir_programa` | só se o nome for um **caminho, caminho de rede ou endereço** (contém `\`, `/` ou `:`) ou um script/atalho (`.bat`, `.lnk`…); o nome simples ("notepad", "chrome.exe") não pergunta |

Como funciona:

- **Onde fica:** `RegistroFerramentas.executar()` consulta a `PoliticaConfirmacao` (uma `RegraConfirmacao` por ferramenta) **antes** de executar. Se houver pedido, chama o `Confirmador` configurado. Não é preciso mexer em cada ferramenta.
- **Como o Windows enxerga o caminho:** `CaminhoExecutavel` (em `tools/confirmacao.py`) ignora pontos e espaços no fim do nome (`run.bat.` abre `run.bat`) e um fluxo alternativo depois de dois-pontos (`run.exe:fluxo`). Antes, a regra olhava só a extensão do texto recebido, e essas formas passavam sem pergunta. `abrir_programa` também executa arquivos, então ganhou a sua regra (`RegraAbrirPrograma`): sem ela, bastava chamar `abrir_programa("C:\\x\\arquivo.exe")` para contornar a confirmação de `abrir_arquivo`.
- **Parâmetros obrigatórios primeiro:** `RegistroFerramentas.executar()` confere os parâmetros obrigatórios do schema **antes** de pedir confirmação (não se pergunta "finalizar ''?" para uma chamada que vai falhar). Um `KeyError` de dentro da ferramenta deixou de ser confundido com "faltou parâmetro": aparece como erro de execução, com a causa real.
- **Padrão seguro:** a resposta padrão é **não**. Fechar a caixa, apertar `Esc`, passar de 120 s sem resposta, usar o botão ■ ou fechar a janela contam como "não". Se não houver confirmador configurado, a ação sensível é **recusada**.
- **Interface gráfica:** a ferramenta roda na thread da IA, mas só a thread da interface abre janelas. `ConfirmadorQt` envia o pedido por um sinal, mostra a caixa e a thread da IA espera a resposta. A caixa tem estilo próprio escuro: o estilo geral da janela pinta todo texto de branco, e uma `QMessageBox` com o fundo claro do sistema ficava ilegível.
- **A caixa sempre aparece à frente:** como o pedido costuma vir por voz, com a Shaula minimizada ou atrás de outro programa, `ConfirmadorQt` restaura a janela se estiver minimizada, marca a caixa como "sempre no topo", a ativa e pisca o ícone na barra de tarefas. (O Windows não deixa uma janela comum "roubar" o foco; sem isso a caixa podia abrir escondida e a ação expirava em silêncio.)
- **Botão ■:** `interromper_resposta()` chama `cancelar_pendentes()`, que nega e fecha qualquer caixa aberta.
- **Terminal (`main.py`):** `ConfirmadorTerminal` pergunta `Autorizar? [s/N]`.
- **Resultado negado:** a ferramenta devolve "Ação cancelada: você não autorizou…", e a Shaula mostra isso.
- **Desligar:** a variável de ambiente `SHAULA_CONFIRMAR=0` desliga todas as confirmações (não recomendado).

#### Pedidos diretos de desligar (atalho sem o modelo)

A confirmação mora no registro, então só acontece se a ferramenta for **chamada**. Um modelo local pequeno às vezes responde em texto ("ok, desligando…") ou pergunta o tempo em vez de chamá-la, e aí nenhuma caixa aparecia. Por isso `DetectorDesligar` (`tools/intencao_desligar.py`) reconhece o pedido claro e `TrabalhadorIA.run()` chama `desligar_computador` direto, antes do modelo. O detector é composto por duas classes injetáveis: `NormalizadorTexto` (minúsculas, sem acento) e `InterpretadorTempo` (extrai o atraso).

| Frase (exemplos) | Argumentos |
|---|---|
| "desligue o computador", "por favor, desligue o pc" | `{}` (a ferramenta usa 60 s) |
| "desliga o pc agora", "desligue já o notebook" | `{"segundos": 0}` |
| "desligar o computador em 30 segundos", "desligue o pc daqui a 2 minutos", "desligue o notebook em 1 hora" | `{"segundos": 30}`, `{"segundos": 120}`, `{"segundos": 3600}` |

Não dispara com perguntas (`como`, `qual`, `o que`, `quando`… e qualquer frase terminada em `?` que não seja um pedido educado como "você pode desligar o pc?"), negações e cancelamentos (`não`, `nunca`, `cancela…`, `pare de`, `sem`), frases que pedem mais que desligar ou desligam sob condição (`e`, `depois`, `antes`, `mas`, `quando`, `se`…: "desligue o pc depois de baixar o arquivo", "desligue o pc e abra o chrome"), textos com mais de 200 caracteres ou mensagens com anexo; nesses casos o modelo responde normalmente e, se chamar a ferramenta, a confirmação vale do mesmo jeito. O atalho **não pula** a confirmação: só garante que a pergunta aconteça. Os outros pedidos sensíveis (finalizar processo, fechar programa ou janela, abrir executável) **não** têm atalho: dependem de o modelo chamar a ferramenta.

### Lembretes persistentes

Os lembretes pendentes ficam gravados em `~/.shaula/lembretes.json` (via `ArmazenamentoJson`). **O arquivo é a fonte da verdade; os `Timer` são só despertadores**:

- Ao abrir a Shaula, os lembretes que ainda vão acontecer **voltam a contar**, e os que venceram com a Shaula fechada são **entregues uma vez, marcados como "atrasado"** (com "era para dd/mm às hh:mm"), um por vez e depois de a janela subir.
- Se a Shaula estiver fechada na hora marcada, **nada avisa naquele momento**: o aviso aparece quando ela abrir.
- `listar_lembretes` e `cancelar_lembrete` leem e alteram o arquivo, então valem para **todas as janelas** (cada janela tem seu próprio `GerenciadorLembretes`).
- Na hora de disparar, o lembrete é removido do arquivo **antes** de ser entregue, dentro de uma trava: se duas janelas tiverem um `Timer` para o mesmo lembrete, só a primeira entrega, e um lembrete cancelado em outra janela não dispara.
- **Conferência da hora:** o despertador só entrega o lembrete se ele já venceu (folga de 2 s). Os números são reaproveitados (cancelar o de maior número e criar outro dá o mesmo `#`), e o despertador antigo de **outra janela**, que não ficou sabendo do cancelamento, disparava na hora do lembrete velho e entregava o novo horas antes. Agora ele reagenda para a hora certa.
- Os números (`#1`, `#2`…) continuam de onde o arquivo parou, entre sessões e entre janelas. O horário é gravado com precisão total.
- Se não for possível gravar em disco, o lembrete funciona na sessão e a resposta avisa disso.

### Perguntar sobre a tela (`analisar_tela`)

"O que tem na minha tela?", "leia esse erro", "que programa é esse?": a ferramenta `analisar_tela` captura um monitor e **mostra a imagem ao modelo** (que precisa ter visão; o `qwen3.5:9b` tem). Diferente de `tirar_print`, que guarda um arquivo para o usuário, nada é salvo em disco.

- **Qual monitor:** o principal, ou o `monitor` pedido (um por chamada).
- **A Shaula sai da frente:** por padrão, `OcultadorJanelasProprias` minimiza, só durante a captura (cerca de 0,4 s de espera pela animação), as janelas da Shaula que **cobrem** o monitor capturado, e as restaura num `finally` (mesmo se a captura falhar). Se a Shaula está em outro monitor, nada se mexe. `ocultar_shaula=false` mantém tudo no lugar.
- **Imagem:** `CapturadorTela.capturar_para_modelo()` devolve um JPEG com no máximo 1024 px no lado maior (~750 tokens de imagem, o que `OrcamentoContexto` estima). Textos pequenos podem ficar difíceis de ler nessa resolução.
- **Como a imagem chega ao modelo:** o Ollama não aceita imagens em mensagens de ferramenta. `AnalisarTelaFerramenta` devolve um `ResultadoComImagens` (uma `str` com o atributo `.imagens`); `TrabalhadorIA` coloca a imagem numa mensagem de usuário logo em seguida, **repetindo o pedido original** (o `OrcamentoContexto` pode ter de descartar as mensagens anteriores), e as chamadas seguintes dessa troca vão **sem ferramentas** (os schemas custam ~3.800 tokens). A imagem não vai para o histórico da conversa.
- **Privacidade:** a imagem só vai para o Ollama local.
- **Ferramenta de síntese:** `precisa_de_sintese` é verdadeiro: quem responde é o modelo, depois de olhar a imagem.

---

## Dependências de plataforma

A aplicação é projetada para Windows. Vários módulos utilizam APIs, comandos ou comportamentos específicos do sistema:

- `janelas.py` — `ctypes.windll.user32`;
- `captura_tela.py` — GDI/User32/Shell32/Kernel32;
- `clipboard.py` — clipboard Win32;
- `arquivos.py` — unidades do Windows e `os.startfile`;
- `programas.py` — comando `start`;
- `sistema.py` — PowerShell e `LockWorkStation`;
- `rede.py` — `netsh` para Wi-Fi (e `ollama_processo.py`, com `tasklist`/`taskkill`): a saída é lida na página OEM do console (`CodificacaoConsole`, em `tools/console.py`), com `errors="replace"`; antes, no Windows, um SSID como "Casa da Vovó" saía com acento trocado e certos caracteres lançavam `UnicodeDecodeError`;
- `notificacoes.py` — PowerShell + WinRT Toast;
- `lembretes.py` — fallback com `MessageBoxW`;
- `janelas_proprias.py` — `ShowWindow`, `EnumWindows` e afins (instância própria da `user32`, com `argtypes`/`restype`);
- `ollama_processo.py` — `tasklist`/`taskkill`;
- `voz.py` — `MicrofoneSounddevice` usa o microfone padrão do Windows (via PortAudio, embutido no pacote `sounddevice`).

`GerenciadorProcessos` usa `psutil`, embora sua lista de processos protegidos seja especificamente orientada ao Windows.

---

## Testes presentes no pacote

A suíte tem **524 testes** em vinte arquivos (contagem estática, com os casos de `parametrize` expandidos; ver a nota de validação abaixo):

| Arquivo | Testes | Cobre |
|---|---|---|
| `tests/test_analisar_tela.py` | 44 | imagens de captura (orientação, PNG, JPEG), ocultação das janelas da Shaula, `capturar_para_modelo`, prints em PNG, ferramenta `analisar_tela` e a entrega da imagem pelo `TrabalhadorIA` |
| `tests/test_anexos.py` | 17 | estratégias de anexo (imagem, texto, PDF, vídeo) e `GerenciadorAnexos` |
| `tests/test_voz.py` | 55 | gravador, nível/volume, limpeza de transcrição, `GerenciadorVoz`, pré-aquecimento, adaptadores |
| `tests/test_lembretes.py` | 19 | persistência, restauração ao abrir, lembretes atrasados, duas janelas sem entrega dupla, cancelamento entre janelas, arquivo corrompido |
| `tests/test_ollama_chat.py` | 10 | `ChatInterrompivel` |
| `tests/test_blocos_codigo.py` | 36 | divisão de mensagens em texto e código, formatação, realce de sintaxe, botão Copiar, altura do bloco e integração com a janela |
| `tests/test_confirmacao.py` | 76 | regras e política de confirmação, registro (autorizado, negado, sem confirmador), terminal, a caixa de diálogo do Qt (sim, não, fechar, cancelar, tempo limite) e `AtrasoDesligamento` |
| `tests/test_desligar_atalho.py` | 19 | `DetectorDesligar`: pedidos claros (com tempos e cortesias), frases que não devem disparar (perguntas, negações, outros comandos) e colaboradores injetáveis |
| `tests/test_memoria_contexto.py` | 12 | `CompactadorHistorico`, `ResumidorHistorico` e o orçamento com resumo (a conversa antiga não some do contexto) |
| `tests/test_calculadora.py` | 25 | `Calculadora`: conversão de base com sinal, argumento nomeado recusado, fatorial, erros em português, determinante de valores pequenos |
| `tests/test_comandos_locais.py` | 36 | `ComandosLocais`: comando de saída tolerante a pontuação e ao nome "Shaula"; apagar conversa só com a frase exata |
| `tests/test_console.py` | 3 | `CodificacaoConsole` e seu uso em `verificar_wifi` |
| `tests/test_desligar_computador.py` | 6 | `desligar_computador`: sucesso, desligamento já agendado (1190), outros códigos, tempo negativo |
| `tests/test_pesquisa_factual.py` | 18 | `DetectorPerguntaFactual`: perguntas factuais continuam pesquisando; acompanhamentos e perguntas sobre a conversa não |
| `tests/test_registro_parametros.py` | 4 | `RegistroFerramentas`: parâmetro obrigatório conferido antes da confirmação; `KeyError` interno não vira "faltou parâmetro" |
| `tests/test_nota_anexo.py` | 19 | `NotaAnexo` e `DescricaoAnexo`: montar e separar a nota (vários arquivos, detalhes com vírgula e parênteses, nomes como "Relatório, versão final.pdf"), formato e tipo por extensão |
| `tests/test_cartao_anexo.py` | 13 | `IconeArquivo` e `CartaoAnexo` (nome, formato, detalhe, nome cortado) e a integração com a janela: só arquivo = só cartão, texto + arquivos = cartões + balão sem a nota, miniatura de imagem |
| `tests/test_correcoes.py` | 41 | persistência atômica, histórico, conversas concorrentes, cache, busca de arquivos, calculadora, `abrir_programa`, ping, detector de busca, `OrcamentoContexto`, `TrabalhadorIA` |
| `tests/test_correcoes_sistema.py` | 29 | processos, lembretes, janelas, captura de tela, voz (ociosidade e carga), registro |
| `tests/test_esforco.py` | 42 | níveis de esforço: catálogo, estado salvo em disco, repasse ao Ollama pelo `TrabalhadorIA`, comando `esforço` do terminal e o espaço mínimo de histórico em cada nível |

Os de anexos cobrem: imagem válida, redimensionamento, arquivo corrompido, limite de tamanho, leitura de texto/código, truncamento, fallback Latin-1, PDF de texto e escaneado, falta de `pymupdf`, frames de vídeo, tipo desconhecido, caminho inexistente, filtro de diálogo e `caminho_valido()`.

Os de voz não dependem de Qt, microfone nem modelo — usam fontes de áudio e motores falsos injetados: nível e volume; gravador (grava até o evento `parar`, abre/fecha a fonte, cancelamento, gravação curta ou sem voz, teto de tempo); limpeza (alucinações, grafias do nome, eco do prompt); `GerenciadorVoz` (ordem dos estados, carga do modelo **durante** a gravação, repasse de `parar`/`cancelado`/nível, cancelamento em cada fase, `VozIndisponivel`, liberação por ociosidade e seu cancelamento por novo uso); pré-carregamento; adaptadores `faster-whisper` e `sounddevice`.

Os de interrupção cobrem `ChatInterrompivel`: resposta normal, erro propagado, cancelamento com a chamada ainda bloqueada, fechamento da conexão, cancelamento antes de começar, resposta junto do pedido de parar, reuso do cliente — e dois testes com o `ollama.Client` **real** contra um servidor HTTP local lento.

`test_correcoes.py` e `test_correcoes_sistema.py` testam, entre outros, que o nível de esforço chega ao Ollama (`think`, `num_ctx`, `num_predict`), que erros não viram resposta persistida, que o laço de ferramentas para no limite de rodadas do nível sem gravar mensagens de ferramenta, que mensagens com anexo vão sem ferramentas, e as proteções da tabela acima.

O fixture que isola a pasta pessoal (`HOME`/`USERPROFILE` numa pasta temporária, para nenhum teste ler ou alterar o `~/.shaula` real) está em **`tools/conftest.py`**, não em `tests/`: pelo escopo do pytest ele não vale para a suíte de `tests/` (ver [Inconsistências](#inconsistências-do-pacote-470)). Fora do Windows, os testes que importam `interface.py` simulam `ctypes.windll`. Para rodar: `pip install pytest` no `.venv` e `python -m pytest tests` (em Linux, com `QT_QPA_PLATFORM=offscreen`).

### O que foi possível validar nesta auditoria

- todos os arquivos `.py` do pacote compilam;
- `RegistroFerramentas` contém 40 instâncias concretas e o CLI, 13; os nomes das 40 ferramentas conferem com a lista deste README e do manual;
- **foram executados fora do Windows, sem PySide6** (com um executor mínimo compatível com pytest): `test_calculadora`, `test_comandos_locais`, `test_console`, `test_desligar_atalho`, `test_desligar_computador`, `test_lembretes`, `test_memoria_contexto`, `test_nota_anexo`, `test_pesquisa_factual`, `test_registro_parametros` e `test_voz` (216 casos, todos passaram), além de 4.000 conversas aleatórias contra o `OrcamentoContexto` (sem violar nenhuma regra);
- cada nome de arquivo, classe, função e variável de ambiente citado neste README foi procurado no código; os números (níveis de esforço, limites de anexos, voz, proteções) foram conferidos contra o código;
- a contagem de 524 testes e a divisão por arquivo vêm de contagem estática (a parte de `NotaAnexo` foi executada; `test_cartao_anexo.py` e o visual dos cartões não, por precisarem de PySide6). Na auditoria da 4.40, 327 testes passaram em Linux (`QT_QPA_PLATFORM=offscreen`); **a suíte completa da 4.70 e a interface não foram executadas nesta revisão** (sem PySide6, Ollama nem Windows) e devem ser rodadas no `.venv` antes de considerar a versão fechada.

Isso **não** substitui executar a suíte no `.venv` do Windows, nem valida no Windows: captura de tela (`BitBlt`), enumeração de janelas, `LockWorkStation`, toasts, microfone real com o modelo Whisper baixado, a carga do modelo de voz em paralelo à gravação, o fechamento de várias janelas e o encerramento do Ollama.

> O instalador não instala `pytest`. Para executar a suíte em uma instalação nova, rode `pip install pytest` no ambiente virtual.

---

## Limitações conhecidas

- Desempenho do `qwen3.5:9b` pode ser muito baixo sem GPU dedicada suficiente. Em uma placa de 8 GB de VRAM (por exemplo, RTX 5060) ele cabe com o `num_ctx` dos níveis Baixo e Médio (10240 e 11264), mas com pouca folga: confira com `ollama ps` se a coluna PROCESSOR mostra `100% GPU`. Se parte do modelo for para a CPU, a velocidade cai muito; nesse caso, um modelo menor (`qwen3.5:4b`, trocando `MODEL`) ou as variáveis do Ollama `OLLAMA_FLASH_ATTENTION=1` e `OLLAMA_KV_CACHE_TYPE=q8_0` podem ajudar (recomendações gerais, não verificadas nesta auditoria).
- O prompt de sistema (~1.700 tokens) mais os 40 schemas de ferramentas (~4.100) ocupam cerca de 5.900 tokens do contexto antes de qualquer conversa, e a reserva de resposta (`num_predict`) sai do mesmo `num_ctx`. Por isso mensagens com anexo vão sem ferramentas, e históricos longos são cortados (`OrcamentoContexto`). Até a 4.65.5 o contexto dos níveis era 8192 a 16384 e o Médio deixava só ~180 tokens para a conversa: a Shaula "esquecia" o que foi dito logo na segunda mensagem, embora o texto continuasse no chat. Desde a 4.70 os níveis deixam de ~3.200 tokens (Baixo/Médio) a ~6.300 (Máx) para o histórico; como o `qwen3.5` usa atenção completa em só 8 de 32 camadas, cada token de contexto custa cerca de 32 KB de VRAM (o aumento por nível é de 64 a 96 MB). A estimativa é por caracteres (3 por token), propositalmente conservadora.
- Com raciocínio (todos os níveis menos Baixo) as respostas são melhores, porém mais lentas; o nível Baixo troca qualidade por velocidade.
- A heurística de `DetectorPerguntaFactual` é propositalmente simples e pode pesquisar demais ou deixar passar formulações incomuns.
- Vídeos são representados por no máximo 4 frames e não incluem áudio.
- Não existe estratégia de anexo de áudio.
- PDFs escaneados são limitados a 4 páginas renderizadas por anexo.
- Texto de PDF e arquivos de texto é truncado em 12.000 caracteres.
- **Voz: não foi validada com microfone real nem com o modelo Whisper baixado** — a lógica foi testada com fontes/motores falsos, e a interface em `offscreen`. A qualidade do reconhecimento em português e a latência em CPU precisam ser conferidas no Windows.
- Voz: a primeira vez exige internet (download de ~1,5 GB do modelo `medium`); sem GPU, a transcrição de uma frase leva alguns segundos *depois* que você para de falar.
- Voz: não há palavra de ativação ("Shaula, ...") nem escuta contínua — é sempre por clique ou `Ctrl+M`; também não há resposta falada (síntese de voz).
- Voz: a gravação só termina por comando seu (ou pelo teto de 10 minutos); o `faster-whisper` processa o áudio em janelas de 30 s, então ditados muito longos demoram proporcionalmente mais para transcrever.
- Interromper a resposta: a chamada ao modelo é abandonada na hora e a conexão é fechada; que o Ollama realmente pare de gerar depois disso é comportamento do servidor (esperado, mas não verificado aqui). Não há interrupção parcial: como não há streaming, não existe "resposta até a metade" para aproveitar.
- A implementação é fortemente dependente de Windows em vários serviços.
- Se a Shaula estiver fechada na hora de um lembrete, o aviso só aparece (como "atrasado") quando ela for aberta de novo.
- `analisar_tela` envia no máximo 1024 px de lado maior e um monitor por chamada; textos pequenos podem não ser legíveis. A mensagem seguinte à captura vai sem ferramentas.
- As confirmações dependem de a ação passar por `RegistroFerramentas`; `SHAULA_CONFIRMAR=0` as desliga. O `ConfirmadorQt` espera até 120 s pela resposta.
- O atalho `DetectorDesligar` só reconhece frases curtas e diretas, em português, sobre desligar o computador. Finalizar processo, fechar programa/janela e abrir executável (e qualquer pedido mais elaborado, ou com anexo) dependem de o modelo chamar a ferramenta; a confirmação continua valendo quando ele chama, mas se ele responder só em texto, nenhuma caixa aparece.
- A pesquisa automática ignora mensagens que dependem da conversa, mas ainda é uma heurística: uma pergunta factual que contenha, por exemplo, `isso` ou `lembra` não dispara pesquisa (o modelo ainda pode pesquisar por conta própria).
- Num PDF longo só o começo é lido (12.000 caracteres, cerca de 6 páginas de um livro): o cartão e o aviso dizem até onde.
- O resumo do histórico descartado é mecânico (começo de cada fala, sem usar o modelo): serve para a Shaula retomar o assunto, mas perde detalhes.
- Voz: o modelo é recarregado quando o microfone é usado depois de 3 minutos de inatividade (a carga acontece durante a gravação, mas a transcrição só termina quando ela acaba).
- O realce de sintaxe é leve (expressões regulares por linha): serve para leitura e não é um analisador. Não há quebra automática de linha nos blocos de código, e o botão Copiar copia sempre o bloco inteiro (para copiar um trecho, selecione-o com o mouse e use `Ctrl+C`).
- Nas chamadas `ctypes` de `janelas.py` e `sistema.py`, os handles são passados sem `argtypes`/`restype`. Funciona porque handles de janela cabem em 32 bits, mas é frágil.

---

## Inconsistências do pacote 4.70

Ainda presentes (nenhuma afeta o uso normal da Shaula, mas convém corrigir):

1. **Não existe `tests/conftest.py`.** O fixture que isola a pasta pessoal nos testes (`HOME`/`USERPROFILE` numa pasta temporária) está em `tools/conftest.py`. Pelo escopo do pytest, ele só vale para testes dentro de `tools/`: **os testes de `tests/` não são isolados** e podem ler o `~/.shaula` real (conversas, cache, esforço e, principalmente, lembretes pendentes, que um teste poderia entregar de verdade). O certo é mover o arquivo para `tests/conftest.py`.
2. **Cópias antigas dentro de `tools/`:** `tools/interface.py` (versão antiga de `interface.py`, com raciocínio fixo desligado e os textos antigos de voz; nada a importa) e `tools/test_correcoes.py`, `tools/test_correcoes_sistema.py` e `tools/test_esforco.py` (duplicatas de `tests/`, sem os testes novos). Podem ser apagadas para não serem abertas ou executadas por engano.
3. **`requests` no instalador.** O instalador instala e verifica `requests`, mas nenhum módulo do pacote o importa (a pesquisa usa `urllib`).
4. **`pytest` ausente do instalador.** A suíte existe, mas o instalador não instala o runner de testes (`pip install pytest` no `.venv`).
5. **Apagar a conversa não pede confirmação.** `excluir conversa`, `esquecer tudo` e semelhantes apagam o histórico do disco na hora. Por isso exigem a frase exata, mas um pedido de confirmação (a mesma caixa das ações sensíveis) seria mais seguro.
6. **Ferramentas não são interrompíveis.** O botão ■ cancela a chamada ao modelo, mas não uma ferramenta em andamento (`buscar_arquivo` em "todos" os discos pode levar minutos; `bloquear_tela` com atraso dorme na thread). Fechar a janela espera só 3 s pela thread da IA; se ela ainda estiver presa numa ferramenta, o Qt pode abortar com "QThread: Destroyed while thread is still running".
7. **`ConfirmadorQt` não libera a caixa depois de usada:** cada `QMessageBox` fica como filha da janela até ela fechar (um vazamento pequeno por confirmação).

---

## UML e casos de uso

A arquitetura correspondente a este README está em:

```text
Documentação/Shaula_UML_Completo_4.70.md
Documentação/Shaula_Casos_de_Uso_4.70.md
```

O UML representa as classes e relações realmente presentes na versão 4.70, incluindo múltiplas conversas, os 40 tools registrados, serviços, Strategy de pesquisa, Strategy de anexos, voz, interrupção da resposta, controle de contexto (com compactação e resumo do histórico), confirmação (com o atalho de desligar) e persistência atômica. O documento de casos de uso mostra o que o usuário consegue fazer (inclusive falar comandos e interromper a resposta) e quais sistemas externos participam.
