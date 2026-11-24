import re


class DetectorAcaoSemFerramenta:
    """
    Pega o modelo "mentindo sem querer": responder "Firefox movido
    para o monitor 1." SEM ter chamado nenhuma ferramenta. Modelos
    locais pequenos fazem isso, em especial quando o histórico tem
    várias respostas curtas desse formato (o histórico guarda só o
    texto final, nunca a chamada da ferramenta, então o modelo aprende
    a "responder igual" em vez de agir).

    Só decide se um TEXTO afirma que uma ação foi feita; quem sabe se
    alguma ferramenta rodou na troca é o TrabalhadorIA, que consulta
    este detector apenas quando nenhuma rodou.

    A heurística é de propósito simples e barata: resposta curta (um
    relato de ação costuma ser uma frase) com um verbo de ação no
    particípio ou gerúndio. Um falso positivo só custa uma nova
    geração — o aviso dado ao modelo manda responder normalmente se o
    pedido não envolvia ação.
    """

    LIMITE_CARACTERES = 220

    # Verbos das ações que as ferramentas da Shaula realmente fazem
    # (janelas, programas, processos, volume, arquivos...), no
    # particípio ou gerúndio. Regulares (-ado/-ando) e os em -ido.
    AFIRMACAO = re.compile(
        r"\b(?:"
        r"(?:minimiz|maximiz|restaur|execut|envi|ativ|desativ|ajust|"
        r"inici|finaliz|encerr|reinici|deslig|apag|copi|renome|salv|"
        r"cri|alter|aument|silenci|fech)(?:ad[oa]s?|ando)|"
        r"(?:mov|remov|exclu|defin|diminu)(?:[ií]d[oa]s?|[eií]ndo)|"
        r"abrindo|abert[oa]s?"
        r")\b",
        re.IGNORECASE
    )

    MENSAGEM_CORRECAO = (
        "Você acabou de responder dizendo que fez uma ação, mas NÃO "
        "chamou nenhuma ferramenta nesta troca — então nada foi "
        "feito de verdade. Se o usuário pediu uma ação no "
        "computador (mover janela, abrir ou fechar programa etc.), "
        "chame AGORA a ferramenta correspondente e só depois diga o "
        "resultado dela. Nunca diga que executou algo sem ter "
        "chamado a ferramenta. Se o pedido não envolve ação (é só "
        "conversa ou explicação), responda de novo normalmente, sem "
        "afirmar que executou algo."
    )

    AVISO = (
        "⚠️ Não chamei nenhuma ferramenta nesta resposta — o que "
        "está escrito acima pode não ter acontecido de verdade. "
        "Tente pedir de novo."
    )

    def afirma_acao(self, texto):

        texto = (texto or "").strip()

        return bool(
            texto
            and len(texto) <= self.LIMITE_CARACTERES
            and self.AFIRMACAO.search(texto)
        )

    def mensagem_de_correcao(self):

        return {
            "role": "system",
            "content": self.MENSAGEM_CORRECAO
        }

    def com_aviso(self, texto):

        return f"{texto.rstrip()}\n\n{self.AVISO}"
