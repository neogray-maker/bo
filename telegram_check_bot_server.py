#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Серверная версия Telegram Check Bot
Работает на VPS/хостинге 24/7
"""

import asyncio
import re
import logging
import os
import json
from datetime import datetime
from telethon import TelegramClient, events
from telethon.tl.functions.channels import JoinChannelRequest
from flask import Flask, request, jsonify, render_template_string

app = Flask(__name__)

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Конфигурация из переменных окружения
API_ID = int(os.getenv('API_ID', '21502665'))
API_HASH = os.getenv('API_HASH', 'a8c8544fd0f02965cb23b86ea6bd5599')
PHONE_NUMBER = os.getenv('PHONE_NUMBER', '+1 828 893 5130')
CHANNEL_ID = int(os.getenv('CHANNEL_ID', '-1003034671650'))

# Создание клиента Telegram
client = TelegramClient('session', API_ID, API_HASH)

# Регулярное выражение для поиска ссылок на чеки
check_regex = re.compile(
    r't\.me/(CryptoBot|send|tonRocketBot|CryptoTestnetBot|wallet|xrocket|xJetSwapBot)\?start=([A-Za-z0-9_-]{10,})'
)

# Множество для отслеживания активированных чеков
activated_checks = set()

# Статистика
bot_stats = {
    'total_checks': 0,
    'activated_checks': 0,
    'start_time': datetime.now().isoformat(),
    'status': 'stopped'
}

async def activate_check(bot_username, check_code):
    """Активация чека через бота"""
    try:
        logger.info(f"Попытка активации чека: {check_code} через {bot_username}")
        
        # Отправляем команду активации
        await client.send_message(bot_username, f'/start {check_code}')
        
        # Добавляем в список активированных
        activated_checks.add(check_code)
        bot_stats['activated_checks'] = len(activated_checks)
        bot_stats['total_checks'] += 1
        
        # Отправляем уведомление в канал
        message = f'✅ Чек активирован: {check_code}\nВсего активировано: {len(activated_checks)}'
        await client.send_message(CHANNEL_ID, message)
        
        logger.info(f"Чек {check_code} успешно активирован")
        
    except Exception as e:
        logger.error(f"Ошибка при активации чека {check_code}: {e}")

@client.on(events.NewMessage(incoming=True))
async def handler(event):
    """Обработчик входящих сообщений"""
    if not event.text:
        return

    logger.info(f"Получено сообщение: {event.text[:100]}...")

    # Поиск ссылок в тексте сообщения
    for match in check_regex.finditer(event.raw_text):
        bot_username, check_code = match.groups()
        if check_code not in activated_checks:
            await activate_check(bot_username, check_code)

    # Поиск ссылок в кнопках сообщения
    if event.buttons:
        for row in event.buttons:
            for button in row:
                url = getattr(button, 'url', '')
                if url:
                    match = check_regex.search(url)
                    if match:
                        bot_username, check_code = match.groups()
                        if check_code not in activated_checks:
                            await activate_check(bot_username, check_code)

async def start_bot():
    """Запуск бота"""
    try:
        logger.info("Запуск Telegram бота...")
        bot_stats['status'] = 'starting'
        
        # Запуск клиента
        await client.start(PHONE_NUMBER)
        logger.info("Бот успешно запущен и готов к работе")
        bot_stats['status'] = 'running'
        
        # Отправка уведомления о запуске
        await client.send_message(CHANNEL_ID, "🤖 Бот запущен и готов к активации чеков")
        
        # Запуск до отключения
        await client.run_until_disconnected()
        
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
        bot_stats['status'] = 'error'
    finally:
        await client.disconnect()
        bot_stats['status'] = 'stopped'

# HTML шаблон для веб-интерфейса
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>�� Telegram Check Bot</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; background: #1a1a1a; color: white; }
        .status { padding: 20px; border-radius: 10px; margin: 20px 0; }
        .running { background: #2d5a2d; border: 1px solid #4a7c4a; }
        .stopped { background: #5a2d2d; border: 1px solid #7c4a4a; }
        .error { background: #5a5a2d; border: 1px solid #7c7c4a; }
        button { padding: 15px 30px; font-size: 16px; margin: 10px; border: none; border-radius: 5px; cursor: pointer; }
        .start-btn { background: #28a745; color: white; }
        .stop-btn { background: #dc3545; color: white; }
        .stats { background: #2a2a2a; padding: 15px; border-radius: 5px; margin: 20px 0; }
        h1 { color: #00ff00; text-align: center; }
        .check-item { background: #333; padding: 10px; margin: 5px 0; border-radius: 5px; }
    </style>
</head>
<body>
    <h1>�� Telegram Check Bot Control Panel</h1>
    
    <div id="status" class="status stopped">
        <h3>�� Статус: <span id="bot-status">Остановлен</span></h3>
        <p>⏰ Время запуска: <span id="start-time">-</span></p>
    </div>
    
    <div class="stats">
        <h3>📈 Статистика:</h3>
        <p>�� Всего чеков: <span id="total-checks">0</span></p>
        <p>✅ Активировано: <span id="activated-checks">0</span></p>
        <p>📋 Уникальных чеков: <span id="unique-checks">0</span></p>
    </div>
    
    <div style="text-align: center;">
        <button class="start-btn" onclick="startBot()">🚀 Запустить бота</button>
        <button class="stop-btn" onclick="stopBot()">🛑 Остановить бота</button>
        <button onclick="updateStatus()">🔄 Обновить статус</button>
    </div>
    
    <div class="stats">
        <h3>📋 Последние активированные чеки:</h3>
        <div id="recent-checks">Загрузка...</div>
    </div>
    
    <script>
        function updateStatus() {
            fetch('/api/status')
                .then(response => response.json())
                .then(data => {
                    document.getElementById('bot-status').textContent = 
                        data.status === 'running' ? 'Работает' : 
                        data.status === 'error' ? 'Ошибка' : 'Остановлен';
                    
                    document.getElementById('start-time').textContent = 
                        new Date(data.start_time).toLocaleString();
                    
                    document.getElementById('total-checks').textContent = data.total_checks;
                    document.getElementById('activated-checks').textContent = data.activated_checks;
                    document.getElementById('unique-checks').textContent = data.unique_checks;
                    
                    const statusDiv = document.getElementById('status');
                    statusDiv.className = 'status ' + 
                        (data.status === 'running' ? 'running' : 
                         data.status === 'error' ? 'error' : 'stopped');
                    
                    // Показываем последние чеки
                    const recentDiv = document.getElementById('recent-checks');
                    if (data.recent_checks && data.recent_checks.length > 0) {
                        recentDiv.innerHTML = data.recent_checks.slice(0, 10).map(check => 
                            `<div class="check-item">✅ ${check}</div>`
                        ).join('');
                    } else {
                        recentDiv.innerHTML = 'Нет активированных чеков';
                    }
                });
        }
        
        function startBot() {
            fetch('/api/start', {method: 'POST'})
                .then(response => response.json())
                .then(data => {
                    alert(data.message);
                    updateStatus();
                });
        }
        
        function stopBot() {
            fetch('/api/stop', {method: 'POST'})
                .then(response => response.json())
                .then(data => {
                    alert(data.message);
                    updateStatus();
                });
        }
        
        // Автообновление каждые 5 секунд
        setInterval(updateStatus, 5000);
        updateStatus();
    </script>
</body>
</html>
"""

# API маршруты
@app.route('/')
def index():
    """Главная страница с веб-интерфейсом"""
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/status')
def api_status():
    """API для получения статуса бота"""
    return jsonify({
        'status': bot_stats['status'],
        'total_checks': bot_stats['total_checks'],
        'activated_checks': bot_stats['activated_checks'],
        'unique_checks': len(activated_checks),
        'start_time': bot_stats['start_time'],
        'recent_checks': list(activated_checks)[-20:]  # Последние 20 чеков
    })

@app.route('/api/start', methods=['POST'])
def api_start():
    """API для запуска бота"""
    if bot_stats['status'] == 'running':
        return jsonify({'success': False, 'message': 'Бот уже работает!'})
    
    # Запускаем бота в отдельном потоке
    import threading
    thread = threading.Thread(target=lambda: asyncio.run(start_bot()))
    thread.daemon = True
    thread.start()
    
    return jsonify({'success': True, 'message': 'Бот запущен!'})

@app.route('/api/stop', methods=['POST'])
def api_stop():
    """API для остановки бота"""
    if bot_stats['status'] != 'running':
        return jsonify({'success': False, 'message': 'Бот не запущен!'})
    
    # Останавливаем клиента
    asyncio.create_task(client.disconnect())
    bot_stats['status'] = 'stopping'
    
    return jsonify({'success': True, 'message': 'Команда остановки отправлена!'})

@app.route('/api/stats')
def api_stats():
    """API для получения статистики"""
    return jsonify({
        'total_checks': bot_stats['total_checks'],
        'activated_checks': bot_stats['activated_checks'],
        'unique_checks': len(activated_checks),
        'uptime': str(datetime.now() - datetime.fromisoformat(bot_stats['start_time'])),
        'status': bot_stats['status']
    })

if __name__ == '__main__':
    logger.info("🚀 Запускаю Telegram Check Bot Server...")
    
    # Запускаем Flask сервер
    app.run(host='0.0.0.0', port=5000, debug=False)
