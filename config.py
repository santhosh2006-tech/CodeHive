# Database Configurations
DB_CONFIG = {
    'host': 'localhost',
    'database': 'user_db',
    'user': 'root',
    'password': 'password'
}

# Registry Configurations
SERVICE_REGISTRY = ServiceRegistry()
CLIENT_REGISTRY = ClientRegistry()

# Example usage:
# SERVICE_REGISTRY.register_service('example_service', 'http://example.com')
# CLIENT_REGISTRY.register_client('example_client', 'http://example.com')