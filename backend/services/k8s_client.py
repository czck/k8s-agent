"""Kubernetes 集成服务 —— 支持本地 kubeconfig 和远程配置"""

from __future__ import annotations
import os
from kubernetes import client, config

from schemas.response import PodInfo, EventInfo


def _load_k8s_config() -> None:
    """配置 K8s 客户端连接"""
    import os
    import logging
    logger = logging.getLogger(__name__)
    
    kubeconfig_path = os.path.expanduser('~/.kube/config')
    logger.info(f"KUBECONFIG环境变量: {os.environ.get('KUBECONFIG')}")
    logger.info(f"默认kubeconfig路径: {kubeconfig_path}")
    logger.info(f"kubeconfig文件是否存在: {os.path.exists(kubeconfig_path)}")
    
    try:
        # 优先尝试加载默认的kubeconfig文件（VM中运行时使用）
        logger.info("尝试加载kubeconfig文件...")
        config.load_kube_config()
        logger.info("成功加载kubeconfig文件")
    except Exception as e:
        logger.error(f"加载kubeconfig失败: {e}")
        # 如果加载失败，尝试使用in-cluster配置（Pod中运行时使用）
        try:
            logger.info("尝试加载in-cluster配置...")
            config.load_incluster_config()
            logger.info("成功加载in-cluster配置")
        except Exception as e:
            logger.error(f"加载in-cluster配置失败: {e}")
            raise Exception(f"无法加载Kubernetes配置: {e}")


def list_pods(namespace: str | None = None) -> list[PodInfo]:
    """
    获取 Pod 列表。
    namespace=None 表示所有命名空间。
    """
    # 加载配置
    _load_k8s_config()
    
    # 创建 API 客户端
    v1 = client.CoreV1Api()

    if namespace:
        pod_list = v1.list_namespaced_pod(namespace=namespace)
    else:
        pod_list = v1.list_pod_for_all_namespaces()

    return [
        PodInfo(
            name=pod.metadata.name,
            namespace=pod.metadata.namespace,
        )
        for pod in pod_list.items
    ]


def diagnose_pod(pod_name: str, namespace: str) -> tuple[str, list[EventInfo]]:
    """
    诊断 Pod，获取其日志和事件。
    
    Args:
        pod_name: Pod 名称
        namespace: 命名空间
    
    Returns:
        tuple: (日志字符串, 事件列表)
    """
    # 加载配置
    _load_k8s_config()
    
    # 创建 API 客户端
    v1 = client.CoreV1Api()
    
    # 获取 Pod 日志（最后100行）
    try:
        logs = v1.read_namespaced_pod_log(
            name=pod_name,
            namespace=namespace,
            tail_lines=100,
            container=None  # 默认为第一个容器
        )
        # 截断日志，避免太长
        if len(logs) > 10000:
            logs = logs[-10000:]  # 保留最后10000个字符
    except Exception as e:
        logs = f"获取日志失败: {e}"
    
    # 获取 Pod 事件（最近10条）
    try:
        events = v1.list_namespaced_event(
            namespace=namespace,
            field_selector=f"involvedObject.name={pod_name}"
        )
        # 按时间排序，取最近10条
        sorted_events = sorted(
            events.items,
            key=lambda e: e.last_timestamp or e.event_time or e.first_timestamp,
            reverse=True
        )[:10]
        
        event_infos = []
        for event in sorted_events:
            event_infos.append(EventInfo(
                name=event.metadata.name,
                type=event.type or "Unknown",
                reason=event.reason or "Unknown",
                message=event.message or "",
                count=event.count or 0,
                last_timestamp=event.last_timestamp.isoformat() if event.last_timestamp else ""
            ))
    except Exception as e:
        event_infos = [EventInfo(
            name="error",
            type="Error",
            reason="FailedToGetEvents",
            message=f"获取事件失败: {e}",
            count=0,
            last_timestamp=""
        )]
    
    return logs, event_infos
