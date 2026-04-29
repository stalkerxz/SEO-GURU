from typing import Any, Dict, List

from seo_prompt_builder import build_ai_video_analysis_prompt, build_platform_seo_prompt


def _parse_resolution(resolution: str | None) -> tuple[int, int]:
    if not resolution or 'x' not in resolution:
        return (0, 0)
    try:
        w, h = resolution.split('x', 1)
        return int(w), int(h)
    except ValueError:
        return (0, 0)


def _base_context(analysis_report: Dict[str, Any]) -> Dict[str, Any]:
    technical = analysis_report.get('technical', {})
    duration = float(technical.get('durationSec') or 0)
    width, height = _parse_resolution(technical.get('resolution'))
    short_side = min(width, height) if width and height else 0
    vertical = bool(width and height and height > width)
    has_audio = bool(technical.get('hasAudio'))
    low_quality = bool(short_side and short_side < 720)
    long_video = duration > 180

    fit_note = (
        'Видео уже вертикальное и подходит для Shorts/Reels/TikTok.'
        if vertical
        else 'Видео горизонтальное: для коротких платформ стоит сделать адаптацию 9:16.'
    )

    return {
        'duration': duration,
        'vertical': vertical,
        'has_audio': has_audio,
        'low_quality': low_quality,
        'long_video': long_video,
        'fit_note': fit_note,
    }


def _common_tips(ctx: Dict[str, Any]) -> List[str]:
    tips: List[str] = [ctx['fit_note']]
    if not ctx['has_audio']:
        tips.append('Добавьте музыку, речь или звуковые акценты для удержания внимания.')
    if ctx['long_video']:
        tips.append('Подготовьте короткую версию до 60–180 секунд для коротких платформ.')
    if ctx['low_quality']:
        tips.append('Экспортируйте ролик в Full HD (1080p) для более чёткого восприятия.')
    tips.append('Усильте хук в первые 1–3 секунды: вопрос, обещание пользы или контрастный кадр.')
    return tips


def generate_mock_seo_package(analysis_report: Dict[str, Any], platform: str) -> Dict[str, Any]:
    ai_input = analysis_report.get('ai_input', {})
    _ = build_ai_video_analysis_prompt(ai_input)
    _ = build_platform_seo_prompt(platform, ai_input)

    ctx = _base_context(analysis_report)
    tips = _common_tips(ctx)

    if platform == 'youtubeVideo':
        title_options = [
            'Что происходит в этом видео: разбор по шагам',
            'Главные моменты ролика за несколько минут',
            'Сюжет, монтаж и стиль: честный разбор',
            'Как улучшить это видео для роста охватов',
            'Видео-анализ: сильные стороны и точки роста',
        ]
        return {
            'titleOptions': title_options,
            'bestTitle': title_options[0],
            'description': 'Подробный разбор ролика: структура, монтаж, удержание и идеи для улучшения. Без обещаний мгновенных результатов, только практические шаги.',
            'hashtags': ['#видео', '#анализ', '#youtube', '#контент', '#seo'],
            'tags': ['видео анализ', 'ютуб seo', 'монтаж видео', 'удержание аудитории', 'контент стратегия'],
            'chapters': ['00:00 Вступление', '00:20 О чём ролик', '01:10 Сильные стороны', '02:00 Что улучшить', '03:00 Итоги'],
            'thumbnailText': 'РАЗБОР ВИДЕО',
            'pinnedComment': 'Какой момент в ролике кажется вам самым сильным? Напишите в комментариях 👇',
            'category': 'Education',
            'playlistSuggestion': 'Разборы и оптимизация видео',
            'improvementTips': tips,
        }

    if platform == 'youtubeShorts':
        title_options = [
            'Короткий разбор видео за 60 секунд',
            'Почему этот ролик цепляет (и где просадка)',
            '1 видео — 3 быстрых улучшения',
            'Разбор хука и удержания за минуту',
            'Как поднять охват этого ролика',
        ]
        return {
            'titleOptions': title_options,
            'bestTitle': title_options[0],
            'description': 'Быстрый SEO-разбор: что работает, что стоит улучшить и как адаптировать ролик под короткий формат.',
            'hashtags': ['#shorts', '#разбор', '#видео', '#контент', '#охваты'],
            'tags': ['shorts seo', 'хук', 'удержание', 'короткие видео'],
            'coverText': 'РАЗБОР ЗА 60 СЕК',
            'pinnedComment': 'Нужен разбор вашего Shorts? Оставьте тему в комментарии.',
            'hookText': 'Стоп! За 1 минуту покажу, как улучшить этот ролик.',
            'improvementTips': tips,
        }

    if platform == 'instagramReels':
        return {
            'caption': 'Разбираем ролик по структуре, визуалу и удержанию. Сохраняйте, чтобы применить в следующем Reels.',
            'firstLineHook': '3 правки, которые сделают ролик сильнее уже сегодня.',
            'hashtags': ['#reels', '#контент', '#видеомаркетинг', '#креатор', '#smm'],
            'altText': 'Кадр из видео с акцентом на разбор структуры и визуального стиля.',
            'coverText': 'REELS РАЗБОР',
            'pinnedComment': 'Какой пункт разобрать подробнее в следующем Reels?',
            'storyAnnouncement': 'Новый разбор в Reels: хук, монтаж и SEO-подача. Смотрите в ленте 👀',
            'cta': 'Сохраните пост и отправьте коллеге, который монтирует видео.',
            'improvementTips': tips,
        }

    return {
        'caption': 'Короткий разбор видео: что цепляет, а что снижает досматриваемость.',
        'hookText': 'Если ролик не добирает просмотры — начните с этих 3 правок.',
        'hashtags': ['#tiktok', '#видео', '#контент', '#монтаж', '#советы'],
        'coverText': '3 ПРАВКИ ДЛЯ ОХВАТА',
        'pinnedComment': 'Хотите вторую часть с примерами? Пишите «часть 2».',
        'cta': 'Подпишитесь, чтобы не пропустить новые разборы.',
        'trendAngle': 'Образовательный формат «до/после» с быстрыми инсайтами.',
        'improvementTips': tips,
    }
