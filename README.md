# SmartEmulsion

O projeto SmartEmulsion é um sistema de monitorização e ação corretiva automática direcionado à gestão de emulsão de óleo de corte. Foi desenvolvido no âmbito da Licenciatura em Engenharia Informática da Escola Superior de Tecnologia e Gestão (ESTG) do Politécnico de Leiria. O sistema constitui um *upgrade* direto do projeto anterior, designado "EmulsãoSmart". O seu objetivo central é evoluir de uma monitorização meramente passiva para uma automação ativa que controla o processo de enchimento e reposição da emulsão nas máquinas industriais da empresa parceira Aníbal H. Abrantes (AHA).

## Funcionalidades Principais
* Monitorização analógica do pH da emulsão.
* Leitura contínua da concentração da emulsão.
* Deteção do nível do fluido no tanque de armazenamento.
* Cálculo automático das quantidades exatas de água a introduzir no tanque.
* Cálculo exato das quantidades de óleo a adicionar para assegurar a proporção adequada.
* Controlo ativo de uma bomba injetora de óleo (bomba peristáltica).
* Acionamento de uma eletroválvula no circuito de reposição de água.
* Configuração escalável que permite aos operadores parametrizarem a capacidade do tanque específico de cada máquina.
* Comunicação com a intranet da fábrica através do protocolo HTTP (pedidos GET e PUT).
* Sistema de avisos integrado com alertas para anomalias detetadas nos parâmetros físicos.
* Filtro inteligente do sinal emitido pelos sensores para garantir maior fiabilidade dos dados recolhidos.
* Interface gráfica de utilizador que permite acionar de forma manual a injeção de fluidos.
* Registo persistente do histórico das leituras numa base de dados.

## Hardware e Eletrónica
A infraestrutura física do protótipo é suportada pelos seguintes componentes:
* Microcomputador Raspberry Pi 5 acoplado a um ecrã tátil de 7 polegadas.
* Módulo conversor analógico-digital (ADC) ADS1115 que disponibiliza 16 bits de resolução e comunicação através de barramento I2C.
* Sensor de nível por pressão hidrostática, concebido em aço inoxidável e com saída analógica de 4-20mA.
* Eletroválvula BACOENG de 3/4" que atua de forma normalmente fechada (NC) para proteção anti-inundação (fail-safe).
* Bomba peristáltica Kamoer KKDD-24S18A, selecionada para a dosagem rigorosa de fluidos viscosos.
* Módulos de relé eletromecânico (5V, low-level trigger) instalados para garantir o isolamento galvânico entre os circuitos de controlo lógicos e as cargas de potência.
* Sensores DFRobot para aferição de turbidez, condutividade elétrica e pH.
* Fonte de alimentação industrial Mean Well RS150-24 operando a 24V DC.

## Stack Tecnológica
A arquitetura aplicacional foi desenhada para operar nativamente em modo quiosque, integrando:
* **Backend:** Escrito em Python. Faz a gestão do ciclo de vida, o arranque de *threads* para monitorização e interage fisicamente com a camada de hardware (via biblioteca *gpiozero* e *adafruit-circuitpython-ads1x15*).
* **Persistência de Dados:** Base de dados relacional SQLite local. Gere três tabelas estruturais (*tanks*, *sensor_readings*, *settings*).
* **Frontend / HCI:** Single Page Application construída com HTML5 e CSS3. A estilização recorre à framework utilitária Tailwind CSS. 
* **Renderização:** A biblioteca *pywebview* (versão 6.2.1) estabelece a ponte IPC, exibindo a página Web numa janela nativa sem a dependência de um *browser* independente.
* **API Local:** A micro-framework *bottle* fornece os *endpoints* necessários para suportar os pedidos de rede.

## Integração de Rede
O sistema expõe uma API RESTful formatada em JSON, destinada a alimentar infraestruturas fabris (como ambientes Node-RED, InfluxDB e Grafana). Alguns dos *endpoints* disponibilizados pelo servidor Bottle incluem:
* `GET /api/sensors`: Consulta instantânea de todos os sensores e atuadores.
* `POST /api/control/fill/start`: Executa o algoritmo matemático de mistura e despoleta o enchimento.
* `GET /api/tanks`: Listagem dos parâmetros e geometria de todos os tanques registados.
* `POST /api/email/send`: Gatilho manual para envio imediato de relatório SMTP.

## Autores do Projeto
* Martim Ribeiro (2231018)
* Fábio Nunes (2231014)

Trabalho executado sob a orientação técnica e letiva dos professores Filipe Neves, Paulo Costa e João Galvão (Departamento de Engenharia Eletrotécnica e de Computadores). Conta com o apoio fundamental dos engenheiros João Godinho e João Almeida, representantes da empresa parceira.
