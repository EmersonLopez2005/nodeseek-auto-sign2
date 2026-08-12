# -*- coding: utf-8 -*-

import os
import time
import json
import random
import re
import hashlib
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# === 核心库加载 ===
try:
    from curl_cffi import requests
    print("成功加载 curl_cffi 模块 (v3)")
except ImportError:
    print("【严重警告】未安装 curl_cffi 模块！")
    import requests

# 验证码解决器
try:
    from turnstile_solver import TurnstileSolver
except ImportError:
    print("警告：验证码解决器模块未找到")
    TurnstileSolver = None

# Playwright 浏览器登录
try:
    from browser_login import browser_login, browser_sign, PLAYWRIGHT_AVAILABLE
    if PLAYWRIGHT_AVAILABLE:
        print("成功加载 Playwright 浏览器登录模块")
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    browser_login = None
    browser_sign = None

# 环境变量
try:
    from dotenv import load_dotenv
    load_dotenv()
except: pass

# === 通知模块 ===
hadsend = False
send = None
try:
    from notify import send
    hadsend = True
except ImportError:
    print("未加载通知模块")

# === 站点配置 ===
SITES_CONFIG = {
    "nodeseek": {
        "name": "NodeSeek",
        "type": "nodeseek",
        "sign_api": "https://www.nodeseek.com/api/attendance",
        "stats_api": "https://www.nodeseek.com/api/account/credit/page-",
        "board_url": "https://www.nodeseek.com/board",
        "origin": "https://www.nodeseek.com",
        "cookie_var": "NS_COOKIE",
        "login_url": "https://www.nodeseek.com/signIn.html",
        "login_api": "https://www.nodeseek.com/api/account/signIn",
        "sitekey": "0x4AAAAAAAaNy7leGjewpVyR",
        "user_var": "NS_USER",
        "pass_var": "NS_PASS",
        "account_var": "NS_USER_PASS"
    },
    "9nb": {
        "name": "9nb",
        "type": "bbs1org",
        # 签到页（GET），返回 HTML
        "sign_url": "https://9nb.de/index.php?a=daily_checkin",
        # 校验用页面：访问后若未被重定向到登录页即视为已登录
        "check_url": "https://9nb.de/index.php?a=daily_checkin",
        "login_page": "https://9nb.de/index.php?a=login",
        "login_post": "https://9nb.de/index.php?a=login",
        "board_url": "https://9nb.de/index.php",
        "origin": "https://9nb.de",
        "cookie_var": "NB_COOKIE",
        "user_var": "NB_USER",
        "pass_var": "NB_PASS",
        "account_var": "NB_USER_PASS"
    }
}

# === Refract 签名配置 ===
REFRACT_KEY = "CHICZkKViFoZmVbIH1Y6"
REFRACT_VERSION = "0.3.34"
BROWSER_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
IMPERSONATE_VER = "chrome124"


def compute_refract_sign(method, url, user_agent, body, refract_key):
    """计算 refract-sign: SHA-1(method\\n\\nurl\\n\\nua\\n\\nbody\\n\\nkey)"""
    sign_str = f"{method}\n\n{url}\n\n{user_agent}\n\n{body}\n\n{refract_key}"
    return hashlib.sha1(sign_str.encode()).hexdigest()


def make_refract_headers(method, url, body="", refract_key=None):
    """生成 refract-sign / refract-version / refract-key 请求头"""
    key = refract_key or REFRACT_KEY
    sign = compute_refract_sign(method, url, BROWSER_UA, body, key)
    return {
        "refract-sign": sign,
        "refract-version": REFRACT_VERSION,
        "refract-key": key,
    }


# === 通知状态管理 ===
NOTIFICATION_FILE = "./cookie/notification_status.json"


def load_notification_status():
    try:
        if os.path.exists(NOTIFICATION_FILE):
            with open(NOTIFICATION_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except: pass
    return {}


def save_notification_status(status):
    try:
        os.makedirs(os.path.dirname(NOTIFICATION_FILE), exist_ok=True)
        with open(NOTIFICATION_FILE, 'w', encoding='utf-8') as f:
            json.dump(status, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"保存通知状态失败: {e}")


def should_send_notification(site_name):
    """检查是否应该发送通知（每天只发送一次）"""
    status = load_notification_status()
    today = datetime.now().strftime('%Y-%m-%d')
    site_status = status.get(site_name, {})
    last_sent = site_status.get('last_sent_date')
    return last_sent != today


def mark_notification_sent(site_name):
    """标记通知已发送"""
    status = load_notification_status()
    today = datetime.now().strftime('%Y-%m-%d')
    if site_name not in status: status[site_name] = {}
    status[site_name]['last_sent_date'] = today
    save_notification_status(status)


# === Cookie 文件操作 ===
def get_cookie_file_path(site_name, account_index=None):
    if account_index is not None:
        return f"./cookie/{site_name.upper()}_COOKIE_{account_index}.txt"
    return f"./cookie/{site_name.upper()}_COOKIE.txt"


def load_cookies_from_file(site_name, account_index=None):
    try:
        path = get_cookie_file_path(site_name, account_index)
        if os.path.exists(path):
            with open(path, "r", encoding='utf-8') as f:
                content = f.read().strip()
                if content: return content
    except: pass
    return ""


def save_cookie_to_file(site_name, cookie_str, account_index=None):
    try:
        path = get_cookie_file_path(site_name, account_index)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding='utf-8') as f:
            f.write(cookie_str)
        print(f"Cookie已保存: {path}")
        return True
    except Exception as e:
        print(f"保存Cookie失败: {e}")
        return False


def split_env_items(value):
    return [p.strip() for p in value.split("&") if p.strip()]


def get_env_cookie(site_config, account_index):
    cookies = split_env_items(os.getenv(site_config["cookie_var"], ""))
    idx = account_index - 1
    if 0 <= idx < len(cookies) and "=" in cookies[idx]:
        return cookies[idx]
    return ""


def looks_like_cookie(value):
    return "=" in value and ";" in value


def get_accounts(site_config):
    """读取账号密码。优先使用 *_USER_PASS，其次兼容 NS_USER/NS_PASS，最后兼容旧的 NS_COOKIE=用户&密码。"""
    account_var = site_config.get("account_var")
    account_parts = split_env_items(os.getenv(account_var, "")) if account_var else []

    if not account_parts:
        users = split_env_items(os.getenv(site_config.get("user_var", ""), ""))
        pwds = split_env_items(os.getenv(site_config.get("pass_var", ""), ""))
        account_parts = []
        for i, user in enumerate(users):
            account_parts.append(user)
            if i < len(pwds):
                account_parts.append(pwds[i])

    if not account_parts:
        legacy_parts = split_env_items(os.getenv(site_config["cookie_var"], ""))
        if legacy_parts and not any(looks_like_cookie(p) for p in legacy_parts):
            print(f"提示：检测到 {site_config['cookie_var']} 可能仍在使用旧格式 用户&密码，建议迁移到 {account_var}")
            account_parts = legacy_parts

    accounts = []
    for i in range(0, len(account_parts), 2):
        user = account_parts[i]
        pwd = account_parts[i + 1] if i + 1 < len(account_parts) else None
        accounts.append({"user": user, "pwd": pwd})
    return accounts


# === 核心业务逻辑 ===
def create_session(cookie_str=None):
    """创建一个预配置的 Session 对象"""
    session = requests.Session()
    session.headers = {
        "User-Agent": BROWSER_UA,
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9",
    }
    if cookie_str:
        for cookie in re.split(r";\s*", cookie_str):
            if '=' in cookie:
                k, v = cookie.split('=', 1)
                session.cookies.set(k.strip(), v.strip())
    return session


def cookie_dict_to_str(cookie_dict):
    return "; ".join([f"{k}={v}" for k, v in cookie_dict.items() if v is not None])


def response_looks_like_waf(response):
    text = (response.text or "").lower()
    return any(s in text for s in [
        "just a moment", "cf-chl", "cloudflare", "challenge-platform", "turnstile"
    ])


def check_cookie_validity(site_config, cookie_str, retries=3):
    """返回 True=有效，False=明确无效，None=网络/WAF等不确定状态。"""
    if site_config.get("type") == "bbs1org":
        return bbs1org_check_validity(site_config, cookie_str, retries=retries)

    last_reason = ""
    for attempt in range(1, retries + 1):
        try:
            session = create_session(cookie_str)
            session.get(
                site_config['board_url'],
                headers={"Referer": site_config["origin"]},
                impersonate="chrome124",
                timeout=15
            )
            response = session.get(
                f"{site_config['stats_api']}1",
                headers={"Referer": site_config["board_url"], "Origin": site_config["origin"]},
                impersonate="chrome124",
                timeout=15
            )

            if response_looks_like_waf(response):
                last_reason = "疑似 WAF/Cloudflare 页面"
                print(f"Cookie校验第{attempt}次遇到{last_reason}，暂不判定Cookie失效")
                time.sleep(random.uniform(2, 4))
                continue

            if response.status_code == 200:
                try:
                    data = response.json()
                    if data.get("success") is not None:
                        return True
                except: pass
                text = response.text.lower()
                if "credit" in text or "balance" in text or "success" in text:
                    return True
                last_reason = "200但响应内容不匹配"
            elif response.status_code in (401, 403, 404, 500):
                print(f"Cookie校验返回 {response.status_code}，判定Cookie无效")
                return False
            else:
                last_reason = f"HTTP {response.status_code}"
                print(f"Cookie校验第{attempt}次失败: {last_reason}")
        except Exception as e:
            last_reason = str(e)
            print(f"Cookie校验第{attempt}次异常: {last_reason}")

        if attempt < retries:
            time.sleep(random.uniform(2, 4))

    print(f"Cookie校验多次失败但无法确认失效: {last_reason}")
    return None


def auto_login(site_config, username, password):
    try:
        if not username or not password:
            print("未配置账号或密码，无法自动登录")
            return None
        if TurnstileSolver is None:
            print("验证码解决器不可用，无法自动登录")
            return None

        api_key = os.getenv("CLOUDFREED_API_KEY", "")
        base_url = os.getenv("CLOUDFREED_BASE_URL", "http://localhost:3000")
        if not api_key:
            print("错误：未配置 CLOUDFREED_API_KEY")
            return None

        solver = TurnstileSolver(api_base_url=base_url, client_key=api_key)
        session = create_session()

        # 1. 访问登录页
        login_url = site_config["login_url"]
        login_headers = {"Referer": site_config["origin"]}
        login_headers.update(make_refract_headers("GET", login_url))
        session.get(login_url, headers=login_headers, impersonate=IMPERSONATE_VER, timeout=15)

        # 2. 解决验证码
        print("正在解决验证码...")
        token = solver.solve(
            login_url,
            site_config["sitekey"],
            user_agent=BROWSER_UA,
            verbose=False
        )
        if not token:
            print("验证码失败")
            return None

        # 3. 登录请求 - 根据站点区分字段
        site_name = site_config.get("name", "").lower()
        if "deepflood" in site_name:
            # DeepFlood 不接受 token/source 字段
            login_data = {
                "username": username,
                "password": password,
            }
        else:
            # NodeSeek 需要 token
            login_data = {
                "username": username,
                "password": password,
                "token": token,
                "source": "turnstile"
            }

        login_body = json.dumps(login_data)
        login_api = site_config["login_api"]
        headers = {
            "Origin": site_config["origin"],
            "Referer": login_url,
            "Content-Type": "application/json"
        }
        headers.update(make_refract_headers("POST", login_api, body=login_body))

        resp = session.post(
            login_api,
            json=login_data,
            headers=headers,
            impersonate=IMPERSONATE_VER,
            timeout=15
        )

        if resp.status_code == 200:
            cookie_str = cookie_dict_to_str(session.cookies.get_dict())
            if cookie_str:
                print("登录成功")
                return cookie_str
            print("登录返回200，但未获取到Cookie")
            return None

        print(f"登录失败: {resp.status_code}")
        print(f"登录响应: {(resp.text or '')[:500]}")
        return None

    except Exception as e:
        print(f"登录异常: {e}")
        return None


def deepflood_ns_login(account_index):
    """DeepFlood Cookie失效时，尝试通过对应账号的NodeSeek Cookie进行一键登录。"""
    ns_cookie = load_cookies_from_file("nodeseek", account_index) or get_env_cookie(SITES_CONFIG["nodeseek"], account_index)
    if not ns_cookie:
        print("DeepFlood一键登录失败: 未找到对应账号的NodeSeek Cookie")
        return None

    try:
        session = create_session(ns_cookie)
        df_config = SITES_CONFIG["deepflood"]
        ns_login_url = df_config["ns_login_url"]

        headers = {"Referer": df_config["login_url"]}
        headers.update(make_refract_headers("GET", ns_login_url))

        resp = session.get(
            ns_login_url,
            headers=headers,
            impersonate=IMPERSONATE_VER,
            timeout=20,
            allow_redirects=True
        )
        if response_looks_like_waf(resp):
            print("DeepFlood一键登录遇到WAF/Cloudflare，暂时失败")
            return None

        cookie_str = cookie_dict_to_str(session.cookies.get_dict())
        if cookie_str and check_cookie_validity(df_config, cookie_str, retries=2) is True:
            print("DeepFlood NS一键登录成功")
            return cookie_str

        print(f"DeepFlood一键登录未获得有效Cookie: HTTP {resp.status_code}")
        print(f"一键登录响应: {(resp.text or '')[:300]}")
        return None
    except Exception as e:
        print(f"DeepFlood一键登录异常: {e}")
        return None


# === 9nb (bbs1org) 专用逻辑 ===
def create_html_session(cookie_str=None):
    """创建适合访问 9nb 这类返回 HTML 的论坛的 Session。"""
    session = requests.Session()
    session.headers = {
        "User-Agent": BROWSER_UA,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9",
    }
    if cookie_str:
        for cookie in re.split(r";\s*", cookie_str):
            if '=' in cookie:
                k, v = cookie.split('=', 1)
                session.cookies.set(k.strip(), v.strip())
    return session


def bbs1org_is_login_page(text):
    """判断返回的 HTML 是否为登录页（表示未登录 / Cookie 失效）。"""
    if not text:
        return True
    lowered = text.lower()
    markers = [
        'a=login', 'name="password"', 'name="username"',
        '请使用用户名登录', '密码区分大小写', 'name="bbs_csrf"',
    ]
    return any(m.lower() in lowered for m in markers)


def bbs1org_check_validity(site_config, cookie_str, retries=3):
    """访问签到页，若未被重定向到登录页则视为 Cookie 有效。
    返回 True=有效，False=明确失效，None=不确定。"""
    check_url = site_config.get("check_url") or site_config.get("sign_url")
    last_reason = ""
    for attempt in range(1, retries + 1):
        try:
            session = create_html_session(cookie_str)
            headers = {"Referer": site_config["origin"] + "/"}
            resp = session.get(
                check_url,
                headers=headers,
                impersonate=IMPERSONATE_VER,
                timeout=20,
                allow_redirects=True
            )

            if response_looks_like_waf(resp):
                last_reason = "疑似 WAF/Cloudflare 页面"
                print(f"9nb Cookie校验第{attempt}次遇到{last_reason}，暂不判定失效")
                time.sleep(random.uniform(2, 4))
                continue

            final_url = str(resp.url).lower()
            if "a=login" in final_url:
                print("9nb 被重定向到登录页，判定Cookie无效")
                return False

            if resp.status_code == 200:
                if bbs1org_is_login_page(resp.text):
                    print("9nb 返回登录页内容，判定Cookie无效")
                    return False
                return True

            if resp.status_code in (401, 403):
                print(f"9nb Cookie校验返回 {resp.status_code}，判定Cookie无效")
                return False

            last_reason = f"HTTP {resp.status_code}"
            print(f"9nb Cookie校验第{attempt}次失败: {last_reason}")
        except Exception as e:
            last_reason = str(e)
            print(f"9nb Cookie校验第{attempt}次异常: {last_reason}")

        if attempt < retries:
            time.sleep(random.uniform(2, 4))

    print(f"9nb Cookie校验多次失败但无法确认失效: {last_reason}")
    return None


def bbs1org_parse_stats_cookie(session):
    """解析 __daily_checkin_stats cookie: uid.date.streak.x.x"""
    try:
        raw = session.cookies.get("__daily_checkin_stats")
        if not raw:
            return None
        parts = raw.split(".")
        info = {"raw": raw}
        if len(parts) >= 2:
            info["uid"] = parts[0]
            info["date"] = parts[1]
        if len(parts) >= 3:
            info["streak"] = parts[2]
        return info
    except Exception:
        return None


def bbs1org_sign(cookie, site_config):
    """9nb 签到：GET 签到页，根据返回 HTML 与 __daily_checkin_stats 判断结果。"""
    if not cookie:
        return "fail", "无Cookie"
    try:
        session = create_html_session(cookie)
        sign_url = site_config["sign_url"]
        headers = {"Referer": site_config["origin"] + "/"}

        resp = session.get(
            sign_url,
            headers=headers,
            impersonate=IMPERSONATE_VER,
            timeout=20,
            allow_redirects=True
        )

        if response_looks_like_waf(resp):
            return "fail", "被WAF拦截"

        final_url = str(resp.url).lower()
        if "a=login" in final_url or bbs1org_is_login_page(resp.text):
            return "invalid", "未登录/Cookie失效"

        text = resp.text or ""
        today = datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%Y-%m-%d")
        stats = bbs1org_parse_stats_cookie(session)

        # 依据 __daily_checkin_stats 中的日期判断今天是否已签
        if stats and stats.get("date") == today:
            streak = stats.get("streak", "")
            suffix = f"（连续{streak}天）" if streak else ""
            # 页面文案区分“已签到” vs “刚签到成功”
            if any(k in text for k in ["已签到", "已经签到", "今日已", "已完成"]):
                return "already", f"今日已签到{suffix}"
            return "success", f"签到成功{suffix}"

        # 页面文案兜底判断
        if any(k in text for k in ["签到成功", "打卡成功", "success"]):
            return "success", "签到成功"
        if any(k in text for k in ["已签到", "已经签到", "今日已", "已完成"]):
            return "already", "今日已签到"

        return "fail", f"未知响应 (Code {resp.status_code})"
    except Exception as e:
        return "error", str(e)


def bbs1org_extract_csrf(text):
    """从登录页 HTML 中提取 CSRF 隐藏字段。9nb 使用 <input name="_csrf" value="...">，
    值与 bbs_csrf cookie 相同。返回 (字段名, 值) 或 (None, None)。"""
    if not text:
        return None, None
    csrf_names = ("_csrf", "bbs_csrf", "csrf_token", "csrf", "_token", "token")
    names_pat = "|".join(csrf_names)
    patterns = [
        r'name=["\'](' + names_pat + r')["\']\s+[^>]*?value=["\']([^"\']+)["\']',
        r'value=["\']([^"\']+)["\']\s+[^>]*?name=["\'](' + names_pat + r')["\']',
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            g = m.groups()
            if g[0].lower() in csrf_names:
                return g[0], g[1]
            return g[1], g[0]
    return None, None


def bbs1org_login(site_config, username, password):
    """9nb 账号密码登录：GET 登录页取 _csrf，POST 表单，成功后返回 Cookie 字符串。"""
    if not username or not password:
        print("未配置9nb账号或密码，无法自动登录")
        return None
    try:
        session = create_html_session()
        login_page = site_config["login_page"]

        page_resp = session.get(
            login_page,
            headers={"Referer": site_config["origin"] + "/"},
            impersonate=IMPERSONATE_VER,
            timeout=20,
            allow_redirects=True
        )
        if response_looks_like_waf(page_resp):
            print("9nb登录页遇到WAF/Cloudflare")
            return None

        csrf_name, csrf_val = bbs1org_extract_csrf(page_resp.text)
        # 兜底：9nb 的 _csrf 值等于 bbs_csrf cookie，页面提取失败时用 cookie 补上
        if not csrf_val:
            csrf_val = session.cookies.get("bbs_csrf")
            csrf_name = "_csrf"

        # 9nb 登录表单字段：username / password / _csrf
        login_data = {
            "username": username,
            "password": password,
        }
        if csrf_val:
            login_data[csrf_name or "_csrf"] = csrf_val

        headers = {
            "Origin": site_config["origin"],
            "Referer": login_page,
            "Content-Type": "application/x-www-form-urlencoded",
        }
        resp = session.post(
            site_config["login_post"],
            data=login_data,
            headers=headers,
            impersonate=IMPERSONATE_VER,
            timeout=20,
            allow_redirects=True
        )

        if response_looks_like_waf(resp):
            print("9nb登录请求遇到WAF/Cloudflare")
            return None

        # 登录成功标志：拿到 bbs_auth cookie 且再次校验有效
        if session.cookies.get("bbs_auth"):
            cookie_str = cookie_dict_to_str(session.cookies.get_dict())
            if cookie_str and bbs1org_check_validity(site_config, cookie_str, retries=2) is True:
                print("9nb 登录成功")
                return cookie_str

        print(f"9nb 登录失败: HTTP {resp.status_code}")
        print(f"登录响应: {(resp.text or '')[:300]}")
        return None
    except Exception as e:
        print(f"9nb 登录异常: {e}")
        return None


def sign(cookie, site_config, ns_random):
    if not cookie: return "fail", "无Cookie"

    if site_config.get("type") == "bbs1org":
        return bbs1org_sign(cookie, site_config)

    try:
        session = create_session(cookie)

        # 1. 模拟浏览 (GET) - 预热
        session.get(
            site_config["board_url"],
            headers={"Referer": site_config["origin"]},
            impersonate="chrome124",
            timeout=15
        )

        time.sleep(random.uniform(2, 4))

        # 2. 签到 (POST)
        url = f"{site_config['sign_api']}?random={ns_random}"
        headers = {
            'Origin': site_config["origin"],
            'Referer': site_config["board_url"],
            'Content-Type': 'application/json'
        }

        resp = session.post(url, headers=headers, impersonate="chrome124", timeout=15)

        try:
            data = resp.json()
        except:
            if response_looks_like_waf(resp):
                return "fail", "被WAF拦截"
            return "fail", f"未知响应 (Code {resp.status_code})"

        msg = data.get("message", "")
        if "鸡腿" in msg or data.get("success"): return "success", msg
        elif "已完成签到" in msg: return "already", msg
        elif data.get("status") == 404: return "invalid", msg
        return "fail", msg

    except Exception as e:
        return "error", str(e)


def get_stats(cookie, site_config, days=30):
    if not cookie: return None
    if site_config.get("type") == "bbs1org":
        # 9nb 无积分统计接口，跳过统计
        return None
    try:
        session = create_session(cookie)

        # 统计接口也需要预热访问
        session.get(
            site_config["board_url"],
            headers={"Referer": site_config["origin"]},
            impersonate="chrome124",
            timeout=15
        )

        shanghai_tz = ZoneInfo("Asia/Shanghai")
        now = datetime.now(shanghai_tz)
        start_time = now - timedelta(days=days)

        all_records = []
        page = 1

        while page <= 10:
            url = f"{site_config['stats_api']}{page}"
            headers = {
                "Referer": site_config["board_url"],
                "Origin": site_config["origin"]
            }
            resp = session.get(url, headers=headers, impersonate="chrome124", timeout=10)
            try:
                data = resp.json()
            except: break

            if not data.get("success") or not data.get("data"): break
            records = data.get("data", [])
            if not records: break

            all_records.extend(records)
            page += 1
            time.sleep(0.5)

        valid_records = []
        for r in all_records:
            try:
                amt, _, desc, ts = r
                dt = datetime.fromisoformat(ts.replace('Z', '+00:00')).astimezone(shanghai_tz)
                if dt >= start_time and ("签到" in desc or "鸡腿" in desc):
                    valid_records.append({'amount': amt, 'date': dt.strftime('%Y-%m-%d')})
            except: continue

        total = sum(r['amount'] for r in valid_records)
        count = len(valid_records)
        avg = round(total/count, 2) if count > 0 else 0

        return {'total': total, 'avg': avg, 'days': count, 'period': f"近{days}天"}
    except: return None


# === 主逻辑 ===
def load_account_cookie(site_name, site_config, account_index):
    """优先使用环境变量中的手动 Cookie，避免本地旧 Cookie 文件覆盖用户最新配置。"""
    return get_env_cookie(site_config, account_index) or load_cookies_from_file(site_name, account_index)


def recover_cookie(site_name, site_config, account_index, user, pwd):
    if site_config.get("type") == "bbs1org":
        # 9nb：账号密码登录
        cookie = bbs1org_login(site_config, user, pwd)
        if cookie:
            save_cookie_to_file(site_name, cookie, account_index)
            return cookie
        return None

    if site_name == "deepflood":
        print("尝试通过NodeSeek一键登录恢复DeepFlood Cookie...")
        cookie = deepflood_ns_login(account_index)
        if cookie:
            save_cookie_to_file(site_name, cookie, account_index)
            return cookie
        print("DeepFlood一键登录失败，尝试账号密码登录...")

    # 先尝试传统 API 登录
    cookie = auto_login(site_config, user, pwd)
    if cookie:
        save_cookie_to_file(site_name, cookie, account_index)
        return cookie

    # 传统登录失败，尝试 Playwright 浏览器登录
    if PLAYWRIGHT_AVAILABLE and browser_login:
        print("API登录失败，尝试 Playwright 浏览器登录...")
        cookie = browser_login(site_config, user, pwd, headless=True)
        if cookie:
            save_cookie_to_file(site_name, cookie, account_index)
            return cookie

    return None


def sign_failure_should_recover(status, msg):
    """签到结果明确说明当前Cookie不可用时，触发登录恢复并重试一次。WAF不代表Cookie失效。"""
    text = (msg or "").lower()
    if status in ["invalid", "error"]:
        return True
    return any(s in text for s in [
        "user not found",
        "unauthorized",
        "forbidden",
        "无cookie",
        "登录",
        "cookie"
    ])


def process_site(site_name, site_config, ns_random):
    print(f"\n{'='*30}\n处理站点: {site_config['name']}\n{'='*30}")

    accounts = get_accounts(site_config)
    env_cookies = split_env_items(os.getenv(site_config["cookie_var"], ""))
    account_count = max(len(accounts), len([c for c in env_cookies if "=" in c]))

    if account_count == 0:
        print(f"未配置 {site_config.get('account_var')} / {site_config['cookie_var']}，跳过")
        return

    site_results = []

    for i in range(account_count):
        idx = i + 1
        account = accounts[i] if i < len(accounts) else {}
        user = account.get("user") or f"账号{idx}"
        pwd = account.get("pwd")

        print(f"\n--- 账号: {user} ---")

        cookie = load_account_cookie(site_name, site_config, idx)

        if cookie:
            check_result = check_cookie_validity(site_config, cookie)
            if check_result is False:
                print("Cookie已确认失效，尝试恢复登录...")
                cookie = None
            elif check_result is None:
                print("Cookie状态不确定，继续尝试使用现有Cookie签到")
            else:
                print("Cookie有效")
        else:
            print("无可用Cookie，尝试登录...")

        if not cookie:
            cookie = recover_cookie(site_name, site_config, idx, user, pwd)

        if not cookie:
            print("放弃: 无法获取有效Cookie")
            site_results.append({'user': user, 'status': 'fail', 'msg': '登录失败'})
            continue

        status, msg = sign(cookie, site_config, ns_random)
        print(f"签到结果: {msg}")

        if sign_failure_should_recover(status, msg):
            print("签到失败疑似Cookie不可用，尝试恢复登录后重试一次...")
            new_cookie = recover_cookie(site_name, site_config, idx, user, pwd)
            if new_cookie:
                cookie = new_cookie
                status, msg = sign(cookie, site_config, ns_random)
                print(f"重试签到结果: {msg}")
            else:
                print("恢复登录失败，无法重试签到")

        stats = None
        if status in ["success", "already"]:
            stats = get_stats(cookie, site_config)
            if stats:
                print(f"统计: {stats['days']}天 | 总收益:{stats['total']} | 平均:{stats['avg']}")

        site_results.append({'user': user, 'status': status, 'msg': msg, 'stats': stats})

    # 发送通知
    if hadsend and should_send_notification(site_name):
        msg_lines = []
        for r in site_results:
            line = f"{r['user']}: {r['msg']}"
            if r.get('stats'):
                line += f" (近30天: {r['stats']['total']}个)"
            msg_lines.append(line)

        if msg_lines:
            notify_content = f"{site_config['name']} 汇总\n" + "\n".join(msg_lines)
            send(f"{site_config['name']} 签到", notify_content)
            mark_notification_sent(site_name)
            print("通知已尝试推送")
    else:
        print("今日已通知过，跳过推送")


if __name__ == "__main__":
    print("脚本启动...")
    ns_random = os.getenv("NS_RANDOM", "true")
    for name, config in SITES_CONFIG.items():
        try: process_site(name, config, ns_random)
        except Exception as e: print(f"站点异常: {e}")
