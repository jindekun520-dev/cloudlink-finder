# 网盘资源搜索神器

CloudLink Finder 是一个面向互联网公开分享链接的多网盘资源聚合搜索工具。它支持夸克网盘、百度网盘、阿里云盘、迅雷网盘等主流网盘，并提供链接有效性检测、标题匹配、网盘筛选、提取码复制和新页面打开等功能。

项目提供两种使用方式：

1. **本地或服务器 Docker 部署**：部署完成后，通过浏览器访问。
2. **飞牛 fnOS FPK 安装**：在飞牛 NAS 应用中心手动安装，通过桌面图标或浏览器访问。

## 功能特性

- 🔍 **结构化多源搜索**：使用 PanSou 聚合索引，并保留严格的搜狗/Bing 兜底源
- 📦 **支持 9 种网盘**：夸克、百度、阿里、迅雷、天翼、UC、115、123、移动云盘
- ✅ **链接有效性验证**：返回前调用网盘公开接口确认链接状态和实际资源标题
- 🎯 **标题与链接准确绑定**：每条分享链接保留独立标题，过滤张冠李戴的结果
- 🧭 **指定网盘搜索**：可以只搜索选定的网盘类型
- 📋 **复制并打开**：复制链接或链接及提取码后，在新页签或新窗口打开网盘页面
- 🎨 **暗色模式**：支持亮色、暗色和跟随系统三种主题
- 📱 **响应式设计**：同时适配桌面端和移动端
- ⚡ **搜索缓存**：相同关键词在短时间内使用缓存，加快重复搜索
- 🔧 **可扩展搜索源**：支持通过配置添加自定义搜索 API

## 两种使用方式

| 使用方式 | 适用场景 | 安装入口 | 访问方式 |
|---|---|---|---|
| Docker 本地部署 | 电脑、Linux 服务器、普通 NAS 或开发测试 | 克隆仓库并运行 Docker Compose | `http://本机或服务器IP:8899` |
| 飞牛 FPK 安装 | 飞牛 fnOS NAS 用户 | 应用中心 → 手动安装 → 上传 FPK | 桌面图标或 `http://飞牛NAS-IP:8899` |

如果你使用的是飞牛 NAS，推荐选择 FPK 安装；如果你需要在电脑、服务器或其他 NAS 上运行，选择 Docker 部署。

## 方式一：本地或服务器 Docker 部署

### 环境要求

- Docker 24 或更高版本
- Docker Compose v2（使用 `docker compose` 命令）
- 能够访问项目配置的 Node.js 和 Python 基础镜像
- 默认端口 `8899` 未被其他程序占用

支持安装 Docker Desktop 的 macOS、Windows，以及安装了 Docker Engine 的 Linux 服务器或 NAS。

### 1. 获取代码

从 GitHub 克隆：

```bash
git clone https://github.com/jindekun520-dev/cloudlink-finder.git
cd cloudlink-finder
```

国内网络也可以从 Gitee 克隆：

```bash
git clone https://gitee.com/jindekun_admin/cloudlink-finder.git
cd cloudlink-finder
```

### 2. 构建并启动

在项目根目录执行：

```bash
docker compose -f docker/docker-compose.yaml up -d --build
```

第一次启动会构建前端和后端镜像，所需时间取决于设备性能与网络环境。

### 3. 浏览器访问

在部署机器本机访问：

```text
http://localhost:8899
```

从局域网中的其他设备访问：

```text
http://部署机器IP:8899
```

例如部署机器的局域网 IP 是 `192.168.1.100`：

```text
http://192.168.1.100:8899
```

### 4. 使用其他端口

如果 `8899` 已被占用，可以在启动时指定其他端口：

```bash
PORT=18899 docker compose -f docker/docker-compose.yaml up -d --build
```

然后访问：

```text
http://部署机器IP:18899
```

### 5. 查看状态和日志

```bash
docker compose -f docker/docker-compose.yaml ps
docker compose -f docker/docker-compose.yaml logs -f
```

健康检查接口：

```text
http://部署机器IP:8899/api/health
```

### 6. 停止或更新

停止应用：

```bash
docker compose -f docker/docker-compose.yaml down
```

获取新版本并重新构建：

```bash
git pull
docker compose -f docker/docker-compose.yaml up -d --build
```

搜索缓存和应用数据保存在 Docker 数据卷 `cloudlink-finder-data` 中。普通的 `docker compose down` 不会删除该数据卷；不要在未备份数据时执行带 `-v` 的删除命令。

## 方式二：飞牛 fnOS 安装 FPK

### 环境要求

- 飞牛 fnOS `1.1.3100` 或更高版本
- 已启用 Docker 服务
- 默认端口 `8899` 未被其他应用占用
- 安装和首次构建期间能够访问所需的 Docker 基础镜像

FPK 的应用标识为：

```text
cloudlink-finder
```

当前包声明支持平台：

```text
x86 / ARM（platform = all）
```

### 1. 获取 FPK 安装包

优先从 GitHub 或 Gitee 的项目发布页下载最新的：

```text
cloudlink-finder-<版本号>.fpk
```

- [GitHub 项目地址](https://github.com/jindekun520-dev/cloudlink-finder)
- [Gitee 项目地址](https://gitee.com/jindekun_admin/cloudlink-finder)

如果发布页暂未提供预编译 FPK，可以在 macOS 或 Linux 上从源码构建：

```bash
./scripts/build-fpk.sh
./scripts/verify-fpk.sh
```

构建脚本会自动下载飞牛官方 `fnpack 1.2.3`，并将带版本号的安装包输出到：

```text
release/cloudlink-finder-<版本号>.fpk
```

### 2. 在飞牛应用中心安装

1. 登录飞牛 fnOS 管理界面。
2. 打开“应用中心”。
3. 点击“手动安装”。
4. 选择并上传 `cloudlink-finder-<版本号>.fpk`。
5. 阅读权限和端口提示，确认安装。
6. 等待应用容器完成构建并启动。

### 3. 打开应用

安装成功后，可以使用以下任一方式访问：

- 点击飞牛桌面的“网盘搜索神器”图标，系统会在浏览器窗口中打开应用。
- 在浏览器中直接访问：

```text
http://飞牛NAS-IP:8899
```

例如飞牛 NAS 的地址是 `192.168.1.20`：

```text
http://192.168.1.20:8899
```

### 4. 数据目录和升级说明

当前 FPK 的持久化数据目录为：

```text
/var/apps/cloudlink-finder/shares/cloudlink-finder/data
```

升级前建议备份该目录。正常版本升级应保持应用标识 `cloudlink-finder` 不变，以便复用原有应用数据。

早期测试包曾使用应用标识 `third-pan-search`。如果设备上仍安装着该旧包，建议先备份旧数据并卸载旧包，再安装当前 `cloudlink-finder` 包，避免端口和容器冲突。旧数据目录不会自动迁移到新应用目录。

## 开发环境

如果需要分别启动前后端进行开发：

### 后端

```bash
cd backend
python3 -m pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

### 前端

```bash
cd frontend
npm install
npm run dev
```

## 技术栈

| 层级 | 技术 |
|---|---|
| 前端 | Vue 3 + TypeScript + Vite |
| 后端 | Python FastAPI |
| 数据库 | SQLite |
| 容器 | Docker + Nginx + Supervisor |
| 飞牛打包 | fnpack + FPK |

## 搜索源说明

应用默认使用结构化 PanSou 聚合源，并将搜狗、Bing 作为严格兜底源。一个搜索卡片内出现多个链接时不会猜测标题归属；无法通过网盘公开接口确认有效性的链接也不会进入严格结果。

可以通过后端配置文件 `data/sources.yaml` 添加自定义 API 搜索源。

## 质量保证

当前对夸克、百度、阿里、123 网盘执行严格有效性检测。搜索缓存命中时仍会按短周期重新确认链接状态；外部节点临时失败时会重试，并可回退到全量搜索后在本地按网盘类型过滤。

## 支持网盘

| 网盘 | 域名 |
|---|---|
| 夸克网盘 | `pan.quark.cn` |
| 百度网盘 | `pan.baidu.com` |
| 阿里云盘 | `aliyundrive.com` |
| 迅雷网盘 | `pan.xunlei.com` |
| 天翼云盘 | `cloud.189.cn` |
| UC 网盘 | `drive.uc.cn` |
| 115 网盘 | `115.com` |
| 123 云盘 | `123pan.com` |
| 移动云盘 | `caiyun.139.com` |

## 项目仓库

- GitHub：[jindekun520-dev/cloudlink-finder](https://github.com/jindekun520-dev/cloudlink-finder)
- Gitee：[jindekun_admin/cloudlink-finder](https://gitee.com/jindekun_admin/cloudlink-finder)

## 使用说明

本应用只聚合检索互联网上已经公开的网盘分享信息，不提供资源上传、存储或下载服务，也不会要求或保存用户的网盘账号和密码。请遵守所在地法律法规、网盘平台规则以及内容版权要求，合理使用搜索结果。
