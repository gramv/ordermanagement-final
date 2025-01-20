# app/services/cloudinary_service.py
import cloudinary
import cloudinary.uploader
from cloudinary import api  # Added this import
from flask import current_app

class CloudinaryService:
    def __init__(self):
        try:
            # Direct configuration with credentials
            cloudinary.config(
                cloud_name="djfgi2trd",
                api_key="292342398526215",
                api_secret="oS0-6YmuMCVvA7itLgWF67_ah7w",
                secure=True
            )
            # Verify configuration with a ping
            ping_result = api.ping()
            current_app.logger.info("Cloudinary configured successfully")
        except Exception as e:
            current_app.logger.error(f"Error configuring Cloudinary: {str(e)}")
            raise

    def upload_invoice(self, file_path, invoice_id):
        """
        Upload invoice to Cloudinary
        Returns: dict with public_id and secure_url
        """
        try:
            current_app.logger.info(f"Attempting to upload file: {file_path}")
            result = cloudinary.uploader.upload(
                file_path,
                folder="invoices",
                public_id=f"invoice_{invoice_id}",
                resource_type="auto"
            )
            
            current_app.logger.info(f"Upload successful: {result['public_id']}")
            return {
                'public_id': result['public_id'],
                'secure_url': result['secure_url']
            }
        except Exception as e:
            current_app.logger.error(f"Cloudinary upload error: {str(e)}")
            raise

    def delete_invoice(self, public_id):
        """Delete invoice from Cloudinary"""
        try:
            cloudinary.uploader.destroy(public_id)
            return True
        except Exception as e:
            current_app.logger.error(f"Cloudinary delete error: {str(e)}")
            raise