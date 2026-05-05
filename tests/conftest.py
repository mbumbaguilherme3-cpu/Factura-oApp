"""
Pytest Configuration
Shared fixtures and configuration for all tests
"""

import pytest
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


@pytest.fixture(scope='session')
def test_config():
    """Test configuration"""
    return {
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'SQLALCHEMY_TRACK_MODIFICATIONS': False
    }


@pytest.fixture
def temp_db(tmpdir):
    """Temporary database for testing"""
    db_path = str(tmpdir.join('test.db'))
    return f'sqlite:///{db_path}'
