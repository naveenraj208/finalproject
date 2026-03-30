# tools.py
import random

def get_traffic_density(zone: str):
    """Fetches real-time traffic sensor data for a specific city zone."""
    # Mock data simulation
    density = random.randint(10, 95)
    return {
        "zone": zone,
        "density": f"{density}%",
        "status": "Congested" if density > 70 else "Fluid",
        "last_update": "Just now"
    }

def optimize_power_grid(zone: str, target_load: int = 80):
    """Simulates shifting energy loads to prevent blackouts in a specific zone."""
    reduction = random.randint(5, 20)
    return {
        "action": "Load balancing initiated",
        "zone": zone,
        "load_reduction": f"{reduction}%",
        "new_stability_index": 0.92,
        "note": "Peak load redirected to storage."
    }

def query_air_quality(location: str):
    """Queries AQI sensors for environmental monitoring."""
    aqi = random.randint(15, 120)
    return {
        "location": location,
        "aqi": aqi,
        "category": "Good" if aqi < 50 else "Moderate",
        "pollutant": "PM2.5"
    }

def report_infrastructure_issue(issue_type: str, location: str):
    """Logs a city maintenance request in the central management system."""
    ticket_id = f"TICK-{random.randint(1000, 9999)}"
    return {
        "status": "Ticket Created",
        "ticket_id": ticket_id,
        "type": issue_type,
        "location": location,
        "priority": "High" if "hazard" in issue_type.lower() else "Medium"
    }

# Mapping of tool names to functions for the dispatcher
TOOL_MAP = {
    "get_traffic_density": get_traffic_density,
    "optimize_power_grid": optimize_power_grid,
    "query_air_quality": query_air_quality,
    "report_infrastructure_issue": report_infrastructure_issue
}
