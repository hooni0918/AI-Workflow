# Installation Guide

이 문서는 이 레포를 새 머신이나 새 작업 환경(Claude/Codex/Gemini 런타임)에 맞출 때의 진입점입니다. 상세 동작은 `meta/guides/` 하위에서 대상별로 관리합니다.

배포·hook 인프라는 Python으로 포팅되어 있어 Node 의존성이 없습니다. 모든 명령은 `Makefile` 타겟이며, 내부적으로 `python3 scripts/*.py`를 호출합니다.

## 새 머신 초기화

```bash
make install-hooks
make sync-environment
make sync-system
make sync-local-system
```

`make install-hooks`는 git `commit-msg` hook을 `scripts/commit_msg.py`에 연결합니다.

## 평소 갱신

전역 에이전트 규칙·스킬·hook을 갱신할 때는 시스템 자산만 다시 동기화합니다.

```bash
make sync-system
```

프로젝트 로컬 산출물(로컬 스킬 + settings/hooks)까지 맞출 때는 로컬 시스템 동기화를 함께 실행합니다.

```bash
make sync-local-system
```

## 제거

각 동기화 명령에는 대응 제거 명령이 있습니다. 제거 명령은 이 레포가 만든 산출물만 제거해야 합니다.

```bash
make unsync-environment
make unsync-system
make unsync-local-system
make uninstall-hooks
```

## 상세 가이드

- [가이드 인덱스](guides/index.md)
- [환경 동기화](guides/environment.md)
- [시스템 자산 동기화](guides/system.md)
- [로컬 시스템 동기화](guides/local-system.md)
