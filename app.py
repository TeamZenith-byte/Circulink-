from flask import Flask, render_template, request, jsonify, session, redirect, url_for, send_from_directory
import sqlite3
import os
import time
import base64
import json
import requests
from werkzeug.utils import secure_filename
import google.generativeai as genai

# ================================================================
# APP SETUP
# ================================================================
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
app.secret_key = 'circulink_secret_2025'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

# ================================================================
# GEMINI AI SETUP — Apna naya key yahan paste karo
# ================================================================
GEMINI_API_KEY = "AIzaSyD8VvTMlgabZIsd3-Ne9_8pbJTmjgpXs68"
genai.configure(api_key=GEMINI_API_KEY)

# ================================================================
# ADMIN CREDENTIALS
# ================================================================
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "circulink2025"

# ================================================================
# DATABASE
# ================================================================
def get_db():
    db = sqlite3.connect('circulink.db')
    db.row_factory = sqlite3.Row
    return db


def init_db():
    print("DATABASE INITIALIZATION STARTED")
    db = get_db()
    db.executescript('''
        CREATE TABLE IF NOT EXISTS listings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            category TEXT NOT NULL,
            subcategory TEXT,
            quality TEXT NOT NULL,
            quality_score INTEGER DEFAULT 70,
            price REAL NOT NULL,
            quantity REAL DEFAULT 0,
            seller_name TEXT,
            seller_phone TEXT,
            seller_type TEXT DEFAULT 'Individual',
            location TEXT,
            image_path TEXT,
            co2_saved REAL DEFAULT 2.5,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            listing_id INTEGER,
            item_title TEXT,
            buyer_name TEXT NOT NULL,
            buyer_phone TEXT NOT NULL,
            buyer_email TEXT NOT NULL,
            quantity_wanted REAL,
            offer_price REAL,
            message TEXT,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            phone TEXT,
            subject TEXT,
            message TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS donations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_name TEXT NOT NULL,
            category TEXT NOT NULL,
            condition TEXT,
            quantity TEXT,
            donor_name TEXT NOT NULL,
            donor_phone TEXT NOT NULL,
            donor_email TEXT,
            pickup_address TEXT,
            ngo_name TEXT,
            message TEXT,
            image_path TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    ''')
    db.commit()
    insert_sample_listings(db)
    db.close()


# ================================================================
# 25 SAMPLE LISTINGS
# ================================================================
def insert_sample_listings(db):
    count = db.execute('SELECT COUNT(*) FROM listings').fetchone()[0]
    if count > 0:
        return

    sample_listings = [
        # --- PLASTIC (5) ---
        ('Clean PET Plastic Bottles - 50kg Lot',
         'Plastic', 'PET Bottles', 'Excellent', 88, 28.0, 50,
         'Ramesh Kumar', '9876543210', 'Individual', 'Mumbai, Maharashtra', 3.2),

        ('HDPE Plastic Drums - Industrial Grade',
         'Plastic', 'HDPE Drums', 'Good', 72, 22.0, 100,
         'Suresh Traders', '9812345678', 'Small Business', 'Delhi, NCR', 2.8),

        ('Mixed Plastic Scrap - Factory Waste',
         'Plastic', 'Mixed Plastic', 'Fair', 55, 8.0, 200,
         'Green Collect Pvt Ltd', '9934567890', 'Industry', 'Pune, Maharashtra', 2.1),

        ('PVC Pipes Scrap Bundle',
         'Plastic', 'PVC Pipes', 'Good', 68, 15.0, 75,
         'Mohan Singh', '9712345678', 'Small Business', 'Jaipur, Rajasthan', 2.5),

        ('PP Woven Bags - Used Lot',
         'Plastic', 'Polypropylene Bags', 'Good', 70, 12.0, 30,
         'Priya Devi', '9823456789', 'Individual', 'Kolkata, WB', 2.3),

        # --- METAL (5) ---
        ('Heavy Grade Iron Scrap - 500kg',
         'Metal', 'Iron Scrap', 'Excellent', 90, 32.0, 500,
         'Steel Mart Industries', '9654321098', 'Industry', 'Bhilai, CG', 5.8),

        ('Copper Wire Scrap - Pure Grade',
         'Metal', 'Copper Wire', 'Excellent', 95, 450.0, 20,
         'Vinod Metals', '9765432109', 'Small Business', 'Ludhiana, Punjab', 6.2),

        ('Crushed Aluminum Cans',
         'Metal', 'Aluminum Cans', 'Good', 78, 85.0, 40,
         'RecyclePro Services', '9876541234', 'Small Business', 'Ahmedabad, Gujarat', 4.5),

        ('MS Steel Rods and Bars',
         'Metal', 'Steel Bars', 'Good', 75, 28.0, 300,
         'Ram Lal Scrap', '9812398765', 'Industry', 'Raipur, CG', 5.1),

        ('Brass Fittings Scrap',
         'Metal', 'Brass', 'Excellent', 92, 320.0, 15,
         'Sharma Metal Works', '9723456789', 'Small Business', 'Moradabad, UP', 5.5),

        # --- PAPER (3) ---
        ('Cardboard Boxes - Bulk Lot 150kg',
         'Paper', 'Cardboard', 'Excellent', 85, 12.0, 150,
         'Patel Packaging House', '9923456789', 'Small Business', 'Surat, Gujarat', 1.8),

        ('Old Newspapers Bundle - 80kg',
         'Paper', 'Newspaper', 'Good', 70, 6.0, 80,
         'Ramesh Yadav', '9734567890', 'Individual', 'Lucknow, UP', 1.2),

        ('Office Paper Waste - White Sheets',
         'Paper', 'White Paper', 'Good', 74, 10.0, 60,
         'DataTech Office Solutions', '9645678901', 'Small Business', 'Bangalore, KA', 1.5),

        # --- E-WASTE (3) ---
        ('Old Laptops and Desktop Computers',
         'E-Waste', 'Computers', 'Fair', 58, 120.0, 15,
         'TechRecycle Hub', '9556789012', 'Small Business', 'Hyderabad, TS', 8.5),

        ('Mobile Phones - Old Bulk Lot',
         'E-Waste', 'Mobile Phones', 'Good', 72, 250.0, 8,
         'PhoneScrap Co', '9467890123', 'Small Business', 'Chennai, TN', 6.8),

        ('PCB Circuit Boards - Electronic Scrap',
         'E-Waste', 'Circuit Boards', 'Excellent', 88, 550.0, 5,
         'E-Scrap Hub Delhi', '9378901234', 'Industry', 'Noida, UP', 9.2),

        # --- GLASS (2) ---
        ('Mixed Glass Bottles - 200kg',
         'Glass', 'Glass Bottles', 'Good', 68, 5.0, 200,
         'Shankar Glass Depot', '9289012345', 'Small Business', 'Indore, MP', 1.1),

        ('Broken Window Glass Sheets',
         'Glass', 'Flat Glass', 'Fair', 50, 3.0, 100,
         'City Construction Site', '9190123456', 'Industry', 'Bhopal, MP', 0.8),

        # --- ORGANIC (3) ---
        ('Restaurant Food Waste - Daily',
         'Organic', 'Food Waste', 'Good', 70, 2.0, 500,
         'Hotel Sunshine', '9001234567', 'Restaurant', 'Siwan, Bihar', 1.5),

        ('Farm Agricultural Waste',
         'Organic', 'Agricultural Waste', 'Good', 65, 1.0, 1000,
         'Bihar Farmer Collective', '9912345670', 'Individual', 'Patna, Bihar', 1.2),

        ('Coconut Shell and Husk Waste',
         'Organic', 'Coconut Shell', 'Excellent', 82, 4.0, 200,
         'South Indian Foods Ltd', '9823456701', 'Restaurant', 'Coimbatore, TN', 1.8),

        # --- TEXTILE (3) ---
        ('Old Cotton Clothes - Bulk 50kg',
         'Textile', 'Cotton Fabric', 'Good', 66, 12.0, 50,
         'Kapda Collection Center', '9734567012', 'Individual', 'Surat, Gujarat', 2.2),

        ('Denim Fabric Scraps - Factory',
         'Textile', 'Denim Scraps', 'Good', 72, 18.0, 30,
         'Fashion Waste Solutions', '9645678023', 'Small Business', 'Tirupur, TN', 2.5),

        # --- RUBBER (2) ---
        ('Used Car and Truck Tyres',
         'Rubber', 'Vehicle Tyres', 'Fair', 52, 15.0, 50,
         'AutoScrap Yard Delhi', '9467890045', 'Small Business', 'Delhi, NCR', 3.5),

        ('Industrial Rubber Hose and Pipes',
         'Rubber', 'Rubber Pipes', 'Good', 68, 22.0, 40,
         'Pune Industrial Waste', '9378901056', 'Industry', 'Pune, Maharashtra', 3.1),
         # --- EXTRA PLASTIC (5) ---
        ('Plastic Water Cans - 20L',
         'Plastic', 'HDPE Cans', 'Good', 74, 18.0, 60,
         'Sharma General Store', '9811223344', 'Small Business', 'Siwan, Bihar', 2.4),

        ('Plastic Chair Scrap Lot',
         'Plastic', 'PP Plastic', 'Fair', 52, 10.0, 80,
         'Furniture Depot', '9722334455', 'Small Business', 'Varanasi, UP', 1.9),

        ('Plastic Bottle Caps Bulk',
         'Plastic', 'HDPE Caps', 'Good', 66, 14.0, 25,
         'Anita Devi', '9633445566', 'Individual', 'Gorakhpur, UP', 2.1),

        ('PET Mineral Water Bottles',
         'Plastic', 'PET Bottles', 'Excellent', 86, 25.0, 45,
         'Hotel Grand', '9544556677', 'Restaurant', 'Patna, Bihar', 3.0),

        ('Plastic Packaging Film',
         'Plastic', 'LDPE Film', 'Good', 70, 16.0, 35,
         'Packaging Works', '9455667788', 'Industry', 'Kanpur, UP', 2.2),

        # --- EXTRA METAL (5) ---
        ('Stainless Steel Utensils Scrap',
         'Metal', 'Stainless Steel', 'Good', 76, 45.0, 30,
         'Hotel Kitchen Waste', '9366778899', 'Restaurant', 'Mumbai, Maharashtra', 4.8),

        ('Lead Battery Plates',
         'Metal', 'Lead', 'Fair', 60, 85.0, 20,
         'Auto Repair Shop', '9277889900', 'Small Business', 'Delhi, NCR', 5.2),

        ('Zinc Die Cast Scrap',
         'Metal', 'Zinc', 'Good', 74, 110.0, 15,
         'Die Cast Factory', '9188990011', 'Industry', 'Rajkot, Gujarat', 4.9),

        ('Tin Cans and Containers',
         'Metal', 'Tin', 'Good', 68, 38.0, 50,
         'Food Processing Unit', '9099001122', 'Industry', 'Nashik, Maharashtra', 4.2),

        ('Motor Winding Copper',
         'Metal', 'Copper', 'Excellent', 93, 420.0, 10,
         'Electric Motor Works', '9900112233', 'Small Business', 'Pune, Maharashtra', 6.0),

        # --- EXTRA PAPER (3) ---
        ('Kraft Paper Bags Used',
         'Paper', 'Kraft Paper', 'Good', 72, 9.0, 90,
         'Cement Dealer', '9811334455', 'Small Business', 'Bikaner, Rajasthan', 1.4),

        ('Tetra Pack Cartons',
         'Paper', 'Tetra Pack', 'Fair', 58, 7.0, 40,
         'Dairy Cooperative', '9722445566', 'Industry', 'Anand, Gujarat', 1.1),

        ('Book and Magazine Lot',
         'Paper', 'Books', 'Good', 65, 8.0, 55,
         'School Waste', '9633556677', 'Individual', 'Agra, UP', 1.3),

        # --- EXTRA E-WASTE (3) ---
        ('Old CRT Television Sets',
         'E-Waste', 'Television', 'Poor', 38, 45.0, 12,
         'Electronics Shop', '9544667788', 'Small Business', 'Kolkata, WB', 7.5),

        ('Printer and Cartridge Waste',
         'E-Waste', 'Printers', 'Fair', 55, 80.0, 8,
         'Office Clearance', '9455778899', 'Small Business', 'Hyderabad, TS', 6.2),

        ('UPS and Battery Backup Units',
         'E-Waste', 'UPS Systems', 'Good', 70, 150.0, 6,
         'IT Company Waste', '9366889900', 'Industry', 'Bangalore, KA', 7.8),

        # --- EXTRA GLASS (2) ---
        ('Laboratory Glass Equipment',
         'Glass', 'Lab Glass', 'Fair', 55, 8.0, 30,
         'College Lab', '9277990011', 'Individual', 'Allahabad, UP', 1.0),

        ('Beer and Liquor Bottles',
         'Glass', 'Amber Bottles', 'Good', 72, 6.0, 150,
         'Bar and Restaurant', '9188001122', 'Restaurant', 'Goa', 1.2),

        # --- EXTRA ORGANIC (2) ---
        ('Sugarcane Bagasse Waste',
         'Organic', 'Bagasse', 'Good', 75, 3.0, 800,
         'Sugar Mill Bihar', '9099112233', 'Industry', 'Siwan, Bihar', 1.6),

        ('Flower and Pooja Waste',
         'Organic', 'Flower Waste', 'Good', 68, 2.0, 100,
         'Temple Trust', '9900223344', 'Individual', 'Mathura, UP', 1.3),
    ]

    for listing in sample_listings:
        db.execute('''
            INSERT INTO listings
            (title, category, subcategory, quality, quality_score, price, quantity,
             seller_name, seller_phone, seller_type, location, co2_saved)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', listing)

    db.commit()


# ================================================================
# PAGE ROUTES
# ================================================================
@app.route('/')
def index():
    db = get_db()
    recent_listings = db.execute(
        'SELECT * FROM listings ORDER BY created_at DESC LIMIT 8'
    ).fetchall()
    stats = {
        'total_listings': db.execute('SELECT COUNT(*) FROM listings').fetchone()[0],
        'total_orders': db.execute('SELECT COUNT(*) FROM orders').fetchone()[0],
    }
    db.close()
    return render_template('index.html', recent_listings=recent_listings, stats=stats)


@app.route('/marketplace')
def marketplace():
    db = get_db()
    listings = db.execute(
        'SELECT * FROM listings ORDER BY created_at DESC'
    ).fetchall()
    db.close()
    return render_template('marketplace.html', listings=listings)


@app.route('/donation')
def donation():
    return render_template('donation.html')


@app.route('/contact')
def contact():
    return render_template('contact.html')


# ================================================================
# ADMIN ROUTES
# ================================================================
@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if request.method == 'POST':
        username = request.form.get('username', '')
        password = request.form.get('password', '')
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['admin'] = True
            return redirect(url_for('admin_dashboard'))
        return render_template('admin_login.html', error='Invalid username or password')
    if session.get('admin'):
        return redirect(url_for('admin_dashboard'))
    return render_template('admin_login.html', error=None)


@app.route('/admin/dashboard')
def admin_dashboard():
    if not session.get('admin'):
        return redirect(url_for('admin'))
    db = get_db()
    orders = db.execute('SELECT * FROM orders ORDER BY created_at DESC').fetchall()
    messages = db.execute('SELECT * FROM messages ORDER BY created_at DESC').fetchall()
    donations = db.execute('SELECT * FROM donations ORDER BY created_at DESC').fetchall()
    listings = db.execute('SELECT * FROM listings ORDER BY created_at DESC').fetchall()
    stats = {
        'total_listings': db.execute('SELECT COUNT(*) FROM listings').fetchone()[0],
        'total_orders': db.execute('SELECT COUNT(*) FROM orders').fetchone()[0],
        'pending_orders': db.execute(
            "SELECT COUNT(*) FROM orders WHERE status='pending'"
        ).fetchone()[0],
        'total_messages': db.execute('SELECT COUNT(*) FROM messages').fetchone()[0],
        'total_donations': db.execute('SELECT COUNT(*) FROM donations').fetchone()[0],
    }
    db.close()
    return render_template(
        'admin_dashboard.html',
        orders=orders,
        messages=messages,
        donations=donations,
        listings=listings,
        stats=stats
    )


@app.route('/admin/logout')
def admin_logout():
    session.pop('admin', None)
    return redirect(url_for('admin'))


# ================================================================
# SERVE UPLOADED IMAGES
# ================================================================
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


# ================================================================
# API — AI WASTE ANALYSIS
# ================================================================
@app.route('/api/analyze', methods=['POST'])
def analyze_waste():
    try:
        if 'image' not in request.files:
            return jsonify({'success': False, 'error': 'No image uploaded'})

        file = request.files['image']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'})

        img_bytes = file.read()
        img_b64 = base64.b64encode(img_bytes).decode('utf-8')

        ext = file.filename.rsplit('.', 1)[-1].lower()
        if ext in ['jpg', 'jpeg']:
            mime = 'image/jpeg'
        elif ext == 'png':
            mime = 'image/png'
        else:
            mime = 'image/webp'

        prompt = """You are a waste classification expert for an Indian recycling marketplace.
Analyze this waste image carefully and respond ONLY with valid JSON, no extra text, no markdown.

{
  "success": true,
  "category": "Plastic",
  "subcategory": "PET Bottles",
  "quality_score": 75,
  "quality": "Good",
  "confidence": 88,
  "estimated_price": 18,
  "co2_saved": 2.5,
  "recommendations": ["Clean before selling for better price", "Sort by color if possible"],
  "description": "Clear PET plastic bottles in good condition"
}

Rules:
- category must be one of: Plastic, Paper, Metal, E-Waste, Glass, Organic, Textile, Rubber
- quality must be one of: Excellent, Good, Fair, Poor
- quality_score between 0 and 100
- estimated_price in INR per kg realistic Indian market price
- confidence between 60 and 99
- co2_saved between 0.5 and 10.0
- Give exactly 2 short recommendations in simple English"""

        model = genai.GenerativeModel('gemini-2.0-flash')
        response = model.generate_content([
            {'mime_type': mime, 'data': img_b64},
            prompt
        ])

        raw = response.text.strip()
        raw = raw.replace('```json', '').replace('```', '').strip()

        if raw.startswith('{'):
            data = json.loads(raw)
        else:
            start = raw.find('{')
            end = raw.rfind('}') + 1
            data = json.loads(raw[start:end])

        data['success'] = True
        return jsonify(data)

    except json.JSONDecodeError:
        return jsonify({
            'success': True,
            'category': 'Plastic',
            'subcategory': 'Mixed Plastic',
            'quality_score': 60,
            'quality': 'Good',
            'confidence': 70,
            'estimated_price': 15,
            'co2_saved': 2.0,
            'recommendations': ['Try a clearer photo', 'Good lighting helps AI accuracy'],
            'description': 'Could not analyze clearly - please try again'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


# ================================================================
# API — LIST WASTE (also supports /api/list-waste)
# ================================================================
@app.route('/api/list', methods=['POST'])
@app.route('/api/list-waste', methods=['POST'])
def api_list_waste():
    try:
        data = request.form
        image_path = None

        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename:
                filename = str(int(time.time())) + '_' + secure_filename(file.filename)
                os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                image_path = filename

        db = get_db()
        db.execute('''
            INSERT INTO listings
            (title, category, subcategory, quality, quality_score, price, quantity,
             seller_name, seller_phone, seller_type, location, image_path, co2_saved)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data.get('title'),
            data.get('category'),
            data.get('subcategory', ''),
            data.get('quality', 'Good'),
            int(data.get('quality_score', 70)),
            float(data.get('price', 0)),
            float(data.get('quantity', 0)),
            data.get('seller_name'),
            data.get('seller_phone'),
            data.get('seller_type', 'Individual'),
            data.get('location'),
            image_path,
            float(data.get('co2_saved', 2.5))
        ))
        db.commit()
        db.close()
        return jsonify({'success': True, 'message': 'Listing created successfully'})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


# ================================================================
# API — BUY / MAKE OFFER
# ================================================================
@app.route('/api/buy', methods=['POST'])
def api_buy():
    try:
        data = request.json
        db = get_db()

        listing = db.execute(
            'SELECT title FROM listings WHERE id=?', (data.get('listing_id'),)
        ).fetchone()
        item_title = listing['title'] if listing else 'Unknown Item'

        db.execute('''
            INSERT INTO orders
            (listing_id, item_title, buyer_name, buyer_phone, buyer_email,
             quantity_wanted, offer_price, message)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data.get('listing_id'),
            item_title,
            data.get('buyer_name'),
            data.get('buyer_phone'),
            data.get('buyer_email'),
            data.get('quantity_wanted'),
            data.get('offer_price'),
            data.get('message')
        ))
        db.commit()
        db.close()
        return jsonify({'success': True, 'message': 'Order placed successfully'})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


# ================================================================
# API — DONATE
# ================================================================
@app.route('/api/donate', methods=['POST'])
def api_donate():
    try:
        data = request.form
        image_path = None

        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename:
                filename = str(int(time.time())) + '_' + secure_filename(file.filename)
                os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                image_path = filename

        db = get_db()
        db.execute('''
            INSERT INTO donations
            (item_name, category, condition, quantity, donor_name, donor_phone,
             donor_email, pickup_address, ngo_name, message, image_path)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data.get('item_name'),
            data.get('category'),
            data.get('condition'),
            data.get('quantity'),
            data.get('donor_name'),
            data.get('donor_phone'),
            data.get('donor_email'),
            data.get('pickup_address'),
            data.get('ngo_name'),
            data.get('message'),
            image_path
        ))
        db.commit()
        db.close()
        return jsonify({'success': True, 'message': 'Donation submitted successfully'})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


# ================================================================
# API — CONTACT MESSAGE
# ================================================================
@app.route('/api/contact', methods=['POST'])
def api_contact():
    try:
        data = request.json
        db = get_db()
        db.execute('''
            INSERT INTO messages (name, email, phone, subject, message)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            data.get('name'),
            data.get('email'),
            data.get('phone'),
            data.get('subject'),
            data.get('message')
        ))
        db.commit()
        db.close()
        return jsonify({'success': True, 'message': 'Message sent successfully'})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


# ================================================================
# API — ADMIN: UPDATE ORDER STATUS
# ================================================================
@app.route('/api/order/<int:order_id>/status', methods=['POST'])
def update_order_status(order_id):
    if not session.get('admin'):
        return jsonify({'success': False, 'error': 'Unauthorized'})
    try:
        data = request.json
        db = get_db()
        db.execute(
            'UPDATE orders SET status=? WHERE id=?',
            (data.get('status'), order_id)
        )
        db.commit()
        db.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


# ================================================================
# API — ADMIN: DELETE LISTING
# ================================================================
@app.route('/api/listing/<int:listing_id>/delete', methods=['POST'])
def delete_listing(listing_id):
    if not session.get('admin'):
        return jsonify({'success': False, 'error': 'Unauthorized'})
    try:
        db = get_db()
        db.execute('DELETE FROM listings WHERE id=?', (listing_id,))
        db.commit()
        db.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


# ================================================================
# RUN APP
# ================================================================
# ================================================================
# DATABASE INIT FOR RENDER + LOCAL
# ================================================================
os.makedirs('uploads', exist_ok=True)

try:
    init_db()
    print("DATABASE INITIALIZED SUCCESSFULLY")
except Exception as e:
    print("DATABASE INIT ERROR:", str(e))


# ================================================================
# RUN APP
# ================================================================
if __name__ == '__main__':
    app.run(debug=True)