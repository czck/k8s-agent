"""自动修复服务 - Auto-Healing 自动闭环模块"""

from __future__ import annotations

import logging
import asyncio
from typing import Dict, List, Any
from services.ai_diagnostic import analyze_pod_issues, generate_fix_plan
from services.execution_service import execute_plan
from services.verification_service import verify_recovery
from kubernetes import client, config

logger = logging.getLogger(__name__)

async def auto_heal(pod_name: str, namespace: str, max_attempts: int = 3) -> Dict[str, Any]:
    """自动修复 Pod 问题
    
    Args:
        pod_name: Pod 名称
        namespace: 命名空间
        max_attempts: 最大尝试次数
    
    Returns:
        Dict: 自动修复结果
    """
    try:
        # 加载 Kubernetes 配置
        config.load_kube_config()
        v1 = client.CoreV1Api()
        
        attempts = 0
        history = []
        auto_healed = False
        final_status = "failed"
        
        while attempts < max_attempts:
            attempts += 1
            logger.info(f"Auto-healing attempt {attempts}/{max_attempts} for pod {pod_name} in namespace {namespace}")
            
            # 1. 再次调用 diagnose（获取最新状态）
            logger.info("Step 1: Running diagnose")
            try:
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
                
                history.append({
                    "step": "diagnose",
                    "status": "success",
                    "details": {
                        "summary": ai_analysis.get("summary"),
                        "severity": ai_analysis.get("severity")
                    }
                })
                
                logger.info(f"Diagnose completed: {ai_analysis.get('summary')}")
                
            except Exception as e:
                logger.exception("Diagnose failed")
                history.append({
                    "step": "diagnose",
                    "status": "failed",
                    "details": {
                        "error": str(e)
                    }
                })
                continue
            
            # 2. 基于最新 diagnose 重新调用 plan-fix
            logger.info("Step 2: Running plan-fix")
            try:
                fix_plan = generate_fix_plan(ai_analysis, pod_name, namespace)
                
                history.append({
                    "step": "plan",
                    "status": "success",
                    "details": {
                        "plan_summary": fix_plan.get("plan_summary"),
                        "risk_level": fix_plan.get("risk_level")
                    }
                })
                
                logger.info(f"Plan-fix completed: {fix_plan.get('plan_summary')}")
                
            except Exception as e:
                logger.exception("Plan-fix failed")
                history.append({
                    "step": "plan",
                    "status": "failed",
                    "details": {
                        "error": str(e)
                    }
                })
                continue
            
            # 3. 自动调用 execute-plan
            logger.info("Step 3: Running execute-plan")
            try:
                execution_result = execute_plan(fix_plan, namespace, pod_name)
                
                history.append({
                    "step": "execute",
                    "status": "success" if execution_result.get("executed") else "failed",
                    "details": {
                        "executed": execution_result.get("executed"),
                        "command_count": len(execution_result.get("results", []))
                    }
                })
                
                logger.info(f"Execute-plan completed: executed={execution_result.get('executed')}")
                
            except Exception as e:
                logger.exception("Execute-plan failed")
                history.append({
                    "step": "execute",
                    "status": "failed",
                    "details": {
                        "error": str(e)
                    }
                })
                continue
            
            # 4. 再次调用 verify-recovery
            logger.info("Step 4: Running verify-recovery")
            try:
                verification_result = verify_recovery(pod_name, namespace, [], fix_plan)
                
                history.append({
                    "step": "verify",
                    "status": "success",
                    "details": {
                        "recovered": verification_result.get("recovered"),
                        "status": verification_result.get("status"),
                        "confidence": verification_result.get("confidence")
                    }
                })
                
                logger.info(f"Verify-recovery completed: recovered={verification_result.get('recovered')}, status={verification_result.get('status')}")
                
                # 检查是否恢复
                if verification_result.get("recovered"):
                    auto_healed = True
                    final_status = "resolved"
                    logger.info(f"Auto-healing successful on attempt {attempts}")
                    break
                else:
                    logger.info(f"Auto-healing attempt {attempts} failed, will retry")
                    # 等待一段时间再重试
                    await asyncio.sleep(10)
                    
            except Exception as e:
                logger.exception("Verify-recovery failed")
                history.append({
                    "step": "verify",
                    "status": "failed",
                    "details": {
                        "error": str(e)
                    }
                })
                continue
        
        # 检查是否达到最大尝试次数
        if not auto_healed and attempts >= max_attempts:
            final_status = "manual_intervention_required"
            logger.warning(f"Auto-healing failed after {max_attempts} attempts, manual intervention required")
        
        # 构造返回结果
        return {
            "auto_healed": auto_healed,
            "attempts": attempts,
            "final_status": final_status,
            "history": history
        }
        
    except Exception as e:
        logger.exception("Auto-healing failed")
        return {
            "auto_healed": False,
            "attempts": 0,
            "final_status": "failed",
            "history": [
                {
                    "step": "auto_heal",
                    "status": "failed",
                    "details": {
                        "error": str(e)
                    }
                }
            ]
        }
