# 部署脚本 - 将后端代码上传到VM并启动服务

# VM连接配置
$VM_HOST = "192.168.86.130"
$VM_USER = "root"  # 根据实际情况修改
$VM_PASSWORD = ""  # 根据实际情况修改
$VM_DEPLOY_PATH = "/root/k8s-ai-ops-agent"  # VM中的部署路径

Write-Host "开始部署后端到VM..." -ForegroundColor Green

# 检查是否安装了plink (PuTTY的命令行工具)
$plinkPath = "plink.exe"
$pscpPath = "pscp.exe"

# 检查plink和pscp是否在PATH中
if (-not (Get-Command $plinkPath -ErrorAction SilentlyContinue)) {
    Write-Host "错误: 未找到plink.exe，请先安装PuTTY并确保plink.exe在PATH中" -ForegroundColor Red
    Write-Host "下载地址: https://www.putty.org/" -ForegroundColor Yellow
    exit 1
}

# 1. 在VM中创建部署目录
Write-Host "创建部署目录..." -ForegroundColor Cyan
echo y | plink -batch -pw $VM_PASSWORD $VM_USER@$VM_HOST "mkdir -p $VM_DEPLOY_PATH/backend"

# 2. 上传后端代码到VM
Write-Host "上传后端代码..." -ForegroundColor Cyan
$backendPath = Join-Path $PSScriptRoot "backend"
pscp -batch -pw $VM_PASSWORD -r "$backendPath\*" "$VM_USER@$VM_HOST:$VM_DEPLOY_PATH/backend/"

# 3. 在VM中安装Python依赖
Write-Host "安装Python依赖..." -ForegroundColor Cyan
plink -batch -pw $VM_PASSWORD $VM_USER@$VM_HOST "cd $VM_DEPLOY_PATH/backend && pip3 install -r requirements.txt"

# 4. 在VM中启动后端服务
Write-Host "启动后端服务..." -ForegroundColor Cyan
plink -batch -pw $VM_PASSWORD $VM_USER@$VM_HOST "cd $VM_DEPLOY_PATH/backend && nohup python3 main.py > backend.log 2>&1 &"

Write-Host "部署完成！" -ForegroundColor Green
Write-Host "后端服务已在VM中启动，地址: http://$VM_HOST:8001" -ForegroundColor Yellow
Write-Host "查看日志: plink $VM_USER@$VM_HOST 'tail -f $VM_DEPLOY_PATH/backend/backend.log'" -ForegroundColor Yellow
