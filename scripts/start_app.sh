#!/bin/bash
# 跨境套利系统启动脚本

APP_DIR="$(cd "$(dirname "$0")/.." && pwd)"
APP_FILE="$APP_DIR/app.py"
PORT=4000

echo "检查进程..."

# 检查 Flask 进程
PIDS=$(ps aux | grep "python3 $APP_FILE" | grep -v grep | awk '{print $2}')

if [ -n "$PIDS" ]; then
    echo "发现运行中的进程: $PIDS"
    echo "正在关闭..."
    for pid in $PIDS; do
        kill $pid 2>/dev/null
    done
    sleep 2
    
    # 强制杀死如果还在运行
    PIDS=$(ps aux | grep "python3 $APP_FILE" | grep -v grep | awk '{print $2}')
    if [ -n "$PIDS" ]; then
        echo "强制关闭..."
        for pid in $PIDS; do
            kill -9 $pid 2>/dev/null
        done
        sleep 1
    fi
    echo "已关闭"
else
    echo "没有运行中的进程"
fi

# 检查端口是否被占用
if netstat -tuln 2>/dev/null | grep -q ":$PORT " || ss -tuln 2>/dev/null | grep -q ":$PORT "; then
    echo "端口 $PORT 被占用，正在释放..."
    fuser -k $PORT/tcp 2>/dev/null
    sleep 1
fi

# 启动应用
echo "启动应用..."
cd "$APP_DIR"
setsid python3 "$APP_FILE" > /tmp/flask.log 2>&1 &

# 等待启动
sleep 3

# 验证启动
sleep 2
if curl -s http://127.0.0.1:$PORT/api/lof -o /dev/null; then
    echo "启动成功！"
    echo "访问地址: http://192.168.1.154:$PORT"
    echo "或: http://127.0.0.1:$PORT"
else
    echo "启动失败，请检查日志:"
    cat /tmp/flask.log
fi