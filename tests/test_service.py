from dataclasses import dataclass

from src.service import CheckAvailabilityService
from src.settings import Settings


@dataclass
class FakeFTP:
    entries_by_path: dict[str, list[str]]

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


def test_execute_returns_files_grouped_by_year_and_month() -> None:
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
    service = CheckAvailabilityService(settings, ftp_factory=FakeFTPFactory(fake_ftp))

    response = service.execute({})

    assert response == {
        "2026": {
            "202601": [
                "CAGEDEXC202601.7z",
                "CAGEDMOV202601.7z",
            ],
        },
    }
