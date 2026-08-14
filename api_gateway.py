from flask import Flask, request, jsonify
from client_registry import ClientRegistry
from config import DB_NAME

app = Flask(__name__)

client_registry = ClientRegistry('api_gateway', 'localhost', 9103)
user_db = UserDB(DB_NAME)

@app.route('/register', methods=['POST'])
def register_user():
    data = request.json
    username = data['username']
    password = data['password']
    if user_db.get_user(username):
        return jsonify({'message': 'Username already exists'}), 400
    user_db.insert_user(username, password)
    return jsonify({'message': 'User registered successfully'}), 201

@app.route('/login', methods=['POST'])
def login_user():
    data = request.json
    username = data['username']
    password = data['password']
    user = user_db.get_user(username)
    if user and user[2] == password:
        return jsonify({'message': 'Login successful'}), 200
    else:
        return jsonify({'message': 'Invalid username or password'}), 401

@app.route('/services', methods=['GET'])
def get_services():
    services, status_code = client_registry.get_services()
    return jsonify(services), status_code

if __name__ == '__main__':
    client_registry.register()
    app.run(host='localhost', port=9103)