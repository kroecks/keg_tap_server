# app.py - Main Flask application for Keg Tap Management
from flask import Flask, render_template, request, redirect, url_for, jsonify, send_from_directory, send_file
from PIL import Image
import io
import sqlite3
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'static/beer_images'
app.config['DATABASE'] = 'beer_taps.db'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def get_db_connection():
    conn = sqlite3.connect(app.config['DATABASE'])
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with app.app_context():
        conn = get_db_connection()
        with open('schema.sql') as f:
            conn.executescript(f.read())
        conn.commit()
        conn.close()

@app.route('/')
def index():
    conn = get_db_connection()
    beers = conn.execute('SELECT * FROM beers').fetchall()
    taps = conn.execute('SELECT taps.id, taps.tap_id, taps.beer_id, taps.volume, taps.full_volume, taps.flow_rate, beers.name AS beer_name '
                      'FROM taps LEFT JOIN beers ON taps.beer_id = beers.id').fetchall()
    conn.close()
    return render_template('index.html', beers=beers, taps=taps)

@app.route('/beers')
def beers():
    conn = get_db_connection()
    beers = conn.execute('SELECT * FROM beers').fetchall()
    conn.close()
    return render_template('beers.html', beers=beers)

@app.route('/add_beer', methods=('GET', 'POST'))
def add_beer():
    if request.method == 'POST':
        name = request.form['name']
        abv = float(request.form['abv'])

        # Handle image upload
        image_path = None
        if 'image' in request.files:
            file = request.files['image']
            if file.filename != '':
                filename = secure_filename(file.filename)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                image_path = f'beer_images/{filename}'

        conn = get_db_connection()
        conn.execute('INSERT INTO beers (name, abv, image_path) VALUES (?, ?, ?)',
                    (name, abv, image_path))
        conn.commit()
        conn.close()
        return redirect(url_for('beers'))

    return render_template('add_beer.html')

@app.route('/taps')
def taps():
    conn = get_db_connection()
    taps = conn.execute('SELECT taps.id, taps.tap_id, taps.beer_id, taps.volume, taps.full_volume, taps.flow_rate, beers.name AS beer_name, beers.image_path as beer_image '
                      'FROM taps LEFT JOIN beers ON taps.beer_id = beers.id').fetchall()
    beers = conn.execute('SELECT * FROM beers').fetchall()
    conn.close()
    return render_template('taps.html', taps=taps, beers=beers)

@app.route('/add_tap', methods=('GET', 'POST'))
def add_tap():
    if request.method == 'POST':
        tap_id = request.form['tap_id']
        beer_id = request.form['beer_id'] if request.form['beer_id'] else None
        volume = float(request.form['volume'])
        # Just use the volume as the full_volume, since this is the starting volume
        full_volume = volume
        flow_rate = float(request.form['flow_rate'])

        conn = get_db_connection()
        conn.execute('INSERT INTO taps (tap_id, beer_id, volume, full_volume, flow_rate) VALUES (?, ?, ?, ?)',
                    (tap_id, beer_id, volume, full_volume, flow_rate))
        conn.commit()
        conn.close()
        return redirect(url_for('taps'))

    conn = get_db_connection()
    beers = conn.execute('SELECT * FROM beers').fetchall()
    conn.close()
    return render_template('add_tap.html', beers=beers)

@app.route('/edit_tap/<int:id>', methods=('GET', 'POST'))
def edit_tap(id):
    conn = get_db_connection()
    tap = conn.execute('SELECT * FROM taps WHERE id = ?', (id,)).fetchone()

    if not tap:
        conn.close()
        return redirect(url_for('taps'))

    if request.method == 'POST':
        tap_id = request.form['tap_id']
        beer_id = request.form['beer_id'] if request.form['beer_id'] else None
        volume = float(request.form['volume'])
        full_volume = float(request.form['full_volume'])
        flow_rate = float(request.form['flow_rate'])

        conn.execute('UPDATE taps SET tap_id = ?, beer_id = ?, volume = ?, full_volume = ?, flow_rate = ? WHERE id = ?',
                   (tap_id, beer_id, volume, full_volume, flow_rate, id))
        conn.commit()
        conn.close()
        return redirect(url_for('taps'))

    beers = conn.execute('SELECT * FROM beers').fetchall()
    conn.close()
    return render_template('edit_tap.html', tap=tap, beers=beers)

@app.route('/edit_beer/<int:id>', methods=('GET', 'POST'))
def edit_beer(id):
    conn = get_db_connection()
    beer = conn.execute('SELECT * FROM beers WHERE id = ?', (id,)).fetchone()

    if not beer:
        conn.close()
        return redirect(url_for('beers'))

    if request.method == 'POST':
        name = request.form['name']
        abv = float(request.form['abv'])

        # Handle image upload
        image_path = beer['image_path']  # Keep existing image by default
        if 'image' in request.files:
            file = request.files['image']
            if file.filename != '':
                filename = secure_filename(file.filename)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                image_path = f'beer_images/{filename}'

        conn.execute('UPDATE beers SET name = ?, abv = ?, image_path = ? WHERE id = ?',
                     (name, abv, image_path, id))
        conn.commit()
        conn.close()
        return redirect(url_for('beers'))

    conn.close()
    return render_template('edit_beer.html', beer=beer)

# API Endpoints for ESP32 Communication
@app.route('/api/tap/<tap_id>', methods=['GET'])
def get_tap_info(tap_id):
    conn = get_db_connection()
    tap = conn.execute('SELECT taps.*, beers.name, beers.abv, beers.image_path FROM taps '
                     'LEFT JOIN beers ON taps.beer_id = beers.id '
                     'WHERE tap_id = ?', (tap_id,)).fetchone()
    conn.close()

    if not tap:
        return jsonify({'error': 'Tap not found'}), 404

    return jsonify({
        'tap_id': tap['tap_id'],
        'beer_name': tap['name'],
        'beer_abv': tap['abv'],
        'volume': tap['volume'],
        'full_volume': tap['full_volume'],
        'flow_rate': tap['flow_rate'],
        'image_path': tap['image_path']
    })

@app.route('/api/tap/<tap_id>/image', methods=['GET'])
def get_tap_image(tap_id):
    width = request.args.get('width', type=int)
    height = request.args.get('height', type=int)

    conn = get_db_connection()
    tap = conn.execute('SELECT beers.image_path FROM taps '
                       'LEFT JOIN beers ON taps.beer_id = beers.id '
                       'WHERE tap_id = ?', (tap_id,)).fetchone()
    conn.close()

    if not tap or not tap['image_path']:
        image_path = os.path.join('static/beer_images', 'default.jpg')
    else:
        image_filename = os.path.basename(tap['image_path'])
        image_path = os.path.join('static/beer_images', image_filename)

    if not width or not height:
        return send_file(image_path, mimetype='image/jpeg')

    # Open and resize the image using Pillow
    with Image.open(image_path) as img:
        # Convert mode before resizing/cropping
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")

        # Calculate scale and crop to fill
        src_ratio = img.width / img.height
        target_ratio = width / height

        if target_ratio > src_ratio:
            scale_height = int(width / src_ratio)
            img = img.resize((width, scale_height), Image.LANCZOS)
            top = (scale_height - height) // 2
            img = img.crop((0, top, width, top + height))
        else:
            scale_width = int(height * src_ratio)
            img = img.resize((scale_width, height), Image.LANCZOS)
            left = (scale_width - width) // 2
            img = img.crop((left, 0, left + width, height))

        img_io = io.BytesIO()
        img.save(img_io, format='JPEG', quality=85)
        img_io.seek(0)
        return send_file(img_io, mimetype='image/jpeg')

@app.route('/api/tap/<tap_id>/update_volume', methods=['POST'])
def update_volume(tap_id):
    data = request.json
    if not data or 'pour_time' not in data:
        return jsonify({'error': 'Missing pour_time parameter'}), 400

    pour_time = float(data['pour_time'])  # seconds

    conn = get_db_connection()
    tap = conn.execute('SELECT * FROM taps WHERE tap_id = ?', (tap_id,)).fetchone()

    if not tap:
        conn.close()
        return jsonify({'error': 'Tap not found'}), 404

    # Calculate volume poured based on flow rate (mL/s)
    volume_poured = pour_time * tap['flow_rate']
    new_volume = max(0, tap['volume'] - volume_poured)

    conn.execute('UPDATE taps SET volume = ? WHERE tap_id = ?', (new_volume, tap_id))
    conn.commit()
    conn.close()

    return jsonify({'success': True, 'new_volume': new_volume})

@app.route('/api/tap/<tap_id>/pour_event', methods=['POST'])
def pour_event(tap_id):
    data = request.json
    if not data or 'event_type' not in data:
        return jsonify({'error': 'Missing event_type parameter'}), 400

    event_type = data['event_type']  # 'start' or 'stop'

    if event_type == 'start':
        # Just acknowledge the start event
        return jsonify({'success': True})

    elif event_type == 'stop':
        if 'duration' not in data:
            return jsonify({'error': 'Missing duration parameter for stop event'}), 400

        duration = float(data['duration'])  # seconds

        conn = get_db_connection()
        tap = conn.execute('SELECT * FROM taps WHERE tap_id = ?', (tap_id,)).fetchone()

        if not tap:
            conn.close()
            return jsonify({'error': 'Tap not found'}), 404

        # Calculate volume poured based on flow rate (mL/s)
        volume_poured = duration * tap['flow_rate']
        new_volume = max(0, tap['volume'] - volume_poured)

        conn.execute('UPDATE taps SET volume = ? WHERE tap_id = ?', (new_volume, tap_id))
        conn.commit()
        conn.close()

        return jsonify({'success': True, 'volume_poured': volume_poured, 'new_volume': new_volume})

    return jsonify({'error': 'Invalid event_type'}), 400

if __name__ == '__main__':
    # Check if database exists, if not initialize it
    if not os.path.exists(app.config['DATABASE']):
        init_db()
    app.run(host='0.0.0.0', port=5000, debug=True)