from collections import defaultdict


class RevisorIncompletos:
    """
    Analiza los registros del inventario para identificar
    filas y bloques con información pendiente.

    Este servicio solamente consulta datos cargados
    en memoria. Nunca modifica el archivo Excel.
    """

    CAMPOS_REVISADOS = {
        "tipo": "Tipo",
        "equipo": "Equipo",
        "boca_patch": "Boca patch",
        "puerto_switch": "Puerto switch",
        "vlan": "VLAN"
    }

    def __init__(
        self,
        inventario
    ):
        self.inventario = inventario

    @staticmethod
    def valor_esta_vacio(
        valor
    ):
        """
        Indica si un valor debe considerarse vacío.
        """
        if valor is None:
            return True

        if isinstance(
            valor,
            str
        ):
            return not valor.strip()

        return False

    def obtener_campos_faltantes(
        self,
        registro
    ):
        """
        Devuelve los nombres visibles de los campos
        incompletos de un registro.
        """
        return [
            nombre_visible
            for clave, nombre_visible
            in self.CAMPOS_REVISADOS.items()
            if self.valor_esta_vacio(
                registro.get(clave)
            )
        ]

    def crear_clave_fila(
        self,
        registro
    ):
        """
        Crea una clave única para evitar que una fila
        sea agregada dos veces.
        """
        return (
            self.inventario.normalizar_texto(
                registro.get("hoja")
            ),
            registro.get("bloque"),
            registro.get("fila_excel"),
            registro.get("puerto_switch")
        )

    @staticmethod
    def crear_resultado_registro(
        registro,
        campos_faltantes
    ):
        """
        Convierte un registro en la representación
        utilizada por el reporte y el dashboard.
        """
        return {
            "hoja": registro.get("hoja"),
            "bloque": registro.get("bloque"),
            "fila_excel": registro.get(
                "fila_excel"
            ),
            "puerto_switch": registro.get(
                "puerto_switch"
            ),
            "tipo": registro.get("tipo"),
            "equipo": registro.get("equipo"),
            "boca_patch": registro.get(
                "boca_patch"
            ),
            "vlan": registro.get("vlan"),
            "campos_faltantes": campos_faltantes
        }

    def obtener_filas_incompletas(self):
        """
        Obtiene todos los registros que tienen al menos
        un campo pendiente, evitando duplicados.
        """
        resultados = []
        claves_agregadas = set()

        for registro in self.inventario.registros:
            campos_faltantes = (
                self.obtener_campos_faltantes(
                    registro
                )
            )

            if not campos_faltantes:
                continue

            resultado = (
                self.crear_resultado_registro(
                    registro=registro,
                    campos_faltantes=campos_faltantes
                )
            )

            resultados.append(
                resultado
            )

            claves_agregadas.add(
                self.crear_clave_fila(
                    resultado
                )
            )

        for registro in self.inventario.filas_incompletas:
            clave = self.crear_clave_fila(
                registro
            )

            if clave in claves_agregadas:
                continue

            campos_faltantes = (
                self.obtener_campos_faltantes(
                    registro
                )
            )

            if not campos_faltantes:
                campos_faltantes = [
                    "Tipo",
                    "Equipo",
                    "Boca patch",
                    "VLAN"
                ]

            resultado = (
                self.crear_resultado_registro(
                    registro=registro,
                    campos_faltantes=campos_faltantes
                )
            )

            resultados.append(
                resultado
            )

            claves_agregadas.add(
                clave
            )

        return sorted(
            resultados,
            key=lambda item: (
                self.inventario.normalizar_texto(
                    item.get("hoja")
                ),
                item.get("bloque") or 0,
                item.get("fila_excel") or 0
            )
        )

    def obtener_bloques_incompletos(self):
        """
        Agrupa las filas incompletas por hoja y bloque.
        """
        agrupados = defaultdict(
            list
        )

        for registro in self.obtener_filas_incompletas():
            clave = (
                registro.get("hoja"),
                registro.get("bloque")
            )

            agrupados[clave].append(
                registro
            )

        resultados = [
            {
                "hoja": hoja,
                "bloque": bloque,
                "cantidad": len(filas),
                "filas": filas
            }
            for (
                hoja,
                bloque
            ), filas in agrupados.items()
        ]

        return sorted(
            resultados,
            key=lambda item: (
                self.inventario.normalizar_texto(
                    item.get("hoja")
                ),
                item.get("bloque") or 0
            )
        )

    def contar_filas_incompletas(self):
        """
        Devuelve la cantidad total de filas incompletas.
        """
        return len(
            self.obtener_filas_incompletas()
        )

    def contar_bloques_incompletos(self):
        """
        Devuelve la cantidad de bloques que tienen
        al menos una fila incompleta.
        """
        return len(
            self.obtener_bloques_incompletos()
        )