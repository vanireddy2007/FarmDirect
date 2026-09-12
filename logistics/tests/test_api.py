from fastapi.testclient import TestClient

from logistics.app.aggregation import AggregationStore
from logistics.app.data import FarmerListing
from logistics.app.main import app

client = TestClient(app)

FPO_ID = "6"


# ---------------------------------------------------------------------------
# Basic health and validation
# ---------------------------------------------------------------------------

def test_health_endpoint():
    response = client.get('/health')
    assert response.status_code == 200
    assert response.json()['status'] == 'ok'


def test_invalid_fpo_rejected():
    response = client.get('/api/fpo/INVALID/available-produce')
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Real API / integration tests (use real MySQL via throwaway test produce)
# ---------------------------------------------------------------------------

def test_available_produce(make_test_produce):
    produce_id = make_test_produce('Rice', 100)
    response = client.get(f'/api/fpo/{FPO_ID}/available-produce')
    assert response.status_code == 200
    data = response.json()
    listing_ids = [item['listing_id'] for item in data['produce']]
    assert produce_id in listing_ids


def test_valid_aggregation(make_test_produce):
    id_a = make_test_produce('Rice', 500)
    id_b = make_test_produce('Rice', 400)
    payload = {
        'crop': 'Rice',
        'requested_quantity_kg': 900,
        'selected_listings': [
            {'listing_id': id_a, 'quantity_kg': 500},
            {'listing_id': id_b, 'quantity_kg': 400},
        ],
    }
    response = client.post(f'/api/fpo/{FPO_ID}/aggregate', json=payload)
    assert response.status_code == 200
    result = response.json()
    assert result['batch']['crop'] == 'Rice'
    assert result['batch']['total_quantity_kg'] == 900
    assert len(result['contributions']) == 2


def test_over_allocation_rejected(make_test_produce):
    produce_id = make_test_produce('Rice', 50)
    payload = {
        'crop': 'Rice',
        'requested_quantity_kg': 1000,
        'selected_listings': [
            {'listing_id': produce_id, 'quantity_kg': 1000},
        ],
    }
    response = client.post(f'/api/fpo/{FPO_ID}/aggregate', json=payload)
    assert response.status_code == 400
    assert 'insufficient' in response.json()['detail'].lower() or 'available' in response.json()['detail'].lower()


def test_mixed_crop_allowed(make_test_produce):
    produce_id = make_test_produce('Rice', 200)
    payload = {
        'crop': 'Wheat',
        'requested_quantity_kg': 200,
        'selected_listings': [
            {'listing_id': produce_id, 'quantity_kg': 200},
        ],
    }
    response = client.post(f'/api/fpo/{FPO_ID}/aggregate', json=payload)
    assert response.status_code == 200
    result = response.json()
    assert result['batch']['crop'] == 'Wheat'
    assert result['contributions'][0]['crop'] == 'Rice'


def test_bulk_order_matching(make_test_produce):
    produce_id = make_test_produce('Rice', 600)
    client.post(f'/api/fpo/{FPO_ID}/aggregate', json={
        'crop': 'Rice',
        'requested_quantity_kg': 600,
        'selected_listings': [{'listing_id': produce_id, 'quantity_kg': 600}],
    })

    response = client.post(f'/api/fpo/{FPO_ID}/match-bulk-order', json={
        'buyer_order_id': 'BUY-100',
        'items': [
            {'crop': 'Rice', 'required_quantity_kg': 600},
        ],
    })
    assert response.status_code == 200
    data = response.json()
    assert data['total_matched_quantity_kg'] > 0
    assert data['items'][0]['matched_batches']


def test_suitability_validates_fpo_and_requested_quantity():
    invalid_fpo = client.get('/api/fpo/INVALID/suitability-scores', params={
        'crop': 'Rice', 'required_quantity_kg': 100,
        'reference_latitude': 25.0, 'reference_longitude': 91.0,
    })
    invalid_quantity = client.get(f'/api/fpo/{FPO_ID}/suitability-scores', params={
        'crop': 'Rice', 'required_quantity_kg': 0,
        'reference_latitude': 25.0, 'reference_longitude': 91.0,
    })
    assert invalid_fpo.status_code == 404
    assert invalid_quantity.status_code == 400


def test_suitability_to_aggregation_integration(make_test_produce):
    id_a = make_test_produce('Rice', 400)
    id_b = make_test_produce('Rice', 350)
    id_c = make_test_produce('Rice', 250)

    scores = client.get(f'/api/fpo/{FPO_ID}/suitability-scores', params={
        'crop': 'Rice', 'required_quantity_kg': 1000,
        'reference_latitude': 25.0, 'reference_longitude': 91.0,
    })
    assert scores.status_code == 200
    candidate_ids = [c['listing_id'] for c in scores.json()['candidates']]
    assert id_a in candidate_ids
    assert id_b in candidate_ids
    assert id_c in candidate_ids

    aggregation = client.post(f'/api/fpo/{FPO_ID}/aggregate', json={
        'crop': 'Rice',
        'requested_quantity_kg': 1000,
        'selected_listings': [
            {'listing_id': id_a, 'quantity_kg': 400},
            {'listing_id': id_b, 'quantity_kg': 350},
            {'listing_id': id_c, 'quantity_kg': 250},
        ],
    })
    assert aggregation.status_code == 200
    assert len(aggregation.json()['contributions']) == 3

    available = client.get(f'/api/fpo/{FPO_ID}/available-produce').json()['produce']
    quantities = {item['listing_id']: item['available_quantity_kg'] for item in available}
    assert quantities.get(id_a, 0) == 0
    assert quantities.get(id_b, 0) == 0
    assert quantities.get(id_c, 0) == 0


# ---------------------------------------------------------------------------
# Pure scoring-logic tests (no API, no database — direct store calls only)
# ---------------------------------------------------------------------------

def test_quality_price_quantity_and_distance_affect_scores():
    store = AggregationStore()
    store.listings = {
        'HIGH': FarmerListing('HIGH', 'F-HIGH', 'High Quality', FPO_ID, 'Rice', 'Grade A', 1000, 30, 25.001, 91.001),
        'LOW': FarmerListing('LOW', 'F-LOW', 'Low Quality', FPO_ID, 'Rice', 'Grade B', 500, 20, 25.020, 91.020),
    }
    high_breakdown = store.get_listing_score_breakdown(store.listings['HIGH'], 1000, 25.0, 91.0)
    low_breakdown = store.get_listing_score_breakdown(store.listings['LOW'], 1000, 25.0, 91.0)

    assert high_breakdown['quality'] > low_breakdown['quality']
    assert low_breakdown['price'] > high_breakdown['price']
    assert high_breakdown['quantity'] > low_breakdown['quantity']
    assert high_breakdown['distance'] > low_breakdown['distance']


def test_suitability_ranking_returns_compatible_candidates():
    store = AggregationStore()
    store.refresh_listings = lambda fpo_id: None
    store.listings = {
        'A': FarmerListing('A', 'F-A', 'Farmer A', FPO_ID, 'Rice', 'Grade A', 800, 28.0, 25.010, 91.020),
        'B': FarmerListing('B', 'F-B', 'Farmer B', FPO_ID, 'Rice', 'Grade A', 600, 27.5, 25.030, 91.040),
        'C': FarmerListing('C', 'F-C', 'Farmer C', FPO_ID, 'Wheat', 'Grade B', 700, 26.0, 25.050, 91.060),
    }
    candidates = store.get_suitability_scores(FPO_ID, 'Rice', 1000, 25.0, 91.0)
    assert [c['listing_id'] for c in candidates] == ['B', 'A']
    assert set(candidates[0]['score_breakdown']) == {
        'quality', 'price', 'quantity', 'distance', 'route', 'reliability'
    }


def test_incompatible_crop_quality_and_zero_quantity_are_excluded():
    store = AggregationStore()
    store.refresh_listings = lambda fpo_id: None
    store.listings = {
        'A': FarmerListing('A', 'F-A', 'Farmer A', FPO_ID, 'Rice', 'Grade A', 0, 28.0, 25.010, 91.020),
        'B': FarmerListing('B', 'F-B', 'Farmer B', FPO_ID, 'Rice', 'Unknown', 600, 27.5, 25.030, 91.040),
        'C': FarmerListing('C', 'F-C', 'Farmer C', FPO_ID, 'Wheat', 'Grade B', 700, 26.0, 25.050, 91.060),
    }
    rice_candidates = store.get_suitability_scores(FPO_ID, 'Rice', 100, 25.0, 91.0)
    assert rice_candidates == []

    wheat_candidates = store.get_suitability_scores(FPO_ID, 'Wheat', 100, 25.0, 91.0)
    assert [c['listing_id'] for c in wheat_candidates] == ['C']


# ---------------------------------------------------------------------------
# Route optimization / cost calculation (unchanged, no database dependency)
# ---------------------------------------------------------------------------

def test_capacity_validation_for_route_optimization():
    payload = {
        'order_id': 'ORD-TEST-1',
        'vehicle_capacity_kg': 200,
        'depot': {'lat': 25.0, 'lon': 91.0},
        'stops': [
            {'farmer_id': 'F001', 'farmer_name': 'Farmer A', 'quantity_kg': 500, 'lat': 25.01, 'lon': 91.02},
            {'farmer_id': 'F002', 'farmer_name': 'Farmer B', 'quantity_kg': 400, 'lat': 25.03, 'lon': 91.04},
        ],
    }
    response = client.post('/api/logistics/optimize-route', json=payload)
    assert response.status_code == 400
    assert 'capacity' in response.json()['detail'].lower()


def test_route_optimization_and_retrieval(monkeypatch):
    async def fake_matrix(*args, **kwargs):
        return [
            [0, 1000, 2000],
            [1000, 0, 1000],
            [2000, 1000, 0],
        ]

    async def fake_route(*args, **kwargs):
        return {
            'distance_meters': 15000,
            'duration_seconds': 1800,
            'geometry': 'fake-geometry',
        }

    from logistics.app import logistics as logistics_module
    monkeypatch.setattr(logistics_module.osrm_service, 'get_distance_matrix', fake_matrix)
    monkeypatch.setattr(logistics_module.osrm_service, 'get_route', fake_route)

    payload = {
        'order_id': 'ORD-TEST-2',
        'vehicle_capacity_kg': 1500,
        'depot': {'lat': 25.0, 'lon': 91.0},
        'stops': [
            {'farmer_id': 'F001', 'farmer_name': 'Farmer A', 'quantity_kg': 500, 'lat': 25.01, 'lon': 91.02},
            {'farmer_id': 'F002', 'farmer_name': 'Farmer B', 'quantity_kg': 400, 'lat': 25.03, 'lon': 91.04},
        ],
    }
    response = client.post('/api/logistics/optimize-route', json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data['order_id'] == 'ORD-TEST-2'
    assert data['total_quantity_kg'] == 900
    assert data['route_status'] == 'optimized'

    get_response = client.get('/api/logistics/routes/ORD-TEST-2')
    assert get_response.status_code == 200
    assert get_response.json()['order_id'] == 'ORD-TEST-2'


def test_route_final_osrm_call_uses_optimized_sequence(monkeypatch):
    matrix = [
        [0, 100, 10, 100],
        [100, 0, 10, 10],
        [10, 10, 0, 100],
        [100, 10, 100, 0],
    ]
    route_calls = []

    async def fake_matrix(coordinates):
        assert len(coordinates) == 4
        return matrix

    async def fake_route(coordinates, include_geometry=False):
        route_calls.append(coordinates)
        return {'distance_meters': 4000, 'duration_seconds': 240, 'geometry': None}

    from logistics.app import logistics as logistics_module
    monkeypatch.setattr(logistics_module.osrm_service, 'get_distance_matrix', fake_matrix)
    monkeypatch.setattr(logistics_module.osrm_service, 'get_route', fake_route)

    response = client.post('/api/logistics/optimize-route', json={
        'order_id': 'ORD-ROAD-MATRIX',
        'vehicle_capacity_kg': 1000,
        'depot': {'lat': 25.0, 'lon': 91.0},
        'stops': [
            {'farmer_id': 'F001', 'farmer_name': 'Farmer A', 'quantity_kg': 100, 'lat': 25.01, 'lon': 91.01},
            {'farmer_id': 'F002', 'farmer_name': 'Farmer B', 'quantity_kg': 100, 'lat': 25.02, 'lon': 91.02},
            {'farmer_id': 'F003', 'farmer_name': 'Farmer C', 'quantity_kg': 100, 'lat': 25.03, 'lon': 91.03},
        ],
    })

    assert response.status_code == 200
    assert [stop['farmer_id'] for stop in response.json()['optimized_stop_sequence']] == ['F002', 'F001', 'F003']
    assert route_calls == [[
        (25.0, 91.0),
        (25.02, 91.02),
        (25.01, 91.01),
        (25.03, 91.03),
        (25.0, 91.0),
    ]]
    assert response.json()['total_road_distance_km'] == 4.0
    assert response.json()['estimated_travel_time_minutes'] == 4.0


def test_unknown_route_returns_404():
    response = client.get('/api/logistics/routes/UNKNOWN-ROUTE')
    assert response.status_code == 404


def test_transportation_cost_calculation():
    response = client.post('/api/logistics/calculate-cost', json={
        'order_id': 'ORD-TEST-3',
        'distance_km': 42.5,
        'fuel_efficiency_km_l': 12,
        'fuel_price_per_l': 92.0,
        'driver_cost': 1200,
        'toll_cost': 250,
        'additional_cost': 150,
    })
    assert response.status_code == 200
    data = response.json()
    assert data['fuel_used_l'] > 0
    assert data['total_estimated_cost'] > 0
    assert 'estimate' in data['estimate_note'].lower()


def test_farmer_cost_allocation_and_totals():
    payload = {
        'order_id': 'ORD-TEST-3',
        'farmer_contributions': [
            {'farmer_id': 'F001', 'farmer_name': 'Farmer A', 'quantity_kg': 600},
            {'farmer_id': 'F002', 'farmer_name': 'Farmer B', 'quantity_kg': 400},
            {'farmer_id': 'F003', 'farmer_name': 'Farmer C', 'quantity_kg': 200},
        ],
        'total_transportation_cost': 2400,
    }
    response = client.post('/api/logistics/allocate-cost', json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data['total_transportation_cost'] == 2400
    assert round(sum(item['allocated_cost'] for item in data['farmer_allocations']), 2) == 2400
    assert data['farmer_allocations'][0]['share_percentage'] > 0
