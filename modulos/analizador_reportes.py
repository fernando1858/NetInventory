from collections import Counter, defaultdict


class AnalizadorReportes:
    """
    Calcula indicadores, estadísticas y hallazgos para
    el reporte administrativo de NetInventory.

    Este módulo solamente consulta información cargada
    en memoria. No modifica el Excel ni la base SQLite.
    """

    def __init__(
        self,
        inventario,
        gestor_relaciones,
        validador_inventario
    ):
        self.inventario = inventario
        self.gestor_relaciones = gestor_relaciones
        self.validador_inventario = validador_inventario

    @staticmethod
    def valor_esta_vacio(valor):
        """
        Determina si un valor debe considerarse vacío.
        """
        if valor is None:
            return True

        if isinstance(valor, str):
            return not valor.strip()

        return False

    def normalizar(self, valor):
        """
        Normaliza texto utilizando la lógica del inventario.
        """
        return self.inventario.normalizar_texto(
            valor
        )

    def obtener_registros(self):
        """
        Devuelve los registros cargados del inventario.
        """
        return self.inventario.registros

    def registro_tiene_equipo(self, registro):
        """
        Determina si un puerto tiene un equipo documentado
        y no está marcado como disponible.
        """
        equipo = registro.get("equipo")

        if self.valor_esta_vacio(equipo):
            return False

        if self.inventario.equipo_esta_disponible(
            equipo
        ):
            return False

        return True

    def registro_esta_disponible(self, registro):
        """
        Determina si un puerto está marcado explícitamente
        como disponible.
        """
        return self.inventario.equipo_esta_disponible(
            registro.get("equipo")
        )

    @staticmethod
    def calcular_porcentaje(
        cantidad,
        total
    ):
        """
        Calcula un porcentaje evitando divisiones por cero.
        """
        if not total:
            return 0.0

        return round(
            cantidad * 100 / total,
            2
        )

    def obtener_indicadores_generales(self):
        """
        Calcula los indicadores principales del inventario.
        """
        registros = self.obtener_registros()

        total_registros = len(
            registros
        )

        puertos_ocupados = sum(
            self.registro_tiene_equipo(
                registro
            )
            for registro in registros
        )

        puertos_disponibles = sum(
            self.registro_esta_disponible(
                registro
            )
            for registro in registros
        )

        puertos_sin_definir = max(
            total_registros
            - puertos_ocupados
            - puertos_disponibles,
            0
        )

        registros_con_vlan = sum(
            not self.valor_esta_vacio(
                registro.get("vlan")
            )
            for registro in registros
        )

        registros_sin_vlan = (
            total_registros
            - registros_con_vlan
        )

        hojas = {
            registro.get("hoja")
            for registro in registros
            if not self.valor_esta_vacio(
                registro.get("hoja")
            )
        }

        bloques = {
            (
                registro.get("hoja"),
                registro.get("bloque")
            )
            for registro in registros
            if (
                not self.valor_esta_vacio(
                    registro.get("hoja")
                )
                and registro.get("bloque") is not None
            )
        }

        relaciones = (
            self.gestor_relaciones
            .validar_relaciones()
        )

        validaciones = (
            self.validador_inventario
            .ejecutar_validacion()
        )

        resumen_validaciones = (
            self.validador_inventario
            .obtener_resumen(
                validaciones
            )
        )

        return {
            "total_registros": total_registros,
            "puertos_ocupados": puertos_ocupados,
            "puertos_disponibles": puertos_disponibles,
            "puertos_sin_definir": puertos_sin_definir,
            "porcentaje_ocupacion": (
                self.calcular_porcentaje(
                    puertos_ocupados,
                    total_registros
                )
            ),
            "porcentaje_disponibilidad": (
                self.calcular_porcentaje(
                    puertos_disponibles,
                    total_registros
                )
            ),
            "registros_con_vlan": registros_con_vlan,
            "registros_sin_vlan": registros_sin_vlan,
            "porcentaje_con_vlan": (
                self.calcular_porcentaje(
                    registros_con_vlan,
                    total_registros
                )
            ),
            "hojas_procesadas": len(
                hojas
            ),
            "bloques_detectados": len(
                bloques
            ),
            "relaciones_validas": len(
                relaciones.get(
                    "validas",
                    []
                )
            ),
            "relaciones_invalidas": len(
                relaciones.get(
                    "invalidas",
                    []
                )
            ),
            "switches_sin_relacion": len(
                relaciones.get(
                    "sin_relacion",
                    []
                )
            ),
            "validaciones_totales": (
                resumen_validaciones.get(
                    "total",
                    0
                )
            ),
            "validaciones_criticas": (
                resumen_validaciones.get(
                    "criticos",
                    0
                )
            ),
            "advertencias": (
                resumen_validaciones.get(
                    "advertencias",
                    0
                )
            ),
            "informativos": (
                resumen_validaciones.get(
                    "informativos",
                    0
                )
            )
        }

    def obtener_distribucion_tipos(self):
        """
        Agrupa los registros por tipo de equipo.
        """
        contador = Counter()

        for registro in self.obtener_registros():
            tipo = registro.get("tipo")

            if self.valor_esta_vacio(tipo):
                tipo = "Sin tipo"

            contador[
                str(tipo).strip()
            ] += 1

        return [
            {
                "tipo": tipo,
                "cantidad": cantidad
            }
            for tipo, cantidad in sorted(
                contador.items(),
                key=lambda item: (
                    -item[1],
                    item[0]
                )
            )
        ]

    def obtener_distribucion_vlan(self):
        """
        Agrupa los registros por VLAN.
        """
        contador = Counter()

        for registro in self.obtener_registros():
            vlan = registro.get("vlan")

            if self.valor_esta_vacio(vlan):
                vlan_visible = "Sin VLAN"
            else:
                vlan_visible = str(
                    vlan
                ).strip()

            contador[
                vlan_visible
            ] += 1

        def clave_orden(item):
            vlan, _cantidad = item

            try:
                numero_vlan = int(
                    float(vlan)
                )

                return (
                    0,
                    numero_vlan
                )

            except (
                ValueError,
                TypeError
            ):
                return (
                    1,
                    str(vlan)
                )

        return [
            {
                "vlan": vlan,
                "cantidad": cantidad
            }
            for vlan, cantidad in sorted(
                contador.items(),
                key=clave_orden
            )
        ]

    def obtener_analisis_por_sector(self):
        """
        Calcula ocupación, disponibilidad y documentación
        de VLAN para cada hoja o sector.
        """
        sectores = defaultdict(
            lambda: {
                "total": 0,
                "ocupados": 0,
                "disponibles": 0,
                "sin_definir": 0,
                "con_vlan": 0,
                "sin_vlan": 0
            }
        )

        for registro in self.obtener_registros():
            hoja = (
                registro.get("hoja")
                or "Sin hoja"
            )

            datos = sectores[
                hoja
            ]

            datos["total"] += 1

            if self.registro_tiene_equipo(
                registro
            ):
                datos["ocupados"] += 1

            elif self.registro_esta_disponible(
                registro
            ):
                datos["disponibles"] += 1

            else:
                datos["sin_definir"] += 1

            if self.valor_esta_vacio(
                registro.get("vlan")
            ):
                datos["sin_vlan"] += 1

            else:
                datos["con_vlan"] += 1

        resultados = []

        for hoja, datos in sectores.items():
            total = datos["total"]

            resultados.append(
                {
                    "hoja": hoja,
                    "total": total,
                    "ocupados": datos[
                        "ocupados"
                    ],
                    "disponibles": datos[
                        "disponibles"
                    ],
                    "sin_definir": datos[
                        "sin_definir"
                    ],
                    "con_vlan": datos[
                        "con_vlan"
                    ],
                    "sin_vlan": datos[
                        "sin_vlan"
                    ],
                    "ocupacion_porcentaje": (
                        self.calcular_porcentaje(
                            datos["ocupados"],
                            total
                        )
                    ),
                    "disponibilidad_porcentaje": (
                        self.calcular_porcentaje(
                            datos["disponibles"],
                            total
                        )
                    ),
                    "documentacion_vlan_porcentaje": (
                        self.calcular_porcentaje(
                            datos["con_vlan"],
                            total
                        )
                    )
                }
            )

        return sorted(
            resultados,
            key=lambda item: (
                -item["ocupacion_porcentaje"],
                self.normalizar(
                    item["hoja"]
                )
            )
        )

    def obtener_validaciones_por_sector(self):
        """
        Agrupa las incidencias detectadas por hoja.
        """
        validaciones = (
            self.validador_inventario
            .ejecutar_validacion()
        )

        sectores = defaultdict(
            lambda: {
                "criticas": 0,
                "advertencias": 0,
                "informativas": 0,
                "total": 0
            }
        )

        for validacion in validaciones:
            hoja = (
                validacion.get("hoja")
                or "Sin sector asociado"
            )

            nivel = validacion.get(
                "nivel"
            )

            sectores[
                hoja
            ]["total"] += 1

            if nivel == "CRÍTICO":
                sectores[
                    hoja
                ]["criticas"] += 1

            elif nivel == "ADVERTENCIA":
                sectores[
                    hoja
                ]["advertencias"] += 1

            else:
                sectores[
                    hoja
                ]["informativas"] += 1

        return sorted(
            [
                {
                    "hoja": hoja,
                    **datos
                }
                for hoja, datos in sectores.items()
            ],
            key=lambda item: (
                -item["criticas"],
                -item["advertencias"],
                -item["total"],
                self.normalizar(
                    item["hoja"]
                )
            )
        )

    def obtener_analisis_por_switch(self):
        """
        Calcula la capacidad documentada de cada switch
        almacenado en la base de datos.

        La relación con hoja y bloque permite asociar los
        puertos documentados en el Excel con el switch.
        """
        resultados = []

        switches = (
            self.gestor_relaciones
            .gestor_accesos
            .listar_todos()
        )

        bloques_existentes = (
            self.gestor_relaciones
            .obtener_bloques_existentes()
        )

        for switch in switches:
            hoja = switch.get(
                "hoja_excel"
            )

            bloque = switch.get(
                "bloque_excel"
            )

            registros_switch = []

            if (
                hoja is not None
                and bloque is not None
            ):
                registros_switch = [
                    registro
                    for registro
                    in self.obtener_registros()
                    if (
                        self.normalizar(
                            registro.get("hoja")
                        )
                        == self.normalizar(
                            hoja
                        )
                        and registro.get("bloque")
                        == bloque
                    )
                ]

            total = len(
                registros_switch
            )

            ocupados = sum(
                self.registro_tiene_equipo(
                    registro
                )
                for registro in registros_switch
            )

            disponibles = sum(
                self.registro_esta_disponible(
                    registro
                )
                for registro in registros_switch
            )

            sin_definir = max(
                total
                - ocupados
                - disponibles,
                0
            )

            con_vlan = sum(
                not self.valor_esta_vacio(
                    registro.get("vlan")
                )
                for registro in registros_switch
            )

            sin_vlan = (
                total
                - con_vlan
            )

            if (
                hoja is None
                or bloque is None
            ):
                estado_relacion = (
                    "Sin relación"
                )

            else:
                clave_bloque = (
                    self.normalizar(
                        hoja
                    ),
                    bloque
                )

                if clave_bloque in bloques_existentes:
                    estado_relacion = (
                        "Relación válida"
                    )
                else:
                    estado_relacion = (
                        "Relación inválida"
                    )

            resultados.append(
                {
                    "ultimo_octeto": switch.get(
                        "ultimo_octeto"
                    ),
                    "ip": switch.get("ip"),
                    "ubicacion": switch.get(
                        "ubicacion"
                    ),
                    "marca": switch.get(
                        "marca"
                    ),
                    "modelo": switch.get(
                        "modelo"
                    ),
                    "mac": switch.get("mac"),
                    "hoja": hoja,
                    "bloque": bloque,
                    "estado_relacion": (
                        estado_relacion
                    ),
                    "total_puertos": total,
                    "ocupados": ocupados,
                    "disponibles": disponibles,
                    "sin_definir": sin_definir,
                    "con_vlan": con_vlan,
                    "sin_vlan": sin_vlan,
                    "ocupacion_porcentaje": (
                        self.calcular_porcentaje(
                            ocupados,
                            total
                        )
                    ),
                    "disponibilidad_porcentaje": (
                        self.calcular_porcentaje(
                            disponibles,
                            total
                        )
                    ),
                    "cobertura_vlan_porcentaje": (
                        self.calcular_porcentaje(
                            con_vlan,
                            total
                        )
                    )
                }
            )

        return sorted(
            resultados,
            key=lambda item: (
                item.get("ultimo_octeto")
                if item.get("ultimo_octeto")
                is not None
                else 999
            )
        )

    def obtener_switches_con_capacidad_critica(
        self,
        umbral_disponibilidad=5
    ):
        """
        Devuelve switches relacionados cuya disponibilidad
        es igual o inferior al umbral indicado.
        """
        return [
            switch
            for switch
            in self.obtener_analisis_por_switch()
            if (
                switch["total_puertos"] > 0
                and switch[
                    "disponibilidad_porcentaje"
                ] <= umbral_disponibilidad
            )
        ]

    def obtener_switches_sin_documentacion(self):
        """
        Devuelve switches que no tienen puertos asociados
        en el inventario.
        """
        return [
            switch
            for switch
            in self.obtener_analisis_por_switch()
            if switch["total_puertos"] == 0
        ]

    def obtener_principales_hallazgos(self):
        """
        Genera conclusiones automáticas basadas en
        los datos actuales del inventario.
        """
        indicadores = (
            self.obtener_indicadores_generales()
        )

        sectores = (
            self.obtener_analisis_por_sector()
        )

        incidencias_sector = (
            self.obtener_validaciones_por_sector()
        )

        switches_criticos = (
            self.obtener_switches_con_capacidad_critica()
        )

        switches_sin_documentacion = (
            self.obtener_switches_sin_documentacion()
        )

        hallazgos = []

        total = indicadores[
            "total_registros"
        ]

        if total:
            hallazgos.append(
                "El inventario contiene "
                f"{total} puertos documentados en "
                f"{indicadores['hojas_procesadas']} "
                "sectores."
            )

            hallazgos.append(
                "La ocupación general estimada es de "
                f"{indicadores['porcentaje_ocupacion']:.2f} %, "
                "mientras que la disponibilidad documentada "
                "es de "
                f"{indicadores['porcentaje_disponibilidad']:.2f} %."
            )

            hallazgos.append(
                "El "
                f"{indicadores['porcentaje_con_vlan']:.2f} % "
                "de los registros posee una VLAN documentada."
            )

        if sectores:
            sector_mayor_ocupacion = max(
                sectores,
                key=lambda item: (
                    item[
                        "ocupacion_porcentaje"
                    ]
                )
            )

            sector_mayor_disponibilidad = max(
                sectores,
                key=lambda item: (
                    item[
                        "disponibilidad_porcentaje"
                    ]
                )
            )

            hallazgos.append(
                "El sector con mayor ocupación documentada "
                f"es {sector_mayor_ocupacion['hoja']} "
                "con "
                f"{sector_mayor_ocupacion['ocupacion_porcentaje']:.2f} %."
            )

            hallazgos.append(
                "El sector con mayor disponibilidad "
                f"documentada es "
                f"{sector_mayor_disponibilidad['hoja']} "
                "con "
                f"{sector_mayor_disponibilidad['disponibilidad_porcentaje']:.2f} %."
            )

        if indicadores[
            "validaciones_criticas"
        ]:
            hallazgos.append(
                "Se detectaron "
                f"{indicadores['validaciones_criticas']} "
                "incidencias críticas que deberían "
                "revisarse prioritariamente."
            )

        else:
            hallazgos.append(
                "No se detectaron incidencias críticas "
                "en la validación actual."
            )

        if incidencias_sector:
            sector_mas_incidencias = (
                incidencias_sector[0]
            )

            hallazgos.append(
                "El sector con más incidencias registradas "
                f"es {sector_mas_incidencias['hoja']} "
                "con "
                f"{sector_mas_incidencias['total']} "
                "observaciones."
            )

        if indicadores[
            "switches_sin_relacion"
        ]:
            hallazgos.append(
                "Existen "
                f"{indicadores['switches_sin_relacion']} "
                "switches sin una relación configurada "
                "con un bloque del inventario."
            )

        else:
            hallazgos.append(
                "Todos los switches registrados poseen "
                "una relación configurada."
            )

        if indicadores[
            "relaciones_invalidas"
        ]:
            hallazgos.append(
                "Hay "
                f"{indicadores['relaciones_invalidas']} "
                "relaciones inválidas entre switches "
                "y bloques."
            )

        if switches_criticos:
            switch_critico = sorted(
                switches_criticos,
                key=lambda switch: (
                    switch[
                        "disponibilidad_porcentaje"
                    ],
                    switch.get("ultimo_octeto")
                    or 999
                )
            )[0]

            hallazgos.append(
                "El switch "
                f"{switch_critico['ip']} "
                f"({switch_critico['ubicacion'] or 'sin ubicación'}) "
                "presenta capacidad crítica, con "
                f"{switch_critico['disponibilidad_porcentaje']:.2f} % "
                "de puertos disponibles."
            )

        if switches_sin_documentacion:
            hallazgos.append(
                "Existen "
                f"{len(switches_sin_documentacion)} "
                "switches registrados sin puertos "
                "documentados o sin una relación válida."
            )

        return hallazgos

    def obtener_recomendaciones(self):
        """
        Genera recomendaciones de administración basadas
        en los indicadores actuales.
        """
        indicadores = (
            self.obtener_indicadores_generales()
        )

        switches_criticos = (
            self.obtener_switches_con_capacidad_critica()
        )

        switches_sin_documentacion = (
            self.obtener_switches_sin_documentacion()
        )

        recomendaciones = []

        if indicadores[
            "validaciones_criticas"
        ]:
            recomendaciones.append(
                "Corregir primero las incidencias críticas "
                "indicadas en la hoja Validaciones."
            )

        if indicadores[
            "registros_sin_vlan"
        ]:
            recomendaciones.append(
                "Completar la documentación de VLAN en los "
                f"{indicadores['registros_sin_vlan']} "
                "registros pendientes."
            )

        if indicadores[
            "switches_sin_relacion"
        ]:
            recomendaciones.append(
                "Relacionar los switches pendientes con "
                "sus respectivos bloques del inventario."
            )

        if indicadores[
            "relaciones_invalidas"
        ]:
            recomendaciones.append(
                "Validar o eliminar las relaciones que "
                "apuntan a hojas o bloques inexistentes."
            )

        if switches_criticos:
            recomendaciones.append(
                "Revisar la capacidad de los switches "
                "marcados como críticos antes de conectar "
                "nuevos equipos."
            )

        if switches_sin_documentacion:
            recomendaciones.append(
                "Completar o corregir las relaciones de los "
                "switches que no poseen puertos documentados."
            )

        if indicadores[
            "porcentaje_disponibilidad"
        ] < 5:
            recomendaciones.append(
                "La disponibilidad general de puertos es "
                "baja; conviene planificar capacidad antes "
                "de ampliar la red."
            )

        if not recomendaciones:
            recomendaciones.append(
                "Mantener actualizado el Excel oficial y "
                "generar reportes periódicos para conservar "
                "la trazabilidad del inventario."
            )

        return recomendaciones