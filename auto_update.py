import json
import urllib.request
import time
import os
from datetime import datetime, timezone, timedelta

def get_us_stock_tencent(symbol):
    """使用腾讯接口获取美股（如QQQ/VOO）实时、盘前和盘后数据"""
    url = f"https://qt.gtimg.cn/q=us{symbol}"
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
                
            print(f"  {symbol} (腾讯源 - {session}): ${round(current_price, 2)}")
            return current_price, prev_close, change_pct, session
            
    except Exception as e:
        print(f"  [警告] 腾讯获取 {symbol} 失败: {e}")
    return None, None, None, None

def get_yahoo_daily_pct(symbol):
    """获取雅虎日线数据，计算昨晚真实的收盘涨幅"""
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=5d"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            closes = data['chart']['result'][0]['indicators']['quote'][0]['close']
            valid = [c for c in closes if c is not None]
            if len(valid) >= 2:
                pct = ((valid[-2] - valid[-3]) / valid[-3]) * 100 if len(valid) >= 3 else ((valid[-1] - valid[-2]) / valid[-2]) * 100
                return round(pct, 2)
    except Exception as e:
        pass
    return None

def get_us_indices_tencent():
    """使用腾讯接口获取 NDX 和 SPX 指数数据"""
    print("正在获取 NDX 和 SPX 指数（腾讯接口）...")
    url = "https://qt.gtimg.cn/q=usNDX,usINX"
    req = urllib.request.Request(url)
    req.add_header("User-Agent", "Mozilla/5.0")
    
    results = {"ndx": 20000.0, "ndx_pct": 0.0, "spx": 5000.0, "spx_pct": 0.0}
    
    try:
        with urllib.request.urlopen(req, timeout=8) as response:
            raw_data = response.read().decode('gbk')
            
        for line in raw_data.strip().split(";"):
            line = line.strip()
            if not line or "=" not in line: continue
            code_part, value_part = line.split("=", 1)
            code = code_part.split("_")[-1].strip().lower()
            fields = value_part.strip('"').split("~")
            
            if len(fields) > 32:
                price = float(fields[3]) if fields[3] else 0.0
                pct = float(fields[32]) if fields[32] else 0.0
                
                if "ndx" in code:
                    results["ndx"] = round(price, 2)
                    results["ndx_pct"] = round(pct, 2)
                    print(f"  NDX 纳斯达克100: {results['ndx']} ({results['ndx_pct']}%)")
                elif "inx" in code:
                    results["spx"] = round(price, 2)
                    results["spx_pct"] = round(pct, 2)
                    print(f"  SPX 标普500: {results['spx']} ({results['spx_pct']}%)")
    except Exception as e:
        print(f"  获取腾讯指数失败: {e}")
        
    return results

def get_other_us_data():
    """获取 NQ 期货和 VIX"""
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
    etfs = ["159501", "159659", "159696", "513870", "513500"]
    codes = ",".join([f"sz{code}" if code.startswith("15") else f"sh{code}" for code in etfs])
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
            code = code_part.split("_")[-1].replace("sz", "").replace("sh", "").strip()
            fields = value_part.strip('"').split("~")
            if len(fields) > 78 and code in etfs:
                price = float(fields[3]) if fields[3] else 0.0
                iopv = float(fields[78]) if fields[78] else None
                change_pct = float(fields[32]) if fields[32] else 0.0
                cn_data[code] = {"price": price, "iopv": iopv, "changePct": round(change_pct, 2)}
                print(f"  {code}: 价格 {price}, 涨跌幅 {change_pct}%")
    except Exception as e:
        print(f"  获取国内 ETF 失败: {e}")
    return cn_data

def process_us_stock(symbol, prev_fallback_price):
    """通用处理美股股票数据"""
    price, prev_close, pct, session = get_us_stock_tencent(symbol)
    
    if price is None:
        price = prev_fallback_price
        prev_close = prev_fallback_price
        pct = 0.0
        session = "收盘"
    
    real_close_pct = 0.0
    if session == "收盘":
        real_close_pct = pct
    else:
        y_pct = get_yahoo_daily_pct(symbol)
        if y_pct is not None:
            real_close_pct = y_pct
        else:
            real_close_pct = pct
            
    return {
        "price": round(price, 2),
        "changePct": round(pct, 2),
        "close_price": round(prev_close, 2),
        "close_pct": round(real_close_pct, 2),
        "session": session
    }

def get_dynamic_high(asset_id, current_price, default_high, old_highs):
    """核心逻辑：自动对比并更新历史最高点"""
    # 取出历史记录中的高点，如果没有则使用默认初始高点
    history_high = old_highs.get(asset_id, default_high)
    # 取 默认高点、历史记录高点、当前最新价 三者的最大值
    new_high = max(default_high, history_high, current_price)
    return round(new_high, 4)

def update_json():
    # 1. 尝试读取上一次生成的 prices.json 获取历史高点记忆
    old_highs = {}
    if os.path.exists("prices.json"):
        try:
            with open("prices.json", "r", encoding="utf-8") as f:
                old_data = json.load(f)
                for asset in old_data.get("assets", []):
                    if asset.get("high") is not None:
                        old_highs[asset["id"]] = float(asset["high"])
        except Exception as e:
            print(f"  [提示] 读取历史高点失败: {e}")

    # 2. 抓取所有最新数据
    indices = get_us_indices_tencent()
    other_us = get_other_us_data()
    cn_data = get_cn_etf_data()
    
    qqq_info = process_us_stock("QQQ", 690.38)
    voo_info = process_us_stock("VOO", 688.66)
            
    tz_bj = timezone(timedelta(hours=8))
    now_str = datetime.now(tz_bj).strftime("%Y-%m-%dT%H:%M:%S+08:00")
    
    # 3. 计算并组装 JSON（注入动态高点逻辑）
    json_data = {
        "updated": now_str,
        "assets": [
            {
                "id": "nq", "label": "NQ 期货 · 纳指100",
                "currency": "", "decimals": 2,
                "price": other_us["nq"], "changePct": other_us["nq_pct"],
                "high": None, "highLabel": "", "highDate": "", "ytdBase": None, "iopv": None, "asOf": "", "note": ""
            },
            {
                "id": "vix", "label": "VIX · 恐慌指数",
                "currency": "", "decimals": 2,
                "price": other_us["vix"], "changePct": other_us["vix_pct"],
                "high": None, "highLabel": "", "highDate": "", "ytdBase": None, "iopv": None, "asOf": "", "note": ""
            },
            {
                "id": "ndx", "label": "NDX · 纳斯达克100",
                "currency": "", "decimals": 2,
                "price": indices["ndx"], "changePct": indices["ndx_pct"],
                "high": None, "highLabel": "", "highDate": "", "ytdBase": None, "iopv": None, "asOf": "", "note": ""
            },
            {
                "id": "spx", "label": "SPX · 标普500",
                "currency": "", "decimals": 2,
                "price": indices["spx"], "changePct": indices["spx_pct"],
                "high": None, "highLabel": "", "highDate": "", "ytdBase": None, "iopv": None, "asOf": "", "note": ""
            },
            {
                "id": "qqq", "label": "QQQ · 纳斯达克100 ETF",
                "currency": "$", "decimals": 2,
                "price": qqq_info["price"], "changePct": qqq_info["changePct"],
                "close_price": qqq_info["close_price"], "close_pct": qqq_info["close_pct"],
                "session": qqq_info["session"],
                "high": get_dynamic_high("qqq", qqq_info["price"], 759.66, old_highs), 
                "highLabel": "历史收盘高点", "highDate": "",
                "ytdBase": 614.00, "iopv": None, "asOf": "实时 (腾讯)", "note": ""
            },
            {
                "id": "voo", "label": "VOO · 标普500 ETF",
                "currency": "$", "decimals": 2,
                "price": voo_info["price"], "changePct": voo_info["changePct"],
                "close_price": voo_info["close_price"], "close_pct": voo_info["close_pct"],
                "session": voo_info["session"],
                "high": get_dynamic_high("voo", voo_info["price"], 718.47, old_highs),
                "highLabel": "历史高点", "highDate": "2026-10",
                "ytdBase": 628.30, "iopv": None, "asOf": "实时 (腾讯)", "note": ""
            },
            {
                "id": "159501", "label": "159501 · 嘉实纳指ETF",
                "currency": "¥", "decimals": 3,
                "price": cn_data["159501"]["price"], "changePct": cn_data["159501"]["changePct"],
                "high": get_dynamic_high("159501", cn_data["159501"]["price"], 2.2550, old_highs), 
                "highLabel": "10月高点", "highDate": "", "ytdBase": 1.783, "iopv": cn_data["159501"]["iopv"], "asOf": "实时 (腾讯)", "note": ""
            },
            {
                "id": "159659", "label": "159659 · 招商纳指ETF",
                "currency": "¥", "decimals": 3,
                "price": cn_data["159659"]["price"], "changePct": cn_data["159659"]["changePct"],
                "high": get_dynamic_high("159659", cn_data["159659"]["price"], 2.5290, old_highs),
                "highLabel": "修正高点", "highDate": "2026-10-12", "ytdBase": 1.984, "iopv": cn_data["159659"]["iopv"], "asOf": "实时 (腾讯)", "note": ""
            },
            {
                "id": "159696", "label": "159696 · 易方达纳指ETF",
                "currency": "¥", "decimals": 3,
                "price": cn_data["159696"]["price"], "changePct": cn_data["159696"]["changePct"],
                "high": get_dynamic_high("159696", cn_data["159696"]["price"], 2.2600, old_highs),
                "highLabel": "10月高点", "highDate": "", "ytdBase": 1.735, "iopv": cn_data["159696"]["iopv"], "asOf": "实时 (腾讯)", "note": ""
            },
            {
                "id": "513870", "label": "513870 · 富国纳斯达克100ETF",
                "currency": "¥", "decimals": 3,
                "price": cn_data["513870"]["price"], "changePct": cn_data["513870"]["changePct"],
                "high": get_dynamic_high("513870", cn_data["513870"]["price"], 2.236, old_highs),
                "highLabel": "历史高点", "highDate": "2026-10", "ytdBase": 1.762, "iopv": cn_data["513870"]["iopv"], "asOf": "实时 (腾讯)", "note": ""
            },
            {
                "id": "513500", "label": "513500 · 博时标普500ETF",
                "currency": "¥", "decimals": 3,
                "price": cn_data["513500"]["price"], "changePct": cn_data["513500"]["changePct"],
                "high": get_dynamic_high("513500", cn_data["513500"]["price"], 2.778, old_highs),
                "highLabel": "历史高点", "highDate": "2026-10", "ytdBase": 2.432, "iopv": cn_data["513500"]["iopv"], "asOf": "实时 (腾讯)", "note": ""
            }
        ]
    }
    
    json_str = json.dumps(json_data, ensure_ascii=False, indent=2)
    with open("prices.json", "w", encoding="utf-8") as f:
        f.write(json_str)
    with open("prices.js", "w", encoding="utf-8") as f:
        f.write("window.LATEST_PRICES = " + json_str + ";")
        
    print(f"[{now_str}] 数据同步成功！（已自动对比并更新历史高点）\n")

# 云端专用：跑一次直接结束，千万别加 while True
update_json()
