import ctypes
import subprocess
import platform
import socket
import time
import psutil


class InformacoesSistema:
    """
    Informações de hardware, teste de conexão, e controle de
    desligamento do computador.

    O medidor de CPU do psutil é "pré-aquecido" na criação da
    instância (não na importação do módulo, como antes) — veja
    o comentário no construtor.
    """

    def __init__(self):

        # psutil.cpu_percent() mede o uso da CPU comparando duas
        # leituras. Sem um "baseline" anterior, a única forma de
        # ter uma leitura válida na primeira chamada é usar
        # interval=1, que BLOQUEIA a thread por 1 segundo
        # inteiro. Como esta instância vive durante toda a
        # execução da Chelsea, fazemos essa primeira leitura
        # aqui, uma única vez — depois, informacoes_hardware()
        # pode usar interval=None e ter uma leitura instantânea.
        psutil.cpu_percent(interval=None)

    # --------------------------------------------------------
    # AUXILIARES
    # --------------------------------------------------------

    def _executar_powershell(self, comando):
        """Executa um comando PowerShell e retorna o resultado."""

        try:

            resultado = subprocess.run(
                [
                    "powershell",
                    "-NoProfile",
                    "-Command",
                    comando
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="ignore"
            )

            if resultado.returncode != 0:
                return ""

            return resultado.stdout.strip()

        except Exception:
            return ""

    def _obter_cpu_e_placa_mae(self):
        """
        Obtém o nome da CPU e os dados da placa-mãe em uma única
        chamada ao PowerShell — unir as duas consultas corta o
        custo de inicialização do processo powershell.exe pela
        metade, comparado a duas chamadas separadas.
        """

        saida = self._executar_powershell(
            """
            $cpu = (
                Get-CimInstance Win32_Processor |
                Select-Object -First 1 -ExpandProperty Name
            )

            $mb = Get-CimInstance Win32_BaseBoard |
                Select-Object -First 1 Manufacturer,Product,Version

            Write-Output "CPU|$cpu"
            Write-Output "MB|$($mb.Manufacturer)|$($mb.Product)|$($mb.Version)"
            """
        )

        cpu = ""
        placa_mae = ""

        for linha in saida.splitlines():

            if linha.startswith("CPU|"):

                cpu = linha[len("CPU|"):].strip()

            elif linha.startswith("MB|"):

                placa_mae = linha[len("MB|"):].strip()

        return cpu, placa_mae

    def _obter_informacoes_nvidia(self):
        """
        Obtém informações reais da GPU NVIDIA através do
        nvidia-smi. Retorna uma lista de dicts com nome/memória.
        """

        try:

            resultado = subprocess.run(
                [
                    "nvidia-smi",
                    "--query-gpu=name,memory.total,memory.used,memory.free",
                    "--format=csv,noheader,nounits"
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="ignore"
            )

            if resultado.returncode != 0:
                return []

            placas = []

            for linha in resultado.stdout.splitlines():

                linha = linha.strip()

                if not linha:
                    continue

                partes = [
                    parte.strip()
                    for parte in linha.split(",")
                ]

                if len(partes) < 4:
                    continue

                nome = partes[0]

                try:

                    memoria_total = float(partes[1])
                    memoria_usada = float(partes[2])
                    memoria_livre = float(partes[3])

                except ValueError:

                    continue

                placas.append({
                    "nome": nome,
                    "total_mib": memoria_total,
                    "usada_mib": memoria_usada,
                    "livre_mib": memoria_livre
                })

            return placas

        except FileNotFoundError:

            return []

        except Exception:

            return []

    def _mib_para_gb(self, valor):

        return valor / 1024

    # --------------------------------------------------------
    # DESLIGAMENTO
    # --------------------------------------------------------

    def desligar_computador(self, segundos=60):

        try:

            segundos = int(segundos)

            if segundos < 0:
                return "O tempo não pode ser negativo."

            subprocess.run(
                [
                    "shutdown",
                    "/s",
                    "/t",
                    str(segundos)
                ],
                check=True
            )

            if segundos == 0:

                return "O computador será desligado imediatamente."

            return (
                f"O computador foi programado para "
                f"desligar em {segundos} segundos."
            )

        except Exception as erro:

            return (
                "Não foi possível programar o "
                f"desligamento: {erro}"
            )

    def cancelar_desligamento(self):

        try:

            subprocess.run(
                ["shutdown", "/a"],
                check=True,
                capture_output=True,
                text=True
            )

            return "O desligamento programado foi cancelado."

        except subprocess.CalledProcessError:

            return (
                "Não existe nenhum desligamento "
                "programado para cancelar."
            )

        except Exception as erro:

            return (
                "Não foi possível cancelar o "
                f"desligamento: {erro}"
            )

    def bloquear_tela(self, atraso=0):
        """
        Bloqueia a sessão do Windows — a mesma tela que aparece
        com Win+L. Instantâneo por padrão, ou com um atraso em
        segundos (time.sleep bloqueante, igual ao 'atraso' do
        tirar_print — LockWorkStation é uma chamada rápida, não
        precisa da complexidade de threading.Timer que os
        lembretes usam pra atrasos longos).

        LockWorkStation() não tem nenhum estado pra gerenciar
        (ao contrário de desligar_computador, não tem
        "cancelar" aqui — depois que dispara, a tela já bloqueou).
        """

        try:

            atraso = float(atraso or 0)

        except (TypeError, ValueError):

            return "O tempo de espera precisa ser um número, em segundos."

        if atraso < 0:

            return "O tempo de espera não pode ser negativo."

        if atraso > 0:

            time.sleep(atraso)

        try:

            resultado = ctypes.windll.user32.LockWorkStation()

            if not resultado:
                return "Não foi possível bloquear a tela."

            return "Tela bloqueada."

        except Exception as erro:

            return f"Não foi possível bloquear a tela: {erro}"

    # --------------------------------------------------------
    # PING
    # --------------------------------------------------------

    def testar_ping(self, host="google.com"):

        try:

            host = str(host).strip()

            if not host:
                host = "google.com"

            inicio = time.perf_counter()

            resultado = subprocess.run(
                ["ping", "-n", "1", host],
                capture_output=True,
                text=True,
                encoding="cp850",
                errors="ignore"
            )

            fim = time.perf_counter()

            if resultado.returncode != 0:

                return (
                    f"Não foi possível alcançar {host}. "
                    "Verifique sua conexão com a internet."
                )

            tempo = (fim - inicio) * 1000

            ping_ms = None

            for linha in resultado.stdout.splitlines():

                linha_lower = linha.lower()

                if "tempo=" in linha_lower:

                    parte = linha_lower.split("tempo=")[1]

                    numero = ""

                    for caractere in parte:

                        if caractere.isdigit():

                            numero += caractere

                        else:

                            break

                    if numero:

                        ping_ms = int(numero)

                    break

            if ping_ms is None:

                ping_ms = round(tempo, 2)

            return f"Ping para {host}: {ping_ms} ms."

        except Exception as erro:

            return f"Erro ao executar o ping: {erro}"

    # --------------------------------------------------------
    # HARDWARE
    # --------------------------------------------------------

    def informacoes_hardware(self):

        try:

            nome_computador = socket.gethostname()
            sistema = platform.system()
            versao = platform.version()
            arquitetura = platform.machine()

            cpu, placa_mae = self._obter_cpu_e_placa_mae()

            if not cpu:
                cpu = platform.processor()

            if not cpu:
                cpu = "Não identificado"

            fabricante_mae = "Não identificado"
            modelo_mae = "Não identificado"
            versao_mae = "Não identificada"

            if placa_mae:

                partes = placa_mae.split("|")

                if len(partes) >= 1 and partes[0]:
                    fabricante_mae = partes[0]

                if len(partes) >= 2 and partes[1]:
                    modelo_mae = partes[1]

                if len(partes) >= 3 and partes[2]:
                    versao_mae = partes[2]

            placas_nvidia = self._obter_informacoes_nvidia()

            placas_video = []

            if placas_nvidia:

                for gpu in placas_nvidia:

                    placas_video.append({
                        "nome": gpu["nome"],
                        "total_gb": self._mib_para_gb(gpu["total_mib"]),
                        "usada_gb": self._mib_para_gb(gpu["usada_mib"]),
                        "livre_gb": self._mib_para_gb(gpu["livre_mib"])
                    })

            if not placas_video:

                gpu_windows = self._executar_powershell(
                    """
                    Get-CimInstance Win32_VideoController |
                    Where-Object {
                        $_.Name -and
                        $_.Name -notmatch 'Microsoft Basic Display'
                    } |
                    ForEach-Object {
                        "$($_.Name)|$($_.AdapterRAM)"
                    }
                    """
                )

                if gpu_windows:

                    for linha in gpu_windows.splitlines():

                        linha = linha.strip()

                        if not linha:
                            continue

                        partes = linha.split("|")

                        nome_gpu = partes[0].strip()

                        vram_gb = None

                        if len(partes) >= 2:

                            try:

                                vram_bytes = int(partes[1])

                                if vram_bytes > 0:

                                    vram_gb = vram_bytes / (1024 ** 3)

                            except Exception:

                                pass

                        placas_video.append({
                            "nome": nome_gpu,
                            "total_gb": vram_gb,
                            "usada_gb": None,
                            "livre_gb": None
                        })

            if not placas_video:

                placas_video.append({
                    "nome": "Não identificada",
                    "total_gb": None,
                    "usada_gb": None,
                    "livre_gb": None
                })

            nucleos_fisicos = psutil.cpu_count(logical=False)
            nucleos_logicos = psutil.cpu_count(logical=True)
            uso_cpu = psutil.cpu_percent(interval=None)

            memoria = psutil.virtual_memory()

            ram_total_gb = memoria.total / (1024 ** 3)
            ram_disponivel_gb = memoria.available / (1024 ** 3)
            ram_uso_percentual = memoria.percent

            discos = []

            for particao in psutil.disk_partitions(all=False):

                try:

                    uso = psutil.disk_usage(particao.mountpoint)

                    total_gb = uso.total / (1024 ** 3)
                    usado_gb = uso.used / (1024 ** 3)
                    livre_gb = uso.free / (1024 ** 3)

                    discos.append(
                        f"{particao.device} "
                        f"- Total: {total_gb:.2f} GB | "
                        f"Usado: {usado_gb:.2f} GB | "
                        f"Livre: {livre_gb:.2f} GB"
                    )

                except Exception:

                    pass

            resultado = f"""
COMPUTADOR
Nome: {nome_computador}

SISTEMA OPERACIONAL
Sistema: {sistema}
Versão: {versao}
Arquitetura: {arquitetura}

PROCESSADOR
Modelo: {cpu}
Núcleos físicos: {nucleos_fisicos}
Threads: {nucleos_logicos}
Uso atual: {uso_cpu}%

PLACA-MÃE
Fabricante: {fabricante_mae}
Modelo: {modelo_mae}
Versão: {versao_mae}

PLACA DE VÍDEO
"""

            for gpu in placas_video:

                nome = gpu["nome"]
                total = gpu["total_gb"]
                usada = gpu["usada_gb"]
                livre = gpu["livre_gb"]

                resultado += f"Modelo: {nome}\n"

                if total is not None:

                    resultado += f"VRAM total: {total:.2f} GB\n"

                else:

                    resultado += "VRAM total: Não identificada\n"

                if usada is not None:

                    resultado += f"VRAM usada: {usada:.2f} GB\n"

                if livre is not None:

                    resultado += f"VRAM livre: {livre:.2f} GB\n"

                resultado += "\n"

            resultado += f"""
MEMÓRIA RAM
Total: {ram_total_gb:.2f} GB
Disponível: {ram_disponivel_gb:.2f} GB
Uso: {ram_uso_percentual}%

DISCOS
"""

            if discos:

                for disco in discos:

                    resultado += f"{disco}\n"

            else:

                resultado += "Nenhum disco identificado.\n"

            return resultado.strip()

        except Exception as erro:

            return (
                "Não foi possível obter as "
                "informações do computador: "
                f"{erro}"
            )
