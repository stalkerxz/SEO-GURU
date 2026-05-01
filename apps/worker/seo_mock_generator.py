import re
from typing import Any, Dict, List

from seo_prompt_builder import build_ai_video_analysis_prompt, build_platform_seo_prompt

FORBIDDEN_TERMS = {
    'video_yt_full_HD', 'shorts_reels_tiktok', 'needs_adaptation', 'horizontal_youtube_story',
    'vertical_short_clip', 'square_low_quality_social_clip', 'ultra_hd_short', 'general_video',
    'views_and_reach', 'full_hd', 'ultra_hd', 'technical_fingerprint', 'filename_hints',
    'user_keywords', 'mixed_context', 'auto_drift_phonk', 'auto_cinematic', 'auto_detail_showcase',
    'generic_video', 'generic_horizontal_video'
}
TRAVEL_FORBIDDEN_AUTO_TERMS = {'bmw', 'drift', 'phonk', 'авто-ролик', 'street drift'}
AUTO_BRANDS_MODELS = ['bmw', 'mercedes', 'audi', 'toyota', 'kia', 'porsche', 'x3', 'x5', 'tesla', 'lexus', 'honda', 'hyundai']


def _contextual_meta(ai_input: Dict[str, Any]) -> Dict[str, Any]:
    content_hints = ai_input.get('contentHints', [])
    niche = str(ai_input.get('niche', 'general_video')).lower()
    filename = str(ai_input.get('originalFilename', '') or '')
    keywords = ai_input.get('keywords', []) if isinstance(ai_input.get('keywords'), list) else []
    auto_signal_text = ' '.join([filename, ' '.join(keywords)]).lower()
    has_explicit_auto = _has_any(auto_signal_text, AUTO_BRANDS_MODELS)
    if niche == 'travel' and isinstance(content_hints, list) and not has_explicit_auto:
        content_hints = [hint for hint in content_hints if hint != 'auto_model']
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
        'content_hints': content_hints,
        'original_filename': ai_input.get('originalFilename', ''),
        'frame_manifest': ai_input.get('frameManifest', {}),
    }


def _text_blob(meta: Dict[str, Any]) -> str:
    tokens = meta.get('filename_hints', {}).get('tokens', []) if isinstance(meta.get('filename_hints'), dict) else []
    keywords = meta.get('keywords', []) if isinstance(meta.get('keywords'), list) else []
    hints = meta.get('content_hints', []) if isinstance(meta.get('content_hints'), list) else []
    return ' '.join([meta.get('original_filename', ''), ' '.join(tokens), ' '.join(keywords), ' '.join(hints)]).lower()


def _has_any(text: str, terms: List[str]) -> bool:
    return any(term in text for term in terms)


def _has_travel_signal(meta: Dict[str, Any], text: str) -> bool:
    return str(meta.get('niche', '')).lower() == 'travel' or _has_any(
        text, ['travel', 'trip', 'vacation', 'maldives', 'мальдивы', 'турция', 'турецкие', 'море', 'пляж', 'отель', 'курорт', 'отдых', 'путешествие']
    )


def _has_resort_signal(text: str) -> bool:
    return _has_any(text, ['море', 'пляж', 'maldives', 'мальдивы', 'курорт', 'отель', 'resort', 'beach', 'sea'])


def _has_strong_auto_signal(meta: Dict[str, Any], text: str) -> bool:
    niche = str(meta.get('niche', '')).lower()
    has_model = _has_any(text, ['bmw', 'mercedes', 'audi', 'toyota', 'kia', 'porsche', 'x3', 'x5'])
    has_core = _has_any(text, ['auto', 'авто', 'car', 'cars', 'wheel', 'wheels', 'диск', 'диски', 'detailing', 'кузов'])
    has_auto_salon = 'салон' in text and _has_any(text, ['авто', 'car', 'bmw', 'audi', 'mercedes'])
    has_drift_strong = _has_any(text, ['drift', 'дрифт']) and (niche == 'auto' or has_model or has_core)
    return has_model or has_core or has_auto_salon or has_drift_strong or (niche == 'auto' and _has_any(text, ['review', 'обзор', 'sale', 'продажа']))


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
    if 'турецкие мальдивы' in text:
        return 'Турецкие Мальдивы'
    if _has_travel_signal(meta, text):
        return 'путешествие'
    if 'bmw' in tokens and 'x3' in tokens or 'bmw x3' in text:
        return 'BMW X3'
    if 'bmw' in tokens and 'x5' in tokens or 'bmw x5' in text:
        return 'BMW X5'
    if _has_strong_auto_signal(meta, text):
        return 'авто-ролик'
    return 'ролик'


def is_auto_angle(angle: str) -> bool:
    return angle in {'auto_drift_phonk', 'auto_cinematic', 'auto_review', 'auto_sale', 'auto_detail_showcase'}


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
    duration_sec = float((meta.get('technical', {}) or {}).get('durationSec') or 0)
    text = _text_blob(meta)
    niche = str(meta.get('niche', 'general_video')).lower()
    has_auto = _has_strong_auto_signal(meta, text) or bool(vf.get('detectedModel'))
    has_travel = _has_travel_signal(meta, text) or _has_any(' '.join(meta.get('content_hints', [])), ['travel_scene', 'destination_video', 'resort_or_beach'])

    if orientation == 'square' and res_class == 'low':
        return 'square_low_quality_social_clip'

    if has_auto and niche == 'auto':
        if 'drift' in text or 'phonk' in text:
            return 'auto_drift_phonk'
        if 'review' in text or 'обзор' in text:
            return 'auto_review'
        if 'sale' in text or 'продажа' in text:
            return 'auto_sale'
        if 'detail' in text or 'detailing' in text or 'wheel' in text or 'кузов' in text or 'диск' in text:
            return 'auto_detail_showcase'
        return 'auto_cinematic'

    if has_travel:
        if orientation == 'vertical' and 0 < duration_sec <= 180:
            return 'travel_destination_short'
        if _has_resort_signal(text) or 'resort_or_beach' in (meta.get('content_hints') or []):
            return 'travel_resort_reels'
        if orientation == 'horizontal':
            return 'travel_horizontal_story'

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




def _sanitize_text_value(text: str) -> str:
    sanitized = text
    replacements = [
        (r'\bstreet drift\b', ''),
        (r'авто-ролик', 'travel-ролик'),
        (r'авто-контент', 'travel-контент'),
        (r'\bbmw\b', ''),
        (r'\bdrift\b', 'динамичный travel-монтаж'),
        (r'\bphonk\b', ''),
    ]
    for pattern, replacement in replacements:
        sanitized = re.sub(pattern, replacement, sanitized, flags=re.IGNORECASE)
    sanitized = re.sub(r'\s{2,}', ' ', sanitized).strip()
    return sanitized


def sanitize_travel_pack(pack: Dict[str, Any]) -> Dict[str, Any]:
    if str(pack.get('niche', '')).lower() != 'travel':
        return pack

    string_fields = [
        'bestTitle', 'description', 'coverText', 'pinnedComment',
        'hookText', 'firstLineHook', 'trendAngle', 'caption',
        'storyAnnouncement', 'cta', 'altText', 'thumbnailText',
    ]
    for field in string_fields:
        if isinstance(pack.get(field), str):
            pack[field] = _sanitize_text_value(pack[field])

    list_fields = ['titleOptions', 'hashtags', 'tags', 'improvementTips']
    for field in list_fields:
        values = pack.get(field)
        if isinstance(values, list):
            pack[field] = [
                _sanitize_text_value(item) if isinstance(item, str) else item
                for item in values
            ]

    return pack

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
    if str(pack.get('niche', '')).lower() == 'travel':
        for term in TRAVEL_FORBIDDEN_AUTO_TERMS:
            if term in blob:
                warnings = pack.setdefault('warnings', [])
                if 'Travel SEO copy was sanitized from auto terms.' not in warnings:
                    warnings.append('Travel SEO copy was sanitized from auto terms.')
                print(f'Warning: travel SEO copy still has term after sanitization: {term}')
                break


def build_youtube_video_package(meta: Dict[str, Any], angle: str, subject: str, tips: List[str]) -> Dict[str, Any]:
    if angle in {'travel_destination_short', 'travel_resort_reels', 'travel_horizontal_story'}:
        return {
            'bestTitle': f'{subject}: расширенный travel-влог для YouTube',
            'titleOptions': ['Турецкие Мальдивы: расширенный travel-влог', 'Маршрут, локации и советы по поездке', 'Как спланировать отдых в формате travel story'],
            'description': 'Этот материал лучше работает как Shorts/Reels/TikTok в коротком формате.\n\n'
                           'Классический YouTube Video имеет смысл делать в формате расширенного travel-влога: маршрут, логистика, бюджет, советы и личные впечатления.',
            'tags': [subject, 'travel vlog', 'турция', 'путешествие', 'куда поехать', 'курорт'],
            'thumbnailText': 'TRAVEL VLOG',
            'pinnedComment': 'Сделать расширенную версию с маршрутом и советами?',
            'improvementTips': tips + ['Для текущего короткого ролика приоритет — Shorts/Reels/TikTok.', 'Для YouTube Video добавьте полезный travel-контекст.']
        }
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
    if not is_auto_angle(angle):
        return {
            'bestTitle': f'{subject}: полноценная версия для YouTube',
            'titleOptions': [f'{subject}: полноценная версия для YouTube', f'{subject}: полный сюжет в YouTube Video', 'YouTube Video: структурная подача ролика', 'Полная версия ролика для YouTube', 'Развёрнутый формат для YouTube Video'],
            'description': f'Полная версия ролика про {subject} для YouTube Video.\n\n'
                           'В длинном формате проще раскрыть идею через структуру: вступление, основная часть, финальный вывод.\n\n'
                           'Добавьте в описание полезный контекст, чтобы зрителю было понятно, зачем смотреть до конца.\n\n'
                           'В конце добавьте CTA: подписка, комментарий и переход к следующему видео.',
            'tags': [subject, 'YouTube Video', 'full version', 'video content', 'видеомонтаж', 'контент', 'story format', 'brand video', 'long-form', 'SMM'],
            'thumbnailText': 'YOUTUBE STORY',
            'pinnedComment': 'Какой фрагмент раскрыть подробнее в следующем ролике?',
            'improvementTips': tips + ['Добавьте обложку 16:9 с понятным акцентом.', 'Сделайте описание структурным: суть, ценность, CTA.', 'Подготовьте отдельную вертикальную версию для Shorts.']
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
    if angle in {'travel_destination_short', 'travel_resort_reels'}:
        return {
            'bestTitle': 'Турецкие Мальдивы за 15 секунд' if 'турецкие мальдивы' in subject.lower() else f'{subject} за 15 секунд',
            'titleOptions': ['Турецкие Мальдивы за 15 секунд', 'Место в Турции, которое похоже на Мальдивы', 'Travel Shorts: идея для отпуска'],
            'description': 'Короткий travel-ролик про атмосферное место для отдыха. Идея для поездки, если хочется моря, пляжа и красивых кадров.',
            'hashtags': ['#Shorts', '#Travel', '#Турция', '#Мальдивы', '#Путешествия', '#Отдых'],
            'coverText': 'ТУРЕЦКИЕ МАЛЬДИВЫ',
            'pinnedComment': 'Хотели бы сюда попасть?',
            'hookText': 'Это Турция или Мальдивы?',
            'improvementTips': tips
        }
    if angle == 'horizontal_youtube_story':
        return {
            'bestTitle': 'Сильный момент из YouTube-ролика',
            'titleOptions': ['Сильный момент из YouTube-ролика', 'Горизонтальный ролик — короткая версия', 'YouTube cut для Shorts'],
            'description': 'Из горизонтального ролика лучше собрать отдельный вертикальный cut на 10–20 секунд.',
            'hashtags': ['#Shorts', '#YouTube', '#Видео', '#Монтаж', '#Контент'],
            'coverText': 'SHORT CUT',
            'pinnedComment': 'Какой момент вынести в Shorts?',
            'hookText': 'Самый сильный момент — в короткую версию',
            'improvementTips': tips + ['Первые 0.5 сек должны сразу цеплять.', 'Текст на экране лучше сделать крупнее.', 'Не перегружайте описание — 1–2 строки достаточно.']
        }
    if angle == 'square_low_quality_social_clip':
        return {
            'bestTitle': 'Короткая версия после адаптации',
            'titleOptions': ['Короткая версия после адаптации', 'Сначала re-export, потом публикация', 'Shorts после 9:16 cut'],
            'description': 'Квадратный исходник низкого качества. Сначала сделайте re-export в 9:16 Full HD, потом публикуйте.',
            'hashtags': ['#Shorts', '#Видео', '#Монтаж', '#Адаптация', '#Контент'],
            'coverText': 'RE-EXPORT 9:16',
            'pinnedComment': 'Собрать финальную версию после адаптации?',
            'hookText': 'Сначала адаптация, потом публикация',
            'improvementTips': tips + ['Сначала рефрейм 9:16.', 'Переэкспортируйте минимум в Full HD.', 'Проверьте читаемость текста на экране.']
        }
    if is_auto_angle(angle):
        return {
            'bestTitle': f'{subject} Drift Mode 🔥' if 'bmw' in subject.lower() else f'{subject} в режиме максимального вайба 🔥',
            'titleOptions': [f'{subject} Drift Mode 🔥', f'{subject} за 15 секунд', 'Drift. Smoke. Repeat.', 'Phonk + speed = wow', 'Cinematic punch cut'],
            'description': f'{subject} в коротком динамичном фрагменте. Хук с первых кадров и акцент на ритм.',
            'hashtags': ['#Shorts', '#BMW', '#BMWX3', '#Drift', '#Phonk', '#CarEdit'],
            'coverText': 'BMW X3\nDRIFT MODE' if 'x3' in subject.lower() else 'DRIFT\nMODE',
            'pinnedComment': 'Больше дыма или больше cinematic?',
            'hookText': f'{subject} в drift mode за 15 секунд',
            'improvementTips': tips + ['Первые 0.5 сек должны сразу цеплять.', 'Текст на экране лучше сделать крупнее.', 'Не перегружайте описание — 1–2 строки достаточно.']
        }
    return {
        'bestTitle': f'{subject}: короткая вертикальная версия',
        'titleOptions': [f'{subject}: короткая вертикальная версия', f'{subject} за 15 секунд', 'Короткий ролик для Shorts', 'Быстрый cut для ленты', 'Short-form версия'],
        'description': f'{subject} в коротком формате: быстрый вход, понятный акцент и динамичный темп.',
        'hashtags': ['#Shorts', '#Видео', '#Контент', '#Монтаж', '#ShortVideo'],
        'coverText': 'SHORT VERSION',
        'pinnedComment': 'Какой момент сделать главным в следующем коротком ролике?',
        'hookText': 'Сильный момент — с первых кадров',
        'improvementTips': tips + ['Первые 0.5 сек должны сразу цеплять.', 'Текст на экране лучше сделать крупнее.', 'Не перегружайте описание — 1–2 строки достаточно.']
    }


def build_instagram_reels_package(meta: Dict[str, Any], angle: str, subject: str, tips: List[str]) -> Dict[str, Any]:
    if angle in {'travel_destination_short', 'travel_resort_reels', 'travel_horizontal_story'}:
        return {
            'caption': 'Турецкие Мальдивы — звучит как миф, выглядит как идеальный план на отдых. Спокойная вода, свет и атмосфера места, куда хочется вернуться.',
            'firstLineHook': 'Турецкие Мальдивы — место, где хочется выключить телефон',
            'hashtags': ['#travel', '#турция', '#путешествия', '#отдых', '#reels'],
            'altText': 'Короткий travel-ролик о курортном месте в Турции с морем и пляжем.',
            'coverText': 'TRAVEL / RESORT',
            'pinnedComment': 'Какой момент этого места вам понравился больше всего?',
            'storyAnnouncement': 'Показываю место, которое легко принять за Мальдивы.',
            'cta': 'Сохрани идею для поездки.',
            'improvementTips': tips
        }
    if angle == 'horizontal_youtube_story':
        return {
            'caption': 'Горизонтальный исходник лучше превратить в вертикальный Reels: взять самый сильный момент и добавить крупный текст.',
            'firstLineHook': 'Из YouTube-ролика — в Reels',
            'hashtags': ['#reels', '#монтаж', '#контент', '#smm', '#videoedit'],
            'altText': 'Фрагмент горизонтального видео, адаптируемый под вертикальный Reels.',
            'coverText': 'REELS CUT',
            'pinnedComment': 'Какой момент оставить первым кадром?',
            'storyAnnouncement': 'Готовим короткую Reels-версию из большого ролика.',
            'cta': 'Сохрани как идею для адаптации горизонтального видео.',
            'improvementTips': tips + ['Сделайте обложку с крупным акцентом.', 'Первая строка caption должна быть хук-фразой.', 'Лучше использовать 5–7 hashtag, а не 20.']
        }
    if angle == 'square_low_quality_social_clip':
        return {
            'caption': 'Квадратный черновик с низким качеством. Перед публикацией лучше сделать re-export в 9:16 Full HD.',
            'firstLineHook': 'Сначала адаптация, потом Reels',
            'hashtags': ['#reels', '#монтаж', '#контент', '#videoedit', '#smm'],
            'altText': 'Квадратный ролик низкого качества, который нужно адаптировать под вертикальный Reels.',
            'coverText': 'RE-EXPORT 9:16',
            'pinnedComment': 'Делаем финальный Reels после переэкспорта?',
            'storyAnnouncement': 'Пересобираем видео в вертикальный формат для Reels.',
            'cta': 'Сохрани, чтобы не забыть этап адаптации.',
            'improvementTips': tips + ['Сначала рефрейм 9:16.', 'Переэкспортируйте в Full HD.', 'Проверьте читаемость обложки и текста.']
        }
    if is_auto_angle(angle):
        return {
            'caption': f'{subject}, немного дыма и cinematic-настроение. Какой кадр сильнее — первый или финальный?',
            'firstLineHook': f'{subject} в cinematic drift mood',
            'hashtags': ['#bmw', '#bmwx3', '#drift', '#автосъемка', '#reels', '#cargram'],
            'altText': f'Короткий авто-ролик с {subject}: динамичные проезды, дым и cinematic переходы.',
            'coverText': 'BMW X3 / CINEMATIC' if 'x3' in subject.lower() else 'CINEMATIC / DRIFT',
            'pinnedComment': 'Оставить больше дрифта или сделать чистый cinematic?',
            'storyAnnouncement': 'Новый авто-ролик уже в Reels. Залетайте оценить монтаж.',
            'cta': 'Сохрани, если нравится такой стиль авто-контента.',
            'improvementTips': tips + ['Сделайте обложку с крупной моделью авто.', 'Первая строка caption должна быть хук-фразой.', 'Лучше использовать 5–7 hashtag, а не 20.']
        }
    return {
        'caption': f'{subject}: короткий Reels-фрагмент с акцентом на темп и настроение. Какой кадр лучше оставить первым?',
        'firstLineHook': f'{subject}: динамичный Reels cut',
        'hashtags': ['#reels', '#контент', '#монтаж', '#videoedit', '#smm'],
        'altText': f'Короткий ролик для Reels про {subject} с динамичным монтажом.',
        'coverText': 'REELS FORMAT',
        'pinnedComment': 'Какой вариант монтажа оставить в финале?',
        'storyAnnouncement': 'Новый ролик в Reels — заходите оценить подачу.',
        'cta': 'Сохрани, если откликается такой стиль.',
        'improvementTips': tips + ['Сделайте обложку с крупным визуальным акцентом.', 'Первая строка caption должна быть хук-фразой.', 'Лучше использовать 5–7 hashtag, а не 20.']
    }


def build_tiktok_package(meta: Dict[str, Any], angle: str, subject: str, tips: List[str]) -> Dict[str, Any]:
    if angle in {'travel_destination_short', 'travel_resort_reels', 'travel_horizontal_story'}:
        return {
            'caption': 'Турецкие Мальдивы — звучит как миф, выглядит как план.',
            'hookText': 'Это Турция или Мальдивы?',
            'hashtags': ['#travel', '#турция', '#отдых', '#кудапоехать'],
            'coverText': 'TURKEY OR MALDIVES?',
            'pinnedComment': 'Добавить список похожих мест в следующем видео?',
            'cta': 'Сохрани, чтобы не потерять место.',
            'trendAngle': 'travel destination reveal',
            'improvementTips': tips
        }
    if angle == 'horizontal_youtube_story':
        return {
            'caption': 'Из длинного ролика — короткий TikTok. Что оставить первым кадром?',
            'hookText': 'Самый сильный момент — в первые 1 сек',
            'hashtags': ['#tiktok', '#монтаж', '#videoedit', '#контент'],
            'coverText': 'FAST CUT',
            'pinnedComment': 'Оставить этот момент или выбрать другой?',
            'cta': 'Пиши, какой фрагмент сильнее.',
            'trendAngle': 'fast cut from long-form video',
            'improvementTips': tips + ['Резкий хук должен быть до 1 секунды.', 'Меньше текста, больше ритма.', 'Используйте звук и бит как основу монтажа.']
        }
    if angle == 'square_low_quality_social_clip':
        return {
            'caption': 'Квадратный черновик — сначала re-export в 9:16 Full HD, потом публикация в TikTok.',
            'hookText': 'Сначала адаптация формата',
            'hashtags': ['#tiktok', '#videoedit', '#контент', '#монтаж'],
            'coverText': 'RE-EXPORT',
            'pinnedComment': 'Публиковать после адаптации?',
            'cta': 'Пиши, делать ли финальный 9:16 cut.',
            'trendAngle': 're-export and vertical reframing workflow',
            'improvementTips': tips + ['Резкий хук должен быть до 1 секунды.', 'Меньше текста, больше ритма.', 'Используйте звук и бит как основу монтажа.']
        }
    if is_auto_angle(angle):
        return {
            'caption': f'{subject} + drift mood. Залетит?',
            'hookText': f'{subject} ушёл в drift mode',
            'hashtags': ['#bmw', '#drift', '#phonk', '#caredit', '#cartok'],
            'coverText': 'DRIFT MODE',
            'pinnedComment': 'Part 2 ночью?',
            'cta': 'Пиши, какой авто сделать следующим.',
            'trendAngle': 'phonk drift edit / cinematic car transition',
            'improvementTips': tips + ['Резкий хук должен быть до 1 секунды.', 'Меньше текста, больше ритма.', 'Используйте звук и бит как основу монтажа.']
        }
    return {
        'caption': f'{subject}: короткий TikTok-фрагмент. Оставляем этот ритм?',
        'hookText': 'Сильный кадр — с первой секунды',
        'hashtags': ['#tiktok', '#videoedit', '#content', '#монтаж'],
        'coverText': 'QUICK CUT',
        'pinnedComment': 'Оставить этот вариант или сделать быстрее?',
        'cta': 'Пиши, какой формат зайдёт лучше.',
        'trendAngle': 'quick short-form cut',
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
    pack['niche'] = meta.get('niche', 'general_video')
    sanitize_travel_pack(pack)
    _assert_readable(pack)
    pack['videoAngle'] = angle
    pack['generationBasis'] = generation_basis
    return pack
