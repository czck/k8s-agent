#!/bin/bash

# 部署脚本 - 将后端代码上传到VM并启动服务

# VM连接配置
VM_HOST="192.168.86.130"
VM_USER="root"  # 根据实际情况修改
VM_PASSWORD=""  # 根据实际情况修改，或使用SSH密钥
VM_DEPLOY_PATH="/root/k8s-ai-ops-agent"  # VM中的部署路径

echo "开始部署后端到VM..."

# 1. 在VM中创建部署目录
echo "创建部署目录..."
sshpass -p "$VM_PASSWORD" ssh -o StrictHostKeyChecking=no $VM_USER@$VM_HOST "mkdir -p $VM_DEPLOY_PATH/backend"

# 2. 上传后端代码到VM
echo "上传后端代码..."
sshpass -p "$VM_PASSWORD" scp -o StrictHostKeyChecking=no -r backend/* $VM_USER@$VM_HOST:$VM_DEPLOY_PATH/backend/

# 3. 在VM中安装Python依赖
echo "安装Python依赖..."
sshpass -p "$VM_PASSWORD" ssh -o StrictHostKeyChecking=no $VM_USER@$VM_HOST "cd $VM_DEPLOY_PATH/backend && pip3 install -r requirements.txt"

# 4. 在VM中启动后端服务
echo "启动后端服务..."
sshpass -p "$VM_PASSWORD" ssh -o StrictHostKeyChecking=no $VM_USER@$VM_HOST "cd $VM_DEPLOY_PATH/backend && nohup python3 main.py > backend.log 2>&1 &"

echo "部署完成！"
echo "后端服务已在VM中启动，地址: http://$VM_HOST:8001"
echo "查看日志: ssh $VM_USER@$VM_HOST 'tail -f $VM_DEPLOY_PATH/backend/backend.log'"
