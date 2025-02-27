FROM python:3.12-alpine3.21
LABEL authors="tiver"

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY parser.py parser.py

CMD ["python", "parser.py", "--target=hack"]