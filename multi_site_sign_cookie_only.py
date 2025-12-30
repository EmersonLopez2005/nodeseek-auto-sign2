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
        "pass_var": "NS_PASS"
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
        "sitekey": "0x4AAAAAAAaNy7leGjewpVyR",
        "user_var": "DF_USER",
        "pass_var": "DF_PASS"
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
        for cookie in cookie_str.split('; '):
            if '=' in cookie:
                k, v = cookie.split('=', 1)
                session.cookies.set(k, v)
    return session

def check_cookie_validity(site_config, cookie_str):
    try:
        session = create_session(cookie_str)
        # 1. 预访问主页 (GET)
        session.get(
            site_config['board_url'], 
            impersonate="chrome124", 
            timeout=15
        )
        # 2. 验证 API
        response = session.get(
            f"{site_config['stats_api']}1",
            impersonate="chrome124", 
            timeout=15
        )
        if response.status_code == 200:
            try:
                data = response.json()
                if data.get("success") is not None: return True
            except: pass
            text = response.text.lower()
            if "credit" in text or "balance" in text or "success" in text:
                return True
        return False
    except Exception as e:
        return False

def auto_login(site_config, username, password):
    try:
        api_key = os.getenv("CLOUDFREED_API_KEY", "")
        base_url = os.getenv("CLOUDFREED_BASE_URL", "http://localhost:3000")
        if not api_key:
            print("错误：未配置 CLOUDFREED_API_KEY")
            return None
            
        solver = TurnstileSolver(api_base_url=base_url, client_key=api_key)
        session = create_session() 
        
        # 1. 访问登录页
        session.get(site_config["login_url"], impersonate="chrome124")
        
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
            cookies = session.cookies.get_dict()
            cookie_str = "; ".join([f"{k}={v}" for k, v in cookies.items()])
            print(f"登录成功")
            return cookie_str
        else:
            print(f"登录失败: {resp.status_code}")
            return None
            
    except Exception as e:
        print(f"登录异常: {e}")
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
            if "Just a moment" in resp.text:
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
        
        # === 修复点：统计接口也需要预热访问 ===
        session.get(
            site_config["board_url"],
            headers={"Referer": site_config["origin"]},
            impersonate="chrome124",
            timeout=15
        )
        # ================================
        
        shanghai_tz = ZoneInfo("Asia/Shanghai")
        now = datetime.now(shanghai_tz)
        start_time = now - timedelta(days=days)
        
        all_records = []
        page = 1
        
        # 增加 Referer 头，防止直接访问 API 被拒
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
def process_site(site_name, site_config, ns_random):
    print(f"\n{'='*30}\n处理站点: {site_config['name']}\n{'='*30}")
    
    env_cookie = os.getenv(site_config["cookie_var"], "")
    parts = [p.strip() for p in env_cookie.split("&") if p.strip()]
    users, pwds = parts[0::2], parts[1::2]
    
    site_results = []
    
    for i in range(len(users)):
        idx = i + 1
        user = users[i]
        pwd = pwds[i] if i < len(pwds) else None
        
        print(f"\n--- 账号: {user} ---")
        
        cookie = load_cookies_from_file(site_name, idx)
        
        if cookie:
            if not check_cookie_validity(site_config, cookie):
                print("Cookie已失效，尝试重新登录...")
                cookie = None
        else:
            print("无本地Cookie，尝试登录...")
            
        if not cookie and pwd:
            cookie = auto_login(site_config, user, pwd)
            if cookie: save_cookie_to_file(site_name, cookie, idx)
            
        if not cookie:
            print("放弃: 无法获取有效Cookie")
            site_results.append({'user': user, 'status': 'fail', 'msg': '登录失败'})
            continue
            
        status, msg = sign(cookie, site_config, ns_random)
        print(f"签到结果: {msg}")
        
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
            print("通知已推送")
    else:
        print("今日已通知过，跳过推送")

if __name__ == "__main__":
    print("脚本启动...")
    ns_random = os.getenv("NS_RANDOM", "true")
    for name, config in SITES_CONFIG.items():
        try: process_site(name, config, ns_random)
        except Exception as e: print(f"站点异常: {e}")
