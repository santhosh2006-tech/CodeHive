from flask import Flask, request, jsonify
from client_user import ClientUser
from client_registry import ClientRegistry

app = Flask(__name__)

# Import client libraries
client_user = ClientUser()
client_registry = ClientRegistry()

# Map endpoints
@app.route('/users', methods=['GET'])
def get_users():
    users = client_user.get_users()
    return jsonify(users)

@app.route('/users', methods=['POST'])
def create_user():
    data = request.json
    user = client_user.create_user(data)
    return jsonify(user)

@app.route('/users/<int:user_id>', methods=['GET'])
def get_user(user_id):
    user = client_user.get_user(user_id)
    return jsonify(user)

@app.route('/users/<int:user_id>', methods=['PUT'])
def update_user(user_id):
    data = request.json
    user = client_user.update_user(user_id, data)
    return jsonify(user)

@app.route('/users/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    client_user.delete_user(user_id)
    return jsonify({'message': 'User deleted'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=9103)