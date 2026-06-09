class RegistryItemNotFoundError(RuntimeError):
    """Raised when the expected registry item does not exist in DynamoDB."""

    def __init__(self, registry_id: str, table_name: str) -> None:
        self.registry_id = registry_id
        self.table_name = table_name
        super().__init__(
            f"Registry item {registry_id!r} was not found in table {table_name!r}."
        )


class InvalidRegistryTreeError(RuntimeError):
    """Raised when a registry item contains an invalid tree value."""

    def __init__(self, registry_id: str, actual_type: type[object]) -> None:
        self.registry_id = registry_id
        self.actual_type = actual_type
        super().__init__(
            f"Registry item {registry_id!r} has an invalid tree type: "
            f"expected dict, received {actual_type.__name__}."
        )


class TooManyNewFilesError(RuntimeError):
    """Raised when an unexpected number of FTP files requires processing."""

    def __init__(self, file_count: int, max_file_count: int) -> None:
        self.file_count = file_count
        self.max_file_count = max_file_count
        super().__init__(
            f"Found {file_count} new files, exceeding the safety limit of "
            f"{max_file_count}."
        )
