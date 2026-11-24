from .ferramenta import Ferramenta
from .calculadora import Calculadora


class CalcularFerramenta(Ferramenta):

    def __init__(self, calculadora=None):

        self._calculadora = calculadora or Calculadora()

    @property
    def nome(self):
        return "calcular"

    @property
    def descricao(self):
        return "Executa cálculos matemáticos."

    @property
    def parametros(self):
        return {
            "type": "object",
            "properties": {
                "expressao": {"type": "string"}
            },
            "required": ["expressao"]
        }

    def executar(self, argumentos):

        return self._calculadora.calcular(
            argumentos["expressao"]
        )


class MatrizSomaFerramenta(Ferramenta):

    def __init__(self, calculadora=None):

        self._calculadora = calculadora or Calculadora()

    @property
    def nome(self):
        return "matriz_soma"

    @property
    def descricao(self):
        return "Soma duas matrizes elemento por elemento."

    @property
    def parametros(self):
        return {
            "type": "object",
            "properties": {
                "a": {"type": "array"},
                "b": {"type": "array"}
            },
            "required": ["a", "b"]
        }

    def executar(self, argumentos):

        return self._calculadora.matriz_soma(
            argumentos["a"],
            argumentos["b"]
        )


class MatrizSubtracaoFerramenta(Ferramenta):

    def __init__(self, calculadora=None):

        self._calculadora = calculadora or Calculadora()

    @property
    def nome(self):
        return "matriz_subtracao"

    @property
    def descricao(self):
        return "Subtrai duas matrizes elemento por elemento."

    @property
    def parametros(self):
        return {
            "type": "object",
            "properties": {
                "a": {"type": "array"},
                "b": {"type": "array"}
            },
            "required": ["a", "b"]
        }

    def executar(self, argumentos):

        return self._calculadora.matriz_subtracao(
            argumentos["a"],
            argumentos["b"]
        )


class MatrizMultiplicacaoFerramenta(Ferramenta):

    def __init__(self, calculadora=None):

        self._calculadora = calculadora or Calculadora()

    @property
    def nome(self):
        return "matriz_multiplicacao"

    @property
    def descricao(self):
        return (
            "Multiplica duas matrizes usando "
            "multiplicação matricial convencional."
        )

    @property
    def parametros(self):
        return {
            "type": "object",
            "properties": {
                "a": {"type": "array"},
                "b": {"type": "array"}
            },
            "required": ["a", "b"]
        }

    def executar(self, argumentos):

        return self._calculadora.matriz_multiplicacao(
            argumentos["a"],
            argumentos["b"]
        )


class MatrizEscalarFerramenta(Ferramenta):

    def __init__(self, calculadora=None):

        self._calculadora = calculadora or Calculadora()

    @property
    def nome(self):
        return "matriz_escalar"

    @property
    def descricao(self):
        return "Multiplica uma matriz por um número."

    @property
    def parametros(self):
        return {
            "type": "object",
            "properties": {
                "a": {"type": "array"},
                "escalar": {"type": "number"}
            },
            "required": ["a", "escalar"]
        }

    def executar(self, argumentos):

        return self._calculadora.matriz_escalar(
            argumentos["a"],
            argumentos["escalar"]
        )


class MatrizTranspostaFerramenta(Ferramenta):

    def __init__(self, calculadora=None):

        self._calculadora = calculadora or Calculadora()

    @property
    def nome(self):
        return "matriz_transposta"

    @property
    def descricao(self):
        return "Calcula a transposta de uma matriz."

    @property
    def parametros(self):
        return {
            "type": "object",
            "properties": {
                "a": {"type": "array"}
            },
            "required": ["a"]
        }

    def executar(self, argumentos):

        return self._calculadora.matriz_transposta(
            argumentos["a"]
        )


class MatrizDeterminanteFerramenta(Ferramenta):

    def __init__(self, calculadora=None):

        self._calculadora = calculadora or Calculadora()

    @property
    def nome(self):
        return "matriz_determinante"

    @property
    def descricao(self):
        return "Calcula o determinante de uma matriz."

    @property
    def parametros(self):
        return {
            "type": "object",
            "properties": {
                "a": {"type": "array"}
            },
            "required": ["a"]
        }

    def executar(self, argumentos):

        return self._calculadora.matriz_determinante(
            argumentos["a"]
        )


class MatrizInversaFerramenta(Ferramenta):

    def __init__(self, calculadora=None):

        self._calculadora = calculadora or Calculadora()

    @property
    def nome(self):
        return "matriz_inversa"

    @property
    def descricao(self):
        return "Calcula a matriz inversa."

    @property
    def parametros(self):
        return {
            "type": "object",
            "properties": {
                "a": {"type": "array"}
            },
            "required": ["a"]
        }

    def executar(self, argumentos):

        return self._calculadora.matriz_inversa(
            argumentos["a"]
        )


class MatrizPotenciaFerramenta(Ferramenta):

    def __init__(self, calculadora=None):

        self._calculadora = calculadora or Calculadora()

    @property
    def nome(self):
        return "matriz_potencia"

    @property
    def descricao(self):
        return "Calcula uma potência de matriz."

    @property
    def parametros(self):
        return {
            "type": "object",
            "properties": {
                "a": {"type": "array"},
                "potencia": {"type": "integer"}
            },
            "required": ["a", "potencia"]
        }

    def executar(self, argumentos):

        return self._calculadora.matriz_potencia(
            argumentos["a"],
            argumentos["potencia"]
        )


class ConverterBaseFerramenta(Ferramenta):

    def __init__(self, calculadora=None):

        self._calculadora = calculadora or Calculadora()

    @property
    def nome(self):
        return "converter_base"

    @property
    def descricao(self):
        return "Converte números entre bases numéricas."

    @property
    def parametros(self):
        return {
            "type": "object",
            "properties": {
                "valor": {"type": "string"},
                "base_origem": {"type": "integer"},
                "base_destino": {"type": "integer"}
            },
            "required": ["valor", "base_origem", "base_destino"]
        }

    def executar(self, argumentos):

        return self._calculadora.converter_base(
            argumentos["valor"],
            argumentos["base_origem"],
            argumentos["base_destino"]
        )
