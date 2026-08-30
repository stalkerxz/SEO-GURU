from typing import Any, Dict

SUPPORTED_PLATFORMS = {
    'youtube_video': 'YouTube (обычное видео)',
    'youtube_shorts': 'YouTube Shorts',
    'instagram_reels': 'Instagram Reels',
    'tiktok': 'TikTok',
    'youtubeVideo': 'YouTube (обычное видео)',
    'youtubeShorts': 'YouTube Shorts',
    'instagramReels': 'Instagram Reels',
}

PLATFORM_REQUIRED_FIELDS = {
    'youtubeVideo': [
        'bestTitle', 'titleOptions', 'description', 'tags', 'thumbnailText',
        'pinnedComment', 'improvementTips',
    ],
    'youtubeShorts': [
        'hookText', 'bestTitle', 'titleOptions', 'description', 'hashtags',
        'coverText', 'pinnedComment', 'improvementTips',
    ],
    'instagramReels': [
        'firstLineHook', 'caption', 'hashtags', 'coverText', 'storyAnnouncement',
        'cta', 'altText', 'improvementTips',
    ],
    'tiktok': [
        'hookText', 'caption', 'hashtags', 'coverText', 'trendAngle', 'cta',
        'improvementTips',
    ],
}


def build_ai_video_analysis_prompt(ai_input: Dict[str, Any]) -> str:
    return (
        'Ты — AI-аналитик видео и SEO-редактор. Учитывай цель публикации, нишу, язык, гео, бренд/автора, ключевые слова, '
        'технические параметры видео, набор кадров и платформенные особенности. '
        'Запрещено обещать гарантированное попадание в рекомендации, выдумывать факты, давать слишком общие советы и '
        'использовать нерелевантные хештеги. Для Shorts/Reels/TikTok используй 5–8 хештегов. '
        'Верни только валидный JSON без markdown. Тексты должны быть готовы к копированию и публикации. '
        'Если бренд указан — аккуратно используй его в описании/CTA. Если гео указано — добавляй его уместно для локального продвижения. '
        'Используй videoFingerprint, contentHints и frameManifest для video-specific результата по конкретному ролику. '
        'Если visualAnalysis есть и confidence >= 0.5, он является главным источником смысла, а technical/filename hints — только метаданными. '
        'Не делай выводы только по filename — это weak hint. '
        'Если визуальный контент не распознан, не выдумывай объекты и сцены — опирайся только на технические и контекстные hints. '
        f'\n\nВходные данные (JSON):\n{ai_input}'
    )


def build_platform_seo_prompt(platform: str, ai_input: Dict[str, Any]) -> str:
    platform_name = SUPPORTED_PLATFORMS.get(platform, platform)
    required_fields = ', '.join(PLATFORM_REQUIRED_FIELDS.get(platform, []))
    language = ai_input.get('language', 'ru')
    return (
        f'Ты — SEO-редактор для платформы {platform_name}. На основе входных данных подготовь SEO-пакет строго для этой платформы. '
        'Учти: цель публикации, нишу, язык, гео, бренд/автора, ключевые слова, техпараметры видео, кадры и platformFit. '
        'Запрещено: гарантии рекомендаций, выдуманные факты, общие советы без конкретики, нерелевантные хештеги. '
        'Для Shorts/Reels/TikTok используй максимум 5–8 хештегов. '
        'Верни только валидный JSON, структура должна строго соответствовать нужной платформе. '
        'Сделай тексты готовыми к публикации. Бренд и гео используй только уместно. '
        'VISUAL EVIDENCE IS AUTHORITATIVE. '
        'SEO must be specific to this exact video, not only to user keywords. '
        'When visualAnalysis.confidence >= 0.5, use visualAnalysis as the semantic source of truth. '
        'Use seoHooks and coverTextIdeas from visualAnalysis as source material and match the actual mood/style. '
        'Never claim drift, racing, smoke, phonk, burnout, a product, location, person, brand, or activity unless it is '
        'supported by visualAnalysis or explicit user context. Never invent action that is not visible. '
        'Filename, extractedFilenameHints, and old contentHints are weak metadata only and must not override visual evidence. '
        'Generate every semantic field required for this platform; do not leave fields dependent on mock defaults. '
        f'Required semantic fields: {required_fields}. '
        f'Generate publication copy in language={language}; for language=ru all publication text must be Russian. '
        'videoAngle is machine-readable input metadata: do not rewrite it or replace it with prose. '
        'No generic copy. Mention uncertainty if visual content is unclear. '
        f'\n\nПлатформа: {platform}\nВходные данные (JSON):\n{ai_input}'
    )
