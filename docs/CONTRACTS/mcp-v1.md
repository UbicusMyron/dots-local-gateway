# MCP 传输接口 v1

Last Reviewed: 2026-10-15

状态：当前源码实现的接口说明。目标环境按实际连接方式配置。

## Responsibilities

dots 业务使用 Client.get / Client.post / Client.download。MCPTransport 连接可达的 Streamable HTTP MCP 地址，调用 gateway_request，工具参数为 `{ "request": <公共请求对象> }`。网关根据本地配置执行结构化请求。

## Authentication

本地服务监听 127.0.0.1，入口 `/mcp` 使用独立公司 Bearer token，文件权限 0600。认证在 MCP 解析及工具执行之前完成；HTTP 401 表示公司认证失败。tunnel_stdio 桥从本地文件读取该 token 并连接常驻服务。远端 Tunnel 使用 OpenAI 工作区/组织访问控制；第三方 key 由网关本地独立读取。

## Requests

GET 使用 query 字符串对象、空 body；POST 使用 JSON 对象 body。每个本地 route 显式配置 method（默认 GET）、允许字段 body_fields、max_body_bytes（默认 16384，最大 65536）。POST 返回 JSON，stream 取 false 或省略。方法与路径精确匹配，认证 headers 由网关生成。

## Responses

沿用 request.md 的业务信封，补充 INVALID_RESPONSE。文件在线路中为 `{encoding:"base64",content:string,size:int,sha256:string}`；适配器解码并核对字节数，Client 核对 SHA-256。常驻样例的上游响应上限 1 MiB，MCP 客户端每次 HTTP 响应上限 4 MiB；正式大文件范围另行验收。

## Limits And Failures

入口请求上限 128 KiB；请求体接收期限 15 秒；并发连接上限 16。客户端总调用期限覆盖初始化与工具执行；发送一次业务请求。上游重定向返回错误，客户端连接也保持原目标。超时后执行状态通过请求日志核实。错误输出采用固定代码和请求编号。

