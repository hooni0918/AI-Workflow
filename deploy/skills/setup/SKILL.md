---
name: setup
description: iOS 워크플로우가 필요한 로컬 환경을 한 번에 점검하고 빠진 것을 설치한다. 새 팀원 온보딩, "환경 세팅", "setup", "왜 QA가 안 돌아?", axe·시뮬레이터·빌드 도구 문제 진단에 사용한다.
argument-hint: "[--check-only]"
---

# 환경 세팅

워크플로우가 기대하는 로컬 도구를 점검하고, 빠진 것만 설치한다. **점검은 전부 실행해서 확인한다** — "있을 것이다"로 넘기지 않는다.

`--check-only`가 주어지면 설치를 제안하지 않고 리포트만 낸다.

## 절차

### 1. 프로젝트 프로필 먼저 읽기

`.claude/docs/project-profile.md`가 있으면 먼저 읽는다. **프로필이 "미도입"으로 선언한 도구는 점검 대상에서 빼고, 그 사실을 리포트에 한 줄로 남긴다.** 프로필의 결정을 이 스킬이 뒤집지 않는다.

프로필이 없으면 아래 전체를 점검하고, 없는 항목은 "프로젝트가 쓰는지 불명"으로 표시한다.

### 2. 점검

| 항목 | 명령 | 없을 때 | 성격 |
|---|---|---|---|
| Xcode 커맨드라인 | `which xcodebuild` | Xcode 설치 안내 | **게이트** — 없으면 빌드·테스트 전부 불가 |
| 시뮬레이터 | `xcrun simctl list devices booted` | 부팅 안내 (`xcrun simctl boot <UDID>`) | 소프트 — 부팅만 하면 됨 |
| `axe` | `which axe` | 3번 설치 절차 | 소프트 — 없으면 AXe UI 자동화만 멈춘다 |
| Homebrew | `which brew` | https://brew.sh 안내 후 axe 설치 단계 건너뜀 | axe 설치의 전제 |
| SwiftLint | `which swiftlint` | 프로필이 도입을 선언한 경우에만 설치 안내 | 프로필 종속 |
| 플러그인 | 스킬 목록에 `ai-workflow:` 접두사 스킬 존재 | `/plugin marketplace add hooni0918/AI-Workflow` → `/plugin install ai-workflow@hooni-workflow` | — |

시뮬레이터는 이름이 아니라 **UDID**로 다룬다 — 동명 기기가 중복될 수 있다.

### 3. axe 설치 (없을 때만)

```sh
brew install cameroncooke/axe/axe
```

- 설치 **전에 사용자에게 알리고 승인을 받는다.** 임의로 실행하지 않는다
- `--check-only`면 명령만 보여주고 실행하지 않는다
- 설치 후 `axe --version`으로 검증한다. 검증 실패면 실패 사실을 그대로 보고한다 — "설치됐을 것"으로 끝내지 않는다
- brew가 없으면 이 단계를 건너뛰고 리포트에 사유를 남긴다

`axe`가 무엇을 할 수 있는지·명령 형태는 [axe](../axe/SKILL.md) 스킬이 단일 출처다.

### 4. 리포트

항목별 ✔/✘/─(건너뜀)와 **남은 수동 조치만** 출력한다. 이미 갖춰진 항목을 설명하지 않는다.

```
✔ xcodebuild        /usr/bin/xcodebuild
✔ 시뮬레이터        iPhone 17 Pro (0915508D-…) booted
✘ axe               미설치 → brew install cameroncooke/axe/axe 실행할까요?
✔ 플러그인          ai-workflow 활성
─ SwiftLint         프로필에 미도입으로 선언됨 (점검 건너뜀)

남은 조치: axe 설치 승인
```

전부 ✔이면 `환경 준비 완료. /mino 로 시작하세요.` 한 줄로 끝낸다.

## 하지 않는 것

- **프로필이 미도입으로 정한 도구를 설치 제안하지 않는다** — SwiftLint 미도입은 결정이지 결함이 아니다
- 승인 없이 설치 명령 실행
- 점검 결과를 추측으로 채우기 — 명령이 실패하면 실패한 사실을 적는다
- 시뮬레이터 자동 부팅 — 어느 기기를 쓸지는 사용자가 정한다
