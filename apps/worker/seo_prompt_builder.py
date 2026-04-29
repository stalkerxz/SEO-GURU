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


def build_ai_video_analysis_prompt(ai_input: Dict[str, Any]) -> str:
    return (
        'Ты — AI-аналитик видео и SEO-редактор. Учитывай цель публикации, нишу, язык, гео, бренд/автора, ключевые слова, '
        'технические параметры видео, набор кадров и платформенные особенности. '
        'Запрещено обещать гарантированное попадание в рекомендации, выдумывать факты, давать слишком общие советы и '
        'использовать нерелевантные хештеги. Для Shorts/Reels/TikTok используй 5–8 хештегов. '
        'Верни только валидный JSON без markdown. Тексты должны быть готовы к копированию и публикации. '
        'Если бренд указан — аккуратно используй его в описании/CTA. Если гео указано — добавляй его уместно для локального продвижения. '
        f'\n\nВходные данные (JSON):\n{ai_input}'
    )


def build_platform_seo_prompt(platform: str, ai_input: Dict[str, Any]) -> str:
    platform_name = SUPPORTED_PLATFORMS.get(platform, platform)
    return (
        f'Ты — SEO-редактор для платформы {platform_name}. На основе входных данных подготовь SEO-пакет строго для этой платформы. '
        'Учти: цель публикации, нишу, язык, гео, бренд/автора, ключевые слова, техпараметры видео, кадры и platformFit. '
        'Запрещено: гарантии рекомендаций, выдуманные факты, общие советы без конкретики, нерелевантные хештеги. '
        'Для Shorts/Reels/TikTok используй максимум 5–8 хештегов. '
        'Верни только валидный JSON, структура должна строго соответствовать нужной платформе. '
        'Сделай тексты готовыми к публикации. Бренд и гео используй только уместно. '
        f'\n\nПлатформа: {platform}\nВходные данные (JSON):\n{ai_input}'
    )
