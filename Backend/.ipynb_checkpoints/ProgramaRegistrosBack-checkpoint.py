from flask import Flask, request, jsonify
import os
import json
import bcrypt

app = Flask(__name__)

# --- Archivos ---
RUTA_USUARIOS = "./usuarios.json" # Archivo para guardar usuarios

# --- Funciones para manejar usuarios ---

def cargar_usuarios():
    """Carga los usuarios desde el archivo JSON."""
    if not os.path.exists(RUTA_USUARIOS):
        return {} # Devuelve un diccionario vacío si no existe el archivo
    try:
        with open(RUTA_USUARIOS, 'r', encoding='utf-8') as f:
            usuarios = json.load(f)
            # Asegurarse de que es un diccionario
            return usuarios if isinstance(usuarios, dict) else {}
    except json.JSONDecodeError:
        print(f"Advertencia: El archivo de usuarios '{RUTA_USUARIOS}' está vacío o corrupto. Iniciando con diccionario de usuarios vacío.")
        return {}
    except Exception as e:
        print(f"Error al cargar usuarios: {e}")
        return {}

def guardar_usuarios(usuarios):
    """Guarda los usuarios en el archivo JSON."""
    try:
        with open(RUTA_USUARIOS, 'w', encoding='utf-8') as f:
            json.dump(usuarios, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"Error al guardar usuarios: {e}")

# --- Endpoint para Registro ---
@app.route('/register', methods=['POST'])
def register_route():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No se recibieron datos'}), 400

        username = data.get('username')
        password = data.get('password')
        company = data.get('company')

        if not username or not password or not company:
            return jsonify({'error': 'Faltan campos requeridos (usuario, contraseña, empresa)'}), 400

        usuarios = cargar_usuarios()

        if username in usuarios:
            return jsonify({'error': 'El usuario ya existe'}), 409 # 409 Conflict

        # Hashear la contraseña
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

        # Guardar usuario y contraseña hasheada
        usuarios[username] = {
            "password_hash": hashed_password.decode('utf-8'), # Guardar el hash como string
            "company": company
        }
        guardar_usuarios(usuarios)

        return jsonify({'message': 'Usuario registrado exitosamente'}), 201 # 201 Created

    except Exception as e:
        print(f"Error en la ruta /register: {e}")
        return jsonify({'error': f'Error en el registro: {e}'}), 500

# --- Endpoint para Inicio de Sesión ---
@app.route('/login', methods=['POST'])
def login_route():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No se recibieron datos'}), 400

        username = data.get('username')
        password = data.get('password')

        if not username or not password:
            return jsonify({'error': 'Faltan campos requeridos (usuario, contraseña)'}), 400

        usuarios = cargar_usuarios()

        if username not in usuarios:
            return jsonify({'error': 'Usuario no encontrado'}), 404

        user_data = usuarios[username]
        stored_password_hash = user_data.get("password_hash")
        company = user_data.get("company")

        if not stored_password_hash or company is None:
             print(f"Error: Datos incompletos para el usuario {username} en el archivo.")
             return jsonify({'error': 'Error interno en los datos del usuario'}), 500

        # Verificar la contraseña hasheada
        if bcrypt.checkpw(password.encode('utf-8'), stored_password_hash.encode('utf-8')):
            # Contraseña correcta
            return jsonify({'message': 'Inicio de sesión exitoso', 'username': username, 'company': company}), 200
        else:
            # Contraseña incorrecta
            return jsonify({'error': 'Contraseña incorrecta'}), 401 # 401 Unauthorized

    except Exception as e:
        print(f"Error en la ruta /login: {e}")
        return jsonify({'error': f'Error en el inicio de sesión: {e}'}), 500

if __name__ == '__main__':
    # Crear el archivo de usuarios si no existe al iniciar
    if not os.path.exists(RUTA_USUARIOS):
        guardar_usuarios({})

    # Correr en un puerto diferente al backend principal (ej. 5002)
    app.run(debug=True, port=5002)