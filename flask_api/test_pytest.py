import pytest
import json
import os
import users
from app import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

@pytest.fixture(autouse=True)
def setup_test_db():
    """Sets up and tears down a clean test database for each test case."""
    # Use a test database file
    original_db = users.DB_PATH
    users.DB_PATH = 'users_test.db'
    # Force re-initialize the test db
    users.init_db()
    
    yield
    
    # Restore original path and clean up test db file
    users.DB_PATH = original_db
    if os.path.exists('users_test.db'):
        try:
            os.remove('users_test.db')
        except Exception:
            pass

def test_health(client):
    """Tests that the health endpoint returns status: ok."""
    response = client.get('/health')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data == {"status": "ok"}

def test_hello_success(client):
    """Tests that the hello endpoint greets when name parameter is supplied."""
    response = client.get('/hello?name=Bob')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data == {"message": "Hello, Bob!"}

def test_hello_missing_name(client):
    """Tests that the hello endpoint returns 400 when name is missing."""
    response = client.get('/hello')
    assert response.status_code == 400
    data = json.loads(response.data)
    assert "error" in data
    assert data["error"] == "Missing required query parameter: name"

def test_users_empty_list(client):
    """Tests that GET /users initially returns an empty list."""
    response = client.get('/users')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data == []

def test_create_user_success(client):
    """Tests that POST /users successfully creates a user and GET retrieves it."""
    payload = {"name": "Alice", "email": "alice@example.com"}
    response = client.post('/users', json=payload)
    assert response.status_code == 201
    
    data = json.loads(response.data)
    assert data["id"] == 1
    assert data["name"] == "Alice"
    assert data["email"] == "alice@example.com"
    
    # Verify GET lists the user
    response = client.get('/users')
    assert response.status_code == 200
    users_list = json.loads(response.data)
    assert len(users_list) == 1
    assert users_list[0]["name"] == "Alice"
    assert users_list[0]["email"] == "alice@example.com"

def test_create_user_duplicate_email(client):
    """Tests that POST /users returns 400 error on duplicate emails."""
    payload = {"name": "Alice", "email": "alice@example.com"}
    # Create first user
    response = client.post('/users', json=payload)
    assert response.status_code == 201
    
    # Try to create duplicate
    payload_dup = {"name": "Alice Duplicate", "email": "alice@example.com"}
    response = client.post('/users', json=payload_dup)
    assert response.status_code == 400
    data = json.loads(response.data)
    assert "error" in data
    assert "already exists" in data["error"]

def test_create_user_missing_fields(client):
    """Tests that POST /users returns 400 error on missing name or email."""
    response = client.post('/users', json={"name": "Alice"})
    assert response.status_code == 400
    
    response = client.post('/users', json={"email": "alice@example.com"})
    assert response.status_code == 400
