"""Industry configuration for the business-launch workspace. ONE platform serves every industry; what differs is DATA and WORDING, kept here and nowhere else: how a project's physical needs are derived (a recipe bill of materials
for a venue that cooks, an explicit equipment/service requirements list for a studio), what the product and demand are called, and the labels of the start-up cost categories. Nothing here changes authorisation, audit,
the workflow engine, the database or any calculation: a profile only selects a needs source and supplies labels. An unknown industry falls back to 'generic' (requirements only). Pure; no I/O."""

CAPEX_BASE = {"startup_capex_cents": "Capital expenditure (lump sum)", "capex_buildout_cents": "Build-out and construction", "capex_equipment_cents": "Equipment", "capex_furniture_cents": "Furniture and fixtures",
              "capex_technology_cents": "Technology and systems", "capex_other_cents": "Other capital items"}
PREOPEN_BASE = {"preopen_licences_permits_cents": "Licences and permits", "preopen_deposits_cents": "Deposits", "preopen_professional_fees_cents": "Professional fees", "preopen_training_cents": "Pre-opening training and payroll",
                "preopen_launch_marketing_cents": "Launch marketing", "preopen_other_cents": "Other pre-opening costs"}

PROFILES = {
    "hospitality": dict(label="Hospitality", needs=["recipes", "requirements"], product_term="menu item", product_term_plural="menu items", demand_term="guest orders", demand_unit="orders", need_term="ingredient", need_term_plural="ingredients",
                        capex_labels=dict(CAPEX_BASE, capex_buildout_cents="Build-out and construction", capex_equipment_cents="Kitchen, brewing and service equipment", capex_technology_cents="Technology and point of sale"),
                        preopen_labels=dict(PREOPEN_BASE, preopen_licences_permits_cents="Licences and permits (alcohol, food, building)"), inventory_term="opening inventory (ingredients)",
                        requirement_examples=["Walk-in cooler (equipment)", "Linen service (service)", "Takeout containers (consumable)"], supplier_focus="food, beverage ingredients, kitchen equipment and distribution"),
    "fitness": dict(label="Fitness studio", needs=["requirements"], product_term="membership or class pack", product_term_plural="memberships and class packs", demand_term="new sales", demand_unit="sales", need_term="item", need_term_plural="items",
                    capex_labels=dict(CAPEX_BASE, capex_buildout_cents="Studio fit-out and flooring", capex_equipment_cents="Studio equipment", capex_furniture_cents="Reception, lockers and furniture", capex_technology_cents="Booking, access and sound systems"),
                    preopen_labels=dict(PREOPEN_BASE, preopen_licences_permits_cents="Licences, permits and insurance set-up"), inventory_term="opening supplies (towels, cleaning)",
                    requirement_examples=["Spin bikes (equipment)", "Rubber flooring (equipment)", "Towel service (service)"], supplier_focus="fitness equipment, flooring, laundry and facility services"),
    "generic": dict(label="Other business", needs=["requirements"], product_term="product or service", product_term_plural="products and services", demand_term="orders", demand_unit="orders", need_term="item", need_term_plural="items",
                    capex_labels=dict(CAPEX_BASE), preopen_labels=dict(PREOPEN_BASE), inventory_term="opening inventory", requirement_examples=["Equipment", "Recurring service", "Consumable supply"], supplier_focus="equipment, services and supplies"),
}
ALIASES = {"hospitality": ("hospitality", "restaurant", "food and beverage", "brewery", "bar", "cafe"), "fitness": ("fitness", "gym", "studio", "wellness", "yoga")}


def key_for(industry):
    t = (industry or "").strip().lower()
    for k, words in ALIASES.items():
        if any(w in t for w in words):
            return k
    return "generic"


def profile_for(industry):
    k = key_for(industry)
    return dict(PROFILES[k], key=k)


def uses_recipes(industry):
    return "recipes" in PROFILES[key_for(industry)]["needs"]
