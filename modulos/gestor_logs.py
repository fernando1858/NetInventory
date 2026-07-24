from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


class GestorLogs:
    """
    Configura el registro técnico de NetInventory.

    Los archivos se rotan para evitar que el log crezca
    indefinidamente.
    """

    NOMBRE_LOGGER = "netinventory"

    def __init__(
        self,
        carpeta_logs="logs",
        nombre_archivo="netinventory.log",
        maximo_bytes=2_000_000,
        cantidad_respaldos=5
    ):
        self.carpeta_logs = Path(carpeta_logs)
        self.ruta_log = (
            self.carpeta_logs
            / nombre_archivo
        )
        self.maximo_bytes = int(maximo_bytes)
        self.cantidad_respaldos = int(
            cantidad_respaldos
        )

    def configurar(self) -> logging.Logger:
        self.carpeta_logs.mkdir(
            parents=True,
            exist_ok=True
        )

        logger = logging.getLogger(
            self.NOMBRE_LOGGER
        )

        logger.setLevel(
            logging.INFO
        )

        logger.propagate = False

        if logger.handlers:
            return logger

        manejador = RotatingFileHandler(
            filename=self.ruta_log,
            maxBytes=self.maximo_bytes,
            backupCount=self.cantidad_respaldos,
            encoding="utf-8"
        )

        formato = logging.Formatter(
            "%(asctime)s | %(levelname)s | "
            "%(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )

        manejador.setFormatter(
            formato
        )

        logger.addHandler(
            manejador
        )

        return logger

    @classmethod
    def obtener_logger(cls) -> logging.Logger:
        return logging.getLogger(
            cls.NOMBRE_LOGGER
        )