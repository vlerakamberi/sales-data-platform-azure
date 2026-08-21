"""Typed contracts shared by the local transformation and quality boundaries."""

from .runtime import (
    ArtifactMetadata,
    ArtifactType,
    ExecutionContext,
    FailureClassification,
    ProcessingOutcome,
    SourceIdentity,
    TransformationResult,
)

__all__ = [
    "ArtifactMetadata",
    "ArtifactType",
    "ExecutionContext",
    "FailureClassification",
    "ProcessingOutcome",
    "SourceIdentity",
    "TransformationResult",
]
