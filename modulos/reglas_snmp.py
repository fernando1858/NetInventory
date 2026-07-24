from dataclasses import dataclass, field
from typing import Any


@dataclass
class IncidenciaSNMP:
    """
    Representa una observación generada por una regla SNMP.

    Este objeto no imprime información ni modifica datos.
    Puede utilizarse posteriormente en consola, Excel,
    dashboard o una interfaz web.
    """

    nivel: str
    categoria: str
    titulo: str
    detalle: str
    recomendacion: str

    puerto: str | None = None
    ip_switch: str | None = None

    valor_actual: Any = None
    umbral: Any = None

    datos: dict[str, Any] = field(
        default_factory=dict
    )

    def convertir_diccionario(self) -> dict[str, Any]:
        """
        Convierte la incidencia en un diccionario común.
        """
        return {
            "nivel": self.nivel,
            "categoria": self.categoria,
            "titulo": self.titulo,
            "detalle": self.detalle,
            "recomendacion": self.recomendacion,
            "puerto": self.puerto,
            "ip_switch": self.ip_switch,
            "valor_actual": self.valor_actual,
            "umbral": self.umbral,
            "datos": dict(self.datos)
        }


class ReglasSNMP:
    """
    Contiene reglas conservadoras para analizar información
    obtenida directamente desde los switches.

    Estas reglas no utilizan el inventario Excel.

    No consideran automáticamente como fallas:

    - Puertos DOWN.
    - Enlaces a 100 Mbps.
    - Tráfico bajo.
    - Errores históricos que no aumentan.
    """

    NIVEL_CRITICO = "CRÍTICO"
    NIVEL_ADVERTENCIA = "ADVERTENCIA"
    NIVEL_INFORMATIVO = "INFORMATIVO"

    UMBRAL_UTILIZACION_ADVERTENCIA = 80.0
    UMBRAL_UTILIZACION_CRITICA = 95.0

    UMBRAL_ERRORES_ADVERTENCIA = 1
    UMBRAL_ERRORES_CRITICO = 20

    UMBRAL_REINICIO_RECIENTE_HORAS = 24

    @staticmethod
    def convertir_entero(
        valor: Any,
        predeterminado: int = 0
    ) -> int:
        """
        Convierte un valor a entero de forma segura.
        """
        try:
            return int(
                valor
            )

        except (
            TypeError,
            ValueError
        ):
            return predeterminado

    @staticmethod
    def convertir_decimal(
        valor: Any,
        predeterminado: float = 0.0
    ) -> float:
        """
        Convierte un valor a decimal de forma segura.
        """
        try:
            return float(
                valor
            )

        except (
            TypeError,
            ValueError
        ):
            return predeterminado

    @staticmethod
    def obtener_nombre_puerto(
        interfaz: dict[str, Any]
    ) -> str:
        """
        Obtiene un nombre visible para una interfaz.
        """
        nombre = interfaz.get(
            "nombre"
        )

        if nombre is not None:
            texto = str(
                nombre
            ).strip()

            if texto:
                return texto

        indice = interfaz.get(
            "indice"
        )

        if indice is not None:
            return f"Interfaz {indice}"

        return "Interfaz desconocida"

    @staticmethod
    def interfaz_esta_activa(
        interfaz: dict[str, Any]
    ) -> bool:
        """
        Comprueba si la interfaz tiene enlace operativo.
        """
        return (
            str(
                interfaz.get(
                    "estado_operativo",
                    ""
                )
            ).upper()
            == "UP"
        )

    @classmethod
    def detectar_enlace_10_mbps(
        cls,
        interfaz: dict[str, Any],
        ip_switch: str | None = None
    ) -> IncidenciaSNMP | None:
        """
        Advierte cuando una interfaz activa negocia
        únicamente a 10 Mbps.

        No analiza los enlaces a 100 Mbps porque pueden ser
        normales para cámaras, teléfonos o impresoras.
        """
        if not cls.interfaz_esta_activa(
            interfaz
        ):
            return None

        velocidad_bps = cls.convertir_entero(
            interfaz.get(
                "velocidad_bps"
            )
        )

        if velocidad_bps != 10_000_000:
            return None

        puerto = cls.obtener_nombre_puerto(
            interfaz
        )

        return IncidenciaSNMP(
            nivel=cls.NIVEL_ADVERTENCIA,
            categoria="VELOCIDAD",
            titulo="Enlace negociado a 10 Mbps",
            detalle=(
                f"El puerto {puerto} está activo, pero "
                "su enlace negoció solamente a 10 Mbps."
            ),
            recomendacion=(
                "Revisar el cable de red, conectores, "
                "patch panel, configuración de velocidad "
                "y capacidad del dispositivo conectado."
            ),
            puerto=puerto,
            ip_switch=ip_switch,
            valor_actual="10 Mbps",
            umbral="Superior a 10 Mbps",
            datos={
                "velocidad_bps": velocidad_bps,
                "estado_operativo": interfaz.get(
                    "estado_operativo"
                ),
                "estado_administrativo": interfaz.get(
                    "estado_administrativo"
                )
            }
        )

    @classmethod
    def detectar_errores_nuevos(
        cls,
        interfaz: dict[str, Any],
        ip_switch: str | None = None
    ) -> IncidenciaSNMP | None:
        """
        Detecta errores que aumentaron entre dos muestras.

        Los errores acumulados antiguos no se consideran una
        incidencia activa si no aumentan.
        """
        errores_entrada = cls.convertir_entero(
            interfaz.get(
                "errores_nuevos_entrada"
            )
        )

        errores_salida = cls.convertir_entero(
            interfaz.get(
                "errores_nuevos_salida"
            )
        )

        total = (
            errores_entrada
            + errores_salida
        )

        if total < cls.UMBRAL_ERRORES_ADVERTENCIA:
            return None

        puerto = cls.obtener_nombre_puerto(
            interfaz
        )

        if total >= cls.UMBRAL_ERRORES_CRITICO:
            nivel = cls.NIVEL_CRITICO

            titulo = (
                "Incremento importante de errores"
            )

        else:
            nivel = cls.NIVEL_ADVERTENCIA

            titulo = (
                "Se detectaron errores nuevos"
            )

        return IncidenciaSNMP(
            nivel=nivel,
            categoria="ERRORES",
            titulo=titulo,
            detalle=(
                f"Durante la medición, el puerto {puerto} "
                f"registró {total} errores nuevos: "
                f"{errores_entrada} de entrada y "
                f"{errores_salida} de salida."
            ),
            recomendacion=(
                "Revisar cableado, conectores, patch panel, "
                "negociación del enlace y estado físico del "
                "dispositivo conectado. Repetir la medición "
                "para confirmar si los errores continúan."
            ),
            puerto=puerto,
            ip_switch=ip_switch,
            valor_actual=total,
            umbral=cls.UMBRAL_ERRORES_ADVERTENCIA,
            datos={
                "errores_nuevos_entrada": (
                    errores_entrada
                ),
                "errores_nuevos_salida": (
                    errores_salida
                ),
                "errores_nuevos_totales": total
            }
        )

    @classmethod
    def detectar_utilizacion_elevada(
        cls,
        interfaz: dict[str, Any],
        ip_switch: str | None = None
    ) -> IncidenciaSNMP | None:
        """
        Detecta utilización elevada durante una medición.

        Una muestra aislada no confirma saturación sostenida,
        por lo que la recomendación solicita repetirla.
        """
        if not cls.interfaz_esta_activa(
            interfaz
        ):
            return None

        utilizacion = cls.convertir_decimal(
            interfaz.get(
                "utilizacion_maxima"
            )
        )

        if utilizacion < (
            cls.UMBRAL_UTILIZACION_ADVERTENCIA
        ):
            return None

        puerto = cls.obtener_nombre_puerto(
            interfaz
        )

        if utilizacion >= (
            cls.UMBRAL_UTILIZACION_CRITICA
        ):
            nivel = cls.NIVEL_CRITICO

            titulo = (
                "Utilización cercana a la capacidad máxima"
            )

        else:
            nivel = cls.NIVEL_ADVERTENCIA

            titulo = (
                "Utilización elevada del enlace"
            )

        trafico_entrada = cls.convertir_decimal(
            interfaz.get(
                "trafico_entrada_mbps"
            )
        )

        trafico_salida = cls.convertir_decimal(
            interfaz.get(
                "trafico_salida_mbps"
            )
        )

        return IncidenciaSNMP(
            nivel=nivel,
            categoria="UTILIZACIÓN",
            titulo=titulo,
            detalle=(
                f"El puerto {puerto} alcanzó una utilización "
                f"máxima de {utilizacion:.2f} % durante la "
                "medición."
            ),
            recomendacion=(
                "Repetir la medición durante un intervalo "
                "más largo. Si la utilización se mantiene, "
                "revisar el tipo de enlace, tráfico generado "
                "y capacidad disponible."
            ),
            puerto=puerto,
            ip_switch=ip_switch,
            valor_actual=utilizacion,
            umbral=(
                cls.UMBRAL_UTILIZACION_ADVERTENCIA
            ),
            datos={
                "trafico_entrada_mbps": (
                    trafico_entrada
                ),
                "trafico_salida_mbps": (
                    trafico_salida
                ),
                "utilizacion_maxima": utilizacion,
                "velocidad": interfaz.get(
                    "velocidad"
                )
            }
        )

    @classmethod
    def detectar_reinicio_reciente(
        cls,
        informacion_sistema: dict[str, Any],
        ip_switch: str | None = None
    ) -> IncidenciaSNMP | None:
        """
        Informa cuando el switch lleva menos de 24 horas
        encendido.

        Se clasifica como informativo porque un reinicio puede
        haber sido planificado.
        """
        uptime = informacion_sistema.get(
            "uptime",
            {}
        )

        if not isinstance(
            uptime,
            dict
        ):
            return None

        segundos = cls.convertir_entero(
            uptime.get(
                "segundos"
            ),
            predeterminado=-1
        )

        if segundos < 0:
            return None

        umbral_segundos = (
            cls.UMBRAL_REINICIO_RECIENTE_HORAS
            * 3600
        )

        if segundos >= umbral_segundos:
            return None

        texto_uptime = uptime.get(
            "texto"
        ) or f"{segundos} segundos"

        return IncidenciaSNMP(
            nivel=cls.NIVEL_INFORMATIVO,
            categoria="DISPONIBILIDAD",
            titulo="Reinicio reciente del switch",
            detalle=(
                "El switch posee un tiempo de actividad de "
                f"{texto_uptime}, inferior a "
                f"{cls.UMBRAL_REINICIO_RECIENTE_HORAS} horas."
            ),
            recomendacion=(
                "Confirmar si el reinicio fue planificado. "
                "Si no lo fue, revisar alimentación, eventos "
                "del sistema y registros de Zabbix."
            ),
            puerto=None,
            ip_switch=ip_switch,
            valor_actual=texto_uptime,
            umbral=(
                f"{cls.UMBRAL_REINICIO_RECIENTE_HORAS} horas"
            ),
            datos={
                "uptime_segundos": segundos,
                "uptime_texto": texto_uptime
            }
        )