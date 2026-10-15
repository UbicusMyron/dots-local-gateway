# macmini_gateway

网关校验公司调用身份及已配置目标，在本机加入第三方凭证，执行 GET、显式配置的 JSON POST 和文件下载。依赖安装见根目录 README。

## 本地配置

将 `examples/config.example.json` 复制到 `local/config.json`，填写服务 origin、路由、账户及凭证文件引用。`secret_file` 相对于配置文件目录解析。管理员录入第三方凭证和独立公司调用凭证，凭证文件权限设置为 `0600`，本地目录设为 `0700`。

示例使用占位域名和别名；实际路由、认证及调用范围按目标平台配置。POST 的 `body_fields` 明确允许字段，`max_body_bytes` 限制请求体大小。

## 运行

在仓库根目录执行：

```sh
.venv/bin/python -m macmini_gateway.server \
  --config macmini_gateway/local/config.json \
  --caller-secret macmini_gateway/local/caller.secret \
  --port 8765
```

服务监听 `127.0.0.1:8765/mcp`，使用公司 Bearer 认证。Tunnel stdio 桥启动命令：

```sh
.venv/bin/python -m macmini_gateway.tunnel_stdio \
  --caller-secret macmini_gateway/local/caller.secret --port 8765
```

官方 Tunnel 客户端将 stdio 请求转交上述桥。部署时由管理员配置 Tunnel 连接及 launchd，运行账户需具备本地凭证读取权限。日志记录请求编号、状态和耗时。

请求及文件限制见 [MCP 接口](../docs/CONTRACTS/mcp-v1.md)。`Gateway.execute` 的 `caller_verified` 参数由可信服务适配器在认证后提供。
