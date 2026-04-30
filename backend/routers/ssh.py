"""SSH 相关路由"""

from __future__ import annotations

import logging

from fastapi import APIRouter

from schemas.response import ApiResponse, SSHRequest
from services.ssh_client import run_command

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["ssh"])

# 固定执行的测试命令
_TEST_COMMAND = "kubectl get pods"


@router.post("/test-ssh", response_model=ApiResponse)
async def test_ssh(req: SSHRequest):
    """
    通过 SSH 连接远程主机，执行 `kubectl get pods` 并返回结果。

    请求体示例：
    {
        "host": "192.168.1.100",
        "port": 22,
        "username": "root",
        "password": "xxx"
    }
    """
    try:
        result = run_command(
            host=req.host,
            port=req.port,
            username=req.username,
            password=req.password,
            private_key=req.private_key,
            command=_TEST_COMMAND,
        )
        return ApiResponse.ok(data=result)
    except Exception as e:
        logger.exception("SSH command failed")
        return ApiResponse.fail(error=f"SSH 执行失败: {e}")
