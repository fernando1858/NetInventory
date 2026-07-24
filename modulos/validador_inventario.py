from collections import Counter, defaultdict


class ValidadorInventario:
    """
    Analiza la información cargada desde el Excel y detecta
    problemas de calidad, inconsistencias y datos pendientes.

    Este módulo nunca modifica el Excel ni la base de datos.
    """

    NIVEL_CRITICO = "CRÍTICO"
    NIVEL_ADVERTENCIA = "ADVERTENCIA"
    NIVEL_INFORMATIVO = "INFORMATIVO"

    PUERTO_MINIMO = 1
    PUERTO_MAXIMO = 48

    TIPOS_VALIDOS = {
        "Antena",
        "Cámara",
        "Equipo",
        "Sin tipo",
        "Teléfono IP",
        "Troncal"
    }

    def __init__(
        self,
        inventario,
        gestor_relaciones
    ):
        self.inventario = inventario
        self.gestor_relaciones = gestor_relaciones

    def normalizar(self, valor):
        """
        Normaliza texto usando la lógica del inventario.
        """
        return self.inventario.normalizar_texto(
            valor
        )

    def valor_esta_vacio(self, valor):
        """
        Determina si un dato debe considerarse vacío.
        """
        if valor is None:
            return True

        if isinstance(valor, str):
            return not valor.strip()

        return False

    def es_numero_entero(self, valor):
        """
        Indica si un valor puede interpretarse como entero.
        """
        if self.valor_esta_vacio(valor):
            return False

        try:
            numero = float(valor)

        except (ValueError, TypeError):
            return False

        return numero.is_integer()

    def crear_validacion(
        self,
        nivel,
        regla,
        descripcion,
        registro=None,
        hoja=None,
        bloque=None,
        fila_excel=None,
        puerto_switch=None,
        campo=None
    ):
        """
        Construye una validación con una estructura uniforme.
        """
        if registro is not None:
            hoja = registro.get("hoja")
            bloque = registro.get("bloque")
            fila_excel = registro.get("fila_excel")
            puerto_switch = registro.get("puerto_switch")

        return {
            "nivel": nivel,
            "regla": regla,
            "descripcion": descripcion,
            "hoja": hoja,
            "bloque": bloque,
            "fila_excel": fila_excel,
            "puerto_switch": puerto_switch,
            "campo": campo
        }

    def validar_campos_obligatorios(
        self,
        registro
    ):
        """
        Revisa campos esenciales de cada puerto.
        """
        validaciones = []

        campos = {
            "tipo": "Tipo",
            "equipo": "Equipo",
            "boca_patch": "Boca patch",
            "puerto_switch": "Puerto switch",
            "vlan": "VLAN"
        }

        for clave, nombre_visible in campos.items():
            if self.valor_esta_vacio(
                registro.get(clave)
            ):
                nivel = (
                    self.NIVEL_CRITICO
                    if clave == "puerto_switch"
                    else self.NIVEL_ADVERTENCIA
                )

                validaciones.append(
                    self.crear_validacion(
                        nivel=nivel,
                        regla="CAMPO_FALTANTE",
                        descripcion=(
                            f"Falta completar el campo "
                            f"{nombre_visible}."
                        ),
                        registro=registro,
                        campo=nombre_visible
                    )
                )

        return validaciones

    def validar_puerto(
        self,
        registro
    ):
        """
        Revisa que el puerto sea numérico y esté dentro
        del rango habitual.
        """
        validaciones = []
        puerto = registro.get("puerto_switch")

        if self.valor_esta_vacio(puerto):
            return validaciones

        if not self.es_numero_entero(puerto):
            validaciones.append(
                self.crear_validacion(
                    nivel=self.NIVEL_CRITICO,
                    regla="PUERTO_NO_NUMERICO",
                    descripcion=(
                        f"El puerto '{puerto}' no es numérico."
                    ),
                    registro=registro,
                    campo="Puerto switch"
                )
            )
            return validaciones

        puerto = int(float(puerto))

        if not (
            self.PUERTO_MINIMO
            <= puerto
            <= self.PUERTO_MAXIMO
        ):
            validaciones.append(
                self.crear_validacion(
                    nivel=self.NIVEL_CRITICO,
                    regla="PUERTO_FUERA_DE_RANGO",
                    descripcion=(
                        f"El puerto {puerto} está fuera del "
                        f"rango habitual "
                        f"{self.PUERTO_MINIMO}-"
                        f"{self.PUERTO_MAXIMO}."
                    ),
                    registro=registro,
                    campo="Puerto switch"
                )
            )

        return validaciones

    def validar_vlan(
        self,
        registro
    ):
        """
        Comprueba que la VLAN sea numérica cuando exista.
        """
        vlan = registro.get("vlan")

        if self.valor_esta_vacio(vlan):
            return []

        if self.es_numero_entero(vlan):
            return []

        return [
            self.crear_validacion(
                nivel=self.NIVEL_CRITICO,
                regla="VLAN_NO_NUMERICA",
                descripcion=(
                    f"La VLAN '{vlan}' no es numérica."
                ),
                registro=registro,
                campo="VLAN"
            )
        ]

    def validar_boca_patch(
        self,
        registro
    ):
        """
        Comprueba que la boca patch sea numérica cuando exista.

        Se permite texto en troncales o casos especiales,
        pero se informa para revisión.
        """
        boca_patch = registro.get("boca_patch")

        if self.valor_esta_vacio(boca_patch):
            return []

        if self.es_numero_entero(boca_patch):
            return []

        tipo = self.normalizar(
            registro.get("tipo")
        )

        nivel = (
            self.NIVEL_INFORMATIVO
            if "troncal" in tipo
            else self.NIVEL_ADVERTENCIA
        )

        return [
            self.crear_validacion(
                nivel=nivel,
                regla="PATCH_NO_NUMERICO",
                descripcion=(
                    f"La boca patch '{boca_patch}' "
                    "no es numérica."
                ),
                registro=registro,
                campo="Boca patch"
            )
        ]

    def validar_tipo(
        self,
        registro
    ):
        """
        Revisa que el tipo esté normalizado.
        """
        tipo = registro.get("tipo")

        if self.valor_esta_vacio(tipo):
            return []

        if tipo in self.TIPOS_VALIDOS:
            return []

        return [
            self.crear_validacion(
                nivel=self.NIVEL_ADVERTENCIA,
                regla="TIPO_NO_NORMALIZADO",
                descripcion=(
                    f"El tipo '{tipo}' no coincide con "
                    "las categorías normalizadas."
                ),
                registro=registro,
                campo="Tipo"
            )
        ]

    def validar_disponible(
        self,
        registro
    ):
        """
        Revisa contradicciones relacionadas con puertos
        marcados como disponibles.
        """
        equipo = registro.get("equipo")

        if not self.inventario.equipo_esta_disponible(
            equipo
        ):
            return []

        validaciones = []

        tipo = self.normalizar(
            registro.get("tipo")
        )

        tipos_conectados = {
            "antena",
            "camara",
            "telefono ip",
            "troncal"
        }

        if tipo in tipos_conectados:
            validaciones.append(
                self.crear_validacion(
                    nivel=self.NIVEL_ADVERTENCIA,
                    regla="DISPONIBLE_CON_TIPO_ACTIVO",
                    descripcion=(
                        "El puerto está marcado como "
                        f"disponible, pero su tipo es "
                        f"'{registro.get('tipo')}'."
                    ),
                    registro=registro,
                    campo="Equipo"
                )
            )

        return validaciones

    def validar_equipo_segun_tipo(
        self,
        registro
    ):
        """
        Comprueba que determinados tipos tengan
        una identificación de equipo.
        """
        equipo = registro.get("equipo")

        if not self.valor_esta_vacio(equipo):
            return []

        tipo = self.normalizar(
            registro.get("tipo")
        )

        tipos_relevantes = {
            "antena",
            "camara",
            "telefono ip",
            "troncal"
        }

        if tipo not in tipos_relevantes:
            return []

        return [
            self.crear_validacion(
                nivel=self.NIVEL_ADVERTENCIA,
                regla="EQUIPO_NO_IDENTIFICADO",
                descripcion=(
                    f"El puerto es de tipo "
                    f"'{registro.get('tipo')}', pero no "
                    "tiene equipo o destino identificado."
                ),
                registro=registro,
                campo="Equipo"
            )
        ]

    def validar_troncal(
        self,
        registro
    ):
        """
        Revisa que una troncal tenga un destino comprensible.
        """
        tipo = self.normalizar(
            registro.get("tipo")
        )

        if tipo != "troncal":
            return []

        equipo = self.normalizar(
            registro.get("equipo")
        )

        if not equipo:
            return [
                self.crear_validacion(
                    nivel=self.NIVEL_CRITICO,
                    regla="TRONCAL_SIN_DESTINO",
                    descripcion=(
                        "La troncal no tiene un switch "
                        "o destino identificado."
                    ),
                    registro=registro,
                    campo="Equipo"
                )
            ]

        textos_incompletos = {
            "troncal",
            "sin identificar",
            "desconocido",
            "??"
        }

        if equipo in textos_incompletos:
            return [
                self.crear_validacion(
                    nivel=self.NIVEL_ADVERTENCIA,
                    regla="TRONCAL_DESTINO_INCOMPLETO",
                    descripcion=(
                        "La troncal existe, pero su destino "
                        "no está identificado claramente."
                    ),
                    registro=registro,
                    campo="Equipo"
                )
            ]

        return []

    def validar_registro(
        self,
        registro
    ):
        """
        Ejecuta todas las reglas aplicables a una fila.
        """
        validaciones = []

        validaciones.extend(
            self.validar_campos_obligatorios(
                registro
            )
        )

        validaciones.extend(
            self.validar_puerto(
                registro
            )
        )

        validaciones.extend(
            self.validar_vlan(
                registro
            )
        )

        validaciones.extend(
            self.validar_boca_patch(
                registro
            )
        )

        validaciones.extend(
            self.validar_tipo(
                registro
            )
        )

        validaciones.extend(
            self.validar_disponible(
                registro
            )
        )

        validaciones.extend(
            self.validar_equipo_segun_tipo(
                registro
            )
        )

        validaciones.extend(
            self.validar_troncal(
                registro
            )
        )

        return validaciones

    def validar_duplicados(self):
        """
        Revisa puertos repetidos dentro de una misma
        hoja y bloque.
        """
        agrupados = defaultdict(list)

        for registro in self.inventario.registros:
            puerto = registro.get("puerto_switch")

            if self.valor_esta_vacio(puerto):
                continue

            clave = (
                self.normalizar(
                    registro.get("hoja")
                ),
                registro.get("bloque"),
                puerto
            )

            agrupados[clave].append(
                registro
            )

        validaciones = []

        for registros in agrupados.values():
            if len(registros) < 2:
                continue

            filas = [
                str(registro.get("fila_excel"))
                for registro in registros
            ]

            primero = registros[0]

            validaciones.append(
                self.crear_validacion(
                    nivel=self.NIVEL_CRITICO,
                    regla="PUERTO_DUPLICADO",
                    descripcion=(
                        f"El puerto "
                        f"{primero.get('puerto_switch')} "
                        "aparece repetido en las filas "
                        f"{', '.join(filas)}."
                    ),
                    registro=primero,
                    campo="Puerto switch"
                )
            )

        return validaciones

    def validar_relaciones(self):
        """
        Incorpora la validación de relaciones entre
        switches y bloques.
        """
        resultado = (
            self.gestor_relaciones
            .validar_relaciones()
        )

        validaciones = []

        for relacion in resultado.get(
            "invalidas",
            []
        ):
            switch = relacion["switch"]

            validaciones.append(
                self.crear_validacion(
                    nivel=self.NIVEL_CRITICO,
                    regla="RELACION_INVALIDA",
                    descripcion=(
                        f"El switch {switch.get('ip')} "
                        "está relacionado con una hoja o "
                        "bloque que ya no existe."
                    ),
                    hoja=relacion.get("hoja"),
                    bloque=relacion.get("bloque")
                )
            )

        for relacion in resultado.get(
            "sin_relacion",
            []
        ):
            switch = relacion["switch"]

            validaciones.append(
                self.crear_validacion(
                    nivel=self.NIVEL_INFORMATIVO,
                    regla="SWITCH_SIN_RELACION",
                    descripcion=(
                        f"El switch {switch.get('ip')} "
                        "todavía no está asociado con un "
                        "bloque del inventario."
                    )
                )
            )

        return validaciones

    def validar_bloques_sin_switch(self):
        """
        Revisa los bloques detectados que todavía no tienen
        un switch asociado.
        """
        validaciones = []

        for relacion in (
            self.gestor_relaciones.listar_bloques()
        ):
            if relacion.get("switch") is not None:
                continue

            validaciones.append(
                self.crear_validacion(
                    nivel=self.NIVEL_INFORMATIVO,
                    regla="BLOQUE_SIN_SWITCH",
                    descripcion=(
                        "El bloque todavía no tiene un "
                        "switch relacionado."
                    ),
                    hoja=relacion.get("hoja"),
                    bloque=relacion.get("bloque")
                )
            )

        return validaciones

    def ejecutar_validacion(self):
        """
        Ejecuta todas las reglas y devuelve las incidencias.
        """
        validaciones = []

        for registro in self.inventario.registros:
            validaciones.extend(
                self.validar_registro(
                    registro
                )
            )

        validaciones.extend(
            self.validar_duplicados()
        )

        validaciones.extend(
            self.validar_relaciones()
        )

        validaciones.extend(
            self.validar_bloques_sin_switch()
        )

        prioridad = {
            self.NIVEL_CRITICO: 1,
            self.NIVEL_ADVERTENCIA: 2,
            self.NIVEL_INFORMATIVO: 3
        }

        return sorted(
            validaciones,
            key=lambda item: (
                prioridad.get(
                    item.get("nivel"),
                    99
                ),
                self.normalizar(
                    item.get("hoja")
                ),
                item.get("bloque") or 0,
                item.get("fila_excel") or 0,
                item.get("regla") or ""
            )
        )

    def obtener_resumen(
        self,
        validaciones=None
    ):
        """
        Resume los resultados por nivel y regla.
        """
        if validaciones is None:
            validaciones = (
                self.ejecutar_validacion()
            )

        por_nivel = Counter(
            validacion["nivel"]
            for validacion in validaciones
        )

        por_regla = Counter(
            validacion["regla"]
            for validacion in validaciones
        )

        return {
            "total": len(validaciones),
            "criticos": por_nivel[
                self.NIVEL_CRITICO
            ],
            "advertencias": por_nivel[
                self.NIVEL_ADVERTENCIA
            ],
            "informativos": por_nivel[
                self.NIVEL_INFORMATIVO
            ],
            "por_regla": dict(
                sorted(
                    por_regla.items()
                )
            )
        }

    def valor_visible(self, valor):
        if valor is None:
            return "Sin información"

        return valor

    def mostrar_validaciones(
        self,
        validaciones=None
    ):
        """
        Muestra el resultado de la validación en consola.
        """
        if validaciones is None:
            validaciones = (
                self.ejecutar_validacion()
            )

        resumen = self.obtener_resumen(
            validaciones
        )

        print(
            "\n========== VALIDACIÓN DEL INVENTARIO =========="
        )
        print(
            f"\nIncidencias detectadas: "
            f"{resumen['total']}"
        )
        print(
            f"Críticas: {resumen['criticos']}"
        )
        print(
            f"Advertencias: "
            f"{resumen['advertencias']}"
        )
        print(
            f"Informativas: "
            f"{resumen['informativos']}"
        )

        if not validaciones:
            print(
                "\nNo se detectaron problemas."
            )
            return

        for numero, validacion in enumerate(
            validaciones,
            start=1
        ):
            print(
                "\n========================================"
            )
            print(
                f"Incidencia {numero}"
            )
            print(
                f"Nivel: {validacion['nivel']}"
            )
            print(
                f"Regla: {validacion['regla']}"
            )

            if validacion.get("hoja"):
                print(
                    f"Hoja: {validacion['hoja']}"
                )

            if validacion.get("bloque") is not None:
                print(
                    f"Bloque: "
                    f"{validacion['bloque']}"
                )

            if (
                validacion.get("fila_excel")
                is not None
            ):
                print(
                    f"Fila Excel: "
                    f"{validacion['fila_excel']}"
                )

            if (
                validacion.get("puerto_switch")
                is not None
            ):
                print(
                    f"Puerto: "
                    f"{validacion['puerto_switch']}"
                )

            if validacion.get("campo"):
                print(
                    f"Campo: {validacion['campo']}"
                )

            print(
                f"Descripción: "
                f"{validacion['descripcion']}"
            )