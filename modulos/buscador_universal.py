from dataclasses import dataclass
from typing import Any


@dataclass
class ResultadoBusqueda:
    """
    Representa un resultado uniforme del buscador universal.
    """

    categoria: str
    titulo: str
    subtitulo: str
    coincidencias: list[str]
    datos: dict[str, Any]
    prioridad: int = 100


class BuscadorUniversal:
    """
    Busca información en el inventario, switches y relaciones.

    Este módulo solamente consulta datos cargados en memoria
    y almacenados en SQLite. No modifica el Excel ni la base
    de datos.
    """

    MAXIMO_RESULTADOS = 100

    def __init__(
        self,
        inventario,
        gestor_accesos,
        gestor_relaciones
    ):
        self.inventario = inventario
        self.gestor_accesos = gestor_accesos
        self.gestor_relaciones = gestor_relaciones

    def normalizar(self, valor: Any) -> str:
        """
        Normaliza texto utilizando la lógica del inventario.
        """
        return self.inventario.normalizar_texto(
            valor
        )

    @staticmethod
    def valor_visible(
        valor: Any,
        texto_vacio: str = "Sin información"
    ) -> str:
        """
        Convierte valores vacíos en un texto visible.
        """
        if valor is None:
            return texto_vacio

        texto = str(valor).strip()

        if not texto:
            return texto_vacio

        return texto

    def preparar_consulta(
        self,
        consulta: str
    ) -> dict[str, Any]:
        """
        Interpreta el texto ingresado y detecta casos como:

        - IP completa.
        - Último octeto.
        - VLAN indicada mediante texto.
        - Puerto indicado mediante texto.
        """
        texto_original = str(
            consulta or ""
        ).strip()

        texto_normalizado = self.normalizar(
            texto_original
        )

        palabras = [
            palabra
            for palabra in texto_normalizado.split()
            if palabra
        ]

        numero = None

        if texto_normalizado.isdigit():
            numero = int(
                texto_normalizado
            )

        vlan = None

        if len(palabras) >= 2 and palabras[0] == "vlan":
            try:
                vlan = int(
                    palabras[1]
                )
            except ValueError:
                vlan = palabras[1]

        puerto = None

        if len(palabras) >= 2 and palabras[0] in {
            "puerto",
            "port"
        }:
            try:
                puerto = int(
                    palabras[1]
                )
            except ValueError:
                puerto = None

        es_ip = (
            len(texto_original.split(".")) == 4
            and all(
                parte.isdigit()
                for parte in texto_original.split(".")
            )
        )

        return {
            "original": texto_original,
            "normalizada": texto_normalizado,
            "palabras": palabras,
            "numero": numero,
            "vlan": vlan,
            "puerto": puerto,
            "es_ip": es_ip
        }

    def calcular_coincidencias(
        self,
        consulta: dict[str, Any],
        campos: dict[str, Any]
    ) -> tuple[list[str], int]:
        """
        Determina qué campos coinciden y asigna prioridad.

        Una coincidencia exacta tiene mayor prioridad que
        una coincidencia parcial.
        """
        texto_buscado = consulta[
            "normalizada"
        ]

        coincidencias = []
        mejor_prioridad = 100

        if not texto_buscado:
            return coincidencias, mejor_prioridad

        for nombre_visible, valor in campos.items():
            texto_campo = self.normalizar(
                valor
            )

            if not texto_campo:
                continue

            if texto_campo == texto_buscado:
                coincidencias.append(
                    f"{nombre_visible}: coincidencia exacta"
                )

                mejor_prioridad = min(
                    mejor_prioridad,
                    1
                )

            elif texto_buscado in texto_campo:
                coincidencias.append(
                    f"{nombre_visible}: contiene la búsqueda"
                )

                mejor_prioridad = min(
                    mejor_prioridad,
                    10
                )

            elif all(
                palabra in texto_campo
                for palabra in consulta["palabras"]
            ):
                coincidencias.append(
                    f"{nombre_visible}: coincide por palabras"
                )

                mejor_prioridad = min(
                    mejor_prioridad,
                    20
                )

        return coincidencias, mejor_prioridad

    def buscar_en_inventario(
        self,
        consulta: dict[str, Any]
    ) -> list[ResultadoBusqueda]:
        """
        Busca en los puertos cargados desde el Excel.
        """
        resultados = []

        for registro in self.inventario.registros:
            campos = {
                "Hoja": registro.get("hoja"),
                "Bloque": registro.get("bloque"),
                "Tipo": registro.get("tipo"),
                "Tipo original": registro.get(
                    "tipo_original"
                ),
                "Equipo": registro.get("equipo"),
                "Boca patch": registro.get(
                    "boca_patch"
                ),
                "Puerto": registro.get(
                    "puerto_switch"
                ),
                "VLAN": registro.get("vlan"),
                "Fila Excel": registro.get(
                    "fila_excel"
                )
            }

            coincidencias, prioridad = (
                self.calcular_coincidencias(
                    consulta,
                    campos
                )
            )

            if consulta["vlan"] is not None:
                vlan_registro = self.normalizar(
                    registro.get("vlan")
                )

                if vlan_registro == self.normalizar(
                    consulta["vlan"]
                ):
                    coincidencias.append(
                        "VLAN: coincidencia solicitada"
                    )

                    prioridad = min(
                        prioridad,
                        2
                    )

            if consulta["puerto"] is not None:
                try:
                    puerto_registro = int(
                        registro.get("puerto_switch")
                    )
                except (
                    ValueError,
                    TypeError
                ):
                    puerto_registro = None

                if puerto_registro == consulta["puerto"]:
                    coincidencias.append(
                        "Puerto: coincidencia solicitada"
                    )

                    prioridad = min(
                        prioridad,
                        2
                    )

            if not coincidencias:
                continue

            switch = (
                self.gestor_relaciones
                .obtener_switch_por_registro(
                    registro
                )
            )

            datos = dict(
                registro
            )

            datos["switch"] = switch

            equipo = self.valor_visible(
                registro.get("equipo")
            )

            hoja = self.valor_visible(
                registro.get("hoja")
            )

            bloque = self.valor_visible(
                registro.get("bloque")
            )

            puerto = self.valor_visible(
                registro.get("puerto_switch")
            )

            resultados.append(
                ResultadoBusqueda(
                    categoria="Puerto de inventario",
                    titulo=equipo,
                    subtitulo=(
                        f"{hoja} | Bloque {bloque} | "
                        f"Puerto {puerto}"
                    ),
                    coincidencias=coincidencias,
                    datos=datos,
                    prioridad=prioridad
                )
            )

        return resultados

    def buscar_en_switches(
        self,
        consulta: dict[str, Any]
    ) -> list[ResultadoBusqueda]:
        """
        Busca en los switches almacenados en SQLite.
        """
        resultados = []

        for switch in self.gestor_accesos.listar_todos():
            campos = {
                "Último octeto": switch.get(
                    "ultimo_octeto"
                ),
                "IP": switch.get("ip"),
                "Nombre": switch.get("nombre"),
                "MAC": switch.get("mac"),
                "Marca": switch.get("marca"),
                "Modelo": switch.get("modelo"),
                "Usuario": switch.get("usuario"),
                "Ubicación": switch.get(
                    "ubicacion"
                ),
                "Observaciones": switch.get(
                    "observaciones"
                ),
                "Hoja relacionada": switch.get(
                    "hoja_excel"
                ),
                "Bloque relacionado": switch.get(
                    "bloque_excel"
                )
            }

            coincidencias, prioridad = (
                self.calcular_coincidencias(
                    consulta,
                    campos
                )
            )

            if consulta["numero"] is not None:
                if switch.get(
                    "ultimo_octeto"
                ) == consulta["numero"]:
                    coincidencias.append(
                        "Último octeto: coincidencia exacta"
                    )

                    prioridad = min(
                        prioridad,
                        0
                    )

            if consulta["es_ip"]:
                if (
                    self.normalizar(
                        switch.get("ip")
                    )
                    == consulta["normalizada"]
                ):
                    coincidencias.append(
                        "IP: coincidencia exacta"
                    )

                    prioridad = 0

            if not coincidencias:
                continue

            ip = self.valor_visible(
                switch.get("ip")
            )

            ubicacion = self.valor_visible(
                switch.get("ubicacion")
            )

            modelo = self.valor_visible(
                switch.get("modelo")
            )

            resultados.append(
                ResultadoBusqueda(
                    categoria="Switch",
                    titulo=ip,
                    subtitulo=(
                        f"{ubicacion} | {modelo}"
                    ),
                    coincidencias=coincidencias,
                    datos=dict(switch),
                    prioridad=prioridad
                )
            )

        return resultados

    def buscar_en_bloques(
        self,
        consulta: dict[str, Any]
    ) -> list[ResultadoBusqueda]:
        """
        Busca sectores, bloques y switches relacionados.
        """
        resultados = []

        for bloque in (
            self.gestor_relaciones.listar_bloques()
        ):
            switch = bloque.get("switch")

            campos = {
                "Hoja": bloque.get("hoja"),
                "Bloque": bloque.get("bloque"),
                "Puertos documentados": bloque.get(
                    "cantidad_puertos"
                )
            }

            if switch is not None:
                campos.update(
                    {
                        "IP del switch": switch.get("ip"),
                        "Ubicación del switch": switch.get(
                            "ubicacion"
                        ),
                        "Marca del switch": switch.get(
                            "marca"
                        ),
                        "Modelo del switch": switch.get(
                            "modelo"
                        )
                    }
                )

            coincidencias, prioridad = (
                self.calcular_coincidencias(
                    consulta,
                    campos
                )
            )

            if not coincidencias:
                continue

            hoja = self.valor_visible(
                bloque.get("hoja")
            )

            numero_bloque = self.valor_visible(
                bloque.get("bloque")
            )

            if switch is None:
                subtitulo = (
                    "Sin switch relacionado | "
                    f"{bloque.get('cantidad_puertos', 0)} "
                    "puertos documentados"
                )
            else:
                subtitulo = (
                    f"Switch {switch.get('ip')} | "
                    f"{bloque.get('cantidad_puertos', 0)} "
                    "puertos documentados"
                )

            resultados.append(
                ResultadoBusqueda(
                    categoria="Bloque de inventario",
                    titulo=(
                        f"{hoja} - Bloque {numero_bloque}"
                    ),
                    subtitulo=subtitulo,
                    coincidencias=coincidencias,
                    datos={
                        **bloque,
                        "switch": switch
                    },
                    prioridad=prioridad + 5
                )
            )

        return resultados

    def eliminar_duplicados(
        self,
        resultados: list[ResultadoBusqueda]
    ) -> list[ResultadoBusqueda]:
        """
        Evita mostrar dos veces el mismo resultado.
        """
        resultados_unicos = []
        claves = set()

        for resultado in resultados:
            datos = resultado.datos

            if resultado.categoria == "Switch":
                clave = (
                    resultado.categoria,
                    datos.get("id"),
                    datos.get("ultimo_octeto")
                )

            elif resultado.categoria == "Puerto de inventario":
                clave = (
                    resultado.categoria,
                    datos.get("hoja"),
                    datos.get("bloque"),
                    datos.get("fila_excel"),
                    datos.get("puerto_switch")
                )

            else:
                clave = (
                    resultado.categoria,
                    datos.get("hoja"),
                    datos.get("bloque")
                )

            if clave in claves:
                continue

            claves.add(
                clave
            )

            resultados_unicos.append(
                resultado
            )

        return resultados_unicos

    def buscar(
        self,
        texto: str,
        limite: int | None = None
    ) -> list[ResultadoBusqueda]:
        """
        Ejecuta la búsqueda en todas las fuentes disponibles.
        """
        consulta = self.preparar_consulta(
            texto
        )

        if not consulta["normalizada"]:
            return []

        resultados = []

        resultados.extend(
            self.buscar_en_switches(
                consulta
            )
        )

        resultados.extend(
            self.buscar_en_inventario(
                consulta
            )
        )

        resultados.extend(
            self.buscar_en_bloques(
                consulta
            )
        )

        resultados = self.eliminar_duplicados(
            resultados
        )

        resultados.sort(
            key=lambda resultado: (
                resultado.prioridad,
                self.normalizar(
                    resultado.categoria
                ),
                self.normalizar(
                    resultado.titulo
                )
            )
        )

        limite_final = (
            limite
            if limite is not None
            else self.MAXIMO_RESULTADOS
        )

        return resultados[
            :limite_final
        ]

    def mostrar_resultado_switch(
        self,
        resultado: ResultadoBusqueda
    ):
        """
        Muestra los detalles seguros de un switch.

        La contraseña no se muestra en el buscador universal.
        """
        switch = resultado.datos

        print(
            f"IP: {self.valor_visible(switch.get('ip'))}"
        )
        print(
            "Ubicación: "
            f"{self.valor_visible(switch.get('ubicacion'))}"
        )
        print(
            "MAC: "
            f"{self.valor_visible(switch.get('mac'))}"
        )
        print(
            "Marca: "
            f"{self.valor_visible(switch.get('marca'))}"
        )
        print(
            "Modelo: "
            f"{self.valor_visible(switch.get('modelo'))}"
        )

        hoja = switch.get(
            "hoja_excel"
        )

        bloque = switch.get(
            "bloque_excel"
        )

        if hoja is not None and bloque is not None:
            print(
                f"Relación: {hoja} | Bloque {bloque}"
            )
        else:
            print(
                "Relación: Sin relación configurada"
            )

    def mostrar_resultado_puerto(
        self,
        resultado: ResultadoBusqueda
    ):
        """
        Muestra los detalles de un puerto del inventario.
        """
        registro = resultado.datos

        print(
            f"Hoja: {self.valor_visible(registro.get('hoja'))}"
        )
        print(
            f"Bloque: {self.valor_visible(registro.get('bloque'))}"
        )
        print(
            "Fila Excel: "
            f"{self.valor_visible(registro.get('fila_excel'))}"
        )
        print(
            "Puerto switch: "
            f"{self.valor_visible(registro.get('puerto_switch'))}"
        )
        print(
            "Boca patch: "
            f"{self.valor_visible(registro.get('boca_patch'))}"
        )
        print(
            f"Tipo: {self.valor_visible(registro.get('tipo'))}"
        )
        print(
            "Equipo: "
            f"{self.valor_visible(registro.get('equipo'))}"
        )
        print(
            f"VLAN: {self.valor_visible(registro.get('vlan'))}"
        )

        switch = registro.get(
            "switch"
        )

        if switch is None:
            print(
                "Switch relacionado: Sin información"
            )
        else:
            print(
                "Switch relacionado: "
                f"{self.valor_visible(switch.get('ip'))}"
            )
            print(
                "Ubicación del switch: "
                f"{self.valor_visible(switch.get('ubicacion'))}"
            )

    def mostrar_resultado_bloque(
        self,
        resultado: ResultadoBusqueda
    ):
        """
        Muestra los detalles de un bloque.
        """
        bloque = resultado.datos

        print(
            f"Hoja: {self.valor_visible(bloque.get('hoja'))}"
        )
        print(
            f"Bloque: {self.valor_visible(bloque.get('bloque'))}"
        )
        print(
            "Puertos documentados: "
            f"{bloque.get('cantidad_puertos', 0)}"
        )

        switch = bloque.get(
            "switch"
        )

        if switch is None:
            print(
                "Switch relacionado: Sin relación"
            )
        else:
            print(
                f"Switch relacionado: {switch.get('ip')}"
            )
            print(
                "Ubicación: "
                f"{self.valor_visible(switch.get('ubicacion'))}"
            )
            print(
                "Modelo: "
                f"{self.valor_visible(switch.get('modelo'))}"
            )

    def mostrar_resultados(
        self,
        resultados: list[ResultadoBusqueda]
    ):
        """
        Muestra los resultados agrupados y priorizados.
        """
        if not resultados:
            print(
                "\nNo se encontraron coincidencias."
            )
            return

        print(
            f"\nResultados encontrados: {len(resultados)}"
        )

        for numero, resultado in enumerate(
            resultados,
            start=1
        ):
            print(
                "\n=============================================="
            )
            print(
                f"Resultado {numero} | {resultado.categoria}"
            )
            print(
                "----------------------------------------------"
            )
            print(
                resultado.titulo
            )
            print(
                resultado.subtitulo
            )
            print(
                "----------------------------------------------"
            )

            if resultado.categoria == "Switch":
                self.mostrar_resultado_switch(
                    resultado
                )

            elif resultado.categoria == "Puerto de inventario":
                self.mostrar_resultado_puerto(
                    resultado
                )

            else:
                self.mostrar_resultado_bloque(
                    resultado
                )

            if resultado.coincidencias:
                print(
                    "\nCoincidencias:"
                )

                for coincidencia in resultado.coincidencias:
                    print(
                        f"- {coincidencia}"
                    )