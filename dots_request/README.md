# dots_request

公共客户端提供 `Client.get`、`Client.post`、`Client.download`。业务循环、分页、结果处理和重试策略由调用方管理，第三方凭证由 Mac 网关管理。

安装：在仓库根目录执行 `python3 scripts/install_dots.py`。

## 业务接入

管理员提供可达的 MCP 地址及独立公司调用凭证文件。凭证文件权限为 `0600`；配置中的服务与账户别名对应网关配置。

```python
from dots_request import Client, RequestError
from dots_request.mcp_transport import MCPTransport

transport = MCPTransport("https://YOUR_MCP_HOST/mcp", "/absolute/path/caller.secret")
client = Client.from_config("dots_request/config.example.json", transport)
result = client.get("provider", "primary", "/items", query={"page": "1"})
print(result["data"])
```

`config.example.json` 为占位别名目录，使用时替换为管理员提供的配置。下载使用 `client.download(service, account, path, destination)`，目标目录须已存在；客户端核对文件大小和 SHA-256。

捕获 `RequestError` 后使用 `code`、`request_id` 和 `retryable` 定位问题。超时后的执行状态通过请求编号核对。

`MCPTransport` 连接直接可达的 Streamable HTTP 地址。Tunnel 工具入口按工作区连接，平台脚本桥按其实际接口适配。`127.0.0.1` 指向脚本所在机器，连接地址由管理员按执行位置提供。

面向 agent 的调用说明见 `skills/dots-request/SKILL.md`；协议见 [MCP 接口](../docs/CONTRACTS/mcp-v1.md)。
