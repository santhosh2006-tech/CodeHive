from flask import Blueprint, jsonify

health_bp = Blueprint('health', __name__)

@health_bp.route('/health', methods=['GET'])
def health():
    """Returns the health status of the application."""
    return jsonify({"status": "ok"})
