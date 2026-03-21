# Frontend Integration Guide

## Зачем Этот Документ

Этот документ не про продуктовые хотелки и не про backlog. Он про то, как фронтенд должен подключаться к backend API так, чтобы все работало стабильно, предсказуемо и без самопального говна. Здесь описан правильный способ жить с auth, tenant context, template flows, assisted templateization, generation jobs, polling и artifact download.

Если нужен точный reference по payload shape, смотри [api-contract.md](api-contract.md). Этот документ отвечает на другой вопрос: как этим контрактом пользоваться в реальном приложении.

## Базовые Принципы Интеграции

Backend живет под префиксом `/api/v1`. Внутренние browser routes работают только с `Authorization: Bearer <access_token>`. Почти все рабочие экраны tenant-scoped, поэтому фронт обязан явно пробрасывать `organization_id` в query или body, в зависимости от конкретного endpoint.

Фронт не должен угадывать backend state. Он должен следовать контракту. Если route асинхронный, не надо пытаться получить готовый файл сразу. Если backend возвращает presigned URL, не надо строить storage URL руками. Если в ответе есть `render_strategy`, не надо его игнорировать и запускать “любимую” ветку генерации.

## Правильная Архитектура Клиента

Нужен один централизованный `apiClient`, который умеет:

- подставлять `Authorization` header
- отправлять `Content-Type` корректно для JSON и `multipart/form-data`
- один раз делать refresh при `401`
- повторять исходный запрос после успешного refresh
- завершать сессию, если refresh тоже умер
- нормализовать error shape backend в единый клиентский формат

Нужен один session store или context, который хранит:

- `accessToken`
- `refreshToken`
- `user`
- `activeOrganizationId`

Нужен один query layer, где все requests идут через `TanStack Query`. Серверный state не должен разъезжаться по приложению в ручных `fetch` или `axios` вызовах по месту.

## Authentication Flow

Логин делается через `POST /api/v1/auth/login`.

Запрос:

```json
{
  "email": "admin@example.com",
  "password": "Passw0rd!"
}
```

Ответ содержит:

- `access_token`
- `refresh_token`
- `token_type`
- `access_token_expires_in`
- `refresh_token_expires_in`
- `user`

После логина фронт обязан:

1. сохранить токены
2. сохранить `user`
3. выбрать активную организацию из `user.memberships`
4. открыть защищенную часть приложения

Если у пользователя есть membership с `is_default=true`, берется она. Если нет, берется первая активная membership.

Для восстановления сессии после reload фронт должен либо держать user в storage, либо запрашивать `GET /api/v1/auth/me` после инициализации, если access token еще валиден.

Refresh делается через `POST /api/v1/auth/refresh`.

Запрос:

```json
{
  "refresh_token": "opaque-token"
}
```

Logout делается через `POST /api/v1/auth/logout` с bearer token и `refresh_token` в body. После logout фронт обязан чистить локальную сессию полностью.

## Organization Context

Почти все внутренние экраны работают в контексте активной организации. Это значит, что `organization_id` должен браться не из локальной формы, не из route param и не из старого кэша, а из единого organization context.

При смене организации фронт обязан:

1. обновить `activeOrganizationId`
2. инвалидировать tenant-scoped queries
3. перезагрузить текущий экран в новом tenant context

Если этого не сделать, кэш от одной организации легко поедет в другую. Это типовой тупой баг, и он полностью на фронте.

## Общая Стратегия Запросов

Есть три типа запросов.

Первый тип это обычные query на получение данных: шаблоны, карточка шаблона, job status, diagnostics, API keys.

Второй тип это mutation на изменение состояния: upload template, register template, templateize import, generate document, rotate key, revoke key.

Третий тип это long-running async flows, где mutation создает job, а потом отдельный query его поллит.

Правильный паттерн такой:

1. mutation запускает действие
2. mutation response дает идентификатор или новую сущность
3. фронт либо инвалидирует нужные queries, либо переходит на detail screen
4. если это async job, фронт включает polling по `task_id`

Не надо смешивать эти модели. Не надо после `generate` пытаться ждать файл в том же запросе. Backend так не работает.

## Template Flows

### Список И Карточка Шаблона

Список шаблонов:

`GET /api/v1/templates?organization_id=<uuid>`

Карточка шаблона:

`GET /api/v1/templates/{template_id}?organization_id=<uuid>`

Карточка шаблона это основной источник истины по текущей версии. Там фронт смотрит:

- `current_version_details.render_strategy`
- `current_version_details.imported_binding_count`
- `current_version_details.schema`
- `current_version_details.version`
- `current_version_details.original_filename`

Именно по `render_strategy` решается, какой generation flow использовать.

### Upload Нового DOCX

Upload делается через `POST /api/v1/templates/upload` как `multipart/form-data`.

Поля формы:

- `organization_id`
- `name`
- `code`
- `version`
- `description` optional
- `notes` optional
- `publish` optional
- `file`

Пример на `fetch`:

```ts
const formData = new FormData();
formData.append("organization_id", organizationId);
formData.append("name", values.name);
formData.append("code", values.code);
formData.append("version", values.version);
formData.append("description", values.description ?? "");
formData.append("publish", String(values.publish));
formData.append("file", file);

await apiClient.post("/templates/upload", formData);
```

Для `FormData` фронт не должен руками проставлять `Content-Type: multipart/form-data`. Браузер сам подставит boundary. Если поставить руками, можно легко сломать upload.

После успешного upload фронт получает:

- `template`
- `version`

Дальше фронт решает, куда вести пользователя:

- либо на карточку шаблона
- либо сразу на templateization screen, если это обычный DOCX import flow

### Register Уже Существующего DOCX

Register делается через `POST /api/v1/templates/register` c JSON body. Это отдельный flow, если файл уже лежит в storage.

## Schema Extraction Flow

Если пользователь работает с placeholder-based DOCX, frontend может сначала извлечь schema без сохранения:

`POST /api/v1/templates/extract-schema`

Это тоже `multipart/form-data`, где отправляется только `file`.

Если шаблон уже сохранен и нужно повторно вытащить schema из текущей версии:

`POST /api/v1/templates/{template_id}/extract-schema?organization_id=<uuid>`

Этот flow нужен для обычных placeholder template сценариев. Он не заменяет assisted templateization.

## Assisted Templateization Flow

Это основной flow для обычных документов.

Правильная последовательность такая:

1. пользователь загружает `.docx` через `/templates/upload`
2. фронт открывает templateization screen
3. фронт делает `POST /api/v1/templates/{template_id}/import/inspect`
4. фронт параллельно может сделать `POST /api/v1/templates/{template_id}/import/analyze`
5. пользователь вручную выбирает spans текста
6. фронт сохраняет selections через `POST /api/v1/templates/{template_id}/import/templateize`
7. backend переводит текущую версию в `render_strategy = "docx_import"`
8. после этого шаблон готов к imported generation

### Inspect

Inspect request:

`POST /api/v1/templates/{template_id}/import/inspect`

Body:

```json
{
  "organization_id": "uuid"
}
```

Ответ:

- `inspection_checksum`
- `paragraph_count`
- `paragraphs[]`

Каждый paragraph содержит:

- `path`
- `source_type`
- `text`
- `char_count`
- `table_header_label`

Frontend обязан использовать именно эти `path` как адресацию документа. Не нужно придумывать свои paragraph ids.

### Analyze

Analyze request:

`POST /api/v1/templates/{template_id}/import/analyze`

Body:

```json
{
  "organization_id": "uuid"
}
```

Analyze возвращает suggestions. Это подсказки, а не источник истины. Пользователь может принять suggestion, изменить его или проигнорировать. UI не должен зависеть от того, нашел analyzer что-то или нет.

### Как Формировать Selections

Каждая сохраненная выборка должна отправляться в таком виде:

```json
{
  "paragraph_path": "body/p/13",
  "fragment_start": 6,
  "fragment_end": 61,
  "binding_key": "report_topic",
  "label": "Report Topic",
  "component_type": "text",
  "value_type": "string",
  "required": true,
  "sample_value": "Optional"
}
```

Критично важные правила:

- `paragraph_path` должен совпадать с тем, что пришло в `inspect`
- `fragment_start` и `fragment_end` считаются по полному тексту абзаца
- `fragment_end` всегда больше `fragment_start`
- `binding_key` должен проходить regex backend `^[A-Za-z][A-Za-z0-9_.-]{0,119}$`

Frontend не должен пытаться сохранять spans через несколько абзацев в одном selection. Backend работает на уровне одного paragraph span.

### Сохранение Templateization

Request:

`POST /api/v1/templates/{template_id}/import/templateize`

Body:

```json
{
  "organization_id": "uuid",
  "inspection_checksum": "sha256-hex",
  "selections": [
    {
      "paragraph_path": "body/p/13",
      "fragment_start": 6,
      "fragment_end": 61,
      "binding_key": "report_topic",
      "label": "Report Topic"
    }
  ]
}
```

Почему нужен `inspection_checksum`. Он защищает от ситуации, когда фронт пытается сохранить spans поверх другой версии inspection data. Фронт обязан использовать именно тот checksum, который пришел в последнем валидном inspect response.

После успешного templateize frontend должен:

1. обновить detail шаблона
2. обновить schema
3. показать пользователю сохраненные bindings
4. перевести generation UI в режим imported template

## Generation Flow

Есть два разных варианта генерации.

### Constructor Flow

Используется, если `render_strategy = "constructor"`.

Запрос:

`POST /api/v1/documents/generate`

Body:

```json
{
  "organization_id": "uuid",
  "template_id": "uuid",
  "template_version_id": "uuid",
  "data": {
    "student_name": "Anek"
  },
  "constructor": {
    "locale": "ru-RU",
    "metadata": {
      "document_type": "certificate"
    },
    "blocks": [
      {
        "type": "text",
        "id": "text-1",
        "binding": {
          "key": "student_name"
        }
      }
    ]
  }
}
```

Фронт не должен хардкодить constructor defaults из воздуха. Для инициализации используется:

`GET /api/v1/documents/constructor-schema`

### Imported DOCX Flow

Используется, если `render_strategy = "docx_import"`.

Запрос:

`POST /api/v1/documents/generate-imported`

Body:

```json
{
  "organization_id": "uuid",
  "template_id": "uuid",
  "template_version_id": "uuid",
  "data": {
    "report_topic": "Влияние цифровых сервисов на учет расходов",
    "student_identity": "Сериков Нұржан студент группы ИС-404"
  }
}
```

В этом flow `constructor` не нужен. Не надо отправлять туда пустые блоки или придумывать заглушки. Backend сам знает, что делать с imported template.

## Async Jobs И Polling

Обе generation ветки асинхронные. На submit backend возвращает job envelope:

```json
{
  "task_id": "uuid",
  "organization_id": "uuid",
  "status": "queued",
  "template_id": "uuid",
  "template_version_id": "uuid",
  "requested_by_user_id": "uuid",
  "from_cache": false
}
```

После этого фронт должен начать polling:

`GET /api/v1/documents/jobs/{task_id}?organization_id=<uuid>`

Статусы бывают:

- `queued`
- `processing`
- `completed`
- `failed`

Polling должен останавливаться только на terminal status: `completed` или `failed`.

Правильная логика в `TanStack Query` такая:

- пока статус `queued` или `processing`, включен `refetchInterval`
- при `completed` polling отключается
- при `failed` polling отключается

Если job completed, в response будут `artifacts[]`.

## Download И Preview

Чтобы получить лучший артефакт для скачивания:

`GET /api/v1/documents/jobs/{task_id}/download?organization_id=<uuid>`

Чтобы получить лучший preview artifact:

`GET /api/v1/documents/jobs/{task_id}/preview?organization_id=<uuid>`

Ответ содержит `artifact.download_url`. Это уже готовый presigned URL. Фронт не должен сам собирать URL до MinIO и не должен проксировать файл через свой код без необходимости.

Правильный паттерн:

1. фронт получает metadata route
2. берет `download_url`
3. либо делает `window.open(download_url)`, либо отдает ссылку пользователю

## Verification Flow

Верификация документа идет через:

`POST /api/v1/documents/verify`

Форма может отправлять:

- `organization_id` + `file`
- либо `organization_id` + `authenticity_hash`

Если проверяется файл, это `multipart/form-data`.

Если найден match, frontend показывает:

- matched или нет
- `artifact_id`
- `task_id`
- `kind`
- `file_name`
- `issued_at`
- `verification_code`
- `authenticity_hash`

## API Keys Flow

Это internal admin flow.

Создание:

`POST /api/v1/admin/api-keys`

Листинг:

`GET /api/v1/admin/api-keys?organization_id=<uuid>`

Ротация:

`POST /api/v1/admin/api-keys/{api_key_id}/rotate?organization_id=<uuid>`

Отзыв:

`POST /api/v1/admin/api-keys/{api_key_id}/revoke?organization_id=<uuid>`

Plaintext key приходит только в create/rotate responses. Фронт обязан прямо сказать пользователю, что ключ нужно сохранить сейчас, потому что потом backend его уже не вернет.

## Diagnostics Flow

Для operational screens используются:

- `GET /api/v1/admin/diagnostics/failed-jobs?organization_id=<uuid>&limit=25`
- `GET /api/v1/admin/diagnostics/audit-events?organization_id=<uuid>&limit=25`
- `GET /api/v1/admin/diagnostics/cache-stats?organization_id=<uuid>`
- `GET /api/v1/admin/diagnostics/worker-status?organization_id=<uuid>`

Это обычные query. Никакой сложной логики там не нужно. Главное не забывать `organization_id`.

## Обработка Ошибок

Domain errors backend отдает в виде:

```json
{
  "detail": "Readable error message"
}
```

Frontend должен различать:

- `401` сессия умерла
- `403` недостаточно прав
- `404` сущность не найдена
- `409` бизнес-конфликт или лимит
- `422` validation error
- `500` backend error

`422` ошибки не должны тонуть в общем toast. Их нужно маппить обратно в форму. Особенно на upload, login и templateization save.

## Что Фронту Делать Не Надо

Не надо строить storage URLs руками.

Не надо пытаться рендерить DOCX как Word page preview в браузере.

Не надо выбирать generation endpoint по собственным эвристикам. Для этого есть `render_strategy`.

Не надо хардкодить paragraph ids для templateization. Для этого есть `inspect.path`.

Не надо слать multipart руками с самодельным `Content-Type`.

Не надо пытаться дождаться готового документа в response на `generate`.

Не надо хранить tenant-specific данные без `organization_id` в query key.

## Рекомендуемый Happy Path Для Реального UI

Нормальный браузерный happy path должен выглядеть так:

1. логин через `/auth/login`
2. выбор активной организации
3. открытие списка шаблонов
4. upload обычного `.docx`
5. переход на templateization screen
6. `import/inspect` и опционально `import/analyze`
7. пользователь создает selections
8. сохранение через `import/templateize`
9. переход на generation screen
10. submit через `generate-imported`
11. polling по `jobs/{task_id}`
12. скачивание через `jobs/{task_id}/download`

Если это placeholder template, то середина с `templateize` заменяется на extraction/schema + constructor generation.

## Последнее Нормальное Правило

Backend уже оттестирован и ведет себя как сервис, а не как песочница. Значит фронтенд должен интегрироваться с ним так же дисциплинированно. Один auth flow, один organization context, один query layer, один способ polling, один способ download, ноль магии.

Все, что нарушает эти правила, потом превращается в дорогой и унылый рефакторинг.

## Billing Integration

Billing is now a first-class backend surface. Frontend should treat it like any other tenant-scoped admin module, not as a hardcoded pricing page.

Use these routes:

- `GET /api/v1/admin/billing/plans?organization_id=<uuid>`
- `GET /api/v1/admin/billing/snapshot?organization_id=<uuid>`
- `GET /api/v1/admin/billing/invoices?organization_id=<uuid>&limit=25`
- `POST /api/v1/admin/billing/subscription/change`
- `POST /api/v1/admin/billing/cycle/run`

The important rule is simple. The active plan is in `snapshot.subscription.plan`. If a user scheduled an upgrade or downgrade, the next plan is in `snapshot.subscription.pending_plan`. Frontend must show both states clearly and must not pretend the active plan changed immediately when only a pending change exists.

Invoice history is read-only in the current backend. We generate and store finalized monthly invoices automatically. We do not yet expose payment checkout, payment method capture, or webhook-driven payment reconciliation. So the frontend should present invoice history and subscription state, not fake a card-payment UX that the backend does not support.
