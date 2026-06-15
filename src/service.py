from __future__ import annotations

import re
from collections.abc import Callable
from ftplib import FTP
from logging import getLogger
from posixpath import basename
from typing import Any, Protocol
from urllib.parse import quote

from exceptions import (
    InvalidRegistryTreeError,
    RegistryItemNotFoundError,
    TooManyNewFilesError,
)
from settings import Settings


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


class RegistryTableProtocol(Protocol):
    """Minimal DynamoDB table operations required by the service."""

    def get_item(self, **kwargs: object) -> dict[str, Any]: ...


type CagedTree = dict[str, dict[str, list[str]]]
type RegistryTree = dict[str, dict[str, dict[str, dict[str, Any]]]]
type NewFile = dict[str, str]


class CheckAvailabilityService:
    """Build the available Novo CAGED file tree from the public FTP server."""

    YEAR_PATTERN = re.compile(r"^\d{4}$")
    YEAR_MONTH_PATTERN = re.compile(r"^\d{6}$")
    PROCESSED_STATUSES = frozenset({"downloaded", "skipped"})
    FILE_TYPES = {
        "CAGEDMOV": "movement",
        "CAGEDEXC": "exclusion",
        "CAGEDFOR": "late_movement",
    }
    MAX_NEW_FILES = 12

    def __init__(
        self,
        settings: Settings,
        ftp_factory: Callable[..., FTPClientProtocol] = FTP,
        logger: LoggerProtocol | None = None,
        registry_table: RegistryTableProtocol | None = None,
    ) -> None:
        self.settings = settings
        self.ftp_factory = ftp_factory
        self.logger = logger or getLogger(__name__)
        self.registry_table = registry_table

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
    ) -> CagedTree:
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

    def load_registry_tree(self) -> RegistryTree:
        """Return the persisted CAGED file registry tree from DynamoDB."""
        if self.registry_table is None:
            self.logger.debug("No registry table configured, using empty registry")
            return {}

        response = self.registry_table.get_item(
            Key={"registry_id": self.settings.REGISTRY_ID},
        )

        item = response.get("Item")
        if not item:
            self.logger.debug(
                "Registry item not found",
                registry_id=self.settings.REGISTRY_ID,
            )
            raise RegistryItemNotFoundError(
                registry_id=self.settings.REGISTRY_ID,
                table_name=self.settings.REGISTRY_TABLE_NAME,
            )

        tree = item.get("tree", {})
        if not isinstance(tree, dict):
            self.logger.debug(
                "Registry item has invalid tree",
                registry_id=self.settings.REGISTRY_ID,
            )
            raise InvalidRegistryTreeError(
                registry_id=self.settings.REGISTRY_ID,
                actual_type=type(tree),
            )

        return tree

    def check_new_files(
        self,
        ftp_tree: CagedTree,
        registry_tree: RegistryTree,
    ) -> list[NewFile]:
        """Return FTP files that are not completed in the registry."""
        new_files = []

        for year, months in sorted(ftp_tree.items()):
            registry_year = registry_tree.get(year, {})
            if not isinstance(registry_year, dict):
                registry_year = {}

            for reference_date, filenames in sorted(months.items()):
                registry_month = registry_year.get(reference_date, {})
                if not isinstance(registry_month, dict):
                    registry_month = {}

                for filename in sorted(filenames):
                    registry_file = registry_month.get(filename, {})
                    if not isinstance(registry_file, dict):
                        registry_file = {}

                    status = registry_file.get("status")
                    if status in self.PROCESSED_STATUSES:
                        continue

                    new_files.append(
                        {
                            "filename": filename,
                            "ftp_url": self.build_ftp_url(
                                year,
                                reference_date,
                                filename,
                            ),
                            "reference_month": reference_date,
                            "reference_year": year,
                            "s3_key": self.build_s3_key(
                                year,
                                reference_date,
                                filename,
                            ),
                        }
                    )

        return new_files

    def build_ftp_url(
        self,
        year: str,
        reference_date: str,
        filename: str,
    ) -> str:
        """Return the encoded FTP URL for a CAGED file."""
        path = f"{self.settings.FTP_ROOT_DIR}/{year}/{reference_date}/{filename}"
        encoded_path = quote(path)
        return f"ftp://{self.settings.FTP_HOST}{encoded_path}"

    def build_s3_key(
        self,
        year: str,
        reference_date: str,
        filename: str,
    ) -> str:
        """Return the destination key for a raw CAGED archive."""
        file_type = next(
            (
                value
                for prefix, value in self.FILE_TYPES.items()
                if filename.startswith(prefix)
            ),
            "other",
        )
        month = reference_date[-2:]
        return f"raw/caged/year={year}/month={month}/file_type={file_type}/{filename}"

    def execute(self, event: dict[str, Any]) -> dict[str, Any]:
        """Return files for FTP files that need downstream processing."""
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
            ftp_tree = self.build_caged_tree(ftp, self.settings.FTP_ROOT_DIR)

        registry_tree = self.load_registry_tree()
        new_files = self.check_new_files(ftp_tree, registry_tree)

        self.logger.debug(
            "Finished CAGED FTP availability check",
            new_files=len(new_files),
        )

        if len(new_files) > self.MAX_NEW_FILES:
            raise TooManyNewFilesError(
                file_count=len(new_files),
                max_file_count=self.MAX_NEW_FILES,
            )

        return {"new_files": new_files}
