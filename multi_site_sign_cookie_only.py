# -*- coding: utf-8 -*-

import os
import time
import json
import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import requests

# 导入验证码解决器
try:
    from turnstile_solver import TurnstileSolver, TurnstileSolverError
    from yescaptcha import YesCaptchaSolver, YesCaptchaSolverError
except ImportError:
    print("警告：验证码解决器模块未找到，自动登录功能将不可用")

# ---------------- 通知模块动态加载 ----------------
hadsend = False
send = None
try:
    from notify import send
    hadsend = True
except ImportError:
    print("未加载通知模块，跳过通知功能")

# ---------------- 站点配置 ----------------
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

# ---------------- 通知状态管理 ----------------
NOTIFICATION_FILE = "./cookie/notification_status.json"

def load_notification_status():
    """加载通知状态"""
    try:
        if os.path.exists(NOTIFICATION_FILE):
            with open(NOTIFICATION_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        print(f"加载通知状态失败: {e}")
    return {}

def save_notification_status(status):
    """保存通知状态"""
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
    
    if site_name not in status:
        status[site_name] = {}
    
    status[site_name]['last_sent_date'] = today
    save_notification_status(status)

# ---------------- 环境检测函数 ----------------
def detect_environment():
    """检测当前运行环境"""
    if os.environ.get("IN_DOCKER") == "true":
        return "docker"
        
    ql_path_markers = ['/ql/data/', '/ql/config/', '/ql/', '/.ql/']
    in_ql_env = False
    
    for path in ql_path_markers:
        if os.path.exists(path):
            in_ql_env = True
            break
    
    in_github_env = os.environ.get("GITHUB_ACTIONS") == "true" or (os.environ.get("GH_PAT") and os.environ.get("GITHUB_REPOSITORY"))
    
    if in_ql_env:
        return "qinglong"
    elif in_github_env:
        return "github"
    else:
        return "unknown"

# ---------------- Cookie 文件操作 ----------------
def get_cookie_file_path(site_name, account_index=None):
    if account_index is not None:
        return f"./cookie/{site_name.upper()}_COOKIE_{account_index}.txt"
    return f"./cookie/{site_name.upper()}_COOKIE.txt"

def load_cookies_from_file(site_name, account_index=None):
    """从文件加载Cookie"""
    try:
        cookie_file = get_cookie_file_path(site_name, account_index)
        if os.path.exists(cookie_file):
            with open(cookie_file, "r", encoding='utf-8') as f:
                content = f.read().strip()
                # 处理可能的编码问题
                if content:
                    return content
    except UnicodeDecodeError:
        # 如果UTF-8解码失败，尝试其他编码
        try:
            with open(cookie_file, "r", encoding='gbk') as f:
                content = f.read().strip()
                if content:
                    return content
        except:
            pass
    except Exception as e:
        print(f"从文件读取Cookie失败: {e}")
    return ""

def save_cookie_to_file(site_name, cookie_str, account_index=None):
    """将Cookie保存到文件"""
    try:
        cookie_file = get_cookie_file_path(site_name, account_index)
        os.makedirs(os.path.dirname(cookie_file), exist_ok=True)
        
        # 确保cookie_str是字符串，处理可能的编码问题
        if isinstance(cookie_str, bytes):
            cookie_str = cookie_str.decode('utf-8', errors='ignore')
        
        with open(cookie_file, "w", encoding='utf-8') as f:
            f.write(cookie_str)
        print(f"Cookie 已成功保存到文件: {cookie_file}")
        return True
    except Exception as e:
        print(f"保存Cookie到文件失败: {e}")
        return False

def check_cookie_validity(site_config, cookie_str):
    """检查Cookie是否有效"""
    try:
        headers = {
            "Cookie": cookie_str,
            "Origin": site_config["origin"],
            "Referer": site_config["board_url"],
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        
        # 尝试访问用户信息页面
        response = requests.get(
            f"{site_config['stats_api']}1",
            headers=headers
        )
        
        # 正确处理响应编码，特别是中文字符
        if response.encoding is None:
            response.encoding = 'utf-8'
        
        # 确保响应文本正确解码，处理所有可能的编码问题
        try:
            response_text = response.text
        except UnicodeDecodeError as decode_error:
            # 如果默认编码失败，尝试其他常见编码
            try:
                response.encoding = 'gbk'
                response_text = response.text
            except UnicodeDecodeError:
                try:
                    response.encoding = 'gb2312'
                    response_text = response.text
                except UnicodeDecodeError:
                    # 如果所有编码都失败，使用原始字节内容
                    response_text = response.content.decode('utf-8', errors='ignore')
        
        # 检查响应状态和内容
        if response.status_code != 200:
            return False
            
        # 检查是否包含有效内容（credit或其他标识）
        return "credit" in response_text or "balance" in response_text or "amount" in response_text
        
    except Exception as e:
        print(f"检查Cookie有效性时出错: {e}")
        return False

def auto_login_with_captcha(site_config, username, password):
    """自动登录并解决验证码"""
    try:
        # 获取CloudFreed配置
        cloudfreed_api_key = os.getenv("CLOUDFREED_API_KEY", "")
        cloudfreed_base_url = os.getenv("CLOUDFREED_BASE_URL", "http://localhost:3000")
        
        if not cloudfreed_api_key:
            print("错误：未配置 CLOUDFREED_API_KEY 环境变量")
            return None
            
        # 初始化验证码解决器
        solver = TurnstileSolver(
            api_base_url=cloudfreed_base_url,
            client_key=cloudfreed_api_key
        )
        
        # 检查服务可用性（不强制要求，即使服务不可用也尝试继续）
        if not solver.health_check():
            print("警告：CloudFreed 服务可能不可用，但将继续尝试自动登录")
        
        # 为每个登录尝试创建新的独立会话
        session = requests.Session()
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Origin": site_config["origin"],
            "Referer": site_config["login_url"]
        }
        
        # 获取登录页面内容
        login_page_response = session.get(
            site_config["login_url"],
            headers=headers
        )
        
        if login_page_response.status_code != 200:
            print(f"获取登录页面失败: {login_page_response.status_code}")
            return None
        
        # 解决Turnstile验证码
        print("正在解决CloudFlare Turnstile验证码...")
        token = solver.solve(
            site_config["login_url"],
            site_config["sitekey"],
            user_agent=headers["User-Agent"],
            verbose=True
        )
        
        if not token:
            print("验证码解决失败")
            return None
        
        # 执行登录
        login_data = {
            "username": username,
            "password": password,
            "token": token,
            "source": "turnstile"
        }
        
        # 添加JSON请求头
        login_headers = headers.copy()
        login_headers["Content-Type"] = "application/json"
        
        login_response = session.post(
            site_config["login_api"],
            json=login_data,
            headers=login_headers
        )
        
        if login_response.status_code == 200:
            # 获取cookie
            cookies = session.cookies
            cookie_str = "; ".join([f"{name}={value}" for name, value in cookies.items()])
            
            # 打印登录响应和Cookie信息用于调试
            print(f"登录响应状态码: {login_response.status_code}")
            try:
                login_data = login_response.json()
                print(f"登录响应数据: {login_data}")
            except:
                print(f"登录响应内容: {login_response.text[:200]}")
            print(f"获取到的Cookie: {cookie_str}")
            
            # 验证登录是否成功
            if check_cookie_validity(site_config, cookie_str):
                print(f"自动登录成功，已获取新Cookie")
                return cookie_str
            else:
                print("登录成功但Cookie验证失败，尝试直接使用Cookie")
                # 即使验证失败，也返回Cookie尝试使用
                return cookie_str
        else:
            print(f"登录请求失败: {login_response.status_code}")
            try:
                error_data = login_response.json()
                print(f"登录错误信息: {error_data}")
            except:
                print(f"登录响应内容: {login_response.text[:200]}")
            return None
            
    except Exception as e:
        print(f"自动登录过程中出错: {e}")
        return None

def get_valid_cookie(site_config, username, password, account_index=None):
    """获取有效的Cookie，如果失效则自动登录"""
    # 首先尝试从文件读取（按账号索引读取）
    cookie_str = load_cookies_from_file(site_config["name"].lower(), account_index)
    
    # 如果文件没有，尝试从环境变量获取Cookie
    if not cookie_str:
        cookie_str = os.getenv(site_config["cookie_var"], "")
    
    # 检查Cookie是否有效
    if cookie_str and check_cookie_validity(site_config, cookie_str):
        print(f"{site_config['name']} 账号{account_index if account_index else ''} Cookie有效，直接使用")
        return cookie_str
    
    # Cookie失效，尝试自动登录
    print(f"{site_config['name']} 账号{account_index if account_index else ''} Cookie已失效，尝试自动登录...")
    
    if not username or not password:
        print("用户名或密码未配置，无法自动登录")
        return None
    
    new_cookie = auto_login_with_captcha(site_config, username, password)
    
    if new_cookie:
        # 保存新Cookie到文件（按账号索引保存）
        save_cookie_to_file(site_config["name"].lower(), new_cookie, account_index)
        return new_cookie
    else:
        print("自动登录失败")
        return None

# ---------------- 签到逻辑 ----------------
def sign(cookie, site_config, ns_random):
    if not cookie:
        return "invalid", "无有效Cookie"
        
    headers = {
        'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36 Edg/125.0.0.0",
        'origin': site_config["origin"],
        'referer': site_config["board_url"],
        'Content-Type': 'application/json',
        'Cookie': cookie
    }
    try:
        url = f"{site_config['sign_api']}?random={ns_random}"
        response = requests.post(url, headers=headers)
        data = response.json()
        msg = data.get("message", "")
        if "鸡腿" in msg or data.get("success"):
            return "success", msg
        elif "已完成签到" in msg:
            return "already", msg
        elif data.get("status") == 404:
            return "invalid", msg
        return "fail", msg
    except Exception as e:
        return "error", str(e)

# ---------------- 查询签到收益统计函数 ----------------
def get_signin_stats(cookie, site_config, days=30):
    """查询前days天内的签到收益统计"""
    if not cookie:
        return None, "无有效Cookie"
    
    if days <= 0:
        days = 1
    
    headers = {
        'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36 Edg/125.0.0.0",
        'origin': site_config["origin"],
        'referer': site_config["board_url"],
        'Cookie': cookie
    }
    
    try:
        shanghai_tz = ZoneInfo("Asia/Shanghai")
        now_shanghai = datetime.now(shanghai_tz)
        query_start_time = now_shanghai - timedelta(days=days)
        
        all_records = []
        page = 1
        
        while page <= 20:
            url = f"{site_config['stats_api']}{page}"
            response = requests.get(url, headers=headers)
            data = response.json()
            
            if not data.get("success") or not data.get("data"):
                break
                
            records = data.get("data", [])
            if not records:
                break
                
            last_record_time = datetime.fromisoformat(
                records[-1][3].replace('Z', '+00:00'))
            last_record_time_shanghai = last_record_time.astimezone(shanghai_tz)
            if last_record_time_shanghai < query_start_time:
                for record in records:
                    record_time = datetime.fromisoformat(
                        record[3].replace('Z', '+00:00'))
                    record_time_shanghai = record_time.astimezone(shanghai_tz)
                    if record_time_shanghai >= query_start_time:
                        all_records.append(record)
                break
            else:
                all_records.extend(records)
                
            page += 1
            time.sleep(0.5)
        
        signin_records = []
        for record in all_records:
            amount, balance, description, timestamp = record
            record_time = datetime.fromisoformat(
                timestamp.replace('Z', '+00:00'))
            record_time_shanghai = record_time.astimezone(shanghai_tz)
            
            if (record_time_shanghai >= query_start_time and
                    "签到收益" in description and "鸡腿" in description):
                signin_records.append({
                    'amount': amount,
                    'date': record_time_shanghai.strftime('%Y-%m-%d'),
                    'description': description
                })
        
        period_desc = f"近{days}天"
        if days == 1:
            period_desc = "今天"
        
        if not signin_records:
            return {
                'total_amount': 0,
                'average': 0,
                'days_count': 0,
                'records': [],
                'period': period_desc,
            }, f"查询成功，但没有找到{period_desc}的签到记录"
        
        total_amount = sum(record['amount'] for record in signin_records)
        days_count = len(signin_records)
        average = round(total_amount / days_count, 2) if days_count > 0 else 0
        
        stats = {
            'total_amount': total_amount,
            'average': average,
            'days_count': days_count,
            'records': signin_records,
            'period': period_desc
        }
        
        return stats, "查询成功"
        
    except Exception as e:
        return None, f"查询异常: {str(e)}"

# ---------------- 显示签到统计信息 ----------------
def print_signin_stats(stats, account_name):
    """打印签到统计信息"""
    if not stats:
        return
        
    print(f"\n==== {account_name} 签到收益统计 ({stats['period']}) ====")
    print(f"签到天数: {stats['days_count']} 天")
    print(f"总获得鸡腿: {stats['total_amount']} 个")
    print(f"平均每日鸡腿: {stats['average']} 个")

# ---------------- 解析用户名配置 ----------------
def parse_usernames(usernames_str):
    """解析用户名配置字符串"""
    if not usernames_str:
        return []
    
    # 支持多种分隔符：& | , ;
    usernames = re.split(r'[&|,;]', usernames_str)
    return [name.strip() for name in usernames if name.strip()]

def parse_accounts_from_cookie(cookie_str):
    """从Cookie字符串解析账号信息"""
    if not cookie_str:
        return [], []
    
    # 格式：用户名1&密码1&用户名2&密码2
    parts = cookie_str.split("&")
    parts = [part.strip() for part in parts if part.strip()]
    
    usernames = []
    passwords = []
    
    # 每两个元素为一组：用户名和密码
    for i in range(0, len(parts), 2):
        if i + 1 < len(parts):
            usernames.append(parts[i])
            passwords.append(parts[i + 1])
    
    return usernames, passwords

# ---------------- 处理单个站点 ----------------
def process_site(site_name, site_config, ns_random):
    """处理单个站点的签到"""
    print(f"\n{'='*50}")
    print(f"开始处理 {site_config['name']} 站点")
    print(f"{'='*50}")
    
    env_type = detect_environment()
    
    # 从Cookie环境变量解析账号信息
    cookie_str = os.getenv(site_config["cookie_var"], "")
    custom_usernames, passwords = parse_accounts_from_cookie(cookie_str)
    
    # 读取Cookie
    all_cookies = ""
    if env_type == "docker":
        cookie_file = get_cookie_file_path(site_name)
        print(f"Docker环境，尝试从 {cookie_file} 读取Cookie...")
        all_cookies = load_cookies_from_file(site_name)
        if all_cookies:
            print("成功从文件加载Cookie。")
        else:
            print("Cookie文件不存在或为空。")
    else:
        all_cookies = os.getenv(site_config["cookie_var"], "")
        print(f"从环境变量 {site_config['cookie_var']} 读取Cookie")
    
    # 处理Cookie列表
    cookie_list = []
    if all_cookies:
        cookie_list = all_cookies.split("&")
        cookie_list = [c.strip() for c in cookie_list if c.strip()]
    
    # 智能匹配：只处理有用户名密码配置的账号
    valid_cookie_list = []
    for i, cookie in enumerate(cookie_list):
        if i < len(custom_usernames) and i < len(passwords):
            valid_cookie_list.append(cookie)
        else:
            print(f"忽略账号{i+1}：缺少用户名或密码配置")
    
    # 如果没有Cookie但有用户名密码，尝试自动登录
    if not valid_cookie_list and custom_usernames and passwords:
        print("未找到Cookie配置，但检测到用户名密码配置，尝试自动登录...")
        # 确保用户名和密码数量匹配
        min_accounts = min(len(custom_usernames), len(passwords))
        for i in range(min_accounts):
            username = custom_usernames[i]
            password = passwords[i]
            print(f"尝试为 {username} 自动登录...")
            new_cookie = get_valid_cookie(site_config, username, password, i+1)
            if new_cookie:
                valid_cookie_list.append(new_cookie)
    
    print(f"共发现 {len(cookie_list)} 个Cookie，有效配置 {len(valid_cookie_list)} 个账号")
    if custom_usernames:
        print(f"发现 {len(custom_usernames)} 个自定义用户名: {custom_usernames}")
    
    site_results = []
    
    for i, cookie in enumerate(valid_cookie_list):
        account_index = i + 1
        
        # 确定显示名称：优先使用自定义用户名，否则使用默认名称
        if i < len(custom_usernames):
            display_user = custom_usernames[i]
            print(f"\n==== {site_config['name']} {display_user} 开始签到 ====")
        else:
            display_user = f"账号{account_index}"
            print(f"\n==== {site_config['name']} {display_user} 开始签到 ====")
        
        # 检查Cookie是否有效，如果失效则尝试自动登录
        if not check_cookie_validity(site_config, cookie):
            print(f"{display_user} Cookie已失效，尝试自动登录...")
            if i < len(custom_usernames) and i < len(passwords):
                username = custom_usernames[i]
                password = passwords[i]
                new_cookie = get_valid_cookie(site_config, username, password, i+1)
                if new_cookie:
                    cookie = new_cookie
                    print(f"自动登录成功，使用新Cookie")
                else:
                    print(f"自动登录失败，跳过该账号")
                    site_results.append({
                        'account': display_user,
                        'status': 'failed',
                        'message': 'Cookie失效且自动登录失败',
                        'stats': None
                    })
                    continue
            else:
                print(f"无法自动登录：缺少用户名或密码配置")
                site_results.append({
                    'account': display_user,
                    'status': 'failed',
                    'message': 'Cookie失效且无法自动登录',
                    'stats': None
                })
                continue
        
        result, msg = sign(cookie, site_config, ns_random)

        if result in ["success", "already"]:
            print(f"{display_user} 签到成功: {msg}")
            
            print("正在查询签到收益统计...")
            stats, stats_msg = get_signin_stats(cookie, site_config, 30)
            if stats:
                print_signin_stats(stats, display_user)
            else:
                print(f"统计查询失败: {stats_msg}")
            
            site_results.append({
                'account': display_user,
                'status': 'success',
                'message': msg,
                'stats': stats
            })
            
        else:
            print(f"{display_user} 签到失败: {msg}")
            site_results.append({
                'account': display_user,
                'status': 'failed',
                'message': msg,
                'stats': None
            })
    
    # 发送汇总通知（每天只发送一次）
    if hadsend and should_send_notification(site_name):
        try:
            success_count = len([r for r in site_results if r['status'] == 'success'])
            failed_count = len([r for r in site_results if r['status'] != 'success'])
            
            notification_msg = f"{site_config['name']} 签到汇总\n"
            notification_msg += f"成功: {success_count} 个账号\n"
            if failed_count > 0:
                notification_msg += f"失败: {failed_count} 个账号\n"
            
            # 添加成功账号的详细信息
            for result in site_results:
                if result['status'] == 'success':
                    notification_msg += f"\n{result['account']}: {result['message']}"
                    if result['stats']:
                        stats = result['stats']
                        notification_msg += f"\n  {stats['period']}已签到{stats['days_count']}天，共获得{stats['total_amount']}个鸡腿"
            
            # 添加失败账号信息
            for result in site_results:
                if result['status'] != 'success':
                    notification_msg += f"\n{result['account']}: {result['message']}"
            
            send(f"{site_config['name']} 签到汇总", notification_msg)
            mark_notification_sent(site_name)
            print(f"已发送 {site_config['name']} 汇总通知")
        except Exception as e:
            print(f"发送通知失败: {e}")

# ---------------- 主流程 ----------------
if __name__ == "__main__":
    ns_random = os.getenv("NS_RANDOM", "true")

    env_type = detect_environment()
    print(f"当前运行环境: {env_type}")
    print("Cookie多账户签到脚本启动")
    
    # 处理所有配置的站点
    for site_name, site_config in SITES_CONFIG.items():
        try:
            process_site(site_name, site_config, ns_random)
        except Exception as e:
            print(f"处理 {site_config['name']} 站点时发生异常: {e}")
    
    print(f"\n{'='*50}")
    print("所有站点处理完成")
    print(f"{'='*50}")
