
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import psycopg2
import bcrypt
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'

# Database connection
def get_db_connection():
    try:
        database_url = os.environ.get('DATABASE_URL')
        if database_url:
            conn = psycopg2.connect(database_url)
        else:
            # For local development without database
            return None
        return conn
    except:
        return None

# Initialize database tables
def init_db():
    conn = get_db_connection()
    if not conn:
        return
    
    try:
        cur = conn.cursor()
        
        # Users table
        cur.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                email VARCHAR(100) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                full_name VARCHAR(100),
                phone VARCHAR(20),
                address TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Categories table
        cur.execute('''
            CREATE TABLE IF NOT EXISTS categories (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                description TEXT
            )
        ''')
        
        # Products table
        cur.execute('''
            CREATE TABLE IF NOT EXISTS products (
                id SERIAL PRIMARY KEY,
                name VARCHAR(200) NOT NULL,
                description TEXT,
                price DECIMAL(10,2) NOT NULL,
                stock_quantity INTEGER DEFAULT 0,
                category_id INTEGER REFERENCES categories(id),
                seller_id INTEGER REFERENCES users(id),
                image_url VARCHAR(500),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Cart table
        cur.execute('''
            CREATE TABLE IF NOT EXISTS cart (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id),
                product_id INTEGER REFERENCES products(id),
                quantity INTEGER DEFAULT 1,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Orders table
        cur.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id),
                total_amount DECIMAL(10,2) NOT NULL,
                status VARCHAR(50) DEFAULT 'pending',
                shipping_address TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Insert sample data
        cur.execute("SELECT COUNT(*) FROM categories")
        if cur.fetchone()[0] == 0:
            sample_categories = [
                ('Điện tử', 'Thiết bị điện tử và công nghệ'),
                ('Thời trang', 'Quần áo và phụ kiện'),
                ('Nhà cửa', 'Đồ gia dụng và nội thất'),
                ('Sách', 'Sách và văn phòng phẩm')
            ]
            cur.executemany("INSERT INTO categories (name, description) VALUES (%s, %s)", sample_categories)
            
            sample_products = [
                ('iPhone 15', 'Điện thoại thông minh mới nhất', 25000000, 10, 1, 'https://via.placeholder.com/300x300'),
                ('Áo thun nam', 'Áo thun cotton cao cấp', 150000, 50, 2, 'https://via.placeholder.com/300x300'),
                ('Bàn làm việc', 'Bàn gỗ hiện đại', 2500000, 5, 3, 'https://via.placeholder.com/300x300'),
                ('Sách lập trình', 'Học lập trình Python', 200000, 20, 4, 'https://via.placeholder.com/300x300')
            ]
            cur.executemany("INSERT INTO products (name, description, price, stock_quantity, category_id, image_url) VALUES (%s, %s, %s, %s, %s, %s)", sample_products)
        
        conn.commit()
        cur.close()
    except Exception as e:
        print(f"Database error: {e}")
    finally:
        conn.close()

@app.route('/')
def home():
    conn = get_db_connection()
    products = []
    categories = []
    
    if conn:
        try:
            cur = conn.cursor()
            cur.execute('''
                SELECT p.id, p.name, p.description, p.price, p.image_url, c.name as category_name
                FROM products p
                LEFT JOIN categories c ON p.category_id = c.id
                ORDER BY p.created_at DESC
                LIMIT 12
            ''')
            products = cur.fetchall()
            
            cur.execute('SELECT id, name FROM categories')
            categories = cur.fetchall()
            
            cur.close()
            conn.close()
        except Exception as e:
            print(f"Error: {e}")
    
    return render_template('index.html', products=products, categories=categories)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        full_name = request.form['full_name']
        
        conn = get_db_connection()
        if not conn:
            flash('Database connection failed')
            return redirect(url_for('register'))
            
        try:
            cur = conn.cursor()
            
            # Check if user exists
            cur.execute('SELECT id FROM users WHERE username = %s OR email = %s', (username, email))
            if cur.fetchone():
                flash('Username or email already exists')
                return redirect(url_for('register'))
            
            # Hash password
            password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            
            # Insert new user
            cur.execute('''
                INSERT INTO users (username, email, password_hash, full_name)
                VALUES (%s, %s, %s, %s)
            ''', (username, email, password_hash, full_name))
            
            conn.commit()
            cur.close()
            conn.close()
            
            flash('Registration successful! Please login.')
            return redirect(url_for('login'))
            
        except Exception as e:
            flash(f'Registration failed: {e}')
            return redirect(url_for('register'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = get_db_connection()
        if not conn:
            flash('Database connection failed')
            return redirect(url_for('login'))
        
        try:
            cur = conn.cursor()
            cur.execute('SELECT id, username, password_hash FROM users WHERE username = %s', (username,))
            user = cur.fetchone()
            
            if user and bcrypt.checkpw(password.encode('utf-8'), user[2].encode('utf-8')):
                session['user_id'] = user[0]
                session['username'] = user[1]
                flash('Login successful!')
                return redirect(url_for('home'))
            else:
                flash('Invalid username or password')
                
            cur.close()
            conn.close()
            
        except Exception as e:
            flash(f'Login failed: {e}')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully')
    return redirect(url_for('home'))

@app.route('/product/<int:product_id>')
def product_detail(product_id):
    conn = get_db_connection()
    product = None
    
    if conn:
        try:
            cur = conn.cursor()
            cur.execute('''
                SELECT p.id, p.name, p.description, p.price, p.stock_quantity, p.image_url, c.name as category_name
                FROM products p
                LEFT JOIN categories c ON p.category_id = c.id
                WHERE p.id = %s
            ''', (product_id,))
            product = cur.fetchone()
            
            cur.close()
            conn.close()
        except Exception as e:
            print(f"Error: {e}")
    
    return render_template('product_detail.html', product=product)

@app.route('/add_to_cart/<int:product_id>')
def add_to_cart(product_id):
    if 'user_id' not in session:
        flash('Please login to add items to cart')
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    if not conn:
        flash('Database connection failed')
        return redirect(url_for('home'))
    
    try:
        cur = conn.cursor()
        
        # Check if item already in cart
        cur.execute('SELECT id, quantity FROM cart WHERE user_id = %s AND product_id = %s', 
                   (session['user_id'], product_id))
        cart_item = cur.fetchone()
        
        if cart_item:
            # Update quantity
            cur.execute('UPDATE cart SET quantity = quantity + 1 WHERE id = %s', (cart_item[0],))
        else:
            # Add new item
            cur.execute('INSERT INTO cart (user_id, product_id, quantity) VALUES (%s, %s, 1)',
                       (session['user_id'], product_id))
        
        conn.commit()
        cur.close()
        conn.close()
        
        flash('Product added to cart!')
        
    except Exception as e:
        flash(f'Error adding to cart: {e}')
    
    return redirect(url_for('product_detail', product_id=product_id))

@app.route('/cart')
def view_cart():
    if 'user_id' not in session:
        flash('Please login to view cart')
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cart_items = []
    total = 0
    
    if conn:
        try:
            cur = conn.cursor()
            cur.execute('''
                SELECT c.id, p.name, p.price, c.quantity, p.image_url, p.id as product_id
                FROM cart c
                JOIN products p ON c.product_id = p.id
                WHERE c.user_id = %s
            ''', (session['user_id'],))
            cart_items = cur.fetchall()
            
            total = sum(item[2] * item[3] for item in cart_items)
            
            cur.close()
            conn.close()
        except Exception as e:
            print(f"Error: {e}")
    
    return render_template('cart.html', cart_items=cart_items, total=total)

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000, debug=True)
