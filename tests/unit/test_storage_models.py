from sales_data_platform_azure.contracts import SourceIdentity
from sales_data_platform_azure.storage import (
    DataLayer,
    ObjectLocation,
    ObjectMetadata,
    StorageEnvironment,
    StorageObject,
)


def test_only_raw_objects_are_immutable_source_boundaries() -> None:
    source = SourceIdentity("northstar-pos", "batch-1", "1.0")
    metadata = ObjectMetadata(source, "sales", "json", "1.0")
    raw = StorageObject(
        ObjectLocation(StorageEnvironment.DEV, DataLayer.RAW, "dev/raw/object.json"), metadata
    )
    processed = StorageObject(
        ObjectLocation(StorageEnvironment.DEV, DataLayer.PROCESSED, "dev/processed/object.json"),
        metadata,
    )

    assert raw.is_immutable_source is True
    assert processed.is_immutable_source is False
