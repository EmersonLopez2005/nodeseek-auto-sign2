# -*- coding: utf-8 -*-

import os
import time
import json
import random
import re
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
    "deepflood": {
        "name": "DeepFlood",
        "sign_api": "https://www.deepflood.com/api/attendance",
        "stats_api": "https://www.deepflood.com/api/account/credit/page-",
        "board_url": "https://www.deepflood.com/board",
        "origin": "https://www.deepflood.com",
        "cookie_var": "DF_COOKIE",
        "login_url": "https://www.deepflood.com/signIn.html",
        "login_api": "https://www.deepflood.com/api/account/signIn",
        "ns_login_url": "https://www.deepflood.com/nsSignIn.html",
        "sitekey": "0x4AAAAAAAaNy7leGjewpVyR",
        "user_var": "DF_USER",
        "pass_var": "DF_PASS",
        "account_var": "DF_USER_PASS"
    }
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
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
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
        session.get(site_config["login_url"], impersonate="chrome124", timeout=15)

        # 2. 解决验证码
        print("正在解决验证码...")
        token = solver.solve(
            site_config["login_url"],
            site_config["sitekey"],
            user_agent=session.headers["User-Agent"],
            verbose=False
        )
        if not token:
            print("验证码失败")
            return None

        # 3. 登录请求
        login_data = {
            "username": username,
            "password": password,
            "token": token,
            "source": "turnstile"
        }
        headers = {
            "Origin": site_config["origin"],
            "Referer": site_config["login_url"],
            "Content-Type": "application/json"
        }
        resp = session.post(
            site_config["login_api"],
            json=login_data,
            headers=headers,
            impersonate="chrome124",
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
        resp = session.get(
            df_config["ns_login_url"],
            headers={"Referer": df_config["login_url"]},
            impersonate="chrome124",
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


def sign(cookie, site_config, ns_random):
    if not cookie: return "fail", "无Cookie"

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

        headers = {
            "Referer": site_config["board_url"],
            "Origin": site_config["origin"]
        }

        while page <= 10:
            url = f"{site_config['stats_api']}{page}"
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
    if site_name == "deepflood":
        print("尝试通过NodeSeek一键登录恢复DeepFlood Cookie...")
        cookie = deepflood_ns_login(account_index)
        if cookie:
            save_cookie_to_file(site_name, cookie, account_index)
            return cookie
        print("DeepFlood一键登录失败，尝试账号密码登录...")

    cookie = auto_login(site_config, user, pwd)
    if cookie:
        save_cookie_to_file(site_name, cookie, account_index)
    return cookie


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
