#!/bin/bash

# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN="60gPw"
TELEGRAM_CHAT_ID="-102"
API_URL="https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage"

# Threshold Configuration
RUN_QUEUE_THRESHOLD=8        # r column
BLOCKED_THRESHOLD=2          # b column
SWAP_IN_THRESHOLD=10         # si column
SWAP_OUT_THRESHOLD=10      # so column
IO_WAIT_THRESHOLD=15         # wa column (percentage)
SYSTEM_CPU_THRESHOLD=15      # sy column (percentage)
FREE_MEM_THRESHOLD=124288    # 512MB (in kB)
SWAP_USED_THRESHOLD=10
# Capture vmstat output
VMSTAT_OUTPUT=$(vmstat 1 5)

# Check if vmstat command succeeded
if [ $? -ne 0 ]; then
    echo "Error: Failed to execute vmstat command"
    exit 1
fi

# Process results
ALERT_TRIGGERED=false
ALERT_MESSAGE="🚨 *Server Alert* 🚨\nHost: $(hostname)\nTimestamp: $(date)\n\n"

# Check each sample (skip first 2 header lines)
while IFS= read -r line; do
    # Skip empty lines and header lines
    [[ -z "$line" || "$line" =~ ^procs || "$line" =~ ^\ +r ]] && continue

    # Parse relevant fields
    read -r r b swpd free buff cache si so bi bo in cs us sy id wa st <<< "$line"

    # Check thresholds
    if [ "$r" -ge "$RUN_QUEUE_THRESHOLD" ]; then
        ALERT_TRIGGERED=true
        ALERT_MESSAGE+="• High run queue: $r (≥$RUN_QUEUE_THRESHOLD)\n"
    fi

    if [ "$b" -ge "$BLOCKED_THRESHOLD" ]; then
        ALERT_TRIGGERED=true
        ALERT_MESSAGE+="• Blocked processes: $b (≥$BLOCKED_THRESHOLD)\n"
    fi

    # Add to monitoring section:
    swap_used=$(free | awk '/Swap/{printf "%d", $3/$2*100}')
    if [ "$swap_used" -ge "$SWAP_USED_THRESHOLD" ]; then
        ALERT_TRIGGERED=true
        ALERT_MESSAGE+="• High swap usage: ${swap_used}% (≥$SWAP_USED_THRESHOLD%)\n"
    fi
    if [ "$si" -ge "$SWAP_IN_THRESHOLD" ]; then
        ALERT_TRIGGERED=true
        ALERT_MESSAGE+="• Swap in detected: ${si}kB/s (≥$SWAP_IN_THRESHOLD)\n"
    fi

    if [ "$so" -ge "$SWAP_OUT_THRESHOLD" ]; then
        ALERT_TRIGGERED=true
        ALERT_MESSAGE+="• Swap out detected: ${so}kB/s (≥$SWAP_OUT_THRESHOLD)\n"
    fi

    if [ "$wa" -ge "$IO_WAIT_THRESHOLD" ]; then
        ALERT_TRIGGERED=true
        ALERT_MESSAGE+="• High I/O wait: ${wa}% (≥$IO_WAIT_THRESHOLD%)\n"
    fi

    if [ "$sy" -ge "$SYSTEM_CPU_THRESHOLD" ]; then
        ALERT_TRIGGERED=true
        ALERT_MESSAGE+="• High system CPU: ${sy}% (≥$SYSTEM_CPU_THRESHOLD%)\n"
    fi

    if [ "$free" -lt "$FREE_MEM_THRESHOLD" ]; then
        ALERT_TRIGGERED=true
        ALERT_MESSAGE+="• Low free memory: $(($free/1024))MB (≤$(($FREE_MEM_THRESHOLD/1024))MB)\n"
    fi
done <<< "$VMSTAT_OUTPUT"

# Send alert if any threshold was exceeded
if [ "$ALERT_TRIGGERED" = true ]; then
    ALERT_MESSAGE+="\n*Full vmstat output:*\n\`\`\`\n${VMSTAT_OUTPUT}\n\`\`\`"

    # Send to Telegram (with Markdown formatting)
    curl -s -X POST "$API_URL" \
        -d "chat_id=$TELEGRAM_CHAT_ID" \
        -d "text=$ALERT_MESSAGE" \
        -d "parse_mode=markdown" \
        -d "disable_web_page_preview=true" > /dev/null
fi



