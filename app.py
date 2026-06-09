from flask import Flask, render_template, request, jsonify, session, redirect, url_for, send_from_directory
import sqlite3
import os
import time
import base64
import json
from werkzeug.utils import secure_filename
import requests

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
app.secret_key = 'circulink_secret_2025'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

# GROQ API KEY — console.groq.com se free key lo
import os

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "circulink2025"

def get_db():
    db = sqlite3.connect('circulink.db')
    db.row_factory = sqlite3.Row
    return db

def init_db():
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
            city TEXT,
            image_path TEXT,
            co2_saved REAL DEFAULT 2.5,
            rating REAL DEFAULT 0,
            rating_count INTEGER DEFAULT 0,
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
        CREATE TABLE IF NOT EXISTS ratings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            listing_id INTEGER,
            rating INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    ''')
    db.commit()
    insert_sample_listings(db)
    db.close()

def insert_sample_listings(db):
    count = db.execute('SELECT COUNT(*) FROM listings').fetchone()[0]
    if count > 0:
        return

    sample_listings = [
        # PLASTIC (20)
        ('Plastic Wrappers — Ram Prasad Kirana', 'Plastic', 'Plastic Wrappers', 'Good', 70, 12.0, 7, 'Ram Prasad Gupta', '9934100001', 'Small Business', 'Siwan Bazar, Siwan', 'Siwan', 2.1),
        ('Mixed Plastic Bags — Shiv Shakti Store', 'Plastic', 'Plastic Bags', 'Fair', 55, 8.0, 15, 'Shiv Shankar Yadav', '9934100002', 'Small Business', 'Station Road, Siwan', 'Siwan', 1.8),
        ('Plastic Packaging — Garment Shop', 'Plastic', 'Packaging Plastic', 'Good', 66, 12.0, 5, 'Kapil Kumar Singh', '9934100003', 'Small Business', 'Cloth Market, Siwan', 'Siwan', 2.0),
        ('Plastic Cups Bulk — Chai Stall', 'Plastic', 'Disposable Cups', 'Fair', 52, 6.0, 8, 'Raju Chai Wale', '9934100004', 'Individual', 'Bus Stand, Siwan', 'Siwan', 1.5),
        ('PET Bottles — Hospital Collected', 'Plastic', 'PET Bottles', 'Good', 72, 10.0, 12, 'Siwan City Hospital', '9934100005', 'Hospital', 'Civil Lines, Siwan', 'Siwan', 2.3),
        ('Plastic Glasses — Juice Shop', 'Plastic', 'Disposable Glasses', 'Fair', 50, 6.0, 4, 'Fresh Juice Corner', '9934100006', 'Small Business', 'Main Market, Siwan', 'Siwan', 1.4),
        ('HDPE Plastic Cans — Kirana', 'Plastic', 'HDPE Cans', 'Good', 68, 14.0, 20, 'Annapurna General Store', '9934100007', 'Small Business', 'Darauli Road, Gopalganj', 'Gopalganj', 2.2),
        ('Plastic Sweet Box — Mithai Shop', 'Plastic', 'Food Packaging', 'Fair', 54, 9.0, 10, 'Ganga Mithai Bhandar', '9934100008', 'Small Business', 'Sadar Bazar, Siwan', 'Siwan', 1.6),
        ('Plastic Water Pouches — Cold Drink', 'Plastic', 'Plastic Pouches', 'Fair', 52, 7.0, 6, 'Sheetla Cold Drinks', '9934100040', 'Small Business', 'Main Road, Mairwa', 'Siwan', 1.4),
        ('Plastic Fertilizer Bags — Kisan', 'Plastic', 'HDPE Bags', 'Good', 66, 12.0, 25, 'Kiran Fertilizer Store', '9934100046', 'Small Business', 'Krishi Market, Gopalganj', 'Gopalganj', 2.0),
        ('PVC Pipes — Plumber Offcuts', 'Plastic', 'PVC Pipes', 'Good', 70, 14.0, 8, 'Sunil Plumbing Works', '9934100043', 'Small Business', 'Plumber Colony, Siwan', 'Siwan', 2.2),
        ('PP Plastic Drum — Factory', 'Plastic', 'PP Drums', 'Good', 74, 18.0, 30, 'Bihar Paint Factory', '9934200001', 'Industry', 'Industrial Area, Chhapra', 'Chhapra', 2.5),
        ('Plastic Oil Cans — Motor Shop', 'Plastic', 'HDPE Oil Cans', 'Fair', 58, 10.0, 15, 'Shyam Motor Parts', '9934200002', 'Small Business', 'Motor Market, Gopalganj', 'Gopalganj', 1.8),
        ('Toy Shop Plastic Waste', 'Plastic', 'Mixed Plastic', 'Fair', 48, 7.0, 5, 'Bal Mandir Toy Store', '9934200003', 'Small Business', 'Market Area, Siwan', 'Siwan', 1.5),
        ('Pan Shop Plastic Pouches', 'Plastic', 'LDPE Pouches', 'Poor', 38, 5.0, 3, 'Ramesh Pan Bhandar', '9934200004', 'Individual', 'Chowk, Siwan', 'Siwan', 1.2),
        ('Plastic Crates — Cold Storage', 'Plastic', 'HDPE Crates', 'Good', 76, 18.0, 40, 'Bihar Cold Storage', '9934200005', 'Industry', 'Storage Area, Muzaffarpur', 'Muzaffarpur', 2.6),
        ('Soap Factory Plastic — Wrapper', 'Plastic', 'LDPE Film', 'Good', 64, 11.0, 20, 'Saraswati Soap Works', '9934200006', 'Industry', 'Factory Area, Motihari', 'Motihari', 1.9),
        ('Beauty Parlor Plastic Waste', 'Plastic', 'Mixed Plastic', 'Fair', 50, 7.0, 3, 'Priya Beauty Parlor', '9934200007', 'Small Business', 'Ladies Market, Siwan', 'Siwan', 1.4),
        ('Medical Store Plastic Bottles', 'Plastic', 'Medicine Bottles', 'Good', 68, 9.0, 8, 'Dawa Ghar Medical', '9934200008', 'Small Business', 'Medical Lane, Siwan', 'Siwan', 1.7),
        ('Vegetable Oil Shop Containers', 'Plastic', 'HDPE Containers', 'Good', 70, 13.0, 12, 'Shree Oil Center', '9934200009', 'Small Business', 'Oil Market, Gopalganj', 'Gopalganj', 2.1),

        # PAPER (12)
        ('Cardboard Boxes — Kirana Daily', 'Paper', 'Cardboard', 'Good', 74, 9.0, 20, 'Laxmi General Store', '9934100009', 'Small Business', 'Station Road, Siwan', 'Siwan', 1.5),
        ('Cardboard — Hospital Waste', 'Paper', 'Cardboard', 'Good', 70, 7.0, 10, 'City Nursing Home', '9934100010', 'Hospital', 'Doctor Colony, Siwan', 'Siwan', 1.2),
        ('Old Books — School Waste', 'Paper', 'Books/Paper', 'Good', 65, 7.0, 30, 'Govt. High School', '9934100011', 'Individual', 'School Road, Siwan', 'Siwan', 1.1),
        ('Office Paper — Bank Waste', 'Paper', 'White Paper', 'Good', 72, 9.0, 15, 'SBI Branch Siwan', '9934100012', 'Small Business', 'Main Road, Siwan', 'Siwan', 1.4),
        ('Kraft Paper Bags — Atta Chakki', 'Paper', 'Kraft Paper', 'Good', 68, 8.0, 40, 'Shyam Flour Mill', '9934100013', 'Small Business', 'Mairwa Road, Gopalganj', 'Gopalganj', 1.3),
        ('Printing Waste — Press', 'Paper', 'Printing Paper', 'Good', 70, 8.0, 35, 'Janta Printing Press', '9934100015', 'Small Business', 'Press Colony, Chhapra', 'Chhapra', 1.3),
        ('Cement Paper Bags — Dealer', 'Paper', 'Kraft Bags', 'Good', 66, 7.0, 50, 'Shri Cement Depot', '9934200010', 'Small Business', 'Cement Market, Gopalganj', 'Gopalganj', 1.2),
        ('Stationery Shop Paper Waste', 'Paper', 'Mixed Paper', 'Good', 64, 7.0, 8, 'Vidya Stationery', '9934200011', 'Small Business', 'School Road, Siwan', 'Siwan', 1.1),
        ('Newspaper Bundle — Old Lot', 'Paper', 'Newspaper', 'Good', 62, 6.0, 25, 'Ramesh Sabji Wale', '9934100042', 'Individual', 'Vegetable Market, Siwan', 'Siwan', 0.9),
        ('Book Shop Damaged Books', 'Paper', 'Books', 'Fair', 55, 6.0, 15, 'Gyan Pustak Bhandar', '9934200012', 'Small Business', 'Book Market, Chhapra', 'Chhapra', 1.0),
        ('Cardboard — Medical Store', 'Paper', 'Cardboard Boxes', 'Good', 72, 8.0, 8, 'Dawa Ghar Medical', '9934100045', 'Small Business', 'Medical Market, Siwan', 'Siwan', 1.2),
        ('Ayurvedic Shop Paper Boxes', 'Paper', 'Cardboard', 'Good', 68, 8.0, 10, 'Patanjali Kendra Siwan', '9934200013', 'Small Business', 'Health Market, Siwan', 'Siwan', 1.2),

        # METAL (13)
        ('Copper Wire — Electronic Shop', 'Metal', 'Copper Wire', 'Excellent', 92, 580.0, 2, 'Sharma Electronics', '9934100016', 'Small Business', 'Electronics Market, Siwan', 'Siwan', 6.0),
        ('Iron Scrap — Auto Repair', 'Metal', 'Iron Scrap', 'Good', 74, 28.0, 15, 'Vijay Auto Works', '9934100017', 'Small Business', 'Bypass Road, Siwan', 'Siwan', 4.5),
        ('Metal Paint Cans — Hardware', 'Metal', 'Tin Cans', 'Good', 66, 25.0, 8, 'Ramesh Hardware', '9934100018', 'Small Business', 'Hardware Market, Siwan', 'Siwan', 3.8),
        ('Iron Rods — Welding Shop', 'Metal', 'Steel Scrap', 'Good', 75, 29.0, 20, 'Ramu Welding Works', '9934100019', 'Small Business', 'Industrial Area, Gopalganj', 'Gopalganj', 4.8),
        ('Aluminium Foil — Sweet Shop', 'Metal', 'Aluminum Foil', 'Good', 68, 90.0, 3, 'Hari Om Sweets', '9934100041', 'Small Business', 'Sweet Market, Siwan', 'Siwan', 4.0),
        ('Iron Gate Scrap — Fabricator', 'Metal', 'MS Steel', 'Good', 76, 30.0, 35, 'Rahul Steel Fabrication', '9934100050', 'Small Business', 'Fabrication Area, Muzaffarpur', 'Muzaffarpur', 5.0),
        ('Iron Filing — Lathe Machine', 'Metal', 'Iron Filings', 'Good', 72, 24.0, 12, 'Singh Lathe Works', '9934100044', 'Small Business', 'Workshop Area, Chhapra', 'Chhapra', 4.2),
        ('Motorcycle Parts Scrap — Garage', 'Metal', 'Mixed Metal', 'Fair', 62, 26.0, 18, 'Bajaj Service Center', '9934200014', 'Small Business', 'Garage Road, Siwan', 'Siwan', 4.0),
        ('Brass Fittings — Plumber', 'Metal', 'Brass', 'Excellent', 88, 280.0, 3, 'Anil Plumbing Works', '9934200015', 'Small Business', 'Hardware Lane, Gopalganj', 'Gopalganj', 5.5),
        ('Tin Containers — Ghee Shop', 'Metal', 'Tin Cans', 'Good', 70, 28.0, 6, 'Amul Dairy Outlet', '9934200016', 'Small Business', 'Dairy Market, Siwan', 'Siwan', 3.8),
        ('Aluminum Utensils — Hotel', 'Metal', 'Aluminum', 'Good', 74, 85.0, 8, 'Hotel Sona Palace', '9934200017', 'Restaurant', 'Hotel Road, Chhapra', 'Chhapra', 4.5),
        ('Steel Drum — Paint Factory', 'Metal', 'Steel Drums', 'Good', 72, 32.0, 10, 'Shri Paint Works', '9934200018', 'Industry', 'Factory Area, Motihari', 'Motihari', 4.8),
        ('Lead Battery Plates — Garage', 'Metal', 'Lead', 'Fair', 60, 80.0, 5, 'Speed Auto Garage', '9934200019', 'Small Business', 'Transport Nagar, Siwan', 'Siwan', 5.0),

        # E-WASTE (10)
        ('Chargers and Batteries — Repair', 'E-Waste', 'Chargers/Battery', 'Good', 70, 200.0, 2, 'Tech Fix Center', '9934100021', 'Small Business', 'Mobile Market, Siwan', 'Siwan', 7.0),
        ('Circuit Boards PCB', 'E-Waste', 'Circuit Boards', 'Good', 74, 320.0, 3, 'Mobile Care Center', '9934100022', 'Small Business', 'Main Bazar, Siwan', 'Siwan', 8.0),
        ('Wires and PCB — Repair Shop', 'E-Waste', 'Wires and PCB', 'Excellent', 88, 580.0, 2, 'Kumar Electronics', '9934100023', 'Small Business', 'Electronics Lane, Siwan', 'Siwan', 9.0),
        ('Old CRT TV Sets', 'E-Waste', 'Television', 'Poor', 40, 60.0, 5, 'Sonu TV Repair', '9934100024', 'Small Business', 'Station Road, Chhapra', 'Chhapra', 6.5),
        ('Lead Acid Batteries', 'E-Waste', 'Lead Battery', 'Fair', 58, 80.0, 8, 'Shiva Battery House', '9934100025', 'Small Business', 'Bus Stand, Siwan', 'Siwan', 7.5),
        ('Old Mobile Phones', 'E-Waste', 'Mobile Phones', 'Good', 72, 220.0, 5, 'Aman Mobile World', '9934100047', 'Small Business', 'Mobile Bazar, Siwan', 'Siwan', 6.5),
        ('Computer Training Center E-Waste', 'E-Waste', 'Computers', 'Fair', 55, 100.0, 8, 'Digital India Center', '9934200020', 'Small Business', 'Tech Area, Gopalganj', 'Gopalganj', 7.0),
        ('AC and Fridge Parts — Repair', 'E-Waste', 'AC/Refrigerator', 'Fair', 58, 90.0, 6, 'Cool Tech Repair', '9934200021', 'Small Business', 'Electronics Market, Muzaffarpur', 'Muzaffarpur', 7.5),
        ('Old Printers — Office', 'E-Waste', 'Printers', 'Poor', 38, 70.0, 4, 'City Office Solutions', '9934200022', 'Small Business', 'Office Area, Chhapra', 'Chhapra', 6.0),
        ('Electric Motor Copper Winding', 'E-Waste', 'Motor Winding', 'Excellent', 90, 420.0, 3, 'Bharat Motor Repair', '9934200023', 'Small Business', 'Motor Lane, Siwan', 'Siwan', 8.5),

        # ORGANIC (10)
        ('Daily Food Waste — Dhaba', 'Organic', 'Food Waste', 'Good', 68, 2.0, 25, 'Swad Dhaba Siwan', '9934100026', 'Restaurant', 'Highway Dhaba, Siwan', 'Siwan', 1.4),
        ('Vegetable Waste — Sabzi Mandi', 'Organic', 'Vegetable Waste', 'Good', 65, 1.0, 100, 'Siwan Sabzi Mandi', '9934100027', 'Individual', 'Vegetable Market, Siwan', 'Siwan', 1.2),
        ('Fruit Waste — Juice Shop', 'Organic', 'Fruit Waste', 'Good', 70, 1.5, 10, 'Fresh Fruit Center', '9934100028', 'Small Business', 'Main Market, Gopalganj', 'Gopalganj', 1.3),
        ('Rice Husk — Rice Mill', 'Organic', 'Rice Husk', 'Good', 72, 2.0, 500, 'Bihar Rice Mill', '9934100029', 'Industry', 'Mill Area, Gopalganj', 'Gopalganj', 1.5),
        ('Food Waste — Marriage Hall', 'Organic', 'Food Waste', 'Good', 68, 2.0, 80, 'Shiv Marriage Hall', '9934100048', 'Small Business', 'Marriage Hall Road, Siwan', 'Siwan', 1.4),
        ('Sugarcane Bagasse — Mill', 'Organic', 'Bagasse', 'Good', 75, 3.0, 800, 'Gopalganj Sugar Mill', '9934100030', 'Industry', 'Mill Area, Gopalganj', 'Gopalganj', 1.6),
        ('Fish Market Organic Waste', 'Organic', 'Fish Waste', 'Fair', 55, 1.0, 30, 'Siwan Fish Market', '9934200024', 'Individual', 'Fish Market, Siwan', 'Siwan', 1.2),
        ('Dal Mill Husk — Factory', 'Organic', 'Dal Husk', 'Good', 70, 2.0, 300, 'Shri Dal Mill', '9934200025', 'Industry', 'Mill Road, Motihari', 'Motihari', 1.4),
        ('Flower Shop Waste — Daily', 'Organic', 'Flower Waste', 'Good', 68, 1.5, 15, 'Krishna Flower Shop', '9934200026', 'Small Business', 'Temple Road, Siwan', 'Siwan', 1.3),
        ('Bakery Organic Waste — Daily', 'Organic', 'Food Waste', 'Good', 66, 2.0, 20, 'Moti Bakery Siwan', '9934200027', 'Small Business', 'Market Area, Siwan', 'Siwan', 1.4),

        # TEXTILE (8)
        ('Cloth Cutting — Tailor Shop', 'Textile', 'Cloth Cuttings', 'Good', 68, 10.0, 10, 'Lakshmi Tailors', '9934100031', 'Small Business', 'Cloth Market, Siwan', 'Siwan', 2.0),
        ('Garment Fabric — Kapda Shop', 'Textile', 'Cotton Fabric', 'Good', 66, 10.0, 8, 'Fashion Point Garments', '9934100032', 'Small Business', 'Sadar Bazar, Siwan', 'Siwan', 1.9),
        ('Jute Bags — Flour Mill', 'Textile', 'Jute Bags', 'Good', 64, 9.0, 50, 'Ram Lal Atta Chakki', '9934100033', 'Small Business', 'Mill Road, Motihari', 'Motihari', 1.8),
        ('Old Cotton Clothes — Collection', 'Textile', 'Cotton Clothes', 'Fair', 55, 11.0, 20, 'Geeta Devi', '9934100034', 'Individual', 'Residential Area, Siwan', 'Siwan', 2.1),
        ('Cotton Cloth — Ladies Tailor', 'Textile', 'Cotton Cuttings', 'Good', 68, 11.0, 7, 'Meena Ladies Tailor', '9934100049', 'Individual', 'Mahila Market, Siwan', 'Siwan', 1.9),
        ('Tent House Cloth Waste', 'Textile', 'Polyester Fabric', 'Fair', 52, 9.0, 30, 'Shubh Tent House', '9934100035', 'Small Business', 'Event Market, Gopalganj', 'Gopalganj', 1.7),
        ('Shoe Shop Leather Waste', 'Textile', 'Leather Offcuts', 'Fair', 55, 12.0, 5, 'Bata Shoe Agency', '9934200028', 'Small Business', 'Shoe Market, Siwan', 'Siwan', 1.8),
        ('Cotton Ginning Factory Waste', 'Textile', 'Cotton Fiber', 'Good', 70, 14.0, 100, 'Bihar Cotton Gin', '9934200029', 'Industry', 'Factory Road, Motihari', 'Motihari', 2.2),

        # GLASS (5)
        ('Glass Bottles — Hotel Bar', 'Glass', 'Glass Bottles', 'Good', 70, 5.0, 50, 'Hotel Rajmahal', '9934100036', 'Restaurant', 'Hotel Road, Chhapra', 'Chhapra', 1.0),
        ('Medicine Glass Bottles — Medical', 'Glass', 'Medicine Bottles', 'Good', 66, 6.0, 20, 'Jan Aushadhi Kendra', '9934100037', 'Small Business', 'Medical Lane, Siwan', 'Siwan', 0.9),
        ('Pickle Factory Glass Jars', 'Glass', 'Glass Jars', 'Good', 72, 7.0, 40, 'Maa Pickle Factory', '9934200030', 'Industry', 'Food Area, Gopalganj', 'Gopalganj', 1.1),
        ('Ayurvedic Shop Glass Bottles', 'Glass', 'Glass Bottles', 'Good', 68, 6.0, 15, 'Ayur Health Store', '9934200031', 'Small Business', 'Health Market, Chhapra', 'Chhapra', 0.9),
        ('Lab Glass — School Science', 'Glass', 'Lab Glass', 'Fair', 55, 5.0, 8, 'Govt. College Lab', '9934200032', 'Individual', 'College Road, Siwan', 'Siwan', 0.8),

        # RUBBER (5)
        ('Used Cycle Tyres — Shop', 'Rubber', 'Cycle Tyres', 'Fair', 54, 12.0, 15, 'Raj Cycle Store', '9934100038', 'Small Business', 'Cycle Market, Siwan', 'Siwan', 2.5),
        ('Rickshaw Tyres — Garage', 'Rubber', 'Vehicle Tyres', 'Fair', 50, 14.0, 10, 'Santosh Auto Garage', '9934100039', 'Small Business', 'Transport Nagar, Gopalganj', 'Gopalganj', 2.8),
        ('Rubber Hose — Industrial', 'Rubber', 'Rubber Pipes', 'Good', 65, 18.0, 8, 'Industrial Supply Co', '9934200033', 'Industry', 'Industrial Area, Muzaffarpur', 'Muzaffarpur', 3.0),
        ('Sports Shop Rubber Waste', 'Rubber', 'Foam/Rubber', 'Fair', 52, 10.0, 5, 'Victory Sports Center', '9934200034', 'Small Business', 'Sports Market, Siwan', 'Siwan', 2.2),
        ('Shoe Sole Rubber — Cobbler', 'Rubber', 'Rubber Sole', 'Fair', 50, 12.0, 4, 'Mohan Cobbler Shop', '9934200035', 'Individual', 'Market Lane, Siwan', 'Siwan', 2.0),

        # WOOD (7 - new category)
        ('Furniture Shop Wood Waste', 'Paper', 'Wood Scrap', 'Good', 65, 5.0, 50, 'Sharma Furniture Works', '9934200036', 'Small Business', 'Furniture Market, Siwan', 'Siwan', 1.5),
        ('Carpenter Workshop Sawdust', 'Paper', 'Sawdust', 'Good', 62, 3.0, 30, 'Raju Carpenter', '9934200037', 'Individual', 'Workshop Area, Gopalganj', 'Gopalganj', 1.2),
        ('Bamboo Basket Waste', 'Organic', 'Bamboo', 'Good', 68, 4.0, 20, 'Bans Udyog Kendra', '9934200038', 'Small Business', 'Handicraft Area, Muzaffarpur', 'Muzaffarpur', 1.4),
        ('Plywood Factory Offcuts', 'Paper', 'Plywood Offcuts', 'Good', 70, 6.0, 40, 'Bihar Plywood Works', '9934200039', 'Industry', 'Factory Road, Muzaffarpur', 'Muzaffarpur', 1.6),
        ('Incense Stick Factory Waste', 'Organic', 'Wood Powder', 'Good', 65, 4.0, 25, 'Agarbatti Factory', '9934200040', 'Industry', 'Agarbatti Area, Gopalganj', 'Gopalganj', 1.3),
        ('Building Wood Scrap', 'Paper', 'Wood Scrap', 'Fair', 55, 4.0, 60, 'Shri Construction', '9934200041', 'Industry', 'Construction Site, Chhapra', 'Chhapra', 1.2),
        ('Mustard Oil Cake — Factory', 'Organic', 'Oil Cake', 'Excellent', 82, 8.0, 200, 'Tara Oil Mills', '9934200042', 'Industry', 'Oil Mill Area, Motihari', 'Motihari', 2.0),
    ]

    for listing in sample_listings:
        db.execute('''
            INSERT INTO listings
            (title, category, subcategory, quality, quality_score, price, quantity,
             seller_name, seller_phone, seller_type, location, city, co2_saved)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', listing)
    db.commit()


# PAGE ROUTES
@app.route('/')
def index():
    db = get_db()
    recent_listings = db.execute('SELECT * FROM listings ORDER BY created_at DESC LIMIT 8').fetchall()
    stats = {
        'total_listings': db.execute('SELECT COUNT(*) FROM listings').fetchone()[0],
        'total_orders': db.execute('SELECT COUNT(*) FROM orders').fetchone()[0],
    }
    db.close()
    return render_template('index.html', recent_listings=recent_listings, stats=stats)

@app.route('/marketplace')
def marketplace():
    db = get_db()
    listings = db.execute('SELECT * FROM listings ORDER BY created_at DESC').fetchall()
    db.close()
    return render_template('marketplace.html', listings=listings)

@app.route('/donation')
def donation():
    return render_template('donation.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')


# ADMIN ROUTES
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
        'pending_orders': db.execute("SELECT COUNT(*) FROM orders WHERE status='pending'").fetchone()[0],
        'total_messages': db.execute('SELECT COUNT(*) FROM messages').fetchone()[0],
        'total_donations': db.execute('SELECT COUNT(*) FROM donations').fetchone()[0],
    }
    db.close()
    return render_template('admin_dashboard.html', orders=orders, messages=messages, donations=donations, listings=listings, stats=stats)

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin', None)
    return redirect(url_for('admin'))

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


# AI ANALYSIS — GROQ
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
        mime = 'image/jpeg' if ext in ['jpg','jpeg'] else 'image/png' if ext=='png' else 'image/webp'

        prompt_text = (
            "You are an expert waste material analyst and certified kabadi market specialist for India. "
            "Analyze this waste image with 100 percent accuracy for CIRCULINK marketplace Bihar UP. "
            "Study every detail: material type, color, texture, shape, contamination level, moisture, damage, sorting state. "
            "Respond ONLY in valid JSON, absolutely no markdown or extra text. "
            '{"success":true,"category":"Plastic","subcategory":"PET Water Bottles",'
            '"quality_score":82,"quality":"Good","confidence":94,'
            '"estimated_price":20,"price_range":"18-24","co2_saved":2.8,'
            '"should_buy":true,'
            '"buy_recommendation":"Zaroor kharido - saaf PET bottles hai achhe daam milenge",'
            '"condition_notes":"Transparent bottles lightly crushed minimal labels no contamination",'
            '"material_details":"Clear PET plastic food-grade recyclable grade A",'
            '"weight_estimate":"Approximately 8-12 kg visible",'
            '"market_demand":"High",'
            '"recommendations":["Labels hata ke becho 15 percent price badhega","Clear aur colored alag sort karo"],'
            '"description":"Clear transparent PET water bottles good recyclable condition"} '
            "RULES 100 percent follow karo: "
            "1. category ONLY from these exact values: Plastic, Paper, Metal, E-Waste, Glass, Organic, Textile, Rubber. "
            "2. subcategory very specific: for Plastic use PET Bottles/HDPE Drums/PVC Pipes/PP Bags/LDPE Film/Mixed Plastic/Disposable Cups/Food Packaging. "
            "   for Metal use Copper Wire/Iron Scrap/Steel Scrap/Aluminum/Brass/Lead Battery/Tin Cans/MS Steel. "
            "   for Paper use Cardboard/Newspaper/White Paper/Books/Kraft Paper/Printing Paper. "
            "   for E-Waste use Mobile Phones/Circuit Boards/Chargers/Lead Battery/Television/Computer/Motor Winding/Wires PCB. "
            "   for Glass use Glass Bottles/Medicine Bottles/Glass Jars/Lab Glass/Flat Glass. "
            "   for Organic use Food Waste/Vegetable Waste/Rice Husk/Sugarcane Bagasse/Fruit Waste/Flower Waste/Oil Cake. "
            "   for Textile use Cotton Fabric/Polyester/Jute/Denim/Leather/Cloth Cuttings/Mixed Fabric. "
            "   for Rubber use Vehicle Tyres/Cycle Tyres/Rubber Pipes/Rubber Sole/Industrial Rubber. "
            "3. quality: Excellent if 80-100, Good if 60-79, Fair if 40-59, Poor if 0-39. "
            "4. quality_score: 0-100 integer based on ACTUAL visible condition. "
            "5. confidence: 90-99 if image crystal clear, 75-89 if mostly clear, 60-74 if partially visible. "
            "6. estimated_price REALISTIC INR per kg Bihar UP kabadi 2025: "
            "   PET Bottles 15-25, HDPE 12-20, PVC 8-15, Mixed Plastic 5-12, "
            "   Copper Wire 400-650, Iron Scrap 22-35, Steel 25-32, Aluminum 70-100, Brass 250-320, "
            "   Cardboard 7-12, Newspaper 5-8, White Paper 8-12, "
            "   PCB Circuit Boards 280-450, Mobile Phones 150-300, Lead Battery 60-100, Motor Winding 380-480, "
            "   Glass Bottles 3-8, "
            "   Organic Food 1-3, Rice Husk 1-3, Sugarcane Bagasse 2-4, "
            "   Cotton Textile 8-15, Jute 7-12, Polyester 6-10, "
            "   Vehicle Tyres 10-18, Cycle Tyres 8-14. "
            "7. should_buy true only if quality_score above 50. "
            "8. market_demand: High for Copper Metal E-Waste, Medium for Plastic Paper Textile, Low for Organic Glass Rubber. "
            "9. buy_recommendation: ONE sentence honest advice Hindi-English mix. "
            "10. Be 100 percent honest - if waste mixed or contaminated clearly say so."
        )

        headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
        payload = {
            "model": "meta-llama/llama-4-scout-17b-16e-instruct",
            "messages": [{"role": "user", "content": [
                {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{img_b64}"}},
                {"type": "text", "text": prompt_text}
            ]}],
            "max_tokens": 700,
            "temperature": 0.05
        }
        response = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=30)
        result = response.json()
        if 'error' in result:
            raise Exception(result['error'].get('message', 'Groq API error'))
        raw = result['choices'][0]['message']['content'].strip()
        raw = raw.replace('```json', '').replace('```', '').strip()
        data = json.loads(raw) if raw.startswith('{') else json.loads(raw[raw.find('{'):raw.rfind('}')+1])
        data['success'] = True
        return jsonify(data)

    except json.JSONDecodeError:
        return jsonify({'success': True, 'category': 'Plastic', 'subcategory': 'Mixed Plastic',
            'quality_score': 60, 'quality': 'Good', 'confidence': 70, 'estimated_price': 15,
            'price_range': '12-18', 'co2_saved': 2.0, 'should_buy': True,
            'buy_recommendation': 'Theek hai - average quality', 'condition_notes': 'Unclear image',
            'material_details': 'Could not determine', 'weight_estimate': 'Unknown',
            'market_demand': 'Medium', 'recommendations': ['Clearer photo bhejo', 'Good lighting chahiye'],
            'description': 'Analysis unclear'})
    except Exception as e:
        print("AI ERROR:", str(e))
        return jsonify({'success': False, 'error': str(e)})


# LIST WASTE
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
        city = data.get('location', '').split(',')[-1].strip() if data.get('location') else ''
        db = get_db()
        db.execute('''INSERT INTO listings
            (title,category,subcategory,quality,quality_score,price,quantity,
             seller_name,seller_phone,seller_type,location,city,image_path,co2_saved)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)''', (
            data.get('title'), data.get('category'), data.get('subcategory', ''),
            data.get('quality', 'Good'), int(data.get('quality_score', 70)),
            float(data.get('price', 0)), float(data.get('quantity', 0)),
            data.get('seller_name'), data.get('seller_phone'),
            data.get('seller_type', 'Individual'), data.get('location'), city,
            image_path, float(data.get('co2_saved', 2.5))))
        db.commit()
        db.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


# BULK LISTING
@app.route('/api/bulk-list', methods=['POST'])
def api_bulk_list():
    try:
        data = request.json
        items = data.get('items', [])
        if not items:
            return jsonify({'success': False, 'error': 'No items provided'})
        db = get_db()
        count = 0
        for item in items:
            if item.get('title') and item.get('category') and item.get('price'):
                db.execute('''INSERT INTO listings
                    (title,category,subcategory,quality,quality_score,price,quantity,
                     seller_name,seller_phone,seller_type,location,co2_saved)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?)''', (
                    item.get('title'), item.get('category'), item.get('subcategory', ''),
                    item.get('quality', 'Good'), int(item.get('quality_score', 70)),
                    float(item.get('price', 0)), float(item.get('quantity', 0)),
                    item.get('seller_name'), item.get('seller_phone'),
                    item.get('seller_type', 'Individual'), item.get('location'), 2.5))
                count += 1
        db.commit()
        db.close()
        return jsonify({'success': True, 'added': count})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


# RATING
@app.route('/api/rate', methods=['POST'])
def api_rate():
    try:
        data = request.json
        listing_id = data.get('listing_id')
        rating = int(data.get('rating', 0))
        if not listing_id or rating < 1 or rating > 5:
            return jsonify({'success': False, 'error': 'Invalid rating'})
        db = get_db()
        db.execute('INSERT INTO ratings (listing_id, rating) VALUES (?, ?)', (listing_id, rating))
        avg = db.execute('SELECT AVG(rating), COUNT(*) FROM ratings WHERE listing_id=?', (listing_id,)).fetchone()
        db.execute('UPDATE listings SET rating=?, rating_count=? WHERE id=?', (round(avg[0], 1), avg[1], listing_id))
        db.commit()
        db.close()
        return jsonify({'success': True, 'avg_rating': round(avg[0], 1), 'count': avg[1]})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


# PRICE HISTORY DATA
@app.route('/api/price-history')
def api_price_history():
    data = {
        'categories': ['Plastic', 'Paper', 'Metal', 'E-Waste', 'Glass', 'Organic', 'Textile', 'Rubber'],
        'current_prices': [15, 8, 35, 280, 5, 2, 11, 13],
        'last_month': [13, 7, 32, 260, 5, 2, 10, 12],
        'three_months': [12, 7, 30, 240, 4, 1, 9, 11],
        'trend': ['up', 'up', 'up', 'up', 'stable', 'up', 'up', 'up']
    }
    return jsonify(data)


# BUY
@app.route('/api/buy', methods=['POST'])
def api_buy():
    try:
        data = request.json
        db = get_db()
        listing = db.execute('SELECT title FROM listings WHERE id=?', (data.get('listing_id'),)).fetchone()
        item_title = listing['title'] if listing else 'Unknown'
        db.execute('''INSERT INTO orders (listing_id,item_title,buyer_name,buyer_phone,buyer_email,quantity_wanted,offer_price,message)
            VALUES (?,?,?,?,?,?,?,?)''', (
            data.get('listing_id'), item_title, data.get('buyer_name'),
            data.get('buyer_phone'), data.get('buyer_email'),
            data.get('quantity_wanted'), data.get('offer_price'), data.get('message')))
        db.commit()
        db.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


# DONATE
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
        db.execute('''INSERT INTO donations (item_name,category,condition,quantity,donor_name,donor_phone,donor_email,pickup_address,ngo_name,message,image_path)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)''', (
            data.get('item_name'), data.get('category'), data.get('condition'),
            data.get('quantity'), data.get('donor_name'), data.get('donor_phone'),
            data.get('donor_email'), data.get('pickup_address'),
            data.get('ngo_name'), data.get('message'), image_path))
        db.commit()
        db.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


# CONTACT
@app.route('/api/contact', methods=['POST'])
def api_contact():
    try:
        data = request.json
        db = get_db()
        db.execute('INSERT INTO messages (name,email,phone,subject,message) VALUES (?,?,?,?,?)', (
            data.get('name'), data.get('email'), data.get('phone'),
            data.get('subject'), data.get('message')))
        db.commit()
        db.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


# ADMIN ORDER STATUS
@app.route('/api/order/<int:order_id>/status', methods=['POST'])
def update_order_status(order_id):
    if not session.get('admin'):
        return jsonify({'success': False, 'error': 'Unauthorized'})
    try:
        data = request.json
        db = get_db()
        db.execute('UPDATE orders SET status=? WHERE id=?', (data.get('status'), order_id))
        db.commit()
        db.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


# ADMIN DELETE LISTING
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


if __name__ == '__main__':
    os.makedirs('uploads', exist_ok=True)
    init_db()
    app.run(debug=True)