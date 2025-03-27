FROM python:3.9-slim

WORKDIR /app

# 기본 시스템 패키지 설치
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libc6-dev \
    && rm -rf /var/lib/apt/lists/*

# 필요한 Python 패키지 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# pandas와 관련 패키지 설치 (버전 명시로 호환성 보장)
RUN pip install numpy==1.22.4 pandas==1.5.3 openpyxl==3.1.2

# 애플리케이션 파일 복사
COPY . .

# 환경 변수 설정
ENV FLASK_APP=app.py
ENV FLASK_ENV=production

# 포트 설정
EXPOSE 5000

# 애플리케이션 실행
CMD ["python", "app.py"]