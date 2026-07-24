from __future__ import annotations

from typing import Any, Iterable, Sequence

from rich import box
from rich.align import Align
from rich.columns import Columns
from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.text import Text


console = Console()


class Visual:
    """Motor visual oficial de NetInventory basado en Rich."""

    COLOR_PRINCIPAL = "bright_blue"
    COLOR_EXITO = "green"
    COLOR_AVISO = "yellow"
    COLOR_ERROR = "red"
    COLOR_INFO = "cyan"
    COLOR_SNMP = "magenta"
    COLOR_SECUNDARIO = "grey70"

    def __init__(self) -> None:
        self.console = console

    # ======================================================
    # PANTALLA
    # ======================================================

    def limpiar(self) -> None:
        self.console.clear()

    def imprimir(self, contenido: Any = "") -> None:
        self.console.print(contenido)

    def espacio(self, cantidad: int = 1) -> None:
        for _ in range(max(1, cantidad)):
            self.console.print()

    # ======================================================
    # TÍTULOS
    # ======================================================

    def titulo(
        self,
        titulo: str,
        subtitulo: str = "",
        color: str = COLOR_PRINCIPAL
    ) -> None:
        texto = Text(justify="center")
        texto.append(str(titulo), style="bold bright_white")

        if subtitulo:
            texto.append("\n")
            texto.append(str(subtitulo), style="cyan")

        self.console.print(
            Panel(
                Align.center(texto),
                border_style=color,
                box=box.DOUBLE,
                padding=(0, 1),
                expand=True
            )
        )

    def subtitulo(
        self,
        texto: str,
        color: str = COLOR_INFO
    ) -> None:
        self.console.print(
            f"\n[bold {color}]{texto}[/bold {color}]"
        )

    def separador(
        self,
        titulo: str = "",
        color: str = COLOR_PRINCIPAL
    ) -> None:
        self.console.print(
            Rule(title=titulo or None, style=color)
        )

    # ======================================================
    # MENSAJES
    # ======================================================

    def ok(self, texto: str) -> None:
        self.console.print(
            f"[bold green]✔[/bold green] {texto}"
        )

    def info(self, texto: str) -> None:
        self.console.print(
            f"[bold cyan]ℹ[/bold cyan] {texto}"
        )

    def warning(self, texto: str) -> None:
        self.console.print(
            f"[bold yellow]⚠[/bold yellow] {texto}"
        )

    def error(self, texto: str) -> None:
        self.console.print(
            f"[bold red]✖[/bold red] {texto}"
        )

    def mensaje_estado(self, estado: str, texto: str) -> None:
        estado = str(estado).strip().upper()

        if estado == "OK":
            self.ok(texto)
        elif estado == "INFO":
            self.info(texto)
        elif estado in {"AVISO", "WARNING"}:
            self.warning(texto)
        elif estado == "ERROR":
            self.error(texto)
        else:
            self.imprimir(texto)

    # ======================================================
    # BADGES
    # ======================================================

    def badge(
        self,
        texto: str,
        color: str = "green"
    ) -> str:
        return (
            f"[bold white on {color}] "
            f"{str(texto).upper()} "
            f"[/]"
        )

    def badge_estado(self, estado: str) -> str:
        estado = str(estado).strip().upper()

        colores = {
            "ONLINE": "green",
            "OPERATIVO": "green",
            "OK": "green",
            "OFFLINE": "red",
            "ERROR": "red",
            "CRITICO": "red",
            "CRÍTICO": "red",
            "WARNING": "yellow",
            "AVISO": "yellow",
            "PENDIENTE": "yellow",
            "SNMP": "magenta",
            "INFO": "cyan",
            "DESCONOCIDO": "grey50",
            "SIN COMPROBAR": "grey50"
        }

        return self.badge(
            estado,
            colores.get(estado, "bright_blue")
        )

    # ======================================================
    # BARRAS E INDICADORES
    # ======================================================

    def color_porcentaje(
        self,
        porcentaje: float,
        invertir_umbral: bool = False
    ) -> str:
        porcentaje = max(0.0, min(100.0, float(porcentaje)))

        if invertir_umbral:
            if porcentaje >= 90:
                return "red"
            if porcentaje >= 70:
                return "yellow"
            return "green"

        if porcentaje >= 90:
            return "green"
        if porcentaje >= 70:
            return "yellow"
        return "red"

    def barra(
        self,
        porcentaje: float,
        largo: int = 20,
        invertir_umbral: bool = False
    ) -> str:
        porcentaje = max(0.0, min(100.0, float(porcentaje)))
        largo = max(5, int(largo))

        llenos = int(largo * porcentaje / 100)
        vacios = largo - llenos
        color = self.color_porcentaje(
            porcentaje,
            invertir_umbral=invertir_umbral
        )

        barra = "█" * llenos + "░" * vacios

        return (
            f"[{color}]{barra}[/{color}] "
            f"{porcentaje:.1f}%"
        )

    # ======================================================
    # PANELES
    # ======================================================

    def panel(
        self,
        titulo: str,
        contenido: Any,
        color: str = COLOR_PRINCIPAL,
        expandir: bool = True,
        padding: tuple[int, int] = (1, 2)
    ) -> Panel:
        return Panel(
            contenido,
            title=titulo,
            border_style=color,
            box=box.ROUNDED,
            expand=expandir,
            padding=padding
        )

    def mostrar_panel(
        self,
        titulo: str,
        contenido: Any,
        color: str = COLOR_PRINCIPAL,
        expandir: bool = True
    ) -> None:
        self.console.print(
            self.panel(
                titulo=titulo,
                contenido=contenido,
                color=color,
                expandir=expandir
            )
        )

    # ======================================================
    # TARJETAS Y DASHBOARD
    # ======================================================

    def crear_tarjeta(
        self,
        titulo: str,
        contenido: Any,
        color: str = COLOR_PRINCIPAL,
        subtitulo: str | None = None
    ) -> Panel:
        """
        Crea una tarjeta compacta.

        El subtítulo admite marcado Rich, por ejemplo
        barras devueltas por visual.barra().
        """
        texto = Text(justify="center")
        texto.append(
            str(contenido),
            style="bold bright_white"
        )

        if subtitulo:
            texto.append("\n")

            subtitulo_rich = Text.from_markup(
                str(subtitulo)
            )

            subtitulo_rich.justify = "center"
            texto.append_text(
                subtitulo_rich
            )

        return Panel(
            Align.center(
                texto,
                vertical="middle"
            ),
            title=titulo,
            border_style=color,
            box=box.ROUNDED,
            padding=(1, 2),
            expand=True
        )

    def crear_tarjeta_estado(
        self,
        titulo: str,
        contenido: Any,
        porcentaje: float,
        icono: str = "",
        invertir_umbral: bool = False
    ) -> Panel:
        color = self.color_porcentaje(
            porcentaje,
            invertir_umbral=invertir_umbral
        )

        return self.crear_tarjeta(
            titulo=f"{icono} {titulo}".strip(),
            contenido=contenido,
            color=color,
            subtitulo=self.barra(
                porcentaje,
                largo=12,
                invertir_umbral=invertir_umbral
            )
        )

    def dashboard(self, tarjetas: Sequence[dict]) -> None:
        paneles = [
            self.crear_tarjeta(
                titulo=str(tarjeta.get("titulo", "Estado")),
                contenido=tarjeta.get("contenido", "-"),
                color=str(
                    tarjeta.get(
                        "color",
                        self.COLOR_PRINCIPAL
                    )
                ),
                subtitulo=tarjeta.get("subtitulo")
            )
            for tarjeta in tarjetas
        ]

        self.console.print(
            Columns(
                paneles,
                equal=True,
                expand=True,
                column_first=True
            )
        )

    # ======================================================
    # PANELES DE ESTADO
    # ======================================================

    def panel_estado(
        self,
        titulo: str,
        elementos: Iterable,
        color: str = COLOR_PRINCIPAL
    ) -> None:
        lineas = Text()

        for indice, elemento in enumerate(elementos):
            if isinstance(elemento, dict):
                icono = str(elemento.get("icono", "•"))
                texto = str(elemento.get("texto", ""))
                estilo = str(elemento.get("color", "white"))
            else:
                icono = str(elemento[0])
                texto = str(elemento[1])
                estilo = "white"

            if indice > 0:
                lineas.append("\n")

            lineas.append(f"{icono} ", style=estilo)
            lineas.append(texto, style=estilo)

        self.console.print(
            Panel(
                lineas,
                title=titulo,
                border_style=color,
                box=box.ROUNDED,
                padding=(0, 2),
                expand=True
            )
        )

    # ======================================================
    # PANEL DE EVENTOS
    # ======================================================

    def panel_eventos(
        self,
        titulo: str,
        eventos: Iterable,
        color: str = COLOR_INFO,
        limite: int | None = None
    ) -> None:
        eventos = list(eventos)

        if limite is not None:
            eventos = eventos[:limite]

        contenido = Text()

        if not eventos:
            contenido.append(
                "No existen eventos recientes.",
                style="dim"
            )

        for indice, evento in enumerate(eventos):
            if isinstance(evento, dict):
                hora = str(evento.get("hora", "--:--"))
                icono = str(evento.get("icono", "•"))
                texto = str(evento.get("texto", ""))
                estilo = str(evento.get("color", "white"))
            else:
                hora = str(evento[0])
                icono = str(evento[1])
                texto = str(evento[2])
                estilo = "white"

            if indice > 0:
                contenido.append("\n")

            contenido.append(f"{hora:<8}", style="dim cyan")
            contenido.append(f"{icono} ", style=estilo)
            contenido.append(texto, style=estilo)

        self.console.print(
            Panel(
                contenido,
                title=titulo,
                border_style=color,
                box=box.ROUNDED,
                padding=(1, 2),
                expand=True
            )
        )

    # ======================================================
    # PANEL DE ACCIONES
    # ======================================================

    def panel_acciones(
        self,
        titulo: str,
        acciones: Iterable,
        color: str = COLOR_AVISO
    ) -> None:
        acciones = list(acciones)
        contenido = Text()

        if not acciones:
            contenido.append(
                "No existen acciones pendientes.",
                style="green"
            )

        for indice, accion in enumerate(acciones, start=1):
            if isinstance(accion, dict):
                icono = str(accion.get("icono", "•"))
                texto = str(accion.get("texto", ""))
                estilo = str(accion.get("color", "white"))
            else:
                icono = str(accion[0])
                texto = str(accion[1])
                estilo = "white"

            if indice > 1:
                contenido.append("\n")

            contenido.append(f"{indice}. ", style="bold")
            contenido.append(f"{icono} ", style=estilo)
            contenido.append(texto, style=estilo)

        self.console.print(
            Panel(
                contenido,
                title=titulo,
                border_style=color,
                box=box.ROUNDED,
                padding=(1, 2),
                expand=True
            )
        )

    # ======================================================
    # TABLAS
    # ======================================================

    def crear_tabla(
        self,
        titulo: str | None = None,
        mostrar_lineas: bool = False,
        expandir: bool = False
    ) -> Table:
        return Table(
            title=titulo,
            box=box.ROUNDED,
            header_style="bold cyan",
            show_lines=mostrar_lineas,
            expand=expandir,
            border_style="grey50",
            row_styles=["", "dim"]
        )

    def tabla(
        self,
        titulo: str | None,
        columnas: Sequence,
        filas: Iterable,
        expandir: bool = False,
        mostrar_lineas: bool = False
    ) -> None:
        tabla = self.crear_tabla(
            titulo=titulo,
            mostrar_lineas=mostrar_lineas,
            expandir=expandir
        )

        for columna in columnas:
            if isinstance(columna, dict):
                tabla.add_column(
                    str(columna.get("nombre", "")),
                    justify=str(
                        columna.get("justify", "left")
                    ),
                    style=columna.get("style"),
                    no_wrap=bool(
                        columna.get("no_wrap", False)
                    )
                )
            else:
                tabla.add_column(str(columna))

        for fila in filas:
            tabla.add_row(
                *[
                    str(valor)
                    if valor is not None
                    else "-"
                    for valor in fila
                ]
            )

        self.console.print(tabla)

    # ======================================================
    # MENÚS
    # ======================================================

    def menu(
        self,
        titulo: str,
        opciones: Iterable,
        color: str = COLOR_PRINCIPAL
    ) -> None:
        tabla = Table(
            title=titulo,
            box=box.ROUNDED,
            show_header=False,
            border_style=color,
            expand=False,
            padding=(0, 1)
        )

        tabla.add_column(
            width=5,
            style="bold yellow",
            justify="center",
            no_wrap=True
        )
        tabla.add_column(style="white")

        for numero, texto in opciones:
            tabla.add_row(str(numero), str(texto))

        self.console.print(tabla)

    def menu_categorias(
        self,
        titulo: str,
        categorias: Sequence[dict]
    ) -> None:
        self.subtitulo(titulo, self.COLOR_PRINCIPAL)

        for categoria in categorias:
            color = str(
                categoria.get(
                    "color",
                    self.COLOR_PRINCIPAL
                )
            )
            icono = str(categoria.get("icono", ""))
            nombre = str(categoria.get("titulo", ""))
            opciones = categoria.get("opciones", [])

            tabla = Table(
                box=box.SIMPLE,
                show_header=False,
                expand=True,
                padding=(0, 1)
            )

            tabla.add_column(
                width=6,
                justify="center",
                style="bold yellow"
            )
            tabla.add_column()

            tabla.add_row(
                "",
                f"[bold {color}]"
                f"{icono} {nombre}"
                f"[/bold {color}]"
            )

            for numero, texto in opciones:
                tabla.add_row(str(numero), str(texto))

            self.console.print(tabla)

    def menu_paneles(
        self,
        titulo: str,
        categorias: Sequence[dict]
    ) -> None:
        """
        Muestra categorías del menú dentro de paneles
        alineados horizontalmente.

        Cada categoría admite:
        titulo, icono, color y opciones.
        """
        self.separador(
            titulo,
            self.COLOR_PRINCIPAL
        )

        paneles = []

        for categoria in categorias:
            color = str(
                categoria.get(
                    "color",
                    self.COLOR_PRINCIPAL
                )
            )

            icono = str(
                categoria.get(
                    "icono",
                    ""
                )
            )

            nombre = str(
                categoria.get(
                    "titulo",
                    ""
                )
            )

            opciones = categoria.get(
                "opciones",
                []
            )

            contenido = Text()

            for indice, opcion in enumerate(opciones):
                numero, descripcion = opcion

                if indice > 0:
                    contenido.append("\n")

                contenido.append(
                    f"{numero:>3}  ",
                    style="bold yellow"
                )

                contenido.append(
                    str(descripcion),
                    style="white"
                )

            if not opciones:
                contenido.append(
                    "Sin opciones disponibles.",
                    style="dim"
                )

            paneles.append(
                Panel(
                    contenido,
                    title=(
                        f"{icono} {nombre}"
                    ).strip(),
                    border_style=color,
                    box=box.ROUNDED,
                    padding=(1, 2),
                    expand=True
                )
            )

        self.console.print(
            Columns(
                paneles,
                equal=True,
                expand=True
            )
        )

    # ======================================================
    # PIE DE PÁGINA
    # ======================================================

    def pie(
        self,
        elementos: Sequence,
        color: str = COLOR_SECUNDARIO
    ) -> None:
        texto = "  │  ".join(
            str(elemento)
            for elemento in elementos
        )

        self.console.print(Rule(style=color))
        self.console.print(
            Align.center(
                Text(
                    texto,
                    style=f"dim {color}"
                )
            )
        )

    # ======================================================
    # DASHBOARD COMPLETO
    # ======================================================

    def mostrar_dashboard(
        self,
        titulo: str,
        subtitulo: str,
        tarjetas: Sequence[dict],
        estados: Iterable | None = None,
        eventos: Iterable | None = None,
        acciones: Iterable | None = None,
        pie: Sequence | None = None,
        limpiar: bool = True
    ) -> None:
        if limpiar:
            self.limpiar()

        self.titulo(titulo, subtitulo)
        self.dashboard(tarjetas)

        if estados is not None:
            self.panel_estado(
                "Estado general",
                estados,
                self.COLOR_EXITO
            )

        if eventos is not None:
            self.panel_eventos(
                "Eventos recientes",
                eventos,
                self.COLOR_INFO
            )

        if acciones is not None:
            self.panel_acciones(
                "Acciones recomendadas",
                acciones,
                self.COLOR_AVISO
            )

        if pie is not None:
            self.pie(pie)


visual = Visual()