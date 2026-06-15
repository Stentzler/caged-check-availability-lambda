from dataclasses import dataclass
from typing import Any

import pytest

from exceptions import (
    InvalidRegistryTreeError,
    RegistryItemNotFoundError,
    TooManyNewFilesError,
)
from service import CheckAvailabilityService
from settings import Settings


@dataclass
class FakeFTP:
    entries_by_path: dict[str, list[str]]
    current_path: str = ""

    def __enter__(self) -> FakeFTP:
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        return None

    def login(self) -> str:
        return "logged in"

    def cwd(self, dirname: str) -> str:
        return dirname

    def nlst(self) -> list[str]:
        return self.entries_by_path[self.current_path]

    def set_current_path(self, path: str) -> None:
        self.current_path = path


class FakeFTPFactory:
    def __init__(self, ftp: FakeFTP) -> None:
        self.ftp = ftp

    def __call__(self, *args: object, **kwargs: object) -> FakeFTP:
        return self.ftp


@dataclass
class FakeRegistryTable:
    response: dict[str, Any]

    def get_item(self, **kwargs: object) -> dict[str, Any]:
        return self.response


def test_execute_returns_new_files_missing_from_registry() -> None:
    root_dir = "/pdet/microdados/NOVO CAGED"
    entries_by_path = {
        root_dir: ["2026", "Leia-me.txt"],
        f"{root_dir}/2026": ["202601", "other-file.txt"],
        f"{root_dir}/2026/202601": [
            "CAGEDMOV202601.7z",
            "CAGEDEXC202601.7z",
        ],
    }

    class PathAwareFakeFTP(FakeFTP):
        def cwd(self, dirname: str) -> str:
            self.set_current_path(dirname)
            return dirname

    fake_ftp = PathAwareFakeFTP(entries_by_path)
    settings = Settings(FTP_HOST="ftp.mtps.gov.br", FTP_ROOT_DIR=root_dir)
    service = CheckAvailabilityService(
        settings,
        ftp_factory=FakeFTPFactory(fake_ftp),
        registry_table=FakeRegistryTable(response={"Item": {"tree": {}}}),
    )

    response = service.execute({})

    assert response == {
        "new_files": [
            {
                "filename": "CAGEDEXC202601.7z",
                "ftp_url": (
                    "ftp://ftp.mtps.gov.br/pdet/microdados/NOVO%20CAGED/"
                    "2026/202601/CAGEDEXC202601.7z"
                ),
                "reference_month": "202601",
                "reference_year": "2026",
                "s3_key": (
                    "raw/caged/year=2026/month=01/file_type=exclusion/CAGEDEXC202601.7z"
                ),
            },
            {
                "filename": "CAGEDMOV202601.7z",
                "ftp_url": (
                    "ftp://ftp.mtps.gov.br/pdet/microdados/NOVO%20CAGED/"
                    "2026/202601/CAGEDMOV202601.7z"
                ),
                "reference_month": "202601",
                "reference_year": "2026",
                "s3_key": (
                    "raw/caged/year=2026/month=01/file_type=movement/CAGEDMOV202601.7z"
                ),
            },
        ],
    }


def test_check_new_files_skips_downloaded_and_skipped_files() -> None:
    settings = Settings(FTP_HOST="ftp.mtps.gov.br")
    service = CheckAvailabilityService(settings)
    ftp_tree = {
        "2026": {
            "202601": [
                "CAGEDEXC202601.7z",
                "CAGEDFOR202601.7z",
                "CAGEDMOV202601.7z",
            ],
        },
    }
    registry_tree = {
        "2026": {
            "202601": {
                "CAGEDEXC202601.7z": {"status": "downloaded"},
                "CAGEDFOR202601.7z": {"status": "skipped"},
            },
        },
    }

    new_files = service.check_new_files(ftp_tree, registry_tree)

    assert new_files == [
        {
            "filename": "CAGEDMOV202601.7z",
            "ftp_url": (
                "ftp://ftp.mtps.gov.br/pdet/microdados/NOVO%20CAGED/"
                "2026/202601/CAGEDMOV202601.7z"
            ),
            "reference_month": "202601",
            "reference_year": "2026",
            "s3_key": (
                "raw/caged/year=2026/month=01/file_type=movement/CAGEDMOV202601.7z"
            ),
        },
    ]


@pytest.mark.parametrize(
    ("filename", "file_type"),
    [
        ("CAGEDMOV202604.7z", "movement"),
        ("CAGEDEXC202604.7z", "exclusion"),
        ("CAGEDFOR202604.7z", "late_movement"),
        ("README.txt", "other"),
    ],
)
def test_build_s3_key_partitions_files_by_type(
    filename: str,
    file_type: str,
) -> None:
    service = CheckAvailabilityService(Settings())

    s3_key = service.build_s3_key("2026", "202604", filename)

    assert s3_key == (f"raw/caged/year=2026/month=04/file_type={file_type}/{filename}")


def test_check_new_files_retries_failed_and_unknown_statuses() -> None:
    service = CheckAvailabilityService(Settings(FTP_HOST="ftp.mtps.gov.br"))
    ftp_tree = {
        "2026": {
            "202601": [
                "CAGEDEXC202601.7z",
                "CAGEDFOR202601.7z",
            ],
        },
    }
    registry_tree = {
        "2026": {
            "202601": {
                "CAGEDEXC202601.7z": {"status": "failed"},
                "CAGEDFOR202601.7z": {"status": "pending"},
            },
        },
    }

    new_files = service.check_new_files(ftp_tree, registry_tree)

    assert [item["filename"] for item in new_files] == [
        "CAGEDEXC202601.7z",
        "CAGEDFOR202601.7z",
    ]


def test_load_registry_tree_raises_when_item_is_missing() -> None:
    service = CheckAvailabilityService(
        Settings(),
        registry_table=FakeRegistryTable(response={}),
    )

    with pytest.raises(RegistryItemNotFoundError) as error:
        service.load_registry_tree()

    assert error.value.registry_id == "ftp_tree"
    assert error.value.table_name == "downloaded_files_registry"
    assert str(error.value) == (
        "Registry item 'ftp_tree' was not found in table 'downloaded_files_registry'."
    )


def test_load_registry_tree_raises_when_tree_is_invalid() -> None:
    service = CheckAvailabilityService(
        Settings(),
        registry_table=FakeRegistryTable(response={"Item": {"tree": "invalid"}}),
    )

    with pytest.raises(InvalidRegistryTreeError) as error:
        service.load_registry_tree()

    assert error.value.registry_id == "ftp_tree"
    assert error.value.actual_type is str
    assert str(error.value) == (
        "Registry item 'ftp_tree' has an invalid tree type: "
        "expected dict, received str."
    )


def test_execute_allows_new_files_at_safety_limit() -> None:
    service = _build_service_with_file_count(CheckAvailabilityService.MAX_NEW_FILES)

    response = service.execute({})

    assert len(response["new_files"]) == CheckAvailabilityService.MAX_NEW_FILES


def test_execute_raises_when_new_files_exceed_safety_limit() -> None:
    file_count = CheckAvailabilityService.MAX_NEW_FILES + 1
    service = _build_service_with_file_count(file_count)

    with pytest.raises(TooManyNewFilesError) as error:
        service.execute({})

    assert error.value.file_count == file_count
    assert error.value.max_file_count == CheckAvailabilityService.MAX_NEW_FILES
    assert str(error.value) == (
        f"Found {file_count} new files, exceeding the safety limit of "
        f"{CheckAvailabilityService.MAX_NEW_FILES}."
    )


def _build_service_with_file_count(file_count: int) -> CheckAvailabilityService:
    root_dir = "/pdet/microdados/NOVO CAGED"
    year = "2026"
    reference_month = "202601"
    entries_by_path = {
        root_dir: [year],
        f"{root_dir}/{year}": [reference_month],
        f"{root_dir}/{year}/{reference_month}": [
            f"CAGEDTEST{index:02d}202601.7z" for index in range(file_count)
        ],
    }

    class PathAwareFakeFTP(FakeFTP):
        def cwd(self, dirname: str) -> str:
            self.set_current_path(dirname)
            return dirname

    return CheckAvailabilityService(
        Settings(FTP_ROOT_DIR=root_dir),
        ftp_factory=FakeFTPFactory(PathAwareFakeFTP(entries_by_path)),
        registry_table=FakeRegistryTable(response={"Item": {"tree": {}}}),
    )
