import logging
from logger import Logger
from service_registry import ServiceRegistry

logger = Logger().get_logger()

REGISTRY_CONFIG = {
    'host': 'localhost',
    'port': 9002
}

registry = ServiceRegistry()
