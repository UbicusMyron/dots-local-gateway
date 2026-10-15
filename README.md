# AI Operations Gateway

让 dots 上的业务脚本通过本地 Mac 网关调用第三方 API、获取数据和下载文件。dots 负责业务、循环和分页；Mac 负责连接认证、保管凭证和发送请求。

Last Reviewed: 2026-10-15

```text
用户（手机 / 桌面） → dots 工具或业务脚本
                          ↓
                    dots_request
                          ↓
                    已验证的通道
                          ↓
                  macmini_gateway → 第三方 API
```

## 当前进度与下一步

**现在可以安装 dots 客户端并开展模拟 E2E。当前测试 Mac 的常驻网关运行 mock 配置。**

| 链路 | 已取得的证据 | 下一步 |
| --- | --- | --- |
| 本地 MCP、stdio 桥、客户端 | 核心和网络测试通过 | 在真实 dots 重复验收 |
| 官方 Tunnel 本地模拟 | 隔离目录安装包完成循环、下载、模拟推理和分页 | 验证真实云端路径 |
| 本机常驻与真实 Tunnel | 网关、Tunnel 已由 LaunchAgent 管理，退出恢复通过；Tunnel 认证及健康检查通过 | dots 发起实际工具调用 |
| dots 工具调用 | 待验证 | 添加 Tunnel，发现并调用 gateway_request |
| dots 脚本自主调用 | 待验证 | 确认程序可用的地址、认证或平台工具桥，再执行循环 |
| GitHub 真实只读请求 | 本地预检通过：当时 15 个仓库，6 private、9 public | 切换真实配置后从 dots 重测 |
| OpenCode Go 真实推理 | 路由与测试脚本已准备 | 本机导入 Go key、选择可用模型、完成真实预检 |
| 手机发起完整 E2E | 待验证 | 上述链路齐备后发起两项业务测试 |

Tunnel 就绪证明本机已接入云端；dots 工具和脚本各自以真实调用结果验收。当前运行 key 为 2026-10-15 创建的 7 天测试凭证，管理员按 Platform 显示的到期时间安排更新。完整证据见 [E2E-QA](docs/E2E-QA.md)。

## 人、本机 agent、dots 各自做什么

| 角色 | 负责事项 | 交接结果 |
| --- | --- | --- |
| 用户 / 管理员 | 选择正确的 ChatGPT 工作区；创建并关联 Tunnel；在本机录入凭证；保持测试 Mac 开机、联网、唤醒；手机发起任务 | 工作区、Tunnel ID、测试范围与通过标准 |
| 本机 agent | 检查配置和密钥文件权限；安装、启动、维护网关与 Tunnel；真实 API 本地预检；按阶段切换 mock / real 配置；核对请求日志 | 当前运行模式、健康状态、服务别名、可执行用例与 request_id 证据 |
| dots / 云端 agent | 安装 dots_request；验证工具与程序通道；运行业务循环、分页、下载、汇总；报告失败和实际执行位置 | 请求编号、文件摘要、API 结果、各项通过 / 待验证状态 |

第三方 Go / GitHub key 和 Tunnel runtime key 保存在本机网关。dots 使用工作区工具授权，或已验证程序端点所要求的独立连接凭证。仓库和安装包交付源代码、公开配置示例及说明；实际连接信息通过管理员交接。

## dots 安装：先完成这部分

使用 Python 3.11+。以下命令在 dots 的云电脑执行。

**方式一：仓库安装。** 具备仓库读取权限时：

```sh
git clone https://github.com/UbicusMyron/dots-local-gateway.git
cd dots-local-gateway
python3 scripts/install_dots.py
```

**方式二：安装包。** 本机 agent 执行 `.venv/bin/python scripts/package_e2e.py`，交付 `dist/dots-request-e2e.zip`。dots 解压后进入包含 `dots_request/` 和 `scripts/` 的目录，执行同样的 `python3 scripts/install_dots.py`。dist 是本地生成物；Git 仓库分发代码。

安装后先检查导入与离线模拟：

```sh
.venv/bin/python -m dots_request.examples.mock_businesses
.venv/bin/python -m dots_request.e2e --help
```

此处通过证明客户端可运行。真实网络验收按下面的步骤继续。

## E2E 第一步：dots 工具通道

1. 用户在目标 ChatGPT 工作区的 Plugins 中添加 custom MCP server，Connection 选择 Tunnel，选择管理员已创建的 Tunnel。目标工作区应与手机使用的工作区一致。
2. 根据实际 UI 完成连接配置。当前 stdio 桥在本机读取公司调用凭证；OpenAI Tunnel 的组织和工作区权限负责云端访问。具体操作参考 [官方 Tunnel 指南](https://developers.openai.com/api/docs/guides/secure-mcp-tunnels)。
3. dots 确认已发现 `gateway_request`，在本机 mock 模式下提交下面的工具参数：

```json
{
  "request": {
    "service": "demo",
    "account": "demo_account",
    "method": "GET",
    "path": "/items",
    "query": {"page": "0"},
    "body": null
  }
}
```

4. 保存返回的 `request_id` 和结果；本机 agent 核对日志。两端一致后记录“dots 工具通道通过”。

## E2E 第二步：dots 脚本通道

本仓库的 MCPTransport 连接可达的 Streamable HTTP MCP 端点。**真实 Tunnel 的 dots 脚本访问方式仍待验证**：由 dots 检查目标环境是否提供程序调用工具的桥接能力，或由管理员交付已验证的 MCP URL 与对应连接凭证。当前本地模拟成功并未建立该云端路径。

`127.0.0.1` 指向执行脚本的机器；dots 中该地址指向云电脑。Tunnel ID 用于平台 Tunnel 连接，不能直接作为 CLI 的 `--url`。仅发现 MCP 工具时，记录工具通过和脚本待验证，并报告缺少的程序入口；通道调整按项目契约确认。

**取得已验证的直接 MCP 端点后**，在 dots 配置连接（将占位符替换为实际值）：

```sh
.venv/bin/python -m dots_request.connection configure \
  --url 'YOUR_VERIFIED_MCP_URL' \
  --org CUHK-Business-School-AI-Hub \
  --model 'YOUR_VERIFIED_GO_MODEL'
```

通过隐藏输入录入该端点的连接凭证。程序保存到 `.dots-local/`；已有配置会保留，可用 `--config` 选择新文件。若先只做 mock，可省略 `--model`。

本机 agent 确认 mock 模式后执行：

```sh
.venv/bin/python -m dots_request.connection mock --download gateway-e2e-001.txt
```

验收：脚本自身发出三次 GET，收到三个请求编号；下载文件内容为 `gateway e2e fixture` 加换行，SHA-256 为 `79b019416ce41aff9cdab1cd4fe78f20f1cc36c2c7c0fa503e8cb4deb03cb775`。重复执行时选择新的下载文件名。

若采用平台程序工具桥，由 dots 按该桥实际接口接入客户端 Transport，并运行相同业务验收；实现与证据随契约更新。

## E2E 第三步：两个真实业务

本机 agent 先完成 OpenCode key 导入、可用模型确认和真实预检，再将常驻网关切换为同时包含两项服务的 `real.json`。真实配置需要对应凭证齐备，运行方式详见 [运行手册](docs/E2E-RUNBOOK.md)。

在 dots 已验证的程序通道上执行：

```sh
.venv/bin/python -m dots_request.connection opencode
.venv/bin/python -m dots_request.connection github
```

- OpenCode：一次非流式短请求，报告模型、request_id、实际回复；预期回复 `GATEWAY_E2E_OK`，另外核对文本是否匹配。
- GitHub：遍历 `CUHK-Business-School-AI-Hub` 当前凭证可见的仓库元数据，输出名称、URL、private、总数和每页 request_id。本地旧结果仅作参考，按这次响应验收。
- 手机：登录同一工作区，要求 dots 在云电脑执行上述用例，再由本机 agent 核对日志。记录发起端、执行机器、时间与结果。

## 可以直接交给 dots 的任务

> 阅读本仓库 README、docs/CONTRACTS/e2e-v1.md 和 docs/E2E-QA.md。在你的云电脑安装 dots_request，先运行离线模拟，再确认工作区中的 gateway_request 工具并执行一次 demo 请求。随后检查脚本自主调用该工具或 MCP 端点的实际能力；取得可用程序入口后，由脚本完成三次请求及文件下载。第三方凭证归本机网关保管。报告工具调用和脚本调用各自的实际证据；缺少入口时明确说明缺什么。待本机 agent 确认真实配置就绪，再执行 OpenCode 与 GitHub 用例，返回 request_id、文件摘要、推理回复及仓库 private 标记。每项分别记录通过、失败或待验证。

## 本机 agent 接续与排障

先读 [AGENTS.md](AGENTS.md)、[SPEC](docs/SPEC.md)、[ARCH](docs/ARCH.md)、[RULES](docs/RULES.md)，再读 [任务 005](docs/TASKS/005-e2e-handoff.md) 和 [E2E 契约](docs/CONTRACTS/e2e-v1.md)。新机器按运行手册准备；已有测试机器先检查当前进程和配置，复用已安装资源。

当前测试机的服务 label 为 `com.cuhk.macmini-gateway.e2e` 和 `com.cuhk.macmini-tunnel.e2e`。运行材料、日志和证据位于 Git 忽略的 `macmini_gateway/local/e2e/`。`tunnel-health.url` 记录当前回环健康地址；检查 `/healthz`、`/readyz` 和实际 polling 状态，结合真实请求判断链路。

| 现象 | 下一步 |
| --- | --- |
| runtime key 已存在 | 首次录入已保存，沿用现有文件；轮换单独安排 |
| dots 看不到 Tunnel | 核对工作区关联、组织和 Read + Use 权限 |
| 工具可用、脚本无法连接 | 检查平台程序工具桥或已验证的 MCP 端点；分别记录证据 |
| DESTINATION_EXISTS | 选择新的下载路径 |
| AUTH / HTTP 401 | 核对正在使用的连接身份与端点 |
| TIMEOUT / UPSTREAM_ERROR | 通过 request_id 核对本机日志及执行状态，再决定重试 |
| 本机重启、休眠或网络中断 | 检查两项服务、Tunnel 就绪状态，再重复代表性请求 |

生产验收还需在目标 Mac mini 验证服务账户、登录/开机恢复、休眠与断线恢复，以及真实 dots 工具、脚本和文件链路。当前版本的完成范围以 QA 证据为准。
