FROM python:3
LABEL org.opencontainers.image.title="statsimi"
LABEL org.opencontainers.image.description="station similarity classification"
LABEL org.opencontainers.image.authors="Patrick Brosi <brosi@cs.uni-freiburg.de>"
LABEL org.opencontainers.image.source="https://github.com/ad-freiburg/statsimi"
LABEL org.opencontainers.image.revision="0.0.1"
LABEL org.opencontainers.image.licenses="GPL-3.0"
WORKDIR /app

ADD requirements.txt setup.py README.md ./
ADD ./cutil ./cutil
RUN pip install --no-cache-dir --use-feature=in-tree-build .

ADD . .

EXPOSE 8282

ENTRYPOINT ["python", "./statsimi.py"]
CMD ["--http_port", "8282"]