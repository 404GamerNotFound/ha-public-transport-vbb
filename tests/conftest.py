"""Shared fixtures for VBB tests."""

import pytest


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Allow loading custom_components/vbb in every test."""
    yield
