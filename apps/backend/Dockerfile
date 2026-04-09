# Usa un'immagine Python ufficiale leggera
FROM python:3.10-slim

# Imposta la cartella di lavoro nel container
WORKDIR /app

# Installa FFmpeg (necessario per l'elaborazione video/audio)
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

# Copia il file dei requisiti e installa le dipendenze
COPY requirements.txt .

# Poiché il livello gratuito di HF usa la CPU, forziamo l'installazione di PyTorch per CPU
RUN pip install torch==2.5.1 torchvision==0.20.1 torchaudio==2.5.1 --index-url https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir -r requirements.txt

# Copia tutto il resto del codice del backend
COPY . .

# Hugging Face Spaces espone di default la porta 7860
EXPOSE 7860

# Comando per avviare il server FastAPI sulla porta corretta
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]