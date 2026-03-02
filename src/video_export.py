"""Video export with burned-in subtitles using moviepy."""

from pathlib import Path
from typing import List, Optional

from moviepy.editor import VideoFileClip, TextClip, CompositeVideoClip

from .subtitle_extractor import Subtitle


class VideoExporter:
    """Export video with burned-in subtitles."""

    def __init__(
        self,
        font_size: int = 24,
        font: str = "Arial",
        font_color: str = "white",
        position: str = "bottom",
        margin: int = 10,
        background_opacity: float = 0.0,
    ):
        """Initialize video exporter.

        Args:
            font_size: Subtitle font size
            font: Font name
            font_color: Font color (color name or hex code)
            position: Subtitle position ('bottom', 'top', 'center')
            margin: Margin from edge in pixels
            background_opacity: Background opacity (0-1) for subtitle background
        """
        self.font_size = font_size
        self.font = font
        self.font_color = font_color
        self.position = position
        self.margin = margin
        self.background_opacity = background_opacity

    def create_subtitle_clip(
        self,
        subtitle: Subtitle,
        video_width: int,
        video_height: int,
    ) -> TextClip:
        """Create a TextClip for a single subtitle.

        Args:
            subtitle: Subtitle object
            video_width: Video width in pixels
            video_height: Video height in pixels

        Returns:
            TextClip object
        """
        # Create text clip
        txt_clip = TextClip(
            subtitle.text,
            fontsize=self.font_size,
            font=self.font,
            color=self.font_color,
            bg_color=f"black@{self.background_opacity}" if self.background_opacity > 0 else None,
            align="center",
            method="caption",
            size=(video_width * 0.8, None),  # 80% of video width
        )

        # Set position
        if self.position == "bottom":
            position = ("center", video_height - txt_clip.h - self.margin)
        elif self.position == "top":
            position = ("center", self.margin)
        elif self.position == "center":
            position = ("center", "center")
        else:
            position = ("center", video_height - txt_clip.h - self.margin)

        txt_clip = txt_clip.set_position(position)
        txt_clip = txt_clip.set_start(subtitle.start_time)
        txt_clip = txt_clip.set_end(subtitle.end_time)

        return txt_clip

    def export_with_subtitles(
        self,
        video_path: str,
        subtitles: List[Subtitle],
        output_path: str,
        fps: Optional[int] = None,
        codec: str = "libx264",
        audio_codec: str = "aac",
        threads: int = 4,
        preset: str = "medium",
    ) -> None:
        """Export video with burned-in subtitles.

        Args:
            video_path: Path to input video
            subtitles: List of Subtitle objects
            output_path: Path to output video
            fps: Output FPS (None to use original)
            codec: Video codec
            audio_codec: Audio codec
            threads: Number of threads for encoding
            preset: FFmpeg preset (ultrafast, superfast, veryfast, faster, fast, medium, slow, slower, veryslow)
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Load video
        video = VideoFileClip(video_path)

        # Determine FPS
        output_fps = fps or video.fps

        # Create subtitle clips
        subtitle_clips = []
        for subtitle in subtitles:
            try:
                txt_clip = self.create_subtitle_clip(subtitle, video.w, video.h)
                subtitle_clips.append(txt_clip)
            except Exception as e:
                print(f"Warning: Failed to create subtitle clip: {e}")
                continue

        if not subtitle_clips:
            print("No valid subtitle clips created, exporting video without subtitles")
            final_video = video
        else:
            # Composite video with subtitles
            final_video = CompositeVideoClip([video] + subtitle_clips)

        # Set FPS
        final_video = final_video.set_fps(output_fps)

        # Write to file
        final_video.write_videofile(
            str(output_path),
            fps=output_fps,
            codec=codec,
            audio_codec=audio_codec,
            threads=threads,
            preset=preset,
        )

        # Close clips
        video.close()
        final_video.close()
        for clip in subtitle_clips:
            clip.close()

    @staticmethod
    def export_soft_subtitles(
        video_path: str,
        subtitle_path: str,
        output_path: str,
        subtitle_lang: str = "chi",
    ) -> None:
        """Export video with soft subtitles (muxed, not burned).

        Args:
            video_path: Path to input video
            subtitle_path: Path to subtitle file (SRT/ASS/VTT)
            output_path: Path to output video
            subtitle_lang: Subtitle language code for FFmpeg
        """
        import subprocess

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        cmd = [
            "ffmpeg",
            "-i",
            video_path,
            "-i",
            subtitle_path,
            "-c",
            "copy",  # Copy streams without re-encoding
            "-c:s",
            "mov_text",  # Subtitle codec
            "-metadata:s:s:0",
            f"language={subtitle_lang}",
            "-y",  # Overwrite output file
            str(output_path),
        ]

        try:
            subprocess.run(cmd, check=True)
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"FFmpeg failed to mux subtitles: {e}") from e

    @staticmethod
    def extract_audio(video_path: str, output_path: str) -> Path:
        """Extract audio from video file.

        Args:
            video_path: Path to input video
            output_path: Path to output audio file

        Returns:
            Path to extracted audio file
        """
        from .video_processor import VideoProcessor

        processor = VideoProcessor(video_path)
        return processor.extract_audio(output_path)
