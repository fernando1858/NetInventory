from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

console = Console()


class InterfazVisual:
    """
    Capa visual oficial de NetInventory.

    Todo el programa debe imprimir utilizando esta clase.
    """

    def __init__(self):
        self.console = console

    # -------------------------------------------------
    # Pantalla
    # -------------------------------------------------

    def limpiar(self):
        self.console.clear()

    # -------------------------------------------------
    # Títulos
    # -------------------------------------------------

    def titulo(self, texto):
        self.console.print(
            Panel.fit(
                f"[bold white]{texto}[/bold white]",
                border_style="bright_blue",
                box=box.DOUBLE
            )
        )

    def subtitulo(self, texto):
        self.console.print(
            f"\n[bold cyan]{texto}[/bold cyan]"
        )

    # -------------------------------------------------
    # Mensajes
    # -------------------------------------------------

    def ok(self, texto):
        self.console.print(
            f"[green]✓[/green] {texto}"
        )

    def warning(self, texto):
        self.console.print(
            f"[yellow]⚠[/yellow] {texto}"
        )

    def error(self, texto):
        self.console.print(
            f"[red]✖[/red] {texto}"
        )

    def info(self, texto):
        self.console.print(
            f"[cyan]ℹ[/cyan] {texto}"
        )

    # -------------------------------------------------
    # Separadores
    # -------------------------------------------------

    def separador(self):
        self.console.rule(style="grey50")

    # -------------------------------------------------
    # Paneles
    # -------------------------------------------------

    def panel(
        self,
        titulo,
        contenido,
        color="bright_blue"
    ):
        self.console.print(
            Panel(
                contenido,
                title=titulo,
                border_style=color,
                box=box.ROUNDED
            )
        )

    # -------------------------------------------------
    # Tablas
    # -------------------------------------------------

    def crear_tabla(
        self,
        titulo=None
    ):
        tabla = Table(
            title=titulo,
            box=box.SIMPLE_HEAVY,
            show_lines=False,
            header_style="bold cyan"
        )

        return tabla

    def mostrar_tabla(self, tabla):
        self.console.print(tabla)

    # -------------------------------------------------
    # Menús
    # -------------------------------------------------

    def menu(
        self,
        titulo,
        opciones
    ):
        tabla = Table(
            title=titulo,
            box=box.ROUNDED,
            header_style="bold green"
        )

        tabla.add_column(
            "#",
            justify="center",
            width=5
        )

        tabla.add_column(
            "Opción"
        )

        for numero, opcion in opciones:
            tabla.add_row(
                str(numero),
                opcion
            )

        self.console.print(tabla)

    # -------------------------------------------------
    # Resumen rápido
    # -------------------------------------------------

    def resumen(
        self,
        datos
    ):
        tabla = Table(
            box=box.MINIMAL_DOUBLE_HEAD
        )

        tabla.add_column(
            "Elemento",
            style="cyan"
        )

        tabla.add_column(
            "Valor",
            style="white"
        )

        for nombre, valor in datos.items():
            tabla.add_row(
                nombre,
                str(valor)
            )

        self.console.print(tabla)

# -------------------------------------------------
    # Menú principal NetInventory
    # -------------------------------------------------

    def menu_principal(self):
        tabla = Table(
            title="[bold cyan]NETINVENTORY[/bold cyan]",
            box=box.ROUNDED,
            header_style="bold green"
        )

        tabla.add_column(
            "#",
            justify="center",
            width=5,
            style="bold yellow"
        )

        tabla.add_column(
            "Módulo",
            style="white"
        )

        tabla.add_row("1", "🔍 Buscar en NetInventory")
        tabla.add_row("2", "📊 Mostrar resumen general")
        tabla.add_row("3", "🖧 Consultar ficha completa de red")
        tabla.add_row("4", "✔ Validar inventario")
        tabla.add_row("5", "⚙ Gestionar switches y accesos")
        tabla.add_row("6", "📄 Generar reporte Excel")
        tabla.add_row("7", "📡 Centro de monitoreo SNMP")
        tabla.add_row("8", "🌳 Centro de impacto de red")
        tabla.add_row("9", "🩺 Centro de salud de la red")
        tabla.add_row("10", "🚨 Asistente de incidencias")
        tabla.add_row("0", "❌ Salir")

        self.console.print(tabla)