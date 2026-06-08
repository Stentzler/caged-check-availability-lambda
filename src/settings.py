import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    """Runtime configuration loaded from environment variables."""

    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "local")
    SOURCE_NAME: str = os.getenv("SOURCE_NAME", "check-availability")
    FTP_HOST: str = os.getenv("FTP_HOST", "ftp.mtps.gov.br")
    FTP_ROOT_DIR: str = os.getenv("FTP_ROOT_DIR", "/pdet/microdados/NOVO CAGED")


settings: Settings = Settings()
