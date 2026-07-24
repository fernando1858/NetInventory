from collections import Counter
from dataclasses import dataclass, field
from typing import Any

from modulos.descubridor_snmp import DescubridorSNMP
from modulos.visual import visual


@dataclass
class DiagnosticoSwitch:
    """
    Representa el diagnóstico consolidado de un switch.

    Combina:

    - Información registrada en SQLite.
    - Relaciones de topología.
    - Resultado del descubrimiento SNMP.
    """

    switch_id: int | None
    ip: str | None
    nombre: str
    ubicacion: str | None

    rol: str
    criticidad: str

    estado: str
    prioridad: str

    responde_snmp: bool | None

    padre_id: int | None = None
    padre_ip: str | None = None
    padre_nombre: str | None = None

    ancestro_caido_id: int | None = None
    ancestro_caido_ip: str | None = None
    ancestro_caido_nombre: str | None = None

    hijos_directos: int = 0
    descendientes: int = 0

    detalle: str = ""
    recomendacion: str = ""

    datos: dict[str, Any] = field(
        default_factory=dict
    )

    def convertir_diccionario(
        self
    ) -> dict[str, Any]:
        """
        Convierte el diagnóstico en un diccionario.
        """
        return {
            "switch_id": self.switch_id,
            "ip": self.ip,
            "nombre": self.nombre,
            "ubicacion": self.ubicacion,
            "rol": self.rol,
            "criticidad": self.criticidad,
            "estado": self.estado,
            "prioridad": self.prioridad,
            "responde_snmp": self.responde_snmp,
            "padre_id": self.padre_id,
            "padre_ip": self.padre_ip,
            "padre_nombre": self.padre_nombre,
            "ancestro_caido_id": (
                self.ancestro_caido_id
            ),
            "ancestro_caido_ip": (
                self.ancestro_caido_ip
            ),
            "ancestro_caido_nombre": (
                self.ancestro_caido_nombre
            ),
            "hijos_directos": self.hijos_directos,
            "descendientes": self.descendientes,
            "detalle": self.detalle,
            "recomendacion": self.recomendacion,
            "datos": dict(self.datos)
        }


@dataclass
class ResultadoDiagnosticoRed:
    """
    Contiene el diagnóstico completo de la red.
    """

    diagnosticos: list[DiagnosticoSwitch]

    def obtener_por_estado(
        self,
        estado: str
    ) -> list[DiagnosticoSwitch]:
        """
        Filtra diagnósticos por estado.
        """
        return [
            diagnostico
            for diagnostico in self.diagnosticos
            if diagnostico.estado == estado
        ]

    def obtener_por_prioridad(
        self,
        prioridad: str
    ) -> list[DiagnosticoSwitch]:
        """
        Filtra diagnósticos por prioridad.
        """
        return [
            diagnostico
            for diagnostico in self.diagnosticos
            if diagnostico.prioridad == prioridad
        ]

    def obtener_resumen(
        self
    ) -> dict[str, Any]:
        """
        Calcula estadísticas generales.
        """
        estados = Counter(
            diagnostico.estado
            for diagnostico in self.diagnosticos
        )

        prioridades = Counter(
            diagnostico.prioridad
            for diagnostico in self.diagnosticos
        )

        return {
            "switches_analizados": len(
                self.diagnosticos
            ),
            "operativos": estados.get(
                MotorDiagnosticoRed.ESTADO_OPERATIVO,
                0
            ),
            "fallas_locales_probables": estados.get(
                MotorDiagnosticoRed
                .ESTADO_FALLA_LOCAL,
                0
            ),
            "posiblemente_afectados": estados.get(
                MotorDiagnosticoRed
                .ESTADO_POSIBLEMENTE_AFECTADO,
                0
            ),
            "sin_respuesta": estados.get(
                MotorDiagnosticoRed
                .ESTADO_SIN_RESPUESTA,
                0
            ),
            "sin_comprobar": estados.get(
                MotorDiagnosticoRed
                .ESTADO_SIN_COMPROBAR,
                0
            ),
            "prioridad_critica": prioridades.get(
                MotorDiagnosticoRed
                .PRIORIDAD_CRITICA,
                0
            ),
            "prioridad_alta": prioridades.get(
                MotorDiagnosticoRed
                .PRIORIDAD_ALTA,
                0
            ),
            "prioridad_media": prioridades.get(
                MotorDiagnosticoRed
                .PRIORIDAD_MEDIA,
                0
            ),
            "prioridad_baja": prioridades.get(
                MotorDiagnosticoRed
                .PRIORIDAD_BAJA,
                0
            ),
            "prioridad_informativa": prioridades.get(
                MotorDiagnosticoRed
                .PRIORIDAD_INFORMATIVA,
                0
            )
        }

    def obtener_incidencias_principales(
        self
    ) -> list[DiagnosticoSwitch]:
        """
        Devuelve solamente las incidencias que parecen
        ser causas principales.

        No incluye switches posiblemente afectados por
        la caída de un ancestro.
        """
        estados_principales = {
            MotorDiagnosticoRed.ESTADO_FALLA_LOCAL,
            MotorDiagnosticoRed.ESTADO_SIN_RESPUESTA
        }

        return [
            diagnostico
            for diagnostico in self.diagnosticos
            if diagnostico.estado in estados_principales
        ]


class MotorDiagnosticoRed:
    """
    Combina la topología registrada con el resultado
    de un descubrimiento SNMP.

    Esta primera versión se enfoca en disponibilidad
    y correlación padre-hijo.

    No consulta directamente los switches.
    No modifica el Excel.
    No modifica SQLite.
    """

    ESTADO_OPERATIVO = "OPERATIVO"

    ESTADO_FALLA_LOCAL = (
        "FALLA LOCAL PROBABLE"
    )

    ESTADO_POSIBLEMENTE_AFECTADO = (
        "POSIBLEMENTE AFECTADO"
    )

    ESTADO_SIN_RESPUESTA = (
        "SIN RESPUESTA"
    )

    ESTADO_SIN_COMPROBAR = (
        "SIN COMPROBAR"
    )

    PRIORIDAD_CRITICA = "CRÍTICA"
    PRIORIDAD_ALTA = "ALTA"
    PRIORIDAD_MEDIA = "MEDIA"
    PRIORIDAD_BAJA = "BAJA"
    PRIORIDAD_INFORMATIVA = "INFORMATIVA"

    ORDEN_ESTADOS = {
        ESTADO_FALLA_LOCAL: 1,
        ESTADO_SIN_RESPUESTA: 2,
        ESTADO_POSIBLEMENTE_AFECTADO: 3,
        ESTADO_SIN_COMPROBAR: 4,
        ESTADO_OPERATIVO: 5
    }

    ORDEN_PRIORIDADES = {
        PRIORIDAD_CRITICA: 1,
        PRIORIDAD_ALTA: 2,
        PRIORIDAD_MEDIA: 3,
        PRIORIDAD_BAJA: 4,
        PRIORIDAD_INFORMATIVA: 5
    }

    def __init__(
        self,
        gestor_topologia
    ):
        self.gestor_topologia = gestor_topologia

    # ======================================================
    # NORMALIZACIÓN
    # ======================================================

    @staticmethod
    def limpiar_texto(
        valor: Any
    ) -> str | None:
        """
        Convierte valores vacíos en None.
        """
        if valor is None:
            return None

        texto = str(
            valor
        ).strip()

        return texto or None

    def nombre_visible(
        self,
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

    # ======================================================
    # ESTADO SNMP
    # ======================================================

    def construir_mapa_snmp(
        self,
        descubrimiento
    ) -> dict[str, dict]:
        """
        Convierte el resultado del descubrimiento en un
        mapa indexado por IP.
        """
        mapa = {}

        if descubrimiento is None:
            return mapa

        for resultado in descubrimiento.resultados:
            ip = self.limpiar_texto(
                resultado.ip
            )

            if not ip:
                continue

            mapa[ip] = {
                "responde": (
                    resultado.estado
                    == DescubridorSNMP.ESTADO_RESPONDE
                ),
                "estado_descubrimiento": (
                    resultado.estado
                ),
                "nombre_snmp": (
                    resultado.nombre_snmp
                ),
                "descripcion_snmp": (
                    resultado.descripcion_snmp
                ),
                "tiempo_ms": resultado.tiempo_ms,
                "detalle": resultado.detalle
            }

        return mapa

    def switch_responde(
        self,
        switch: dict,
        mapa_snmp: dict[str, dict]
    ) -> bool | None:
        """
        Devuelve:

        - True si respondió.
        - False si fue comprobado y no respondió.
        - None si no existe resultado.
        """
        ip = self.limpiar_texto(
            switch.get("ip")
        )

        if not ip:
            return None

        resultado = mapa_snmp.get(
            ip
        )

        if resultado is None:
            return None

        return bool(
            resultado.get("responde")
        )

    # ======================================================
    # TOPOLOGÍA
    # ======================================================

    def encontrar_ancestro_sin_respuesta(
        self,
        switch: dict,
        mapa_snmp: dict[str, dict]
    ) -> dict | None:
        """
        Busca el primer ancestro que fue comprobado
        y no respondió por SNMP.
        """
        switch_id = switch.get(
            "id"
        )

        if switch_id is None:
            return None

        ancestros = (
            self.gestor_topologia
            .obtener_ancestros(
                switch_id
            )
        )

        for ancestro in ancestros:
            responde = self.switch_responde(
                ancestro,
                mapa_snmp
            )

            if responde is False:
                return ancestro

        return None

    def obtener_padre(
        self,
        switch: dict
    ) -> dict | None:
        """
        Obtiene el padre directo.
        """
        switch_id = switch.get(
            "id"
        )

        if switch_id is None:
            return None

        return (
            self.gestor_topologia
            .obtener_padre(
                switch_id
            )
        )

    # ======================================================
    # PRIORIDAD
    # ======================================================

    def calcular_prioridad(
        self,
        switch: dict,
        estado: str,
        descendientes: int
    ) -> str:
        """
        Calcula prioridad considerando:

        - Estado correlacionado.
        - Rol.
        - Criticidad documentada.
        - Cantidad de descendientes.
        """
        if estado == self.ESTADO_OPERATIVO:
            return self.PRIORIDAD_INFORMATIVA

        if estado == self.ESTADO_SIN_COMPROBAR:
            return self.PRIORIDAD_INFORMATIVA

        if estado == self.ESTADO_POSIBLEMENTE_AFECTADO:
            return self.PRIORIDAD_BAJA

        rol = str(
            switch.get("rol")
            or "NO DEFINIDO"
        ).upper()

        criticidad = str(
            switch.get("criticidad")
            or "NO DEFINIDA"
        ).upper()

        if rol == "CORE":
            return self.PRIORIDAD_CRITICA

        if criticidad == "CRITICA":
            return self.PRIORIDAD_CRITICA

        if descendientes >= 5:
            return self.PRIORIDAD_CRITICA

        if criticidad == "ALTA":
            return self.PRIORIDAD_ALTA

        if descendientes >= 2:
            return self.PRIORIDAD_ALTA

        if criticidad == "MEDIA":
            return self.PRIORIDAD_MEDIA

        if descendientes == 1:
            return self.PRIORIDAD_MEDIA

        if criticidad == "BAJA":
            return self.PRIORIDAD_BAJA

        return self.PRIORIDAD_MEDIA

    # ======================================================
    # DIAGNÓSTICO INDIVIDUAL
    # ======================================================

    def diagnosticar_switch(
        self,
        switch: dict,
        mapa_snmp: dict[str, dict]
    ) -> DiagnosticoSwitch:
        """
        Genera el diagnóstico consolidado de un switch.
        """
        switch_id = switch.get(
            "id"
        )

        ip = self.limpiar_texto(
            switch.get("ip")
        )

        nombre = self.nombre_visible(
            switch
        )

        padre = self.obtener_padre(
            switch
        )

        hijos = (
            self.gestor_topologia
            .obtener_hijos(
                switch_id
            )
            if switch_id is not None
            else []
        )

        descendientes_lista = (
            self.gestor_topologia
            .obtener_descendientes(
                switch_id
            )
            if switch_id is not None
            else []
        )

        cantidad_hijos = len(
            hijos
        )

        cantidad_descendientes = len(
            descendientes_lista
        )

        responde = self.switch_responde(
            switch,
            mapa_snmp
        )

        ancestro_caido = None

        if responde is True:
            estado = self.ESTADO_OPERATIVO

            detalle = (
                "El switch respondió correctamente "
                "a la comprobación SNMP."
            )

            recomendacion = (
                "No se requiere una acción inmediata."
            )

        elif responde is None:
            estado = self.ESTADO_SIN_COMPROBAR

            detalle = (
                "No existe un resultado SNMP para "
                "este switch."
            )

            recomendacion = (
                "Verificar que posea una IP válida y "
                "volver a ejecutar el descubrimiento."
            )

        else:
            ancestro_caido = (
                self.encontrar_ancestro_sin_respuesta(
                    switch,
                    mapa_snmp
                )
            )

            if ancestro_caido is not None:
                estado = (
                    self.ESTADO_POSIBLEMENTE_AFECTADO
                )

                detalle = (
                    f"El switch no respondió, pero el "
                    f"ancestro "
                    f"{self.nombre_visible(ancestro_caido)} "
                    f"({ancestro_caido.get('ip')}) "
                    "tampoco respondió. La falta de acceso "
                    "podría ser una consecuencia de la "
                    "caída del enlace o equipo superior."
                )

                recomendacion = (
                    "Revisar primero el ancestro sin "
                    "respuesta antes de diagnosticar este "
                    "switch como una falla independiente."
                )

            elif padre is not None:
                padre_responde = self.switch_responde(
                    padre,
                    mapa_snmp
                )

                if padre_responde is True:
                    estado = self.ESTADO_FALLA_LOCAL

                    detalle = (
                        "El switch no respondió por SNMP, "
                        "pero su padre directo sí está "
                        "operativo. Esto sugiere una falla "
                        "local, SNMP deshabilitado, una "
                        "comunidad distinta o un problema "
                        "en el enlace hacia este equipo."
                    )

                    recomendacion = (
                        "Revisar alimentación, enlace de "
                        "subida, configuración SNMP y "
                        "conectividad IP del switch."
                    )

                else:
                    estado = self.ESTADO_SIN_RESPUESTA

                    detalle = (
                        "El switch no respondió por SNMP "
                        "y no existe suficiente información "
                        "para atribuir la falla a un ancestro."
                    )

                    recomendacion = (
                        "Revisar conectividad, alimentación "
                        "y configuración SNMP."
                    )

            else:
                estado = self.ESTADO_SIN_RESPUESTA

                detalle = (
                    "El switch no respondió por SNMP y no "
                    "tiene un padre documentado."
                )

                recomendacion = (
                    "Completar la topología y revisar "
                    "conectividad, alimentación y SNMP."
                )

        prioridad = self.calcular_prioridad(
            switch=switch,
            estado=estado,
            descendientes=cantidad_descendientes
        )

        datos_snmp = (
            mapa_snmp.get(
                ip,
                {}
            )
            if ip
            else {}
        )

        return DiagnosticoSwitch(
            switch_id=switch_id,
            ip=ip,
            nombre=nombre,
            ubicacion=self.limpiar_texto(
                switch.get("ubicacion")
            ),
            rol=str(
                switch.get("rol")
                or "NO DEFINIDO"
            ),
            criticidad=str(
                switch.get("criticidad")
                or "NO DEFINIDA"
            ),
            estado=estado,
            prioridad=prioridad,
            responde_snmp=responde,
            padre_id=(
                padre.get("id")
                if padre
                else None
            ),
            padre_ip=(
                padre.get("ip")
                if padre
                else None
            ),
            padre_nombre=(
                self.nombre_visible(padre)
                if padre
                else None
            ),
            ancestro_caido_id=(
                ancestro_caido.get("id")
                if ancestro_caido
                else None
            ),
            ancestro_caido_ip=(
                ancestro_caido.get("ip")
                if ancestro_caido
                else None
            ),
            ancestro_caido_nombre=(
                self.nombre_visible(
                    ancestro_caido
                )
                if ancestro_caido
                else None
            ),
            hijos_directos=cantidad_hijos,
            descendientes=cantidad_descendientes,
            detalle=detalle,
            recomendacion=recomendacion,
            datos={
                "nombre_snmp": datos_snmp.get(
                    "nombre_snmp"
                ),
                "descripcion_snmp": datos_snmp.get(
                    "descripcion_snmp"
                ),
                "tiempo_ms": datos_snmp.get(
                    "tiempo_ms"
                ),
                "detalle_snmp": datos_snmp.get(
                    "detalle"
                )
            }
        )

    # ======================================================
    # DIAGNÓSTICO GENERAL
    # ======================================================

    def ordenar_diagnosticos(
        self,
        diagnosticos: list[DiagnosticoSwitch]
    ) -> list[DiagnosticoSwitch]:
        """
        Ordena primero las incidencias más importantes.
        """
        return sorted(
            diagnosticos,
            key=lambda diagnostico: (
                self.ORDEN_PRIORIDADES.get(
                    diagnostico.prioridad,
                    99
                ),
                self.ORDEN_ESTADOS.get(
                    diagnostico.estado,
                    99
                ),
                diagnostico.ip or "",
                diagnostico.nombre
            )
        )

    def analizar(
        self,
        descubrimiento
    ) -> ResultadoDiagnosticoRed:
        """
        Analiza todos los switches registrados.
        """
        mapa_snmp = self.construir_mapa_snmp(
            descubrimiento
        )

        switches = (
            self.gestor_topologia
            .listar_switches()
        )

        diagnosticos = [
            self.diagnosticar_switch(
                switch=switch,
                mapa_snmp=mapa_snmp
            )
            for switch in switches
        ]

        diagnosticos = self.ordenar_diagnosticos(
            diagnosticos
        )

        return ResultadoDiagnosticoRed(
            diagnosticos=diagnosticos
        )

    # ======================================================
    # PRESENTACIÓN EN CONSOLA
    # ======================================================

    @staticmethod
    def color_prioridad(
        prioridad: str
    ) -> str:
        """Devuelve el color visual de una prioridad."""
        mapa = {
            MotorDiagnosticoRed.PRIORIDAD_CRITICA: "red",
            MotorDiagnosticoRed.PRIORIDAD_ALTA: "bright_red",
            MotorDiagnosticoRed.PRIORIDAD_MEDIA: "yellow",
            MotorDiagnosticoRed.PRIORIDAD_BAJA: "cyan",
            MotorDiagnosticoRed.PRIORIDAD_INFORMATIVA: "green"
        }

        return mapa.get(
            str(prioridad).upper(),
            "white"
        )

    @staticmethod
    def icono_prioridad(
        prioridad: str
    ) -> str:
        """Devuelve un icono consistente para cada prioridad."""
        mapa = {
            MotorDiagnosticoRed.PRIORIDAD_CRITICA: "🔴",
            MotorDiagnosticoRed.PRIORIDAD_ALTA: "🟠",
            MotorDiagnosticoRed.PRIORIDAD_MEDIA: "🟡",
            MotorDiagnosticoRed.PRIORIDAD_BAJA: "🔵",
            MotorDiagnosticoRed.PRIORIDAD_INFORMATIVA: "🟢"
        }

        return mapa.get(
            str(prioridad).upper(),
            "⚪"
        )

    @staticmethod
    def icono_estado(
        estado: str
    ) -> str:
        """Devuelve un icono según el estado correlacionado."""
        mapa = {
            MotorDiagnosticoRed.ESTADO_OPERATIVO: "🟢",
            MotorDiagnosticoRed.ESTADO_FALLA_LOCAL: "🔴",
            MotorDiagnosticoRed.ESTADO_POSIBLEMENTE_AFECTADO: "🟡",
            MotorDiagnosticoRed.ESTADO_SIN_RESPUESTA: "🔴",
            MotorDiagnosticoRed.ESTADO_SIN_COMPROBAR: "⚪"
        }

        return mapa.get(
            str(estado).upper(),
            "⚪"
        )

    @staticmethod
    def valor_visible(
        valor: Any,
        predeterminado: str = "-"
    ) -> str:
        """Convierte valores vacíos en un texto presentable."""
        if valor is None:
            return predeterminado

        texto = str(valor).strip()
        return texto or predeterminado

    def construir_tarjetas_resumen(
        self,
        resumen: dict[str, Any]
    ) -> list[dict]:
        """Construye las tarjetas principales del diagnóstico."""
        fallas = (
            resumen["fallas_locales_probables"]
            + resumen["sin_respuesta"]
        )

        return [
            {
                "titulo": "🖧 Analizados",
                "contenido": str(
                    resumen["switches_analizados"]
                ),
                "color": "bright_blue"
            },
            {
                "titulo": "🟢 Operativos",
                "contenido": str(
                    resumen["operativos"]
                ),
                "color": "green"
            },
            {
                "titulo": "🔴 Fallas",
                "contenido": str(fallas),
                "color": (
                    "red"
                    if fallas
                    else "green"
                )
            },
            {
                "titulo": "🟡 Afectados",
                "contenido": str(
                    resumen["posiblemente_afectados"]
                ),
                "color": (
                    "yellow"
                    if resumen["posiblemente_afectados"]
                    else "green"
                )
            },
            {
                "titulo": "⚪ Sin comprobar",
                "contenido": str(
                    resumen["sin_comprobar"]
                ),
                "color": (
                    "grey50"
                    if resumen["sin_comprobar"]
                    else "green"
                )
            }
        ]

    def construir_estados_prioridad(
        self,
        resumen: dict[str, Any]
    ) -> list[dict]:
        """Construye el panel de prioridades."""
        elementos = [
            (
                "🔴",
                "Críticas.................. "
                f"{resumen['prioridad_critica']}",
                "red"
            ),
            (
                "🟠",
                "Altas..................... "
                f"{resumen['prioridad_alta']}",
                "bright_red"
            ),
            (
                "🟡",
                "Medias.................... "
                f"{resumen['prioridad_media']}",
                "yellow"
            ),
            (
                "🔵",
                "Bajas..................... "
                f"{resumen['prioridad_baja']}",
                "cyan"
            ),
            (
                "🟢",
                "Informativas.............. "
                f"{resumen['prioridad_informativa']}",
                "green"
            )
        ]

        return [
            {
                "icono": icono,
                "texto": texto,
                "color": color
            }
            for icono, texto, color in elementos
        ]

    def mostrar_resultado(
        self,
        resultado: ResultadoDiagnosticoRed
    ):
        """
        Muestra el diagnóstico correlacionado con una
        presentación visual e interacción por incidencia.
        """
        resumen = resultado.obtener_resumen()

        visual.limpiar()
        visual.titulo(
            "DIAGNÓSTICO CORRELACIONADO DE RED",
            "Disponibilidad, topología, criticidad e impacto"
        )

        visual.dashboard(
            self.construir_tarjetas_resumen(
                resumen
            )
        )

        visual.panel_estado(
            "Prioridades detectadas",
            self.construir_estados_prioridad(
                resumen
            ),
            "magenta"
        )

        principales = (
            resultado.obtener_incidencias_principales()
        )

        self.mostrar_tabla_incidencias(
            principales
        )

        afectados = resultado.obtener_por_estado(
            self.ESTADO_POSIBLEMENTE_AFECTADO
        )

        self.mostrar_tabla_afectados(
            afectados
        )

        visual.pie(
            [
                f"{resumen['switches_analizados']} switches",
                f"{resumen['operativos']} operativos",
                f"{len(principales)} incidencias principales",
                "Consulta de solo lectura"
            ]
        )

        if principales:
            self.ejecutar_selector_incidencia(
                principales
            )

    def mostrar_tabla_incidencias(
        self,
        principales: list[DiagnosticoSwitch]
    ) -> None:
        """Muestra las causas principales en una tabla."""
        if not principales:
            visual.ok(
                "No se detectaron incidencias principales."
            )
            return

        filas = []

        for numero, diagnostico in enumerate(
            principales,
            start=1
        ):
            color = self.color_prioridad(
                diagnostico.prioridad
            )

            filas.append(
                (
                    str(numero),
                    (
                        f"[{color}]"
                        f"{self.icono_prioridad(diagnostico.prioridad)} "
                        f"{diagnostico.prioridad}"
                        f"[/{color}]"
                    ),
                    self.valor_visible(
                        diagnostico.nombre
                    ),
                    self.valor_visible(
                        diagnostico.ip
                    ),
                    (
                        f"{self.icono_estado(diagnostico.estado)} "
                        f"{diagnostico.estado}"
                    ),
                    self.valor_visible(
                        diagnostico.rol
                    ),
                    str(
                        diagnostico.descendientes
                    )
                )
            )

        visual.tabla(
            f"Incidencias principales ({len(principales)})",
            [
                {
                    "nombre": "N.º",
                    "justify": "right",
                    "no_wrap": True
                },
                {
                    "nombre": "Prioridad",
                    "no_wrap": True
                },
                "Switch",
                {
                    "nombre": "IP",
                    "no_wrap": True
                },
                "Estado",
                {
                    "nombre": "Rol",
                    "no_wrap": True
                },
                {
                    "nombre": "Desc.",
                    "justify": "right",
                    "no_wrap": True
                }
            ],
            filas,
            expandir=True,
            mostrar_lineas=True
        )

        visual.info(
            "Escribe el número de una incidencia para abrir "
            "su ficha completa."
        )

    def mostrar_tabla_afectados(
        self,
        afectados: list[DiagnosticoSwitch]
    ) -> None:
        """Muestra switches potencialmente afectados."""
        if not afectados:
            return

        filas = []

        for diagnostico in afectados:
            filas.append(
                (
                    self.valor_visible(
                        diagnostico.nombre
                    ),
                    self.valor_visible(
                        diagnostico.ip
                    ),
                    self.valor_visible(
                        diagnostico.ancestro_caido_nombre
                    ),
                    self.valor_visible(
                        diagnostico.ancestro_caido_ip
                    ),
                    str(
                        diagnostico.descendientes
                    )
                )
            )

        visual.tabla(
            f"Equipos posiblemente afectados ({len(afectados)})",
            [
                "Switch",
                {
                    "nombre": "IP",
                    "no_wrap": True
                },
                "Ancestro sin respuesta",
                {
                    "nombre": "IP ancestro",
                    "no_wrap": True
                },
                {
                    "nombre": "Desc.",
                    "justify": "right",
                    "no_wrap": True
                }
            ],
            filas,
            expandir=True
        )

        visual.warning(
            "Estos equipos pueden no ser la causa principal. "
            "Conviene revisar primero el ancestro indicado."
        )

    def ejecutar_selector_incidencia(
        self,
        principales: list[DiagnosticoSwitch]
    ) -> None:
        """Permite abrir la ficha de una incidencia."""
        while True:
            seleccion = input(
                "\nIncidencia para ver detalle "
                "[0 para volver]: "
            ).strip()

            if seleccion in {"", "0"}:
                return

            try:
                indice = int(seleccion)
            except ValueError:
                visual.error(
                    "Debes escribir el número de una incidencia."
                )
                continue

            if indice < 1 or indice > len(principales):
                visual.error(
                    "La incidencia seleccionada no existe."
                )
                continue

            self.mostrar_ficha_incidencia(
                principales[indice - 1]
            )

            input(
                "\nPresiona ENTER para volver al diagnóstico..."
            )

            # Se vuelve a la tabla sin ejecutar nuevamente SNMP.
            resumen = ResultadoDiagnosticoRed(
                diagnosticos=[
                    *principales
                ]
            )

            visual.limpiar()
            return

    def mostrar_ficha_incidencia(
        self,
        diagnostico: DiagnosticoSwitch
    ) -> None:
        """Muestra toda la información disponible de una falla."""
        visual.limpiar()

        color = self.color_prioridad(
            diagnostico.prioridad
        )

        visual.titulo(
            f"INCIDENCIA — {diagnostico.nombre}",
            (
                f"{diagnostico.prioridad} · "
                f"{diagnostico.estado}"
            ),
            color
        )

        visual.dashboard(
            [
                {
                    "titulo": "🌐 IP",
                    "contenido": self.valor_visible(
                        diagnostico.ip
                    ),
                    "color": "cyan"
                },
                {
                    "titulo": "🖧 Rol",
                    "contenido": self.valor_visible(
                        diagnostico.rol
                    ),
                    "color": "bright_blue"
                },
                {
                    "titulo": "⚠ Criticidad",
                    "contenido": self.valor_visible(
                        diagnostico.criticidad
                    ),
                    "color": color
                },
                {
                    "titulo": "🌳 Descendientes",
                    "contenido": str(
                        diagnostico.descendientes
                    ),
                    "color": (
                        "red"
                        if diagnostico.descendientes >= 5
                        else "yellow"
                        if diagnostico.descendientes
                        else "green"
                    )
                }
            ]
        )

        datos_generales = [
            ("Nombre", diagnostico.nombre),
            (
                "Ubicación",
                self.valor_visible(
                    diagnostico.ubicacion
                )
            ),
            (
                "Estado",
                diagnostico.estado
            ),
            (
                "Prioridad",
                diagnostico.prioridad
            ),
            (
                "Padre directo",
                self.valor_visible(
                    diagnostico.padre_nombre
                )
            ),
            (
                "IP del padre",
                self.valor_visible(
                    diagnostico.padre_ip
                )
            ),
            (
                "Ancestro sin respuesta",
                self.valor_visible(
                    diagnostico.ancestro_caido_nombre
                )
            ),
            (
                "IP del ancestro",
                self.valor_visible(
                    diagnostico.ancestro_caido_ip
                )
            ),
            (
                "Hijos directos",
                str(
                    diagnostico.hijos_directos
                )
            ),
            (
                "Descendientes",
                str(
                    diagnostico.descendientes
                )
            )
        ]

        visual.tabla(
            "Información correlacionada",
            [
                {
                    "nombre": "Campo",
                    "style": "cyan",
                    "no_wrap": True
                },
                "Valor"
            ],
            datos_generales,
            expandir=True,
            mostrar_lineas=True
        )

        visual.panel_estado(
            "Diagnóstico",
            [
                {
                    "icono": self.icono_estado(
                        diagnostico.estado
                    ),
                    "texto": diagnostico.detalle,
                    "color": color
                }
            ],
            color
        )

        visual.panel_acciones(
            "Acción recomendada",
            [
                {
                    "icono": "🛠",
                    "texto": diagnostico.recomendacion,
                    "color": "yellow"
                }
            ],
            "yellow"
        )

        datos_snmp = diagnostico.datos or {}

        if any(
            valor not in (None, "")
            for valor in datos_snmp.values()
        ):
            filas_snmp = [
                (
                    "Nombre SNMP",
                    self.valor_visible(
                        datos_snmp.get("nombre_snmp")
                    )
                ),
                (
                    "Descripción SNMP",
                    self.valor_visible(
                        datos_snmp.get("descripcion_snmp")
                    )
                ),
                (
                    "Tiempo de respuesta",
                    (
                        f"{datos_snmp.get('tiempo_ms'):.2f} ms"
                        if isinstance(
                            datos_snmp.get("tiempo_ms"),
                            (int, float)
                        )
                        else "-"
                    )
                ),
                (
                    "Detalle SNMP",
                    self.valor_visible(
                        datos_snmp.get("detalle_snmp")
                    )
                )
            ]

            visual.tabla(
                "Información SNMP",
                [
                    {
                        "nombre": "Campo",
                        "style": "magenta",
                        "no_wrap": True
                    },
                    "Valor"
                ],
                filas_snmp,
                expandir=True
            )

        visual.info(
            "El diagnóstico es de solo lectura. NetInventory "
            "no modifica el switch ni la topología."
        )