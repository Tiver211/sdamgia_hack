FROM python:3.12-alpine3.21
LABEL authors="tiver"

COPY ./requirements.txt .
RUN pip install -r requirements.txt

COPY . ./telegram_bot

ENTRYPOINT ["python", "-m", "telegram_bot.run"]