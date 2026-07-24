import json
from datetime import datetime


class GestorHistorial:
    """
    Registra y consulta cambios realizados en NetInventory.

    Las contraseñas nunca se almacenan dentro del detalle
    del historial.
    """

    def __init__(
        self,
        base_datos
    ):
        self.base_datos = base_datos

    def registrar(
        self,
        accion,
        entidad="switch",
        ultimo_octeto=None,
        ip=None,
        ubicacion=None,
        detalle=None,
        origen="NetInventory"
    ):
        """
        Registra una entrada en el historial.
        """
        if isinstance(
            detalle,
            (
                dict,
                list,
                tuple
            )
        ):
            detalle = json.dumps(
                detalle,
                ensure_ascii=False
            )

        consulta = """
        INSERT INTO historial_cambios (
            fecha,
            accion,
            entidad,
            ultimo_octeto,
            ip,
            ubicacion,
            detalle,
            origen
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?);
        """

        valores = (
            datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
            str(accion).strip().upper(),
            str(entidad).strip().lower(),
            ultimo_octeto,
            ip,
            ubicacion,
            detalle,
            origen
        )

        with self.base_datos.conectar() as conexion:
            conexion.execute(
                consulta,
                valores
            )

            conexion.commit()

    def listar(
        self,
        limite=100,
        accion=None,
        ultimo_octeto=None
    ):
        """
        Devuelve el historial más reciente.
        """
        condiciones = []
        parametros = []

        if accion:
            condiciones.append(
                "accion = ?"
            )

            parametros.append(
                str(accion).strip().upper()
            )

        if ultimo_octeto is not None:
            condiciones.append(
                "ultimo_octeto = ?"
            )

            parametros.append(
                int(ultimo_octeto)
            )

        consulta = """
        SELECT *
        FROM historial_cambios
        """

        if condiciones:
            consulta += (
                " WHERE "
                + " AND ".join(condiciones)
            )

        consulta += """
        ORDER BY fecha DESC, id DESC
        LIMIT ?;
        """

        parametros.append(
            int(limite)
        )

        with self.base_datos.conectar() as conexion:
            filas = conexion.execute(
                consulta,
                parametros
            ).fetchall()

        return [
            dict(fila)
            for fila in filas
        ]

    def buscar(
        self,
        texto,
        limite=100
    ):
        """
        Busca en acciones, IP, ubicación, detalle y origen.
        """
        texto = str(
            texto or ""
        ).strip()

        if not texto:
            return self.listar(
                limite=limite
            )

        patron = f"%{texto}%"

        consulta = """
        SELECT *
        FROM historial_cambios
        WHERE accion LIKE ?
           OR entidad LIKE ?
           OR ip LIKE ?
           OR ubicacion LIKE ?
           OR detalle LIKE ?
           OR origen LIKE ?
           OR CAST(ultimo_octeto AS TEXT) LIKE ?
        ORDER BY fecha DESC, id DESC
        LIMIT ?;
        """

        parametros = (
            patron,
            patron,
            patron,
            patron,
            patron,
            patron,
            patron,
            int(limite)
        )

        with self.base_datos.conectar() as conexion:
            filas = conexion.execute(
                consulta,
                parametros
            ).fetchall()

        return [
            dict(fila)
            for fila in filas
        ]

    def contar(self):
        """
        Devuelve la cantidad total de eventos guardados.
        """
        consulta = """
        SELECT COUNT(*) AS total
        FROM historial_cambios;
        """

        with self.base_datos.conectar() as conexion:
            fila = conexion.execute(
                consulta
            ).fetchone()

        return fila["total"]

    def eliminar_historial_antiguo(
        self,
        conservar_ultimos=5000
    ):
        """
        Conserva solamente los eventos más recientes.

        No se ejecuta automáticamente para evitar pérdidas
        inesperadas.
        """
        conservar_ultimos = int(
            conservar_ultimos
        )

        if conservar_ultimos < 1:
            raise ValueError(
                "Debe conservarse al menos un registro."
            )

        consulta = """
        DELETE FROM historial_cambios
        WHERE id NOT IN (
            SELECT id
            FROM historial_cambios
            ORDER BY fecha DESC, id DESC
            LIMIT ?
        );
        """

        with self.base_datos.conectar() as conexion:
            cursor = conexion.execute(
                consulta,
                (conservar_ultimos,)
            )

            conexion.commit()

        return cursor.rowcount

    def convertir_detalle_visible(
        self,
        detalle
    ):
        """
        Convierte el detalle JSON a líneas legibles.
        """
        if not detalle:
            return []

        try:
            datos = json.loads(
                detalle
            )

        except (
            json.JSONDecodeError,
            TypeError
        ):
            return [
                str(detalle)
            ]

        if isinstance(datos, list):
            lineas = []

            for elemento in datos:
                if isinstance(elemento, dict):
                    campo = elemento.get(
                        "campo",
                        "Dato"
                    )

                    anterior = elemento.get(
                        "anterior"
                    )

                    nuevo = elemento.get(
                        "nuevo"
                    )

                    if elemento.get(
                        "protegido"
                    ):
                        lineas.append(
                            f"{campo}: modificado"
                        )
                    else:
                        lineas.append(
                            f"{campo}: "
                            f"{anterior or 'Sin información'}"
                            f" -> "
                            f"{nuevo or 'Sin información'}"
                        )

                else:
                    lineas.append(
                        str(elemento)
                    )

            return lineas

        if isinstance(datos, dict):
            return [
                f"{clave}: {valor}"
                for clave, valor in datos.items()
            ]

        return [
            str(datos)
        ]

    def mostrar(
        self,
        registros
    ):
        """
        Muestra registros del historial en consola.
        """
        print(
            "\n========== HISTORIAL DE CAMBIOS =========="
        )

        if not registros:
            print(
                "\nNo se encontraron eventos."
            )
            return

        print(
            f"\nEventos mostrados: {len(registros)}"
        )

        for numero, registro in enumerate(
            registros,
            start=1
        ):
            print(
                "\n========================================"
            )
            print(
                f"Evento {numero}"
            )
            print(
                f"Fecha: {registro.get('fecha')}"
            )
            print(
                f"Acción: {registro.get('accion')}"
            )
            print(
                f"Entidad: {registro.get('entidad')}"
            )

            if registro.get("ip"):
                print(
                    f"IP: {registro.get('ip')}"
                )

            if registro.get("ubicacion"):
                print(
                    "Ubicación: "
                    f"{registro.get('ubicacion')}"
                )

            print(
                "Origen: "
                f"{registro.get('origen') or 'Sin información'}"
            )

            lineas = self.convertir_detalle_visible(
                registro.get("detalle")
            )

            if lineas:
                print(
                    "Detalle:"
                )

                for linea in lineas:
                    print(
                        f"- {linea}"
                    )