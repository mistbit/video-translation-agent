"""Example usage of Video Translation Agent."""

import os
from pathlib import Path

from src.asr_transcriber import ASRTranscriber
from src.config import get_config
from src.subtitle_export import SubtitleExporter
from src.subtitle_extractor import SubtitleExtractor
from src.translator import Translator
from src.video_export import VideoExporter


def example_extract_with_asr(video_path: str):
    """Example: Extract subtitles using ASR."""
    print(f"\n=== Extracting subtitles from {video_path} ===")

    config = get_config()

    # Initialize ASR transcriber
    transcriber = ASRTranscriber(model_size=config.asr_model_size)

    # Transcribe video
    subtitles = transcriber.transcribe_video(video_path)

    print(f"Found {len(subtitles)} subtitles")

    # Export to SRT
    output_path = Path(video_path).parent / f"{Path(video_path).stem}_subtitles.srt"
    exporter = SubtitleExporter()
    exporter.export_srt(subtitles, str(output_path))

    print(f"Saved to {output_path}")
    return subtitles


def example_extract_with_ocr(video_path: str):
    """Example: Extract subtitles using OCR."""
    print(f"\n=== Extracting subtitles from {video_path} (OCR) ===")

    config = get_config()

    # Initialize OCR extractor
    extractor = SubtitleExtractor(lang=config.ocr_lang)

    # Extract subtitles
    subtitles = extractor.extract_subtitles(
        video_path, frame_interval=config.frame_interval
    )

    print(f"Found {len(subtitles)} subtitles")

    # Export to SRT
    output_path = Path(video_path).parent / f"{Path(video_path).stem}_ocr_subtitles.srt"
    exporter = SubtitleExporter()
    exporter.export_srt(subtitles, str(output_path))

    print(f"Saved to {output_path}")
    return subtitles


def example_translate_subtitles(srt_path: str, target_lang: str = "en"):
    """Example: Translate subtitles."""
    print(f"\n=== Translating subtitles to {target_lang} ===")

    config = get_config()

    # Import subtitles
    exporter = SubtitleExporter()
    subtitles = exporter.import_srt(srt_path)

    print(f"Loaded {len(subtitles)} subtitles")

    # Translate
    translator = Translator(
        api_key=config.glm_api_key,
        model=config.get("glm.model", "glm-4"),
    )

    translated = translator.translate_subtitles(subtitles, target_lang=target_lang)

    # Export
    output_path = Path(srt_path).parent / f"{Path(srt_path).stem}_{target_lang}.srt"
    exporter.export_srt(translated, str(output_path))

    print(f"Saved to {output_path}")
    return translated


def example_export_video(srt_path: str, video_path: str):
    """Example: Export video with burned-in subtitles."""
    print(f"\n=== Exporting video with subtitles ===")

    config = get_config()

    # Import subtitles
    exporter = SubtitleExporter()
    subtitles = exporter.import_srt(srt_path)

    print(f"Loaded {len(subtitles)} subtitles")

    # Export video
    output_path = (
        Path(video_path).parent / f"{Path(video_path).stem}_with_subs.mp4"
    )

    video_exporter = VideoExporter(
        font_size=config.get("subtitle.font_size", 24),
        font_color=config.get("subtitle.font_color", "white"),
        position=config.get("subtitle.position", "bottom"),
    )

    video_exporter.export_with_subtitles(video_path, subtitles, str(output_path))

    print(f"Saved to {output_path}")


def example_full_pipeline(video_path: str, translate: bool = True, export: bool = True):
    """Example: Run full pipeline - extract, translate, export."""
    print(f"\n{'='*50}")
    print(f"FULL PIPELINE: {video_path}")
    print(f"{'='*50}")

    # Step 1: Extract subtitles
    print("\nStep 1: Extracting subtitles...")
    subtitles = example_extract_with_asr(video_path)

    current_srt = str(Path(video_path).parent / f"{Path(video_path).stem}_subtitles.srt")

    # Step 2: Translate
    if translate and os.environ.get("GLM_API_KEY"):
        print("\nStep 2: Translating subtitles...")
        translated = example_translate_subtitles(current_srt, target_lang="en")
        current_srt = str(
            Path(video_path).parent / f"{Path(video_path).stem}_subtitles_en.srt"
        )
    elif translate:
        print("\nStep 2: Skipping translation (GLM_API_KEY not set)")
    else:
        translated = subtitles if not translate else None

    # Step 3: Export video
    if export:
        print("\nStep 3: Exporting video...")
        subs_to_use = translated if translate and translated else subtitles
        # Note: For translation, we need to create the SRT file first
        if translate and translated:
            temp_srt = Path(video_path).parent / "temp_translated.srt"
            SubtitleExporter().export_srt(translated, str(temp_srt))
            example_export_video(str(temp_srt), video_path)
            temp_srt.unlink()
        else:
            example_export_video(current_srt, video_path)

    print(f"\n{'='*50}")
    print("DONE!")
    print(f"{'='*50}")


if __name__ == "__main__":
    # Check if GLM API key is set
    if not os.environ.get("GLM_API_KEY"):
        print("Warning: GLM_API_KEY environment variable not set.")
        print("Set it with: export GLM_API_KEY='your_api_key'")
        print("\nTranslation features will be skipped.\n")

    # Example usage - replace with your video file path
    video_file = "path/to/your/video.mp4"

    # Uncomment the examples you want to run:

    # 1. Extract subtitles using ASR
    # example_extract_with_asr(video_file)

    # 2. Extract subtitles using OCR
    # example_extract_with_ocr(video_file)

    # 3. Translate existing subtitles
    # example_translate_subtitles("subtitles.srt", target_lang="en")

    # 4. Export video with subtitles
    # example_export_video("subtitles.srt", video_file)

    # 5. Full pipeline
    # example_full_pipeline(video_file, translate=True, export=True)
