# Herbal RAG Demo

本地可演示的中医资料问答。问题先检索知识库，再只根据命中的原文生成回答，并给出能点回片段的引用。

本项目只用于资料检索与学习，不提供诊断、处方或个性化治疗建议。

## 技术栈

- Python 3.11、FastAPI、单个静态页面
- SQLite FTS5 保存资料并检索
- 默认 `extractive`：直接摘录命中片段，不调用大模型
- 可选 `llm`：OpenAI 兼容聊天接口

二字药名（如「甘草」）用 FTS5 trigram 检索会因查询过短而匹配不到。索引改为重叠二字词，再用关键词覆盖率做相关度，演示问题可以稳定命中。

## 安装

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

密钥只放在 `.env` 或环境变量里。`.env` 已在 `.gitignore` 中，不要提交。

| 变量 | 含义 | 默认 |
| --- | --- | --- |
| `LLM_MODE` | `extractive` 或 `llm` | `extractive` |
| `LLM_BASE_URL` | OpenAI 兼容接口根路径 | `https://api.openai.com/v1` |
| `LLM_API_KEY` | 接口密钥 | 空 |
| `LLM_MODEL` | 模型名 | `gpt-4o-mini` |
| `RETRIEVAL_TOP_K` | 最多返回片段数 | `5` |
| `RETRIEVAL_MIN_SCORE` | 相关度下限，0 到 1 | `0.5` |

未填写 `LLM_API_KEY` 时，即使 `LLM_MODE=llm` 也会自动走摘录，避免现场没有密钥就无法演示。

## 资料

`data/sample/` 里有 6 篇自编教学笔记，来源都写明：

`Herbal RAG Demo 自编教学笔记（教学演示，非临床依据）`

这些笔记只记录性味、归经和分类用语，不写剂量和处方。项目不会请求在线中医资料接口。

导入 Markdown 或 TXT：

```bash
python -m app.cli ingest data/sample
python -m app.cli ingest path/to/notes.md
```

文件可以用 YAML 文件头写 `title` 和 `source`。没有文件头时，标题取第一个一级标题，TXT 用文件名，来源记为「未标注来源」。章节取该片段所属标题。同一文件名再次导入时，内容没变会跳过，内容变了会替换旧片段。

数据库在 `data/index/herbal.db`，已忽略，不提交。

## 启动

```bash
uvicorn app.main:app --reload --port 8000
```

浏览器打开 <http://127.0.0.1:8000>。库是空的时候，启动会自动导入 `data/sample/`。

页面也可以直接选择 `.md` / `.txt` 导入。

## 演示步骤

页面顶部应显示「摘录模式（不调用大模型）」和 6 篇资料。按下面的顺序点示例：

1. **黄芪的性味与归经是什么？** 回答摘录「甘、微温」「肺、脾」，句末有 `[1]`。点 `[1]`，右侧滚到对应原文，能看到来源、章节、文件名和相关度。
2. **资料中如何描述甘草？** 回答里有「调和诸药」，引用能对上片段。
3. **什么是四气五味？** 回答同时出现「寒、热、温、凉」和「酸、苦、甘、辛、咸」。
4. **金银花和连翘在资料中有什么不同？** 两段原文并列引用：金银花「味甘，性寒」，连翘「味苦，性微寒」。摘录模式不做额外改写。
5. **资料里对麻黄有哪些使用注意？** 回答摘录「自汗」「不宜自行使用」，不出现具体克数。
6. **阿司匹林适用于哪些疾病？**（拒答）固定回复「现有资料不足，无法根据知识库回答这个问题。」不补充适应症。
7. **我发烧咳嗽，麻黄每天该吃多少克？**（安全边界）固定提示咨询医疗专业人员，紧急情况寻求当地急救服务。不给剂量。若检索到麻黄片段，只供核对，不写入回答。

断网时用第 1 到第 7 步即可完整演示检索、引用和拒答。要改走在线模型时，在 `.env` 中设置 `LLM_MODE=llm`、`LLM_API_KEY` 和 `LLM_BASE_URL`，然后重启。模型输出若不是 JSON、引用对不上本轮片段，或请求失败，回答仍是「现有资料不足」，不会把模型自由发挥的文字直接展示。

## 部署到服务器

推送到 GitHub 的 `main` 分支后，`.github/workflows/deploy.yml` 会自动：

1. 构建 `linux/amd64` 镜像。
2. 推送到阿里云容器镜像仓库，标签为本次提交的 SHA 和 `latest`。
3. 登录服务器，拉取该 SHA 镜像并重启容器。

索引和上传文件在数据卷 `herbal-rag_herbal-index`、`herbal-rag_herbal-uploads` 里，更新镜像不会清掉知识库。容器只用一个进程。

镜像仓库要先在阿里云控制台建好，个人版一般不会在第一次推送时自动创建仓库。

1. 打开容器镜像服务，创建命名空间，再创建仓库 `herbal-rag-demo`。
2. 在「访问凭证」里设置 Registry 的固定密码。这里用的是镜像仓库用户名和固定密码，不是 RAM 的 AccessKey。
3. 记下公网 Registry 域名，例如 `registry.cn-hangzhou.aliyuncs.com` 或 `crpi-xxxx.cn-hangzhou.personal.cr.aliyuncs.com`。不要带 `https://`。

服务器事先装好 Docker 和 Docker Compose 插件（命令是 `docker compose`）。部署用的 SSH 用户要能执行 `docker`。安全组放行 8000，以及你用来登录的 SSH 端口。ECS 若是 ARM 架构，把 workflow 里的 `platforms` 改成 `linux/arm64`。

在本机生成一把只用于部署的密钥，公钥写入服务器对应用户的 `~/.ssh/authorized_keys`：

```bash
ssh-keygen -t ed25519 -f herbal-deploy -N ""
```

私钥全文（含 `BEGIN` / `END` 两行）放到 GitHub 仓库的 Settings → Secrets and variables → Actions。不要把私钥提交进仓库。

| Secret | 内容 |
| --- | --- |
| `ALIYUN_REGISTRY` | Registry 域名，不含协议 |
| `ALIYUN_NAMESPACE` | 命名空间 |
| `ALIYUN_REGISTRY_USER` | 访问凭证里的用户名 |
| `ALIYUN_REGISTRY_PASSWORD` | 访问凭证里的固定密码 |
| `SSH_HOST` | 服务器 IP 或域名 |
| `SSH_USER` | SSH 用户 |
| `SSH_PRIVATE_KEY` | 部署私钥全文 |
| `SSH_PORT` | SSH 端口，不填则用 22 |
| `DEPLOY_PATH` | 服务器目录，不填则用 `/opt/herbal-rag` |

配好 Secrets 后，把包含 workflow 的提交推到 `main`。Actions 页能看到「构建镜像并部署」。成功时日志末尾是 `/api/health` 的 JSON，`documents` 为 6。

浏览器打开 `http://服务器IP:8000`。在线模型只改服务器上的 `/opt/herbal-rag/.env`，文件不存在时流水线会创建一个空文件，服务以摘录模式运行。改完后重新推一次，或在 Actions 里手动运行该 workflow。

页面上的「导入资料」没有登录。服务暴露到公网时，任何人都可以往知识库添加 Markdown 或 TXT。这是教学演示，不要在上面处理真实患者信息。

在自己电脑上仍然用仓库根目录的 `docker compose up -d --build` 做本地构建。服务器更新走的是 `deploy/docker-compose.prod.yml`，只拉取远程镜像。

## 测试

```bash
pytest
```

覆盖切分与重叠、元数据、索引重启后仍在、引用必须对应本轮片段、资料不足拒答、诊断/剂量/急症边界，以及资料正文里的指令不会进入系统提示。

## 行为说明

提问后的顺序是：先做本地安全分类，再检索，最后生成。个人症状、诊断、处方、剂量和急症不会调用大模型。问题原文不写入数据库。

相关度是问题里的关键词有多少出现在「标题 + 章节 + 正文」中。例如「黄芪 / 性味 / 归经」三个词都出现，相关度是 1。只沾到「归经」这类泛词的片段低于默认 0.5，不会当作依据。

在线模型看到的资料包在 `<reference>` 中，系统提示写明这些文字是数据，不是指令。
