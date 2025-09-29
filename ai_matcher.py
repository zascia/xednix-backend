import re
from nltk.corpus import stopwords
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Настройка стоп-слов для очистки текста (используем английский, так как вакансии часто на нем)
STOPWORDS = set(stopwords.words('english'))

def preprocess_text(text):
    """Очистка текста: нижний регистр, удаление пунктуации и стоп-слов."""
    if not text:
        return ""
    # Удаление небуквенных символов и приведение к нижнему регистру
    text = re.sub(r'[^a-zA-Z\s]', '', text.lower())
    words = text.split()
    # Удаление стоп-слов
    return ' '.join([word for word in words if word not in STOPWORDS])

def calculate_relevance(user_skills_text, job_description_text):
    """
    Вычисляет косинусное сходство между навыками пользователя и текстом вакансии.
    """
    if not job_description_text:
        return 0.0

    # 1. Объединение документов для векторизации
    documents = [user_skills_text, job_description_text]

    # 2. Векторизация (TF-IDF)
    # TF-IDF присваивает больший вес редким, но важным словам.
    vectorizer = TfidfVectorizer().fit_transform(documents)

    # 3. Косинусное сходство
    # Измеряет угол между векторами; 1.0 = полное совпадение, 0.0 = отсутствие сходства.
    cosine_scores = cosine_similarity(vectorizer[0], vectorizer[1])

    # Возвращаем процент (первый элемент массива, округленный до 2 знаков)
    return round(cosine_scores[0][0] * 100, 2)

def ai_match_jobs(raw_jobs, full_user_skills, excluded_skills):
    """
    Основная функция матчинга: добавляет 'relevance_score' к каждой вакансии.
    """

    # 1. Подготовка профиля пользователя
    # Преобразуем полный список навыков в строку для векторизации
    user_skills_text = preprocess_text(" ".join(full_user_skills))

    final_results = []

    for job in raw_jobs:
        # 2. Подготовка текста вакансии
        job_text = job.get('title', '') + ' ' + job.get('description', '')
        preprocessed_job_text = preprocess_text(job_text)

        # 3. Расчет релевантности
        score = calculate_relevance(user_skills_text, preprocessed_job_text)

        # 4. Фильтрация по исключениям (уменьшение счета, если найдены исключаемые слова)
        penalty = 0
        for excluded_skill in excluded_skills:
            if excluded_skill.lower() in preprocessed_job_text:
                penalty += 10 # Штраф в 10% за каждое найденное исключение

        final_score = max(0, score - penalty) # Гарантируем, что счет не отрицательный

        # 5. Добавление результата
        job['relevance_score'] = final_score

        # Финальный фильтр: не показываем вакансии с очень низким баллом
        if final_score >= 1:
            final_results.append(job)

    # 6. Сортировка по убыванию релевантности
    final_results.sort(key=lambda x: x['relevance_score'], reverse=True)

    return final_results