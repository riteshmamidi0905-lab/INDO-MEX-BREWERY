#!/usr/bin/env python3
"""REAL INPUT INGESTION (Sprint 21). One tool for receipts, labels, packages, supplier quotes and raw professional responses. It preserves originals (read-only, SHA-256),
records only what was OBSERVED (anything else is NOT OBSERVED), refuses to turn a retail price, listing or snippet into a quote, and never invents a value.
  python3 tools/intake.py route [KIND]                       show the pipeline for an input kind (docs/company/data/input-router.csv)
  python3 tools/intake.py preserve KIND FILE... [--confirm-no-personal-data]   KIND: receipt | label | package | quote | professional_response | event (receipts, quotes and replies need the confirmation flag)
  python3 tools/intake.py record-purchase observed.json      rows of OBSERVED purchase fields (price = the receipt line TOTAL for the quantity bought, written 5.00; ISO dates) (Claude fills it from the images; the founder never types CSV)
  python3 tools/intake.py apply-prices observed.json         write RETAIL RECEIPT unit prices to food/costing/ingredients.csv (only rows that carry ingredient_id and a usable pack size)
  python3 tools/intake.py record-quote quote.json            vendor-issued quotes only; listings/snippets/retail prices are refused as quotes
  python3 tools/intake.py selftest
Originals go to evidence/<kind>/originals/ with evidence/<kind>/provenance.csv. Check images for personal data (card numbers, addresses) before committing."""
import csv, datetime, hashlib, json, os, shutil, stat, sys, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KINDS = ("receipt", "label", "package", "quote", "professional_response", "event")
NO = "NOT OBSERVED"
EXP = "ops/templates/expenses-receipts.csv"; ING = "food/costing/ingredients.csv"; RFQ = "ops/templates/vendor-rfq-comparison.csv"
ROUTER = "docs/company/data/input-router.csv"
D54 = ("PASS", "FAIL", "NOT CHECKED", NO)
QUOTE_DOCS = ("VENDOR QUOTE", "EMAIL QUOTE")           # the only document types that may be recorded as QUOTE
NOT_QUOTES = ("DIRECTORY LISTING", "SEARCH SNIPPET", "RETAIL SHELF PRICE", "RETAIL RECEIPT", "ASSUMPTION", "WEBSITE PRICE")
CONV = {("g", "kg"): 0.001, ("kg", "kg"): 1.0, ("ml", "l"): 0.001, ("l", "l"): 1.0, ("oz", "kg"): 0.0283495, ("lb", "kg"): 0.453592}
def p(*a): return os.path.join(ROOT, *a)
def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""): h.update(b)
    return h.hexdigest()
def now(): return datetime.date.today().isoformat()
def read_prov_at(base, kind):
    f = os.path.join(base, "evidence", kind, "provenance.csv"); return list(csv.DictReader(open(f, encoding="utf-8"))) if os.path.exists(f) else []
def prov_path(kind): return p("evidence", kind, "provenance.csv")
def read_prov(kind):
    f = prov_path(kind); return list(csv.DictReader(open(f, encoding="utf-8"))) if os.path.exists(f) else []
PERSONAL = ("receipt", "professional_response", "quote")
def write_prov(base, kind, rows):
    f = os.path.join(base, "evidence", kind, "provenance.csv")
    with open(f, "w", encoding="utf-8", newline="") as o:
        w = csv.DictWriter(o, fieldnames=["file_id", "original_name", "stored_as", "sha256", "bytes", "date_ingested", "kind", "data_source"], lineterminator="\n"); w.writeheader(); w.writerows(rows)
def preserve(kind, files, base=None, confirmed=False):
    base = base or ROOT
    if kind in PERSONAL and not confirmed: raise SystemExit(f"CHECK FOR PERSONAL DATA BEFORE COMMIT: {kind} files can carry card digits, loyalty or phone numbers, names and emails. Cover or crop them first (or confirm they are clean) and re-run with --confirm-no-personal-data.")
    out = []; rows = read_prov(kind) if base == ROOT else read_prov_at(base, kind)
    d = os.path.join(base, "evidence", kind, "originals"); os.makedirs(d, exist_ok=True)
    seen = {r["sha256"]: r["file_id"] for r in rows}
    for src in files:
        h = sha(src)
        if h in seen: out.append((src, seen[h], "DUPLICATE (already preserved)")); continue
        fid = f"{kind[:3].upper()}-{len(seen) + 1:04d}"; seen[h] = fid
        dest = os.path.join(d, f"{fid}_{os.path.basename(src)}")
        if os.path.exists(dest): raise SystemExit(f"{dest} already exists; refusing to overwrite an original")
        shutil.copy2(src, dest); os.chmod(dest, stat.S_IREAD)
        rows.append(dict(file_id=fid, original_name=os.path.basename(src), stored_as=os.path.relpath(dest, base), sha256=h, bytes=os.path.getsize(src), date_ingested=now(), kind=kind, data_source="real_input"))
        write_prov(base, kind, rows)   # provenance is written right after each copy (no orphaned originals)
        out.append((src, fid, "PRESERVED"))
    return out
import re as _re
def num(v, name):
    """strict amounts: 5 or 5.00 or 1,250.00 (thousands separators only); decimal commas ('5,00') are ambiguous and refused; no negatives, nan or inf"""
    if v in (None, "", NO): return NO
    t = str(v).strip()
    if _re.fullmatch(r"\d+(\.\d+)?", t): return t
    if _re.fullmatch(r"\d{1,3}(,\d{3})+(\.\d+)?", t): return t.replace(",", "")
    raise SystemExit(f"{name}: '{v}' is ambiguous or not a plain amount; write 5.00 (or {NO})")
def file_ids(kinds=KINDS):
    ids = set()
    for k in kinds: ids |= {r["file_id"] for r in read_prov(k)}
    return ids
def record_purchase(items, apply_dir=None):
    ids = file_ids(("receipt", "label", "package")); header = next(csv.reader(open(p(EXP), encoding="utf-8"))); existing = list(csv.DictReader(open(p(EXP), encoding="utf-8")))
    rows = []
    for n, it in enumerate(items, 1):
        ref = it.get("receipt_file_ref") or NO
        if ref != NO and ref not in ids: raise SystemExit(f"item {n}: receipt_file_ref {ref} was never preserved as a receipt, label or package (run preserve first)")
        dt = it.get("date") or NO
        if dt != NO and not _re.fullmatch(r"\d{4}-\d{2}-\d{2}", dt): raise SystemExit(f"item {n}: date '{dt}' must be ISO YYYY-MM-DD (or {NO})")
        key = (ref, it.get("item"), str(it.get("price")))
        if ref != NO and any((e["receipt_file_ref"], e["item"], e["amount_paid_as_on_receipt"]) == (key[0], key[1], key[2]) for e in existing): raise SystemExit(f"item {n}: this receipt line was already recorded (duplicate)")
        d54 = (it.get("d54_label_result") or NO).upper()
        if d54 not in D54: raise SystemExit(f"item {n}: d54_label_result must be one of {D54}")
        row = {h: NO for h in header}
        row.update(receipt_id=f"RCPT-{len(existing) + len(rows) + 1:04d}", date=it.get("date") or NO, vendor=it.get("store") or it.get("vendor") or NO, item=it.get("item") or NO, brand=it.get("brand") or NO,
                   package_size=it.get("package_size") or NO, quantity=num(it.get("quantity"), "quantity"), unit=it.get("unit") or NO, amount_paid_as_on_receipt=num(it.get("price"), "price"),
                   tax_if_shown=num(it.get("tax"), "tax"), lot_or_best_by=it.get("lot_or_best_by") or NO, d54_label_result=d54, category=it.get("category") or NO,
                   linked_product_or_run=it.get("intended_prototype") or NO, receipt_file_ref=ref, data_source=("real_receipt" if ref != NO else "UNVERIFIED_ENTRY"), notes=it.get("notes") or "")
        row["name_dependent_spend (Y/N)"] = it.get("name_dependent_spend") or "N"
        rows.append(row)
        if d54 == "FAIL": print(f"WARNING item {n} ({row['item']}): D-54 label FAIL: do not use this ingredient")
    with open(p(EXP), "a", encoding="utf-8", newline="") as o:
        w = csv.DictWriter(o, fieldnames=header, lineterminator="\n"); w.writerows(rows)
    return rows
def unit_price(it):
    """price per ingredient unit (kg or L) from price paid and pack size such as '500 g' or '1 L'; None when not derivable"""
    try:
        price = float(str(it.get("price")).replace(",", "")); size = _re.sub(r"(\d)([a-z])", r"\1 \2", str(it.get("package_size") or "").lower()).split()
        qty, u = float(size[0]), size[1]; qty *= float(it["quantity"])
        u = u.rstrip("."); ing_unit = "kg" if u in ("g", "kg", "oz", "lb") else "l" if u in ("ml", "l") else None
        if not ing_unit: return None
        return round(price / (qty * CONV[(u, ing_unit)]), 4), ing_unit
    except Exception: return None
def apply_prices(items):
    f = p(ING); rows = list(csv.DictReader(open(f, encoding="utf-8"))); H = list(rows[0].keys()); by = {r["ingredient_id"]: r for r in rows}; done = []
    for it in items:
        iid = it.get("ingredient_id")
        if not iid or iid not in by: continue
        if (it.get("d54_label_result") or "").upper() != "PASS": print(f"skip {iid}: D-54 label result is not PASS"); continue
        if (it.get("receipt_file_ref") or NO) not in file_ids(("receipt",)): print(f"skip {iid}: no preserved receipt"); continue
        if not it.get("quantity"): print(f"skip {iid}: quantity not observed (price is the receipt line TOTAL for the quantity bought; never assumed)"); continue
        if by[iid]["price_class"].strip().upper() in ("QUOTE", "ACTUAL"): print(f"skip {iid}: existing price is a {by[iid]['price_class']}; a retail receipt never overwrites it"); continue
        up = unit_price(it)
        if not up: print(f"skip {iid}: pack size/price not usable ({it.get('package_size')}, {it.get('price')})"); continue
        r = by[iid]
        if r["unit"].lower() != up[1]: print(f"skip {iid}: ingredient unit {r['unit']} vs derived {up[1]}"); continue
        r.update(price_per_unit=str(up[0]), supplier=it.get("store") or NO, price_source=f"retail receipt {it.get('receipt_file_ref') or NO}", price_date=it.get("date") or NO, price_class="RETAIL RECEIPT")
        done.append((iid, up))
    with open(f, "w", encoding="utf-8", newline="") as o:
        w = csv.DictWriter(o, fieldnames=H, lineterminator="\n"); w.writeheader(); w.writerows(rows)
    return done
def record_quote(items):
    ids = file_ids(("quote",)); header = next(csv.reader(open(p(RFQ), encoding="utf-8"))); n0 = len(list(csv.DictReader(open(p(RFQ), encoding="utf-8")))); out = []
    for n, q in enumerate(items, 1):
        dt = (q.get("doc_type") or "").upper()
        if dt in NOT_QUOTES or dt not in QUOTE_DOCS: raise SystemExit(f"quote {n}: doc_type '{dt}' is not a vendor-issued quote ({', '.join(QUOTE_DOCS)}); a listing, snippet, retail or assumed price is never recorded as a QUOTE")
        ref = q.get("source_doc_file_id") or NO
        if ref == NO or ref not in ids: raise SystemExit(f"quote {n}: the original must be preserved as KIND quote first (source_doc_file_id); a receipt or any other kind cannot be a quote source")
        missing = [k for k in ("vendor", "price", "pack", "unit", "valid_until", "date_requested") if not q.get(k)]
        row = {h: NO for h in header}
        row.update(rfq_id=f"RFQ-{n0 + len(out) + 1:04d}", category=q.get("category") or NO, vendor=q.get("vendor") or NO, date_sent=q.get("date_requested") or NO, contact_authorized_by_founder=q.get("contact_authorized_by_founder") or NO,
                   moq=q.get("moq") or NO, unit_price_usd=num(q.get("price"), "price"), lead_time_weeks=q.get("lead_time") or NO, shipping=q.get("delivery") or NO, payment_terms=q.get("payment_terms") or NO,
                   quote_valid_until=q.get("valid_until") or NO, evidence_tier=("QUOTE" if not missing else "QUOTE-INCOMPLETE (missing: " + ", ".join(missing) + ")"),
                   notes=f"product {q.get('product') or NO}; pack {q.get('pack') or NO}; unit {q.get('unit') or NO}; spec compliance {q.get('spec_compliance') or NO}; D-54 concerns {q.get('d54_concerns') or NO}; confidence {q.get('confidence') or NO}; source {ref}")
        out.append(row)
    with open(p(RFQ), "a", encoding="utf-8", newline="") as o:
        w = csv.DictWriter(o, fieldnames=header, lineterminator="\n"); w.writerows(out)
    return out
def route(kind=None):
    rows = list(csv.DictReader(open(p(ROUTER), encoding="utf-8")))
    for r in rows:
        if kind and kind.lower() not in r["input_kind"].lower(): continue
        print(f"\n== {r['input_kind']} ==\n  preserve: {r['preserve_original_in']}\n  record:   {r['record_in']}\n  command:  {r['command']}\n  Claude:   {r['claude_does']}\n  never:    {r['never_do']}")
def selftest():
    global ROOT
    old = ROOT
    def refused(fn):
        try: fn()
        except SystemExit: return True
        return False
    with tempfile.TemporaryDirectory() as d:
        ROOT = d
        for sub in ("ops/templates", "food/costing"): os.makedirs(os.path.join(d, sub))
        for src in (EXP, RFQ, ING): shutil.copy(os.path.join(old, src), os.path.join(d, src))
        img = os.path.join(d, "r.jpg"); open(img, "wb").write(b"fake receipt bytes")
        qdoc = os.path.join(d, "q.pdf"); open(qdoc, "wb").write(b"fake vendor quote")
        assert refused(lambda: preserve("receipt", [img], base=d))                      # personal-data confirmation required
        out = preserve("receipt", [img], base=d, confirmed=True); assert out[0][2] == "PRESERVED" and out[0][1] == "REC-0001"
        mode = os.stat(os.path.join(d, "evidence", "receipt", "originals", "REC-0001_r.jpg")).st_mode
        assert os.path.exists(os.path.join(d, "evidence", "receipt", "provenance.csv")) and not (mode & stat.S_IWUSR)   # read-only (mode check: root ignores access())
        assert preserve("receipt", [img], base=d, confirmed=True) == [(img, "REC-0001", "DUPLICATE (already preserved)")]
        qout = preserve("quote", [qdoc], base=d, confirmed=True); assert qout[0][1] == "QUO-0001"
        it = dict(store="TEST STORE", date="2026-01-01", item="TEST paneer", package_size="400 g", quantity="1", price="5.00", d54_label_result="PASS", receipt_file_ref="REC-0001", ingredient_id="i-paneer", unit="pack")
        assert unit_price(it) == (12.5, "kg") and unit_price(dict(it, package_size="16 oz", price="4.00"))[1] == "kg" and unit_price(dict(it, package_size="500g", price="2.00")) == (4.0, "kg")
        rows = record_purchase([it]); assert rows[0]["brand"] == NO and rows[0]["lot_or_best_by"] == NO and rows[0]["data_source"] == "real_receipt"   # never invented
        assert refused(lambda: record_purchase([it]))                                  # duplicate receipt line
        assert refused(lambda: record_purchase([dict(item="x", d54_label_result="PASS", receipt_file_ref="REC-9999")]))
        assert refused(lambda: record_purchase([dict(item="x", price="abc", d54_label_result="PASS")]))
        assert refused(lambda: record_purchase([dict(item="x", price="5,00", d54_label_result="PASS")]))   # decimal comma is ambiguous
        assert refused(lambda: record_purchase([dict(item="x", price="5.00", date="2026-1-1", d54_label_result="PASS")]))
        assert record_purchase([dict(item="y", price="1,250.50", d54_label_result="NOT CHECKED")])[0]["data_source"] == "UNVERIFIED_ENTRY"   # no receipt, flagged
        assert apply_prices([it]) == [("i-paneer", (12.5, "kg"))]
        assert apply_prices([dict(it, d54_label_result="FAIL")]) == [] and apply_prices([dict(it, receipt_file_ref="NOT OBSERVED")]) == [] and apply_prices([{k: v for k, v in it.items() if k != "quantity"}]) == []
        for bad in ("DIRECTORY LISTING", "SEARCH SNIPPET", "RETAIL SHELF PRICE"):
            assert refused(lambda: record_quote([dict(doc_type=bad, source_doc_file_id="QUO-0001")]))
        assert refused(lambda: record_quote([dict(doc_type="VENDOR QUOTE", source_doc_file_id="REC-0001")]))   # a receipt cannot be a quote source
        assert refused(lambda: record_quote([dict(doc_type="VENDOR QUOTE", source_doc_file_id=NO)]))
        good = record_quote([dict(doc_type="VENDOR QUOTE", source_doc_file_id="QUO-0001", vendor="TEST", price="10.00", pack="1 kg", unit="kg", valid_until="2026-12-31", date_requested="2026-01-01")])
        assert good[0]["evidence_tier"] == "QUOTE"
        part = record_quote([dict(doc_type="EMAIL QUOTE", source_doc_file_id="QUO-0001", vendor="TEST", price="10.00")])
        assert part[0]["evidence_tier"].startswith("QUOTE-INCOMPLETE")
    ROOT = old
    print("selftest ok: preserve (confirmation, read-only, SHA-256, dedupe), NOT OBSERVED defaults, strict amounts, duplicates, D-54/receipt/quantity guards on prices, non-quotes and wrong-kind sources refused, complete vs incomplete quotes")
if __name__ == "__main__":
    a = sys.argv[1:]
    if not a: print(__doc__)
    elif a[0] == "selftest": selftest()
    elif a[0] == "route": route(a[1] if len(a) > 1 else None)
    elif a[0] == "preserve" and len(a) > 2 and a[1] in KINDS:
        conf = "--confirm-no-personal-data" in a; files = [x for x in a[2:] if x != "--confirm-no-personal-data"]
        for src, fid, st in preserve(a[1], files, confirmed=conf): print(f"{st}: {src} -> {fid}")
    elif a[0] == "record-purchase": print(len(record_purchase(json.load(open(a[1])))), "purchase rows recorded")
    elif a[0] == "apply-prices": print(apply_prices(json.load(open(a[1]))))
    elif a[0] == "record-quote": print(len(record_quote(json.load(open(a[1])))), "quotes recorded")
    else: print(__doc__)
