# dots_request

Python 3.10+ 标准库实现的 GET 调用核心。当前交付以本地模拟网关验证；真实 dots、MCP、公司认证和文件线协议待任务 001 验证后接入。Python 为本组件本地实现选择，线上适配依据通道证据确定。

在仓库根目录执行：

```sh
python3 -m unittest discover -s dots_request/tests -v
python3 -m dots_request.examples.mock_businesses
```

组件独立使用时，把整个 `dots_request/` 放入应用的 Python 导入路径。公共入口：

```python
from dots_request import Client, RequestError

# transport 由应用注入，须符合本组件 Transport 接口。
client = Client.from_config("/absolute/path/config.json", transport)
result = client.get("demo", "demo_account", "/items", query={"page": "1"})
items = result["data"]
client.download("demo", "demo_account", "/report", "/absolute/path/report.csv")
```

`config.example.json` 记录服务/账户别名、单次调用超时秒数和文件大小上限。配置路径由调用方显式提供。公司连接信息由未来通道适配器管理；第三方认证由堡垒机管理。示例只使用模拟内容。

`get` 构造草案中的 GET 请求，query 的键和值均为字符串，body 为 null。返回经过结构检查的字典（request_id、ok、status、data 或 file）。业务数据的秘密隔离由网关负责；客户端过滤未知顶层字段，错误仅展示代码和请求编号，保留 retryable 元数据供业务决定。TIMEOUT 表示执行结果待核实。客户端每次调用提交一次，业务拥有循环、并发与重试。

`Transport.send(request, timeout=...)` 是暂定的 Python 注入边界：适配器负责连接认证、单次提交、实际超时限制、接收大小限制和解码。成功响应沿用请求草案；文件在适配器内归一化为 `file={"content": bytes, "sha256": "64位小写十六进制摘要"}`。这是内存表示；实际文件传输形式由通道验证定案。客户端内存大小检查发生在接收之后，因此适配器还需限制接收量。

`download` 校验文件大小和 SHA-256，在目标目录写完整临时文件后原子创建目标文件。目录需预先存在、由调用方控制并支持硬链接；已有文件或符号链接返回 DESTINATION_EXISTS。网关返回的文件名由适配器忽略，保存位置由业务明确指定。摘要用于完整性核对，连接身份由通道认证保证。

公共 skill 位于 `skills/dots-request/SKILL.md`；将其目录安装到目标环境的技能目录后使用。真实工具入口采用验证通过的 MCP 通道。
