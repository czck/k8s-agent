"""Kubernetes 相关路由"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Query, Body
from kubernetes import client

from schemas.response import ApiResponse, PodListData
from services.k8s_client import list_pods, _load_k8s_config
from services.ai_diagnostic import analyze_pod_issues, generate_fix_plan
from services.execution_service import execute_plan
from services.verification_service import verify_recovery
from services.auto_healing_service import auto_heal

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["kubernetes"])


@router.get("/pods", response_model=ApiResponse)
async def get_pods(namespace: str | None = Query(None, description="按命名空间过滤，留空返回所有")):
    """获取当前集群的 Pod 列表（name + namespace）"""
    try:
        pods = list_pods(namespace=namespace)
        return ApiResponse.ok(
            data=PodListData(pods=pods, total=len(pods)),
        )
    except Exception as e:
        logger.exception("Failed to list pods")
        return ApiResponse.fail(error=f"获取 Pod 列表失败: {e}")


@router.post("/diagnose", response_model=ApiResponse)
async def diagnose(
    pod_name: str = Body(...),
    namespace: str = Body("default"),
):
    """诊断 Pod 问题并提供 AI 分析"""
    try:
        _load_k8s_config()
        v1 = client.CoreV1Api()

        # 获取日志
        logs = v1.read_namespaced_pod_log(
            name=pod_name,
            namespace=namespace,
            tail_lines=100
        )

        # 截断日志（最多 2000 字符）
        truncated_logs = logs[:2000]

        # 获取事件
        events = v1.list_namespaced_event(namespace=namespace)

        filtered_events = [
            {
                "reason": e.reason,
                "message": e.message
            }
            for e in events.items
            if e.involved_object.name == pod_name
        ][:10]

        # 调用 AI 分析
        ai_analysis = analyze_pod_issues(truncated_logs, filtered_events)

        # 构造返回数据
        data = {
            "logs": truncated_logs,
            "events": filtered_events,
            "ai_analysis": ai_analysis
        }

        return ApiResponse.ok(data=data)

    except Exception as e:
        logger.exception("Failed to diagnose pod")
        return ApiResponse.fail(error=f"诊断 Pod 失败: {str(e)}")


@router.post("/plan-fix", response_model=ApiResponse)
async def plan_fix(
    diagnosis: dict = Body(...),
    pod_name: str = Body(...),
    namespace: str = Body(...),
):
    """基于诊断结果生成修复方案"""
    try:
        # 调用 AI 生成修复方案
        fix_plan = generate_fix_plan(diagnosis, pod_name, namespace)

        # 构造返回数据
        data = {
            "fix_plan": fix_plan
        }

        return ApiResponse.ok(data=data)

    except Exception as e:
        logger.exception("Failed to generate fix plan")
        return ApiResponse.fail(error=f"生成修复方案失败: {str(e)}")


@router.post("/execute-plan", response_model=ApiResponse)
async def execute_plan_endpoint(
    plan: dict = Body(...),
    namespace: str = Body(...),
    pod_name: str = Body(...),
):
    """执行修复计划"""
    try:
        # 执行修复计划
        execution_result = execute_plan(plan, namespace, pod_name)

        # 构造返回数据
        data = execution_result

        return ApiResponse.ok(data=data)

    except Exception as e:
        logger.exception("Failed to execute plan")
        return ApiResponse.fail(error=f"执行修复计划失败: {str(e)}")


@router.post("/verify-recovery", response_model=ApiResponse)
async def verify_recovery_endpoint(
    pod_name: str = Body(...),
    namespace: str = Body(...),
    executed_results: list = Body([]),
    plan: dict = Body({}),
):
    """验证修复结果"""
    try:
        # 验证修复结果
        verification_result = verify_recovery(pod_name, namespace, executed_results, plan)

        # 构造返回数据
        data = verification_result

        return ApiResponse.ok(data=data)

    except Exception as e:
        logger.exception("Failed to verify recovery")
        return ApiResponse.fail(error=f"验证修复结果失败: {str(e)}")


@router.post("/auto-heal", response_model=ApiResponse)
async def auto_heal_endpoint(
    pod_name: str = Body(...),
    namespace: str = Body(...),
    max_attempts: int = Body(3, ge=1, le=5),
):
    """自动修复 Pod 问题"""
    try:
        # 执行自动修复
        auto_heal_result = await auto_heal(pod_name, namespace, max_attempts)

        # 构造返回数据
        data = auto_heal_result

        return ApiResponse.ok(data=data)

    except Exception as e:
        logger.exception("Failed to auto-heal")
        return ApiResponse.fail(error=f"自动修复失败: {str(e)}")
