# 构建笔记

## 背景

- 服务器配置较低，约 `1.6G` 内存。
- 机器上同时运行了其他业务容器，前端 `Nuxt 3` 生产构建时容易出现 CPU 打满、内存快速上涨、SSH 卡顿的问题。
- 已为服务器增加 `2G swap`，用于降低构建时直接失联的风险。

## 已做调整

- 前端构建命令已在 `frontend/Dockerfile` 中限制 Node 堆内存：

```dockerfile
RUN NODE_OPTIONS=--max-old-space-size=768 npm run build
```

## 服务器稳定构建步骤

在服务器项目目录执行：

```bash
cd /srv/extra-word-from-book/app
```

### 1. 先停止当前项目里非必须在线的容器

优先停止前端与 nginx，给构建腾资源：

```bash
docker compose stop frontend nginx
```

如果允许当前项目后端接口在构建期间短暂停机，也可以继续停止：

```bash
docker compose stop backend
```

说明：

- 一般不建议先停 `postgres`。
- 不要随意停止其他仍在使用中的项目容器。

### 2. 单独构建前端

```bash
docker compose build frontend
```

### 3. 构建完成后启动服务

如果只停了前端与 nginx：

```bash
docker compose up -d frontend nginx
```

如果连 backend 也停了：

```bash
docker compose up -d backend frontend nginx
```

执行完成后建议立即检查状态：

```bash
docker compose ps
```

确认至少以下服务为 `Up`：

- `app-frontend-1`
- `app-nginx-1`

如果此前停止过 `backend`，也要确认：

- `app-backend-1`

## 推荐发布顺序

不要使用一次性全量构建：

```bash
docker compose up -d --build
```

在小内存机器上更稳的方式是分开执行：

```bash
docker compose build backend
docker compose up -d backend
docker compose build frontend
docker compose up -d frontend nginx
```

## 域名出现 502 的处理

本次实际构建过程中，停止 `frontend/nginx` 后，公网域名访问出现过 `502 Bad Gateway`。

这类情况优先检查当前项目服务是否已经重新拉起：

```bash
cd /srv/extra-word-from-book/app
docker compose up -d frontend nginx
docker compose ps
```

如果仍异常，再查看日志：

```bash
docker compose logs --tail=100 frontend
docker compose logs --tail=100 nginx
docker compose logs --tail=100 backend
```

说明：

- 若构建期间停止了 `frontend/nginx`，公网网关可能会暂时返回 `502`。
- 构建完成后重新执行 `docker compose up -d frontend nginx` 可恢复访问。
- 若此前连 `backend` 也停止过，需要一并重新启动。

## 资源检查命令

构建时建议另开窗口观察：

```bash
free -h
docker stats --no-stream
dmesg | tail -n 50
```

关注点：

- `free -h`：观察内存和 `swap` 使用情况。
- `docker stats --no-stream`：观察容器资源占用。
- `dmesg | tail -n 50`：检查是否出现 `Out of memory`、`Killed process`、`oom-killer`。

## 本次验证通过的最小操作

本次已验证可用的最小前端构建与恢复步骤：

```bash
cd /srv/extra-word-from-book/app
docker compose stop frontend nginx
docker compose build frontend
docker compose up -d frontend nginx
docker compose ps
```

## swap 配置记录

已执行：

```bash
fallocate -l 2G /swapfile
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile
echo '/swapfile swap swap defaults 0 0' >> /etc/fstab
```

## 结论

- 当前服务器可以完成构建，但余量较小。
- 前端生产构建必须尽量串行执行，避免与其他高负载任务叠加。
- 如果后续构建仍频繁影响线上稳定性，优先考虑：
  - 升级服务器到至少 `2C4G`
  - 改为本地构建镜像，再推送到服务器运行
