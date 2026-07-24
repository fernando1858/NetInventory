from collections import Counter
from dataclasses import dataclass
from typing import Any

from modulos.reglas_snmp import (
    IncidenciaSNMP,
    ReglasSNMP
)


@dataclass
class ResultadoAnalisisSNMP:
    """
    Contiene el resultado completo de un análisis.
    """

    ip_switch: str | None
    interfaces_analizadas: int
    incidencias: list[IncidenciaSNMP]

    def contar_por_nivel(self) -> dict[str, int]:
        """
        Cuenta incidencias por nivel.
        """
        contador = Counter(
            incidencia.nivel
            for incidencia in self.incidencias
        )

        return {
            "criticas": contador.get(
                ReglasSNMP.NIVEL_CRITICO,
                0
            ),
            "advertencias": contador.get(
                ReglasSNMP.NIVEL_ADVERTENCIA,
                0
            ),
            "informativas": contador.get(
                ReglasSNMP.NIVEL_INFORMATIVO,
                0
            ),
            "total": len(
                self.incidencias
            )
        }

    def contar_por_categoria(self) -> dict[str, int]:
        """
        Cuenta incidencias por categoría.
        """
        return dict(
            Counter(
                incidencia.categoria
                for incidencia in self.incidencias
            )
        )

    def obtener_estado_general(self) -> str:
        """
        Determina el estado global del análisis.
        """
        resumen = self.contar_por_nivel()

        if resumen["criticas"] > 0:
            return "REQUIERE ATENCIÓN"

        if resumen["advertencias"] > 0:
            return "CON OBSERVACIONES"

        if resumen["informativas"] > 0:
            return "SIN FALLAS CRÍTICAS"

        return "SIN INCIDENCIAS"

    def convertir_diccionario(self) -> dict[str, Any]:
        """
        Convierte todo el análisis en un diccionario.
        """
        return {
            "ip_switch": self.ip_switch,
            "interfaces_analizadas": (
                self.interfaces_analizadas
            ),
            "estado_general": (
                self.obtener_estado_general()
            ),
            "resumen": self.contar_por_nivel(),
            "categorias": (
                self.contar_por_categoria()
            ),
            "incidencias": [
                incidencia.convertir_diccionario()
                for incidencia in self.incidencias
            ]
        }


class AnalizadorSNMP:
    """
    Motor de análisis conservador para NetInventory.

    Recibe datos ya obtenidos por SNMP y ejecuta reglas
    independientes.

    No consulta switches.
    No modifica configuraciones.
    No utiliza el inventario Excel.
    """

    ORDEN_NIVELES = {
        ReglasSNMP.NIVEL_CRITICO: 1,
        ReglasSNMP.NIVEL_ADVERTENCIA: 2,
        ReglasSNMP.NIVEL_INFORMATIVO: 3
    }

    def __init__(
        self,
        reglas=None
    ):
        self.reglas = (
            reglas
            if reglas is not None
            else ReglasSNMP
        )

    @staticmethod
    def obtener_ip(
        ip_switch: str | None
    ) -> str | None:
        """
        Normaliza la IP visible del switch.
        """
        if ip_switch is None:
            return None

        texto = str(
            ip_switch
        ).strip()

        return texto or None

    def analizar_interfaz(
        self,
        interfaz: dict[str, Any],
        ip_switch: str | None = None
    ) -> list[IncidenciaSNMP]:
        """
        Ejecuta todas las reglas aplicables a una interfaz.
        """
        incidencias = []

        reglas_interfaz = [
            self.reglas.detectar_enlace_10_mbps,
            self.reglas.detectar_errores_nuevos,
            self.reglas.detectar_utilizacion_elevada
        ]

        for regla in reglas_interfaz:
            incidencia = regla(
                interfaz=interfaz,
                ip_switch=ip_switch
            )

            if incidencia is not None:
                incidencias.append(
                    incidencia
                )

        return incidencias

    def analizar_sistema(
        self,
        informacion_sistema: dict[str, Any] | None,
        ip_switch: str | None = None
    ) -> list[IncidenciaSNMP]:
        """
        Ejecuta las reglas correspondientes al switch.
        """
        if not informacion_sistema:
            return []

        incidencia = (
            self.reglas.detectar_reinicio_reciente(
                informacion_sistema=(
                    informacion_sistema
                ),
                ip_switch=ip_switch
            )
        )

        if incidencia is None:
            return []

        return [
            incidencia
        ]

    def ordenar_incidencias(
        self,
        incidencias: list[IncidenciaSNMP]
    ) -> list[IncidenciaSNMP]:
        """
        Ordena primero los casos más importantes.
        """
        return sorted(
            incidencias,
            key=lambda incidencia: (
                self.ORDEN_NIVELES.get(
                    incidencia.nivel,
                    99
                ),
                incidencia.categoria,
                incidencia.puerto or "",
                incidencia.titulo
            )
        )

    def analizar(
        self,
        interfaces: list[dict[str, Any]],
        informacion_sistema: (
            dict[str, Any] | None
        ) = None,
        ip_switch: str | None = None
    ) -> ResultadoAnalisisSNMP:
        """
        Analiza las interfaces y la información general
        de un switch.
        """
        ip_switch = self.obtener_ip(
            ip_switch
        )

        incidencias = []

        for interfaz in interfaces:
            incidencias.extend(
                self.analizar_interfaz(
                    interfaz=interfaz,
                    ip_switch=ip_switch
                )
            )

        incidencias.extend(
            self.analizar_sistema(
                informacion_sistema=(
                    informacion_sistema
                ),
                ip_switch=ip_switch
            )
        )

        incidencias = self.ordenar_incidencias(
            incidencias
        )

        return ResultadoAnalisisSNMP(
            ip_switch=ip_switch,
            interfaces_analizadas=len(
                interfaces
            ),
            incidencias=incidencias
        )