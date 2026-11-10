import json
import urllib.request
from datetime import datetime, timezone, timedelta

def get_us_data():
    print("正在获取美股与期货数据（新浪财经）...")
    symbols = "gb_qqq,hf_NQ,znb_VIX"
    url = f"https://hq.sinajs.cn/list={symbols}"
    
    req = urllib.request.Request(url)
    req.add_header("Referer", "https://finance.sina.com.cn")
    req.add_header("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64)")
    
    results = {
        "qqq": 681.04, "qqq_pct": 0.0,
        "nq": 28248.28, "nq_pct": 0.0,
        "vix": 19.42, "vix_pct": 0.0
    }
    
    def safe_float(val, default=0.0):
        try:
            if not val or str(val).strip() == "" or str(val).strip() == "None":
                return default
            return float(val)
        except:
            return default

    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            raw_data = response.read().decode('gbk')
            
        for line in raw_data.strip().split("\n"):
            if "=" not in line or '""' in line:
                continue
            
            code_part = line.split("=")[0].split("_")[-1].strip().lower()
            data = line.split('"')[1].split(",")
            
            if code_part == "qqq" and len(data) > 2:
                results["qqq"] = round(safe_float(data[1], 681.04), 2)
                results["qqq_pct"] = round(safe_float(data[2], 0.0), 2)
                print(f"  QQQ: {results['qqq']} ({results['qqq_pct']}%)")
                
            elif code_part == "nq" and len(data) > 8:
                # NQ 期货：新浪有时会返回空昨收，我们需要智能探测
                price = safe_float(data[0], 28248.28)
                pre_close = safe_float(data[1], 0.0)
                
                # 如果 data[1] 为空，尝试用 data[7] (昨结) 或 data[8] (今开)
                if pre_close == 0:
                    pre_close = safe_float(data[7], 0.0)
                if pre_close == 0:
                    pre_close = safe_float(data[8], price)
                    
                pct = ((price - pre_close) / pre_close) * 100 if pre_close > 0 else 0.0
                
                results["nq"] = round(price, 2)
                results["nq_pct"] = round(pct, 2)
                print(f"  NQ 期货: {results['nq']} ({results['nq_pct']}%)")
                
            elif code_part == "vix" and len(data) > 1:
                results["vix"] = round(safe_float(data[1], 19.42), 2)
                if len(data) > 3:
                    results["vix_pct"] = round(safe_float(data[3], 0.0), 2)
                print(f"  VIX: {results['vix']} ({results['vix_pct']}%)")
                
    except Exception as e:
        print(f"  获取美股数据失败: {e}")
        
    return results
def get_cn_etf_data():
    print("正在获取国内 ETF 数据（腾讯原始行情接口）...")
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
            if not line or "=" not in line:
                continue
            
            code_part, value_part = line.split("=", 1)
            code = code_part.split("_")[-1].replace("sz", "").strip()
            fields = value_part.strip('"').split("~")
            
            if len(fields) > 78:
                price = float(fields[3]) if fields[3] else 0.0
                iopv = float(fields[78]) if fields[78] else None
                change_pct = float(fields[32]) if fields[32] else 0.0
                cn_data[code] = {
                    "price": price, 
                    "iopv": iopv, 
                    "changePct": round(change_pct, 2)
                }
                print(f"  {code} 价格: {price} (今日 {change_pct}%), IOPV: {iopv}")
                
    except Exception as e:
        print(f"  获取国内 ETF 失败: {e}")
        
    return cn_data

def update_json():
    us_data = get_us_data()
    cn_data = get_cn_etf_data()
    
    tz_bj = timezone(timedelta(hours=8))
    now_str = datetime.now(tz_bj).strftime("%Y-%m-%dT%H:%M:%S+08:00")
    
    def make_asset(aid, label, currency, decimals, price, high, highLabel, highDate, ytdBase, iopv, asOf, changePct):
        return {
            "id": aid, "label": label, "currency": currency, "decimals": decimals,
            "price": price, "high": high, "highLabel": highLabel, "highDate": highDate,
            "ytdBase": ytdBase, "iopv": iopv, "asOf": asOf, "changePct": changePct
        }
    
    json_data = {
        "updated": now_str,
        "assets": [
            make_asset("qqq", "QQQ · 纳斯达克100 ETF", "$", 2, us_data["qqq"], 759.66, "历史收盘高点", "", 614.00, None, "实时 (新浪)", us_data["qqq_pct"]),
            make_asset("nq", "NQ 期货 · 纳指100", "", 2, us_data["nq"], None, "", "", None, None, "实时 (新浪)", us_data["nq_pct"]),
            make_asset("vix", "VIX · 恐慌指数", "", 2, us_data["vix"], None, "", "", None, None, "实时 (新浪)", us_data["vix_pct"]),
            make_asset("159501", "159501 · 嘉实纳指ETF", "¥", 3, cn_data["159501"]["price"], 2.2550, "10月高点", "", 1.799, cn_data["159501"]["iopv"], "实时 (腾讯)", cn_data["159501"]["changePct"]),
            make_asset("159659", "159659 · 招商纳指ETF", "¥", 3, cn_data["159659"]["price"], 2.5290, "修正高点", "2026-10-12", 1.920, cn_data["159659"]["iopv"], "实时 (腾讯)", cn_data["159659"]["changePct"]),
            make_asset("159696", "159696 · 易方达纳指ETF", "¥", 3, cn_data["159696"]["price"], 2.2600, "10月高点", "", 1.692, cn_data["159696"]["iopv"], "实时 (腾讯)", cn_data["159696"]["changePct"]),
        ]
    }
    
    json_str = json.dumps(json_data, ensure_ascii=False, indent=2)
    
    # 同时生成 json 和 js
    with open("prices.json", "w", encoding="utf-8") as f:
        f.write(json_str)
    with open("prices.js", "w", encoding="utf-8") as f:
        f.write("window.LATEST_PRICES = " + json_str + ";")
        
    print(f"[{now_str}] 数据同步成功 (含涨跌幅)！\n")

if __name__ == "__main__":
    update_json()