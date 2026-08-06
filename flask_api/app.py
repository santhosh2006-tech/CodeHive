import logging
from flask import Flask
from health import health_bp
from greeting import greeting_bp
from users import users_bp

# Configure basic logging to log startup and blueprint registration events
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Register Blueprints
app.register_blueprint(health_bp)
logger.info("Registered health blueprint.")

app.register_blueprint(greeting_bp)
logger.info("Registered greeting blueprint.")

app.register_blueprint(users_bp)
logger.info("Registered users blueprint.")

logger.info("Flask application initialized with blueprints.")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
