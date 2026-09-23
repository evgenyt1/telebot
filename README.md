# telebot

Минимальный бот для **личных переписок Telegram**, подключаемый к аккаунту через Telegram Business Bots. Если собеседник или владелец аккаунта пишет отдельное слово «время» (например, «которое время?»), бот отвечает текущим временем от имени подключённого аккаунта. Упоминать бота в переписке не нужно. Бот обрабатывает новые текстовые сообщения в выбранных личных чатах; сообщения, отправленные самим ботом, пропускает.

## Подключение

Нужны Python 3.9+ с `zoneinfo`, установленный `cloudflared` и токен бота от [@BotFather](https://t.me/BotFather). Зависимостей Python нет.

1. Создайте бота через `@BotFather` (`/newbot`). В настройках бота включите **Secretary Mode** (режим подключения к аккаунту).
2. В Telegram откройте **Настройки → Telegram Business → Чат-боты** и подключите этого бота. Выберите чаты, к которым у него будет доступ, и разрешите отвечать на сообщения (`can_reply`). Подключение не требует Telegram Premium.
3. Создайте локальный файл `.env` по образцу `.env.example`. Вставьте `BOT_TOKEN` и сгенерируйте `WEBHOOK_SECRET` командой из образца. Файл `.env` исключён из Git.
4. В первом терминале запустите сервер:

   ```sh
   python3 bot.py serve
   ```

5. Во втором терминале запустите публичный HTTPS туннель:

   ```sh
   cloudflared tunnel --url http://127.0.0.1:8080
   ```

6. Скопируйте выданный адрес вида `https://random.trycloudflare.com` и в третьем терминале зарегистрируйте вебхук:

   ```sh
   python3 bot.py set-webhook https://random.trycloudflare.com
   python3 bot.py webhook-info
   ```

После этого напишите «время» в одной из разрешённых личных переписок или попросите сделать это собеседника. Бот ответит временем в часовом поясе `TIME_ZONE` из `.env`. По умолчанию это `Europe/Istanbul`.

## Остановка и ограничения

При каждом перезапуске Quick Tunnel выдаёт новый адрес: повторите `set-webhook`. Когда закончите эксперимент, выполните `python3 bot.py delete-webhook`, затем остановите сервер и туннель. Quick Tunnel предназначен для тестирования и не гарантирует постоянную доступность. Для постоянной работы потребуются стабильный HTTPS адрес и постоянно запущенный процесс.

Telegram доставляет сообщения только из чатов, разрешённых владельцем аккаунта. Право `can_reply` и возможность ответа ограничиваются правилами Telegram, включая окно активности входящего сообщения. Бот не читает историю до подключения и не работает с секретными чатами.

## Как это работает

Telegram отправляет `business_message` на `/webhook`. Сервер проверяет заголовок `X-Telegram-Bot-Api-Secret-Token`, тип чата, отправителя и отдельное слово «время». Затем он проверяет права соединения через `getBusinessConnection` и вызывает `sendMessage` с `business_connection_id`. Проверить локальный сервер можно по `http://127.0.0.1:8080/health`.

Официальные материалы: [Telegram Business Bots](https://core.telegram.org/bots/features#business-bots), [Telegram Bot API](https://core.telegram.org/bots/api), [Cloudflare Quick Tunnels](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/do-more-with-tunnels/trycloudflare/).
