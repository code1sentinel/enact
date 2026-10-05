"""Adapter failures. Exit closed; never write a half-valid empty payload."""

from __future__ import annotations


class AdapterError(ValueError):
    """Unparseable or unmappable dump. Message is safe to print."""
