import requests
from datetime import datetime, timedelta
import os
import time
from tqdm import tqdm
import logging
from pathlib import Path
import json
from shapely.geometry import Polygon
import getpass

# Configure logging
logging.basicConfig(
    filename='sentinel_download.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MoroccoSentinelDownloader:
    def __init__(self, username, password):
        """Initialize with Data Space Ecosystem credentials"""
        self.username = username
        self.password = password
        self.base_url = "https://catalogue.dataspace.copernicus.eu/odata/v1"
        self.download_base_url = "https://zipper.dataspace.copernicus.eu/odata/v1"
        
        # Get access token
        try:
            self.get_token()
            logger.info("Successfully connected to Copernicus Data Space")
        except Exception as e:
            logger.error(f"Failed to connect: {str(e)}")
            raise Exception("Could not connect to Copernicus Data Space. Please check your credentials.")

    def get_token(self):
        """Get authentication token"""
        auth_url = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"
        data = {
            'grant_type': 'password',
            'username': self.username,
            'password': self.password,
            'client_id': 'cdse-public'
        }
        
        response = requests.post(auth_url, data=data)
        if response.status_code == 200:
            self.token = response.json()['access_token']
            self.headers = {'Authorization': f'Bearer {self.token}'}
        else:
            raise Exception(f"Authentication failed: {response.text}")

    def create_search_polygon(self, region):
        """Create search polygon for region"""
        # Élargir les zones de recherche pour le Maroc
        regions = {
            'north': {
                'min_lon': -7.0,  # Élargi vers l'ouest
                'max_lon': -1.0,  # Élargi vers l'est
                'min_lat': 32.0,  # Ajusté pour le nord du Maroc
                'max_lat': 36.0
            },
            'central': {
                'min_lon': -13.0,  # Élargi pour inclure la côte
                'max_lon': -2.0,
                'min_lat': 29.0,
                'max_lat': 32.0
            },
            'south': {
                'min_lon': -13.0,
                'max_lon': -1.0,
                'min_lat': 26.0,  # Ajusté pour le sud du Maroc
                'max_lat': 29.0
            }
        }
        
        if region not in regions:
            return None
        
        bounds = regions[region]
        polygon = f"POLYGON(({bounds['min_lon']} {bounds['min_lat']}, "\
                  f"{bounds['max_lon']} {bounds['min_lat']}, "\
                  f"{bounds['max_lon']} {bounds['max_lat']}, "\
                  f"{bounds['min_lon']} {bounds['max_lat']}, "\
                  f"{bounds['min_lon']} {bounds['min_lat']}))"
        
        return polygon

    def search_scenes(self, region, start_date, end_date, max_cloud_percentage=30):
        """Search for scenes using CDSE API"""
        max_attempts = 3
        wait_time = 30
        
        for attempt in range(max_attempts):
            try:
                footprint = self.create_search_polygon(region)
                if not footprint:
                    logger.error(f"Invalid region: {region}")
                    return []

                logger.info(f"Searching for L2A scenes in {region} from {start_date} to {end_date}")
                
                # Format dates
                start_str = start_date.strftime("%Y-%m-%dT%H:%M:%SZ")
                end_str = end_date.strftime("%Y-%m-%dT%H:%M:%SZ")
                
                # Simplified query with less restrictive filters
                query = (
                    f"{self.base_url}/Products?$filter="
                    f"Collection/Name eq 'SENTINEL-2' "
                    f"and contains(Name,'MSIL2A') "
                    f"and OData.CSC.Intersects(area=geography'SRID=4326;{footprint}') "
                    f"and ContentDate/Start ge '{start_str}' "  # Changed gt to ge (greater or equal)
                    f"and ContentDate/Start le '{end_str}' "    # Changed lt to le (less or equal)
                    f"and Attributes/OData.CSC.DoubleAttribute/any(att:att/Name eq 'cloudCover' "
                    f"and att/Value le {max_cloud_percentage})"
                    f"&$orderby=ContentDate/Start desc"
                )
                
                logger.debug(f"Query URL: {query}")  # Add this line to debug the query
                
                response = requests.get(
                    query,
                    headers=self.headers
                )
                
                if response.status_code == 200:
                    products = response.json().get('value', [])
                    logger.debug(f"Raw API response: {response.text}")  # Add this line for debugging
                    
                    if not products:
                        logger.warning(f"No products found for region {region} in date range")
                        return []
                    
                    logger.info(f"Found {len(products)} products")
                    return products
                else:
                    raise Exception(f"Search failed: {response.text}")
                
            except Exception as e:
                if attempt < max_attempts - 1:
                    wait_time *= (attempt + 1)
                    logger.warning(f"Search error, retrying in {wait_time} seconds... ({attempt + 1}/{max_attempts})")
                    time.sleep(wait_time)
                    self.get_token()
                else:
                    logger.error(f"Failed after {max_attempts} attempts: {str(e)}")
                    return []

    def get_cloud_cover(self, product):
        """Extract cloud cover from product metadata safely"""
        try:
            # Try different possible locations for cloud cover
            if 'CloudCover' in product:
                return float(product['CloudCover'])
            elif 'Properties' in product and 'cloudCover' in product['Properties']:
                return float(product['Properties']['cloudCover'])
            elif 'Attributes' in product:
                for attr in product['Attributes']:
                    if attr.get('Name') == 'cloudCover':
                        return float(attr.get('Value', 100))
            return 100  # Default if not found
        except (ValueError, TypeError):
            return 100

    def download_sentinel_images(self, regions, start_date, end_date, output_base_dir, 
                            max_cloud_percentage=30):
        """Main download method"""
        output_base_dir = Path(output_base_dir)
        output_base_dir.mkdir(parents=True, exist_ok=True)
        
        total_products = 0
        downloaded_products = 0
        
        # Process each region
        for region in regions:
            logger.info(f"\nProcessing region: {region}")
            print(f"\nProcessing region: {region}")
            
            region_dir = output_base_dir / region
            region_dir.mkdir(exist_ok=True)
            
            # Search for products
            products = self.search_scenes(
                region,
                start_date,
                end_date,
                max_cloud_percentage
            )
            
            if products:
                total_products += len(products)
                print(f"Found {len(products)} products for {region}")
                
                # Sort products by cloud cover
                sorted_products = sorted(products, key=lambda x: self.get_cloud_cover(x))
                
                for product in sorted_products:
                    try:
                        cloud_cover = self.get_cloud_cover(product)
                        print(f"\nDownloading: {product['Name']}")
                        print(f"Cloud coverage: {cloud_cover:.1f}%")
                        print(f"Product ID: {product['Id']}")
                        
                        if self.download_product(product, str(region_dir)):
                            downloaded_products += 1
                            print(f"Successfully downloaded: {product['Name']}")
                        
                        # Add delay between downloads
                        time.sleep(5)
                        
                    except Exception as e:
                        logger.error(f"Error processing {product['Name']}: {str(e)}")
            else:
                print(f"No products found for {region}")
        
        # Print final summary
        print("\nDownload Summary:")
        print(f"Total products found: {total_products}")
        print(f"Successfully downloaded: {downloaded_products}")
        print(f"Failed downloads: {total_products - downloaded_products}")

    def download_product(self, product, output_dir):
        """Download a single product"""
        max_retries = 3
        retry_delay = 30
        
        for attempt in range(max_retries):
            try:
                product_id = product['Id']
                product_title = product['Name']
                
                # Get download URL
                download_url = f"{self.download_base_url}/Products({product_id})/$value"
                
                logger.info(f"Downloading product with bands B02(Blue), B03(Green), B04(Red), B08(NIR) at 10m resolution")
                
                # Start download with streaming
                with requests.get(download_url, headers=self.headers, stream=True) as r:
                    r.raise_for_status()
                    total_size = int(r.headers.get('content-length', 0))
                    
                    output_file = Path(output_dir) / f"{product_title}.zip"
                    
                    with open(output_file, 'wb') as f:
                        with tqdm(
                            total=total_size,
                            unit='iB',
                            unit_scale=True,
                            desc=f"{product_title} (10m - B02,B03,B04,B08)"
                        ) as pbar:
                            for chunk in r.iter_content(chunk_size=8192):
                                size = f.write(chunk)
                                pbar.update(size)
                    
                return True
                
            except Exception as e:
                if attempt < max_retries - 1:
                    retry_delay *= (attempt + 1)
                    logger.warning(f"Download failed, retrying in {retry_delay} seconds... ({attempt + 1}/{max_retries})")
                    time.sleep(retry_delay)
                    # Refresh token before retry
                    self.get_token()
                else:
                    logger.error(f"Failed to download after {max_retries} attempts: {str(e)}")
                    return False

def get_user_credentials():
    """Prompt user for Copernicus Data Space credentials"""
    print("\nPlease enter your Copernicus Data Space credentials:")
    username = input("Username: ")
    password = getpass.getpass("Password: ")
    return username, password

def main():
    # Get credentials from user
    try:
        username, password = get_user_credentials()
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        return
    
    try:
        # Initialize downloader with user credentials
        downloader = MoroccoSentinelDownloader(username, password)
        
        # Example usage
        regions = ['north', 'central', 'south']
        start_date = datetime(2023, 6, 1)
        end_date = datetime(2023, 6, 30)
        output_dir = 'morocco_sentinel_data'
        
        print("\nStarting Sentinel-2 download process...")
        print(f"Date range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        print(f"Regions: {', '.join(regions)}")
        print(f"Output directory: {output_dir}")
        
        # Start download
        downloader.download_sentinel_images(
            regions=regions,
            start_date=start_date,
            end_date=end_date,
            output_base_dir=output_dir,
            max_cloud_percentage=30
        )
    except Exception as e:
        print(f"\nError: {str(e)}")
        logger.error(f"Program error: {str(e)}")

if __name__ == "__main__":
    main()