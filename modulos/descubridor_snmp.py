from collections import Counter
from dataclasses import dataclass
from time import perf_counter
from typing import Any

from modulos.snmp_cliente import ClienteSNMP


@dataclass
class ResultadoSwitchDescubierto:
    """
    Representa el resultado de una comprobación SNMP
    sobre un switch registrado.

    No contiene contraseñas ni usuarios administrativos.
    """

    ip: str
    estado: str

    ubicacion: str | None = None
    marca: str | None = None
    modelo: str | None = None

    nombre_snmp: str | None = None
    descripcion_snmp: str | None = None

    tiempo_ms: float | None = None
    detalle: str | None = None

    def convertir_diccionario(
        self
    ) -> dict[str, Any]:
        """
        Convierte el resultado en un diccionario común.
        """
        return {
            "ip": self.ip,
            "estado": self.estado,
            "ubicacion": self.ubicacion,
            "marca": self.marca,
            "modelo": self.modelo,
            "nombre_snmp": self.nombre_snmp,
            "descripcion_snmp": self.descripcion_snmp,
            "tiempo_ms": self.tiempo_ms,
            "detalle": self.detalle
        }


@dataclass
class ResultadoDescubrimientoSNMP:
    """
    Contiene el resultado completo del descubrimiento.
    """

    resultados: list[ResultadoSwitchDescubierto]
    ips_duplicadas: list[str]
    registros_sin_ip: int
    registros_ip_invalida: int
    duracion_total: float

    def obtener_por_estado(
        self,
        estado: str
    ) -> list[ResultadoSwitchDescubierto]:
        """
        Filtra resultados por estado.
        """
        return [
            resultado
            for resultado in self.resultados
            if resultado.estado == estado
        ]

    def obtener_resumen(
        self
    ) -> dict[str, Any]:
        """
        Calcula estadísticas generales.
        """
        respondieron = self.obtener_por_estado(
            DescubridorSNMP.ESTADO_RESPONDE
        )

        sin_respuesta = self.obtener_por_estado(
            DescubridorSNMP.ESTADO_SIN_RESPUESTA
        )

        tiempos = [
            resultado.tiempo_ms
            for resultado in respondieron
            if resultado.tiempo_ms is not None
        ]

        tiempo_promedio = (
            round(
                sum(tiempos) / len(tiempos),
                2
            )
            if tiempos
            else None
        )

        return {
            "revisados": len(
                self.resultados
            ),
            "respondieron": len(
                respondieron
            ),
            "sin_respuesta": len(
                sin_respuesta
            ),
            "ips_duplicadas": len(
                self.ips_duplicadas
            ),
            "registros_sin_ip": (
                self.registros_sin_ip
            ),
            "registros_ip_invalida": (
                self.registros_ip_invalida
            ),
            "tiempo_promedio_ms": (
                tiempo_promedio
            ),
            "duracion_total": round(
                self.duracion_total,
                2
            )
        }


class DescubridorSNMP:
    """
    Revisa rápidamente todos los switches almacenados
    en SQLite mediante una consulta SNMP liviana.

    Este módulo:

    - No consulta interfaces.
    - No mide tráfico.
    - No utiliza el Excel.
    - No modifica switches.
    - No muestra ni almacena las comunidades utilizadas.
    """

    ESTADO_RESPONDE = "RESPONDE"
    ESTADO_SIN_RESPUESTA = "SIN RESPUESTA"

    def __init__(
        self,
        cliente_snmp: ClienteSNMP,
        gestor_accesos
    ):
        self.cliente_snmp = cliente_snmp
        self.gestor_accesos = gestor_accesos

    @staticmethod
    def normalizar_valor(
        valor: Any
    ) -> str | None:
        """
        Convierte un valor en texto limpio.
        """
        if valor is None:
            return None

        texto = str(
            valor
        ).strip()

        return texto or None

    @staticmethod
    def limpiar_valor_snmp(
        valor: Any
    ) -> str | None:
        """
        Limpia comillas externas de valores SNMP.
        """
        if valor is None:
            return None

        texto = str(
            valor
        ).strip()

        if not texto:
            return None

        return texto.strip(
            '"'
        )

    def obtener_switches_registrados(
        self
    ) -> list[dict]:
        """
        Obtiene todos los switches desde SQLite.
        """
        switches = (
            self.gestor_accesos
            .listar_todos()
        )

        return list(
            switches or []
        )

    def detectar_ips_duplicadas(
        self,
        switches: list[dict]
    ) -> list[str]:
        """
        Detecta direcciones IP repetidas en SQLite.
        """
        contador = Counter()

        for switch in switches:
            ip = self.normalizar_valor(
                switch.get("ip")
            )

            if ip:
                contador[ip] += 1

        return sorted(
            [
                ip
                for ip, cantidad in contador.items()
                if cantidad > 1
            ],
            key=self.clave_ip
        )

    @staticmethod
    def clave_ip(
        ip: str
    ) -> tuple[int, int, int, int]:
        """
        Crea una clave para ordenar IPv4 numéricamente.
        """
        try:
            partes = tuple(
                int(parte)
                for parte in str(ip).split(".")
            )

            if len(partes) == 4:
                return partes

        except (
            ValueError,
            TypeError
        ):
            pass

        return (
            999,
            999,
            999,
            999
        )

    def ordenar_switches(
        self,
        switches: list[dict]
    ) -> list[dict]:
        """
        Ordena los switches por dirección IP.
        """
        return sorted(
            switches,
            key=lambda switch: self.clave_ip(
                self.normalizar_valor(
                    switch.get("ip")
                )
                or ""
            )
        )

    def comprobar_switch(
        self,
        switch: dict
    ) -> ResultadoSwitchDescubierto:
        """
        Ejecuta una consulta liviana al grupo system.

        La consulta permite obtener nombre y descripción
        además de confirmar que SNMP responde.
        """
        ip = self.normalizar_valor(
            switch.get("ip")
        )

        if ip is None:
            raise ValueError(
                "No se puede comprobar un switch sin IP."
            )

        inicio = perf_counter()

        prueba = (
            self.cliente_snmp
            .probar_conectividad(
                ip
            )
        )

        tiempo_ms = round(
            (
                perf_counter()
                - inicio
            ) * 1000,
            2
        )

        datos_comunes = {
            "ip": ip,
            "ubicacion": self.normalizar_valor(
                switch.get("ubicacion")
            ),
            "marca": self.normalizar_valor(
                switch.get("marca")
            ),
            "modelo": self.normalizar_valor(
                switch.get("modelo")
            ),
            "tiempo_ms": tiempo_ms
        }

        if not prueba.correcto:
            return ResultadoSwitchDescubierto(
                estado=self.ESTADO_SIN_RESPUESTA,
                detalle=(
                    prueba.error
                    or "El equipo no respondió por SNMP."
                ),
                **datos_comunes
            )

        nombre_snmp = self.limpiar_valor_snmp(
            (prueba.datos or {}).get("nombre")
        )

        informacion = (
            self.cliente_snmp
            .obtener_informacion_sistema(
                ip
            )
        )

        if not informacion.correcto:
            return ResultadoSwitchDescubierto(
                estado=self.ESTADO_RESPONDE,
                nombre_snmp=nombre_snmp,
                descripcion_snmp=None,
                detalle=(
                    "El switch respondió a la prueba SNMP "
                    "mínima, pero no fue posible obtener toda "
                    "la información del grupo system. "
                    f"Detalle: {informacion.error or 'Sin detalle'}"
                ),
                **datos_comunes
            )

        datos = informacion.datos or {}

        return ResultadoSwitchDescubierto(
            estado=self.ESTADO_RESPONDE,
            nombre_snmp=(
                self.limpiar_valor_snmp(
                    datos.get("nombre")
                )
                or nombre_snmp
            ),
            descripcion_snmp=(
                self.limpiar_valor_snmp(
                    datos.get("descripcion")
                )
            ),
            detalle=None,
            **datos_comunes
        )

    def ejecutar(
        self,
        notificar_progreso=None
    ) -> ResultadoDescubrimientoSNMP:
        """
        Revisa todos los switches con IP válida.

        notificar_progreso puede ser una función que reciba:

            numero_actual,
            total,
            switch
        """
        inicio_general = perf_counter()

        switches = self.obtener_switches_registrados()

        ips_duplicadas = self.detectar_ips_duplicadas(
            switches
        )

        registros_sin_ip = 0
        registros_ip_invalida = 0
        switches_validos = []

        for switch in switches:
            ip = self.normalizar_valor(
                switch.get("ip")
            )

            if not ip:
                registros_sin_ip += 1
                continue

            try:
                self.cliente_snmp.validar_ip(
                    ip
                )

            except ValueError:
                registros_ip_invalida += 1
                continue

            switches_validos.append(
                switch
            )

        switches_validos = self.ordenar_switches(
            switches_validos
        )

        resultados = []
        total = len(
            switches_validos
        )

        for numero, switch in enumerate(
            switches_validos,
            start=1
        ):
            if notificar_progreso is not None:
                notificar_progreso(
                    numero,
                    total,
                    switch
                )

            resultado = self.comprobar_switch(
                switch
            )

            resultados.append(
                resultado
            )

        duracion_total = (
            perf_counter()
            - inicio_general
        )

        return ResultadoDescubrimientoSNMP(
            resultados=resultados,
            ips_duplicadas=ips_duplicadas,
            registros_sin_ip=registros_sin_ip,
            registros_ip_invalida=(
                registros_ip_invalida
            ),
            duracion_total=duracion_total
        )