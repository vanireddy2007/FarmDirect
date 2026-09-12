# Logistics Module — API Contract

**Owner:** Logistics (FPO Aggregation + Smart Logistics)
**Service base URL:** _TBD — confirm host/port with the team before merging into the main API_CONTRACT.md_
**Status:** All endpoints below are implemented and tested (18/18 tests passing) against real MySQL data.

This document is the source of truth for how the backend and frontend should call the logistics service. Do not invent extra fields or guess response shapes — if something you need isn't listed here, ask the logistics owner before changing anything.

---

## 1. Get Available Produce

**GET** `/api/fpo/{fpo_id}/available-produce`

Returns every produce listing currently visible to the given FPO (real data, live from MySQL — any FPO can see any farmer's produce; there is no per-FPO filtering by design).

**Response 200**
```json
{
  "fpo_id": "6",
  "produce": [
    {
      "listing_id": "2",
      "farmer_id": "2",
      "farmer_name": "farmer ",
      "fpo_id": "6",
      "crop": "Tomato",
      "quality": "A",
      "available_quantity_kg": 50.0,
      "price_per_kg": 20.0,
      "latitude": 17.8684342,
      "longitude": 77.8227189
    }
  ]
}
```

**Errors**
- `404` — FPO ID does not exist or is not role `FPO`.

---

## 2. Get Suitability Scores

**GET** `/api/fpo/{fpo_id}/suitability-scores`

Ranks currently available, quality-compatible listings for a given crop and required quantity, using a weighted score: quality 25%, price 20%, quantity fit 20%, pickup proximity 20%, route compatibility 10% (neutral, no route data yet), fulfillment reliability 5% (neutral, no reliability data yet).

**Query parameters**
| Name | Type |
|---|---|
| crop | string |
| required_quantity_kg | float (> 0) |
| reference_latitude | float |
| reference_longitude | float |

**Response 200**
```json
{
  "fpo_id": "6",
  "crop": "Tomato",
  "required_quantity_kg": 30,
  "candidates": [
    {
      "listing_id": "2",
      "farmer_id": "2",
      "farmer_name": "farmer ",
      "crop": "Tomato",
      "quality": "A",
      "available_quantity_kg": 50.0,
      "price_per_kg": 20.0,
      "suitability_score": 87.5,
      "score_breakdown": {
        "quality": 100.0,
        "price": 80.0,
        "quantity": 100.0,
        "distance": 95.0,
        "route": 50.0,
        "reliability": 50.0
      }
    }
  ]
}
```
Candidates are sorted by `suitability_score`, highest first.

**Errors**
- `404` — invalid FPO ID
- `400` — `required_quantity_kg` <= 0

---

## 3. Create Aggregation Batch

**POST** `/api/fpo/{fpo_id}/aggregate`

Creates a batch from one or more selected listings. Mixed crops in one batch are intentional and allowed. Persists quantity reductions directly to the real `produce` table with a safety check against double-allocation.

**Request body**
```json
{
  "crop": "Mixed",
  "requested_quantity_kg": 80,
  "selected_listings": [
    { "listing_id": "2", "quantity_kg": 30 },
    { "listing_id": "5", "quantity_kg": 50 }
  ]
}
```
- `crop`: string — a label for the batch (does not restrict which crops can be selected)
- `requested_quantity_kg`: float, > 0
- `selected_listings`: at least 1 entry, each `quantity_kg` > 0

**Response 200**
```json
{
  "message": "Aggregation batch created successfully.",
  "batch": {
    "batch_id": "BATCH-0001",
    "fpo_id": "6",
    "crop": "Mixed",
    "total_quantity_kg": 80,
    "available_quantity_kg": 80,
    "status": "created",
    "farmer_contributions": [
      { "listing_id": "2", "farmer_id": "2", "farmer_name": "farmer ", "quantity_kg": 30, "crop": "Tomato" },
      { "listing_id": "5", "farmer_id": "3", "farmer_name": "...", "quantity_kg": 50, "crop": "Potato" }
    ]
  },
  "contributions": [ /* same array as batch.farmer_contributions */ ]
}
```

**Errors** (all `400`, message describes the exact problem)
- Invalid FPO ID
- A `quantity_kg` <= 0
- An invalid/unknown `listing_id`
- Selected quantity exceeds a listing's available quantity
- Duplicate `listing_id` in the same request
- Sum of `selected_listings` quantities does not equal `requested_quantity_kg`
- A listing's real stock changed/ran out since it was last read (race-condition safety check)

---

## 4. Get Batches

**GET** `/api/fpo/{fpo_id}/batches`

Returns all batches created by this FPO (in-memory for the current server session — not yet persisted to a dedicated batches table).

**Response 200**
```json
{
  "fpo_id": "6",
  "batches": [
    {
      "batch_id": "BATCH-0001",
      "crop": "Mixed",
      "total_quantity_kg": 80,
      "available_quantity_kg": 80,
      "farmer_contributions": [ /* same shape as above */ ],
      "status": "created",
      "order_association": null
    }
  ]
}
```
- `status`: `"created"` or `"matched"`
- `order_association`: `buyer_order_id` once matched, otherwise `null`

**Errors**
- `404` — invalid FPO ID

---

## 5. Match Bulk Order

**POST** `/api/fpo/{fpo_id}/match-bulk-order`

Matches a buyer's order (one or more crops) against this FPO's existing batches. Each crop is matched independently; a batch's remaining quantity carries over until fully consumed.

**Request body**
```json
{
  "buyer_order_id": "ORDER-123",
  "items": [
    { "crop": "Tomato", "required_quantity_kg": 40 },
    { "crop": "Potato", "required_quantity_kg": 20 }
  ]
}
```
- `items`: at least 1 entry

**Response 200**
```json
{
  "message": "Bulk order matching completed.",
  "buyer_order_id": "ORDER-123",
  "items": [
    {
      "crop": "Tomato",
      "matched_quantity_kg": 40,
      "remaining_quantity_kg": 0,
      "matched_batches": [
        { "batch_id": "BATCH-0001", "matched_quantity_kg": 40, "farmer_contributions": [ /* ... */ ] }
      ]
    }
  ],
  "total_matched_quantity_kg": 40,
  "total_remaining_quantity_kg": 0
}
```

**Errors**
- `404` — invalid FPO ID
- `400` — ValueError from matching logic

---

## 6. Optimize Route

**POST** `/api/logistics/optimize-route`

Calls OSRM + OR-Tools to compute the optimal pickup sequence and real road distance for a set of farmer stops. **This is the endpoint the frontend should call instead of its own local Haversine calculation.**

**Request body**
```json
{
  "order_id": "ORDER-123",
  "vehicle_capacity_kg": 500,
  "depot": { "lat": 17.868, "lon": 77.822 },
  "stops": [
    { "farmer_id": "2", "farmer_name": "farmer ", "quantity_kg": 40, "lat": 17.87, "lon": 77.83 }
  ]
}
```

**Response 200**
```json
{
  "order_id": "ORDER-123",
  "optimized_stop_sequence": [
    { "sequence": 1, "farmer_id": "2", "farmer_name": "farmer ", "quantity_kg": 40, "lat": 17.87, "lon": 77.83 }
  ],
  "farmer_ids": ["2"],
  "farmer_names": ["farmer "],
  "pickup_quantities": [40],
  "total_quantity_kg": 40,
  "total_road_distance_km": 12.4,
  "estimated_travel_time_minutes": 22.5,
  "vehicle_capacity_kg": 500,
  "route_status": "optimized"
}
```
- `route_status`: `"optimized"`, `"partial"`, or `"pending"`

**Errors**
- `400` — ValueError (e.g. total stop quantity exceeds vehicle capacity)
- `503` — OSRM service unreachable or timed out

---

## 7. Calculate Transportation Cost

**POST** `/api/logistics/calculate-cost`

**Request body**
```json
{
  "order_id": "ORDER-123",
  "distance_km": 12.4,
  "fuel_efficiency_km_l": 8,
  "fuel_price_per_l": 95,
  "driver_cost": 300,
  "toll_cost": 50,
  "additional_cost": 20
}
```
All numeric fields required; `fuel_efficiency_km_l` and `distance_km` must be > 0, the rest >= 0.

**Response 200**
```json
{
  "order_id": "ORDER-123",
  "fuel_used_l": 1.55,
  "fuel_cost": 147.25,
  "driver_cost": 300,
  "toll_cost": 50,
  "additional_cost": 20,
  "total_estimated_cost": 517.25,
  "estimate_note": "..."
}
```

---

## 8. Allocate Cost to Farmers

**POST** `/api/logistics/allocate-cost`

Splits a total transportation cost across contributing farmers proportionally to their quantity.

**Request body**
```json
{
  "order_id": "ORDER-123",
  "farmer_contributions": [
    { "farmer_id": "2", "farmer_name": "farmer ", "quantity_kg": 40 }
  ],
  "total_transportation_cost": 517.25
}
```
- `farmer_contributions`: flexible list of dicts (any keys needed by the caller — the allocator reads `farmer_id`, `farmer_name`, `quantity_kg`)

**Response 200**
```json
{
  "order_id": "ORDER-123",
  "total_transportation_cost": 517.25,
  "farmer_allocations": [
    {
      "farmer_id": "2",
      "farmer_name": "farmer ",
      "quantity_kg": 40,
      "share_percentage": 100.0,
      "allocated_cost": 517.25
    }
  ]
}
```

**Errors**
- `400` — ValueError from allocation logic

---

## 9. Get Route by Order ID

**GET** `/api/logistics/routes/{order_id}`

Returns a previously computed route (same shape as the Optimize Route response above). Stored in-memory for the current server session.

**Errors**
- `404` — no route stored for this `order_id`

---

## Integration notes for the team

- **Frontend:** `logistics.js` currently computes its own route with a local coordinate dictionary + Haversine formula. Replace that with a call to endpoint **#6** above, and use endpoint **#9** to re-fetch a previously computed route.
- **Backend:** there is currently no call from the main backend (`:8000`) into this logistics service at all. If the main backend is meant to proxy these calls (rather than the frontend calling the logistics service directly), that needs to be decided and documented as an addition to this contract.
- **All quantities are in kilograms (`_kg` suffix).** The frontend displays produce in Quintals (Qtl) — conversion must happen on the frontend or backend side; this service does not do unit conversion.
- **Mixed crops in one aggregation batch are intentional** — do not add same-crop validation anywhere in the pipeline.
