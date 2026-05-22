#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# 🛡️ Watchdog — мониторинг и перезапуск бота
# ═══════════════════════════════════════════════════════════════
# Проверяет:
# 1. Что процесс bot.py существует и не завис
# 2. Что health endpoint отвечает (HTTP :8000)
# 3. Что бот не потребляет слишком много памяти
# При проблемах — убивает процесс и перезапускает
# ═══════════════════════════════════════════════════════════════

# ─── Конфигурация ──────────────────────────────────────────────
BOT_DIR="$(cd "$(dirname "$0")" && pwd)"  # папка со скриптом
BOT_SCRIPT="bot.py"
DB_SERVER_SCRIPT="database_server.py"

# Используем python из виртуального окружения, если есть
if [ -f "${BOT_DIR}/venv/bin/python" ]; then
    PYTHON="${BOT_DIR}/venv/bin/python"
else
    PYTHON="python3"
fi
HEALTH_PORT=8000
DB_SERVER_PORT=5001
HEALTH_URL="http://127.0.0.1:${HEALTH_PORT}"
DB_SERVER_HEALTH="http://127.0.0.1:${DB_SERVER_PORT}/health"
LOG_FILE="${BOT_DIR}/watchdog.log"
MAX_RESTARTS_PER_HOUR=5          # макс перезапусков в час
MAX_MEMORY_MB=500                # макс память процесса (MB)
CHECK_INTERVAL=60                # проверка каждые 60 секунд
RESTART_DELAY=5                  # пауза перед перезапуском (сек)

# ─── Toggle debug output ───────────────────────────────────────
DEBUG=true  # установите false чтобы убрать детальные логи

# ═══════════════════════════════════════════════════════════════

log() {
    local timestamp
    timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[${timestamp}] WATCHDOG: $1"
    echo "[${timestamp}] WATCHDOG: $1" >> "$LOG_FILE"
}

debug() {
    if [ "$DEBUG" = true ]; then
        local timestamp
        timestamp=$(date '+%Y-%m-%d %H:%M:%S')
        echo "[${timestamp}] DEBUG: $1" >> "$LOG_FILE"
    fi
}

# ─── Счётчик перезапусков ──────────────────────────────────────
RESTART_COUNT_FILE="${BOT_DIR}/.restart_count"
RESTART_HOUR_FILE="${BOT_DIR}/.restart_hour"

init_restart_counter() {
    echo 0 > "$RESTART_COUNT_FILE"
    date +%H > "$RESTART_HOUR_FILE"
}

check_restart_limit() {
    local current_hour
    current_hour=$(date +%H)
    local saved_hour
    saved_hour=$(cat "$RESTART_HOUR_FILE" 2>/dev/null || echo "-1")
    local count
    count=$(cat "$RESTART_COUNT_FILE" 2>/dev/null || echo 0)

    # Если час сменился — сбрасываем счётчик
    if [ "$current_hour" != "$saved_hour" ]; then
        echo 0 > "$RESTART_COUNT_FILE"
        echo "$current_hour" > "$RESTART_HOUR_FILE"
        debug "Restart counter reset for new hour"
        return 0
    fi

    if [ "$count" -ge "$MAX_RESTARTS_PER_HOUR" ]; then
        log "⚠️  Too many restarts ($count) this hour! Waiting..."
        return 1
    fi

    return 0
}

increment_restart_count() {
    local count
    count=$(cat "$RESTART_COUNT_FILE" 2>/dev/null || echo 0)
    count=$((count + 1))
    echo "$count" > "$RESTART_COUNT_FILE"
    debug "Restart count incremented to $count"
}

# ─── Проверка PID ──────────────────────────────────────────────

get_bot_pid() {
    # Ищем python процесс, запущенный с bot.py
    local pid
    pid=$(pgrep -f "python.*${BOT_SCRIPT}" 2>/dev/null | head -1)
    echo "$pid"
}

is_process_alive() {
    local pid=$1
    if [ -z "$pid" ]; then
        return 1
    fi
    kill -0 "$pid" 2>/dev/null
    return $?
}

# ─── Проверка памяти ───────────────────────────────────────────

check_memory() {
    local pid=$1
    if [ -z "$pid" ]; then
        return 1
    fi

    local mem_kb
    mem_kb=$(ps -o rss= -p "$pid" 2>/dev/null | tr -d ' ')
    if [ -z "$mem_kb" ]; then
        return 1
    fi

    local mem_mb=$((mem_kb / 1024))
    debug "Bot PID $pid memory: ${mem_mb}MB"

    if [ "$mem_mb" -gt "$MAX_MEMORY_MB" ]; then
        log "⚠️  Memory limit exceeded: ${mem_mb}MB > ${MAX_MEMORY_MB}MB"
        return 1
    fi

    return 0
}

# ─── Проверка HTTP Health ──────────────────────────────────────

check_health() {
    # Пробуем curl, если нет — используем wget или python
    if command -v curl &> /dev/null; then
        local http_code
        http_code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "$HEALTH_URL" 2>/dev/null)
        if [ "$http_code" = "200" ]; then
            debug "Health check: HTTP $http_code"
            return 0
        fi
        debug "Health check: HTTP $http_code"
        return 1

    elif command -v wget &> /dev/null; then
        if wget -q --timeout=5 -O /dev/null "$HEALTH_URL" 2>/dev/null; then
            debug "Health check: OK (wget)"
            return 0
        fi
        debug "Health check: FAIL (wget)"
        return 1

    else
        # fallback на python
        $PYTHON -c "
import urllib.request
try:
    urllib.request.urlopen('$HEALTH_URL', timeout=5)
    exit(0)
except:
    exit(1)
" 2>/dev/null
        return $?
    fi
}

# ─── Функции для Database Server ──────────────────────────────

get_db_pid() {
    local pid
    pid=$(pgrep -f "python.*${DB_SERVER_SCRIPT}" 2>/dev/null | head -1)
    echo "$pid"
}

check_db_health() {
    if command -v curl &> /dev/null; then
        local http_code
        http_code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 3 "$DB_SERVER_HEALTH" 2>/dev/null)
        [ "$http_code" = "200" ] && return 0
    else
        python3 -c "
import urllib.request
try:
    urllib.request.urlopen('$DB_SERVER_HEALTH', timeout=3)
    exit(0)
except:
    exit(1)
" 2>/dev/null && return 0
    fi
    return 1
}

start_db_server() {
    local pid
    pid=$(get_db_pid)
    if [ -n "$pid" ] && is_process_alive "$pid"; then
        debug "Database server already running (PID $pid)"
        return 0
    fi

    log "🗄️  Starting database server..."
    cd "$BOT_DIR" || return 1
    nohup $PYTHON -u "$DB_SERVER_SCRIPT" >> "${BOT_DIR}/db_server.log" 2>&1 &
    local new_pid=$!

    # Ждём пока сервер запустится (до 10 секунд)
    for i in $(seq 1 10); do
        sleep 1
        if check_db_health; then
            log "✅ Database server ready (PID $new_pid)"
            return 0
        fi
    done

    log "    ⚠️  Database server failed to start!"
    return 1
}

stop_db_server() {
    local pid=$1
    if [ -z "$pid" ]; then
        pid=$(get_db_pid)
    fi
    if [ -z "$pid" ]; then
        return
    fi

    log "🗄️  Stopping database server (PID $pid)..."
    kill "$pid" 2>/dev/null
    for i in $(seq 1 10); do
        if ! is_process_alive "$pid"; then
            log "    Database server stopped"
            return 0
        fi
        sleep 1
    done
    kill -9 "$pid" 2>/dev/null
    log "    Database server killed"
}

# ─── Остановка бота ────────────────────────────────────────────

stop_bot() {
    local pid=$1

    if [ -z "$pid" ]; then
        return
    fi

    log "🛑  Stopping bot (PID $pid)..."

    # Сначала SIGTERM (вежливый)
    kill "$pid" 2>/dev/null

    # Ждём 10 секунд
    for i in $(seq 1 10); do
        if ! is_process_alive "$pid"; then
            log "    Bot stopped gracefully"
            return 0
        fi
        sleep 1
    done

    # Если не остановился — SIGKILL
    log "    Force killing bot..."
    kill -9 "$pid" 2>/dev/null
    sleep 2

    # Проверяем, что убит
    if is_process_alive "$pid"; then
        log "    ⚠️  Could not kill bot process!"
        return 1
    fi

    log "    Bot killed"
    return 0
}

# ─── Запуск бота ───────────────────────────────────────────────

start_bot() {
    log "🚀  Starting bot..."

    # Переходим в папку бота
    cd "$BOT_DIR" || {
        log "    ⚠️  Cannot cd to $BOT_DIR"
        return 1
    }

    # Запускаем бота в фоне с nohup
    nohup $PYTHON -u "$BOT_SCRIPT" >> "${BOT_DIR}/bot_console.log" 2>&1 &
    local new_pid=$!

    # Ждём несколько секунд и проверяем
    sleep 3

    if is_process_alive "$new_pid"; then
        log "✅  Bot started (PID $new_pid)"
        return 0
    else
        log "    ⚠️  Bot failed to start!"
        return 1
    fi
}

# ─── Главный цикл ──────────────────────────────────────────────

main() {
    log "═══════════════════════════════════════════════"
    log "🛡️  Watchdog started"
    log "📁  Bot directory: $BOT_DIR"
    log "⏱   Check interval: ${CHECK_INTERVAL}s"
    log "🔁  Max restarts/hour: $MAX_RESTARTS_PER_HOUR"
    log "📊  Max memory: ${MAX_MEMORY_MB}MB"
    log "═══════════════════════════════════════════════"

    # Инициализируем счётчик рестартов
    init_restart_counter

    # Сначала запускаем сервер БД
    log "🗄️  Ensuring database server is running..."
    if ! check_db_health; then
        start_db_server
    else
        log "✅ Database server already running"
    fi

    local consecutive_failures=0

    while true; do
        # Проверяем сервер БД и запускаем если упал
        if ! check_db_health; then
            log "⚠️  Database server not responding, restarting..."
            stop_db_server
            start_db_server
        fi

        local pid
        pid=$(get_bot_pid)

        log_line=""
        needs_restart=false
        reason=""

        if [ -z "$pid" ]; then
            # Процесса нет — нужно запустить
            reason="Process not found"
            needs_restart=true
            log_line="❌  Bot process NOT FOUND"

        elif ! is_process_alive "$pid"; then
            # Процесс есть в pgrep, но не жив
            reason="Process dead"
            needs_restart=true
            log_line="❌  Bot process DEAD (PID $pid)"

        elif ! check_health; then
            # Процесс жив, но health check не проходит
            reason="Health check failed"
            needs_restart=true
            log_line="⚠️  Bot NOT RESPONDING (PID $pid)"

        elif ! check_memory "$pid"; then
            # Слишком много памяти
            reason="Memory exceeded"
            needs_restart=true
            log_line="⚠️  Bot MEMORY LIMIT EXCEEDED (PID $pid)"
        fi

        # Если всё хорошо — сбрасываем счётчик неудач
        if [ "$needs_restart" = false ]; then
            consecutive_failures=0
            debug "✅  Bot is healthy (PID $pid)"
        else
            # Логируем проблему
            log "$log_line — $reason"
            consecutive_failures=$((consecutive_failures + 1))

            # Проверяем лимит рестартов
            if ! check_restart_limit; then
                log "⏳  Waiting 10 minutes before retry..."
                sleep 600
                continue
            fi

            # Останавливаем старый процесс если есть
            if [ -n "$pid" ]; then
                stop_bot "$pid"
            fi

            # Пауза перед перезапуском
            log "⏳  Restarting in ${RESTART_DELAY}s..."
            sleep "$RESTART_DELAY"

            # Запускаем заново
            if start_bot; then
                increment_restart_count
                consecutive_failures=0
            else
                log "    ⚠️  Restart failed! Will retry..."
            fi
        fi

        # Ждём до следующей проверки
        sleep "$CHECK_INTERVAL"
    done
}

# ─── Запуск ────────────────────────────────────────────────────

# Создаём лог-файл если нет
touch "$LOG_FILE" 2>/dev/null

# Обработка сигналов
trap 'log "Watchdog stopped by signal"; exit 0' SIGINT SIGTERM

main