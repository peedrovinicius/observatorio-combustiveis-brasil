from src.publication_contract import (
    PUBLIC_IMAGE_FILES,
)
from src.publish_readme import (
    README_IMAGES,
)
from src.reporting import (
    REPORT_IMAGES,
)
from src.site import (
    SITE_IMAGES,
)
from src.snapshot import (
    SNAPSHOT_IMAGES,
)


def test_public_image_contract_is_shared() -> None:
    assert tuple(README_IMAGES) == PUBLIC_IMAGE_FILES
    assert tuple(REPORT_IMAGES) == PUBLIC_IMAGE_FILES
    assert tuple(SITE_IMAGES) == PUBLIC_IMAGE_FILES
    assert tuple(SNAPSHOT_IMAGES) == PUBLIC_IMAGE_FILES
