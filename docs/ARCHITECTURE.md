# Архитектура рекомендательного сервиса

## Цель
Сервис рекомендует книги на основе оценок пользователей. Пересчёт рекомендаций происходит асинхронно в батч-режиме, не блокируя основной API.

## Компоненты

```mermaid
graph LR
    A[FastAPI App] -->|POST /reviews| B[(PostgreSQL/SQLite)]
    A -->|enqueue| C[Redis Queue]
    D[Batch Worker] -->|dequeue| C
    D -->|read/write| B
    D -->|write| E[RecommendationCache]
    A -->|GET /recommendations| E