import json
import os
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch


WORKER_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORKER_DIR))

# The repository's local test command should still work when optional worker
# runtime dependencies have not been installed on the host.
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

from ai_seo_service import (  # noqa: E402
    PLATFORMS,
    REQUIRED_SEMANTIC_FIELDS,
    _complete_visual_ai_package,
    _platform_prompt_input,
    generate_seo_packages,
)
from seo_mock_generator import build_video_angle  # noqa: E402
from seo_prompt_builder import build_platform_seo_prompt  # noqa: E402


URBAN_SUNSET_VISUAL = {
    'confidence': 0.85,
    'summary': 'городской пейзаж на закате с движущимися автомобилями',
    'detectedScene': 'городская дорога на закате',
    'detectedObjects': ['автомобили', 'жилые дома', 'уличные фонари', 'дорога'],
    'detectedLocationType': 'городская улица',
    'mood': ['меланхоличный', 'спокойный', 'загадочный'],
    'style': ['ночной городской пейзаж', 'драматическое освещение'],
    'visualStrengths': ['выразительное небо', 'городские огни'],
    'visualWeaknesses': [],
    'seoHooks': [
        'Вечерний городской трафик и закат',
        'Красивые городские пейзажи при закате',
    ],
    'coverTextIdeas': ['Закат в городе: дорога и огни ночи'],
    'suggestedNiche': 'городские пейзажи',
    'suggestedVideoAngle': 'Показ городского вождения и красоты вечернего города',
    'vehiclePresent': True,
    'autoContent': True,
    'travelContent': False,
    'eventContent': False,
}


def build_ai_input(visual=None):
    visual = visual or URBAN_SUNSET_VISUAL
    angle = build_video_angle({
        'niche': 'auto',
        'technical': {'durationSec': 15, 'resolution': '1080x1920', 'aspectRatio': '9:16'},
        'video_fingerprint': {'orientation': 'vertical', 'resolutionClass': 'full_hd'},
        'visual_analysis': visual,
    })
    return {
        'userGoal': 'views_and_reach',
        'niche': 'auto',
        'language': 'ru',
        'technicalSummary': {'durationSec': 15, 'resolution': '1080x1920', 'aspectRatio': '9:16'},
        'videoFingerprint': {
            'orientation': 'vertical',
            'resolutionClass': 'full_hd',
            'filenameTokens': ['bmw', 'drift'],
            'detectedModel': 'BMW',
            'contentHints': ['auto_model'],
        },
        'platformFit': {platform: {'score': 85} for platform in PLATFORMS},
        'originalFilename': 'bmw_drift_phonk.mp4',
        'extractedFilenameHints': {'tokens': ['bmw', 'drift', 'phonk']},
        'contentHints': ['auto_model', 'drift'],
        'recommendations': ['Добавьте DRIFT MODE и больше дыма.'],
        'visualAnalysis': visual,
        'analysisBasis': 'visual_ai',
        'videoAngle': angle,
    }


class VisualAiAuthorityTests(unittest.TestCase):
    def test_urban_traffic_is_not_auto_showcase(self):
        ai_input = build_ai_input()
        self.assertEqual(ai_input['videoAngle'], 'urban_drive_sunset')

    def test_high_confidence_visual_path_never_inherits_mock_semantics(self):
        ai_input = build_ai_input()
        report = {'ai_input': ai_input}
        partial_candidate = {
            'bestTitle': 'Город на закате: дорога, огни и драматичное небо',
            'description': 'Вечерняя городская дорога на фоне заката.',
            'hashtags': ['#город', '#закат'],
            'hookText': 'авто-ролик в drift mode за 15 секунд',
            'coverText': 'DRIFT MODE',
            'pinnedComment': 'Больше дыма или больше cinematic?',
            'videoAngle': 'Показ городского вождения произвольной фразой',
        }

        with patch.dict(os.environ, {'AI_PROVIDER': 'openai', 'OPENAI_API_KEY': 'test-key'}):
            with patch('ai_seo_service._openai_platform_json', return_value=partial_candidate):
                packages, provider, fallback_used, warnings = generate_seo_packages(report)

        self.assertEqual(provider, 'openai')
        self.assertFalse(fallback_used)
        self.assertTrue(any('Unsupported SEO claim sanitized: drift' == item for item in warnings))
        self.assertTrue(any('Unsupported SEO claim sanitized: smoke' == item for item in warnings))

        forbidden = ['drift', 'дрифт', 'smoke', 'дым', 'phonk', 'race', 'гонка']
        for platform, package in packages.items():
            for field in REQUIRED_SEMANTIC_FIELDS[platform]:
                self.assertTrue(package.get(field), f'{platform}.{field} must be completed')
            semantic_blob = json.dumps(
                {key: value for key, value in package.items() if key not in {
                    'platform', 'language', 'userGoal', 'niche', 'resolution', 'aspectRatio',
                    'orientation', 'videoDurationSec', 'score', 'videoAngle', 'generationBasis',
                    'analysisBasis', 'seoCompletionMode',
                }},
                ensure_ascii=False,
            ).casefold()
            for term in forbidden:
                self.assertNotIn(term, semantic_blob, f'{platform} leaked unsupported term {term}')
            self.assertIn('город', semantic_blob)
            self.assertIn('закат', semantic_blob)
            self.assertNotEqual(package.get('coverText'), 'DRIFT MODE')
            self.assertEqual(package['videoAngle'], 'urban_drive_sunset')
            self.assertEqual(
                package['generationBasis'],
                ['visual_ai', 'technical_fingerprint', 'user_context'],
            )
            self.assertEqual(package['seoCompletionMode'], 'ai_visual_completion')

    def test_supported_drift_and_smoke_claims_are_preserved(self):
        visual = {
            **URBAN_SUNSET_VISUAL,
            'summary': 'BMW drifting with tire smoke',
            'detectedScene': 'drift track',
            'detectedObjects': ['BMW', 'tires', 'smoke'],
            'seoHooks': ['BMW drift with tire smoke'],
            'suggestedNiche': 'automotive',
            'suggestedVideoAngle': 'drift track action',
        }
        ai_input = build_ai_input(visual)
        candidate = {
            'hookText': 'BMW drift with tire smoke',
            'bestTitle': 'BMW drifting on a smoke-filled track',
            'titleOptions': ['BMW drift with tire smoke'],
            'description': 'BMW drifting with visible tire smoke.',
            'hashtags': ['#drift', '#smoke'],
            'coverText': 'DRIFT SMOKE',
            'pinnedComment': 'Which drift moment is strongest?',
            'improvementTips': ['Open on the visible drift moment.'],
        }

        package, warnings = _complete_visual_ai_package('youtubeShorts', ai_input, candidate)

        self.assertIn('drift', package['hookText'].casefold())
        self.assertIn('smoke', package['hookText'].casefold())
        self.assertFalse(any('drift' in item or 'smoke' in item for item in warnings))

    def test_hallucinated_visual_cover_idea_is_also_guarded(self):
        visual = {**URBAN_SUNSET_VISUAL, 'coverTextIdeas': ['DRIFT MODE']}
        ai_input = build_ai_input(visual)

        package, warnings = _complete_visual_ai_package('youtubeShorts', ai_input, {})

        self.assertNotIn('drift', package['coverText'].casefold())
        self.assertIn('город', package['coverText'].casefold())
        self.assertIn('Unsupported SEO claim sanitized: drift', warnings)

    def test_visual_prompt_demotes_filename_and_legacy_hints(self):
        ai_input = build_ai_input()
        prompt_input = _platform_prompt_input(ai_input)
        prompt = build_platform_seo_prompt('youtubeShorts', prompt_input)

        self.assertNotIn('recommendations', prompt_input)
        self.assertNotIn('detectedModel', prompt_input['videoFingerprint'])
        self.assertEqual(prompt_input['weakMetadata']['originalFilename'], 'bmw_drift_phonk.mp4')
        self.assertIn('VISUAL EVIDENCE IS AUTHORITATIVE', prompt)
        self.assertIn('hookText, bestTitle, titleOptions', prompt)
        self.assertIn('language=ru', prompt)

    def test_mock_provider_path_still_uses_mock_generator(self):
        report = {
            'ai_input': {
                'userGoal': 'views_and_reach',
                'niche': 'auto',
                'language': 'ru',
                'originalFilename': 'bmw_drift.mp4',
                'extractedFilenameHints': {'tokens': ['bmw', 'drift']},
                'keywords': ['BMW', 'drift'],
                'contentHints': ['auto_model'],
                'videoAngle': 'auto_drift_phonk',
            }
        }
        with patch.dict(os.environ, {'AI_PROVIDER': 'mock'}, clear=False):
            packages, provider, fallback_used, warnings = generate_seo_packages(report)

        self.assertEqual(provider, 'mock')
        self.assertFalse(fallback_used)
        self.assertEqual(warnings, [])
        self.assertIn('drift', json.dumps(packages, ensure_ascii=False).casefold())


if __name__ == '__main__':
    unittest.main()
