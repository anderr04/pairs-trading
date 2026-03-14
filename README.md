# Pairs Trading Divergence Bot

Este repositorio contiene un bot automatizado para ejecutar una estrategia de *Pairs Trading* (Cointegración Estadística) diseñado para operar 24/7 en una máquina virtual (VM).

## Estructura del Proyecto

- `config.yaml`: Parámetros de trading, capital, umbrales de Z-Score y configuración general.
- `pairs.csv`: Lista de pares a evaluar (formato CSV con columnas `stock1` y `stock2`).
- `data_manager.py`: Descarga y procesamiento de datos usando `yfinance`.
- `analyzer.py`: Análisis matemático (Cointegración Engle-Granger, ADF Test, Z-Score).
- `strategy.py`: Lógica de señales (Long/Short/Close) basada en los umbrales de Z-Score.
- `execution.py`: Simula la ejecución (Paper Trading) aplicando comisiones y *slippage*.
- `main.py`: Loop principal y orquestador del bot.
- `trading_bot.service`: Archivo de configuración para Systemd (Linux) para ejecución ininterrumpida.

## Requisitos
- Python 3.9+
- Dependencias (ver `requirements.txt`)

## Despliegue en una VM (Linux / Ubuntu)

Sigue estos pasos para desplegar el bot en tu VM en la nube:

1. **Clonar el repositorio:**
   ```bash
   git clone <URL_DE_TU_REPOSITORIO>
   cd pairs_trading_bot
   ```

2. **Instalar dependencias:**
   ```bash
   sudo apt update
   sudo apt install python3-pip python3-venv -y
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Configurar el servicio Systemd (para que corra 24/7):**
   Edita el archivo `pairs_trading_bot.service` y asegúrate de que las rutas (como `WorkingDirectory` y `ExecStart`) coincidan con la ubicación donde clonaste el repo. Por defecto apunta a `/opt/pairs_trading_bot`.
   
   Copia el archivo al directorio de systemd:
   ```bash
   sudo cp pairs_trading_bot.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable pairs_trading_bot.service
   sudo systemctl start pairs_trading_bot.service
   ```

4. **Verificar los logs:**
   ```bash
   sudo journalctl -u pairs_trading_bot.service -f
   ```
   También puedes ver el archivo local de logs configurado en `config.yaml` (`trading_bot.log`).
