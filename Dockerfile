FROM python:3.14-slim

ENV TZ=Asia/Shanghai

RUN pip install --no-cache-dir -i https://mirrors.aliyun.com/pypi/simple/ uv

WORKDIR /app

COPY pyproject.toml ./
COPY uv.lock ./

# 先装依赖（docker 缓存）
RUN uv sync --frozen --no-install-project -i https://mirrors.aliyun.com/pypi/simple/

COPY main.py ./
COPY gunicorn.py ./
COPY src ./src
COPY README.md ./

# 再装项目
RUN uv sync --frozen -i https://mirrors.aliyun.com/pypi/simple/

EXPOSE 5050

CMD ["./.venv/bin/gunicorn", "-c", "gunicorn.py", "main:app"]
