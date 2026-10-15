# 本机端到端准备 QA

Last Reviewed: 2026-10-15

## 已执行证据

| 检查 | 结果 | 范围 |
| --- | --- | --- |
| 网关核心 | 20 项通过 | GET/POST、认证门控、路由与字段限制、上游错误、超时、文件、凭证隔离、HTTPS 请求行为 |
| 客户端核心 | 13 项通过 | 参数检查、单次提交、错误诊断、文件落盘及摘要 |
| 本地网络集成 | 9 项通过 | 独立服务进程、实际回环 MCP、认证拒绝、请求大小、三次循环、下载、POST、stdio 工具发现与调用、上游错误、秘密隔离、总超时 |
| 依赖检查 | 通过 | MCP 1.30.0 与完整固定版本 requirements-e2e.txt；pip check 通过 |
| launchd 材料 | 通过静态校验 | mock/opencode plist 均通过 plutil -lint |
| 治理检查 | 通过 | constitution check-governance.sh |
| 补丁格式检查 | 通过 | git diff --check |

命令见任务 004。本地网络测试在允许回环端口的执行环境中完成，测试结束后回收服务进程；使用临时模拟凭证和固定上游响应。SDK 的 stdio 返回可能只提供 text content，适配及测试兼容 text 与 structuredContent 两种标准表示。

## 本机准备结果

- 项目 `.venv` 安装了固定版本依赖。
- `macmini_gateway/local/e2e` 包含独立随机公司调用秘密、模拟秘密、mock/opencode 配置、两份 launchd plist、可执行 Tunnel 桥包装脚本。
- 用户已有 `.env` 的内容保持本地，初次准备轮次未读取或导入真实 API key；后续 GitHub 用例已按用户授权将该 key 导入本机受限文件。
- dist 中提供 dots 与本机安装包；打包采用代码与公开说明白名单。凭证与本地运行目录由本机保管。
- OpenCode Go 配置采用实际打开的官方文档所列 `/inference/go/v1/chat/completions` 与 `/inference/go/v1/models`；搜索索引曾显示旧 `/zen/go/v1` 路径，已按打开页面修正。真实上游仍待执行。

## 待实际环境验证

| 验证项 | 状态 / 下一条件 |
| --- | --- |
| launchd 常驻、退出恢复、登录恢复 | 网关与 Tunnel 已 bootstrap，退出后 PID 自动更新并恢复；登录恢复待实测 |
| Secure MCP Tunnel | 已创建并接入，runtime key 验证成功，healthz/readyz 返回 200；云端工具调用待验证 |
| 桌面 Codex 经 Tunnel 调用 | 等 Tunnel 接入 |
| 真实 dots 工具调用 | 等目标 dots 可选择连接 |
| 真实 dots 脚本自主三次请求 | 需确认云脚本访问 Tunnel 的实际地址及认证/工具桥；本地 HTTP 成功仅支持本地结论 |
| 云端文件到达与摘要 | 等真实脚本通道 |
| OpenCode Go 推理 | 准备好导入脚本与短请求入口；需本机导入 key 并选定账号可用模型 |
| 手机发起及双端 request_id 核对 | 等上述链路齐备 |
| 断线、休眠、目标生产 Mac mini 恢复 | 在相应目标环境执行 |

## Sources

- https://developers.openai.com/api/docs/guides/secure-mcp-tunnels
- https://opencode.ai/v2/docs/console/go/

## Tunnel 与常驻接入（2026-10-15）

官方 tunnel-client v0.0.16 已通过受限运行凭证读取用户创建的 Tunnel 元数据并进入 polling；本机 healthz 与 readyz 均返回 200。网关和 Tunnel 使用用户 LaunchAgent 常驻，分别发送 SIGTERM 后均自动恢复为新 PID；恢复后本地三次请求和文件摘要核对通过。当前常驻网关运行 mock 配置，真实 API 与云端调用按独立用例继续验收。

隔离目录中的 dots 安装包通过官方 dev proxy、stdio 桥与独立网关完成三次请求、下载、模拟推理和模拟 GitHub 分页；该证据属于本地模拟通道。运行记录保存于被忽略的 local/e2e 目录：full-simulation.json、resident-recovery.json、tunnel-health-evidence.json。

## GitHub 真实只读预检（2026-10-15）

用户明确指定 CUHK-Business-School-AI-Hub，并授权本机 key 的真实只读请求。命令：`.venv/bin/python scripts/run_github_preflight.py`。

实际链路：业务脚本 → dots_request → 回环 MCP → 独立网关进程 → GitHub HTTPS API。使用固定 org GET 路由，key 由网关本地读取。每页 5 条，共 4 次请求（含空末页），得到 15 个可见仓库，private 6 个、public 9 个。完整结果保存在被 Git 忽略的 `macmini_gateway/local/e2e/github-repositories.json`。

实测首先发现 Python 系统 CA 信任链问题。服务现使用 certifi CA 包，并支持 --ca-file；证书与主机名校验保持启用。证书校验失败归为安全的 UPSTREAM_ERROR，新增回归测试。

回归：20 项网关核心、13 项客户端（含 4 项 GitHub 分页/去重/错误测试）、9 项网络集成，共 42 项通过。真实 GitHub 预检验证组织仓库元数据的读取与 private 标记；手机、Tunnel、真实 dots 脚本仍按独立链路验收。
