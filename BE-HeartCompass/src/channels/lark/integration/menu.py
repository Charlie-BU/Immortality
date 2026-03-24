import logging
import re
from src.database.database import session
from src.database.models import RelationChain, User

logger = logging.getLogger(__name__)


def _sendText2OpenId(open_id: str, text: str) -> None:
    # 函数内导入，避免循环导入
    from src.channels.lark.integration.index import sendText2OpenId

    sendText2OpenId(open_id, text)


def _getRelationChainId(open_id: str, crush_id: int) -> int | None:
    with session() as db:
        user = db.query(User).filter(User.lark_open_id == open_id).first()
        if user is None:
            logger.warning(f"open_id：{open_id} 未授权")
            return None
        user_id = user.id
        relation_chain = (
            db.query(RelationChain)
            .filter(
                RelationChain.user_id == user_id, RelationChain.crush_id == crush_id
            )
            .first()
        )
        if relation_chain is None:
            logger.warning(f"不存在关系链")
            return None
        return relation_chain.id


def showMenu(open_id: str) -> None:
    menu_text = "\n\n".join(
        [
            "【System】可用指令：",
            *[
                f"{index}. {item['content']}\n{item['hint']}"
                for index, item in enumerate(menu, start=1)
            ],
        ]
    )
    _sendText2OpenId(open_id, menu_text)


def switchRelationChain(open_id: str, crush_id: int) -> None:
    from src.channels.lark.integration import index as lark_integration

    relation_chain_id = _getRelationChainId(open_id, crush_id)
    if relation_chain_id is None:
        _sendText2OpenId(
            open_id, f"【System】切换失败，未找到 crush_id={crush_id} 对应关系链"
        )
        return

    with lark_integration._state_lock:
        lark_integration._active_relation_chain_by_open_id[open_id] = relation_chain_id
        lark_integration._pending_messages_by_open_id.pop(open_id, None)
        lark_integration._cancelFlushTimerLocked(open_id)
    logger.info(f"切换relation_chain成功，relation_chain_id：{relation_chain_id}")
    _sendText2OpenId(open_id, f"【System】已切换 relation_chain_id={relation_chain_id}")


def addContextByNarrative(open_id: str, narrative: str) -> None:
    _sendText2OpenId(open_id, f"【System】通过自然语言添加上下文暂未实现：{narrative}")


def addContextByScreenshot(
    open_id: str,
    screenshot_url: str,
    additional_context: str,
    his_name_or_position_on_screenshot: str,
) -> None:
    _sendText2OpenId(
        open_id,
        f"【System】通过聊天记录截图添加上下文暂未实现：{screenshot_url} {additional_context} {his_name_or_position_on_screenshot}",
    )


menu = [
    {
        "hint": "/<person_id>",
        "content": "切换当前对话对象",
        "regex": r"/(\d+)",
        "command": switchRelationChain,
    },
    {
        "hint": "/add-context-by-narrative:\n<narrative>",
        "content": "通过自然语言添加上下文",
        "regex": r"/add-context-by-narrative:\n(.*)",
        "command": addContextByNarrative,
    },
    {
        "hint": "/add-context-by-screenshot:\n<screenshot>\n<additional_context>\n<his_name_or_position_on_screenshot>",
        "content": "通过聊天记录截图添加上下文",
        "regex": r"/add-context-by-screenshot:\n(.*)\n(.*)\n(.*)",
        "command": addContextByScreenshot,
    },
    {
        "hint": "/menu",
        "content": "显示菜单",
        "regex": r"/menu",
        "command": showMenu,
    },
]


def handleMenuCommand(message: str, open_id: str) -> bool:
    match = None
    index_hit = None
    for idx, item in enumerate(menu):
        match = re.fullmatch(item["regex"], message, re.DOTALL)
        if not match:
            continue
        index_hit = idx
        break
    if not match:
        return False

    current_item = menu[index_hit]
    command = current_item["command"]
    if command == switchRelationChain:
        command(open_id, int(match.group(1)))
    elif command == addContextByNarrative:
        command(open_id, match.group(1))
    elif command == addContextByScreenshot:
        command(open_id, match.group(1), match.group(2), match.group(3))
    elif command == showMenu:
        command(open_id)
    else:
        logger.error(f"未实现的菜单命令：{current_item}")
        return False
    return True
