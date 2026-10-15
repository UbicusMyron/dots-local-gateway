# Task: dots_request 调用核心与模拟验证

Last Reviewed: 2026-10-15

状态：调用核心已完成；真实通道适配在任务 001 和最小契约定案后验收。

## Goal

交付业务脚本可复用的 GET 调用、响应消费、文件保存、配置及公共 skill，以模拟网关验证。

## Source Context

用户于 2026-10-15 明确要求实现 dots_request。依据 SPEC、ARCH、RULES 和 request 草案，独立推进与通道无关的调用核心。任务 001 的真实连接证据仍待补齐。

## Scope

- dots_request：标准库 Python 客户端、配置示例、两个业务用例、模拟测试、README 和公共 skill。
- AGENTS、SPEC、ARCH、DEVELOPMENT：同步本轮授权与实际实现状态。
- 本任务与调用端本地证据：记录实际命令和边界。
- 稳定线上接口以通道验证与范围确认作为冻结条件；本轮 Python 注入接口用于模拟开发，真实平台、认证机制和部署按各自任务推进。

## Interfaces

- Consumes: request.md 草案的 GET 字段、显式别名配置及注入 Transport。
- Produces: 业务数据、结构化错误、大小与摘要校验后的本地文件。
- Public contracts touched: 共享请求契约保持草案；暂定 Python 适配器边界见 dots_request/README.md。
- Downstream tasks relying on this: 已验证通道的适配器、真实 dots 联合验收。

## Acceptance Criteria

- 两个业务用例共用入口，业务脚本完成三次分页请求及一次下载。
- 非法别名、路径和参数在提交前反馈；错误响应可按代码及请求编号定位。
- 超时及传输异常按安全诊断反馈；每次调用提交一次。
- 下载校验大小和摘要；完整文件原子发布，已有文件及符号链接得到保护。
- 使用模拟秘密检查返回、请求及异常诊断；真实秘密由堡垒机管理。

## Verification

- Command: `python3 -m unittest discover -s dots_request/tests -v`
- Command: `python3 -m dots_request.examples.mock_businesses`
- Command: `python3 /Users/myron/.codex/skills/.system/skill-creator/scripts/quick_validate.py dots_request/skills/dots-request`
- Command: `bash /Users/myron/.codex/skills/constitution-skill/scripts/check-governance.sh .`
- Expected evidence: 单元测试和双业务模拟通过；skill 校验及治理检查结果见 docs/DOTS-REQUEST-EVIDENCE.md，真实通道证据独立记录。

## Governance Drift Check

- SPEC/AGENTS：记录用户本轮授权及调用核心阶段。
- ARCH：记录本地 Python 运行时与组件落盘状态。
- CONTRACTS：共享线上契约保持设计草案；文件 bytes 为 Python 内存表示。
- RULES：继续遵循既定职责和模拟验证边界。
