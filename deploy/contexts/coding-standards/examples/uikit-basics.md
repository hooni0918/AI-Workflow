> **예시 (참고용).** UIKit을 쓰는 프로젝트의 예시다. 마스터 표준이 아니며, 네 프로젝트의 .claude/docs에 네 것으로 정의해 대체하라.

# UIKit 작성 규칙 (예시)

UI는 `UIViewController` 서브클래스 + 코드 기반 AutoLayout으로 짠다. 스토리보드·xib는 쓰지 않는다.

## 화면은 UIViewController 서브클래스로

한 화면은 `UIViewController`를 상속한 코드 정의 타입으로 만든다. 스토리보드·xib 인스턴스화 경로(`@IBOutlet`/`@IBAction`/`UIStoryboard`)는 쓰지 않는다 — 화면 구성·연결을 코드 한곳에서 읽히게 하기 위함이다.

- 뷰 계층은 `loadView()` 또는 `viewDidLoad()`에서 코드로 조립한다. 생명주기 콜백(`viewDidLoad`/`viewWillAppear` 등)에는 그 시점에 꼭 필요한 일만 둔다.
- 화면 네이밍은 `<도메인>ViewController`다. 접미사 규칙의 단일 출처는 프로젝트의 `.claude/docs`(네이밍 정의)다 — 여기서 다시 단정하지 않는다.

## 레이아웃은 코드 NSLayoutConstraint AutoLayout

레이아웃은 코드로 작성한 AutoLayout 제약으로 잡는다.

- 뷰를 코드로 추가하면 `translatesAutoresizingMaskIntoConstraints = false`를 먼저 끈다. 켠 채로 제약을 걸면 제약 충돌이 런타임에 터진다.
- 제약은 `NSLayoutConstraint.activate([...])`로 한 번에 활성화한다. 제약 객체를 따로 들고 있어야 하는 경우(런타임 갱신)에만 프로퍼티로 보관한다.
- 프레임 기반 수동 레이아웃(`frame`/`autoresizingMask` 직접 계산)으로 화면을 짜지 않는다 — AutoLayout과 섞이면 어느 쪽이 최종 위치를 정하는지 추적이 끊긴다.

## DesignSystem 토큰을 쓴다

색·타이포·간격 같은 시각 값은 화면에서 리터럴로 박지 않고 DesignSystem 모듈의 토큰을 쓴다.

- 색은 `AppColors`, 타이포는 `AppTypography` 같은 `App` 접두 enum 토큰을 통해 받는다. 화면 코드에 `UIColor(red:...)`·`UIFont.systemFont(...)` 리터럴을 직접 두지 않는다.
- 반복되는 UI 요소는 역할명 컴포넌트(예: `TitleLabel`)로 DesignSystem에 둔 것을 재사용한다. 같은 모양을 화면마다 다시 조립하지 않는다.
- DesignSystem이 어느 레이어에 있고 누가 그것을 import할 수 있는지는 프로젝트의 `.claude/docs`(레이어 규칙)가 단일 출처다.

## 화면 상태는 VC가 UseCase를 직접 호출

화면 동작은 `UIViewController`가 Domain의 UseCase를 직접 호출해 처리한다. UI와 도메인 사이에 전용 상태 컨테이너(ViewModel/Store/Reducer 등)를 두지 않는 예시다.

- VC는 주입받은 UseCase의 `execute(...)`를 호출하고, 그 결과로 자기 뷰를 갱신한다. UseCase는 생성자 주입으로 받는다 — DI 방식의 단일 출처는 프로젝트의 `.claude/docs`(레이어 규칙)다.
- VC가 UseCase가 할 일(도메인 규칙·데이터 변환)을 대신 하지 않는다. VC는 입력을 UseCase로 넘기고 출력을 화면에 반영하는 데까지만 책임진다.
- 전용 상태 패턴(ViewModel 도입 여부·형태)은 프로젝트마다 다르다. 도입하는 프로젝트라면 그 규칙을 네 `.claude/docs`에 정의해 따른다.

## 비동기는 async/await

비동기 작업은 `async/await`로 표현하고, 동기 컨텍스트(생명주기 콜백 등)에서 진입할 때만 `Task`로 감싼다. Combine은 쓰지 않는 예시다.

- UseCase 호출이 `async`면 `Task { ... }` 안에서 `await`한다. 화면 갱신은 메인 액터에서 일어나도록 둔다.
- `Task`의 생명주기를 화면 생명주기와 맞춘다 — 화면이 사라질 때 더 살아 있으면 안 되는 작업은 보관한 `Task`를 `cancel()`하거나 구조적 동시성으로 범위를 묶는다.
- Combine(`Publisher`/`@Published`/`sink`)으로 비동기 흐름을 구성하지 않는다. 이벤트 스트림이 필요하면 `AsyncSequence`를 검토한다.
- Swift 6 strict concurrency 강제 조건은 프로젝트의 `.claude/docs`(동시성 전제)가 단일 출처다 — 여기서 다시 단정하지 않는다.
