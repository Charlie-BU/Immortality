from robyn.robyn import Response

from src.server.subRouters.user import user_router
from src.server.subRouters.context import context_router
from src.server.subRouters.analysis import analysis_router
from src.server.subRouters.context_crud import context_crud_router
from src.server.subRouters.virtual_figure import virtual_figure_router


async def registerRouters(app):
    # 全局异常处理
    @app.exception
    def handleException(error):
        return Response(
            status_code=500, description=f"error msg: {error}", headers={}
        )  # todo: server 报错信息暴露到客户端，危险，生产环境需移除

    app.get("/ping")(lambda: "pong")

    app.include_router(user_router)
    app.include_router(context_router)
    app.include_router(analysis_router)
    app.include_router(context_crud_router)
    app.include_router(virtual_figure_router)
