# 기업 뉴스 모니터 (매시간 자동 정리, 무료)

60개 기업의 뉴스를 매시간 모아 '최근 이슈 3가지'를 정리하고, 새 소식이 거의 없으면 이전 내용을 그대로 유지합니다.
AI나 API 키는 쓰지 않아서 결제가 필요 없습니다.

## 파일 설명
- `index.html` : 앱 화면
- `briefs.json` : 정리 결과 (자동으로 갱신됨)
- `companies.json` : 기업 목록과 검색어
- `update_briefs.py` : 뉴스 수집 + 이슈 정리 스크립트
- `.github/workflows/update.yml` : 매시간 자동 실행 설정

## 설치 순서
1. GitHub 저장소(Public)를 만들고, 이 폴더 **안의 파일들**을 저장소 맨 앞(루트)에 올립니다. 폴더째 올리면 안 됩니다.
   - 저장소 첫 화면에 `index.html`과 `.github` 폴더가 바로 보여야 합니다.
   - `.github`가 안 올라가면 `Add file` → `Create new file`에서 이름칸에 `.github/workflows/update.yml`을 입력하고 내용을 붙여 넣으세요.
2. `Settings` → `Pages` → Branch를 `main`, 폴더를 `/ (root)`로 선택하고 `Save`.
3. `Actions` 탭 → `update-briefs` → `Run workflow`. 1~3분 뒤 초록 체크가 뜨면 성공입니다.
4. `https://내아이디.github.io/저장소이름/` 주소로 접속합니다. 휴대폰에서는 `홈 화면에 추가`를 누르면 앱처럼 쓸 수 있어요.

API 키나 Secret 설정은 필요 없습니다.

## 조절하는 값 (`update.yml`의 env)
- `MIN_NEW` : 새 기사가 이 개수 이상일 때만 다시 정리합니다. 올리면 덜 자주 바뀝니다.
- `WINDOW` : 뉴스 검색 기간 (`1d`, `3d`, `7d`).

## 알아둘 점
- GitHub 예약 실행은 정시에 안 돌고 몇 분~수십 분 밀릴 수 있습니다.
- 저장소에 60일 동안 활동이 없으면 예약 실행이 멈출 수 있어요. 멈추면 `Actions` 탭에서 다시 켜 주세요.
- 이슈 정리는 기사 제목의 겹치는 단어를 기준으로 묶는 방식이라, 문장으로 요약해 주지는 않고 대표 기사 제목이 나옵니다. 정확하지 않을 수 있으니 중요한 내용은 원문을 확인하세요.
- 기업을 바꾸려면 `companies.json`과 `index.html` 안의 기업 목록(`GROUPS`)을 같이 고쳐야 합니다.
