from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from client_user import ClientUser
from service_registry import ServiceRegistry

app = FastAPI()

# Initialize service registry
service_registry = ServiceRegistry()

# Define request and response models
class UserRequest(BaseModel):
    username: str
    password: str

class UserResponse(BaseModel):
    username: str
    message: str

# Define endpoint for user registration
@app.post("/register")
def register_user(request: UserRequest):
    client_user = ClientUser(request.username, request.password)
    if client_user.register():
        return JSONResponse(content={"username": request.username, "message": "User registered successfully"}, media_type="application/json")
    else:
        return JSONResponse(content={"username": request.username, "message": "User already exists"}, media_type="application/json", status_code=400)

# Define endpoint for user login
@app.post("/login")
def login_user(request: UserRequest):
    client_user = ClientUser(request.username, request.password)
    if client_user.login():
        return JSONResponse(content={"username": request.username, "message": "User logged in successfully"}, media_type="application/json")
    else:
        return JSONResponse(content={"username": request.username, "message": "Invalid username or password"}, media_type="application/json", status_code=401)
