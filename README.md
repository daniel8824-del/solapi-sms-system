# Solapi SMS 시스템

솔라피 API를 이용한 SMS 발송 시스템입니다. 

## 아키텍처

이 프로젝트는 다음과 같은 아키텍처로 구성되어 있습니다:

1. **Flask 웹 애플리케이션**: 사용자 인터페이스와 API 엔드포인트를 제공합니다.
2. **AWS Lambda 백엔드**: 무거운 데이터 처리 및 SMS 발송 로직을 처리합니다.
3. **AWS S3**: 필요에 따라 파일을 저장합니다.

## 설치 및 실행 방법

### 도커 개발 환경

1. Docker와 Docker Compose 설치

2. 환경 변수 설정
   ```
   cp .env.example .env
   # .env 파일 편집하여 필요한 값 입력
   ```

3. 도커 컨테이너 실행
   ```
   docker compose up --build -d
   ```

4. 애플리케이션 접속
   ```
   http://localhost:5000
   ```

### 로컬 개발 환경

1. 가상환경 생성 및 활성화
   ```
   python -m venv .venv
   .venv\Scripts\activate  # Windows
   source .venv/bin/activate  # Mac/Linux
   ```

2. 필요한 패키지 설치
   ```
   pip install -r requirements.txt
   ```

3. 환경 변수 설정
   ```
   cp .env.example .env
   # .env 파일 편집하여 필요한 값 입력
   ```

4. 애플리케이션 실행
   ```
   python app.py
   ```

## AWS Lambda 함수 배포

AWS Lambda 배포 방법:
1. Lambda 함수 생성
2. `lambda_update.py` 코드를 Lambda 함수에 업로드
3. 필요한 환경 변수 설정 (API_KEY, API_SECRET, SENDER_PHONE 등)
4. Lambda 함수 URL 활성화
5. `.env` 파일의 `LAMBDA_FUNCTION_URL` 변수 업데이트

## 주요 파일 구조

```
├── app.py                 # Flask 웹 애플리케이션
├── lambda_update.py      # AWS Lambda 함수 코드
├── docker-compose.yml     # Docker Compose 설정 파일
├── Dockerfile             # Docker 이미지 빌드 파일
├── templates/             # 웹 페이지 템플릿
│   └── index.html         # 메인 페이지
├── data/                  # 데이터 파일 저장 디렉토리
│   ├── bulk_template.xlsx # 대량 메시지 템플릿 파일
│   └── sample_template.csv # 샘플 CSV 템플릿
├── uploads/               # 업로드 파일 임시 저장소
└── requirements.txt       # 프로젝트 의존성
```

## 환경 변수

- `FLASK_SECRET_KEY`: Flask 세션 암호화 키
- `LAMBDA_FUNCTION_URL`: AWS Lambda 함수 URL
- `API_KEY`: 솔라피 API 키
- `API_SECRET`: 솔라피 API 시크릿
- `SENDER_PHONE`: 발신자 전화번호
- `MY_AWS_ACCESS_KEY`: AWS 접근 키
- `MY_AWS_SECRET_KEY`: AWS 시크릿 키
- `MY_AWS_REGION`: AWS 리전
- `MY_AWS_BUCKET_NAME`: AWS S3 버킷 이름
- `DEBUG_MODE`: 디버그 모드 설정 (True/False)

## 주요 기능

### 1. 단일 메시지 발송
- 한 명의 수신자에게 SMS/MMS 발송
- 이미지 첨부 기능 (MMS)
- 발송 결과 실시간 확인

### 2. 대량 메시지 발송
- 다수의 수신자에게 동일한 SMS/MMS 발송
- 수신자 번호 직접 입력 또는 엑셀 파일 업로드
- 이미지 첨부 기능 (MMS)
- 발송 결과 요약 및 상세 정보 제공

### 3. 자동화 메시지 발송
- 엑셀 파일을 통한 개인별 맞춤 메시지 자동 생성
- 변수 치환 기능 (이름, 주문일자, 주문금액 등)
- 메시지 미리보기 기능
- 체크박스로 발송 대상 선택 가능
- 이미지 첨부 기능 (MMS)

## 엑셀 템플릿 사용 가이드

### 기본 구조
- **sample 시트**: A2 셀에 메시지 템플릿 작성 (변수는 {{변수명}} 형식으로 사용)
- **data 시트**: 수신자 정보와 변수 데이터 입력

### 필수 열
- **조건**: TRUE/FALSE 값으로 발송 여부 설정
- **휴대폰번호**: 수신자 전화번호
- **이름**: 수신자 이름 (변수로 사용 가능)
- 그 외 템플릿에서 사용하는 변수명과 동일한 열 추가 가능 (주문일자, 주문금액 등)

## 개발 환경

- Python 3.9+
- Flask 2.2.3
- Pandas 1.5.3
- OpenPyXL 3.1.2
- Requests 2.28.2
- Boto3 1.26.135
- Docker & Docker Compose

## 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다.
