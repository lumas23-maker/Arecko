"""
Video processing utilities using FFmpeg.
Handles compression, format conversion, and thumbnail generation.
"""
import os
import tempfile
import subprocess
import ffmpeg
from django.core.files.base import ContentFile


def get_video_info(input_path):
    """Get video metadata (duration, width, height, etc.)"""
    try:
        probe = ffmpeg.probe(input_path)
        video_stream = next(
            (stream for stream in probe['streams'] if stream['codec_type'] == 'video'),
            None
        )
        if video_stream:
            return {
                'width': int(video_stream.get('width', 0)),
                'height': int(video_stream.get('height', 0)),
                'duration': float(probe['format'].get('duration', 0)),
                'size': int(probe['format'].get('size', 0)),
                'codec': video_stream.get('codec_name', ''),
            }
    except Exception as e:
        print(f"[VIDEO] Error getting video info: {e}")
    return None


def compress_video(input_path, output_path, target_width=720, crf=28):
    """
    Compress video for web delivery.

    Args:
        input_path: Path to input video
        output_path: Path for compressed output
        target_width: Max width (height scales proportionally)
        crf: Constant Rate Factor (18-28, higher = smaller file, lower quality)
    """
    try:
        # Get original dimensions
        info = get_video_info(input_path)
        if not info:
            return False

        # Calculate scaled dimensions (maintain aspect ratio)
        if info['width'] > target_width:
            scale = f"scale={target_width}:-2"  # -2 ensures even number for height
        else:
            scale = f"scale={info['width']}:-2"  # Keep original if smaller

        # Run FFmpeg compression
        (
            ffmpeg
            .input(input_path)
            .output(
                output_path,
                vcodec='libx264',
                crf=crf,
                preset='medium',
                acodec='aac',
                audio_bitrate='128k',
                movflags='faststart',  # Enable streaming
                vf=scale
            )
            .overwrite_output()
            .run(capture_stdout=True, capture_stderr=True)
        )

        # Log compression results
        original_size = info['size']
        compressed_size = os.path.getsize(output_path)
        reduction = ((original_size - compressed_size) / original_size) * 100
        print(f"[VIDEO] Compressed: {original_size/1024/1024:.1f}MB -> {compressed_size/1024/1024:.1f}MB ({reduction:.1f}% reduction)")

        return True
    except ffmpeg.Error as e:
        print(f"[VIDEO] FFmpeg error: {e.stderr.decode() if e.stderr else str(e)}")
        return False
    except Exception as e:
        print(f"[VIDEO] Compression error: {e}")
        return False


def generate_thumbnail(input_path, output_path, time_offset=1):
    """
    Generate a thumbnail image from video.

    Args:
        input_path: Path to video
        output_path: Path for thumbnail (jpg)
        time_offset: Seconds into video to capture frame
    """
    try:
        (
            ffmpeg
            .input(input_path, ss=time_offset)
            .output(output_path, vframes=1, format='image2', vcodec='mjpeg', q=2)
            .overwrite_output()
            .run(capture_stdout=True, capture_stderr=True)
        )
        print(f"[VIDEO] Thumbnail generated: {output_path}")
        return True
    except ffmpeg.Error as e:
        print(f"[VIDEO] Thumbnail error: {e.stderr.decode() if e.stderr else str(e)}")
        return False
    except Exception as e:
        print(f"[VIDEO] Thumbnail error: {e}")
        return False


def convert_to_mp4(input_path, output_path):
    """
    Convert video to MP4 format for web compatibility.
    """
    try:
        (
            ffmpeg
            .input(input_path)
            .output(
                output_path,
                vcodec='libx264',
                acodec='aac',
                movflags='faststart'
            )
            .overwrite_output()
            .run(capture_stdout=True, capture_stderr=True)
        )
        print(f"[VIDEO] Converted to MP4: {output_path}")
        return True
    except ffmpeg.Error as e:
        print(f"[VIDEO] Conversion error: {e.stderr.decode() if e.stderr else str(e)}")
        return False
    except Exception as e:
        print(f"[VIDEO] Conversion error: {e}")
        return False


def process_uploaded_video(uploaded_file):
    """
    Process an uploaded video file:
    1. Save to temp file
    2. Compress video
    3. Generate thumbnail
    4. Return processed video and thumbnail as file objects

    Args:
        uploaded_file: Django UploadedFile object

    Returns:
        dict with 'video' and 'thumbnail' ContentFile objects, or None on failure
    """
    temp_dir = tempfile.mkdtemp()

    try:
        # Save uploaded file to temp location
        input_path = os.path.join(temp_dir, 'input_video')
        with open(input_path, 'wb') as f:
            for chunk in uploaded_file.chunks():
                f.write(chunk)

        # Get original file info
        info = get_video_info(input_path)
        if not info:
            print("[VIDEO] Could not read video info, skipping processing")
            return None

        print(f"[VIDEO] Processing: {info['width']}x{info['height']}, {info['duration']:.1f}s, {info['size']/1024/1024:.1f}MB")

        # Compress video
        compressed_path = os.path.join(temp_dir, 'compressed.mp4')
        if not compress_video(input_path, compressed_path):
            print("[VIDEO] Compression failed, using original")
            compressed_path = input_path

        # Generate thumbnail
        thumbnail_path = os.path.join(temp_dir, 'thumbnail.jpg')
        thumbnail_time = min(1, info['duration'] / 2)  # 1 second or middle of video
        generate_thumbnail(input_path, thumbnail_path, time_offset=thumbnail_time)

        # Read processed files into memory
        result = {}

        with open(compressed_path, 'rb') as f:
            video_content = f.read()
            original_name = getattr(uploaded_file, 'name', 'video.mp4')
            base_name = os.path.splitext(original_name)[0]
            result['video'] = ContentFile(video_content, name=f"{base_name}.mp4")

        if os.path.exists(thumbnail_path):
            with open(thumbnail_path, 'rb') as f:
                thumb_content = f.read()
                result['thumbnail'] = ContentFile(thumb_content, name=f"{base_name}_thumb.jpg")

        return result

    except Exception as e:
        print(f"[VIDEO] Processing failed: {e}")
        return None
    finally:
        # Cleanup temp files
        import shutil
        try:
            shutil.rmtree(temp_dir)
        except:
            pass


def is_video_file(filename):
    """Check if file is a video based on extension."""
    if not filename:
        return False
    video_extensions = ('.mp4', '.mov', '.avi', '.webm', '.mkv', '.flv', '.wmv', '.m4v')
    return filename.lower().endswith(video_extensions)
