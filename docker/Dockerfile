# 前端产物在打包阶段已预构建（frontend/dist），此处不再引入 Node 构建阶段，
# 避免 NAS 端拉取 node 镜像与执行 npm install 造成安装长时间卡住或失败。
#
# 使用 Docker 官方镜像，避免第三方镜像代理（docker.1ms.run 等）网络波动导致安装失败。
# 构建时仍可通过 --build-arg 覆盖。
ARG PYTHON_IMAGE=python:3.12-slim

FROM ${PYTHON_IMAGE}

# 安装 Nginx 和 Supervisor
RUN apt-get update && \
    apt-get install -y --no-install-recommends nginx supervisor && \
    rm -rf /var/lib/apt/lists/* && \
    rm /etc/nginx/sites-enabled/default

# 创建应用目录
RUN mkdir -p /app/backend /app/data

# 安装 Python 依赖
COPY backend/requirements.txt /app/backend/
RUN pip install --no-cache-dir \
        -i https://mirrors.aliyun.com/pypi/simple/ \
        --trusted-host mirrors.aliyun.com \
        -r /app/backend/requirements.txt

# 复制后端代码
COPY backend/ /app/backend/

# 复制预构建的前端产物（打包时由 scripts/build-fpk.sh 生成并校验）
COPY dist/ /usr/share/nginx/html/

# 复制 Nginx 配置
COPY nginx/default.conf /etc/nginx/conf.d/default.conf

# 复制 Supervisor 配置
COPY supervisor/supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# 创建数据目录和日志目录
RUN mkdir -p /app/data /var/log/supervisor

# 暴露端口
EXPOSE 80

# 启动 Supervisor（管理 Nginx + FastAPI）
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
