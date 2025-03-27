import pandas as pd
import io
import os
import uuid
from s3_helper import get_s3_client, AWS_BUCKET_NAME
import openpyxl

# 글로벌 변수 정의
message_data = []
SENDER_PHONE = os.environ.get('SENDER_PHONE', "01032018824")

def read_recipients_from_s3(s3_key):
    """S3에 저장된 엑셀 파일에서 수신자 정보를 읽어옵니다."""
    global message_data
    message_data = []
    
    sample_template = "안녕하세요 {{이름}}님, {{주문일자}}에 주문하신 {{주문상품}}이 발송되었습니다."
    has_template_from_a2 = False
    debug_mode = False
    
    try:
        print(f"S3에서 엑셀 파일 로드 중: {s3_key}")
        
        # S3에서 파일 데이터 가져오기
        s3_client = get_s3_client()
        response = s3_client.get_object(Bucket=AWS_BUCKET_NAME, Key=s3_key)
        excel_data = response['Body'].read()
        
        # BytesIO로 메모리에서 엑셀 파일 열기
        excel_io = io.BytesIO(excel_data)
        
        try:
            wb = openpyxl.load_workbook(excel_io, read_only=True, data_only=True)
            
            if 'sample' in wb.sheetnames:
                print("'sample' 시트를 찾았습니다.")
                sheet = wb['sample']                
                a2_value = sheet['A2'].value

                if a2_value and a2_value.strip():
                    print(f"원본 A2 셀 값: '{a2_value}'")    
                    sample_template = str(a2_value)
                    sample_template = sample_template.replace('\r\n', '\n').replace('\r', '\n')
                    
                    print(f"A2 셀에서 읽은 템플릿(띄어쓰기 확인): '{sample_template}'")
                    print(f"템플릿 문자 코드 확인: {[ord(c) for c in sample_template[:20]]}")
                    
                    if "\n" not in sample_template:
                        if "]" in sample_template:
                            bracket_pos = sample_template.find("]")
                            if bracket_pos > 0:
                                sample_template = sample_template[:bracket_pos+1] + "\n" + sample_template[bracket_pos+1:]
                        
                        if "님," in sample_template:
                            sample_template = sample_template.replace("님,", "님,\n")
                        
                        if "쇼핑몰입니다" in sample_template:
                            sample_template = sample_template.replace("쇼핑몰입니다", "쇼핑몰입니다.\n")
                        
                        if "발송됩니다" in sample_template:
                            sample_template = sample_template.replace("발송됩니다", "발송됩니다.\n")
                        
                        if "◎" in sample_template:
                            sample_template = sample_template.replace("◎", "\n◎")
                        
                        if "감사합니다" in sample_template:
                            sample_template = sample_template.replace("감사합니다", "\n감사합니다")
                    
                    while "\n\n" in sample_template: sample_template = sample_template.replace("\n\n", "\n")
                    sample_template = sample_template.replace(":", ": ")
                    while "  " in sample_template: sample_template = sample_template.replace("  ", " ")
                    
                    print(f"처리된 템플릿:\n{sample_template}")
                    print(f"처리된 템플릿 문자 코드: {[ord(c) for c in sample_template[:20]]}")
                    has_template_from_a2 = True
                else:
                    print("A2 셀이 비어 있거나 값이 없습니다. 기본 템플릿을 사용합니다.")
            else:
                print("'sample' 시트를 찾을 수 없습니다. 기본 템플릿을 사용합니다.")
                
        except Exception as e:
            print(f"openpyxl을 사용한 A2 셀 확인 중 오류 발생: {str(e)}")
            print("기본 템플릿을 사용합니다.")
        
        # 파일 포인터를 처음으로 되돌림
        excel_io.seek(0)
        
        # pandas로 엑셀 데이터 읽기
        try:
            # 여러 시트를 시도
            for sheet in ['Sheet1', '발송', '발송목록', '데이터', 'Data', 'data']:
                try:
                    df = pd.read_excel(excel_io, sheet_name=sheet)
                    is_solapi_data = True
                    print(f"'{sheet}' 시트에서 데이터를 읽었습니다.")
                    break
                except:
                    continue
            else:
                try:
                    df = pd.read_excel(excel_io)
                    is_solapi_data = True
                    print("첫 번째 시트에서 데이터를 읽었습니다.")
                except:
                    print("엑셀 파일에서 시트를 읽을 수 없습니다.")
                    return message_data
        except Exception as e:
            print(f"pandas로 엑셀 파일 읽기 중 오류: {str(e)}")
            return message_data
        
        if has_template_from_a2:
            print(f"A2 셀 템플릿을 사용합니다. (길이: {len(sample_template)}자)")
        else:
            print("기본 템플릿을 사용합니다.")
        
        has_checkbox = False
        checkbox_col = None
        
        print("Excel 파일 열:", df.columns.tolist())

        for col in df.columns:
            col_str = str(col).lower()
            if col_str == '조건':  # '조건' 열이 TRUE/FALSE 값을 가집니다
                has_checkbox = True
                checkbox_col = col
                print(f"조건 열 발견: {checkbox_col}")
                break
        
        if checkbox_col is None:
            for col in df.columns:
                if str(col).startswith('Unnamed') or col == 0:  # 체크박스는 보통 이름이 없는 첫 번째 열
                    has_checkbox = True
                    checkbox_col = col
                    print(f"체크박스 열 발견: {checkbox_col}")
                    break
        
        recipients = []
        processed_count = 0
        skipped_count = 0
        
        for idx, row in df.iterrows():
            if has_checkbox:
                cell_value = str(row[checkbox_col]).upper()
                is_checked = cell_value in ['TRUE', '1', 'YES', 'Y', 'O', 'V', 'T', 'TRUE', 'OK']
                if debug_mode:
                    print(f"행 {idx+1}: 조건 값 '{cell_value}', 체크됨: {is_checked}")
                
                if not is_checked:
                    skipped_count += 1
                    continue
            
            phone_col = None
            if '휴대폰번호' in df.columns:
                phone_col = '휴대폰번호'
                print(f"정확한 휴대폰번호 열 발견: {phone_col}")
            else:
                for col in df.columns:
                    col_str = str(col).lower()
                    if col_str == '전화번호' or '수신' in col_str or '휴대' in col_str or '전화' in col_str or '연락' in col_str or '폰' in col_str:
                        phone_col = col
                        print(f"유사한 휴대폰번호 열 발견: {phone_col}")
                        break
            
            if phone_col is None:
                print(f"[경고] 행 {idx+1}: 휴대폰번호 열을 찾을 수 없습니다.")
                skipped_count += 1
                continue
            
            if phone_col not in row.index or pd.isna(row[phone_col]) or str(row[phone_col]).strip() == '':
                print(f"[경고] 행 {idx+1}: 수신번호가 없음 -> 건너뛰기")
                skipped_count += 1
                continue
                
            phone = str(row[phone_col])
            phone = ''.join(filter(str.isdigit, phone))
            
            if not phone or len(phone) < 10:
                print(f"[경고] 행 {idx+1}: 유효하지 않은 전화번호: {row[phone_col]} -> 건너뛰기")
                skipped_count += 1
                continue
                
            name_col = None
            for col in df.columns:
                col_str = str(col).lower()
                if col_str == '이름' or '성명' in col_str or '고객' in col_str:
                    name_col = col
                    print(f"이름 열 발견: {name_col}")
                    break
            
            recipient = {
                'to': phone,
                'from': SENDER_PHONE,
                'text': ''}
            
            message_text = ''
            
            if '메시지내용' in row and not pd.isna(row['메시지내용']):
                message_text = str(row['메시지내용'])
            elif '비고' in row and not pd.isna(row['비고']):
                message_text = str(row['비고'])
            elif '메시지' in row and not pd.isna(row['메시지']):
                message_text = str(row['메시지'])
            elif '내용' in row and not pd.isna(row['내용']):
                message_text = str(row['내용'])
            
            if message_text == '' and '템플릿' in row and not pd.isna(row['템플릿']):
                if has_template_from_a2:
                    print(f"행 {idx+1}: A2 셀 템플릿을 우선 사용합니다.")
                    template = sample_template
                else:
                    template = str(row['템플릿'])
                    print(f"행 {idx+1}: '템플릿' 열에서 템플릿을 사용합니다: {template[:30]}...")
                    
                import re
                single_var_pattern = r'{([^{}]+)}'
                double_var_pattern = r'{{([^{}]+)}}'
                single_variables = re.findall(single_var_pattern, template)
                double_variables = re.findall(double_var_pattern, template)
                variables = list(set(single_variables + double_variables))
                
                print(f"템플릿에서 발견된 단일 중괄호 변수: {single_variables}")
                print(f"템플릿에서 발견된 이중 중괄호 변수: {double_variables}")
                print(f"처리할 모든 변수: {variables}")
                
                variable_mapping = {
                    '주문상품': ['주문상품', '주문금액', '상품명', '상품', '제품명', '제품'],
                    '이름': ['이름', '고객명', '성명', '받는분', '수신자'],
                    '주문일자': ['주문일자', '주문날짜', '결제일', '결제일자', '구매일'],
                    '주문금액': ['주문금액', '결제금액', '금액', '가격'],
                    '휴대폰번호': ['휴대폰번호', '전화번호', '연락처', '핸드폰', '휴대폰'],
                    '배송업체': ['배송업체', '택배사', '배송사'],
                    '송장번호': ['송장번호', '운송장번호', '택배번호']}
                
                print(f"엑셀 파일 열 목록: {list(row.index)}")
                
                for var_name in variables:
                    found = False
                    if var_name in row.index and not pd.isna(row[var_name]):
                        var_value = str(row[var_name])
                        print(f"변수 '{var_name}'을 동일한 이름의 열에서 찾음: {var_value}")
                        found = True

                    elif var_name in variable_mapping:
                        for alt_name in variable_mapping[var_name]:
                            if alt_name in row.index and not pd.isna(row[alt_name]):
                                var_value = str(row[alt_name])
                                print(f"변수 '{var_name}'을 대체 열 '{alt_name}'에서 찾음: {var_value}")
                                found = True
                                break
                    else:
                        var_name_lower = var_name.lower()
                        for col in row.index:
                            col_lower = str(col).lower()
                            if var_name_lower in col_lower or col_lower in var_name_lower:
                                if not pd.isna(row[col]):
                                    var_value = str(row[col])
                                    print(f"변수 '{var_name}'을 유사한 이름의 열 '{col}'에서 찾음: {var_value}")
                                    found = True
                                    break
                
                    if found:
                        if '일자' in var_name or '날짜' in var_name or 'date' in var_name.lower():
                            try:
                                if ' 00:00:00' in var_value:  # 'YYYY-MM-DD 00:00:00' 형식
                                    var_value = var_value.split(' ')[0]
                                elif 'T00:00:00' in var_value:  # 'YYYY-MM-DDT00:00:00' 형식
                                    var_value = var_value.split('T')[0]
                                elif '.' in var_value and len(var_value) > 10:  # 'YYYY-MM-DD.000000' 형식
                                    var_value = var_value.split('.')[0]
                                
                                from pandas import Timestamp
                                if 'var_name' in row.index and isinstance(row[var_name], Timestamp):
                                    var_value = row[var_name].strftime('%Y-%m-%d')
                            except Exception as e:
                                print(f"날짜 변환 중 오류: {str(e)}")
                            
                            print(f"{var_name} 날짜 변환: {var_value}")
                        
                        import re
                        single_var_pattern = re.escape(f"{{{var_name}}}")
                        if re.search(single_var_pattern, template):
                            template = re.sub(single_var_pattern, var_value, template)
                            print(f"{var_name} 단일 중괄호 치환 완료: '{var_value}'")
                        
                        double_var_pattern = re.escape(f"{{{{{var_name}}}}}")
                        if re.search(double_var_pattern, template):
                            template = re.sub(double_var_pattern, var_value, template)
                            print(f"{var_name} 이중 중괄호 치환 완료: '{var_value}'")
                    else:
                        print(f"'{var_name}' 열을 찾을 수 없거나 값이 비어 있습니다.")
                        if var_name.lower() in ['이름', '주문상품', '주문금액', '상품', '금액']:
                            default_value = var_name if var_name.lower() == '이름' else '상품'
                            
                            var_pattern = re.escape(f"{{{var_name}}}")
                            if re.search(var_pattern, template):
                                template = re.sub(var_pattern, default_value, template)
                                print(f"{var_name} 기본값 적용: '{default_value}'")
                            
                            double_var_pattern = re.escape(f"{{{{{var_name}}}}}")
                            if re.search(double_var_pattern, template):
                                template = re.sub(double_var_pattern, default_value, template)
                                print(f"{var_name} 이중 중괄호 기본값 적용: '{default_value}'")
                
                message_text = template
                
                if '{' in message_text and '}' in message_text:
                    import re
                    bracket_pattern = r'{([^{}]+)}'
                    message_text = re.sub(bracket_pattern, r'\1', message_text)
                    if debug_mode:
                        print(f"중괄호 제거 후 메시지: {message_text}")
                
                if len(message_text) > 30:
                    preview = message_text[:30] + "..."
                else:
                    preview = message_text
                print(f"행 {idx+1}: 최종 메시지 생성 (길이: {len(message_text)}자) - {preview}")
            
            # 여기에서 기본 템플릿을 사용하는 경우의 코드를 포함할 수 있습니다
            # (이전 함수에서의 코드와 동일)
            if not message_text or message_text.strip() == '':
                try:
                    temp_msg = sample_template
                    
                    if name_col and name_col in row.index and not pd.isna(row[name_col]):
                        name_value = str(row[name_col])
                        
                    import re
                    name_pattern = re.escape("{{이름}}")
                    if re.search(name_pattern, temp_msg):
                            temp_msg = re.sub(name_pattern, name_value, temp_msg)
                            print(f"이름 치환 완료: '{name_value}'")
                    else:
                        print(f"이름 열을 찾을 수 없거나 값이 비어 있습니다. name_col: {name_col}")
                    
                    if '주문일자' in row.index and not pd.isna(row['주문일자']):
                        order_date = str(row['주문일자'])
                        
                        if ' 00:00:00' in order_date:  # 'YYYY-MM-DD 00:00:00' 형식
                            order_date = order_date.split(' ')[0]
                        elif 'T00:00:00' in order_date:  # 'YYYY-MM-DDT00:00:00' 형식 (ISO 형식)
                            order_date = order_date.split('T')[0]
                        elif '.' in order_date and len(order_date) > 10:  # 'YYYY-MM-DD.000000' 형식
                            order_date = order_date.split('.')[0]
                        
                        try:
                            from pandas import Timestamp
                            if isinstance(row['주문일자'], Timestamp):
                                order_date = row['주문일자'].strftime('%Y-%m-%d')
                        except:
                            pass
                        
                        print(f"주문일자 원본: {str(row['주문일자'])} -> 변환됨: {order_date}")
                        
                        import re
                        date_pattern = re.escape("{{주문일자}}")
                        if re.search(date_pattern, temp_msg):
                            temp_msg = re.sub(date_pattern, order_date, temp_msg)
                            print(f"주문일자 치환 완료: '{order_date}'")
                    else:
                        print(f"주문일자 열을 찾을 수 없거나 값이 비어 있습니다.")
                        
                    import re
                    var_pattern = r'{([^{}]+)}'
                    
                    variables = re.findall(var_pattern, temp_msg)
                    print(f"템플릿에서 발견된 변수: {variables}")
                    
                    # 변수 치환 코드 생략 (기존 코드와 동일)
                    
                    message_text = temp_msg
                    
                    if '{' in message_text and '}' in message_text:
                        import re
                        bracket_pattern = r'{([^{}]+)}'
                        message_text = re.sub(bracket_pattern, r'\1', message_text)
                    
                    if len(message_text) > 30:
                        preview = message_text[:30] + "..."
                    else:
                        preview = message_text
                    print(f"행 {idx+1}: 최종 메시지 생성 (길이: {len(message_text)}자) - {preview}")
                except Exception as e:
                    if name_col and not pd.isna(row[name_col]):
                        message_text = f"안녕하세요 {row[name_col]}님, 메시지가 도착했습니다."
                    else:
                        message_text = "안녕하세요, 메시지가 도착했습니다."
                    print(f"[정보] 행 {idx+1}: 템플릿 처리 오류로 기본 메시지 사용: {str(e)}")
            
            recipient['text'] = message_text
            
            if '제목' in row and not pd.isna(row['제목']):
                recipient['subject'] = str(row['제목'])
            
            # 첨부파일 처리 로직은 생략 (S3에서는 직접 처리가 어려움)
            
            recipients.append(recipient)
            processed_count += 1
        
        print(f"\n총 {df.shape[0]}행 중 {processed_count}개 처리됨, {skipped_count}개 건너뜀")
        
        if has_checkbox:
            print("체크박스 선택된 항목만 처리되었습니다.")
        
        return recipients
    except Exception as e:
        print(f"S3 엑셀 파일 읽기 오류: {str(e)}")
        return message_data

def format_message_for_sms(text):
    """
    문자 메시지에 최적화된 포맷팅을 적용합니다.
    솔라피 메시지 전송 시 줄바꿈과 공백이 유지되도록 처리합니다.
    """
    if not text:
        return text
    
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    text = text.replace('\xa0', ' ')
    text = text.replace(': ', ':').replace(':', ': ')
    while "  " in text: text = text.replace("  ", " ")
    text = text.replace('\n', '\r\n')
    print(f"포맷팅 후 메시지 확인: {repr(text)}")
    return text 