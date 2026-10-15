# macmini_gateway

当前交付为 Python 3.11+ 的只读网关核心，使用标准库，已通过模拟客户端和模拟第三方验证。公司连接认证、MCP/Tunnel 接线、常驻服务入口与 launchd 配置在通道验证和契约确认后交付。

## 本地运行

在仓库根目录执行：

```sh
python3 -m macmini_gateway
python3 -m unittest discover -s macmini_gateway/tests -v
```

第一条命令完全离线，临时生成 0600 模拟凭证，连续调用三次并核对下载内容和 SHA-256；退出时清理临时材料。第二条验证核心及 HTTPS 传输行为。实际生产传输使用 HTTPS，模拟验证通过注入测试对端执行。

## 已实现能力

- 固定 HTTPS origin、精确业务路径、允许的查询字段和账户凭证路由。
- 本地 Bearer 与 X- API key 适配；平台 token 刷新由后续平台适配任务补充。
- GET JSON 请求与有大小上限的文件下载；业务循环和重试由调用端决定。
- 系统 CA 验证、直接 HTTPS 连接、逐次请求；重定向作为上游错误返回。
- 0600、当前服务用户所有的普通凭证文件；末级符号链接校验；加载时读取，重建实例后应用凭证轮换。
- 输出长度检查、已加载凭证的原文及常见编码检查、JSON 解码后递归检查。
- 固定错误消息、服务生成请求编号、状态与耗时日志。

## 配置与内部调用

参考 `examples/config.mock.json`。配置文件路径显式传入；相对 secret_file 以配置所在目录解析。管理员维护的 origin 与 routes 构成目标信任边界，routes 收录业务端点，认证交换端点由未来独立适配器消费。服务目录与配置由服务用户或管理员管理，确保其父目录及配置引用可信。

```python
from macmini_gateway import Gateway

gateway = Gateway("/absolute/local/path/config.json")
result = gateway.execute(
    {"service": "demo", "account": "demo_account", "method": "GET", "path": "/items"},
    caller_verified=True,
)
```

`caller_verified` 是内部可信适配器传入的认证结论。当前只有模拟调用方；将来连接适配器必须自行验证公司身份，并用独立上下文提供此值。请求对象中的同名字段按未知字段拒绝。此 Python 方法属于待接线内部接口，正式网络入口依据共享契约确认。

JSON 返回 data；文件暂返回 file.content（base64）、size、sha256，默认上限 1 MiB，可配置至 16 MiB。成功结果完整交付；超限、输出检查失败和中断返回错误。文件形式、错误扩展 INVALID_RESPONSE 和这些限额是本地实现约定，正式双方契约依据通道实验确认。

输出检查覆盖已加载秘密及测试编码；平台接入时须结合端点语义和代表性数据检查转换、压缩或其他编码产生的秘密。文件大小上限按上游原始响应字节计，base64 有额外内存与传输开销。

## 部署接续条件

任务 001 提供本地 MCP、桌面 Codex、真实 dots 工具与脚本的独立证据后，确定可信公司身份的接入位置、文件传输形式与常驻进程组合。随后增加服务入口及 launchd 配置，并验证启动、退出恢复、连接中断和休眠恢复。真实凭证由管理员在目标 Mac mini 本地录入。
