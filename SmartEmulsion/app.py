import webview
import threading
import os
import sys
import json
import time
import schedule
from bottle import Bottle, run, response, request
from sensores import sensor_manager, HAS_HARDWARE
if HAS_HARDWARE:
    from adafruit_ads1x15.analog_in import AnalogIn
from database import init_db, get_history, get_history_v2, get_weekly_summary, save_reading, get_tanks, save_tank, delete_tank, get_supply_stats, get_refill_history, get_daily_averages

# Configuração do Servidor Externo (API para Node-RED / Grafana)
api_server = Bottle()

@api_server.hook('after_request')
def enable_cors():
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Origin, Accept, Content-Type, X-Requested-With, X-CSRF-Token'

@api_server.route('/<:re:.*>', method='OPTIONS')
def enable_cors_options():
    response.status = 200
    return {}

@api_server.get('/api/sensors')
def external_get_sensors():
    response.content_type = 'application/json'
    return json.dumps(sensor_manager.read_sensors())

@api_server.get('/api/control/pump')
def control_pump():
    action = request.query.get('action', 'off')
    if action == 'on':
        sensor_manager.bomba_hw.off() # .off() liga no teu hardware
        sensor_manager.current_data["pump_running"] = True
        return {"status": "success", "message": "Bomba ligada"}
    else:
        sensor_manager.bomba_hw.on() # .on() desliga
        sensor_manager.current_data["pump_running"] = False
        return {"status": "success", "message": "Bomba desligada"}

@api_server.get('/api/control/valve')
def control_valve():
    action = request.query.get('action', 'off')
    if action == 'on':
        sensor_manager.valvula_hw.off() # .off() abre no teu hardware
        sensor_manager.current_data["valve_open"] = True
        return {"status": "success", "message": "Válvula aberta"}
    else:
        sensor_manager.valvula_hw.on() # .on() fecha
        sensor_manager.current_data["valve_open"] = False
        return {"status": "success", "message": "Válvula fechada"}

# --- NOVOS ENDPOINTS REST (Equivalentes às funções do JS Bridge) ---

@api_server.get('/api/tanks')
def api_get_tanks():
    response.content_type = 'application/json'
    return json.dumps(Bridge().get_tanks())

@api_server.post('/api/tanks')
def api_save_tank():
    response.content_type = 'application/json'
    return json.dumps(Bridge().save_tank(request.json or {}))

@api_server.post('/api/tanks/calibrate')
def api_calibrate_tank():
    data = request.json or {}
    response.content_type = 'application/json'
    return json.dumps(Bridge().calibrate_tank(data.get("tank_id"), data.get("current_level")))

@api_server.delete('/api/tanks/<tank_id:int>')
def api_delete_tank(tank_id):
    response.content_type = 'application/json'
    return json.dumps(Bridge().delete_tank(tank_id))

@api_server.post('/api/tanks/sync')
def api_sync_tank():
    response.content_type = 'application/json'
    return json.dumps(Bridge().sync_tank(request.json or {}))

@api_server.get('/api/tanks/<tank_id:int>/history')
def api_get_history(tank_id):
    response.content_type = 'application/json'
    return json.dumps(Bridge().get_history(tank_id))

@api_server.get('/api/tanks/<tank_id:int>/history_v2')
def api_get_history_v2(tank_id):
    period = request.query.get('period', '7d')
    response.content_type = 'application/json'
    return json.dumps(Bridge().get_history_v2(tank_id, period))

@api_server.get('/api/tanks/<tank_id:int>/supply_stats')
def api_get_supply_stats(tank_id):
    period = request.query.get('period', '7d')
    response.content_type = 'application/json'
    return json.dumps(Bridge().get_supply_stats(tank_id, period))

@api_server.get('/api/tanks/<tank_id:int>/refill_history')
def api_get_refill_history(tank_id):
    response.content_type = 'application/json'
    return json.dumps(Bridge().get_refill_history(tank_id))

@api_server.get('/api/tanks/<tank_id:int>/weekly')
def api_get_weekly(tank_id):
    response.content_type = 'application/json'
    return json.dumps(Bridge().get_weekly(tank_id))

@api_server.post('/api/control/buzzer')
def api_set_buzzer():
    state = (request.json or {}).get('state', False)
    response.content_type = 'application/json'
    return json.dumps(Bridge().set_buzzer(state))

@api_server.post('/api/control/fill/start')
def api_trigger_fill():
    response.content_type = 'application/json'
    return json.dumps(Bridge().trigger_fill(request.json or {}))

@api_server.post('/api/control/fill/cancel')
def api_cancel_fill():
    response.content_type = 'application/json'
    return json.dumps(Bridge().cancel_fill())

@api_server.get('/api/email/schedule')
def api_get_email_schedule():
    response.content_type = 'application/json'
    return json.dumps(Bridge().get_email_schedule())

@api_server.post('/api/email/schedule')
def api_set_email_schedule():
    data = request.json or {}
    response.content_type = 'application/json'
    return json.dumps(Bridge().set_email_schedule(
        data.get('time_str'), 
        data.get('recipient'), 
        data.get('sender_email'), 
        data.get('sender_password')
    ))

@api_server.post('/api/email/send')
def api_send_email():
    data = request.json or {}
    response.content_type = 'application/json'
    return json.dumps(Bridge().send_email(data.get('recipient_email')))

# -------------------------------------------------------------------

def run_api_server():
    # Ouve em todas as interfaces na porta 5000
    try:
        run(api_server, host='0.0.0.0', port=5000, quiet=True)
    except Exception as e:
        print(f"[ERRO] Servidor API: {e}")

def load_email_config():
    try:
        with open("settings.json", "r") as f:
            return json.load(f)
    except:
        return {
            "time": "19:00", 
            "recipient": "admin@emulpro.com",
            "sender_email": "f.f.nunes2005@gmail.com",
            "sender_password": "kgdddkiqsozauqxb"
        }

def save_email_config(time_str, recipient, sender_email, sender_password):
    with open("settings.json", "w") as f:
        json.dump({
            "time": time_str, 
            "recipient": recipient,
            "sender_email": sender_email,
            "sender_password": sender_password
        }, f)

class Bridge:
    def get_email_schedule(self):
        return load_email_config()

    def set_email_schedule(self, time_str, recipient, sender_email, sender_password):
        global email_job, current_recipient
        current_recipient = recipient
        save_email_config(time_str, recipient, sender_email, sender_password)
        if 'email_job' in globals() and email_job:
            schedule.cancel_job(email_job)
        if time_str:
            print(f"[CONFIG] Novo horário do relatório: {time_str} para {recipient}")
            # Use a wrapper function to call send_email so it's fresh
            email_job = schedule.every().day.at(time_str).do(lambda: self.send_email(current_recipient))
        return {"status": "success"}

    def get_tanks(self):
        try:
            return get_tanks()
        except Exception as e:
            print(f"[ERRO] Falha ao carregar tanques: {e}")
            return []

    def save_tank(self, tank):
        try:
            name = tank.get("name")
            capacity = float(tank.get("capacity"))
            height = float(tank.get("height"))
            tank_id = tank.get("id")
            
            # Valor padrão ou existente
            calibration_factor = 0.0
            
            # Se for uma edição, tentar manter o fator atual
            if tank_id:
                existing_tanks = get_tanks()
                this_tank = next((t for t in existing_tanks if t['id'] == tank_id), None)
                if this_tank:
                    calibration_factor = this_tank.get('calibration_factor', 0.0)

            save_tank(name, capacity, height, calibration_factor, tank_id)
            return {"status": "success"}
        except Exception as e:
            print(f"[ERRO] Falha ao salvar tanque: {e}")
            return {"status": "error", "message": str(e)}

    def calibrate_tank(self, tank_id, current_real_h):
        try:
            if not tank_id:
                return {"status": "error", "message": "ID do tanque não fornecido."}
            if current_real_h is None or str(current_real_h).strip() == "":
                return {"status": "error", "message": "Altura real não fornecida."}
                
            calibration_factor = 0.0
            if sensor_manager.ads:
                try:
                    v_level = AnalogIn(sensor_manager.ads, 3).voltage
                    corrente = (v_level / 110.0) * 1000.0

                    if corrente > 4.4:
                        perc_raw = (corrente - 4.35) / (20.0 - 4.35)
                        raw_h_cm = perc_raw * 500.0 
                        calibration_factor = float(current_real_h) - raw_h_cm
                        print(f"[CALIBRAÇÃO] Novo OFFSET calculado: {calibration_factor:.4f}")
                    else:
                        calibration_factor = float(current_real_h)
                        print(f"[CALIBRAÇÃO] Sensor no limite inferior. OFFSET assumido: {calibration_factor}")
                except Exception as e:
                    print(f"[ERRO] Falha ao ler sensor para calibração: {e}")
                    return {"status": "error", "message": "Erro ao ler sensor."}
            else:
                print("[AVISO] ADS1115 não detetado. Calibração ignorada.")
                return {"status": "error", "message": "Hardware não detetado."}
                
            # Atualizar só o fator de calibração na DB para este tanque
            import sqlite3
            conn = sqlite3.connect("emulsao_smart.db")
            cursor = conn.cursor()
            cursor.execute('UPDATE tanks SET calibration_factor=? WHERE id=?', (calibration_factor, tank_id))
            conn.commit()
            conn.close()
            
            # Se for o tanque ativo, atualizar em runtime
            if sensor_manager.current_data.get("tank_id") == tank_id:
                sensor_manager.current_data["calibration_factor"] = float(calibration_factor)
                
            return {"status": "success", "calibration_factor": calibration_factor}
        except Exception as e:
            print(f"[ERRO] Falha ao calibrar tanque: {e}")
            return {"status": "error", "message": str(e)}

    def delete_tank(self, tank_id):
        try:
            delete_tank(tank_id)
            return {"status": "success"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def sync_tank(self, tank):
        try:
            tank_id = tank.get("id")
            if not tank_id:
                return {"status": "error", "message": "ID do tanque é obrigatório para sincronizar"}
                
            # Ler dados reais da base de dados usando apenas o ID
            tanks = get_tanks()
            db_tank = next((t for t in tanks if t['id'] == tank_id), None)
            
            if not db_tank:
                return {"status": "error", "message": "Tanque não encontrado na base de dados"}
                
            sensor_manager.current_data["tank_id"] = db_tank.get("id")
            sensor_manager.current_data["tank_name"] = db_tank.get("name", "Tanque")
            sensor_manager.current_data["capacity"] = float(db_tank.get("capacity", 500))
            sensor_manager.current_data["height"] = float(db_tank.get("height", 500))
            sensor_manager.current_data["calibration_factor"] = float(db_tank.get("calibration_factor", 1.0))
            
            print(f"[BRIDGE] Tanque sincronizado: ID {sensor_manager.current_data['tank_id']} - {sensor_manager.current_data['tank_name']} (Fator: {sensor_manager.current_data['calibration_factor']})")
            return {"status": "success"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def get_history(self, tank_id):
        try:
            return get_history(tank_id)
        except Exception as e:
            print(f"[ERRO] Falha ao obter histórico: {e}")
            return []

    def get_history_v2(self, tank_id, period):
        try:
            return get_history_v2(tank_id, period)
        except Exception as e:
            print(f"[ERRO] Falha ao obter histórico v2 ({period}): {e}")
            return []

    def get_supply_stats(self, tank_id, period):
        try:
            return get_supply_stats(tank_id, period)
        except Exception as e:
            print(f"[ERRO] Falha ao obter estatísticas de abastecimento: {e}")
            return {"water": 0, "oil": 0}

    def get_refill_history(self, tank_id):
        try:
            return get_refill_history(tank_id)
        except Exception as e:
            print(f"[ERRO] Falha ao obter histórico de abastecimento: {e}")
            return []

    def get_weekly(self, tank_id):
        try:
            return get_weekly_summary(tank_id)
        except Exception as e:
            print(f"[ERRO] Falha ao obter resumo semanal: {e}")
            return []

    def get_sensors(self):
        return sensor_manager.read_sensors()

    def set_buzzer(self, state):
        sensor_manager.set_buzzer(state)
        return {"status": "ok"}

    def trigger_fill(self, req):
        try:
            capacity = sensor_manager.current_data["capacity"]
            target_lvl_pct = float(req.get("target_level_percent", 0))
            target_oil_pct = float(req.get("target_oil_percent", 0))
            
            target_liters = (target_lvl_pct / 100) * capacity
            
            # Cálculo automático da quantidade de óleo a adicionar
            current_vol = sensor_manager.current_data.get("raw_level", 0)
            current_oil_pct = sensor_manager.current_data.get("oil", 0)
            
            current_oil_vol = current_vol * (current_oil_pct / 100.0)
            target_oil_vol = target_liters * (target_oil_pct / 100.0)
            
            oil_to_add = target_oil_vol - current_oil_vol
            if oil_to_add < 0:
                oil_to_add = 0.0
            
            oil_to_add = round(oil_to_add, 2)
            
            print(f"[BRIDGE] Iniciando enchimento: Alvo {target_liters}L ({target_lvl_pct}%), Óleo a adicionar: {oil_to_add}L")
            
            # Iniciar processo de enchimento em background com refinamento
            sensor_manager.process_fill(target_liters, oil_to_add, target_oil_pct)
            
            return {"status": "success", "message": "Processo de enchimento iniciado", "calculated_oil": oil_to_add}
        except Exception as e:
            print(f"[ERRO] Falha ao iniciar enchimento: {e}")
            return {"status": "error", "message": str(e)}

    def cancel_fill(self):
        try:
            sensor_manager.cancel_fill()
            return {"status": "success"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def send_email(self, recipient_email):
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        from datetime import datetime
        
        # DEFINIR AQUI AS CREDENCIAIS DE ENVIO:
        cfg = load_email_config()
        SENDER_EMAIL = cfg.get("sender_email", "f.f.nunes2005@gmail.com")
        SENDER_PASSWORD = cfg.get("sender_password", "kgdddkiqsozauqxb")
        
        try:
            # Recolher dados do tanque
            tank_id = sensor_manager.current_data.get("tank_id")
            tank_name = sensor_manager.current_data.get("tank_name", "Tanque")
            
            # Tentar obter médias do dia atual
            avg_data = None
            if tank_id:
                avg_data = get_daily_averages(tank_id)
            
            # Se não houver dados históricos de hoje, cair de volta para dados instantâneos
            if not avg_data:
                data = sensor_manager.read_sensors()
                avg_data = {
                    'avg_level': data.get('level_percent', 0),
                    'avg_oil': data.get('oil', 0),
                    'avg_ph': data.get('ph', 0),
                    'avg_turb': data.get('turbidity', 0),
                    'avg_cond': data.get('conductivity', 0)
                }
            
            data_atual = datetime.now().strftime("%d/%m/%Y")
            
            # Formatar a mensagem do e-mail
            msg = MIMEMultipart()
            msg['From'] = SENDER_EMAIL
            msg['To'] = recipient_email
            msg['Subject'] = f"Relatório EmulPro - {tank_name} - {data_atual}"
            
            body = f"""Olá,
Segue o relatório com as médias do dia atual ({data_atual}) para o seu tanque:

[ {tank_name} ]
• Nível de Enchimento (Média): {avg_data.get('avg_level', 0):.1f}%
• Concentração de Óleo (Média): {avg_data.get('avg_oil', 0):.1f}%
• pH (Média): {avg_data.get('avg_ph', 0):.2f}
• Turbidez (Média): {avg_data.get('avg_turb', 0):.1f} NTU
• Condutividade (Média): {avg_data.get('avg_cond', 0):.1f} µS

Gerado automaticamente por EmulPro.
"""
            msg.attach(MIMEText(body, 'plain', 'utf-8'))
            
            print(f"[BRIDGE] A enviar e-mail para {recipient_email}...")
            
            # Enviar e-mail via servidor SMTP do Gmail (ou outro)
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.sendmail(SENDER_EMAIL, recipient_email, msg.as_string())
            server.quit()
            
            print(f"[BRIDGE] E-mail enviado com sucesso para {recipient_email}.")
            return {"status": "success"}
        except Exception as e:
            print(f"[ERRO] Falha ao enviar e-mail: {e}")
            return {"status": "error", "message": str(e)}

    def close_app(self):
        print("[BRIDGE] Fechando aplicação...")
        os._exit(0)

def agendador_de_emails():
    while True:
        schedule.run_pending()
        time.sleep(1)

def start_app():
    # Desativar aceleração de hardware para evitar problemas de renderização no Raspberry Pi (linhas no ecrã)
    os.environ["WEBKIT_DISABLE_COMPOSITING_MODE"] = "1"
    os.environ["WEBKIT_DISABLE_ACCELERATED_2D_CANVAS"] = "1"
    
    # Inicializar Base de Dados
    init_db()
    
    # Iniciar monitorização em background
    sensor_manager.start_monitoring(interval=5)

    # Iniciar Thread do relógio de e-mails em background
    threading.Thread(target=agendador_de_emails, daemon=True).start()

    # Configurar alarme persistente de e-mail
    cfg = load_email_config()
    Bridge().set_email_schedule(
        cfg.get("time", "19:00"), 
        cfg.get("recipient", "admin@emulpro.com"),
        cfg.get("sender_email", "f.f.nunes2005@gmail.com"),
        cfg.get("sender_password", "kgdddkiqsozauqxb")
    )

    # Iniciar Servidor API HTTP para Node-RED / Grafana (Porta 5000)
    threading.Thread(target=run_api_server, daemon=True).start()
    
    # Caminho para o ficheiro HTML
    html_path = os.path.join(os.path.dirname(__file__), "templates", "index.html")
    
    # Criar a Janela (Fullscreen para Kiosk)
    api = Bridge()
    window = webview.create_window(
        "EmulPro", 
        html_path, 
        js_api=api,
        width=1280, 
        height=720,
        fullscreen=True # Ativar fullscreen para modo quiosque
    )
    
    # Iniciar com backend GTK explicitamente se estiver em Linux
    gui_backend = "gtk" if sys.platform.startswith("linux") else None
    webview.start(gui=gui_backend)

if __name__ == "__main__":
    start_app()
