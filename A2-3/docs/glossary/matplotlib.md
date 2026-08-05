# matplotlib

- 용어집 색인: [`README.md`](README.md)
- 대시보드 흐름: [`../data-flow.md`](../data-flow.md#11-dashboard-종합-리포트와-차트-생성)

matplotlib은 Python에서 데이터를 그래프와 차트로 표현하는 시각화 라이브러리다. 데이터 값으로 Figure와 Axes를 구성하고 선, 막대, 텍스트, 범례 등을 그린 뒤 PNG 같은 이미지 파일로 저장할 수 있다.

참고: [matplotlib 공식 빠른 시작 문서](https://matplotlib.org/stable/users/explain/quick_start.html)

## 이 프로젝트에서의 역할

실시간 웹 대시보드 대신 matplotlib으로 다음 정적 PNG 3종을 만든다.

1. 감정 분포
2. 시간별 감정 추이
3. 별점별 감정 분포

matplotlib의 객체 지향 방식으로 `Figure`와 `Axes`를 명시적으로 생성하고, 화면을 띄우지 않는 비대화형 backend에서 파일로 저장한다. 이 방식은 CLI와 자동화 테스트가 GUI 없는 환경에서도 동작하게 한다.

matplotlib은 데이터를 저장하거나 AI 분석을 수행하지 않는다. Output 모듈이 Service에서 계산한 `DashboardData`를 받아 이미지로 표현하는 데만 사용한다. `Figure` 객체는 Output 모듈 밖으로 반환하지 않고 생성된 PNG 경로만 돌려준다.
