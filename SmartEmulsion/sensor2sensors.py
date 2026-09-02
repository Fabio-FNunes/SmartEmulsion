import time
import sys

# Coeficientes da Calibração (Água da Torneira)
BETA_0 = -0.086612135  # Interseção
BETA_1 = 0.005758619   # Multiplicador da Condutividade
BETA_2 = -0.011296349  # Multiplicador da Turbidez

def calcular_concentracao_oleo(leitura_condutividade: float, leitura_turbidez: float) -> float:
    """
    Calcula a concentração de óleo com base na regressão linear múltipla.
    """
    # Aplicação da fórmula da Regressão Linear Múltipla
    concentracao = (BETA_1 * leitura_condutividade) + (BETA_2 * leitura_turbidez) + BETA_0
    
    # Filtro de segurança (Clamp) para ruído dos sensores
    # Garante que o sistema nunca devolve concentrações negativas ou acima do limite do tanque
    if concentracao < 0.0:
        concentracao = 0.0
    elif concentracao > 15.0:
        concentracao = 15.0
        
    return concentracao

if __name__ == "__main__":
    try:
        from adafruit_extended_bus import ExtendedI2C as I2C
        import adafruit_ads1x15.ads1115 as ADS
        from adafruit_ads1x15.analog_in import AnalogIn
        
        print("A iniciar ligação aos sensores reais (ADS1115)...")
        i2c = I2C(3)
        ads = ADS.ADS1115(i2c, address=0x48)
        ads.gain = 1
        
        # Canal A1 - Condutividade; Canal A2 - Turbidez
        chan_cond = AnalogIn(ads, 1)
        chan_turb = AnalogIn(ads, 2)

        print("A ler sensores em tempo real. Pressione Ctrl+C para sair.\n")
        
        while True:
            # Lê os valores brutos do ADS
            v_cond = chan_cond.voltage
            v_turb = chan_turb.voltage
            
            # Cálculos dos valores reais de condutividade e turbidez (conforme fórmulas base do projeto)
            cond_val = max(0, 7205.5 * v_cond - 442.4)
            turb_val = max(0.0, min(400.0, -114.286 * v_turb + 457.144))
            
            # Usa a fórmula de regressão linear múltipla para calcular a concentração
            concentracao = calcular_concentracao_oleo(cond_val, turb_val)
            
            # Atualiza o output em tempo real na mesma linha
            sys.stdout.write('\r' + ' ' * 120 + '\r')
            sys.stdout.write(f"Cond: {cond_val:.1f} | Turb: {turb_val:.1f} | V_Cond: {v_cond:.3f}V | V_Turb: {v_turb:.3f}V -> C: {concentracao:.2f}%")
            sys.stdout.flush()
            
            time.sleep(1)

    except KeyboardInterrupt:
        print("\nLeitura cancelada pelo utilizador.")
        sys.exit(0)
    except ImportError:
        print("Erro: Bibliotecas de hardware não detetadas. (Estás a correr fora do Raspberry Pi?)")
        
        # Simulação simples para testar a lógica sem hardware
        dados_teste = [
            {"condutividade": 1059.0, "turbidez": 50.2}, 
            {"condutividade": 1924.6, "turbidez": 356.0}, 
            {"condutividade": 3000.9, "turbidez": 342.3}, 
            {"condutividade": 4043.9, "turbidez": 370.6}, 
        ]
        print("--- Validação do Algoritmo (Simulação) ---")
        for dados in dados_teste:
            cond = dados["condutividade"]
            turb = dados["turbidez"]
            resultado = calcular_concentracao_oleo(cond, turb)
            print(f"Condutividade: {cond:.1f} | Turbidez: {turb:.1f} -> Calculada: {resultado:.2f}%")
    except Exception as e:
        print(f"\nOcorreu um erro: {e}")
