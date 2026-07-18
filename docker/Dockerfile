# ==================== 第一阶段：构建前端 ====================
FROM node:20-alpine AS frontend-builder

WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci --no-audit 2>/dev/null || npm install --no-audit
COPY frontend/ ./
RUN npm run build


# ==================== 第二阶段：最终运行镜像 ====================
FROM python:3.12-slim

# 安装 Nginx 和 Supervisor
RUN apt-get update && \
    apt-get install -y --no-install-recommends nginx supervisor && \
    rm -rf /var/lib/apt/lists/* && \
    rm /etc/nginx/sites-enabled/default

# 创建应用目录
RUN mkdir -p /app/backend /app/data

# 安装 Python 依赖
COPY backend/requirements.txt /app/backend/
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

# 复制后端代码
COPY backend/ /app/backend/

# 复制前端构建产物
COPY --from=frontend-builder /app/frontend/dist /usr/share/nginx/html

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
