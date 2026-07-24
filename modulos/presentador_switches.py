from __future__ import annotations

from modulos.visual import visual


class PresentadorSwitches:
    """Presentación visual de switches registrados."""

    def __init__(self, gestor_accesos):
        self.gestor_accesos = gestor_accesos

    @staticmethod
    def valor_visible(valor, predeterminado="-"):
        if valor is None:
            return predeterminado
        texto = str(valor).strip()
        return texto or predeterminado

    @staticmethod
    def color_criticidad(valor):
        return {
            "CRITICA": "red",
            "CRÍTICA": "red",
            "ALTA": "bright_red",
            "MEDIA": "yellow",
            "BAJA": "cyan",
        }.get(str(valor or "").upper(), "grey50")

    @staticmethod
    def color_rol(valor):
        return {
            "CORE": "red",
            "DISTRIBUCION": "magenta",
            "DISTRIBUCIÓN": "magenta",
            "ACCESO": "cyan",
        }.get(str(valor or "").upper(), "grey50")

    @staticmethod
    def texto_booleano(valor):
        if valor in {1, True, "1", "SI", "Sí", "si", "sí"}:
            return "Sí"
        if valor in {0, False, "0", "NO", "No", "no"}:
            return "No"
        return "Sin definir"

    def mostrar_lista(self, switches, titulo="Switches registrados"):
        visual.limpiar()
        visual.titulo(
            titulo,
            "Inventario administrativo de switches"
        )

        if not switches:
            visual.warning("No se encontraron switches.")
            return None

        visual.dashboard([
            {
                "titulo": "🖧 Registrados",
                "contenido": str(len(switches)),
                "color": "bright_blue"
            },
            {
                "titulo": "🌳 Con padre",
                "contenido": str(sum(
                    s.get("switch_padre_id") is not None
                    for s in switches
                )),
                "color": "green"
            },
            {
                "titulo": "📄 Con Excel",
                "contenido": str(sum(
                    s.get("hoja_excel") is not None
                    and s.get("bloque_excel") is not None
                    for s in switches
                )),
                "color": "cyan"
            },
            {
                "titulo": "⚠ Sin clasificar",
                "contenido": str(sum(
                    str(s.get("rol") or "NO DEFINIDO").upper()
                    == "NO DEFINIDO"
                    for s in switches
                )),
                "color": "yellow"
            }
        ])

        filas = []

        for numero, switch in enumerate(switches, start=1):
            modelo = self.gestor_accesos.limpiar_modelo(
                switch.get("marca"),
                switch.get("modelo")
            )
            rol = self.valor_visible(
                switch.get("rol"),
                "NO DEFINIDO"
            )
            criticidad = self.valor_visible(
                switch.get("criticidad"),
                "NO DEFINIDA"
            )

            filas.append((
                str(numero),
                self.valor_visible(switch.get("ip")),
                self.valor_visible(
                    switch.get("ubicacion"),
                    self.valor_visible(switch.get("nombre"))
                ),
                self.valor_visible(switch.get("marca")),
                self.valor_visible(modelo),
                f"[{self.color_rol(rol)}]{rol}[/]",
                f"[{self.color_criticidad(criticidad)}]{criticidad}[/]",
                self.valor_visible(switch.get("hoja_excel")),
                self.valor_visible(switch.get("bloque_excel")),
            ))

        visual.tabla(
            titulo,
            [
                {"nombre": "N.º", "justify": "right", "no_wrap": True},
                {"nombre": "IP", "no_wrap": True},
                "Ubicación",
                {"nombre": "Marca", "no_wrap": True},
                "Modelo",
                {"nombre": "Rol", "no_wrap": True},
                {"nombre": "Criticidad", "no_wrap": True},
                "Hoja",
                {"nombre": "Bloque", "justify": "right", "no_wrap": True},
            ],
            filas,
            expandir=True
        )

        while True:
            seleccion = input(
                "\nSwitch para ver ficha [0 para volver]: "
            ).strip()

            if seleccion in {"", "0"}:
                return None

            try:
                indice = int(seleccion)
            except ValueError:
                visual.error("Debes escribir un número.")
                continue

            if not 1 <= indice <= len(switches):
                visual.error("La opción seleccionada no existe.")
                continue

            switch = switches[indice - 1]
            self.mostrar_ficha(switch)
            return switch

    def mostrar_ficha(self, switch, mostrar_password=True):
        visual.limpiar()

        nombre = self.valor_visible(
            switch.get("nombre_logico"),
            self.valor_visible(
                switch.get("nombre"),
                self.valor_visible(switch.get("ubicacion"), "Switch")
            )
        )

        criticidad = self.valor_visible(
            switch.get("criticidad"),
            "NO DEFINIDA"
        )

        visual.titulo(
            f"FICHA DEL SWITCH — {nombre}",
            self.valor_visible(switch.get("ip")),
            self.color_criticidad(criticidad)
        )

        visual.dashboard([
            {
                "titulo": "🌐 IP",
                "contenido": self.valor_visible(switch.get("ip")),
                "color": "cyan"
            },
            {
                "titulo": "🖧 Rol",
                "contenido": self.valor_visible(
                    switch.get("rol"),
                    "NO DEFINIDO"
                ),
                "color": self.color_rol(switch.get("rol"))
            },
            {
                "titulo": "⚠ Criticidad",
                "contenido": criticidad,
                "color": self.color_criticidad(criticidad)
            },
            {
                "titulo": "📍 Ubicación",
                "contenido": self.valor_visible(
                    switch.get("ubicacion")
                ),
                "color": "bright_blue"
            }
        ])

        modelo = self.gestor_accesos.limpiar_modelo(
            switch.get("marca"),
            switch.get("modelo")
        )

        password = self.valor_visible(
            switch.get("password"),
            "Sin contraseña registrada"
        )

        visual.tabla(
            "Información administrativa",
            [
                {"nombre": "Campo", "style": "cyan", "no_wrap": True},
                "Valor"
            ],
            [
                ("ID interno", self.valor_visible(switch.get("id"))),
                ("Último octeto", self.valor_visible(switch.get("ultimo_octeto"))),
                ("Nombre", self.valor_visible(switch.get("nombre"))),
                ("IP", self.valor_visible(switch.get("ip"))),
                ("MAC", self.valor_visible(switch.get("mac"))),
                ("Marca", self.valor_visible(switch.get("marca"))),
                ("Modelo", self.valor_visible(modelo)),
                ("Usuario", self.valor_visible(switch.get("usuario"))),
                ("Contraseña", password),
                ("Ubicación", self.valor_visible(switch.get("ubicacion"))),
                ("Observaciones", self.valor_visible(switch.get("observaciones"))),
            ],
            expandir=True,
            mostrar_lineas=True
        )

        visual.tabla(
            "Inventario y topología",
            [
                {"nombre": "Campo", "style": "magenta", "no_wrap": True},
                "Valor"
            ],
            [
                ("Hoja Excel", self.valor_visible(switch.get("hoja_excel"))),
                ("Bloque Excel", self.valor_visible(switch.get("bloque_excel"))),
                ("Nombre lógico", self.valor_visible(switch.get("nombre_logico"))),
                ("Rol", self.valor_visible(switch.get("rol"), "NO DEFINIDO")),
                ("Criticidad", criticidad),
                ("Switch padre ID", self.valor_visible(switch.get("switch_padre_id"))),
                ("Puerto de subida", self.valor_visible(switch.get("puerto_subida"))),
                ("Tecnología de subida", self.valor_visible(switch.get("tecnologia_subida"))),
                ("Tiene PoE", self.texto_booleano(switch.get("tiene_poe"))),
                ("Tiene UPS", self.texto_booleano(switch.get("tiene_ups"))),
                ("Notas topológicas", self.valor_visible(switch.get("notas_topologia"))),
            ],
            expandir=True,
            mostrar_lineas=True
        )

        visual.info(
            "Credenciales visibles porque esta ficha se abrió "
            "desde el módulo administrativo protegido."
        )