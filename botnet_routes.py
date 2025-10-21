from fastapi import APIRouter, Request, HTTPException
from typing import Dict
from botnet_service import get_botnet_service

router = APIRouter()

@router.post("/botnet")
async def botnet(request: Dict):
    """🤖 Single bot login using optimized botnet service"""
    botnet_service = get_botnet_service()
    username = request.get("username", "")
    password = request.get("password", "")
    appId = request.get("appId", "")
    result = await botnet_service.manage_bot_session(username, password, appId)
    if result.get("success"):
        return {
            "message": result["message"],
            "username": result["username"],
            "userId": result.get("userId", ""),
            "accessToken": result.get("accessToken", ""),
            "authCode": result.get("authCode", ""),
            "sync_result": result.get("sync_result", {}),
            "ws_result": result.get("ws_result", {}),
            "ws_response": result.get("ws_result", {}).get("response", ""),
        }
    else:
        return {"message": result.get("message", "Unknown error"), "success": False}
