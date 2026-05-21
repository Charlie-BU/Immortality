# CLI 导入副作用

这次问题的本质很简单：`immortality auth -h` 本来应该走项目自己的命令树，却在导入阶段被 `robyn` 抢先解析了参数。

## 关键结论

- CLI 启动链路里，任何模块顶层导入都必须足够“轻”；只要带进 Web 框架、副作用初始化、参数解析，就可能污染整个命令行行为。
- 这类问题最容易在 `-h / --help` 场景暴露，因为很多框架会在导入或初始化时直接读取 `sys.argv`。

## 这次踩坑点

- `src/cli/commands/auth.py` 在注册子命令时会导入 `src.services.user`。
- `src/services/user.py` 原先顶层 `from robyn import Request`，导致 CLI 还没开始解析自己的参数，就已经把 `robyn` 引进来了。
- 结果是 `uv run immortality auth -h` 打出来的不是项目帮助，而是 Robyn 的帮助。

## 修法

- 纯类型依赖不要做运行时导入；像 `Request` 这种只用于注解的符号，用 `TYPE_CHECKING` 或 postponed annotations 处理。
- CLI 命令模块尽量只保留参数注册；真正依赖重模块的导入，放到命令执行函数里再做。

## 最小经验

- 如果一个模块既会被 Server 用，也会被 CLI 预加载，就默认按“无副作用模块”来写。
- 看到“只是导个类型”这类写法时，要先问一句：它会不会顺手把整套框架带进来。
