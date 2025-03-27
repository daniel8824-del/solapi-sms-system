@echo off
echo 솔라피 개발 환경을 시작합니다...

REM 이전 컨테이너 정리
docker-compose down

REM 이미지 빌드 및 컨테이너 시작
docker-compose up --build -d

REM 로그 확인
echo 애플리케이션 로그를 표시합니다. Ctrl+C로 로그 보기를 종료할 수 있습니다.
docker-compose logs -f 