# Simple Flask API

This is a simple Flask API with `/health`, `/hello`, `/goodbye`, and `/users` endpoints.

## Architecture

The application is refactored into a modular Blueprint-based structure:
* **`app.py`**: The application entry point. Configures the basic logging configuration and registers all module Blueprints.
* **`health.py`**: Blueprint containing the `/health` check route.
* **`greeting.py`**: Blueprint containing the greeting logic and routes for `/hello` and `/goodbye`.
* **`users.py`**: Blueprint containing the SQLite-backed `/users` endpoint (`GET` to list, `POST` to create).
* **`users.db`**: SQLite database file created automatically on startup to store user records.

Basic logging is configured to log application startup sequence and Blueprint registrations to standard output.

---

## Endpoints

### 1. GET `/health`
Returns the status of the server.
- **Response**: `{"status": "ok"}`

### 2. GET `/hello`
Greets the user by name.
- **Parameters**: 
  - `name` (string, **required**): The name of the person to greet.
- **Response (Success)**: `{"message": "Hello, <name>!"}`
- **Response (Error - Missing/Empty Name)**: `{"error": "Missing required query parameter: name"}` (Status Code: `400`)

### 3. GET `/goodbye`
Says goodbye to the user by name.
- **Parameters**: 
  - `name` (string, **required**): The name of the person to say goodbye to.
- **Response (Success)**: `{"message": "Goodbye, <name>!"}`
- **Response (Error - Missing/Empty Name)**: `{"error": "Missing required query parameter: name"}` (Status Code: `400`)

### 4. GET & POST `/users`
SQLite database backed users endpoint.
- **GET**: Lists all registered users.
- **POST**: Creates a new user record with JSON payload: `{"name": "Alice", "email": "alice@example.com"}`.

---

## How to Run

### 1. Prerequisites
Make sure you have Python 3 installed.

### 2. Install Dependencies
It is recommended to use a virtual environment:

```bash
# Create a virtual environment
python -m venv venv

# Activate the virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows (cmd):
# venv\Scripts\activate
# On Windows (PowerShell):
# .\venv\Scripts\Activate.ps1

# Install the required packages
pip install -r requirements.txt
```

### 3. Start the Server
Run the Flask application:
```bash
python app.py
```
The application will be running at `http://127.0.0.1:5000/`.

### 4. Running the Tests
To run the automated tests using `pytest` or `unittest`:
```bash
# Run pytest tests
python -m pytest test_pytest.py

# Run legacy unittest tests
python -m unittest test_app.py
```

### 5. Manual Testing
You can test the endpoints using `curl` or in your browser:

```bash
# Test health check
curl http://127.0.0.1:5000/health
# Expected Output: {"status":"ok"}

# Test hello with name
curl http://127.0.0.1:5000/hello?name=Alice
# Expected Output: {"message":"Hello, Alice!"}

# Test hello missing name
curl http://127.0.0.1:5000/hello
# Expected Output: {"error":"Missing required query parameter: name"} (Status 400)
```
