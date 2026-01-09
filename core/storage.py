"""
Custom Cloudinary storage for handling video and image uploads.
"""
from cloudinary_storage.storage import MediaCloudinaryStorage
import cloudinary


VIDEO_EXTENSIONS = ('.mp4', '.mov', '.avi', '.webm', '.mkv', '.flv', '.wmv', '.m4v')
IMAGE_EXTENSIONS = ('.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.tiff', '.svg')


class AutoMediaCloudinaryStorage(MediaCloudinaryStorage):
    """
    Custom storage that uses resource_type='auto' for uploads to automatically
    detect whether uploaded file is an image, video, or raw file.
    For URL generation, uses the correct resource_type based on file extension.
    """

    def _get_resource_type(self, name):
        """
        Determine resource type based on file extension.
        Returns 'video' for video files, 'image' for images.
        """
        if name:
            lower_name = name.lower()
            if lower_name.endswith(VIDEO_EXTENSIONS):
                return 'video'
        return 'image'

    def _upload_resource_type(self, name):
        """Use 'auto' for uploads so Cloudinary auto-detects the type."""
        return 'auto'

    def _save(self, name, content):
        """Override save to use resource_type='auto' for uploads."""
        from cloudinary_storage.storage import RESOURCE_TYPES

        # Get the original resource type method
        original_method = self._get_resource_type

        # Temporarily override to use 'auto' for upload
        self._get_resource_type = lambda n: 'auto'

        try:
            result = super()._save(name, content)
        finally:
            # Restore original method
            self._get_resource_type = original_method

        return result

    def url(self, name):
        """
        Generate the URL with the correct resource_type for delivery.
        Cloudinary URLs must use 'video' or 'image', not 'auto'.
        """
        if not name:
            return None

        # Determine the correct resource type for this file
        resource_type = self._get_resource_type(name)

        # Build the Cloudinary URL with the correct resource type
        url = cloudinary.utils.cloudinary_url(
            name,
            resource_type=resource_type,
            type='upload'
        )[0]

        return url
