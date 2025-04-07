ARG BUILD_FROM
FROM ${BUILD_FROM}

ENV LANG C.UTF-8

RUN apk add --no-cache python3 py3-pip build-base libffi-dev

WORKDIR /app

COPY requirements.txt ./
RUN pip install --break-system-packages -r requirements.txt

COPY run.sh /run.sh
RUN chmod a+x /run.sh

COPY app /app

CMD [ "/run.sh" ]