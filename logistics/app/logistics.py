from __future__ import annotations

from typing import Any

import httpx
from ortools.constraint_solver import pywrapcp, routing_enums_pb2

from .models import (
    FarmerCostAllocationRequest,
    FarmerCostShare,
    PickupLocation,
    RouteOptimizationRequest,
    RouteResult,
    RouteStop,
    TransportationCostRequest,
    TransportationCostResult,
)


class OSRMService:
    BASE_URL = 'https://router.project-osrm.org'

    async def get_route(self, coordinates: list[tuple[float, float]], include_geometry: bool = False) -> dict[str, Any]:
        if len(coordinates) < 2:
            raise ValueError('At least two coordinates are required to compute a route.')
        if any(lat < -90 or lat > 90 or lon < -180 or lon > 180 for lat, lon in coordinates):
            raise ValueError('Invalid coordinates supplied for OSRM routing.')

        points = ';'.join(f'{lon},{lat}' for lat, lon in coordinates)
        url = f'{self.BASE_URL}/route/v1/driving/{points}?overview=full&geometries=geojson'
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(url)
                response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise TimeoutError('OSRM routing request timed out.') from exc
        except httpx.HTTPError as exc:
            raise ConnectionError('Unable to reach the OSRM routing service.') from exc

        payload = response.json()
        if 'routes' not in payload or not payload['routes']:
            raise ValueError('OSRM could not find a valid route for the supplied coordinates.')

        route = payload['routes'][0]
        return {
            'distance_meters': route.get('distance', 0),
            'duration_seconds': route.get('duration', 0),
            'geometry': route.get('geometry') if include_geometry else None,
        }

    async def get_distance_matrix(self, coordinates: list[tuple[float, float]]) -> list[list[float]]:
        """Return the OSRM road-distance matrix for depot and pickup points."""
        if len(coordinates) < 2:
            raise ValueError('At least two coordinates are required to compute a distance matrix.')
        if any(lat < -90 or lat > 90 or lon < -180 or lon > 180 for lat, lon in coordinates):
            raise ValueError('Invalid coordinates supplied for OSRM routing.')

        points = ';'.join(f'{lon},{lat}' for lat, lon in coordinates)
        url = f'{self.BASE_URL}/table/v1/driving/{points}?annotations=distance'
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(url)
                response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise TimeoutError('OSRM distance matrix request timed out.') from exc
        except httpx.HTTPError as exc:
            raise ConnectionError('Unable to reach the OSRM routing service.') from exc

        payload = response.json()
        distances = payload.get('distances')
        if not distances or len(distances) != len(coordinates) or any(
            len(row) != len(coordinates) for row in distances
        ):
            raise ValueError('OSRM did not return a valid distance matrix.')
        return distances


class RoutingOptimizer:
    def __init__(self, osrm_service: OSRMService) -> None:
        self.osrm_service = osrm_service

    async def optimize_route(self, request: RouteOptimizationRequest) -> RouteResult:
        total_quantity = sum(stop.quantity_kg for stop in request.stops)
        if total_quantity > request.vehicle_capacity_kg:
            raise ValueError('Total pickup quantity exceeds vehicle capacity.')

        if not request.stops:
            raise ValueError('At least one pickup point is required.')

        matrix_coords = [(request.depot.lat, request.depot.lon)]
        matrix_coords.extend((stop.lat, stop.lon) for stop in request.stops)
        road_distances = await self.osrm_service.get_distance_matrix(matrix_coords)

        manager = pywrapcp.RoutingIndexManager(len(matrix_coords), 1, 0)
        routing = pywrapcp.RoutingModel(manager)

        def distance_callback(from_index: int, to_index: int) -> int:
            from_node = manager.IndexToNode(from_index)
            to_node = manager.IndexToNode(to_index)
            return int(road_distances[from_node][to_node])

        transit_index = routing.RegisterTransitCallback(distance_callback)
        routing.SetArcCostEvaluatorOfAllVehicles(transit_index)
        search_parameters = pywrapcp.DefaultRoutingSearchParameters()
        search_parameters.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
        search_parameters.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
        search_parameters.time_limit.seconds = 5
        solution = routing.SolveWithParameters(search_parameters)

        if solution is None:
            raise ValueError('Route optimization could not find a valid solution.')

        route_nodes = []
        index = routing.Start(0)
        while not routing.IsEnd(index):
            node = manager.IndexToNode(index)
            if node > 0:
                stop = request.stops[node - 1]
                route_nodes.append(stop)
            index = solution.Value(routing.NextVar(index))

        ordered = [RouteStop(
            sequence=i + 1,
            farmer_id=stop.farmer_id,
            farmer_name=stop.farmer_name,
            quantity_kg=stop.quantity_kg,
            lat=stop.lat,
            lon=stop.lon,
        ) for i, stop in enumerate(route_nodes)]

        optimized_coords = [(request.depot.lat, request.depot.lon)]
        optimized_coords.extend((stop.lat, stop.lon) for stop in route_nodes)
        optimized_coords.append((request.depot.lat, request.depot.lon))
        route_data = await self.osrm_service.get_route(optimized_coords, include_geometry=False)
        distance_meters = float(route_data['distance_meters'])
        duration_seconds = float(route_data['duration_seconds'])

        return RouteResult(
            order_id=request.order_id,
            optimized_stop_sequence=ordered,
            farmer_ids=[stop.farmer_id for stop in ordered],
            farmer_names=[stop.farmer_name for stop in ordered],
            pickup_quantities=[stop.quantity_kg for stop in ordered],
            total_quantity_kg=total_quantity,
            total_road_distance_km=distance_meters / 1000,
            estimated_travel_time_minutes=duration_seconds / 60,
            vehicle_capacity_kg=request.vehicle_capacity_kg,
            route_status='optimized',
        )

class TransportationCostCalculator:
    @staticmethod
    def calculate(request: TransportationCostRequest) -> TransportationCostResult:
        fuel_used = request.distance_km / request.fuel_efficiency_km_l
        fuel_cost = fuel_used * request.fuel_price_per_l
        total_estimated_cost = fuel_cost + request.driver_cost + request.toll_cost + request.additional_cost
        return TransportationCostResult(
            order_id=request.order_id,
            fuel_used_l=round(fuel_used, 3),
            fuel_cost=round(fuel_cost, 2),
            driver_cost=round(request.driver_cost, 2),
            toll_cost=round(request.toll_cost, 2),
            additional_cost=round(request.additional_cost, 2),
            total_estimated_cost=round(total_estimated_cost, 2),
            estimate_note='Transportation cost is an estimate based on the supplied assumptions and route inputs.',
        )


class FarmerCostAllocator:
    @staticmethod
    def allocate(request: FarmerCostAllocationRequest) -> dict[str, Any]:
        total_quantity = sum(item['quantity_kg'] for item in request.farmer_contributions)
        if total_quantity <= 0:
            raise ValueError('Total farmer contribution must be greater than zero.')

        allocations: list[FarmerCostShare] = []
        for item in request.farmer_contributions:
            quantity = float(item['quantity_kg'])
            share = (quantity / total_quantity) * 100
            allocated_cost = (quantity / total_quantity) * request.total_transportation_cost
            allocations.append(FarmerCostShare(
                farmer_id=item['farmer_id'],
                farmer_name=item['farmer_name'],
                quantity_kg=quantity,
                share_percentage=round(share, 2),
                allocated_cost=round(allocated_cost, 2),
            ))

        rounded_total = round(sum(item.allocated_cost for item in allocations), 2)
        difference = round(request.total_transportation_cost - rounded_total, 2)
        if abs(difference) > 0:
            allocations[0].allocated_cost = round(allocations[0].allocated_cost + difference, 2)

        return {
            'order_id': request.order_id,
            'total_transportation_cost': request.total_transportation_cost,
            'farmer_allocations': [
                {
                    'farmer_id': item.farmer_id,
                    'farmer_name': item.farmer_name,
                    'quantity_kg': item.quantity_kg,
                    'share_percentage': item.share_percentage,
                    'allocated_cost': item.allocated_cost,
                }
                for item in allocations
            ],
        }


osrm_service = OSRMService()
