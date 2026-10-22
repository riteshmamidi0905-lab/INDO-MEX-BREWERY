"""Brewing arithmetic for the NASHA pilot-batch FORMULATION BRIEFS (planning support; nothing has been brewed or measured).

Every function is a published, widely used approximation (labelled below). The NASHA inputs are targets and assumptions, never results: gravities,
efficiency and hop alpha acid are placeholders until a licensed brewer sets them and the first pilot batch is MEASURED. Outputs are expected values from
the formulas, not laboratory values, and must never be presented as measured alcohol content.
"""
import math
from dataclasses import dataclass

LB_PER_KG = 2.20462
GAL_PER_L = 0.264172
# Typical extract potentials, points per pound per US gallon (ppg), as listed on maltster spec sheets and in standard references. Real lots vary +/- 2-3 ppg.
PPG = {"pilsner malt": 37, "pale 2-row": 37, "wheat malt": 38, "flaked oats": 33, "flaked wheat": 35, "dextrin malt": 33, "Munich malt": 35, "sucrose": 46}


def abv_simple(og, fg):
    """ABV ~ (OG - FG) x 131.25 : the common homebrew/brewery approximation. Accurate to roughly +/-0.2 ABV points for ordinary beers; measure the real beer."""
    return (og - fg) * 131.25


def abv_alt(og, fg):
    """Alternate (higher-gravity) formula: ABV = 76.08 (OG-FG)/(1.775-OG) x FG/0.794."""
    return 76.08 * (og - fg) / (1.775 - og) * (fg / 0.794)


def apparent_attenuation(og, fg):
    return (og - fg) / (og - 1.0)


def plato(sg):
    """Degrees Plato from specific gravity (standard polynomial)."""
    return -616.868 + 1111.14 * sg - 630.272 * sg ** 2 + 135.997 * sg ** 3


def og_from_grist(grist_kg: dict, batch_l: float, efficiency: float):
    """OG expected from a grist (kg per malt), batch volume into the fermenter (L) and brewhouse efficiency (0-1). Points = sum(lb x ppg) x eff / gallons."""
    gal = batch_l * GAL_PER_L
    pts = sum(kg * LB_PER_KG * PPG[m] for m, kg in grist_kg.items()) * efficiency / gal
    return 1.0 + pts / 1000.0


def grist_for_og(target_og, percents: dict, batch_l, efficiency):
    """Total grist mass (kg) and per-malt masses that reach target_og for the given percentage bill (percents sum to 100)."""
    assert abs(sum(percents.values()) - 100) < 1e-9
    gal = batch_l * GAL_PER_L
    need_pts = (target_og - 1.0) * 1000 * gal
    avg_ppg = sum(PPG[m] * p / 100 for m, p in percents.items())
    total_lb = need_pts / (avg_ppg * efficiency)
    total_kg = total_lb / LB_PER_KG
    return total_kg, {m: round(total_kg * p / 100, 2) for m, p in percents.items()}


def tinseth_ibu(grams, alpha_pct, batch_l, boil_min, og_boil):
    """Tinseth (1997) IBU estimate for a boil addition. Whirlpool/hop-stand and dry-hop contributions are NOT modelled (they are handled as brewer decisions)."""
    bigness = 1.65 * 0.000125 ** (og_boil - 1.0)
    boil = (1 - math.exp(-0.04 * boil_min)) / 4.15
    mg_per_l = alpha_pct / 100.0 * grams * 1000.0 / batch_l
    return bigness * boil * mg_per_l


def srm_morey(lb_malt_lovibond: list, batch_gal):
    """Morey colour estimate from [(pounds, lovibond)] and batch gallons."""
    mcu = sum(lb * lov for lb, lov in lb_malt_lovibond) / batch_gal
    return 1.4922 * mcu ** 0.6859


def fruit_gravity_points(puree_kg, brix, batch_l):
    """Gravity contribution (SG points) from fruit sugar, treating the sugar as fully fermentable sucrose-equivalent (46 ppg). Fruit solids that are not sugar are ignored."""
    sugar_lb = puree_kg * brix / 100.0 * LB_PER_KG
    return sugar_lb * PPG["sucrose"] / (batch_l * GAL_PER_L)


def base_og_for_target_abv(target_abv, fg, fruit_points):
    """Base-wort OG that, after fruit sugar is added and fermented to FG, gives target_abv by the simple formula."""
    og_total = fg + target_abv / 131.25
    return og_total - fruit_points / 1000.0


def co2_psi(volumes, temp_c):
    """Equilibrium keg/tank gauge pressure (psi) for a CO2 volume target at a beer temperature (standard Henry's-law fit used in brewing references)."""
    t = temp_c * 9 / 5 + 32
    return -16.6999 - 0.0101059 * t + 0.00116512 * t * t + 0.173354 * t * volumes + 4.24267 * volumes - 0.0684226 * volumes * volumes


@dataclass(frozen=True)
class Formulation:
    name: str
    target_abv: float
    og: float
    fg: float

    def expected_abv(self):
        return abv_simple(self.og, self.fg)

    def within(self, tol=0.1):
        return abs(self.expected_abv() - self.target_abv) <= tol
