# 更新后端服务脚本 - 添加 execute-plan 接口

# VM连接配置
$VM_HOST = "192.168.86.130"
$VM_USER = "root"  # 根据实际情况修改
$VM_PASSWORD = ""  # 根据实际情况修改
$VM_DEPLOY_PATH = "/root/k8s-ai-ops-agent"  # VM中的部署路径

Write-Host "开始更新后端服务..." -ForegroundColor Green

# 1. 停止VM中的后端服务
Write-Host "停止后端服务..." -ForegroundColor Cyan
try {
    plink -batch -pw $VM_PASSWORD $VM_USER@$VM_HOST "ps aux | grep python3 | grep main.py | awk '{print $2}' | xargs kill 2>/dev/null"
} catch {
    Write-Host "停止服务时出现错误: $_" -ForegroundColor Yellow
}

# 2. 上传修改后的文件
Write-Host "上传修改后的文件..." -ForegroundColor Cyan
try {
    # 上传 k8s.py 文件
    pscp -batch -pw $VM_PASSWORD "$PSScriptRoot\backend\routers\k8s.py" "$VM_USER@$VM_HOST:$VM_DEPLOY_PATH/backend/routers/"
    
    # 上传 execution_service.py 文件
    pscp -batch -pw $VM_PASSWORD "$PSScriptRoot\backend\services\execution_service.py" "$VM_USER@$VM_HOST:$VM_DEPLOY_PATH/backend/services/"
    
    # 上传 ai_diagnostic.py 文件
    pscp -batch -pw $VM_PASSWORD "$PSScriptRoot\backend\services\ai_diagnostic.py" "$VM_USER@$VM_HOST:$VM_DEPLOY_PATH/backend/services/"
    
    Write-Host "文件上传成功" -ForegroundColor Green
} catch {
    Write-Host "文件上传失败: $_" -ForegroundColor Red
    exit 1
}

# 3. 在VM中启动后端服务
Write-Host "启动后端服务..." -ForegroundColor Cyan
try {
    plink -batch -pw $VM_PASSWORD $VM_USER@$VM_HOST "cd $VM_DEPLOY_PATH/backend && nohup python3 main.py > backend.log 2>&1 &"
    Write-Host "服务启动命令已执行" -ForegroundColor Green
} catch {
    Write-Host "启动服务失败: $_" -ForegroundColor Red
    exit 1
}

# 4. 验证服务是否启动成功
Write-Host "验证服务启动..." -ForegroundColor Cyan
Start-Sleep -Seconds 3
try {
    $serviceStatus = plink -batch -pw $VM_PASSWORD $VM_USER@$VM_HOST "ps aux | grep python3 | grep main.py"
    if ($serviceStatus) {
        Write-Host "服务启动成功！" -ForegroundColor Green
    } else {
        Write-Host "服务启动失败，未找到运行中的进程" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "验证服务状态失败: $_" -ForegroundColor Yellow
}

Write-Host "更新完成！" -ForegroundColor Green
Write-Host "后端服务已在VM中重启，地址: http://$VM_HOST:8000" -ForegroundColor Yellow
Write-Host "测试诊断接口: curl -X POST http://$VM_HOST:8000/api/diagnose -H \"Content-Type: application/json\" -d '{\"pod_name\":\"calico-node-k88st\",\"namespace\":\"calico-system\"}'" -ForegroundColor Yellow
Write-Host "测试修复方案接口: curl -X POST http://$VM_HOST:8000/api/plan-fix -H \"Content-Type: application/json\" -d '{\"diagnosis\":{\"summary\":\"Pod 运行正常\",\"root_cause\":\"未发现异常\",\"severity\":\"low\",\"symptoms\":[],\"suggested_actions\":[\"定期监控 Pod 状态\"]},\"pod_name\":\"calico-node-k88st\",\"namespace\":\"calico-system\"}'" -ForegroundColor Yellow
Write-Host "测试执行计划接口: curl -X POST http://$VM_HOST:8000/api/execute-plan -H \"Content-Type: application/json\" -d '{\"plan\":{\"plan_summary\":\"监控 Pod 状态\",\"commands\":[\"kubectl get pod calico-node-k88st -n calico-system\"],\"risk_level\":\"low\",\"requires_approval\":false,\"rollback_hint\":\"无需回滚，仅监控状态\"},\"namespace\":\"calico-system\",\"pod_name\":\"calico-node-k88st\"}'" -ForegroundColor Yellow
