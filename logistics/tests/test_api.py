from fastapi.testclient import TestClient

from logistics.app.main import app


client = TestClient(app)


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
    async def fake_route(*args, **kwargs):
        return {
            'distance_meters': 15000,
            'duration_seconds': 1800,
            'geometry': 'fake-geometry',
        }

    from logistics.app import logistics as logistics_module
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
