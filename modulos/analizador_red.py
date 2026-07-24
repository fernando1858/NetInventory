from collections import Counter
from typing import Any

from modulos.visual import visual


class AnalizadorRed:
    """Analiza impacto, cobertura y rutas de la red (solo lectura)."""

    TIPOS_CONTABILIZADOS = {
        "Antena", "Cámara", "Teléfono IP", "Troncal", "Equipo", "Sin tipo"
    }

    def __init__(self, inventario, gestor_topologia):
        self.inventario = inventario
        self.gestor_topologia = gestor_topologia

    @staticmethod
    def limpiar_texto(valor: Any) -> str | None:
        if valor is None:
            return None
        texto = str(valor).strip()
        return texto or None

    @staticmethod
    def valor_visible(valor, predeterminado="Sin definir"):
        if valor is None:
            return predeterminado
        texto = str(valor).strip()
        return texto or predeterminado

    @staticmethod
    def color_prioridad(prioridad: str) -> str:
        return {
            "CRÍTICA": "red",
            "ALTA": "bright_red",
            "MEDIA": "yellow",
            "BAJA": "cyan",
        }.get(str(prioridad).upper(), "bright_blue")

    def nombre_visible(self, switch: dict) -> str:
        return str(
            switch.get("nombre_logico")
            or switch.get("nombre")
            or switch.get("ubicacion")
            or switch.get("ip")
            or "Switch sin nombre"
        )

    def obtener_switch(self, identificador) -> dict | None:
        return self.gestor_topologia.obtener_switch(identificador)

    def registros_de_switch(self, switch: dict) -> list[dict]:
        return self.evaluar_cobertura_switch(switch)["registros"]

    def evaluar_cobertura_switch(self, switch: dict) -> dict:
        hoja = self.limpiar_texto(switch.get("hoja_excel"))
        bloque = switch.get("bloque_excel")

        if hoja is None or bloque is None:
            return {
                "estado": "SIN RELACIÓN",
                "motivo": "No tiene hoja o bloque Excel relacionado.",
                "registros": [],
            }

        try:
            bloque = int(bloque)
        except (TypeError, ValueError):
            return {
                "estado": "RELACIÓN INVÁLIDA",
                "motivo": "El bloque Excel relacionado no es válido.",
                "registros": [],
            }

        hoja_normalizada = self.inventario.normalizar_texto(hoja)
        registros = [
            r for r in self.inventario.registros
            if self.inventario.normalizar_texto(r.get("hoja")) == hoja_normalizada
            and r.get("bloque") == bloque
        ]

        if not registros:
            return {
                "estado": "BLOQUE SIN REGISTROS",
                "motivo": (
                    f"La relación apunta a {hoja} / bloque {bloque}, "
                    "pero no se cargaron registros."
                ),
                "registros": [],
            }

        return {
            "estado": "CUBIERTO",
            "motivo": f"{len(registros)} registros encontrados.",
            "registros": registros,
        }

    def obtener_nodos_afectados(self, switch: dict) -> list[dict]:
        switch_id = switch.get("id")
        if switch_id is None:
            return [switch]
        return [switch, *self.gestor_topologia.obtener_descendientes(switch_id)]

    def resumir_registros(self, registros: list[dict]) -> dict:
        tipos = Counter()
        con_equipo = 0
        disponibles = 0

        for registro in registros:
            tipo = self.limpiar_texto(registro.get("tipo")) or "Sin tipo"
            tipos[tipo] += 1
            equipo = self.limpiar_texto(registro.get("equipo"))
            if equipo:
                if self.inventario.equipo_esta_disponible(equipo):
                    disponibles += 1
                else:
                    con_equipo += 1

        return {
            "puertos_documentados": len(registros),
            "equipos_conectados": con_equipo,
            "disponibles": disponibles,
            "antenas": tipos.get("Antena", 0),
            "camaras": tipos.get("Cámara", 0),
            "telefonos_ip": tipos.get("Teléfono IP", 0),
            "troncales": tipos.get("Troncal", 0),
            "equipos": tipos.get("Equipo", 0),
            "sin_tipo": tipos.get("Sin tipo", 0),
            "tipos": dict(tipos),
        }

    def calcular_prioridad(self, switch: dict, descendientes: int, equipos_conectados: int) -> str:
        criticidad = str(switch.get("criticidad") or "NO DEFINIDA").upper()
        rol = str(switch.get("rol") or "NO DEFINIDO").upper()

        if criticidad == "CRITICA" or rol == "CORE":
            return "CRÍTICA"
        if criticidad == "ALTA" or descendientes >= 3 or equipos_conectados >= 60:
            return "ALTA"
        if criticidad == "MEDIA" or descendientes >= 1 or equipos_conectados >= 20:
            return "MEDIA"
        return "BAJA"

    def analizar_switch(self, identificador) -> dict:
        switch = self.obtener_switch(identificador)
        if switch is None:
            raise ValueError("No se encontró el switch indicado.")

        nodos = self.obtener_nodos_afectados(switch)
        hijos_directos = self.gestor_topologia.obtener_hijos(switch.get("id"))
        registros = []
        sectores = []
        cobertura_switches = []

        for nodo in nodos:
            nombre = self.nombre_visible(nodo)
            sectores.append({
                "nombre": nombre,
                "ip": nodo.get("ip"),
                "hoja": nodo.get("hoja_excel"),
                "bloque": nodo.get("bloque_excel"),
            })
            cobertura = self.evaluar_cobertura_switch(nodo)
            cobertura_switches.append({
                "nombre": nombre,
                "ip": nodo.get("ip"),
                "estado": cobertura["estado"],
                "motivo": cobertura["motivo"],
                "hoja": nodo.get("hoja_excel"),
                "bloque": nodo.get("bloque_excel"),
                "cantidad_registros": len(cobertura["registros"]),
            })
            registros.extend(cobertura["registros"])

        resumen = self.resumir_registros(registros)
        cubiertos = [x for x in cobertura_switches if x["estado"] == "CUBIERTO"]
        sin_relacion = [x for x in cobertura_switches if x["estado"] == "SIN RELACIÓN"]
        invalidas = [x for x in cobertura_switches if x["estado"] == "RELACIÓN INVÁLIDA"]
        sin_registros = [x for x in cobertura_switches if x["estado"] == "BLOQUE SIN REGISTROS"]
        total = len(cobertura_switches)
        porcentaje = round(len(cubiertos) / total * 100, 1) if total else 0.0
        descendientes = max(len(nodos) - 1, 0)
        prioridad = self.calcular_prioridad(
            switch, descendientes, resumen["equipos_conectados"]
        )

        return {
            "switch": switch,
            "nombre": self.nombre_visible(switch),
            "hijos_directos": len(hijos_directos),
            "descendientes": descendientes,
            "switches_afectados": len(nodos),
            "sectores": sectores,
            "cobertura_switches": cobertura_switches,
            "switches_cubiertos": len(cubiertos),
            "switches_sin_relacion": sin_relacion,
            "relaciones_invalidas": invalidas,
            "bloques_sin_registros": sin_registros,
            "cobertura_porcentaje": porcentaje,
            "prioridad": prioridad,
            **resumen,
        }

    def mostrar_analisis(self, analisis: dict):
        switch = analisis["switch"]
        prioridad = analisis["prioridad"]
        color = self.color_prioridad(prioridad)

        visual.limpiar()
        visual.titulo(
            "CENTRO DE IMPACTO DE RED",
            f"Análisis de {analisis['nombre']}",
            color,
        )

        visual.dashboard([
            {"titulo": "⚠ Prioridad", "contenido": prioridad, "color": color},
            {"titulo": "🌳 Hijos", "contenido": str(analisis["hijos_directos"]), "color": "cyan"},
            {"titulo": "🖧 Descendientes", "contenido": str(analisis["descendientes"]), "color": "yellow"},
            {"titulo": "📍 Afectados", "contenido": str(analisis["switches_afectados"]), "color": "red" if analisis["switches_afectados"] >= 10 else "yellow"},
            {
                "titulo": "📊 Cobertura",
                "contenido": f"{analisis['cobertura_porcentaje']:.1f} %",
                "color": visual.color_porcentaje(analisis["cobertura_porcentaje"]),
                "subtitulo": visual.barra(analisis["cobertura_porcentaje"], largo=10),
            },
        ])

        visual.tabla(
            "Switch analizado",
            [{"nombre": "Campo", "style": "cyan", "no_wrap": True}, "Valor"],
            [
                ("Nombre", analisis["nombre"]),
                ("IP", self.valor_visible(switch.get("ip"))),
                ("Rol", self.valor_visible(switch.get("rol"))),
                ("Criticidad documentada", self.valor_visible(switch.get("criticidad"))),
                ("Prioridad calculada", prioridad),
            ],
            expandir=True,
            mostrar_lineas=True,
        )

        visual.dashboard([
            {"titulo": "🔌 Puertos", "contenido": str(analisis["puertos_documentados"]), "color": "bright_blue"},
            {"titulo": "💻 Equipos", "contenido": str(analisis["equipos_conectados"]), "color": "green"},
            {"titulo": "📡 AP", "contenido": str(analisis["antenas"]), "color": "magenta"},
            {"titulo": "📷 Cámaras", "contenido": str(analisis["camaras"]), "color": "yellow"},
            {"titulo": "☎ Teléfonos", "contenido": str(analisis["telefonos_ip"]), "color": "cyan"},
            {"titulo": "🌐 Troncales", "contenido": str(analisis["troncales"]), "color": "bright_blue"},
        ])

        filas = [
            (
                str(i),
                sector["nombre"],
                self.valor_visible(sector.get("ip"), "-"),
                self.valor_visible(sector.get("hoja"), "-"),
                self.valor_visible(sector.get("bloque"), "-"),
            )
            for i, sector in enumerate(analisis["sectores"], start=1)
        ]
        visual.tabla(
            "Sectores potencialmente afectados",
            [
                {"nombre": "N.º", "justify": "right", "no_wrap": True},
                "Sector / Switch",
                {"nombre": "IP", "no_wrap": True},
                "Hoja",
                {"nombre": "Bloque", "justify": "right", "no_wrap": True},
            ],
            filas,
            expandir=True,
        )

        total_fuera = (
            len(analisis["switches_sin_relacion"])
            + len(analisis["relaciones_invalidas"])
            + len(analisis["bloques_sin_registros"])
        )
        visual.panel_estado(
            "Cobertura del análisis",
            [
                ("🟢", f"Con inventario asociado..... {analisis['switches_cubiertos']} de {analisis['switches_afectados']}"),
                ("🟢" if analisis["cobertura_porcentaje"] == 100 else "🟡", f"Cobertura................... {analisis['cobertura_porcentaje']:.1f} %"),
                ("🔴" if total_fuera else "🟢", f"Fuera del conteo............ {total_fuera}"),
                ("🔵", f"Puertos disponibles......... {analisis['disponibles']}"),
                ("🟡" if analisis["sin_tipo"] else "🟢", f"Registros sin tipo.......... {analisis['sin_tipo']}"),
            ],
            "yellow" if total_fuera else "green",
        )

        problemas = (
            analisis["switches_sin_relacion"]
            + analisis["relaciones_invalidas"]
            + analisis["bloques_sin_registros"]
        )
        if problemas:
            visual.tabla(
                "Observaciones de cobertura",
                ["Switch", {"nombre": "IP", "no_wrap": True}, "Estado", "Hoja", "Bloque", "Motivo"],
                [
                    (
                        x["nombre"],
                        self.valor_visible(x.get("ip"), "-"),
                        x["estado"],
                        self.valor_visible(x.get("hoja"), "-"),
                        self.valor_visible(x.get("bloque"), "-"),
                        x["motivo"],
                    )
                    for x in problemas
                ],
                expandir=True,
                mostrar_lineas=True,
            )
            visual.warning(
                "Las cifras de infraestructura representan un mínimo documentado."
            )
        else:
            visual.ok("Todos los switches afectados tienen inventario asociado.")

    def obtener_ruta_hacia_core(self, identificador) -> dict:
        switch = self.obtener_switch(identificador)
        if switch is None:
            raise ValueError("No se encontró el switch indicado.")

        ruta = [switch]
        visitados = set()
        switch_id = switch.get("id")
        if switch_id is not None:
            visitados.add(switch_id)

        actual = switch
        while actual.get("switch_padre_id") is not None:
            padre_id = actual.get("switch_padre_id")
            if padre_id in visitados:
                raise ValueError("Se detectó un ciclo en la topología.")
            padre = self.gestor_topologia.obtener_por_id(padre_id)
            if padre is None:
                raise ValueError(
                    "La ruta está incompleta porque uno de los padres documentados no existe."
                )
            ruta.append(padre)
            visitados.add(padre_id)
            actual = padre

        ultimo = ruta[-1]
        es_core = str(ultimo.get("rol") or "").upper() == "CORE"
        enlaces = []
        for posicion in range(len(ruta) - 1):
            hijo = ruta[posicion]
            padre = ruta[posicion + 1]
            enlace = self.gestor_topologia.obtener_enlace_por_hijo(hijo.get("id"))
            enlaces.append({"hijo": hijo, "padre": padre, "enlace": enlace})

        return {
            "switch": switch,
            "ruta": ruta,
            "enlaces": enlaces,
            "saltos": max(len(ruta) - 1, 0),
            "termina_en_core": es_core,
            "core": ultimo if es_core else None,
        }

    def mostrar_ruta_hacia_core(self, resultado: dict):
        switch = resultado["switch"]
        visual.limpiar()
        visual.titulo("RUTA HACIA EL CORE", self.nombre_visible(switch))
        visual.dashboard([
            {"titulo": "🌐 IP", "contenido": self.valor_visible(switch.get("ip")), "color": "cyan"},
            {"titulo": "🪜 Saltos", "contenido": str(resultado["saltos"]), "color": "bright_blue"},
            {"titulo": "🧭 Estado", "contenido": "COMPLETA" if resultado["termina_en_core"] else "INCOMPLETA", "color": "green" if resultado["termina_en_core"] else "red"},
        ])

        filas = []
        for indice, nodo in enumerate(resultado["ruta"]):
            if indice == 0:
                etapa = "INICIO"
            elif indice == len(resultado["ruta"]) - 1 and resultado["termina_en_core"]:
                etapa = "CORE"
            else:
                etapa = f"SALTO {indice}"

            puerto_hijo = puerto_padre = tecnologia = "-"
            if indice < len(resultado["enlaces"]):
                enlace = resultado["enlaces"][indice].get("enlace")
                if enlace:
                    puerto_hijo = self.valor_visible(enlace.get("puerto_hijo"), "-")
                    puerto_padre = self.valor_visible(enlace.get("puerto_padre"), "-")
                    tecnologia = self.valor_visible(enlace.get("tecnologia"), "-")

            filas.append((
                etapa,
                self.nombre_visible(nodo),
                self.valor_visible(nodo.get("ip"), "-"),
                puerto_hijo,
                tecnologia,
                puerto_padre,
            ))

        visual.tabla(
            "Recorrido documentado",
            [
                {"nombre": "Etapa", "no_wrap": True},
                "Switch",
                {"nombre": "IP", "no_wrap": True},
                "Puerto hijo",
                "Tecnología",
                "Puerto padre",
            ],
            filas,
            expandir=True,
            mostrar_lineas=True,
        )

        acciones = []
        for detalle in resultado["enlaces"]:
            hijo, padre, enlace = detalle["hijo"], detalle["padre"], detalle.get("enlace")
            texto = f"Revisar {self.nombre_visible(hijo)} → {self.nombre_visible(padre)}"
            if enlace:
                texto += (
                    f" | {self.valor_visible(enlace.get('puerto_hijo'), '-')}"
                    f" → {self.valor_visible(enlace.get('puerto_padre'), '-')}"
                )
            acciones.append(("🛠", texto))

        if acciones:
            visual.panel_acciones("Orden recomendado de revisión", acciones, "yellow")
        else:
            visual.ok("El switch seleccionado ya es la raíz de la topología.")

    def auditar_cobertura_global(self):
        resultados = []
        for switch in self.gestor_topologia.listar_switches():
            cobertura = self.evaluar_cobertura_switch(switch)
            resultados.append({
                "nombre": self.nombre_visible(switch),
                "ip": switch.get("ip"),
                "hoja": switch.get("hoja_excel"),
                "bloque": switch.get("bloque_excel"),
                "estado": cobertura["estado"],
                "motivo": cobertura["motivo"],
                "cantidad_registros": len(cobertura["registros"]),
            })

        cubiertos = [x for x in resultados if x["estado"] == "CUBIERTO"]
        sin_relacion = [x for x in resultados if x["estado"] == "SIN RELACIÓN"]
        invalidas = [x for x in resultados if x["estado"] == "RELACIÓN INVÁLIDA"]
        sin_registros = [x for x in resultados if x["estado"] == "BLOQUE SIN REGISTROS"]
        total = len(resultados)
        porcentaje = round(len(cubiertos) / total * 100, 1) if total else 0.0

        return {
            "total": total,
            "cubiertos": cubiertos,
            "sin_relacion": sin_relacion,
            "relaciones_invalidas": invalidas,
            "bloques_sin_registros": sin_registros,
            "porcentaje": porcentaje,
        }

    def mostrar_auditoria_cobertura(self):
        auditoria = self.auditar_cobertura_global()
        visual.limpiar()
        visual.titulo(
            "AUDITORÍA DE COBERTURA DEL INVENTARIO",
            "Relaciones entre switches y bloques del Excel",
        )

        visual.dashboard([
            {"titulo": "🖧 Registrados", "contenido": str(auditoria["total"]), "color": "bright_blue"},
            {"titulo": "🟢 Cubiertos", "contenido": str(len(auditoria["cubiertos"])), "color": "green"},
            {"titulo": "🟡 Sin relación", "contenido": str(len(auditoria["sin_relacion"])), "color": "yellow" if auditoria["sin_relacion"] else "green"},
            {"titulo": "🔴 Inválidas", "contenido": str(len(auditoria["relaciones_invalidas"])), "color": "red" if auditoria["relaciones_invalidas"] else "green"},
            {"titulo": "⚪ Sin registros", "contenido": str(len(auditoria["bloques_sin_registros"])), "color": "grey50" if auditoria["bloques_sin_registros"] else "green"},
            {"titulo": "📊 Cobertura", "contenido": f"{auditoria['porcentaje']:.1f} %", "color": visual.color_porcentaje(auditoria["porcentaje"]), "subtitulo": visual.barra(auditoria["porcentaje"], largo=10)},
        ])

        pendientes = (
            auditoria["sin_relacion"]
            + auditoria["relaciones_invalidas"]
            + auditoria["bloques_sin_registros"]
        )
        if pendientes:
            visual.tabla(
                f"Pendientes de cobertura ({len(pendientes)})",
                ["Switch", {"nombre": "IP", "no_wrap": True}, "Estado", "Hoja", "Bloque", "Motivo"],
                [
                    (
                        x["nombre"],
                        self.valor_visible(x.get("ip"), "-"),
                        x["estado"],
                        self.valor_visible(x.get("hoja"), "-"),
                        self.valor_visible(x.get("bloque"), "-"),
                        x["motivo"],
                    )
                    for x in pendientes
                ],
                expandir=True,
                mostrar_lineas=True,
            )
        else:
            visual.ok("Todos los switches tienen cobertura de inventario.")

    def mostrar_menu(self):
        visual.limpiar()
        visual.titulo(
            "CENTRO DE IMPACTO DE RED",
            "Topología, dependencias e inventario",
        )
        visual.panel_estado(
            "Funciones disponibles",
            [
                ("🔍", "Analizar el impacto potencial de un switch."),
                ("📊", "Auditar la cobertura global del inventario."),
                ("🌳", "Mostrar la ruta documentada hacia el Core."),
            ],
            "cyan",
        )
        visual.menu_paneles(
            "MENÚ PRINCIPAL",
            [
                {"titulo": "IMPACTO", "icono": "⚠", "color": "red", "opciones": [("1", "Analizar impacto de un switch")]},
                {"titulo": "INVENTARIO", "icono": "📊", "color": "cyan", "opciones": [("2", "Auditar cobertura del inventario")]},
                {"titulo": "TOPOLOGÍA", "icono": "🌳", "color": "green", "opciones": [("3", "Mostrar ruta hacia el Core"), ("0", "Volver")]},
            ],
        )

    def ejecutar(self):
        while True:
            self.mostrar_menu()
            opcion = input("\nSelecciona una opción: ").strip()

            if opcion in {"0", "1", "2", "3"}:
                visual.limpiar()

            if opcion == "1":
                identificador = input("\nSwitch a analizar (octeto, ID o IP): ").strip()
                if not identificador:
                    visual.error("Debes indicar un switch.")
                    input("\nPresiona ENTER para continuar...")
                    continue
                try:
                    analisis = self.analizar_switch(identificador)
                except ValueError as error:
                    visual.error(str(error))
                    input("\nPresiona ENTER para continuar...")
                    continue
                self.mostrar_analisis(analisis)
                input("\nPresiona ENTER para continuar...")

            elif opcion == "2":
                self.mostrar_auditoria_cobertura()
                input("\nPresiona ENTER para continuar...")

            elif opcion == "3":
                identificador = input("\nSwitch a analizar (octeto, ID o IP): ").strip()
                if not identificador:
                    visual.error("Debes indicar un switch.")
                    input("\nPresiona ENTER para continuar...")
                    continue
                try:
                    ruta = self.obtener_ruta_hacia_core(identificador)
                except ValueError as error:
                    visual.error(str(error))
                    input("\nPresiona ENTER para continuar...")
                    continue
                self.mostrar_ruta_hacia_core(ruta)
                input("\nPresiona ENTER para continuar...")

            elif opcion == "0":
                break

            else:
                visual.error("Opción inválida.")
                input("\nPresiona ENTER para continuar...")