import sqlite3
from pathlib import Path


class BaseDatos:
    """
    Administra la conexión, estructura y migraciones
    de la base de datos SQLite de NetInventory.

    Las migraciones agregan columnas nuevas sin eliminar
    ni modificar los datos existentes.
    """

    def __init__(
        self,
        ruta_db="datos/netinventory.db"
    ):
        self.ruta_db = Path(
            ruta_db
        )

        self.ruta_db.parent.mkdir(
            parents=True,
            exist_ok=True
        )

    # ======================================================
    # CONEXIÓN
    # ======================================================

    def conectar(self):
        """
        Crea una conexión configurada para acceder
        a las columnas mediante sus nombres.

        También habilita las claves foráneas de SQLite.
        """
        conexion = sqlite3.connect(
            self.ruta_db
        )

        conexion.row_factory = sqlite3.Row

        conexion.execute(
            "PRAGMA foreign_keys = ON;"
        )

        return conexion

    # ======================================================
    # CREACIÓN GENERAL
    # ======================================================

    def crear_tablas(self):
        """
        Crea todas las tablas necesarias y ejecuta las
        migraciones compatibles con bases anteriores.
        """
        consulta_switches = """
        CREATE TABLE IF NOT EXISTS accesos_switches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            ultimo_octeto INTEGER,
            nombre TEXT NOT NULL,
            ip TEXT,
            mac TEXT,
            marca TEXT,
            modelo TEXT,
            usuario TEXT,
            password TEXT,
            ubicacion TEXT,
            observaciones TEXT,

            hoja_excel TEXT,
            bloque_excel INTEGER,

            nombre_logico TEXT,
            rol TEXT DEFAULT 'NO DEFINIDO',
            criticidad TEXT DEFAULT 'NO DEFINIDA',

            switch_padre_id INTEGER,
            puerto_subida TEXT,
            tecnologia_subida TEXT,

            tiene_poe INTEGER,
            tiene_ups INTEGER,

            notas_topologia TEXT,

            fecha_creacion TEXT
                DEFAULT CURRENT_TIMESTAMP,

            fecha_actualizacion TEXT
                DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (
                switch_padre_id
            )
            REFERENCES accesos_switches(id)
            ON DELETE SET NULL
            ON UPDATE CASCADE
        );
        """

        consulta_historial = """
        CREATE TABLE IF NOT EXISTS historial_cambios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            fecha TEXT NOT NULL
                DEFAULT CURRENT_TIMESTAMP,

            accion TEXT NOT NULL,
            entidad TEXT NOT NULL,

            ultimo_octeto INTEGER,
            ip TEXT,
            ubicacion TEXT,

            detalle TEXT,
            origen TEXT
        );
        """

        consulta_enlaces = """
        CREATE TABLE IF NOT EXISTS enlaces_red (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            switch_padre_id INTEGER NOT NULL,
            switch_hijo_id INTEGER NOT NULL UNIQUE,
            puerto_padre TEXT,
            puerto_hijo TEXT,
            tecnologia TEXT DEFAULT 'NO DEFINIDA',
            velocidad_esperada_mbps INTEGER,
            observaciones TEXT,
            fecha_creacion TEXT DEFAULT CURRENT_TIMESTAMP,
            fecha_actualizacion TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (switch_padre_id)
                REFERENCES accesos_switches(id)
                ON DELETE CASCADE
                ON UPDATE CASCADE,
            FOREIGN KEY (switch_hijo_id)
                REFERENCES accesos_switches(id)
                ON DELETE CASCADE
                ON UPDATE CASCADE,
            CHECK (switch_padre_id <> switch_hijo_id)
        );
        """

        with self.conectar() as conexion:
            conexion.execute(
                consulta_switches
            )

            conexion.execute(
                consulta_historial
            )

            conexion.execute(
                consulta_enlaces
            )

            conexion.commit()

        self.actualizar_estructura_switches()
        self.actualizar_estructura_historial()
        self.completar_octetos_existentes()
        self.completar_valores_topologia()
        self.limpiar_padres_invalidos()
        self.migrar_relaciones_a_enlaces()
        self.crear_indices()

    # ======================================================
    # CONSULTA DE ESTRUCTURA
    # ======================================================

    def obtener_columnas_tabla(
        self,
        nombre_tabla
    ):
        """
        Obtiene los nombres de las columnas existentes
        en una tabla.
        """
        consulta = (
            f"PRAGMA table_info({nombre_tabla});"
        )

        with self.conectar() as conexion:
            filas = conexion.execute(
                consulta
            ).fetchall()

        return {
            fila["name"]
            for fila in filas
        }

    def columna_existe(
        self,
        tabla,
        columna
    ):
        """
        Indica si una columna existe en una tabla.
        """
        columnas = self.obtener_columnas_tabla(
            tabla
        )

        return columna in columnas

    def agregar_columna_si_falta(
        self,
        tabla,
        columna,
        definicion
    ):
        """
        Agrega una columna conservando todos los datos
        existentes.

        SQLite no permite agregar mediante ALTER TABLE
        una clave foránea completa sobre una tabla creada,
        por lo que switch_padre_id se valida también desde
        la lógica de NetInventory.
        """
        if self.columna_existe(
            tabla,
            columna
        ):
            return False

        consulta = (
            f"ALTER TABLE {tabla} "
            f"ADD COLUMN {columna} {definicion};"
        )

        with self.conectar() as conexion:
            conexion.execute(
                consulta
            )

            conexion.commit()

        return True

    # ======================================================
    # MIGRACIÓN DE SWITCHES
    # ======================================================

    def actualizar_estructura_switches(self):
        """
        Mantiene compatibilidad con bases creadas en
        versiones anteriores de NetInventory.

        Agrega tanto las columnas tradicionales como los
        nuevos datos de topología.
        """
        columnas_necesarias = {
            # Campos anteriores
            "ultimo_octeto": "INTEGER",
            "hoja_excel": "TEXT",
            "bloque_excel": "INTEGER",
            "observaciones": "TEXT",
            "fecha_creacion": "TEXT",
            "fecha_actualizacion": "TEXT",

            # Inventario enriquecido
            "nombre_logico": "TEXT",
            "rol": "TEXT DEFAULT 'NO DEFINIDO'",
            "criticidad": (
                "TEXT DEFAULT 'NO DEFINIDA'"
            ),

            # Dependencias y enlaces
            "switch_padre_id": "INTEGER",
            "puerto_subida": "TEXT",
            "tecnologia_subida": "TEXT",

            # Características físicas
            "tiene_poe": "INTEGER",
            "tiene_ups": "INTEGER",

            # Documentación adicional
            "notas_topologia": "TEXT"
        }

        for columna, definicion in (
            columnas_necesarias.items()
        ):
            self.agregar_columna_si_falta(
                tabla="accesos_switches",
                columna=columna,
                definicion=definicion
            )

    # ======================================================
    # MIGRACIÓN DEL HISTORIAL
    # ======================================================

    def actualizar_estructura_historial(self):
        """
        Mantiene actualizada la tabla del historial.
        """
        columnas_necesarias = {
            "fecha": "TEXT",
            "accion": "TEXT",
            "entidad": "TEXT",
            "ultimo_octeto": "INTEGER",
            "ip": "TEXT",
            "ubicacion": "TEXT",
            "detalle": "TEXT",
            "origen": "TEXT"
        }

        for columna, definicion in (
            columnas_necesarias.items()
        ):
            self.agregar_columna_si_falta(
                tabla="historial_cambios",
                columna=columna,
                definicion=definicion
            )

    # ======================================================
    # NORMALIZACIÓN DE DATOS EXISTENTES
    # ======================================================

    def completar_octetos_existentes(self):
        """
        Completa el último octeto de registros antiguos
        que solamente poseían la IP completa.
        """
        consulta = """
        SELECT id, ip
        FROM accesos_switches
        WHERE ultimo_octeto IS NULL
          AND ip IS NOT NULL;
        """

        with self.conectar() as conexion:
            filas = conexion.execute(
                consulta
            ).fetchall()

            for fila in filas:
                ip = str(
                    fila["ip"]
                ).strip()

                partes = ip.split(".")

                if len(partes) != 4:
                    continue

                try:
                    ultimo_octeto = int(
                        partes[-1]
                    )

                except ValueError:
                    continue

                if not 1 <= ultimo_octeto <= 254:
                    continue

                conexion.execute(
                    """
                    UPDATE accesos_switches
                    SET ultimo_octeto = ?,
                        fecha_actualizacion =
                            CURRENT_TIMESTAMP
                    WHERE id = ?;
                    """,
                    (
                        ultimo_octeto,
                        fila["id"]
                    )
                )

            conexion.commit()

    def completar_valores_topologia(self):
        """
        Asigna valores predeterminados seguros a los
        registros antiguos.

        No intenta adivinar el rol, criticidad, PoE,
        UPS ni dependencia de cada switch.
        """
        with self.conectar() as conexion:
            conexion.execute(
                """
                UPDATE accesos_switches
                SET rol = 'NO DEFINIDO'
                WHERE rol IS NULL
                   OR TRIM(rol) = '';
                """
            )

            conexion.execute(
                """
                UPDATE accesos_switches
                SET criticidad = 'NO DEFINIDA'
                WHERE criticidad IS NULL
                   OR TRIM(criticidad) = '';
                """
            )

            conexion.execute(
                """
                UPDATE accesos_switches
                SET nombre_logico = nombre
                WHERE (
                    nombre_logico IS NULL
                    OR TRIM(nombre_logico) = ''
                )
                AND nombre IS NOT NULL;
                """
            )

            conexion.commit()

    def limpiar_padres_invalidos(self):
        """
        Elimina referencias a switches padre que ya no
        existen.

        También evita que un switch quede definido como
        padre de sí mismo.
        """
        with self.conectar() as conexion:
            conexion.execute(
                """
                UPDATE accesos_switches
                SET switch_padre_id = NULL
                WHERE switch_padre_id = id;
                """
            )

            conexion.execute(
                """
                UPDATE accesos_switches
                SET switch_padre_id = NULL
                WHERE switch_padre_id IS NOT NULL
                  AND switch_padre_id NOT IN (
                      SELECT id
                      FROM accesos_switches
                  );
                """
            )

            conexion.commit()

    def migrar_relaciones_a_enlaces(self):
        """
        Crea enlaces para las relaciones padre-hijo ya
        existentes sin borrar ni duplicar información.

        El valor histórico puerto_subida se interpreta como
        puerto del switch padre, según el criterio utilizado
        al documentar la topología actual.
        """
        consulta = """
        SELECT
            id AS switch_hijo_id,
            switch_padre_id,
            puerto_subida,
            tecnologia_subida
        FROM accesos_switches
        WHERE switch_padre_id IS NOT NULL;
        """

        with self.conectar() as conexion:
            filas = conexion.execute(
                consulta
            ).fetchall()

            for fila in filas:
                conexion.execute(
                    """
                    INSERT INTO enlaces_red (
                        switch_padre_id,
                        switch_hijo_id,
                        puerto_padre,
                        tecnologia
                    )
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(switch_hijo_id) DO UPDATE SET
                        switch_padre_id = excluded.switch_padre_id,
                        puerto_padre = COALESCE(
                            enlaces_red.puerto_padre,
                            excluded.puerto_padre
                        ),
                        tecnologia = CASE
                            WHEN enlaces_red.tecnologia IS NULL
                              OR TRIM(enlaces_red.tecnologia) = ''
                              OR enlaces_red.tecnologia = 'NO DEFINIDA'
                            THEN excluded.tecnologia
                            ELSE enlaces_red.tecnologia
                        END,
                        fecha_actualizacion = CURRENT_TIMESTAMP;
                    """,
                    (
                        fila["switch_padre_id"],
                        fila["switch_hijo_id"],
                        fila["puerto_subida"],
                        fila["tecnologia_subida"]
                        or "NO DEFINIDA"
                    )
                )

            conexion.commit()

    # ======================================================
    # ÍNDICES
    # ======================================================

    def crear_indices(self):
        """
        Crea índices para acelerar búsquedas, relaciones,
        historial y consultas de topología.
        """
        with self.conectar() as conexion:
            duplicados_octeto = conexion.execute(
                """
                SELECT ultimo_octeto
                FROM accesos_switches
                WHERE ultimo_octeto IS NOT NULL
                GROUP BY ultimo_octeto
                HAVING COUNT(*) > 1;
                """
            ).fetchall()

            if not duplicados_octeto:
                conexion.execute(
                    """
                    CREATE UNIQUE INDEX IF NOT EXISTS
                    idx_switches_ultimo_octeto
                    ON accesos_switches(
                        ultimo_octeto
                    )
                    WHERE ultimo_octeto IS NOT NULL;
                    """
                )

            duplicados_ip = conexion.execute(
                """
                SELECT ip
                FROM accesos_switches
                WHERE ip IS NOT NULL
                GROUP BY ip
                HAVING COUNT(*) > 1;
                """
            ).fetchall()

            if not duplicados_ip:
                conexion.execute(
                    """
                    CREATE UNIQUE INDEX IF NOT EXISTS
                    idx_switches_ip
                    ON accesos_switches(ip)
                    WHERE ip IS NOT NULL;
                    """
                )

            conexion.execute(
                """
                CREATE INDEX IF NOT EXISTS
                idx_switches_relacion
                ON accesos_switches(
                    hoja_excel,
                    bloque_excel
                );
                """
            )

            conexion.execute(
                """
                CREATE INDEX IF NOT EXISTS
                idx_switches_nombre_logico
                ON accesos_switches(
                    nombre_logico
                );
                """
            )

            conexion.execute(
                """
                CREATE INDEX IF NOT EXISTS
                idx_switches_rol
                ON accesos_switches(
                    rol
                );
                """
            )

            conexion.execute(
                """
                CREATE INDEX IF NOT EXISTS
                idx_switches_criticidad
                ON accesos_switches(
                    criticidad
                );
                """
            )

            conexion.execute(
                """
                CREATE INDEX IF NOT EXISTS
                idx_switches_padre
                ON accesos_switches(
                    switch_padre_id
                );
                """
            )

            conexion.execute(
                """
                CREATE INDEX IF NOT EXISTS
                idx_enlaces_padre
                ON enlaces_red(
                    switch_padre_id
                );
                """
            )

            conexion.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS
                idx_enlaces_hijo
                ON enlaces_red(
                    switch_hijo_id
                );
                """
            )

            conexion.execute(
                """
                CREATE INDEX IF NOT EXISTS
                idx_historial_fecha
                ON historial_cambios(
                    fecha
                );
                """
            )

            conexion.execute(
                """
                CREATE INDEX IF NOT EXISTS
                idx_historial_octeto
                ON historial_cambios(
                    ultimo_octeto
                );
                """
            )

            conexion.commit()

    # ======================================================
    # DIAGNÓSTICO DE ESTRUCTURA
    # ======================================================

    def obtener_version_estructura(self):
        """
        Devuelve información básica de la estructura
        instalada. Será útil para diagnósticos futuros.
        """
        columnas_switches = (
            self.obtener_columnas_tabla(
                "accesos_switches"
            )
        )

        columnas_topologia = {
            "nombre_logico",
            "rol",
            "criticidad",
            "switch_padre_id",
            "puerto_subida",
            "tecnologia_subida",
            "tiene_poe",
            "tiene_ups",
            "notas_topologia"
        }

        faltantes = sorted(
            columnas_topologia
            - columnas_switches
        )

        return {
            "topologia_disponible": (
                not faltantes
            ),
            "columnas_topologia": sorted(
                columnas_topologia
            ),
            "columnas_faltantes": faltantes
        }