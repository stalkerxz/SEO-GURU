from typing import Any, Dict, List

from seo_prompt_builder import build_ai_video_analysis_prompt, build_platform_seo_prompt

FORBIDDEN_TERMS = {
    'video_yt_full_HD', 'shorts_reels_tiktok', 'needs_adaptation', 'horizontal_youtube_story',
    'vertical_short_clip', 'square_low_quality_social_clip', 'ultra_hd_short', 'general_video',
    'views_and_reach', 'full_hd', 'ultra_hd', 'technical_fingerprint', 'filename_hints',
    'user_keywords', 'mixed_context', 'auto_drift_phonk', 'auto_cinematic', 'auto_detail_showcase',
    'generic_video', 'generic_horizontal_video'
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
        pack.get('hookText', ''), pack.get('firstLineHook', ''), pack.get('trendAngle', ''), pack.get('caption', ''),
        pack.get('storyAnnouncement', ''), pack.get('cta', ''), pack.get('altText', ''), pack.get('thumbnailText', ''),
        ' '.join(pack.get('titleOptions', [])), ' '.join(pack.get('hashtags', [])), ' '.join(pack.get('tags', []))
    ]).lower()
    for term in FORBIDDEN_TERMS:
        if term.lower() in blob:
            raise ValueError(f'Forbidden technical term leaked into SEO copy: {term}')


def build_youtube_video_package(meta: Dict[str, Any], angle: str, subject: str, tips: List[str]) -> Dict[str, Any]:
    if angle == 'horizontal_youtube_story':
        return {
            'bestTitle': 'Горизонтальный ролик для YouTube: сильный формат',
            'titleOptions': [
                'Горизонтальный ролик для YouTube: сильный формат',
                'Full HD история для YouTube Video',
                f'{subject}: полноценный YouTube-формат',
                'Как раскрыть ролик в длинном формате YouTube',
                'YouTube Video версия: структура, ритм, результат'
            ],
            'description': 'Это основной горизонтальный формат для YouTube Video в Full HD.\n\n'
                           'В ролике есть пространство для истории: вступление, развитие и финальный акцент, поэтому зритель дольше удерживается.\n\n'
                           'Сделайте описание структурным: что в видео, почему это важно, и кого заинтересует.\n\n'
                           'Добавьте CTA в конце: подписка, комментарий и переход к следующему ролику.',
            'tags': ['YouTube Video', 'Full HD', 'горизонтальный ролик', 'видеомонтаж', 'контент для YouTube', 'story edit', 'cinematic', 'brand content', 'video production', 'SMM видео'],
            'thumbnailText': 'YOUTUBE FORMAT',
            'pinnedComment': 'Сделать из этого ролика отдельный вертикальный cut для Shorts?',
            'improvementTips': tips + ['Добавьте обложку 16:9 с крупным объектом и коротким текстом.', 'Добавьте структуру в описание: хук, суть, CTA.', 'Соберите отдельную Shorts-версию из самого сильного момента.']
        }
    return {
        'bestTitle': f'{subject} в drift/cinematic формате — сильный авто-ролик',
        'titleOptions': [
            f'{subject} Drift & Cinematic: полный авто-ролик',
            f'{subject}: дым, ритм и cinematic монтаж',
            f'Авто-ролик про {subject} — динамика и атмосфера',
            f'{subject}: как выглядит drift edit в длинном формате',
            f'{subject} — уличный стиль, скорость и визуальный ритм'
        ],
        'description': f'В этом видео {subject} показан через сочетание drift-динамики и cinematic подачи.\n\n'
                       'Почему стоит смотреть: насыщенный темп, выразительный звук и монтаж, который держит внимание до финала.\n\n'
                       f'Если вам близка тема авто-контента, дрифта и брендовой визуальной стилистики, это видео точно зайдёт. {meta.get("geo", "")}'.strip()
                       + '\n\nОцените монтаж в комментариях и подпишитесь, чтобы не пропустить следующую серию.',
        'tags': [subject, 'drift', 'cinematic car edit', 'car video', 'автосъемка', 'car montage', 'street drift', 'phonk drift', 'auto content', 'BMW', 'Tyumen', 'PROTOPOPOV PRODUCTION'],
        'thumbnailText': 'BMW X3 DRIFT' if 'x3' in subject.lower() else 'DRIFT CINEMATIC',
        'pinnedComment': 'Какой момент оставить главным в следующем видео: больше дыма или больше cinematic?',
        'improvementTips': tips + ['Добавьте обложку 16:9 с контрастным текстом.', 'Сделайте описание из 2–4 абзацев с логичной структурой.', 'Подготовьте отдельную версию для Shorts с другим темпом.']
    }


def build_youtube_shorts_package(meta: Dict[str, Any], angle: str, subject: str, tips: List[str]) -> Dict[str, Any]:
    if angle == 'horizontal_youtube_story':
        desc = 'Это горизонтальный исходник. Для Shorts сделайте 9:16 cut на 10–20 секунд с самым сильным моментом.'
    elif angle == 'square_low_quality_social_clip':
        desc = 'Квадрат и низкое качество. Сначала пересоберите в 9:16 и переэкспортируйте в Full HD.'
    else:
        desc = f'{subject} в коротком динамичном фрагменте. Хук с первых кадров и акцент на ритм.'
    return {
        'bestTitle': f'{subject} Drift Mode 🔥' if 'bmw' in subject.lower() else f'{subject} в режиме максимального вайба 🔥',
        'titleOptions': [f'{subject} Drift Mode 🔥', f'{subject} за 15 секунд', 'Drift. Smoke. Repeat.', 'Phonk + speed = wow', 'Cinematic punch cut'],
        'description': desc,
        'hashtags': ['#Shorts', '#BMW', '#BMWX3', '#Drift', '#Phonk', '#CarEdit'],
        'coverText': 'BMW X3\nDRIFT MODE' if 'x3' in subject.lower() else 'DRIFT\nMODE',
        'pinnedComment': 'Больше дыма или больше cinematic?',
        'hookText': f'{subject} в drift mode за 15 секунд',
        'improvementTips': tips + ['Первые 0.5 сек должны сразу цеплять.', 'Текст на экране лучше сделать крупнее.', 'Не перегружайте описание — 1–2 строки достаточно.']
    }


def build_instagram_reels_package(meta: Dict[str, Any], angle: str, subject: str, tips: List[str]) -> Dict[str, Any]:
    caption = f'{subject}, немного дыма и cinematic-настроение. Какой кадр сильнее — первый или финальный?'
    if angle == 'horizontal_youtube_story':
        caption = 'Горизонтальный исходник выглядит сильно, но для Reels нужен вертикальный 9:16 cut. Какой момент вынести в first frame?'
    elif angle == 'square_low_quality_social_clip':
        caption = 'Квадратный черновик с низким качеством. Перед публикацией в Reels лучше сделать чистый re-export в 9:16.'
    return {
        'caption': caption,
        'firstLineHook': f'{subject} в cinematic drift mood',
        'hashtags': ['#bmw', '#bmwx3', '#drift', '#автосъемка', '#reels', '#cargram'],
        'altText': f'Короткий авто-ролик с {subject}: динамичные проезды, дым и cinematic переходы.',
        'coverText': 'BMW X3 / CINEMATIC' if 'x3' in subject.lower() else 'CINEMATIC / DRIFT',
        'pinnedComment': 'Оставить больше дрифта или сделать чистый cinematic?',
        'storyAnnouncement': 'Новый авто-ролик уже в Reels. Залетайте оценить монтаж.',
        'cta': 'Сохрани, если нравится такой стиль авто-контента.',
        'improvementTips': tips + ['Сделайте обложку с крупной моделью авто.', 'Первая строка caption должна быть хук-фразой.', 'Лучше использовать 5–7 hashtag, а не 20.']
    }


def build_tiktok_package(meta: Dict[str, Any], angle: str, subject: str, tips: List[str]) -> Dict[str, Any]:
    caption = f'{subject} + drift mood. Залетит?'
    if angle == 'horizontal_youtube_story':
        caption = 'Горизонтальный исходник. Нужен 9:16 cut с самым резким моментом.'
    elif angle == 'square_low_quality_social_clip':
        caption = 'Квадратный черновик — лучше переэкспорт в 9:16 Full HD перед публикацией.'
    return {
        'caption': caption,
        'hookText': f'{subject} ушёл в drift mode',
        'hashtags': ['#bmw', '#drift', '#phonk', '#caredit', '#cartok'],
        'coverText': 'DRIFT MODE',
        'pinnedComment': 'Part 2 ночью?',
        'cta': 'Пиши, какой авто сделать следующим.',
        'trendAngle': 'phonk drift edit / cinematic car transition',
        'improvementTips': tips + ['Резкий хук должен быть до 1 секунды.', 'Меньше текста, больше ритма.', 'Используйте звук и бит как основу монтажа.']
    }


def generate_mock_seo_package(analysis_report: Dict[str, Any], platform: str) -> Dict[str, Any]:
    ai_input = analysis_report.get('ai_input', {})
    _ = build_ai_video_analysis_prompt(ai_input)
    _ = build_platform_seo_prompt(platform, ai_input)

    meta = _contextual_meta(ai_input)
    vf = meta.get('video_fingerprint', {}) or {}
    subject = detect_subject(meta)
    angle = ai_input.get('videoAngle') or build_video_angle(meta)
    generation_basis = ai_input.get('generationBasis') or _generation_basis(meta, angle)

    base_tips = _common_tips(['Проверьте первые секунды: они должны сразу цеплять внимание.'], meta)
    if platform == 'youtubeVideo':
        pack = build_youtube_video_package(meta, angle, subject, base_tips)
    elif platform == 'youtubeShorts':
        pack = build_youtube_shorts_package(meta, angle, subject, base_tips)
    elif platform == 'instagramReels':
        pack = build_instagram_reels_package(meta, angle, subject, base_tips)
    else:
        pack = build_tiktok_package(meta, angle, subject, base_tips)
    _assert_readable(pack)
    pack['videoAngle'] = angle
    pack['generationBasis'] = generation_basis
    return pack
