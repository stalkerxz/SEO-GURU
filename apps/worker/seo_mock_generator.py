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


def _contextual_meta(ai_input: Dict[str, Any]) -> Dict[str, Any]:
    return {
        'goal': ai_input.get('userGoal', 'views_and_reach'),
        'niche': ai_input.get('niche', 'general_video'),
        'geo': ai_input.get('geo', ''),
        'brand': ai_input.get('brandName', ''),
        'keywords': ai_input.get('keywords', []),
        'platform_fit': ai_input.get('platformFit', {}),
        'technical': ai_input.get('technicalSummary', {}),
        'geo': ai_input.get('geo', ''),
        'filename_hints': ai_input.get('extractedFilenameHints', {}),
        'video_fingerprint': ai_input.get('videoFingerprint', {}),
        'content_hints': ai_input.get('contentHints', []),
    }


def _detect_auto_subject(meta: Dict[str, Any]) -> str:
    keywords = [str(x).strip() for x in (meta.get('keywords') or []) if str(x).strip()]
    full = ' '.join(keywords).lower()
    for model in ['bmw x5', 'bmw x3']:
        if model in full:
            return model.upper().replace('X', 'X')
    hints = meta.get('filename_hints', {}) or {}
    detected = hints.get('detectedModel')
    if isinstance(detected, str) and detected.strip():
        return detected.strip()
    return 'BMW'


def _common_tips(base: List[str], meta: Dict[str, Any]) -> List[str]:
    tips = list(base)
    if meta['goal'] == 'leads':
        tips.append('Добавьте CTA на заявку: ссылка в профиле, оффер и конкретный следующий шаг.')
    if meta['goal'] == 'portfolio':
        tips.append('Сделайте упор на визуальный стиль, цвет и качество монтажа как витрину портфолио.')
    if meta['brand']:
        tips.append(f"Аккуратно усилите узнаваемость бренда «{meta['brand']}» в тексте и призыве к действию.")
    if meta['geo']:
        tips.append(f"Добавьте локальный контекст для {meta['geo']} в описании и призыве.")
    return tips


def build_video_specific_angle(meta: Dict[str, Any]) -> str:
    hints = set(meta.get('content_hints') or [])
    if meta.get('niche') == 'auto':
        if 'drift' in hints and 'phonk_music' in hints:
            return 'auto_drift_phonk'
        if 'review' in hints:
            return 'auto_review'
        if 'sale_video' in hints:
            return 'auto_sale'
        if 'night_scene' in hints:
            return 'auto_night'
        if 'cinematic_style' in hints:
            return 'auto_cinematic'
        return 'generic_auto'
    return 'generic_video'


def generate_mock_seo_package(analysis_report: Dict[str, Any], platform: str) -> Dict[str, Any]:
    ai_input = analysis_report.get('ai_input', {})
    _ = build_ai_video_analysis_prompt(ai_input)
    _ = build_platform_seo_prompt(platform, ai_input)

    technical = analysis_report.get('technical', {})
    duration = float(technical.get('durationSec') or 0)
    width, height = _parse_resolution(technical.get('resolution'))
    vertical = bool(width and height and height > width)
    meta = _contextual_meta(ai_input)
    base_tips = ['Усильте хук в первые 1–3 секунды.', 'Добавьте более ясный CTA в конце ролика.']
    video_fingerprint = meta.get('video_fingerprint') or {}
    content_hints = set(meta.get('content_hints') or [])
    angle = build_video_specific_angle(meta)
    if not vertical:
        base_tips.append('Подготовьте вертикальную версию 9:16 для short-form платформ.')
    if video_fingerprint.get('resolutionClass') == 'low' or video_fingerprint.get('orientation') == 'square':
        base_tips.append('Текущий формат/разрешение слабо подходит для Reels/TikTok/Shorts: лучше 9:16 и минимум HD.')
    if duration > 180:
        base_tips.append('Сделайте короткую версию до 60–180 секунд.')
    if duration < 10:
        base_tips.append('Это очень короткий хук: усилите первые 0.5 секунды самым контрастным моментом.')

    tips = _common_tips(base_tips, meta)
    niche_prefix = 'Авто' if meta['niche'] == 'auto' else 'Контент'
    kw = ', '.join(meta['keywords'][:3]) if isinstance(meta['keywords'], list) and meta['keywords'] else 'видео'
    brand = f" · {meta['brand']}" if meta['brand'] else ''
    geo = f" в {meta['geo']}" if meta['geo'] else ''

    if meta['niche'] == 'auto':
        subject = _detect_auto_subject(meta)
        geo_tag = f" ({meta['geo']})" if meta['geo'] else ''
        brand_line = f" от {meta['brand']}" if meta['brand'] else ''
        short_video_hint = float(meta.get('technical', {}).get('durationSec') or 0) <= 60
        auto_hash_ru = ['#АвтоВидео', '#АвтоСъемка']
        duration_phrase = 'динамичный фрагмент' if duration > 30 else 'короткий ролик'
        if platform == 'youtubeShorts':
            if angle == 'auto_drift_phonk':
                titles = [f'{subject} Drift Mode под phonk', f'{subject} drift / phonk edit', f'{subject} — дым и контроль']
            elif angle == 'auto_review':
                titles = [f'{subject}: быстрый обзор деталей', f'{subject} — мнение и ключевые фишки', f'{subject} review short']
            elif angle == 'auto_sale':
                titles = [f'Видео для продажи {subject}: что показать первым', f'{subject} на продажу — состояние и детали', f'{subject} sale preview']
            elif angle == 'auto_night':
                titles = [f'{subject} — ночной cinematic edit', f'{subject} в city lights', f'Night drive short | {subject}']
            elif angle == 'auto_cinematic':
                titles = [f'{subject} в cinematic стиле', f'Cinematic car edit | {subject}', f'{subject} — атмосферный проезд']
            else:
                titles = [f'{subject} авто-ролик в cinematic стиле', f'{subject} short car edit', f'{subject} динамичный монтаж']
            return {
                'titleOptions': titles,
                'bestTitle': titles[0],
                'description': f'{duration_phrase.capitalize()} {geo_tag}{brand_line}. Упор на video-specific подачу с учётом технических и контекстных hints.',
                'hashtags': ['#Shorts', '#BMW', f"#{subject.replace(' ', '')}", '#Drift' if 'drift' in content_hints else '#CarEdit', '#driftmode' if 'drift' in content_hints else '#Cinematic', *auto_hash_ru][:7],
                'coverText': f'{subject} / DRIFT MODE',
                'pinnedComment': 'Оставить больше дыма или cinematic-проезды?' if 'drift' in content_hints else 'Какой стиль заходит больше — cinematic или drive edit?',
                'improvementTips': tips
            }
        if platform == 'instagramReels':
            return {
                'caption': f'{subject} в деле{geo_tag}. Быстрый cinematic car edit, как вам вайб?{brand_line}',
                'hashtags': ['#bmw', f"#{subject.replace(' ', '').lower()}", '#drift', '#автосъемка', f"#{meta['geo'].lower()}" if meta['geo'] else '#reels', '#reels'][:6],
                'coverText': f'{subject} • CINEMATIC',
                'pinnedComment': 'Оставить больше дрифта или добавить спокойных проездов?',
                'improvementTips': tips
            }
        if platform == 'tiktok':
            return {
                'caption': f'{subject} + {"phonk drift" if "phonk_music" in content_hints else "car edit"}? Проверим залетит ли 🔥',
                'hookText': f'{subject} + {"drift mode" if "drift" in content_hints else "cinematic mode"}?',
                'trendAngle': 'phonk / drift / cinematic car edit' if 'phonk_music' in content_hints else angle,
                'hashtags': ['#bmw', '#drift' if 'drift' in content_hints else '#caredit', '#caredit', '#tiktokauto', '#phonk' if 'phonk_music' in content_hints else '#cinematic', '#автосъемка'],
                'pinnedComment': 'Сделать part 2 с ночной съёмкой?',
                'improvementTips': tips
            }
        if platform == 'youtubeVideo':
            long_form_hint = 'Основной формат лучше публиковать как Shorts.' if short_video_hint else 'Можно выпускать как обычное YouTube видео.'
            geo_label = meta['geo'] or 'по проекту'
            return {
                'titleOptions': [f'{subject}: cinematic drift edit', f'{subject} — авто монтаж и разбор'],
                'bestTitle': f'{subject} cinematic drift edit | авто-разбор',
                'description': f'{long_form_hint} В описании добавьте гео {geo_label} и бренд{brand_line or ""}.',
                'hashtags': ['#BMW', '#CarEdit', '#Drift', '#YouTubeVideo', '#АвтоВидео', '#Cinematic'],
                'pinnedComment': 'Если нужен long-version breakdown — написать отдельный разбор?',
                'improvementTips': tips
            }

    return {
        'titleOptions': [f'{niche_prefix}-разбор: как усилить ролик{geo}', f'{niche_prefix}: быстрые улучшения для охватов{brand}'],
        'bestTitle': f'{niche_prefix}-SEO: практичный разбор{brand}',
        'description': f'Готовый SEO-пакет{geo}. Упор на цель «{meta["goal"]}», нишу «{meta["niche"]}» и ключевые темы: {kw}.',
        'caption': f'Прокачиваем ролик{geo}: структура, хук, монтаж, CTA. {brand}'.strip(),
        'hashtags': ['#video', '#seo', '#content', '#shorts', '#reels', '#tiktok'][:6],
        'tags': [kw, meta['niche'], meta['goal']],
        'coverText': f'{niche_prefix.upper()} SEO',
        'thumbnailText': f'{niche_prefix.upper()} SEO',
        'pinnedComment': f'Нужен разбор под вашу цель «{meta["goal"]}»{geo}? Напишите в комментариях.',
        'cta': f'Сохраните и примените к следующему ролику{geo}.',
        'improvementTips': tips,
    }
