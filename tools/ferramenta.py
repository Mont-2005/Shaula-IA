from abc import ABC, abstractmethod


class Ferramenta(ABC):
    """
    Classe base para toda ferramenta que a Shaula pode chamar.

    Cada ferramenta concreta define seu nome, descrição e o
    esquema de parâmetros (formato JSON Schema, o mesmo que o
    Ollama espera), e implementa executar() com a lógica de
    verdade.

    O RegistroFerramentas (ver registro.py) guarda uma instância
    de cada uma e cuida do despacho pelo nome.
    """

    @property
    @abstractmethod
    def nome(self):
        """Nome da ferramenta, usado pelo modelo para chamá-la."""

        raise NotImplementedError

    @property
    @abstractmethod
    def descricao(self):
        """Descrição em texto do que a ferramenta faz, mostrada ao modelo."""

        raise NotImplementedError

    @property
    def parametros(self):
        """
        Esquema JSON dos parâmetros aceitos (formato usado pelo
        Ollama/OpenAI). Ferramentas sem parâmetros podem deixar
        o padrão (objeto vazio).
        """

        return {
            "type": "object",
            "properties": {},
            "required": []
        }

    @property
    def precisa_de_sintese(self):
        """
        A maioria das ferramentas já devolve uma frase pronta
        como resultado — mandar esse texto de volta para o
        modelo só para ele reformular custa uma segunda
        inferência inteira, sem necessidade. Ferramentas cujo
        resultado precisa mesmo passar pelo modelo de novo
        (hoje, só a pesquisa na internet, que devolve dados
        brutos a serem sintetizados) sobrescrevem isto para
        True.
        """

        return False

    @abstractmethod
    def executar(self, argumentos):
        """
        Executa a ferramenta com os argumentos fornecidos (um
        dicionário) e devolve uma string com o resultado — o
        mesmo formato que a Shaula sempre usou para respostas
        de ferramentas.
        """

        raise NotImplementedError

    def schema_openai(self):
        """
        Monta o dicionário de definição da ferramenta no formato
        que o Ollama espera dentro da lista `tools` enviada ao
        modelo.
        """

        return {
            "type": "function",
            "function": {
                "name": self.nome,
                "description": self.descricao,
                "parameters": self.parametros
            }
        }
