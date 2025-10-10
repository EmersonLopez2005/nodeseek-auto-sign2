# NodeSeek & DeepFlood 自动签到脚本

[![GitHub stars](https://img.shields.io/github/stars/EmersonLopez2005/nodeseek-auto-sign?style=flat-square)](https://github.com/EmersonLopez2005/nodeseek-auto-sign/stargazers)
[![GitHub forks](https://img.shields.io/github/forks/EmersonLopez2005/nodeseek-auto-sign?style=flat-square)](https://github.com/EmersonLopez2005/nodeseek-auto-sign/network)
[![GitHub issues](https://img.shields.io/github/issues/EmersonLopez2005/nodeseek-auto-sign?style=flat-square)](https://github.com/EmersonLopez2005/nodeseek-auto-sign/issues)
[![GitHub license](https://img.shields.io/github/license/EmersonLopez2005/nodeseek-auto-sign?style=flat-square)](https://github.com/EmersonLopez2005/nodeseek-auto-sign/blob/main/LICENSE)

> 🚀 支持 NodeSeek 和 DeepFlood 两个论坛的多账户自动签到脚本，支持Cookie失效自动登录，专为青龙面板优化

## 📦 相关仓库

- **账号密码登录版**：https://github.com/EmersonLopez2005/nodeseek-auto-sign2
- **Cookie登录版**：https://github.com/EmersonLopez2005/nodeseek-auto-sign

## 📦 依赖安装

在运行脚本前，需要安装必要的依赖包：

```bash
pip install -r requirements.txt
```

依赖包包括：
- `requests>=2.25.0` - HTTP请求库
- `curl-cffi>=0.5.0` - 高性能HTTP客户端（可选，已兼容标准requests）

## ✨ 特性

- 🎯 **双站点支持** - 同时支持 NodeSeek 和 DeepFlood 论坛
- 🔐 **智能登录** - 支持Cookie登录和账号密码自动登录
- 🔄 **自动续期** - Cookie失效时自动通过账号密码登录更新
- 🛡️ **验证码绕过** - 集成CloudFlare Turnstile验证码解决服务
- 👥 **多账户管理** - 每个站点支持无限个账户
- 📱 **智能通知** - 每天只发送一次汇总通知，告别通知轰炸
- 🏷️ **自定义用户名** - 支持为每个账户设置个性化显示名称
- 📊 **签到统计** - 自动统计近30天签到收益
- 🐳 **多环境支持** - 青龙面板、Docker、GitHub Actions
- 🔄 **自动重试** - 网络异常自动重试机制

## 📦 快速开始

### 1. 青龙面板部署（推荐）

#### 拉取仓库
```bash
# 账号密码登录版（推荐）
ql repo https://github.com/EmersonLopez2005/nodeseek-auto-sign2.git

# 或 Cookie登录版
ql repo https://github.com/EmersonLopez2005/nodeseek-auto-sign.git
```

#### 配置环境变量
在青龙面板 `环境变量` 中添加：

```bash
# 必需配置
TG_BOT_TOKEN=你的Telegram机器人Token
TG_USER_ID=你的Telegram用户ID

# 账号密码配置（格式：用户名1&密码1&用户名2&密码2）
NS_COOKIE=你的NodeSeek用户名1&你的NodeSeek密码1&你的NodeSeek用户名2&你的NodeSeek密码2
DF_COOKIE=你的DeepFlood用户名1&你的DeepFlood密码1&你的DeepFlood用户名2&你的DeepFlood密码2

# CloudFreed验证码服务配置（必须配置）
CLOUDFREED_API_KEY=你的CloudFreed客户端密钥
CLOUDFREED_BASE_URL=http://您的服务器IP:3000
```

#### 添加定时任务
```bash
30 8 * * * python3 /ql/scripts/nodeseek-auto-sign/multi_site_sign_cookie_only.py
```

### 2. CloudFreed自建服务部署

#### 部署CloudFreed服务
```bash
docker run -itd \
  --name cloudflyer \
  -p 3000:3000 \
  --restart unless-stopped \
  jackzzs/cloudflyer \
  -K 你的客户端密钥 \
  -H 0.0.0.0
```

#### 验证服务状态
```bash
# 检查容器运行状态
docker ps | grep cloudflyer

# 测试服务连通性
curl http://localhost:3000/health
```

### 3. 获取Cookie和账号密码

#### NodeSeek Cookie获取
1. 浏览器登录 [NodeSeek](https://www.nodeseek.com)
2. 按F12打开开发者工具
3. 切换到 `Network` 标签
4. 访问 [签到页面](https://www.nodeseek.com/board)
5. 在请求中找到Cookie值

#### DeepFlood Cookie获取
1. 浏览器登录 [DeepFlood](https://www.deepflood.com)
2. 按F12打开开发者工具
3. 切换到 `Network` 标签
4. 访问 [签到页面](https://www.deepflood.com/board)
5. 在请求中找到Cookie值

### 3. Telegram通知配置

#### 创建Telegram机器人
1. 在Telegram中搜索 `@BotFather`
2. 发送 `/newbot` 创建新机器人
3. 按提示设置机器人名称
4. 获得 `TG_BOT_TOKEN`

#### 获取用户ID
1. 在Telegram中搜索 `@userinfobot`
2. 发送任意消息获得你的 `TG_USER_ID`

## 🔧 配置说明

### 环境变量详解

| 变量名 | 必需 | 说明 | 示例 |
|--------|------|------|------|
| `TG_BOT_TOKEN` | ✅ | Telegram机器人Token | `1234567890:ABC...` |
| `TG_USER_ID` | ✅ | Telegram用户ID | `123456789` |
| `NS_COOKIE` | ✅ | NodeSeek账号密码（格式：用户名1&密码1&用户名2&密码2） | `user1&pass1&user2&pass2` |
| `DF_COOKIE` | ✅ | DeepFlood账号密码（格式：用户名1&密码1&用户名2&密码2） | `user1&pass1&user2&pass2` |
| `CLOUDFREED_API_KEY` | ✅ | CloudFreed服务API密钥 | `your-api-key` |
| `CLOUDFREED_BASE_URL` | ✅ | CloudFreed服务地址 | `http://您的服务器IP:3000` |
| `NS_RANDOM` | ❌ | 随机参数，默认true | `true` |

### 账号密码配置规则

#### 1. 格式说明
账号密码采用"用户名&密码"格式，多账号用&分隔：
```bash
# 单账号
NS_COOKIE=用户名&密码

# 多账号
NS_COOKIE=用户名1&密码1&用户名2&密码2&用户名3&密码3
```

#### 2. 自动登录流程
1. 脚本从NS_COOKIE/DF_COOKIE解析用户名和密码
2. 检查每个账号的Cookie是否有效
3. 如果Cookie失效，自动使用账号密码登录并获取新Cookie
4. 每个账号的Cookie独立保存到单独的文件中
5. 下次运行时直接使用保存的Cookie，直到再次失效



## 📱 通知效果

### 汇总通知示例
```
NodeSeek 签到汇总
成功: 3 个账号
失败: 0 个账号

张三: 签到成功，获得 5 个鸡腿
  近30天已签到25天，共获得125个鸡腿

李四: 签到成功，获得 3 个鸡腿
  近30天已签到23天，共获得98个鸡腿

王五: 签到成功，获得 4 个鸡腿
  近30天已签到20天，共获得80个鸡腿
```

### 通知优化
- ✅ **每天只发送一次** - 避免重复通知骚扰
- ✅ **汇总统计** - 显示成功/失败账号数量
- ✅ **详细信息** - 包含每个账号的签到结果和统计
- ✅ **分站点通知** - NodeSeek和DeepFlood分别发送

## 🐳 其他部署方式

### Docker部署
```bash
# 克隆仓库
git clone https://github.com/EmersonLopez2005/nodeseek-auto-sign.git
cd nodeseek-auto-sign

# 创建Cookie文件
mkdir cookie
echo "你的NodeSeek_Cookie" > cookie/NODESEEK_COOKIE.txt
echo "你的DeepFlood_Cookie" > cookie/DEEPFLOOD_COOKIE.txt

# 运行脚本（支持自动登录版本）
python3 multi_site_sign_cookie_only.py
```

### GitHub Actions部署
1. Fork本仓库
2. 在仓库 `Settings` → `Secrets and variables` → `Actions` 中添加环境变量
3. 启用 GitHub Actions 工作流

## 📋 文件说明

```
nodeseek-auto-sign/
├── multi_site_sign_cookie_only.py    # 主脚本（支持自动登录，推荐使用）
├── multi_site_sign_simple.py         # 简单版本脚本
├── notify.py                         # 通知模块
├── turnstile_solver.py              # CloudFlare验证码解决器
├── yescaptcha.py                    # 验证码服务集成
├── requirements.txt                  # 依赖包列表
├── README.md                        # 使用说明
└── cookie/                          # Cookie存储目录（Docker用）
    ├── notification_status.json     # 通知状态记录
    ├── NODESEEK_COOKIE.txt          # NodeSeek Cookie文件
    └── DEEPFLOOD_COOKIE.txt         # DeepFlood Cookie文件
```

## 🔍 常见问题

### Q: 支持账号密码登录吗？
A: 是的！现在完全采用账号密码登录方式，支持Cookie失效时的自动登录，集成了CloudFreed验证码解决服务。每个账号的Cookie会独立保存，下次运行直接使用。

### Q: 如何配置CloudFreed服务？
A: 需要部署CloudFreed自建服务，具体命令参考部署说明。服务运行后配置CLOUDFREED_API_KEY环境变量即可。

### Q: Cookie失效后会自动更新吗？
A: 是的！当检测到Cookie失效时，脚本会自动使用配置的账号密码登录，并更新Cookie。每个账号的Cookie会独立保存到单独的文件中。

### Q: Cookie多久需要更新？
A: 通常Cookie有效期为1-3个月，失效后需要重新获取。脚本会自动检测Cookie失效并在通知中提醒。

### Q: 可以只使用其中一个站点吗？
A: 可以，只配置对应站点的Cookie即可。未配置的站点会自动跳过。

### Q: 通知发送失败怎么办？
A: 检查 `TG_BOT_TOKEN` 和 `TG_USER_ID` 是否正确，确保机器人已启动对话。

### Q: CloudFreed可以正常调用吗？
A: 需要确保：
1. CloudFreed服务已正确部署并运行
2. `CLOUDFREED_API_KEY` 和 `CLOUDFREED_BASE_URL` 环境变量已正确配置
3. 服务地址可访问（默认 http://localhost:3000）

### Q: 忘记CloudFreed密钥怎么办？
A: 如果忘记了客户端密钥：
1. 查看容器日志获取密钥：`docker logs cloudflyer`
2. 日志中会显示生成的客户端密钥
3. 重新配置环境变量 `CLOUDFREED_API_KEY`
4. 确保 `CLOUDFREED_BASE_URL` 指向正确的服务地址

### Q: 签到失败怎么办？
A: 通常是Cookie失效导致，重新获取Cookie即可。也可能是网络问题，脚本会自动重试。

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情

## ⭐ Star History

[![Star History Chart](https://api.star-history.com/svg?repos=EmersonLopez2005/nodeseek-auto-sign&type=Date)](https://star-history.com/#EmersonLopez2005/nodeseek-auto-sign&Date)

## 🙏 致谢

- 感谢 [NodeSeek](https://www.nodeseek.com) 和 [DeepFlood](https://www.deepflood.com) 提供优质的技术社区
- 感谢所有贡献者和用户的支持

---

如果这个项目对你有帮助，请给个 ⭐ Star 支持一下！