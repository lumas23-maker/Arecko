"""
Custom Cloudinary storage for handling video and image uploads.
"""
from cloudinary_storage.storage import MediaCloudinaryStorage
import cloudinary
import os


VIDEO_EXTENSIONS = ('.mp4', '.mov', '.avi', '.webm', '.mkv', '.flv', '.wmv', '.m4v')


class AutoMediaCloudinaryStorage(MediaCloudinaryStorage):
    """
    Custom storage that handles videos and images with correct resource_type.
    Videos are stored with '/videos/' in the path for later detection.
    """

    def _is_video_by_extension(self, name):
        """Check if file is a video based on extension."""
        if name:
            return name.lower().endswith(VIDEO_EXTENSIONS)
        return False

    def _is_video_by_path(self, name):
        """Check if file is a video based on path containing 'videos/'."""
        if name:
            return '/videos/' in name or name.startswith('videos/')
        return False

    def _is_video(self, name):
        """Check if file is a video by extension or path."""
        return self._is_video_by_extension(name) or self._is_video_by_path(name)

    def _get_resource_type(self, name):
        """Return 'video' for video files, 'image' for everything else."""
        return 'video' if self._is_video(name) else 'image'

    def _save(self, name, content):
        """
        Save file, putting videos in a 'videos/' subfolder.
        """
        # If it's a video, modify the path to include 'videos/'
        if self._is_video_by_extension(name):
            # Replace 'stories/' with 'stories/videos/' for videos
            if 'stories/' in name and '/videos/' not in name:
                name = name.replace('stories/', 'stories/videos/')

        return super()._save(name, content)

    def url(self, name):
        """
        Generate the URL with the correct resource_type for delivery.
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
