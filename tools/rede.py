import re
import subprocess

import psutil


class InformacoesRede:
    """
    Informações sobre a rede: IP local por interface, e — se
    houver Wi-Fi — a qual rede está conectado.

    O IP e o status das interfaces vêm do psutil (já é
    dependência do projeto). Para o nome da rede Wi-Fi (SSID),
    não existe equivalente no psutil nem uma chamada ctypes de
    uma linha só — a forma mais simples e confiável é ler a
    saída do comando 'netsh wlan show interfaces', que o
    próprio Windows já formata em texto pronto pra ler.

    Atenção: o texto que o netsh devolve muda de idioma
    conforme o idioma do Windows ("Estado"/"SSID"/"Sinal" no
    Windows em português). Isso foi testado com uma saída de
    exemplo em português — se o Windows estiver configurado em
    outro idioma, a extração desses campos pode não funcionar
    (a função não vai travar, só não vai achar SSID/sinal).
    """

    def obter_ip_local(self):
        """Lista o(s) endereço(s) IPv4 local(is), por interface, ignorando loopback e interfaces desativadas."""

        enderecos = psutil.net_if_addrs()
        estatisticas = psutil.net_if_stats()

        linhas = []

        for interface, lista_enderecos in enderecos.items():

            stats = estatisticas.get(interface)

            if stats is None or not stats.isup:
                continue

            for endereco in lista_enderecos:

                if endereco.family.name != "AF_INET":
                    continue

                if endereco.address.startswith("127."):
                    continue

                linhas.append(f"{interface}: {endereco.address}")

        if not linhas:
            return "Não encontrei nenhum IP local ativo."

        return "IP(s) local(is):\n" + "\n".join(linhas)

    def verificar_wifi(self):
        """Verifica se há uma rede Wi-Fi conectada e devolve o nome dela (SSID) e a força do sinal."""

        try:

            resultado = subprocess.run(
                ["netsh", "wlan", "show", "interfaces"],
                capture_output=True,
                text=True,
                timeout=10
            )

        except FileNotFoundError:

            return "Não consegui consultar o Wi-Fi (comando netsh não encontrado)."

        except subprocess.TimeoutExpired:

            return "A consulta ao Wi-Fi demorou demais para responder."

        saida = resultado.stdout

        if not saida.strip():
            return "Não encontrei nenhuma interface Wi-Fi neste computador."

        estado = self._extrair_campo(saida, r"Estado\s*:\s*(.+)")

        if not estado or "desconectad" in estado.lower():
            return "O Wi-Fi não está conectado a nenhuma rede no momento."

        ssid = self._extrair_campo(saida, r"^\s*SSID\s*:\s*(.+)$")
        sinal = self._extrair_campo(saida, r"Sinal\s*:\s*(.+)")

        mensagem = "Conectado ao Wi-Fi"

        if ssid:
            mensagem += f" '{ssid}'"

        mensagem += "."

        if sinal:
            mensagem += f" Sinal: {sinal}."

        return mensagem

    def _extrair_campo(self, texto, padrao):

        correspondencia = re.search(padrao, texto, re.MULTILINE)

        if not correspondencia:
            return None

        return correspondencia.group(1).strip()
