from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from ipaddress import IPv4Address, ip_network

from modulos.registrador_dispositivo_snmp import RegistradorDispositivoSNMP
from modulos.visual import visual


@dataclass
class DispositivoDescubierto:
    ip: str
    comunidad: str | None
    nombre: str | None
    descripcion: str | None
    registrado: bool


class DescubridorRedSNMP:
    """Busca dispositivos SNMP en una subred privada. Solo lectura."""

    OID_SYS_DESCR = "1.3.6.1.2.1.1.1.0"
    OID_SYS_NAME = "1.3.6.1.2.1.1.5.0"
    MAX_HOSTS = 1022
    MAX_TRABAJADORES = 32

    def __init__(self, cliente_snmp, gestor_accesos):
        self.cliente_snmp = cliente_snmp
        self.gestor_accesos = gestor_accesos

        self.registrador = RegistradorDispositivoSNMP(
            gestor_accesos
        )

        self.ultimo_resultado = []

    @staticmethod
    def _valor(valor):
        if valor is None:
            return None
        texto = str(valor).strip()
        return texto or None

    def validar_red(self, texto):
        try:
            red = ip_network(texto.strip(), strict=False)
        except ValueError as error:
            raise ValueError(
                "Escribe una red CIDR válida, por ejemplo 192.168.4.0/23."
            ) from error

        if red.version != 4:
            raise ValueError("Solo se admiten redes IPv4.")

        if not red.is_private:
            raise ValueError(
                "Por seguridad, solo se admiten redes IPv4 privadas."
            )

        hosts = max(int(red.num_addresses) - 2, 0)

        if hosts > self.MAX_HOSTS:
            raise ValueError(
                f"La red supera el máximo permitido de {self.MAX_HOSTS} hosts."
            )

        return red

    def ips_registradas(self):
        return {
            str(item.get("ip")).strip()
            for item in self.gestor_accesos.listar_todos()
            if item.get("ip")
        }

    def consultar_oid(self, ip, oid):
        try:
            resultados = (
                self.cliente_snmp
                .probar_todas_las_comunidades_tecnicas(
                    ip=ip,
                    oid=oid
                )
            )
        except Exception:
            return None, None

        for resultado in resultados or []:
            if not resultado.get("correcto"):
                continue

            datos = resultado.get("datos") or {}

            return (
                self._valor(resultado.get("comunidad")),
                self._valor(datos.get("valor"))
            )

        return None, None

    def consultar_ip(self, ip, registradas):
        comunidad, descripcion = self.consultar_oid(
            ip,
            self.OID_SYS_DESCR
        )

        if descripcion is None:
            return None

        _, nombre = self.consultar_oid(
            ip,
            self.OID_SYS_NAME
        )

        return DispositivoDescubierto(
            ip=ip,
            comunidad=comunidad,
            nombre=nombre,
            descripcion=descripcion,
            registrado=ip in registradas
        )

    def ejecutar(self, red_texto, trabajadores=16):
        red = self.validar_red(red_texto)
        trabajadores = max(
            1,
            min(int(trabajadores), self.MAX_TRABAJADORES)
        )

        ips = [str(ip) for ip in red.hosts()]
        registradas = self.ips_registradas()
        encontrados = []

        visual.info(
            f"Explorando {len(ips)} direcciones de {red}."
        )
        visual.info(
            "Se mostrarán únicamente equipos que respondan por SNMP."
        )

        with ThreadPoolExecutor(max_workers=trabajadores) as ejecutor:
            futuros = {
                ejecutor.submit(
                    self.consultar_ip,
                    ip,
                    registradas
                ): ip
                for ip in ips
            }

            completados = 0

            for futuro in as_completed(futuros):
                completados += 1

                try:
                    resultado = futuro.result()
                except Exception:
                    resultado = None

                if resultado is not None:
                    encontrados.append(resultado)
                    visual.ok(
                        f"{resultado.ip} respondió por SNMP."
                    )

                if completados % 50 == 0 or completados == len(ips):
                    visual.info(
                        f"Progreso: {completados} de {len(ips)}."
                    )

        self.ultimo_resultado = sorted(
            encontrados,
            key=lambda item: IPv4Address(item.ip)
        )

        return list(
            self.ultimo_resultado
        )

    def mostrar_resultados(self, dispositivos, red_texto):
        visual.limpiar()
        visual.titulo(
            "DESCUBRIMIENTO SNMP DE RED",
            red_texto
        )

        registrados = [x for x in dispositivos if x.registrado]
        nuevos = [x for x in dispositivos if not x.registrado]

        visual.dashboard([
            {
                "titulo": "📡 Encontrados",
                "contenido": str(len(dispositivos)),
                "color": "cyan"
            },
            {
                "titulo": "🟢 Registrados",
                "contenido": str(len(registrados)),
                "color": "green"
            },
            {
                "titulo": "🟡 No registrados",
                "contenido": str(len(nuevos)),
                "color": "yellow" if nuevos else "green"
            }
        ])

        if not dispositivos:
            visual.warning(
                "Ningún dispositivo respondió por SNMP."
            )
            return

        filas = []

        for numero, item in enumerate(dispositivos, start=1):
            estado = (
                "[green]REGISTRADO[/]"
                if item.registrado
                else "[yellow]NUEVO[/]"
            )

            filas.append((
                str(numero),
                item.ip,
                estado,
                item.nombre or "-",
                item.descripcion or "-",
                item.comunidad or "-"
            ))

        visual.tabla(
            "Dispositivos que respondieron",
            [
                {"nombre": "N.º", "justify": "right", "no_wrap": True},
                {"nombre": "IP", "no_wrap": True},
                {"nombre": "Inventario", "no_wrap": True},
                "Nombre SNMP",
                "Descripción",
                {"nombre": "Comunidad", "no_wrap": True}
            ],
            filas,
            expandir=True,
            mostrar_lineas=True
        )

        if nuevos:
            visual.panel_acciones(
                "Equipos pendientes de revisión",
                [
                    (
                        str(numero),
                        f"{item.ip} | "
                        f"{item.nombre or 'Sin nombre SNMP'}"
                    )
                    for numero, item in enumerate(
                        nuevos,
                        start=1
                    )
                ],
                "yellow"
            )

            visual.warning(
                "Selecciona solamente equipos que hayas "
                "confirmado como switches administrables."
            )

            self.gestionar_nuevos(
                nuevos
            )
        else:
            visual.ok(
                "Todos los equipos SNMP encontrados ya están registrados."
            )

    def gestionar_nuevos(
        self,
        nuevos
    ):
        """
        Permite revisar y registrar switches descubiertos.
        """
        while True:
            seleccion = input(
                "\nEquipo nuevo para revisar "
                "[0 para terminar]: "
            ).strip()

            if seleccion in {"", "0"}:
                return

            try:
                indice = int(seleccion)
            except ValueError:
                visual.error(
                    "Debes escribir el número de un equipo."
                )
                continue

            if not 1 <= indice <= len(nuevos):
                visual.error(
                    "El equipo seleccionado no existe."
                )
                continue

            dispositivo = nuevos[indice - 1]

            if dispositivo.registrado:
                visual.info(
                    "Este equipo ya fue registrado "
                    "durante la sesión."
                )
                continue

            visual.limpiar()
            visual.titulo(
                "EQUIPO SNMP DESCUBIERTO",
                dispositivo.ip
            )

            visual.tabla(
                "Información detectada",
                [
                    {
                        "nombre": "Campo",
                        "style": "cyan",
                        "no_wrap": True
                    },
                    "Valor"
                ],
                [
                    (
                        "IP",
                        dispositivo.ip
                    ),
                    (
                        "Nombre SNMP",
                        dispositivo.nombre or "-"
                    ),
                    (
                        "Descripción SNMP",
                        dispositivo.descripcion or "-"
                    ),
                    (
                        "Comunidad",
                        dispositivo.comunidad or "-"
                    )
                ],
                expandir=True,
                mostrar_lineas=True
            )

            visual.menu_paneles(
                "ACCIONES",
                [
                    {
                        "titulo": "REGISTRO",
                        "icono": "🖧",
                        "color": "green",
                        "opciones": [
                            (
                                "1",
                                "Registrar como switch en SQLite"
                            )
                        ]
                    },
                    {
                        "titulo": "NAVEGACIÓN",
                        "icono": "↩",
                        "color": "red",
                        "opciones": [
                            (
                                "0",
                                "Volver a equipos encontrados"
                            )
                        ]
                    }
                ]
            )

            opcion = input(
                "\nSelecciona una opción: "
            ).strip()

            if opcion == "0":
                visual.limpiar()
                continue

            if opcion != "1":
                visual.error(
                    "Opción inválida."
                )
                continue

            try:
                self.registrador.registrar(
                    dispositivo
                )
            except ValueError as error:
                visual.error(
                    str(error)
                )
            except Exception as error:
                visual.error(
                    "No fue posible registrar el switch."
                )
                visual.info(
                    f"Detalle: {error}"
                )

            input(
                "\nPresiona ENTER para continuar..."
            )

            visual.limpiar()