from robyn import Robyn, ALLOW_CORS

from src.server.routers import registerRouters


async def initRobynServer(app: Robyn):
    # CORS中间件
    # todo: 生产环境需要注释：使用nginx解决跨域
    ALLOW_CORS(app, origins=["*"])
    # 注册路由
    await registerRouters(app)
