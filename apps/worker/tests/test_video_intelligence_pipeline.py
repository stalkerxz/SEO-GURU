import json
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch


WORKER_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORKER_DIR))

try:
    import boto3  # noqa: F401
except ModuleNotFoundError:
    sys.modules['boto3'] = MagicMock()

try:
    import openai  # noqa: F401
except ModuleNotFoundError:
    openai_stub = types.ModuleType('openai')
    openai_stub.OpenAI = MagicMock
    sys.modules['openai'] = openai_stub

for optional_module in ['psycopg2', 'redis']:
    try:
        __import__(optional_module)
    except ModuleNotFoundError:
        sys.modules[optional_module] = MagicMock()

from ai_seo_service import (  # noqa: E402
    PLATFORMS,
    _complete_visual_ai_package,
    _topic_evidence_blob,
    _unsupported_claims,
    _visual_action_evidence_blob,
    analyze_full_video_intelligence,
    generate_seo_packages,
    transcribe_audio_with_openai,
)
from audio_analysis import analyze_audio_technical, no_audio_analysis  # noqa: E402
from video_intelligence import build_retention_analysis, normalize_video_intelligence  # noqa: E402
from video_sampling import build_sampling_plan, target_frame_count  # noqa: E402
from video_temporal_analysis import build_temporal_analysis, detect_scene_changes  # noqa: E402
import worker  # noqa: E402


CITY_VISUAL = {
    'confidence': 0.85,
    'summary': 'Городская магистраль на закате с обычным автомобильным трафиком',
    'detectedScene': 'городская дорога на закате',
    'detectedLocationType': 'городская улица',
    'detectedObjects': ['дорога', 'автомобили', 'фонари', 'драматичное небо'],
    'style': ['кинематографичный городской пейзаж'],
    'mood': ['спокойный', 'вечерний'],
    'seoHooks': ['Закат над городской дорогой'],
    'coverTextIdeas': ['Город на закате'],
    'visualStrengths': ['драматичное небо'],
    'visualWeaknesses': [],
    'suggestedNiche': 'городские пейзажи',
    'suggestedVideoAngle': 'обычная городская поездка на закате',
}

CITY_INTELLIGENCE = {
    'version': 1,
    'summary': 'Ролик показывает спокойную поездку по городской магистрали на фоне заката.',
    'primarySubject': 'городская дорога на закате',
    'contentType': 'атмосферное короткое видео',
    'contentNiche': 'городские пейзажи',
    'locationType': 'городская магистраль',
    'people': {'present': False, 'role': ''},
    'story': {
        'structure': 'ambient_single_scene',
        'beginning': 'Открывается вид на дорогу и небо.',
        'development': 'Автомобили продолжают обычное движение.',
        'climax': 'Закатное небо становится главным визуальным акцентом.',
        'ending': 'Поездка продолжается в вечернем городе.',
        'payoff': 'Драматичный городской закат.',
    },
    'openingHook': {
        'summary': 'Городская дорога сразу появляется на фоне яркого неба.',
        'strength': 0.72,
        'type': 'beauty',
        'retentionRisk': 'Низкая сменяемость кадров.',
    },
    'editing': {
        'pacing': 'slow',
        'estimatedSceneCount': 3,
        'cutsPerMinute': 4.8,
        'averageShotDurationSec': 8.2,
        'style': ['плавное наблюдение'],
        'strengths': ['цельная атмосфера'],
        'weaknesses': ['мало визуальных изменений'],
    },
    'audio': {
        'hasAudio': True,
        'speechPresent': False,
        'speechSummary': '',
        'audioRole': 'фон',
        'silenceRisk': 'низкий',
    },
    'mood': ['спокойный', 'драматичный'],
    'style': ['городской синематик'],
    'strongestMoments': [{'timestampSec': 18.4, 'reason': 'Самое выразительное закатное небо.'}],
    'retention': {
        'strengths': ['сильный цветовой акцент'],
        'risks': ['однообразное движение'],
        'dropOffRisks': ['длинный участок без смены композиции'],
        'improvements': ['Сократить самый однообразный участок.'],
    },
    'visualStrengths': ['закатное небо'],
    'visualWeaknesses': ['мало смен планов'],
    'seoEvidence': {
        'primaryTopics': ['город', 'дорога', 'закат'],
        'secondaryTopics': ['вечерний трафик'],
        'confirmedEntities': ['автомобили'],
        'safeKeywords': ['городская дорога', 'закат', 'вечерний город'],
        'unsafeUnsupportedClaims': ['дрифт', 'гонка'],
    },
    'recommendedContentAngle': 'Атмосфера вечерней городской поездки.',
    'canonicalVideoAngle': 'urban_drive_sunset',
    'confidence': 0.86,
}


def city_ai_input():
    return {
        'userGoal': 'views_and_reach',
        'niche': 'auto',
        'language': 'ru',
        'keywords': [],
        'originalFilename': 'bmw_drift_phonk.mp4',
        'extractedFilenameHints': {'tokens': ['bmw', 'drift', 'phonk']},
        'contentHints': ['auto_model', 'drift'],
        'recommendations': ['DRIFT MODE', 'more smoke'],
        'technicalSummary': {'durationSec': 24.8, 'resolution': '1080x1920', 'aspectRatio': '9:16'},
        'videoFingerprint': {'orientation': 'vertical', 'filenameTokens': ['bmw', 'drift', 'phonk']},
        'platformFit': {platform: {'score': 85} for platform in PLATFORMS},
        'visualAnalysis': CITY_VISUAL,
        'videoIntelligence': CITY_INTELLIGENCE,
        'audioAnalysis': {'hasAudio': True, 'silenceRatio': 0.1, 'transcriptionStatus': 'empty'},
        'transcript': {'status': 'empty', 'language': '', 'text': '', 'segments': []},
        'videoAngle': 'urban_drive_sunset',
    }


class AdaptiveSamplingTests(unittest.TestCase):
    def test_ten_second_video_uses_small_sample(self):
        self.assertEqual(target_frame_count(10), 8)

    def test_thirty_second_video_uses_more_frames(self):
        self.assertEqual(target_frame_count(30), 10)
        self.assertGreater(target_frame_count(30), target_frame_count(10))

    def test_two_minute_video_uses_more_frames(self):
        self.assertEqual(target_frame_count(120), 16)
        self.assertGreater(target_frame_count(120), target_frame_count(30))

    def test_long_video_respects_hard_max(self):
        self.assertEqual(target_frame_count(3600), 24)
        self.assertLessEqual(len(build_sampling_plan(3600)['selectedTimestampsSec']), 24)

    def test_opening_timestamps_are_always_represented(self):
        timestamps = build_sampling_plan(10)['selectedTimestampsSec']
        for expected in [0.0, 0.5, 1.0, 2.0, 3.0]:
            self.assertIn(expected, timestamps)

    def test_end_frame_is_present(self):
        plan = build_sampling_plan(24.8)
        self.assertIn(24.75, plan['selectedTimestampsSec'])
        self.assertEqual(plan['endingFrameCount'], 1)

    def test_scene_candidates_have_priority_over_uniform_fill(self):
        plan = build_sampling_plan(60, [8, 17, 29, 44, 53])
        self.assertEqual(plan['strategy'], 'adaptive_scene_aware')
        self.assertGreater(plan['sceneFrameCount'], 0)
        self.assertIn(29.0, plan['selectedTimestampsSec'])

    def test_near_duplicate_timestamps_are_removed(self):
        timestamps = build_sampling_plan(15, [0.51, 1.05, 3.1, 3.15])['selectedTimestampsSec']
        gaps = [right - left for left, right in zip(timestamps, timestamps[1:])]
        self.assertTrue(all(gap >= 0.199 for gap in gaps))

    def test_scene_detection_failure_selects_uniform_fallback(self):
        plan = build_sampling_plan(45, [], scene_detection_failed=True)
        self.assertEqual(plan['strategy'], 'adaptive_uniform_fallback')
        self.assertEqual(plan['sceneFrameCount'], 0)

    def test_configured_limit_is_clamped_and_applied(self):
        with patch.dict(os.environ, {'VIDEO_AI_MAX_FRAMES': '7'}):
            self.assertEqual(target_frame_count(120), 7)


class TemporalAndAudioTests(unittest.TestCase):
    def test_temporal_analysis_calculates_scene_metrics(self):
        result = build_temporal_analysis(30, [5, 10, 20])
        self.assertEqual(result['estimatedSceneCount'], 4)
        self.assertEqual(result['cutsPerMinute'], 6.0)
        self.assertEqual(result['averageShotDurationSec'], 7.5)
        self.assertEqual(result['pacing'], 'medium')

    def test_scene_detection_error_is_explicit_for_caller_fallback(self):
        completed = SimpleNamespace(returncode=1, stderr='ffmpeg error')
        with patch('video_temporal_analysis.subprocess.run', return_value=completed):
            with self.assertRaises(RuntimeError):
                detect_scene_changes('/tmp/video.mp4')

    def test_video_without_audio_returns_no_audio(self):
        result = no_audio_analysis(24.8)
        self.assertFalse(result['hasAudio'])
        self.assertEqual(result['transcriptionStatus'], 'no_audio')
        self.assertEqual(result['speechPresent'], False)

    def test_audio_analysis_parses_silence_and_loudness(self):
        stderr = '\n'.join([
            '[silencedetect] silence_start: 2.0',
            '[silencedetect] silence_end: 5.0 | silence_duration: 3.0',
            '[Parsed_volumedetect] mean_volume: -18.5 dB',
        ])
        completed = SimpleNamespace(returncode=0, stderr=stderr)
        stream = {'codec_name': 'aac', 'channels': 2, 'sample_rate': '48000'}
        with patch('audio_analysis.subprocess.run', return_value=completed):
            result = analyze_audio_technical('/tmp/video.mp4', stream, 10)
        self.assertEqual(result['silenceRatio'], 0.3)
        self.assertEqual(result['approximateLoudness'], -18.5)
        self.assertEqual(result['sampleRate'], 48000)

    def test_transcription_exception_returns_graceful_result(self):
        client = MagicMock()
        client.audio.transcriptions.create.side_effect = TimeoutError('timeout')
        with tempfile.NamedTemporaryFile(suffix='.mp3') as audio_file:
            with patch.dict(os.environ, {'AI_PROVIDER': 'openai', 'OPENAI_API_KEY': 'test-key'}):
                with patch('ai_seo_service.OpenAI', return_value=client):
                    result = transcribe_audio_with_openai(audio_file.name, 'ru')
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['segments'], [])
        self.assertIn('Audio transcription failed', result['_warning'])

    def test_mock_mode_does_not_request_transcription(self):
        with patch.dict(os.environ, {'AI_PROVIDER': 'mock'}, clear=False):
            result = transcribe_audio_with_openai('/does/not/matter.mp3', 'ru')
        self.assertEqual(result['status'], 'not_requested')

    def test_noncritical_pipeline_failures_keep_job_compatible(self):
        metadata = {
            'format': {'duration': '24.8', 'bit_rate': '1200000'},
            'streams': [
                {'codec_type': 'video', 'width': 1080, 'height': 1920, 'r_frame_rate': '30/1', 'codec_name': 'h264'},
                {'codec_type': 'audio', 'codec_name': 'aac', 'channels': 2, 'sample_rate': '48000'},
            ],
        }
        context = {
            'userGoal': 'views_and_reach', 'niche': 'general_video', 'language': 'ru',
            'geo': '', 'brandName': '', 'keywords': [], 'originalFilename': 'video.mp4',
            'extractedFilenameHints': {'tokens': ['video']},
        }
        with patch.dict(os.environ, {'AI_PROVIDER': 'mock', 'STORAGE_MODE': 'local'}):
            with patch('worker.ffprobe_json', return_value=metadata), \
                    patch('worker.detect_scene_changes', side_effect=RuntimeError('scene failed')), \
                    patch('worker.extract_frames_at_timestamps', return_value=([], ['frame warning'])), \
                    patch('worker.analyze_audio_technical', side_effect=RuntimeError('audio failed')), \
                    patch('worker.analyze_video_frames_with_ai', return_value={}), \
                    patch('worker.analyze_opening_frames_with_ai', side_effect=RuntimeError('opening failed')), \
                    patch('worker.analyze_full_video_intelligence', side_effect=RuntimeError('synthesis failed')):
                result, report = worker.analyze_file('/tmp/video.mp4', 'job-1', context)

        self.assertTrue(result['has_audio'])
        self.assertEqual(report['samplingPlan']['strategy'], 'adaptive_uniform_fallback')
        self.assertEqual(report['transcript']['status'], 'not_requested')
        self.assertEqual(report['aiProviderUsed'], 'mock')
        warning_blob = ' '.join(report['aiWarnings'])
        for expected in ['Scene detection failed', 'Audio technical analysis failed', 'Opening AI analysis failed', 'Full video intelligence synthesis failed']:
            self.assertIn(expected, warning_blob)
        self.assertEqual(set(report['seoDraft']), set(PLATFORMS))


class VideoIntelligenceSeoTests(unittest.TestCase):
    def test_normalizer_handles_invalid_numeric_model_values(self):
        result = normalize_video_intelligence({
            'summary': 'Городской ролик',
            'editing': {
                'estimatedSceneCount': 'unknown',
                'cutsPerMinute': 'many',
                'averageShotDurationSec': None,
            },
            'confidence': '86%',
        })
        self.assertEqual(result['editing']['estimatedSceneCount'], 0)
        self.assertEqual(result['editing']['cutsPerMinute'], 0.0)
        self.assertEqual(result['confidence'], 0.86)

    def test_high_confidence_video_intelligence_is_primary_semantic_source(self):
        package, warnings = _complete_visual_ai_package('youtubeShorts', city_ai_input(), {})
        self.assertEqual(warnings, [])
        self.assertEqual(package['videoAngle'], 'urban_drive_sunset')
        self.assertEqual(package['generationBasis'][0], 'video_intelligence')
        self.assertIn('visual_ai', package['generationBasis'])
        self.assertIn('audio_analysis', package['generationBasis'])
        self.assertIn('город', json.dumps(package, ensure_ascii=False).casefold())

    def test_dirty_filename_cannot_pollute_city_video_fallback(self):
        report = {'ai_input': city_ai_input()}
        with patch.dict(os.environ, {'AI_PROVIDER': 'openai', 'OPENAI_API_KEY': 'test-key'}):
            with patch('ai_seo_service._openai_platform_json', side_effect=TimeoutError):
                packages, provider, fallback_used, _ = generate_seo_packages(report)
        self.assertEqual(provider, 'openai')
        self.assertTrue(fallback_used)
        semantic = json.dumps(packages, ensure_ascii=False).casefold()
        for forbidden in ['drift', 'дрифт', 'smoke', 'дым', 'phonk', 'race', 'racing', 'гонка']:
            self.assertNotIn(forbidden, semantic)
        self.assertIn('город', semantic)
        self.assertIn('закат', semantic)

    def test_transcript_topic_does_not_confirm_visual_action(self):
        ai_input = city_ai_input()
        ai_input['transcript'] = {
            'status': 'completed',
            'text': 'Сегодня поговорим про дрифт и его историю.',
            'segments': [],
        }
        unsupported = _unsupported_claims(
            'Автомобиль дрифтит на городской дороге.',
            _topic_evidence_blob(ai_input),
            _visual_action_evidence_blob(ai_input),
        )
        self.assertIn('drift', unsupported)

    def test_transcript_can_confirm_an_informational_topic(self):
        ai_input = city_ai_input()
        ai_input['transcript'] = {
            'status': 'completed',
            'text': 'Сегодня поговорим про дрифт и его историю.',
            'segments': [],
        }
        unsupported = _unsupported_claims(
            'Сегодня поговорим про дрифт: история и советы.',
            _topic_evidence_blob(ai_input),
            _visual_action_evidence_blob(ai_input),
        )
        self.assertNotIn('drift', unsupported)

    def test_full_synthesis_invalid_response_preserves_pr18_visual_path(self):
        response = SimpleNamespace(output_text='not valid json')
        client = MagicMock()
        client.responses.create.return_value = response
        ai_input = city_ai_input()
        ai_input.pop('videoIntelligence')
        with patch.dict(os.environ, {'AI_PROVIDER': 'openai', 'OPENAI_API_KEY': 'test-key'}):
            with patch('ai_seo_service.OpenAI', return_value=client):
                synthesis = analyze_full_video_intelligence(ai_input)
            with patch('ai_seo_service._openai_platform_json', side_effect=TimeoutError):
                packages, provider, fallback_used, _ = generate_seo_packages({'ai_input': ai_input})
        self.assertEqual(synthesis['_status'], 'invalid_response')
        self.assertEqual(provider, 'openai')
        self.assertTrue(fallback_used)
        for package in packages.values():
            self.assertEqual(package['analysisBasis'], 'visual_ai')
            self.assertEqual(package['generationBasis'][0], 'visual_ai')

    def test_retention_analysis_carries_clear_disclaimer(self):
        result = build_retention_analysis(CITY_INTELLIGENCE, None, {'pacing': 'slow'})
        self.assertEqual(result['estimatedHookStrength'], 0.72)
        self.assertIn('не фактическая аналитика', result['disclaimer'])


if __name__ == '__main__':
    unittest.main()
