# MJJBox TL3 Button - 测试指南

## 🧪 测试清单

### 1. 基础功能测试

#### 1.1 按钮插入测试
- [ ] 访问 mjjbox.com 任意用户页面
- [ ] 确认页面加载完成后按钮显示在等级面板中
- [ ] 确认按钮文本为 "📊 查看详细要求"
- [ ] 确认按钮位于 `.mjjbox-panel-controls` 容器内

#### 1.2 用户数据获取测试
- [ ] 打开浏览器控制台（F12）
- [ ] 检查是否有 API 调用 `/api/user/current`
- [ ] 验证控制台没有错误信息
- [ ] 如果 API 失败，确认脚本使用页面解析获取数据

#### 1.3 权限检测测试

**管理员用户测试：**
- [ ] 使用管理员账号登录
- [ ] 确认按钮为启用状态（彩色渐变）
- [ ] 点击按钮，确认在新标签页打开
- [ ] 验证 URL 格式：`https://mjjbox.com/admin/users/{userId}/{username}/tl3_requirements`
- [ ] 确认 userId 和 username 正确

**普通用户测试：**
- [ ] 使用普通账号登录
- [ ] 确认按钮为禁用状态（灰色）
- [ ] 鼠标悬停，确认显示提示："需要管理员权限才能查看"
- [ ] 点击按钮，确认无反应

**未登录用户测试：**
- [ ] 退出登录
- [ ] 确认按钮为禁用状态（灰色）
- [ ] 鼠标悬停，确认显示提示："无法获取用户信息"

### 2. 样式和主题测试

#### 2.1 亮色主题测试
- [ ] 切换到亮色主题（如果站点支持）
- [ ] 确认按钮使用渐变紫色 (#667eea → #764ba2)
- [ ] 鼠标悬停，确认颜色反转
- [ ] 确认有向上移动 2px 的动画效果
- [ ] 确认有阴影增强效果

#### 2.2 暗色主题测试
- [ ] 切换到暗色主题
- [ ] 确认按钮使用深紫色渐变 (#4c51bf → #553c9a)
- [ ] 验证悬停效果与亮色主题一致
- [ ] 确认按钮在暗色背景下清晰可见

#### 2.3 科技主题测试
- [ ] 切换到科技主题（如果站点支持）
- [ ] 确认按钮使用青绿渐变 (#00ff87 → #00d4ff)
- [ ] 确认文字颜色为黑色 (#000000)
- [ ] 验证悬停效果正常

#### 2.4 响应式测试
- [ ] 调整浏览器窗口大小（1920px → 1366px → 768px → 375px）
- [ ] 确认按钮在不同尺寸下正常显示
- [ ] 确认与其他控件的间距合理（gap: 10px）
- [ ] 确认按钮文字不会溢出或换行

### 3. 边界情况测试

#### 3.1 数据缺失测试
- [ ] 模拟 userId 缺失（修改脚本临时注释 userId 获取）
- [ ] 确认按钮禁用并显示提示
- [ ] 模拟 username 缺失
- [ ] 确认按钮禁用并显示提示

#### 3.2 API 错误测试
- [ ] 使用浏览器开发工具阻止 `/api/user/current` 请求
- [ ] 确认脚本回退到页面解析
- [ ] 验证功能仍然正常（如果页面有用户信息）

#### 3.3 动态内容测试
- [ ] 使用 AJAX 导航切换页面（如果站点支持）
- [ ] 确认按钮在新页面加载后正确显示
- [ ] 验证 MutationObserver 正常工作
- [ ] 确认不会出现重复按钮

### 4. 兼容性测试

#### 4.1 浏览器测试
- [ ] Chrome/Chromium (最新版)
- [ ] Firefox (最新版)
- [ ] Edge (最新版)
- [ ] Safari (最新版，如果可用)
- [ ] Opera (可选)

#### 4.2 用户脚本管理器测试
- [ ] Tampermonkey
- [ ] Greasemonkey (仅 Firefox)
- [ ] Violentmonkey

#### 4.3 现有功能回归测试
- [ ] 确认等级面板其他控件正常工作
- [ ] 确认页面其他功能不受影响
- [ ] 确认没有 CSS 样式冲突
- [ ] 确认没有 JavaScript 错误

### 5. 性能测试

#### 5.1 加载性能
- [ ] 测量脚本加载时间（通过控制台 Performance 标签）
- [ ] 确认不超过 100ms
- [ ] 检查是否有不必要的重复 API 调用

#### 5.2 内存测试
- [ ] 打开多个标签页
- [ ] 使用浏览器任务管理器检查内存使用
- [ ] 确认没有内存泄漏

### 6. 安全测试

#### 6.1 XSS 防护测试
- [ ] 确认所有动态插入的内容使用 textContent 而非 innerHTML
- [ ] 确认外部链接包含 `rel="noopener noreferrer"`
- [ ] 验证没有 eval() 或其他不安全代码

#### 6.2 权限测试
- [ ] 确认脚本仅在 mjjbox.com 域名下运行
- [ ] 尝试在其他网站运行，确认不激活
- [ ] 验证 @match 规则正确

## 📝 测试结果记录

### 测试环境信息
- **测试日期：** ___________
- **浏览器：** ___________
- **用户脚本管理器：** ___________
- **脚本版本：** ___________
- **操作系统：** ___________

### 发现的问题
| 问题编号 | 严重程度 | 描述 | 重现步骤 | 状态 |
|---------|---------|------|---------|------|
| 1 | | | | |
| 2 | | | | |
| 3 | | | | |

### 测试结论
- [ ] 所有测试通过
- [ ] 部分测试失败（见上表）
- [ ] 需要进一步测试

## 🔧 调试工具

### 控制台命令

```javascript
// 查看当前用户数据
console.log(document.querySelector('.mjjbox-btn-tl3').href);

// 检查权限状态
console.log(document.querySelector('.mjjbox-btn-tl3').classList.contains('disabled'));

// 触发面板更新
const event = new Event('DOMContentLoaded');
window.dispatchEvent(event);

// 手动调用初始化
// (需要在脚本中暴露 init 函数)
```

### 测试用例脚本

```javascript
// 在控制台运行此脚本以自动测试
(function testTL3Button() {
    const results = {
        buttonExists: !!document.querySelector('.mjjbox-btn-tl3'),
        buttonEnabled: !document.querySelector('.mjjbox-btn-tl3')?.classList.contains('disabled'),
        hasCorrectText: document.querySelector('.mjjbox-btn-tl3')?.textContent.includes('查看详细要求'),
        hasCorrectHref: /\/admin\/users\/\d+\/[^\/]+\/tl3_requirements/.test(
            document.querySelector('.mjjbox-btn-tl3')?.href || ''
        )
    };
    
    console.table(results);
    
    const passed = Object.values(results).filter(v => v).length;
    const total = Object.keys(results).length;
    console.log(`测试结果: ${passed}/${total} 通过`);
    
    return results;
})();
```

## 📞 反馈问题

如果在测试过程中发现问题，请提供以下信息：

1. **问题描述：** 详细描述问题现象
2. **重现步骤：** 如何重现该问题
3. **预期行为：** 应该是什么样的
4. **实际行为：** 实际发生了什么
5. **环境信息：** 浏览器、用户脚本管理器、操作系统
6. **控制台日志：** 相关的错误或警告信息
7. **截图：** 如果可能，提供截图

## ✅ 测试签名

- **测试人员：** ___________
- **测试日期：** ___________
- **签名：** ___________
