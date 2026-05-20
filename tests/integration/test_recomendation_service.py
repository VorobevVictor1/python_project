def test_service_generate_and_cache(db_session):
    """Полный цикл: события → расчёт → кэш → чтение."""
    from app.recommender.service import RecommendationService
    
    # Подготовка: добавляем тестовые события в БД
    # ... (используем фикстуры из conftest.py)
    
    service = RecommendationService(db=db_session)
    
    # Генерация
    result = service.generate_for_user(user_id=1)
    assert result.user_id == 1
    
    # Сохранение
    cached = service.save_to_cache(result)
    assert cached.user_id == 1
    
    # Чтение
    loaded = service.get_from_cache(user_id=1)
    assert loaded is not None
    assert len(loaded.recommendations) == len(result.recommendations)