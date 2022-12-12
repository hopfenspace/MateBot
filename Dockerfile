FROM debian:stable-slim
ENV LANG C.UTF-8
RUN	apt update && \
	apt upgrade -y && \
	apt install python3 python3-pip default-libmysqlclient-dev build-essential -y && \
    rm -rf /var/cache/apt/archives/*.deb /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN	pip3 install -r requirements.txt && \
    pip3 install pymysql mysqlclient && \
    pip3 freeze
COPY . .
ENTRYPOINT ["python3", "-m", "matebot_core"]
CMD ["auto"]
