from video_translation_agent.adapters.media import MediaProbeAdapter
from video_translation_agent.adapters.qa import QAAdapter
from video_translation_agent.adapters.render import LocalRenderAdapter
from video_translation_agent.adapters.asr import ASRAdapter, FasterWhisperASRAdapter
from video_translation_agent.adapters.subtitles import SubtitleParser
from video_translation_agent.adapters.translation import LocalTranslationAdapter
from video_translation_agent.adapters.tts import LocalTTSAdapter
from video_translation_agent.domain.enums import StageName
from video_translation_agent.pipeline.registry import StageRegistry
from video_translation_agent.stages.caption import build_caption_stage
from video_translation_agent.stages.ingest import build_ingest_stage
from video_translation_agent.stages.normalize import build_normalize_stage
from video_translation_agent.stages.qa import build_qa_stage
from video_translation_agent.stages.render import build_render_stage
from video_translation_agent.stages.translate import build_translate_stage
from video_translation_agent.stages.tts import build_tts_stage


def build_default_stage_registry(
    *,
    media_probe_adapter: MediaProbeAdapter | None = None,
    subtitle_parser: SubtitleParser | None = None,
    asr_adapter: ASRAdapter | None = None,
    translation_adapter: LocalTranslationAdapter | None = None,
    tts_adapter: LocalTTSAdapter | None = None,
    render_adapter: LocalRenderAdapter | None = None,
    qa_adapter: QAAdapter | None = None,
) -> StageRegistry:
    registry = StageRegistry(stage_order=list(StageName))
    registry.register(
        StageName.INGEST,
        build_ingest_stage(media_probe_adapter or MediaProbeAdapter()),
    )
    registry.register(
        StageName.CAPTION,
        build_caption_stage(
            subtitle_parser or SubtitleParser(),
            asr_adapter or FasterWhisperASRAdapter(),
        ),
    )
    registry.register(StageName.NORMALIZE, build_normalize_stage())
    registry.register(
        StageName.TRANSLATE,
        build_translate_stage(translation_adapter or LocalTranslationAdapter()),
    )
    registry.register(
        StageName.TTS,
        build_tts_stage(tts_adapter or LocalTTSAdapter()),
    )
    registry.register(
        StageName.RENDER,
        build_render_stage(render_adapter or LocalRenderAdapter()),
    )
    registry.register(
        StageName.QA,
        build_qa_stage(qa_adapter or QAAdapter()),
    )
    return registry
