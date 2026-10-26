# Importamos Flask (servidor web), request (formularios), session (login), sqlite3 (base de datos), random e json
from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
import random
import json

app = Flask(__name__)
# Clave de seguridad obligatoria para poder usar las sesiones de Login
app.secret_key = 'clave_super_secreta' 

# 1. Función que crea las tablas en la base de datos si no existen
def init_db():
    conn = sqlite3.connect('database.db')
    # Tabla de usuarios: guarda nombre único y contraseña
    conn.execute('CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username TEXT UNIQUE, password TEXT)')
    # Tabla de tareas: asocia cada tarea al usuario que la creó
    conn.execute('CREATE TABLE IF NOT EXISTS tasks (id INTEGER PRIMARY KEY, username TEXT, title TEXT, duration INTEGER, status TEXT DEFAULT "pendiente")')
    conn.close()

# 2. Función para crear el archivo JSON visible para la presentación en VS Code
def actualizar_archivo_visible():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    # Obtenemos todas las tareas y las pasamos a formato diccionario
    tareas = [dict(row) for row in conn.execute('SELECT * FROM tasks').fetchall()]
    conn.close()
    # Escribimos los datos en el archivo "base_datos_visible.json"
    with open('base_datos_visible.json', 'w', encoding='utf-8') as f:
        json.dump(tareas, f, indent=4, ensure_ascii=False)

# 3. Función que simula la IA eligiendo textos al azar para el paso a paso
def generar_pasos_ia(tarea):
    analisis = ["Evaluar los recursos necesarios para", "Revisar la documentación base de", "Planificar la estructura inicial de"]
    ejecucion = ["Aplicar los métodos correspondientes en", "Desarrollar el proceso principal de", "Ejecutar la lógica de"]
    cierre = ["Verificar los resultados obtenidos", "Documentar los detalles del proceso", "Confirmar que no haya errores pendientes"]
    
    return [
        f"{random.choice(analisis)} '{tarea}'",
        f"{random.choice(ejecucion)} '{tarea}'",
        random.choice(cierre)
    ]

# --- RUTAS DE AUTENTICACIÓN ---

# 4. Ruta para registrarse
@app.route('/register', methods=['GET', 'POST'])
def register():
    error = None
    if request.method == 'POST': # Si se hizo clic en el botón de registro
        user, pwd = request.form['username'], request.form['password']
        try:
            conn = sqlite3.connect('database.db')
            conn.execute('INSERT INTO users (username, password) VALUES (?, ?)', (user, pwd))
            conn.commit()
            conn.close()
            return redirect(url_for('login')) # Si es exitoso, lo envía al Login
        except sqlite3.IntegrityError:
            error = "El usuario ya existe." # Error si el usuario ya está en la BD
    return render_template('register.html', error=error)

# 5. Ruta para Iniciar Sesión
@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        user, pwd = request.form['username'], request.form['password']
        conn = sqlite3.connect('database.db')
        # Busca si coinciden el usuario y contraseña
        usuario = conn.execute('SELECT * FROM users WHERE username = ? AND password = ?', (user, pwd)).fetchone()
        conn.close()
        
        if usuario:
            session['username'] = user # Guarda el usuario en la sesión del navegador
            return redirect(url_for('index')) # Lo envía al Dashboard
        error = "Credenciales incorrectas."
    return render_template('login.html', error=error)

# 6. Ruta para Cerrar Sesión
@app.route('/logout')
def logout():
    session.pop('username', None) # Borra la sesión actual
    return redirect(url_for('login'))

# --- RUTAS DEL DASHBOARD ---

# 7. Ruta Principal (Dashboard)
@app.route('/')
def index():
    # Bloqueo: Si no hay sesión iniciada, lo devuelve al Login
    if 'username' not in session:
        return redirect(url_for('login'))
        
    conn = sqlite3.connect('database.db')
    # Extrae solo las tareas del usuario logueado, ordenando las pendientes primero
    tasks_data = conn.execute('SELECT * FROM tasks WHERE username = ? ORDER BY status DESC, id DESC', (session['username'],)).fetchall()
    conn.close()
    
    # Formatea las tareas y les añade los pasos de la IA antes de enviarlas al HTML
    tasks = [{'id': r[0], 'title': r[2], 'duration': r[3], 'status': r[4], 'steps': generar_pasos_ia(r[2])} for r in tasks_data]
    return render_template('index.html', tasks=tasks, username=session['username'])

# 8. Ruta para Agregar Tarea (Botón Agregar Tarea)
@app.route('/add', methods=['POST'])
def add():
    if 'username' in session:
        title, duration = request.form.get('title'), request.form.get('duration', 1)
        conn = sqlite3.connect('database.db')
        # Inserta la tarea vinculándola al usuario de la sesión
        conn.execute('INSERT INTO tasks (username, title, duration, status) VALUES (?, ?, ?, "pendiente")', (session['username'], title, int(duration)))
        conn.commit()
        conn.close()
        actualizar_archivo_visible() # Actualiza el archivo JSON al agregar
    return redirect(url_for('index'))

# 9. Ruta para Marcar Completada (Botón ✓)
@app.route('/complete/<int:id>')
def complete(id):
    conn = sqlite3.connect('database.db')
    conn.execute('UPDATE tasks SET status = "completada" WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    actualizar_archivo_visible() # Actualiza el JSON
    return redirect(url_for('index'))

# 10. Ruta para Eliminar Tarea (Botón ✗)
@app.route('/delete/<int:id>')
def delete(id):
    conn = sqlite3.connect('database.db')
    conn.execute('DELETE FROM tasks WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    actualizar_archivo_visible() # Actualiza el JSON
    return redirect(url_for('index'))

# 11. Arranque de la aplicación
if __name__ == '__main__':
    init_db() # Crea las tablas al arrancar
    actualizar_archivo_visible() 
    app.run(debug=True) # Enciende el servidor local