from collections import deque
from typing import Any


class GestorTopologia:
    """
    Administra la topología lógica de switches almacenada
    en SQLite.

    Permite:

    - Clasificar switches.
    - Definir criticidad.
    - Asignar switches padre.
    - Documentar enlaces de subida.
    - Consultar hijos y descendientes.
    - Calcular niveles de topología.
    - Detectar ciclos y relaciones inválidas.

    Este módulo no consulta SNMP y no modifica el Excel.
    """

    ROLES_VALIDOS = {
        "CORE",
        "DISTRIBUCION",
        "ACCESO",
        "NO DEFINIDO"
    }

    CRITICIDADES_VALIDAS = {
        "CRITICA",
        "ALTA",
        "MEDIA",
        "BAJA",
        "NO DEFINIDA"
    }

    TECNOLOGIAS_VALIDAS = {
        "FIBRA",
        "COBRE",
        "INALAMBRICO",
        "OTRA",
        "NO DEFINIDA"
    }

    def __init__(
        self,
        gestor_accesos
    ):
        self.gestor_accesos = gestor_accesos
        self.base_datos = gestor_accesos.base_datos
        self.historial = gestor_accesos.historial

    # ======================================================
    # NORMALIZACIÓN
    # ======================================================

    @staticmethod
    def limpiar_texto(
        valor: Any
    ) -> str | None:
        """
        Limpia un valor textual.
        """
        if valor is None:
            return None

        texto = str(
            valor
        ).strip()

        return texto or None

    @classmethod
    def normalizar_opcion(
        cls,
        valor: Any
    ) -> str:
        """
        Normaliza opciones como rol, criticidad y
        tecnología.
        """
        texto = cls.limpiar_texto(
            valor
        )

        if texto is None:
            return ""

        texto = texto.upper()

        reemplazos = {
            "Á": "A",
            "É": "E",
            "Í": "I",
            "Ó": "O",
            "Ú": "U",
            "Ñ": "N"
        }

        for original, reemplazo in (
            reemplazos.items()
        ):
            texto = texto.replace(
                original,
                reemplazo
            )

        return " ".join(
            texto.split()
        )

    @staticmethod
    def convertir_booleano(
        valor: Any
    ) -> int | None:
        """
        Convierte Sí/No, True/False o 1/0 a formato SQLite.

        Devuelve:
        - 1 para Sí.
        - 0 para No.
        - None para Sin definir.
        """
        if valor is None:
            return None

        if isinstance(
            valor,
            bool
        ):
            return int(valor)

        if isinstance(
            valor,
            int
        ):
            if valor in {
                0,
                1
            }:
                return valor

        texto = str(
            valor
        ).strip().lower()

        if texto in {
            "si",
            "sí",
            "s",
            "yes",
            "y",
            "true",
            "1"
        }:
            return 1

        if texto in {
            "no",
            "n",
            "false",
            "0"
        }:
            return 0

        if texto in {
            "",
            "ninguno",
            "sin definir",
            "no definido",
            "-"
        }:
            return None

        raise ValueError(
            "El valor debe ser Sí, No o Sin definir."
        )

    @staticmethod
    def texto_booleano(
        valor: Any
    ) -> str:
        """
        Convierte el valor SQLite en texto visible.
        """
        if valor is None:
            return "Sin definir"

        try:
            valor = int(
                valor
            )

        except (
            ValueError,
            TypeError
        ):
            return "Sin definir"

        if valor == 1:
            return "Sí"

        if valor == 0:
            return "No"

        return "Sin definir"

    # ======================================================
    # CONSULTAS BÁSICAS
    # ======================================================

    def listar_switches(
        self
    ) -> list[dict]:
        """
        Devuelve todos los switches ordenados por IP.
        """
        consulta = """
        SELECT
            switch.*,
            padre.ip AS padre_ip,
            padre.nombre AS padre_nombre,
            padre.nombre_logico AS padre_nombre_logico
        FROM accesos_switches AS switch
        LEFT JOIN accesos_switches AS padre
            ON padre.id = switch.switch_padre_id
        ORDER BY
            switch.ultimo_octeto,
            switch.ip;
        """

        with self.base_datos.conectar() as conexion:
            filas = conexion.execute(
                consulta
            ).fetchall()

        return [
            dict(fila)
            for fila in filas
        ]

    def obtener_por_id(
        self,
        switch_id: int
    ) -> dict | None:
        """
        Obtiene un switch mediante su ID interno.
        """
        try:
            switch_id = int(
                switch_id
            )

        except (
            ValueError,
            TypeError
        ):
            return None

        consulta = """
        SELECT
            switch.*,
            padre.ip AS padre_ip,
            padre.nombre AS padre_nombre,
            padre.nombre_logico AS padre_nombre_logico
        FROM accesos_switches AS switch
        LEFT JOIN accesos_switches AS padre
            ON padre.id = switch.switch_padre_id
        WHERE switch.id = ?;
        """

        with self.base_datos.conectar() as conexion:
            fila = conexion.execute(
                consulta,
                (
                    switch_id,
                )
            ).fetchone()

        if fila is None:
            return None

        return dict(
            fila
        )

    def obtener_por_ip(
        self,
        ip: str
    ) -> dict | None:
        """
        Obtiene un switch mediante su dirección IP.
        """
        ip = self.limpiar_texto(
            ip
        )

        if not ip:
            return None

        consulta = """
        SELECT
            switch.*,
            padre.ip AS padre_ip,
            padre.nombre AS padre_nombre,
            padre.nombre_logico AS padre_nombre_logico
        FROM accesos_switches AS switch
        LEFT JOIN accesos_switches AS padre
            ON padre.id = switch.switch_padre_id
        WHERE switch.ip = ?;
        """

        with self.base_datos.conectar() as conexion:
            fila = conexion.execute(
                consulta,
                (
                    ip,
                )
            ).fetchone()

        if fila is None:
            return None

        return dict(
            fila
        )

    def obtener_switch(
        self,
        identificador
    ) -> dict | None:
        """
        Acepta ID, IP completa o último octeto.
        """
        if identificador is None:
            return None

        texto = str(
            identificador
        ).strip()

        if not texto:
            return None

        if "." in texto:
            return self.obtener_por_ip(
                texto
            )

        try:
            numero = int(
                texto
            )

        except ValueError:
            return None

        switch = self.obtener_por_id(
            numero
        )

        if switch is not None:
            return switch

        try:
            return (
                self.gestor_accesos
                .obtener_por_octeto(
                    numero
                )
            )

        except ValueError:
            return None

    # ======================================================
    # VALIDACIONES
    # ======================================================

    @classmethod
    def validar_rol(
        cls,
        rol: str
    ) -> str:
        """
        Valida y normaliza el rol.
        """
        rol = cls.normalizar_opcion(
            rol
        )

        if not rol:
            rol = "NO DEFINIDO"

        if rol not in cls.ROLES_VALIDOS:
            raise ValueError(
                "Rol inválido. Opciones: "
                + ", ".join(
                    sorted(
                        cls.ROLES_VALIDOS
                    )
                )
            )

        return rol

    @classmethod
    def validar_criticidad(
        cls,
        criticidad: str
    ) -> str:
        """
        Valida y normaliza la criticidad.
        """
        criticidad = cls.normalizar_opcion(
            criticidad
        )

        if not criticidad:
            criticidad = "NO DEFINIDA"

        if (
            criticidad
            not in cls.CRITICIDADES_VALIDAS
        ):
            raise ValueError(
                "Criticidad inválida. Opciones: "
                + ", ".join(
                    sorted(
                        cls.CRITICIDADES_VALIDAS
                    )
                )
            )

        return criticidad

    @classmethod
    def validar_tecnologia(
        cls,
        tecnologia: str
    ) -> str:
        """
        Valida y normaliza la tecnología del enlace.
        """
        tecnologia = cls.normalizar_opcion(
            tecnologia
        )

        if not tecnologia:
            tecnologia = "NO DEFINIDA"

        if (
            tecnologia
            not in cls.TECNOLOGIAS_VALIDAS
        ):
            raise ValueError(
                "Tecnología inválida. Opciones: "
                + ", ".join(
                    sorted(
                        cls.TECNOLOGIAS_VALIDAS
                    )
                )
            )

        return tecnologia

    def padre_crearia_ciclo(
        self,
        switch_id: int,
        padre_id: int
    ) -> bool:
        """
        Comprueba si asignar un padre generaría un ciclo.

        Ejemplo inválido:

        Core -> Pabellón -> Biblioteca -> Core
        """
        try:
            switch_id = int(
                switch_id
            )

            padre_id = int(
                padre_id
            )

        except (
            ValueError,
            TypeError
        ):
            return True

        if switch_id == padre_id:
            return True

        visitados = set()
        actual_id = padre_id

        while actual_id is not None:
            if actual_id == switch_id:
                return True

            if actual_id in visitados:
                return True

            visitados.add(
                actual_id
            )

            actual = self.obtener_por_id(
                actual_id
            )

            if actual is None:
                return False

            actual_id = actual.get(
                "switch_padre_id"
            )

        return False

    # ======================================================
    # ACTUALIZACIÓN DE DATOS
    # ======================================================

    def actualizar_clasificacion(
        self,
        switch_id: int,
        nombre_logico: str | None = None,
        rol: str = "NO DEFINIDO",
        criticidad: str = "NO DEFINIDA",
        tiene_poe: Any = None,
        tiene_ups: Any = None,
        notas_topologia: str | None = None
    ) -> dict:
        """
        Actualiza la clasificación y características de
        un switch.
        """
        switch = self.obtener_por_id(
            switch_id
        )

        if switch is None:
            raise ValueError(
                "El switch indicado no existe."
            )

        nombre_logico = (
            self.limpiar_texto(
                nombre_logico
            )
            or switch.get("nombre")
            or switch.get("ubicacion")
            or switch.get("ip")
        )

        rol = self.validar_rol(
            rol
        )

        criticidad = self.validar_criticidad(
            criticidad
        )

        tiene_poe = self.convertir_booleano(
            tiene_poe
        )

        tiene_ups = self.convertir_booleano(
            tiene_ups
        )

        notas_topologia = self.limpiar_texto(
            notas_topologia
        )

        cambios = []

        campos = {
            "Nombre lógico": (
                switch.get("nombre_logico"),
                nombre_logico
            ),
            "Rol": (
                switch.get("rol"),
                rol
            ),
            "Criticidad": (
                switch.get("criticidad"),
                criticidad
            ),
            "Tiene PoE": (
                self.texto_booleano(
                    switch.get("tiene_poe")
                ),
                self.texto_booleano(
                    tiene_poe
                )
            ),
            "Tiene UPS": (
                self.texto_booleano(
                    switch.get("tiene_ups")
                ),
                self.texto_booleano(
                    tiene_ups
                )
            ),
            "Notas topología": (
                switch.get("notas_topologia"),
                notas_topologia
            )
        }

        for campo, valores in campos.items():
            anterior, nuevo = valores

            if str(
                anterior or ""
            ).strip() != str(
                nuevo or ""
            ).strip():
                cambios.append(
                    {
                        "campo": campo,
                        "anterior": anterior,
                        "nuevo": nuevo
                    }
                )

        consulta = """
        UPDATE accesos_switches
        SET
            nombre_logico = ?,
            rol = ?,
            criticidad = ?,
            tiene_poe = ?,
            tiene_ups = ?,
            notas_topologia = ?,
            fecha_actualizacion = CURRENT_TIMESTAMP
        WHERE id = ?;
        """

        with self.base_datos.conectar() as conexion:
            conexion.execute(
                consulta,
                (
                    nombre_logico,
                    rol,
                    criticidad,
                    tiene_poe,
                    tiene_ups,
                    notas_topologia,
                    switch_id
                )
            )

            conexion.commit()

        if cambios:
            self.historial.registrar(
                accion="ACTUALIZADO",
                entidad="topologia",
                ultimo_octeto=switch.get(
                    "ultimo_octeto"
                ),
                ip=switch.get("ip"),
                ubicacion=switch.get(
                    "ubicacion"
                ),
                detalle=cambios,
                origen="Gestor de topología"
            )

        return self.obtener_por_id(
            switch_id
        )

    def obtener_enlace_por_hijo(
        self,
        switch_hijo_id: int
    ) -> dict | None:
        """
        Obtiene el enlace completo asociado a un switch hijo.
        """
        consulta = """
        SELECT
            enlace.*,
            padre.ip AS padre_ip,
            padre.nombre_logico AS padre_nombre_logico,
            hijo.ip AS hijo_ip,
            hijo.nombre_logico AS hijo_nombre_logico
        FROM enlaces_red AS enlace
        INNER JOIN accesos_switches AS padre
            ON padre.id = enlace.switch_padre_id
        INNER JOIN accesos_switches AS hijo
            ON hijo.id = enlace.switch_hijo_id
        WHERE enlace.switch_hijo_id = ?;
        """

        with self.base_datos.conectar() as conexion:
            fila = conexion.execute(
                consulta,
                (switch_hijo_id,)
            ).fetchone()

        return dict(fila) if fila else None

    def asignar_padre(
        self,
        switch_id: int,
        padre_id: int | None,
        puerto_padre: str | None = None,
        puerto_hijo: str | None = None,
        tecnologia_subida: str = "NO DEFINIDA",
        puerto_subida: str | None = None
    ) -> dict:
        """
        Asigna o elimina el padre y mantiene un enlace de red
        con ambos extremos.

        puerto_subida se conserva como alias compatible con
        versiones anteriores y equivale a puerto_padre.
        """
        switch = self.obtener_por_id(switch_id)

        if switch is None:
            raise ValueError("El switch hijo no existe.")

        if puerto_padre is None and puerto_subida is not None:
            puerto_padre = puerto_subida

        puerto_padre = self.limpiar_texto(puerto_padre)
        puerto_hijo = self.limpiar_texto(puerto_hijo)

        if padre_id in {None, "", 0, "0"}:
            padre = None
            padre_id = None
            puerto_padre = None
            puerto_hijo = None
            tecnologia_subida = "NO DEFINIDA"
        else:
            try:
                padre_id = int(padre_id)
            except (ValueError, TypeError) as error:
                raise ValueError(
                    "El identificador del padre no es válido."
                ) from error

            padre = self.obtener_por_id(padre_id)

            if padre is None:
                raise ValueError("El switch padre no existe.")

            if self.padre_crearia_ciclo(switch_id, padre_id):
                raise ValueError(
                    "La relación generaría un ciclo en la topología."
                )

            tecnologia_subida = self.validar_tecnologia(
                tecnologia_subida
            )

        enlace_anterior = self.obtener_enlace_por_hijo(switch_id)
        padre_anterior = self.obtener_padre(switch_id)
        cambios = []

        valores = {
            "Switch padre": (
                padre_anterior.get("ip") if padre_anterior else None,
                padre.get("ip") if padre else None
            ),
            "Puerto del padre": (
                enlace_anterior.get("puerto_padre")
                if enlace_anterior else switch.get("puerto_subida"),
                puerto_padre
            ),
            "Puerto del hijo": (
                enlace_anterior.get("puerto_hijo")
                if enlace_anterior else None,
                puerto_hijo
            ),
            "Tecnología": (
                enlace_anterior.get("tecnologia")
                if enlace_anterior
                else switch.get("tecnologia_subida"),
                tecnologia_subida
            )
        }

        for campo, (anterior, nuevo) in valores.items():
            if str(anterior or "").strip() != str(nuevo or "").strip():
                cambios.append({
                    "campo": campo,
                    "anterior": anterior,
                    "nuevo": nuevo
                })

        with self.base_datos.conectar() as conexion:
            conexion.execute(
                """
                UPDATE accesos_switches
                SET
                    switch_padre_id = ?,
                    puerto_subida = ?,
                    tecnologia_subida = ?,
                    fecha_actualizacion = CURRENT_TIMESTAMP
                WHERE id = ?;
                """,
                (
                    padre_id,
                    puerto_padre,
                    tecnologia_subida,
                    switch_id
                )
            )

            if padre_id is None:
                conexion.execute(
                    """
                    DELETE FROM enlaces_red
                    WHERE switch_hijo_id = ?;
                    """,
                    (switch_id,)
                )
            else:
                conexion.execute(
                    """
                    INSERT INTO enlaces_red (
                        switch_padre_id,
                        switch_hijo_id,
                        puerto_padre,
                        puerto_hijo,
                        tecnologia,
                        fecha_actualizacion
                    )
                    VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(switch_hijo_id) DO UPDATE SET
                        switch_padre_id = excluded.switch_padre_id,
                        puerto_padre = excluded.puerto_padre,
                        puerto_hijo = excluded.puerto_hijo,
                        tecnologia = excluded.tecnologia,
                        fecha_actualizacion = CURRENT_TIMESTAMP;
                    """,
                    (
                        padre_id,
                        switch_id,
                        puerto_padre,
                        puerto_hijo,
                        tecnologia_subida
                    )
                )

            conexion.commit()

        if cambios:
            self.historial.registrar(
                accion="ACTUALIZADO",
                entidad="enlace_red",
                ultimo_octeto=switch.get("ultimo_octeto"),
                ip=switch.get("ip"),
                ubicacion=switch.get("ubicacion"),
                detalle=cambios,
                origen="Gestor de topología"
            )

        return self.obtener_por_id(switch_id)

    # ======================================================
    # RELACIONES Y DEPENDENCIAS
    # ======================================================

    def obtener_padre(
        self,
        switch_id: int
    ) -> dict | None:
        """
        Devuelve el padre directo de un switch.
        """
        switch = self.obtener_por_id(
            switch_id
        )

        if switch is None:
            return None

        padre_id = switch.get(
            "switch_padre_id"
        )

        if padre_id is None:
            return None

        return self.obtener_por_id(
            padre_id
        )

    def obtener_hijos(
        self,
        switch_id: int
    ) -> list[dict]:
        """
        Devuelve los hijos directos.
        """
        consulta = """
        SELECT *
        FROM accesos_switches
        WHERE switch_padre_id = ?
        ORDER BY
            ultimo_octeto,
            ip;
        """

        with self.base_datos.conectar() as conexion:
            filas = conexion.execute(
                consulta,
                (
                    switch_id,
                )
            ).fetchall()

        return [
            dict(fila)
            for fila in filas
        ]

    def obtener_descendientes(
        self,
        switch_id: int
    ) -> list[dict]:
        """
        Devuelve todos los descendientes de un switch,
        sin repetir registros.
        """
        descendientes = []
        visitados = {
            switch_id
        }

        pendientes = deque(
            self.obtener_hijos(
                switch_id
            )
        )

        while pendientes:
            switch = pendientes.popleft()

            identificador = switch.get(
                "id"
            )

            if identificador in visitados:
                continue

            visitados.add(
                identificador
            )

            descendientes.append(
                switch
            )

            pendientes.extend(
                self.obtener_hijos(
                    identificador
                )
            )

        return descendientes

    def obtener_ancestros(
        self,
        switch_id: int
    ) -> list[dict]:
        """
        Devuelve la cadena desde el padre directo hasta
        el nivel superior.
        """
        ancestros = []
        visitados = {
            switch_id
        }

        actual = self.obtener_padre(
            switch_id
        )

        while actual is not None:
            identificador = actual.get(
                "id"
            )

            if identificador in visitados:
                break

            visitados.add(
                identificador
            )

            ancestros.append(
                actual
            )

            actual = self.obtener_padre(
                identificador
            )

        return ancestros

    def calcular_nivel(
        self,
        switch_id: int
    ) -> int:
        """
        Calcula el nivel jerárquico.

        Nivel 0: raíz o Core.
        Nivel 1: depende directamente de la raíz.
        Nivel 2: depende de un switch de nivel 1.
        """
        return len(
            self.obtener_ancestros(
                switch_id
            )
        )

    def obtener_raices(
        self
    ) -> list[dict]:
        """
        Devuelve switches sin padre.
        """
        consulta = """
        SELECT *
        FROM accesos_switches
        WHERE switch_padre_id IS NULL
        ORDER BY
            CASE
                WHEN rol = 'CORE' THEN 0
                ELSE 1
            END,
            ultimo_octeto,
            ip;
        """

        with self.base_datos.conectar() as conexion:
            filas = conexion.execute(
                consulta
            ).fetchall()

        return [
            dict(fila)
            for fila in filas
        ]

    # ======================================================
    # VALIDACIÓN GENERAL
    # ======================================================

    def validar_topologia(
        self
    ) -> dict:
        """
        Revisa la consistencia general de la topología.
        """
        switches = self.listar_switches()

        sin_clasificar = []
        sin_criticidad = []
        sin_padre = []
        ciclos = []
        padres_invalidos = []

        ids_existentes = {
            switch.get("id")
            for switch in switches
        }

        for switch in switches:
            switch_id = switch.get(
                "id"
            )

            if switch.get("rol") in {
                None,
                "",
                "NO DEFINIDO"
            }:
                sin_clasificar.append(
                    switch
                )

            if switch.get("criticidad") in {
                None,
                "",
                "NO DEFINIDA"
            }:
                sin_criticidad.append(
                    switch
                )

            padre_id = switch.get(
                "switch_padre_id"
            )

            if (
                padre_id is None
                and switch.get("rol") != "CORE"
            ):
                sin_padre.append(
                    switch
                )

            if (
                padre_id is not None
                and padre_id not in ids_existentes
            ):
                padres_invalidos.append(
                    switch
                )

            if padre_id is not None:
                if self.padre_crearia_ciclo(
                    switch_id,
                    padre_id
                ):
                    ciclos.append(
                        switch
                    )

        return {
            "total_switches": len(
                switches
            ),
            "sin_clasificar": (
                sin_clasificar
            ),
            "sin_criticidad": (
                sin_criticidad
            ),
            "sin_padre": sin_padre,
            "ciclos": ciclos,
            "padres_invalidos": (
                padres_invalidos
            ),
            "correcta": not (
                ciclos
                or padres_invalidos
            )
        }

    # ======================================================
    # RESÚMENES
    # ======================================================

    def obtener_resumen_switch(
        self,
        switch_id: int
    ) -> dict:
        """
        Construye un resumen de topología para un switch.
        """
        switch = self.obtener_por_id(
            switch_id
        )

        if switch is None:
            raise ValueError(
                "El switch no existe."
            )

        padre = self.obtener_padre(
            switch_id
        )

        hijos = self.obtener_hijos(
            switch_id
        )

        descendientes = self.obtener_descendientes(
            switch_id
        )

        return {
            "switch": switch,
            "padre": padre,
            "hijos": hijos,
            "descendientes": descendientes,
            "nivel": self.calcular_nivel(
                switch_id
            ),
            "cantidad_hijos": len(
                hijos
            ),
            "cantidad_descendientes": len(
                descendientes
            ),
            "impacto_estimado": (
                len(descendientes)
            )
        }

    def obtener_arbol(
        self
    ) -> list[dict]:
        """
        Devuelve una representación estructurada del árbol.
        """

        def construir_nodo(
            switch,
            visitados
        ):
            switch_id = switch.get(
                "id"
            )

            if switch_id in visitados:
                return {
                    "switch": switch,
                    "hijos": [],
                    "ciclo_detectado": True
                }

            nuevos_visitados = set(
                visitados
            )

            nuevos_visitados.add(
                switch_id
            )

            hijos = self.obtener_hijos(
                switch_id
            )

            return {
                "switch": switch,
                "hijos": [
                    construir_nodo(
                        hijo,
                        nuevos_visitados
                    )
                    for hijo in hijos
                ],
                "ciclo_detectado": False
            }

        return [
            construir_nodo(
                raiz,
                set()
            )
            for raiz in self.obtener_raices()
        ]

    # ======================================================
    # PRESENTACIÓN EN CONSOLA
    # ======================================================

    @staticmethod
    def nombre_visible(
        switch: dict
    ) -> str:
        """
        Obtiene el mejor nombre disponible.
        """
        return str(
            switch.get("nombre_logico")
            or switch.get("nombre")
            or switch.get("ubicacion")
            or switch.get("ip")
            or "Switch sin nombre"
        )

    def mostrar_switch(
        self,
        switch: dict
    ):
        """
        Muestra información topológica de un switch.
        """
        if not switch:
            print(
                "\nSwitch no encontrado."
            )
            return

        padre = self.obtener_padre(
            switch.get("id")
        )

        print(
            "\n========================================"
        )
        print(
            f"Nombre lógico: "
            f"{self.nombre_visible(switch)}"
        )
        print(
            f"IP: {switch.get('ip') or 'Sin información'}"
        )
        print(
            f"Ubicación: "
            f"{switch.get('ubicacion') or 'Sin información'}"
        )
        print(
            f"Rol: "
            f"{switch.get('rol') or 'NO DEFINIDO'}"
        )
        print(
            f"Criticidad: "
            f"{switch.get('criticidad') or 'NO DEFINIDA'}"
        )
        print(
            "Switch padre: "
            + (
                f"{self.nombre_visible(padre)} "
                f"({padre.get('ip')})"
                if padre
                else "Sin padre"
            )
        )
        enlace = self.obtener_enlace_por_hijo(
            switch.get("id")
        )

        print(
            f"Puerto del padre: "
            f"{(enlace or {}).get('puerto_padre') or switch.get('puerto_subida') or 'Sin definir'}"
        )
        print(
            f"Puerto del hijo: "
            f"{(enlace or {}).get('puerto_hijo') or 'Sin definir'}"
        )
        print(
            f"Tecnología del enlace: "
            f"{(enlace or {}).get('tecnologia') or switch.get('tecnologia_subida') or 'NO DEFINIDA'}"
        )
        print(
            f"PoE: "
            f"{self.texto_booleano(switch.get('tiene_poe'))}"
        )
        print(
            f"UPS: "
            f"{self.texto_booleano(switch.get('tiene_ups'))}"
        )

        notas = switch.get(
            "notas_topologia"
        )

        if notas:
            print(
                f"Notas: {notas}"
            )

    def mostrar_arbol(
        self
    ):
        """
        Muestra la topología jerárquica en consola.
        """
        arbol = self.obtener_arbol()

        print(
            "\n========================================"
        )
        print(
            "          TOPOLOGÍA DE SWITCHES"
        )
        print(
            "========================================"
        )

        if not arbol:
            print(
                "\nNo existen switches registrados."
            )
            return

        def imprimir_nodo(
            nodo,
            nivel=0
        ):
            switch = nodo["switch"]

            prefijo = (
                "    " * nivel
            )

            rama = (
                "└── "
                if nivel > 0
                else ""
            )

            nombre = self.nombre_visible(
                switch
            )

            rol = (
                switch.get("rol")
                or "NO DEFINIDO"
            )

            criticidad = (
                switch.get("criticidad")
                or "NO DEFINIDA"
            )

            print(
                f"{prefijo}{rama}"
                f"{nombre} | "
                f"{switch.get('ip')} | "
                f"{rol} | {criticidad}"
            )

            if nodo.get(
                "ciclo_detectado"
            ):
                print(
                    f"{prefijo}    "
                    "[CICLO DETECTADO]"
                )
                return

            for hijo in nodo.get(
                "hijos",
                []
            ):
                imprimir_nodo(
                    hijo,
                    nivel + 1
                )

        for raiz in arbol:
            imprimir_nodo(
                raiz
            )