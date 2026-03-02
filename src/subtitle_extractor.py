"""OCR-based subtitle extraction using PaddleOCR."""

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

import numpy as np
from paddleocr import PaddleOCR

from .video_processor import VideoProcessor


@dataclass
class Subtitle:
    """Subtitle data structure with timestamp and text."""

    start_time: float  # in seconds
    end_time: float  # in seconds
    text: str


@dataclass
class OCRResult:
    """OCR detection result from a single frame."""

    frame_number: int
    timestamp: float
    text: str
    confidence: float


class SubtitleExtractor:
    """Subtitle extractor using PaddleOCR for OCR-based subtitle detection."""

    def __init__(
        self,
        lang: str = "ch",
        use_angle_cls: bool = True,
        det_db_thresh: float = 0.3,
        det_db_box_thresh: float = 0.5,
    ):
        """Initialize subtitle extractor.

        Args:
            lang: Language code ('ch' for Chinese+English, 'en' for English only)
            use_angle_cls: Whether to use angle classification
            det_db_thresh: Detection threshold
            det_db_box_thresh: Bounding box threshold
        """
        self.lang = lang
        self.ocr = PaddleOCR(
            use_angle_cls=use_angle_cls,
            lang=lang,
            det_db_thresh=det_db_thresh,
            det_db_box_thresh=det_db_box_thresh,
            show_log=False,
        )

    def extract_from_frame(self, frame: np.ndarray) -> List[OCRResult]:
        """Extract text from a single frame.

        Args:
            frame: Image frame as numpy array (BGR format)

        Returns:
            List of OCRResult objects
        """
        result = self.ocr.ocr(frame, cls=True)

        ocr_results = []
        if result and result[0]:
            for line in result[0]:
                box = line[0]
                text_info = line[1]
                text = text_info[0]
                confidence = text_info[1]

                ocr_results.append(
                    OCRResult(
                        frame_number=0,
                        timestamp=0.0,
                        text=text,
                        confidence=confidence,
                    )
                )

        return ocr_results

    def extract_subtitles(
        self,
        video_path: str,
        frame_interval: float = 1.0,
        min_confidence: float = 0.5,
    ) -> List[Subtitle]:
        """Extract subtitles from video using OCR.

        Args:
            video_path: Path to video file
            frame_interval: Time interval between frames to analyze (seconds)
            min_confidence: Minimum confidence threshold for text detection

        Returns:
            List of Subtitle objects with timestamps and text
        """
        video_processor = VideoProcessor(video_path)
        info = video_processor.get_info()

        # Extract frames and perform OCR
        frame_ocr_results = {}

        with video_processor:
            for frame_num, timestamp, frame in video_processor.extract_frames_by_interval(frame_interval):
                ocr_results = self.extract_from_frame(frame)

                for ocr_result in ocr_results:
                    if ocr_result.confidence >= min_confidence:
                        # Update frame number and timestamp
                        ocr_result.frame_number = frame_num
                        ocr_result.timestamp = timestamp
                        frame_ocr_results[frame_num] = ocr_result

        # Convert OCR results to subtitles with time ranges
        subtitles = self._ocr_to_subtitles(frame_ocr_results, info)

        return subtitles

    def _ocr_to_subtitles(
        self, ocr_results: dict, video_info: "VideoProcessor.VideoInfo"
    ) -> List[Subtitle]:
        """Convert frame-based OCR results to time-based subtitles.

        Args:
            ocr_results: Dictionary mapping frame numbers to OCRResult objects
            video_info: VideoInfo object with video metadata

        Returns:
            List of Subtitle objects
        """
        if not ocr_results:
            return []

        # Sort by frame number
        sorted_frames = sorted(ocr_results.keys())

        subtitles = []

        for i, frame_num in enumerate(sorted_frames):
            ocr_result = ocr_results[frame_num]

            # Calculate time range for this subtitle
            start_time = ocr_result.timestamp

            # End time is either the next frame's timestamp or a default duration
            if i < len(sorted_frames) - 1:
                next_frame_num = sorted_frames[i + 1]
                next_ocr_result = ocr_results[next_frame_num]

                # If the text is the same, extend the subtitle
                if ocr_result.text == next_ocr_result.text:
                    continue  # Will be handled when we reach the last occurrence

                end_time = next_ocr_result.timestamp
            else:
                # Last subtitle - give it a default duration
                end_time = min(start_time + 5.0, video_info.duration)

            subtitles.append(
                Subtitle(start_time=start_time, end_time=end_time, text=ocr_result.text)
            )

        # Merge consecutive subtitles with the same text
        return self._merge_consecutive_subtitles(subtitles)

    def _merge_consecutive_subtitles(self, subtitles: List[Subtitle]) -> List[Subtitle]:
        """Merge consecutive subtitles with identical text.

        Args:
            subtitles: List of Subtitle objects

        Returns:
            Merged list of Subtitle objects
        """
        if not subtitles:
            return []

        merged = [subtitles[0]]

        for current in subtitles[1:]:
            last = merged[-1]

            if current.text == last.text:
                # Merge: extend end time
                last.end_time = current.end_time
            else:
                merged.append(current)

        return merged

    def filter_subtitle_region(
        self,
        frame: np.ndarray,
        bbox: List[List[float]],
        video_info: "VideoProcessor.VideoInfo",
    ) -> bool:
        """Filter OCR results based on subtitle region heuristics.

        Args:
            frame: Image frame
            bbox: Bounding box coordinates
            video_info: VideoInfo object

        Returns:
            True if the text is likely a subtitle
        """
        height = frame.shape[0]
        width = frame.shape[1]

        # Calculate bounding box center
        x_center = sum([p[0] for p in bbox]) / 4
        y_center = sum([p[1] for p in bbox]) / 4

        # Subtitles are typically at the bottom 30% of the screen
        subtitle_region_top = height * 0.7

        return y_center >= subtitle_region_top
