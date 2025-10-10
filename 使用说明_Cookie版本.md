# Cookie多账户签到脚本使用说明

## 🎯 脚本特点

**你只需要这一个脚本：`multi_site_sign_cookie_only.py`**

✅ **纯Cookie登录** - 无需账号密码，避免CF机器人检测  
✅ **双站点支持** - 同时支持NodeSeek和DeepFlood  
✅ **多账户管理** - 每个站点支持多个Cookie账户  
✅ **通知优化** - 每天只发送一次汇总通知，不再频繁骚扰  
✅ **简化配置** - 去掉复杂的验证码配置，只需要Cookie  

## 📋 环境变量配置

### 必需的环境变量

```bash
# NodeSeek站点Cookie（多个Cookie用&分隔）
NS_COOKIE=cookie1&cookie2&cookie3

# DeepFlood站点Cookie（多个Cookie用&分隔）  
DF_COOKIE=cookie1&cookie2&cookie3

# 可选配置
NS_RANDOM=true
```

### Cookie获取方法

1. **浏览器登录** 对应网站
2. **F12打开开发者工具** → Network标签
3. **手动签到一次** 或刷新页面
4. **找到请求** → Headers → Cookie
5. **复制完整Cookie值**

### 多账户配置示例

```bash
# 单账户
NS_COOKIE=sessionid=abc123; csrftoken=def456; userid=789

# 多账户（用&分隔）
NS_COOKIE=sessionid=abc123; csrftoken=def456&sessionid=xyz789; csrftoken=uvw012

# DeepFlood同理
DF_COOKIE=sessionid=aaa111; csrftoken=bbb222&sessionid=ccc333; csrftoken=ddd444
```

## 🚀 青龙面板配置

### 1. 上传脚本
将 `multi_site_sign_cookie_only.py` 上传到青龙面板脚本目录

### 2. 配置环境变量
在青龙面板环境变量中添加：
- `NS_COOKIE` - NodeSeek的Cookie
- `DF_COOKIE` - DeepFlood的Cookie  
- `NS_RANDOM` - 设置为true（可选）

### 3. 添加定时任务
```bash
# 每天早上8:30执行
30 8 * * * python3 /ql/scripts/multi_site_sign_cookie_only.py
```

## 📁 文件结构

```
你的目录/
├── multi_site_sign_cookie_only.py    # 主脚本（这一个就够了）
└── cookie/                           # 自动创建的目录
    └── notification_status.json      # 通知状态记录
```

## 🔔 通知说明

### 新的通知机制
- **每天只发送一次** 汇总通知
- **包含所有账户** 的签到结果
- **详细统计信息** 包括近30天收益

### 通知内容示例
```
NodeSeek 签到汇总
成功: 3 个账号
失败: 0 个账号

账号1: 签到成功，获得 5 个鸡腿
  近30天已签到25天，共获得125个鸡腿

账号2: 签到成功，获得 3 个鸡腿  
  近30天已签到23天，共获得98个鸡腿

账号3: 签到成功，获得 4 个鸡腿
  近30天已签到28天，共获得140个鸡腿
```

## ❓ 常见问题

### Q: 只有这一个脚本就够了吗？
**A: 是的！** `multi_site_sign_cookie_only.py` 这一个脚本就能处理两个站点的多账户签到。

### Q: 需要配置验证码相关的环境变量吗？
**A: 不需要！** 纯Cookie登录，无需 `SOLVER_TYPE`、`API_BASE_URL`、`CLIENTT_KEY` 等验证码配置。

### Q: Cookie过期了怎么办？
**A: 手动更新Cookie** 到环境变量中即可，脚本会自动使用新Cookie。

### Q: 如何知道Cookie是否有效？
**A: 运行脚本后查看日志**，会显示每个账号的签到结果。

### Q: 可以只签到一个站点吗？
**A: 可以！** 只配置对应站点的Cookie环境变量即可：
- 只要NodeSeek：只配置 `NS_COOKIE`
- 只要DeepFlood：只配置 `DF_COOKIE`  
- 两个都要：两个都配置

## 🎉 优势总结

1. **简单** - 只需要一个脚本文件
2. **稳定** - 纯Cookie登录，避开CF检测
3. **智能** - 自动处理多账户，汇总通知
4. **灵活** - 支持单站点或双站点使用
5. **清爽** - 每天只发一次通知，不再骚扰

现在你可以删除其他复杂的脚本，只用这一个就够了！