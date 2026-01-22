import os
import shutil
from flask import Flask, request, jsonify, send_file, render_template, redirect, url_for, flash
from flask_cors import CORS
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from datetime import datetime
import subprocess
import threading
import sys

# --- SETTINGS (ABSOLUTE PATHS) ---
# Programın çalıştığı ana dizini al
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
SEPARATED_FOLDER = os.path.join(BASE_DIR, 'separated')

# Klasörleri oluştur
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(SEPARATED_FOLDER, exist_ok=True)

app = Flask(__name__)
CORS(app)
app.secret_key = 'xiao_secret_key_final_v2'

# --- DATABASE CONFIG ---
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(BASE_DIR, "database.db")}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- LOGIN MANAGER ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


# --- MODELS ---
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    projects = db.relationship('Project', backref='owner', lazy=True)


class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    song_name = db.Column(db.String(200), nullable=False)
    folder_name = db.Column(db.String(200), nullable=False)
    status = db.Column(db.String(20), default='draft')
    date_created = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)


with app.app_context():
    db.create_all()


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# --- DEMUCS RUNNER (TR WINDOWS FIX) ---
global_progress = "Ready."


def run_demucs(file_path, model, shifts, overlap, song_name_clean):
    global global_progress

    # 1. ORTAM DEĞİŞKENLERİ (ENVIRONMENT)
    # FFmpeg'i ve UTF-8 kodlamayı zorluyoruz
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["TORCHAUDIO_BACKEND"] = "soundfile"

    # Eğer ffmpeg.exe proje klasöründeyse onu PATH'e ekle
    ffmpeg_local = os.path.join(BASE_DIR, "ffmpeg.exe")
    if os.path.exists(ffmpeg_local):
        print(f"Server Log: Using local FFmpeg -> {ffmpeg_local}")
        # PATH'in en başına ekle ki sistemdekini değil bunu kullansın
        env["PATH"] = BASE_DIR + os.pathsep + env.get("PATH", "")

    # 2. KOMUTU HAZIRLA
    demucs_cmd = shutil.which("demucs")
    if not demucs_cmd:
        # Eğer PATH'de yoksa modül olarak çağır
        command = [sys.executable, "-m", "demucs"]
    else:
        command = [demucs_cmd]

    command.extend([
        "-n", model,
        "--shifts", str(shifts),
        "--overlap", str(overlap),
        "--out", SEPARATED_FOLDER,
        "--jobs", "2",
        file_path
    ])

    print(f"Server Log: Executing Demucs...")

    try:
        # 3. İŞLEMİ BAŞLAT (Encoding Hatalarını Yoksayarak)
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding='utf-8',  # UTF-8 okumaya çalış
            errors='ignore',  # OKUYAMAZSAN ÇÖKME, GEÇ (Kritik Nokta)
            cwd=BASE_DIR,
            env=env
        )

        # 4. ÇIKTILARI OKU
        for line in process.stdout:
            if not line: continue

            clean_line = line.strip()
            # İlerleme çubuğunu veya hataları yakala
            if "Separated" in clean_line:
                global_progress = "Separating Stems..."
                print(f"Demucs Status: {clean_line}")
            elif "%" in clean_line:
                # Yüzdeleri göster
                global_progress = clean_line
            elif "Traceback" in clean_line or "Error" in clean_line:
                print(f"DEMUCS ERROR LOG: {clean_line}")

        process.wait()

        if process.returncode == 0:
            global_progress = "Processing Complete! Loading..."
            print("Server Log: Demucs finished successfully.")
        else:
            global_progress = "Error: Analysis failed."
            print(f"CRITICAL: Demucs failed with code {process.returncode}")

    except Exception as e:
        print(f"CRITICAL SYSTEM ERROR: {e}")
        global_progress = f"System Error: {str(e)}"


# --- ROUTES ---

@app.route('/')
def home():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password.')
    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if User.query.filter_by(username=username).first():
            flash('Username already exists.')
            return redirect(url_for('register'))
        new_user = User(username=username, password=generate_password_hash(password, method='scrypt'))
        db.session.add(new_user)
        db.session.commit()
        login_user(new_user)
        return redirect(url_for('dashboard'))
    return render_template('register.html')


@app.route('/dashboard')
@login_required
def dashboard():
    drafts = Project.query.filter_by(user_id=current_user.id, status='draft').order_by(
        Project.date_created.desc()).all()
    finished = Project.query.filter_by(user_id=current_user.id, status='finished').order_by(
        Project.date_created.desc()).all()
    return render_template('dashboard.html', user=current_user, drafts=drafts, finished=finished)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


@app.route('/mixer')
@login_required
def mixer():
    return render_template('mixer.html')


# --- API ENDPOINTS ---

@app.route('/process', methods=['POST'])
@login_required
def process_audio():
    global global_progress

    if 'file' not in request.files: return jsonify({'error': 'No file part'})
    file = request.files['file']
    if file.filename == '': return jsonify({'error': 'No selected file'})

    model = request.form.get('model', 'htdemucs_6s')
    shifts = int(request.form.get('shifts', 1))
    overlap = float(request.form.get('overlap', 0.25))

    if file:
        filename = secure_filename(file.filename)
        save_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(save_path)

        song_name = os.path.splitext(filename)[0]

        new_project = Project(
            song_name=song_name,
            folder_name=song_name,
            status='draft',
            user_id=current_user.id
        )
        db.session.add(new_project)
        db.session.commit()

        global_progress = "Initializing..."
        threading.Thread(target=run_demucs, args=(save_path, model, shifts, overlap, song_name)).start()

        return jsonify({'status': 'success', 'song_name': song_name, 'project_id': new_project.id})


@app.route('/progress')
def progress():
    return jsonify({'progress': global_progress})


@app.route('/download/<song_name>/<stem>')
def download_stem(song_name, stem):
    # Model klasörünü dinamik bul
    possible_models = ['htdemucs_6s', 'htdemucs', 'mdx_extra_q', 'mdx', 'mdx_extra']
    target_file = None

    for m in possible_models:
        potential_path = os.path.join(SEPARATED_FOLDER, m, song_name, f"{stem}.wav")
        if os.path.exists(potential_path):
            target_file = potential_path
            break

    if target_file:
        return send_file(target_file)
    else:
        print(f"DEBUG: File not found {song_name}/{stem}")
        return "File Not Found", 404


@app.route('/update_status/<int:project_id>', methods=['POST'])
@login_required
def update_status(project_id):
    project = Project.query.get(project_id)
    if project and project.user_id == current_user.id:
        data = request.json
        project.status = data.get('status', 'draft')
        db.session.commit()
        return jsonify({'success': True})
    return jsonify({'error': 'Unauthorized'}), 403


@app.route('/protocol-secret-xiao')
def secret_page():
    return render_template('secret.html')


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)