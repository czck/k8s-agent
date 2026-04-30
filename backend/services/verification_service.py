"""验证服务 - 验证修复结果"""

from __future__ import annotations

import logging
from typing import Dict, List, Any, Optional
from kubernetes import client, config
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

def verify_recovery(pod_name: str, namespace: str, executed_results: List[Dict], plan: Dict[str, Any]) -> Dict[str, Any]:
    """验证修复结果
    
    Args:
        pod_name: Pod 名称
        namespace: 命名空间
        executed_results: 执行结果
        plan: 修复计划
    
    Returns:
        Dict: 验证结果
    """
    try:
        # 加载 Kubernetes 配置
        config.load_kube_config()
        v1 = client.CoreV1Api()
        
        # 初始化验证结果
        recovered = False
        status = "failed"
        confidence = 0
        evidence = []
        remaining_issues = []
        recommendation = "rollback"
        
        # 1. Pod 状态检查
        try:
            pod = v1.read_namespaced_pod(name=pod_name, namespace=namespace)
            pod_status = pod.status.phase
            
            if pod_status == "Running":
                evidence.append("pod is running")
                confidence += 30
            elif pod_status in ["CrashLoopBackOff", "Error"]:
                remaining_issues.append(f"Pod status is {pod_status}")
                confidence -= 20
            elif pod_status == "Pending":
                # 检查 Pending 时间
                start_time = pod.status.start_time
                if start_time:
                    pending_duration = datetime.now(start_time.tzinfo) - start_time
                    if pending_duration > timedelta(minutes=2):
                        remaining_issues.append("Pod is pending for more than 2 minutes")
                        confidence -= 15
                    else:
                        evidence.append("Pod is pending but within acceptable time")
                        confidence += 10
            else:
                remaining_issues.append(f"Pod status is {pod_status}")
                confidence -= 10
                
            # 2. 重启次数检查
            restart_count = pod.status.container_statuses[0].restart_count if pod.status.container_statuses else 0
            if restart_count == 0:
                evidence.append("no restart detected")
                confidence += 20
            elif restart_count < 3:
                evidence.append(f"restart count is {restart_count}")
                confidence += 10
            else:
                remaining_issues.append(f"high restart count: {restart_count}")
                confidence -= 20
                
        except client.exceptions.ApiException as e:
            if e.status == 404:
                remaining_issues.append("Pod not found")
                confidence -= 30
            else:
                remaining_issues.append(f"Error checking pod status: {str(e)}")
                confidence -= 20
        
        # 3. 日志验证
        try:
            logs = v1.read_namespaced_pod_log(
                name=pod_name,
                namespace=namespace,
                tail_lines=100
            )
            
            error_keywords = ["error", "exception", "crash", "fail", "warning"]
            error_found = False
            for keyword in error_keywords:
                if keyword in logs.lower():
                    error_found = True
                    remaining_issues.append(f"Error found in logs: {keyword}")
                    confidence -= 15
                    break
            
            if not error_found:
                evidence.append("no errors found in logs")
                confidence += 25
                
        except Exception as e:
            remaining_issues.append(f"Error checking logs: {str(e)}")
            confidence -= 10
        
        # 4. Event 验证
        try:
            events = v1.list_namespaced_event(namespace=namespace, field_selector=f"involvedObject.name={pod_name}")
            
            error_events = []
            for event in events.items:
                if event.type == "Warning" or event.type == "Error":
                    # 检查事件时间，只考虑最近的事件
                    event_time = event.last_timestamp or event.first_timestamp
                    if event_time:
                        event_age = datetime.now(event_time.tzinfo) - event_time
                        if event_age < timedelta(minutes=5):
                            error_events.append(event.message)
            
            if error_events:
                for event in error_events:
                    remaining_issues.append(f"Error event: {event}")
                confidence -= 20
            else:
                evidence.append("no error events detected")
                confidence += 20
                
        except Exception as e:
            remaining_issues.append(f"Error checking events: {str(e)}")
            confidence -= 10
        
        # 计算最终状态和推荐
        confidence = max(0, min(100, confidence))
        
        if confidence >= 70:
            recovered = True
            status = "healthy"
            recommendation = "success"
        elif confidence >= 40:
            recovered = False
            status = "degraded"
            recommendation = "retry"
        else:
            recovered = False
            status = "failed"
            recommendation = "rollback"
        
        # 构造返回结果
        return {
            "recovered": recovered,
            "status": status,
            "confidence": confidence,
            "evidence": evidence,
            "remaining_issues": remaining_issues,
            "recommendation": recommendation
        }
        
    except Exception as e:
        logger.exception("Failed to verify recovery")
        return {
            "recovered": False,
            "status": "failed",
            "confidence": 0,
            "evidence": [],
            "remaining_issues": [f"Verification failed: {str(e)}"],
            "recommendation": "rollback"
        }
