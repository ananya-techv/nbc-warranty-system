from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from werkzeug.security import check_password_hash
import sqlite3
import qrcode
import io
import base64
from datetime import date, timedelta
from functools import wraps

app = Flask(__name__)
app.secret_key = 'nbc-warranty-dev-secret-change-in-production'  # fine for a local portfolio project

DATABASE = 'warranty.db'
WARRANTY_DAYS = 365          # standard warranty period
EXPIRING_SOON_DAYS = 30      # flag as "expiring" if within this many days
POINTS_PER_INSTALL = 10      # loyalty points awarded per verified install


def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row  # lets us access columns by name, e.g. row['sku']
    return conn


def get_warranty_status(warranty_expiry_str):
    """Classify a warranty as active / expiring / expired based on today's date."""
    expiry = date.fromisoformat(warranty_expiry_str)
    today = date.today()
    days_left = (expiry - today).days
    if days_left < 0:
        return 'expired'
    elif days_left <= EXPIRING_SOON_DAYS:
        return 'expiring'
    else:
        return 'active'


# ---------- Auth decorators ----------
def mechanic_login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if 'mechanic_id' not in session:
            return redirect(url_for('mechanic_login'))
        return f(*args, **kwargs)
    return wrapper


def admin_login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get('is_admin'):
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return wrapper


# ---------- Home ----------
@app.route('/')
def home():
    conn = get_db()
    total_installations = conn.execute('SELECT COUNT(*) FROM installations').fetchone()[0]
    total_bearings_available = conn.execute(
        'SELECT COUNT(*) FROM bearings WHERE is_used = 0'
    ).fetchone()[0]
    top_mechanics = conn.execute(
        'SELECT name, loyalty_points FROM mechanics ORDER BY loyalty_points DESC LIMIT 3'
    ).fetchall()
    conn.close()
    return render_template(
        'index.html',
        total_installations=total_installations,
        total_bearings_available=total_bearings_available,
        top_mechanics=top_mechanics
    )


# ---------- Mechanic auth ----------
@app.route('/login', methods=['GET', 'POST'])
def mechanic_login():
    error = None
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        conn = get_db()
        mechanic = conn.execute(
            'SELECT * FROM mechanics WHERE username = ?', (username,)
        ).fetchone()
        conn.close()
        if mechanic and check_password_hash(mechanic['password_hash'], password):
            session['mechanic_id'] = mechanic['id']
            session['mechanic_name'] = mechanic['name']
            return redirect(url_for('install_page'))
        error = 'Invalid username or password.'
    return render_template('login.html', role='Mechanic', error=error)


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))


# ---------- Admin auth ----------
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    error = None
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        conn = get_db()
        admin = conn.execute(
            'SELECT * FROM admins WHERE username = ?', (username,)
        ).fetchone()
        conn.close()
        if admin and check_password_hash(admin['password_hash'], password):
            session['is_admin'] = True
            session['admin_username'] = admin['username']
            return redirect(url_for('dashboard'))
        error = 'Invalid username or password.'
    return render_template('login.html', role='Admin', error=error)


# ---------- Installation (mechanic-only) ----------
@app.route('/install')
@mechanic_login_required
def install_page():
    return render_template('install.html', mechanic_name=session['mechanic_name'])


# ---------- Feature 1: Bearing code verification (AJAX endpoint) ----------
@app.route('/api/verify-bearing', methods=['POST'])
@mechanic_login_required
def api_verify_bearing():
    data = request.get_json()
    code = (data.get('bearing_code') or '').strip()

    conn = get_db()
    bearing = conn.execute(
        'SELECT * FROM bearings WHERE bearing_code = ?', (code,)
    ).fetchone()
    conn.close()

    if not bearing:
        return jsonify({'valid': False, 'message': 'Bearing code not found.'})
    if bearing['is_used']:
        return jsonify({'valid': False, 'message': 'This bearing has already been installed.'})

    return jsonify({
        'valid': True,
        'message': f"Valid bearing - SKU {bearing['sku']}",
        'sku': bearing['sku']
    })


# ---------- Feature 2 + 3 + 5: Create installation, certificate, loyalty points ----------
@app.route('/api/install', methods=['POST'])
@mechanic_login_required
def api_install():
    data = request.get_json()
    bearing_code = (data.get('bearing_code') or '').strip()
    location = (data.get('location') or '').strip()
    mechanic_id = session['mechanic_id']  # auto-filled from login, not from the form

    if not bearing_code:
        return jsonify({'success': False, 'message': 'Bearing code is required.'}), 400

    conn = get_db()
    bearing = conn.execute(
        'SELECT * FROM bearings WHERE bearing_code = ?', (bearing_code,)
    ).fetchone()

    if not bearing:
        conn.close()
        return jsonify({'success': False, 'message': 'Bearing code not found.'}), 404
    if bearing['is_used']:
        conn.close()
        return jsonify({'success': False, 'message': 'This bearing has already been installed.'}), 409

    today = date.today()
    warranty_expiry = today + timedelta(days=WARRANTY_DAYS)

    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO installations (bearing_id, mechanic_id, location, install_date, warranty_expiry)
        VALUES (?, ?, ?, ?, ?)
    ''', (bearing['id'], mechanic_id, location, str(today), str(warranty_expiry)))
    installation_id = cursor.lastrowid

    cursor.execute('UPDATE bearings SET is_used = 1 WHERE id = ?', (bearing['id'],))
    cursor.execute(
        'UPDATE mechanics SET loyalty_points = loyalty_points + ? WHERE id = ?',
        (POINTS_PER_INSTALL, mechanic_id)
    )
    conn.commit()

    updated_points = conn.execute(
        'SELECT loyalty_points FROM mechanics WHERE id = ?', (mechanic_id,)
    ).fetchone()['loyalty_points']
    conn.close()

    return jsonify({
        'success': True,
        'installation_id': installation_id,
        'warranty_expiry': str(warranty_expiry),
        'mechanic_points': updated_points,
        'points_awarded': POINTS_PER_INSTALL,
        'certificate_url': url_for('certificate', installation_id=installation_id)
    })


def generate_qr_base64(data_text):
    """Generate a QR code PNG in-memory and return it as a base64 data URI,
    so we can embed it directly in HTML without saving image files to disk."""
    img = qrcode.make(data_text)
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    encoded = base64.b64encode(buffer.getvalue()).decode('utf-8')
    return f"data:image/png;base64,{encoded}"


# ---------- Feature 3: Digital certificate (with QR code) ----------
@app.route('/certificate/<int:installation_id>')
def certificate(installation_id):
    conn = get_db()
    record = conn.execute('''
        SELECT installations.*, bearings.bearing_code, bearings.sku, mechanics.name AS mechanic_name
        FROM installations
        JOIN bearings ON installations.bearing_id = bearings.id
        JOIN mechanics ON installations.mechanic_id = mechanics.id
        WHERE installations.id = ?
    ''', (installation_id,)).fetchone()
    conn.close()

    if not record:
        return "Certificate not found", 404

    status = get_warranty_status(record['warranty_expiry'])
    days_left = (date.fromisoformat(record['warranty_expiry']) - date.today()).days

    cert_no = f"NBC-CERT-{installation_id:05d}"
    qr_data = (
        f"Certificate: {cert_no} | Bearing: {record['bearing_code']} | "
        f"SKU: {record['sku']} | Installed: {record['install_date']} | "
        f"Warranty Expiry: {record['warranty_expiry']}"
    )
    qr_image = generate_qr_base64(qr_data)

    return render_template(
        'certificate.html', record=record, status=status,
        days_left=days_left, cert_no=cert_no, qr_image=qr_image
    )


# ---------- Feature 4: Warranty tracking dashboard (admin-only) ----------
@app.route('/dashboard')
@admin_login_required
def dashboard():
    conn = get_db()
    records = conn.execute('''
        SELECT installations.*, bearings.bearing_code, bearings.sku, mechanics.name AS mechanic_name
        FROM installations
        JOIN bearings ON installations.bearing_id = bearings.id
        JOIN mechanics ON installations.mechanic_id = mechanics.id
        ORDER BY installations.install_date DESC
    ''').fetchall()
    conn.close()

    enriched = []
    counts = {'active': 0, 'expiring': 0, 'expired': 0}
    for r in records:
        status = get_warranty_status(r['warranty_expiry'])
        counts[status] += 1
        enriched.append({**dict(r), 'status': status})

    return render_template('dashboard.html', records=enriched, counts=counts)


# ---------- Feature 5: Mechanic loyalty leaderboard (admin-only) ----------
@app.route('/mechanics')
@admin_login_required
def mechanics_page():
    conn = get_db()
    mechanics = conn.execute(
        'SELECT * FROM mechanics ORDER BY loyalty_points DESC'
    ).fetchall()
    conn.close()
    return render_template('mechanics.html', mechanics=mechanics)


if __name__ == '__main__':
    app.run(debug=True)
