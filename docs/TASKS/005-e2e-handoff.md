# Task: 补齐安装与通道交接

Last Reviewed: 2026-10-15

状态：执行中。用户要求补齐全部前置链路并模拟验证；Platform 登录、Tunnel 创建与工作区关联由实际账号条件推进。

## Goal

完成本机常驻与恢复、官方 Tunnel 客户端模拟、dots 安装入口和可核对的交接状态。

## Source Context

SPEC 的脚本自主请求与本地凭证边界；任务 004；本轮用户的完整链路授权。

## Scope

本地安装工具、dots 连接配置与运行入口、模拟验收、真实服务预检、Tunnel 接入及交接文档。账号访问依实际 UI 和权限完成。

## Interfaces

- Consumes: 已有 MCP 服务与客户端，官方 tunnel-client，目标 Platform 组织及 ChatGPT 工作区。
- Produces: 可安装的 dots 材料、运行状态与模拟证据。
- Public contracts touched: docs/CONTRACTS/e2e-v1.md 的安装与连接条件。
- Downstream tasks relying on this: 手机端真实 dots 联合验收。

## Acceptance Criteria

安装包在隔离目录执行三次请求及文件核对；常驻退出恢复后可调用；真实调用路径与模拟证据分别标识；可用连接信息齐备后交接 dots 安装。

## Verification

- Command: `.venv/bin/python -m unittest discover -s tests -v`
- Command: `bash /Users/myron/.codex/skills/constitution-skill/scripts/check-governance.sh .`
- Expected evidence: 相关测试通过、实际常驻与 Tunnel 模拟记录、账号未完成条件明确记录。

## Governance Drift Check

- SPEC changed? 维持原业务与凭证职责。
- ARCH changed? 通道依据实际验证确认。
- CONTRACTS changed? 安装连接参数同步记录。
- RULES/AGENTS changed? 沿用现有规则。
