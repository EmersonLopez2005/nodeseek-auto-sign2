# MJJBox TL3 Requirements Button - 用户脚本

## 📖 简介

这是一个用于 mjjbox.com 的 Tampermonkey/Greasemonkey 用户脚本，用于在用户等级面板中添加一个"查看详细要求"按钮，方便管理员快速访问用户的 TL3（Trust Level 3）要求页面。

## ✨ 功能特性

- 🎯 **智能按钮插入** - 自动在等级面板中添加 TL3 按钮
- 🔐 **权限检测** - 自动检测用户是否具有管理员权限
- 🎨 **主题适配** - 支持亮色、暗色和科技主题
- 📱 **响应式设计** - 适配不同屏幕尺寸
- 🛡️ **错误处理** - 优雅处理用户数据缺失和权限不足的情况
- 💡 **工具提示** - 为禁用状态提供清晰的说明

## 📦 安装

### 前置要求

1. 安装浏览器扩展（选择其一）：
   - [Tampermonkey](https://www.tampermonkey.net/) (推荐)
   - [Greasemonkey](https://www.greasespot.net/)
   - [Violentmonkey](https://violentmonkey.github.io/)

### 安装步骤

1. 安装 Tampermonkey 扩展
2. 点击扩展图标 → "创建新脚本"
3. 复制 `mjjbox-tl3-button.user.js` 的全部内容
4. 粘贴到编辑器中
5. 按 `Ctrl+S` (Windows/Linux) 或 `Cmd+S` (Mac) 保存
6. 访问 [mjjbox.com](https://mjjbox.com) 查看效果

## 🎯 使用说明

### 基本使用

脚本会在页面加载完成后自动运行：

1. **自动检测** - 脚本会自动检测页面中的等级面板
2. **插入按钮** - 在 `.mjjbox-panel-controls` 容器中添加 TL3 按钮
3. **权限验证** - 检测当前用户是否具有管理员权限

### 按钮状态

#### ✅ 已启用（管理员用户）
- 按钮颜色：渐变紫色（亮色主题）/ 深紫色（暗色主题）/ 青绿渐变（科技主题）
- 点击行为：在新标签页打开 TL3 要求页面
- URL 格式：`https://mjjbox.com/admin/users/{userId}/{username}/tl3_requirements`

#### ⛔ 已禁用（非管理员用户）
- 按钮颜色：灰色
- 鼠标悬停：显示提示 "需要管理员权限才能查看"
- 点击行为：无

#### ⚠️ 已禁用（用户数据缺失）
- 按钮颜色：灰色
- 鼠标悬停：显示提示 "无法获取用户信息"
- 点击行为：无

## 🎨 样式定制

### 主题支持

脚本支持三种主题模式：

```css
/* 亮色主题 */
body.theme-light .mjjbox-btn-tl3 {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

/* 暗色主题 */
body.theme-dark .mjjbox-btn-tl3 {
    background: linear-gradient(135deg, #4c51bf 0%, #553c9a 100%);
}

/* 科技主题 */
body.theme-tech .mjjbox-btn-tl3 {
    background: linear-gradient(135deg, #00ff87 0%, #00d4ff 100%);
}
```

### 自定义样式

如需自定义按钮样式，可以修改 `GM_addStyle` 中的 CSS 规则：

```css
.mjjbox-btn-tl3 {
    /* 修改这些属性以自定义外观 */
    padding: 8px 16px;
    border-radius: 6px;
    font-size: 14px;
    /* ... */
}
```

## 🔧 技术实现

### 用户数据获取

脚本使用两种方式获取用户信息：

1. **API 调用** (优先)
   ```javascript
   fetch('/api/user/current')
   ```

2. **页面解析** (备选)
   - 从 URL 中提取 userId: `/users/(\d+)/`
   - 从 DOM 中查找 username: `.user-name, .username, [data-username]`

### 权限检测

脚本使用三种方式检测管理员权限：

1. API 响应中的 `admin` 字段
2. API 响应中的 `role` 字段
3. HEAD 请求测试 `/admin/users` 端点

### 面板检测

脚本会查找以下类名的元素作为等级面板：
- `.mjjbox-level-panel`
- `.level-panel`
- `.user-level-panel`

如果找不到现有面板，脚本会创建一个新的面板。

## 🐛 调试

### 启用调试日志

打开浏览器控制台（F12），脚本会输出以下信息：

- `Failed to fetch user data: {status}` - API 调用失败
- `Error fetching user data: {error}` - 网络错误或其他异常

### 常见问题

#### Q: 按钮没有显示？
A: 检查以下几点：
1. 确认脚本已启用（Tampermonkey 图标显示为绿色）
2. 确认页面 URL 匹配 `https://mjjbox.com/*`
3. 打开控制台查看是否有错误信息
4. 刷新页面重试

#### Q: 按钮始终是灰色的？
A: 可能的原因：
1. 当前用户不是管理员
2. 无法获取用户信息（网络问题或 API 变更）
3. 权限检测失败

#### Q: 点击按钮后页面 404？
A: 可能的原因：
1. 用户 ID 或用户名获取错误
2. TL3 要求页面 URL 已变更
3. 目标用户不存在

## 🔒 安全性

- ✅ 所有外部链接使用 `rel="noopener noreferrer"`
- ✅ API 请求包含 `credentials: 'include'` 确保身份验证
- ✅ 不存储或传输敏感信息
- ✅ 仅在 mjjbox.com 域名下运行

## 📝 更新日志

### v1.0.0 (2024-01-XX)
- ✨ 初始版本发布
- 🎯 支持 TL3 按钮插入
- 🔐 实现权限检测
- 🎨 支持多主题适配
- 📱 响应式设计

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

### 开发指南

1. Fork 本仓库
2. 创建功能分支
3. 修改 `mjjbox-tl3-button.user.js`
4. 在 Tampermonkey 中测试
5. 提交 Pull Request

### 测试清单

- [ ] 按钮在等级面板中正确显示
- [ ] 管理员用户可以点击按钮
- [ ] 非管理员用户看到禁用状态和提示
- [ ] 三种主题下样式正常
- [ ] 响应式布局正常工作
- [ ] 没有 JavaScript 错误

## 📄 许可证

本项目采用 MIT 许可证 - 查看 LICENSE 文件了解详情

## 🙏 致谢

- 感谢 [mjjbox.com](https://mjjbox.com) 提供优质的社区平台
- 感谢 Tampermonkey/Greasemonkey 项目

---

如果这个脚本对你有帮助，请给个 ⭐ Star 支持一下！
