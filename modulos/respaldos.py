import shutil
import sqlite3
from datetime import datetime
from pathlib import Path


class GestorRespaldos:
    """
    Administra respaldos de la base de datos SQLite.

    Permite:
    - Crear respaldos.
    - Listarlos.
    - Eliminar respaldos antiguos.
    - Restaurar una copia anterior.
    """

    def __init__(
        self,
        ruta_db,
        carpeta_respaldos="backups",
        maximo_respaldos=20
    ):
        self.ruta_db = Path(ruta_db)
        self.carpeta_respaldos = Path(
            carpeta_respaldos
        )
        self.maximo_respaldos = maximo_respaldos

        self.carpeta_respaldos.mkdir(
            parents=True,
            exist_ok=True
        )

    def generar_nombre_respaldo(
        self,
        prefijo="netinventory"
    ):
        """
        Genera un nombre único utilizando fecha,
        hora y microsegundos.
        """
        marca_tiempo = datetime.now().strftime(
            "%Y%m%d_%H%M%S_%f"
        )

        return f"{prefijo}_{marca_tiempo}.db"

    def validar_base_datos(self, ruta_db):
        """
        Comprueba que el archivo indicado sea una base
        SQLite válida y que contenga la tabla principal.
        """
        ruta_db = Path(ruta_db)

        if not ruta_db.exists():
            raise FileNotFoundError(
                "El archivo de base de datos no existe."
            )

        if ruta_db.suffix.lower() != ".db":
            raise ValueError(
                "El archivo seleccionado no tiene "
                "extensión .db."
            )

        try:
            conexion = sqlite3.connect(
                ruta_db
            )

            resultado = conexion.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'table'
                  AND name = 'accesos_switches';
                """
            ).fetchone()

            conexion.close()

        except sqlite3.DatabaseError as error:
            raise ValueError(
                "El archivo seleccionado no es una "
                "base de datos SQLite válida."
            ) from error

        if resultado is None:
            raise ValueError(
                "El respaldo no contiene la tabla "
                "accesos_switches."
            )

        return True

    def crear_respaldo(
        self,
        prefijo="netinventory"
    ):
        """
        Crea una copia de la base de datos actual.

        Devuelve la ruta generada o None si la base
        todavía no existe.
        """
        if not self.ruta_db.exists():
            return None

        self.validar_base_datos(
            self.ruta_db
        )

        nombre_respaldo = (
            self.generar_nombre_respaldo(
                prefijo
            )
        )

        ruta_respaldo = (
            self.carpeta_respaldos
            / nombre_respaldo
        )

        shutil.copy2(
            self.ruta_db,
            ruta_respaldo
        )

        self.eliminar_respaldos_antiguos()

        return ruta_respaldo

    def listar_respaldos(self):
        """
        Devuelve los respaldos del más reciente
        al más antiguo.
        """
        respaldos = list(
            self.carpeta_respaldos.glob(
                "netinventory*.db"
            )
        )

        respaldos_validos = []

        for respaldo in respaldos:
            try:
                self.validar_base_datos(
                    respaldo
                )
                respaldos_validos.append(
                    respaldo
                )

            except (
                FileNotFoundError,
                ValueError
            ):
                continue

        return sorted(
            respaldos_validos,
            key=lambda ruta: ruta.stat().st_mtime,
            reverse=True
        )

    def obtener_informacion_respaldo(
        self,
        ruta_respaldo
    ):
        """
        Devuelve información visible de un respaldo.
        """
        ruta_respaldo = Path(
            ruta_respaldo
        )

        fecha = datetime.fromtimestamp(
            ruta_respaldo.stat().st_mtime
        )

        return {
            "ruta": ruta_respaldo,
            "nombre": ruta_respaldo.name,
            "fecha": fecha.strftime(
                "%d-%m-%Y %H:%M:%S"
            ),
            "tamano_bytes": (
                ruta_respaldo.stat().st_size
            ),
            "tamano_kb": round(
                ruta_respaldo.stat().st_size / 1024,
                2
            )
        }

    def obtener_respaldo_por_indice(
        self,
        indice
    ):
        """
        Obtiene un respaldo mediante el número
        mostrado en la interfaz.
        """
        respaldos = self.listar_respaldos()

        try:
            indice = int(
                str(indice).strip()
            )

        except (ValueError, TypeError) as error:
            raise ValueError(
                "La opción debe ser numérica."
            ) from error

        if indice < 1 or indice > len(respaldos):
            raise ValueError(
                "La opción seleccionada no existe."
            )

        return respaldos[indice - 1]

    def eliminar_respaldos_antiguos(self):
        """
        Conserva únicamente la cantidad máxima
        configurada de respaldos.
        """
        respaldos = self.listar_respaldos()

        respaldos_sobrantes = respaldos[
            self.maximo_respaldos:
        ]

        for respaldo in respaldos_sobrantes:
            try:
                respaldo.unlink()

            except OSError:
                continue

    def obtener_ultimo_respaldo(self):
        """
        Devuelve el respaldo más reciente.
        """
        respaldos = self.listar_respaldos()

        if not respaldos:
            return None

        return respaldos[0]

    def restaurar_respaldo(
        self,
        ruta_respaldo
    ):
        """
        Restaura un respaldo sobre la base actual.

        Antes de reemplazarla, crea una copia especial
        del estado existente.
        """
        ruta_respaldo = Path(
            ruta_respaldo
        )

        self.validar_base_datos(
            ruta_respaldo
        )

        respaldo_estado_actual = None

        if self.ruta_db.exists():
            respaldo_estado_actual = (
                self.crear_respaldo(
                    prefijo=(
                        "netinventory_"
                        "antes_restauracion"
                    )
                )
            )

        self.ruta_db.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        archivo_temporal = (
            self.ruta_db.parent
            / "netinventory_restauracion_temp.db"
        )

        try:
            shutil.copy2(
                ruta_respaldo,
                archivo_temporal
            )

            self.validar_base_datos(
                archivo_temporal
            )

            archivo_temporal.replace(
                self.ruta_db
            )

        except Exception:
            if archivo_temporal.exists():
                archivo_temporal.unlink()

            raise

        return {
            "restaurado": ruta_respaldo,
            "respaldo_estado_actual": (
                respaldo_estado_actual
            )
        }