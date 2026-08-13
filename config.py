# Import config
from config import *

# Define gateway route properties
gateway_route_properties = {
    'host': 'localhost',
    'port': 9103,
    'routes': {
        '/users': {
            'methods': ['GET', 'POST']
        },
        '/users/<int:user_id>': {
            'methods': ['GET', 'PUT', 'DELETE']
        }
    }
)