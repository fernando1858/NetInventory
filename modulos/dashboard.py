from collections import Counter
from datetime import datetime
from pathlib import Path

from config import (
    AREA_RESPONSABLE,
    NOMBRE_APLICACION,
    ORGANIZACION,
    SEPARADOR_PRINCIPAL,
    SEPARADOR_SECUNDARIO,
    VERSION_APLICACION
)


class Dashboard:
    """
    Centro de operaciones inicial de NetInventory.

    Resume inventario, switches, topología, cobertura y
    tareas pendientes sin ejecutar un diagnóstico SNMP
    completo durante el inicio.

    Este módulo es exclusivamente de consulta.
    """

    def __init__(
        self,
        inventario,
        gestor_accesos,
        gestor_relaciones,
        gestor_topologia,
        analizador_red,
        revisor_incompletos,
        ruta_excel
    ):
        self.inventario = inventario
        self.gestor_accesos = gestor_accesos
        self.gestor_relaciones = gestor_relaciones
        self.gestor_topologia = gestor_topologia
        self.analizador_red = analizador_red
        self.revisor_incompletos = revisor_incompletos
        self.ruta_excel = Path(ruta_excel)

    # ======================================================
    # UTILIDADES
    # ======================================================

    @staticmethod
    def texto_estado(
        correcto,
        texto_correcto,
        texto_advertencia
    ):
        return (
            f"[OK] {texto_correcto}"
            if correcto
            else f"[AVISO] {texto_advertencia}"
        )

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

    def obtener_fecha_excel(self):
        if not self.ruta_excel.exists():
            return "Archivo no encontrado"

        fecha = datetime.fromtimestamp(
            self.ruta_excel.stat().st_mtime
        )

        return fecha.strftime(
            "%d-%m-%Y %H:%M:%S"
        )

    def obtener_hojas_procesadas(self):
        return len(
            {
                registro.get("hoja")
                for registro in self.inventario.registros
                if registro.get("hoja") is not None
            }
        )

    def obtener_bloques_detectados(self):
        return len(
            {
                (
                    registro.get("hoja"),
                    registro.get("bloque")
                )
                for registro in self.inventario.registros
                if (
                    registro.get("hoja") is not None
                    and registro.get("bloque") is not None
                )
            }
        )

    # ======================================================
    # INVENTARIO
    # ======================================================

    def obtener_resumen_inventario(self):
        registros = self.inventario.registros

        tipos = Counter(
            registro.get("tipo") or "Sin tipo"
            for registro in registros
        )

        con_equipo = sum(
            registro.get("equipo") is not None
            for registro in registros
        )

        disponibles = sum(
            self.inventario.equipo_esta_disponible(
                registro.get("equipo")
            )
            for registro in registros
        )

        desconocidos = sum(
            self.inventario.equipo_es_desconocido(
                registro.get("equipo")
            )
            for registro in registros
        )

        con_vlan = sum(
            registro.get("vlan") is not None
            for registro in registros
        )

        return {
            "registros": len(registros),
            "con_equipo": con_equipo,
            "disponibles": disponibles,
            "desconocidos": desconocidos,
            "con_vlan": con_vlan,
            "antenas": tipos.get("Antena", 0),
            "camaras": tipos.get("Cámara", 0),
            "telefonos": tipos.get("Teléfono IP", 0),
            "equipos": tipos.get("Equipo", 0),
            "troncales": tipos.get("Troncal", 0),
            "sin_tipo": tipos.get("Sin tipo", 0)
        }

    # ======================================================
    # RELACIONES Y TOPOLOGÍA
    # ======================================================

    def obtener_estado_relaciones(self):
        try:
            resultado = (
                self.gestor_relaciones
                .validar_relaciones()
            )

            return {
                "validas": len(
                    resultado.get("validas", [])
                ),
                "invalidas": len(
                    resultado.get("invalidas", [])
                ),
                "sin_relacion": len(
                    resultado.get("sin_relacion", [])
                )
            }

        except Exception:
            return {
                "validas": 0,
                "invalidas": 0,
                "sin_relacion": 0
            }

    def obtener_estado_topologia(self):
        try:
            return self.gestor_topologia.validar_topologia()

        except Exception:
            return {
                "total_switches": 0,
                "sin_clasificar": [],
                "sin_criticidad": [],
                "sin_padre": [],
                "ciclos": [],
                "padres_invalidos": [],
                "correcta": False
            }

    def obtener_cobertura(self):
        try:
            return self.analizador_red.auditar_cobertura_global()

        except Exception:
            return {
                "total": 0,
                "cubiertos": [],
                "sin_relacion": [],
                "relaciones_invalidas": [],
                "bloques_sin_registros": [],
                "porcentaje": 0.0
            }

    # ======================================================
    # RECOMENDACIONES
    # ======================================================

    def construir_recomendaciones(
        self,
        resumen
    ):
        recomendaciones = []

        if resumen["relaciones_invalidas"] > 0:
            recomendaciones.append(
                "Corregir las relaciones inválidas entre "
                "switches y bloques del Excel."
            )

        if resumen["switches_sin_relacion"] > 0:
            recomendaciones.append(
                f"Relacionar {resumen['switches_sin_relacion']} "
                "switches pendientes con su bloque del inventario."
            )

        if resumen["cobertura_pendiente"] > 0:
            recomendaciones.append(
                f"Revisar {resumen['cobertura_pendiente']} "
                "switches que todavía no aportan datos al "
                "Centro de Impacto."
            )

        if resumen["bloques_incompletos"] > 0:
            recomendaciones.append(
                f"Completar {resumen['bloques_incompletos']} "
                "bloques con información pendiente."
            )

        if resumen["filas_incompletas"] > 0:
            recomendaciones.append(
                f"Revisar {resumen['filas_incompletas']} "
                "filas incompletas detectadas en el Excel."
            )

        if resumen["duplicados"] > 0:
            recomendaciones.append(
                f"Resolver {resumen['duplicados']} puertos "
                "duplicados en el inventario."
            )

        if resumen["sin_clasificar"] > 0:
            recomendaciones.append(
                f"Clasificar {resumen['sin_clasificar']} "
                "switches dentro de la topología."
            )

        if resumen["sin_criticidad"] > 0:
            recomendaciones.append(
                f"Definir criticidad para "
                f"{resumen['sin_criticidad']} switches."
            )

        if resumen["sin_padre"] > 0:
            recomendaciones.append(
                f"Revisar {resumen['sin_padre']} switches "
                "sin padre documentado."
            )

        if resumen["ciclos"] > 0:
            recomendaciones.append(
                "Corregir ciclos detectados en la topología."
            )

        if resumen["padres_invalidos"] > 0:
            recomendaciones.append(
                "Corregir referencias a switches padre "
                "que no existen."
            )

        if not recomendaciones:
            recomendaciones.append(
                "No existen tareas críticas pendientes "
                "en la documentación actual."
            )

        return recomendaciones

    def obtener_estado_general(
        self,
        resumen
    ):
        criticos = (
            resumen["relaciones_invalidas"]
            + resumen["duplicados"]
            + resumen["ciclos"]
            + resumen["padres_invalidos"]
        )

        if criticos > 0:
            return "REQUIERE REVISIÓN"

        pendientes = (
            resumen["switches_sin_relacion"]
            + resumen["cobertura_pendiente"]
            + resumen["bloques_incompletos"]
            + resumen["filas_incompletas"]
            + resumen["sin_clasificar"]
            + resumen["sin_criticidad"]
            + resumen["sin_padre"]
        )

        if pendientes > 0:
            return "OPERATIVO CON PENDIENTES"

        return "DOCUMENTACIÓN COMPLETA"

    # ======================================================
    # RESUMEN GENERAL
    # ======================================================

    def obtener_resumen(self):
        relaciones = self.obtener_estado_relaciones()
        topologia = self.obtener_estado_topologia()
        cobertura = self.obtener_cobertura()
        inventario = self.obtener_resumen_inventario()

        switches = len(
            self.gestor_accesos.listar_todos()
        )

        bloques_incompletos = (
            self.revisor_incompletos
            .contar_bloques_incompletos()
        )

        filas_incompletas = (
            self.revisor_incompletos
            .contar_filas_incompletas()
        )

        duplicados = len(
            self.inventario.duplicados_detectados
        )

        cobertura_pendiente = (
            len(cobertura["sin_relacion"])
            + len(cobertura["relaciones_invalidas"])
            + len(cobertura["bloques_sin_registros"])
        )

        resumen = {
            "archivo": self.ruta_excel.name,
            "actualizacion_excel": self.obtener_fecha_excel(),
            "hojas": self.obtener_hojas_procesadas(),
            "bloques": self.obtener_bloques_detectados(),
            "switches": switches,
            "relaciones_validas": relaciones["validas"],
            "relaciones_invalidas": relaciones["invalidas"],
            "switches_sin_relacion": relaciones["sin_relacion"],
            "bloques_incompletos": bloques_incompletos,
            "filas_incompletas": filas_incompletas,
            "duplicados": duplicados,
            "cobertura_total": cobertura["total"],
            "switches_cubiertos": len(cobertura["cubiertos"]),
            "cobertura_porcentaje": cobertura["porcentaje"],
            "cobertura_pendiente": cobertura_pendiente,
            "sin_clasificar": len(
                topologia["sin_clasificar"]
            ),
            "sin_criticidad": len(
                topologia["sin_criticidad"]
            ),
            "sin_padre": len(
                topologia["sin_padre"]
            ),
            "ciclos": len(
                topologia["ciclos"]
            ),
            "padres_invalidos": len(
                topologia["padres_invalidos"]
            ),
            "topologia_correcta": bool(
                topologia["correcta"]
            ),
            **inventario
        }

        resumen["estado_general"] = (
            self.obtener_estado_general(
                resumen
            )
        )

        resumen["recomendaciones"] = (
            self.construir_recomendaciones(
                resumen
            )
        )

        return resumen

    # ======================================================
    # PRESENTACIÓN
    # ======================================================

    def mostrar_encabezado(self):
        ancho = len(SEPARADOR_PRINCIPAL)

        print(f"\n{SEPARADOR_PRINCIPAL}")
        print(
            f"{NOMBRE_APLICACION.upper()} "
            "- CENTRO DE OPERACIONES"
            .center(ancho)
        )
        print(
            f"Versión {VERSION_APLICACION}".center(ancho)
        )
        print(
            ORGANIZACION.center(ancho)
        )
        print(
            AREA_RESPONSABLE.center(ancho)
        )
        print(SEPARADOR_PRINCIPAL)

    def mostrar(self):
        resumen = self.obtener_resumen()

        self.mostrar_encabezado()

        print(
            f"\nEstado general: "
            f"{resumen['estado_general']}"
        )
        print(
            f"Excel: {resumen['archivo']}"
        )
        print(
            "Última modificación local: "
            f"{resumen['actualizacion_excel']}"
        )

        print(f"\n{SEPARADOR_SECUNDARIO}")
        print(
            "INFRAESTRUCTURA".center(
                len(SEPARADOR_SECUNDARIO)
            )
        )
        print(SEPARADOR_SECUNDARIO)

        print(
            f"Switches registrados: "
            f"{resumen['switches']}"
        )
        print(
            f"Relaciones válidas: "
            f"{resumen['relaciones_validas']}"
        )
        print(
            "Cobertura del inventario: "
            f"{resumen['switches_cubiertos']} de "
            f"{resumen['cobertura_total']} "
            f"({resumen['cobertura_porcentaje']} %)"
        )
        print(
            self.texto_estado(
                resumen["topologia_correcta"],
                "Topología estructuralmente válida.",
                "La topología contiene observaciones."
            )
        )

        print(f"\n{SEPARADOR_SECUNDARIO}")
        print(
            "INVENTARIO DOCUMENTADO".center(
                len(SEPARADOR_SECUNDARIO)
            )
        )
        print(SEPARADOR_SECUNDARIO)

        print(
            f"Hojas procesadas: {resumen['hojas']}"
        )
        print(
            f"Bloques detectados: {resumen['bloques']}"
        )
        print(
            f"Registros documentados: "
            f"{resumen['registros']}"
        )
        print(
            f"Registros con equipo: "
            f"{resumen['con_equipo']}"
        )

        print(
            "\n"
            f"AP / Antenas: {resumen['antenas']} | "
            f"Cámaras: {resumen['camaras']} | "
            f"Teléfonos IP: {resumen['telefonos']}"
        )
        print(
            f"Equipos: {resumen['equipos']} | "
            f"Troncales: {resumen['troncales']} | "
            f"Puertos disponibles: {resumen['disponibles']}"
        )

        print(f"\n{SEPARADOR_SECUNDARIO}")
        print(
            "CONTROL DE CALIDAD".center(
                len(SEPARADOR_SECUNDARIO)
            )
        )
        print(SEPARADOR_SECUNDARIO)

        print(
            f"Bloques incompletos: "
            f"{resumen['bloques_incompletos']}"
        )
        print(
            f"Filas incompletas: "
            f"{resumen['filas_incompletas']}"
        )
        print(
            f"Puertos repetidos: "
            f"{resumen['duplicados']}"
        )
        print(
            f"Registros desconocidos: "
            f"{resumen['desconocidos']}"
        )
        print(
            f"Registros sin tipo: "
            f"{resumen['sin_tipo']}"
        )
        print(
            f"Registros con VLAN: "
            f"{resumen['con_vlan']}"
        )

        print(f"\n{SEPARADOR_SECUNDARIO}")
        print(
            "TOPOLOGÍA Y RELACIONES".center(
                len(SEPARADOR_SECUNDARIO)
            )
        )
        print(SEPARADOR_SECUNDARIO)

        print(
            f"Relaciones inválidas: "
            f"{resumen['relaciones_invalidas']}"
        )
        print(
            f"Switches sin relación: "
            f"{resumen['switches_sin_relacion']}"
        )
        print(
            f"Switches sin clasificar: "
            f"{resumen['sin_clasificar']}"
        )
        print(
            f"Switches sin criticidad: "
            f"{resumen['sin_criticidad']}"
        )
        print(
            f"Switches sin padre: "
            f"{resumen['sin_padre']}"
        )
        print(
            f"Ciclos detectados: "
            f"{resumen['ciclos']}"
        )
        print(
            f"Padres inválidos: "
            f"{resumen['padres_invalidos']}"
        )

        print(f"\n{SEPARADOR_SECUNDARIO}")
        print(
            "ACCIONES RECOMENDADAS".center(
                len(SEPARADOR_SECUNDARIO)
            )
        )
        print(SEPARADOR_SECUNDARIO)

        for numero, recomendacion in enumerate(
            resumen["recomendaciones"][:6],
            start=1
        ):
            print(
                f"{numero}. {recomendacion}"
            )

        print(
            "\nSNMP no se consulta automáticamente al iniciar. "
            "Usa el Centro de Salud o el Centro SNMP para "
            "obtener el estado en tiempo real."
        )

        print(SEPARADOR_PRINCIPAL)