FROM python:3.11-slim

WORKDIR /app

# 1. Сначала копируем файл зависимостей
COPY requirements.txt .

# 2. Автоматически устанавливаем зависимости при сборке образа
RUN pip install --no-cache-dir -r requirements.txt

# 3. Копируем остальной код проекта
COPY . .

# 4. Запуск приложения
CMD ["python", "main.py"]
