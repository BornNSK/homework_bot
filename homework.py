import os
import sys
import time
import telegram
import logging
import requests
from exceptions import ApiError, UnknownStatus
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s, %(levelname)s, %(message)s',
                    )

logger = logging.StreamHandler(sys.stdout)
logger.setLevel(logging.DEBUG)
logger.setFormatter('%(asctime)s, %(levelname)s, %(message)s')


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    """Проверка доступности токенов."""
    return all({PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, })


def send_message(bot, message):
    """Отправка сообщения в Telegram."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.debug('Сообщение отправлено успешно!')
    except Exception as error:
        logging.error(f'Ошибка при отправке сообщения: {error}')


def get_api_answer(timestamp):
    """Получаем ответ от API."""
    params = {'from_date': timestamp}
    try:
        request = requests.get(ENDPOINT, headers=HEADERS, params=params)
    except requests.exceptions.RequestException as error:
        logging.error(f'Ошибка при запросе к основному API: {error}')
    if request.status_code != 200:
        raise ApiError(f'Ошибка доступа к API. Код:{request.status_code}')
    return request.json()


def check_response(response):
    """Проверка ответа API на корректность."""
    if not isinstance(response, dict):
        raise TypeError('Проверьте, что возвращается словарь.')
    if 'homeworks' not in response:
        raise KeyError('Отсутствует ожидаемое значение - homeworks')
    if not isinstance(response['homeworks'], list):
        raise TypeError('Проверьте, что данные являются листом.')
    try:
        homework = response.get('homeworks')[0]
        return homework
    except IndexError:
        raise IndexError('Список домашних работ пуст')


def parse_status(homework):
    """Получение статуса работы."""
    if 'homework_name' not in homework:
        raise ValueError('Отсутствует ключ "homework_name" в ответе API')
    if 'status' not in homework:
        raise ValueError('Отсутствует ключ "status" в ответе API')
    homework_name = homework["homework_name"]
    homework_status = homework["status"]
    if homework_status not in HOMEWORK_VERDICTS:
        raise UnknownStatus(f'Неизвестный статус работы: {homework_status}')
    verdict = HOMEWORK_VERDICTS[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    temp_status = ''
    if not check_tokens():
        logging.critical('Проверьте токены.')
        sys.exit()
    while True:
        try:
            api = get_api_answer(timestamp)
            homeworks = check_response(api)
            if len(homeworks) != 0 and temp_status != homeworks ['status']:
                new_status = parse_status(homeworks)
                send_message(bot, new_status)
                temp_status = homeworks['status']
            logging.debug("Статус работы не изменился.") 
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(message)
            send_message(bot, message)
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
