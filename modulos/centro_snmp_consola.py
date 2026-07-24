from modulos.descubridor_snmp import DescubridorSNMP
from modulos.diagnostico_red import MotorDiagnosticoRed
from modulos.descubridor_red_snmp import DescubridorRedSNMP
from modulos.monitor_snmp_consola import MonitorSNMPConsola
from modulos.ui import InterfazUsuario
from modulos.visual import visual


class CentroSNMPConsola:
    """
    Reúne las herramientas SNMP de NetInventory:

    - Descubrimiento general de switches.
    - Monitorización detallada de un switch.
    - Análisis de salud.

    Todas las consultas son de solo lectura.
    """

    def __init__(
        self,
        cliente_snmp,
        gestor_accesos,
        gestor_topologia,
        inventario
    ):
        self.cliente_snmp = cliente_snmp
        self.gestor_accesos = gestor_accesos
        self.gestor_topologia = gestor_topologia
        self.inventario = inventario
        self.ui = InterfazUsuario

        self.descubridor = DescubridorSNMP(
            cliente_snmp=cliente_snmp,
            gestor_accesos=gestor_accesos
        )

        self.monitor = MonitorSNMPConsola(
            cliente_snmp=cliente_snmp,
            gestor_accesos=gestor_accesos,
            inventario=inventario
        )

        self.motor_diagnostico = MotorDiagnosticoRed(
            gestor_topologia=gestor_topologia
        )

        self.descubridor_red = DescubridorRedSNMP(
            cliente_snmp=cliente_snmp,
            gestor_accesos=gestor_accesos
        )

        self.ultimo_descubrimiento = None
        self.ultimo_diagnostico_correlacionado = None

    # ======================================================
    # EJECUCIÓN
    # ======================================================

    def ejecutar(self):
        """
        Ejecuta el menú principal del centro SNMP.
        """
        while True:
            self.mostrar_menu()

            opcion = input(
                "\nSelecciona una opción: "
            ).strip()

            if opcion in {
                "0",
                "1",
                "2",
                "3",
                "4",
                "5",
                "6"
            }:
                visual.limpiar()

            if opcion == "1":
                self.ejecutar_descubrimiento()
                self.ui.pausar()

            elif opcion == "2":
                self.mostrar_ultimo_descubrimiento()
                self.ui.pausar()

            elif opcion == "3":
                self.monitor.ejecutar()

            elif opcion == "4":
                self.ejecutar_diagnostico_correlacionado()
                self.ui.pausar()

            elif opcion == "5":
                self.ejecutar_prueba_snmp_tecnica()
                self.ui.pausar()

            elif opcion == "6":
                self.ejecutar_descubrimiento_red()
                self.ui.pausar()

            elif opcion == "0":
                self.ui.mostrar_info(
                    "Centro SNMP finalizado."
                )
                break

            else:
                self.ui.mostrar_error(
                    "Opción inválida. Selecciona una "
                    "opción disponible."
                )

                self.ui.pausar()

    def mostrar_menu(self):
        """
        Muestra el Centro SNMP usando la interfaz visual.

        No ejecuta consultas automáticamente. Las tarjetas
        utilizan únicamente el último diagnóstico realizado
        durante la sesión actual.
        """
        switches_registrados = len(
            self.gestor_accesos.listar_todos()
        )

        if self.ultimo_descubrimiento is None:
            tarjetas = [
                {
                    "titulo": "📡 SNMP",
                    "contenido": "Sin comprobar",
                    "color": "grey50",
                    "subtitulo": "Sin diagnóstico en esta sesión"
                },
                {
                    "titulo": "🖧 Switches",
                    "contenido": str(switches_registrados),
                    "color": "bright_blue",
                    "subtitulo": "Registrados"
                },
                {
                    "titulo": "✅ Respondieron",
                    "contenido": "-",
                    "color": "grey50",
                    "subtitulo": "Ejecuta un diagnóstico"
                },
                {
                    "titulo": "⚠ Sin respuesta",
                    "contenido": "-",
                    "color": "grey50",
                    "subtitulo": "Ejecuta un diagnóstico"
                }
            ]

            estados = [
                {
                    "icono": "🔵",
                    "texto": (
                        "El Centro SNMP está disponible y listo "
                        "para realizar consultas de solo lectura."
                    ),
                    "color": "cyan"
                },
                {
                    "icono": "⚪",
                    "texto": (
                        "Todavía no se ha ejecutado un diagnóstico "
                        "durante esta sesión."
                    ),
                    "color": "grey70"
                }
            ]

        else:
            resumen = self.ultimo_descubrimiento.obtener_resumen()
            revisados = resumen.get("revisados", 0)
            respondieron = resumen.get("respondieron", 0)
            sin_respuesta = resumen.get("sin_respuesta", 0)
            solo_ping = resumen.get("solo_ping", 0)

            porcentaje = (
                respondieron / revisados * 100
                if revisados
                else 0.0
            )

            color_snmp = visual.color_porcentaje(
                porcentaje
            )

            tarjetas = [
                {
                    "titulo": "📡 SNMP",
                    "contenido": f"{respondieron} / {revisados}",
                    "color": color_snmp,
                    "subtitulo": visual.barra(
                        porcentaje,
                        largo=10
                    )
                },
                {
                    "titulo": "🖧 Switches",
                    "contenido": str(switches_registrados),
                    "color": "bright_blue",
                    "subtitulo": "Registrados"
                },
                {
                    "titulo": "✅ Respondieron",
                    "contenido": str(respondieron),
                    "color": "green",
                    "subtitulo": "Por SNMP"
                },
                {
                    "titulo": "⚠ Sin respuesta",
                    "contenido": str(sin_respuesta),
                    "color": (
                        "green"
                        if sin_respuesta == 0
                        else "red"
                    ),
                    "subtitulo": (
                        f"Solo ping: {solo_ping}"
                    )
                }
            ]

            estados = [
                {
                    "icono": "🟢",
                    "texto": (
                        f"Respondieron por SNMP: {respondieron} "
                        f"de {revisados}."
                    ),
                    "color": "green"
                },
                {
                    "icono": (
                        "🟢"
                        if sin_respuesta == 0
                        else "🔴"
                    ),
                    "texto": (
                        f"Sin respuesta: {sin_respuesta}."
                    ),
                    "color": (
                        "green"
                        if sin_respuesta == 0
                        else "red"
                    )
                },
                {
                    "icono": (
                        "🟢"
                        if solo_ping == 0
                        else "🟡"
                    ),
                    "texto": (
                        f"Solo ping, sin SNMP: {solo_ping}."
                    ),
                    "color": (
                        "green"
                        if solo_ping == 0
                        else "yellow"
                    )
                },
                {
                    "icono": "⏱",
                    "texto": (
                        "Duración del último diagnóstico: "
                        f"{resumen.get('duracion_total', 0):.2f} s."
                    ),
                    "color": "cyan"
                }
            ]

        visual.limpiar()
        visual.titulo(
            "CENTRO DE MONITOREO SNMP",
            "Consultas de solo lectura · NetInventory"
        )
        visual.dashboard(
            tarjetas
        )
        visual.panel_estado(
            "Estado de la sesión",
            estados,
            "cyan"
        )
        visual.menu_paneles(
            "MENÚ PRINCIPAL",
            [
                {
                    "titulo": "DIAGNÓSTICO",
                    "icono": "📡",
                    "color": "cyan",
                    "opciones": [
                        (
                            "1",
                            "Ejecutar diagnóstico general"
                        ),
                        (
                            "2",
                            "Mostrar último diagnóstico"
                        ),
                        (
                            "3",
                            "Monitorizar un switch"
                        )
                    ]
                },
                {
                    "titulo": "ANÁLISIS Y PRUEBAS",
                    "icono": "🧠",
                    "color": "magenta",
                    "opciones": [
                        (
                            "4",
                            "Diagnóstico inteligente"
                        ),
                        (
                            "5",
                            "Prueba SNMP técnica"
                        ),
                        (
                            "6",
                            "Descubrir equipos SNMP en una subred"
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
                            "Volver al menú principal"
                        )
                    ]
                }
            ]
        )
        visual.pie(
            [
                "SNMP v2c",
                f"{switches_registrados} switches",
                "Solo lectura",
                "Ctrl+C para interrumpir una consulta"
            ]
        )



    # ======================================================
    # DESCUBRIMIENTO DE SUBRED
    # ======================================================

    def ejecutar_descubrimiento_red(self):
        """
        Recorre una red privada y compara los equipos SNMP
        encontrados con los registros de SQLite.
        """
        visual.limpiar()
        visual.titulo(
            "DESCUBRIMIENTO SNMP DE SUBRED",
            "Detección de equipos no registrados"
        )

        visual.panel_estado(
            "Ejemplos",
            [
                (
                    "🔵",
                    "192.168.5.0/24 revisa 254 direcciones."
                ),
                (
                    "🔵",
                    "192.168.4.0/23 revisa 510 direcciones."
                ),
                (
                    "🟢",
                    "La operación es de solo lectura."
                )
            ],
            "cyan"
        )

        red_texto = input(
            "\nRed a explorar [192.168.4.0/23]: "
        ).strip()

        if not red_texto:
            red_texto = "192.168.4.0/23"

        confirmar = input(
            f"Explorar {red_texto} por SNMP (S/N): "
        ).strip().lower()

        if confirmar not in {"s", "si", "sí"}:
            visual.info(
                "Descubrimiento cancelado."
            )
            return

        try:
            dispositivos = self.descubridor_red.ejecutar(
                red_texto=red_texto,
                trabajadores=16
            )
        except ValueError as error:
            visual.error(
                str(error)
            )
            return
        except Exception as error:
            visual.error(
                "No fue posible completar el descubrimiento."
            )
            visual.info(
                f"Detalle: {error}"
            )
            return

        self.descubridor_red.mostrar_resultados(
            dispositivos=dispositivos,
            red_texto=red_texto
        )

    # ======================================================
    # PRUEBA SNMP TÉCNICA
    # ======================================================

    def ejecutar_prueba_snmp_tecnica(self):
        """
        Prueba cada comunidad configurada contra un OID
        concreto y presenta el resultado con Rich.
        """
        visual.limpiar()
        visual.titulo(
            "PRUEBA SNMP TÉCNICA",
            "Consulta de solo lectura"
        )

        visual.info(
            "Esta prueba no modifica la configuración "
            "del switch."
        )

        ip = input(
            "\nIP del switch: "
        ).strip()

        oid = input(
            "OID [1.3.6.1.2.1.1.1.0]: "
        ).strip()

        if not oid:
            oid = "1.3.6.1.2.1.1.1.0"

        visual.panel_estado(
            "Configuración usada",
            [
                ("🔵", "Versión........ SNMP v2c"),
                (
                    "🔵",
                    f"Puerto......... {self.cliente_snmp.puerto}"
                ),
                (
                    "🔵",
                    f"Timeout........ {self.cliente_snmp.timeout} s"
                ),
                (
                    "🔵",
                    f"Reintentos..... {self.cliente_snmp.reintentos}"
                ),
                ("🔵", f"OID............ {oid}")
            ],
            "cyan"
        )

        try:
            resultados = (
                self.cliente_snmp
                .probar_todas_las_comunidades_tecnicas(
                    ip=ip,
                    oid=oid
                )
            )

        except ValueError as error:
            visual.error(
                str(error)
            )
            return

        except Exception as error:
            visual.error(
                "La prueba técnica no pudo completarse."
            )
            visual.info(
                f"Detalle: {error}"
            )
            return

        if not resultados:
            visual.error(
                "No existen comunidades configuradas."
            )
            return

        filas = []
        alguna_correcta = False

        for numero, resultado in enumerate(
            resultados,
            start=1
        ):
            comunidad = str(
                resultado.get(
                    "comunidad",
                    "-"
                )
            )

            if resultado.get("correcto"):
                alguna_correcta = True

                valor = (
                    resultado.get("datos", {})
                    .get("valor")
                )

                estado = "[bold green]RESPUESTA CORRECTA[/]"
                detalle = self.valor_visible(
                    valor,
                    "-"
                )
            else:
                estado = "[bold red]ERROR[/]"
                detalle = self.valor_visible(
                    resultado.get("error"),
                    "Sin detalle"
                )

            filas.append(
                (
                    str(numero),
                    comunidad,
                    estado,
                    detalle
                )
            )

        visual.tabla(
            "Resultados por comunidad",
            [
                {
                    "nombre": "N.º",
                    "justify": "right",
                    "no_wrap": True
                },
                "Comunidad",
                "Estado",
                "Valor / Detalle"
            ],
            filas,
            expandir=True,
            mostrar_lineas=True
        )

        if alguna_correcta:
            visual.ok(
                "Al menos una comunidad respondió "
                "correctamente."
            )
        else:
            visual.error(
                "Ninguna comunidad obtuvo respuesta."
            )

            visual.panel_estado(
                "Interpretación",
                [
                    (
                        "🟡",
                        "Timeout: revisar ruta, ACL, VRF, "
                        "firewall o servicio SNMP."
                    ),
                    (
                        "🟡",
                        "Authorization error: revisar comunidad "
                        "o permisos."
                    ),
                    (
                        "🟡",
                        "No Such Object: probar otro OID."
                    )
                ],
                "yellow"
            )

    def ejecutar_diagnostico_correlacionado(self):
        """
        Combina disponibilidad SNMP, topología, criticidad
        y dependencias para localizar causas probables.
        """
        self.ui.mostrar_titulo(
            "Diagnóstico inteligente de red",
            limpiar=True
        )

        print(
            "Se comprobarán los switches registrados y "
            "después se correlacionarán los resultados "
            "con la topología documentada.\n"
        )

        try:
            descubrimiento = self.descubridor.ejecutar(
                notificar_progreso=self.notificar_progreso
            )

            diagnostico = self.motor_diagnostico.analizar(
                descubrimiento
            )

        except Exception as error:
            self.ui.mostrar_error(
                "No fue posible completar el diagnóstico "
                "inteligente de red."
            )
            print(f"\nDetalle: {error}")
            return

        self.ultimo_descubrimiento = descubrimiento
        self.ultimo_diagnostico_correlacionado = diagnostico

        self.motor_diagnostico.mostrar_resultado(
            diagnostico
        )

    # ======================================================
    # DESCUBRIMIENTO
    # ======================================================

    @staticmethod
    def valor_visible(
        valor,
        predeterminado="Sin información"
    ):
        """
        Convierte valores vacíos en texto visible.
        """
        if valor is None:
            return predeterminado

        texto = str(valor).strip()

        return texto or predeterminado

    def notificar_progreso(
        self,
        numero,
        total,
        switch
    ):
        """
        Muestra el progreso del descubrimiento.
        """
        ip = self.valor_visible(
            switch.get("ip")
        )

        ubicacion = self.valor_visible(
            switch.get("ubicacion")
        )

        print(
            f"[{numero}/{total}] "
            f"Comprobando {ip} - {ubicacion}..."
        )

    def ejecutar_descubrimiento(self):
        """
        Comprueba todos los switches registrados.
        """
        self.ui.mostrar_titulo(
            "Diagnóstico general SNMP",
            limpiar=True
        )

        print(
            "Se comprobarán todos los switches "
            "registrados con una IP válida."
        )

        print(
            "\nLos equipos sin respuesta pueden tardar "
            "varios segundos debido a los intentos con "
            "las comunidades configuradas.\n"
        )

        try:
            resultado = self.descubridor.ejecutar(
                notificar_progreso=(
                    self.notificar_progreso
                )
            )

        except Exception as error:
            self.ui.mostrar_error(
                "No fue posible completar el "
                "diagnóstico general."
            )

            print(
                f"\nDetalle: {error}"
            )
            return

        self.ultimo_descubrimiento = resultado

        self.mostrar_descubrimiento(
            resultado
        )

    def mostrar_ultimo_descubrimiento(self):
        """
        Vuelve a mostrar el último resultado guardado
        temporalmente durante la sesión.
        """
        self.ui.mostrar_titulo(
            "Último diagnóstico SNMP",
            limpiar=True
        )

        if self.ultimo_descubrimiento is None:
            self.ui.mostrar_aviso(
                "Todavía no se ha ejecutado un "
                "diagnóstico en esta sesión."
            )
            return

        self.mostrar_descubrimiento(
            self.ultimo_descubrimiento
        )

    def mostrar_descubrimiento(
        self,
        descubrimiento
    ):
        """
        Muestra el resultado completo del descubrimiento
        usando tarjetas y tablas Rich.
        """
        resumen = descubrimiento.obtener_resumen()

        respondieron = (
            descubrimiento.obtener_por_estado(
                DescubridorSNMP.ESTADO_RESPONDE
            )
        )

        sin_respuesta = (
            descubrimiento.obtener_por_estado(
                DescubridorSNMP
                .ESTADO_SIN_RESPUESTA
            )
        )

        revisados = int(
            resumen.get(
                "revisados",
                0
            )
            or 0
        )

        respondieron_total = int(
            resumen.get(
                "respondieron",
                0
            )
            or 0
        )

        sin_respuesta_total = int(
            resumen.get(
                "sin_respuesta",
                0
            )
            or 0
        )

        solo_ping = int(
            resumen.get(
                "solo_ping",
                0
            )
            or 0
        )

        porcentaje = (
            respondieron_total / revisados * 100
            if revisados
            else 0.0
        )

        visual.titulo(
            "DIAGNÓSTICO GENERAL SNMP",
            "Resumen de disponibilidad de la red"
        )

        visual.dashboard(
            [
                {
                    "titulo": "📡 Disponibilidad",
                    "contenido": (
                        f"{respondieron_total} / {revisados}"
                    ),
                    "color": (
                        visual.color_porcentaje(
                            porcentaje
                        )
                    ),
                    "subtitulo": visual.barra(
                        porcentaje,
                        largo=12
                    )
                },
                {
                    "titulo": "🟢 Respondieron",
                    "contenido": str(
                        respondieron_total
                    ),
                    "color": "green"
                },
                {
                    "titulo": "🔴 Sin respuesta",
                    "contenido": str(
                        sin_respuesta_total
                    ),
                    "color": (
                        "red"
                        if sin_respuesta_total
                        else "green"
                    )
                },
                {
                    "titulo": "🟡 Solo ping",
                    "contenido": str(
                        solo_ping
                    ),
                    "color": (
                        "yellow"
                        if solo_ping
                        else "green"
                    )
                }
            ]
        )

        tiempo_promedio = resumen.get(
            "tiempo_promedio_ms"
        )

        estados = [
            (
                "🔵",
                f"Switches revisados......... {revisados}"
            ),
            (
                "🟢",
                "Respondieron por SNMP...... "
                f"{respondieron_total}"
            ),
            (
                "🔴" if sin_respuesta_total else "🟢",
                "Sin respuesta.............. "
                f"{sin_respuesta_total}"
            ),
            (
                "🟡" if solo_ping else "🟢",
                "Solo ping, sin SNMP........ "
                f"{solo_ping}"
            ),
            (
                "🟡"
                if resumen.get("ips_duplicadas", 0)
                else "🟢",
                "IP duplicadas.............. "
                f"{resumen.get('ips_duplicadas', 0)}"
            ),
            (
                "🟡"
                if resumen.get("registros_sin_ip", 0)
                else "🟢",
                "Registros sin IP........... "
                f"{resumen.get('registros_sin_ip', 0)}"
            ),
            (
                "🟡"
                if resumen.get("registros_ip_invalida", 0)
                else "🟢",
                "IP inválidas............... "
                f"{resumen.get('registros_ip_invalida', 0)}"
            )
        ]

        if tiempo_promedio is not None:
            estados.append(
                (
                    "⏱",
                    "Tiempo promedio........... "
                    f"{tiempo_promedio:.2f} ms"
                )
            )

        estados.append(
            (
                "⏱",
                "Duración total............. "
                f"{resumen.get('duracion_total', 0):.2f} s"
            )
        )

        visual.panel_estado(
            "Resumen del diagnóstico",
            estados,
            "cyan"
        )

        self.mostrar_switches_respondieron(
            respondieron
        )

        self.mostrar_switches_sin_respuesta(
            sin_respuesta
        )

        self.mostrar_ips_duplicadas(
            descubrimiento.ips_duplicadas
        )

    def mostrar_switches_respondieron(
        self,
        resultados
    ):
        """
        Muestra en una tabla los equipos que respondieron.
        """
        if not resultados:
            visual.warning(
                "Ningún switch respondió por SNMP."
            )
            return

        filas = []

        for resultado in resultados:
            ip = self.valor_visible(
                resultado.ip,
                "-"
            )

            nombre = self.valor_visible(
                resultado.nombre_snmp,
                "-"
            )

            ubicacion = self.valor_visible(
                resultado.ubicacion,
                "-"
            )

            marca = self.valor_visible(
                resultado.marca,
                "-"
            )

            if resultado.tiempo_ms is None:
                tiempo = "-"
            else:
                tiempo = (
                    f"{resultado.tiempo_ms:.2f} ms"
                )

            filas.append(
                (
                    f"[green]●[/] {ip}",
                    nombre,
                    ubicacion,
                    marca,
                    tiempo
                )
            )

        visual.tabla(
            f"Respondieron por SNMP ({len(resultados)})",
            [
                {
                    "nombre": "IP",
                    "no_wrap": True
                },
                "Nombre SNMP",
                "Ubicación",
                {
                    "nombre": "Marca",
                    "no_wrap": True
                },
                {
                    "nombre": "Tiempo",
                    "justify": "right",
                    "no_wrap": True
                }
            ],
            filas,
            expandir=True
        )

    def mostrar_switches_sin_respuesta(
        self,
        resultados
    ):
        """
        Muestra los switches sin respuesta en una tabla.
        """
        if not resultados:
            visual.ok(
                "Todos los switches revisados "
                "respondieron por SNMP."
            )
            return

        filas = []

        for resultado in resultados:
            ip = self.valor_visible(
                resultado.ip,
                "-"
            )

            ubicacion = self.valor_visible(
                resultado.ubicacion,
                "-"
            )

            marca = self.valor_visible(
                resultado.marca,
                "-"
            )

            modelo = self.valor_visible(
                resultado.modelo,
                "-"
            )

            equipo = (
                f"{marca} {modelo}"
            ).strip()

            if resultado.tiempo_ms is None:
                tiempo = "-"
            else:
                tiempo = (
                    f"{resultado.tiempo_ms:.2f} ms"
                )

            motivo = self.valor_visible(
                resultado.detalle,
                "Sin detalle"
            )

            filas.append(
                (
                    f"[red]●[/] {ip}",
                    ubicacion,
                    equipo,
                    tiempo,
                    motivo
                )
            )

        visual.tabla(
            f"Sin respuesta ({len(resultados)})",
            [
                {
                    "nombre": "IP",
                    "no_wrap": True
                },
                "Ubicación",
                "Equipo",
                {
                    "nombre": "Tiempo",
                    "justify": "right",
                    "no_wrap": True
                },
                "Motivo"
            ],
            filas,
            expandir=True,
            mostrar_lineas=True
        )

        visual.warning(
            "Los equipos sin respuesta deben revisarse "
            "antes de asumir una falla física."
        )

    def mostrar_ips_duplicadas(
        self,
        ips_duplicadas
    ):
        """
        Muestra las direcciones IP repetidas.
        """
        if not ips_duplicadas:
            return

        acciones = [
            {
                "icono": "🔴",
                "texto": str(ip),
                "color": "red"
            }
            for ip in ips_duplicadas
        ]

        visual.panel_acciones(
            "Direcciones IP duplicadas",
            acciones,
            "red"
        )

        visual.warning(
            "Estas direcciones deben revisarse en la "
            "base de datos de switches."
        )