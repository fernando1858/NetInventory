from datetime import datetime


class CentroSaludRed:
    """
    Presenta una visión ejecutiva del estado de NetInventory.

    Combina:
    - Consistencia de la topología.
    - Cobertura del inventario.
    - Disponibilidad SNMP.
    - Diagnóstico correlacionado.

    Todas las operaciones son de solo lectura.
    """

    def __init__(
        self,
        gestor_topologia,
        analizador_red,
        centro_snmp
    ):
        self.gestor_topologia = gestor_topologia
        self.analizador_red = analizador_red
        self.centro_snmp = centro_snmp

        self.ultimo_resultado = None

    @staticmethod
    def porcentaje(
        parte,
        total
    ):
        if not total:
            return 0.0

        return round(
            parte / total * 100,
            1
        )

    def snmp_disponible(self):
        """
        Comprueba si el Centro SNMP real está disponible.
        """
        return (
            hasattr(
                self.centro_snmp,
                "descubridor"
            )
            and hasattr(
                self.centro_snmp,
                "motor_diagnostico"
            )
        )

    def ejecutar_comprobacion_snmp(self):
        """
        Ejecuta una comprobación nueva y correlaciona
        los resultados con la topología.
        """
        if not self.snmp_disponible():
            return {
                "disponible": False,
                "descubrimiento": None,
                "diagnostico": None,
                "resumen_descubrimiento": None,
                "resumen_diagnostico": None
            }

        descubrimiento = (
            self.centro_snmp.descubridor.ejecutar(
                notificar_progreso=(
                    self.centro_snmp.notificar_progreso
                )
            )
        )

        diagnostico = (
            self.centro_snmp.motor_diagnostico.analizar(
                descubrimiento
            )
        )

        self.centro_snmp.ultimo_descubrimiento = (
            descubrimiento
        )

        self.centro_snmp\
            .ultimo_diagnostico_correlacionado = (
                diagnostico
            )

        return {
            "disponible": True,
            "descubrimiento": descubrimiento,
            "diagnostico": diagnostico,
            "resumen_descubrimiento": (
                descubrimiento.obtener_resumen()
            ),
            "resumen_diagnostico": (
                diagnostico.obtener_resumen()
            )
        }

    def construir_estado(
        self,
        ejecutar_snmp=True
    ):
        """
        Construye el estado general de la red.
        """
        topologia = (
            self.gestor_topologia.validar_topologia()
        )

        cobertura = (
            self.analizador_red
            .auditar_cobertura_global()
        )

        if ejecutar_snmp:
            snmp = self.ejecutar_comprobacion_snmp()
        else:
            snmp = {
                "disponible": False,
                "descubrimiento": None,
                "diagnostico": None,
                "resumen_descubrimiento": None,
                "resumen_diagnostico": None
            }

        estado_general = self.calcular_estado_general(
            topologia=topologia,
            cobertura=cobertura,
            snmp=snmp
        )

        resultado = {
            "fecha": datetime.now(),
            "topologia": topologia,
            "cobertura": cobertura,
            "snmp": snmp,
            "estado_general": estado_general
        }

        self.ultimo_resultado = resultado

        return resultado

    def calcular_estado_general(
        self,
        topologia,
        cobertura,
        snmp
    ):
        """
        Determina un estado ejecutivo sin confundir una
        falla SNMP con una caída física confirmada.
        """
        problemas_topologia = (
            len(topologia["ciclos"])
            + len(topologia["padres_invalidos"])
        )

        if problemas_topologia:
            return {
                "nivel": "CRÍTICO",
                "mensaje": (
                    "La topología contiene errores "
                    "estructurales."
                )
            }

        if snmp["disponible"]:
            resumen = snmp["resumen_diagnostico"]

            if (
                resumen["prioridad_critica"] > 0
                or resumen["fallas_locales_probables"] > 0
            ):
                return {
                    "nivel": "CRÍTICO",
                    "mensaje": (
                        "Existen incidencias críticas o "
                        "fallas locales probables."
                    )
                }

            if (
                resumen["sin_respuesta"] > 0
                or resumen["posiblemente_afectados"] > 0
            ):
                return {
                    "nivel": "OBSERVACIÓN",
                    "mensaje": (
                        "La red presenta equipos sin "
                        "respuesta o estados por comprobar."
                    )
                }

        if cobertura["porcentaje"] < 100:
            return {
                "nivel": "OBSERVACIÓN",
                "mensaje": (
                    "La red está operativa, pero la "
                    "cobertura del inventario es parcial."
                )
            }

        return {
            "nivel": "NORMAL",
            "mensaje": (
                "No se detectaron observaciones relevantes."
            )
        }

    @staticmethod
    def indicador(
        condicion,
        texto_ok,
        texto_error
    ):
        return (
            f"[OK] {texto_ok}"
            if condicion
            else f"[AVISO] {texto_error}"
        )

    def mostrar_estado(
        self,
        resultado
    ):
        """
        Muestra el Centro de Salud en consola.
        """
        topologia = resultado["topologia"]
        cobertura = resultado["cobertura"]
        snmp = resultado["snmp"]
        estado = resultado["estado_general"]

        print("\n" + "=" * 78)
        print("CENTRO DE SALUD DE LA RED".center(78))
        print("=" * 78)

        print(
            "\nEstado general: "
            f"{estado['nivel']}"
        )
        print(
            f"Detalle: {estado['mensaje']}"
        )
        print(
            "Última comprobación: "
            f"{resultado['fecha'].strftime('%d/%m/%Y %H:%M:%S')}"
        )

        print("\n" + "-" * 78)
        print("TOPOLOGÍA")
        print("-" * 78)

        print(
            f"Switches registrados: "
            f"{topologia['total_switches']}"
        )
        print(
            self.indicador(
                not topologia["ciclos"],
                "Sin ciclos detectados.",
                f"Ciclos detectados: "
                f"{len(topologia['ciclos'])}"
            )
        )
        print(
            self.indicador(
                not topologia["padres_invalidos"],
                "Sin padres inválidos.",
                "Existen padres inválidos: "
                f"{len(topologia['padres_invalidos'])}"
            )
        )
        print(
            self.indicador(
                not topologia["sin_padre"],
                "Todos los switches no Core tienen padre.",
                "Switches sin padre: "
                f"{len(topologia['sin_padre'])}"
            )
        )
        print(
            self.indicador(
                not topologia["sin_clasificar"],
                "Todos los switches están clasificados.",
                "Switches sin clasificar: "
                f"{len(topologia['sin_clasificar'])}"
            )
        )

        print("\n" + "-" * 78)
        print("COBERTURA DEL INVENTARIO")
        print("-" * 78)

        print(
            f"Switches cubiertos: "
            f"{len(cobertura['cubiertos'])} de "
            f"{cobertura['total']}"
        )
        print(
            f"Cobertura: {cobertura['porcentaje']} %"
        )
        print(
            "Sin relación con Excel: "
            f"{len(cobertura['sin_relacion'])}"
        )
        print(
            "Relación inválida: "
            f"{len(cobertura['relaciones_invalidas'])}"
        )
        print(
            "Relación sin registros: "
            f"{len(cobertura['bloques_sin_registros'])}"
        )

        print("\n" + "-" * 78)
        print("ESTADO SNMP Y DIAGNÓSTICO")
        print("-" * 78)

        if not snmp["disponible"]:
            print(
                "[AVISO] SNMP no está disponible en esta "
                "ejecución."
            )
        else:
            descubrimiento = (
                snmp["resumen_descubrimiento"]
            )
            diagnostico = (
                snmp["resumen_diagnostico"]
            )

            print(
                "Respondieron por SNMP: "
                f"{descubrimiento['respondieron']} de "
                f"{descubrimiento['revisados']}"
            )
            print(
                "Solo ping, sin SNMP: "
                f"{descubrimiento.get('solo_ping', 0)}"
            )
            print(
                "Sin respuesta SNMP: "
                f"{descubrimiento['sin_respuesta']}"
            )
            print(
                "Operativos según correlación: "
                f"{diagnostico['operativos']}"
            )
            print(
                "Fallas locales probables: "
                f"{diagnostico['fallas_locales_probables']}"
            )
            print(
                "Posiblemente afectados: "
                f"{diagnostico['posiblemente_afectados']}"
            )
            print(
                "Prioridad crítica: "
                f"{diagnostico['prioridad_critica']}"
            )
            print(
                "Prioridad alta: "
                f"{diagnostico['prioridad_alta']}"
            )

        print("\n" + "-" * 78)
        print("OBSERVACIONES PRINCIPALES")
        print("-" * 78)

        observaciones = []

        if topologia["sin_padre"]:
            observaciones.append(
                f"{len(topologia['sin_padre'])} switches "
                "sin padre documentado."
            )

        if topologia["sin_clasificar"]:
            observaciones.append(
                f"{len(topologia['sin_clasificar'])} switches "
                "sin clasificación."
            )

        pendientes_cobertura = (
            len(cobertura["sin_relacion"])
            + len(cobertura["relaciones_invalidas"])
            + len(cobertura["bloques_sin_registros"])
        )

        if pendientes_cobertura:
            observaciones.append(
                f"{pendientes_cobertura} switches fuera del "
                "conteo completo de inventario."
            )

        if snmp["disponible"]:
            resumen = snmp["resumen_diagnostico"]

            if resumen["sin_respuesta"]:
                observaciones.append(
                    f"{resumen['sin_respuesta']} switches "
                    "sin respuesta en la comprobación."
                )

            if resumen["fallas_locales_probables"]:
                observaciones.append(
                    f"{resumen['fallas_locales_probables']} "
                    "fallas locales probables."
                )

        if observaciones:
            for numero, observacion in enumerate(
                observaciones,
                start=1
            ):
                print(
                    f"{numero}. {observacion}"
                )
        else:
            print(
                "[OK] No existen observaciones pendientes."
            )

    def ejecutar(self):
        """
        Ejecuta una comprobación completa y muestra el estado.
        """
        print(
            "\nAnalizando topología, cobertura y estado SNMP..."
        )

        try:
            resultado = self.construir_estado(
                ejecutar_snmp=True
            )

        except Exception as error:
            print(
                "\n[ERROR] No fue posible completar el "
                "Centro de Salud."
            )
            print(
                f"Detalle: {error}"
            )
            return

        self.mostrar_estado(
            resultado
        )