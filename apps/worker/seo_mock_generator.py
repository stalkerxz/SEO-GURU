from typing import Any, Dict, List

from seo_prompt_builder import build_ai_video_analysis_prompt, build_platform_seo_prompt


def _contextual_meta(ai_input: Dict[str, Any]) -> Dict[str, Any]:
    return {
        'goal': ai_input.get('userGoal', 'views_and_reach'),
        'niche': ai_input.get('niche', 'general_video'),
        'geo': ai_input.get('geo', ''),
        'brand': ai_input.get('brandName', ''),
        'keywords': ai_input.get('keywords', []),
        'platform_fit': ai_input.get('platformFit', {}),
        'technical': ai_input.get('technicalSummary', {}),
        'filename_hints': ai_input.get('extractedFilenameHints', {}),
        'video_fingerprint': ai_input.get('videoFingerprint', {}),
        'content_hints': ai_input.get('contentHints', []),
        'original_filename': ai_input.get('originalFilename', ''),
        'frame_manifest': ai_input.get('frameManifest', {}),
    }


def _text_blob(meta: Dict[str, Any]) -> str:
    tokens = meta.get('filename_hints', {}).get('tokens', []) if isinstance(meta.get('filename_hints'), dict) else []
    keywords = meta.get('keywords', []) if isinstance(meta.get('keywords'), list) else []
    hints = meta.get('content_hints', []) if isinstance(meta.get('content_hints'), list) else []
    return ' '.join([meta.get('original_filename', ''), ' '.join(tokens), ' '.join(keywords), ' '.join(hints)]).lower()


def _common_tips(base: List[str], meta: Dict[str, Any]) -> List[str]:
    tips = list(base)
    if meta['goal'] == 'leads':
        tips.append('Добавьте CTA на заявку: ссылка в профиле, оффер и конкретный следующий шаг.')
    if meta['goal'] == 'portfolio':
        tips.append('Сделайте упор на визуальный стиль и структуру монтажа как витрину портфолио.')
    if meta['brand']:
        tips.append(f"Аккуратно усилите узнаваемость бренда «{meta['brand']}» в тексте и CTA.")
    if meta['geo']:
        tips.append(f"Добавьте локальный контекст для {meta['geo']} в описании и комментарии.")
    return tips


def build_video_angle(meta: Dict[str, Any]) -> str:
    vf = meta.get('video_fingerprint', {}) or {}
    orientation = vf.get('orientation')
    res_class = vf.get('resolutionClass')
    duration_bucket = vf.get('durationBucket')
    primary_hint = vf.get('platformPrimaryHint')
    visual_hint = vf.get('visualRhythmHint', '')
    detected_model = (vf.get('detectedModel') or '').lower()
    platform_fit = meta.get('platform_fit', {}) or {}
    yt_score = int(platform_fit.get('youtubeVideo') or 0)
    text = _text_blob(meta)
    niche = str(meta.get('niche', 'general_video')).lower()

    auto_terms = ['auto', 'bmw', 'x3', 'x5', 'car', 'drift', 'авто', 'дрифт']
    has_auto = niche == 'auto' or any(term in text for term in auto_terms) or bool(detected_model)
    if orientation == 'square' and res_class == 'low':
        return 'square_low_quality_social_clip'
    if orientation == 'horizontal' and res_class == 'full_hd' and yt_score >= 70:
        return 'horizontal_youtube_story'
    if orientation == 'vertical' and duration_bucket in {'ultra_short', 'short', 'medium'}:
        return 'vertical_short_clip'

    if has_auto:
        if 'drift' in text or 'phonk' in text:
            return 'auto_drift_phonk'
        if 'review' in text or 'обзор' in text:
            return 'auto_review'
        if 'sale' in text or 'продажа' in text:
            return 'auto_sale'
        if 'detail' in text or 'detailing' in text or 'wheel' in text or 'кузов' in text or 'диск' in text:
            return 'auto_detail_showcase'
        if 'cinematic' in text or visual_hint in {'extended_story', 'mixed'}:
            return 'auto_cinematic'
        return 'auto_cinematic'

    if any(x in text for x in ['event', 'conference', 'scene', 'people', 'мероприят', 'сцена']):
        return 'event_people_scene'
    if primary_hint == 'shorts_reels_tiktok':
        return 'generic_short_video'
    if orientation == 'horizontal':
        return 'generic_horizontal_video'
    return 'generic_video'


def _generation_basis(meta: Dict[str, Any], angle: str) -> List[str]:
    basis = ['technical_fingerprint']
    if meta.get('original_filename') or (meta.get('filename_hints', {}) or {}).get('tokens'):
        basis.append('filename_hints')
    if meta.get('keywords'):
        basis.append('user_keywords')
    if len(basis) > 1 or angle.startswith('auto_'):
        basis.append('mixed_context')
    return basis


def generate_mock_seo_package(analysis_report: Dict[str, Any], platform: str) -> Dict[str, Any]:
    ai_input = analysis_report.get('ai_input', {})
    _ = build_ai_video_analysis_prompt(ai_input)
    _ = build_platform_seo_prompt(platform, ai_input)

    meta = _contextual_meta(ai_input)
    technical = meta.get('technical') or {}
    duration = float(technical.get('durationSec') or 0)
    vf = meta.get('video_fingerprint', {}) or {}
    orientation = vf.get('orientation', 'unknown')
    res_class = vf.get('resolutionClass', 'unknown')
    platform_fit = meta.get('platform_fit', {}) or {}
    yt_score = int(platform_fit.get('youtubeVideo') or 0)

    angle = ai_input.get('videoAngle') or build_video_angle(meta)
    generation_basis = ai_input.get('generationBasis') or _generation_basis(meta, angle)

    if angle == 'square_low_quality_social_clip':
        pack = {
            'bestTitle': 'Квадратный клип: как адаптировать под Reels и Shorts',
            'description': 'Видео в квадратном формате и низком разрешении. Лучше пересобрать в 9:16, усилить первый кадр и переэкспортировать в 1080×1920.',
            'hashtags': ['#shorts', '#reels', '#content', '#videoedit'],
            'coverText': 'АДАПТАЦИЯ 9:16',
            'pinnedComment': 'Нужен разбор по адаптации этого ролика в 9:16?',
            'improvementTips': _common_tips([
                'Пересобрать в вертикальный формат 9:16.',
                'Экспортировать минимум в 1080×1920.',
                'Увеличить читаемость первого кадра.',
                'Использовать этот клип как черновик, а не финальный ролик.'
            ], meta)
        }
    elif angle == 'horizontal_youtube_story':
        yt_advice = 'Формат уже сильный для YouTube Video.' if yt_score >= 70 else 'Стоит усилить структуру для YouTube и подготовить short-form версии.'
        pack = {
            'bestTitle': 'Горизонтальный ролик: сильный формат для YouTube',
            'description': f'Видео в Full HD горизонтальном формате. Лучше подходит для YouTube Video. {yt_advice}',
            'hashtags': ['#youtube', '#video', '#storytelling', '#content'],
            'coverText': 'YOUTUBE FORMAT',
            'pinnedComment': 'Сделать отдельный вертикальный cut под Shorts?',
            'improvementTips': _common_tips([
                'Использовать как обычное YouTube-видео.',
                'Сделать отдельную 9:16 версию для Shorts/Reels/TikTok.',
                'Добавить структурный хук в первые 3 секунды.'
            ], meta)
        }
    elif angle == 'auto_detail_showcase':
        pack = {
            'bestTitle': 'Авто-детали крупным планом | cinematic edit',
            'description': 'Подача ролика как демонстрация авто-деталей: экстерьер, диски, кузов и фактура кадров.',
            'hashtags': ['#авто', '#автосъемка', '#caredit', '#detailing'],
            'coverText': 'AUTO DETAILS',
            'pinnedComment': 'Какие детали показать в part 2: диски, салон или кузов?',
            'improvementTips': _common_tips(['Соберите монтаж по блокам: экстерьер → детали → финальный проезд.'], meta)
        }
    elif angle == 'event_people_scene':
        pack = {
            'bestTitle': 'Событие в кадре: динамичный видеоотчёт',
            'description': 'По формату ролика лучше подать как видеоотчёт / атмосферный фрагмент события, без жёстких утверждений о сценах.',
            'hashtags': ['#event', '#video', '#report', '#content'],
            'coverText': 'EVENT HIGHLIGHTS',
            'pinnedComment': 'Сделать продолжение в формате highlights?',
            'improvementTips': _common_tips(['Добавьте таймкоды/сцены и ключевой момент в первые секунды.'], meta)
        }
    else:
        generic_key = f'{orientation}_{res_class}_{vf.get("durationBucket", "unknown")}_{vf.get("platformPrimaryHint", "unknown")}'
        if orientation == 'vertical':
            best = 'Вертикальный клип: версия для Shorts/Reels/TikTok'
        elif orientation == 'horizontal' and res_class == 'full_hd':
            best = 'Горизонтальный Full HD: использовать как YouTube-ролик'
        elif orientation == 'square' and res_class == 'low':
            best = 'Квадратный low-res клип: нужен рефрейм и переэкспорт'
        elif duration > 180:
            best = 'Длинный ролик: сделайте long-form + short cut'
        else:
            best = 'Видео-SEO пакет по техническому профилю ролика'
        pack = {
            'bestTitle': best,
            'description': f'Generic пакет для профиля {generic_key}. SEO зависит от technical fingerprint и platform fit.',
            'hashtags': ['#video', '#seo', '#content', '#creator'],
            'coverText': 'VIDEO FORMAT',
            'pinnedComment': 'Нужна адаптация под другую платформу?',
            'improvementTips': _common_tips(['Соберите первую сцену как чёткий хук.', 'Проверьте адаптацию под целевую платформу.'], meta)
        }

    if platform in {'youtubeShorts', 'instagramReels', 'tiktok'} and orientation != 'vertical':
        pack['improvementTips'].append('Для short-form платформ нужен рефрейм в 9:16.')
    if platform in {'youtubeShorts', 'instagramReels', 'tiktok'} and res_class == 'low':
        pack['improvementTips'].append('Нужен реэкспорт в более высоком качестве (минимум 1080×1920).')
    if platform in {'youtubeShorts', 'instagramReels', 'tiktok'} and vf.get('durationBucket') in {'ultra_short', 'short'}:
        pack['improvementTips'].append('Сфокусируйте первые 0.5–2 секунды на самом сильном моменте (hook-first).')
    if platform == 'youtubeVideo' and yt_score < 60:
        pack['description'] += ' Сейчас YouTube Video оценён ниже 60: лучше дополнительно подготовить short-form версию.'

    pack['videoAngle'] = angle
    pack['generationBasis'] = generation_basis
    return pack
