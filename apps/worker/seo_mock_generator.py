from typing import Any, Dict, List

from seo_prompt_builder import build_ai_video_analysis_prompt, build_platform_seo_prompt

FORBIDDEN_TERMS = {
    'video_yt_full_HD', 'shorts_reels_tiktok', 'needs_adaptation', 'horizontal_youtube_story',
    'vertical_short_clip', 'square_low_quality_social_clip', 'ultra_hd_short', 'general_video',
    'views_and_reach', 'full_hd', 'ultra_hd', 'technical_fingerprint', 'filename_hints',
    'user_keywords', 'mixed_context'
}


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


def readable_goal(goal: str) -> str:
    return {
        'views_and_reach': 'охваты и просмотры',
        'subscribers': 'рост подписчиков',
        'leads': 'получение заявок',
        'portfolio': 'презентация портфолио',
        'sales': 'продажи',
    }.get(str(goal), 'продвижение видео')


def readable_niche(niche: str) -> str:
    return {
        'auto': 'авто-контент', 'general_video': 'видео общего формата', 'travel': 'travel-контент'
    }.get(str(niche), 'контент для соцсетей')


def readable_angle(angle: str) -> str:
    return {
        'horizontal_youtube_story': 'горизонтальный ролик для YouTube',
        'vertical_short_clip': 'вертикальный короткий ролик',
        'square_low_quality_social_clip': 'квадратный ролик с низким качеством',
        'auto_drift_phonk': 'авто / drift / phonk',
        'auto_cinematic': 'авто / cinematic',
        'auto_review': 'авто / обзор',
        'auto_sale': 'авто / продажа',
        'auto_detail_showcase': 'авто / детали',
    }.get(str(angle), 'универсальный формат ролика')


def readable_resolution_class(resolution_class: str) -> str:
    return {
        'low': 'низкое разрешение',
        'full_hd': 'Full HD',
        'ultra_hd': 'высокое разрешение',
    }.get(str(resolution_class), 'стандартное разрешение')


def readable_platform_hint(hint: str) -> str:
    return {
        'video_yt_full_HD': 'горизонтальный формат для YouTube',
        'shorts_reels_tiktok': 'формат для Shorts/Reels/TikTok',
        'needs_adaptation': 'нужна адаптация формата',
    }.get(str(hint), 'универсальная публикация')


def detect_subject(meta: Dict[str, Any]) -> str:
    vf = meta.get('video_fingerprint', {}) or {}
    model = (vf.get('detectedModel') or '').strip()
    if model:
        return model
    tokens = ' '.join((meta.get('filename_hints', {}) or {}).get('tokens', [])).lower()
    text = _text_blob(meta)
    if 'bmw' in tokens and 'x3' in tokens or 'bmw x3' in text:
        return 'BMW X3'
    if 'bmw' in tokens and 'x5' in tokens or 'bmw x5' in text:
        return 'BMW X5'
    if any(x in text for x in ['drift', 'phonk', 'авто', 'car']):
        return 'авто-ролик'
    return 'ролик'


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
    visual_hint = vf.get('visualRhythmHint', '')
    text = _text_blob(meta)
    niche = str(meta.get('niche', 'general_video')).lower()

    auto_terms = ['auto', 'bmw', 'x3', 'x5', 'car', 'drift', 'авто', 'дрифт', 'phonk', 'cinematic']
    has_auto = niche == 'auto' or any(term in text for term in auto_terms) or bool(vf.get('detectedModel'))

    if orientation == 'square' and res_class == 'low':
        return 'square_low_quality_social_clip'

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

    if orientation == 'horizontal' and res_class == 'full_hd':
        return 'horizontal_youtube_story'
    if orientation == 'vertical' and duration_bucket in {'ultra_short', 'short', 'medium'}:
        return 'vertical_short_clip'
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


def _assert_readable(pack: Dict[str, Any]) -> None:
    blob = ' '.join([
        pack.get('bestTitle', ''), pack.get('description', ''), pack.get('coverText', ''), pack.get('pinnedComment', ''),
        ' '.join(pack.get('titleOptions', [])), ' '.join(pack.get('hashtags', []))
    ]).lower()
    for term in FORBIDDEN_TERMS:
        if term.lower() in blob:
            raise ValueError(f'Forbidden technical term leaked into SEO copy: {term}')


def _platformize(pack: Dict[str, Any], platform: str, subject: str) -> Dict[str, Any]:
    result = dict(pack)
    if platform == 'youtubeVideo':
        result['description'] = f"{result['description']}\n\nСтруктура для YouTube: хук в начале, развитие сюжета и финальный CTA."
    elif platform == 'youtubeShorts':
        result['bestTitle'] = result.get('titleOptions', [result['bestTitle']])[0]
    elif platform == 'instagramReels':
        result['description'] = f"{result['description']} Сохраняйте идею для следующего монтажа с {subject}."
    elif platform == 'tiktok':
        result['description'] = f"{result['description']} Коротко, резко, в трендовом ритме."
    return result


def generate_mock_seo_package(analysis_report: Dict[str, Any], platform: str) -> Dict[str, Any]:
    ai_input = analysis_report.get('ai_input', {})
    _ = build_ai_video_analysis_prompt(ai_input)
    _ = build_platform_seo_prompt(platform, ai_input)

    meta = _contextual_meta(ai_input)
    vf = meta.get('video_fingerprint', {}) or {}
    subject = detect_subject(meta)
    angle = ai_input.get('videoAngle') or build_video_angle(meta)
    generation_basis = ai_input.get('generationBasis') or _generation_basis(meta, angle)

    if angle == 'auto_drift_phonk':
        pack = {
            'bestTitle': f'{subject} Drift Mode под phonk',
            'titleOptions': [
                f'{subject} Drift Mode под phonk',
                f'{subject}: дым, скорость и cinematic',
                f'Drift edit: {subject} в кадре'
            ],
            'description': f'Короткий вертикальный ролик с {subject} в drift/cinematic стиле. Подходит для Shorts, Reels и TikTok: быстрый хук, динамика и понятный визуальный образ.',
            'hashtags': ['#Shorts', '#BMW', '#BMWX3', '#Drift', '#Phonk', '#АвтоСъемка', '#CarEdit', '#Cinematic'],
            'coverText': 'BMW X3 DRIFT MODE' if 'x3' in subject.lower() else 'DRIFT MODE',
            'pinnedComment': 'Больше cinematic или больше дрифта?',
            'improvementTips': _common_tips(['Добавьте плотный хук в первые 1–2 секунды и держите ритм под музыку.'], meta)
        }
    elif angle == 'auto_cinematic':
        pack = {
            'bestTitle': f'{subject}: cinematic атмосфера в движении',
            'titleOptions': [f'{subject}: cinematic атмосфера в движении', f'{subject} в свете города', 'Атмосферный авто-ролик в стиле cinematic'],
            'description': f'Атмосферный ролик про {subject}: свет, движение и стильный монтаж. Подходит для публикации на Shorts, Reels и TikTok.',
            'hashtags': ['#BMW', '#Cinematic', '#CarEdit', '#АвтоСъемка', '#Shorts'],
            'coverText': 'CINEMATIC DRIVE',
            'pinnedComment': 'Оставить плавный вайб или ускорить монтаж?',
            'improvementTips': _common_tips(['Усильте световые акценты и плавные переходы в середине ролика.'], meta)
        }
    elif angle == 'horizontal_youtube_story':
        pack = {
            'bestTitle': 'Горизонтальный ролик для YouTube: сильный формат',
            'titleOptions': ['Горизонтальный ролик для YouTube: сильный формат', 'Сильная YouTube-версия в Full HD', 'Формат для YouTube Video без потери качества'],
            'description': 'Видео снято в горизонтальном Full HD формате, поэтому лучше подходит для YouTube Video. Для Shorts/Reels/TikTok стоит сделать отдельную вертикальную версию.',
            'hashtags': ['#YouTube', '#Видео', '#Контент', '#Монтаж', '#SMM'],
            'coverText': 'YOUTUBE FORMAT',
            'pinnedComment': 'Сделать отдельную короткую версию под Shorts?',
            'improvementTips': _common_tips(['Оставьте эту версию как основную для YouTube, а короткую соберите отдельно в 9:16.'], meta)
        }
    elif angle == 'square_low_quality_social_clip':
        pack = {
            'bestTitle': 'Квадратный клип: нужна адаптация под Reels и Shorts',
            'titleOptions': ['Квадратный клип: нужна адаптация под Reels и Shorts', 'Черновой клип: пересоберите под 9:16', 'Квадратный формат: как подготовить к публикации'],
            'description': 'Ролик в квадратном формате и низком разрешении лучше использовать как черновик. Для публикации стоит пересобрать его в 9:16 и экспортировать минимум в Full HD.',
            'hashtags': ['#Reels', '#Shorts', '#ВидеоМонтаж', '#Контент', '#SMM'],
            'coverText': 'АДАПТАЦИЯ ФОРМАТА',
            'pinnedComment': 'Собрать финальную вертикальную версию?',
            'improvementTips': _common_tips(['Сначала делайте рефрейм 9:16, затем переэкспорт в Full HD.'], meta)
        }
    else:
        best_title = f'Вертикальный ролик для Shorts, Reels и TikTok' if angle == 'vertical_short_clip' and subject == 'ролик' else f'{subject}: вертикальный ролик для Shorts, Reels и TikTok'
        pack = {
            'bestTitle': best_title,
            'titleOptions': [best_title, f'{subject}: короткий динамичный формат', 'Короткое видео под соцсети'],
            'description': (
                f'Готовый к публикации ролик в формате {readable_angle(angle)}. '
                f'Цель — {readable_goal(meta.get("goal"))}, ниша — {readable_niche(meta.get("niche"))}. '
                f'Текущее качество: {readable_resolution_class(vf.get("resolutionClass"))}, рекомендация платформы: {readable_platform_hint(vf.get("platformPrimaryHint"))}.'
            ),
            'hashtags': ['#Shorts', '#Reels', '#TikTok', '#Контент', '#Видео'],
            'coverText': 'SHORT FORMAT',
            'pinnedComment': 'Нужна версия с другим темпом монтажа?',
            'improvementTips': _common_tips(['Проверьте первые секунды: они должны сразу цеплять внимание.'], meta)
        }

    pack = _platformize(pack, platform, subject)
    _assert_readable(pack)
    pack['videoAngle'] = angle
    pack['generationBasis'] = generation_basis
    return pack
