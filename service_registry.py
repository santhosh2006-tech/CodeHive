# service_registry.py
from flask import Flask, request, jsonify
from config import REGISTRY_SERVICE_HOST, REGISTRY_SERVICE_PORT

app = Flask(__name__)

services = {}

class Service:
    def __init__(self, name, host, port):
        self.name = name
        self.host = host
        self.port = port

    def to_dict(self):
        return {'name': self.name, 'host': self.host, 'port': self.port}

@app.route('/register', methods=['POST'])
def register_service():
    data = request.json
    service_name = data['name']
    host = data['host']
    port = data['port']
    services[service_name] = Service(service_name, host, port)
    return jsonify({'message': 'Service registered successfully'}), 201

@app.route('/deregister', methods=['POST'])
def deregister_service():
    data = request.json
    service_name = data['name']
    if service_name in services:
        del services[service_name]
        return jsonify({'message': 'Service deregistered successfully'}), 200
    else:
        return jsonify({'message': 'Service not found'}), 404

@app.route('/services', methods=['GET'])
def get_services():
    services_list = [service.to_dict() for service in services.values()]
    return jsonify(services_list), 200

if __name__ == '__main__':
    app.run(host=REGISTRY_SERVICE_HOST, port=REGISTRY_SERVICE_PORT)