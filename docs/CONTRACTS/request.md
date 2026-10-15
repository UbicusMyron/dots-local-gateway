# 公共请求契约草案

Last Reviewed: 2026-10-15

状态：设计草案。字段表达接口边界，传输、认证方式、文件表示及读写范围经验证与确认后冻结。

## Component Responsibilities

- Producer: dots_request 根据业务脚本或工具调用生成结构化请求。
- Executor: macmini_gateway 完成公司调用认证、参数检查和平台认证，执行 API 请求与下载。
- Consumer: dots_request 消费业务响应并保存接收的文件；业务插件负责后续计算。
- Transport: 现成通道承载请求和响应；具体连接及文件表示依据技术验证冻结。
- Configuration: dots_request 持有公司调用连接信息及服务/账户别名；macmini_gateway 持有第三方目标、认证适配及本地凭证引用。

## Request

```json
{
  "service": "demo",
  "account": "demo_account",
  "method": "GET",
  "path": "/items",
  "query": {"page": "1"},
  "body": null
}
```

service/account 为本地已配置别名；method 为方法字符串，开放集合待确认；path 为相对配置基址的接口路径；query 为参数对象；body 为可选 JSON 数据。模拟验证使用 GET。
调用方身份来自通道或外层连接认证。

## Response

成功示意：
```json
{"request_id":"demo-1","ok":true,"status":200,"data":{"items":[]}}
```

校验反馈示意：
```json
{"request_id":"demo-1","ok":false,"error":{"code":"INVALID_REQUEST","message":"Use a configured destination","retryable":false}}
```

拟用错误分类：UNAUTHENTICATED、INVALID_REQUEST、UNKNOWN_CONNECTION、UPSTREAM_ERROR、TIMEOUT。分类标识属于机器协议，message 提供可执行说明。具体传输状态码在接口冻结时定义。message 使用经过输出检查的业务信息。超时反馈说明执行状态待核实。

## Validation

- 有效请求采用已配置服务/账户、相对路径、通过校验的目标和本地生成的认证字段。
- 对外能力限定为结构化 API 请求和下载；程序执行由 dots 负责，凭证读取由堡垒机本地服务负责。
- 认证刷新结果由本地适配器消费；业务端点与认证端点按用途分开处理。秘密隔离结合端点、响应语义和输出检查实现。
- 返回头字段和异常说明使用明确选择并检查后的业务内容。

## Files

业务文件允许上云。首版以 dots 实际收到文件并完成内容或摘要校验作为交付标准。
传输形式、大小限制和中断语义列为 Open Questions，通过通道验证后确定。

## Compatibility

当前处于首次接口设计阶段；正式冻结后的变更同步更新调用端与相关测试。
