"""统一 JSON 响应模型"""

from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """
    所有接口统一返回结构：
    {
        "success": true/false,
        "data": <payload>,
        "error": null / "错误描述"
    }
    """

    success: bool
    data: T | None = None
    error: str | None = None

    @classmethod
    def ok(cls, data: Any = None) -> "ApiResponse":
        return cls(success=True, data=data)

    @classmethod
    def fail(cls, error: str) -> "ApiResponse":
        return cls(success=False, error=error)


# ---------- K8s 相关 ----------

class PodInfo(BaseModel):
    name: str
    namespace: str


class PodListData(BaseModel):
    pods: list[PodInfo]
    total: int


class DiagnoseRequest(BaseModel):
    """POST /api/diagnose 请求体"""
    pod_name: str
    namespace: str = "default"


class EventInfo(BaseModel):
    """事件信息"""
    name: str
    type: str
    reason: str
    message: str
    count: int
    last_timestamp: str


class DiagnoseData(BaseModel):
    """诊断结果"""
    logs: str
    events: list[EventInfo]


# ---------- SSH 相关 ----------

class SSHRequest(BaseModel):
    """POST /api/test-ssh 请求体"""
    host: str
    port: int = 22
    username: str
    password: str | None = None
    private_key: str | None = None  # PEM 格式私钥内容


class SSHResultData(BaseModel):
    host: str
    command: str
    exit_code: int
    stdout: str
    stderr: str
