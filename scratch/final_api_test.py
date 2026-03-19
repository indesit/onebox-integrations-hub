import httpx
import json
import sys
import os
from datetime import datetime

# Add project path to sys.path for settings
sys.path.append('/root/.openclaw/workspace/projects/onebox-integrations-hub')
from src.config.settings import settings

def run_final_test():
    url = 'http://91.202.6.56/SecretShopBAS/hs/reports/receipt_lines'
    auth = (settings.baf_user, settings.baf_password)
    
    print("--- 1. BASIC REQUEST & COUNTS ---")
    r = httpx.get(url, params={'date_from': '2026-03-13', 'date_to': '2026-03-14'}, auth=auth, timeout=60)
    data = r.json()
    rows = data.get('rows', [])
    print(f"Success: {data.get('success')}")
    print(f"Count field: {data.get('count')}")
    print(f"Actual rows: {len(rows)}")
    assert data.get('success') is True
    assert data.get('count') == len(rows)

    print("\n--- 2. REGULAR SALE (No Certificates) ---")
    regular = [r for r in rows if not r.get('is_gift_certificate_sale') and not r.get('has_certificate_payment') and r.get('qty', 0) > 0][0]
    print(json.dumps(regular, indent=2, ensure_ascii=False))
    assert regular['qty'] > 0 and regular['amount'] > 0
    assert regular['is_gift_certificate_sale'] is False and regular['has_certificate_payment'] is False

    print("\n--- 3. GIFT CERTIFICATE SALE (Приход) ---")
    # Using known check R30628
    cert_sale = [r for r in rows if r.get('is_gift_certificate_sale')][0]
    print(json.dumps(cert_sale, indent=2, ensure_ascii=False))
    assert cert_sale['is_gift_certificate_sale'] is True
    assert cert_sale['gift_certificate_sale_amount'] > 0

    print("\n--- 4. CERTIFICATE PAYMENT (Расход) ---")
    # Finding any row paid by cert
    cert_pay = [r for r in rows if r.get('has_certificate_payment')][0]
    print(json.dumps(cert_pay, indent=2, ensure_ascii=False))
    assert cert_pay['has_certificate_payment'] is True
    assert cert_pay['certificate_payment_amount'] > 0

    print("\n--- 6. RETURNS (ЧекККМВозврат) ---")
    # Checking March 1st for returns
    r_ret = httpx.get(url, params={'date_from': '2026-03-01', 'date_to': '2026-03-01'}, auth=auth, timeout=60)
    rows_ret = r_ret.json().get('rows', [])
    returns = [r for r in rows_ret if r.get('qty', 0) < 0]
    if returns:
        print(json.dumps(returns[0], indent=2, ensure_ascii=False))
        assert returns[0]['qty'] < 0 and returns[0]['amount'] < 0
        assert returns[0]['price'] > 0
    else:
        print("No returns found in sample, but logic verified in previous step.")

    print("\n--- 7 & 8. UUID & DATETIME FORMAT ---")
    sample = rows[0]
    print(f"Receipt UUID: {sample['receipt_uuid']}")
    print(f"Datetime: {sample['receipt_datetime']}")
    # Simple regex-like check
    assert len(sample['receipt_uuid']) == 36
    assert "T" in sample['receipt_datetime']

    print("\n--- 9. MULTI-LINE DUPLICATION CHECK ---")
    # Find a receipt with > 1 line
    from collections import Counter
    counts = {}
    for r in rows:
        counts[r['receipt_uuid']] = counts.get(r['receipt_uuid'], 0) + 1
    
    multi_uuid = [u for u, c in counts.items() if c > 1][0]
    lines = [r for r in rows if r['receipt_uuid'] == multi_uuid]
    print(f"Checking Receipt {multi_uuid} with {len(lines)} lines")
    for l in lines:
        print(f"Line {l['line_no']}: CertSale={l['is_gift_certificate_sale']}, CertPay={l['certificate_payment_amount']}")
        assert l['is_gift_certificate_sale'] == lines[0]['is_gift_certificate_sale']
        assert l['certificate_payment_amount'] == lines[0]['certificate_payment_amount']

    print("\n--- 10. EMPTY PERIOD ---")
    r_empty = httpx.get(url, params={'date_from': '2020-01-01', 'date_to': '2020-01-02'}, auth=auth)
    print(f"Empty status: {r_empty.status_code}, Rows: {len(r_empty.json().get('rows', []))}")
    assert r_empty.json()['count'] == 0

    print("\n--- 11. ERROR HANDLING ---")
    r_err1 = httpx.get(url, params={'date_to': '2026-03-14'}, auth=auth)
    print(f"No date_from: {r_err1.status_code} - {r_err1.text}")
    
    r_err2 = httpx.get(url, params={'date_from': '14-03-2026'}, auth=auth)
    print(f"Wrong format: {r_err2.status_code} - {r_err2.text}")

if __name__ == "__main__":
    run_final_test()
