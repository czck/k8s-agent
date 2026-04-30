"""SSH 客户端服务 —— 基于 paramiko"""

from __future__ import annotations

import io

import paramiko

from schemas.response import SSHResultData


def run_command(
    host: str,
    username: str,
    command: str,
    port: int = 22,
    password: str | None = None,
    private_key: str | None = None,
    timeout: int = 30,
) -> SSHResultData:
    """
    通过 SSH 在远程主机上执行命令并返回结果。

    认证优先级：private_key > password
    """
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    connect_kwargs: dict = {
        "hostname": host,
        "port": port,
        "username": username,
        "timeout": timeout,
    }

    if private_key:
        pkey = paramiko.RSAKey.from_private_key(io.StringIO(private_key))
        connect_kwargs["pkey"] = pkey
    elif password:
        connect_kwargs["password"] = password
    # 若两者都没给，paramiko 会尝试系统 SSH agent / 默认密钥

    try:
        ssh.connect(**connect_kwargs)
        stdin, stdout, stderr = ssh.exec_command(command, timeout=timeout)

        exit_code = stdout.channel.recv_exit_status()
        out = stdout.read().decode("utf-8", errors="replace")
        err = stderr.read().decode("utf-8", errors="replace")

        return SSHResultData(
            host=host,
            command=command,
            exit_code=exit_code,
            stdout=out,
            stderr=err,
        )
    finally:
        ssh.close()
