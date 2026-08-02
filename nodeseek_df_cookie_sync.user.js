// ==UserScript==
// @name         NodeSeek / DeepFlood Cookie 同步到青龙
// @namespace    https://github.com/local/ns-df-cookie-sync
// @version      2.4.0
// @description  抓取 NodeSeek / DeepFlood 登录 Cookie（含 HttpOnly、含父域 cf_clearance/session），以青龙远端值为基准按账号(uid)合并，跨浏览器不覆盖；登录态变化立即同步，否则每天保底自动同步一次
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

  // GM_cookie.list 的 Promise 包装
  function listCookies(query) {
    return new Promise((resolve) => {
      try {
        GM_cookie.list(query, (cookies, err) => resolve(err ? [] : (cookies || [])));
      } catch (e) { resolve([]); }
    });
  }

  // 读取当前站点全部 Cookie（含 HttpOnly、含挂在父域 .nodeseek.com 上的 cf_clearance/session）
  // 拼成 "k=v; k2=v2" 字符串
  async function getSiteCookieString() {
    const host = location.hostname;                       // www.nodeseek.com
    const rootDomain = host.split('.').slice(-2).join('.'); // nodeseek.com

    // 多种查询做并集：{} 无过滤最全（含 HttpOnly/父域），其余作兜底
    const queries = [
      {},
      { url: location.origin + '/' },
      { domain: host },
      { domain: rootDomain },
      { domain: '.' + rootDomain },
      // 按关键 cookie 名精确查询（部分 Tampermonkey 版本对 cf_clearance 需按名查才返回）
      { name: 'cf_clearance', domain: rootDomain },
      { name: 'cf_clearance', domain: '.' + rootDomain },
      { name: 'cf_clearance', url: location.origin + '/' },
      { name: 'session', domain: host },
    ];
    const results = await Promise.all(queries.map(listCookies));

    // 仅保留属于当前站点的 cookie（domain 匹配 host 或其父域）
    const belongs = (d) => {
      if (!d) return false;
      const dd = d.replace(/^\./, '');
      return host === dd || host.endsWith('.' + dd) || dd === rootDomain;
    };

    const map = {};
    results.forEach((list) => {
      list.forEach((c) => {
        if (!c || !c.name) return;
        if (c.domain && !belongs(c.domain)) return; // 过滤掉别的网站的 cookie
        if (c.value !== undefined && c.value !== '') map[c.name] = c.value;
        else if (!(c.name in map)) map[c.name] = c.value;
      });
    });

    // 兜底：GM_cookie 拿不到的（如某些非 HttpOnly），用 document.cookie 补齐
    (document.cookie || '').split(/;\s*/).forEach((kv) => {
      const i = kv.indexOf('=');
      if (i > 0) {
        const k = kv.slice(0, i).trim();
        const v = kv.slice(i + 1).trim();
        if (k && !(k in map) && v) map[k] = v;
      }
    });

    return Object.keys(map).map((k) => `${k}=${map[k]}`).join('; ');
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

  // 从任意 cookie 串取 uid（用于对远端已有值按账号拆分），取不到返回 null
  function uidOf(cookieStr) {
    const p = parsePjwt(cookieStr);
    return p && p.id ? String(p.id) : null;
  }

  // 登录态指纹：只取关键登录字段，忽略高频变动的 fog/hmti_/colorscheme 等。
  // 用于判断“登录态是否真的变了”，避免每次开页面都重复同步。
  function loginSignature(cookieStr) {
    const pick = ['session', 'pjwt'];
    const parts = [];
    pick.forEach((k) => {
      const m = cookieStr.match(new RegExp('(?:^|;\\s*)' + k + '=([^;]+)'));
      if (m) parts.push(k + '=' + m[1]);
    });
    return parts.join('|');
  }

  // 把青龙里已有的 env 值（uid1cookie&uid2cookie&...）拆成 { uid: cookie }
  // 无法识别 uid 的老数据用占位 key 保留，避免误删
  function splitRemote(remoteValue) {
    const map = {};
    let anon = 0;
    (remoteValue || '').split('&').forEach((part) => {
      part = part.trim();
      if (!part) return;
      const uid = uidOf(part);
      map[uid ? 'uid_' + uid : 'legacy_' + (anon++)] = part;
    });
    return map;
  }

  function mergeMap(map) {
    return Object.keys(map).filter((k) => map[k]).map((k) => map[k]).join('&');
  }

  // ===== 主同步流程（以青龙远端值为基准合并，跨浏览器不覆盖）=====
  let syncing = false;
  async function syncCurrent(opts) {
    opts = opts || {};
    if (syncing) return;
    syncing = true;
    try {
      const cookieStr = await getSiteCookieString();
      if (!cookieStr || !/=/.test(cookieStr)) {
        if (!opts.silent) toast('未读取到有效 Cookie，请先登录再同步');
        return;
      }

      let info = detectAccountName(cookieStr);
      if (!info) {
        if (opts.silent) return; // 自动模式下识别不到就不打扰
        const manual = prompt('无法自动识别账号，请为当前账号输入唯一标识（如账号名）', '账号1');
        if (!manual) return;
        info = { key: manual, name: manual };
      }

      // 关键 cookie 完整性检查（缺 session/cf_clearance 时签到可能失败）
      const missing = ['session', 'cf_clearance'].filter((k) => !new RegExp('(?:^|;\\s*)' + k + '=').test(cookieStr));
      if (missing.length && !opts.silent) {
        toast('⚠️ 注意：未读取到 ' + missing.join('、') + '，将尽量保留青龙里旧值中的该字段');
      }
      // session 缺失属于致命错误：绝不推送，避免覆盖青龙里可用的旧 cookie
      if (/(?:^|;\s*)session=/.test(cookieStr) === false) {
        if (!opts.silent) toast('❌ 未读取到 session，已放弃同步（防止覆盖青龙可用值）。请确认已登录并开启 Beta 版 HttpOnly 读取');
        return;
      }

      // 同步策略（方案C）：
      //   1) 登录态(session+pjwt)变化 → 立即同步
      //   2) 登录态未变，但今天还没同步过 → 每天保底同步一次（顺便更新 cf_clearance）
      //   3) 登录态未变且今天已同步过 → 静默跳过
      const sig = loginSignature(cookieStr);
      const lastKey = 'last_sig_' + SITE.env + '_' + info.key;
      const dayKey = 'last_day_' + SITE.env + '_' + info.key;
      const today = new Date().toLocaleDateString('sv');  // YYYY-MM-DD（本地时区）
      const changed = GM_getValue(lastKey, '') !== sig;
      const syncedToday = GM_getValue(dayKey, '') === today;

      if (opts.silent && !changed && syncedToday) return; // 登录态没变且今天已推过 → 跳过

      if (!opts.silent) {
        if (!changed) toast(`ℹ️ ${info.name} 登录态未变化，仍执行一次同步...`);
        else toast(`正在同步 ${SITE.label} - ${info.name} ...`);
      }

      const token = await qlToken();
      const existing = await qlGetEnv(token, SITE.env);

      // 关键：以远端现有值为基准，仅更新/新增当前账号那一份
      const map = splitRemote(existing ? existing.value : '');

      // 安全阀：若本次抓取缺 cf_clearance，但远端该账号旧值里有，则保留旧的 cf_clearance
      let finalCookie = cookieStr;
      if (!/(?:^|;\s*)cf_clearance=/.test(finalCookie)) {
        const old = map[info.key] || '';
        const m = old.match(/(?:^|;\s*)(cf_clearance=[^;]+)/);
        if (m) {
          finalCookie = finalCookie + '; ' + m[1];
          if (!opts.silent) toast('ℹ️ 已从旧值补回 cf_clearance');
        }
      }

      map[info.key] = finalCookie;
      const merged = mergeMap(map);
      const accCount = Object.keys(map).filter((k) => map[k]).length;

      await qlSaveEnv(token, existing, SITE.env, merged);
      GM_setValue(lastKey, sig);
      GM_setValue(dayKey, today);  // 记录今日已同步，供每日保底判断

      // 同步完成后通知：区分「登录态更新」和「每日保底同步」
      let prefix = '✅ 已同步';
      if (opts.silent) prefix = changed ? '🔄 登录态更新，已自动同步' : '📅 每日保底，已自动同步';
      toast(`${prefix} ${SITE.label} - ${info.name}（远端共 ${accCount} 个账号）`);
    } catch (e) {
      if (!opts.silent) toast('❌ 同步失败: ' + e.message);
      else console.warn('[CookieSync] 自动同步失败:', e.message);
    } finally {
      syncing = false;
    }
  }

  // 自动同步开关（默认开启）
  function autoEnabled() { return GM_getValue('auto_sync', true); }
  function toggleAuto() {
    const v = !autoEnabled();
    GM_setValue('auto_sync', v);
    toast('自动同步已' + (v ? '开启' : '关闭'));
  }

  // 预览当前抓到的完整 cookie（用于确认 session/cf_clearance 是否齐全）
  async function previewCookie() {
    const cookieStr = await getSiteCookieString();
    const names = cookieStr.split(/;\s*/).map((s) => s.split('=')[0]).filter(Boolean);
    const has = (k) => names.includes(k);
    const report =
      `本站抓取到 ${names.length} 个 cookie：\n${names.join(', ')}\n\n` +
      `关键字段检查：\n` +
      `  session      ${has('session') ? '✅' : '❌ 缺失'}\n` +
      `  cf_clearance ${has('cf_clearance') ? '✅' : '❌ 缺失'}\n` +
      `  pjwt         ${has('pjwt') ? '✅' : '❌ 缺失'}\n\n` +
      `完整值（可复制核对）：\n${cookieStr}`;

    if (document.getElementById('cs-preview-panel')) return;
    const mask = document.createElement('div');
    mask.id = 'cs-preview-panel';
    mask.style.cssText =
      'position:fixed;inset:0;z-index:2147483647;background:rgba(0,0,0,.45);' +
      'display:flex;align-items:center;justify-content:center;';
    const box = document.createElement('div');
    box.style.cssText =
      'width:560px;max-width:92vw;max-height:80vh;overflow:auto;background:#fff;color:#222;' +
      'border-radius:10px;padding:18px;font-family:system-ui,sans-serif;font-size:13px;';
    const ta = document.createElement('textarea');
    ta.readOnly = true;
    ta.value = report;
    ta.style.cssText = 'width:100%;height:320px;box-sizing:border-box;font-family:monospace;font-size:12px;';
    const btn = document.createElement('button');
    btn.textContent = '关闭';
    btn.style.cssText = 'margin-top:10px;padding:6px 16px;border:none;background:#2d7ff9;color:#fff;border-radius:6px;cursor:pointer;';
    btn.onclick = () => mask.remove();
    box.appendChild(ta);
    box.appendChild(btn);
    mask.appendChild(box);
    mask.addEventListener('click', (e) => { if (e.target === mask) mask.remove(); });
    document.body.appendChild(mask);
  }

  // ===== 菜单 =====
  GM_registerMenuCommand(`🍪 立即同步当前 ${SITE.label} Cookie`, () => syncCurrent());
  GM_registerMenuCommand('🔍 预览将同步的 Cookie', previewCookie);
  GM_registerMenuCommand('⚙️ 配置青龙面板', configQinglong);
  GM_registerMenuCommand('🔄 开关自动同步', toggleAuto);

  // ===== 自动同步：登录后（检测到 pjwt）自动推送，cookie 未变则跳过 =====
  async function autoSync() {
    if (!autoEnabled()) return;
    if (!cfg.url || !cfg.id || !cfg.secret) return; // 未配置青龙则不打扰
    const cookieStr = await getSiteCookieString();
    if (!cookieStr || !uidOf(cookieStr)) return;    // 未登录/识别不到账号
    syncCurrent({ silent: true });
  }

  // 首次进入延迟触发，给页面/cookie 一点加载时间
  setTimeout(autoSync, 3000);
  // 页面重新可见时（如切回标签页、登录跳转后）再查一次
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible') autoSync();
  });
})();
