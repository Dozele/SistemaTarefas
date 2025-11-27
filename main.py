import mysql.connector
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
import os

# Configura o Flask para servir arquivos estáticos da pasta atual
app = Flask(__name__, static_url_path='', static_folder='.')
CORS(app)

# --- CONFIGURAÇÃO DO BANCO ---
# IMPORTANTE: Verifique se a senha do banco está correta
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': "", # <--- SUA SENHA AQUI
    'database': 'taskflow_db'
}

def get_db_connection():
    try:
        conn = mysql.connector.connect(**db_config)
        return conn
    except mysql.connector.Error as err:
        print(f"Erro MySQL: {err}")
        return None

# --- ROTA PRINCIPAL (Carrega o Site) ---
@app.route('/')
def index():
    # Quando acessar http://localhost:5000, entrega o index.html
    return send_from_directory('.', 'index.html')

# --- ROTAS DE AUTENTICAÇÃO ---

@app.route('/register', methods=['POST'])
def register():
    data = request.json
    conn = get_db_connection()
    if not conn: return jsonify({"error": "Erro de conexão DB"}), 500
    cursor = conn.cursor()
    
    hashed_pw = generate_password_hash(data['password'])
    
    try:
        sql = "INSERT INTO users (name, email, password) VALUES (%s, %s, %s)"
        cursor.execute(sql, (data['name'], data['email'], hashed_pw))
        conn.commit()
        return jsonify({"message": "Usuário criado com sucesso!"}), 201
    except mysql.connector.Error as err:
        return jsonify({"error": "Email já cadastrado ou erro no servidor"}), 400
    finally:
        cursor.close()
        conn.close()

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    conn = get_db_connection()
    if not conn: return jsonify({"error": "Erro de conexão DB"}), 500
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("SELECT * FROM users WHERE email = %s", (data['email'],))
    user = cursor.fetchone()
    
    cursor.close()
    conn.close()

    if user and check_password_hash(user['password'], data['password']):
        return jsonify({
            "message": "Login realizado",
            "user": {
                "id": user['id'],
                "name": user['name'],
                "email": user['email']
            }
        }), 200
    else:
        return jsonify({"error": "Email ou senha incorretos"}), 401

# --- ROTAS DE TAREFAS ---

@app.route('/tasks', methods=['GET'])
def get_tasks():
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({"error": "Usuário não identificado"}), 401

    conn = get_db_connection()
    if not conn: return jsonify({"error": "Erro de conexão DB"}), 500
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("SELECT * FROM tasks WHERE user_id = %s ORDER BY created_at DESC", (user_id,))
    tasks = cursor.fetchall()
    
    for task in tasks:
        if task['due_date']:
            task['due_date'] = task['due_date'].strftime('%Y-%m-%d')
        task['completed'] = bool(task['completed'])
            
    cursor.close()
    conn.close()
    return jsonify(tasks)

@app.route('/tasks', methods=['POST'])
def add_task():
    data = request.json
    conn = get_db_connection()
    if not conn: return jsonify({"error": "Erro de conexão DB"}), 500
    cursor = conn.cursor()
    
    sql = "INSERT INTO tasks (user_id, title, category, priority, due_date, completed) VALUES (%s, %s, %s, %s, %s, %s)"
    
    due_date = data.get('due_date')
    if due_date == '': due_date = None

    val = (data['user_id'], data['title'], data['category'], data['priority'], due_date, False)
    
    try:
        cursor.execute(sql, val)
        conn.commit()
        return jsonify({"message": "Criado", "id": cursor.lastrowid}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/tasks/<int:id>', methods=['PUT'])
def update_task(id):
    data = request.json
    conn = get_db_connection()
    if not conn: return jsonify({"error": "Erro de conexão DB"}), 500
    cursor = conn.cursor()

    # Verifica se é uma edição completa ou apenas toggle de status
    if 'title' in data:
        # EDIÇÃO COMPLETA
        sql = "UPDATE tasks SET title=%s, category=%s, priority=%s, due_date=%s WHERE id=%s"
        due_date = data.get('due_date')
        if due_date == '': due_date = None
        val = (data['title'], data['category'], data['priority'], due_date, id)
    else:
        # APENAS ATUALIZAR STATUS (CHECKBOX)
        sql = "UPDATE tasks SET completed = %s WHERE id = %s"
        val = (data['completed'], id)

    try:
        cursor.execute(sql, val)
        conn.commit()
        return jsonify({"message": "Atualizado"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/tasks/<int:id>', methods=['DELETE'])
def delete_task(id):
    conn = get_db_connection()
    if not conn: return jsonify({"error": "Erro de conexão DB"}), 500
    cursor = conn.cursor()
    cursor.execute("DELETE FROM tasks WHERE id = %s", (id,))
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({"message": "Deletado"}), 200

if __name__ == '__main__':
    print("Servidor rodando! Acesse: http://127.0.0.1:5000")
    app.run(debug=True)