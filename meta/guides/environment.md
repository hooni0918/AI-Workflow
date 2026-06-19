# Environment Sync

현재 머신의 사용자 환경을 이 레포 기준으로 맞춥니다.

```bash
make sync-environment
```

## 수행 작업

- Windows에서 PowerShell 7 존재 여부를 확인하고, 없으면 `winget`으로 `Microsoft.PowerShell`을 설치합니다.
- Windows PowerShell과 PowerShell 7의 실제 `$PROFILE` 경로를 확인해 UTF-8 설정 block을 삽입 또는 갱신합니다.
- `~/.gitignore_global`에 관리 block으로 무시 패턴을 추가합니다.
- `core.excludesFile`이 비어 있으면 `~/.gitignore_global`을 등록합니다.
- 이 레포가 설치하거나 등록한 상태는 상태 파일에 기록합니다.

## 제거

```bash
make unsync-environment
```

제거 명령은 이 레포가 넣은 marker block만 제거합니다. PowerShell 7은 `sync-environment`가 직접 설치했다고 상태 파일에 기록된 경우에만 제거를 시도합니다.

## 반복 실행 기준

`sync-environment`는 여러 번 실행해도 PowerShell profile block이나 global gitignore pattern을 중복 추가하지 않아야 합니다. 같은 값으로 수렴하며 중복 등록하지 않습니다.

## 새 머신 기준

새 머신에서는 git hook 설치 후 가장 먼저 실행합니다.

```bash
make install-hooks
make sync-environment
```

이 명령은 사용자 환경을 바꾸므로 `unsync-environment`가 되돌릴 수 있는 대상과 되돌리지 않을 대상을 가이드에 함께 기록해야 합니다.
