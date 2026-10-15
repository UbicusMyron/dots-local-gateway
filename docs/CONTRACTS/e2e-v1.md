# 本机联合测试契约 v1

Last Reviewed: 2026-10-15

状态：2026-10-15 用户授权的本机测试接口。生产冻结以真实 dots 与 Tunnel 的验证证据为依据。

## Responsibilities

dots 业务使用 Client.get / Client.post / Client.download。MCPTransport 连接可达的 Streamable HTTP MCP 地址，调用 gateway_request，工具参数为 `{ "request": <公共请求对象> }`。网关根据本地配置执行结构化请求。

## Authentication

本地服务监听 127.0.0.1，入口 `/mcp` 使用独立公司 Bearer token，文件权限 0600。认证在 MCP 解析及工具执行之前完成；HTTP 401 表示公司认证失败。tunnel_stdio 桥从本地文件读取该 token 并连接常驻服务。远端 Tunnel 使用 OpenAI 工作区/组织访问控制；第三方 key 由网关本地独立读取。

## Requests

GET 使用 query 字符串对象、空 body；POST 使用 JSON 对象 body。每个本地 route 显式配置 method（默认 GET）、允许字段 body_fields、max_body_bytes（默认 16384，最大 65536）。POST 返回 JSON，stream 取 false 或省略。方法与路径精确匹配，认证 headers 由网关生成。

本次 OpenCode Go 路由：GET `/inference/go/v1/models`，POST `/inference/go/v1/chat/completions`，字段 model/messages/max_tokens/stream。模型 ID 在执行前由账号可用列表确定。

## Responses

沿用 request.md 的业务信封，补充 INVALID_RESPONSE。文件在线路中为 `{encoding:"base64",content:string,size:int,sha256:string}`；适配器解码并核对字节数，Client 核对 SHA-256。常驻样例的上游响应上限 1 MiB，MCP 客户端每次 HTTP 响应上限 4 MiB；正式大文件范围另行验收。

## Limits And Failures

入口请求上限 128 KiB；请求体接收期限 15 秒；并发连接上限 16。客户端总调用期限覆盖初始化与工具执行；发送一次业务请求。上游重定向返回错误，客户端连接也保持原目标。超时后执行状态通过请求日志核实。错误输出采用固定代码和请求编号。

## Transport Acceptance

本地 Streamable HTTP、stdio 桥、桌面 Codex、真实 dots 工具和真实 dots 脚本分别记录。Tunnel 的工具可用性与 dots 脚本可调用性各自以实际证据确认。脚本适配器需要可直接连接的 MCP 地址及适用的调用凭证；本地回环地址指向脚本所在机器。

## GitHub 第二用例

2026-10-15 用户授权真实只读测试。固定服务 github、账户 personal、origin https://api.github.com；GET `/orgs/CUHK-Business-School-AI-Hub/repos`，query 允许 type/sort/direction/per_page/page。网关提供固定 User-Agent；分页、去重、公私标记汇总归 dots 业务脚本。结果为 token 可见的组织仓库元数据，完整性按本次分页终止条件记录。
