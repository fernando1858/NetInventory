import os
from getpass import getpass
from pathlib import Path

from config import (
    AREA_RESPONSABLE,
    NOMBRE_APLICACION,
    ORGANIZACION,
    VERSION_APLICACION
)
from modulos.presentador_switches import PresentadorSwitches
from modulos.ui import InterfazUsuario
from modulos.visual import visual


class InterfazConsola:
    """
    Administra los menús y la interacción por consola
    de NetInventory.
    """

    MAX_INTENTOS_ACCESO = 3

    def __init__(
        self,
        inventario,
        gestor_accesos,
        exportador,
        gestor_fichas,
        gestor_relaciones,
        revisor_incompletos,
        validador_inventario,
        gestor_respaldos,
        buscador_universal,
        centro_snmp,
        gestor_topologia,
        analizador_red,
        centro_salud_red,
        asistente_incidencias,
        centro_operaciones_noc,
        ruta_excel
    ):
        self.inventario = inventario
        self.gestor_accesos = gestor_accesos
        self.exportador = exportador
        self.gestor_fichas = gestor_fichas
        self.gestor_relaciones = gestor_relaciones
        self.revisor_incompletos = revisor_incompletos
        self.validador_inventario = validador_inventario
        self.gestor_respaldos = gestor_respaldos
        self.buscador_universal = buscador_universal
        self.centro_snmp = centro_snmp
        self.gestor_topologia = gestor_topologia
        self.analizador_red = analizador_red
        self.centro_salud_red = centro_salud_red
        self.asistente_incidencias = asistente_incidencias
        self.centro_operaciones_noc = centro_operaciones_noc
        self.ruta_excel = ruta_excel

        self.gestor_historial = (
            gestor_accesos.historial
        )

        self.ui = InterfazUsuario

        self.presentador_switches = PresentadorSwitches(
            gestor_accesos
        )

    # ======================================================
    # MENÚ PRINCIPAL
    # ======================================================

    def ejecutar(self):
        """
        Ejecuta el menú principal reorganizado.

        El primer nivel solamente contiene las cinco áreas
        principales de NetInventory.
        """
        while True:
            self.mostrar_menu_principal()

            opcion = input(
                "\nSelecciona una opción: "
            ).strip()

            if opcion in {
                "0",
                "1",
                "2",
                "3",
                "4",
                "5"
            }:
                visual.limpiar()

            if opcion == "1":
                self.centro_operaciones_noc.ejecutar()

            elif opcion == "2":
                self.ejecutar_menu_explorar()

            elif opcion == "3":
                self.ejecutar_menu_inventario()

            elif opcion == "4":
                if self.autenticar_accesos():
                    self.ejecutar_menu_accesos()

            elif opcion == "5":
                self.ejecutar_menu_reportes()

            elif opcion == "0":
                visual.ok(
                    "NetInventory finalizado."
                )
                break

            else:
                visual.error(
                    "Opción inválida. Selecciona una "
                    "opción disponible."
                )
                self.ui.pausar()

    def mostrar_menu_principal(self):
        """
        Muestra una pantalla inicial compacta con Rich.
        """
        switches = len(
            self.gestor_accesos.listar_todos()
        )

        registros = len(
            getattr(
                self.inventario,
                "registros",
                []
            )
            or []
        )

        duplicados = len(
            getattr(
                self.inventario,
                "duplicados_detectados",
                []
            )
            or []
        )

        try:
            relaciones = (
                self.gestor_relaciones
                .validar_relaciones()
            )

            invalidas = len(
                relaciones.get(
                    "invalidas",
                    []
                )
            )

            sin_relacion = len(
                relaciones.get(
                    "sin_relacion",
                    []
                )
            )

        except Exception:
            invalidas = 0
            sin_relacion = 0

        descubrimiento = getattr(
            self.centro_snmp,
            "ultimo_descubrimiento",
            None
        )

        if descubrimiento is None:
            estado_snmp = "Sin comprobar"
            color_snmp = "grey50"
            subtitulo_snmp = "Ejecuta el NOC"

        else:
            try:
                resumen_snmp = (
                    descubrimiento.obtener_resumen()
                )

                respondieron = int(
                    resumen_snmp.get(
                        "respondieron",
                        0
                    )
                    or 0
                )

                revisados = int(
                    resumen_snmp.get(
                        "revisados",
                        0
                    )
                    or 0
                )

                porcentaje = (
                    respondieron / revisados * 100
                    if revisados
                    else 0.0
                )

                estado_snmp = (
                    f"{respondieron} / {revisados}"
                )

                color_snmp = (
                    visual.color_porcentaje(
                        porcentaje
                    )
                )

                subtitulo_snmp = visual.barra(
                    porcentaje,
                    largo=8
                )

            except Exception:
                estado_snmp = "Sin comprobar"
                color_snmp = "grey50"
                subtitulo_snmp = "Ejecuta el NOC"

        pendientes = (
            duplicados
            + invalidas
            + sin_relacion
        )

        visual.limpiar()
        visual.titulo(
            "NETINVENTORY 1.0",
            "Centro de Operaciones e Inventario de Red"
        )

        visual.dashboard(
            [
                {
                    "titulo": "🟢 Sistema",
                    "contenido": "Operativo",
                    "color": "green",
                    "subtitulo": "SQLite y Excel cargados"
                },
                {
                    "titulo": "🖧 Switches",
                    "contenido": str(switches),
                    "color": "bright_blue",
                    "subtitulo": "Registrados"
                },
                {
                    "titulo": "🔌 Puertos",
                    "contenido": str(registros),
                    "color": "cyan",
                    "subtitulo": "Documentados"
                },
                {
                    "titulo": "📡 SNMP",
                    "contenido": estado_snmp,
                    "color": color_snmp,
                    "subtitulo": subtitulo_snmp
                },
                {
                    "titulo": "⚠ Pendientes",
                    "contenido": str(pendientes),
                    "color": (
                        "yellow"
                        if pendientes
                        else "green"
                    ),
                    "subtitulo": (
                        "Inventario y relaciones"
                    )
                }
            ]
        )

        visual.menu_paneles(
            "ÁREAS PRINCIPALES",
            [
                {
                    "titulo": "OPERACIÓN DIARIA",
                    "icono": "🛰",
                    "color": "green",
                    "opciones": [
                        (
                            "1",
                            "Centro de Operaciones NOC"
                        )
                    ]
                },
                {
                    "titulo": "CONSULTA",
                    "icono": "🔍",
                    "color": "cyan",
                    "opciones": [
                        (
                            "2",
                            "Explorar y buscar"
                        ),
                        (
                            "3",
                            "Inventario y documentación"
                        )
                    ]
                },
                {
                    "titulo": "GESTIÓN",
                    "icono": "⚙",
                    "color": "yellow",
                    "opciones": [
                        (
                            "4",
                            "Administración de red"
                        ),
                        (
                            "5",
                            "Reportes e historial"
                        )
                    ]
                },
                {
                    "titulo": "SESIÓN",
                    "icono": "↩",
                    "color": "red",
                    "opciones": [
                        (
                            "0",
                            "Salir"
                        )
                    ]
                }
            ]
        )

        visual.pie(
            [
                "SQLite como base operativa",
                "Excel de solo lectura",
                "Consultas SNMP de solo lectura"
            ]
        )

    def mostrar_menu_explorar(self):
        """
        Muestra las herramientas de consulta rápida.
        """
        visual.limpiar()
        visual.titulo(
            "EXPLORAR Y BUSCAR",
            "Consulta transversal de NetInventory"
        )

        visual.menu_paneles(
            "HERRAMIENTAS",
            [
                {
                    "titulo": "BÚSQUEDA",
                    "icono": "🔍",
                    "color": "cyan",
                    "opciones": [
                        (
                            "1",
                            "Buscador universal"
                        ),
                        (
                            "2",
                            "Consultar ficha completa de red"
                        )
                    ]
                },
                {
                    "titulo": "SWITCHES",
                    "icono": "🖧",
                    "color": "bright_blue",
                    "opciones": [
                        (
                            "3",
                            "Mostrar switches registrados"
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
                            "Volver"
                        )
                    ]
                }
            ]
        )

    def ejecutar_menu_explorar(self):
        """
        Ejecuta las herramientas de consulta.
        """
        while True:
            self.mostrar_menu_explorar()

            opcion = input(
                "\nSelecciona una opción: "
            ).strip()

            if opcion in {
                "0",
                "1",
                "2",
                "3",
                "4"
            }:
                visual.limpiar()

            if opcion == "1":
                self.buscar_en_netinventory()
                self.ui.pausar()

            elif opcion == "2":
                self.consultar_ficha_red()
                self.ui.pausar()

            elif opcion == "3":
                self.mostrar_todos_los_switches()
                self.ui.pausar()

            elif opcion == "0":
                return

            else:
                visual.error(
                    "Opción inválida."
                )
                self.ui.pausar()

    def mostrar_menu_inventario(self):
        """
        Muestra las herramientas de documentación.
        """
        visual.limpiar()
        visual.titulo(
            "INVENTARIO Y DOCUMENTACIÓN",
            "Calidad, relaciones y cobertura"
        )

        visual.menu_paneles(
            "HERRAMIENTAS",
            [
                {
                    "titulo": "INVENTARIO",
                    "icono": "📦",
                    "color": "cyan",
                    "opciones": [
                        (
                            "1",
                            "Mostrar resumen general"
                        ),
                        (
                            "2",
                            "Validar inventario"
                        )
                    ]
                },
                {
                    "titulo": "COBERTURA",
                    "icono": "📊",
                    "color": "yellow",
                    "opciones": [
                        (
                            "3",
                            "Mostrar relaciones switch ↔ Excel"
                        ),
                        (
                            "4",
                            "Auditar cobertura del inventario"
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
                            "Volver"
                        )
                    ]
                }
            ]
        )

    def ejecutar_menu_inventario(self):
        """
        Ejecuta las funciones documentales.
        """
        while True:
            self.mostrar_menu_inventario()

            opcion = input(
                "\nSelecciona una opción: "
            ).strip()

            if opcion in {
                "0",
                "1",
                "2",
                "3",
                "4"
            }:
                visual.limpiar()

            if opcion == "1":
                self.inventario.mostrar_resumen_general()
                self.ui.pausar()

            elif opcion == "2":
                self.validador_inventario\
                    .mostrar_validaciones()
                self.ui.pausar()

            elif opcion == "3":
                self.gestor_relaciones\
                    .mostrar_relaciones()
                self.ui.pausar()

            elif opcion == "4":
                self.analizador_red\
                    .mostrar_auditoria_cobertura()
                self.ui.pausar()

            elif opcion == "0":
                return

            else:
                visual.error(
                    "Opción inválida."
                )
                self.ui.pausar()

    def mostrar_menu_reportes(self):
        """
        Muestra reportes y trazabilidad.
        """
        visual.limpiar()
        visual.titulo(
            "REPORTES E HISTORIAL",
            "Exportación y trazabilidad de cambios"
        )

        visual.menu_paneles(
            "HERRAMIENTAS",
            [
                {
                    "titulo": "REPORTES",
                    "icono": "📄",
                    "color": "green",
                    "opciones": [
                        (
                            "1",
                            "Generar reporte Excel"
                        )
                    ]
                },
                {
                    "titulo": "HISTORIAL PROTEGIDO",
                    "icono": "🕘",
                    "color": "yellow",
                    "opciones": [
                        (
                            "2",
                            "Mostrar historial de cambios"
                        ),
                        (
                            "3",
                            "Buscar en historial"
                        ),
                        (
                            "4",
                            "Acerca de NetInventory y diagnóstico"
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
                            "Volver"
                        )
                    ]
                }
            ]
        )

    def ejecutar_menu_reportes(self):
        """
        Ejecuta reportes y consultas de historial.
        """
        while True:
            self.mostrar_menu_reportes()

            opcion = input(
                "\nSelecciona una opción: "
            ).strip()

            if opcion in {
                "0",
                "1",
                "2",
                "3"
            }:
                visual.limpiar()

            if opcion == "1":
                self.generar_reporte()
                self.ui.pausar()

            elif opcion == "2":
                if self.autenticar_accesos():
                    self.mostrar_historial()
                    self.ui.pausar()

            elif opcion == "3":
                if self.autenticar_accesos():
                    self.buscar_historial()
                    self.ui.pausar()

            elif opcion == "4":
                self.mostrar_acerca()
                self.ui.pausar()

            elif opcion == "0":
                return

            else:
                visual.error(
                    "Opción inválida."
                )
                self.ui.pausar()

    def buscar_en_netinventory(self):
        """
        Ejecuta una búsqueda simultánea en:

        - Inventario de puertos.
        - Equipos documentados.
        - Hojas y bloques.
        - VLAN.
        - Patch panel.
        - Switches registrados.
        - Relaciones entre switches y bloques.

        El buscador nunca muestra contraseñas.
        """
        self.ui.mostrar_titulo(
            "Buscador universal",
            limpiar=True
        )

        print(
            "Puedes buscar por equipo, sector, IP, MAC, "
            "modelo, VLAN, puerto, patch panel o ubicación."
        )

        print("\nEjemplos:")
        print("- AP GERENCIA")
        print("- Administración")
        print("- 192.168.5.221")
        print("- 221")
        print("- VLAN 4")
        print("- Puerto 17")
        print("- SF300-24")

        consulta = self.ui.pedir_texto(
            "\n¿Qué deseas buscar?: "
        )

        self.ui.mostrar_info(
            f"Buscando: {consulta}"
        )

        try:
            resultados = (
                self.buscador_universal.buscar(
                    texto=consulta,
                    limite=100
                )
            )

        except Exception as error:
            self.ui.mostrar_error(
                "No fue posible completar la búsqueda: "
                f"{error}"
            )
            return

        self.buscador_universal.mostrar_resultados(
            resultados
        )

        if len(resultados) == 100:
            self.ui.mostrar_aviso(
                "Se alcanzó el límite de 100 resultados. "
                "Utiliza una búsqueda más específica."
            )

    def mostrar_acerca(self):
        """
        Muestra información de versión, arquitectura y
        diagnóstico básico del entorno.
        """
        visual.limpiar()

        ruta_log = Path(
            "logs/netinventory.log"
        )

        ruta_db = getattr(
            self.gestor_accesos.base_datos,
            "ruta_db",
            "datos/netinventory.db"
        )

        visual.titulo(
            f"ACERCA DE {NOMBRE_APLICACION.upper()}",
            f"Versión {VERSION_APLICACION}"
        )

        visual.dashboard(
            [
                {
                    "titulo": "🏫 Organización",
                    "contenido": ORGANIZACION,
                    "color": "bright_blue"
                },
                {
                    "titulo": "🛠 Área",
                    "contenido": AREA_RESPONSABLE,
                    "color": "cyan"
                },
                {
                    "titulo": "🗄 Base operativa",
                    "contenido": "SQLite",
                    "color": "green",
                    "subtitulo": str(ruta_db)
                },
                {
                    "titulo": "📄 Excel",
                    "contenido": "Solo lectura",
                    "color": "green",
                    "subtitulo": self.ruta_excel.name
                },
                {
                    "titulo": "📡 SNMP",
                    "contenido": "Solo lectura",
                    "color": "green"
                },
                {
                    "titulo": "📝 Logs",
                    "contenido": (
                        "Disponible"
                        if ruta_log.exists()
                        else "Se crea al ejecutar"
                    ),
                    "color": "yellow",
                    "subtitulo": str(ruta_log)
                }
            ]
        )

        visual.panel_estado(
            "Arquitectura de NetInventory",
            [
                (
                    "🟢",
                    "SQLite almacena switches, relaciones, "
                    "topología, credenciales e historial."
                ),
                (
                    "🟢",
                    "El Excel se consulta como documentación "
                    "externa sin ser modificado."
                ),
                (
                    "🟢",
                    "SNMP se utiliza para consultas y "
                    "diagnóstico de solo lectura."
                ),
                (
                    "🟢",
                    "Las modificaciones sensibles crean "
                    "respaldos y quedan registradas."
                ),
                (
                    "📝",
                    "Los errores inesperados guardan traceback "
                    "completo en logs/netinventory.log."
                )
            ],
            "green"
        )

        visual.tabla(
            "Módulos principales",
            [
                {
                    "nombre": "Área",
                    "style": "cyan",
                    "no_wrap": True
                },
                "Función"
            ],
            [
                (
                    "Centro NOC",
                    "Estado ejecutivo, alertas y accesos rápidos."
                ),
                (
                    "SNMP",
                    "Diagnóstico, monitoreo y descubrimiento."
                ),
                (
                    "Inventario",
                    "Puertos, equipos, bloques y validaciones."
                ),
                (
                    "Topología",
                    "Dependencias, rutas al Core e impacto."
                ),
                (
                    "Administración",
                    "Switches, relaciones, respaldos e historial."
                ),
                (
                    "Reportes",
                    "Exportación del estado documentado."
                )
            ],
            expandir=True,
            mostrar_lineas=True
        )

        visual.info(
            "NetInventory 1.0 se encuentra en fase de "
            "estabilización funcional."
        )

    # ======================================================
    # FICHA COMPLETA DE RED
    # ======================================================

    def consultar_ficha_red(self):
        """
        Consulta una ficha mediante sector, switch y puerto.
        """
        self.ui.mostrar_titulo(
            "Ficha completa de red",
            limpiar=True
        )

        hoja = self.ui.pedir_texto(
            "Escribe la hoja o sector: "
        )

        nombre_real = (
            self.gestor_fichas
            .obtener_nombre_real_hoja(
                hoja
            )
        )

        if nombre_real is None:
            self.ui.mostrar_error(
                "No se encontró esa hoja o sector."
            )
            return

        self.ui.mostrar_exito(
            f"Hoja encontrada: {nombre_real}"
        )

        switches = (
            self.gestor_fichas
            .mostrar_switches_disponibles(
                nombre_real
            )
        )

        if not switches:
            self.ui.mostrar_aviso(
                "No hay switches disponibles "
                "para ese sector."
            )
            return

        seleccion = self.ui.pedir_texto(
            "\nSelecciona un switch: "
        )

        try:
            switch = (
                self.gestor_fichas
                .obtener_switch_por_indice(
                    switches,
                    seleccion
                )
            )

        except ValueError as error:
            self.ui.mostrar_error(
                str(error)
            )
            return

        puerto = self.ui.pedir_entero(
            "Escribe el número de puerto: ",
            minimo=1
        )

        try:
            fichas = (
                self.gestor_fichas
                .construir_fichas(
                    hoja_buscada=nombre_real,
                    switch=switch,
                    puerto_buscado=puerto
                )
            )

        except ValueError as error:
            self.ui.mostrar_error(
                str(error)
            )
            return

        self.gestor_fichas.mostrar_fichas(
            fichas
        )

    # ======================================================
    # REPORTE EXCEL
    # ======================================================

    def generar_reporte(self):
        """
        Genera el reporte Excel del inventario actual.
        """
        self.ui.mostrar_titulo(
            "Generar reporte Excel",
            limpiar=True
        )

        self.ui.mostrar_info(
            "Preparando el reporte del inventario."
        )

        ruta = self.exportador.exportar_reporte(
            self.inventario
        )

        if ruta is None:
            self.ui.mostrar_error(
                "No fue posible generar el reporte."
            )
            return

        self.ui.mostrar_exito(
            "Reporte generado correctamente."
        )

        print(
            f"\nRuta: {ruta}"
        )

        if not self.ui.confirmar(
            "\n¿Deseas abrir el reporte ahora?"
        ):
            return

        try:
            os.startfile(
                ruta
            )

        except AttributeError:
            self.ui.mostrar_aviso(
                "La apertura automática solamente "
                "está disponible en Windows."
            )

        except OSError as error:
            self.ui.mostrar_error(
                "El reporte fue generado, pero no "
                f"pudo abrirse automáticamente: {error}"
            )

    # ======================================================
    # AUTENTICACIÓN
    # ======================================================

    def autenticar_accesos(self):
        """
        Protege las funciones que contienen credenciales.
        """
        self.ui.mostrar_titulo(
            "Acceso protegido",
            limpiar=True
        )

        clave_correcta = os.getenv(
            "CLAVE_ACCESOS"
        )

        if not clave_correcta:
            self.ui.mostrar_error(
                "No se configuró CLAVE_ACCESOS "
                "en el archivo .env."
            )
            self.ui.pausar()
            return False

        self.ui.mostrar_aviso(
            "Este módulo contiene información sensible."
        )

        for intento in range(
            1,
            self.MAX_INTENTOS_ACCESO + 1
        ):
            clave_ingresada = getpass(
                "\nContraseña de acceso: "
            )

            if clave_ingresada == clave_correcta:
                self.ui.mostrar_exito(
                    "Acceso autorizado."
                )
                return True

            intentos_restantes = (
                self.MAX_INTENTOS_ACCESO
                - intento
            )

            if intentos_restantes > 0:
                self.ui.mostrar_error(
                    "Contraseña incorrecta. "
                    f"Intentos restantes: "
                    f"{intentos_restantes}"
                )

        self.ui.mostrar_error(
            "Acceso denegado."
        )

        self.ui.pausar()

        return False

    # ======================================================
    # MENÚ DE SWITCHES
    # ======================================================

    def mostrar_menu_accesos(self):
        """
        Muestra la administración de red usando Rich.

        Este menú aparece después de superar la autenticación,
        por lo que concentra funciones administrativas,
        credenciales, topología, respaldos e historial.
        """
        switches = len(
            self.gestor_accesos.listar_todos()
        )

        try:
            resultado_relaciones = (
                self.gestor_relaciones
                .validar_relaciones()
            )

            relaciones_validas = len(
                resultado_relaciones.get(
                    "validas",
                    []
                )
            )

            relaciones_invalidas = len(
                resultado_relaciones.get(
                    "invalidas",
                    []
                )
            )

            sin_relacion = len(
                resultado_relaciones.get(
                    "sin_relacion",
                    []
                )
            )

        except Exception:
            relaciones_validas = 0
            relaciones_invalidas = 0
            sin_relacion = 0

        visual.limpiar()
        visual.titulo(
            "ADMINISTRACIÓN DE RED",
            "Switches, relaciones, topología y seguridad"
        )

        visual.dashboard(
            [
                {
                    "titulo": "🖧 Switches",
                    "contenido": str(switches),
                    "color": "bright_blue",
                    "subtitulo": "Registrados en SQLite"
                },
                {
                    "titulo": "🔗 Relaciones",
                    "contenido": str(
                        relaciones_validas
                    ),
                    "color": "green",
                    "subtitulo": "Válidas"
                },
                {
                    "titulo": "⚠ Inválidas",
                    "contenido": str(
                        relaciones_invalidas
                    ),
                    "color": (
                        "red"
                        if relaciones_invalidas
                        else "green"
                    )
                },
                {
                    "titulo": "📄 Sin relación",
                    "contenido": str(
                        sin_relacion
                    ),
                    "color": (
                        "yellow"
                        if sin_relacion
                        else "green"
                    )
                }
            ]
        )

        visual.panel_estado(
            "Sesión protegida",
            [
                (
                    "🔐",
                    "Acceso autorizado mediante la clave "
                    "administrativa de NetInventory."
                ),
                (
                    "👁",
                    "Las credenciales de los switches se "
                    "mostrarán en sus fichas."
                ),
                (
                    "💾",
                    "Las operaciones sensibles crean respaldo "
                    "antes de modificar SQLite."
                )
            ],
            "yellow"
        )

        visual.menu_paneles(
            "HERRAMIENTAS ADMINISTRATIVAS",
            [
                {
                    "titulo": "SWITCHES",
                    "icono": "🖧",
                    "color": "cyan",
                    "opciones": [
                        (
                            "1",
                            "Buscar switch"
                        ),
                        (
                            "2",
                            "Mostrar todos los switches"
                        ),
                        (
                            "3",
                            "Importar o actualizar desde PASSSWITCH"
                        )
                    ]
                },
                {
                    "titulo": "RELACIONES CON INVENTARIO",
                    "icono": "🔗",
                    "color": "green",
                    "opciones": [
                        (
                            "4",
                            "Relacionar switch con bloque"
                        ),
                        (
                            "5",
                            "Mostrar relaciones"
                        ),
                        (
                            "6",
                            "Validar relaciones"
                        ),
                        (
                            "7",
                            "Quitar una relación"
                        )
                    ]
                },
                {
                    "titulo": "SEGURIDAD Y TRAZABILIDAD",
                    "icono": "💾",
                    "color": "yellow",
                    "opciones": [
                        (
                            "8",
                            "Mostrar respaldos"
                        ),
                        (
                            "9",
                            "Restaurar respaldo"
                        ),
                        (
                            "10",
                            "Mostrar historial"
                        ),
                        (
                            "11",
                            "Buscar en historial"
                        )
                    ]
                },
                {
                    "titulo": "TOPOLOGÍA",
                    "icono": "🌳",
                    "color": "magenta",
                    "opciones": [
                        (
                            "12",
                            "Gestionar topología de red"
                        ),
                        (
                            "0",
                            "Volver"
                        )
                    ]
                }
            ]
        )

        visual.pie(
            [
                "Módulo protegido",
                "SQLite operativo",
                "Excel de solo lectura"
            ]
        )

    def ejecutar_menu_accesos(self):
        """
        Ejecuta el menú protegido.
        """
        while True:
            self.mostrar_menu_accesos()

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
                "6",
                "7",
                "8",
                "9",
                "10",
                "11",
                "12"
            }:
                visual.limpiar()

            if opcion == "1":
                self.buscar_acceso()
                self.ui.pausar()

            elif opcion == "2":
                self.mostrar_todos_los_switches()
                self.ui.pausar()

            elif opcion == "3":
                self.importar_switches()
                self.ui.pausar()

            elif opcion == "4":
                self.relacionar_switch()
                self.ui.pausar()

            elif opcion == "5":
                self.gestor_relaciones.mostrar_relaciones()
                self.ui.pausar()

            elif opcion == "6":
                self.validar_relaciones()
                self.ui.pausar()

            elif opcion == "7":
                self.quitar_relacion_switch()
                self.ui.pausar()

            elif opcion == "8":
                self.mostrar_respaldos()
                self.ui.pausar()

            elif opcion == "9":
                self.restaurar_respaldo()
                self.ui.pausar()

            elif opcion == "10":
                self.mostrar_historial()
                self.ui.pausar()

            elif opcion == "11":
                self.buscar_historial()
                self.ui.pausar()

            elif opcion == "12":
                self.ejecutar_menu_topologia()

            elif opcion == "0":
                break

            else:
                self.ui.mostrar_error(
                    "Opción inválida. "
                    "Selecciona una opción disponible."
                )
                self.ui.pausar()

    def buscar_acceso(self):
        """
        Busca switches almacenados en SQLite.
        """
        visual.limpiar()
        visual.titulo(
            "BUSCAR SWITCH",
            "IP, MAC, marca, modelo, usuario o ubicación"
        )

        texto = self.ui.pedir_texto(
            "\n¿Qué deseas buscar?: "
        )

        resultados = self.gestor_accesos.buscar(
            texto
        )

        self.presentador_switches.mostrar_lista(
            resultados,
            titulo=f"Resultados para: {texto}"
        )

    def mostrar_todos_los_switches(self):
        """
        Muestra los switches registrados.
        """
        switches = (
            self.gestor_accesos
            .listar_todos()
        )

        self.presentador_switches.mostrar_lista(
            switches,
            titulo="Switches registrados"
        )

    def crear_respaldo_previo(self):
        """
        Crea un respaldo antes de modificar SQLite.
        """
        try:
            ruta_respaldo = (
                self.gestor_respaldos
                .crear_respaldo()
            )

        except (
            OSError,
            ValueError
        ) as error:
            self.ui.mostrar_error(
                "No fue posible crear el respaldo: "
                f"{error}"
            )
            return False

        if ruta_respaldo is None:
            self.ui.mostrar_info(
                "La base de datos todavía no existe. "
                "No fue necesario crear un respaldo."
            )
            return True

        self.ui.mostrar_exito(
            "Respaldo creado correctamente."
        )

        print(
            f"\nRuta: {ruta_respaldo}"
        )

        return True

    def mostrar_respaldos(self):
        """
        Muestra los respaldos disponibles.
        """
        self.ui.mostrar_titulo(
            "Respaldos disponibles",
            limpiar=True
        )

        respaldos = (
            self.gestor_respaldos
            .listar_respaldos()
        )

        if not respaldos:
            self.ui.mostrar_info(
                "No existen respaldos todavía."
            )
            return []

        for numero, respaldo in enumerate(
            respaldos,
            start=1
        ):
            informacion = (
                self.gestor_respaldos
                .obtener_informacion_respaldo(
                    respaldo
                )
            )

            print(
                f"\n{numero}) "
                f"{informacion['fecha']} | "
                f"{informacion['tamano_kb']} KB"
            )

        self.ui.mostrar_info(
            "Se conservan automáticamente los "
            f"{self.gestor_respaldos.maximo_respaldos} "
            "respaldos más recientes."
        )

        return respaldos

    def restaurar_respaldo(self):
        """
        Restaura un respaldo seleccionado.
        """
        self.ui.mostrar_titulo(
            "Restaurar respaldo",
            limpiar=True
        )

        respaldos = self.mostrar_respaldos()

        if not respaldos:
            return

        seleccion = self.ui.pedir_entero(
            "\nSelecciona el respaldo: ",
            minimo=1,
            maximo=len(respaldos)
        )

        try:
            respaldo = (
                self.gestor_respaldos
                .obtener_respaldo_por_indice(
                    seleccion
                )
            )

        except ValueError as error:
            self.ui.mostrar_error(
                str(error)
            )
            return

        informacion = (
            self.gestor_respaldos
            .obtener_informacion_respaldo(
                respaldo
            )
        )

        self.ui.mostrar_subtitulo(
            "Respaldo seleccionado"
        )

        print(
            f"Fecha: {informacion['fecha']}"
        )
        print(
            f"Tamaño: {informacion['tamano_kb']} KB"
        )

        self.ui.mostrar_aviso(
            "La base de datos actual será reemplazada. "
            "Antes se guardará una copia del estado actual."
        )

        if not self.ui.confirmar(
            "\n¿Deseas continuar?"
        ):
            self.ui.mostrar_info(
                "Restauración cancelada."
            )
            return

        if not self.ui.confirmar_texto(
            "Escribe RESTAURAR para confirmar: ",
            "RESTAURAR"
        ):
            self.ui.mostrar_info(
                "La confirmación no coincide. "
                "Restauración cancelada."
            )
            return

        try:
            resultado = (
                self.gestor_respaldos
                .restaurar_respaldo(
                    respaldo
                )
            )

        except (
            FileNotFoundError,
            ValueError,
            OSError
        ) as error:
            self.ui.mostrar_error(
                f"No se pudo restaurar: {error}"
            )
            return

        self.ui.mostrar_exito(
            "Respaldo restaurado correctamente."
        )

        print(
            "\nBase restaurada desde: "
            f"{resultado['restaurado'].name}"
        )

        respaldo_actual = resultado.get(
            "respaldo_estado_actual"
        )

        if respaldo_actual is not None:
            print(
                "Copia del estado anterior: "
                f"{respaldo_actual.name}"
            )

        self.ui.mostrar_aviso(
            "Cierra y vuelve a ejecutar NetInventory "
            "para cargar los datos restaurados."
        )

    # ======================================================
    # IMPORTACIÓN PASSSWITCH
    # ======================================================

    def importar_switches(self):
        """
        Sincroniza SQLite con la hoja PASSSWITCH.
        """
        self.ui.mostrar_titulo(
            "Importar o actualizar",
            limpiar=True
        )

        self.ui.mostrar_info(
            "PASSSWITCH es la fuente oficial "
            "de información de los switches."
        )

        print(
            "\nEl Excel será leído, pero nunca modificado."
        )

        if not self.ui.confirmar(
            "\n¿Deseas continuar?"
        ):
            self.ui.mostrar_info(
                "Importación cancelada."
            )
            return

        if not self.crear_respaldo_previo():
            self.ui.mostrar_error(
                "La importación fue cancelada para "
                "proteger la base de datos."
            )
            return

        try:
            resultado = (
                self.gestor_accesos
                .importar_desde_passswitch(
                    self.ruta_excel
                )
            )

        except Exception as error:
            self.ui.mostrar_error(
                "Error durante la importación: "
                f"{error}"
            )
            return

        self.ui.mostrar_exito(
            "Importación finalizada."
        )

        self.ui.mostrar_subtitulo(
            "Resultado"
        )

        print(
            f"Switches nuevos: "
            f"{resultado['nuevos']}"
        )
        print(
            f"Switches actualizados: "
            f"{resultado['actualizados']}"
        )
        print(
            f"Switches sin cambios: "
            f"{resultado.get('sin_cambios', 0)}"
        )
        print(
            f"Filas ignoradas: "
            f"{len(resultado['ignorados'])}"
        )
        print(
            f"Errores: "
            f"{len(resultado['errores'])}"
        )

        if resultado["ignorados"]:
            self.ui.mostrar_subtitulo(
                "Filas ignoradas"
            )

            for item in resultado["ignorados"]:
                print(
                    f"- Fila {item['fila']}: "
                    f"{item['motivo']}"
                )

        if resultado["errores"]:
            self.ui.mostrar_subtitulo(
                "Errores"
            )

            for item in resultado["errores"]:
                print(
                    f"- Fila {item['fila']} | "
                    f"Octeto {item['octeto']}: "
                    f"{item['motivo']}"
                )

        switches_ausentes = resultado.get(
            "ausentes",
            []
        )

        if not switches_ausentes:
            self.ui.mostrar_info(
                "No hay switches ausentes "
                "en PASSSWITCH."
            )
            return

        self.ui.mostrar_subtitulo(
            "Switches ausentes"
        )

        for switch in switches_ausentes:
            print(
                f"- {switch.get('ip')} | "
                f"{switch.get('ubicacion') or 'Sin ubicación'}"
            )

        self.ui.mostrar_aviso(
            "Los switches ausentes no se eliminarán "
            "automáticamente."
        )

        if not self.ui.confirmar(
            "\n¿Deseas eliminarlos de la base de datos?"
        ):
            self.ui.mostrar_info(
                "Los switches se mantuvieron."
            )
            return

        if not self.ui.confirmar(
            "¿Confirmas la eliminación?"
        ):
            self.ui.mostrar_info(
                "Eliminación cancelada."
            )
            return

        resultado_eliminacion = (
            self.gestor_accesos
            .eliminar_switches_ausentes(
                switches_ausentes
            )
        )

        self.ui.mostrar_subtitulo(
            "Resultado de eliminación"
        )

        print(
            "Switches ausentes detectados: "
            f"{resultado_eliminacion['detectados']}"
        )
        print(
            "Switches eliminados: "
            f"{resultado_eliminacion['eliminados']}"
        )
        print(
            "Errores: "
            f"{len(resultado_eliminacion['errores'])}"
        )

    # ======================================================
    # RELACIONES SWITCH - BLOQUE
    # ======================================================

    def relacionar_switch(self):
        """
        Relaciona un switch con una hoja y bloque.
        """
        self.ui.mostrar_titulo(
            "Relacionar switch",
            limpiar=True
        )

        octeto = self.ui.pedir_entero(
            "Último octeto del switch: ",
            minimo=1,
            maximo=254
        )

        hoja = self.ui.pedir_texto(
            "Hoja del inventario: "
        )

        bloque = self.ui.pedir_entero(
            "Número de bloque: ",
            minimo=1
        )

        try:
            switch = (
                self.gestor_accesos
                .obtener_por_octeto(
                    octeto
                )
            )

        except ValueError as error:
            self.ui.mostrar_error(
                str(error)
            )
            return

        if switch is None:
            self.ui.mostrar_error(
                "No existe un switch con ese "
                "último octeto."
            )
            return

        nombre_real_hoja = (
            self.gestor_relaciones
            .obtener_nombre_real_hoja(
                hoja
            )
        )

        if nombre_real_hoja is None:
            self.ui.mostrar_error(
                "La hoja indicada no existe "
                "en el inventario."
            )
            return

        if not self.gestor_relaciones.bloque_existe(
            nombre_real_hoja,
            bloque
        ):
            self.ui.mostrar_error(
                f"El bloque {bloque} no existe "
                f"en la hoja {nombre_real_hoja}."
            )
            return

        switch_actual = (
            self.gestor_relaciones
            .obtener_switch_por_bloque(
                nombre_real_hoja,
                bloque
            )
        )

        reemplazar = False

        if (
            switch_actual is not None
            and switch_actual.get(
                "ultimo_octeto"
            )
            != switch.get(
                "ultimo_octeto"
            )
        ):
            self.ui.mostrar_aviso(
                "Ese bloque ya está relacionado con "
                f"{switch_actual.get('ip')}."
            )

            if not self.ui.confirmar(
                "¿Deseas reemplazar la relación?"
            ):
                self.ui.mostrar_info(
                    "Operación cancelada."
                )
                return

            reemplazar = True

        if not self.crear_respaldo_previo():
            self.ui.mostrar_error(
                "La operación fue cancelada para "
                "proteger la base de datos."
            )
            return

        try:
            relacion = (
                self.gestor_relaciones
                .relacionar(
                    ultimo_octeto=octeto,
                    hoja=nombre_real_hoja,
                    bloque=bloque,
                    reemplazar=reemplazar
                )
            )

        except ValueError as error:
            self.ui.mostrar_error(
                "No se pudo guardar la relación: "
                f"{error}"
            )
            return

        self.ui.mostrar_exito(
            "Relación guardada correctamente."
        )

        print(
            f"\nSwitch: "
            f"{relacion['switch'].get('ip')}"
        )
        print(
            f"Hoja: {relacion['hoja']}"
        )
        print(
            f"Bloque: {relacion['bloque']}"
        )

    def validar_relaciones(self):
        """
        Revisa las relaciones entre switches y bloques.
        """
        self.ui.mostrar_titulo(
            "Validar relaciones",
            limpiar=True
        )

        resultado = (
            self.gestor_relaciones
            .mostrar_validacion_relaciones()
        )

        relaciones_invalidas = resultado.get(
            "invalidas",
            []
        )

        if not relaciones_invalidas:
            self.ui.mostrar_exito(
                "No existen relaciones inválidas."
            )
            return

        if not self.ui.confirmar(
            "\n¿Deseas quitar todas las "
            "relaciones inválidas?"
        ):
            self.ui.mostrar_info(
                "Las relaciones inválidas "
                "se mantuvieron."
            )
            return

        if not self.ui.confirmar(
            "¿Confirmas la limpieza?"
        ):
            self.ui.mostrar_info(
                "Limpieza cancelada."
            )
            return

        if not self.crear_respaldo_previo():
            self.ui.mostrar_error(
                "La limpieza fue cancelada para "
                "proteger la base de datos."
            )
            return

        resultado_limpieza = (
            self.gestor_relaciones
            .limpiar_relaciones_invalidas()
        )

        self.ui.mostrar_exito(
            "Validación y limpieza finalizadas."
        )

        print(
            "\nRelaciones inválidas detectadas: "
            f"{resultado_limpieza['detectadas']}"
        )
        print(
            "Relaciones quitadas: "
            f"{resultado_limpieza['eliminadas']}"
        )
        print(
            "Errores: "
            f"{len(resultado_limpieza['errores'])}"
        )

    def quitar_relacion_switch(self):
        """
        Quita una relación sin eliminar el switch.
        """
        self.ui.mostrar_titulo(
            "Quitar relación",
            limpiar=True
        )

        octeto = self.ui.pedir_entero(
            "Último octeto del switch: ",
            minimo=1,
            maximo=254
        )

        try:
            relacion = (
                self.gestor_relaciones
                .obtener_relacion_por_octeto(
                    octeto
                )
            )

        except ValueError as error:
            self.ui.mostrar_error(
                str(error)
            )
            return

        if relacion is None:
            self.ui.mostrar_error(
                "No existe ese switch."
            )
            return

        if (
            relacion["hoja"] is None
            or relacion["bloque"] is None
        ):
            self.ui.mostrar_info(
                "Ese switch no tiene una "
                "relación guardada."
            )
            return

        print(
            f"\nSwitch: "
            f"{relacion['switch'].get('ip')}"
        )
        print(
            f"Hoja actual: {relacion['hoja']}"
        )
        print(
            f"Bloque actual: {relacion['bloque']}"
        )

        if not self.ui.confirmar(
            "\n¿Confirmas quitar esta relación?"
        ):
            self.ui.mostrar_info(
                "Operación cancelada."
            )
            return

        if not self.crear_respaldo_previo():
            self.ui.mostrar_error(
                "La operación fue cancelada para "
                "proteger la base de datos."
            )
            return

        try:
            eliminado = (
                self.gestor_relaciones
                .quitar_relacion(
                    octeto
                )
            )

        except ValueError as error:
            self.ui.mostrar_error(
                str(error)
            )
            return

        if eliminado:
            self.ui.mostrar_exito(
                "Relación eliminada correctamente."
            )

        else:
            self.ui.mostrar_error(
                "No fue posible eliminar la relación."
            )


    # ======================================================
    # TOPOLOGÍA DE RED
    # ======================================================

    def mostrar_menu_topologia(self):
        """
        Muestra las opciones de gestión de topología.
        """
        self.ui.mostrar_titulo(
            "Gestión de topología de red",
            limpiar=True
        )

        self.ui.mostrar_lista_opciones(
            [
                ("1", "Mostrar árbol de topología"),
                ("2", "Clasificar un switch"),
                ("3", "Asignar switch padre"),
                ("4", "Quitar switch padre"),
                ("5", "Ver detalle e impacto"),
                ("6", "Validar topología"),
                ("0", "Volver")
            ]
        )

    def ejecutar_menu_topologia(self):
        """
        Ejecuta el menú de topología.
        """
        while True:
            self.mostrar_menu_topologia()

            opcion = input(
                "\nSelecciona una opción: "
            ).strip()

            if opcion == "1":
                self.ui.limpiar_pantalla()
                self.gestor_topologia.mostrar_arbol()
                self.ui.pausar()

            elif opcion == "2":
                self.clasificar_switch_topologia()
                self.ui.pausar()

            elif opcion == "3":
                self.asignar_padre_topologia()
                self.ui.pausar()

            elif opcion == "4":
                self.quitar_padre_topologia()
                self.ui.pausar()

            elif opcion == "5":
                self.ver_detalle_topologia()
                self.ui.pausar()

            elif opcion == "6":
                self.validar_topologia()
                self.ui.pausar()

            elif opcion == "0":
                break

            else:
                self.ui.mostrar_error(
                    "Opción inválida. Selecciona una opción disponible."
                )
                self.ui.pausar()

    def listar_switches_topologia(self, excluir_id=None):
        """
        Muestra una lista numerada de switches.
        """
        switches = self.gestor_topologia.listar_switches()

        if excluir_id is not None:
            switches = [
                switch
                for switch in switches
                if switch.get("id") != excluir_id
            ]

        if not switches:
            self.ui.mostrar_error(
                "No existen switches disponibles."
            )
            return []

        print(
            "\n"
            f"{'N.º':<5}"
            f"{'IP':<18}"
            f"{'Nombre lógico':<35}"
            f"{'Rol':<16}"
            f"{'Criticidad':<14}"
        )
        print("-" * 88)

        for numero, switch in enumerate(switches, start=1):
            nombre = (
                switch.get("nombre_logico")
                or switch.get("nombre")
                or switch.get("ubicacion")
                or "Sin nombre"
            )

            print(
                f"{numero:<5}"
                f"{str(switch.get('ip') or '-')[:17]:<18}"
                f"{str(nombre)[:34]:<35}"
                f"{str(switch.get('rol') or 'NO DEFINIDO')[:15]:<16}"
                f"{str(switch.get('criticidad') or 'NO DEFINIDA')[:13]:<14}"
            )

        return switches

    def seleccionar_switch_topologia(
        self,
        titulo,
        excluir_id=None
    ):
        """
        Selecciona un switch mediante una lista numerada.
        """
        self.ui.mostrar_titulo(
            titulo,
            limpiar=True
        )

        switches = self.listar_switches_topologia(
            excluir_id=excluir_id
        )

        if not switches:
            return None

        print("\n0) Cancelar")

        while True:
            seleccion = input(
                "\nSelecciona un switch: "
            ).strip()

            if seleccion == "0":
                return None

            try:
                indice = int(seleccion)
            except ValueError:
                self.ui.mostrar_error(
                    "Debes ingresar el número de una opción."
                )
                continue

            if not 1 <= indice <= len(switches):
                self.ui.mostrar_error(
                    "La opción seleccionada no existe."
                )
                continue

            return switches[indice - 1]

    def pedir_opcion_topologia(
        self,
        titulo,
        opciones,
        valor_actual
    ):
        """
        Solicita una opción cerrada.
        """
        print(f"\n{titulo}:")

        for numero, opcion in enumerate(opciones, start=1):
            print(f"{numero}) {opcion}")

        print(f"\nValor actual: {valor_actual}")

        while True:
            seleccion = input(
                "Selecciona una opción [Enter para conservar]: "
            ).strip()

            if not seleccion:
                return valor_actual

            try:
                indice = int(seleccion)
            except ValueError:
                self.ui.mostrar_error(
                    "Debes ingresar el número de una opción."
                )
                continue

            if not 1 <= indice <= len(opciones):
                self.ui.mostrar_error(
                    "La opción seleccionada no existe."
                )
                continue

            return opciones[indice - 1]

    def pedir_booleano_topologia(
        self,
        titulo,
        valor_actual
    ):
        """
        Solicita Sí, No o Sin definir.
        """
        actual = self.gestor_topologia.texto_booleano(
            valor_actual
        )

        opcion = self.pedir_opcion_topologia(
            titulo,
            ["Sí", "No", "Sin definir"],
            actual
        )

        if opcion == "Sí":
            return 1

        if opcion == "No":
            return 0

        return None

    def clasificar_switch_topologia(self):
        """
        Clasifica un switch.
        """
        switch = self.seleccionar_switch_topologia(
            "Clasificar switch"
        )

        if switch is None:
            return

        nombre_actual = (
            switch.get("nombre_logico")
            or switch.get("nombre")
            or ""
        )

        nombre_logico = input(
            f"\nNombre lógico [{nombre_actual}]: "
        ).strip() or nombre_actual

        rol = self.pedir_opcion_topologia(
            "Rol",
            ["CORE", "DISTRIBUCION", "ACCESO", "NO DEFINIDO"],
            switch.get("rol") or "NO DEFINIDO"
        )

        criticidad = self.pedir_opcion_topologia(
            "Criticidad",
            ["CRITICA", "ALTA", "MEDIA", "BAJA", "NO DEFINIDA"],
            switch.get("criticidad") or "NO DEFINIDA"
        )

        tiene_poe = self.pedir_booleano_topologia(
            "¿El switch tiene PoE?",
            switch.get("tiene_poe")
        )

        tiene_ups = self.pedir_booleano_topologia(
            "¿El switch tiene respaldo UPS?",
            switch.get("tiene_ups")
        )

        notas_actuales = switch.get("notas_topologia") or ""
        notas = input(
            f"\nNotas [{notas_actuales or 'sin notas'}]: "
        ).strip() or notas_actuales or None

        if not self.ui.confirmar(
            "\n¿Guardar esta clasificación?"
        ):
            return

        if not self.crear_respaldo_previo():
            return

        try:
            actualizado = self.gestor_topologia.actualizar_clasificacion(
                switch_id=switch["id"],
                nombre_logico=nombre_logico,
                rol=rol,
                criticidad=criticidad,
                tiene_poe=tiene_poe,
                tiene_ups=tiene_ups,
                notas_topologia=notas
            )
        except ValueError as error:
            self.ui.mostrar_error(str(error))
            return

        self.ui.mostrar_exito(
            "Clasificación guardada correctamente."
        )
        self.gestor_topologia.mostrar_switch(actualizado)

    def asignar_padre_topologia(self):
        """
        Asigna un padre y documenta ambos extremos del enlace.
        """
        hijo = self.seleccionar_switch_topologia(
            "Seleccionar switch hijo"
        )

        if hijo is None:
            return

        padre = self.seleccionar_switch_topologia(
            "Seleccionar switch padre",
            excluir_id=hijo.get("id")
        )

        if padre is None:
            return

        enlace_actual = (
            self.gestor_topologia
            .obtener_enlace_por_hijo(
                hijo.get("id")
            )
            or {}
        )

        puerto_padre_actual = (
            enlace_actual.get("puerto_padre")
            or hijo.get("puerto_subida")
            or ""
        )
        puerto_hijo_actual = (
            enlace_actual.get("puerto_hijo")
            or ""
        )

        puerto_padre = input(
            "\nPuerto del switch padre "
            f"[{puerto_padre_actual or 'sin definir'}]: "
        ).strip() or puerto_padre_actual or None

        puerto_hijo = input(
            "Puerto del switch hijo "
            f"[{puerto_hijo_actual or 'sin definir'}]: "
        ).strip() or puerto_hijo_actual or None

        tecnologia_actual = (
            enlace_actual.get("tecnologia")
            or hijo.get("tecnologia_subida")
            or "NO DEFINIDA"
        )

        tecnologia = self.pedir_opcion_topologia(
            "Tecnología del enlace",
            [
                "FIBRA",
                "COBRE",
                "INALAMBRICO",
                "OTRA",
                "NO DEFINIDA"
            ],
            tecnologia_actual
        )

        print(
            f"\nPadre: {padre.get('ip')} | "
            f"{self.gestor_topologia.nombre_visible(padre)}"
        )
        print(
            f"Puerto padre: {puerto_padre or 'Sin definir'}"
        )
        print("                 │")
        print(f"Medio: {tecnologia}")
        print("                 │")
        print(
            f"Puerto hijo: {puerto_hijo or 'Sin definir'}"
        )
        print(
            f"Hijo: {hijo.get('ip')} | "
            f"{self.gestor_topologia.nombre_visible(hijo)}"
        )

        if not self.ui.confirmar(
            "\n¿Guardar este enlace?"
        ):
            return

        if not self.crear_respaldo_previo():
            return

        try:
            actualizado = self.gestor_topologia.asignar_padre(
                switch_id=hijo["id"],
                padre_id=padre["id"],
                puerto_padre=puerto_padre,
                puerto_hijo=puerto_hijo,
                tecnologia_subida=tecnologia
            )
        except ValueError as error:
            self.ui.mostrar_error(str(error))
            return

        self.ui.mostrar_exito(
            "Enlace de red guardado correctamente."
        )
        self.gestor_topologia.mostrar_switch(actualizado)

    def quitar_padre_topologia(self):
        """
        Quita el padre de un switch.
        """
        switch = self.seleccionar_switch_topologia(
            "Quitar switch padre"
        )

        if switch is None:
            return

        padre = self.gestor_topologia.obtener_padre(
            switch.get("id")
        )

        if padre is None:
            self.ui.mostrar_info(
                "El switch seleccionado no tiene padre."
            )
            return

        print(
            f"\nHijo: {switch.get('ip')} | "
            f"{self.gestor_topologia.nombre_visible(switch)}"
        )
        print(
            f"Padre: {padre.get('ip')} | "
            f"{self.gestor_topologia.nombre_visible(padre)}"
        )

        if not self.ui.confirmar(
            "\n¿Confirmas quitar esta relación?"
        ):
            return

        if not self.crear_respaldo_previo():
            return

        try:
            actualizado = self.gestor_topologia.asignar_padre(
                switch_id=switch["id"],
                padre_id=None
            )
        except ValueError as error:
            self.ui.mostrar_error(str(error))
            return

        self.ui.mostrar_exito(
            "El switch quedó sin padre asignado."
        )
        self.gestor_topologia.mostrar_switch(actualizado)

    def ver_detalle_topologia(self):
        """
        Muestra detalle e impacto.
        """
        switch = self.seleccionar_switch_topologia(
            "Detalle e impacto topológico"
        )

        if switch is None:
            return

        resumen = self.gestor_topologia.obtener_resumen_switch(
            switch.get("id")
        )

        self.gestor_topologia.mostrar_switch(
            resumen["switch"]
        )

        print("\n--------------- IMPACTO ----------------")
        print(f"Nivel topológico: {resumen['nivel']}")
        print(f"Hijos directos: {resumen['cantidad_hijos']}")
        print(
            "Descendientes totales: "
            f"{resumen['cantidad_descendientes']}"
        )
        print(
            "Impacto potencial mínimo: "
            f"{resumen['impacto_estimado']} switches"
        )

        if resumen["hijos"]:
            print("\nHijos directos:")
            for hijo in resumen["hijos"]:
                print(
                    f"- {hijo.get('ip')} | "
                    f"{self.gestor_topologia.nombre_visible(hijo)}"
                )

        if resumen["descendientes"]:
            print("\nTodos los descendientes:")
            for descendiente in resumen["descendientes"]:
                print(
                    f"- {descendiente.get('ip')} | "
                    f"{self.gestor_topologia.nombre_visible(descendiente)}"
                )

    def validar_topologia(self):
        """
        Valida la topología.
        """
        self.ui.mostrar_titulo(
            "Validar topología",
            limpiar=True
        )

        resultado = self.gestor_topologia.validar_topologia()

        print(
            f"\nSwitches registrados: "
            f"{resultado['total_switches']}"
        )
        print(
            f"Sin clasificar: "
            f"{len(resultado['sin_clasificar'])}"
        )
        print(
            f"Sin criticidad: "
            f"{len(resultado['sin_criticidad'])}"
        )
        print(
            "Sin padre y no definidos como Core: "
            f"{len(resultado['sin_padre'])}"
        )
        print(
            f"Ciclos detectados: "
            f"{len(resultado['ciclos'])}"
        )
        print(
            f"Padres inválidos: "
            f"{len(resultado['padres_invalidos'])}"
        )

        if resultado["correcta"]:
            self.ui.mostrar_exito(
                "No se detectaron ciclos ni padres inválidos."
            )
        else:
            self.ui.mostrar_error(
                "La topología contiene relaciones inválidas."
            )

    # ======================================================
    # HISTORIAL
    # ======================================================

    def mostrar_historial(self):
        """
        Muestra los eventos más recientes.
        """
        self.ui.mostrar_titulo(
            "Historial de cambios",
            limpiar=True
        )

        registros = (
            self.gestor_historial
            .listar(
                limite=50
            )
        )

        self.gestor_historial.mostrar(
            registros
        )

        print(
            "\nEventos totales guardados: "
            f"{self.gestor_historial.contar()}"
        )

    def buscar_historial(self):
        """
        Busca eventos en el historial.
        """
        self.ui.mostrar_titulo(
            "Buscar en historial",
            limpiar=True
        )

        texto = self.ui.pedir_texto(
            "Escribe IP, octeto, ubicación, "
            "acción o dato: "
        )

        registros = (
            self.gestor_historial
            .buscar(
                texto=texto,
                limite=100
            )
        )

        self.gestor_historial.mostrar(
            registros
        )