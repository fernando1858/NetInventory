import re
from typing import Any

from modulos.analizador_snmp import AnalizadorSNMP
from modulos.monitor_snmp import (
    MonitorSNMP,
    ResultadoMonitoreo
)
from modulos.snmp_cliente import (
    ClienteSNMP,
    ResultadoSNMP
)
from modulos.ui import InterfazUsuario
from modulos.visual import visual


class MonitorSNMPConsola:
    """
    Interfaz de consola para consultar y analizar switches
    mediante SNMP.

    El monitor funciona de manera independiente del Excel.

    Todas las operaciones SNMP implementadas son de lectura:
    GET y GETBULK. No modifica la configuración de los
    switches.
    """

    INTERVALO_PREDETERMINADO = 5.0

    def __init__(
        self,
        cliente_snmp: ClienteSNMP,
        gestor_accesos,
        inventario
    ):
        self.cliente_snmp = cliente_snmp
        self.gestor_accesos = gestor_accesos
        self.inventario = inventario

        self.monitor_snmp = MonitorSNMP(
            cliente_snmp=cliente_snmp
        )

        self.analizador_snmp = AnalizadorSNMP()

        self.ui = InterfazUsuario

        self.switch_actual = None

        self.ultima_medicion: (
            ResultadoMonitoreo | None
        ) = None

    # ======================================================
    # EJECUCIÓN GENERAL
    # ======================================================

    def ejecutar(self):
        """
        Inicia el monitor SNMP y solicita seleccionar
        un switch registrado en SQLite.
        """
        if not self.seleccionar_switch():
            self.ui.mostrar_info(
                "Monitor SNMP finalizado."
            )
            return

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
                "6",
                "7"
            }:
                visual.limpiar()

            if opcion == "1":
                self.mostrar_informacion_general()
                self.ui.pausar()

            elif opcion == "2":
                self.mostrar_estado_interfaces()
                self.ui.pausar()

            elif opcion == "3":
                self.medir_trafico_actual()
                self.ui.pausar()

            elif opcion == "4":
                self.mostrar_errores_nuevos()
                self.ui.pausar()

            elif opcion == "5":
                self.mostrar_enlaces_reducidos()
                self.ui.pausar()

            elif opcion == "6":
                self.analizar_salud_switch()
                self.ui.pausar()

            elif opcion == "7":
                self.cambiar_switch()

            elif opcion == "0":
                self.ui.mostrar_info(
                    "Monitor SNMP finalizado."
                )
                break

            else:
                self.ui.mostrar_error(
                    "Opción inválida. Selecciona una "
                    "opción disponible."
                )

                self.ui.pausar()

    # ======================================================
    # VALORES Y FORMATO
    # ======================================================

    @staticmethod
    def valor_visible(
        valor: Any,
        predeterminado: str = "Sin información"
    ) -> str:
        """
        Convierte valores vacíos en texto visible.
        """
        if valor is None:
            return predeterminado

        texto = str(
            valor
        ).strip()

        if not texto:
            return predeterminado

        return texto.strip(
            '"'
        )

    @staticmethod
    def obtener_ip_switch(
        switch: dict
    ) -> str | None:
        """
        Obtiene la dirección IP de un registro de switch.
        """
        ip = switch.get(
            "ip"
        )

        if ip is None:
            return None

        ip = str(
            ip
        ).strip()

        return ip or None

    @staticmethod
    def sumar_errores(
        interfaz: dict
    ) -> int:
        """
        Suma los errores acumulados de entrada y salida.
        """
        errores_entrada = int(
            interfaz.get(
                "errores_entrada",
                0
            )
            or 0
        )

        errores_salida = int(
            interfaz.get(
                "errores_salida",
                0
            )
            or 0
        )

        return (
            errores_entrada
            + errores_salida
        )

    @staticmethod
    def sumar_errores_nuevos(
        interfaz: dict
    ) -> int:
        """
        Suma los errores producidos entre dos muestras.
        """
        errores_entrada = int(
            interfaz.get(
                "errores_nuevos_entrada",
                0
            )
            or 0
        )

        errores_salida = int(
            interfaz.get(
                "errores_nuevos_salida",
                0
            )
            or 0
        )

        return (
            errores_entrada
            + errores_salida
        )

    def obtener_interfaces_fisicas(
        self,
        interfaces: list[dict]
    ) -> list[dict]:
        """
        Excluye interfaces lógicas conocidas.
        """
        return [
            interfaz
            for interfaz in interfaces
            if self.monitor_snmp.es_interfaz_fisica(
                interfaz
            )
        ]


    # ======================================================
    # CRUCE SNMP + INVENTARIO EXCEL
    # ======================================================

    @staticmethod
    def extraer_numero_puerto(
        nombre_interfaz: Any
    ) -> int | None:
        """
        Obtiene el número físico final desde nombres como:

        - 1/1/24
        - Gi1/0/24
        - GigabitEthernet1/0/24
        - GE24
        - 24

        Las interfaces lógicas ya son excluidas previamente
        por MonitorSNMP.
        """
        if nombre_interfaz is None:
            return None

        texto = str(
            nombre_interfaz
        ).strip()

        if not texto:
            return None

        numeros = re.findall(
            r"\d+",
            texto
        )

        if not numeros:
            return None

        try:
            return int(
                numeros[-1]
            )
        except ValueError:
            return None

    def obtener_registros_inventario_switch(
        self
    ) -> list[dict]:
        """
        Obtiene los puertos del bloque Excel relacionado con
        el switch seleccionado.
        """
        if self.switch_actual is None:
            return []

        hoja = self.switch_actual.get(
            "hoja_excel"
        )
        bloque = self.switch_actual.get(
            "bloque_excel"
        )

        if hoja is None or bloque is None:
            return []

        try:
            bloque = int(
                bloque
            )
        except (
            TypeError,
            ValueError
        ):
            return []

        hoja_normalizada = (
            self.inventario.normalizar_texto(
                hoja
            )
        )

        return [
            registro
            for registro in self.inventario.registros
            if (
                self.inventario.normalizar_texto(
                    registro.get("hoja")
                )
                == hoja_normalizada
                and registro.get("bloque") == bloque
            )
        ]

    def construir_mapa_inventario_puertos(
        self
    ) -> dict[int, dict]:
        """
        Crea un mapa puerto físico -> registro del Excel.
        """
        mapa = {}

        for registro in (
            self.obtener_registros_inventario_switch()
        ):
            puerto = registro.get(
                "puerto_switch"
            )

            try:
                puerto = int(
                    puerto
                )
            except (
                TypeError,
                ValueError
            ):
                continue

            mapa[puerto] = registro

        return mapa

    def enriquecer_interfaces_con_inventario(
        self,
        interfaces: list[dict]
    ) -> list[dict]:
        """
        Añade tipo, equipo, patch y VLAN del Excel a cada
        interfaz obtenida por SNMP.
        """
        mapa = self.construir_mapa_inventario_puertos()
        enriquecidas = []

        for interfaz in interfaces:
            copia = dict(
                interfaz
            )

            numero_puerto = self.extraer_numero_puerto(
                interfaz.get("nombre")
                or interfaz.get("descripcion")
            )

            registro = mapa.get(
                numero_puerto
            )

            copia[
                "numero_puerto_inventario"
            ] = numero_puerto

            if registro is None:
                copia.update(
                    {
                        "tipo_inventario": None,
                        "equipo_inventario": None,
                        "patch_inventario": None,
                        "vlan_inventario": None,
                        "registro_inventario": None,
                        "encontrado_inventario": False
                    }
                )
            else:
                copia.update(
                    {
                        "tipo_inventario": registro.get(
                            "tipo"
                        ),
                        "equipo_inventario": registro.get(
                            "equipo"
                        ),
                        "patch_inventario": registro.get(
                            "boca_patch"
                        ),
                        "vlan_inventario": registro.get(
                            "vlan"
                        ),
                        "registro_inventario": dict(registro),
                        "encontrado_inventario": True
                    }
                )

            enriquecidas.append(
                copia
            )

        return enriquecidas

    # ======================================================
    # SELECCIÓN DE SWITCH
    # ======================================================

    def obtener_switches_disponibles(
        self
    ) -> list[dict]:
        """
        Obtiene los switches registrados que tienen
        una dirección IPv4 válida.
        """
        switches = (
            self.gestor_accesos
            .listar_todos()
        )

        resultados = []

        for switch in switches:
            ip = self.obtener_ip_switch(
                switch
            )

            if not ip:
                continue

            try:
                self.cliente_snmp.validar_ip(
                    ip
                )

            except ValueError:
                continue

            resultados.append(
                switch
            )

        def clave_orden(switch):
            ultimo_octeto = switch.get(
                "ultimo_octeto"
            )

            try:
                return int(
                    ultimo_octeto
                )

            except (
                ValueError,
                TypeError
            ):
                ip = self.obtener_ip_switch(
                    switch
                )

                if not ip:
                    return 999

                try:
                    return int(
                        ip.split(".")[-1]
                    )

                except (
                    ValueError,
                    IndexError
                ):
                    return 999

        return sorted(
            resultados,
            key=clave_orden
        )

    def mostrar_lista_switches(
        self,
        switches: list[dict]
    ):
        """Muestra los switches disponibles sin exponer credenciales."""
        visual.limpiar()
        visual.titulo(
            "SELECCIONAR SWITCH",
            "Equipos registrados con una dirección IP válida"
        )

        if not switches:
            visual.error(
                "No existen switches con una IP válida en la base de datos."
            )
            return

        filas = []

        for numero, switch in enumerate(switches, start=1):
            filas.append(
                (
                    str(numero),
                    self.valor_visible(switch.get("ip")),
                    self.valor_visible(switch.get("ubicacion")),
                    self.valor_visible(switch.get("marca")),
                    self.valor_visible(switch.get("modelo"))
                )
            )

        visual.tabla(
            titulo="Switches disponibles",
            columnas=[
                {"nombre": "N.º", "justify": "right", "no_wrap": True},
                {"nombre": "IP", "style": "cyan", "no_wrap": True},
                "Ubicación",
                {"nombre": "Marca", "no_wrap": True},
                "Modelo"
            ],
            filas=filas,
            expandir=True
        )

        visual.info("Escribe 0 para cancelar la selección.")

    def seleccionar_switch(
        self
    ) -> bool:
        """
        Solicita seleccionar un switch registrado.

        Devuelve True si se seleccionó correctamente.
        """
        switches = self.obtener_switches_disponibles()

        self.mostrar_lista_switches(
            switches
        )

        if not switches:
            self.ui.pausar()
            return False

        while True:
            seleccion = input(
                "\nSelecciona un switch: "
            ).strip()

            if seleccion == "0":
                return False

            try:
                indice = int(
                    seleccion
                )

            except ValueError:
                self.ui.mostrar_error(
                    "Debes ingresar el número de "
                    "una opción."
                )
                continue

            if (
                indice < 1
                or indice > len(switches)
            ):
                self.ui.mostrar_error(
                    "La opción seleccionada no existe."
                )
                continue

            switch = switches[
                indice - 1
            ]

            ip = self.obtener_ip_switch(
                switch
            )

            try:
                ip = self.cliente_snmp.validar_ip(
                    ip
                )

            except ValueError as error:
                self.ui.mostrar_error(
                    "La dirección IP del switch "
                    f"no es válida: {error}"
                )
                continue

            self.switch_actual = switch
            self.ultima_medicion = None

            self.ui.mostrar_exito(
                f"Switch seleccionado: {ip}"
            )

            return True

    def cambiar_switch(self):
        """
        Permite seleccionar otro switch sin cerrar
        el monitor.
        """
        switch_anterior = self.switch_actual
        medicion_anterior = self.ultima_medicion

        seleccionado = self.seleccionar_switch()

        if seleccionado:
            return

        self.switch_actual = switch_anterior
        self.ultima_medicion = medicion_anterior

        self.ui.mostrar_info(
            "Se mantuvo el switch anterior."
        )

        self.ui.pausar()

    def obtener_ip_actual(
        self
    ) -> str:
        """
        Obtiene la IP del switch seleccionado.
        """
        if self.switch_actual is None:
            raise ValueError(
                "No existe un switch seleccionado."
            )

        ip = self.obtener_ip_switch(
            self.switch_actual
        )

        return self.cliente_snmp.validar_ip(
            ip
        )

    # ======================================================
    # MENÚ
    # ======================================================

    def mostrar_menu(self):
        """Muestra las funciones disponibles para el switch."""
        ip = self.obtener_ip_actual()
        ubicacion = self.valor_visible(
            self.switch_actual.get("ubicacion")
        )
        marca = self.valor_visible(
            self.switch_actual.get("marca")
        )
        modelo = self.valor_visible(
            self.switch_actual.get("modelo")
        )

        visual.limpiar()
        visual.titulo(
            "MONITOR SNMP",
            "Consultas detalladas de solo lectura"
        )

        visual.dashboard(
            [
                {
                    "titulo": "🌐 IP",
                    "contenido": ip,
                    "color": "cyan"
                },
                {
                    "titulo": "📍 Ubicación",
                    "contenido": ubicacion,
                    "color": "green"
                },
                {
                    "titulo": "🖧 Equipo",
                    "contenido": marca,
                    "subtitulo": modelo,
                    "color": "bright_blue"
                },
                {
                    "titulo": "📊 Medición",
                    "contenido": (
                        "Disponible"
                        if self.ultima_medicion is not None
                        else "Sin ejecutar"
                    ),
                    "color": (
                        "green"
                        if self.ultima_medicion is not None
                        else "grey50"
                    )
                }
            ]
        )

        visual.menu_paneles(
            "MENÚ DEL SWITCH",
            [
                {
                    "titulo": "CONSULTAS",
                    "icono": "🔎",
                    "color": "cyan",
                    "opciones": [
                        ("1", "Información general"),
                        ("2", "Estado de interfaces"),
                        ("3", "Medir tráfico actual")
                    ]
                },
                {
                    "titulo": "ANÁLISIS",
                    "icono": "🩺",
                    "color": "magenta",
                    "opciones": [
                        ("4", "Errores nuevos"),
                        ("5", "Velocidad reducida"),
                        ("6", "Salud del switch")
                    ]
                },
                {
                    "titulo": "NAVEGACIÓN",
                    "icono": "↩",
                    "color": "yellow",
                    "opciones": [
                        ("7", "Cambiar switch"),
                        ("0", "Volver")
                    ]
                }
            ]
        )

        visual.pie(
            [
                "SNMP v2c",
                ip,
                "Solo lectura",
                "Ctrl+C para interrumpir"
            ]
        )

    def mostrar_informacion_general(self):
        """Consulta los objetos estándar del grupo system."""
        visual.limpiar()
        visual.titulo(
            "INFORMACIÓN GENERAL",
            "Datos del sistema obtenidos mediante SNMP"
        )

        ip = self.obtener_ip_actual()
        visual.info(f"Consultando {ip} por SNMP.")

        resultado: ResultadoSNMP = (
            self.cliente_snmp.obtener_informacion_sistema(ip)
        )

        if not resultado.correcto:
            visual.error("No fue posible consultar el switch.")
            visual.imprimir(f"[dim]Detalle: {resultado.error}[/dim]")
            return

        datos = resultado.datos
        uptime = datos.get("uptime", {})

        filas = [
            ("IP", ip),
            ("Nombre", self.valor_visible(datos.get("nombre"))),
            ("Descripción", self.valor_visible(datos.get("descripcion"))),
            ("Ubicación SNMP", self.valor_visible(datos.get("ubicacion"))),
            (
                "Ubicación registrada",
                self.valor_visible(self.switch_actual.get("ubicacion"))
            ),
            ("Contacto", self.valor_visible(datos.get("contacto"))),
            ("OID del sistema", self.valor_visible(datos.get("oid_sistema"))),
            ("Tiempo encendido", self.valor_visible(uptime.get("texto")))
        ]

        visual.tabla(
            titulo="Sistema",
            columnas=[
                {"nombre": "Dato", "style": "cyan", "no_wrap": True},
                "Valor"
            ],
            filas=filas,
            expandir=True,
            mostrar_lineas=True
        )
        visual.ok("El switch respondió correctamente.")

    def mostrar_estado_interfaces(self):
        """
        Muestra estado administrativo, estado operativo,
        velocidad, errores e información del inventario Excel.
        """
        visual.limpiar()
        visual.titulo(
            "ESTADO DE INTERFACES",
            "SNMP + inventario documental del Excel"
        )

        ip = self.obtener_ip_actual()
        visual.info(f"Consultando interfaces de {ip}.")

        resultado = self.cliente_snmp.obtener_interfaces(ip)

        if not resultado.correcto:
            visual.error("No fue posible consultar las interfaces.")
            visual.imprimir(f"[dim]Detalle: {resultado.error}[/dim]")
            return

        interfaces = self.obtener_interfaces_fisicas(resultado.datos)
        interfaces = self.enriquecer_interfaces_con_inventario(interfaces)

        activas = sum(
            interfaz.get("estado_operativo") == "UP"
            for interfaz in interfaces
        )
        inactivas = len(interfaces) - activas
        con_errores = sum(
            self.sumar_errores(interfaz) > 0
            for interfaz in interfaces
        )
        identificadas = sum(
            interfaz.get("encontrado_inventario", False)
            for interfaz in interfaces
        )
        cobertura = (
            identificadas / len(interfaces) * 100
            if interfaces
            else 0.0
        )

        visual.dashboard(
            [
                {
                    "titulo": "🖧 Interfaces",
                    "contenido": str(len(interfaces)),
                    "color": "bright_blue"
                },
                {
                    "titulo": "✅ Activas",
                    "contenido": str(activas),
                    "color": "green"
                },
                {
                    "titulo": "⛔ Inactivas",
                    "contenido": str(inactivas),
                    "color": "red" if inactivas else "green"
                },
                {
                    "titulo": "⚠ Errores",
                    "contenido": str(con_errores),
                    "color": "red" if con_errores else "green"
                },
                {
                    "titulo": "📄 Inventario",
                    "contenido": f"{identificadas}/{len(interfaces)}",
                    "subtitulo": f"{cobertura:.1f} % relacionado",
                    "color": "cyan"
                }
            ]
        )

        hoja = (
            self.switch_actual.get("hoja_excel")
            if self.switch_actual
            else None
        )
        bloque = (
            self.switch_actual.get("bloque_excel")
            if self.switch_actual
            else None
        )

        if hoja is None or bloque is None:
            visual.warning(
                "Este switch no tiene relación con un bloque del Excel. "
                "La columna Ubicación quedará sin información."
            )
        else:
            visual.info(
                f"Inventario relacionado: {hoja} / bloque {bloque}."
            )

        filas = []

        for interfaz in interfaces:
            nombre = self.valor_visible(interfaz.get("nombre"))
            admin = self.valor_visible(
                interfaz.get("estado_administrativo")
            )
            estado = self.valor_visible(
                interfaz.get("estado_operativo")
            )
            velocidad = self.valor_visible(
                interfaz.get("velocidad")
            )
            velocidad_bps = int(
                interfaz.get("velocidad_bps", 0) or 0
            )
            tipo = self.valor_visible(
                interfaz.get("tipo_inventario"),
                "-"
            )
            ubicacion = self.valor_visible(
                interfaz.get("equipo_inventario"),
                "-"
            )
            errores = self.sumar_errores(interfaz)

            if estado == "UP":
                estado_v = "[bold green]● UP[/bold green]"
            elif estado == "DOWN":
                estado_v = "[bold red]● DOWN[/bold red]"
            else:
                estado_v = f"[yellow]{estado}[/yellow]"

            if admin == "UP":
                admin_v = "[green]UP[/green]"
            elif admin == "DOWN":
                admin_v = "[red]DOWN[/red]"
            else:
                admin_v = admin

            if estado != "UP":
                velocidad_v = "[dim]-[/dim]"
            elif velocidad_bps >= 1_000_000_000:
                velocidad_v = f"[bold green]{velocidad}[/bold green]"
            elif velocidad_bps == 100_000_000:
                velocidad_v = f"[yellow]{velocidad}[/yellow]"
            elif 0 < velocidad_bps <= 10_000_000:
                velocidad_v = f"[bold red]{velocidad}[/bold red]"
            else:
                velocidad_v = velocidad

            errores_v = (
                f"[bold red]{errores}[/bold red]"
                if errores > 0
                else "[green]0[/green]"
            )

            filas.append(
                (
                    nombre,
                    admin_v,
                    estado_v,
                    velocidad_v,
                    tipo,
                    ubicacion,
                    errores_v
                )
            )

        visual.tabla(
            titulo=f"Interfaces físicas de {ip}",
            columnas=[
                {"nombre": "Puerto", "style": "cyan", "no_wrap": True},
                {"nombre": "Admin", "justify": "center", "no_wrap": True},
                {"nombre": "Estado", "justify": "center", "no_wrap": True},
                {"nombre": "Velocidad", "justify": "center", "no_wrap": True},
                {"nombre": "Tipo", "no_wrap": True},
                "Ubicación",
                {"nombre": "Errores", "justify": "right", "no_wrap": True}
            ],
            filas=filas,
            expandir=True
        )

        visual.info(
            "Puerto, estado, velocidad y errores provienen de SNMP; "
            "Tipo y Ubicación provienen del Excel."
        )

        self.ejecutar_selector_detalle_puerto(
            interfaces
        )

    def ejecutar_selector_detalle_puerto(
        self,
        interfaces: list[dict]
    ) -> None:
        """
        Permite abrir la ficha ampliada de un puerto.

        Acepta el número físico final o el nombre completo:
        10, 1/1/10, Gi1/0/10, etc.
        """
        while True:
            seleccion = input(
                "\nPuerto para ver información adicional "
                "[0 para volver]: "
            ).strip()

            if seleccion == "0" or not seleccion:
                return

            interfaz = self.buscar_interfaz_seleccionada(
                interfaces,
                seleccion
            )

            if interfaz is None:
                visual.error(
                    "No se encontró ese puerto en la consulta."
                )
                continue

            self.mostrar_detalle_puerto(
                interfaz
            )

            input(
                "\nPresiona ENTER para volver a la lista "
                "de interfaces..."
            )

            visual.limpiar()
            self.mostrar_estado_interfaces()
            return

    def buscar_interfaz_seleccionada(
        self,
        interfaces: list[dict],
        seleccion: str
    ) -> dict | None:
        """Localiza una interfaz por número o nombre."""
        texto = str(seleccion).strip().lower()

        try:
            numero_buscado = int(texto)
        except ValueError:
            numero_buscado = None

        for interfaz in interfaces:
            nombre = self.valor_visible(
                interfaz.get("nombre"),
                ""
            )

            descripcion = self.valor_visible(
                interfaz.get("descripcion"),
                ""
            )

            numero = self.extraer_numero_puerto(
                nombre or descripcion
            )

            if numero_buscado is not None and numero == numero_buscado:
                return interfaz

            if texto in {
                nombre.lower(),
                descripcion.lower()
            }:
                return interfaz

        return None

    def obtener_interfaz_medida(
        self,
        nombre_puerto: str,
        intervalo: float
    ) -> tuple[ResultadoMonitoreo | None, dict | None]:
        """
        Toma dos muestras y devuelve solamente el puerto
        solicitado dentro del resultado.
        """
        ip = self.obtener_ip_actual()

        visual.info(
            "Tomando dos muestras SNMP para comprobar "
            "tráfico y errores nuevos."
        )

        resultado = self.monitor_snmp.medir_trafico(
            ip=ip,
            intervalo=intervalo,
            solo_fisicas=True
        )

        if not resultado.correcto:
            visual.error(
                "No fue posible completar la medición."
            )
            visual.info(
                f"Detalle: {resultado.error}"
            )
            return None, None

        self.ultima_medicion = resultado

        nombre_normalizado = str(
            nombre_puerto
        ).strip().lower()

        for interfaz in resultado.interfaces:
            nombre = self.valor_visible(
                interfaz.get("nombre"),
                ""
            ).lower()

            descripcion = self.valor_visible(
                interfaz.get("descripcion"),
                ""
            ).lower()

            if nombre_normalizado in {
                nombre,
                descripcion
            }:
                return resultado, interfaz

        numero_buscado = self.extraer_numero_puerto(
            nombre_puerto
        )

        for interfaz in resultado.interfaces:
            numero = self.extraer_numero_puerto(
                interfaz.get("nombre")
                or interfaz.get("descripcion")
            )

            if numero == numero_buscado:
                return resultado, interfaz

        return resultado, None

    def mostrar_detalle_puerto(
        self,
        interfaz: dict
    ) -> None:
        """
        Muestra documentación ampliada, contadores SNMP
        y herramientas de diagnóstico para un puerto.
        """
        while True:
            visual.limpiar()

            nombre = self.valor_visible(
                interfaz.get("nombre"),
                "Puerto sin nombre"
            )

            visual.titulo(
                f"DETALLE DEL PUERTO {nombre}",
                "Información documental y diagnóstico SNMP"
            )

            registro = (
                interfaz.get("registro_inventario")
                or {}
            )

            hoja = self.valor_visible(
                self.switch_actual.get("hoja_excel")
                if self.switch_actual
                else None,
                "-"
            )

            bloque = self.valor_visible(
                self.switch_actual.get("bloque_excel")
                if self.switch_actual
                else None,
                "-"
            )

            documentacion = [
                ("Sector / hoja", hoja),
                ("Bloque", bloque),
                (
                    "Puerto del switch",
                    self.valor_visible(
                        interfaz.get(
                            "numero_puerto_inventario"
                        ),
                        "-"
                    )
                ),
                (
                    "Boca de patch panel",
                    self.valor_visible(
                        interfaz.get("patch_inventario"),
                        "-"
                    )
                ),
                (
                    "Tipo documentado",
                    self.valor_visible(
                        interfaz.get("tipo_inventario"),
                        "-"
                    )
                ),
                (
                    "Equipo / ubicación",
                    self.valor_visible(
                        interfaz.get("equipo_inventario"),
                        "-"
                    )
                ),
                (
                    "VLAN documentada",
                    self.valor_visible(
                        interfaz.get("vlan_inventario"),
                        "-"
                    )
                )
            ]

            campos_extra = [
                ("Fila del Excel", "fila"),
                ("Observaciones", "observaciones"),
                ("Patch", "patch"),
                ("Punto de red", "punto_red"),
                ("Teléfono", "telefono"),
                ("MAC documentada", "mac")
            ]

            claves_incluidas = {
                "hoja",
                "bloque",
                "puerto_switch",
                "tipo",
                "equipo",
                "boca_patch",
                "vlan"
            }

            for etiqueta, clave in campos_extra:
                valor = registro.get(clave)

                if valor not in (None, ""):
                    documentacion.append(
                        (
                            etiqueta,
                            self.valor_visible(valor, "-")
                        )
                    )
                    claves_incluidas.add(clave)

            # Muestra otros campos documentados no vacíos,
            # sin asumir una estructura rígida del Excel.
            for clave, valor in registro.items():
                if (
                    clave in claves_incluidas
                    or clave.startswith("_")
                    or valor in (None, "")
                ):
                    continue

                etiqueta = str(clave).replace(
                    "_",
                    " "
                ).strip().title()

                documentacion.append(
                    (
                        etiqueta,
                        self.valor_visible(valor, "-")
                    )
                )

            visual.tabla(
                "Documentación del puerto",
                [
                    {
                        "nombre": "Campo",
                        "style": "cyan",
                        "no_wrap": True
                    },
                    "Valor"
                ],
                documentacion,
                expandir=True,
                mostrar_lineas=True
            )

            errores_entrada = int(
                interfaz.get(
                    "errores_entrada",
                    0
                )
                or 0
            )

            errores_salida = int(
                interfaz.get(
                    "errores_salida",
                    0
                )
                or 0
            )

            total_errores = (
                errores_entrada
                + errores_salida
            )

            visual.panel_estado(
                "Contadores SNMP acumulados",
                [
                    (
                        "🔵",
                        "Índice SNMP............... "
                        f"{self.valor_visible(interfaz.get('indice'), '-')}"
                    ),
                    (
                        "🔵",
                        "Descripción SNMP.......... "
                        f"{self.valor_visible(interfaz.get('descripcion'), '-')}"
                    ),
                    (
                        "🔴" if errores_entrada else "🟢",
                        "Errores de entrada........ "
                        f"{errores_entrada}"
                    ),
                    (
                        "🔴" if errores_salida else "🟢",
                        "Errores de salida......... "
                        f"{errores_salida}"
                    ),
                    (
                        "🔴" if total_errores else "🟢",
                        "Errores acumulados........ "
                        f"{total_errores}"
                    )
                ],
                "red" if total_errores else "green"
            )

            if total_errores:
                visual.warning(
                    "El total es acumulado y no confirma por sí "
                    "solo una falla activa. La prueba de errores "
                    "nuevos permite comprobar si sigue aumentando."
                )
            else:
                visual.ok(
                    "El puerto no registra errores acumulados."
                )

            visual.menu_paneles(
                "PRUEBAS Y ACCIONES",
                [
                    {
                        "titulo": "DIAGNÓSTICO",
                        "icono": "🧪",
                        "color": "cyan",
                        "opciones": [
                            (
                                "1",
                                "Medir errores y tráfico durante 5 s"
                            ),
                            (
                                "2",
                                "Medir usando otro intervalo"
                            )
                        ]
                    },
                    {
                        "titulo": "AYUDA TÉCNICA",
                        "icono": "🛠",
                        "color": "yellow",
                        "opciones": [
                            (
                                "3",
                                "Interpretar errores acumulados"
                            ),
                            (
                                "4",
                                "Mostrar plan de revisión física"
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
                                "Volver a interfaces"
                            )
                        ]
                    }
                ]
            )

            opcion = input(
                "\nSelecciona una opción: "
            ).strip()

            if opcion == "0":
                return

            if opcion == "1":
                self.diagnosticar_puerto(
                    interfaz,
                    self.INTERVALO_PREDETERMINADO
                )
                input(
                    "\nPresiona ENTER para continuar..."
                )

            elif opcion == "2":
                intervalo = self.solicitar_intervalo()
                self.diagnosticar_puerto(
                    interfaz,
                    intervalo
                )
                input(
                    "\nPresiona ENTER para continuar..."
                )

            elif opcion == "3":
                visual.limpiar()
                self.mostrar_interpretacion_errores(
                    interfaz
                )
                input(
                    "\nPresiona ENTER para continuar..."
                )

            elif opcion == "4":
                visual.limpiar()
                self.mostrar_plan_revision_puerto(
                    interfaz
                )
                input(
                    "\nPresiona ENTER para continuar..."
                )

            else:
                visual.error(
                    "Opción inválida."
                )
                input(
                    "\nPresiona ENTER para continuar..."
                )

    def diagnosticar_puerto(
        self,
        interfaz: dict,
        intervalo: float
    ) -> None:
        """Mide actividad y errores nuevos de un puerto."""
        visual.limpiar()

        nombre = self.valor_visible(
            interfaz.get("nombre"),
            "-"
        )

        visual.titulo(
            f"DIAGNÓSTICO DEL PUERTO {nombre}",
            f"Intervalo de medición: {intervalo:g} segundos"
        )

        errores_iniciales = self.sumar_errores(
            interfaz
        )

        resultado, medida = self.obtener_interfaz_medida(
            nombre,
            intervalo
        )

        if resultado is None or medida is None:
            visual.error(
                "La medición terminó, pero no fue posible "
                "localizar el puerto en la segunda muestra."
            )
            return

        errores_nuevos_entrada = int(
            medida.get(
                "errores_nuevos_entrada",
                0
            )
            or 0
        )

        errores_nuevos_salida = int(
            medida.get(
                "errores_nuevos_salida",
                0
            )
            or 0
        )

        errores_nuevos = (
            errores_nuevos_entrada
            + errores_nuevos_salida
        )

        errores_finales = (
            errores_iniciales
            + errores_nuevos
        )

        entrada = float(
            medida.get(
                "trafico_entrada_mbps",
                0
            )
            or 0
        )

        salida = float(
            medida.get(
                "trafico_salida_mbps",
                0
            )
            or 0
        )

        utilizacion = float(
            medida.get(
                "utilizacion_maxima",
                0
            )
            or 0
        )

        visual.dashboard(
            [
                {
                    "titulo": "📥 Entrada",
                    "contenido": f"{entrada:.3f} Mb/s",
                    "color": "cyan"
                },
                {
                    "titulo": "📤 Salida",
                    "contenido": f"{salida:.3f} Mb/s",
                    "color": "cyan"
                },
                {
                    "titulo": "📊 Uso",
                    "contenido": f"{utilizacion:.2f} %",
                    "color": (
                        "red"
                        if utilizacion >= 80
                        else "yellow"
                        if utilizacion >= 50
                        else "green"
                    )
                },
                {
                    "titulo": "⚠ Errores nuevos",
                    "contenido": str(errores_nuevos),
                    "color": (
                        "red"
                        if errores_nuevos
                        else "green"
                    )
                }
            ]
        )

        visual.panel_estado(
            "Resultado de la medición",
            [
                (
                    "🔵",
                    f"Errores iniciales......... {errores_iniciales}"
                ),
                (
                    "🔵",
                    f"Errores finales........... {errores_finales}"
                ),
                (
                    "🔴" if errores_nuevos else "🟢",
                    f"Errores nuevos............ {errores_nuevos}"
                ),
                (
                    "🔴" if errores_nuevos_entrada else "🟢",
                    "Nuevos de entrada......... "
                    f"{errores_nuevos_entrada}"
                ),
                (
                    "🔴" if errores_nuevos_salida else "🟢",
                    "Nuevos de salida.......... "
                    f"{errores_nuevos_salida}"
                )
            ],
            "red" if errores_nuevos else "green"
        )

        if errores_nuevos:
            visual.error(
                "El contador aumentó durante la medición. "
                "Existe evidencia de un problema activo."
            )
            self.mostrar_plan_revision_puerto(
                interfaz,
                compacto=True
            )
        else:
            visual.ok(
                "Los errores no aumentaron durante la medición. "
                "Los contadores actuales parecen históricos."
            )

    def mostrar_interpretacion_errores(
        self,
        interfaz: dict
    ) -> None:
        """Explica qué significan los contadores disponibles."""
        nombre = self.valor_visible(
            interfaz.get("nombre"),
            "-"
        )

        visual.titulo(
            f"INTERPRETACIÓN DE ERRORES — {nombre}",
            "Qué significan y cómo confirmar una falla"
        )

        visual.panel_estado(
            "Qué muestran estos contadores",
            [
                (
                    "🔵",
                    "Errores de entrada: problemas detectados "
                    "al recibir tramas en el puerto."
                ),
                (
                    "🔵",
                    "Errores de salida: problemas registrados "
                    "al transmitir desde el puerto."
                ),
                (
                    "🟡",
                    "Son contadores acumulados desde el último "
                    "reinicio o reinicio de contadores."
                ),
                (
                    "🟡",
                    "Este contador genérico no identifica por sí "
                    "solo si fueron CRC, descartes, colisiones "
                    "u otra categoría específica."
                )
            ],
            "cyan"
        )

        visual.panel_acciones(
            "Cómo determinar si el problema sigue activo",
            [
                (
                    "1",
                    "Tomar dos muestras separadas por algunos "
                    "segundos."
                ),
                (
                    "2",
                    "Confirmar si el contador aumenta."
                ),
                (
                    "3",
                    "Repetir después de cambiar cable, conector "
                    "o puerto."
                ),
                (
                    "4",
                    "Comparar el resultado antes y después de "
                    "cada acción."
                )
            ],
            "yellow"
        )

    def mostrar_plan_revision_puerto(
        self,
        interfaz: dict,
        compacto: bool = False
    ) -> None:
        """Muestra acciones concretas para revisar el puerto."""
        nombre = self.valor_visible(
            interfaz.get("nombre"),
            "-"
        )

        if not compacto:
            visual.titulo(
                f"PLAN DE REVISIÓN — {nombre}",
                "Acciones seguras de diagnóstico"
            )

        visual.panel_acciones(
            "Acciones recomendadas",
            [
                (
                    "1",
                    "Revisar y volver a conectar el patch cord "
                    "del switch."
                ),
                (
                    "2",
                    "Revisar el patch panel, ponchado y conectores."
                ),
                (
                    "3",
                    "Probar temporalmente otro cable conocido "
                    "como bueno."
                ),
                (
                    "4",
                    "Confirmar velocidad negociada y que no haya "
                    "caídas de enlace."
                ),
                (
                    "5",
                    "Mover temporalmente el equipo a otro puerto, "
                    "documentando el cambio."
                ),
                (
                    "6",
                    "Repetir la medición para comprobar si los "
                    "errores siguen aumentando."
                )
            ],
            "red"
        )

        visual.info(
            "Todas estas acciones son de diagnóstico. No se "
            "realiza ningún cambio automático en el switch."
        )

    def solicitar_intervalo(
        self
    ) -> float:
        """
        Solicita el intervalo entre las dos muestras SNMP.
        """
        texto = input(
            "\nIntervalo en segundos "
            f"[{self.INTERVALO_PREDETERMINADO:g}]: "
        ).strip()

        if not texto:
            return self.INTERVALO_PREDETERMINADO

        try:
            intervalo = float(
                texto.replace(
                    ",",
                    "."
                )
            )

        except ValueError:
            self.ui.mostrar_aviso(
                "Intervalo inválido. Se utilizarán "
                f"{self.INTERVALO_PREDETERMINADO:g} "
                "segundos."
            )

            return self.INTERVALO_PREDETERMINADO

        if intervalo < 1:
            self.ui.mostrar_aviso(
                "El intervalo mínimo es 1 segundo. "
                "Se utilizará el valor predeterminado."
            )

            return self.INTERVALO_PREDETERMINADO

        return intervalo

    def ejecutar_medicion(
        self,
        intervalo: float | None = None
    ) -> ResultadoMonitoreo | None:
        """
        Toma dos muestras de interfaces y conserva
        el resultado en memoria.
        """
        if intervalo is None:
            intervalo = self.solicitar_intervalo()

        ip = self.obtener_ip_actual()

        self.ui.mostrar_info(
            "Tomando la primera muestra."
        )

        print(
            f"\nSwitch: {ip}"
        )

        print(
            "Se esperarán aproximadamente "
            f"{intervalo:g} segundos."
        )

        resultado = (
            self.monitor_snmp
            .medir_trafico(
                ip=ip,
                intervalo=intervalo,
                solo_fisicas=True
            )
        )

        if not resultado.correcto:
            self.ui.mostrar_error(
                "No fue posible completar la medición."
            )

            print(
                f"\nDetalle: {resultado.error}"
            )
            return None

        self.ultima_medicion = resultado

        return resultado

    def medir_trafico_actual(self):
        """Muestra tráfico, utilización y errores entre dos muestras."""
        visual.limpiar()
        visual.titulo(
            "TRÁFICO ACTUAL",
            "Medición de utilización mediante dos muestras SNMP"
        )

        resultado = self.ejecutar_medicion()

        if resultado is None:
            return

        interfaces = resultado.interfaces
        activas = [
            interfaz
            for interfaz in interfaces
            if interfaz.get("estado_operativo") == "UP"
        ]
        con_trafico = [
            interfaz
            for interfaz in activas
            if (
                float(interfaz.get("trafico_entrada_mbps", 0) or 0) > 0
                or float(interfaz.get("trafico_salida_mbps", 0) or 0) > 0
            )
        ]
        utilizacion_alta = [
            interfaz
            for interfaz in activas
            if float(interfaz.get("utilizacion_maxima", 0) or 0) >= 80
        ]
        errores_nuevos = [
            interfaz
            for interfaz in interfaces
            if self.sumar_errores_nuevos(interfaz) > 0
        ]

        visual.dashboard(
            [
                {"titulo": "⏱ Intervalo", "contenido": f"{resultado.intervalo_real:.2f} s", "color": "cyan"},
                {"titulo": "🖧 Interfaces", "contenido": str(len(interfaces)), "color": "bright_blue"},
                {"titulo": "✅ Activas", "contenido": str(len(activas)), "color": "green"},
                {"titulo": "📈 Con tráfico", "contenido": str(len(con_trafico)), "color": "magenta"},
                {"titulo": "🔥 Uso alto", "contenido": str(len(utilizacion_alta)), "color": "red" if utilizacion_alta else "green"},
                {"titulo": "⚠ Errores nuevos", "contenido": str(len(errores_nuevos)), "color": "red" if errores_nuevos else "green"}
            ]
        )

        filas = []

        for interfaz in interfaces:
            nombre = self.valor_visible(interfaz.get("nombre"))
            estado = self.valor_visible(interfaz.get("estado_operativo"))
            velocidad = self.valor_visible(interfaz.get("velocidad"))
            entrada = float(interfaz.get("trafico_entrada_mbps", 0) or 0)
            salida = float(interfaz.get("trafico_salida_mbps", 0) or 0)
            uso = float(interfaz.get("utilizacion_maxima", 0) or 0)
            errores = self.sumar_errores_nuevos(interfaz)

            estado_v = (
                "[green]UP[/green]"
                if estado == "UP"
                else "[red]DOWN[/red]"
            )

            if uso >= 80:
                uso_v = f"[bold red]{uso:.2f} %[/bold red]"
            elif uso >= 50:
                uso_v = f"[yellow]{uso:.2f} %[/yellow]"
            else:
                uso_v = f"[green]{uso:.2f} %[/green]"

            errores_v = (
                f"[bold red]{errores}[/bold red]"
                if errores
                else "[green]0[/green]"
            )

            filas.append(
                (
                    nombre,
                    estado_v,
                    velocidad,
                    f"{entrada:.3f} Mb",
                    f"{salida:.3f} Mb",
                    uso_v,
                    errores_v
                )
            )

        visual.tabla(
            titulo="Utilización de interfaces",
            columnas=[
                {"nombre": "Puerto", "style": "cyan", "no_wrap": True},
                {"nombre": "Estado", "justify": "center", "no_wrap": True},
                {"nombre": "Velocidad", "justify": "center", "no_wrap": True},
                {"nombre": "Entrada", "justify": "right", "no_wrap": True},
                {"nombre": "Salida", "justify": "right", "no_wrap": True},
                {"nombre": "Uso", "justify": "right", "no_wrap": True},
                {"nombre": "Errores", "justify": "right", "no_wrap": True}
            ],
            filas=filas,
            expandir=True
        )

        visual.ok("Medición finalizada.")

    def obtener_medicion_disponible(
        self
    ) -> ResultadoMonitoreo | None:
        """
        Reutiliza la última medición o crea una nueva.
        """
        if self.ultima_medicion is not None:
            return self.ultima_medicion

        self.ui.mostrar_info(
            "Todavía no existe una medición reciente."
        )

        print(
            "\nSe realizará una medición antes "
            "de analizar los errores."
        )

        return self.ejecutar_medicion(
            intervalo=self.INTERVALO_PREDETERMINADO
        )

    def mostrar_errores_nuevos(self):
        """Muestra errores que aumentaron durante la última medición."""
        visual.limpiar()
        visual.titulo(
            "ERRORES NUEVOS",
            "Cambios detectados entre las dos últimas muestras"
        )

        resultado = self.obtener_medicion_disponible()

        if resultado is None:
            return

        interfaces = [
            interfaz
            for interfaz in resultado.interfaces
            if self.sumar_errores_nuevos(interfaz) > 0
        ]

        if not interfaces:
            visual.ok(
                "No se detectaron errores nuevos durante la última medición."
            )
            return

        visual.warning(
            f"Se detectaron errores nuevos en {len(interfaces)} interfaces."
        )

        filas = []
        for interfaz in interfaces:
            entrada = int(interfaz.get("errores_nuevos_entrada", 0) or 0)
            salida = int(interfaz.get("errores_nuevos_salida", 0) or 0)
            nombre = self.valor_visible(interfaz.get("nombre"))
            filas.append(
                (
                    nombre,
                    f"[red]{entrada}[/red]",
                    f"[red]{salida}[/red]",
                    f"[bold red]{entrada + salida}[/bold red]"
                )
            )

        visual.tabla(
            titulo="Interfaces con incremento de errores",
            columnas=[
                {"nombre": "Puerto", "style": "cyan", "no_wrap": True},
                {"nombre": "Entrada", "justify": "right"},
                {"nombre": "Salida", "justify": "right"},
                {"nombre": "Total", "justify": "right"}
            ],
            filas=filas,
            expandir=True
        )

    def mostrar_enlaces_reducidos(self):
        """
        Muestra enlaces activos negociados a 10 Mbps.

        Los enlaces a 100 Mbps se presentan solamente como
        información, porque pueden corresponder a cámaras,
        teléfonos IP, impresoras u otros equipos Fast
        Ethernet.
        """
        self.ui.mostrar_titulo(
            "Enlaces a velocidad reducida",
            limpiar=True
        )

        ip = self.obtener_ip_actual()

        resultado = (
            self.cliente_snmp
            .obtener_interfaces(
                ip
            )
        )

        if not resultado.correcto:
            self.ui.mostrar_error(
                "No fue posible consultar las interfaces."
            )

            print(
                f"\nDetalle: {resultado.error}"
            )
            return

        interfaces = self.obtener_interfaces_fisicas(
            resultado.datos
        )

        enlaces_10_mbps = [
            interfaz
            for interfaz in interfaces
            if (
                interfaz.get(
                    "estado_operativo"
                ) == "UP"
                and int(
                    interfaz.get(
                        "velocidad_bps",
                        0
                    )
                    or 0
                ) == 10_000_000
            )
        ]

        enlaces_100_mbps = [
            interfaz
            for interfaz in interfaces
            if (
                interfaz.get(
                    "estado_operativo"
                ) == "UP"
                and int(
                    interfaz.get(
                        "velocidad_bps",
                        0
                    )
                    or 0
                ) == 100_000_000
            )
        ]

        if enlaces_10_mbps:
            self.ui.mostrar_aviso(
                "Se detectaron enlaces activos a 10 Mbps."
            )

            for interfaz in enlaces_10_mbps:
                print(
                    f"- {interfaz.get('nombre')}: "
                    f"{interfaz.get('velocidad')}"
                )

            print(
                "\nEstos enlaces deberían revisarse por "
                "posibles problemas de cableado, conectores, "
                "patch panel o negociación."
            )

        else:
            self.ui.mostrar_exito(
                "No se detectaron enlaces activos "
                "negociados a 10 Mbps."
            )

        if enlaces_100_mbps:
            print(
                "\n----------------------------------------------"
            )
            print(
                "ENLACES ACTIVOS A 100 MBPS"
            )
            print(
                "----------------------------------------------"
            )

            for interfaz in enlaces_100_mbps:
                print(
                    f"- {interfaz.get('nombre')}: "
                    f"{interfaz.get('velocidad')}"
                )

            print(
                "\nLos enlaces a 100 Mbps son informativos. "
                "No se consideran automáticamente una falla."
            )

    # ======================================================
    # ANÁLISIS DE SALUD
    # ======================================================

    def mostrar_resumen_analisis(
        self,
        resultado
    ):
        """
        Muestra el resumen y las incidencias generadas
        por el motor de reglas SNMP.
        """
        resumen = resultado.contar_por_nivel()

        print(
            "\n=============================================="
        )

        print(
            "          ANÁLISIS DE SALUD SNMP"
        )

        print(
            "=============================================="
        )

        print(
            f"\nIP del switch: "
            f"{resultado.ip_switch}"
        )

        print(
            "Interfaces analizadas: "
            f"{resultado.interfaces_analizadas}"
        )

        print(
            "Estado general: "
            f"{resultado.obtener_estado_general()}"
        )

        print(
            "\nResumen de incidencias:"
        )

        print(
            f"- Críticas: "
            f"{resumen['criticas']}"
        )

        print(
            f"- Advertencias: "
            f"{resumen['advertencias']}"
        )

        print(
            f"- Informativas: "
            f"{resumen['informativas']}"
        )

        print(
            f"- Total: "
            f"{resumen['total']}"
        )

        if not resultado.incidencias:
            self.ui.mostrar_exito(
                "No se detectaron incidencias con "
                "las reglas actuales."
            )
            return

        print(
            "\n=============================================="
        )

        print(
            "          INCIDENCIAS DETECTADAS"
        )

        print(
            "=============================================="
        )

        for numero, incidencia in enumerate(
            resultado.incidencias,
            start=1
        ):
            print(
                "\n----------------------------------------------"
            )

            print(
                f"{numero}. [{incidencia.nivel}] "
                f"{incidencia.titulo}"
            )

            if incidencia.puerto:
                print(
                    f"Puerto: {incidencia.puerto}"
                )

            print(
                f"Categoría: "
                f"{incidencia.categoria}"
            )

            print(
                f"Detalle: "
                f"{incidencia.detalle}"
            )

            print(
                f"Recomendación: "
                f"{incidencia.recomendacion}"
            )

    def analizar_salud_switch(self):
        """
        Consulta información general, toma dos muestras
        de interfaces y ejecuta el analizador SNMP.

        No utiliza el Excel ni genera advertencias basadas
        en documentación incompleta.
        """
        self.ui.mostrar_titulo(
            "Análisis de salud del switch",
            limpiar=True
        )

        ip = self.obtener_ip_actual()

        ubicacion = self.valor_visible(
            self.switch_actual.get(
                "ubicacion"
            )
        )

        print(
            f"Switch: {ip}"
        )

        print(
            f"Ubicación: {ubicacion}"
        )

        self.ui.mostrar_info(
            "Consultando información general."
        )

        informacion = (
            self.cliente_snmp
            .obtener_informacion_sistema(
                ip
            )
        )

        if not informacion.correcto:
            self.ui.mostrar_error(
                "No fue posible obtener la información "
                "general del switch."
            )

            print(
                f"\nDetalle: {informacion.error}"
            )
            return

        print(
            "\nSe tomarán dos muestras SNMP para analizar "
            "tráfico, utilización y errores nuevos."
        )

        intervalo = self.solicitar_intervalo()

        medicion = (
            self.monitor_snmp
            .medir_trafico(
                ip=ip,
                intervalo=intervalo,
                solo_fisicas=True
            )
        )

        if not medicion.correcto:
            self.ui.mostrar_error(
                "No fue posible medir las interfaces."
            )

            print(
                f"\nDetalle: {medicion.error}"
            )
            return

        self.ultima_medicion = medicion

        resultado = (
            self.analizador_snmp
            .analizar(
                interfaces=medicion.interfaces,
                informacion_sistema=(
                    informacion.datos
                ),
                ip_switch=ip
            )
        )

        self.mostrar_resumen_analisis(
            resultado
        )