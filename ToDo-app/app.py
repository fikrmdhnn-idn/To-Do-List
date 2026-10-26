import sqlite3
import os
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, jsonify

app = Flask(__name__)
app.config['SECRET_KEY'] = 'mahasiswa-produktif-secret-key-2026'

# Lokasi file database SQLite
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'database.db')


def get_db_connection():
    """Membuka koneksi ke SQLite dengan row_factory agar kolom bisa diakses via nama atribut."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Membuat tabel tasks jika belum ada."""
    with get_db_connection() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                course TEXT,
                deadline TEXT NOT NULL,
                priority TEXT DEFAULT 'Sedang',
                completed INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()


def calculate_deadline_meta(deadline_str, completed):
    """
    Menghitung status deadline dan label sisa waktu yang ramah pengguna.
    Mengembalikan dict: { 'status': 'done'|'overdue'|'urgent'|'upcoming', 'label': str, 'formatted': str }
    """
    if completed:
        try:
            dt = datetime.fromisoformat(deadline_str)
            formatted = dt.strftime("%d %b %Y, %H:%M")
        except Exception:
            formatted = deadline_str
        return {
            'status': 'done',
            'label': 'Selesai',
            'formatted': formatted
        }

    try:
        deadline_dt = datetime.fromisoformat(deadline_str)
        now = datetime.now()
        diff = deadline_dt - now
        formatted = deadline_dt.strftime("%d %b %Y, %H:%M")

        if diff.total_seconds() < 0:
            # Sudah lewat deadline
            past = abs(diff)
            days = past.days
            hours = past.seconds // 3600
            if days > 0:
                label = f"Terlewat {days} hari"
            elif hours > 0:
                label = f"Terlewat {hours} jam"
            else:
                label = "Baru saja lewat"
            return {'status': 'overdue', 'label': label, 'formatted': formatted}
        else:
            days = diff.days
            hours = diff.seconds // 3600
            minutes = (diff.seconds % 3600) // 60

            if days == 0 and hours < 24:
                # Kurang dari 24 jam (Mendekati deadline / Urgent)
                if hours == 0:
                    label = f"Sisa {minutes} menit lagi"
                else:
                    label = f"Sisa {hours} jam {minutes} mnt"
                return {'status': 'urgent', 'label': label, 'formatted': formatted}
            elif days == 1:
                return {'status': 'urgent', 'label': 'Besok deadline', 'formatted': formatted}
            else:
                return {'status': 'upcoming', 'label': f"Sisa {days} hari", 'formatted': formatted}

    except Exception:
        return {'status': 'upcoming', 'label': 'Jadwal deadline', 'formatted': deadline_str}


@app.route('/')
def index():
    """Halaman utama daftar tugas kuliah dengan filter."""
    filter_status = request.args.get('filter', 'all')
    search_query = request.args.get('q', '').strip()

    conn = get_db_connection()

    base_query = 'SELECT * FROM tasks'
    conditions = []
    params = []

    if filter_status == 'active':
        conditions.append('completed = 0')
    elif filter_status == 'completed':
        conditions.append('completed = 1')

    if search_query:
        conditions.append('(title LIKE ? OR course LIKE ?)')
        params.extend([f'%{search_query}%', f'%{search_query}%'])

    if conditions:
        base_query += ' WHERE ' + ' AND '.join(conditions)

    # Urutkan berdasarkan status belum selesai terlebih dahulu, lalu deadline terdekat
    base_query += ' ORDER BY completed ASC, deadline ASC'

    tasks_raw = conn.execute(base_query, params).fetchall()

    # Hitung statistik
    total_count = conn.execute('SELECT COUNT(*) FROM tasks').fetchone()[0]
    active_count = conn.execute('SELECT COUNT(*) FROM tasks WHERE completed = 0').fetchone()[0]
    completed_count = conn.execute('SELECT COUNT(*) FROM tasks WHERE completed = 1').fetchone()[0]
    conn.close()

    # Perkaya data tugas dengan informasi status deadline
    tasks = []
    for row in tasks_raw:
        task_dict = dict(row)
        task_dict['meta'] = calculate_deadline_meta(task_dict['deadline'], task_dict['completed'])
        tasks.append(task_dict)

    return render_template(
        'index.html',
        tasks=tasks,
        total_count=total_count,
        active_count=active_count,
        completed_count=completed_count,
        filter_status=filter_status,
        search_query=search_query,
        current_time=datetime.now().strftime("%Y-%m-%dT%H:%M")
    )


@app.route('/add', methods=['POST'])
def add_task():
    """Menambahkan tugas kuliah baru ke database."""
    title = request.form.get('title', '').strip()
    course = request.form.get('course', '').strip()
    deadline = request.form.get('deadline', '').strip()
    priority = request.form.get('priority', 'Sedang')

    if not title or not deadline:
        return redirect(url_for('index'))

    with get_db_connection() as conn:
        conn.execute(
            'INSERT INTO tasks (title, course, deadline, priority, completed) VALUES (?, ?, ?, ?, 0)',
            (title, course, deadline, priority)
        )
        conn.commit()

    return redirect(url_for('index'))


@app.route('/toggle/<int:task_id>', methods=['POST'])
def toggle_task(task_id):
    """Menandai tugas sebagai selesai atau belum selesai."""
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json

    with get_db_connection() as conn:
        task = conn.execute('SELECT completed FROM tasks WHERE id = ?', (task_id,)).fetchone()
        if not task:
            if is_ajax:
                return jsonify({'success': False, 'message': 'Tugas tidak ditemukan'}), 404
            return redirect(url_for('index'))

        new_status = 0 if task['completed'] == 1 else 1
        conn.execute('UPDATE tasks SET completed = ? WHERE id = ?', (new_status, task_id))
        conn.commit()

    if is_ajax:
        return jsonify({'success': True, 'completed': bool(new_status)})

    return redirect(url_for('index'))


@app.route('/delete/<int:task_id>', methods=['POST'])
def delete_task(task_id):
    """Menghapus tugas dari database."""
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json

    with get_db_connection() as conn:
        conn.execute('DELETE FROM tasks WHERE id = ?', (task_id,))
        conn.commit()

    if is_ajax:
        return jsonify({'success': True})

    return redirect(url_for('index'))


if __name__ == '__main__':
    init_db()
    # Menjalankan server Flask di port 5000
    app.run(debug=True, host='127.0.0.1', port=5000)
