class GestorFichasRed:
    def __init__(
        self,
        inventario,
        gestor_relaciones,
        gestor_accesos
    ):
        self.inventario = inventario
        self.gestor_relaciones = gestor_relaciones
        self.gestor_accesos = gestor_accesos

    def normalizar(self, valor):
        return self.inventario.normalizar_texto(
            valor
        )

    def convertir_entero(
        self,
        valor,
        nombre_campo
    ):
        try:
            return int(
                str(valor).strip()
            )

        except (ValueError, TypeError) as error:
            raise ValueError(
                f"{nombre_campo} debe ser numérico."
            ) from error

    def obtener_nombre_real_hoja(
        self,
        hoja_buscada
    ):
        hoja_normalizada = self.normalizar(
            hoja_buscada
        )

        for registro in self.inventario.registros:
            nombre_hoja = registro.get("hoja")

            if (
                self.normalizar(nombre_hoja)
                == hoja_normalizada
            ):
                return nombre_hoja

        return None

    def obtener_switches_relacionados_con_hoja(
        self,
        hoja_buscada
    ):
        hoja_normalizada = self.normalizar(
            hoja_buscada
        )

        switches = []

        for switch in self.gestor_accesos.listar_todos():
            hoja_switch = self.normalizar(
                switch.get("hoja_excel")
            )

            bloque_switch = switch.get(
                "bloque_excel"
            )

            if (
                hoja_switch == hoja_normalizada
                and bloque_switch is not None
            ):
                switches.append(switch)

        return sorted(
            switches,
            key=lambda switch: (
                switch.get("ultimo_octeto") or 0
            )
        )

    def obtener_switch_por_indice(
        self,
        switches,
        indice
    ):
        indice = self.convertir_entero(
            indice,
            "La opción"
        )

        if indice < 1 or indice > len(switches):
            raise ValueError(
                "La opción seleccionada no existe."
            )

        return switches[indice - 1]

    def buscar_puerto_por_switch(
        self,
        hoja_buscada,
        switch,
        puerto_buscado
    ):
        nombre_real_hoja = (
            self.obtener_nombre_real_hoja(
                hoja_buscada
            )
        )

        if nombre_real_hoja is None:
            raise ValueError(
                "No se encontró esa hoja o sector."
            )

        if switch is None:
            raise ValueError(
                "No se seleccionó un switch válido."
            )

        hoja_relacionada = switch.get(
            "hoja_excel"
        )

        bloque_relacionado = switch.get(
            "bloque_excel"
        )

        if (
            hoja_relacionada is None
            or bloque_relacionado is None
        ):
            raise ValueError(
                "Ese switch todavía no está relacionado "
                "con una hoja y bloque del inventario."
            )

        if (
            self.normalizar(hoja_relacionada)
            != self.normalizar(nombre_real_hoja)
        ):
            raise ValueError(
                f"El switch {switch.get('ip')} pertenece "
                f"a la hoja {hoja_relacionada}, no a "
                f"{nombre_real_hoja}."
            )

        puerto = self.convertir_entero(
            puerto_buscado,
            "El puerto"
        )

        registros = [
            registro
            for registro in self.inventario.registros
            if (
                self.normalizar(
                    registro.get("hoja")
                )
                == self.normalizar(nombre_real_hoja)
                and registro.get("bloque")
                == bloque_relacionado
                and registro.get("puerto_switch")
                == puerto
            )
        ]

        return registros

    def construir_fichas(
        self,
        hoja_buscada,
        switch,
        puerto_buscado
    ):
        registros = self.buscar_puerto_por_switch(
            hoja_buscada=hoja_buscada,
            switch=switch,
            puerto_buscado=puerto_buscado
        )

        return [
            {
                "registro": registro,
                "switch": switch
            }
            for registro in registros
        ]

    def valor_visible(self, valor):
        if valor is None:
            return "Sin información"

        return valor

    def mostrar_switches_disponibles(
        self,
        hoja_buscada
    ):
        switches = (
            self.obtener_switches_relacionados_con_hoja(
                hoja_buscada
            )
        )

        if not switches:
            print(
                "\nNo hay switches relacionados "
                "con esta hoja."
            )
            return []

        print(
            "\nSwitches asociados:"
        )

        for numero, switch in enumerate(
            switches,
            start=1
        ):
            print(
                f"{numero}. "
                f"{switch.get('ip')} | "
                f"{switch.get('ubicacion') or 'Sin ubicación'}"
            )

        return switches

    def mostrar_fichas(self, fichas):
        if not fichas:
            print(
                "\nNo se encontró ese puerto dentro "
                "del switch seleccionado."
            )
            return

        for ficha in fichas:
            registro = ficha["registro"]
            switch = ficha["switch"]

            print(
                "\n========================================"
            )
            print(
                "FICHA COMPLETA DE RED"
            )
            print(
                "========================================"
            )

            print(
                "\n---------- UBICACIÓN DOCUMENTADA ----------"
            )
            print(
                f"Hoja / sector: "
                f"{registro.get('hoja')}"
            )
            print(
                f"Fila del Excel: "
                f"{registro.get('fila_excel')}"
            )

            print(
                "\n---------- PUERTO Y CONEXIÓN ----------"
            )
            print(
                f"Puerto del switch: "
                f"{registro.get('puerto_switch')}"
            )
            print(
                "Equipo conectado: "
                f"{self.valor_visible(registro.get('equipo'))}"
            )
            print(
                "Tipo: "
                f"{self.valor_visible(registro.get('tipo'))}"
            )
            print(
                "Boca del patch panel: "
                f"{self.valor_visible(registro.get('boca_patch'))}"
            )
            print(
                "VLAN: "
                f"{self.valor_visible(registro.get('vlan'))}"
            )

            print(
                "\n---------- SWITCH AL QUE PERTENECE ----------"
            )
            print(
                "IP: "
                f"{self.valor_visible(switch.get('ip'))}"
            )
            print(
                "Ubicación: "
                f"{self.valor_visible(switch.get('ubicacion'))}"
            )
            print(
                "MAC: "
                f"{self.valor_visible(switch.get('mac'))}"
            )
            print(
                "Marca: "
                f"{self.valor_visible(switch.get('marca'))}"
            )
            print(
                "Modelo: "
                f"{self.valor_visible(switch.get('modelo'))}"
            )

            observaciones = switch.get(
                "observaciones"
            )

            if observaciones:
                print(
                    f"Observaciones: {observaciones}"
                )