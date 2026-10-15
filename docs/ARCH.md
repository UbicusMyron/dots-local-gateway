# ARCH

Last Reviewed: 2026-10-15

## Product Shape

- Base profile: `custom`
- Capability modules: `none`
- Technology recipe: `none`
- Project fit: 文件配置及常驻服务构成产品，模型能力由现成 Codex 提供。基本连接认证在代理服务内直接实现，运行时依据通道验证选择；上述枚举记录当前模块与技术模板选择状态。

## Architecture Summary

业务 script / Codex → dots 公共调用入口 → 现成连接通道 → 堡垒机 MCP/API 服务 → 第三方。
Secure MCP Tunnel 为首选待验证通道；其客户端在堡垒机主动连接云端、转交请求和回传结果。
代理服务确定性执行请求；Codex 用于主动配置、开发和排障。

## Technology Stack

- Runtime/language: 通道验证后选择最小可维护运行时。
- Frameworks: 根据运行时及 MCP 接入验证结果确定。
- Storage: 本地配置与受限凭证文件。
- External services: OpenAI dots、候选 Secure MCP Tunnel、待选第三方平台。
- Deployment: Mac mini 上常驻服务由 launchd 管理；生产部署在目标与授权明确后开展。

## Module Boundaries

| Module | Responsibility | Owns | Collaboration |
| --- | --- | --- | --- |
| dots 业务 | 意图理解、循环、算法、结果处理 | 业务代码和结果文件 | 通过公共入口调用堡垒机 |
| 公共调用入口 | 程序/工具提交请求和接收结果 | 服务别名目录、调用方连接信息 | 平台认证交由堡垒机，业务计算交由 dots |
| 连接通道 | 请求和响应传输 | 通道状态 | 向堡垒机递交结构化请求 |
| 堡垒机代理 | 基本认证、参数检查、请求、下载 | 平台适配和认证逻辑 | 将业务结果交还 dots |
| 本地凭证配置 | 账户到凭证的对应关系 | 本地凭证和固定目标地址 | 凭证读取权限归属本地服务 |

## Data Model

服务别名与账户别名用于本地凭证路由。请求编号用于关联错误和日志。业务响应和文件允许上云。第三方凭证保存在堡垒机并由本地服务读取。

## Interfaces

- 草案边界见 `docs/CONTRACTS/request.md`（仓库根目录相对路径），线上接口在验证及确认后冻结。
- 接口接收结构化 API 请求，业务程序在 dots 执行。
- MCP 工具调用与脚本程序调用分别验证可达性。
- 文件返回方法、大小边界及异常时的部分结果语义在传输验证后定案。

## Considered Approaches

- 现成隧道 + 确定性服务：复用成熟传输能力，集中维护本地凭证边界。
- Codex 负责主动维护、常驻程序负责请求：自动调用具有直接、可重复的执行路径。
- 业务循环在 dots：业务迭代与凭证服务各自维护。
- 根据 Tunnel 的脚本调用验证结果，可评估带基本认证的 HTTPS 入口；采用备选方案需要确认接入和认证范围。

## Dependency Rules

业务依赖公共请求契约；堡垒机拥有凭证路径和平台认证实现。首版公司连接认证直接服务于当前调用链路。

## Operational Concerns

- Configuration: 配置引用本地秘密文件，仓库保存配置示例及模拟材料。
- Observability: 默认记录请求编号、服务别名、状态和耗时。
- Failure handling: 结果待核实的写操作先核对状态，再决定重试；业务重试决策由 dots 负责。
- Backups/migrations: 真实接入前确定凭证的本地备份及恢复方式。
- Security: 目标采用配置地址；认证字段由本地服务生成。重定向及下载地址逐次校验，凭证随匹配目标发送。认证端点响应由本地适配器消费，业务结果通过独立响应路径返回。
- Availability: launchd 负责启动和退出重启；部署时验证休眠、连接中断和重启后的恢复及凭证读取。

## Tradeoffs

首版采用逐次请求，接受网络往返开销，以保持执行路径简短。业务文件直接按需求上云。已认证公司调用方共享首版开放范围。

## Open Technical Questions

对应 SPEC Q2/Q3：账号可用性、程序调用路径、文件传输、运行时和首个适配器。Tunnel 当前处于候选验证阶段。

## Sources

以下官方资料于 2026-10-15 的方案讨论中查阅，实施时重新核对实际账号与版本：
- https://developers.openai.com/api/docs/guides/secure-mcp-tunnels
- https://learn.chatgpt.com/docs/dots/computers-and-apps
