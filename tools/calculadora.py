import ast
import math
import operator
import numpy as np


class Calculadora:
    """
    Serviço de cálculo: expressões matemáticas, operações de
    matriz e conversão entre bases numéricas.

    Não guarda nenhum estado entre chamadas — é uma classe por
    organização (agrupa lógica relacionada com um "dono" claro),
    não porque precise de instância. As classes Ferramenta
    correspondentes (ver ferramentas_calculo.py) delegam pra cá.
    """

    OPERADORES = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.Pow: operator.pow,
        ast.Mod: operator.mod,
        ast.USub: operator.neg,
        ast.UAdd: operator.pos,

        # Em Python, "^" é XOR de bits — mas quem digita "5^10"
        # numa calculadora quase sempre quer dizer "5 elevado a
        # 10", não bits. Tratamos "^" como potenciação aqui para
        # bater com a expectativa comum, já que "**" continua
        # funcionando normalmente para quem usa a notação Python.
        ast.BitXor: operator.pow,
    }

    FUNCOES = {
        "sqrt": math.sqrt,
        "sin": math.sin,
        "cos": math.cos,
        "tan": math.tan,
        "log": math.log,
        "log10": math.log10,
        "log2": math.log2,
        "exp": math.exp,
        "factorial": math.factorial,
        "ceil": math.ceil,
        "floor": math.floor,
        "fabs": math.fabs,
    }

    CONSTANTES = {
        "pi": math.pi,
        "e": math.e,
        "tau": math.tau,
    }

    # Limites de segurança. Sem eles, uma expressão como
    # 7**(10**8) ou factorial(10**7) prendia a thread da IA por
    # minutos (o Python calcula o inteiro gigante inteiro antes
    # de qualquer verificação), e o botão de parar não consegue
    # interromper uma ferramenta em execução. O Python também
    # se recusa a converter para texto inteiros com mais de
    # 4300 dígitos (~14 mil bits), então resultados maiores que
    # isso não poderiam ser mostrados de qualquer forma.
    LIMITE_BITS_RESULTADO = 20_000
    LIMITE_FATORIAL = 1_500

    # Mensagens que o Python dá em inglês, traduzidas para o usuário.
    MENSAGENS_DE_ERRO = {
        "math domain error": (
            "essa operação não existe para esse valor "
            "(fora do domínio da função)."
        ),
        "not defined for negative": (
            "o fatorial não existe para números negativos."
        ),
        "only accepts non-negative": (
            "o fatorial não existe para números negativos."
        ),
    }

    # --------------------------------------------------------
    # EXPRESSÕES MATEMÁTICAS
    # --------------------------------------------------------

    def _avaliar_no(self, no):

        if isinstance(no, ast.Constant):

            if isinstance(no.value, (int, float)):
                return no.value

            raise ValueError("Valor inválido.")

        if isinstance(no, ast.BinOp):

            operador = self.OPERADORES.get(type(no.op))

            if operador is None:
                raise ValueError("Operador não permitido.")

            esquerda = self._avaliar_no(no.left)
            direita = self._avaliar_no(no.right)

            if isinstance(no.op, (ast.Pow, ast.BitXor)):
                self._validar_potencia(esquerda, direita)

            return operador(esquerda, direita)

        if isinstance(no, ast.UnaryOp):

            operador = self.OPERADORES.get(type(no.op))

            if operador is None:
                raise ValueError("Operador não permitido.")

            valor = self._avaliar_no(no.operand)

            return operador(valor)

        if isinstance(no, ast.Name):

            if no.id in self.CONSTANTES:
                return self.CONSTANTES[no.id]

            raise ValueError(
                f"Constante desconhecida: {no.id}"
            )

        if isinstance(no, ast.Call):

            if not isinstance(no.func, ast.Name):
                raise ValueError("Função inválida.")

            nome = no.func.id

            if nome not in self.FUNCOES:
                raise ValueError(
                    f"Função não permitida: {nome}"
                )

            # Argumentos nomeados eram ignorados em silêncio: log(8, base=2)
            # virava log(8) e devolvia uma resposta errada.
            if no.keywords:
                raise ValueError(
                    "use só argumentos por posição, "
                    "por exemplo log(8, 2)."
                )

            argumentos = [
                self._avaliar_no(argumento)
                for argumento in no.args
            ]

            # factorial(5.0) é aceito quando o valor é inteiro.
            if (
                nome == "factorial"
                and argumentos
                and isinstance(argumentos[0], float)
                and argumentos[0].is_integer()
            ):
                argumentos[0] = int(argumentos[0])

            if (
                nome == "factorial"
                and argumentos
                and isinstance(argumentos[0], int)
                and argumentos[0] > self.LIMITE_FATORIAL
            ):
                raise OverflowError

            return self.FUNCOES[nome](*argumentos)

        raise ValueError(
            "Expressão matemática inválida."
        )

    def _validar_potencia(self, base, expoente):
        """
        Recusa, ANTES de calcular, potências inteiras cujo
        resultado seria gigante. Potências com float já falham
        sozinhas com OverflowError.
        """

        if not (
            isinstance(base, int)
            and isinstance(expoente, int)
        ):
            return

        if expoente <= 0 or abs(base) <= 1:
            return

        bits_estimados = expoente * math.log2(abs(base))

        if bits_estimados > self.LIMITE_BITS_RESULTADO:
            raise OverflowError

    def calcular(self, expressao):

        expressao = expressao.strip()

        if not expressao:
            return (
                "Nenhuma expressão matemática "
                "foi fornecida."
            )

        try:

            arvore = ast.parse(
                expressao,
                mode="eval"
            )

            resultado = self._avaliar_no(
                arvore.body
            )

            if isinstance(resultado, complex):

                return (
                    "O resultado não é um número real."
                )

            if isinstance(resultado, float):

                if not math.isfinite(resultado):
                    raise OverflowError

                resultado = round(
                    resultado,
                    12
                )

            return f"Resultado: {resultado}"

        except ZeroDivisionError:

            return "Não é possível dividir por zero."

        except ValueError as erro:

            # O limite de 4300 dígitos do Python para converter
            # inteiros em texto chega aqui como ValueError com
            # uma mensagem em inglês — traduzimos.
            if "digits" in str(erro).lower():

                return (
                    "O resultado é grande demais "
                    "para ser mostrado."
                )

            for trecho, traducao in self.MENSAGENS_DE_ERRO.items():

                if trecho in str(erro).lower():

                    return f"Não consegui calcular: {traducao}"

            return f"Não consegui calcular: {erro}"

        except OverflowError:

            return (
                "O resultado é grande demais "
                "para ser calculado."
            )

        except Exception:

            return (
                f"Não consegui interpretar "
                f"a expressão: {expressao}"
            )

    # --------------------------------------------------------
    # MATRIZES
    # --------------------------------------------------------

    def _criar_matriz(self, dados):

        try:

            matriz = np.array(
                dados,
                dtype=float
            )

            if matriz.ndim != 2:
                return None

            return matriz

        except Exception:

            return None

    def _formatar_matriz(self, matriz):
        """
        Formata a matriz de maneira simples e legível.

        Exemplo:

        [1 2 3]
        [3 7 8]
        """

        linhas = []

        for linha in matriz:

            valores = []

            for valor in linha:

                valor = float(valor)

                if valor.is_integer():

                    valores.append(
                        str(int(valor))
                    )

                else:

                    valores.append(
                        f"{valor:.6g}"
                    )

            linhas.append(
                "[" + " ".join(valores) + "]"
            )

        return "\n".join(linhas)

    def matriz_soma(self, a, b):

        a = self._criar_matriz(a)
        b = self._criar_matriz(b)

        if a is None or b is None:
            return "Matriz inválida."

        if a.shape != b.shape:

            return (
                "As matrizes precisam ter "
                "o mesmo tamanho."
            )

        return self._formatar_matriz(a + b)

    def matriz_subtracao(self, a, b):

        a = self._criar_matriz(a)
        b = self._criar_matriz(b)

        if a is None or b is None:
            return "Matriz inválida."

        if a.shape != b.shape:

            return (
                "As matrizes precisam ter "
                "o mesmo tamanho."
            )

        return self._formatar_matriz(a - b)

    def matriz_multiplicacao(self, a, b):

        a = self._criar_matriz(a)
        b = self._criar_matriz(b)

        if a is None or b is None:
            return "Matriz inválida."

        if a.shape[1] != b.shape[0]:

            return (
                "Não é possível multiplicar essas "
                "matrizes. O número de colunas da "
                "primeira deve ser igual ao número "
                "de linhas da segunda."
            )

        return self._formatar_matriz(a @ b)

    def matriz_escalar(self, a, escalar):

        a = self._criar_matriz(a)

        if a is None:
            return "Matriz inválida."

        return self._formatar_matriz(
            a * escalar
        )

    def matriz_transposta(self, a):

        a = self._criar_matriz(a)

        if a is None:
            return "Matriz inválida."

        return self._formatar_matriz(
            a.T
        )

    def matriz_determinante(self, a):

        a = self._criar_matriz(a)

        if a is None:
            return "Matriz inválida."

        if a.shape[0] != a.shape[1]:

            return (
                "O determinante só existe "
                "para matrizes quadradas."
            )

        resultado = np.linalg.det(a)

        # "Zero" é relativo à escala da matriz: um limite fixo de 1e-12
        # zerava o determinante de matrizes legítimas de valores
        # pequenos (como [[1e-7, 0], [0, 1e-7]], que vale 1e-14).
        escala = float(np.prod(np.linalg.norm(a, axis=1)))

        if escala == 0 or abs(resultado) < 1e-12 * escala:
            resultado = 0

        if float(resultado).is_integer():

            return str(int(resultado))

        return f"{resultado:.12g}"

    def matriz_inversa(self, a):

        a = self._criar_matriz(a)

        if a is None:
            return "Matriz inválida."

        if a.shape[0] != a.shape[1]:

            return (
                "A matriz precisa ser quadrada."
            )

        try:

            resultado = np.linalg.inv(a)

            return self._formatar_matriz(
                resultado
            )

        except np.linalg.LinAlgError:

            return (
                "Essa matriz não possui inversa."
            )

    def matriz_potencia(self, a, potencia):

        a = self._criar_matriz(a)

        if a is None:
            return "Matriz inválida."

        if a.shape[0] != a.shape[1]:

            return (
                "A matriz precisa ser quadrada."
            )

        try:

            resultado = np.linalg.matrix_power(
                a,
                int(potencia)
            )

            return self._formatar_matriz(
                resultado
            )

        except Exception as erro:

            return (
                f"Não consegui calcular "
                f"a potência: {erro}"
            )

    # --------------------------------------------------------
    # CONVERSÃO DE BASES NUMÉRICAS
    # --------------------------------------------------------

    def converter_base(
        self,
        valor,
        base_origem,
        base_destino
    ):

        try:

            base_origem = int(base_origem)
            base_destino = int(base_destino)

            bases_permitidas = [2, 8, 10, 16]

            if base_origem not in bases_permitidas:

                return (
                    "A base de origem deve ser "
                    "2, 8, 10 ou 16."
                )

            if base_destino not in bases_permitidas:

                return (
                    "A base de destino deve ser "
                    "2, 8, 10 ou 16."
                )

            valor = str(
                valor
            ).strip().upper()

            if not valor:

                return (
                    "Nenhum número foi fornecido."
                )

            # O sinal é tratado à parte: bin(-5)[2:] devolvia "b101" e
            # hex(-255)[2:] devolvia "XFF" em vez de -101 e -FF.
            sinal = ""

            if valor[:1] in ("-", "+"):

                sinal = "-" if valor[0] == "-" else ""

                valor = valor[1:]

            if (
                base_origem == 2
                and valor.startswith("0B")
            ):

                valor = valor[2:]

            elif (
                base_origem == 8
                and valor.startswith("0O")
            ):

                valor = valor[2:]

            elif (
                base_origem == 16
                and valor.startswith("0X")
            ):

                valor = valor[2:]

            numero_decimal = int(
                valor,
                base_origem
            )

            if base_destino == 2:

                resultado = bin(
                    numero_decimal
                )[2:]

            elif base_destino == 8:

                resultado = oct(
                    numero_decimal
                )[2:]

            elif base_destino == 10:

                resultado = str(
                    numero_decimal
                )

            elif base_destino == 16:

                resultado = hex(
                    numero_decimal
                )[2:].upper()

            else:

                return "Base de destino inválida."

            if numero_decimal == 0:
                sinal = ""

            return (
                f"{sinal}{valor} (base {base_origem}) = "
                f"{sinal}{resultado} (base {base_destino})"
            )

        except ValueError:

            return (
                f"'{valor}' não é um número válido "
                f"na base {base_origem}."
            )

        except Exception as erro:

            return (
                f"Erro na conversão: {erro}"
            )
