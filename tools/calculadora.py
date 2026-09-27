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

            argumentos = [
                self._avaliar_no(argumento)
                for argumento in no.args
            ]

            return self.FUNCOES[nome](*argumentos)

        raise ValueError(
            "Expressão matemática inválida."
        )

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

            if isinstance(resultado, float):

                if math.isfinite(resultado):
                    resultado = round(
                        resultado,
                        12
                    )

            return f"Resultado: {resultado}"

        except ZeroDivisionError:

            return "Não é possível dividir por zero."

        except ValueError as erro:

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

        if abs(resultado) < 1e-12:
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

            return (
                f"{valor} (base {base_origem}) = "
                f"{resultado} (base {base_destino})"
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
