import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

RunCommand = Callable[..., subprocess.CompletedProcess[str]]


class RenderExecutionError(RuntimeError):
    pass


@dataclass(frozen=True)
class RenderResult:
    used_ffmpeg: bool
    used_fallback: bool
    warnings: list[str]


class LocalRenderAdapter:
    def __init__(
        self,
        *,
        ffmpeg_bin: str = "ffmpeg",
        run_command: RunCommand = subprocess.run,
        prefer_ffmpeg: bool = True,
        allow_copy_fallback: bool = True,
    ):
        self.ffmpeg_bin = ffmpeg_bin
        self.run_command = run_command
        self.prefer_ffmpeg = prefer_ffmpeg
        self.allow_copy_fallback = allow_copy_fallback

    def render(
        self,
        *,
        source_video: Path,
        dub_audio: Path,
        subtitle_srt: Path,
        mix_output: Path,
        final_video_output: Path,
        burn_subtitles: bool,
    ) -> RenderResult:
        warnings: list[str] = []

        mix_output.parent.mkdir(parents=True, exist_ok=True)
        final_video_output.parent.mkdir(parents=True, exist_ok=True)

        if self.prefer_ffmpeg:
            try:
                self._render_with_ffmpeg(
                    source_video=source_video,
                    dub_audio=dub_audio,
                    subtitle_srt=subtitle_srt,
                    mix_output=mix_output,
                    final_video_output=final_video_output,
                    burn_subtitles=burn_subtitles,
                )
                return RenderResult(
                    used_ffmpeg=True,
                    used_fallback=False,
                    warnings=warnings,
                )
            except RenderExecutionError as exc:
                warnings.append(str(exc))

        if not self.allow_copy_fallback:
            raise RenderExecutionError(
                "ffmpeg rendering unavailable and fallback disabled"
            )

        try:
            self._render_with_avfoundation(
                source_video=source_video,
                dub_audio=dub_audio,
                mix_output=mix_output,
                final_video_output=final_video_output,
            )
            warnings.append("render used AVFoundation fallback; subtitles not burned")
            return RenderResult(
                used_ffmpeg=False,
                used_fallback=True,
                warnings=warnings,
            )
        except RenderExecutionError as exc:
            warnings.append(str(exc))

        shutil.copyfile(dub_audio, mix_output)
        shutil.copyfile(source_video, final_video_output)
        warnings.append("render used local copy fallback; subtitles not burned")
        return RenderResult(
            used_ffmpeg=False,
            used_fallback=True,
            warnings=warnings,
        )

    def _render_with_ffmpeg(
        self,
        *,
        source_video: Path,
        dub_audio: Path,
        subtitle_srt: Path,
        mix_output: Path,
        final_video_output: Path,
        burn_subtitles: bool,
    ) -> None:
        mix_command = [
            self.ffmpeg_bin,
            "-y",
            "-i",
            str(dub_audio),
            "-c:a",
            "pcm_s16le",
            str(mix_output),
        ]
        self._run_or_raise(mix_command)

        render_command = [
            self.ffmpeg_bin,
            "-y",
            "-i",
            str(source_video),
            "-i",
            str(mix_output),
            "-map",
            "0:v:0",
            "-map",
            "1:a:0",
            "-c:v",
            "copy",
            "-c:a",
            "aac",
        ]
        if burn_subtitles:
            render_command.extend(["-vf", f"subtitles={subtitle_srt}"])
        render_command.append(str(final_video_output))
        self._run_or_raise(render_command)

    def _run_or_raise(self, command: list[str]) -> None:
        try:
            completed = self.run_command(
                command,
                check=False,
                capture_output=True,
                text=True,
            )
        except FileNotFoundError as exc:
            raise RenderExecutionError("ffmpeg executable not found on PATH") from exc
        except OSError as exc:
            raise RenderExecutionError(f"failed to run ffmpeg: {exc}") from exc

        if completed.returncode != 0:
            stderr = (completed.stderr or "").strip()
            raise RenderExecutionError(stderr or "ffmpeg failed with unknown error")

    def _render_with_avfoundation(
        self,
        *,
        source_video: Path,
        dub_audio: Path,
        mix_output: Path,
        final_video_output: Path,
    ) -> None:
        shutil.copyfile(dub_audio, mix_output)
        swift_script = (
            "import Foundation;"
            "import AVFoundation;"
            "let sourceURL = URL(fileURLWithPath: CommandLine.arguments[1]);"
            "let audioURL = URL(fileURLWithPath: CommandLine.arguments[2]);"
            "let outputURL = URL(fileURLWithPath: CommandLine.arguments[3]);"
            "try? FileManager.default.removeItem(at: outputURL);"
            "let composition = AVMutableComposition();"
            "let videoAsset = AVURLAsset(url: sourceURL);"
            "let audioAsset = AVURLAsset(url: audioURL);"
            'guard let sourceVideoTrack = videoAsset.tracks(withMediaType: .video).first else { fatalError("missing video track") };'
            "let videoTrack = composition.addMutableTrack(withMediaType: .video, preferredTrackID: kCMPersistentTrackID_Invalid)!;"
            "try videoTrack.insertTimeRange(CMTimeRange(start: .zero, duration: videoAsset.duration), of: sourceVideoTrack, at: .zero);"
            "videoTrack.preferredTransform = sourceVideoTrack.preferredTransform;"
            "if let sourceAudioTrack = audioAsset.tracks(withMediaType: .audio).first {"
            " let audioTrack = composition.addMutableTrack(withMediaType: .audio, preferredTrackID: kCMPersistentTrackID_Invalid)!;"
            " try audioTrack.insertTimeRange(CMTimeRange(start: .zero, duration: composition.duration), of: sourceAudioTrack, at: .zero);"
            "};"
            'guard let export = AVAssetExportSession(asset: composition, presetName: AVAssetExportPresetHighestQuality) else { fatalError("no export session") };'
            "export.outputURL = outputURL;"
            "export.outputFileType = .mp4;"
            "let sem = DispatchSemaphore(value: 0);"
            "export.exportAsynchronously { sem.signal() };"
            "_ = sem.wait(timeout: .now() + 600);"
            "if export.status != .completed {"
            ' let err = export.error.map { String(describing: $0) } ?? "unknown";'
            ' fputs("export failed: \\(export.status.rawValue) \\(err)\\n", stderr);'
            " exit(2);"
            "}"
        )
        try:
            completed = self.run_command(
                [
                    "swift",
                    "-e",
                    swift_script,
                    str(source_video),
                    str(dub_audio),
                    str(final_video_output),
                ],
                check=False,
                capture_output=True,
                text=True,
            )
        except FileNotFoundError as exc:
            raise RenderExecutionError(
                "swift executable not found for AVFoundation fallback"
            ) from exc
        except OSError as exc:
            raise RenderExecutionError(
                f"failed to run AVFoundation fallback: {exc}"
            ) from exc

        if completed.returncode != 0:
            stderr = (completed.stderr or "").strip()
            raise RenderExecutionError(
                stderr or "AVFoundation fallback failed with unknown error"
            )
