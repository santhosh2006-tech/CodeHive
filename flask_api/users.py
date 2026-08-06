import sqlite3
import os
from flask import Blueprint, request, jsonify

users_bp = Blueprint('users', __name__)
DB_PATH = 'users.db'

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE
        )
    ''')
    conn.commit()
    conn.close()

# Ensure table exists on module import/startup
init_db()

@users_bp.route('/users', methods=['GET'])
def get_users():
    """Lists all users in the SQLite database."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id, name, email FROM users')
        rows = cursor.fetchall()
        users = [dict(row) for row in rows]
        conn.close()
        return jsonify(users), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@users_bp.route('/users', methods=['POST'])
def create_user():
    """Creates a new user in the SQLite database."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "Missing JSON request body"}), 400
    
    name = data.get('name', '').strip()
    email = data.get('email', '').strip()
    
    if not name or not email:
        return jsonify({"error": "Missing required fields: name, email"}), 400
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('INSERT INTO users (name, email) VALUES (?, ?)', (name, email))
        conn.commit()
        user_id = cursor.lastrowid
        conn.close()
        return jsonify({"id": user_id, "name": name, "email": email}), 201
    except sqlite3.IntegrityError:
        return jsonify({"error": f"User with email '{email}' already exists"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500
