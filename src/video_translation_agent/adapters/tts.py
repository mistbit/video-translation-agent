import hashlib
import math
import shutil
import subprocess
import tempfile
import wave
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class TTSClip:
    sample_rate_hz: int
    duration_ms: int
    pcm16_samples: list[int]


class LocalTTSAdapter:
    def __init__(
        self,
        *,
        sample_rate_hz: int = 16_000,
        say_bin: str = "say",
        afconvert_bin: str = "afconvert",
        run_command=subprocess.run,
    ):
        self.sample_rate_hz = sample_rate_hz
        self.say_bin = say_bin
        self.afconvert_bin = afconvert_bin
        self.run_command = run_command

    def synthesize(
        self,
        *,
        text: str,
        voice_profile: str,
        target_duration_ms: int,
    ) -> TTSClip:
        cleaned = " ".join(text.split()).strip()
        if not cleaned:
            cleaned = "[silence]"

        spoken_clip = self._synthesize_with_macos_voice(
            text=cleaned,
            voice_profile=voice_profile,
            target_duration_ms=target_duration_ms,
        )
        if spoken_clip is not None:
            return spoken_clip

        estimated_ms = max(320, min(12_000, int(len(cleaned) * 65)))
        duration_ms = max(240, estimated_ms)
        if target_duration_ms > 0:
            duration_ms = max(240, min(duration_ms, target_duration_ms + 1_500))

        sample_count = max(1, int(self.sample_rate_hz * duration_ms / 1000))
        frequency_hz = self._frequency_for_text(cleaned, voice_profile)
        amplitude = 7_500
        fade_samples = min(240, sample_count // 8)

        samples: list[int] = []
        for index in range(sample_count):
            t = index / self.sample_rate_hz
            sample = int(amplitude * math.sin(2.0 * math.pi * frequency_hz * t))
            if fade_samples > 0:
                if index < fade_samples:
                    sample = int(sample * (index / fade_samples))
                elif index >= sample_count - fade_samples:
                    sample = int(sample * ((sample_count - index) / fade_samples))
            samples.append(sample)

        return TTSClip(
            sample_rate_hz=self.sample_rate_hz,
            duration_ms=duration_ms,
            pcm16_samples=samples,
        )

    def _synthesize_with_macos_voice(
        self,
        *,
        text: str,
        voice_profile: str,
        target_duration_ms: int,
    ) -> TTSClip | None:
        if (
            shutil.which(self.say_bin) is None
            or shutil.which(self.afconvert_bin) is None
        ):
            return None

        voice_name = self._voice_name_for_profile(voice_profile)
        speech_rate = self._speech_rate_for_target(
            text=text,
            target_duration_ms=target_duration_ms,
        )
        with tempfile.TemporaryDirectory(prefix="vta-tts-") as temp_dir:
            root = Path(temp_dir)
            aiff_path = root / "speech.aiff"
            wav_path = root / "speech.wav"

            say_command = [
                self.say_bin,
                "-v",
                voice_name,
                "-r",
                str(speech_rate),
                "-o",
                str(aiff_path),
                text,
            ]
            if not self._run_command(say_command):
                return None

            convert_command = [
                self.afconvert_bin,
                "-f",
                "WAVE",
                "-d",
                f"LEI16@{self.sample_rate_hz}",
                "-c",
                "1",
                str(aiff_path),
                str(wav_path),
            ]
            if not self._run_command(convert_command):
                return None

            try:
                with wave.open(str(wav_path), "rb") as wav_file:
                    frame_rate = wav_file.getframerate()
                    frame_count = wav_file.getnframes()
                    frames = wav_file.readframes(frame_count)
            except (wave.Error, OSError):
                return None

        samples = [
            int.from_bytes(frames[index : index + 2], byteorder="little", signed=True)
            for index in range(0, len(frames), 2)
        ]
        adjusted = self._fit_samples_to_duration(
            samples=samples,
            target_duration_ms=target_duration_ms,
            sample_rate_hz=frame_rate,
        )
        duration_ms = max(1, int(len(adjusted) * 1000 / frame_rate))
        return TTSClip(
            sample_rate_hz=frame_rate,
            duration_ms=duration_ms,
            pcm16_samples=adjusted,
        )

    def _run_command(self, command: list[str]) -> bool:
        try:
            completed = self.run_command(
                command,
                check=False,
                capture_output=True,
                text=True,
            )
        except (FileNotFoundError, OSError):
            return False
        return completed.returncode == 0

    @staticmethod
    def _voice_name_for_profile(voice_profile: str) -> str:
        profile = voice_profile.lower()
        if "male" in profile:
            return "Daniel"
        if "uk" in profile or "brit" in profile:
            return "Daniel"
        return "Samantha"

    @staticmethod
    def _speech_rate_for_target(*, text: str, target_duration_ms: int) -> int:
        if target_duration_ms <= 0:
            return 180
        words = max(1, len(text.split()))
        minutes = max(target_duration_ms / 60000.0, 1 / 60)
        wpm = int(words / minutes)
        return max(120, min(260, wpm))

    @staticmethod
    def _fit_samples_to_duration(
        *,
        samples: list[int],
        target_duration_ms: int,
        sample_rate_hz: int,
    ) -> list[int]:
        if target_duration_ms <= 0:
            return samples
        target_count = max(1, int(sample_rate_hz * target_duration_ms / 1000))
        if len(samples) >= target_count:
            return samples[:target_count]
        return samples + [0] * (target_count - len(samples))

    @staticmethod
    def write_wav(path: Path, clip: TTSClip) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with wave.open(str(path), "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(clip.sample_rate_hz)
            wav_file.writeframes(
                b"".join(
                    int(sample).to_bytes(2, byteorder="little", signed=True)
                    for sample in clip.pcm16_samples
                )
            )

    @staticmethod
    def merge_with_timeline(
        *,
        sample_rate_hz: int,
        timeline_clips: list[tuple[int, list[int]]],
    ) -> list[int]:
        if not timeline_clips:
            return []

        max_index = 0
        for start_ms, samples in timeline_clips:
            start_idx = int(sample_rate_hz * start_ms / 1000)
            max_index = max(max_index, start_idx + len(samples))

        merged = [0] * max_index
        for start_ms, samples in timeline_clips:
            start_idx = int(sample_rate_hz * start_ms / 1000)
            for offset, value in enumerate(samples):
                idx = start_idx + offset
                mixed = merged[idx] + value
                merged[idx] = max(-32768, min(32767, mixed))
        return merged

    @staticmethod
    def _frequency_for_text(text: str, voice_profile: str) -> float:
        digest = hashlib.sha256(f"{voice_profile}|{text}".encode("utf-8")).hexdigest()
        bucket = int(digest[:8], 16) % 300
        return 180.0 + bucket
