from fastapi.testclient import TestClient

from logistics.app.aggregation import AggregationStore
from logistics.app.data import FarmerListing
from logistics.app.routers import fpo as fpo_router
from logistics.app.main import app


client = TestClient(app)


def _fresh_storage(monkeypatch):
    storage = AggregationStore()
    monkeypatch.setattr(fpo_router, 'storage', storage)
    return storage


def test_health_endpoint():
    response = client.get('/health')
    assert response.status_code == 200
    assert response.json()['status'] == 'ok'


def test_available_produce():
    response = client.get('/api/fpo/FPO-001/available-produce')
    assert response.status_code == 200
    data = response.json()
    assert len(data['produce']) >= 3
    assert all(item['fpo_id'] == 'FPO-001' for item in data['produce'])


def test_valid_aggregation():
    payload = {
        'crop': 'Rice',
        'requested_quantity_kg': 900,
        'selected_listings': [
            {'listing_id': 'L001', 'quantity_kg': 500},
            {'listing_id': 'L002', 'quantity_kg': 400},
        ],
    }
    response = client.post('/api/fpo/FPO-001/aggregate', json=payload)
    assert response.status_code == 200
    result = response.json()
    assert result['batch']['crop'] == 'Rice'
    assert result['batch']['total_quantity_kg'] == 900
    assert result['contributions'][0]['quantity_kg'] == 500


def test_over_allocation_rejected():
    payload = {
        'crop': 'Rice',
        'requested_quantity_kg': 1000,
        'selected_listings': [
            {'listing_id': 'L001', 'quantity_kg': 1000},
        ],
    }
    response = client.post('/api/fpo/FPO-001/aggregate', json=payload)
    assert response.status_code == 400
    assert 'insufficient' in response.json()['detail'].lower() or 'available' in response.json()['detail'].lower()


def test_invalid_fpo_rejected():
    response = client.get('/api/fpo/INVALID/available-produce')
    assert response.status_code == 404


def test_mixed_crop_rejected():
    payload = {
        'crop': 'Wheat',
        'requested_quantity_kg': 200,
        'selected_listings': [
            {'listing_id': 'L001', 'quantity_kg': 200},
        ],
    }
    response = client.post('/api/fpo/FPO-001/aggregate', json=payload)
    assert response.status_code == 400
    assert 'crop' in response.json()['detail'].lower()


def test_bulk_order_matching():
    response = client.post('/api/fpo/FPO-001/match-bulk-order', json={
        'buyer_order_id': 'BUY-100',
        'crop': 'Rice',
        'required_quantity_kg': 600,
    })
    assert response.status_code == 200
    data = response.json()
    assert data['matched_quantity_kg'] > 0
    assert data['remaining_quantity_kg'] >= 0
    assert data['matched_batches']


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


def test_suitability_ranking_returns_compatible_candidates(monkeypatch):
    _fresh_storage(monkeypatch)
    response = client.get('/api/fpo/FPO-001/suitability-scores', params={
        'crop': 'Rice',
        'required_quantity_kg': 1000,
        'reference_latitude': 25.0,
        'reference_longitude': 91.0,
    })

    assert response.status_code == 200
    data = response.json()
    assert [item['listing_id'] for item in data['candidates']] == ['L001', 'L002']
    assert set(data['candidates'][0]['score_breakdown']) == {
        'quality', 'price', 'quantity', 'distance', 'route', 'reliability'
    }


def test_quality_price_quantity_and_distance_affect_scores(monkeypatch):
    storage = _fresh_storage(monkeypatch)
    storage.listings = {
        'HIGH': FarmerListing('HIGH', 'F-HIGH', 'High Quality', 'FPO-001', 'Rice', 'Grade A', 1000, 30, 25.001, 91.001),
        'LOW': FarmerListing('LOW', 'F-LOW', 'Low Quality', 'FPO-001', 'Rice', 'Grade B', 500, 20, 25.020, 91.020),
    }
    high = client.get('/api/fpo/FPO-001/suitability-scores', params={
        'crop': 'Rice', 'required_quantity_kg': 1000,
        'reference_latitude': 25.0, 'reference_longitude': 91.0,
    }).json()['candidates']
    by_id = {item['listing_id']: item for item in high}

    assert by_id['HIGH']['score_breakdown']['quality'] > by_id['LOW']['score_breakdown']['quality']
    assert by_id['LOW']['score_breakdown']['price'] > by_id['HIGH']['score_breakdown']['price']
    assert by_id['HIGH']['score_breakdown']['quantity'] > by_id['LOW']['score_breakdown']['quantity']
    assert by_id['HIGH']['score_breakdown']['distance'] > by_id['LOW']['score_breakdown']['distance']
    assert high[0]['listing_id'] == 'HIGH'


def test_incompatible_crop_quality_and_zero_quantity_are_excluded(monkeypatch):
    storage = _fresh_storage(monkeypatch)
    storage.listings['L001'].available_quantity_kg = 0
    storage.listings['L002'].quality = 'Unknown'
    response = client.get('/api/fpo/FPO-001/suitability-scores', params={
        'crop': 'Rice', 'required_quantity_kg': 100,
        'reference_latitude': 25.0, 'reference_longitude': 91.0,
    })
    assert response.status_code == 200
    assert response.json()['candidates'] == []

    wheat_response = client.get('/api/fpo/FPO-001/suitability-scores', params={
        'crop': 'Wheat', 'required_quantity_kg': 100,
        'reference_latitude': 25.0, 'reference_longitude': 91.0,
    })
    assert wheat_response.status_code == 200
    assert [item['listing_id'] for item in wheat_response.json()['candidates']] == ['L003']


def test_suitability_validates_fpo_and_requested_quantity(monkeypatch):
    _fresh_storage(monkeypatch)
    invalid_fpo = client.get('/api/fpo/INVALID/suitability-scores', params={
        'crop': 'Rice', 'required_quantity_kg': 100,
        'reference_latitude': 25.0, 'reference_longitude': 91.0,
    })
    invalid_quantity = client.get('/api/fpo/FPO-001/suitability-scores', params={
        'crop': 'Rice', 'required_quantity_kg': 0,
        'reference_latitude': 25.0, 'reference_longitude': 91.0,
    })
    assert invalid_fpo.status_code == 404
    assert invalid_quantity.status_code == 400


def test_suitability_to_aggregation_integration(monkeypatch):
    storage = _fresh_storage(monkeypatch)
    storage.listings['L001'].available_quantity_kg = 800
    storage.listings['L002'].available_quantity_kg = 600
    storage.listings['L006'] = FarmerListing(
        'L006', 'F006', 'Farmer F', 'FPO-001', 'Rice', 'Grade A', 300, 28.5, 25.015, 91.025
    )

    scores = client.get('/api/fpo/FPO-001/suitability-scores', params={
        'crop': 'Rice', 'required_quantity_kg': 1000,
        'reference_latitude': 25.0, 'reference_longitude': 91.0,
    })
    assert scores.status_code == 200
    assert len(scores.json()['candidates']) == 3
    assert storage.listings['L001'].available_quantity_kg == 800
    assert storage.listings['L002'].available_quantity_kg == 600
    assert storage.listings['L006'].available_quantity_kg == 300

    aggregation = client.post('/api/fpo/FPO-001/aggregate', json={
        'crop': 'Rice',
        'requested_quantity_kg': 1000,
        'selected_listings': [
            {'listing_id': 'L001', 'quantity_kg': 400},
            {'listing_id': 'L002', 'quantity_kg': 350},
            {'listing_id': 'L006', 'quantity_kg': 250},
        ],
    })
    assert aggregation.status_code == 200
    assert len(aggregation.json()['contributions']) == 3

    available = client.get('/api/fpo/FPO-001/available-produce').json()['produce']
    quantities = {item['listing_id']: item['available_quantity_kg'] for item in available}
    assert quantities['L001'] == 400
    assert quantities['L002'] == 250
    assert quantities['L006'] == 50
