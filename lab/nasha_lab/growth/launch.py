"""Business-launch workspace service methods (mixed into GrowthService): projects, assumptions, milestones, research findings, suppliers and their published products, shortlists and financial scenarios.
Every write goes through GrowthService._write (authorised by role, audited in the same transaction, guarded by the database's audit constraint). Supplier data is deliberately conservative: a supplier is
only 'verified_public' with an official website, a source URL and a verification date; prices exist only when published (price_class NONE_PUBLISHED otherwise); contact details cannot be stored (schema CHECK)."""
from datetime import date

from psycopg.types.json import Jsonb

from . import financials as FIN, supplier_intel as SI

FRESH_DAYS, STALE_DAYS = 90, 180


def freshness(verified_on, as_of=None, status=None):
    """Data freshness of a supplier record: fresh (<=90 days), aging (<=180), stale (older) or unverified (never)."""
    if status == "synthetic_fixture":
        return "synthetic (not applicable)"
    if verified_on is None:
        return "unverified"
    d = ((as_of or date.today()) - verified_on).days
    return "fresh" if d <= FRESH_DAYS else "aging" if d <= STALE_DAYS else "stale"


class LaunchMixin:
    # ------------------------------------------------------------ projects, assumptions, milestones, findings
    def create_project(self, name, industry, location, concept, budget_cents, launch_target=None, basis="synthetic"):
        i = self._id("proj")
        return self._write("project.create", "launch_projects", lambda: self.con.execute(
            "INSERT INTO launch_projects (tenant_id,id,name,industry,location,concept,budget_cents,launch_target,basis,created_by) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id",
            (self.tenant, i, name, industry, location, concept, budget_cents, launch_target, basis, self.user)).fetchone()[0])

    def set_project_stage(self, project_id, stage):
        def go():
            if not self.con.execute("UPDATE launch_projects SET stage=%s WHERE tenant_id=%s AND id=%s RETURNING id", (stage, self.tenant, project_id)).fetchone():
                raise self.Blocked("no such project in this tenant")
            return project_id
        return self._write("project.stage", "launch_projects", go)

    def set_assumption(self, project_id, key, label, value, unit, basis, note=None):
        """Create or replace one stated assumption (founder input, synthetic assumption or public reference)."""
        def go():
            r = self.con.execute("SELECT id FROM project_assumptions WHERE tenant_id=%s AND project_id=%s AND key=%s FOR UPDATE", (self.tenant, project_id, key)).fetchone()
            if r:
                self.con.execute("UPDATE project_assumptions SET label=%s, value=%s, unit=%s, basis=%s, note=%s WHERE tenant_id=%s AND id=%s", (label, value, unit, basis, note, self.tenant, r[0]))
                return r[0]
            i = self._id("asm")
            self.con.execute("INSERT INTO project_assumptions (tenant_id,id,project_id,key,label,value,unit,basis,note,created_by) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)", (self.tenant, i, project_id, key, label, value, unit, basis, note, self.user))
            return i
        return self._write("project.assumption", "project_assumptions", go)

    def add_milestone(self, project_id, title, phase, due=None, note=None):
        i = self._id("ms")
        return self._write("milestone.write", "project_milestones", lambda: self.con.execute(
            "INSERT INTO project_milestones (tenant_id,id,project_id,title,phase,due,note,created_by) VALUES (%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id", (self.tenant, i, project_id, title, phase, due, note, self.user)).fetchone()[0])

    def set_milestone_status(self, milestone_id, status):
        def go():
            if not self.con.execute("UPDATE project_milestones SET status=%s WHERE tenant_id=%s AND id=%s RETURNING id", (status, self.tenant, milestone_id)).fetchone():
                raise self.Blocked("no such milestone in this tenant")
            return milestone_id
        return self._write("milestone.write", "project_milestones", go)

    def add_finding(self, project_id, topic, finding, source_kind, confidence, limitation, source_url=None, retrieved_on=None):
        i = self._id("find")
        return self._write("finding.add", "research_findings", lambda: self.con.execute(
            "INSERT INTO research_findings (tenant_id,id,project_id,topic,finding,source_kind,source_url,retrieved_on,confidence,limitation,created_by) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id",
            (self.tenant, i, project_id, topic, finding, source_kind, source_url, retrieved_on, confidence, limitation, self.user)).fetchone()[0])

    # ------------------------------------------------------------ suppliers
    def add_supplier(self, name, category, service_area, verification_status, source_kind, website_url=None, contact_channel="none recorded", verified_on=None, source_url=None, notes=None, confirm_distinct=False):
        """Refuses a record that looks like an existing supplier (same official domain, or a near-identical name) unless the caller states it is distinct. The rule is SI.duplicate_score; a person decides."""
        if not confirm_distinct:
            self._authorize("read")
            cand = dict(name=name, website_url=website_url)
            for r in self.con.execute("SELECT id, name, website_url FROM suppliers WHERE tenant_id=%s", (self.tenant,)).fetchall():
                score, why = SI.duplicate_score(cand, dict(name=r[1], website_url=r[2]))
                if score >= SI.DUPLICATE_THRESHOLD:
                    self._audit("supplier.add", "suppliers", None, "deny", {"why": f"possible duplicate of {r[1]} ({r[0]}): {'; '.join(why)}"})
                    raise self.Blocked(f"possible duplicate of existing supplier '{r[1]}' ({'; '.join(why)}); confirm it is distinct to add it anyway")
        i = self._id("sup")
        return self._write("supplier.add", "suppliers", lambda: self.con.execute(
            "INSERT INTO suppliers (tenant_id,id,name,category,service_area,website_url,contact_channel,verification_status,verified_on,source_kind,source_url,notes,created_by) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id",
            (self.tenant, i, name, category, service_area, website_url, contact_channel, verification_status, verified_on, source_kind, source_url, notes, self.user)).fetchone()[0])

    def add_supplier_source(self, supplier_id, kind, url, claim, access, observed_on):
        """A dated public source for a supplier fact. `access` says whether the page was read or only a search snippet was seen; neither contacts anyone."""
        i = self._id("ssrc")
        return self._write("supplier.add", "supplier_sources", lambda: self.con.execute(
            "INSERT INTO supplier_sources (tenant_id,id,supplier_id,kind,url,claim,access,observed_on,created_by) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id",
            (self.tenant, i, supplier_id, kind, url, claim, access, observed_on, self.user)).fetchone()[0])

    def add_supplier_product(self, supplier_id, name, unit, price_class, limitation, unit_price_cents=None, ingredient_ref=None, pack_qty=None, lead_days=None, min_order_cents=None, valid_from=None, valid_to=None, source_url=None):
        i = self._id("sprod")
        return self._write("supplier.add", "supplier_products", lambda: self.con.execute(
            "INSERT INTO supplier_products (tenant_id,id,supplier_id,name,ingredient_ref,unit,unit_price_cents,pack_qty,lead_days,min_order_cents,price_class,valid_from,valid_to,source_url,limitation,created_by) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id",
            (self.tenant, i, supplier_id, name, ingredient_ref, unit, unit_price_cents, pack_qty, lead_days, min_order_cents, price_class, valid_from, valid_to, source_url, limitation, self.user)).fetchone()[0])

    def set_project_supplier(self, project_id, supplier_id, status, note=None):
        def go():
            r = self.con.execute("SELECT id FROM project_suppliers WHERE tenant_id=%s AND project_id=%s AND supplier_id=%s FOR UPDATE", (self.tenant, project_id, supplier_id)).fetchone()
            if r:
                self.con.execute("UPDATE project_suppliers SET status=%s, note=%s WHERE tenant_id=%s AND id=%s", (status, note, self.tenant, r[0])); return r[0]
            i = self._id("psup")
            self.con.execute("INSERT INTO project_suppliers (tenant_id,id,project_id,supplier_id,status,note,created_by) VALUES (%s,%s,%s,%s,%s,%s,%s)", (self.tenant, i, project_id, supplier_id, status, note, self.user))
            return i
        return self._write("supplier.shortlist", "project_suppliers", go)

    def supplier_directory(self, as_of=None, project_id=None):
        """Suppliers with their published products, verification status and computed data freshness. Read-only."""
        self._authorize("read")
        rows = self.con.execute("SELECT s.id, s.name, s.category, s.service_area, s.website_url, s.contact_channel, s.verification_status, s.verified_on, s.source_kind, s.source_url, s.notes, ps.status "
                                "FROM suppliers s LEFT JOIN project_suppliers ps ON ps.tenant_id=s.tenant_id AND ps.supplier_id=s.id AND ps.project_id IS NOT DISTINCT FROM %s WHERE s.tenant_id=%s ORDER BY s.verification_status, s.name", (project_id, self.tenant)).fetchall()
        prods = {}
        for r in self.con.execute("SELECT supplier_id, name, ingredient_ref, unit, unit_price_cents, pack_qty, lead_days, min_order_cents, price_class, valid_from, valid_to, source_url, limitation FROM supplier_products WHERE tenant_id=%s ORDER BY name", (self.tenant,)).fetchall():
            prods.setdefault(r[0], []).append(dict(zip(("name", "ingredient_ref", "unit", "unit_price_cents", "pack_qty", "lead_days", "min_order_cents", "price_class", "valid_from", "valid_to", "source_url", "limitation"), r[1:])))
        srcs = {}
        for r in self.con.execute("SELECT supplier_id, kind, url, claim, access, observed_on FROM supplier_sources WHERE tenant_id=%s ORDER BY observed_on, kind, url", (self.tenant,)).fetchall():
            srcs.setdefault(r[0], []).append(dict(zip(("kind", "url", "claim", "access", "observed_on"), r[1:])))
        out = []
        for r in rows:
            d = dict(zip(("id", "name", "category", "service_area", "website_url", "contact_channel", "verification_status", "verified_on", "source_kind", "source_url", "notes", "shortlist_status"), r))
            d["freshness"] = freshness(d["verified_on"], as_of, d["verification_status"])
            d["products"] = prods.get(d["id"], [])
            d["sources"] = srcs.get(d["id"], [])
            d["priced_products"] = sum(1 for p in d["products"] if p["price_class"] != "NONE_PUBLISHED")
            out.append(d)
        return out

    def supplier_intelligence(self, project_id=None, as_of=None):
        """Supplier cards (information category, rule-based class, service-area match to the project's location), candidate duplicates, and the quote matrix grouped by price category. Read-only, derived on demand
        from stored records; nothing here is stored, so it cannot drift from them."""
        self._authorize("read")
        directory = self.supplier_directory(as_of, project_id)
        loc = None
        if project_id:
            r = self.con.execute("SELECT location FROM launch_projects WHERE tenant_id=%s AND id=%s", (self.tenant, project_id)).fetchone()
            loc = r[0] if r else None
        asof = as_of or date.today()
        cards = [dict(SI.supplier_card(s, loc, asof), shortlist_status=s["shortlist_status"], category=s["category"], service_area=s["service_area"]) for s in directory]
        return dict(project_location=loc, cards=cards, duplicates=SI.find_duplicates(directory), quotes=SI.quote_matrix(directory, asof),
                    information_categories=SI.INFO_LABEL, price_categories=SI.PRICE_LABEL, duplicate_threshold=SI.DUPLICATE_THRESHOLD)

    # ------------------------------------------------------------ project overview and financial scenarios
    def list_projects(self):
        self._authorize("read")
        return [dict(zip(("id", "name", "industry", "location", "concept", "budget_cents", "launch_target", "stage", "basis"), r))
                for r in self.con.execute("SELECT id, name, industry, location, concept, budget_cents, launch_target, stage, basis FROM launch_projects WHERE tenant_id=%s ORDER BY created_at, id", (self.tenant,)).fetchall()]

    def project_overview(self, project_id):
        self._authorize("read")
        p = next((x for x in self.list_projects() if x["id"] == project_id), None)
        if not p:
            return None
        q = lambda sql: self.con.execute(sql, (self.tenant, project_id)).fetchall()
        p["assumptions"] = [dict(zip(("key", "label", "value", "unit", "basis", "note"), (r[0], r[1], float(r[2]), r[3], r[4], r[5]))) for r in q("SELECT key, label, value, unit, basis, note FROM project_assumptions WHERE tenant_id=%s AND project_id=%s ORDER BY key")]
        p["milestones"] = [dict(zip(("id", "title", "phase", "due", "status", "note"), r)) for r in q("SELECT id, title, phase, due, status, note FROM project_milestones WHERE tenant_id=%s AND project_id=%s ORDER BY due NULLS LAST, created_at")]
        p["findings"] = [dict(zip(("id", "topic", "finding", "source_kind", "source_url", "retrieved_on", "confidence", "limitation"), (r[0], r[1], r[2], r[3], r[4], r[5], float(r[6]), r[7])))
                         for r in q("SELECT id, topic, finding, source_kind, source_url, retrieved_on, confidence, limitation FROM research_findings WHERE tenant_id=%s AND project_id=%s ORDER BY topic, created_at")]
        p["shortlist"] = [dict(zip(("supplier_id", "name", "status", "note"), r)) for r in q("SELECT ps.supplier_id, s.name, ps.status, ps.note FROM project_suppliers ps JOIN suppliers s ON s.tenant_id=ps.tenant_id AND s.id=ps.supplier_id WHERE ps.tenant_id=%s AND ps.project_id=%s ORDER BY ps.status, s.name")]
        p["scenarios"] = [dict(zip(("id", "name", "inputs_hash", "created_at"), r)) for r in q("SELECT id, name, inputs_hash, created_at FROM financial_scenarios WHERE tenant_id=%s AND project_id=%s ORDER BY created_at, id")]
        return p

    def product_economics(self):
        """Current price and unit cost of every product, from the stored products and prices."""
        self._authorize("read")
        return [dict(id=r[0], name=r[1], price_cents=int(r[2]), unit_cost_cents=float(r[3]), cost_basis=r[4], price_basis=r[5]) for r in self.con.execute(
            "SELECT p.id, p.name, pr.amount_cents, p.unit_cost_cents, p.cost_basis, pr.basis FROM products p JOIN prices pr ON pr.tenant_id=p.tenant_id AND pr.product_id=p.id AND pr.status='current' WHERE p.tenant_id=%s AND p.unit_cost_cents IS NOT NULL ORDER BY p.name", (self.tenant,)).fetchall()]

    def scenario_inputs(self, project_id, overrides=None, product_ids=None):
        self._authorize("read")
        ov = self.project_overview(project_id)
        if ov is None:
            return None
        prods = [p for p in self.product_economics() if not product_ids or p["id"] in product_ids]
        return FIN.build_inputs(prods, {a["key"]: a["value"] for a in ov["assumptions"]}, overrides, ov["budget_cents"])

    def preview_scenario(self, project_id, overrides=None, product_ids=None):
        """Compute (do not save) a scenario from stored data: nothing is written, nothing is audited."""
        inp = self.scenario_inputs(project_id, overrides, product_ids)
        return None if inp is None else dict(inputs=inp, **FIN.run(inp))

    def save_scenario(self, project_id, name, overrides=None, product_ids=None):
        inp = self.scenario_inputs(project_id, overrides, product_ids)
        if inp is None:
            raise self.Blocked("no such project in this tenant")
        res = FIN.run(inp)
        i = self._id("scn")
        return self._write("scenario.save", "financial_scenarios", lambda: self.con.execute(
            "INSERT INTO financial_scenarios (tenant_id,id,project_id,name,inputs,inputs_hash,results,created_by) VALUES (%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id",
            (self.tenant, i, project_id, name, Jsonb(inp), res["inputs_hash"], Jsonb(dict(results=res["results"], sensitivity=res["sensitivity"])), self.user)).fetchone()[0])

    def get_scenario(self, scenario_id):
        self._authorize("read")
        r = self.con.execute("SELECT id, project_id, name, inputs, inputs_hash, results, created_at FROM financial_scenarios WHERE tenant_id=%s AND id=%s", (self.tenant, scenario_id)).fetchone()
        return None if not r else dict(zip(("id", "project_id", "name", "inputs", "inputs_hash", "results", "created_at"), r))

    # ------------------------------------------------------------ governed procurement recommendation (state machine rows are written by the workflow's own store; only the final, audited step is here)
    def record_procurement(self, run_id, approval_id, approved_by):
        """The one consequential write of the launch workflow: mark an APPROVED procurement recommendation as recorded. Authorised as procurement.record, audited with the approval that allowed it; the database refuses
        the EXECUTED state without audit evidence from this same transaction. Idempotent per run. It records a recommendation: it places no order and contacts no supplier."""
        def go():
            r = self.con.execute("SELECT state FROM procurement_recommendations WHERE tenant_id=%s AND id=%s FOR UPDATE", (self.tenant, run_id)).fetchone()
            if not r:
                raise self.Blocked("no such recommendation in this tenant")
            if r[0] == "EXECUTED":
                return run_id
            if r[0] != "APPROVED":
                raise self.Blocked(f"recommendation is {r[0]}, not APPROVED")
            self.con.execute("UPDATE procurement_recommendations SET state='EXECUTED', approval_id=%s, decided_by=%s WHERE tenant_id=%s AND id=%s", (approval_id, approved_by, self.tenant, run_id))
            return run_id, None, {"approval": approval_id, "approved_by": approved_by}
        return self._write("procurement.record", "procurement_recommendations", go)

    # ------------------------------------------------------------ marketing: offer economics from stored prices and costs
    def offer_economics(self):
        """Every stored offer with its product's current price and unit cost: margin before and after the discount and the volume uplift needed to hold gross profit (pricing engine). Read-only."""
        from . import pricing as GP
        self._authorize("read")
        out = []
        for oid, name, pname, disc, starts, ends, status, price, cost in self.con.execute(
                "SELECT o.id, o.name, p.name, o.discount_pct, o.starts, o.ends, o.status, pr.amount_cents, p.unit_cost_cents FROM offers o JOIN products p ON p.tenant_id=o.tenant_id AND p.id=o.product_id "
                "JOIN prices pr ON pr.tenant_id=p.tenant_id AND pr.product_id=p.id AND pr.status='current' WHERE o.tenant_id=%s ORDER BY o.starts, o.name", (self.tenant,)).fetchall():
            if cost is None:
                continue
            a = GP.discount_analysis(int(price), float(cost), float(disc))
            out.append(dict(id=oid, name=name, product=pname, discount_pct=float(disc), starts=starts, ends=ends, status=status, price_cents=int(price), unit_cost_cents=float(cost), margin_before=round(a["margin_before"], 4),
                            margin_after=None if a["margin_after"] is None else round(a["margin_after"], 4), breakeven_volume_uplift=None if a["breakeven_volume_uplift"] is None else round(a["breakeven_volume_uplift"], 4), assumption=a["assumption"]))
        return out

    def campaigns(self):
        self._authorize("read")
        return [dict(zip(("id", "name", "status", "offer", "segment"), r)) for r in self.con.execute(
            "SELECT c.id, c.name, c.status, o.name, s.name FROM campaigns c LEFT JOIN offers o ON o.tenant_id=c.tenant_id AND o.id=c.offer_id LEFT JOIN segments s ON s.tenant_id=c.tenant_id AND s.id=c.segment_id WHERE c.tenant_id=%s ORDER BY c.created_at", (self.tenant,)).fetchall()]
