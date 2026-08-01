// ==UserScript==
// @name         NodeSeek / DeepFlood Cookie 同步到青龙
// @namespace    https://github.com/local/ns-df-cookie-sync
// @version      1.0.0
// @description  抓取 NodeSeek / DeepFlood 登录 Cookie（含 HttpOnly），按账号合并后同步到青龙面板的 NS_COOKIE / DF_COOKIE 环境变量
// @author       you
// @match        https://www.nodeseek.com/*
// @match        https://www.deepflood.com/*
// @grant        GM_cookie
// @grant        GM_xmlhttpRequest
// @grant        GM_setValue
// @grant        GM_getValue
// @grant        GM_registerMenuCommand
// @grant        GM_notification
// @connect      *
// @run-at       document-idle
// @noframes
// ==/UserScript==

(function () {
  'use strict';

  // ===== 站点配置 =====
  const SITES = {
    'www.nodeseek.com': { env: 'NS_COOKIE', label: 'NodeSeek' },
    'www.deepflood.com': { env: 'DF_COOKIE', label: 'DeepFlood' },
  };
  const SITE = SITES[location.host];
  if (!SITE) return;

  // ===== 青龙配置读取 =====
  const cfg = {
    get url() { return (GM_getValue('ql_url', '') || '').replace(/\/+$/, ''); },
    get id() { return GM_getValue('ql_client_id', ''); },
    get secret() { return GM_getValue('ql_client_secret', ''); },
  };

  // 页面内嵌配置面板（避免 prompt 失焦即消失，可自由复制粘贴）
  function configQinglong() {
    if (document.getElementById('cs-config-panel')) return;

    const mask = document.createElement('div');
    mask.id = 'cs-config-panel';
    mask.style.cssText =
      'position:fixed;inset:0;z-index:2147483647;background:rgba(0,0,0,.45);' +
      'display:flex;align-items:center;justify-content:center;font-size:14px;';

    const box = document.createElement('div');
    box.style.cssText =
      'width:420px;max-width:92vw;background:#fff;color:#222;border-radius:10px;' +
      'padding:20px;box-shadow:0 8px 30px rgba(0,0,0,.3);font-family:system-ui,sans-serif;';

    box.innerHTML =
      '<div style="font-size:16px;font-weight:600;margin-bottom:14px;">青龙面板配置</div>' +
      field('青龙地址', 'cs-url', '如 http://192.168.1.1:5700', cfg.url) +
      field('Client ID', 'cs-id', '系统设置 > 应用设置 新建应用获取', cfg.id) +
      field('Client Secret', 'cs-secret', '应用密钥', cfg.secret) +
      '<div style="display:flex;gap:10px;justify-content:flex-end;margin-top:16px;">' +
      '<button id="cs-cancel" style="padding:7px 16px;border:1px solid #ccc;background:#f5f5f5;border-radius:6px;cursor:pointer;">取消</button>' +
      '<button id="cs-save" style="padding:7px 16px;border:none;background:#2d7ff9;color:#fff;border-radius:6px;cursor:pointer;">保存</button>' +
      '</div>';

    function field(label, id, ph, val) {
      return (
        '<div style="margin-bottom:12px;">' +
        '<label style="display:block;margin-bottom:4px;color:#555;">' + label + '</label>' +
        '<input id="' + id + '" placeholder="' + ph + '" value="' + (val || '').replace(/"/g, '&quot;') + '" ' +
        'style="width:100%;box-sizing:border-box;padding:8px;border:1px solid #ccc;border-radius:6px;" />' +
        '</div>'
      );
    }

    mask.appendChild(box);
    document.body.appendChild(mask);

    const close = () => mask.remove();
    mask.addEventListener('click', (e) => { if (e.target === mask) close(); });
    box.querySelector('#cs-cancel').addEventListener('click', close);
    box.querySelector('#cs-save').addEventListener('click', () => {
      const url = box.querySelector('#cs-url').value.trim();
      const id = box.querySelector('#cs-id').value.trim();
      const secret = box.querySelector('#cs-secret').value.trim();
      if (!url || !id || !secret) { alert('三项都要填写'); return; }
      GM_setValue('ql_url', url);
      GM_setValue('ql_client_id', id);
      GM_setValue('ql_client_secret', secret);
      close();
      toast('青龙配置已保存');
    });
  }
  // ===== 工具函数 =====
  function toast(text, type) {
    try {
      GM_notification({ title: 'Cookie 同步', text: String(text), timeout: 4000 });
    } catch (e) { /* ignore */ }
    console.log('[CookieSync]', text);
  }

  function gm(method, url, opts) {
    opts = opts || {};
    return new Promise((resolve, reject) => {
      GM_xmlhttpRequest({
        method,
        url,
        headers: opts.headers || {},
        data: opts.data,
        timeout: 20000,
        onload: (r) => resolve(r),
        onerror: (e) => reject(new Error('请求失败: ' + (e && e.error || 'network'))),
        ontimeout: () => reject(new Error('请求超时')),
      });
    });
  }

  // 读取当前站点全部 Cookie（含 HttpOnly），拼成 "k=v; k2=v2" 字符串
  function getSiteCookieString() {
    return new Promise((resolve, reject) => {
      GM_cookie.list({ domain: location.hostname }, (cookies, err) => {
        if (err) return reject(new Error('GM_cookie 读取失败: ' + err));
        if (!cookies || !cookies.length) return resolve('');
        // 去重（同名取后者），过滤空值
        const map = {};
        cookies.forEach((c) => { if (c && c.name) map[c.name] = c.value; });
        const str = Object.keys(map)
          .map((k) => `${k}=${map[k]}`)
          .join('; ');
        resolve(str);
      });
    });
  }
  // ===== 青龙 OpenAPI =====
  async function qlToken() {
    if (!cfg.url || !cfg.id || !cfg.secret) {
      throw new Error('尚未配置青龙，请先点菜单「配置青龙」');
    }
    const url = `${cfg.url}/open/auth/token?client_id=${encodeURIComponent(cfg.id)}&client_secret=${encodeURIComponent(cfg.secret)}`;
    const r = await gm('GET', url);
    const j = JSON.parse(r.responseText);
    if (j.code !== 200 || !j.data || !j.data.token) {
      throw new Error('获取青龙 token 失败: ' + (r.responseText || '').slice(0, 200));
    }
    return j.data.token;
  }

  async function qlGetEnv(token, name) {
    const url = `${cfg.url}/open/envs?searchValue=${encodeURIComponent(name)}`;
    const r = await gm('GET', url, { headers: { Authorization: 'Bearer ' + token } });
    const j = JSON.parse(r.responseText);
    if (j.code !== 200) throw new Error('查询环境变量失败: ' + r.responseText);
    // 精确匹配 name
    return (j.data || []).find((e) => e.name === name) || null;
  }

  async function qlSaveEnv(token, existing, name, value) {
    const headers = {
      Authorization: 'Bearer ' + token,
      'Content-Type': 'application/json',
    };
    if (existing) {
      // 更新
      const body = JSON.stringify({ id: existing.id, name, value, remarks: existing.remarks || 'cookie-sync' });
      const r = await gm('PUT', `${cfg.url}/open/envs`, { headers, data: body });
      const j = JSON.parse(r.responseText);
      if (j.code !== 200) throw new Error('更新失败: ' + r.responseText);
    } else {
      // 新建
      const body = JSON.stringify([{ name, value, remarks: 'cookie-sync' }]);
      const r = await gm('POST', `${cfg.url}/open/envs`, { headers, data: body });
      const j = JSON.parse(r.responseText);
      if (j.code !== 200) throw new Error('新建失败: ' + r.responseText);
    }
    // 确保启用
    try {
      const env = existing || (await qlGetEnv(token, name));
      if (env && env.status !== 0) {
        await gm('PUT', `${cfg.url}/open/envs/enable`, { headers, data: JSON.stringify([env.id]) });
      }
    } catch (e) { /* 启用失败不影响主流程 */ }
  }
  // ===== 多账号本地存储 =====
  // 结构: GM_setValue('cookies_' + env, { "账号标识": "cookie串", ... })
  function storeKey() { return 'cookies_' + SITE.env; }

  function loadStore() {
    try { return JSON.parse(GM_getValue(storeKey(), '{}')) || {}; }
    catch (e) { return {}; }
  }
  function saveStore(obj) { GM_setValue(storeKey(), JSON.stringify(obj)); }

  // base64url 解码（兼容 UTF-8 中文）
  function b64urlDecode(str) {
    str = str.replace(/-/g, '+').replace(/_/g, '/');
    while (str.length % 4) str += '=';
    const bin = atob(str);
    // 处理 UTF-8
    const bytes = Uint8Array.from(bin, (c) => c.charCodeAt(0));
    return new TextDecoder('utf-8').decode(bytes);
  }

  // 从 cookie 串里的 pjwt 解析账号 { id, name }
  function parsePjwt(cookieStr) {
    const m = cookieStr.match(/(?:^|;\s*)pjwt=([^;]+)/);
    if (!m) return null;
    try {
      const parts = m[1].split('.');
      if (parts.length < 2) return null;
      const payload = JSON.parse(b64urlDecode(parts[0])); // 该站 pjwt 的 payload 在第 1 段
      if (payload && payload.id) return payload;
    } catch (e) { /* ignore */ }
    // 兜底：尝试第 2 段（标准 JWT 布局）
    try {
      const parts = m[1].split('.');
      const payload = JSON.parse(b64urlDecode(parts[1]));
      if (payload && payload.id) return payload;
    } catch (e) { /* ignore */ }
    return null;
  }

  // 尝试识别当前登录账号，用作合并时的 key，避免同账号重复占位
  function detectAccountName(cookieStr) {
    // 1) 优先解析 pjwt（含 id / name），最可靠
    const p = parsePjwt(cookieStr);
    if (p && p.id) return { key: 'uid_' + p.id, name: p.name || ('uid_' + p.id) };

    // 2) 退而求其次：页面个人空间链接 <a href="/space/12345">
    const a = document.querySelector('a[href^="/space/"]');
    if (a) {
      const m = a.getAttribute('href').match(/\/space\/(\d+)/);
      if (m) return { key: 'uid_' + m[1], name: 'uid_' + m[1] };
    }
    // 3) 都失败：交给上层弹框手填
    return null;
  }

  function mergeCookies(store) {
    return Object.keys(store)
      .filter((k) => store[k])
      .map((k) => store[k])
      .join('&');
  }

  // ===== 主同步流程 =====
  async function syncCurrent() {
    try {
      const cookieStr = await getSiteCookieString();
      if (!cookieStr || !/=/.test(cookieStr)) {
        toast('未读取到有效 Cookie，请先登录再同步');
        return;
      }

      let info = detectAccountName(cookieStr);
      if (!info) {
        const manual = prompt('无法自动识别账号，请为当前账号输入一个唯一标识（如账号名，用于区分多账号）', '账号1');
        if (!manual) return;
        info = { key: manual, name: manual };
      }

      const store = loadStore();
      store[info.key] = cookieStr;
      saveStore(store);

      const merged = mergeCookies(store);
      const accCount = Object.keys(store).filter((k) => store[k]).length;

      toast(`正在同步 ${SITE.label} - ${info.name}（本地共 ${accCount} 个账号）...`);

      const token = await qlToken();
      const existing = await qlGetEnv(token, SITE.env);
      await qlSaveEnv(token, existing, SITE.env, merged);

      toast(`✅ ${SITE.label} 已同步到青龙 ${SITE.env}（${accCount} 个账号）`);
    } catch (e) {
      toast('❌ 同步失败: ' + e.message);
    }
  }

  function clearStore() {
    if (confirm(`确定清空本地缓存的 ${SITE.label}（${SITE.env}）多账号 Cookie 吗？\n（不会影响青龙里已同步的值）`)) {
      saveStore({});
      toast('已清空本地缓存');
    }
  }

  // ===== 菜单 =====
  GM_registerMenuCommand(`🍪 同步当前 ${SITE.label} Cookie 到青龙`, syncCurrent);
  GM_registerMenuCommand('⚙️ 配置青龙面板', configQinglong);
  GM_registerMenuCommand(`🗑️ 清空本地 ${SITE.label} 多账号缓存`, clearStore);
})();
