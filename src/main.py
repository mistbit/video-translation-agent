"""CLI entry point for Video Translation Agent."""

from pathlib import Path
from typing import Optional

import typer

from .asr_transcriber import ASRTranscriber, combine_ocr_and_asr
from .config import get_config
from .subtitle_export import SubtitleExporter
from .subtitle_extractor import SubtitleExtractor
from .translator import Translator
from .video_export import VideoExporter
from .video_processor import VideoProcessor

app = typer.Typer(help="Video Translation Agent - Extract, translate, and export video subtitles")


@app.command()
def extract(
    video_path: str = typer.Argument(..., help="Path to input video file"),
    method: str = typer.Option("ocr", "--method", "-m", help="Extraction method: ocr, asr, or both"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output SRT file path"),
    config_file: Optional[str] = typer.Option(None, "--config", "-c", help="Path to config file"),
    frame_interval: Optional[float] = typer.Option(None, "--interval", help="Frame interval for OCR (seconds)"),
    model_size: Optional[str] = typer.Option(None, "--model-size", help="Whisper model size"),
):
    """Extract subtitles from video using OCR or ASR."""
    # Load config
    config = get_config(config_file) if config_file else get_config()

    # Determine output path
    if output is None:
        video_file = Path(video_path)
        output = str(video_file.parent / f"{video_file.stem}_subtitles.srt")

    print(f"Extracting subtitles from: {video_path}")
    print(f"Method: {method}")

    # Extract subtitles
    subtitles = []

    if method in ("ocr", "both"):
        print("Running OCR extraction...")
        extractor = SubtitleExtractor(
            lang=config.ocr_lang,
            use_angle_cls=config.get("ocr.use_angle_cls", True),
        )
        interval = frame_interval or config.frame_interval
        ocr_subtitles = extractor.extract_subtitles(video_path, frame_interval=interval)
        print(f"OCR found {len(ocr_subtitles)} subtitles")
        subtitles = ocr_subtitles

    if method in ("asr", "both"):
        print("Running ASR transcription...")
        transcriber = ASRTranscriber(
            model_size=model_size or config.asr_model_size,
            compute_type=config.get("asr.compute_type", "int8"),
        )
        asr_subtitles = transcriber.transcribe_video(video_path)
        print(f"ASR found {len(asr_subtitles)} subtitles")

        if method == "both":
            # Combine OCR and ASR results
            print("Combining OCR and ASR results...")
            subtitles = combine_ocr_and_asr(ocr_subtitles, asr_subtitles)
        else:
            subtitles = asr_subtitles

    # Export subtitles
    print(f"Exporting to: {output}")
    exporter = SubtitleExporter()
    exporter.export_srt(subtitles, output)

    print(f"✓ Extracted {len(subtitles)} subtitles to {output}")


@app.command()
def translate(
    srt_path: str = typer.Argument(..., help="Path to input SRT file"),
    lang: str = typer.Option(..., "--lang", "-l", help="Target language: zh or en"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output SRT file path"),
    config_file: Optional[str] = typer.Option(None, "--config", "-c", help="Path to config file"),
):
    """Translate subtitles to another language."""
    # Load config
    config = get_config(config_file) if config_file else get_config()

    # Determine output path
    if output is None:
        srt_file = Path(srt_path)
        lang_suffix = "_zh" if lang == "zh" else "_en"
        output = str(srt_file.parent / f"{srt_file.stem}{lang_suffix}.srt")

    print(f"Translating: {srt_path}")
    print(f"Target language: {lang}")

    # Import and translate
    exporter = SubtitleExporter()
    subtitles = exporter.import_srt(srt_path)

    translator = Translator(
        api_key=config.glm_api_key,
        model=config.get("glm.model", "glm-4"),
        temperature=config.get("glm.temperature", 0.3),
    )

    # Detect source language if not specified
    if subtitles:
        sample_text = " ".join([s.text for s in subtitles[:5]])
        source_lang = Translator.detect_language(sample_text)
        print(f"Detected source language: {source_lang}")

        # Auto-detect target if not specified
        if source_lang == lang:
            lang = Translator.get_inverse_language(source_lang)
            print(f"Source and target are same, switching to: {lang}")

    translated = translator.translate_subtitles(
        subtitles,
        target_lang=lang,
    )

    # Export translated subtitles
    exporter.export_srt(translated, output)

    print(f"✓ Translated {len(translated)} subtitles to {output}")


@app.command()
def export(
    srt_path: str = typer.Argument(..., help="Path to subtitle file"),
    video_path: str = typer.Argument(..., help="Path to input video file"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output video file path"),
    config_file: Optional[str] = typer.Option(None, "--config", "-c", help="Path to config file"),
    soft_subs: bool = typer.Option(False, "--soft", "-s", help="Use soft subtitles (muxed) instead of burned-in"),
):
    """Export video with subtitles."""
    # Load config
    config = get_config(config_file) if config_file else get_config()

    # Determine output path
    if output is None:
        video_file = Path(video_path)
        output = str(video_file.parent / f"{video_file.stem}_with_subs.mp4")

    print(f"Processing: {video_path}")
    print(f"Subtitles: {srt_path}")

    # Import subtitles
    exporter = SubtitleExporter()
    subtitles = exporter.import_srt(srt_path)
    print(f"Loaded {len(subtitles)} subtitles")

    # Export video
    if soft_subs:
        print("Exporting with soft subtitles...")
        VideoExporter.export_soft_subtitles(video_path, srt_path, output)
    else:
        print("Exporting with burned-in subtitles...")
        video_exporter = VideoExporter(
            font_size=config.get("subtitle.font_size", 24),
            font_color=config.get("subtitle.font_color", "white"),
            position=config.get("subtitle.position", "bottom"),
            margin=config.get("subtitle.margin", 10),
        )
        video_exporter.export_with_subtitles(video_path, subtitles, output)

    print(f"✓ Exported video to {output}")


@app.command()
def full(
    video_path: str = typer.Argument(..., help="Path to input video file"),
    translate: bool = typer.Option(False, "--translate", "-t", help="Translate subtitles"),
    lang: str = typer.Option("en", "--lang", "-l", help="Translation target language: zh or en"),
    export: bool = typer.Option(False, "--export", "-e", help="Export video with subtitles"),
    method: str = typer.Option("asr", "--method", "-m", help="Extraction method: ocr, asr, or both"),
    output_dir: Optional[str] = typer.Option(None, "--output-dir", "-d", help="Output directory"),
    config_file: Optional[str] = typer.Option(None, "--config", "-c", help="Path to config file"),
):
    """Full pipeline: extract, optionally translate, and optionally export."""
    # Load config
    config = get_config(config_file) if config_file else get_config()

    # Determine output directory
    output_path = Path(output_dir) if output_dir else config.output_dir
    output_path.mkdir(parents=True, exist_ok=True)

    video_file = Path(video_path)
    base_name = video_file.stem

    # Step 1: Extract subtitles
    print("\n" + "=" * 50)
    print("STEP 1: Extracting subtitles...")
    print("=" * 50)

    srt_output = output_path / f"{base_name}_subtitles.srt"

    subtitles = []

    if method in ("ocr", "both"):
        extractor = SubtitleExtractor(lang=config.ocr_lang)
        ocr_subtitles = extractor.extract_subtitles(video_path, frame_interval=config.frame_interval)
        print(f"OCR found {len(ocr_subtitles)} subtitles")
        subtitles = ocr_subtitles

    if method in ("asr", "both"):
        transcriber = ASRTranscriber(model_size=config.asr_model_size)
        asr_subtitles = transcriber.transcribe_video(video_path)
        print(f"ASR found {len(asr_subtitles)} subtitles")

        if method == "both":
            subtitles = combine_ocr_and_asr(ocr_subtitles, asr_subtitles)
        else:
            subtitles = asr_subtitles

    # Export extracted subtitles
    exporter = SubtitleExporter()
    exporter.export_srt(subtitles, str(srt_output))
    print(f"✓ Saved to: {srt_output}")

    current_srt = str(srt_output)

    # Step 2: Translate (if requested)
    if translate:
        print("\n" + "=" * 50)
        print("STEP 2: Translating subtitles...")
        print("=" * 50)

        translator = Translator(
            api_key=config.glm_api_key,
            model=config.get("glm.model", "glm-4"),
            temperature=config.get("glm.temperature", 0.3),
        )

        # Detect source language
        if subtitles:
            sample_text = " ".join([s.text for s in subtitles[:5]])
            source_lang = Translator.detect_language(sample_text)
            print(f"Detected source language: {source_lang}")

            if source_lang == lang:
                lang = Translator.get_inverse_language(source_lang)
                print(f"Source and target are same, switching to: {lang}")

        translated = translator.translate_subtitles(subtitles, target_lang=lang)
        translated_output = output_path / f"{base_name}_subtitles_{lang}.srt"
        exporter.export_srt(translated, str(translated_output))
        current_srt = str(translated_output)

        print(f"✓ Translated to: {translated_output}")

    # Step 3: Export video (if requested)
    if export:
        print("\n" + "=" * 50)
        print("STEP 3: Exporting video with subtitles...")
        print("=" * 50)

        video_output = output_path / f"{base_name}_output.mp4"

        video_exporter = VideoExporter(
            font_size=config.get("subtitle.font_size", 24),
            font_color=config.get("subtitle.font_color", "white"),
            position=config.get("subtitle.position", "bottom"),
            margin=config.get("subtitle.margin", 10),
        )
        video_exporter.export_with_subtitles(video_path, subtitles if not translate else translated, str(video_output))

        print(f"✓ Exported to: {video_output}")

    print("\n" + "=" * 50)
    print("Done!")
    print("=" * 50)


if __name__ == "__main__":
    app()
