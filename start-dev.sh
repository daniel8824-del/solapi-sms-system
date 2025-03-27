#!/bin/bash

# 이전 컨테이너 정리
docker-compose down

# 이미지 빌드 및 컨테이너 시작
docker-compose up --build -d

# 로그 확인
docker-compose logs -f 