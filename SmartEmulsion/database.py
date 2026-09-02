import sqlite3
from datetime import datetime
import os

DATABASE_NAME = "emulsao_smart.db"

def get_connection():
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    # Forçar remoção se houver erro de esquema (opcional, mas seguro neste caso)
    conn = get_connection()
    cursor = conn.cursor()
    
    # Criar tabela de tanques
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS tanks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        capacity REAL NOT NULL,
        height REAL NOT NULL,
        calibration_factor REAL DEFAULT 1.0
    )
    ''')

    # Criar tabela de leituras com TODAS as colunas necessárias
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS sensor_readings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        tank_id INTEGER,
        ph REAL,
        oil_concentration REAL,
        level_percent REAL,
        conductivity REAL,
        turbidity REAL,
        FOREIGN KEY (tank_id) REFERENCES tanks(id) ON DELETE CASCADE
    )
    ''')

    # Criar tabela de abastecimentos
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS refills (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        tank_id INTEGER,
        water_liters REAL,
        oil_liters REAL,
        FOREIGN KEY (tank_id) REFERENCES tanks(id) ON DELETE CASCADE
    )
    ''')
    
    conn.commit()
    conn.close()
    print("[DB] Base de dados inicializada.")

def save_reading(tank_id, ph, oil, level_percent, conductivity, turbidity):
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    cursor.execute('''
    INSERT INTO sensor_readings (timestamp, tank_id, ph, oil_concentration, level_percent, conductivity, turbidity)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (now, tank_id, ph, oil, level_percent, conductivity, turbidity))
    conn.commit()
    conn.close()

def get_tanks():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM tanks')
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def save_tank(name, capacity, height, calibration_factor=1.0, tank_id=None):
    conn = get_connection()
    cursor = conn.cursor()
    if tank_id:
        cursor.execute('UPDATE tanks SET name=?, capacity=?, height=?, calibration_factor=? WHERE id=?', 
                       (name, capacity, height, calibration_factor, tank_id))
    else:
        cursor.execute('INSERT INTO tanks (name, capacity, height, calibration_factor) VALUES (?, ?, ?, ?)', 
                       (name, capacity, height, calibration_factor))
    conn.commit()
    conn.close()

def delete_tank(tank_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM tanks WHERE id=?', (tank_id,))
    conn.commit()
    conn.close()

def get_history(tank_id, limit=20):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM sensor_readings WHERE tank_id = ? ORDER BY timestamp DESC LIMIT ?', (tank_id, limit))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in reversed(rows)]

def get_history_v2(tank_id, period='day'):
    conn = get_connection()
    cursor = conn.cursor()
    
    if period == 'day':
        # Últimas 24 horas, agrupado por hora
        query = '''
            SELECT strftime('%Y-%m-%d %H:00', timestamp) as label,
                   AVG(ph) as ph, AVG(oil_concentration) as oil, AVG(level_percent) as level
            FROM sensor_readings 
            WHERE tank_id = ? AND timestamp >= datetime('now', '-1 day')
            GROUP BY label ORDER BY label ASC
        '''
    elif period == 'week':
        # Últimos 7 dias, agrupado por dia
        query = '''
            SELECT DATE(timestamp) as label,
                   AVG(ph) as ph, AVG(oil_concentration) as oil, AVG(level_percent) as level
            FROM sensor_readings 
            WHERE tank_id = ? AND timestamp >= datetime('now', '-7 days')
            GROUP BY label ORDER BY label ASC
        '''
    elif period == 'month':
        # Últimos 30 dias, agrupado por dia
        query = '''
            SELECT DATE(timestamp) as label,
                   AVG(ph) as ph, AVG(oil_concentration) as oil, AVG(level_percent) as level
            FROM sensor_readings 
            WHERE tank_id = ? AND timestamp >= datetime('now', '-30 days')
            GROUP BY label ORDER BY label ASC
        '''
    else:
        return []

    cursor.execute(query, (tank_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_daily_averages(tank_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
    SELECT 
        AVG(ph) as avg_ph, 
        AVG(level_percent) as avg_level, 
        AVG(oil_concentration) as avg_oil,
        AVG(conductivity) as avg_cond,
        AVG(turbidity) as avg_turb
    FROM sensor_readings 
    WHERE tank_id = ? AND DATE(timestamp) = DATE('now', 'localtime')
    ''', (tank_id,))
    row = cursor.fetchone()
    conn.close()
    if row and row['avg_level'] is not None:
        return dict(row)
    return None

def get_weekly_summary(tank_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
    SELECT DATE(timestamp) as date, MAX(ph) as max_ph, AVG(level_percent) as avg_level, MAX(oil_concentration) as max_oil
    FROM sensor_readings WHERE tank_id = ? GROUP BY DATE(timestamp) ORDER BY date DESC LIMIT 7
    ''', (tank_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def save_refill(tank_id, water_liters, oil_liters):
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    cursor.execute('''
    INSERT INTO refills (timestamp, tank_id, water_liters, oil_liters)
    VALUES (?, ?, ?, ?)
    ''', (now, tank_id, water_liters, oil_liters))
    conn.commit()
    conn.close()

def get_supply_stats(tank_id, period='day'):
    conn = get_connection()
    cursor = conn.cursor()
    
    if period == 'day':
        query = "SELECT SUM(water_liters) as water, SUM(oil_liters) as oil FROM refills WHERE tank_id = ? AND timestamp >= datetime('now', '-1 day')"
    elif period == 'week':
        query = "SELECT SUM(water_liters) as water, SUM(oil_liters) as oil FROM refills WHERE tank_id = ? AND timestamp >= datetime('now', '-7 days')"
    elif period == 'month':
        query = "SELECT SUM(water_liters) as water, SUM(oil_liters) as oil FROM refills WHERE tank_id = ? AND timestamp >= datetime('now', '-30 days')"
    else:
        return {"water": 0, "oil": 0}

    cursor.execute(query, (tank_id,))
    row = cursor.fetchone()
    conn.close()
    return {"water": row['water'] or 0, "oil": row['oil'] or 0}

def get_refill_history(tank_id, limit=30):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT timestamp, water_liters, oil_liters 
        FROM refills 
        WHERE tank_id = ? 
        ORDER BY timestamp DESC 
        LIMIT ?
    ''', (tank_id, limit))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]
