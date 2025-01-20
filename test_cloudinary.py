# test_cloudinary.py
import os
from dotenv import load_dotenv
import cloudinary
import cloudinary.uploader
import cloudinary.api  # Add this import

def test_cloudinary():
    # Load environment variables
    load_dotenv()
    
    print("\nTesting Cloudinary Configuration:")
    
    # Configure Cloudinary
    cloudinary.config(
        cloud_name="djfgi2trd",
        api_key="292342398526215",
        api_secret="oS0-6YmuMCVvA7itLgWF67_ah7w",
        secure=True
    )
    
    try:
        # Test configuration
        print(f"\nCloud name: {cloudinary.config().cloud_name}")
        print(f"API key length: {len(str(cloudinary.config().api_key))}")
        print(f"API secret length: {len(str(cloudinary.config().api_secret))}")
        
        # Test API connection
        result = cloudinary.api.ping()
        print("\nCloudinary connection successful!")
        print(f"API Response: {result}")
        
    except Exception as e:
        print(f"\nCloudinary error: {str(e)}")
        print("Full configuration:")
        print(f"Cloud name: {cloudinary.config().cloud_name}")
        print(f"API key exists: {'Yes' if cloudinary.config().api_key else 'No'}")
        print(f"API secret exists: {'Yes' if cloudinary.config().api_secret else 'No'}")

if __name__ == "__main__":
    test_cloudinary()