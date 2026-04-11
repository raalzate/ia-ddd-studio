# 1. Imagen base: Python 3.11 slim (no local model binaries needed)
FROM python:3.11-slim

# 2. Variable de entorno para evitar problemas de buffering de logs
ENV PYTHONUNBUFFERED=1

# 3. Establecer el directorio de trabajo dentro del contenedor
WORKDIR /app

# 4. Copiar el archivo de requisitos e instalar las bibliotecas de Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copiar el código fuente
COPY src/ src/
COPY static/ static/
COPY main.py .

# 6. Exponer el puerto por defecto de Streamlit
EXPOSE 8501

# 7. Ejecutar la aplicación Streamlit
CMD ["streamlit", "run", "main.py", "--server.port=8501", "--server.address=0.0.0.0"]