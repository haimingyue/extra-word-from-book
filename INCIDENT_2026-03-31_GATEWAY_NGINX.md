# 事故复盘：2026-03-31 晚间公网访问异常

## 现象

- 晚间访问站点时，`ping` 服务器 IP 正常，但 `curl` / 浏览器访问域名失败。
- 当前项目容器 `app-frontend-1`、`app-backend-1`、`app-nginx-1` 后续排查时均可恢复正常。
- 最终确认异常点在外层公网网关 `gateway-nginx`。

## 影响范围

- `caniread.tlpy8.com` 公网访问异常。
- 由于外层网关不可用，前端页面和后端 API 的公网请求均受影响。
- 服务器本身未离线，应用内部服务并非整体损坏。

## 关键证据

### 1. 当前项目服务本身是可恢复的

- `docker ps` 显示以下容器可正常运行：
  - `app-frontend-1`
  - `app-backend-1`
  - `app-nginx-1`
  - `app-postgres-1`
- 本机访问 `http://127.0.0.1:8080` 返回 `200`。

### 2. `gateway-nginx` 持续重启

- `docker ps` 一度显示 `gateway-nginx Restarting`。
- `docker events` 显示 `2026-03-31 22:20` 至 `22:32` 期间，`gateway-nginx` 持续 `start -> die` 循环，退出码为 `1`。

### 3. `gateway-nginx` 启动失败的直接原因

`docker logs gateway-nginx` 中出现以下报错：

- `host not found in upstream "backend:8080" in /etc/nginx/conf.d/10-api.conf`
- `host not found in upstream "escape-ordinary-nuxt:3000" in /etc/nginx/conf.d/20-main.conf`
- `host not found in upstream "vitepress-internal:80" in /etc/nginx/conf.d/30-source.conf`

说明外层网关配置中仍然保留了历史项目或旧服务的 upstream，而这些 upstream 在当前环境已经不存在。

## 根因

本次事故的根因是：

- `gateway-nginx` 的配置目录中仍保留了历史项目的 nginx 配置。
- 这些历史配置依赖的容器名在当前服务器环境中已不存在。
- 当 `gateway-nginx` 被重新启动时，会重新解析全部 `.conf` 文件。
- 由于 upstream 无法解析，nginx 启动失败，导致公网入口不可用。

## 触发条件

本次故障发生时，用户未手动操作当前项目。

根据 `docker events`，可以确认 `gateway-nginx` 在晚间被触发重启。虽然未进一步定位到首次重启的外部触发源，但可以确定：

- 一旦 `gateway-nginx` 发生重启
- 旧配置就会导致其无法启动
- 从而出现“`ping` 正常，但公网 HTTP 访问失败”的现象

## 处置过程

### 1. 先确认当前项目服务状态

- 检查 `docker ps`
- 检查 `docker compose ps`
- 检查 `app-nginx-1`、`app-backend-1` 日志

### 2. 定位到公网网关问题

- 发现 `gateway-nginx` 持续重启
- 查看日志后确认 upstream 配置错误

### 3. 收敛网关配置

将历史配置从 `/root/gateway-nginx/conf.d/` 中移出或禁用：

- `20-main.conf.disabled`
- `30-source.conf.disabled`

保留当前项目在线所需配置：

- `00-default-ssl.conf`
- `40-caniread.conf`

### 4. 校验配置并恢复服务

执行 nginx 配置校验：

```bash
docker run --rm \
  -v /root/gateway-nginx/nginx.conf:/etc/nginx/nginx.conf:ro \
  -v /root/gateway-nginx/conf.d:/etc/nginx/conf.d:ro \
  -v /etc/letsencrypt:/etc/letsencrypt:ro \
  nginx:stable nginx -t
```

校验通过后，重启网关并验证：

```bash
docker restart gateway-nginx
curl -I https://caniread.tlpy8.com
```

最终恢复正常，返回 `HTTP/2 200`。

## 结论

本次事故不是服务器离线，也不是当前项目应用整体损坏。

真正的故障点是：

- 外层公网网关 `gateway-nginx`
- 在重启后加载到了失效的历史 upstream 配置
- 导致 nginx 无法启动

## 后续预防措施

### 1. 只保留当前项目使用的网关配置

`/root/gateway-nginx/conf.d/` 中只保留当前仍在线的配置文件。历史配置统一移到单独目录，不再参与 nginx 启动。

### 2. 配置变更后先执行 nginx 校验

以后修改网关配置前后，必须先执行：

```bash
docker run --rm \
  -v /root/gateway-nginx/nginx.conf:/etc/nginx/nginx.conf:ro \
  -v /root/gateway-nginx/conf.d:/etc/nginx/conf.d:ro \
  -v /etc/letsencrypt:/etc/letsencrypt:ro \
  nginx:stable nginx -t
```

### 3. 排查并移除历史自动化

如果服务器上已不再使用旧项目、旧证书续期方案或旧部署脚本，应继续清理：

- 历史 certbot / letsencrypt 定时任务
- 历史 compose 项目
- 旧项目的自动重启或自动部署逻辑

### 4. 保持配置目录可读性

建议目录结构示例：

```text
/root/gateway-nginx/
  nginx.conf
  conf.d/                # 仅当前在线配置
  conf.d.disabled/       # 历史配置归档
```

## 当前状态

截至本次复盘完成时：

- `gateway-nginx` 已恢复正常
- `caniread.tlpy8.com` 可正常返回 `200`
- 当前项目前后端与数据库容器运行正常
