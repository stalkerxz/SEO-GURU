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
    }


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


def generate_mock_seo_package(analysis_report: Dict[str, Any], platform: str) -> Dict[str, Any]:
    ai_input = analysis_report.get('ai_input', {})
    _ = build_ai_video_analysis_prompt(ai_input)
    _ = build_platform_seo_prompt(platform, ai_input)

    technical = analysis_report.get('technical', {})
    duration = float(technical.get('durationSec') or 0)
    width, height = _parse_resolution(technical.get('resolution'))
    vertical = bool(width and height and height > width)
    base_tips = ['Усильте хук в первые 1–3 секунды.', 'Добавьте более ясный CTA в конце ролика.']
    if not vertical:
        base_tips.append('Подготовьте вертикальную версию 9:16 для short-form платформ.')
    if duration > 180:
        base_tips.append('Сделайте короткую версию до 60–180 секунд.')

    meta = _contextual_meta(ai_input)
    tips = _common_tips(base_tips, meta)
    niche_prefix = 'Авто' if meta['niche'] == 'auto' else 'Контент'
    kw = ', '.join(meta['keywords'][:3]) if isinstance(meta['keywords'], list) and meta['keywords'] else 'видео'
    brand = f" · {meta['brand']}" if meta['brand'] else ''
    geo = f" в {meta['geo']}" if meta['geo'] else ''

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
