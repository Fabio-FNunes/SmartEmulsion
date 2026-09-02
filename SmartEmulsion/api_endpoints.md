# EmulPro API - Endpoints & cURL Examples

Abaixo encontras todos os endpoints REST disponíveis na tua aplicação (com o IP `10.196.7.127` na porta `5000`), bem como exemplos práticos usando `curl`.

---

## 📊 1. Sensores e Monitorização

### Ler Estado Atual (Todos os Sensores)
Retorna o estado instantâneo de todos os sensores, estado da bomba e válvulas.
```bash
curl -X GET http://10.196.7.127:5000/api/sensors
```

---

## 🚰 2. Controlo Manual (Hardware)

### Ligar / Desligar a Bomba
Usa `action=on` ou `action=off`.
```bash
curl -X GET "http://10.196.7.127:5000/api/control/pump?action=on"
```

### Abrir / Fechar a Válvula
Usa `action=on` ou `action=off`.
```bash
curl -X GET "http://10.196.7.127:5000/api/control/valve?action=on"
```

### Ligar / Desligar o Alarme (Buzzer)
```bash
curl -X POST http://10.196.7.127:5000/api/control/buzzer \
     -H "Content-Type: application/json" \
     -d '{"state": true}'
```

---

## 🧪 3. Gestão de Tanques

### Listar Todos os Tanques
```bash
curl -X GET http://10.196.7.127:5000/api/tanks
```

### Criar um Novo Tanque
*Nota: Não inclua o campo `id` para criar um tanque novo.*
```bash
curl -X POST http://10.196.7.127:5000/api/tanks \
     -H "Content-Type: application/json" \
     -d '{
           "name": "Tanque Industrial",
           "capacity": 1000.0,
           "height": 200.0
         }'
```

### Atualizar um Tanque Existente
*Basta incluir o `id` correspondente ao tanque que queres atualizar.*
```bash
curl -X POST http://10.196.7.127:5000/api/tanks \
     -H "Content-Type: application/json" \
     -d '{
           "id": 1,
           "name": "Tanque Industrial Modificado",
           "capacity": 1500.0,
           "height": 200.0
         }'
```

### Apagar um Tanque
*Substitui `1` pelo ID do tanque.*
```bash
curl -X DELETE http://10.196.7.127:5000/api/tanks/1
```

### Calibrar um Tanque
Define a altura real atual para calibrar o sensor ultrassónico de um determinado tanque.
```bash
curl -X POST http://10.196.7.127:5000/api/tanks/calibrate \
     -H "Content-Type: application/json" \
     -d '{
           "tank_id": 1,
           "current_level": 45.5
         }'
```

### Sincronizar (Mudar o tanque ativo em tempo real)
Faz com que a aplicação mude as suas medições de referência para este tanque.
```bash
curl -X POST http://10.196.7.127:5000/api/tanks/sync \
     -H "Content-Type: application/json" \
     -d '{
           "id": 1,
           "name": "Tanque Industrial",
           "capacity": 1000.0,
           "height": 200.0,
           "calibration_factor": 1.0
         }'
```

---

## 📈 4. Histórico e Estatísticas de Tanques

### Histórico Simples (Últimas leituras do Tanque 1)
```bash
curl -X GET http://10.196.7.127:5000/api/tanks/1/history
```

### Histórico Agrupado V2
Aceita o parâmetro de query `period` (`day`, `week`, `month`).
```bash
curl -X GET "http://10.196.7.127:5000/api/tanks/1/history_v2?period=day"
```

### Estatísticas de Abastecimento
Soma dos litros de água e óleo nos abastecimentos, num dado `period`.
```bash
curl -X GET "http://10.196.7.127:5000/api/tanks/1/supply_stats?period=week"
```

### Histórico Detalhado de Abastecimentos (Refills)
```bash
curl -X GET http://10.196.7.127:5000/api/tanks/1/refill_history
```

### Resumo Semanal
Mínimos, médias e máximos de pH, óleo e nível agrupados por dia.
```bash
curl -X GET http://10.196.7.127:5000/api/tanks/1/weekly
```

---

## ⚙️ 5. Processo Automático de Enchimento

### Iniciar Processo de Enchimento
Calcula e inicia a mistura para atingir a percentagem de enchimento pretendida com a percentagem de óleo pretendida.
```bash
curl -X POST http://10.196.7.127:5000/api/control/fill/start \
     -H "Content-Type: application/json" \
     -d '{
           "target_level_percent": 80.0,
           "target_oil_percent": 5.0
         }'
```

### Cancelar Enchimento em Curso
```bash
curl -X POST http://10.196.7.127:5000/api/control/fill/cancel
```

---

## 📧 6. Notificações e E-mails

### Consultar Configuração de Email Atual
```bash
curl -X GET http://10.196.7.127:5000/api/email/schedule
```

### Guardar/Atualizar Configuração de Alarme de Email Diário
```bash
curl -X POST http://10.196.7.127:5000/api/email/schedule \
     -H "Content-Type: application/json" \
     -d '{
           "time_str": "19:00",
           "recipient": "admin@emulpro.com",
           "sender_email": "f.f.nunes2005@gmail.com",
           "sender_password": "kgdddkiqsozauqxb"
         }'
```

### Enviar Email de Relatório Agora (Trigger Manual)
Envia o relatório com os dados instantâneos (ou média do dia) de imediato.
```bash
curl -X POST http://10.196.7.127:5000/api/email/send \
     -H "Content-Type: application/json" \
     -d '{"recipient_email": "admin@emulpro.com"}'
```
