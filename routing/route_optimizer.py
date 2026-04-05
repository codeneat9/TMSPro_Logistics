"""
Route Optimization Module using OSMnx and NetworkX

This module provides:
1. Primary route calculation via shortest path
2. Alternate route generation (2-3 alternatives)
3. Route metrics (distance, estimated time, traffic risk)
4. Decision logic for rerouting based on delay predictions
"""

import logging
from dataclasses import dataclass
from typing import List, Tuple, Optional, Dict
import math

import networkx as nx
import osmnx as ox
from geopy.distance import geodesic
from geopy.geocoders import Nominatim

# Suppress OSMnx warnings
logging.getLogger('osmnx').setLevel(logging.ERROR)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class RouteInfo:
    """Container for route information"""
    route_name: str  # "Primary", "Alternative 1", etc.
    coordinates: List[Tuple[float, float]]  # List of (lat, lon) waypoints
    distance_km: float
    estimated_time_min: float
    node_ids: List[int]  # OSM node IDs for the route
    risk_score: float  # 0.0-1.0, where 1.0 is highest delay risk
    metadata: Dict = None

    def to_dict(self) -> dict:
        """Convert to JSON-serializable dict"""
        return {
            "route_name": self.route_name,
            "distance_km": round(self.distance_km, 2),
            "estimated_time_min": round(self.estimated_time_min, 1),
            "num_waypoints": len(self.coordinates),
            "risk_score": round(self.risk_score, 3),
            "coordinates": self.coordinates,
            "metadata": self.metadata or {}
        }


class RouteOptimizer:
    """
    Main routing engine using OSMnx for OpenStreetMap data.
    
    Features:
    - Fetches road network for a bounding box
    - Calculates shortest/fastest paths
    - Generates alternate routes
    - Estimates travel time with traffic factors
    """

    def __init__(self, city: str = "Lisbon", country: str = "Portugal", cache_dir: str = "./routing_cache"):
        """
        Initialize the route optimizer.
        
        Args:
            city: City name for OSM queries
            country: Country name
            cache_dir: Cache directory for downloaded graphs
        """
        self.city = city
        self.country = country
        self.cache_dir = cache_dir
        self.G = None  # Will hold the street network graph
        self.geocoder = Nominatim(user_agent="delay_routing_agent")
        
        logger.info(f"RouteOptimizer initialized for {city}, {country}")

    def load_network(self, network_type: str = "drive") -> bool:
        """
        Load the street network for the given city.
        
        Args:
            network_type: "drive", "bike", "walk", or "all"
            
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Downloading street network for {self.city}...")
            # Download the graph (this could take a minute on first run)
            self.G = ox.graph_from_place(
                f"{self.city}, {self.country}",
                network_type=network_type,
                simplify=True,
                retain_all=False
            )
            logger.info(f"Network loaded: {len(self.G.nodes)} nodes, {len(self.G.edges)} edges")
            return True
        except Exception as e:
            logger.error(f"Failed to load network: {e}")
            return False

    def load_network_bbox(
        self,
        north: float,
        south: float,
        east: float,
        west: float,
        network_type: str = "drive"
    ) -> bool:
        """
        Load street network for a specific bounding box.
        
        Args:
            north, south, east, west: Bounding box coordinates
            network_type: "drive", "bike", "walk", or "all"
            
        Returns:
            True if successful
        """
        try:
            logger.info(f"Downloading street network for bbox: ({north}, {south}, {east}, {west})")
            self.G = ox.graph_from_bbox(
                north, south, east, west,
                network_type=network_type,
                simplify=True
            )
            logger.info(f"Network loaded: {len(self.G.nodes)} nodes, {len(self.G.edges)} edges")
            return True
        except Exception as e:
            logger.error(f"Failed to load network: {e}")
            return False

    def _get_nearest_node(self, lat: float, lon: float) -> int:
        """Find nearest node in the graph to given coordinates."""
        if self.G is None:
            raise ValueError("Network not loaded. Call load_network() first.")
        return ox.distance.nearest_nodes(self.G, lon, lat)

    def _haversine_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate straight-line distance in km using Haversine formula."""
        return geodesic((lat1, lon1), (lat2, lon2)).km

    def _estimate_travel_time(
        self,
        distance_km: float,
        time_of_day: int = None,
        traffic_factor: float = 1.0,
        base_speed_kmh: float = 25.0
    ) -> float:
        """
        Estimate travel time in minutes.
        
        Args:
            distance_km: Distance in kilometers
            time_of_day: Hour (0-23). Rush hours get traffic_factor boost
            traffic_factor: Multiplier for congestion (1.0 = normal, 1.5 = heavy)
            base_speed_kmh: Average speed in km/h
            
        Returns:
            Estimated travel time in minutes
        """
        # Adjust for rush hours (8-10 AM, 5-7 PM)
        if time_of_day is not None:
            if 8 <= time_of_day <= 10 or 17 <= time_of_day <= 19:
                traffic_factor *= 1.3  # 30% slower in rush hour
        
        # Calculate time: distance / (speed / traffic_factor) * 60
        adjusted_speed = base_speed_kmh / traffic_factor
        time_minutes = (distance_km / adjusted_speed) * 60
        
        return time_minutes

    def _calculate_risk_score(
        self,
        distance_km: float,
        delay_probability: float = None,
        time_of_day: int = None,
        weather_conditions: str = "clear"  # "clear", "rain", "storm"
    ) -> float:
        """
        Calculate route risk score (0.0-1.0).
        
        Factors:
        - Predicted delay probability
        - Distance (longer = more risk)
        - Time of day (rush hour = higher risk)
        - Weather
        
        Returns:
            Risk score 0.0-1.0
        """
        risk = 0.0
        
        # Delay probability factor (40% of score)
        if delay_probability is not None:
            risk += delay_probability * 0.4
        
        # Distance factor (20% of score) - longer routes risky
        distance_risk = min(distance_km / 15.0, 1.0)  # Normalize to 15km max
        risk += distance_risk * 0.2
        
        # Time of day factor (20% of score)
        if time_of_day is not None:
            if 8 <= time_of_day <= 10 or 17 <= time_of_day <= 19:
                risk += 0.3  # Rush hour adds 0.3 to risk
            else:
                risk += 0.0
        risk = min(risk, 0.8)  # Cap at 0.8 from time
        
        # Weather factor (20% of score)
        weather_risk = {"clear": 0.0, "rain": 0.5, "storm": 1.0}.get(weather_conditions, 0.0)
        risk += weather_risk * 0.2
        
        return min(risk, 1.0)

    def calculate_primary_route(
        self,
        origin_lat: float,
        origin_lon: float,
        dest_lat: float,
        dest_lon: float,
        delay_probability: float = None,
        time_of_day: int = None,
        weather: str = "clear"
    ) -> Optional[RouteInfo]:
        """
        Calculate the shortest/fastest primary route.
        
        Args:
            origin_lat, origin_lon: Starting coordinates
            dest_lat, dest_lon: Destination coordinates
            delay_probability: Predicted delay probability (0.0-1.0)
            time_of_day: Hour (0-23)
            weather: "clear", "rain", or "storm"
            
        Returns:
            RouteInfo object or None if calculation fails
        """
        try:
            if self.G is None:
                raise ValueError("Network not loaded")

            # Find nearest nodes
            origin_node = self._get_nearest_node(origin_lat, origin_lon)
            dest_node = self._get_nearest_node(dest_lat, dest_lon)

            # Calculate shortest path
            route_nodes = nx.shortest_path(self.G, origin_node, dest_node, weight="length")

            # Extract coordinates from nodes
            coordinates = []
            total_distance = 0.0
            
            for i, node in enumerate(route_nodes):
                lat = self.G.nodes[node]["y"]
                lon = self.G.nodes[node]["x"]
                coordinates.append((lat, lon))
                
                # Sum edge distances
                if i > 0:
                    prev_node = route_nodes[i - 1]
                    edge_data = self.G.get_edge_data(prev_node, node)
                    if edge_data:
                        # In OSMnx MultiDiGraph, edge_data is dict with edge keys as integers
                        # Get the first edge (0 is typically the main road)
                        if isinstance(edge_data, dict) and len(edge_data) > 0:
                            # Get first edge's data (dict keys are edge indices like 0, 1, etc)
                            first_edge = edge_data[0] if 0 in edge_data else next(iter(edge_data.values()))
                            if isinstance(first_edge, dict) and "length" in first_edge:
                                total_distance += first_edge["length"] / 1000  # Convert m to km

            # Estimate travel time
            estimated_time = self._estimate_travel_time(
                total_distance,
                time_of_day=time_of_day,
                traffic_factor=1.0
            )

            # Calculate risk score
            risk_score = self._calculate_risk_score(
                total_distance,
                delay_probability=delay_probability,
                time_of_day=time_of_day,
                weather_conditions=weather
            )

            return RouteInfo(
                route_name="Primary Route",
                coordinates=coordinates,
                distance_km=total_distance,
                estimated_time_min=estimated_time,
                node_ids=route_nodes,
                risk_score=risk_score,
                metadata={
                    "algorithm": "shortest_path",
                    "network_nodes": len(route_nodes),
                    "delay_prob": delay_probability
                }
            )

        except Exception as e:
            logger.error(f"Error calculating primary route: {e}")
            return None

    def calculate_alternate_routes(
        self,
        origin_lat: float,
        origin_lon: float,
        dest_lat: float,
        dest_lon: float,
        num_alternatives: int = 2,
        delay_probability: float = None,
        time_of_day: int = None,
        weather: str = "clear"
    ) -> List[RouteInfo]:
        """
        Calculate alternate routes using different strategy (e.g., distance-aware).
        
        Args:
            origin_lat, origin_lon: Starting coordinates
            dest_lat, dest_lon: Destination coordinates
            num_alternatives: Number of alternate routes to generate (1-3)
            delay_probability: Predicted delay probability
            time_of_day: Hour (0-23)
            weather: "clear", "rain", or "storm"
            
        Returns:
            List of RouteInfo objects for alternate routes
        """
        try:
            if self.G is None:
                raise ValueError("Network not loaded")

            alternates = []
            origin_node = self._get_nearest_node(origin_lat, origin_lon)
            dest_node = self._get_nearest_node(dest_lat, dest_lon)

            # Strategy 1: Prefer avoiding main roads (via "residential" preference)
            # We'll perturb edge weights to find different paths
            for alt_idx in range(num_alternatives):
                try:
                    # Create a copy with perturbed weights
                    G_temp = self.G.copy()
                    
                    # Multiply some edge weights by a factor to avoid certain roads
                    for u, v, key, data in G_temp.edges(keys=True, data=True):
                        highway_type = data.get("highway", "residential")
                        
                        # If it's a main road in this iteration, penalize it
                        if alt_idx == 0:
                            if isinstance(highway_type, list):
                                highway_type = highway_type[0]
                            if highway_type in ["motorway", "trunk", "primary"]:
                                G_temp[u][v][key]["length"] *= 1.5  # 50% penalty
                        elif alt_idx == 1:
                            if isinstance(highway_type, list):
                                highway_type = highway_type[0]
                            if highway_type in ["secondary", "tertiary"]:
                                G_temp[u][v][key]["length"] *= 1.3

                    # Calculate path
                    route_nodes = nx.shortest_path(G_temp, origin_node, dest_node, weight="length")

                    # Extract coordinates and distance
                    coordinates = []
                    total_distance = 0.0
                    
                    for i, node in enumerate(route_nodes):
                        lat = G_temp.nodes[node]["y"]
                        lon = G_temp.nodes[node]["x"]
                        coordinates.append((lat, lon))
                        
                        if i > 0:
                            prev_node = route_nodes[i - 1]
                            edge_data = G_temp.get_edge_data(prev_node, node)
                            if edge_data:
                                # Handle MultiDiGraph edge structure
                                if isinstance(edge_data, dict) and len(edge_data) > 0:
                                    # Get first edge's data
                                    first_edge = edge_data[0] if 0 in edge_data else next(iter(edge_data.values()))
                                    if isinstance(first_edge, dict) and "length" in first_edge:
                                        total_distance += first_edge["length"] / 1000

                    # Estimate time (slightly slower due to road preference)
                    traffic_factor = 1.0 + (alt_idx * 0.1)  # Slightly slower alternatives
                    estimated_time = self._estimate_travel_time(
                        total_distance,
                        time_of_day=time_of_day,
                        traffic_factor=traffic_factor
                    )

                    # Calculate risk
                    risk_score = self._calculate_risk_score(
                        total_distance,
                        delay_probability=delay_probability,
                        time_of_day=time_of_day,
                        weather_conditions=weather
                    )

                    alternates.append(RouteInfo(
                        route_name=f"Alternative Route {alt_idx + 1}",
                        coordinates=coordinates,
                        distance_km=total_distance,
                        estimated_time_min=estimated_time,
                        node_ids=route_nodes,
                        risk_score=risk_score,
                        metadata={
                            "algorithm": f"perturbed_shortest_path_{alt_idx}",
                            "network_nodes": len(route_nodes),
                            "traffic_factor": traffic_factor
                        }
                    ))
                except nx.NetworkXNoPath:
                    logger.warning(f"No alternate path found for alternative {alt_idx + 1}")
                    continue

            return alternates

        except Exception as e:
            logger.error(f"Error calculating alternate routes: {e}")
            return []

    def get_all_routes(
        self,
        origin_lat: float,
        origin_lon: float,
        dest_lat: float,
        dest_lon: float,
        num_alternatives: int = 2,
        delay_probability: float = None,
        time_of_day: int = None,
        weather: str = "clear"
    ) -> Dict:
        """
        Calculate primary + alternate routes in one call.
        
        Returns:
            Dictionary with routes and comparison info
        """
        # Ensure network is loaded
        if self.G is None:
            logger.info("Network not loaded. Loading OSM network...")
            self.load_network(network_type="drive")
        
        primary = self.calculate_primary_route(
            origin_lat, origin_lon, dest_lat, dest_lon,
            delay_probability=delay_probability,
            time_of_day=time_of_day,
            weather=weather
        )

        alternates = self.calculate_alternate_routes(
            origin_lat, origin_lon, dest_lat, dest_lon,
            num_alternatives=num_alternatives,
            delay_probability=delay_probability,
            time_of_day=time_of_day,
            weather=weather
        )

        all_routes = [primary] + alternates if primary else alternates

        return {
            "primary_route": primary.to_dict() if primary else None,
            "alternate_routes": [r.to_dict() for r in alternates],
            "all_routes": [r.to_dict() for r in all_routes],
            "recommended_route": min(all_routes, key=lambda r: r.risk_score).to_dict() if all_routes else None,
            "summary": {
                "total_routes": len(all_routes),
                "origin": {"lat": origin_lat, "lon": origin_lon},
                "destination": {"lat": dest_lat, "lon": dest_lon},
                "predicted_delay_prob": delay_probability
            }
        }
