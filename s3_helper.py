import boto3
import os
from botocore.exceptions import NoCredentialsError
import uuid
import io

# AWS 설정
AWS_ACCESS_KEY = os.environ.get('MY_AWS_ACCESS_KEY')
AWS_SECRET_KEY = os.environ.get('MY_AWS_SECRET_KEY')
AWS_BUCKET_NAME = os.environ.get('MY_AWS_BUCKET_NAME', 'solapi-files')
AWS_REGION = os.environ.get('MY_AWS_REGION', 'ap-northeast-2')

def get_s3_client():
    """S3 클라이언트 객체를 반환합니다."""
    return boto3.client(
        's3',
        aws_access_key_id=AWS_ACCESS_KEY,
        aws_secret_access_key=AWS_SECRET_KEY,
        region_name=AWS_REGION
    )

def upload_file_to_s3(local_file_path, s3_file_key=None):
    """파일을 S3에 업로드하고 URL을 반환합니다."""
    if s3_file_key is None:
        # 고유한 파일 이름 생성
        file_ext = os.path.splitext(local_file_path)[1]
        s3_file_key = f"uploads/{uuid.uuid4()}{file_ext}"
    
    try:
        s3_client = get_s3_client()
        s3_client.upload_file(local_file_path, AWS_BUCKET_NAME, s3_file_key)
        
        # 파일 URL 생성
        file_url = f"https://{AWS_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/{s3_file_key}"
        return True, file_url, s3_file_key
    except FileNotFoundError:
        return False, "파일을 찾을 수 없습니다.", None
    except NoCredentialsError:
        return False, "AWS 자격 증명이 올바르지 않습니다.", None
    except Exception as e:
        return False, str(e), None

def upload_fileobj_to_s3(file_obj, original_filename=None):
    """파일 객체를 S3에 업로드하고 URL을 반환합니다."""
    try:
        s3_client = get_s3_client()
        file_ext = os.path.splitext(original_filename)[1] if original_filename else '.bin'
        s3_file_key = f"uploads/{uuid.uuid4()}{file_ext}"
        
        s3_client.upload_fileobj(file_obj, AWS_BUCKET_NAME, s3_file_key)
        
        # 파일 URL 생성
        file_url = f"https://{AWS_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/{s3_file_key}"
        return True, file_url, s3_file_key
    except NoCredentialsError:
        return False, "AWS 자격 증명이 올바르지 않습니다.", None
    except Exception as e:
        return False, str(e), None

def download_file_from_s3(s3_file_key, local_file_path):
    """S3에서 파일을 다운로드합니다."""
    try:
        s3_client = get_s3_client()
        s3_client.download_file(AWS_BUCKET_NAME, s3_file_key, local_file_path)
        return True, "파일 다운로드 성공"
    except Exception as e:
        return False, str(e)

def read_object_from_s3(s3_file_key):
    """S3에서 파일 객체를 읽어 바이트로 반환합니다."""
    try:
        s3_client = get_s3_client()
        response = s3_client.get_object(Bucket=AWS_BUCKET_NAME, Key=s3_file_key)
        file_content = response['Body'].read()
        return True, file_content
    except Exception as e:
        return False, str(e)

def delete_file_from_s3(s3_file_key):
    """S3에서 파일을 삭제합니다."""
    try:
        s3_client = get_s3_client()
        s3_client.delete_object(Bucket=AWS_BUCKET_NAME, Key=s3_file_key)
        return True, "파일 삭제 성공"
    except Exception as e:
        return False, str(e)

def generate_presigned_url(s3_file_key, expiration=3600):
    """임시 접근 가능한 URL을 생성합니다."""
    try:
        s3_client = get_s3_client()
        url = s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': AWS_BUCKET_NAME, 'Key': s3_file_key},
            ExpiresIn=expiration
        )
        return True, url
    except Exception as e:
        return False, str(e) 