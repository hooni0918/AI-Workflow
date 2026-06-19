# 프로젝트 기여 가이드

이 문서는 AI-Workflow 프로젝트에 문서를 추가하거나 수정할 때 따라야 할 규칙을 정의합니다.

동시에, `meta/` 폴더 안에 들어있는 모든 문서의 최상위 문서입니다.

---

## 로컬 환경 세팅

배포·hook 인프라는 Python으로 포팅되어 있어 Node 의존성이 없습니다. `make` 타겟으로 설치합니다.

```bash
git clone https://github.com/hooni0918/AI-Workflow.git
cd AI-Workflow
make install-hooks
make sync-system
make sync-local-system
```

수정 후 전역 에이전트 자산만 반영하려면 `make sync-system`을 다시 실행합니다. 전체 설치 흐름은 [Installation Guide](meta/INSTALLATION_GUIDE.md)를 따릅니다.

---

## 디렉터리 구조와 역할

| 디렉터리 | 역할 | 배포 여부 |
|-----------|------|-----------|
| `deploy/rules/` | 전역 AI 행동 규칙 | 배포됨 |
| `deploy/skills/` | 스킬 정의 (code-review, discussion, pre-exit) | 배포됨 |
| `deploy/contexts/` | 보조 참조 문서 (테스트 전략 가정 등) | 배포됨 |
| `deploy/hooks/` | 정책 hook | 배포됨 |
| `local/skills/` | 이 레포 로컬 스킬 (scw 등) | 로컬 배포 |
| `meta/` | 프로젝트 관리 문서 (설치 가이드, 동기화 가이드) | 배포 안 됨 |
| `scripts/` | 배포/제거 Python 스크립트 | 배포 안 됨 |

---

## 스킬 추가 규칙

새 스킬을 추가할 때는 아래 구조를 따릅니다.

```
deploy/skills/<스킬명>/
├── SKILL.md        # 필수. AI가 로드하는 스킬 정의
├── README.md       # 필수. 사람용 설명 (AI 지시 금지)
└── ...             # SKILL.md에서 참조하는 보조 파일
```

`SKILL.md`에는 YAML frontmatter가 필요합니다.

```yaml
---
name: 스킬명
description: 스킬에 대한 한 줄 설명
argument-hint: 인자 힌트 (선택)
---
```

---

## 핵심 원칙

### 미정리 메모는 가장 가까운 TODO.md에

가이드 문서 본문에 "미정리", "TBD", "TODO" 같은 미해결 메모를 남기지 마세요. AI가 해당 규칙을 적용할 때 판단할 수 없습니다.

미해결 사항은 해당 문서와 가장 가까운 경로의 `TODO.md`에 적으세요.

```
contexts/
├── TODO.md                 ← contexts 하위 문서의 미결 사항은 여기에
└── testing-strategy/
    └── assumptions.md
```

---

## 문서 작성 규칙

- md 파일을 작성하거나 수정할 때, 한 문장이 한 가지 역할(규칙·사례·트리거)만 담도록 분리합니다.
- 진입점·인덱스 문서에서 다른 문서를 가리킬 때는 **트리거**(언제 보는가)만 적고 본문 요약은 적지 않습니다 (`deploy/rules/global.md` 「참조 문서 진입점 작성」 참고).
- 미확정 전제(테스트·CI·스냅샷·SwiftLint 설정 등)는 본문에 단정하지 않고 "가정" 라벨로 표기합니다. 테스트 관련 가정의 단일 출처는 [testing-strategy/assumptions.md](deploy/contexts/testing-strategy/assumptions.md)입니다.
