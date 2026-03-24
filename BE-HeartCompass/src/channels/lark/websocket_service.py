import json
import os
import lark_oapi as lark
from lark_oapi.api.im.v1 import (
    GetMessageResourceRequest,
    P2ImMessageReceiveV1,
)

from src.channels.lark.client import larkClient
from src.channels.lark.composite_api.im.send_text import SendTextRequest, sendText
from src.channels.lark.composite_api.im.send_image import SendImageRequest, sendImage
from src.channels.lark.composite_api.im.send_file import SendFileRequest, sendFile


# 全局单例
_lark_client = larkClient()


def _extractText(content: str) -> str:
    if not content:
        return ""
    try:
        payload = json.loads(content)
        if isinstance(payload, dict):
            text = payload.get("text")
            if isinstance(text, str):
                return text
    except Exception:
        return content
    return ""


def _extractPayload(content: str) -> dict:
    if not content:
        return {}
    try:
        payload = json.loads(content)
        if isinstance(payload, dict):
            return payload
    except Exception:
        return {}
    return {}


def _inferFileType(file_name: str) -> str:
    ext = os.path.splitext(file_name.lower())[1]
    if ext == ".pdf":
        return "pdf"
    if ext in {".doc", ".docx"}:
        return "doc"
    if ext in {".xls", ".xlsx"}:
        return "xls"
    if ext in {".ppt", ".pptx"}:
        return "ppt"
    if ext == ".opus":
        return "opus"
    if ext == ".mp4":
        return "mp4"
    if ext == ".txt":
        return "txt"
    return "stream"


def _replyImage(message: P2ImMessageReceiveV1) -> None:
    payload = _extractPayload(message.event.message.content)
    image_key = payload.get("image_key")
    if not isinstance(image_key, str) or not image_key:
        return
    download_req = (
        GetMessageResourceRequest.builder()
        .type("image")
        .message_id(message.event.message.message_id)
        .file_key(image_key)
        .build()
    )
    download_resp = _lark_client.im.v1.message_resource.get(download_req)
    if not download_resp.success():
        sendText(
            _lark_client,
            SendTextRequest(
                text="已收到：图片（回传失败）",
                receive_id_type="chat_id",
                receive_id=message.event.message.chat_id,
            ),
        )
        return
    send_req = SendImageRequest(
        image=download_resp.file,
        receive_id_type="chat_id",
        receive_id=message.event.message.chat_id,
    )
    send_resp = sendImage(_lark_client, send_req)
    if not send_resp.success():
        sendText(
            _lark_client,
            SendTextRequest(
                text="已收到：图片（回传失败）",
                receive_id_type="chat_id",
                receive_id=message.event.message.chat_id,
            ),
        )


def _replyFile(message: P2ImMessageReceiveV1) -> None:
    payload = _extractPayload(message.event.message.content)
    file_key = payload.get("file_key")
    if not isinstance(file_key, str) or not file_key:
        return
    download_req = (
        GetMessageResourceRequest.builder()
        .type("file")
        .message_id(message.event.message.message_id)
        .file_key(file_key)
        .build()
    )
    download_resp = _lark_client.im.v1.message_resource.get(download_req)
    if not download_resp.success():
        sendText(
            _lark_client,
            SendTextRequest(
                text="已收到：文件（回传失败）",
                receive_id_type="chat_id",
                receive_id=message.event.message.chat_id,
            ),
        )
        return
    file_name = download_resp.file_name or "received_file"
    send_req = SendFileRequest(
        file=download_resp.file,
        file_name=file_name,
        file_type=_inferFileType(file_name),
        receive_id_type="chat_id",
        receive_id=message.event.message.chat_id,
    )
    send_resp = sendFile(_lark_client, send_req)
    # 失败兜底
    if not send_resp.success():
        sendText(
            _lark_client,
            SendTextRequest(
                text="已收到：文件（回传失败）",
                receive_id_type="chat_id",
                receive_id=message.event.message.chat_id,
            ),
        )


def _handleMessage(data: P2ImMessageReceiveV1) -> None:
    message = data.event.message
    if message.message_type == "text":
        text = _extractText(message.content)
        if not text:
            return
        req = SendTextRequest(
            text=f"已收到：{text}",
            receive_id_type="chat_id",
            receive_id=message.chat_id,
        )
        sendText(_lark_client, req)
        return
    if message.message_type == "image":
        _replyImage(data)
        return
    if message.message_type == "file":
        _replyFile(data)
        return


def startLarkWebSocketServer() -> None:
    event_handler = (
        lark.EventDispatcherHandler.builder("", "", lark.LogLevel.DEBUG)
        .register_p2_im_message_receive_v1(_handleMessage)
        .build()
    )
    ws_client = lark.ws.Client(
        os.getenv("LARK_APP_ID"),
        os.getenv("LARK_APP_SECRET"),
        event_handler=event_handler,
        log_level=lark.LogLevel.DEBUG,
    )
    ws_client.start()
