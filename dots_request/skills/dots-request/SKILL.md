---
name: dots-request
description: 在已配置的 dots_request 环境中编写或运行通过堡垒机获取业务 API 数据和下载文件的脚本，复用公共入口与服务账户别名。
---

# 共享业务请求

先读取目标环境的 dots_request 组件 README、调用方提供的配置路径及通道适配器说明。当前版本支持 GET、显式配置的 JSON POST 和下载。MCPTransport 使用管理员提供的可达地址与公司调用凭证，业务调用按已配置服务和账户执行。

通过 `Client.from_config(config_path, transport)` 创建客户端，使用 `get(service, account, path, query=...)` 获取业务数据，使用 `download(service, account, path, destination, query=...)` 保存文件。路径为相对服务基址的 `/...` 路径，query 的键和值为字符串，目标目录由业务指定并预先创建。配置别名对应堡垒机账户，第三方凭证与认证逻辑由堡垒机处理。

循环、分页和结果计算写在业务脚本中。捕获 `RequestError`，报告 code、request_id 和 retryable；重试由业务明确决定。TIMEOUT 后先核对执行状态。下载成功后消费返回的本地路径；DESTINATION_EXISTS 时由业务选择新路径或明确处理已有结果。

交付时说明实际执行位置、连接方式及请求编号。真实平台接入及第三方写操作遵循项目已确认的范围。
