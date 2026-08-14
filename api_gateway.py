from fastapi import FastAPI
from client_user import ClientUser
from service_registry import ServiceRegistry

app = FastAPI()

@app.get="/users")
def get_users():
    client = ClientUser()
    return client.get_users()

@app.get="/services")
def get_services():
    registry = ServiceRegistry()
    return registry.get_services()