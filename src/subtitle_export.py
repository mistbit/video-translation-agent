"""Subtitle export/import in various formats (SRT, VTT, ASS)."""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from .subtitle_extractor import Subtitle


class SubtitleExporter:
    """Exporter for subtitle files in various formats."""

    @staticmethod
    def format_srt_time(seconds: float) -> str:
        """Convert seconds to SRT time format.

        Args:
            seconds: Time in seconds

        Returns:
            Time string in SRT format (HH:MM:SS,mmm)
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

    @staticmethod
    def parse_srt_time(time_str: str) -> float:
        """Parse SRT time string to seconds.

        Args:
            time_str: Time string in SRT format (HH:MM:SS,mmm)

        Returns:
            Time in seconds
        """
        match = re.match(r"(\d+):(\d+):(\d+),(\d+)", time_str)
        if not match:
            raise ValueError(f"Invalid SRT time format: {time_str}")

        hours, minutes, secs, millis = map(int, match.groups())
        return hours * 3600 + minutes * 60 + secs + millis / 1000

    def export_srt(
        self,
        subtitles: List[Subtitle],
        output_path: str,
        encoding: str = "utf-8-sig",
    ) -> None:
        """Export subtitles to SRT format.

        Args:
            subtitles: List of Subtitle objects
            output_path: Path to output SRT file
            encoding: File encoding (default: utf-8-sig for SRT with BOM)
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding=encoding) as f:
            for i, subtitle in enumerate(subtitles, 1):
                f.write(f"{i}\n")
                f.write(
                    f"{self.format_srt_time(subtitle.start_time)} --> "
                    f"{self.format_srt_time(subtitle.end_time)}\n"
                )
                f.write(f"{subtitle.text}\n\n")

    def import_srt(self, input_path: str, encoding: str = "utf-8-sig") -> List[Subtitle]:
        """Import subtitles from SRT format.

        Args:
            input_path: Path to input SRT file
            encoding: File encoding

        Returns:
            List of Subtitle objects
        """
        with open(input_path, "r", encoding=encoding) as f:
            content = f.read()

        subtitles = []
        # Split by blank lines to get subtitle blocks
        blocks = re.split(r"\n\s*\n", content.strip())

        for block in blocks:
            if not block.strip():
                continue

            lines = block.split("\n")

            # Skip empty blocks
            if len(lines) < 3:
                continue

            # Parse subtitle index
            try:
                index = int(lines[0])
            except ValueError:
                continue

            # Parse time range
            time_match = re.search(
                r"(\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2},\d{3})",
                lines[1],
            )
            if not time_match:
                continue

            start_time = self.parse_srt_time(time_match.group(1))
            end_time = self.parse_srt_time(time_match.group(2))

            # Join remaining lines as subtitle text
            text = "\n".join(lines[2:]).strip()

            subtitles.append(
                Subtitle(start_time=start_time, end_time=end_time, text=text)
            )

        return subtitles

    @staticmethod
    def format_vtt_time(seconds: float) -> str:
        """Convert seconds to WebVTT time format.

        Args:
            seconds: Time in seconds

        Returns:
            Time string in WebVTT format (HH:MM:SS.mmm)
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"

    def export_vtt(
        self,
        subtitles: List[Subtitle],
        output_path: str,
        encoding: str = "utf-8",
    ) -> None:
        """Export subtitles to WebVTT format.

        Args:
            subtitles: List of Subtitle objects
            output_path: Path to output VTT file
            encoding: File encoding
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding=encoding) as f:
            f.write("WEBVTT\n\n")

            for subtitle in subtitles:
                f.write(
                    f"{self.format_vtt_time(subtitle.start_time)} --> "
                    f"{self.format_vtt_time(subtitle.end_time)}\n"
                )
                f.write(f"{subtitle.text}\n\n")

    @staticmethod
    def format_ass_time(seconds: float) -> str:
        """Convert seconds to ASS/SSA time format.

        Args:
            seconds: Time in seconds

        Returns:
            Time string in ASS format (H:MM:SS.cc)
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        centis = int((seconds % 1) * 100)
        return f"{hours}:{minutes:02d}:{secs:02d}.{centis:02d}"

    def export_ass(
        self,
        subtitles: List[Subtitle],
        output_path: str,
        font_size: int = 24,
        font_color: str = "&H00ffffff&",
        margin_v: int = 10,
        encoding: str = "utf-8-sig",
    ) -> None:
        """Export subtitles to ASS/SSA format.

        Args:
            subtitles: List of Subtitle objects
            output_path: Path to output ASS file
            font_size: Font size
            font_color: Font color in ASS format
            margin_v: Bottom margin
            encoding: File encoding
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding=encoding) as f:
            # Write ASS header
            f.write("[Script Info]\n")
            f.write("ScriptType: v4.00+\n")
            f.write("Collisions: Normal\n")
            f.write("PlayDepth: 0\n")
            f.write("\n")
            f.write("[V4+ Styles]\n")
            f.write(
                f"Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
            )
            f.write(
                f"Style: Default,Arial,{font_size},&H00ffffff&,&H000000FF&,&H00000000&,&H00000000&,-1,0,0,0,100,100,0,0,1,2,0,2,10,10,{margin_v},1\n"
            )
            f.write("\n")
            f.write("[Events]\n")
            f.write(
                "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
            )

            # Write subtitle events
            for subtitle in subtitles:
                # Escape special characters for ASS format
                text = subtitle.text
                text = text.replace("\\", "\\\\")
                text = text.replace("{", "\\{")
                text = text.replace("}", "\\}")

                f.write(
                    f"Dialogue: 0,{self.format_ass_time(subtitle.start_time)},"
                    f"{self.format_ass_time(subtitle.end_time)},"
                    f"Default,,0,0,0,,{text}\n"
                )

    def export(
        self,
        subtitles: List[Subtitle],
        output_path: str,
        format: Optional[str] = None,
        **kwargs,
    ) -> None:
        """Export subtitles to specified format.

        Args:
            subtitles: List of Subtitle objects
            output_path: Path to output file
            format: Output format ('srt', 'vtt', 'ass'). If None, inferred from file extension
            **kwargs: Additional format-specific options
        """
        output_path = Path(output_path)

        if format is None:
            format = output_path.suffix[1:].lower()

        if format == "srt":
            self.export_srt(subtitles, output_path, **kwargs)
        elif format == "vtt":
            self.export_vtt(subtitles, output_path, **kwargs)
        elif format in ["ass", "ssa"]:
            self.export_ass(subtitles, output_path, **kwargs)
        else:
            raise ValueError(f"Unsupported subtitle format: {format}")
