# 网盘资源搜索神器

CloudLink Finder 是一个面向公开分享链接的网盘资源搜索引擎，支持夸克网盘、百度网盘、阿里云盘、迅雷网盘等主流网盘。

## 功能特性

- 🔍 **结构化多源搜索**：使用 PanSou 聚合索引，并保留严格的搜狗/Bing 兜底源
- 📦 **9种网盘支持**：夸克、百度、阿里云盘、迅雷、天翼、UC、115、123、移动云盘
- ✅ **链接有效性验证**：返回前调用网盘公开接口确认链接状态和实际资源标题
- 🎯 **标题链接准确绑定**：每条分享链接保留独立标题，过滤张冠李戴结果
- 📋 **复制并打开**：复制链接或链接及提取码后，在新页签/窗口打开网盘页面
- 🎨 **暗色模式**：支持亮色/暗色/跟随系统三种主题
- 📱 **响应式设计**：同时适配桌面端和移动端
- ⚡ **搜索缓存**：相同关键字短时间缓存，加速响应
- 🔧 **可扩展**：支持通过配置添加自定义搜索API源

## 快速开始

### 开发环境

```bash
# 后端
cd backend
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload

# 前端
cd frontend
npm install
npm run dev
```

### Docker 部署

```bash
docker compose -f docker/docker-compose.yaml up -d
```

访问 http://localhost:8899

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | Vue 3 + TypeScript + Vite |
| 后端 | Python FastAPI |
| 数据库 | SQLite |
| 容器 | Docker + Nginx + Supervisor |

## 搜索源说明

应用默认使用结构化 PanSou 聚合源，并将搜狗、Bing 作为严格兜底源。一个搜索卡片内出现多个链接时不会猜测标题归属；无法通过网盘公开接口确认有效性的链接也不会进入严格结果。

可通过后端配置文件 `data/sources.yaml` 添加自定义API搜索源。

## 质量保证

当前对夸克、百度、阿里、123 网盘执行严格有效性检测。搜索缓存命中时仍会按短周期重新确认链接状态；外部节点临时失败时会重试，并可回退到全量搜索后在本地按网盘类型过滤。

## 支持网盘

| 网盘 | 域名 |
|------|------|
| 夸克网盘 | pan.quark.cn |
| 百度网盘 | pan.baidu.com |
| 阿里云盘 | aliyundrive.com |
| 迅雷网盘 | pan.xunlei.com |
| 天翼云盘 | cloud.189.cn |
| UC网盘 | drive.uc.cn |
| 115网盘 | 115.com |
| 123云盘 | 123pan.com |
| 移动云盘 | caiyun.139.com |
