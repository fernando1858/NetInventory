import time
from dataclasses import dataclass
from typing import Any

from modulos.snmp_cliente import (
    ClienteSNMP,
    ResultadoSNMP
)


@dataclass
class ResultadoMonitoreo:
    """
    Representa el resultado de una medición de tráfico.
    """

    correcto: bool
    interfaces: list[dict[str, Any]]
    intervalo_real: float
    error: str | None = None


class MonitorSNMP:
    """
    Calcula tráfico, utilización y errores recientes
    tomando dos muestras SNMP.

    Este módulo es exclusivamente de lectura.
    No ejecuta operaciones SNMP SET.
    """

    UMBRAL_UTILIZACION_ADVERTENCIA = 70.0
    UMBRAL_UTILIZACION_CRITICA = 90.0

    VELOCIDADES_ANORMALES_MBPS = {
        10
    }

    def __init__(
        self,
        cliente_snmp: ClienteSNMP
    ):
        self.cliente_snmp = cliente_snmp

    @staticmethod
    def indexar_interfaces(
        interfaces: list[dict[str, Any]]
    ) -> dict[int, dict[str, Any]]:
        """
        Indexa interfaces usando ifIndex.
        """
        return {
            interfaz["indice"]: interfaz
            for interfaz in interfaces
            if interfaz.get("indice") is not None
        }

    @staticmethod
    def calcular_diferencia_contador(
        valor_inicial: int,
        valor_final: int,
        bits_contador: int = 64
    ) -> int:
        """
        Calcula la diferencia entre contadores SNMP.

        También considera un posible desbordamiento.
        """
        valor_inicial = max(
            int(valor_inicial or 0),
            0
        )

        valor_final = max(
            int(valor_final or 0),
            0
        )

        if valor_final >= valor_inicial:
            return valor_final - valor_inicial

        maximo_contador = 2 ** bits_contador

        return (
            maximo_contador
            - valor_inicial
            + valor_final
        )

    @staticmethod
    def bytes_a_mbps(
        diferencia_bytes: int,
        intervalo: float
    ) -> float:
        """
        Convierte bytes transferidos durante un intervalo
        a megabits por segundo.
        """
        if intervalo <= 0:
            return 0.0

        bits = diferencia_bytes * 8

        return round(
            bits / intervalo / 1_000_000,
            3
        )

    @staticmethod
    def calcular_utilizacion(
        trafico_mbps: float,
        velocidad_bps: int
    ) -> float:
        """
        Calcula el porcentaje de uso respecto de la
        velocidad negociada del enlace.
        """
        if velocidad_bps <= 0:
            return 0.0

        capacidad_mbps = (
            velocidad_bps
            / 1_000_000
        )

        if capacidad_mbps <= 0:
            return 0.0

        return round(
            trafico_mbps
            * 100
            / capacidad_mbps,
            2
        )

    @staticmethod
    def obtener_numero_puerto(
        nombre: str
    ) -> int | None:
        """
        Extrae el último componente numérico de nombres
        como 1/1/14.
        """
        texto = str(
            nombre or ""
        ).strip()

        if not texto:
            return None

        ultimo_fragmento = texto.split("/")[-1]

        try:
            return int(
                ultimo_fragmento
            )

        except ValueError:
            return None

    @staticmethod
    def es_interfaz_fisica(
        interfaz: dict[str, Any]
    ) -> bool:
        """
        Excluye interfaces lógicas conocidas.
        """
        nombre = str(
            interfaz.get("nombre") or ""
        ).lower()

        descripcion = str(
            interfaz.get("descripcion") or ""
        ).lower()

        texto = f"{nombre} {descripcion}"

        exclusiones = {
            "vlan",
            "loopback",
            "management",
            "mgmt",
            "bridge",
            "cpu",
            "null",
            "tunnel"
        }

        return not any(
            palabra in texto
            for palabra in exclusiones
        )

    def clasificar_utilizacion(
        self,
        utilizacion: float
    ) -> str:
        """
        Clasifica el nivel de utilización.
        """
        if utilizacion >= (
            self.UMBRAL_UTILIZACION_CRITICA
        ):
            return "CRÍTICA"

        if utilizacion >= (
            self.UMBRAL_UTILIZACION_ADVERTENCIA
        ):
            return "ALTA"

        if utilizacion > 0:
            return "NORMAL"

        return "SIN TRÁFICO"

    def detectar_observaciones(
        self,
        interfaz: dict[str, Any]
    ) -> list[str]:
        """
        Genera observaciones útiles para administración.
        """
        observaciones = []

        estado = interfaz.get(
            "estado_operativo"
        )

        velocidad_bps = int(
            interfaz.get("velocidad_bps") or 0
        )

        velocidad_mbps = (
            velocidad_bps // 1_000_000
            if velocidad_bps > 0
            else 0
        )

        utilizacion_maxima = max(
            interfaz.get(
                "utilizacion_entrada"
            ) or 0,
            interfaz.get(
                "utilizacion_salida"
            ) or 0
        )

        errores_nuevos = (
            interfaz.get(
                "errores_nuevos_entrada"
            ) or 0
        ) + (
            interfaz.get(
                "errores_nuevos_salida"
            ) or 0
        )

        trafico_total = (
            interfaz.get(
                "trafico_entrada_mbps"
            ) or 0
        ) + (
            interfaz.get(
                "trafico_salida_mbps"
            ) or 0
        )

        if (
            estado == "UP"
            and velocidad_mbps
            in self.VELOCIDADES_ANORMALES_MBPS
        ):
            observaciones.append(
                f"Enlace negociado a {velocidad_mbps} Mbps"
            )

        if utilizacion_maxima >= (
            self.UMBRAL_UTILIZACION_CRITICA
        ):
            observaciones.append(
                "Utilización crítica del enlace"
            )

        elif utilizacion_maxima >= (
            self.UMBRAL_UTILIZACION_ADVERTENCIA
        ):
            observaciones.append(
                "Utilización elevada del enlace"
            )

        if errores_nuevos > 0:
            observaciones.append(
                f"{errores_nuevos} errores nuevos"
            )

        if (
            estado == "UP"
            and trafico_total == 0
        ):
            observaciones.append(
                "Puerto activo sin tráfico durante la muestra"
            )

        return observaciones

    def construir_medicion(
        self,
        inicial: dict[str, Any],
        final: dict[str, Any],
        intervalo: float
    ) -> dict[str, Any]:
        """
        Construye una medición comparando dos muestras.
        """
        diferencia_entrada = (
            self.calcular_diferencia_contador(
                inicial.get(
                    "bytes_entrada",
                    0
                ),
                final.get(
                    "bytes_entrada",
                    0
                )
            )
        )

        diferencia_salida = (
            self.calcular_diferencia_contador(
                inicial.get(
                    "bytes_salida",
                    0
                ),
                final.get(
                    "bytes_salida",
                    0
                )
            )
        )

        trafico_entrada = self.bytes_a_mbps(
            diferencia_entrada,
            intervalo
        )

        trafico_salida = self.bytes_a_mbps(
            diferencia_salida,
            intervalo
        )

        velocidad_bps = int(
            final.get("velocidad_bps") or 0
        )

        utilizacion_entrada = (
            self.calcular_utilizacion(
                trafico_entrada,
                velocidad_bps
            )
        )

        utilizacion_salida = (
            self.calcular_utilizacion(
                trafico_salida,
                velocidad_bps
            )
        )

        errores_nuevos_entrada = max(
            int(
                final.get(
                    "errores_entrada",
                    0
                )
            )
            - int(
                inicial.get(
                    "errores_entrada",
                    0
                )
            ),
            0
        )

        errores_nuevos_salida = max(
            int(
                final.get(
                    "errores_salida",
                    0
                )
            )
            - int(
                inicial.get(
                    "errores_salida",
                    0
                )
            ),
            0
        )

        resultado = {
            **final,
            "numero_puerto": (
                self.obtener_numero_puerto(
                    final.get("nombre")
                )
            ),
            "intervalo_segundos": round(
                intervalo,
                3
            ),
            "bytes_intervalo_entrada": (
                diferencia_entrada
            ),
            "bytes_intervalo_salida": (
                diferencia_salida
            ),
            "trafico_entrada_mbps": (
                trafico_entrada
            ),
            "trafico_salida_mbps": (
                trafico_salida
            ),
            "utilizacion_entrada": (
                utilizacion_entrada
            ),
            "utilizacion_salida": (
                utilizacion_salida
            ),
            "utilizacion_maxima": max(
                utilizacion_entrada,
                utilizacion_salida
            ),
            "nivel_utilizacion": (
                self.clasificar_utilizacion(
                    max(
                        utilizacion_entrada,
                        utilizacion_salida
                    )
                )
            ),
            "errores_nuevos_entrada": (
                errores_nuevos_entrada
            ),
            "errores_nuevos_salida": (
                errores_nuevos_salida
            )
        }

        resultado["observaciones"] = (
            self.detectar_observaciones(
                resultado
            )
        )

        return resultado

    def medir_trafico(
        self,
        ip: str,
        intervalo: float = 5.0,
        solo_fisicas: bool = True
    ) -> ResultadoMonitoreo:
        """
        Toma dos muestras y calcula tráfico real.
        """
        if intervalo < 1:
            return ResultadoMonitoreo(
                correcto=False,
                interfaces=[],
                intervalo_real=0,
                error=(
                    "El intervalo debe ser de al menos "
                    "1 segundo."
                )
            )

        primera = (
            self.cliente_snmp
            .obtener_interfaces(
                ip
            )
        )

        if not primera.correcto:
            return ResultadoMonitoreo(
                correcto=False,
                interfaces=[],
                intervalo_real=0,
                error=(
                    "No se pudo obtener la primera muestra: "
                    f"{primera.error}"
                )
            )

        inicio = time.monotonic()

        time.sleep(
            intervalo
        )

        segunda = (
            self.cliente_snmp
            .obtener_interfaces(
                ip
            )
        )

        fin = time.monotonic()

        if not segunda.correcto:
            return ResultadoMonitoreo(
                correcto=False,
                interfaces=[],
                intervalo_real=fin - inicio,
                error=(
                    "No se pudo obtener la segunda muestra: "
                    f"{segunda.error}"
                )
            )

        intervalo_real = fin - inicio

        iniciales = self.indexar_interfaces(
            primera.datos
        )

        finales = self.indexar_interfaces(
            segunda.datos
        )

        mediciones = []

        for indice, interfaz_final in finales.items():
            interfaz_inicial = iniciales.get(
                indice
            )

            if interfaz_inicial is None:
                continue

            if (
                solo_fisicas
                and not self.es_interfaz_fisica(
                    interfaz_final
                )
            ):
                continue

            mediciones.append(
                self.construir_medicion(
                    inicial=interfaz_inicial,
                    final=interfaz_final,
                    intervalo=intervalo_real
                )
            )

        mediciones.sort(
            key=lambda interfaz: (
                interfaz.get("indice") or 0
            )
        )

        return ResultadoMonitoreo(
            correcto=True,
            interfaces=mediciones,
            intervalo_real=intervalo_real
        )