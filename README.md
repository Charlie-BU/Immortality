# Digital Immortality 使用说明

本文档面向第一次接入 `digital-immortality` 的用户，按实际使用顺序介绍完整流程。

## 0. 环境准备

在开始前，请先满足以下任一条件：

- 已安装 `uv`（推荐）
- 已安装 `Python 3.13+` 环境

安装 `uv`，请在 terminal 执行：

mac / linux:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

windows:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

## 1. 安装 CLI

已安装 uv:

```bash
uv tool install digital-immortality --default-index https://pypi.org/simple
```

未安装 uv:

```bash
pip install digital-immortality -i https://pypi.org/simple
```

安装完成后，重启 terminal，确认命令可用：

```bash
immortality --help
```

## 2. 首次执行健康检查（预期失败）

执行：

```bash
immortality doctor
```

首次检查通常不会通过，这是正常现象。`doctor` 会明确提示缺失项，主要覆盖以下检查：

- `.env` 环境变量是否已配置
- 数据库是否可连接
- Python 版本是否满足要求（`>=3.13`）
- 依赖是否安装完整

## 3. 执行 setup 配置环境变量

执行：

```bash
immortality setup
```

该命令会先让你选择数据库配置方式：

- `Docker setup (recommended)`：推荐。自动拉起 PostgreSQL 并填充本地数据库连接参数
- `Manual setup`：手动填写数据库连接参数（保持旧行为）

当你选择 `Docker setup (recommended)` 时，CLI 会自动完成：

- 检查 `docker` / `docker compose`（兼容 `docker-compose`）
- 在 `~/.immortality/` 写入并使用 docker 资源文件
- 启动 PostgreSQL（镜像为 `pgvector/pgvector:pg16`）
- 确保存在两个数据库：
  - `immortality`
  - `immortality_checkpoint`
- 初始化 `vector` 扩展（`CREATE EXTENSION IF NOT EXISTS vector;`）

然后继续引导你填写其余必要配置，并在本地创建目录：

- `~/.immortality/.env`：环境变量配置文件
- `~/.immortality/logs/`：后续服务运行日志目录
- `~/.immortality/docker-compose.yml`：Docker 模式数据库编排文件

## 4. 再次执行 doctor（预期通过）

配置完成后再次检查：

```bash
immortality doctor
```

理论上此时应通过所有检查项；若未通过，请按输出中的 `guidance` 逐项修复。

## 5. 启动飞书服务

最终启动命令：

```bash
immortality lark-service start
```

说明：

- `lark-service start` 会先自动执行一次 `doctor`
- 如果检查失败，服务不会启动，并直接输出修复提示
- 启动成功后，日志会持续写入 `~/.immortality/logs/`

## 6. Docker 常见问题

### 6.1 collation version mismatch

若你在 `immortality setup`（Docker 模式）看到类似错误：

- `database "... " has a collation version mismatch`
- `template database "template1" has a collation version mismatch`

通常是因为你复用了旧的 PostgreSQL volume（历史镜像与当前镜像底层库版本不一致）。

本地开发建议直接重建 volume（会清空本地数据库数据）：

```bash
docker compose -f ~/.immortality/docker-compose.yml down -v
docker compose -f ~/.immortality/docker-compose.yml up -d postgres
```

然后重新执行：

```bash
immortality setup
immortality doctor
```
