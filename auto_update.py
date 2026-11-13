import json
import urllib.request
import time
from datetime import datetime, timezone, timedelta

def get_qqq_tencent():
    """使用腾讯接口获取 QQQ 实时、盘前和盘后数据"""
    url = "https://qt.gtimg.cn/q=usQQQ"
    req = urllib.request.Request(url)
    req.add_header("User-Agent", "Mozilla/5.0")
    
    try:
        with urllib.request.urlopen(req, timeout=8) as response:
            raw_data = response.read().decode('gbk')
            
        data_str = raw_data.split('"')[1]
        fields = data_str.split("~")
        
        if len(fields) > 32:
            current_price = float(fields[3])
            prev_close = float(fields[4])
            change_pct = float(fields[32])
            
            market_state = fields[30] if len(fields) > 30 else ""
            
            session = "实时"
            if "盘前" in market_state:
                session = "盘前"
            elif "盘后" in market_state:
                session = "盘后"
            elif current_price == prev_close:
                session = "收盘"
                
            print(f"  QQQ (腾讯源 - {session}): ${round(current_price, 2)}")
            return current_price, prev_close, change_pct, session
            
    except Exception as e:
        print(f"  [警告] 腾讯获取 QQQ 失败: {e}")
    return None, None, None, None

def get_yahoo_daily_pct():
    """获取雅虎日线数据，计算昨晚真实的收盘涨幅（克服腾讯不提供历史涨幅的缺点）"""
    url = "https://query1.finance.yahoo.com/v8/finance/chart/QQQ?interval=1d&range=5d"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            closes = data['chart']['result'][0]['indicators']['quote'][0]['close']
            valid = [c for c in closes if c is not None]
            if len(valid) >= 2:
                # 计算倒数第二天的收盘价涨幅（即昨晚的涨幅）
                pct = ((valid[-2] - valid[-3]) / valid[-3]) * 100 if len(valid) >= 3 else ((valid[-1] - valid[-2]) / valid[-2]) * 100
                return round(pct, 2)
    except Exception as e:
        pass
    return None

def get_other_us_data():
    print("正在获取期货与 VIX 数据（新浪财经）...")
    symbols = "hf_NQ,znb_VIX"
    url = f"https://hq.sinajs.cn/list={symbols}"
    req = urllib.request.Request(url)
    req.add_header("Referer", "https://finance.sina.com.cn")
    req.add_header("User-Agent", "Mozilla/5.0")
    
    results = {"nq": 28000.0, "nq_pct": 0.0, "vix": 19.42, "vix_pct": 0.0}
    
    def safe_float(val, default=0.0):
        try:
            if not val or str(val).strip() == "" or str(val).strip() == "None": return default
            return float(val)
        except: return default

    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            raw_data = response.read().decode('gbk')
            
        for line in raw_data.strip().split("\n"):
            if "=" not in line or '""' in line: continue
            code_part = line.split("=")[0].split("_")[-1].strip().lower()
            data = line.split('"')[1].split(",")
            
            if code_part == "nq" and len(data) > 8:
                price = safe_float(data[0], 28000.0)
                pre_close = safe_float(data[1], 0.0) or safe_float(data[7], 0.0) or safe_float(data[8], price)
                pct = ((price - pre_close) / pre_close) * 100 if pre_close > 0 else 0.0
                results["nq"] = round(price, 2)
                results["nq_pct"] = round(pct, 2)
                print(f"  NQ 期货: {results['nq']} ({results['nq_pct']}%)")
            elif code_part == "vix" and len(data) > 1:
                results["vix"] = round(safe_float(data[1], 19.42), 2)
                if len(data) > 3: results["vix_pct"] = round(safe_float(data[3], 0.0), 2)
                print(f"  VIX: {results['vix']} ({results['vix_pct']}%)")
    except Exception as e:
        print(f"  获取新浪数据失败: {e}")
    return results

def get_cn_etf_data():
    print("正在获取国内 ETF 数据（腾讯接口）...")
    etfs = ["159501", "159659", "159696"]
    codes = ",".join([f"sz{code}" for code in etfs])
    url = f"https://qt.gtimg.cn/q={codes}"
    req = urllib.request.Request(url)
    req.add_header("Referer", "https://finance.qq.com")
    
    cn_data = {code: {"price": 2.00, "iopv": None, "changePct": 0.0} for code in etfs}
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            raw_data = response.read().decode('gbk')
        for line in raw_data.strip().split(";"):
            line = line.strip()
            if not line or "=" not in line: continue
            code_part, value_part = line.split("=", 1)
            code = code_part.split("_")[-1].replace("sz", "").strip()
            fields = value_part.strip('"').split("~")
            if len(fields) > 78:
                price = float(fields[3]) if fields[3] else 0.0
                iopv = float(fields[78]) if fields[78] else None
                change_pct = float(fields[32]) if fields[32] else 0.0
                cn_data[code] = {"price": price, "iopv": iopv, "changePct": round(change_pct, 2)}
                print(f"  {code}: 价格 {price}, 涨跌幅 {change_pct}%")
    except Exception as e:
        print(f"  获取国内 ETF 失败: {e}")
    return cn_data

def update_json():
    other_us = get_other_us_data()
    cn_data = get_cn_etf_data()
    
    q_price, q_prev, q_pct, q_session = get_qqq_tencent()
    
    if q_price is None:
        print("  [兜底] 腾讯接口失败，使用 NQ 期货模拟 QQQ")
        q_prev = 690.38
        q_pct = other_us["nq_pct"]
        q_price = q_prev * (1 + q_pct / 100)
        q_session = "模拟盘前"
    
    # 智能获取昨晚的收盘涨幅
    real_close_pct = 0.0
    if q_session == "收盘":
        # 如果现在是收盘状态，当前涨幅就是昨晚涨幅
        real_close_pct = q_pct
    else:
        # 如果是盘中或盘前，去查日线真实涨幅
        y_pct = get_yahoo_daily_pct()
        if y_pct is not None:
            real_close_pct = y_pct
        else:
            real_close_pct = q_pct # 兜底
            
    tz_bj = timezone(timedelta(hours=8))
    now_str = datetime.now(tz_bj).strftime("%Y-%m-%dT%H:%M:%S+08:00")
    
    json_data = {
        "updated": now_str,
        "assets": [
            {
                "id": "qqq", "label": "QQQ · 纳斯达克100 ETF",
                "currency": "$", "decimals": 2,
                "price": round(q_price, 2), "changePct": round(q_pct, 2),
                "close_price": round(q_prev, 2), 
                "close_pct": real_close_pct,  # 修复：不再写死 3.54
                "session": q_session,
                "high": 759.66, "highLabel": "历史收盘高点", "highDate": "",
                "ytdBase": 614.00, "iopv": None, "asOf": "实时 (腾讯)", "note": ""
            },
            {
                "id": "nq", "label": "NQ 期货 · 纳指100",
                "currency": "", "decimals": 2,
                "price": other_us["nq"], "changePct": other_us["nq_pct"],
                "high": None, "highLabel": "", "highDate": "", "ytdBase": None, "iopv": None, "asOf": "实时 (新浪)", "note": ""
            },
            {
                "id": "vix", "label": "VIX · 恐慌指数",
                "currency": "", "decimals": 2,
                "price": other_us["vix"], "changePct": other_us["vix_pct"],
                "high": None, "highLabel": "", "highDate": "", "ytdBase": None, "iopv": None, "asOf": "实时 (新浪)", "note": ""
            },
            {
                "id": "159501", "label": "159501 · 嘉实纳指ETF",
                "currency": "¥", "decimals": 3,
                "price": cn_data["159501"]["price"], "changePct": cn_data["159501"]["changePct"],
                "high": 2.2550, "highLabel": "10月高点", "highDate": "", "ytdBase": 1.799, "iopv": cn_data["159501"]["iopv"], "asOf": "实时 (腾讯)", "note": ""
            },
            {
                "id": "159659", "label": "159659 · 招商纳指ETF",
                "currency": "¥", "decimals": 3,
                "price": cn_data["159659"]["price"], "changePct": cn_data["159659"]["changePct"],
                "high": 2.5290, "highLabel": "修正高点", "highDate": "2026-10-12", "ytdBase": 1.920, "iopv": cn_data["159659"]["iopv"], "asOf": "实时 (腾讯)", "note": ""
            },
            {
                "id": "159696", "label": "159696 · 易方达纳指ETF",
                "currency": "¥", "decimals": 3,
                "price": cn_data["159696"]["price"], "changePct": cn_data["159696"]["changePct"],
                "high": 2.2600, "highLabel": "10月高点", "highDate": "", "ytdBase": 1.692, "iopv": cn_data["159696"]["iopv"], "asOf": "实时 (腾讯)", "note": ""
            }
        ]
    }
    
    json_str = json.dumps(json_data, ensure_ascii=False, indent=2)
    with open("prices.json", "w", encoding="utf-8") as f:
        f.write(json_str)
    with open("prices.js", "w", encoding="utf-8") as f:
        f.write("window.LATEST_PRICES = " + json_str + ";")
        
    print(f"[{now_str}] 数据同步成功！\n")

# 云端专用：跑一次直接结束，千万别加 while True
update_json()