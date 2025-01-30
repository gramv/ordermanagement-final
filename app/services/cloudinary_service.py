# app/services/cloudinary_service.py
import cloudinary
import cloudinary.uploader
from cloudinary import api
from flask import current_app
import os

class CloudinaryService:
    def __init__(self):
        try:
            # Configuration is already done in Config class
            # Just verify the configuration
            ping_result = api.ping()
            current_app.logger.info("Cloudinary configured successfully")
        except Exception as e:
            current_app.logger.error(f"Error configuring Cloudinary: {str(e)}")
            raise

    def upload_invoice(self, file_path, invoice_id=None):
        """
        Upload invoice to Cloudinary
        Args:
            file_path: Path to the file to upload
            invoice_id: Optional invoice ID for naming the file
        Returns: dict with public_id, url, secure_url, and signature
        """
        try:
            # Verify file exists
            if not os.path.exists(file_path):
                raise ValueError(f"File not found: {file_path}")

            current_app.logger.info(f"Attempting to upload file: {file_path}")
            
            # Add additional error checking
            if not file_path:
                raise ValueError("Missing required parameter: file_path")
            
            # Generate a unique identifier if no invoice_id is provided
            public_id = f"invoice_{invoice_id}" if invoice_id else f"invoice_temp_{os.path.basename(file_path)}"
                
            # Upload with error handling
            result = cloudinary.uploader.upload(
                file_path,
                folder="invoices",
                public_id=public_id,
                resource_type="auto",
                timeout=60  # Add timeout
            )
            
            if not result or 'public_id' not in result or 'secure_url' not in result:
                raise ValueError("Invalid response from Cloudinary")
            
            current_app.logger.info(f"Upload successful: {result['public_id']}")
            return result
        except Exception as e:
            current_app.logger.error(f"Cloudinary upload error: {str(e)}")
            raise

    def delete_invoice(self, public_id):
        """Delete invoice from Cloudinary"""
        try:
            if not public_id:
                raise ValueError("public_id is required")
            result = cloudinary.uploader.destroy(public_id)
            return result.get('result') == 'ok'
        except Exception as e:
            current_app.logger.error(f"Cloudinary delete error: {str(e)}")
            raise