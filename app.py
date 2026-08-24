📊 충청호남팀 영업사원 주차별 VDT 목표 관리 (8월)
🚨
데이터 구성 중 에러가 발생했습니다!

🛠️ 상세 에러 보기

Traceback (most recent call last):
  File "/mount/src/monthmanagement/app.py", line 208, in load_vdt_data
    all_targets = target_ws.get_all_values()
  File "/home/adminuser/venv/lib/python3.14/site-packages/gspread/worksheet.py", line 486, in get_all_values
    return self.get_values(
           ~~~~~~~~~~~~~~~^
        range_name=range_name,
        ^^^^^^^^^^^^^^^^^^^^^^
    ...<6 lines>...
        return_type=return_type,
        ^^^^^^^^^^^^^^^^^^^^^^^^
    )
    ^
  File "/home/adminuser/venv/lib/python3.14/site-packages/gspread/worksheet.py", line 463, in get_values
    return self.get(
           ~~~~~~~~^
        range_name=range_name,
        ^^^^^^^^^^^^^^^^^^^^^^
    ...<6 lines>...
        return_type=return_type,
        ^^^^^^^^^^^^^^^^^^^^^^^^
    )
    ^
  File "/home/adminuser/venv/lib/python3.14/site-packages/gspread/worksheet.py", line 958, in get
    response = self.client.values_get(
        self.spreadsheet_id, get_range_name, params=params
    )
  File "/home/adminuser/venv/lib/python3.14/site-packages/gspread/http_client.py", line 236, in values_get
    r = self.request("get", url, params=params)
  File "/home/adminuser/venv/lib/python3.14/site-packages/gspread/http_client.py", line 128, in request
    raise APIError(response)
gspread.exceptions.APIError: APIError: [429]: Quota exceeded for quota metric 'Read requests' and limit 'Read requests per minute per user' of service 'sheets.googleapis.com' for consumer 'project_number:523839461594'.
