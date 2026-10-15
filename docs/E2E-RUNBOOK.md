# 本机与个人 dots 联合测试

Last Reviewed: 2026-10-15

## 当前准备范围

本机模拟 Mac mini，常驻服务处理认证和第三方调用；dots 云电脑运行脚本；手机发起任务。当前测试机已接入真实 Tunnel，网关与 Tunnel 已常驻并通过退出恢复测试，网关当前运行 mock 配置。GitHub 本地真实预检已通过；OpenCode 真实调用和 dots 云端工具、程序通道待验收。最新角色分工及交接顺序见 [项目 README](../README.md)，执行证据见 [E2E-QA](E2E-QA.md)。以下初始化步骤用于新环境，已有环境先检查并复用现有材料。

## 本机安装

在仓库根目录执行（Python 3.11+）：

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-e2e.txt
.venv/bin/python scripts/prepare_e2e.py
```

prepare 已在本机生成 `macmini_gateway/local/e2e`，再次运行需选择新的空目录。该目录权限 0700，凭证 0600，位于 Git 忽略范围。

先前台运行模拟服务：

```sh
.venv/bin/python -m macmini_gateway.server --config macmini_gateway/local/e2e/mock.json --caller-secret macmini_gateway/local/e2e/caller.secret --mock
```

另一终端运行：

```sh
.venv/bin/python -m dots_request.e2e --url http://127.0.0.1:8765/mcp --caller-secret macmini_gateway/local/e2e/caller.secret --download macmini_gateway/local/e2e/result.txt
```

文件目标使用新路径。成功输出三个不同请求编号和下载 SHA-256。

## 常驻服务

准备程序生成含绝对路径的 `gateway-mock.plist` 与 `gateway-opencode.plist`，共用 label 与端口，按阶段加载其中一个。退出前台服务后执行：

```sh
launchctl bootstrap "gui/$(id -u)" "$PWD/macmini_gateway/local/e2e/gateway-mock.plist"
launchctl print "gui/$(id -u)/com.cuhk.macmini-gateway.e2e"
```

退出恢复验证：记录当前 pid，对该 pid 执行 `kill -TERM`，等新 pid 出现，再执行模拟脚本。结束时：

```sh
launchctl bootout "gui/$(id -u)/com.cuhk.macmini-gateway.e2e"
```

此为当前登录用户 LaunchAgent；持续跨登录启动时，将选定 plist 安装到 `~/Library/LaunchAgents/`。专用服务账户、无人登录启动及生产机器恢复属于生产部署验收。保留 `service.log` 中的请求编号、状态和耗时作为证据。

## Tunnel 准备

依据官方指南，在 Platform 创建 Tunnel，赋予运行身份 Read + Use，关联目标 ChatGPT 工作区；本机安装官方 tunnel-client，使用独立 OpenAI runtime key。Go key 与 Tunnel runtime key 分别配置。

常驻服务运行后，Tunnel 的 stdio 命令使用项目虚拟环境 Python 和模块 `macmini_gateway.tunnel_stdio`，参数为 `--caller-secret <绝对文件路径>`。工作目录通过包装脚本固定，以支持含空格的项目路径。

```sh
tunnel-client init --sample sample_mcp_stdio_local --profile gateway-e2e --tunnel-id YOUR_TUNNEL_ID --mcp-command '/absolute/path/to/tunnel-bridge.sh'
tunnel-client doctor --profile gateway-e2e --explain
tunnel-client run --profile gateway-e2e
```

准备程序已生成可执行的 `macmini_gateway/local/e2e/tunnel-bridge.sh`；将该绝对路径用于 mcp-command。脚本结构如下：

```sh
#!/bin/sh
cd '/absolute/project/path' || exit 1
exec '/absolute/project/path/.venv/bin/python' -m macmini_gateway.tunnel_stdio --caller-secret '/absolute/project/path/macmini_gateway/local/e2e/caller.secret'
```

Tunnel runtime key 由管理员在本机按官方客户端配置方式录入。创建连接后先用桌面工具调用一次 gateway_request，再在 dots 中调用，核对本机相应 request_id。当前测试机已安装 com.cuhk.macmini-tunnel.e2e LaunchAgent；新机器依据实际 profile、二进制和凭证路径生成配置。

## dots 安装与程序通道验证

仅向 dots 交付 `dots_request/`、`requirements-e2e.txt`、本说明及公开服务别名。第三方配置和凭证由本机维护。

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-e2e.txt
```

脚本入口使用 `python -m dots_request.e2e`。MCPTransport 支持可达的 HTTPS MCP 端点，Bearer 凭证为该端点认可的公司连接凭证。`127.0.0.1` 仅用于本机 QA。

**待账号实测：**官方公开说明确认 Tunnel 的受支持产品调用路径；当前材料尚未建立 dots 云脚本直接调用该 Tunnel 的地址与认证方式。拿到 Tunnel 后先验证此路径；若平台仅开放工具调用，则记录工具通过、脚本待验证，依据实际能力接入平台工具桥或确认备用通道。以脚本自主完成三次请求作为该项通过条件。模型代替脚本逐次点工具的结果单独归入工具证据。

## OpenCode Go 实测准备

在本机选择 .env 中对应变量名，导入脚本只读取并写入本地文件，输出固定状态：

```sh
.venv/bin/python scripts/import_opencode_secret.py --env-file .env --variable YOUR_GO_KEY_VARIABLE --destination macmini_gateway/local/e2e/opencode.secret
```

停止模拟服务，加载 `gateway-opencode.plist`。确认当前 Go 文档的 endpoint 和账号支持的 chat/completions 模型。执行一次短请求：

```sh
.venv/bin/python -m dots_request.e2e --url http://127.0.0.1:8765/mcp --caller-secret macmini_gateway/local/e2e/caller.secret --mode opencode --model YOUR_CHAT_COMPLETIONS_MODEL_ID
```

本机执行用于验证真实上游；dots 执行需改用已验证的云端可达连接。max_tokens 为 32，stream 为 false，每次执行发送一个推理请求；请求消耗 Go 用量。响应文案与预期标记另行核对，HTTP 成功本身作为链路证据。

## 手机发起文案

“请在你的云电脑运行已安装的 dots_request 端到端测试脚本，先完成三次模拟请求和一个小文件下载。报告运行所在机器、三个请求编号及文件 SHA-256。然后使用已配置的 OpenCode Go 服务和选定模型执行一次短请求，报告请求编号和回复。”

## 验收记录

分别保存本地 MCP、stdio 桥、桌面工具、dots 工具、dots 脚本循环、文件摘要、真实推理、常驻退出恢复和断线恢复证据。真实运行前先明确脚本通道是否可达。上生产前在目标 Mac mini 重复权限、启动与恢复验证。

## Sources

- https://developers.openai.com/api/docs/guides/secure-mcp-tunnels
- https://learn.chatgpt.com/docs/dots/computers-and-apps
- https://opencode.ai/docs/go/
- https://github.com/modelcontextprotocol/python-sdk

## 第二个真实用例：GitHub 仓库清单

目标组织为 `CUHK-Business-School-AI-Hub`，用户已授权使用本机 fine-grained key 进行只读测试。当前 key 已从本地材料导入 `macmini_gateway/local/e2e/github.secret`（0600）；测试输出使用仓库元数据与请求编号。

新增环境使用以下命令生成精确组织 GET 路由，凭证由管理员放入同目录的 github.secret：

```sh
.venv/bin/python scripts/prepare_github_e2e.py --org CUHK-Business-School-AI-Hub
```

当前本机已生成 github.json 与 real.json。前者用于独立 GitHub 验收，后者组合 OpenCode Go 与 GitHub，适合两项真实用例共用同一常驻服务；启动 real.json 时两份第三方凭证均需齐备。

单独 GitHub 服务：

```sh
.venv/bin/python -m macmini_gateway.server --config macmini_gateway/local/e2e/github.json --caller-secret macmini_gateway/local/e2e/caller.secret
```

业务脚本（本机先用回环地址，dots 实测改为已验证的云端可达连接）：

```sh
.venv/bin/python -m dots_request.e2e --url http://127.0.0.1:8765/mcp --caller-secret macmini_gateway/local/e2e/caller.secret --mode github --org CUHK-Business-School-AI-Hub --per-page 5
```

脚本逐页 GET 组织仓库列表，按 ID 去重，输出 full_name、html_url、private、总数、公私数量及各页 request_id。空结果合法；错误、重复页、异常字段及达到页数保护上限均返回失败。complete 表示本次分页遍历到末页；结果反映该 token 当时能读取的组织仓库元数据。代码内容权限另有独立接口和权限要求。

可重复本机预检：`.venv/bin/python scripts/run_github_preflight.py`，自动创建并回收临时 MCP 服务，结果写入本地 `github-repositories.json`。此命令执行真实只读请求。

手机补充文案：“再运行 GitHub 用例，列出 CUHK-Business-School-AI-Hub 中当前 key 可见的全部仓库，标出 private，报告总数、公私数量与每页请求编号。”

服务的真实 HTTPS 请求默认使用 certifi CA 包，管理员可通过 `--ca-file` 指定受信任证书包，证书及主机名校验持续启用。

参考：https://docs.github.com/en/rest/repos/repos#list-organization-repositories
