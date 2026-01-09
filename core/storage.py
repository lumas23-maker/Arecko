"""
Custom Cloudinary storage for handling video and image uploads.
"""
from cloudinary_storage.storage import MediaCloudinaryStorage


class AutoMediaCloudinaryStorage(MediaCloudinaryStorage):
    """
    Custom storage that uses resource_type='auto' to automatically
    detect whether uploaded file is an image, video, or raw file.
    This ensures videos are properly processed and playable.
    """

    def _get_resource_type(self, name):
        """Override to always return 'auto' for automatic detection."""
        return 'auto'
