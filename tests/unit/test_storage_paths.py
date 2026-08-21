from datetime import date

import pytest

from sales_data_platform_azure.storage import (
    DataLayer,
    PathRequest,
    StorageEnvironment,
    build_object_location,
)

PARTITION = date(2026, 8, 21)


def _request(**changes: object) -> PathRequest:
    values: dict[str, object] = {
        "environment": "dev",
        "layer": "raw",
        "source_system": "Northstar-POS",
        "dataset": "Sales",
        "partition_date": PARTITION,
        "stable_object_identity": "source-checksum-v1",
        "format": ".json",
        "execution_id": "run-1",
    }
    values.update(changes)
    return PathRequest(**values)  # type: ignore[arg-type]


def test_governed_layers_and_environments_are_exact() -> None:
    assert [layer.value for layer in DataLayer] == [
        "raw",
        "processed",
        "curated",
        "quarantine",
    ]
    assert [environment.value for environment in StorageEnvironment] == ["dev", "prod"]
    with pytest.raises(ValueError):
        DataLayer("archive")
    with pytest.raises(ValueError):
        StorageEnvironment("staging")


def test_path_is_deterministic_normalized_partitioned_and_uses_forward_slashes() -> None:
    first = build_object_location(_request())
    second = build_object_location(_request())

    assert first == second
    assert first.address.startswith("dev/raw/northstar-pos/sales/year=2026/month=08/day=21/")
    assert first.address.endswith(".json")
    assert "\\" not in first.address


@pytest.mark.parametrize(
    ("field", "first", "second"),
    [
        ("environment", "dev", "prod"),
        ("source_system", "northstar-pos", "northstar-web"),
        ("dataset", "sales", "returns"),
        ("partition_date", date(2026, 8, 21), date(2026, 8, 22)),
        ("format", "json", "parquet"),
    ],
)
def test_governed_inputs_produce_distinct_addresses(
    field: str, first: object, second: object
) -> None:
    first_location = build_object_location(_request(**{field: first}))
    second_location = build_object_location(_request(**{field: second}))
    assert first_location.address != second_location.address


@pytest.mark.parametrize("layer", ["processed", "curated"])
def test_derived_addresses_ignore_execution_identity(layer: str) -> None:
    first = build_object_location(_request(layer=layer, execution_id="run-1"))
    replay = build_object_location(_request(layer=layer, execution_id="run-2"))
    assert first == replay


def test_raw_replay_reuses_address_and_ignores_execution_identity() -> None:
    first = build_object_location(_request(execution_id="run-1"))
    replay = build_object_location(_request(execution_id="run-2"))
    assert first == replay
    assert first.layer is DataLayer.RAW


def test_quarantine_address_preserves_separate_execution_attempts() -> None:
    first = build_object_location(_request(layer="quarantine", execution_id="run-1"))
    replay = build_object_location(_request(layer="quarantine", execution_id="run-2"))
    assert first.address != replay.address


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("source_system", ""),
        ("dataset", "   "),
        ("dataset", ".."),
        ("dataset", "sales/secret"),
        ("dataset", "sales\\secret"),
        ("dataset", "/absolute"),
        ("dataset", "C:\\absolute"),
        ("dataset", "~user"),
        ("dataset", ".relative"),
        ("stable_object_identity", "../secret"),
        ("stable_object_identity", None),
        ("format", "json/../../secret"),
        ("format", ""),
        ("environment", "staging"),
        ("layer", "archive"),
    ],
)
def test_unsafe_or_unsupported_path_inputs_are_rejected(field: str, value: object) -> None:
    with pytest.raises(ValueError):
        build_object_location(_request(**{field: value}))


def test_quarantine_requires_execution_identity() -> None:
    with pytest.raises(ValueError, match="execution_id"):
        build_object_location(_request(layer="quarantine", execution_id=None))
