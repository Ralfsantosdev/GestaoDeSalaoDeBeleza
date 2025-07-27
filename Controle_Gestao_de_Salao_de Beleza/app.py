from flask import Flask, render_template, request, redirect, url_for, flash, session
import sqlite3
import hashlib
import datetime

app = Flask(__name__)
app.secret_key = 'sua_chave_secreta_aqui'

# Função para conectar ao banco de dados
def get_db_connection():
    conn = sqlite3.connect('salon_management.db')
    conn.row_factory = sqlite3.Row
    return conn

# Criar tabelas no banco de dados
def criar_tabelas():
    conn = get_db_connection()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS clientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT,
            email TEXT,
            telefone TEXT,
            observacoes TEXT
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS produtos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT,
            custo REAL,
            preco_venda REAL
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT,
            is_admin BOOLEAN DEFAULT 0
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS funcionarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT,
            cargo TEXT,
            salario REAL
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS registro_atividades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER,
            acao TEXT,
            data_hora TEXT,
            FOREIGN KEY (usuario_id) REFERENCES usuarios (id)
        )
    ''')
    conn.commit()
    conn.close()

# Função para registrar atividades
def registrar_atividade(usuario_id, acao):
    conn = get_db_connection()
    conn.execute('''
        INSERT INTO registro_atividades (usuario_id, acao, data_hora)
        VALUES (?, ?, ?)
    ''', (usuario_id, acao, datetime.datetime.now().isoformat()))
    conn.commit()
    conn.close()

# Rota principal
@app.route('/')
def index():
    return render_template('index.html')

# Rota para registrar usuário
@app.route('/registrar', methods=['POST'])
def registrar():
    username = request.form['username']
    password = request.form['password']
    hashed_password = hashlib.sha256(password.encode()).hexdigest()  # Hash da senha

    if username and password:
        conn = get_db_connection()
        try:
            conn.execute('''
                INSERT INTO usuarios (username, password, is_admin)
                VALUES (?, ?, ?)
            ''', (username, hashed_password, 1))  # O primeiro usuário será administrador
            conn.commit()
            flash('Usuário registrado com sucesso!', 'success')
        except sqlite3.IntegrityError:
            flash('Nome de usuário já existe. Escolha outro.', 'warning')
        finally:
            conn.close()
    else:
        flash('Por favor, preencha todos os campos obrigatórios.', 'warning')

    return redirect(url_for('index'))

# Rota para login
@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']
    hashed_password = hashlib.sha256(password.encode()).hexdigest()

    conn = get_db_connection()
    user = conn.execute('SELECT * FROM usuarios WHERE username = ? AND password = ?', (username, hashed_password)).fetchone()
    conn.close()

    if user:
        session['user_id'] = user['id']
        session['username'] = user['username']
        session['is_admin'] = user['is_admin']  # Armazena se o usuário é administrador
        flash('Login bem-sucedido!', 'success')
        return redirect(url_for('index'))
    else:
        flash('Nome de usuário ou senha incorretos.', 'danger')
        return redirect(url_for('index'))

# Rota para logout
@app.route('/logout')
def logout():
    session.clear()  # Limpa a sessão
    flash('Logout realizado com sucesso.', 'success')
    return redirect(url_for('index'))

# Rota para cadastrar funcionário
@app.route('/cadastrar_funcionario', methods=['POST'])
def cadastrar_funcionario():
    if 'user_id' not in session or not session.get('is_admin'):  # Verifica se o usuário é administrador
        flash('Apenas administradores podem cadastrar funcionários.', 'warning')
        return redirect(url_for('index'))

    nome = request.form['nome']
    cargo = request.form['cargo']
    salario = request.form['salario']

    if nome and cargo and salario:
        try:
            salario = float(salario)  # Converte o salário para float
            conn = get_db_connection()
            conn.execute('''
                INSERT INTO funcionarios (nome, cargo, salario)
                VALUES (?, ?, ?)
            ''', (nome, cargo, salario))
            conn.commit()
            registrar_atividade(session['user_id'], f'Funcionário {nome} cadastrado.')  # Registro da atividade
            conn.close()
            flash('Funcionário cadastrado com sucesso!', 'success')
        except ValueError:
            flash('Por favor, insira um valor numérico válido para o salário.', 'error')
    else:
        flash('Por favor, preencha todos os campos obrigatórios.', 'warning')

    return redirect(url_for('index'))

# Rota para editar funcionário
@app.route('/editar_funcionario/<int:id>', methods=['GET', 'POST'])
def editar_funcionario(id):
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Apenas administradores podem editar funcionários.', 'warning')
        return redirect(url_for('index'))

    conn = get_db_connection()

    if request.method == 'POST':
        nome = request.form['nome']
        cargo = request.form['cargo']
        salario = request.form['salario']

        if nome and cargo and salario:
            try:
                salario = float(salario)
                conn.execute('''
                    UPDATE funcionarios
                    SET nome = ?, cargo = ?, salario = ?
                    WHERE id = ?
                ''', (nome, cargo, salario, id))
                conn.commit()
                registrar_atividade(session['user_id'], f'Funcionário {nome} editado.')  # Registro da atividade
                flash('Funcionário atualizado com sucesso!', 'success')
            except ValueError:
                flash('Por favor, insira um valor numérico válido para o salário.', 'error')
        else:
            flash('Por favor, preencha todos os campos obrigatórios.', 'warning')

        return redirect(url_for('index'))

    funcionario = conn.execute('SELECT * FROM funcionarios WHERE id = ?', (id,)).fetchone()
    conn.close()
    return render_template('editar_funcionario.html', funcionario=funcionario)

# Rota para remover funcionário
@app.route('/remover_funcionario/<int:id>', methods=['POST'])
def remover_funcionario(id):
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Apenas administradores podem remover funcionários.', 'warning')
        return redirect(url_for('index'))

    conn = get_db_connection()
    funcionario = conn.execute('SELECT * FROM funcionarios WHERE id = ?', (id,)).fetchone()
    if funcionario:
        conn.execute('DELETE FROM funcionarios WHERE id = ?', (id,))
        conn.commit()
        registrar_atividade(session['user_id'], f'Funcionário {funcionario["nome"]} removido.')  # Registro da atividade
        flash('Funcionário removido com sucesso!', 'success')
    else:
        flash('Funcionário não encontrado.', 'warning')
    conn.close()

    return redirect(url_for('index'))

# Rota para listar funcionários
@app.route('/listar_funcionarios')
def listar_funcionarios():
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Apenas administradores podem acessar essa página.', 'warning')
        return redirect(url_for('index'))

    conn = get_db_connection()
    funcionarios = conn.execute('SELECT * FROM funcionarios').fetchall()
    conn.close()
    return render_template('listar_funcionarios.html', funcionarios=funcionarios)

# Rota para ver registro de atividades
@app.route('/registro_atividades')
def registro_atividades():
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Apenas administradores podem acessar essa página.', 'warning')
        return redirect(url_for('index'))

    conn = get_db_connection()
    atividades = conn.execute('SELECT * FROM registro_atividades').fetchall()
    conn.close()
    return render_template('registro_atividades.html', atividades=atividades)

# Rota para cadastrar cliente
@app.route('/cadastrar_cliente', methods=['POST'])
def cadastrar_cliente():
    if 'user_id' not in session:  # Verifica se o usuário está logado
        flash('Você precisa estar logado para cadastrar clientes.', 'warning')
        return redirect(url_for('index'))

    nome = request.form['nome']
    email = request.form['email']
    telefone = request.form['telefone']
    observacoes = request.form['observacoes']

    if nome and email and telefone:
        conn = get_db_connection()
        conn.execute('''
            INSERT INTO clientes (nome, email, telefone, observacoes)
            VALUES (?, ?, ?, ?)
        ''', (nome, email, telefone, observacoes))
        conn.commit()
        conn.close()
        flash('Cliente cadastrado com sucesso!', 'success')
    else:
        flash('Por favor, preencha todos os campos obrigatórios.', 'warning')

    return redirect(url_for('index'))

# Rota para cadastrar produto
@app.route('/cadastrar_produto', methods=['POST'])
def cadastrar_produto():
    if 'user_id' not in session:  # Verifica se o usuário está logado
        flash('Você precisa estar logado para cadastrar produtos.', 'warning')
        return redirect(url_for('index'))

    nome = request.form['produto_nome']
    custo = request.form['custo']
    preco_venda = request.form['preco_venda']

    if nome and custo and preco_venda:
        try:
            custo = float(custo)
            preco_venda = float(preco_venda)
            conn = get_db_connection()
            conn.execute('''
                INSERT INTO produtos (nome, custo, preco_venda)
                VALUES (?, ?, ?)
            ''', (nome, custo, preco_venda))
            conn.commit()
            conn.close()
            flash('Produto cadastrado com sucesso!', 'success')
        except ValueError:
            flash('Por favor, insira valores numéricos válidos para custo e preço de venda.', 'error')
    else:
        flash('Por favor, preencha todos os campos obrigatórios.', 'warning')

    return redirect(url_for('index'))

# Rota para ver relatório financeiro
@app.route('/relatorio')
def relatorio():
    if 'user_id' not in session:  # Verifica se o usuário está logado
        flash('Você precisa estar logado para ver o relatório.', 'warning')
        return redirect(url_for('index'))

    conn = get_db_connection()
    total_clientes = conn.execute('SELECT COUNT(*) FROM clientes').fetchone()[0]
    total_produtos = conn.execute('SELECT COUNT(*) FROM produtos').fetchone()[0]
    conn.close()
    return f"Total de Clientes: {total_clientes}<br>Total de Produtos: {total_produtos}"

# Inicializar o banco de dados
criar_tabelas()

if __name__ == '__main__':
    app.run(debug=True)