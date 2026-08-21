"""Bounded Data Quality evaluation for canonical Northstar sales batches."""

from .sales import QualityResult, QualitySeverity, evaluate_sales_batch

__all__ = ["QualityResult", "QualitySeverity", "evaluate_sales_batch"]
