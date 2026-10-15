# Task: 验证 dots 与堡垒机的最小请求通道

Last Reviewed: 2026-10-15

状态：待执行任务草案；本轮交付为文档。账号、目标 Mac mini、通道访问及执行授权为启动条件。

## Goal

用模拟工具验证真实 dots 的 AI 和程序请求堡垒机，并取得模拟数据及小文件；按证据记录可用能力、待补齐条件和后续接入选择。

## Source Context

- docs/SPEC.md：脚本自主调用和凭证边界。
- docs/ARCH.md：候选隧道及模块职责。
- docs/RULES.md：测试数据和部署范围。
- docs/CONTRACTS/request.md：请求边界草案。

## Scope

### Touch

- macmini_gateway 中一个模拟 MCP 服务探针。
- dots_request 中一个调用探针，包含三次循环及结果核对；两个组件合计最多两个代码文件。
- docs/CONTRACTS/transport-probe.md：执行前补充实际探针命令和认证方式。
- docs/TRANSPORT-EVIDENCE.md：测试证据。
- 本任务状态。

### Size Justification

本任务为单条跨组件连接验证，触及两个顶层组件，以最小服务探针和调用探针组成一个联合验证单元。代码合计最多两个文件、约 300 行，连同契约、证据及任务状态合计最多五个文件。正式组件实现归入后续分组件任务。

### Execution Boundary

- 本任务使用模拟凭证、模拟数据及模拟 GET 接口。
- 真实平台接入、生产部署、写操作和业务插件归属后续明确授权的任务。
- 首版认证单位为公司调用方，业务循环由 dots 脚本执行。

### Public Contracts

- Change scope: 模拟探针契约。
- Production contract gate: 公司生产请求或认证接口在独立范围确认及验证后冻结。

## Interfaces

- Consumes: 官方 Tunnel 文档、目标账号的实际能力和本地模拟服务。
- Produces: 经验证的调用路径和各项条件的证据。
- Public contracts touched: 模拟工具；命令及精确结构在选定运行时后补充探针契约。
- Downstream tasks relying on this: macmini_gateway、dots_request 的正式实现与真实平台接入；阶段路线见 docs/DEVELOPMENT.md。

## Requirements

- 执行前确认可访问的目标 dots、Mac mini 和工作区，使用模拟秘密。
- 检查现有资源与权限，确定运行时，补齐精确命令后将本任务标为 Ready。
- 通过模拟标记和请求编号证明请求实际经过堡垒机。
- 脚本自主执行三次循环请求。
- 模拟文件以内容摘要进行核对。

## Acceptance Criteria

- 真实 dots 工具调用成功，并有本地对应请求记录。
- dots 脚本自主连续三次调用成功。
- 模拟下载内容一致；返回与日志通过模拟秘密隔离检查。
- 公司调用认证通过后执行，其他认证状态返回对应校验反馈，并记录处理层及证据。
- 证据逐项标记通过、异常或待验证；本任务以全部验收项通过作为完成条件。

## Verification

- Command: `bash /Users/myron/.codex/skills/constitution-skill/scripts/check-governance.sh .`
- Expected evidence: 治理结构检查通过。端到端能力以目标环境调用证据验收。
- 端到端命令：确定运行时与脚本调用方式后，在 docs/CONTRACTS/transport-probe.md 写入精确命令、环境、预期输出，随后进入 Ready。
- Execution status: 待执行项目标明所需条件，已执行项目记录命令、结果和证据。

## Governance Drift Check

- SPEC changed? 保持脚本自主调用目标，记录验证结果及待解决条件。
- ARCH changed? 更换通道时说明依据及认证影响。
- CONTRACTS changed? 通过测试并确认范围后冻结接口。
- RULES/AGENTS changed? 保持凭证本地保管及使用边界。
- 文档更新范围依据实际决策变化确定；验证证据归入证据文件。

## Risks

账号权限、dots 插件可用性及脚本通道需要实际验证；本地与云端证据分别记录。

## Handoff Notes

- Reviewer should check: 证据来自真实目标环境，循环请求由脚本自主完成。
- Human should decide: 真实平台首个接入对象，以及首版读写范围；模拟验证设计可先行。
