这是一份根据你的要求，整合了这次对话的基础设施配置流程（NFS, NIS）以及你上传的关于网络解析、组件通信、依赖安装及底层权限同步的 Markdown SOP（Standard Operating Procedure）的完整标准文档。



你可以将以下内容保存为 `SLURM\_MultiNode\_Cluster\_Setup\_SOP.md` 文件，作为未来继续添加新计算节点（如 `node02`, `node03` ... `nodeN`）的参考手册。



---



\# 多节点 SLURM 集群基础设施扩容与维护标准操作流程 (SOP)



\*\*文档版本\*\*：v1.1

\*\*适用场景\*\*：从单机 SLURM 节点平滑扩容至多节点集群；基于 NIS 环境配置计算节点；解决包含 NVML GPU 识别的定制化安装。

\*\*环境架构示例\*\*：



\* \*\*主节点 (`main`)\*\*：同时承担控制节点 (`slurmctld`)、数据库 (`slurmdbd`)、计算节点 及 \*\*NIS Server\*\*、\*\*NFS Server\*\* 角色。

\* \*\*计算节点 (`node01`, `nodeN`)\*\*：承担计算节点 (`slurmd`) 及 \*\*NIS Client\*\*、\*\*NFS Client\*\* 角色。具有 GPU 资源。



---



\## 目录



1\. 网络解析与主机名配置 (核心防坑)

2\. 基础设施 Phase 1：NIS 账户同步服务配置

3\. 基础设施 Phase 2：NFS 共享存储服务配置

4\. 安全基础：MUNGE 密钥与系统账户 UID/GID 同步

5\. SLURM 核心组件配置更新与热加载

6\. 计算节点 SLURM 安装与集群加入

7\. 常见状态排障指南 (SOP)



---



\## 1. 网络解析与主机名配置 (核心防坑)



在分布式集群中，管理节点的主机名\*\*绝对不能\*\*解析到本地环回地址（Loopback），否则计算节点将无法与主节点建立 TCP 连接（报错 `Connection refused`）。



\### 1.1 修改主节点 (`main`) 的 `/etc/hosts`



必须注销现代 Ubuntu 系统默认生成的 `127.0.1.1 main`，将其显式指向集群局域网 IP。



```bash

\# 在 main 上编辑 /etc/hosts

127.0.0.1 localhost

\# 127.0.1.1 main  <-- ⚠️ 必须注释或删除此行



\# 添加集群局域网 IP 解析

10.0.0.1 main

10.0.1.1 node01

\# 10.0.X.X nodeN



```



\### 1.2 修改新计算节点 (`nodeN`) 的 `/etc/hosts`



计算节点必须能够解析主节点的主机名：



```bash

\# 在 nodeN 上编辑 /etc/hosts

127.0.0.1 localhost

10.0.0.1 main

10.0.1.1 node01

\# 10.0.X.X nodeN



```



\*验证方法：在 `nodeN` 上执行 `ping -c 2 main`，必须返回 `10.0.0.1` 且无丢包。\*



---



\## 2. 基础设施 Phase 1：NIS 账户同步服务配置



物理计算用户的账号密码应通过 NIS 下发。



\### 2.1 主节点 (`main`)：配置 NIS Server



1\. \*\*安装软件包：\*\*

```bash

sudo apt update

sudo apt install nis



```





2\. \*\*设置域名：\*\* 假设域名为 `nisdomain`。

```bash

echo "nisdomain" | sudo tee /etc/defaultdomain

sudo domainname nisdomain



```





3\. \*\*配置 Server 角色：\*\* 修改 `/etc/default/nis`，设置 `NISSERVER=master`。

4\. \*\*配置安全网络：\*\* 修改 `/etc/ypserv.securenets`，添加允许访问的网段，注释掉 `0.0.0.0`。

```text

255.0.0.0       127.0.0.0

255.255.0.0     10.0.0.0  # 你的局域网网段



```





5\. \*\*初始化数据库：\*\*

```bash

sudo /usr/lib/yp/ypinit -m



```





\* ⚠️ \*\*关键要点\*\*：在提示 `next host to add` 时，确保列表中\*\*只有\*\* `main`（或加上未来的从服务器），\*\*直接按 `Ctrl + D` 结束添加，然后输入 `y` 确认\*\*。





6\. \*\*启动服务：\*\*

```bash

sudo systemctl restart rpcbind ypserv yppasswdd

sudo systemctl enable rpcbind ypserv yppasswdd

sudo make -C /var/yp  # 手动触发一次数据库更新



```







\### 2.2 计算节点 (`nodeN`)：配置 NIS Client



1\. \*\*安装软件包：\*\*

```bash

sudo apt update

sudo apt install nis



```





\*(安装时弹出界面请输入域名 `nisdomain`)\*

2\. \*\*手动确认域名 (保险)：\*\*

```bash

echo "nisdomain" | sudo tee /etc/defaultdomain

sudo domainname nisdomain



```





3\. \*\*指向 Server：\*\* 编辑 `/etc/yp.conf`，末尾添加：

```text

domain nisdomain server main



```





4\. \*\*修改 NSS 优先级 (关键)：\*\* 编辑 `/etc/nsswitch.conf`，在 `passwd`、`group`、`shadow` 后加上 `nis`。

```text

passwd:         files systemd nis

group:          files systemd nis

shadow:         files nis



```





5\. \*\*重启服务并验证：\*\*

```bash

sudo systemctl restart rpcbind ypbind

sudo systemctl enable rpcbind ypbind



ypwhich     # 预期输出: main

id 某NIS用户 # 预期输出: 成功的UID/GID信息



```







---



\## 3. 基础设施 Phase 2：NFS 共享存储服务配置



用于共享主节点的软件安装目录 (`/opt`, `/usr/local`) 和 NIS 用户的家目录。



\### 3.1 主节点 (`main`)：配置 NFS Server



1\. \*\*安装软件包：\*\*

```bash

sudo apt update

sudo apt install nfs-kernel-server



```





2\. \*\*配置共享目录：\*\* 编辑 `/etc/exports`。

\* ⚠️ \*\*路径对齐关键\*\*：确认 NIS 用户的家目录基准路径（例如是 `/home` 还是 `/data/home`）。主从节点路径必须完全一致。





```text

\# 示例: 共享局域网

/data/home 10.0.0.0/16(rw,sync,no\_root\_squash,no\_subtree\_check)

/opt       10.0.0.0/16(rw,sync,no\_root\_squash,no\_subtree\_check)

/usr/local 10.0.0.0/16(rw,sync,no\_root\_squash,no\_subtree\_check)



```





3\. \*\*加载配置：\*\*

```bash

sudo exportfs -arv

sudo systemctl restart nfs-kernel-server

sudo systemctl enable nfs-kernel-server



```







\### 3.2 计算节点 (`nodeN`)：配置 NFS Client



1\. \*\*安装软件包：\*\*

```bash

sudo apt update

sudo apt install nfs-common



```





2\. \*\*配置开机挂载 (关键)：\*\* 编辑 `/etc/fstab`，添加挂载点。

\* ⚠️ \*\*路径对齐关键\*\*：新节点必须先手动创建对应的本地挂载目录（如 `sudo mkdir -p /data/home`）。

\* ⚠️ \*\*防卡死关键\*\*：使用 `\_netdev` 参数，确保网络就绪后再挂载。





```text

main:/data/home /data/home nfs rw,defaults,\_netdev 0 0

main:/opt       /opt       nfs rw,defaults,\_netdev 0 0

main:/usr/local /usr/local nfs rw,defaults,\_netdev 0 0



```





3\. \*\*执行挂载与验证：\*\*

```bash

sudo systemctl daemon-reload  # 刷新 systemd 缓存

sudo mount -a

df -h | grep main             # 验证挂载成功



```







---



\## 4. 安全基础：MUNGE 密钥与系统账户 UID/GID 同步



\### 4.1 MUNGE 密钥平滑同步 (零干扰)



当主节点有作业正在运行完成时，\*\*严禁\*\*在主节点重新生成密钥。



1\. \*\*主节点复制密钥：\*\* 将现有密钥放入共享目录。

```bash

sudo cp /etc/munge/munge.key /data/home/munge\_transfer.key



```





2\. \*\*计算节点 (`nodeN`) 同步：\*\*

```bash

sudo systemctl stop munge

sudo cp /data/home/munge\_transfer.key /etc/munge/munge.key

\# 严格设置权限 (权限不对 Munge 会拒绝启动)

sudo chown munge:munge /etc/munge/munge.key

sudo chmod 400 /etc/munge/munge.key

sudo systemctl start munge

sudo systemctl enable munge



```





3\. \*\*主节点清理：\*\* `sudo rm /data/home/munge\_transfer.key`。



\### 4.2 系统级服务账号 UID/GID 同步 (Security Violation 终极修复)



系统级守护进程账户（如 `slurm`, `munge`, UID < 1000）\*\*绝对不能\*\*放入 NIS。它们必须存在于各个节点的本地 `/etc/passwd` 中，且 \*\*UID 和 GID 必须全集群绝对一致\*\*。若 ID 不一致，会导致任务提交报错 `Security violation`。



以主节点 ID 为基准（假设为 `slurm:998`, `munge:115:121`）。



\*\*新计算节点 (`nodeN`) 冲突修复标准流程（騰笼换鸟）：\*\*

假设 `998` 在新节点上已被 `systemd-network` 占用。



```bash

\# 在新节点执行 (严格按顺序)



\# 1. 停止相关服务，强杀残留占用进程

sudo systemctl stop munge slurmd systemd-networkd systemd-networkd.socket

sudo pkill -u 998   



\# 2. 将占用 998 的系统服务迁移到低位空闲 ID (如 990)

sudo usermod -u 990 systemd-network

sudo groupmod -g 990 systemd-network

sudo find / -uid 998 -exec chown -h 990 {} + 2>/dev/null

sudo find / -gid 998 -exec chgrp -h 990 {} + 2>/dev/null



\# 3. 将 slurm 正式对齐到主节点基准 998

sudo groupmod -g 998 slurm

sudo usermod -u 998 -g 998 slurm



\# 4. 将 munge 对齐到主节点基准 115:121

sudo groupmod -g 121 munge

sudo usermod -u 115 -g 121 munge



\# 5. 修复核心服务目录的属主权限

sudo chown -R slurm:slurm /var/spool/slurmd /var/log/slurm 2>/dev/null

sudo chown -R munge:munge /etc/munge /var/log/munge /var/lib/munge /run/munge 2>/dev/null



\# 6. 重启服务

sudo systemctl start systemd-networkd.socket systemd-networkd

sudo systemctl start munge

\# ⚠️ 此时先别启动 slurmd，等配置文件同步



```



---



\## 5. SLURM 核心组件配置更新与热加载



将主节点的 `slurm.conf` 中的记账寻址从本地环回切换为局域网寻址。



\### 5.1 修改主节点配置文件



在主节点修改以下两个文件：



\*\*`/etc/slurm/slurm.conf`\*\*



```ini

\# 将 127.0.0.1 或 localhost 改为局域网主机名 main

AccountingStorageHost=main



```



\*\*`/etc/slurm/slurmdbd.conf`\*\* ⚠️ \*极易遗漏\*



```ini

\# 必须与 slurm.conf 保持寻址同步，否则控制进程无法连接数据库

DbdHost=main



```



\### 5.2 热加载配置（不中断运行作业）



按照以下顺序应用配置，主节点正在运行的任务不会受到任何影响：



```bash

\# 1. 重启数据库进程 (短暂暂停记账写入，后续自动补录)

sudo systemctl restart slurmdbd



\# 2. 热加载主节点控制进程配置 (刷新网络监听与记账客户端指向)

sudo scontrol reconfigure



```



---



\## 6. 计算节点 SLURM 安装与集群加入



\### 6.1 安装 NVIDIA 驱动 (异构 GPU 环境)



\*驱动必须在计算节点本地安装，不能共享。\* 驱动版本必须适合本地卡（如 P100）。



```bash

sudo apt update

sudo apt install nvidia-driver-535  # 示例版本

sudo reboot

nvidia-smi  # 验证识别正常



```



\*(⚠️ \*\*CUDA Toolkits\*\* 可以通过 NFS 共享 `/usr/local` 复用主节点的)\*



\### 6.2 安装定制版 SLURM (含 NVML 支持)



如果主节点 SLURM 源码编译包含了 `AutoDetect=nvml` 等插件，计算节点\*\*不能\*\*使用 `apt install slurmd`（不含 NVML）。必须使用主节点编译生成的 `.deb` 包。



```bash

\# 在 main 节点执行：将编译好的定制deb包拷贝到 NFS 共享目录

cd /data/home/qhyu/

cp -r /opt/slurm/build/23.11.5/deb/ slurm\_debs\_custom/



```



```bash

\# 在计算节点 nodeN 执行：联合依赖包进行本地安装

cd /data/home/qhyu/slurm\_debs\_custom/



\# 必须卸载官方默认阉割版

sudo apt-get remove --purge slurmd slurm-client slurm-wlm

sudo apt-get autoremove



\# 本地安装定制deb

sudo apt install ./libjwt0\*.deb \\

&nbsp;                ./slurm-smd\_23.11.5-1\_amd64.deb \\

&nbsp;                ./slurm-smd-slurmd\_23.11.5-1\_amd64.deb \\

&nbsp;                ./slurm-smd-client\_23.11.5-1\_amd64.deb



```



\### 6.3 同步全局配置文件



将主节点上更新后的配置文件分发至新节点。



\* ⚠️ \*\*全集群一致性\*\*：新旧节点的配置文件必须 100% 一致。



```bash

\# 在新计算节点 nodeN 上操作

sudo cp /data/home/qhyu/slurm.conf /etc/slurm/slurm.conf

sudo cp /data/home/qhyu/gres.conf /etc/slurm/gres.conf

sudo cp /data/home/qhyu/cgroup.conf /etc/slurm/cgroup.conf



```



\### 6.4 最终合并与启动



1\. \*\*主节点热加载热扩容\*\*：修改主节点 `/etc/slurm/slurm.conf` 末尾，加上 `nodeN` 的节点定义和队列设置。执行 `sudo scontrol reconfigure`。

2\. \*\*计算节点服务启动\*\*：

```bash

\# 在计算节点 nodeN

sudo systemctl start slurmd

sudo systemctl enable slurmd



```







---



\## 7. 常见状态排障指南 (SOP)



\### 7.1 错误的状态恢复做法 ❌



\*\*严禁\*\*使用 `sudo scontrol update nodename=node01 state=FUTURE` 然后再 `RESUME` 的方式强行消除 `sinfo` 的带星号状态。这只是视觉欺骗，底层通信断裂，会导致作业卡死。



\### 7.2 计算节点状态 `inval` ( Invalid ) 处理



\*\*现象\*\*：`node01` 状态显示为 `inval`。

\*\*原因\*\*：两台机器的配置文件对不上（硬件汇报不符或哈希值不同）。

\*\*标准修复\*\*：确保配置文件完全同步到新节点，并在新节点 `sudo systemctl restart slurmd`，当其带着正确信息重新报到时，`inval` 会\*\*自动消失\*\*。



\### 7.3 计算节点状态 `idle\*` ( 带星号 ) 或作业卡 `CG` ( Completing )



这在清理本地用户后或网络故障时常见，会导致作业卡在 `CG` 状态无法通过 `scancel` 取消。



当确认底层网络、Munge 密钥和系统账号 UID 修复后，执行主节点硬重置：



```bash

\# 1. 将节点置为 DOWN 并注明原因，此操作会瞬间强制清理所有卡在 CG 状态的“幽灵作业”

sudo scontrol update nodename=node01 state=DOWN reason="clear\_stuck\_jobs"



\# 2. 重新拉起节点

sudo scontrol update nodename=node01 state=RESUME



```



\*验证方法：查看 `sinfo` 节点状态无星号，提交测试任务运行正常。\*



```bash

srun -p P100 -N 1 --gres=gpu:1 nvidia-smi



```

