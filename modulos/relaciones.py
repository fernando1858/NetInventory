class GestorRelaciones:
    def __init__(
        self,
        inventario,
        gestor_accesos
    ):
        self.inventario = inventario
        self.gestor_accesos = gestor_accesos
        self.historial = gestor_accesos.historial

    def normalizar(self, valor):
        return self.inventario.normalizar_texto(
            valor
        )

    def obtener_bloques_existentes(self):
        bloques = {}

        for registro in self.inventario.registros:
            hoja = registro.get("hoja")
            bloque = registro.get("bloque")

            if hoja is None or bloque is None:
                continue

            clave = (
                self.normalizar(hoja),
                bloque
            )

            if clave not in bloques:
                bloques[clave] = {
                    "hoja": hoja,
                    "bloque": bloque,
                    "cantidad_puertos": 0
                }

            bloques[clave][
                "cantidad_puertos"
            ] += 1

        return bloques

    def bloque_existe(
        self,
        hoja_buscada,
        bloque_buscado
    ):
        try:
            bloque_buscado = int(
                bloque_buscado
            )

        except (
            ValueError,
            TypeError
        ):
            return False

        clave = (
            self.normalizar(
                hoja_buscada
            ),
            bloque_buscado
        )

        return (
            clave
            in self.obtener_bloques_existentes()
        )

    def obtener_nombre_real_hoja(
        self,
        hoja_buscada
    ):
        hoja_normalizada = self.normalizar(
            hoja_buscada
        )

        for registro in self.inventario.registros:
            nombre_real = registro.get(
                "hoja"
            )

            if (
                self.normalizar(nombre_real)
                == hoja_normalizada
            ):
                return nombre_real

        return None

    def obtener_switch_por_bloque(
        self,
        hoja,
        bloque
    ):
        return (
            self.gestor_accesos
            .buscar_por_origen_excel(
                hoja,
                bloque
            )
        )

    def obtener_switch_por_registro(
        self,
        registro
    ):
        if registro is None:
            return None

        return self.obtener_switch_por_bloque(
            registro.get("hoja"),
            registro.get("bloque")
        )

    def obtener_relacion_por_octeto(
        self,
        ultimo_octeto
    ):
        switch = (
            self.gestor_accesos
            .obtener_por_octeto(
                ultimo_octeto
            )
        )

        if switch is None:
            return None

        return {
            "switch": switch,
            "hoja": switch.get(
                "hoja_excel"
            ),
            "bloque": switch.get(
                "bloque_excel"
            )
        }

    def actualizar_relacion_directa(
        self,
        ultimo_octeto,
        hoja,
        bloque
    ):
        consulta = """
        UPDATE accesos_switches
        SET
            hoja_excel = ?,
            bloque_excel = ?,
            fecha_actualizacion = CURRENT_TIMESTAMP
        WHERE ultimo_octeto = ?;
        """

        with (
            self.gestor_accesos
            .base_datos
            .conectar()
        ) as conexion:
            cursor = conexion.execute(
                consulta,
                (
                    hoja,
                    bloque,
                    ultimo_octeto
                )
            )

            conexion.commit()

        return cursor.rowcount > 0

    def relacionar(
        self,
        ultimo_octeto,
        hoja,
        bloque,
        reemplazar=False
    ):
        switch = (
            self.gestor_accesos
            .obtener_por_octeto(
                ultimo_octeto
            )
        )

        if switch is None:
            raise ValueError(
                "No existe un switch con ese "
                "último octeto."
            )

        try:
            bloque = int(bloque)

        except (
            ValueError,
            TypeError
        ) as error:
            raise ValueError(
                "El bloque debe ser numérico."
            ) from error

        nombre_real_hoja = (
            self.obtener_nombre_real_hoja(
                hoja
            )
        )

        if nombre_real_hoja is None:
            raise ValueError(
                "La hoja indicada no existe "
                "en el inventario cargado."
            )

        if not self.bloque_existe(
            nombre_real_hoja,
            bloque
        ):
            raise ValueError(
                f"No existe el bloque {bloque} "
                f"en la hoja {nombre_real_hoja}."
            )

        switch_actual = (
            self.obtener_switch_por_bloque(
                nombre_real_hoja,
                bloque
            )
        )

        if (
            switch_actual is not None
            and switch_actual.get(
                "ultimo_octeto"
            )
            != switch.get(
                "ultimo_octeto"
            )
        ):
            if not reemplazar:
                raise ValueError(
                    "Ese bloque ya está relacionado con "
                    f"el switch {switch_actual.get('ip')}."
                )

            self.quitar_relacion(
                switch_actual.get(
                    "ultimo_octeto"
                ),
                origen=(
                    "Reemplazo de relación"
                )
            )

        hoja_anterior = switch.get(
            "hoja_excel"
        )

        bloque_anterior = switch.get(
            "bloque_excel"
        )

        actualizado = self.actualizar_relacion_directa(
            ultimo_octeto=switch.get(
                "ultimo_octeto"
            ),
            hoja=nombre_real_hoja,
            bloque=bloque
        )

        if not actualizado:
            raise ValueError(
                "No se pudo guardar la relación."
            )

        detalle = [
            {
                "campo": "Hoja relacionada",
                "anterior": hoja_anterior,
                "nuevo": nombre_real_hoja
            },
            {
                "campo": "Bloque relacionado",
                "anterior": bloque_anterior,
                "nuevo": bloque
            }
        ]

        self.historial.registrar(
            accion=(
                "RELACIÓN ACTUALIZADA"
                if (
                    hoja_anterior is not None
                    or bloque_anterior is not None
                )
                else "RELACIÓN CREADA"
            ),
            entidad="relación",
            ultimo_octeto=switch.get(
                "ultimo_octeto"
            ),
            ip=switch.get("ip"),
            ubicacion=switch.get(
                "ubicacion"
            ),
            detalle=detalle,
            origen="Gestión manual"
        )

        return {
            "switch": (
                self.gestor_accesos
                .obtener_por_octeto(
                    ultimo_octeto
                )
            ),
            "hoja": nombre_real_hoja,
            "bloque": bloque
        }

    def quitar_relacion(
        self,
        ultimo_octeto,
        origen="Gestión manual"
    ):
        switch = (
            self.gestor_accesos
            .obtener_por_octeto(
                ultimo_octeto
            )
        )

        if switch is None:
            raise ValueError(
                "No existe un switch con ese "
                "último octeto."
            )

        hoja_anterior = switch.get(
            "hoja_excel"
        )

        bloque_anterior = switch.get(
            "bloque_excel"
        )

        consulta = """
        UPDATE accesos_switches
        SET
            hoja_excel = NULL,
            bloque_excel = NULL,
            fecha_actualizacion = CURRENT_TIMESTAMP
        WHERE ultimo_octeto = ?;
        """

        with (
            self.gestor_accesos
            .base_datos
            .conectar()
        ) as conexion:
            cursor = conexion.execute(
                consulta,
                (
                    switch.get(
                        "ultimo_octeto"
                    ),
                )
            )

            conexion.commit()

        eliminado = cursor.rowcount > 0

        if eliminado and (
            hoja_anterior is not None
            or bloque_anterior is not None
        ):
            self.historial.registrar(
                accion="RELACIÓN ELIMINADA",
                entidad="relación",
                ultimo_octeto=switch.get(
                    "ultimo_octeto"
                ),
                ip=switch.get("ip"),
                ubicacion=switch.get(
                    "ubicacion"
                ),
                detalle=[
                    {
                        "campo": "Hoja relacionada",
                        "anterior": hoja_anterior,
                        "nuevo": None
                    },
                    {
                        "campo": "Bloque relacionado",
                        "anterior": bloque_anterior,
                        "nuevo": None
                    }
                ],
                origen=origen
            )

        return eliminado

    def listar_bloques(self):
        bloques_existentes = (
            self.obtener_bloques_existentes()
        )

        resultados = []

        for datos in (
            bloques_existentes.values()
        ):
            switch = (
                self.obtener_switch_por_bloque(
                    datos["hoja"],
                    datos["bloque"]
                )
            )

            resultados.append(
                {
                    "hoja": datos["hoja"],
                    "bloque": datos["bloque"],
                    "cantidad_puertos": (
                        datos[
                            "cantidad_puertos"
                        ]
                    ),
                    "switch": switch
                }
            )

        return sorted(
            resultados,
            key=lambda item: (
                self.normalizar(
                    item["hoja"]
                ),
                item["bloque"]
            )
        )

    def mostrar_relaciones(self):
        relaciones = self.listar_bloques()

        print(
            "\n========== RELACIONES DE SWITCHES =========="
        )

        if not relaciones:
            print(
                "\nNo se detectaron bloques."
            )
            return

        relacionados = 0
        sin_relacion = 0

        for relacion in relaciones:
            switch = relacion["switch"]

            print(
                "\n----------------------------------------"
            )
            print(
                f"Hoja: {relacion['hoja']}"
            )
            print(
                f"Bloque: {relacion['bloque']}"
            )
            print(
                "Puertos documentados: "
                f"{relacion['cantidad_puertos']}"
            )

            if switch is None:
                print(
                    "Switch: Sin relacionar"
                )

                sin_relacion += 1

            else:
                print(
                    f"Switch: {switch.get('ip')}"
                )
                print(
                    "Ubicación: "
                    f"{switch.get('ubicacion') or 'Sin información'}"
                )
                print(
                    "Marca: "
                    f"{switch.get('marca') or 'Sin información'}"
                )
                print(
                    "Modelo: "
                    f"{switch.get('modelo') or 'Sin información'}"
                )

                relacionados += 1

        print(
            "\n========== RESUMEN =========="
        )
        print(
            f"Bloques relacionados: "
            f"{relacionados}"
        )
        print(
            f"Bloques sin relación: "
            f"{sin_relacion}"
        )

    def validar_relaciones(self):
        bloques_existentes = (
            self.obtener_bloques_existentes()
        )

        validas = []
        invalidas = []
        sin_relacion = []

        for switch in (
            self.gestor_accesos.listar_todos()
        ):
            hoja = switch.get(
                "hoja_excel"
            )

            bloque = switch.get(
                "bloque_excel"
            )

            if hoja is None and bloque is None:
                sin_relacion.append(
                    {
                        "switch": switch,
                        "motivo": (
                            "El switch no tiene "
                            "una relación configurada."
                        )
                    }
                )

                continue

            if hoja is None or bloque is None:
                invalidas.append(
                    {
                        "switch": switch,
                        "hoja": hoja,
                        "bloque": bloque,
                        "motivo": (
                            "La relación está incompleta."
                        )
                    }
                )

                continue

            clave = (
                self.normalizar(hoja),
                bloque
            )

            if clave in bloques_existentes:
                validas.append(
                    {
                        "switch": switch,
                        "hoja": (
                            bloques_existentes[
                                clave
                            ]["hoja"]
                        ),
                        "bloque": bloque
                    }
                )
            else:
                invalidas.append(
                    {
                        "switch": switch,
                        "hoja": hoja,
                        "bloque": bloque,
                        "motivo": (
                            "La hoja o el bloque ya no "
                            "existen en el Excel actual."
                        )
                    }
                )

        return {
            "validas": validas,
            "invalidas": invalidas,
            "sin_relacion": sin_relacion
        }

    def mostrar_validacion_relaciones(self):
        resultado = (
            self.validar_relaciones()
        )

        validas = resultado["validas"]
        invalidas = resultado["invalidas"]
        sin_relacion = resultado[
            "sin_relacion"
        ]

        print(
            "\n========== VALIDACIÓN DE RELACIONES =========="
        )
        print(
            f"\nRelaciones válidas: "
            f"{len(validas)}"
        )
        print(
            f"Relaciones inválidas: "
            f"{len(invalidas)}"
        )
        print(
            f"Switches sin relación: "
            f"{len(sin_relacion)}"
        )

        if validas:
            print(
                "\n---------- RELACIONES VÁLIDAS ----------"
            )

            for relacion in validas:
                switch = relacion["switch"]

                print(
                    f"[OK] {switch.get('ip')} | "
                    f"{relacion['hoja']} | "
                    f"Bloque {relacion['bloque']}"
                )

        if invalidas:
            print(
                "\n---------- RELACIONES INVÁLIDAS ----------"
            )

            for relacion in invalidas:
                switch = relacion["switch"]

                print(
                    "\n----------------------------------------"
                )
                print(
                    f"Switch: {switch.get('ip')}"
                )
                print(
                    "Hoja guardada: "
                    f"{relacion.get('hoja') or 'Sin información'}"
                )
                print(
                    "Bloque guardado: "
                    f"{relacion.get('bloque') or 'Sin información'}"
                )
                print(
                    f"Motivo: {relacion['motivo']}"
                )

        if sin_relacion:
            print(
                "\n---------- SWITCHES SIN RELACIÓN ----------"
            )

            for registro in sin_relacion:
                switch = registro["switch"]

                print(
                    f"- {switch.get('ip')} | "
                    f"{switch.get('ubicacion') or 'Sin ubicación'}"
                )

        if not invalidas:
            print(
                "\nNo se encontraron relaciones inválidas."
            )

        return resultado

    def limpiar_relaciones_invalidas(self):
        resultado = (
            self.validar_relaciones()
        )

        invalidas = resultado["invalidas"]

        eliminadas = 0
        errores = []

        for relacion in invalidas:
            switch = relacion["switch"]

            try:
                if self.quitar_relacion(
                    switch.get(
                        "ultimo_octeto"
                    ),
                    origen=(
                        "Limpieza de relaciones inválidas"
                    )
                ):
                    eliminadas += 1

            except ValueError as error:
                errores.append(
                    {
                        "ip": switch.get("ip"),
                        "motivo": str(error)
                    }
                )

        return {
            "detectadas": len(invalidas),
            "eliminadas": eliminadas,
            "errores": errores
        }