"""Video processing module for extracting video information, frames, and audio."""

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Generator, List, Tuple

import cv2
import numpy as np


@dataclass
class VideoInfo:
    """Video information container."""

    width: int
    height: int
    fps: float
    frame_count: int
    duration: float  # in seconds


class VideoProcessor:
    """Video processor using OpenCV for frame extraction and FFmpeg for audio."""

    def __init__(self, video_path: str):
        """Initialize video processor.

        Args:
            video_path: Path to video file
        """
        self.video_path = Path(video_path)
        self._cap: Optional[cv2.VideoCapture] = None

    def __enter__(self):
        """Context manager entry."""
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

    def open(self) -> None:
        """Open video file."""
        self._cap = cv2.VideoCapture(str(self.video_path))
        if not self._cap.isOpened():
            raise IOError(f"Cannot open video file: {self.video_path}")

    def close(self) -> None:
        """Close video file."""
        if self._cap is not None:
            self._cap.release()
            self._cap = None

    def get_info(self) -> VideoInfo:
        """Get video information.

        Returns:
            VideoInfo object with video metadata

        Raises:
            IOError: If video file cannot be opened
        """
        if self._cap is None:
            self.open()

        width = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = self._cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(self._cap.get(cv2.CAP_PROP_FRAME_COUNT))

        if fps > 0:
            duration = frame_count / fps
        else:
            duration = 0.0

        return VideoInfo(
            width=width,
            height=height,
            fps=fps,
            frame_count=frame_count,
            duration=duration,
        )

    def extract_frame(self, frame_number: int) -> np.ndarray:
        """Extract a specific frame from the video.

        Args:
            frame_number: Frame number to extract (0-indexed)

        Returns:
            Frame as numpy array (BGR format)

        Raises:
            IOError: If frame cannot be extracted
        """
        if self._cap is None:
            self.open()

        self._cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
        ret, frame = self._cap.read()

        if not ret or frame is None:
            raise IOError(f"Failed to extract frame {frame_number}")

        return frame

    def extract_frames_by_interval(
        self, interval: float = 1.0
    ) -> Generator[Tuple[int, float, np.ndarray], None, None]:
        """Extract frames at regular time intervals.

        Args:
            interval: Time interval between frames in seconds

        Yields:
            Tuple of (frame_number, timestamp, frame)
        """
        info = self.get_info()
        if info.fps <= 0:
            return

        frame_step = int(interval * info.fps)
        if frame_step < 1:
            frame_step = 1

        for frame_num in range(0, info.frame_count, frame_step):
            timestamp = frame_num / info.fps
            frame = self.extract_frame(frame_num)
            yield frame_num, timestamp, frame

    def extract_all_frames(self) -> Generator[Tuple[int, float, np.ndarray], None, None]:
        """Extract all frames from the video.

        Yields:
            Tuple of (frame_number, timestamp, frame)
        """
        info = self.get_info()
        if info._cap is None:
            self.open()

        frame_num = 0
        while True:
            ret, frame = self._cap.read()
            if not ret:
                break

            timestamp = frame_num / info.fps if info.fps > 0 else 0.0
            yield frame_num, timestamp, frame
            frame_num += 1

    def extract_audio(self, output_path: str = None, sample_rate: int = 16000) -> Path:
        """Extract audio from video using FFmpeg.

        Args:
            output_path: Path to save audio file. If None, uses video_path with .wav extension
            sample_rate: Audio sample rate

        Returns:
            Path to extracted audio file

        Raises:
            RuntimeError: If FFmpeg is not available or extraction fails
        """
        if output_path is None:
            output_path = str(self.video_path).rsplit(".", 1)[0] + ".wav"
        else:
            output_path = Path(output_path)

        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Use FFmpeg to extract audio
        cmd = [
            "ffmpeg",
            "-i",
            str(self.video_path),
            "-vn",  # No video
            "-acodec",
            "pcm_s16le",  # 16-bit PCM
            "-ar",
            str(sample_rate),  # Sample rate
            "-ac",
            "1",  # Mono
            "-y",  # Overwrite output file
            str(output_path),
        ]

        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, check=True
            )
        except subprocess.CalledProcessError as e:
            raise RuntimeError(
                f"FFmpeg failed to extract audio: {e.stderr}"
            ) from e
        except FileNotFoundError:
            raise RuntimeError(
                "FFmpeg not found. Please install FFmpeg to use audio extraction."
            )

        return output_path

    def save_frame(self, frame: np.ndarray, output_path: str) -> None:
        """Save a frame to an image file.

        Args:
            frame: Frame as numpy array
            output_path: Path to save image
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(output_path), frame)

    @staticmethod
    def get_video_info_ffmpeg(video_path: str) -> VideoInfo:
        """Get video information using FFmpeg (alternative to OpenCV).

        Args:
            video_path: Path to video file

        Returns:
            VideoInfo object with video metadata

        Raises:
            RuntimeError: If FFmpeg fails or file is not found
        """
        cmd = [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-count_frames",
            "-show_entries",
            "stream=width,height,r_frame_rate,nb_read_frames,duration",
            "-of",
            "default=nokey=1:noprint_wrappers=1",
            video_path,
        ]

        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, check=True
            )
            values = [v.strip() for v in result.stdout.split("\n") if v.strip()]

            if len(values) < 5:
                raise RuntimeError("Unexpected FFmpeg output format")

            width = int(values[0])
            height = int(values[1])
            fps_str = values[2]
            # Parse FPS from "30/1" format
            if "/" in fps_str:
                num, den = fps_str.split("/")
                fps = float(num) / float(den)
            else:
                fps = float(fps_str)
            frame_count = int(values[3])
            duration = float(values[4])

            return VideoInfo(
                width=width,
                height=height,
                fps=fps,
                frame_count=frame_count,
                duration=duration,
            )
        except subprocess.CalledProcessError as e:
            raise RuntimeError(
                f"FFprobe failed: {e.stderr}"
            ) from e
        except FileNotFoundError:
            raise RuntimeError("FFprobe not found. Please install FFmpeg.")
