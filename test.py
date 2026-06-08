import json

from src.service import CheckAvailabilityService
from src.settings import settings


def main() -> None:
    service = CheckAvailabilityService(settings)
    caged_tree = service.execute({})
    print(json.dumps(caged_tree, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
