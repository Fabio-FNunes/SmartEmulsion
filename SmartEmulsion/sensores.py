import time
import random
import threading
from database import save_reading, init_db, save_refill
import os
import sys
import math
from sensor2sensors import calcular_concentracao_oleo

HAS_HARDWARE = False
try:
    from gpiozero import OutputDevice
    import board
    import busio
    from adafruit_extended_bus import ExtendedI2C as I2C
    import adafruit_ads1x15.ads1115 as ADS
    from adafruit_ads1x15.analog_in import AnalogIn
    HAS_HARDWARE = True
    print("[SISTEMA] Hardware detetado.")
except Exception as e:
    HAS_HARDWARE = False
    print(f"[AVISO] MOCK: {e}")
    class OutputDevice:
        def __init__(self, pin, active_high=True, initial_value=False):
            self.pin = pin
            self.value = 1 if initial_value else 0
        def on(self): self.value = 1
        def off(self): self.value = 0

class SensorManager:
    def __init__(self):
        self.running = False
        self.last_valid_v_level = None
        self.last_valid_v_ph = None
        self.ph_history = []
        self.current_data = {
            "ph": 7.0, "oil": 0.0, "level": 0.0, "raw_level": 0.0, "level_percent": 0.0,
            "conductivity": 0.0, "turbidity": 0.0, "tank_id": None,
            "tank_name": "Tanque", "capacity": 500.0, "height": 500.0,
            "valve_open": False, "pump_running": False, "fill_active": False
        }
        
        self.PIN_VALVE = 24 
        self.PIN_PUMP = 16
        self.PIN_BUZZER = 23
        # Fluxo da bomba: 300 ml em 23.7 seg (32.6 - 8.9 da mangueira) = 12.658 ml/seg = 0.012658 L/seg
        self.OIL_PUMP_RATE_L_SEC = 0.012658

        # CÓPIA EXATA DOS TEUS SCRIPTS DE TESTE (Lógica Invertida pelo Hardware)
        if HAS_HARDWARE:
            self.valvula_hw = OutputDevice(self.PIN_VALVE, active_high=False, initial_value=False)
            self.bomba_hw = OutputDevice(self.PIN_PUMP, active_high=False, initial_value=False)
            self.buzzer_hw = OutputDevice(self.PIN_BUZZER, active_high=True, initial_value=False)
        else:
            self.valvula_hw = OutputDevice(self.PIN_VALVE)
            self.bomba_hw = OutputDevice(self.PIN_PUMP)
            self.buzzer_hw = OutputDevice(self.PIN_BUZZER)

        # Garantia que iniciam desligados 
        # (O hardware revelou que .on() é que FECHA/DESLIGA o relé)
        self.valvula_hw.on()
        self.bomba_hw.on()

        self.ads = None
        self.ads2 = None
        if HAS_HARDWARE:
            try:
                i2c = I2C(3)
                self.ads = ADS.ADS1115(i2c, address=0x48)
                self.ads.gain = 1
                print("[SISTEMA] ADS1 (0x48) detetado.")
            except: print("[ERRO] ADS1115 (0x48) não encontrado.")
            
            try:
                i2c = I2C(3)
                self.ads2 = ADS.ADS1115(i2c, address=0x49)
                self.ads2.gain = 1
                print("[SISTEMA] ADS2 (0x49) detetado.")
            except: 
                print("[AVISO] ADS2 (0x49) não encontrado. Usando apenas ADS1.")
                self.ads2 = None
        
        self.lock = threading.Lock()
        self.cancel_fill_flag = False

    def read_sensors(self):
        with self.lock:
            if HAS_HARDWARE and self.ads:
                try:
                    # pH: Canal A0 (Conforme projeto passado)
                    raw_v_ph = AnalogIn(self.ads, 0).voltage
                    v_ph = raw_v_ph  # Filtro de saltos removido (causava bloqueio permanente)
                    self.last_valid_v_ph = v_ph
                    
                    raw_ph = -6.16 * v_ph + 16.07
                    
                    # Filtro de Média Móvel (15 amostras) para o pH
                    if not hasattr(self, 'ph_history'):
                        self.ph_history = []
                    self.ph_history.append(raw_ph)
                    if len(self.ph_history) > 15:
                        self.ph_history.pop(0)
                        
                    avg_ph = sum(self.ph_history) / len(self.ph_history)
                    self.current_data["ph"] = round(avg_ph, 2)
                    
                    # Condutividade: Canal A1 (Conforme projeto passado)
                    v_cond = AnalogIn(self.ads, 1).voltage
                    self.current_data["conductivity"] = round(max(0, 7205.5 * v_cond - 442.4), 1)
                    
                    # Turbidez: Canal A2 (Conforme projeto passado)
                    v_turb = AnalogIn(self.ads, 2).voltage
                    self.current_data["turbidity"] = round(max(0.0, min(400.0, -114.286 * v_turb + 457.144)), 1)
                    
                    # Nível: Canal A3 (Dinâmico com base na altura do tanque)
                    raw_v_level = AnalogIn(self.ads, 3).voltage
                    v_level = raw_v_level  # Filtro removido (impedia o tanque de registar descidas bruscas como 0cm)
                    self.last_valid_v_level = v_level
                    
                    corrente = (v_level / 110.0) * 1000.0
                    
                    # Aumentamos o corte para 4.4mA para garantir 0% absoluto no ar
                    if corrente > 4.4:
                        # 1. Usamos 4.35mA como base (acima do ruído do ar)
                        # Escala recalculada para 4.35mA - 20mA
                        perc_sensor = (corrente - 4.35) / (20.0 - 4.35)
                        altura_real_lida_cm = max(0, perc_sensor * 500.0)
                        
                        # 2. Aplicar fator de calibração (AGORA É UM OFFSET)
                        # Assumimos 0.0 se não houver fator (ou mantemos perto do original se for o multiplier 1.0 de antigamente, somar 1cm não é crítico)
                        factor = self.current_data.get("calibration_factor", 0.0)
                        if factor == 1.0: # Compatibilidade com base de dados antiga
                            factor = 0.0
                        
                        altura_ajustada = max(0, altura_real_lida_cm + factor)
                        
                        # 3. Obter definições do tanque
                        tank_h = self.current_data.get("height") or 500.0
                        tank_cap = self.current_data.get("capacity") or 500.0
                        
                        # 4. Calcular volume final
                        vol_litros = (altura_ajustada / tank_h) * tank_cap
                        raw_level = min(vol_litros, tank_cap)
                    else: 
                        raw_level = 0.0

                    # Filtro de Média Móvel (10 amostras) para o Nível
                    if not hasattr(self, 'level_history'):
                        self.level_history = []
                    self.level_history.append(raw_level)
                    if len(self.level_history) > 10:
                        self.level_history.pop(0)
                        
                    avg_level = sum(self.level_history) / len(self.level_history)
                    self.current_data["level"] = round(avg_level, 1)
                    self.current_data["raw_level"] = round(raw_level, 1)

                    # Cálculo da Concentração de Óleo (%) via regressão linear múltipla (sensor2sensors)
                    self.current_data["oil"] = round(calcular_concentracao_oleo(self.current_data["conductivity"], self.current_data["turbidity"]), 1)
                except Exception as e:
                    print(f"[ERRO] Leitura sensores: {e}")
            
            capacity = self.current_data.get("capacity", 500.0)
            if capacity and capacity > 0:
                self.current_data["level_percent"] = round((self.current_data["level"] / capacity) * 100, 1)
            else:
                self.current_data["level_percent"] = 0.0
                
            self.current_data["ph"] = max(0, min(14, self.current_data.get("ph", 7.0)))
        return self.current_data

    def calculate_oil(self, turbidity, conductivity):
        """Calcula a concentração de óleo usando IDW (Inverse Distance Weighting)"""
        pontos = [
            (178.4, 216.0, 0.0),
            (339.8, 845.6, 3.0),
            (50.2, 1059.0, 5.0),
            (267.4, 1727.4, 6.0),
            (356.0, 1924.6, 7.0),
            (393.6, 2216.4, 8.0),
            (342.3, 3000.9, 11.0),
            (303.4, 2726.2, 13.0),
            (316.0, 3417.0, 14.0),
            (370.6, 4043.9, 15.0),
            (282.0, 4206.9, 16.0),
            (352.6, 4937.4, 18.0),
            (400.0, 4982.4, 20.0),
        ]
        
        max_turbidez = 400.0
        max_condutividade = 12000.0
        turbidez_norm = turbidity / max_turbidez
        condutividade_norm = conductivity / max_condutividade
        
        distancias = []
        for ponto_turbidez, ponto_condutividade, ponto_concentracao in pontos:
            turbidez_ponto_norm = ponto_turbidez / max_turbidez
            condutividade_ponto_norm = ponto_condutividade / max_condutividade
            distancia = math.sqrt((turbidez_norm - turbidez_ponto_norm) ** 2 + 
                                 (condutividade_norm - condutividade_ponto_norm) ** 2)
            distancias.append((distancia, ponto_concentracao))
            
        distancias.sort(key=lambda x: x[0])
        d1, c1 = distancias[0]
        d2, c2 = distancias[1]
        
        if d1 == 0:
            return round(c1, 1)
        
        peso1 = 1 / d1
        peso2 = 1 / d2
        concentracao = (peso1 * c1 + peso2 * c2) / (peso1 + peso2)
        
        return round(max(0.0, min(concentracao, 100.0)), 1)

    def start_monitoring(self, interval=5):
        self.running = True
        def loop():
            while self.running:
                data = self.read_sensors()
                if data.get("tank_id"):
                    try:
                        save_reading(data["tank_id"], data["ph"], data["oil"], data["level_percent"], data.get("conductivity", 0), data.get("turbidity", 0))
                    except: pass
                time.sleep(interval)
        threading.Thread(target=loop, daemon=True).start()

    def process_fill(self, target_vol, oil_to_add, target_oil_pct):
        def filling_sequence():
            with self.lock: 
                self.current_data["fill_active"] = True
                self.cancel_fill_flag = False
            
            try:
                agua_target = target_vol - oil_to_add
                initial_level = self.current_data["raw_level"]

                # Iniciar Bomba de Óleo numa Thread paralela (para arrancar logo e misturar)
                def pump_oil_task():
                    if oil_to_add > 0 and not self.cancel_fill_flag:
                        print(f"[AÇÃO] LIGAR BOMBA ({oil_to_add}L)")
                        self.bomba_hw.off() # .off() liga
                        self.current_data["pump_running"] = True
                        
                        start_pump = time.time()
                        while (time.time() - start_pump) < ((oil_to_add / self.OIL_PUMP_RATE_L_SEC) + 8.9):
                            if self.cancel_fill_flag: break
                            time.sleep(0.05)
                            
                        print("[AÇÃO] DESLIGAR BOMBA")
                        self.bomba_hw.on() # .on() desliga
                        self.current_data["pump_running"] = False

                oil_thread = threading.Thread(target=pump_oil_task, daemon=True)
                oil_thread.start()

                # Válvula de Água (Corre no loop principal)
                if agua_target > self.current_data["raw_level"]:
                    print(f"[AÇÃO] ABRIR VÁLVULA (Alvo Água: {agua_target}L)")
                    self.valvula_hw.off() # .off() abre
                    self.current_data["valve_open"] = True
                    
                    # Se estiver em MOCK (dry test sem sensor), simular o enchimento rapidamente
                    # Se tiver hardware mas o nível não subir (teste a seco), vai ficar aqui à espera.
                    while self.current_data["raw_level"] < agua_target and not self.cancel_fill_flag:
                        self.read_sensors()
                        # Sleep 1s, mas verifica a flag de cancelamento a cada 0.1s para parar rápido
                        for _ in range(10):
                            if self.cancel_fill_flag: break
                            time.sleep(0.1)
                        if not HAS_HARDWARE:
                            self.current_data["level"] += 5.0
                            self.current_data["raw_level"] += 5.0
                    
                    print("[AÇÃO] FECHAR VÁLVULA")
                    self.valvula_hw.on() # .on() fecha
                    self.current_data["valve_open"] = False

                # Esperar que o óleo termine caso a água seja muito rápida
                oil_thread.join()

                # SALVAR REGISTO DE ABASTECIMENTO
                if not self.cancel_fill_flag and self.current_data["tank_id"]:
                    actual_water_added = max(0, self.current_data["raw_level"] - initial_level)
                    save_refill(self.current_data["tank_id"], actual_water_added, oil_to_add)
                    print(f"[DB] Abastecimento salvo: {actual_water_added}L água, {oil_to_add}L óleo")

            finally:
                # Segurança Absoluta
                self.valvula_hw.on()
                self.bomba_hw.on()
                with self.lock:
                    self.current_data["fill_active"] = False
                    self.current_data["valve_open"] = False
                    self.current_data["pump_running"] = False

        threading.Thread(target=filling_sequence, daemon=True).start()

    def cancel_fill(self): self.cancel_fill_flag = True

    def _buzzer_loop(self):
        while getattr(self, 'buzzer_active', False):
            self.buzzer_hw.on()
            time.sleep(0.3)
            if getattr(self, 'buzzer_active', False):
                self.buzzer_hw.off()
                time.sleep(0.3)
        self.buzzer_hw.off()

    def set_buzzer(self, state):
        if state:
            if not getattr(self, 'buzzer_active', False):
                self.buzzer_active = True
                threading.Thread(target=self._buzzer_loop, daemon=True).start()
        else:
            self.buzzer_active = False
            self.buzzer_hw.off()

sensor_manager = SensorManager()
