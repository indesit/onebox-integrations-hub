# PROJECT_BRIEF: OneBox Integrations Hub

## 1. Обзор (Overview)
Создание единой масштабируемой платформы (Hub) для интеграции CRM OneBox с внешними сервисами (Telegram, SendPulse, Google Sheets и др.). Проект должен стандартизировать способы обмена данными и упростить добавление новых интеграций.

## 2. Бизнес-цели (Business Goals)
- Снизить стоимость и время разработки новых интеграций для OneBox.
- Обеспечить отказоустойчивость (retries, error handling).
- Создать единую точку мониторинга и логирования всех обменов.

## 3. Основной функционал (Core Features)
- **OneBox Core Adapter:** Базовая логика взаимодействия с OneBox API/Webhooks.
- **Service Adapters:** Специфичные модули для Telegram, SendPulse, Google Sheets.
- **Integration Layer:** Маппинг сущностей, очереди обработки, механизмы повторов.

## 4. Пользователи / Роли (User Roles)
- **Система (Admin/Dev):** Настройка маппинга и мониторинг.
- **CRM OneBox:** Инициатор или получатель данных.

## 5. Ограничения (Constraints)
- Стек: Python (предпочтительно для работы с OpenClaw/ACP).
- Инфраструктура: Docker-контейнеризация.
- OneBox API v2.

## 6. Требования к качеству (Quality Attributes)
- **Модульность:** Добавление нового сервиса без изменения Core.
- **Надежность:** Обработка таймаутов API и ошибок авторизации.
- **Прозрачность:** Подробное логирование запросов/ответов.

## 7. Риски и допущения (Risks & Assumptions)
- Риск: Изменения в API внешних сервисов (SendPulse/Google).
- Допущение: OneBox имеет доступ к Hub через Webhooks или Hub опрашивает OneBox (Polling).

---
*Created: 2026-03-09*
*Source of Truth: projects/onebox-integrations-hub/docs/00-brief/PROJECT_BRIEF.md*
