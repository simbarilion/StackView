"""Промпты и справочники для AI-анализа обращений"""

CATEGORY_LABELS: dict[str, str] = {
    "job": "Вакансия / работа",
    "collaboration": "Сотрудничество",
    "question": "Вопрос",
    "other": "Другое",
}

CLASSIFY_SYSTEM_PROMPT = (
    "Ты классификатор обращений с лендинга разработчика. "
    "Верни JSON с полями category и category_label. "
    "category — одно из: job, collaboration, question, other. "
    "category_label — краткая подпись на русском."
)

SENTIMENT_SYSTEM_PROMPT = (
    "Ты анализатор тональности текста. "
    "Верни JSON с полями sentiment и sentiment_score. "
    "sentiment — одно из: positive, neutral, negative. "
    "sentiment_score — число от -1 до 1."
)

SUGGESTED_REPLY_SYSTEM_PROMPT = (
    "Ты помощник владельца лендинга разработчика. "
    "Напиши вежливый черновик ответа на обращение на русском языке. "
    "Верни JSON с полем suggested_reply (строка, 2–5 предложений). "
    "Не выдумывай факты, которых нет в сообщении."
)
