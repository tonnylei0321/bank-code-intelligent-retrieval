#!/bin/bash

# 监控训练进度脚本
# 用法: ./监控训练进度.sh

echo "🎯 开始监控训练任务 #23"
echo "================================"
echo ""

while true; do
    clear
    echo "🎯 训练任务 #23 实时监控"
    echo "================================"
    echo ""
    
    # 查询数据库获取最新状态
    result=$(sqlite3 mvp/data/bank_code.db "SELECT status, current_epoch, epochs, progress_percentage, train_loss, val_loss FROM training_jobs WHERE id = 23")
    
    if [ -z "$result" ]; then
        echo "❌ 未找到训练任务 #23"
        break
    fi
    
    # 解析结果
    IFS='|' read -r status current_epoch total_epochs progress train_loss val_loss <<< "$result"
    
    # 显示状态
    echo "📊 基本信息"
    echo "  状态: $status"
    echo "  进度: ${progress}%"
    echo "  当前轮数: ${current_epoch}/${total_epochs}"
    echo ""
    
    # 显示Loss
    echo "📉 训练指标"
    if [ ! -z "$train_loss" ] && [ "$train_loss" != "" ]; then
        echo "  训练Loss: $train_loss"
    else
        echo "  训练Loss: 等待中..."
    fi
    
    if [ ! -z "$val_loss" ] && [ "$val_loss" != "" ]; then
        echo "  验证Loss: $val_loss"
    else
        echo "  验证Loss: 等待中..."
    fi
    echo ""
    
    # 显示进度条
    echo "📊 进度条"
    progress_int=${progress%.*}
    if [ -z "$progress_int" ]; then
        progress_int=0
    fi
    
    bar_length=50
    filled=$((progress_int * bar_length / 100))
    empty=$((bar_length - filled))
    
    printf "  ["
    for ((i=0; i<filled; i++)); do printf "█"; done
    for ((i=0; i<empty; i++)); do printf "░"; done
    printf "] ${progress}%%\n"
    echo ""
    
    # 显示最新日志
    echo "📝 最新日志 (最近5条)"
    echo "--------------------------------"
    tail -100 mvp/logs/app_2026-01-21.log | grep "Job 23" | tail -5
    echo ""
    
    # 检查是否完成
    if [ "$status" = "completed" ]; then
        echo "✅ 训练完成！"
        break
    elif [ "$status" = "failed" ]; then
        echo "❌ 训练失败！"
        break
    elif [ "$status" = "stopped" ]; then
        echo "⚠️  训练已停止"
        break
    fi
    
    echo "⏱️  自动刷新中... (按Ctrl+C退出)"
    echo "================================"
    
    # 每10秒刷新一次
    sleep 10
done

echo ""
echo "监控结束"
