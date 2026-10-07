from ollama import chat

from tools.registro import RegistroFerramentas


MODEL = "qwen3.5:9b"

# Sem isso, o Ollama usa o num_ctx padrão da instalação —
# menor do que o histórico de conversa + schemas das
# ferramentas costuma precisar. 8192 é o valor que já vínhamos
# usando com o qwen3:8b; a Qwen3.5 é nativamente multimodal
# (texto e imagem no mesmo modelo, sem encoder separado), mas
# ainda vale reconferir com `ollama ps` depois da troca se
# continua cabendo 100% na GPU nesse valor, ou se precisa
# baixar (ex.: 6144) pra não estourar a VRAM.
OPTIONS = {"num_ctx": 8192}


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
# INICIALIZAÇÃO
# ============================================================

print("=" * 50)
print("                 Shaula v3.50")
print("=" * 50)
print("Digite 'sair' para encerrar.\n")

registro = RegistroFerramentas(
    ferramentas_permitidas=FERRAMENTAS_DESTA_VERSAO
)

mensagens = [
    system_message
]


# ============================================================
# LOOP PRINCIPAL
# ============================================================

while True:

    mensagem = input("Você: ")

    if mensagem.lower().strip() == "sair":
        print("Encerrando Shaula...")
        break

    mensagens.append({
        "role": "user",
        "content": mensagem
    })

    # --------------------------------------------------------
    # Executar ferramentas enquanto o Qwen solicitar
    # --------------------------------------------------------

    while True:

        resposta = chat(
            model=MODEL,
            messages=mensagens,
            tools=registro.schemas_openai(),
            options=OPTIONS
        )

        mensagens.append(
            resposta.message
        )

        # ----------------------------------------------------
        # Sem ferramenta = resposta normal
        # ----------------------------------------------------

        if not resposta.message.tool_calls:

            print(
                f"\nShaula: "
                f"{resposta.message.content}\n"
            )

            break

        # ----------------------------------------------------
        # Executar ferramentas
        # ----------------------------------------------------

        for chamada in resposta.message.tool_calls:

            nome = chamada.function.name
            argumentos = chamada.function.arguments

            print(
                f"\n[Executando: "
                f"{nome}({argumentos})]"
            )

            try:

                resultado = registro.executar(
                    nome,
                    argumentos
                )

            except Exception as erro:

                resultado = (
                    f"Erro ao executar "
                    f"{nome}: {erro}"
                )

            print(
                f"[Resultado: {resultado}]\n"
            )

            mensagens.append({
                "role": "tool",
                "tool_name": nome,
                "content": str(resultado)
            })
