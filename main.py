from ollama import chat

from tools.confirmacao import ConfirmadorTerminal
from tools.contexto import OrcamentoContexto
from tools.esforco import CatalogoEsforco, EstadoEsforco
from tools.registro import RegistroFerramentas


MODEL = "qwen3.5:9b"

# Raciocínio (think), tamanho do contexto (num_ctx), teto de tokens por
# resposta e máximo de rodadas de ferramentas dependem do NÍVEL DE
# ESFORÇO (Baixo, Médio, Alto, Extra, Máx), definido em
# tools/esforco.py e compartilhado com a interface gráfica: a escolha
# fica salva em ~/.shaula/configuracoes.json. Aqui, o comando
# `esforço <nível>` troca o nível.


# ============================================================
# FERRAMENTAS DISPONÍVEIS NESTA VERSÃO (linha de comando)
# ============================================================
#
# O main.py sempre teve acesso a um subconjunto menor de
# ferramentas que a versão com interface gráfica (sem internet,
# sem controle de janelas/monitores, sem informações de
# sistema) — preservamos esse mesmo escopo aqui, restringindo o
# RegistroFerramentas compartilhado.

FERRAMENTAS_DESTA_VERSAO = {
    "abrir_programa",
    "buscar_arquivo",
    "abrir_arquivo",
    "calcular",
    "matriz_soma",
    "matriz_subtracao",
    "matriz_multiplicacao",
    "matriz_escalar",
    "matriz_transposta",
    "matriz_determinante",
    "matriz_inversa",
    "matriz_potencia",
    "converter_base",
}


system_message = {
    "role": "system",
    "content": """
Você é Shaula, um assistente de computador local.

Você conversa normalmente com o usuário e pode executar
ações no computador usando as ferramentas disponíveis.

============================================================
REGRAS IMPORTANTES
============================================================

O Python é responsável por realizar cálculos.

O Qwen é responsável por interpretar o pedido do usuário,
escolher a ferramenta correta e explicar o resultado.

Nunca invente resultados de cálculos.

Nunca invente caminhos de arquivos.

Use sempre as ferramentas quando elas forem apropriadas.

============================================================
ARQUIVOS
============================================================

A Shaula consegue procurar arquivos em diferentes
unidades do computador.

Use buscar_arquivo quando o usuário quiser localizar um arquivo.

Se o usuário especificar uma unidade:

"C:"
"D:"
"E:"
"F:"
"G:"

procure somente nessa unidade.

Se o usuário disser:

"todos os discos"
"todas as unidades"
"em todos os discos"

use:

unidade = "todos"

Se o usuário não especificar uma unidade, a busca padrão
é feita no perfil do usuário.

============================================================
ABRIR ARQUIVOS
============================================================

Use abrir_arquivo quando o usuário quiser abrir um arquivo.

A ferramenta utiliza o Windows para abrir o arquivo com
o aplicativo associado ao formato.

Ela pode abrir, por exemplo:

- PDF
- EXE
- DOC
- DOCX
- XLS
- XLSX
- TXT
- JPG
- JPEG
- PNG
- MP3
- MP4
- arquivos de atalho
- outros formatos reconhecidos pelo Windows

Exemplo:

"Abra C:\\Users\\gabin\\Documents\\teste.pdf"

Use:

abrir_arquivo(
    caminho="C:\\Users\\gabin\\Documents\\teste.pdf"
)

NUNCA invente um caminho.

============================================================
BUSCAR E DEPOIS ABRIR
============================================================

A Shaula pode executar duas ações em sequência.

Exemplo:

Usuário:

"Procure Carteirinha Nova Plano de Saúde no D:"

Primeiro use:

buscar_arquivo(
    nome="Carteirinha Nova Plano de Saúde",
    unidade="D:"
)

Depois de receber o resultado, se o usuário disser:

"Abra esse arquivo"

use o caminho exato retornado pela ferramenta.

Não invente ou altere o caminho.

Se houver vários resultados, peça ao usuário para indicar
qual deseja abrir, a menos que exista um resultado claramente
correspondente.

============================================================
PROGRAMAS
============================================================

Use abrir_programa quando o usuário pedir para abrir um
programa pelo nome.

Exemplos:

"Abra o Firefox"

"Abra o Discord"

"Abra o Steam"

Não use abrir_programa para arquivos comuns como PDF,
DOCX ou JPG.

Para esses casos use abrir_arquivo.

============================================================
MATEMÁTICA
============================================================

Use calcular para contas matemáticas.

Exemplo:

"Quanto é 25 vezes 18?"

Use:

calcular("25 * 18")

Nunca faça o cálculo manualmente quando a ferramenta
calcular puder realizá-lo.

============================================================
MATRIZES
============================================================

Use as ferramentas de matriz para:

- soma;
- subtração;
- multiplicação;
- multiplicação por escalar;
- transposta;
- determinante;
- inversa;
- potência.

O usuário pode escrever matrizes naturalmente.

Exemplo:

[1 2 3]
[3 7 8]

Interprete como:

[[1, 2, 3],
 [3, 7, 8]]

============================================================
FORMATAÇÃO DE MATRIZES
============================================================

Quando mostrar uma matriz para o usuário, use:

[1 2 3]
[3 7 8]

Não use LaTeX.

Não escreva:

$$
\\begin{bmatrix}
1 & 2 & 3 \\
3 & 7 & 8
\\end{bmatrix}
$$

Não mostre a representação Python:

[[1, 2, 3], [3, 7, 8]]

Cada linha da matriz deve ficar em uma linha separada.

============================================================
CONVERSÃO DE BASES
============================================================

Use converter_base para conversões entre:

2  = binário
8  = octal
10 = decimal
16 = hexadecimal

Exemplo:

"Converta 255 para binário"

valor = "255"
base_origem = 10
base_destino = 2

Sempre use a ferramenta para realizar a conversão.

============================================================
IDIOMAS
============================================================

A Shaula pode conversar em português, inglês ou francês.

Responda no mesmo idioma utilizado pelo usuário.

Se o usuário misturar idiomas, use o idioma predominante
na mensagem atual.

Não traduza automaticamente a pergunta.

============================================================
COMPORTAMENTO
============================================================

Use o histórico da conversa.

Se uma ferramenta retornar um caminho de arquivo,
resultado ou outra informação importante, use essa
informação nas próximas ações.

Você pode executar várias ferramentas em sequência
quando necessário.

Depois de receber o resultado de uma ferramenta,
responda naturalmente ao usuário.

Se uma ferramenta já realizou uma ação, não diga que
"tentará" realizá-la. Informe o resultado real retornado
pela ferramenta.
"""
}


# ============================================================
# ASSISTENTE DE TERMINAL
# ============================================================

class AssistenteTerminal:
    """
    Versão de linha de comando da Shaula.

    Antes, este arquivo era um script: tudo rodava no nível do
    módulo (um simples `import main` já abria o laço de input) e
    o estado vivia em variáveis soltas. Agora o estado (histórico,
    registro de ferramentas, orçamento de contexto) pertence à
    classe, e nada executa até chamar `executar()`.
    """

    COMANDOS_SAIDA = frozenset({"sair"})

    COMANDOS_ESFORCO = frozenset({"esforço", "esforco", "/esforço", "/esforco"})

    def __init__(
        self,
        modelo=MODEL,
        estado_esforco=None,
        mensagem_sistema=None,
        ferramentas_permitidas=None,
        funcao_chat=chat,
        entrada=input,
        saida=print,
        confirmador=None
    ):

        self.modelo = modelo

        self.estado_esforco = estado_esforco or EstadoEsforco()

        self._chat = funcao_chat

        self._entrada = entrada

        self._saida = saida

        # Ações que exigem confirmação (ex.: abrir um .exe) perguntam
        # no terminal, com [s/N].
        self.registro = RegistroFerramentas(
            ferramentas_permitidas=(
                ferramentas_permitidas
                if ferramentas_permitidas is not None
                else FERRAMENTAS_DESTA_VERSAO
            ),
            confirmador=confirmador or ConfirmadorTerminal(entrada, saida)
        )

        self.mensagens = [
            mensagem_sistema
            if mensagem_sistema is not None
            else system_message
        ]

    # --------------------------------------------------------
    # LAÇO PRINCIPAL
    # --------------------------------------------------------

    def executar(self):
        """Laço de conversa. Termina com 'sair' ou Ctrl+C/Ctrl+D."""

        self._mostrar_cabecalho()

        while True:

            try:

                texto = self._entrada("Você: ")

            except (EOFError, KeyboardInterrupt):

                self._saida("\nEncerrando Shaula...")

                break

            if texto.lower().strip() in self.COMANDOS_SAIDA:

                self._saida("Encerrando Shaula...")

                break

            if not texto.strip():

                continue

            if self._tratar_comando_esforco(texto):

                continue

            self.responder(texto)

    def _tratar_comando_esforco(self, texto):
        """
        `esforço` mostra o nível atual e os disponíveis;
        `esforço alto` troca o nível. Devolve True se a linha era
        um comando desse tipo (e portanto não vai ao modelo).
        """

        partes = texto.strip().split(maxsplit=1)

        if partes[0].lower() not in self.COMANDOS_ESFORCO:

            return False

        if len(partes) == 2:

            perfil = self.estado_esforco.definir(partes[1])

            if perfil is None:

                self._saida(
                    f"Nível desconhecido: '{partes[1]}'. Use um de: "
                    + ", ".join(p.nome for p in CatalogoEsforco.listar())
                    + ".\n"
                )

                return True

            self._saida(
                f"Esforço definido para {perfil.nome}: {perfil.resumo}."
            )

            if perfil.aviso:
                self._saida(f"Atenção: {perfil.aviso}")

            self._saida("")

            return True

        atual = self.estado_esforco.perfil

        self._saida(f"Esforço atual: {atual.nome} ({atual.resumo}).")

        self._saida(
            "Níveis: "
            + ", ".join(p.nome for p in CatalogoEsforco.listar())
            + ". Troque com: esforço <nível>\n"
        )

        return True

    def responder(self, texto):
        """
        Processa UMA mensagem do usuário: chama o modelo,
        executa as ferramentas que ele pedir e imprime a
        resposta final. Devolve o texto final (ou None se falhou).
        """

        self.mensagens.append({
            "role": "user",
            "content": texto
        })

        # Foto do nível no momento da pergunta.
        perfil = self.estado_esforco.perfil

        orcamento = OrcamentoContexto(
            num_ctx=perfil.num_ctx,
            reserva_resposta=perfil.num_predict
        )

        opcoes = {
            "num_ctx": perfil.num_ctx,
            "num_predict": perfil.num_predict
        }

        schemas = self.registro.schemas_openai()

        tokens_schemas = orcamento.estimar_schemas(schemas)

        for _rodada in range(perfil.max_rodadas):

            try:

                resposta = self._chat(
                    model=self.modelo,
                    messages=orcamento.ajustar(
                        self.mensagens,
                        tokens_ferramentas=tokens_schemas
                    ),
                    tools=schemas,
                    options=opcoes,
                    think=perfil.pensar
                )

            except Exception as erro:

                # Sem isso, o Ollama desligado derrubava o
                # programa inteiro com um traceback.
                self._saida(
                    "\nErro ao comunicar com o Ollama: "
                    f"{erro}\n"
                )

                return None

            self.mensagens.append(
                resposta.message
            )

            if not resposta.message.tool_calls:

                conteudo = resposta.message.content or ""

                self._saida(
                    f"\nShaula: {conteudo}\n"
                )

                return conteudo

            for chamada in resposta.message.tool_calls:

                self._executar_chamada(chamada)

        self._saida(
            "\nA Shaula chamou ferramentas "
            f"{perfil.max_rodadas} vezes seguidas sem "
            "chegar a uma resposta e parou. Reformule o pedido.\n"
        )

        return None

    # --------------------------------------------------------
    # FERRAMENTAS
    # --------------------------------------------------------

    def _executar_chamada(self, chamada):

        nome = chamada.function.name

        argumentos = chamada.function.arguments

        self._saida(
            f"\n[Executando: {nome}({argumentos})]"
        )

        try:

            resultado = self.registro.executar(
                nome,
                argumentos
            )

        except Exception as erro:

            resultado = f"Erro ao executar {nome}: {erro}"

        self._saida(
            f"[Resultado: {resultado}]\n"
        )

        self.mensagens.append({
            "role": "tool",
            "tool_name": nome,
            "content": str(resultado)
        })

    # --------------------------------------------------------
    # APRESENTAÇÃO
    # --------------------------------------------------------

    def _mostrar_cabecalho(self):

        self._saida("=" * 50)
        self._saida("          Shaula 4.75 (terminal)")
        self._saida("=" * 50)
        self._saida(
            f"Esforço: {self.estado_esforco.perfil.nome} "
            "(digite 'esforço' para ver ou trocar)."
        )
        self._saida("Digite 'sair' para encerrar.\n")


def main():

    AssistenteTerminal().executar()


if __name__ == "__main__":

    main()
