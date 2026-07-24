import asyncio
from dataclasses import dataclass
from typing import Any

from pysnmp.hlapi.v1arch.asyncio import (
    CommunityData,
    ObjectIdentity,
    ObjectType,
    SnmpDispatcher,
    UdpTransportTarget,
    bulk_walk_cmd,
    get_cmd
)


@dataclass
class ResultadoSNMP:
    """
    Representa el resultado uniforme de una consulta SNMP.
    """

    correcto: bool
    datos: Any
    error: str | None = None
    comunidad_utilizada: str | None = None


class ClienteSNMP:
    """
    Cliente SNMP v2c de solo lectura para NetInventory.

    Puede probar automáticamente varias comunidades hasta
    encontrar una que responda.

    La comunidad válida se conserva temporalmente por IP
    para evitar repetir intentos innecesarios.

    Solo implementa operaciones GET y GETBULK.
    No contiene operaciones SNMP SET.
    """

    OIDS_SISTEMA = {
        "descripcion": "1.3.6.1.2.1.1.1.0",
        "oid_sistema": "1.3.6.1.2.1.1.2.0",
        "uptime": "1.3.6.1.2.1.1.3.0",
        "contacto": "1.3.6.1.2.1.1.4.0",
        "nombre": "1.3.6.1.2.1.1.5.0",
        "ubicacion": "1.3.6.1.2.1.1.6.0",
        "servicios": "1.3.6.1.2.1.1.7.0"
    }

    OIDS_INTERFACES = {
        "indice": "1.3.6.1.2.1.2.2.1.1",
        "descripcion": "1.3.6.1.2.1.2.2.1.2",
        "tipo": "1.3.6.1.2.1.2.2.1.3",
        "mtu": "1.3.6.1.2.1.2.2.1.4",
        "velocidad": "1.3.6.1.2.1.2.2.1.5",
        "mac": "1.3.6.1.2.1.2.2.1.6",
        "estado_administrativo": "1.3.6.1.2.1.2.2.1.7",
        "estado_operativo": "1.3.6.1.2.1.2.2.1.8",
        "ultimo_cambio": "1.3.6.1.2.1.2.2.1.9",

        # Contadores de tráfico de alta capacidad, 64 bits.
        "bytes_entrada": "1.3.6.1.2.1.31.1.1.1.6",
        "bytes_salida": "1.3.6.1.2.1.31.1.1.1.10",

        "errores_entrada": "1.3.6.1.2.1.2.2.1.14",
        "errores_salida": "1.3.6.1.2.1.2.2.1.20",

        "nombre": "1.3.6.1.2.1.31.1.1.1.1",
        "velocidad_alta": "1.3.6.1.2.1.31.1.1.1.15"
    }

    ESTADOS_ADMINISTRATIVOS = {
        "1": "UP",
        "2": "DOWN",
        "3": "TESTING"
    }

    ESTADOS_OPERATIVOS = {
        "1": "UP",
        "2": "DOWN",
        "3": "TESTING",
        "4": "UNKNOWN",
        "5": "DORMANT",
        "6": "NOT PRESENT",
        "7": "LOWER LAYER DOWN"
    }

    def __init__(
        self,
        comunidades: list[str] | tuple[str, ...] | str,
        puerto: int = 161,
        timeout: float = 3,
        reintentos: int = 1
    ):
        self.comunidades = self.normalizar_comunidades(
            comunidades
        )

        if not self.comunidades:
            raise ValueError(
                "Debe configurarse al menos una comunidad SNMP."
            )

        self.puerto = int(
            puerto
        )

        self.timeout = float(
            timeout
        )

        self.reintentos = int(
            reintentos
        )

        # Guarda en memoria la comunidad correcta para cada IP.
        self.comunidades_por_ip: dict[str, str] = {}

    @staticmethod
    def normalizar_comunidades(
        comunidades
    ) -> list[str]:
        """
        Convierte texto, lista o tupla en una lista limpia,
        ordenada y sin comunidades duplicadas.
        """
        if comunidades is None:
            return []

        if isinstance(
            comunidades,
            str
        ):
            elementos = comunidades.split(",")

        else:
            elementos = list(
                comunidades
            )

        resultados = []
        vistas = set()

        for comunidad in elementos:
            texto = str(
                comunidad or ""
            ).strip()

            if not texto:
                continue

            if texto in vistas:
                continue

            vistas.add(
                texto
            )

            resultados.append(
                texto
            )

        return resultados

    @staticmethod
    def validar_ip(
        ip: str
    ) -> str:
        """
        Valida una dirección IPv4.
        """
        ip = str(
            ip or ""
        ).strip()

        partes = ip.split(".")

        if len(partes) != 4:
            raise ValueError(
                "La dirección IP no tiene un formato válido."
            )

        try:
            octetos = [
                int(parte)
                for parte in partes
            ]

        except ValueError as error:
            raise ValueError(
                "La dirección IP contiene valores no numéricos."
            ) from error

        if any(
            octeto < 0 or octeto > 255
            for octeto in octetos
        ):
            raise ValueError(
                "La dirección IP contiene un octeto inválido."
            )

        return ip

    @staticmethod
    def convertir_valor(
        valor: Any
    ) -> str | None:
        """
        Convierte valores PySNMP en texto.
        """
        if valor is None:
            return None

        try:
            return valor.prettyPrint()

        except AttributeError:
            return str(
                valor
            )

    @staticmethod
    def convertir_entero(
        valor: Any,
        predeterminado: int = 0
    ) -> int:
        """
        Convierte valores SNMP numéricos a entero.
        """
        if valor is None:
            return predeterminado

        try:
            return int(
                str(valor)
            )

        except (
            ValueError,
            TypeError
        ):
            return predeterminado

    @staticmethod
    def convertir_uptime(
        valor: str | int | None
    ) -> dict[str, Any]:
        """
        Convierte centésimas de segundo a texto legible.
        """
        if valor is None:
            return {
                "centisegundos": None,
                "segundos": None,
                "texto": "Sin información"
            }

        try:
            centisegundos = int(
                str(valor)
            )

        except ValueError:
            return {
                "centisegundos": None,
                "segundos": None,
                "texto": str(valor)
            }

        segundos_totales = (
            centisegundos // 100
        )

        dias, resto = divmod(
            segundos_totales,
            86400
        )

        horas, resto = divmod(
            resto,
            3600
        )

        minutos, segundos = divmod(
            resto,
            60
        )

        return {
            "centisegundos": centisegundos,
            "segundos": segundos_totales,
            "dias": dias,
            "horas": horas,
            "minutos": minutos,
            "segundos_restantes": segundos,
            "texto": (
                f"{dias} días, "
                f"{horas:02d}:{minutos:02d}:{segundos:02d}"
            )
        }

    @staticmethod
    def convertir_bytes(
        cantidad: int
    ) -> str:
        """
        Convierte bytes a una unidad legible.
        """
        cantidad = max(
            int(cantidad),
            0
        )

        unidades = [
            "B",
            "KB",
            "MB",
            "GB",
            "TB",
            "PB"
        ]

        valor = float(
            cantidad
        )

        for unidad in unidades:
            if (
                valor < 1024
                or unidad == unidades[-1]
            ):
                return (
                    f"{valor:.2f} {unidad}"
                )

            valor /= 1024

        return f"{cantidad} B"

    @staticmethod
    def convertir_velocidad(
        bits_por_segundo: int
    ) -> str:
        """
        Convierte bits por segundo a texto legible.
        """
        if bits_por_segundo <= 0:
            return "Sin información"

        if bits_por_segundo >= 1_000_000_000:
            return (
                f"{bits_por_segundo / 1_000_000_000:.2f} Gbps"
            )

        if bits_por_segundo >= 1_000_000:
            return (
                f"{bits_por_segundo / 1_000_000:.0f} Mbps"
            )

        if bits_por_segundo >= 1_000:
            return (
                f"{bits_por_segundo / 1_000:.0f} Kbps"
            )

        return (
            f"{bits_por_segundo} bps"
        )

    async def _crear_destino(
        self,
        ip: str
    ):
        """
        Crea el destino UDP para una consulta SNMP.
        """
        return await UdpTransportTarget.create(
            (
                ip,
                self.puerto
            ),
            timeout=self.timeout,
            retries=self.reintentos
        )

    def obtener_comunidades_para_ip(
        self,
        ip: str
    ) -> list[str]:
        """
        Prioriza la comunidad que ya funcionó para una IP.

        Si todavía no se conoce, devuelve todas las
        comunidades configuradas en su orden original.
        """
        comunidad_conocida = (
            self.comunidades_por_ip.get(
                ip
            )
        )

        if comunidad_conocida is None:
            return list(
                self.comunidades
            )

        return [
            comunidad_conocida,
            *[
                comunidad
                for comunidad in self.comunidades
                if comunidad != comunidad_conocida
            ]
        ]

    def guardar_comunidad_correcta(
        self,
        ip: str,
        comunidad: str
    ):
        """
        Guarda temporalmente la comunidad válida de una IP.
        """
        self.comunidades_por_ip[
            ip
        ] = comunidad

    def olvidar_comunidad_ip(
        self,
        ip: str
    ):
        """
        Elimina una comunidad almacenada temporalmente.
        """
        self.comunidades_por_ip.pop(
            ip,
            None
        )

    async def _consultar_oids_con_comunidad(
        self,
        ip: str,
        comunidad: str,
        oids: dict[str, str]
    ) -> ResultadoSNMP:
        """
        Ejecuta una consulta GET usando una comunidad.
        """
        dispatcher = SnmpDispatcher()

        try:
            destino = await self._crear_destino(
                ip
            )

            objetos = [
                ObjectType(
                    ObjectIdentity(
                        oid
                    )
                )
                for oid in oids.values()
            ]

            (
                error_indicacion,
                error_estado,
                error_indice,
                variables
            ) = await get_cmd(
                dispatcher,
                CommunityData(
                    comunidad,
                    mpModel=1
                ),
                destino,
                *objetos,
                lookupMib=False
            )

            if error_indicacion:
                return ResultadoSNMP(
                    correcto=False,
                    datos={},
                    error=str(
                        error_indicacion
                    )
                )

            if error_estado:
                posicion = int(
                    error_indice or 0
                )

                detalle = (
                    error_estado.prettyPrint()
                    if hasattr(
                        error_estado,
                        "prettyPrint"
                    )
                    else str(error_estado)
                )

                if posicion > 0:
                    detalle += (
                        f" en el OID número {posicion}"
                    )

                return ResultadoSNMP(
                    correcto=False,
                    datos={},
                    error=detalle
                )

            claves = list(
                oids.keys()
            )

            datos = {}

            for clave, variable in zip(
                claves,
                variables
            ):
                _oid_respuesta, valor = variable

                datos[clave] = (
                    self.convertir_valor(
                        valor
                    )
                )

            return ResultadoSNMP(
                correcto=True,
                datos=datos,
                comunidad_utilizada=comunidad
            )

        except Exception as error:
            return ResultadoSNMP(
                correcto=False,
                datos={},
                error=(
                    "Error durante la consulta SNMP: "
                    f"{error}"
                )
            )

        finally:
            dispatcher.transport_dispatcher.close_dispatcher()

    async def _consultar_oids(
        self,
        ip: str,
        oids: dict[str, str]
    ) -> ResultadoSNMP:
        """
        Prueba las comunidades configuradas hasta que una
        responda correctamente.
        """
        ip = self.validar_ip(
            ip
        )

        errores = []

        for comunidad in self.obtener_comunidades_para_ip(
            ip
        ):
            resultado = (
                await self._consultar_oids_con_comunidad(
                    ip=ip,
                    comunidad=comunidad,
                    oids=oids
                )
            )

            if resultado.correcto:
                self.guardar_comunidad_correcta(
                    ip,
                    comunidad
                )

                return resultado

            errores.append(
                resultado.error
                or "Sin respuesta"
            )

        self.olvidar_comunidad_ip(
            ip
        )

        return ResultadoSNMP(
            correcto=False,
            datos={},
            error=(
                "Ninguna comunidad SNMP configurada "
                "obtuvo respuesta. "
                f"Último detalle: {errores[-1]}"
                if errores
                else "No se configuraron comunidades."
            )
        )

    async def _recorrer_oid_con_comunidad(
        self,
        ip: str,
        comunidad: str,
        oid_base: str
    ) -> ResultadoSNMP:
        """
        Recorre un árbol OID con una comunidad concreta.
        """
        dispatcher = SnmpDispatcher()
        resultados = {}

        try:
            destino = await self._crear_destino(
                ip
            )

            generador = bulk_walk_cmd(
                dispatcher,
                CommunityData(
                    comunidad,
                    mpModel=1
                ),
                destino,
                0,
                25,
                ObjectType(
                    ObjectIdentity(
                        oid_base
                    )
                ),
                lookupMib=False,
                lexicographicMode=False
            )

            async for (
                error_indicacion,
                error_estado,
                _error_indice,
                variables
            ) in generador:
                if error_indicacion:
                    return ResultadoSNMP(
                        correcto=False,
                        datos={},
                        error=str(
                            error_indicacion
                        )
                    )

                if error_estado:
                    detalle = (
                        error_estado.prettyPrint()
                        if hasattr(
                            error_estado,
                            "prettyPrint"
                        )
                        else str(error_estado)
                    )

                    return ResultadoSNMP(
                        correcto=False,
                        datos={},
                        error=detalle
                    )

                for variable in variables:
                    oid_respuesta, valor = variable

                    oid_texto = (
                        oid_respuesta.prettyPrint()
                    )

                    indice = oid_texto.rsplit(
                        ".",
                        1
                    )[-1]

                    resultados[
                        indice
                    ] = self.convertir_valor(
                        valor
                    )

            return ResultadoSNMP(
                correcto=True,
                datos=resultados,
                comunidad_utilizada=comunidad
            )

        except Exception as error:
            return ResultadoSNMP(
                correcto=False,
                datos={},
                error=(
                    "Error recorriendo el OID "
                    f"{oid_base}: {error}"
                )
            )

        finally:
            dispatcher.transport_dispatcher.close_dispatcher()

    async def _recorrer_oid(
        self,
        ip: str,
        oid_base: str
    ) -> ResultadoSNMP:
        """
        Recorre un OID probando las comunidades configuradas.
        """
        ip = self.validar_ip(
            ip
        )

        errores = []

        for comunidad in self.obtener_comunidades_para_ip(
            ip
        ):
            resultado = (
                await self._recorrer_oid_con_comunidad(
                    ip=ip,
                    comunidad=comunidad,
                    oid_base=oid_base
                )
            )

            if resultado.correcto:
                self.guardar_comunidad_correcta(
                    ip,
                    comunidad
                )

                return resultado

            errores.append(
                resultado.error
                or "Sin respuesta"
            )

        self.olvidar_comunidad_ip(
            ip
        )

        return ResultadoSNMP(
            correcto=False,
            datos={},
            error=(
                "Ninguna comunidad SNMP configurada "
                f"permitió recorrer {oid_base}. "
                f"Último detalle: {errores[-1]}"
                if errores
                else (
                    "No se configuraron comunidades SNMP."
                )
            )
        )

    async def obtener_informacion_sistema_async(
        self,
        ip: str
    ) -> ResultadoSNMP:
        """
        Consulta los objetos estándar del grupo system.
        """
        ip = self.validar_ip(
            ip
        )

        resultado = await self._consultar_oids(
            ip=ip,
            oids=self.OIDS_SISTEMA
        )

        if not resultado.correcto:
            return resultado

        uptime_original = resultado.datos.get(
            "uptime"
        )

        resultado.datos[
            "uptime_original"
        ] = uptime_original

        resultado.datos[
            "uptime"
        ] = self.convertir_uptime(
            uptime_original
        )

        resultado.datos[
            "ip"
        ] = ip

        return resultado

    def obtener_informacion_sistema(
        self,
        ip: str
    ) -> ResultadoSNMP:
        """
        Versión síncrona para información del sistema.
        """
        return asyncio.run(
            self.obtener_informacion_sistema_async(
                ip
            )
        )

    async def obtener_interfaces_async(
        self,
        ip: str
    ) -> ResultadoSNMP:
        """
        Obtiene y combina las tablas estándar de interfaces.
        """
        ip = self.validar_ip(
            ip
        )

        # Primero obtiene sysName para descubrir y almacenar
        # rápidamente la comunidad válida del dispositivo.
        prueba = await self._consultar_oids(
            ip=ip,
            oids={
                "nombre": self.OIDS_SISTEMA[
                    "nombre"
                ]
            }
        )

        if not prueba.correcto:
            return ResultadoSNMP(
                correcto=False,
                datos=[],
                error=prueba.error
            )

        tablas = {}

        for nombre, oid in self.OIDS_INTERFACES.items():
            resultado = await self._recorrer_oid(
                ip=ip,
                oid_base=oid
            )

            if not resultado.correcto:
                return ResultadoSNMP(
                    correcto=False,
                    datos=[],
                    error=(
                        f"No se pudo consultar {nombre}: "
                        f"{resultado.error}"
                    )
                )

            tablas[
                nombre
            ] = resultado.datos

        indices = set()

        for tabla in tablas.values():
            indices.update(
                tabla.keys()
            )

        interfaces = []

        for indice in indices:
            velocidad = self.convertir_entero(
                tablas[
                    "velocidad"
                ].get(
                    indice
                )
            )

            velocidad_alta_mbps = (
                self.convertir_entero(
                    tablas[
                        "velocidad_alta"
                    ].get(
                        indice
                    )
                )
            )

            if velocidad_alta_mbps > 0:
                velocidad = (
                    velocidad_alta_mbps
                    * 1_000_000
                )

            estado_admin_codigo = str(
                tablas[
                    "estado_administrativo"
                ].get(
                    indice,
                    ""
                )
            )

            estado_operativo_codigo = str(
                tablas[
                    "estado_operativo"
                ].get(
                    indice,
                    ""
                )
            )

            bytes_entrada = self.convertir_entero(
                tablas[
                    "bytes_entrada"
                ].get(
                    indice
                )
            )

            bytes_salida = self.convertir_entero(
                tablas[
                    "bytes_salida"
                ].get(
                    indice
                )
            )

            interfaz = {
                "indice": self.convertir_entero(
                    indice
                ),
                "nombre": (
                    tablas[
                        "nombre"
                    ].get(
                        indice
                    )
                    or tablas[
                        "descripcion"
                    ].get(
                        indice
                    )
                    or f"Interfaz {indice}"
                ),
                "descripcion": tablas[
                    "descripcion"
                ].get(
                    indice
                ),
                "tipo": self.convertir_entero(
                    tablas[
                        "tipo"
                    ].get(
                        indice
                    )
                ),
                "mtu": self.convertir_entero(
                    tablas[
                        "mtu"
                    ].get(
                        indice
                    )
                ),
                "mac": tablas[
                    "mac"
                ].get(
                    indice
                ),
                "estado_administrativo_codigo": (
                    estado_admin_codigo
                ),
                "estado_administrativo": (
                    self.ESTADOS_ADMINISTRATIVOS.get(
                        estado_admin_codigo,
                        "DESCONOCIDO"
                    )
                ),
                "estado_operativo_codigo": (
                    estado_operativo_codigo
                ),
                "estado_operativo": (
                    self.ESTADOS_OPERATIVOS.get(
                        estado_operativo_codigo,
                        "DESCONOCIDO"
                    )
                ),
                "velocidad_bps": velocidad,
                "velocidad": self.convertir_velocidad(
                    velocidad
                ),
                "bytes_entrada": bytes_entrada,
                "entrada": self.convertir_bytes(
                    bytes_entrada
                ),
                "bytes_salida": bytes_salida,
                "salida": self.convertir_bytes(
                    bytes_salida
                ),
                "errores_entrada": (
                    self.convertir_entero(
                        tablas[
                            "errores_entrada"
                        ].get(
                            indice
                        )
                    )
                ),
                "errores_salida": (
                    self.convertir_entero(
                        tablas[
                            "errores_salida"
                        ].get(
                            indice
                        )
                    )
                ),
                "ultimo_cambio": tablas[
                    "ultimo_cambio"
                ].get(
                    indice
                )
            }

            interfaces.append(
                interfaz
            )

        interfaces.sort(
            key=lambda interfaz: (
                interfaz["indice"]
            )
        )

        return ResultadoSNMP(
            correcto=True,
            datos=interfaces,
            comunidad_utilizada=(
                self.comunidades_por_ip.get(
                    ip
                )
            )
        )

    def obtener_interfaces(
        self,
        ip: str
    ) -> ResultadoSNMP:
        """
        Versión síncrona para consultar interfaces.
        """
        return asyncio.run(
            self.obtener_interfaces_async(
                ip
            )
        )

    def probar_conectividad(
        self,
        ip: str
    ) -> ResultadoSNMP:
        """
        Comprueba SNMP consultando sysName.0.
        """
        return asyncio.run(
            self._consultar_oids(
                ip=ip,
                oids={
                    "nombre": self.OIDS_SISTEMA[
                        "nombre"
                    ]
                }
            )
        )


    def probar_comunidad_tecnica(
        self,
        ip: str,
        comunidad: str,
        oid: str = "1.3.6.1.2.1.1.1.0"
    ) -> ResultadoSNMP:
        """
        Ejecuta una única consulta SNMP v2c usando una
        comunidad concreta y un OID concreto.

        Este método está pensado para diagnóstico técnico.
        No prueba otras comunidades ni altera la comunidad
        almacenada temporalmente para la IP.
        """
        ip = self.validar_ip(
            ip
        )

        comunidad = str(
            comunidad or ""
        ).strip()

        oid = str(
            oid or ""
        ).strip()

        if not comunidad:
            raise ValueError(
                "La comunidad SNMP no puede estar vacía."
            )

        if not oid:
            raise ValueError(
                "El OID no puede estar vacío."
            )

        return asyncio.run(
            self._consultar_oids_con_comunidad(
                ip=ip,
                comunidad=comunidad,
                oids={
                    "valor": oid
                }
            )
        )

    def probar_todas_las_comunidades_tecnicas(
        self,
        ip: str,
        oid: str = "1.3.6.1.2.1.1.1.0"
    ) -> list[dict]:
        """
        Prueba individualmente todas las comunidades
        configuradas y conserva el detalle de cada intento.
        """
        ip = self.validar_ip(
            ip
        )

        resultados = []

        for comunidad in self.obtener_comunidades_para_ip(
            ip
        ):
            resultado = self.probar_comunidad_tecnica(
                ip=ip,
                comunidad=comunidad,
                oid=oid
            )

            resultados.append(
                {
                    "comunidad": comunidad,
                    "correcto": resultado.correcto,
                    "datos": resultado.datos,
                    "error": resultado.error
                }
            )

        return resultados

    def obtener_comunidad_en_uso(
        self,
        ip: str
    ) -> str | None:
        """
        Devuelve la comunidad detectada para una IP.

        Este método debe usarse solo para diagnóstico
        interno. No conviene mostrar la comunidad en
        pantallas o reportes compartidos.
        """
        ip = self.validar_ip(
            ip
        )

        return self.comunidades_por_ip.get(
            ip
        )