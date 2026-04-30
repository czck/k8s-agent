# 后端部署到VM指南

## 架构说明

```
浏览器
   ↓
Next.js（本地）
   ↓
FastAPI（VM）
   ↓
Kubernetes（本机/VM）
```

## 前提条件

1. VM中已安装Kubernetes集群
2. VM中已安装Python 3.8+
3. 本地已安装PuTTY（用于SSH连接）
4. 本地已安装PowerShell 5+

## 部署步骤

### 1. 修改部署配置

编辑 `deploy-to-vm.ps1` 文件，修改以下配置：

```powershell
$VM_HOST = "192.168.86.130"  # VM的IP地址
$VM_USER = "root"             # VM的用户名
$VM_PASSWORD = ""             # VM的密码
$VM_DEPLOY_PATH = "/root/k8s-ai-ops-agent"  # VM中的部署路径
```

### 2. 安装PuTTY

如果尚未安装PuTTY，请从以下地址下载并安装：
https://www.putty.org/

安装后确保 `plink.exe` 和 `pscp.exe` 在系统PATH中。

### 3. 执行部署脚本

在PowerShell中运行部署脚本：

```powershell
cd d:\AI\K8s-AI-Ops-Agent
.\deploy-to-vm.ps1
```

### 4. 验证部署

部署完成后，可以通过以下方式验证：

1. 检查后端服务是否运行：
   ```powershell
   plink root@192.168.86.130 "ps aux | grep python"
   ```

2. 查看后端日志：
   ```powershell
   plink root@192.168.86.130 "tail -f /root/k8s-ai-ops-agent/backend/backend.log"
   ```

3. 测试API接口：
   ```powershell
   Invoke-WebRequest -Uri http://192.168.86.130:8000/health -UseBasicParsing
   ```

### 5. 修改前端配置

修改前端代码，将API请求地址指向VM中的后端：

```typescript
// frontend/app/page.tsx
const API_BASE_URL = 'http://192.168.86.130:8000';
```

## 手动部署（可选）

如果自动部署脚本无法使用，可以手动执行以下步骤：

### 1. 在VM中创建部署目录

```bash
ssh root@192.168.86.130
mkdir -p /root/k8s-ai-ops-agent/backend
```

### 2. 上传后端代码

在本地PowerShell中执行：

```powershell
pscp -r backend\* root@192.168.86.130:/root/k8s-ai-ops-agent/backend/
```

### 3. 在VM中安装依赖

```bash
ssh root@192.168.86.130
cd /root/k8s-ai-ops-agent/backend
pip3 install -r requirements.txt
```

### 4. 启动后端服务

```bash
cd /root/k8s-ai-ops-agent/backend
nohup python3 main.py > backend.log 2>&1 &
```

## 常见问题

### 1. SSH连接失败

- 检查VM的SSH服务是否启动
- 检查防火墙是否允许SSH连接（端口22）
- 确认用户名和密码是否正确

### 2. 后端服务无法启动

- 检查Python版本是否符合要求（Python 3.8+）
- 检查依赖是否正确安装
- 查看后端日志获取详细错误信息

### 3. API请求失败

- 检查后端服务是否正在运行
- 检查防火墙是否允许HTTP连接（端口8000）
- 检查CORS配置是否正确

### 4. Kubernetes连接失败

- 确认VM中已安装Kubernetes集群
- 检查kubeconfig文件是否存在且配置正确
- 确认kubeconfig文件位于默认路径（~/.kube/config）

## 停止后端服务

如果需要停止后端服务，可以执行：

```bash
ssh root@192.168.86.130
ps aux | grep python  # 查找进程ID
kill <进程ID>
```

## 更新后端代码

如果需要更新后端代码，可以重新执行部署脚本，或手动上传修改后的文件并重启服务。

```bash
ssh root@192.168.86.130
cd /root/k8s-ai-ops-agent/backend
ps aux | grep python | grep main.py | awk '{print $2}' | xargs kill
nohup python3 main.py > backend.log 2>&1 &
```
