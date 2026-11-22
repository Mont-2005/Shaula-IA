import os
import time

import psutil


class GerenciadorProcessos:
    """
    Lista processos em execução e permite finalizar processos
    pelo nome ou PID.

    Usa só psutil (já é dependência do projeto — a mesma
    biblioteca usada em InformacoesSistema para hardware).
    Nada de ctypes aqui: é tudo API de alto nível e
    multiplataforma por baixo dos panos, o que também significa
    bem menos superfície pra bug do tipo que já tivemos com GDI
    e WinRT.
    """

    # Processos essenciais do Windows que essa ferramenta nunca
    # finaliza — matar um desses pode travar ou derrubar a
    # sessão inteira do usuário. Comparação sempre em minúsculas.
    PROCESSOS_PROTEGIDOS = {
        "system", "system idle process", "registry",
        "smss.exe", "csrss.exe", "wininit.exe", "winlogon.exe",
        "services.exe", "lsass.exe", "explorer.exe", "svchost.exe",
        "dwm.exe", "fontdrvhost.exe", "python.exe", "pythonw.exe",
        # O servidor do modelo: finalizá-lo derruba a própria Shaula
        # no meio da conversa.
        "ollama.exe", "ollama app.exe",
        # Processos de sessão e de segurança do Windows: não fecham
        # um programa do usuário, mas matá-los quebra menu Iniciar,
        # teclado, som, impressão ou o antivírus.
        "ctfmon.exe", "sihost.exe", "taskhostw.exe", "runtimebroker.exe",
        "audiodg.exe", "searchhost.exe", "startmenuexperiencehost.exe",
        "shellexperiencehost.exe", "applicationframehost.exe",
        "spoolsv.exe", "lsm.exe", "wudfhost.exe", "dllhost.exe",
        "msmpeng.exe", "securityhealthservice.exe",
    }

    # --------------------------------------------------------
    # LISTAR
    # --------------------------------------------------------

    def listar_processos_protegidos(self):
        """Lista os processos que essa ferramenta nunca finaliza, por segurança."""

        nomes = sorted(self.PROCESSOS_PROTEGIDOS)

        linhas = ["Processos protegidos (nunca finalizados por segurança):"]

        for nome in nomes:
            linhas.append(f"- {nome}")

        return "\n".join(linhas)

    # --------------------------------------------------------
    # LISTAR (por consumo)
    # --------------------------------------------------------

    def listar_processos(self, ordenar_por="cpu", limite=10):
        """
        Lista os processos que mais consomem CPU ou memória.
        'ordenar_por': "cpu" ou "memoria".
        """

        ordenar_por = str(ordenar_por or "cpu").strip().lower()

        if ordenar_por not in ("cpu", "memoria"):
            return "Ordenação inválida. Use 'cpu' ou 'memoria'."

        try:
            limite = int(limite)
        except (TypeError, ValueError):
            return "O limite precisa ser um número inteiro."

        if limite <= 0:
            return "O limite precisa ser maior que zero."

        processos = []

        for proc in psutil.process_iter(["pid", "name"]):

            try:
                # "Aquece" a medição de CPU deste processo — a
                # primeira chamada de cpu_percent() sempre
                # devolve 0.0, porque ela mede a diferença entre
                # duas leituras (mesmo motivo documentado em
                # InformacoesSistema para a CPU do sistema como
                # um todo).
                proc.cpu_percent(interval=None)
                processos.append(proc)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        time.sleep(0.3)

        dados = []

        for proc in processos:

            try:
                with proc.oneshot():
                    cpu = proc.cpu_percent(interval=None)
                    memoria_mb = proc.memory_info().rss / (1024 * 1024)
                    dados.append({
                        "pid": proc.pid,
                        "nome": proc.name(),
                        "cpu": cpu,
                        "memoria_mb": memoria_mb,
                    })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        if not dados:
            return "Não consegui listar nenhum processo."

        chave = "cpu" if ordenar_por == "cpu" else "memoria_mb"

        dados.sort(key=lambda item: item[chave], reverse=True)

        dados = dados[:limite]

        linhas = [f"Top {len(dados)} processos por {ordenar_por}:"]

        for item in dados:
            linhas.append(
                f"PID {item['pid']}: {item['nome']} — "
                f"{item['cpu']:.1f}% CPU, {item['memoria_mb']:.0f} MB"
            )

        return "\n".join(linhas)

    # --------------------------------------------------------
    # FINALIZAR
    # --------------------------------------------------------

    def finalizar_processo(self, alvo):
        """
        Finaliza um processo pelo PID (número exato) ou pelo
        nome (busca por trecho, sem diferenciar maiúsculas de
        minúsculas — mata TODOS os processos que combinarem,
        já que programas como o Chrome rodam várias instâncias
        com o mesmo nome, e normalmente é isso que a pessoa
        quer dizer com "fecha o chrome").
        """

        alvo = str(alvo).strip()

        if not alvo:
            return "Preciso saber qual processo finalizar."

        if alvo.isdigit():
            return self._finalizar_por_pid(int(alvo))

        return self._finalizar_por_nome(alvo)

    # Nome mínimo para finalizar por trecho. Como a busca é por
    # "contém", um trecho como "e" ou "ho" combinava com quase
    # todos os processos do sistema.
    TAMANHO_MINIMO_NOME = 3

    def _eh_protegido(self, nome):
        """
        Compara o nome com a lista de protegidos com ou sem
        ".exe": pedir para finalizar "svchost" ou "explorer" (sem
        extensão) burlava a lista, porque só "svchost.exe" estava
        nela, e a busca por trecho acabava encontrando o processo
        real e finalizando.
        """

        nome = str(nome).strip().lower()

        return (
            nome in self.PROCESSOS_PROTEGIDOS
            or f"{nome}.exe" in self.PROCESSOS_PROTEGIDOS
        )

    def _pids_da_propria_shaula(self):
        """PID desta Shaula e dos processos acima dela (launcher, .bat)."""

        pids = {os.getpid()}

        try:

            for pai in psutil.Process().parents():
                pids.add(pai.pid)

        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

        return pids

    def _finalizar_varios(self, processos):
        """
        Pede o encerramento de todos de uma vez e espera junto
        (antes era um por um, com até 3 s de espera cada — 30
        processos do Chrome travados levavam minutos). Devolve
        (finalizados, falhas).
        """

        finalizados = []
        falhas = []
        aguardando = []

        for proc in processos:

            try:

                nome_real = proc.info.get("name") or proc.name()

                proc.terminate()

                aguardando.append((proc, nome_real))

            except psutil.NoSuchProcess:
                continue

            except psutil.AccessDenied:
                falhas.append(f"PID {proc.pid}: acesso negado")

        _, vivos = psutil.wait_procs(
            [proc for proc, _ in aguardando],
            timeout=3
        )

        vivos_pids = {proc.pid for proc in vivos}

        for proc, nome_real in aguardando:

            if proc.pid in vivos_pids:

                try:
                    proc.kill()
                except psutil.NoSuchProcess:
                    pass
                except psutil.AccessDenied:
                    falhas.append(f"PID {proc.pid}: acesso negado")
                    continue

            finalizados.append(f"{nome_real} (PID {proc.pid})")

        return finalizados, falhas

    def _finalizar_um(self, proc):
        """Tenta terminar graciosamente; se não responder a tempo, força o encerramento."""

        proc.terminate()

        try:
            proc.wait(timeout=3)
        except psutil.TimeoutExpired:
            proc.kill()

    def _finalizar_por_pid(self, pid):

        try:
            proc = psutil.Process(pid)
            nome = proc.name()
        except psutil.NoSuchProcess:
            return f"Não existe nenhum processo com PID {pid}."

        if self._eh_protegido(nome) or pid in self._pids_da_propria_shaula():
            return (
                f"Não vou finalizar '{nome}' (PID {pid}) — é um "
                "processo essencial do sistema ou a própria Shaula."
            )

        try:
            self._finalizar_um(proc)
        except psutil.NoSuchProcess:
            return f"'{nome}' (PID {pid}) já não estava mais em execução."
        except psutil.AccessDenied:
            return (
                f"Não tenho permissão para finalizar '{nome}' "
                f"(PID {pid}). Talvez precise rodar a Shaula "
                "como administrador."
            )

        return f"Processo '{nome}' (PID {pid}) finalizado."

    def _finalizar_por_nome(self, nome):

        nome = nome.strip()

        if self._eh_protegido(nome):
            return (
                f"Não vou finalizar '{nome}' — é um processo "
                "essencial do sistema."
            )

        if len(nome) < self.TAMANHO_MINIMO_NOME:
            return (
                f"'{nome}' é curto demais e combinaria com "
                "processos demais. Diga o nome completo do "
                "programa (ex.: 'chrome')."
            )

        nome_busca = nome.lower()

        propria = self._pids_da_propria_shaula()

        encontrados = []

        protegidos_ignorados = 0

        for proc in psutil.process_iter(["pid", "name"]):

            try:

                nome_proc = proc.info["name"] or ""

                if nome_busca not in nome_proc.lower():
                    continue

                # O filtro vale para o nome REAL do processo
                # encontrado, não só para o que foi digitado.
                if self._eh_protegido(nome_proc) or proc.pid in propria:
                    protegidos_ignorados += 1
                    continue

                encontrados.append(proc)

            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        if not encontrados:

            if protegidos_ignorados:
                return (
                    f"Os processos que combinam com '{nome}' são "
                    "essenciais do sistema (ou a própria Shaula) "
                    "e não serão finalizados."
                )

            return f"Não encontrei nenhum processo chamado '{nome}'."

        finalizados, falhas = self._finalizar_varios(encontrados)

        partes = []

        if finalizados:
            partes.append(
                f"{len(finalizados)} processo(s) finalizado(s): "
                + ", ".join(finalizados)
            )

        if falhas:
            partes.append(
                f"{len(falhas)} falharam: " + ", ".join(falhas)
            )

        if protegidos_ignorados:
            partes.append(
                f"{protegidos_ignorados} processo(s) essencial(is) "
                "foram ignorados por segurança."
            )

        return "\n".join(partes)
