# Project README

## Introduction
This project provides a basic structure for a microservices-based system. It includes a user database, a service registry, an API gateway, and infrastructure management.

## Components
* User Database: Stores user credentials and provides authentication functionality.
* Service Registry: Registers and manages services in the system.
* API Gateway: Handles incoming requests and routes them to the appropriate services.
* Infrastructure: Manages the underlying infrastructure for the system.

## Tests
The project includes unit tests for each component, which can be run using the unittest framework.

## Usage
1. Run the tests: python -m unittest discover
2. Start the API gateway: python api_gateway.py
3. Use the API gateway to access the services: curl http://localhost:9204/test_service