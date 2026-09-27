import os
import ctypes

from .cache import CacheComandos


class BuscadorArquivos:
    """
    Busca e abertura de arquivos no disco, com cache de
    resultados (para não varrer o disco de novo em buscas
    repetidas pelo mesmo nome).

    Recebe um CacheComandos e a pasta do usuário via construtor
    (injeção de dependência), em vez de depender de módulos
    importados com estado global — facilita testar com pastas
    temporárias isoladas.
    """

    PASTAS_IGNORADAS = {
        ".venv",
        "__pycache__",
        ".git",
        ".vscode",
        "node_modules",
        "AppData",
    }

    # Número final de resultados mostrados ao usuário. Usado
    # também para interromper a varredura mais cedo: assim que
    # já temos correspondências EXATAS suficientes para
    # preencher os resultados finais, continuar varrendo o
    # resto do disco não muda a saída, então não vale a pena
    # continuar.
    LIMITE_RESULTADOS = 20

    def __init__(
        self,
        cache=None,
        pasta_usuario=None
    ):

        self._cache = cache or CacheComandos()

        self.pasta_usuario = (
            pasta_usuario
            or os.path.expanduser("~")
        )

    def obter_unidades(self):
        """
        Retorna as unidades disponíveis no Windows.
        Exemplo: ['C:\\', 'D:\\', 'E:\\']
        """

        unidades = []

        mascara = ctypes.windll.kernel32.GetLogicalDrives()

        for i in range(26):

            if mascara & (1 << i):

                letra = chr(65 + i)
                unidade = f"{letra}:\\"

                if os.path.exists(unidade):

                    unidades.append(unidade)

        return unidades

    def normalizar_unidade(self, unidade):
        """
        Converte entradas como:
        D
        D:
        D:\\
        d:
        em:
        D:\\
        """

        if not unidade:
            return None

        unidade = unidade.strip().upper()

        if len(unidade) == 1 and unidade.isalpha():
            unidade += ":"

        if len(unidade) >= 2 and unidade[1] == ":":
            return unidade[:2] + "\\"

        return None

    def _chave_cache(self, nome, unidade):
        """
        Monta a chave usada para memorizar/consultar o cache de
        arquivos já encontrados. Inclui o escopo da busca
        (unidade específica, todos os discos, ou perfil do
        usuário) porque o mesmo nome pode existir em lugares
        diferentes conforme onde a busca foi feita.
        """

        if unidade and unidade.lower().strip() == "todos":

            escopo = "todos"

        elif unidade:

            escopo = (
                self.normalizar_unidade(unidade)
                or unidade.lower().strip()
            )

        else:

            escopo = "perfil"

        return f"{nome}@{escopo}"

    def buscar_em_pasta(self, pasta, nome, ignorar_pastas=True):
        """Procura arquivos dentro de uma pasta."""

        encontrados = []
        exatos = 0

        try:

            for raiz, diretorios, arquivos in os.walk(
                pasta,
                topdown=True,
                onerror=lambda erro: None
            ):

                if ignorar_pastas:

                    diretorios[:] = [
                        pasta
                        for pasta in diretorios
                        if pasta not in self.PASTAS_IGNORADAS
                    ]

                for arquivo in arquivos:

                    arquivo_lower = arquivo.lower()
                    caminho = os.path.join(raiz, arquivo)

                    if arquivo_lower == nome:

                        encontrados.append((2, caminho))
                        exatos += 1

                        if exatos >= self.LIMITE_RESULTADOS:

                            # Já temos correspondências exatas
                            # suficientes para preencher os
                            # resultados finais — continuar
                            # varrendo o resto do disco não
                            # mudaria a saída.
                            return encontrados

                    elif nome in arquivo_lower:

                        encontrados.append((1, caminho))

        except (PermissionError, OSError):

            pass

        return encontrados

    def buscar_arquivo(self, nome, unidade=None):
        """
        Procura um arquivo.

        Se unidade for especificada: pesquisa somente naquela
        unidade.

        Se unidade for 'todos': pesquisa em todas as unidades
        disponíveis.

        Se unidade não for especificada: pesquisa no perfil do
        usuário.
        """

        nome = nome.strip().lower()

        if not nome:
            return "Você precisa informar o nome do arquivo."

        # CACHE: já achamos esse arquivo, nesse mesmo escopo,
        # antes? Se sim, e ele ainda existir, retornamos direto
        # — sem varrer o disco de novo.

        chave = self._chave_cache(nome, unidade)

        caminho_memorizado = self._cache.obter(
            "arquivos",
            chave
        )

        if caminho_memorizado:

            if os.path.isfile(caminho_memorizado):

                return (
                    "Encontrei 1 arquivo (memorizado de uma "
                    "busca anterior, sem precisar varrer o "
                    "disco de novo):\n"
                    f"- {caminho_memorizado}\n"
                )

            # O arquivo memorizado não existe mais — descartamos
            # a entrada velha e caímos para a busca normal.
            self._cache.remover(
                "arquivos",
                chave
            )

        resultados = []

        if unidade and unidade.lower().strip() != "todos":

            unidade_normalizada = self.normalizar_unidade(
                unidade
            )

            if not unidade_normalizada:

                return (
                    f"Não entendi a unidade '{unidade}'. "
                    "Use, por exemplo, C:, D: ou E:."
                )

            if not os.path.exists(unidade_normalizada):

                return (
                    f"A unidade {unidade_normalizada} "
                    "não está disponível."
                )

            resultados = self.buscar_em_pasta(
                unidade_normalizada,
                nome,
                ignorar_pastas=False
            )

        elif unidade and unidade.lower().strip() == "todos":

            for disco in self.obter_unidades():

                resultados.extend(
                    self.buscar_em_pasta(
                        disco,
                        nome,
                        ignorar_pastas=False
                    )
                )

        else:

            resultados = self.buscar_em_pasta(
                self.pasta_usuario,
                nome,
                ignorar_pastas=True
            )

        resultados.sort(
            key=lambda resultado: resultado[0],
            reverse=True
        )

        caminhos = []

        for prioridade, caminho in resultados:

            if caminho not in caminhos:

                caminhos.append(caminho)

        if not caminhos:

            local = (
                unidade
                if unidade
                else "seu perfil de usuário"
            )

            return (
                f"Não encontrei nenhum arquivo contendo "
                f"'{nome}' em {local}."
            )

        caminhos = caminhos[:self.LIMITE_RESULTADOS]

        self._cache.definir(
            "arquivos",
            chave,
            caminhos[0]
        )

        resultado = f"Encontrei {len(caminhos)} arquivo(s):\n"

        for caminho in caminhos:

            resultado += f"- {caminho}\n"

        return resultado

    def abrir_arquivo(self, caminho):
        """Abre um arquivo usando o programa padrão do Windows."""

        caminho = caminho.strip()

        if not os.path.isfile(caminho):
            return f"Não encontrei o arquivo: {caminho}"

        try:

            os.startfile(caminho)

            return f"Abri o arquivo: {caminho}"

        except Exception as erro:

            return f"Não consegui abrir o arquivo: {erro}"
