
import numpy as np

from app.recommender.types import ReadingEventDTO, Recommendation, UserRecommendations


class RecommenderEngine:
    """
    Алгоритм коллаборативной фильтрации на основе косинусного сходства.

    Использует numpy для эффективных векторных операций.

    Принцип работы:
    1. Строим матрицу "пользователь × книга" с оценками
    2. Для целевого пользователя находим похожих (косинусное сходство)
    3. Для непрочитанных книг считаем взвешенную оценку от похожих пользователей
    4. Возвращаем топ-N книг по скорингу
    """

    def __init__(self, top_n: int = 10, min_similarity: float = 0.1, min_ratings: int = 3):
        self.top_n = top_n
        self.min_similarity = min_similarity
        self.min_ratings = min_ratings

    def _build_mappings(
        self, events: list[ReadingEventDTO]
    ) -> tuple[dict[int, int], dict[int, int], dict[int, int], dict[int, int]]:
        """
        Строим маппинги user_id/book_id → индекс в матрице и обратно.

        :return: (user_to_idx, idx_to_user, book_to_idx, idx_to_book)
        """
        users = sorted(set(e.user_id for e in events))
        books = sorted(set(e.book_id for e in events))

        user_to_idx = {u: i for i, u in enumerate(users)}
        idx_to_user = {i: u for u, i in user_to_idx.items()}
        book_to_idx = {b: i for i, b in enumerate(books)}
        idx_to_book = {i: b for b, i in book_to_idx.items()}

        return user_to_idx, idx_to_user, book_to_idx, idx_to_book

    def _build_rating_matrix(
        self,
        events: list[ReadingEventDTO],
        user_to_idx: dict[int, int],
        book_to_idx: dict[int, int],
    ) -> np.ndarray:
        """
        Строим матрицу оценок: [n_users, n_books].

        NaN означает "нет оценки", а не 0 — это важно для корректного расчёта сходства.
        """
        n_users = len(user_to_idx)
        n_books = len(book_to_idx)
        matrix = np.full((n_users, n_books), np.nan)

        # Если пользователь оценил книгу несколько раз — берём последнюю оценку
        # Сортируем события по времени
        for event in sorted(events, key=lambda e: e.completed_at):
            u_idx = user_to_idx[event.user_id]
            b_idx = book_to_idx[event.book_id]
            matrix[u_idx, b_idx] = event.rating

        return matrix

    def _cosine_similarity_matrix(self, rating_matrix: np.ndarray) -> np.ndarray:
        """
        Вычисляем попарное косинусное сходство между всеми пользователями.

        :param rating_matrix: [n_users, n_books] с NaN для пропущенных оценок
        :return: [n_users, n_users] матрица сходств
        """
        n_users = rating_matrix.shape[0]
        similarities = np.zeros((n_users, n_users))

        # Заполняем матрицу попарно (можно оптимизировать через broadcasting)
        for i in range(n_users):
            for j in range(i + 1, n_users):
                # Берём только общие книги (где оба поставили оценку)
                mask = ~np.isnan(rating_matrix[i]) & ~np.isnan(rating_matrix[j])
                if np.sum(mask) == 0:
                    continue

                vec_i = rating_matrix[i, mask]
                vec_j = rating_matrix[j, mask]

                # Косинусное сходство
                norm_i = np.linalg.norm(vec_i)
                norm_j = np.linalg.norm(vec_j)
                if norm_i == 0 or norm_j == 0:
                    continue

                sim = np.dot(vec_i, vec_j) / (norm_i * norm_j)
                similarities[i, j] = sim
                similarities[j, i] = sim  # симметрия

        # Диагональ = 1 (пользователь идентичен себе), но мы её не используем
        np.fill_diagonal(similarities, 1.0)

        return similarities

    def _predict_scores(
        self,
        user_idx: int,
        rating_matrix: np.ndarray,
        similarities: np.ndarray,
        user_read_mask: np.ndarray,
    ) -> np.ndarray:
        """
        Предсказываем скоры для всех книг целевому пользователю.

        :param user_idx: индекс пользователя в матрице
        :param rating_matrix: [n_users, n_books]
        :param similarities: [n_users, n_users]
        :param user_read_mask: [n_books] булев массив — какие книги уже прочитаны
        :return: [n_books] массив скоров (0 для прочитанных/неподходящих)
        """
        n_books = rating_matrix.shape[1]
        scores = np.zeros(n_books)

        # Берём только пользователей с достаточным сходством
        similar_users = np.where(
            (similarities[user_idx] >= self.min_similarity)
            & (np.arange(len(similarities)) != user_idx)
        )[0]

        if len(similar_users) == 0:
            return scores

        # Для каждой книги считаем взвешенное среднее от похожих пользователей
        for book_idx in range(n_books):
            if user_read_mask[book_idx]:
                continue  # уже прочитано — не рекомендуем

            # Оценки похожих пользователей для этой книги
            ratings = rating_matrix[similar_users, book_idx]
            valid_mask = ~np.isnan(ratings)

            if not np.any(valid_mask):
                continue

            weights = similarities[user_idx, similar_users][valid_mask]
            valid_ratings = ratings[valid_mask]

            # Взвешенное среднее
            total_weight = np.sum(weights)
            if total_weight > 0:
                scores[book_idx] = np.sum(weights * valid_ratings) / total_weight

        return scores

    def predict_for_user(
        self,
        user_id: int,
        events: list[ReadingEventDTO],
        all_book_ids: set[int],
    ) -> UserRecommendations:
        """
        Основная точка входа: предсказать рекомендации для пользователя.
        """
        if not events:
            return UserRecommendations(user_id=user_id)

        # 1. Строим маппинги и матрицу
        user_to_idx, idx_to_user, book_to_idx, idx_to_book = self._build_mappings(events)

        # Проверяем, есть ли пользователь в данных
        if user_id not in user_to_idx:
            return UserRecommendations(user_id=user_id)

        rating_matrix = self._build_rating_matrix(events, user_to_idx, book_to_idx)
        user_idx = user_to_idx[user_id]

        # 2. Проверяем, достаточно ли оценок у пользователя
        user_ratings = rating_matrix[user_idx]
        n_user_ratings = np.sum(~np.isnan(user_ratings))
        if n_user_ratings < self.min_ratings:
            return UserRecommendations(user_id=user_id)

        # 3. Вычисляем попарные сходства
        similarities = self._cosine_similarity_matrix(rating_matrix)

        # 4. Определяем, какие книги пользователь уже прочитал
        user_read_mask = ~np.isnan(user_ratings)

        # 5. Предсказываем скоры
        predicted_scores = self._predict_scores(
            user_idx, rating_matrix, similarities, user_read_mask
        )

        # 6. Фильтруем: только книги из all_book_ids и с положительным скором
        valid_book_mask = np.array(
            [idx_to_book[i] in all_book_ids for i in range(len(idx_to_book))]
        )
        final_mask = (predicted_scores > 0) & valid_book_mask & (~user_read_mask)

        # 7. Сортируем и берём топ-N
        candidate_indices = np.where(final_mask)[0]
        candidate_scores = predicted_scores[candidate_indices]

        if len(candidate_scores) == 0:
            return UserRecommendations(user_id=user_id)

        # Сортируем по убыванию скора
        top_local_indices = np.argsort(candidate_scores)[::-1][: self.top_n]
        top_indices = candidate_indices[top_local_indices]

        # Формируем результат
        recommendations = [
            Recommendation(book_id=idx_to_book[idx], score=round(float(predicted_scores[idx]), 3))
            for idx in top_indices
        ]

        return UserRecommendations(
            user_id=user_id, recommendations=recommendations, algorithm_version="cosine_numpy_v1"
        )
