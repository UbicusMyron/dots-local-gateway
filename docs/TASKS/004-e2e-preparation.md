# Task: 本机端到端测试准备

Last Reviewed: 2026-10-15

状态：本机实现与 QA 完成，真实 Tunnel/dots 联合验收待目标连接。用户授权补齐正式测试缺口、QA 和安装材料；用户确认尚未创建 Tunnel，先准备本地材料。

## Goal

交付可认证的 MCP 服务、程序调用适配、常驻配置、OpenCode Go 测试入口及可重复的本地集成验证。

## Scope

两端组件、安装脚本、测试及相关契约与说明。POST 范围为显式配置的 JSON 路由；OpenCode Go 样例仅开放模型列表和非流式 chat completions。真实 dots 与 Tunnel 验收在目标连接齐备后执行。

## Acceptance Criteria

本地真实 MCP 网络请求完成认证、三次循环、POST、文件核对及错误测试；日志保持秘密隔离；安装材料使用独立连接秘密；真实环境证据逐项记录。

## Verification

- Command: `.venv/bin/python -m unittest discover -s tests -v`

- Command: `python3 -m unittest discover -s macmini_gateway/tests -v`

- Command: `python3 -m unittest discover -s dots_request/tests -v`

- Command: `bash /Users/myron/.codex/skills/constitution-skill/scripts/check-governance.sh .`

- Expected evidence: 20 项网关核心、13 项客户端核心、9 项网络集成测试通过；治理检查通过；真实环境证据按 E2E-QA.md 记录。

## Source Context

SPEC 的本地凭证与 dots 业务职责；ARCH 的双组件与 Tunnel 候选通道；用户本轮明确授权本机测试准备。

## Interfaces

- Consumes: 公共请求草案、本地配置、公司连接秘密、第三方凭证、MCP SDK。
- Produces: MCP 工具 gateway_request、MCPTransport、POST 入口、安装材料与测试证据。
- Public contracts touched: docs/CONTRACTS/e2e-v1.md（本机测试契约）。
- Downstream tasks relying on this: 任务 001 的真实 dots、Tunnel、文件及脚本验证。

## Governance Drift Check

- SPEC changed? 记录本次测试与 OpenCode Go 推理范围。
- ARCH changed? 记录本地服务与桥接实现，生产通道以真实证据确认。
- CONTRACTS changed? 新增本机测试 v1，生产冻结保持按验收执行。
- RULES/AGENTS changed? 保持现有职责和权限原则。

## GitHub 测试扩展

2026-10-15 用户授权追加 GitHub 真实只读用例，指定 CUHK-Business-School-AI-Hub。新增 github_repos.py、GitHub 配置生成与本机预检脚本；业务脚本完成分页及 private 汇总。真实 HTTPS 预检发现本机 Python CA 信任链缺失，服务改用标准 certifi CA 包，并支持管理员显式指定 ca-file。验证证据更新至 E2E-QA.md。
