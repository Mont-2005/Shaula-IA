import pytest

from tools.calculadora import Calculadora


@pytest.fixture
def calc():
    return Calculadora()


# ---------------- conversão de base ----------------

@pytest.mark.parametrize("valor,origem,destino,esperado", [
    ("255", 10, 16, "FF"),
    ("-255", 10, 16, "-FF"),            # antes: "XFF"
    ("-5", 10, 2, "-101"),              # antes: "b101"
    ("-17", 10, 8, "-21"),              # antes: "o21"
    ("-101", 2, 10, "-5"),
    ("-0xff", 16, 10, "-255"),
    ("0b101", 2, 10, "5"),
    ("-0", 10, 2, "0"),
])
def test_converter_base_com_e_sem_sinal(calc, valor, origem, destino, esperado):
    resposta = calc.converter_base(valor, origem, destino)
    assert resposta.split(" = ")[1].split(" ")[0] == esperado


def test_converter_base_recusa_digito_invalido(calc):
    assert "não é um número válido" in calc.converter_base("12", 2, 10)


# ---------------- expressões ----------------

def test_argumento_nomeado_nao_e_ignorado_em_silencio(calc):
    # antes: log(8, base=2) devolvia ln(8) = 2.079...
    assert "posição" in calc.calcular("log(8, base=2)")
    assert calc.calcular("log(8, 2)") == "Resultado: 3.0"


def test_fatorial_aceita_float_inteiro(calc):
    assert calc.calcular("factorial(5.0)") == "Resultado: 120"


@pytest.mark.parametrize("expressao,trecho", [
    ("sqrt(-1)", "fora do domínio"),
    ("factorial(-1)", "números negativos"),
    ("1/0", "dividir por zero"),
    ("9**9**9", "grande demais"),
])
def test_erros_em_portugues(calc, expressao, trecho):
    assert trecho in calc.calcular(expressao)


@pytest.mark.parametrize("expressao,esperado", [
    ("2+2", "Resultado: 4"),
    ("10/4", "Resultado: 2.5"),
    ("0.1+0.2", "Resultado: 0.3"),
    ("2**10", "Resultado: 1024"),
    ("sqrt(16)", "Resultado: 4.0"),
])
def test_continua_calculando(calc, expressao, esperado):
    assert calc.calcular(expressao) == esperado


# ---------------- matrizes ----------------

def test_determinante_de_matriz_de_valores_pequenos_nao_vira_zero(calc):
    # antes: 1e-14 era arredondado para 0 por um limite fixo
    assert calc.matriz_determinante([[1e-7, 0], [0, 1e-7]]) == "1e-14"


@pytest.mark.parametrize("matriz,esperado", [
    ([[1, 2], [3, 4]], "-2"),
    ([[1, 2], [2, 4]], "0"),              # singular
    ([[0.1, 0.2], [0.3, 0.6]], "0"),      # singular com erro de ponto flutuante
    ([[2, 0], [0, 3]], "6"),
])
def test_determinante_continua_certo(calc, matriz, esperado):
    assert calc.matriz_determinante(matriz) == esperado
