"""
API Client for Illinois Fiscal Data API

This module provides a Python client to interact with the Fiscal Data REST API.
Used by ADK agent tools to fetch data from the API layer.

Usage:
    from utils.api_client import FiscalDataClient
    
    client = FiscalDataClient(base_url="http://localhost:5000")
    entities = client.search_entities("Skokie")
    revenues = client.get_entity_revenues("016/020/32")
"""

import requests
from typing import Optional, Dict, Any, List
import os


class FiscalDataClient:
    """Client for the Illinois Fiscal Data REST API."""
    
    def __init__(self, base_url: Optional[str] = None, timeout: int = 30):
        """
        Initialize the API client.
        
        Args:
            base_url: API base URL (default: from env or localhost:5000)
            timeout: Request timeout in seconds
        """
        self.base_url = base_url or os.environ.get(
            'FISCAL_API_URL', 
            'http://localhost:5000'
        )
        self.timeout = timeout
        self._session = requests.Session()
    
    def _make_request(
        self, 
        method: str, 
        endpoint: str, 
        params: Optional[Dict] = None,
        json_data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Make an HTTP request to the API.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            params: Query parameters
            json_data: JSON body for POST requests
            
        Returns:
            API response as dictionary
        """
        url = f"{self.base_url}{endpoint}"
        
        try:
            response = self._session.request(
                method=method,
                url=url,
                params=params,
                json=json_data,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.Timeout:
            return {"status": "error", "error_message": "Request timed out"}
        except requests.exceptions.ConnectionError:
            return {"status": "error", "error_message": f"Could not connect to API at {self.base_url}"}
        except requests.exceptions.HTTPError as e:
            try:
                return response.json()
            except:
                return {"status": "error", "error_message": str(e)}
        except Exception as e:
            return {"status": "error", "error_message": str(e)}
    
    # -------------------------------------------------------------------------
    # HEALTH CHECK
    # -------------------------------------------------------------------------
    
    def health_check(self) -> Dict[str, Any]:
        """Check if the API is healthy."""
        return self._make_request("GET", "/api/v1/health")
    
    # -------------------------------------------------------------------------
    # ENTITY METHODS
    # -------------------------------------------------------------------------
    
    def search_entities(
        self, 
        search_term: str, 
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        Search for government entities by name.
        
        Args:
            search_term: Name or partial name to search for
            limit: Maximum number of results
            
        Returns:
            dict with status and list of matching entities
        """
        return self._make_request(
            "GET", 
            "/api/v1/entities/search",
            params={"q": search_term, "limit": limit}
        )
    
    def get_entity_details(self, entity_code: str) -> Dict[str, Any]:
        """
        Get details for a specific entity.
        
        Args:
            entity_code: Entity code (format: XXX/YYY/ZZ)
            
        Returns:
            dict with status and entity details
        """
        return self._make_request("GET", f"/api/v1/entities/{entity_code}")
    
    # -------------------------------------------------------------------------
    # FINANCIAL DATA METHODS
    # -------------------------------------------------------------------------
    
    def get_entity_revenues(self, entity_code: str) -> Dict[str, Any]:
        """
        Get revenue breakdown for an entity.
        
        Args:
            entity_code: Entity code
            
        Returns:
            dict with revenue details by category
        """
        return self._make_request("GET", f"/api/v1/entities/{entity_code}/revenues")
    
    def get_entity_expenditures(self, entity_code: str) -> Dict[str, Any]:
        """
        Get expenditure breakdown for an entity.
        
        Args:
            entity_code: Entity code
            
        Returns:
            dict with expenditure details by category
        """
        return self._make_request("GET", f"/api/v1/entities/{entity_code}/expenditures")
    
    def get_entity_debt(self, entity_code: str) -> Dict[str, Any]:
        """
        Get debt information for an entity.
        
        Args:
            entity_code: Entity code
            
        Returns:
            dict with debt details
        """
        return self._make_request("GET", f"/api/v1/entities/{entity_code}/debt")
    
    def get_entity_pensions(self, entity_code: str) -> Dict[str, Any]:
        """
        Get pension information for an entity.
        
        Args:
            entity_code: Entity code
            
        Returns:
            dict with pension system details
        """
        return self._make_request("GET", f"/api/v1/entities/{entity_code}/pensions")
    
    # -------------------------------------------------------------------------
    # GEOGRAPHIC METHODS
    # -------------------------------------------------------------------------
    
    def get_county_entities(
        self, 
        county: str, 
        entity_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get all entities in a county.
        
        Args:
            county: County name
            entity_type: Optional filter by entity type
            
        Returns:
            dict with list of entities in the county
        """
        params = {}
        if entity_type:
            params["entity_type"] = entity_type
            
        return self._make_request(
            "GET", 
            f"/api/v1/counties/{county}/entities",
            params=params if params else None
        )
    
    def get_county_summary(self, county: str) -> Dict[str, Any]:
        """
        Get aggregated summary for a county.
        
        Args:
            county: County name
            
        Returns:
            dict with county statistics
        """
        return self._make_request("GET", f"/api/v1/counties/{county}/summary")
    
    # -------------------------------------------------------------------------
    # COMPARISON METHODS
    # -------------------------------------------------------------------------
    
    def compare_entities(self, entity_codes: List[str]) -> Dict[str, Any]:
        """
        Compare multiple entities.
        
        Args:
            entity_codes: List of entity codes to compare
            
        Returns:
            dict with comparison data
        """
        codes_str = ",".join(entity_codes)
        return self._make_request(
            "GET", 
            "/api/v1/entities/compare",
            params={"codes": codes_str}
        )
    
    def rank_entities(
        self,
        metric: str = "population",
        entity_type: Optional[str] = None,
        county: Optional[str] = None,
        order: str = "top",
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        Rank entities by a metric.
        
        Args:
            metric: Ranking metric (population, eav, employees)
            entity_type: Filter by entity type
            county: Filter by county
            order: "top" or "bottom"
            limit: Maximum results
            
        Returns:
            dict with ranked entities
        """
        params = {
            "metric": metric,
            "order": order,
            "limit": limit
        }
        if entity_type:
            params["entity_type"] = entity_type
        if county:
            params["county"] = county
            
        return self._make_request(
            "GET", 
            "/api/v1/entities/rank",
            params=params
        )
    
    # -------------------------------------------------------------------------
    # CONTEXT MANAGER SUPPORT
    # -------------------------------------------------------------------------
    
    def close(self):
        """Close the HTTP session."""
        self._session.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

# Global client instance
_default_client: Optional[FiscalDataClient] = None


def get_client() -> FiscalDataClient:
    """Get or create the default API client."""
    global _default_client
    if _default_client is None:
        _default_client = FiscalDataClient()
    return _default_client


def search_entities(search_term: str, limit: int = 10) -> Dict[str, Any]:
    """Search for entities using the default client."""
    return get_client().search_entities(search_term, limit)


def get_entity_details(entity_code: str) -> Dict[str, Any]:
    """Get entity details using the default client."""
    return get_client().get_entity_details(entity_code)


def get_entity_revenues(entity_code: str) -> Dict[str, Any]:
    """Get entity revenues using the default client."""
    return get_client().get_entity_revenues(entity_code)


def get_entity_expenditures(entity_code: str) -> Dict[str, Any]:
    """Get entity expenditures using the default client."""
    return get_client().get_entity_expenditures(entity_code)


# =============================================================================
# TEST
# =============================================================================

if __name__ == "__main__":
    """Test the API client."""
    print("Testing Fiscal Data API Client...")
    
    client = FiscalDataClient()
    
    # Test health check
    print("\n1. Health Check:")
    result = client.health_check()
    print(f"   Status: {result.get('status')}")
    print(f"   Data Source: {result.get('data_source')}")
    
    # Test entity search
    print("\n2. Search for 'Skokie':")
    result = client.search_entities("Skokie")
    print(f"   Status: {result.get('status')}")
    print(f"   Count: {result.get('count')}")
    if result.get('entities'):
        for entity in result['entities'][:3]:
            print(f"   - {entity.get('UnitName')} ({entity.get('EntityType')}, {entity.get('County')} County)")
    
    # Test entity details
    print("\n3. Get entity details for '016/020/32':")
    result = client.get_entity_details("016/020/32")
    if result.get('status') == 'success':
        entity = result.get('entity', {})
        print(f"   Name: {entity.get('UnitName')}")
        print(f"   Population: {entity.get('Population'):,}" if entity.get('Population') else "   Population: N/A")
    else:
        print(f"   Error: {result.get('error_message')}")
    
    # Test county entities
    print("\n4. Get entities in Cook County:")
    result = client.get_county_entities("Cook", entity_type="Village")
    print(f"   Status: {result.get('status')}")
    print(f"   Count: {result.get('count')}")
    
    print("\n✅ API Client tests complete!")
