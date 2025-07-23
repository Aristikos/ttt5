import speech_recognition as sr
import json
import os
import nltk
from nltk.sentiment import SentimentIntensityAnalyzer
from datetime import datetime
import random
import re
import time
import sys

# Инициализация NLTK
nltk.download('vader_lexicon', quiet=True)
nltk.download('punkt', quiet=True)
sia = SentimentIntensityAnalyzer()

# Конфигурация программы
LOG_FILE = "thoughts_log.json"
MAX_ATTEMPTS = 3
RECORD_TIMEOUT = 5
PHRASE_LIMIT = 15

# Базовая модерация
BANNED_WORDS = ["ненависть", "презираю", "убей", "суицид", "насилие", "терроризм"]

# Цитаты для разных настроений
QUOTES = {
    "позитив": [
        "Единственный способ делать великие дела – любить то, что делаешь. – Стив Джобс",
        "Верьте, что вы можете, и вы уже на полпути. – Теодор Рузвельт",
        "Успех — это способность идти от неудачи к неудаче, не теряя энтузиазма. – Уинстон Черчилль"
    ],
    "негатив": [
        "Трудности готовят обычных людей к необычной судьбе. – К.С. Льюис",
        "Самая темная ночь предшествует рассвету. – Томас Фуллер",
        "Иногда нужно пройти через плохое, чтобы добраться до хорошего. – Неизвестно"
    ],
    "нейтрально": [
        "Спокойствие – величайшее проявление силы. – Неизвестно",
        "Жизнь — это то, что происходит, пока мы строим другие планы. – Джон Леннон",
        "Не беспокойся о том, что идет не так. Беспокойся о том, что ты можешь сделать правильно. – Неизвестно"
    ]
}

def show_animation(message, duration=1.5):
    """Показывает анимацию с сообщением"""
    for _ in range(3):
        for char in ['�', '⡆', '⠇', '⠋', '⠙', '⠸', '⢰', '⣠', '⣄', '⡆']:
            sys.stdout.write(f'\r{char} {message}')
            sys.stdout.flush()
            time.sleep(0.05)
    sys.stdout.write('\r' + ' ' * (len(message) + 2) + '\r')
    sys.stdout.flush()

def record_and_recognize():
    """Записывает и распознает речь"""
    recognizer = sr.Recognizer()
    
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            with sr.Microphone() as source:
                print(f"\n{'='*40}")
                print(f"🎤 ПОПЫТКА {attempt}/{MAX_ATTEMPTS}: Говорите после сигнала...")
                
                # Автоматическая калибровка шума
                recognizer.adjust_for_ambient_noise(source, duration=0.8)
                print("🔊 Готово! Слушаю...", end='', flush=True)
                
                # Запись с визуальной индикацией
                show_animation("Запись...")
                
                audio = recognizer.listen(
                    source, 
                    timeout=RECORD_TIMEOUT, 
                    phrase_time_limit=PHRASE_LIMIT
                )
                
                show_animation("Обработка...")
                text = recognizer.recognize_google(audio, language="ru-RU")
                
                print(f"\n✅ УСПЕШНО: {text}")
                return text
                
        except sr.WaitTimeoutError:
            print("\n⏳ Время ожидания истекло. Пожалуйста, говорите, когда увидите сигнал.")
        except sr.UnknownValueError:
            print("\n🔇 Речь не распознана. Пожалуйста, говорите четче и громче.")
        except Exception as e:
            print(f"\n❌ Ошибка: {str(e)}")
    
    print("\n⚠️ Не удалось распознать речь после нескольких попыток")
    return None

def moderate_text(text):
    """Проверка на запрещенные слова с использованием регулярных выражений"""
    text_lower = text.lower()
    pattern = r'\b(' + '|'.join(BANNED_WORDS) + r')\b'
    return bool(re.search(pattern, text_lower))

def analyze_sentiment(text):
    """Анализирует тональность текста с помощью NLTK с русской адаптацией"""
    # Добавляем русскоязычную лексику
    custom_lexicon = {
        'хороший': 2.0, 'отлично': 3.0, 'прекрасно': 3.0, 'люблю': 3.0,
        'рад': 2.5, 'счастлив': 3.0, 'восторг': 3.5, 'восхитительно': 3.0,
        'плохой': -2.0, 'ужасно': -3.0, 'ненавижу': -3.0, 'грустно': -2.0,
        'разочарован': -2.5, 'злой': -2.0, 'устал': -1.5
    }
    
    # Обновляем лексикон анализатора
    sia.lexicon.update(custom_lexicon)
    
    # Анализ текста
    score = sia.polarity_scores(text)['compound']
    
    if score >= 0.1:
        return "позитив"
    elif score <= -0.1:
        return "негатив"
    else:
        return "нейтрально"

def save_thought(text, mood):
    """Сохраняет запись в файл"""
    entry = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "text": text,
        "mood": mood
    }
    
    try:
        # Создаем файл, если его нет
        if not os.path.exists(LOG_FILE):
            with open(LOG_FILE, 'w', encoding='utf-8') as f:
                json.dump([], f)
        
        # Читаем существующие данные
        with open(LOG_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Добавляем новую запись
        data.append(entry)
        
        # Сохраняем обратно
        with open(LOG_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        return True
    except Exception as e:
        print(f"🚨 Ошибка сохранения: {e}")
        return False

def show_stats():
    """Показывает статистику записей"""
    if not os.path.exists(LOG_FILE):
        return
    
    try:
        with open(LOG_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        mood_count = {"позитив": 0, "нейтрально": 0, "негатив": 0}
        for entry in data:
            mood_count[entry["mood"]] += 1
        
        total = len(data)
        print("\n📊 СТАТИСТИКА ДНЕВНИКА:")
        print(f"• Всего записей: {total}")
        print(f"• Позитивных: {mood_count['позитив']} ({mood_count['позитив']/total*100:.1f}%)")
        print(f"• Нейтральных: {mood_count['нейтрально']} ({mood_count['нейтрально']/total*100:.1f}%)")
        print(f"• Негативных: {mood_count['негатив']} ({mood_count['негатив']/total*100:.1f}%)")
        
        if mood_count['негатив'] > mood_count['позитив']:
            print("\n💙 За последнее время у вас было больше сложных мыслей.")
            print("Помните, что обращение за помощью - признак силы.")
    
    except:
        print("\n⚠️ Не удалось загрузить статистику")

def print_welcome():
    """Печатает приветственное сообщение"""
    print("\n" + "=" * 50)
    print("🌟 ДНЕВНИК МЫСЛЕЙ v2.0")
    print("=" * 50)
    print("📝 Записывайте свои мысли голосом и анализируйте их настроение")
    print("🔊 Проверка микрофона: УСПЕШНО")
    print(f"💾 Дневник: {LOG_FILE}")
    print("\n✏️ ГОВОРИТЕ КОГДА УВИДИТЕ СИГНАЛ 'Говорите после сигнала...'")
    print("🛑 Для выхода нажмите Ctrl+C в любой момент")

def main():
    print_welcome()
    
    try:
        while True:
            text = record_and_recognize()
            if not text:
                continue
            
            if moderate_text(text):
                print("\n🚫 ВНИМАНИЕ: Обнаружены нежелательные выражения")
                save_thought(text, "заблокировано")
                print("Запись сохранена с пометкой 'заблокировано'")
            else:
                mood = analyze_sentiment(text)
                quote = random.choice(QUOTES[mood])
                
                print(f"\n📊 АНАЛИЗ НАСТРОЕНИЯ: {mood.upper()}")
                print(f"💬 МУДРАЯ МЫСЛЬ: {quote}")
                
                if save_thought(text, mood):
                    print("💾 Запись успешно сохранена в дневнике")
                    
                    if mood == "негатив":
                        print("\n💙 Поддержка:")
                        print("- Помните, что трудности временны")
                        print("- Поговорите с близким человеком")
                        print("- Обратитесь к специалисту при необходимости")
            
            show_stats()
            print("\n" + "=" * 50)
            print("🎤 ГОТОВ К НОВОЙ МЫСЛИ...")
    
    except KeyboardInterrupt:
        print("\n\n🛑 Программа завершена. Все записи сохранены.")
        print("До новых встреч! 👋")

if __name__ == "__main__":
    main()