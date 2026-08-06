from flask import Blueprint, request, jsonify

greeting_bp = Blueprint('greeting', __name__)

def get_greeting_response(greeting_word):
    """Reusable helper for greetings with input validation."""
    name = request.args.get('name', '').strip()
    if not name:
        return jsonify({"error": "Missing required query parameter: name"}), 400
    return jsonify({"message": f"{greeting_word}, {name}!"})

@greeting_bp.route('/hello', methods=['GET'])
def hello():
    """Greets the user by name."""
    return get_greeting_response("Hello")

@greeting_bp.route('/goodbye', methods=['GET'])
def goodbye():
    """Says goodbye to the user by name."""
    return get_greeting_response("Goodbye")
