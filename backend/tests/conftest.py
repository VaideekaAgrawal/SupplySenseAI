"""Test fixtures and shared test utilities."""

import pytest
from fastapi.testclient import TestClient

# Add backend root to sys.path
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from main import app
from services.data_store import DataStore


@pytest.fixture(scope="session")
def client():
    """FastAPI test client (reused across all tests in session)."""
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="session")
def store():
    """Shared data store instance."""
    return DataStore.get()


@pytest.fixture(scope="session")
def sample_shipment(store):
    """Return the first shipment from the seeded data store."""
    return store.get_shipments()[0]


@pytest.fixture(scope="session")
def sample_disruption(store):
    """Return the first disruption from the seeded data store."""
    return store.get_disruptions()[0]
