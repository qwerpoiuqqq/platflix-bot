#!/bin/bash
export TZ="Asia/Seoul"
# 두 개의 파이썬 스크립트가 동시에 실행되도록 설정

# 실시간 봇 실행
python3 bot.py &

# 매일 아침 8시에 자동 실행되는 daily_check
python3 daily_check.py
