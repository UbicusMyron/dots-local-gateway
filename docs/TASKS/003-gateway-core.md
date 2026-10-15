# Task: macmini_gateway 本地只读核心

Last Reviewed: 2026-10-15

状态：本地模拟实现完成；正式传输及生产验收依赖任务 001。

## Goal

依据用户本轮“实现 macmini_gateway”的授权，交付可独立验证的本地执行核心。通道、公司认证机制及稳定接口依据任务 001 的验证结果确认。

## Scope

- Touch: macmini_gateway/ 的核心、离线演示、配置样例、测试与说明；本任务及阶段入口。
- 输入：SPEC、ARCH、RULES、公共请求草案。
- 输出：固定目的地 GET 请求、凭证路由、JSON 与有界下载、输出检查。
- 当前 Python 内部接口使用可信适配器认证结论；公司连接认证由后续选定通道提供并验证。
- 正式网络接口及文件表示在共享契约确认后冻结。此任务实现以模拟边界为准。

## Source Context

- docs/SPEC.md：凭证归属、结构化调用和组件验收。
- docs/ARCH.md：网关职责与通道验证顺序。
- docs/RULES.md：模拟输入、输出检查及验证证据。
- docs/CONTRACTS/request.md：待确认的公共请求草案。

## Interfaces

- Consumes: 显式路径配置、管理员维护的本地凭证、内部结构化 GET 请求及可信适配器认证结论。
- Produces: JSON 业务数据、模拟文件表示、请求编号与固定错误反馈。
- Public contracts touched: None；共享契约保持草案状态。
- Downstream tasks relying on this: 任务 001 的服务接线、dots_request 适配及双端联合验收。

## Acceptance Criteria

- 模拟调用方通过认证门控后执行配置业务路由。
- 两个账户的凭证独立路由；无效输入在上游调用前拒绝。
- 模拟 JSON 与文件可核对；异常反馈及日志通过模拟秘密隔离检查。
- 真实链路各项验证按实际证据单独标记。

## Verification

- Command: `python3 -m unittest discover -s macmini_gateway/tests -v`
- Command: `python3 -m macmini_gateway`
- Command: `bash /Users/myron/.codex/skills/constitution-skill/scripts/check-governance.sh .`
- Expected evidence: 16 项测试通过，演示连续三次请求及下载摘要通过；治理结构检查通过。


2026-10-15 本地验证：

- `python3 -m unittest discover -s macmini_gateway/tests -v`：16 项通过。
- 覆盖默认认证拒绝、三次脚本循环、双账户认证路由、目标与查询校验、重定向、上游错误、超时、大小限制、文件内容与摘要、秘密隔离、凭证权限及符号链接。
- HTTPS 传输通过替换连接对象验证请求、分块读取、大小限制与关闭行为；证书和真实网络连通性由后续真实链路验证。
- `python3 -m macmini_gateway`：离线模拟三次请求与一次下载，内容和 SHA-256 核对通过。
- 本地 MCP：待接入与验证。
- 桌面 Codex 经通道调用：待验证。
- 真实 dots 工具调用及脚本循环：待目标环境验证。
- Mac mini launchd 恢复与双端联合验收：待服务入口及目标部署验证。

## Handoff

本地文件格式与 INVALID_RESPONSE 为组件内部实验约定。稳定接口冻结时同步核对 dots_request；实际平台认证刷新在平台及认证方式明确后实施。真实凭证接入、第三方写操作与生产部署按已记录的范围确认流程开展。

## Governance Drift Check

- SPEC/ARCH/RULES/AGENTS：沿用现有边界，正式服务实现仍依赖通道验证。
- CONTRACTS：维持设计草案；内部测试约定记录在组件 README。
- DEVELOPMENT：记录用户授权先行完成的本地核心及后续依赖。
- 治理检查：原验证记录存在 1 项 Non-Goals 标题差异；2026-10-15 文档修复增补治理章节及写作豁免，复核通过。实质范围保持一致。
