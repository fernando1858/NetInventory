from __future__ import annotations

from datetime import datetime
from typing import Any

from modulos.visual import visual


class CentroOperacionesNOC:
    """
    Pantalla ejecutiva de NetInventory.

    Consolida información ya disponible en:
    - SQLite;
    - inventario Excel cargado en memoria;
    - topología;
    - último diagnóstico SNMP;
    - último descubrimiento de subred;
    - última medición de puertos.

    No modifica equipos de red.
    """

    def __init__(
        self,
        inventario,
        gestor_accesos,
        gestor_relaciones,
        gestor_topologia,
        revisor_incompletos,
        centro_snmp,
        analizador_red,
        centro_salud_red,
        asistente_incidencias
    ):
        self.inventario = inventario
        self.gestor_accesos = gestor_accesos
        self.gestor_relaciones = gestor_relaciones
        self.gestor_topologia = gestor_topologia
        self.revisor_incompletos = revisor_incompletos
        self.centro_snmp = centro_snmp
        self.analizador_red = analizador_red
        self.centro_salud_red = centro_salud_red
        self.asistente_incidencias = asistente_incidencias

        self.ultima_actualizacion = None

    @staticmethod
    def valor(
        objeto: Any,
        clave: str,
        predeterminado=0
    ):
        if isinstance(objeto, dict):
            return objeto.get(
                clave,
                predeterminado
            )

        return getattr(
            objeto,
            clave,
            predeterminado
        )

    def obtener_resumen_snmp(self) -> dict:
        descubrimiento = getattr(
            self.centro_snmp,
            "ultimo_descubrimiento",
            None
        )

        if descubrimiento is None:
            return {
                "ejecutado": False,
                "revisados": 0,
                "respondieron": 0,
                "sin_respuesta": 0,
                "solo_ping": 0
            }

        try:
            resumen = descubrimiento.obtener_resumen()
        except Exception:
            resumen = {}

        return {
            "ejecutado": True,
            "revisados": int(
                resumen.get("revisados", 0) or 0
            ),
            "respondieron": int(
                resumen.get("respondieron", 0) or 0
            ),
            "sin_respuesta": int(
                resumen.get("sin_respuesta", 0) or 0
            ),
            "solo_ping": int(
                resumen.get("solo_ping", 0) or 0
            )
        }

    def obtener_dispositivos_nuevos(self) -> list:
        descubridor_red = getattr(
            self.centro_snmp,
            "descubridor_red",
            None
        )

        if descubridor_red is None:
            return []

        resultados = getattr(
            descubridor_red,
            "ultimo_resultado",
            []
        ) or []

        return [
            item
            for item in resultados
            if not getattr(item, "registrado", False)
        ]

    def obtener_errores_activos(self) -> list[dict]:
        monitor_consola = getattr(
            self.centro_snmp,
            "monitor",
            None
        )

        if monitor_consola is None:
            return []

        monitor = getattr(
            monitor_consola,
            "monitor_snmp",
            None
        )

        medicion = (
            getattr(monitor_consola, "ultima_medicion", None)
            or getattr(monitor, "ultima_medicion", None)
        )

        if medicion is None:
            return []

        interfaces = getattr(
            medicion,
            "interfaces",
            []
        ) or []

        activos = []

        for interfaz in interfaces:
            entrada = int(
                interfaz.get(
                    "errores_nuevos_entrada",
                    0
                )
                or 0
            )

            salida = int(
                interfaz.get(
                    "errores_nuevos_salida",
                    0
                )
                or 0
            )

            total = entrada + salida

            if total > 0:
                activos.append(
                    {
                        "puerto": (
                            interfaz.get("nombre")
                            or interfaz.get("descripcion")
                            or "-"
                        ),
                        "entrada": entrada,
                        "salida": salida,
                        "total": total
                    }
                )

        return activos

    def obtener_resumen_diagnostico(self) -> dict:
        diagnostico = getattr(
            self.centro_snmp,
            "ultimo_diagnostico_correlacionado",
            None
        )

        if diagnostico is None:
            return {
                "criticas": 0,
                "altas": 0,
                "incidencias": []
            }

        try:
            resumen = diagnostico.obtener_resumen()
            incidencias = (
                diagnostico
                .obtener_incidencias_principales()
            )
        except Exception:
            return {
                "criticas": 0,
                "altas": 0,
                "incidencias": []
            }

        return {
            "criticas": int(
                resumen.get(
                    "prioridad_critica",
                    0
                )
                or 0
            ),
            "altas": int(
                resumen.get(
                    "prioridad_alta",
                    0
                )
                or 0
            ),
            "incidencias": incidencias
        }

    def obtener_cobertura(self) -> dict:
        try:
            auditoria = (
                self.analizador_red
                .auditar_cobertura_global()
            )

            return {
                "porcentaje": float(
                    auditoria.get(
                        "porcentaje",
                        0
                    )
                    or 0
                ),
                "pendientes": (
                    len(
                        auditoria.get(
                            "sin_relacion",
                            []
                        )
                    )
                    + len(
                        auditoria.get(
                            "relaciones_invalidas",
                            []
                        )
                    )
                    + len(
                        auditoria.get(
                            "bloques_sin_registros",
                            []
                        )
                    )
                )
            }

        except Exception:
            return {
                "porcentaje": 0.0,
                "pendientes": 0
            }

    def obtener_inventario(self) -> dict:
        try:
            bloques_incompletos = (
                self.revisor_incompletos
                .contar_bloques_incompletos()
            )
        except Exception:
            bloques_incompletos = 0

        try:
            filas_incompletas = (
                self.revisor_incompletos
                .contar_filas_incompletas()
            )
        except Exception:
            filas_incompletas = 0

        duplicados = len(
            getattr(
                self.inventario,
                "duplicados_detectados",
                []
            )
            or []
        )

        return {
            "registros": len(
                getattr(
                    self.inventario,
                    "registros",
                    []
                )
                or []
            ),
            "bloques_incompletos": bloques_incompletos,
            "filas_incompletas": filas_incompletas,
            "duplicados": duplicados
        }

    def construir_estado(self) -> dict:
        switches = len(
            self.gestor_accesos.listar_todos()
        )

        snmp = self.obtener_resumen_snmp()
        nuevos = self.obtener_dispositivos_nuevos()
        errores = self.obtener_errores_activos()
        diagnostico = self.obtener_resumen_diagnostico()
        cobertura = self.obtener_cobertura()
        inventario = self.obtener_inventario()

        alertas_criticas = (
            diagnostico["criticas"]
            + len(errores)
        )

        alertas_pendientes = (
            diagnostico["altas"]
            + cobertura["pendientes"]
            + inventario["bloques_incompletos"]
            + inventario["duplicados"]
            + len(nuevos)
        )

        if alertas_criticas > 0:
            estado = "CRÍTICO"
            color = "red"
            icono = "🔴"

        elif (
            alertas_pendientes > 0
            or (
                snmp["ejecutado"]
                and snmp["sin_respuesta"] > 0
            )
        ):
            estado = "ATENCIÓN"
            color = "yellow"
            icono = "🟡"

        elif not snmp["ejecutado"]:
            estado = "SIN COMPROBAR"
            color = "grey50"
            icono = "⚪"

        else:
            estado = "OPERATIVO"
            color = "green"
            icono = "🟢"

        return {
            "estado": estado,
            "color": color,
            "icono": icono,
            "switches": switches,
            "snmp": snmp,
            "nuevos": nuevos,
            "errores": errores,
            "diagnostico": diagnostico,
            "cobertura": cobertura,
            "inventario": inventario,
            "alertas_criticas": alertas_criticas,
            "alertas_pendientes": alertas_pendientes
        }

    def mostrar(self) -> dict:
        estado = self.construir_estado()

        visual.limpiar()
        visual.titulo(
            "CENTRO DE OPERACIONES NOC",
            "Vista ejecutiva de NetInventory",
            estado["color"]
        )

        snmp = estado["snmp"]

        disponibilidad = (
            snmp["respondieron"]
            / snmp["revisados"]
            * 100
            if snmp["revisados"]
            else 0.0
        )

        visual.dashboard(
            [
                {
                    "titulo": (
                        f"{estado['icono']} Estado"
                    ),
                    "contenido": estado["estado"],
                    "color": estado["color"]
                },
                {
                    "titulo": "🖧 Switches",
                    "contenido": str(
                        estado["switches"]
                    ),
                    "color": "bright_blue",
                    "subtitulo": "Registrados en SQLite"
                },
                {
                    "titulo": "📡 SNMP",
                    "contenido": (
                        f"{snmp['respondieron']} / "
                        f"{snmp['revisados']}"
                        if snmp["ejecutado"]
                        else "Sin medir"
                    ),
                    "color": (
                        visual.color_porcentaje(
                            disponibilidad
                        )
                        if snmp["ejecutado"]
                        else "grey50"
                    ),
                    "subtitulo": (
                        visual.barra(
                            disponibilidad,
                            largo=8
                        )
                        if snmp["ejecutado"]
                        else "Ejecuta actualización NOC"
                    )
                },
                {
                    "titulo": "🔴 Sin respuesta",
                    "contenido": (
                        str(snmp["sin_respuesta"])
                        if snmp["ejecutado"]
                        else "-"
                    ),
                    "color": (
                        "red"
                        if snmp["sin_respuesta"]
                        else "green"
                        if snmp["ejecutado"]
                        else "grey50"
                    )
                },
                {
                    "titulo": "🆕 Nuevos",
                    "contenido": str(
                        len(estado["nuevos"])
                    ),
                    "color": (
                        "yellow"
                        if estado["nuevos"]
                        else "green"
                    ),
                    "subtitulo": "Detectados por subred"
                },
                {
                    "titulo": "⚠ Errores activos",
                    "contenido": str(
                        len(estado["errores"])
                    ),
                    "color": (
                        "red"
                        if estado["errores"]
                        else "green"
                    ),
                    "subtitulo": "Última medición"
                },
                {
                    "titulo": "📊 Cobertura",
                    "contenido": (
                        f"{estado['cobertura']['porcentaje']:.1f} %"
                    ),
                    "color": visual.color_porcentaje(
                        estado["cobertura"]["porcentaje"]
                    ),
                    "subtitulo": (
                        f"{estado['cobertura']['pendientes']} "
                        "pendientes"
                    )
                },
                {
                    "titulo": "🚨 Críticas",
                    "contenido": str(
                        estado["alertas_criticas"]
                    ),
                    "color": (
                        "red"
                        if estado["alertas_criticas"]
                        else "green"
                    )
                }
            ]
        )

        visual.panel_estado(
            "Resumen ejecutivo",
            [
                (
                    estado["icono"],
                    "Estado general.............. "
                    f"{estado['estado']}"
                ),
                (
                    "📦",
                    "Registros de puertos........ "
                    f"{estado['inventario']['registros']}"
                ),
                (
                    "🟡"
                    if estado["inventario"][
                        "bloques_incompletos"
                    ]
                    else "🟢",
                    "Bloques incompletos......... "
                    f"{estado['inventario']['bloques_incompletos']}"
                ),
                (
                    "🟡"
                    if estado["inventario"]["duplicados"]
                    else "🟢",
                    "Puertos duplicados.......... "
                    f"{estado['inventario']['duplicados']}"
                ),
                (
                    "🟠"
                    if estado["diagnostico"]["altas"]
                    else "🟢",
                    "Incidencias de prioridad alta "
                    f"{estado['diagnostico']['altas']}"
                ),
                (
                    "⏱",
                    "Última actualización NOC..... "
                    f"{self.ultima_actualizacion or 'No ejecutada'}"
                )
            ],
            estado["color"]
        )

        self.mostrar_alertas_resumidas(
            estado
        )

        visual.menu_paneles(
            "ACCIONES DEL NOC",
            [
                {
                    "titulo": "OPERACIÓN",
                    "icono": "📡",
                    "color": "cyan",
                    "opciones": [
                        (
                            "1",
                            "Actualizar estado SNMP y diagnóstico"
                        ),
                        (
                            "2",
                            "Ver alertas activas"
                        ),
                        (
                            "3",
                            "Monitorizar un switch"
                        )
                    ]
                },
                {
                    "titulo": "ANÁLISIS",
                    "icono": "🧠",
                    "color": "yellow",
                    "opciones": [
                        (
                            "4",
                            "Descubrir equipos en una subred"
                        ),
                        (
                            "5",
                            "Analizar impacto de red"
                        ),
                        (
                            "6",
                            "Abrir Centro de Salud"
                        ),
                        (
                            "7",
                            "Abrir Asistente de Incidencias"
                        )
                    ]
                },
                {
                    "titulo": "NAVEGACIÓN",
                    "icono": "↩",
                    "color": "red",
                    "opciones": [
                        (
                            "8",
                            "Redibujar pantalla"
                        ),
                        (
                            "0",
                            "Volver"
                        )
                    ]
                }
            ]
        )

        return estado

    def mostrar_alertas_resumidas(
        self,
        estado: dict
    ) -> None:
        alertas = []

        snmp = estado["snmp"]

        if snmp["ejecutado"] and snmp["sin_respuesta"]:
            alertas.append(
                (
                    "🔴",
                    f"{snmp['sin_respuesta']} switches "
                    "sin respuesta SNMP."
                )
            )

        if snmp["solo_ping"]:
            alertas.append(
                (
                    "🟡",
                    f"{snmp['solo_ping']} equipos responden "
                    "ping, pero no SNMP."
                )
            )

        if estado["nuevos"]:
            alertas.append(
                (
                    "🆕",
                    f"{len(estado['nuevos'])} dispositivos "
                    "SNMP nuevos pendientes de revisión."
                )
            )

        if estado["errores"]:
            alertas.append(
                (
                    "🔴",
                    f"{len(estado['errores'])} puertos con "
                    "errores nuevos."
                )
            )

        if estado["cobertura"]["pendientes"]:
            alertas.append(
                (
                    "🟡",
                    f"{estado['cobertura']['pendientes']} switches "
                    "con cobertura incompleta."
                )
            )

        if estado["diagnostico"]["criticas"]:
            alertas.append(
                (
                    "🚨",
                    f"{estado['diagnostico']['criticas']} "
                    "incidencias críticas."
                )
            )

        if alertas:
            visual.panel_acciones(
                "Alertas visibles",
                alertas[:8],
                "red"
                if estado["alertas_criticas"]
                else "yellow"
            )
        else:
            visual.ok(
                "No hay alertas activas con la información "
                "disponible en esta sesión."
            )

    def actualizar_estado(self) -> None:
        descubridor = getattr(
            self.centro_snmp,
            "descubridor",
            None
        )

        if descubridor is None:
            visual.error(
                "El cliente SNMP no está disponible."
            )
            return

        visual.limpiar()
        visual.titulo(
            "ACTUALIZACIÓN DEL NOC",
            "Comprobación de switches registrados"
        )

        def progreso(numero, total, switch):
            if (
                numero == 1
                or numero == total
                or numero % 5 == 0
            ):
                ip = (
                    switch.get("ip")
                    if isinstance(switch, dict)
                    else "-"
                )

                visual.info(
                    f"Revisando {numero} de {total}: {ip}"
                )

        try:
            descubrimiento = descubridor.ejecutar(
                notificar_progreso=progreso
            )

            self.centro_snmp.ultimo_descubrimiento = (
                descubrimiento
            )

            motor = getattr(
                self.centro_snmp,
                "motor_diagnostico",
                None
            )

            if motor is not None:
                diagnostico = motor.analizar(
                    descubrimiento
                )

                self.centro_snmp\
                    .ultimo_diagnostico_correlacionado = (
                        diagnostico
                    )

            self.ultima_actualizacion = (
                datetime.now().strftime(
                    "%d-%m-%Y %H:%M:%S"
                )
            )

            visual.ok(
                "Estado SNMP y diagnóstico actualizados."
            )

        except Exception as error:
            visual.error(
                "No fue posible completar la actualización."
            )
            visual.info(
                f"Detalle: {error}"
            )

    def mostrar_alertas(self) -> None:
        estado = self.construir_estado()

        visual.limpiar()
        visual.titulo(
            "ALERTAS ACTIVAS DEL NOC",
            "Información consolidada de la sesión"
        )

        filas = []

        snmp = estado["snmp"]

        if snmp["ejecutado"] and snmp["sin_respuesta"]:
            filas.append(
                (
                    "CRÍTICA",
                    "SNMP",
                    f"{snmp['sin_respuesta']} switches "
                    "sin respuesta.",
                    "Revisar causas principales y topología."
                )
            )

        for item in estado["errores"]:
            filas.append(
                (
                    "CRÍTICA",
                    "PUERTO",
                    (
                        f"{item['puerto']} generó "
                        f"{item['total']} errores nuevos."
                    ),
                    "Revisar cable, patch panel y negociación."
                )
            )

        for item in estado["nuevos"]:
            filas.append(
                (
                    "MEDIA",
                    "DESCUBRIMIENTO",
                    (
                        f"{getattr(item, 'ip', '-')} | "
                        f"{getattr(item, 'nombre', '-')}"
                    ),
                    "Confirmar dispositivo y registrar si corresponde."
                )
            )

        for incidencia in estado["diagnostico"][
            "incidencias"
        ]:
            filas.append(
                (
                    getattr(
                        incidencia,
                        "prioridad",
                        "MEDIA"
                    ),
                    "TOPOLOGÍA",
                    (
                        f"{getattr(incidencia, 'nombre', '-')} | "
                        f"{getattr(incidencia, 'estado', '-')}"
                    ),
                    getattr(
                        incidencia,
                        "recomendacion",
                        "Revisar el equipo."
                    )
                )
            )

        if not filas:
            visual.ok(
                "No existen alertas activas para mostrar."
            )
            return

        visual.tabla(
            f"Alertas ({len(filas)})",
            [
                {
                    "nombre": "Prioridad",
                    "no_wrap": True
                },
                {
                    "nombre": "Origen",
                    "no_wrap": True
                },
                "Detalle",
                "Acción recomendada"
            ],
            filas,
            expandir=True,
            mostrar_lineas=True
        )

    def ejecutar(self) -> None:
        while True:
            self.mostrar()

            opcion = input(
                "\nSelecciona una opción: "
            ).strip()

            if opcion == "1":
                self.actualizar_estado()
                input(
                    "\nPresiona ENTER para continuar..."
                )

            elif opcion == "2":
                self.mostrar_alertas()
                input(
                    "\nPresiona ENTER para continuar..."
                )

            elif opcion == "3":
                monitor = getattr(
                    self.centro_snmp,
                    "monitor",
                    None
                )

                if monitor is None:
                    visual.error(
                        "El monitor SNMP no está disponible."
                    )
                    input(
                        "\nPresiona ENTER para continuar..."
                    )
                else:
                    monitor.ejecutar()

            elif opcion == "4":
                metodo = getattr(
                    self.centro_snmp,
                    "ejecutar_descubrimiento_red",
                    None
                )

                if metodo is None:
                    visual.error(
                        "El descubrimiento de subred "
                        "no está disponible."
                    )
                    input(
                        "\nPresiona ENTER para continuar..."
                    )
                else:
                    metodo()
                    input(
                        "\nPresiona ENTER para continuar..."
                    )

            elif opcion == "5":
                self.analizador_red.ejecutar()

            elif opcion == "6":
                self.centro_salud_red.ejecutar()

            elif opcion == "7":
                self.asistente_incidencias.ejecutar()

            elif opcion == "8":
                continue

            elif opcion == "0":
                return

            else:
                visual.error(
                    "Opción inválida."
                )
                input(
                    "\nPresiona ENTER para continuar..."
                )