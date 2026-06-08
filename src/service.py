from __future__ import annotations

import re
from collections.abc import Callable
from ftplib import FTP
from logging import getLogger
from posixpath import basename
from typing import Any, Protocol

from src.settings import Settings


class FTPClientProtocol(Protocol):
    """Minimal FTP operations required by the availability service."""

    def __enter__(self) -> FTPClientProtocol: ...

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None: ...

    def login(self) -> str: ...

    def cwd(self, dirname: str) -> str: ...

    def nlst(self) -> list[str]: ...


class LoggerProtocol(Protocol):
    """Minimal logger operations used by the service."""

    def debug(self, message: str, *args: object, **kwargs: object) -> None: ...


class CheckAvailabilityService:
    """Build the available Novo CAGED file tree from the public FTP server."""

    YEAR_PATTERN = re.compile(r"^\d{4}$")
    YEAR_MONTH_PATTERN = re.compile(r"^\d{6}$")

    def __init__(
        self,
        settings: Settings,
        ftp_factory: Callable[..., FTPClientProtocol] = FTP,
        logger: LoggerProtocol | None = None,
    ) -> None:
        self.settings = settings
        self.ftp_factory = ftp_factory
        self.logger = logger or getLogger(__name__)

    def list_entries(self, ftp: FTPClientProtocol, path: str) -> list[str]:
        """Return normalized entry names for a remote FTP directory."""
        self.logger.debug("Listing FTP directory", path=path)
        ftp.cwd(path)
        entries = [basename(entry) for entry in ftp.nlst()]
        self.logger.debug(
            "Listed FTP directory",
            path=path,
            entries_count=len(entries),
        )
        return entries

    def build_caged_tree(
        self,
        ftp: FTPClientProtocol,
        root_dir: str,
    ) -> dict[str, dict[str, list[str]]]:
        """Return files grouped as year -> year_month -> file names."""
        tree = {}
        self.logger.debug("Building CAGED FTP tree", root_dir=root_dir)

        for year in sorted(self.list_entries(ftp, root_dir)):
            if not self.YEAR_PATTERN.fullmatch(year):
                continue

            year_path = f"{root_dir}/{year}"
            year_months = [
                entry
                for entry in self.list_entries(ftp, year_path)
                if self.YEAR_MONTH_PATTERN.fullmatch(entry)
            ]
            self.logger.debug(
                "Found CAGED month directories",
                year=year,
                months_count=len(year_months),
            )

            tree[year] = {
                year_month: sorted(self.list_entries(ftp, f"{year_path}/{year_month}"))
                for year_month in sorted(year_months)
            }

        self.logger.debug("Built CAGED FTP tree", years_count=len(tree))
        return tree

    def execute(self, event: dict[str, Any]) -> dict[str, Any]:
        """Connect to the FTP server and return the complete availability tree."""
        self.logger.debug(
            "Connecting to CAGED FTP server",
            ftp_host=self.settings.FTP_HOST,
            ftp_root_dir=self.settings.FTP_ROOT_DIR,
        )
        with self.ftp_factory(
            self.settings.FTP_HOST,
            timeout=30,
            encoding="latin-1",
        ) as ftp:
            ftp.login()
            caged_tree = self.build_caged_tree(ftp, self.settings.FTP_ROOT_DIR)

        self.logger.debug(
            "Finished CAGED FTP availability check",
            years_count=len(caged_tree),
        )
        return caged_tree
