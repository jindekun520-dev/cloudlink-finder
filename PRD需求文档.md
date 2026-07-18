# 飞牛网盘资源搜索神器 — 产品需求文档（PRD）

> **版本**：v1.0  
> **日期**：2026-07-12  
> **状态**：待确认  

---

## 一、项目概述

### 1.1 项目背景

飞牛NAS用户在日常使用中，经常需要从互联网上搜索和下载各类资源（影视、软件、文档、音乐等）。目前主流的网盘（夸克网盘、百度网盘、阿里云盘等）上有大量用户分享的资源，但用户缺乏一个统一、便捷的搜索入口。

当前已有一些开源方案（如爱盼 Aipan、PanSou、PanHub），但它们存在以下问题：
- **部署门槛高**：Aipan 依赖 PostgreSQL + Redis + Elasticsearch，NAS 运行压力大
- **非飞牛原生**：没有适配飞牛NAS的 FPK 应用格式，需要手动配置 Docker
- **功能冗余**：内置博客、投稿、后台管理等非核心功能
- **UI 不够友好**：部分项目移动端适配差

本项目旨在开发一款**轻量、专注、原生适配飞牛NAS**的网盘资源搜索应用。

### 1.2 项目定位

一款运行在飞牛NAS上的**网盘资源聚合搜索引擎**，用户输入关键字即可检索全网公开分享的网盘资源链接，支持按网盘类型筛选，一键复制链接进行下载。

### 1.3 核心价值

| 维度 | 说明 |
|------|------|
| **轻量化** | SQLite 数据库，无额外中间件依赖，NAS 低配也能流畅运行 |
| **原生化** | 符合飞牛 FPK 应用规范，应用中心一键安装 |
| **专注** | 只做搜索，不做博客/投稿/后台管理 |
| **美观** | 现代化 UI，支持亮色/暗色主题，移动端适配 |

---

## 二、用户场景

### 2.1 典型用户故事

**场景 1 — 搜索影视资源**
> 小王想在 NAS 上下载电影《奥本海默》，他打开飞牛NAS的网盘搜索神器，输入"奥本海默 4K"，选择夸克网盘筛选，立刻看到多条有效的夸克网盘分享链接，点击复制后在夸克APP中保存并下载。

**场景 2 — 搜索软件资源**
> 老李需要找一个 macOS 上的 PDF 编辑工具，他在搜索框中输入"PDF Expert mac"，从返回结果中找到了百度网盘的分享链接，包含破解版软件。

**场景 3 — 多网盘对比**
> 小张想下载一部热门电视剧，她搜索"庆余年2 全集"，应用同时返回了百度网盘、夸克网盘、阿里云盘三个平台的资源链接，她选择了自己会员的阿里云盘链接进行下载。

**场景 4 — 手机端使用**
> 用户在手机浏览器上打开飞牛NAS的网盘搜索神器，界面自适应移动端，搜索体验流畅。

---

## 三、功能需求

### 3.1 核心功能（P0 — 必须有）

#### F1：关键字搜索
- 用户在搜索框输入关键字，点击搜索或按回车触发
- 支持空格分隔的多关键字组合搜索
- 搜索结果以列表形式展示，每条结果包含：
  - 资源标题/名称
  - 网盘类型标识（夸克/百度/阿里/迅雷等）
  - 资源描述/简介（如有）
  - 分享链接（可点击复制）
  - 提取码（如有）
  - 资源大小（如有）
  - 分享时间（如有）

#### F2：网盘类型筛选
- 支持按网盘类型过滤搜索结果
- 默认搜索全部网盘，用户可多选筛选：
  - 夸克网盘
  - 百度网盘
  - 阿里云盘
  - 迅雷网盘
  - 天翼云盘
  - UC网盘
  - 115网盘
  - 123云盘
  - 移动云盘

#### F3：一键复制链接
- 每条搜索结果提供"复制链接"按钮
- 点击后自动复制分享链接 + 提取码到剪贴板
- 复制成功后给出轻提示

#### F4：搜索结果排序
- 默认按相关度（时间 + 匹配度）排序
- 支持切换排序方式：
  - 最新发布
  - 文件大小（如有）

### 3.2 增强功能（P1 — 应该有）

#### F5：搜索历史
- 自动记录用户的搜索关键字（最近20条）
- 点击历史记录可快速重新搜索
- 支持清空搜索历史

#### F6：热门搜索推荐
- 首页展示当前热门搜索关键字（基于搜索频率统计）
- 点击热门关键字直接搜索

#### F7：暗色模式
- 支持亮色/暗色主题切换
- 默认跟随飞牛NAS系统主题设置

#### F8：结果为空时的处理
- 显示友好的空状态提示
- 建议更换关键字或放宽筛选条件

### 3.3 扩展功能（P2 — 可以有）

#### F9：搜索源配置
- 支持用户在设置中管理搜索源（API端点）
- 支持启用/禁用特定搜索源
- 支持添加自定义搜索源

#### F10：搜索缓存
- 相同关键字在一定时间内（如5分钟）返回缓存结果
- 减少对上游搜索源的请求压力

#### F11：资源有效性检测
- 尝试检测分享链接是否仍然有效
- 标注"已失效"的资源链接

---

## 四、飞牛NAS兼容性设计

### 4.1 应用类型

采用飞牛官方推荐的 **Docker 应用** 方案，封装为 `.fpk` 格式。

### 4.2 FPK 目录结构

```
feiniu-pan-search/
├── app/
│   ├── docker/
│   │   └── docker-compose.yaml      # 前后端容器编排
│   └── ui/
│       ├── images/                   # 应用截图
│       └── config                    # Web入口配置
├── cmd/
│   ├── main                          # 生命周期管理（start/stop/status）
│   ├── install_init                  # 安装初始化
│   ├── uninstall_init                # 卸载清理
│   └── upgrade_init                  # 升级迁移
├── config/
│   ├── privilege                     # 权限配置
│   └── resource                      # 资源配置（docker-project）
├── wizard/
│   └── install                       # 安装向导（可选：配置端口等）
├── manifest                          # 应用元信息
├── ICON.PNG                          # 64×64 图标
└── ICON_256.PNG                      # 256×256 图标
```

### 4.3 关键配置项

| 配置 | 值 | 说明 |
|------|-----|------|
| `manifest.appname` | `third-pan-search` | 应用唯一标识 |
| `manifest.platform` | `all` | 支持 x86 和 ARM |
| `manifest.os_min_version` | `1.1.3100` | 最低系统版本 |
| `manifest.source` | `thirdparty` | 第三方应用 |
| `manifest.service_port` | 用户可选，默认 8899 | Web 服务端口 |
| `privilege.run-as` | `package` | 非 root 运行 |
| `resource.docker-project` | 声明 | Docker 容器资源 |

### 4.4 Web 入口

通过飞牛应用中心的桌面图标点击打开，跳转到 Web 界面。

`app/ui/config` 配置示例：
```json
{
    ".url": {
        "title": "网盘搜索",
        "icon": "images/icon.png",
        "type": "url",
        "protocol": "http",
        "port": "8899",
        "url": "/"
    }
}
```

---

## 五、技术方案

### 5.1 总体架构

```
┌──────────────────────────────────────────────┐
│                   飞牛NAS                      │
│  ┌─────────────────────────────────────────┐ │
│  │          Docker Compose 编排             │ │
│  │  ┌──────────────┐  ┌──────────────────┐ │ │
│  │  │   前端容器     │  │    后端容器       │ │ │
│  │  │  Vue 3 +     │  │  Python FastAPI  │ │ │
│  │  │  Vite +      │◄─┤  + SQLite        │ │ │
│  │  │  Element Plus│  │  + 搜索聚合引擎   │ │ │
│  │  └──────────────┘  └───────┬──────────┘ │ │
│  │                             │             │ │
│  └─────────────────────────────┼─────────────┘ │
│                                 │               │
└─────────────────────────────────┼───────────────┘
                                  │
                          ┌───────▼────────┐
                          │  上游搜索源      │
                          │  ┌───────────┐ │
                          │  │ TG频道API  │ │
                          │  ├───────────┤ │
                          │  │ 公开搜索API │ │
                          │  ├───────────┤ │
                          │  │ 自定义源    │ │
                          │  └───────────┘ │
                          └────────────────┘
```

### 5.2 技术栈选型

| 层级 | 技术 | 选型理由 |
|------|------|----------|
| **前端框架** | Vue 3 + TypeScript | 社区主流，生态丰富 |
| **构建工具** | Vite | 极速开发体验 |
| **UI 组件库** | Element Plus | 成熟的中后台组件库，暗色主题支持好 |
| **后端框架** | Python FastAPI | 轻量、高性能、异步支持好 |
| **ORM** | SQLAlchemy + aiosqlite | 异步 SQLite 支持 |
| **数据库** | SQLite | 零配置、轻量，适合 NAS 场景 |
| **HTTP 客户端** | httpx (async) | 异步并发请求上游搜索源 |
| **容器化** | Docker + Docker Compose | 飞牛 FPK 标准方案 |
| **反向代理** | Nginx（前端容器内） | 静态文件服务 + API 代理 |

### 5.3 搜索数据源设计

#### 搜索策略

采用**多源聚合 + 结果去重**的策略：

1. **内置搜索源**：预置若干个可靠的公开搜索API或TG频道接口
2. **并发请求**：使用 `asyncio` 并发请求所有启用的搜索源
3. **结果聚合**：收集所有源的返回结果
4. **去重排序**：根据链接去重，按发布时间 + 匹配度排序
5. **缓存优化**：相同关键字短时间内的结果缓存，减少对外请求

#### 初始内置搜索源方案

| 搜索源 | 类型 | 说明 |
|--------|------|------|
| PanSou API | 公开API | GitHub 4.4k Stars 的聚合搜索服务 |
| TG频道聚合 | 插件 | 从若干公开的资源分享TG频道检索 |
| 自定义源 | 用户配置 | 用户可自行添加API端点 |

> **注意**：具体的内置搜索源需要在实际开发中验证可用性和稳定性。首选 PanSou 这类有维护的开源项目API，或自建轻量搜索后端。

### 5.4 API 接口设计

#### 后端 API

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/search` | 搜索资源 |
| `GET` | `/api/hot` | 热门搜索关键字 |
| `GET` | `/api/history` | 搜索历史 |
| `DELETE` | `/api/history` | 清空搜索历史 |
| `GET` | `/api/sources` | 搜索源列表 |
| `PUT` | `/api/sources` | 更新搜索源配置 |
| `GET` | `/api/health` | 健康检查 |

#### 搜索接口参数

```
GET /api/search?kw={关键字}&cloud_types={网盘类型}&page={页码}&size={每页条数}&sort={排序方式}
```

响应示例：
```json
{
    "code": 0,
    "data": {
        "total": 128,
        "items": [
            {
                "id": "abc123",
                "title": "[夸克] 奥本海默 4K HDR 杜比视界",
                "description": "奥本海默电影资源",
                "cloud_type": "quark",
                "cloud_name": "夸克网盘",
                "share_url": "https://pan.quark.cn/s/xxxxxx",
                "share_code": "1234",
                "file_size": "25.8GB",
                "publish_time": "2026-07-10",
                "source": "pansou"
            }
        ]
    }
}
```

### 5.5 数据库设计（SQLite）

```sql
-- 搜索历史表
CREATE TABLE search_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    keyword TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 搜索源配置表
CREATE TABLE search_sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    type TEXT NOT NULL,          -- 'api' | 'tg_channel' | 'custom'
    endpoint TEXT NOT NULL,
    enabled INTEGER DEFAULT 1,
    priority INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 搜索结果缓存表
CREATE TABLE search_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    keyword TEXT NOT NULL,
    cloud_types TEXT,            -- 逗号分隔的网盘类型
    result_json TEXT NOT NULL,   -- 缓存的结果JSON
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 索引
CREATE INDEX idx_history_keyword ON search_history(keyword);
CREATE INDEX idx_cache_keyword ON search_cache(keyword);
CREATE INDEX idx_cache_created ON search_cache(created_at);
```

### 5.6 Docker 部署方案

```yaml
# docker-compose.yaml
version: "3.9"
services:
  backend:
    image: feiniu-pan-search-backend:latest
    container_name: pan-search-backend
    restart: unless-stopped
    ports:
      - "${PORT}:8000"
    volumes:
      - pan-search-data:/app/data          # SQLite 数据库持久化
    environment:
      - TZ=Asia/Shanghai
      - CACHE_TTL=300                       # 缓存有效期（秒）
    logging:
      options:
        max-size: 10m
        max-file: "3"

  frontend:
    image: feiniu-pan-search-frontend:latest
    container_name: pan-search-frontend
    restart: unless-stopped
    ports:
      - "${WEB_PORT}:80"
    environment:
      - BACKEND_URL=http://backend:8000
    depends_on:
      - backend
    logging:
      options:
        max-size: 10m
        max-file: "3"

volumes:
  pan-search-data:
    name: pan-search-data
```

> **简化方案**：也可将前后端打包到单一容器，减少资源占用。在单个容器中 Nginx 服务静态前端文件并反向代理到 Python 后端。

### 5.7 单容器简化方案（推荐）

考虑到 NAS 设备的资源限制，推荐采用单容器方案：

```
单容器内部：
├── Nginx (静态文件 + 反向代理)
├── FastAPI 后端 (通过 supervisord 管理)
└── SQLite 数据库
```

Dockerfile 使用多阶段构建：
- 阶段1：Node.js 构建前端静态文件
- 阶段2：Python 环境 + Nginx + Supervisor

---

## 六、UI/UX 设计参考

### 6.1 页面结构

```
┌──────────────────────────────────────┐
│           网盘资源搜索神器             │
│  ┌────────────────────────────────┐  │
│  │  🔍 输入关键字搜索网盘资源...    │  │  ← 搜索栏
│  │  [夸克] [百度] [阿里] ... [搜索] │  │  ← 网盘筛选 + 搜索按钮
│  └────────────────────────────────┘  │
│                                       │
│  🔥 热门搜索：奥本海默 | 庆余年2 ... │  ← 热门关键字
│                                       │
│  ┌────────────────────────────────┐  │
│  │ 📂 [夸克] 奥本海默 4K HDR      │  │
│  │ 25.8GB | 2026-07-10           │  │  ← 搜索结果卡片
│  │ [复制链接] [复制提取码]         │  │
│  ├────────────────────────────────┤  │
│  │ 📂 [百度] 奥本海默 1080P       │  │
│  │ 12.3GB | 提取码: abcd         │  │  ← 搜索结果卡片
│  │ [复制链接及提取码]              │  │
│  ├────────────────────────────────┤  │
│  │ ...更多结果...                  │  │
│  └────────────────────────────────┘  │
│                                       │
│  第 1/13 页  ← 上一页  下一页 →      │  ← 分页
└──────────────────────────────────────┘
```

### 6.2 设计原则

- **简洁至上**：去除一切非必要元素，聚焦搜索和结果展示
- **响应式**：适配桌面（飞牛Web桌面）和移动端
- **暗色优先**：NAS 管理界面多为暗色，默认暗色主题
- **操作便捷**：复制链接一步到位，减少操作步骤

---

## 七、开发计划

### 7.1 里程碑

| 阶段 | 内容 | 预计时间 |
|------|------|----------|
| **M1 — 基础框架** | 前后端项目脚手架搭建、Docker 化 | 1-2天 |
| **M2 — 核心搜索** | 搜索API对接、结果解析、去重排序 | 2-3天 |
| **M3 — 前端界面** | 搜索页、结果展示、筛选交互 | 2-3天 |
| **M4 — 增强功能** | 搜索历史、热门推荐、暗色模式 | 1-2天 |
| **M5 — FPK封装** | 飞牛FPK规范适配、打包脚本 | 1-2天 |
| **M6 — 测试优化** | 功能测试、性能优化、文档 | 1-2天 |

**总计**：约 8-14 天

### 7.2 交付物

| 交付物 | 说明 |
|--------|------|
| 源代码 | 前后端完整源代码（GitHub 仓库） |
| Docker 镜像 | 前端镜像 + 后端镜像（或合并镜像） |
| FPK 安装包 | `.fpk` 文件，飞牛应用中心一键安装 |
| 用户文档 | 安装和使用说明 |
| 开发文档 | API 文档、二次开发指南 |

---

## 八、待确认事项

在正式开始开发前，需要和你确认以下问题：

### Q1：技术栈确认
上述方案采用 **Vue 3 + FastAPI + SQLite + Docker**，是否认可？是否有其他偏好（如 React 替代 Vue、Node.js 替代 Python）？

### Q2：搜索数据源策略
搜索源的核心难点在于**如何获取网盘资源数据**。当前方案是聚合已有的公开搜索API（如 PanSou），你是否：
- A. 接受使用第三方公开搜索API作为数据源
- B. 希望自建搜索源（需要额外的爬虫开发，工作量大增）
- C. 优先封装已有的开源项目（如 PanSou/PanHub），再逐步定制

### Q3：单容器 vs 多容器
- A. 单容器（资源占用小，推荐NAS场景）
- B. 前后端分离双容器（更灵活，但资源占用稍大）

### Q4：是否需要用户系统
当前设计不包含用户登录/注册。是否需要多用户支持、个人收藏等功能？

### Q5：搜索源的维护
内置搜索源可能会因上游变化而失效，你希望的维护策略是？
- A. 通过应用更新来修复搜索源
- B. 支持用户自行配置/添加搜索源
- C. 两者都支持

---

> 📌 **请确认以上需求文档内容，特别是第八章的待确认事项。确认后我将立即开始开发工作。**

