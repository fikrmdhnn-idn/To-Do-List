import sqlite3
import os
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, jsonify

app = Flask(__name__)
app.config['SECRET_KEY'] = 'tugas-kuliah-dark-mode-2026'

# Lokasi database SQLite
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'database.db')


def get_db_connection():
    """Membuka koneksi ke SQLite database."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Inisialisasi tabel database jika belum ada."""
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


def process_task(task_row, now):
    """
    Memproses baris tugas dan menentukan statusnya:
    - active: belum selesai dan belum melewati deadline
    - overdue: belum selesai tapi sudah melewati tenggat waktu
    - completed: sudah dicentang selesai oleh pengguna
    """
    task = dict(task_row)
    deadline_str = task.get('deadline', '')
    is_completed = bool(task.get('completed', 0))

    try:
        deadline_dt = datetime.fromisoformat(deadline_str)
        formatted_date = deadline_dt.strftime("%d %b %Y, %H:%M")
        is_past_deadline = deadline_dt < now
    except Exception:
        deadline_dt = None
        formatted_date = deadline_str
        is_past_deadline = False

    if is_completed:
        task['category'] = 'completed'
        task['status_label'] = 'Selesai Dikerjakan'
        task['status_badge'] = 'badge-completed'
        task['time_desc'] = 'Telah diselesaikan'
    elif is_past_deadline:
        # Sudah melebihi tenggat waktu dan belum dicentang
        task['category'] = 'overdue'
        task['status_label'] = 'Telah Melebihi Tenggat Waktu'
        task['status_badge'] = 'badge-overdue'

        if deadline_dt:
            diff = now - deadline_dt
            days = diff.days
            hours = diff.seconds // 3600
            if days > 0:
                task['time_desc'] = f"Terlewat {days} hari yang lalu"
            elif hours > 0:
                task['time_desc'] = f"Terlewat {hours} jam yang lalu"
            else:
                task['time_desc'] = "Baru saja terlewat"
        else:
            task['time_desc'] = "Tenggat waktu terlewat"
    else:
        # Masih aktif dan dalam masa tenggat
        task['category'] = 'active'
        task['status_badge'] = 'badge-active'

        if deadline_dt:
            diff = deadline_dt - now
            days = diff.days
            hours = diff.seconds // 3600
            minutes = (diff.seconds % 3600) // 60

            if days == 0 and hours < 24:
                task['status_label'] = 'Mendekati Deadline'
                task['status_badge'] = 'badge-urgent'
                if hours == 0:
                    task['time_desc'] = f"Sisa {minutes} menit lagi!"
                else:
                    task['time_desc'] = f"Sisa {hours} jam {minutes} menit lagi"
            elif days == 1:
                task['status_label'] = 'Deadline Besok'
                task['status_badge'] = 'badge-urgent'
                task['time_desc'] = "Besok harus dikumpulkan"
            else:
                task['status_label'] = 'Sedang Berjalan'
                task['time_desc'] = f"Sisa {days} hari lagi"
        else:
            task['status_label'] = 'Sedang Berjalan'
            task['time_desc'] = 'Sesuai jadwal'

    task['formatted_deadline'] = formatted_date
    return task


@app.route('/')
def index():
    """Halaman utama dengan pembagian tugas aktif dan tugas selesai/terlewat."""
    filter_tab = request.args.get('tab', 'active')  # 'active', 'history', 'all'
    search_query = request.args.get('q', '').strip()
    now = datetime.now()

    conn = get_db_connection()

    query = 'SELECT * FROM tasks'
    params = []
    if search_query:
        query += ' WHERE title LIKE ? OR course LIKE ?'
        params.extend([f'%{search_query}%', f'%{search_query}%'])

    query += ' ORDER BY deadline ASC'
    rows = conn.execute(query, params).fetchall()
    conn.close()

    all_tasks = [process_task(row, now) for row in rows]

    # Klasifikasi:
    # 1. active_tasks: Belum selesai DAN belum lewat deadline (tugas yang mau dikerjakan)
    # 2. history_tasks: Sudah selesai ATAU telah melebihi tenggat waktu
    active_tasks = [t for t in all_tasks if t['category'] == 'active']
    overdue_tasks = [t for t in all_tasks if t['category'] == 'overdue']
    completed_tasks = [t for t in all_tasks if t['category'] == 'completed']

    # Gabungan tempat tugas yang telah selesai bersama dengan yang telah melebihi tenggat waktu
    history_tasks = [t for t in all_tasks if t['category'] in ('completed', 'overdue')]
    # Urutkan history: yang overdue dan yang baru selesai di atas
    history_tasks.sort(key=lambda x: (x['category'] != 'overdue', x['deadline']), reverse=True)

    counts = {
        'total': len(all_tasks),
        'active': len(active_tasks),
        'overdue': len(overdue_tasks),
        'completed': len(completed_tasks),
        'history': len(history_tasks)
    }

    return render_template(
        'index.html',
        active_tasks=active_tasks,
        history_tasks=history_tasks,
        all_tasks=all_tasks,
        counts=counts,
        current_tab=filter_tab,
        search_query=search_query,
        current_time=now.strftime("%Y-%m-%dT%H:%M")
    )


@app.route('/add', methods=['POST'])
def add_task():
    """Menambahkan tugas baru ke daftar."""
    title = request.form.get('title', '').strip()
    course = request.form.get('course', '').strip()
    deadline = request.form.get('deadline', '').strip()
    priority = request.form.get('priority', 'Sedang')

    if title and deadline:
        with get_db_connection() as conn:
            conn.execute(
                'INSERT INTO tasks (title, course, deadline, priority, completed) VALUES (?, ?, ?, ?, 0)',
                (title, course, deadline, priority)
            )
            conn.commit()

    return redirect(url_for('index', tab='active'))


@app.route('/toggle/<int:task_id>', methods=['POST'])
def toggle_task(task_id):
    """
    Menandai tugas selesai secara manual:
    - Jika belum selesai -> dicentang menjadi selesai (berpindah ke tempat selesai)
    - Jika sudah selesai -> dikembalikan ke belum selesai
    """
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

    return redirect(request.referrer or url_for('index'))


@app.route('/delete/<int:task_id>', methods=['POST'])
def delete_task(task_id):
    """Menghapus tugas secara permanen dari daftar."""
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json
    with get_db_connection() as conn:
        conn.execute('DELETE FROM tasks WHERE id = ?', (task_id,))
        conn.commit()

    if is_ajax:
        return jsonify({'success': True})

    return redirect(request.referrer or url_for('index'))


@app.route('/clear-history', methods=['POST'])
def clear_history():
    """Menghapus seluruh tugas yang ada di riwayat (selesai & melebihi deadline)."""
    now_iso = datetime.now().strftime("%Y-%m-%dT%H:%M")
    with get_db_connection() as conn:
        # Hapus yang completed == 1 ATAU yang belum selesai tapi deadline sudah terlewat
        conn.execute('DELETE FROM tasks WHERE completed = 1 OR deadline < ?', (now_iso,))
        conn.commit()
    return redirect(url_for('index', tab='history'))


if __name__ == '__main__':
    init_db()
    # Server berjalan di protokol HTTP (http://127.0.0.1:5000)
    print("=" * 60)
    print("🚀 Server Aplikasi Tugas Kuliah Aktif!")
    print("📌 Akses via browser: http://127.0.0.1:5000 (Gunakan HTTP, bukan HTTPS)")
    print("=" * 60)
    app.run(debug=True, host='127.0.0.1', port=5000)
