# Operational Flow Diagram (text, conceptual, not to scale)

> HISTORICAL (Track A concept): not evidence and not scoped to the Core 5 development program.

```
                              ROAD / ARRIVAL (north or south edge: site-dependent)
                                         │
                        ┌────────────────┴────────────────┐
                        │  PARKING + RIDESHARE + BIKES     │
                        └───────┬─────────────────┬────────┘
                                │ guests          │ service road (separate)
                        ┌───────▼────────┐        │
                        │ GATE / THRESHOLD│       │
                        │ (shaded, lit)   │       │
                        └───────┬─────────┘       │
                                │                 │
   ┌────────────────────────────▼───────────────┐ │
   │               TANK HALL (glazed)           │ │
   │  ┌───────────────── TANK CLOISTER ───────┐ │ │
   │  │  [FV1][FV2][FV3][FV4][FV5][FV6]       │ │ │
   │  │  ═══ glass wall (guests) ═══════════  │ │ │
   │  │  BREW DECK: kettle · mash tun · mill  │ │ │
   │  └───────────────────────────────────────┘ │ │
   │  Mezzanine gallery (guests) ↑elevator/stairs│ │
   │                                             │ │
   │  BAR + TAPS ──── DINING ──── KITCHEN ───────┼─┼─► BOH: dish, walk-in, dry store
   └───────┬──────────────────────┬──────────────┘ │
           │                      │ runners        │
           │                ┌─────▼────────────────▼──┐
           │                │ SHADE COURT (arcade,    │
           │                │ fans, rill, trees)      │
           │                │ STAGE ALCOVE ───────────│
           │                │ FAMILY LAWN             │
           │                └─────────────────────────┘
           │
   MERCH + RESTROOMS (ADA) near bar
   
   SERVICE COURT (rear, separate road):
     • grain receiving / mill room ──► brew deck (hot side)
     • keg cooler ◄──► bar (cold line) and loading dock
     • spent-grain bin (downwind, farm pickup)
     • CO₂ / glycol / chemical storage
     • wastewater pretreatment + floor drains
     • food deliveries ──► dry store / walk-in
```

## Flows
| Flow | Path | Constraint |
|---|---|---|
| **Guests** | Parking → gate → tank hall → bar/dining → court; mezzanine via elevator | Never cross the brew floor, loading, or service roads |
| **Food** | Prep → pass → runners → dining and court | Short runs; shaded runner lane in the court |
| **Grain** | Truck → service court → mill → brew deck | Dust control; separate from guest paths |
| **Kegs** | Fermenter/brite → keg fill → keg cooler → bar lines; empties → dock | Cold chain; short line lengths |
| **Waste** | Floor drains → pretreatment → sewer; spent grain → bins → pickup; grease trap for kitchen | Trade-waste permit `[PRO]` |
| **Smoke/steam/odor** | Kettle hood and kitchen hoods vent upward, downwind of the court | Fire code, make-up air `[PRO]` |
| **Safety** | Glass separation, CO₂ detectors, emergency egress from tank hall and court | Occupancy/fire `[PRO]` |
| **Sound** | Stage toward the least sensitive boundary; indoor quiet zones | City ordinance `[PRO]` |
