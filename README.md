# Лабораторная работа №14. Разработка конвейеров обработки данных на Python и Go
**Студент:** *Платов Артем Русланович*\
**Группа:** *220032-11*\
**Вариант:** *16*\
**Сложность:** *Средняя*
---

# Конвейер обработки данных мониторинга оборудования

**Вариант 16:** Мониторинг производственного оборудования (Modbus/OPC эмуляция)

## Архитектура конвейера

```
┌──────────────────┐     JSON Lines      ┌───────────────────┐
│  Go-сборщик      │ ──────────────────→ │  Python (Polars)  │
│  (горутины,      │    equipment_data   │  Очистка          │
│   буфер. канал,  │    .jsonl           │  Агрегация        │
│   пакетная зап.) │                     └────────┬──────────┘
└──────────────────┘                              │
                                                  │ write_parquet()
                                                  ▼
                                         ┌───────────────────┐
                                         │  equipment_data   │
                                         │  .parquet         │
                                         └────────┬──────────┘
                                                  │
                    ┌─────────────────────────────┼──────────────┐
                    │                             │              │
                    ▼                             ▼              ▼
           ┌──────────────┐           ┌──────────────┐  ┌──────────────┐
           │  DuckDB SQL  │           │  Polars API  │  │  Matplotlib  │
           │  анализ      │           │  анализ      │  │  Визаул.     │
           └──────────────┘           └──────────────┘  └──────────────┘
```

## Состав проекта

```
lab6/
├── go-collector/
│   ├── main.go            # Сборщик на Go
│   ├── main_test.go       # Go-тесты (8 тестов)
│   └── go.mod             # Go module
├── python-analysis/
│   ├── 01_import_data.py       # Загрузка JSON → Polars
│   ├── 02_clean_data.py        # Очистка и валидация
│   ├── 03_aggregation.py       # Аггрегационный анализ
│   ├── 04_save_parquet.py      # Сохранение в Parquet
│   ├── 05_duckdb_analysis.py   # DuckDB + сравнение
│   ├── 06_visualization.py     # Графики
│   └── tests/
│       ├── conftest.py         # Фикстуры (sample JSONL + DataFrame)
│       ├── test_import.py      # Тесты загрузки (5)
│       ├── test_clean.py       # Тесты очистки (10)
│       ├── test_aggregation.py # Тесты агрегации (5)
│       └── test_parquet.py     # Тесты Parquet (4)
├── charts/                # Сгенерированные графики
│   ├── 01_temperature_timeseries.png
│   ├── 02_avg_metrics_barh.png
│   ├── 03_temperature_histogram.png
│   └── 04_power_pie.png
└── README.md
```

## Требования

- **Go** 1.21+
- **Python** 3.12+
- **Пакеты Python:** `polars`, `duckdb`, `pandas`, `matplotlib`, `numpy`

```bash
py -m pip install polars duckdb pandas matplotlib numpy
```

## Запуск

### 1. Go-сборщик

```bash
cd go-collector
go build -o collector.exe .
.\collector.exe
# Ctrl+C для остановки
```

Сборщик эмулирует опрос 6 станков (CNC-001, Press-001, Robot-001, и т.д.)
каждые 10 секунд и записывает данные в `equipment_data.jsonl` батчами
(макс. 30 записей или каждые 20 секунд).

### 2. Очистка данных

```bash
py python-analysis/02_clean_data.py
```

### 3. Анализ (агрегация)

```bash
py python-analysis/03_aggregation.py
```

### 4. Сохранение в Parquet

```bash
py python-analysis/04_save_parquet.py
```

### 5. DuckDB + сравнение производительности

```bash
py python-analysis/05_duckdb_analysis.py
```

### 6. Визуализация

```bash
py python-analysis/06_visualization.py
```

Графики сохранятся в `charts/`.

## Тестирование

### Go-тесты (8 тестов)

```bash
cd go-collector
go test -v -count=1 ./...
```

Проверяют: генерацию показателей (поля, диапазоны, fault-режим), запись в JSON Lines,
пакетную запись (по размеру батча, по закрытию канала, по таймауту), количество
станков за цикл опроса.

### Python-тесты (24 теста)

```bash
py -m pytest python-analysis/tests -v
```

| Файл | Тесты | Что проверяют |
|---|---|---|
| `test_import.py` | 5 | Загрузка JSONL, колонки, количество строк, тип timestamp, пропуски |
| `test_clean.py` | 10 | Дедупликация (точна и по ключу), удаление fault, типы колонок, validation_flag |
| `test_aggregation.py` | 5 | Группировка по оборудованию/статусу, AVG температуры, SUM мощности |
| `test_parquet.py` | 4 | Запись/чтение, фильтрация, сжатие zstd, сохранение схемы |

**Всего: 32 теста (8 Go + 24 Python)**

## Примеры SQL-запросов (DuckDB)

```sql
-- Средние показатели по каждому станку
SELECT
    equipment_id,
    COUNT(*)                    AS readings,
    ROUND(AVG(temperature), 2) AS avg_temp,
    ROUND(AVG(pressure), 2)    AS avg_pressure,
    ROUND(SUM(power_consumption), 2) AS total_power
FROM 'go-collector/equipment_data.parquet'
WHERE status != 'fault'
GROUP BY equipment_id
ORDER BY equipment_id;

-- Почасовая агрегация
SELECT
    equipment_id,
    DATE_TRUNC('hour', timestamp) AS hour,
    COUNT(*)                      AS readings,
    ROUND(AVG(temperature), 2)    AS avg_temp
FROM 'go-collector/equipment_data.parquet'
WHERE status NOT IN ('fault', 'critical')
GROUP BY equipment_id, DATE_TRUNC('hour', timestamp)
ORDER BY hour, equipment_id;
```

## Характеристики Go-сборщика

| Параметр | Значение |
|---|---|
| Режим сбора | Горутины + WaitGroup (6 горутин/цикл) |
| Интервал опроса | 10 с |
| Размер батча | 30 записей |
| Таймаут батча | 20 с |
| Буфер канала | 100 записей |
| Graceful shutdown | SIGINT/SIGTERM → дообработка → flush |
| Формат вывода | JSON Lines (1 объект/строка) |

## Пример данных

```json
{"equipment_id":"CNC-001","temperature":65.2,"pressure":3.4,
 "vibration":0.82,"rpm":12000,"power_consumption":5.3,
 "status":"normal","timestamp":"2026-05-26T14:00:00+03:00"}
```

## Примечания

- Данные синтетические (эмуляция Modbus/OPC). В реальной среде заменить
  `simulateReading()` на вызов Modbus-клиента.
- Parquet предпочтительнее CSV/JSON для аналитики благодаря колоночному
  хранению и сжатию.
- DuckDB оптимален для ad-hoc SQL-запросов без загрузки данных в память.
