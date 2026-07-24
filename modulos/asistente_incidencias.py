class AsistenteIncidencias:
    """
    Guía de diagnóstico basada en los datos ya existentes
    en NetInventory.

    No modifica switches, Excel ni base de datos.
    """

    def __init__(
        self,
        analizador_red,
        gestor_topologia,
        centro_snmp
    ):
        self.analizador_red = analizador_red
        self.gestor_topologia = gestor_topologia
        self.centro_snmp = centro_snmp

    @staticmethod
    def valor_visible(
        valor,
        predeterminado="Sin definir"
    ):
        if valor is None:
            return predeterminado

        texto = str(valor).strip()
        return texto or predeterminado

    def obtener_estado_snmp(
        self,
        switch
    ):
        """
        Ejecuta una prueba SNMP mínima sobre un switch.
        """
        if not hasattr(
            self.centro_snmp,
            "cliente_snmp"
        ):
            return {
                "disponible": False,
                "correcto": None,
                "detalle": (
                    "El Centro SNMP no está disponible."
                )
            }

        ip = switch.get("ip")

        if not ip:
            return {
                "disponible": True,
                "correcto": None,
                "detalle": (
                    "El switch no tiene una IP registrada."
                )
            }

        try:
            resultado = (
                self.centro_snmp.cliente_snmp
                .probar_conectividad(
                    ip
                )
            )

        except Exception as error:
            return {
                "disponible": True,
                "correcto": False,
                "detalle": str(error)
            }

        return {
            "disponible": True,
            "correcto": resultado.correcto,
            "detalle": (
                "El switch respondió por SNMP."
                if resultado.correcto
                else (
                    resultado.error
                    or "El switch no respondió por SNMP."
                )
            )
        }


    def obtener_ejemplos_switches(
        self,
        limite=5
    ):
        """
        Obtiene ejemplos reales de switches registrados.
        """
        ejemplos = []

        for switch in self.gestor_topologia.listar_switches():
            nombre = self.analizador_red.nombre_visible(
                switch
            )

            if nombre and nombre not in ejemplos:
                ejemplos.append(
                    nombre
                )

            if len(ejemplos) >= limite:
                break

        return ejemplos

    def obtener_ejemplos_inventario(
        self,
        tipo_buscado,
        limite=5
    ):
        """
        Obtiene ejemplos reales desde el inventario Excel.
        """
        tipo_normalizado = (
            self.analizador_red.inventario
            .normalizar_texto(
                tipo_buscado
            )
        )

        ejemplos = []

        for registro in (
            self.analizador_red.inventario.registros
        ):
            tipo = (
                self.analizador_red.inventario
                .normalizar_texto(
                    registro.get("tipo")
                )
            )

            equipo = self.valor_visible(
                registro.get("equipo"),
                ""
            )

            coincide = False

            if tipo_buscado == "AP":
                coincide = (
                    "antena" in tipo
                    or "access point" in tipo
                    or tipo == "ap"
                )

            elif tipo_buscado == "teléfono":
                coincide = (
                    "telefono" in tipo
                )

            elif tipo_buscado == "equipo":
                coincide = (
                    tipo == "equipo"
                    or "equipo" in tipo
                )

            else:
                coincide = (
                    tipo_normalizado in tipo
                )

            if (
                coincide
                and equipo
                and equipo not in ejemplos
            ):
                ejemplos.append(
                    equipo
                )

            if len(ejemplos) >= limite:
                break

        return ejemplos

    @staticmethod
    def mostrar_ejemplos(
        titulo,
        ejemplos
    ):
        """
        Muestra una lista corta de ejemplos antes de pedir
        una entrada al usuario.
        """
        print(
            f"\n{titulo}"
        )

        if not ejemplos:
            print(
                "- No hay ejemplos disponibles."
            )
            return

        for ejemplo in ejemplos:
            print(
                f"- {ejemplo}"
            )

    def solicitar_switch(
        self,
        mensaje
    ):
        print(
            f"\n{mensaje}."
        )
        print(
            "Puedes escribir:"
        )
        print(
            "- Último octeto, por ejemplo: 220"
        )
        print(
            "- IP completa, por ejemplo: 192.168.5.220"
        )
        print(
            "- ID interno del switch"
        )

        self.mostrar_ejemplos(
            "Ejemplos reales de switches:",
            self.obtener_ejemplos_switches()
        )

        identificador = input(
            "\nEntrada: "
        ).strip()

        if not identificador:
            raise ValueError(
                "Debes indicar un switch."
            )

        switch = self.analizador_red.obtener_switch(
            identificador
        )

        if switch is None:
            raise ValueError(
                "No se encontró el switch indicado."
            )

        return switch

    def mostrar_resumen_switch(
        self,
        switch
    ):
        nombre = self.analizador_red.nombre_visible(
            switch
        )

        print(
            f"\nSwitch: {nombre}"
        )
        print(
            "IP: "
            f"{self.valor_visible(switch.get('ip'))}"
        )
        print(
            "Rol: "
            f"{self.valor_visible(switch.get('rol'))}"
        )
        print(
            "Criticidad: "
            f"{self.valor_visible(switch.get('criticidad'))}"
        )

    def mostrar_ruta_resumida(
        self,
        ruta
    ):
        nombres = [
            self.analizador_red.nombre_visible(
                nodo
            )
            for nodo in ruta["ruta"]
        ]

        print(
            "\nRuta hacia el Core:"
        )
        print(
            " -> ".join(
                nombres
            )
        )
        print(
            f"Saltos: {ruta['saltos']}"
        )

        if not ruta["termina_en_core"]:
            print(
                "[AVISO] La ruta no termina en un switch "
                "clasificado como CORE."
            )

    def mostrar_impacto_resumido(
        self,
        impacto
    ):
        print(
            "\nImpacto potencial:"
        )
        print(
            "Switches afectados: "
            f"{impacto['switches_afectados']}"
        )
        print(
            "Registros con equipo: "
            f"{impacto['equipos_conectados']}"
        )
        print(
            f"AP: {impacto['antenas']}"
        )
        print(
            f"Cámaras: {impacto['camaras']}"
        )
        print(
            f"Teléfonos IP: {impacto['telefonos_ip']}"
        )
        print(
            "Prioridad calculada: "
            f"{impacto['prioridad']}"
        )
        print(
            "Cobertura del análisis: "
            f"{impacto['cobertura_porcentaje']} %"
        )

    def mostrar_estado_snmp(
        self,
        switch
    ):
        estado = self.obtener_estado_snmp(
            switch
        )

        print(
            "\nEstado SNMP:"
        )

        if estado["correcto"] is True:
            print(
                "[OK] Responde por SNMP."
            )
        elif estado["correcto"] is False:
            print(
                "[AVISO] No responde por SNMP."
            )
            print(
                f"Detalle: {estado['detalle']}"
            )
        else:
            print(
                f"[AVISO] {estado['detalle']}"
            )

    def construir_contexto(
        self,
        switch
    ):
        impacto = self.analizador_red.analizar_switch(
            switch.get("id")
        )

        ruta = (
            self.analizador_red
            .obtener_ruta_hacia_core(
                switch.get("id")
            )
        )

        return impacto, ruta

    def incidencia_sector_sin_red(self):
        switch = self.solicitar_switch(
            "Switch o sector principal afectado"
        )

        impacto, ruta = self.construir_contexto(
            switch
        )

        print("\n" + "=" * 72)
        print("INCIDENCIA: SECTOR SIN RED".center(72))
        print("=" * 72)

        self.mostrar_resumen_switch(
            switch
        )
        self.mostrar_ruta_resumida(
            ruta
        )
        self.mostrar_impacto_resumido(
            impacto
        )
        self.mostrar_estado_snmp(
            switch
        )

        print("\nOrden sugerido de revisión:")
        print(
            "1. Confirmar si el problema afecta a todo "
            "el sector o solo a un equipo."
        )
        print(
            "2. Revisar alimentación y luces del switch "
            "del sector."
        )
        print(
            "3. Revisar el enlace desde el switch afectado "
            "hacia su padre."
        )
        print(
            "4. Consultar el estado SNMP de los switches "
            "que aparecen en la ruta."
        )
        print(
            "5. Revisar el siguiente enlace hacia el Core "
            "solo si el primer tramo está operativo."
        )

    def incidencia_switch_no_responde(self):
        switch = self.solicitar_switch(
            "Switch que no responde"
        )

        impacto, ruta = self.construir_contexto(
            switch
        )

        print("\n" + "=" * 72)
        print("INCIDENCIA: SWITCH SIN RESPUESTA".center(72))
        print("=" * 72)

        self.mostrar_resumen_switch(
            switch
        )
        self.mostrar_estado_snmp(
            switch
        )
        self.mostrar_ruta_resumida(
            ruta
        )
        self.mostrar_impacto_resumido(
            impacto
        )

        print("\nOrden sugerido de revisión:")
        print(
            "1. Comprobar ping desde el equipo técnico."
        )
        print(
            "2. Confirmar alimentación, UPS e indicadores "
            "del switch."
        )
        print(
            "3. Revisar el puerto de subida del switch hijo."
        )
        print(
            "4. Revisar el puerto correspondiente en el "
            "switch padre."
        )
        print(
            "5. Si responde a ping, revisar únicamente "
            "configuración o acceso SNMP."
        )

    def buscar_registros_equipo(
        self,
        texto
    ):
        normalizado = (
            self.analizador_red.inventario
            .normalizar_texto(
                texto
            )
        )

        resultados = []

        for registro in (
            self.analizador_red.inventario.registros
        ):
            equipo = (
                self.analizador_red.inventario
                .normalizar_texto(
                    registro.get("equipo")
                )
            )

            tipo = (
                self.analizador_red.inventario
                .normalizar_texto(
                    registro.get("tipo")
                )
            )

            if (
                normalizado in equipo
                or normalizado in tipo
            ):
                resultados.append(
                    registro
                )

        return resultados

    def seleccionar_registro(
        self,
        tipo_incidente
    ):
        print(
            f"\nEscribe el nombre o ubicación del "
            f"{tipo_incidente}."
        )

        self.mostrar_ejemplos(
            "Ejemplos reales encontrados en el inventario:",
            self.obtener_ejemplos_inventario(
                tipo_incidente
            )
        )

        print(
            "\nTambién puedes escribir solo una parte del "
            "nombre, por ejemplo: GERENCIA, BIBLIOTECA "
            "o RECEPCIÓN."
        )

        texto = input(
            "\nEntrada: "
        ).strip()

        if not texto:
            raise ValueError(
                "Debes escribir un criterio de búsqueda."
            )

        resultados = self.buscar_registros_equipo(
            texto
        )

        if not resultados:
            raise ValueError(
                "No se encontraron registros coincidentes."
            )

        print(
            f"\nResultados encontrados: {len(resultados)}"
        )

        limite = min(
            len(resultados),
            25
        )

        for numero, registro in enumerate(
            resultados[:limite],
            start=1
        ):
            print(
                f"{numero}) "
                f"{self.valor_visible(registro.get('equipo'))} | "
                f"{registro.get('hoja')} | "
                f"Bloque {registro.get('bloque')} | "
                f"Puerto {registro.get('puerto_switch')}"
            )

        seleccion = input(
            "\nSelecciona un resultado: "
        ).strip()

        try:
            indice = int(
                seleccion
            )
        except ValueError as error:
            raise ValueError(
                "La selección debe ser numérica."
            ) from error

        if indice < 1 or indice > limite:
            raise ValueError(
                "La selección indicada no existe."
            )

        return resultados[
            indice - 1
        ]

    def mostrar_incidente_dispositivo(
        self,
        titulo,
        tipo_incidente
    ):
        registro = self.seleccionar_registro(
            tipo_incidente
        )

        switch = (
            self.analizador_red
            .gestor_topologia
            .gestor_accesos
            .buscar_por_origen_excel(
                registro.get("hoja"),
                registro.get("bloque")
            )
        )

        print("\n" + "=" * 72)
        print(titulo.center(72))
        print("=" * 72)

        print(
            "\nUbicación registrada: "
            f"{self.valor_visible(registro.get('equipo'))}"
        )
        print(
            f"Tipo: {self.valor_visible(registro.get('tipo'))}"
        )
        print(
            f"Hoja: {registro.get('hoja')}"
        )
        print(
            f"Bloque: {registro.get('bloque')}"
        )
        print(
            "Puerto del switch: "
            f"{registro.get('puerto_switch')}"
        )
        print(
            "Boca patch: "
            f"{self.valor_visible(registro.get('boca_patch'))}"
        )
        print(
            f"VLAN documentada: "
            f"{self.valor_visible(registro.get('vlan'))}"
        )

        if switch is None:
            print(
                "\n[AVISO] El bloque no está relacionado con "
                "un switch registrado."
            )
        else:
            print(
                "\nSwitch relacionado: "
                f"{self.analizador_red.nombre_visible(switch)}"
            )
            print(
                f"IP: {self.valor_visible(switch.get('ip'))}"
            )
            self.mostrar_estado_snmp(
                switch
            )

        print("\nOrden sugerido de revisión:")
        print(
            "1. Confirmar alimentación del dispositivo."
        )
        print(
            "2. Revisar cable, inyector PoE y patch panel "
            "cuando corresponda."
        )
        print(
            "3. Revisar el puerto indicado en la tabla de "
            "estado de interfaces."
        )
        print(
            "4. Confirmar que el estado del puerto sea UP y "
            "que la velocidad sea la esperada."
        )
        print(
            "5. Revisar VLAN o configuración solo después "
            "de descartar el problema físico."
        )

    def ejecutar(self):
        while True:
            print("\n" + "=" * 72)
            print("ASISTENTE DE INCIDENCIAS".center(72))
            print("=" * 72)

            print("\n1) Un sector quedó sin red")
            print("2) Un switch no responde")
            print("3) Un AP no funciona")
            print("4) Un equipo no tiene conexión")
            print("5) Un teléfono IP no funciona")
            print("0) Volver")

            opcion = input(
                "\nSelecciona una opción: "
            ).strip()

            try:
                if opcion == "1":
                    self.incidencia_sector_sin_red()

                elif opcion == "2":
                    self.incidencia_switch_no_responde()

                elif opcion == "3":
                    self.mostrar_incidente_dispositivo(
                        "INCIDENCIA: AP SIN SERVICIO",
                        "AP"
                    )

                elif opcion == "4":
                    self.mostrar_incidente_dispositivo(
                        "INCIDENCIA: EQUIPO SIN CONEXIÓN",
                        "equipo"
                    )

                elif opcion == "5":
                    self.mostrar_incidente_dispositivo(
                        "INCIDENCIA: TELÉFONO IP",
                        "teléfono"
                    )

                elif opcion == "0":
                    break

                else:
                    print(
                        "\n[ERROR] Opción inválida."
                    )
                    input(
                        "\nPresiona ENTER para continuar..."
                    )
                    continue

            except ValueError as error:
                print(
                    f"\n[ERROR] {error}"
                )

            except Exception as error:
                print(
                    "\n[ERROR] No fue posible completar "
                    "el análisis."
                )
                print(
                    f"Detalle: {error}"
                )

            input(
                "\nPresiona ENTER para continuar..."
            )