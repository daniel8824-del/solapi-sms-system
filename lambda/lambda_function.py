import json
import base64
import os
import re
import uuid
import io
import boto3
import requests
from botocore.exceptions import NoCredentialsError
import hashlib
import hmac
import time
import datetime
from dotenv import load_dotenv
import csv
from io import StringIO

# .env 파일 로드
load_dotenv()

# 솔라피 API 설정
API_KEY = os.environ.get('API_KEY', '')
API_SECRET = os.environ.get('API_SECRET', '')
SENDER_PHONE = os.environ.get('SENDER_PHONE', '')

# AWS S3 설정
AWS_ACCESS_KEY = os.environ.get('AWS_ACCESS_KEY', '')
AWS_SECRET_KEY = os.environ.get('AWS_SECRET_KEY', '')
AWS_REGION = os.environ.get('AWS_REGION', 'ap-northeast-2')
AWS_BUCKET_NAME = os.environ.get('AWS_BUCKET_NAME', '')

# 솔라피 API URL
API_BASE_URL = "https://api.solapi.com/messages/v4"
FILE_UPLOAD_URL = "https://api.solapi.com/storage/v1/files"

def get_auth_header(api_key, api_secret):
    """HTTP 요청 인증을 위한, HMAC 서명 기반 헤더를 생성합니다."""
    date = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%fZ')
    salt = str(uuid.uuid4())
    
    # HMAC 서명 생성
    signature_message = date + salt
    signature = hmac.new(
        api_secret.encode(),
        signature_message.encode(),
        hashlib.sha256
    ).hexdigest()
    
    # 헤더 생성
    return {
        'Authorization': f'HMAC-SHA256 apiKey={api_key}, date={date}, salt={salt}, signature={signature}',
        'Content-Type': 'application/json'
    }

def upload_file(api_key, api_secret, file_path=None, file_content=None, filename=None):
    """솔라피 API에 파일을 업로드합니다."""
    import os
    import mimetypes
    
    headers = get_auth_header(api_key, api_secret)
    headers.pop('Content-Type')  # multipart/form-data로 자동 설정
    
    try:
        print(f"파일 업로드 시작: file_path={file_path}, filename={filename}")
        
        # 파일 크기 제한 (MMS 이미지는 200KB 이하)
        if file_path:
            file_size = os.path.getsize(file_path)
            if file_size > 200 * 1024:  # 200KB를 바이트로 환산
                print(f"파일 크기 초과: {file_size} bytes")
                return None, "FILE_TOO_LARGE"
                
            # 파일 MIME 타입 유추
            content_type, _ = mimetypes.guess_type(file_path)
            if not content_type:
                content_type = 'image/jpeg'  # 기본값 설정
            
            print(f"파일 타입: {content_type}")
            
            # 지원하는 이미지 타입인지 확인
            if not content_type.startswith(('image/jpeg', 'image/png', 'image/gif')):
                print(f"지원하지 않는 파일 타입: {content_type}")
                return None, "UNSUPPORTED_TYPE"
                
            # 파일 업로드
            with open(file_path, 'rb') as f:
                files = {'file': (os.path.basename(file_path), f, content_type)}
                response = requests.post(FILE_UPLOAD_URL, headers=headers, files=files)
        elif file_content and filename:
            # 파일 크기 제한
            if len(file_content) > 200 * 1024:  # 200KB를 바이트로 환산
                print(f"파일 크기 초과: {len(file_content)} bytes")
                return None, "FILE_TOO_LARGE"
                
            # 파일 MIME 타입 유추
            content_type, _ = mimetypes.guess_type(filename)
            if not content_type:
                content_type = 'image/jpeg'  # 기본값 설정
            
            print(f"파일 타입: {content_type}")
            
            # 지원하는 이미지 타입인지 확인
            if not content_type.startswith(('image/jpeg', 'image/png', 'image/gif')):
                print(f"지원하지 않는 파일 타입: {content_type}")
                return None, "UNSUPPORTED_TYPE"
                
            # 파일 업로드
            files = {'file': (filename, io.BytesIO(file_content), content_type)}
            response = requests.post(FILE_UPLOAD_URL, headers=headers, files=files)
        else:
            print("유효하지 않은 파라미터: file_path 또는 file_content와 filename이 필요합니다.")
            return None, "INVALID_PARAMS"
        
        print(f"API 응답: status_code={response.status_code}, text={response.text}")
            
        if response.status_code == 200:
            result = response.json()
            if "fileId" in result:
                print(f"파일 업로드 성공: fileId={result['fileId']}, type={result.get('type', '')}")
                return result["fileId"], result.get("type", "")
            else:
                print(f"fileId가 응답에 없음: {result}")
                return None, "NO_FILE_ID"
        else:
            print(f"API 오류 응답: {response.text}")
            return None, response.text
    except Exception as e:
        print(f"파일 업로드 중 예외 발생: {str(e)}")
        return None, str(e)

def send_single_message(api_key, api_secret, to, from_number, text, image_id=None):
    """단일 메시지를 발송합니다."""
    headers = get_auth_header(api_key, api_secret)
    
    # 메시지 타입 결정
    message_type = "MMS" if image_id else "SMS"
    if text and len(text) > 90 and not image_id:
        message_type = "LMS"
    
    print(f"메시지 타입: {message_type}, 이미지 ID: {image_id}")
        
    # 요청 데이터 구성
    data = {
        "message": {
            "to": to,
            "from": from_number,
            "text": text,
            "type": message_type
        }
    }
    
    # 이미지가 있는 경우 추가
    if image_id:
        data["message"]["imageId"] = image_id
        data["message"]["type"] = "MMS"  # 이미지가 있으면 반드시 MMS로 설정
        print(f"이미지 첨부 메시지 발송: imageId={image_id}, type=MMS")
    
    print(f"요청 데이터: {json.dumps(data)}")
        
    # API 요청
    response = requests.post(f"{API_BASE_URL}/send", headers=headers, json=data)
    
    print(f"API 응답: status_code={response.status_code}, text={response.text}")
    
    # 결과 처리
    if response.status_code == 200:
        return {
            "success": True, 
            "result": response.json()
        }
    else:
        return {
            "success": False, 
            "error": response.text
        }

def send_many_messages(api_key, api_secret, messages):
    """다수의 메시지를 발송합니다."""
    if not messages:
        return {"error": "메시지가 없습니다."}
        
    headers = get_auth_header(api_key, api_secret)
    
    # 요청 데이터 구성
    data = {"messages": messages}
    
    # API 요청
    response = requests.post(f"{API_BASE_URL}/send-many", headers=headers, json=data)
    
    # 결과 처리
    if response.status_code == 200:
        result = response.json()
        return result
    else:
        return {"error": response.text}

def read_recipients_from_excel(excel_data, filename=None):
    """CSV 파일에서 수신자 목록을 읽어옵니다."""
    try:
        # CSV 파일 읽기
        import csv
        from io import StringIO
        
        # 바이너리 데이터를 문자열로 디코딩
        csv_text = excel_data.decode('utf-8-sig')  # BOM 처리
        csv_file = StringIO(csv_text)
        csv_reader = csv.reader(csv_file)
        
        recipients = []
        
        # 헤더 분석
        headers = {}
        header_row = next(csv_reader, None)
        if header_row:
            for col_idx, header in enumerate(header_row):
                if header:
                    headers[header.strip()] = col_idx
        
        # 수신자 정보 추출
        for row in csv_reader:
            # 조건 열 확인 (조건이 있는 경우, TRUE인 경우만 발송)
            if '조건' in headers:
                condition = row[headers['조건']]
                if not condition or condition.upper() == 'FALSE':
                    continue
            
            # 휴대폰 번호 확인
            phone_col = next((headers[h] for h in headers if any(k in h for k in ['휴대폰', '전화', 'phone', '수신'])), None)
            if phone_col is None:
                continue
                
            phone = row[phone_col]
            if not phone:
                continue
                
            # 전화번호 정제 (숫자만 추출)
            if isinstance(phone, (int, float)):
                phone = str(int(phone))
            elif isinstance(phone, str):
                phone = re.sub(r'[^0-9]', '', phone)
            
            if not phone:
                continue
                
            # 메시지 내용 구성
            text = ""
            
            # 별도 텍스트 컬럼이 있는지 확인
            text_col = next((headers[h] for h in headers if any(k in h for k in ['text', '내용', '메시지'])), None)
            if text_col is not None:
                text = row[text_col]
            
            # 한 줄에 모든 수신자 정보가 있는 경우 처리
            recipient = {
                'to': phone,
                'from': SENDER_PHONE,
                'text': text if text else "",
                'type': 'SMS'  # 기본 메시지 타입
            }
            
            recipients.append(recipient)
        
        return recipients
    except Exception as e:
        print(f"CSV 파일 처리 중 오류 발생: {str(e)}")
        return []

def parse_recipients_only(excel_data, filename=None):
    """CSV 파일에서 수신자 번호만 추출합니다."""
    try:
        # CSV 파일 읽기
        import csv
        from io import StringIO
        
        # 바이너리 데이터를 문자열로 디코딩
        csv_text = excel_data.decode('utf-8-sig')  # BOM 처리
        csv_file = StringIO(csv_text)
        csv_reader = csv.reader(csv_file)
        
        # 헤더 분석
        headers = {}
        header_row = next(csv_reader, None)
        if header_row:
            for col_idx, header in enumerate(header_row):
                if header:
                    headers[header.strip()] = col_idx
        
        # 수신자 번호가 있을 것 같은 컬럼 찾기
        phone_columns = []
        for header, col_idx in headers.items():
            header_lower = str(header).lower()
            if any(keyword in header_lower for keyword in ['휴대폰', '전화', 'phone', '수신', '번호']):
                phone_columns.append(col_idx)
        
        if not phone_columns:
            return {"success": False, "message": "수신자 번호 컬럼을 찾을 수 없습니다."}
        
        # 첫 번째 찾은 컬럼에서 번호 추출
        phone_col = phone_columns[0]
        recipients = []
        
        for row in csv_reader:
            if len(row) <= phone_col:
                continue
                
            phone = row[phone_col]
            if not phone:
                continue
                
            # 전화번호 정제 (숫자만 추출)
            if isinstance(phone, (int, float)):
                phone = str(int(phone))
            elif isinstance(phone, str):
                phone = re.sub(r'[^0-9]', '', phone)
            
            if phone:
                recipients.append(phone)
        
        # 중복 제거
        recipients = list(set(recipients))
        
        return {
            "success": True,
            "recipients": recipients,
            "count": len(recipients)
        }
    except Exception as e:
        return {"success": False, "message": str(e)}

def upload_to_s3(file_data, filename):
    """파일을 S3에 업로드합니다."""
    if not AWS_ACCESS_KEY or not AWS_SECRET_KEY or not AWS_BUCKET_NAME:
        return False, "AWS S3 인증 정보가 설정되지 않았습니다."
    
    try:
        s3_client = boto3.client(
            's3',
            aws_access_key_id=AWS_ACCESS_KEY,
            aws_secret_access_key=AWS_SECRET_KEY,
            region_name=AWS_REGION
        )
        
        # S3에 업로드할 파일 키 생성
        file_extension = os.path.splitext(filename)[1] if filename else '.bin'
        s3_key = f"uploads/{uuid.uuid4()}{file_extension}"
        
        # 파일 업로드
        if isinstance(file_data, bytes):
            s3_client.upload_fileobj(io.BytesIO(file_data), AWS_BUCKET_NAME, s3_key)
        else:
            s3_client.upload_file(file_data, AWS_BUCKET_NAME, s3_key)
            
        file_url = f"https://{AWS_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/{s3_key}"
        return True, {"url": file_url, "key": s3_key}
    except NoCredentialsError:
        return False, "AWS 인증 정보가 올바르지 않습니다."
    except Exception as e:
        return False, str(e)

def lambda_handler(event, context):
    """Lambda 함수 핸들러"""
    try:
        # 디버깅: 입력 이벤트 로깅
        print(f"받은 이벤트: {json.dumps(event)}")
        
        # API Gateway 또는 Lambda URL을 통해 들어온 요청 처리
        if isinstance(event, dict) and event.get('body'):
            # API Gateway 통합의 경우
            print("API Gateway 통합 요청 감지됨")
            body = json.loads(event['body'])
        else:
            # Lambda URL의 경우
            print("직접 Lambda URL 호출 감지됨")
            body = event
            
        print(f"처리할 본문 데이터: {json.dumps(body)}")
        request_type = body.get('type', '')
        print(f"요청 타입: '{request_type}'")
        
        # 디버깅용 ping 요청 처리
        if request_type == 'ping':
            return {
                'success': True,
                'message': 'Lambda 함수가 정상적으로 응답했습니다.',
                'request': body
            }
        
        # 1. 단일 메시지 발송
        if request_type == 'single':
            to = body.get('to', '')
            message = body.get('message', '')
            
            if not to or not message:
                return {
                    'success': False,
                    'message': '수신번호와 메시지 내용이 필요합니다.'
                }
                
            # 이미지 처리
            image_id = None
            if 'image' in body:
                print(f"이미지 필드 발견: {json.dumps(body['image'])}")
                
                image_data = body['image']
                # 이미지 데이터가 비어있거나 null인 경우 처리
                if image_data is None or (isinstance(image_data, dict) and len(image_data) == 0):
                    print("이미지 필드가 비어있습니다. 일반 SMS로 발송합니다.")
                elif not isinstance(image_data, dict):
                    print(f"이미지 데이터 형식 오류: {type(image_data)}")
                    return {
                        'success': False,
                        'message': f'이미지 데이터 형식 오류: 딕셔너리 형태여야 합니다.'
                    }
                elif 'data' not in image_data or not image_data.get('data'):
                    print("이미지 데이터에 'data' 필드가 없거나 비어있습니다.")
                    return {
                        'success': False,
                        'message': '이미지 데이터에는 base64로 인코딩된 data 필드가 필요합니다.'
                    }
                else:
                    # Base64 디코딩
                    try:
                        print(f"이미지 데이터 처리 시작: data 길이={len(image_data['data'])}")
                        image_content = base64.b64decode(image_data['data'])
                        image_filename = image_data.get('filename', 'image.jpg')
                        print(f"이미지 디코딩 완료: 크기={len(image_content)} bytes, 파일명={image_filename}")
                        
                        # 솔라피 API에 이미지 업로드
                        image_id, image_error = upload_file(
                            API_KEY, 
                            API_SECRET, 
                            file_content=image_content, 
                            filename=image_filename
                        )
                        
                        if not image_id:
                            print(f"이미지 업로드 실패: {image_error}")
                            return {
                                'success': False,
                                'message': f'이미지 업로드 실패: {image_error}'
                            }
                        print(f"이미지 업로드 성공: image_id={image_id}")
                    except Exception as e:
                        print(f"이미지 처리 중 오류 발생: {str(e)}")
                        return {
                            'success': False,
                            'message': f'이미지 처리 중 오류 발생: {str(e)}'
                        }
            
            # 메시지 발송
            print(f"메시지 발송 시작: to={to}, image_id={image_id}")
            result = send_single_message(
                API_KEY,
                API_SECRET,
                to,
                SENDER_PHONE,
                message,
                image_id
            )
            
            print(f"메시지 발송 결과: {json.dumps(result)}")
            return result
            
        # 2. 대량 메시지 발송 (텍스트 입력)
        elif request_type == 'bulk_text':
            text = body.get('text', '')
            recipients_str = body.get('recipients', '')
            
            print("=" * 80)
            print(f"Lambda 수신 데이터:")
            print(f"text: {text[:30]}...")
            print(f"recipients_str 타입: {type(recipients_str)}")
            print(f"recipients_str 내용: {recipients_str}")
            print(f"recipients_str 길이: {len(recipients_str) if isinstance(recipients_str, str) else 'not a string'}")
            print("=" * 80)
            
            if not text or not recipients_str:
                return {
                    'success': False,
                    'message': '메시지 내용과 수신자 목록이 필요합니다.'
                }
                
            # 수신자 목록 처리
            recipients = []
            try:
                # JSON 형식으로 파싱 시도
                recipients_json = json.loads(recipients_str)
                if isinstance(recipients_json, list):
                    recipients = recipients_json
                else:
                    recipients = recipients_str.split(',')
            except:
                # 쉼표로 구분된 문자열로 처리
                recipients = recipients_str.split(',')
                
            recipients = [r.strip() for r in recipients if r.strip()]
            
            if not recipients:
                return {
                    'success': False,
                    'message': '유효한 수신자 정보가 없습니다.'
                }
                
            # 이미지 처리
            image_id = None
            message_type = "SMS"
            
            if 'image' in body and body['image']:
                image_data = body['image']
                image_content = base64.b64decode(image_data['data'])
                image_filename = image_data['filename']
                
                # 솔라피 API에 이미지 업로드
                image_id, image_error = upload_file(
                    API_KEY, 
                    API_SECRET, 
                    file_content=image_content, 
                    filename=image_filename
                )
                
                if image_id:
                    message_type = "MMS"
                else:
                    return {
                        'success': False,
                        'message': f'이미지 업로드 실패: {image_error}'
                    }
            
            # 메시지 객체 생성
            messages = []
            for recipient in recipients:
                message = {
                    'to': recipient,
                    'from': SENDER_PHONE,
                    'text': text,
                    'type': message_type
                }
                
                if image_id:
                    message['imageId'] = image_id
                    
                messages.append(message)
                
            # 메시지 발송
            result = send_many_messages(API_KEY, API_SECRET, messages)
            
            # 응답 결과 가공
            response = {
                'success': True,
                'total': len(messages),
                'failedCount': 0,
                'failedList': [],
                'message': '대량 메시지가 성공적으로 발송되었습니다.'
            }
            
            # 실패 메시지 처리
            if "failedMessageList" in result and result["failedMessageList"]:
                failed_list = result["failedMessageList"]
                response["failedCount"] = len(failed_list)
                
                error_messages = {
                    "ValidationError": "유효성 검사 오류",
                    "HttpError": "HTTP 오류",
                    "InsufficientBalance": "잔액 부족",
                    "NotEnoughBalance": "잔액 부족",
                    "RateLimitError": "요청 한도 초과",
                    "ServerError": "서버 오류",
                    "InvalidPhoneNumber": "유효하지 않은 전화번호",
                    "InvalidFrom": "발신번호 오류",
                    "BlockedNumber": "차단된 번호"
                }
                
                for failed in failed_list:
                    error_info = {
                        "to": failed.get("to", "알 수 없음"),
                        "reason": "알 수 없는 오류"
                    }
                    
                    if "errorCode" in failed:
                        code = failed["errorCode"]
                        if code in error_messages:
                            error_info["reason"] = error_messages[code]
                        else:
                            error_info["reason"] = f"오류 코드: {code}"
                    
                    response["failedList"].append(error_info)
            
            return response
            
        # 3. 엑셀 파일 처리
        elif request_type == 'bulk_excel':
            if 'excel' not in body or not body['excel']:
                return {
                    'success': False,
                    'message': '엑셀 파일이 필요합니다.'
                }
                
            excel_data = body['excel']
            excel_content = base64.b64decode(excel_data['data'])
            excel_filename = excel_data['filename']
            
            # 엑셀에서 수신자 정보 추출
            recipients = read_recipients_from_excel(excel_content, excel_filename)
            
            if not recipients:
                return {
                    'success': False,
                    'message': '유효한 수신자 정보가 없습니다.'
                }
                
            # 미리보기 모드 확인
            preview_mode = body.get('preview', False)
            if preview_mode:
                # 미리보기 데이터만 반환
                preview_data = []
                for i, recipient in enumerate(recipients[:5]):
                    preview = {
                        'index': i + 1,
                        'phone': recipient['to'],
                        'text': recipient['text'][:100] + '...' if len(recipient['text']) > 100 else recipient['text']
                    }
                    preview_data.append(preview)
                    
                return {
                    'success': True,
                    'total': len(recipients),
                    'recipients': recipients,
                    'preview': preview_data
                }
            
            # 이미지 처리
            if 'image' in body and body['image']:
                image_data = body['image']
                image_content = base64.b64decode(image_data['data'])
                image_filename = image_data['filename']
                
                # 솔라피 API에 이미지 업로드
                image_id, image_error = upload_file(
                    API_KEY, 
                    API_SECRET, 
                    file_content=image_content, 
                    filename=image_filename
                )
                
                if image_id:
                    # 모든 메시지에 이미지 추가
                    for recipient in recipients:
                        recipient['imageId'] = image_id
                        recipient['type'] = 'MMS'
                else:
                    return {
                        'success': False,
                        'message': f'이미지 업로드 실패: {image_error}'
                    }
            
            # 메시지 발송
            result = send_many_messages(API_KEY, API_SECRET, recipients)
            
            # 응답 결과 가공
            response = {
                'success': True,
                'total': len(recipients),
                'failedCount': 0,
                'failedList': [],
                'message': '대량 메시지가 성공적으로 발송되었습니다.'
            }
            
            # 실패 메시지 처리
            if "failedMessageList" in result and result["failedMessageList"]:
                failed_list = result["failedMessageList"]
                response["failedCount"] = len(failed_list)
                
                error_messages = {
                    "ValidationError": "유효성 검사 오류",
                    "HttpError": "HTTP 오류",
                    "InsufficientBalance": "잔액 부족",
                    "NotEnoughBalance": "잔액 부족",
                    "RateLimitError": "요청 한도 초과",
                    "ServerError": "서버 오류",
                    "InvalidPhoneNumber": "유효하지 않은 전화번호",
                    "InvalidFrom": "발신번호 오류",
                    "BlockedNumber": "차단된 번호"
                }
                
                for failed in failed_list:
                    error_info = {
                        "to": failed.get("to", "알 수 없음"),
                        "reason": "알 수 없는 오류"
                    }
                    
                    if "errorCode" in failed:
                        code = failed["errorCode"]
                        if code in error_messages:
                            error_info["reason"] = error_messages[code]
                        else:
                            error_info["reason"] = f"오류 코드: {code}"
                    
                    response["failedList"].append(error_info)
            
            return response
            
        # 4. 수신자 목록만 추출
        elif request_type == 'parse_recipients':
            if 'excel' not in body or not body['excel']:
                return {
                    'success': False,
                    'message': '엑셀 파일이 필요합니다.'
                }
                
            excel_data = body['excel']
            excel_content = base64.b64decode(excel_data['data'])
            excel_filename = excel_data['filename']
            
            # 수신자 번호만 추출
            return parse_recipients_only(excel_content, excel_filename)
        
        # 요청 타입이 유효하지 않은 경우
        return {
            'success': False,
            'message': '유효하지 않은 요청 유형입니다.'
        }
        
    except Exception as e:
        return {
            'success': False,
            'message': str(e)
        }

# AWS Lambda 환경이 아닌 경우를 위한 로컬 테스트 함수
def main():
    # 단일 텍스트 메시지 테스트
    test_event = {
        'type': 'single',
        'to': '01012345678',
        'message': '안녕하세요, 테스트 메시지입니다.'
    }
    
    print("======= 단일 텍스트 메시지 테스트 =======")
    result = lambda_handler(test_event, None)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    
    # 비어있는 이미지 필드 테스트
    test_event_empty_image = {
        'type': 'single',
        'to': '01012345678',
        'message': '안녕하세요, 이미지 테스트입니다.',
        'image': {}
    }
    
    print("\n======= 비어있는 이미지 필드 테스트 =======")
    result = lambda_handler(test_event_empty_image, None)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    
    # 올바른 이미지 필드 테스트 (이미지 파일이 있는 경우에만 실행)
    try:
        with open("test_image.jpg", "rb") as img_file:
            image_data = base64.b64encode(img_file.read()).decode('utf-8')
            
            test_event_image = {
                'type': 'single',
                'to': '01012345678',
                'message': '안녕하세요, 이미지 첨부 테스트입니다.',
                'image': {
                    'data': image_data,
                    'filename': 'test_image.jpg'
                }
            }
            
            print("\n======= 이미지 첨부 테스트 =======")
            result = lambda_handler(test_event_image, None)
            print(json.dumps(result, indent=2, ensure_ascii=False))
    except FileNotFoundError:
        print("\n테스트 이미지 파일(test_image.jpg)이 없어 이미지 첨부 테스트를 건너뜁니다.")

# 로컬에서 실행할 때만 main 함수 호출
if __name__ == '__main__':
    main() 