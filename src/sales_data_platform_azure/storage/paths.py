"""Canonical, safe logical addressing for governed data-layer objects."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import date

from .models import DataLayer, ObjectLocation, StorageEnvironment

_COMPONENT = re.compile(r"[a-z0-9](?:[a-z0-9._-]*[a-z0-9])?")
_FORMAT = re.compile(r"[a-z0-9]+")


@dataclass(frozen=True, slots=True)
class PathRequest:
    """Stable logical inputs to the one canonical path builder."""

    environment: StorageEnvironment | str
    layer: DataLayer | str
    source_system: str
    dataset: str
    partition_date: date
    stable_object_identity: str
    format: str
    execution_id: str | None = None


def build_object_location(request: PathRequest) -> ObjectLocation:
    """Build a deterministic, cloud-neutral object location using `/` separators."""
    environment = _enum_value(StorageEnvironment, request.environment, "environment")
    layer = _enum_value(DataLayer, request.layer, "layer")
    source_system = _component(request.source_system, "source_system")
    dataset = _component(request.dataset, "dataset")
    stable_identity = _identity(request.stable_object_identity, "stable_object_identity")
    extension = _extension(request.format)

    identity = stable_identity
    if layer is DataLayer.QUARANTINE:
        identity = f"{stable_identity}\x00{_identity(request.execution_id, 'execution_id')}"

    digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()
    object_name = f"{dataset}-{digest}.{extension}"
    partition = request.partition_date
    address = "/".join(
        (
            environment.value,
            layer.value,
            source_system,
            dataset,
            f"year={partition.year:04d}",
            f"month={partition.month:02d}",
            f"day={partition.day:02d}",
            object_name,
        )
    )
    return ObjectLocation(environment, layer, address)


def _enum_value(enum_type: type[StorageEnvironment] | type[DataLayer], value: object, name: str):
    try:
        return enum_type(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"unsupported {name}: {value!r}") from error


def _component(value: object, name: str) -> str:
    text = _identity(value, name).lower()
    if not _COMPONENT.fullmatch(text):
        raise ValueError(f"{name} contains an unsafe path fragment")
    return text


def _identity(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be non-empty text")
    text = value.strip()
    if text in {".", ".."} or ".." in text or "/" in text or "\\" in text:
        raise ValueError(f"{name} contains an unsafe path fragment")
    if text.startswith(("~", ".")) or re.match(r"^[A-Za-z]:", text):
        raise ValueError(f"{name} must not be an absolute or relative path")
    return text


def _extension(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("format must be non-empty text")
    extension = value.strip().lower().removeprefix(".")
    if not _FORMAT.fullmatch(extension):
        raise ValueError("format contains an unsafe extension")
    return extension
