"""执行服务 - 执行修复计划"""

from __future__ import annotations

import logging
import subprocess
from typing import Dict, List, Any, Optional
from kubernetes import client, config

logger = logging.getLogger(__name__)

# 命令白名单
ALLOWED_COMMANDS = {
    'kubectl': {
        'get': ['pods', 'deployments', 'services', 'events', 'logs'],
        'describe': ['pod', 'deployment', 'service'],
        'rollout': ['restart', 'status'],
        'scale': ['deployment'],
        'delete': ['pod'],
        'wait': ['pod']
    },
    'systemctl': {
        'status': [],
        'restart': [],
        'start': [],
        'stop': []
    },
    'journalctl': {
        '-u': [],
        '--since': [],
        '--until': []
    }
}

# 危险命令
DANGEROUS_COMMANDS = [
    'rm -rf',
    'delete namespace',
    'format',
    'reboot',
    'shutdown'
]

def validate_command(command: str) -> bool:
    """验证命令是否安全
    
    Args:
        command: 要执行的命令
    
    Returns:
        bool: 命令是否安全
    """
    # 检查危险命令
    for dangerous in DANGEROUS_COMMANDS:
        if dangerous in command:
            logger.warning(f"Dangerous command detected: {command}")
            return False
    
    # 检查白名单
    parts = command.split()
    if not parts:
        return False
    
    cmd = parts[0]
    if cmd not in ALLOWED_COMMANDS:
        logger.warning(f"Command not in whitelist: {cmd}")
        return False
    
    # 检查子命令
    if len(parts) > 1:
        subcmd = parts[1]
        allowed_subcmds = ALLOWED_COMMANDS.get(cmd, {})
        if subcmd not in allowed_subcmds:
            logger.warning(f"Subcommand not allowed: {subcmd}")
            return False
    
    return True

def execute_kubernetes_command(command: str, namespace: str) -> Dict[str, Any]:
    """通过 Kubernetes API 执行命令
    
    Args:
        command: 要执行的命令
        namespace: 命名空间
    
    Returns:
        Dict: 执行结果
    """
    try:
        # 加载 Kubernetes 配置
        config.load_kube_config()
        v1 = client.CoreV1Api()
        apps_v1 = client.AppsV1Api()
        
        parts = command.split()
        if len(parts) < 2:
            return {
                "success": False,
                "output": "",
                "error": "Command too short"
            }
        
        cmd = parts[0]
        subcmd = parts[1]
        
        if cmd != 'kubectl':
            return {
                "success": False,
                "output": "",
                "error": "Only kubectl commands supported through API"
            }
        
        # 处理不同的 kubectl 命令
        if subcmd == 'get':
            if 'pods' in parts:
                pods = v1.list_namespaced_pod(namespace=namespace)
                output = "\n".join([f"{pod.metadata.name} - {pod.status.phase}" for pod in pods.items])
                return {
                    "success": True,
                    "output": output,
                    "error": ""
                }
            elif 'deployments' in parts:
                deployments = apps_v1.list_namespaced_deployment(namespace=namespace)
                output = "\n".join([f"{dep.metadata.name} - {dep.status.ready_replicas}/{dep.spec.replicas}" for dep in deployments.items])
                return {
                    "success": True,
                    "output": output,
                    "error": ""
                }
        
        elif subcmd == 'rollout' and len(parts) > 3 and parts[2] == 'restart' and parts[3] == 'deployment':
            deployment_name = parts[4] if len(parts) > 4 else None
            if deployment_name:
                apps_v1.restart_namespaced_deployment(name=deployment_name, namespace=namespace)
                return {
                    "success": True,
                    "output": f"Deployment {deployment_name} restarted",
                    "error": ""
                }
        
        elif subcmd == 'logs':
            pod_name = parts[2] if len(parts) > 2 else None
            if pod_name and '-n' in parts:
                ns_idx = parts.index('-n')
                if ns_idx + 1 < len(parts):
                    pod_namespace = parts[ns_idx + 1]
                    logs = v1.read_namespaced_pod_log(name=pod_name, namespace=pod_namespace)
                    return {
                        "success": True,
                        "output": logs,
                        "error": ""
                    }
        
        # 如果命令无法通过 API 执行，返回失败
        return {
            "success": False,
            "output": "",
            "error": "Command not supported through API"
        }
        
    except Exception as e:
        logger.exception(f"Failed to execute Kubernetes command: {command}")
        return {
            "success": False,
            "output": "",
            "error": str(e)
        }

def execute_ssh_command(command: str) -> Dict[str, Any]:
    """通过 SSH 执行命令（备用）
    
    Args:
        command: 要执行的命令
    
    Returns:
        Dict: 执行结果
    """
    try:
        # 这里使用 subprocess 模拟 SSH 执行
        # 实际项目中，应该使用 paramiko 连接到 VM 执行命令
        result = subprocess.run(
            command, 
            shell=True, 
            capture_output=True, 
            text=True, 
            timeout=30
        )
        
        return {
            "success": result.returncode == 0,
            "output": result.stdout,
            "error": result.stderr
        }
        
    except Exception as e:
        logger.exception(f"Failed to execute SSH command: {command}")
        return {
            "success": False,
            "output": "",
            "error": str(e)
        }

def execute_plan(plan: Dict[str, Any], namespace: str, pod_name: str) -> Dict[str, Any]:
    """执行修复计划
    
    Args:
        plan: 修复计划
        namespace: 命名空间
        pod_name: Pod 名称
    
    Returns:
        Dict: 执行结果
    """
    try:
        # 安全检查
        risk_level = plan.get("risk_level", "low")
        requires_approval = plan.get("requires_approval", False)
        
        if risk_level == "high" and not requires_approval:
            return {
                "executed": False,
                "results": [],
                "rollback_hint": plan.get("rollback_hint", "")
            }
        
        commands = plan.get("commands", [])
        results = []
        
        for command in commands:
            # 验证命令
            if not validate_command(command):
                results.append({
                    "command": command,
                    "success": False,
                    "output": "",
                    "error": "Command not allowed"
                })
                continue
            
            # 先尝试通过 Kubernetes API 执行
            api_result = execute_kubernetes_command(command, namespace)
            
            # 如果 API 执行失败，尝试通过 SSH 执行
            if not api_result["success"]:
                ssh_result = execute_ssh_command(command)
                results.append({
                    "command": command,
                    "success": ssh_result["success"],
                    "output": ssh_result["output"],
                    "error": ssh_result["error"]
                })
            else:
                results.append({
                    "command": command,
                    "success": api_result["success"],
                    "output": api_result["output"],
                    "error": api_result["error"]
                })
            
        # 检查是否所有命令都执行成功
        all_success = all(result["success"] for result in results)
        
        return {
            "executed": True,
            "results": results,
            "rollback_hint": plan.get("rollback_hint", "")
        }
        
    except Exception as e:
        logger.exception("Failed to execute plan")
        return {
            "executed": False,
            "results": [],
            "rollback_hint": plan.get("rollback_hint", "")
        }
