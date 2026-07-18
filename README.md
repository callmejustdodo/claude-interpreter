# claude-interpreter

Claude Code용 한국어 ↔ 영어 통역 플러그인.

- **입력**: 한국어 프롬프트 → Haiku가 영어로 번역 → 영어 프롬프트만 Claude에게 전달 (한국어 원문은 컨텍스트에 남지 않음)
- **출력**: Claude의 영어 답변 → Haiku가 한국어로 번역 → 턴 종료 시 화면에 표시

## 동작 방식

Claude Code 훅에는 프롬프트를 "교체"하는 API가 없다. 대신 UserPromptSubmit 훅에서
프롬프트를 **block하면 컨텍스트에서 완전히 지워진다**는 동작을 이용한다.

```
사용자가 한국어 입력
  └─ UserPromptSubmit 훅
       ├─ Haiku(claude -p)로 영어 번역
       ├─ 한국어 프롬프트 block (컨텍스트에서 삭제)
       └─ 백그라운드 프로세스가 영어 번역문을 입력창에 자동 타이핑 + 제출
            └─ 재제출된 영어 프롬프트는 훅이 알아보고 그대로 통과
Claude가 영어로 작업/답변
  └─ Stop 훅
       └─ 마지막 답변이 영어면 Haiku로 한국어 번역 → systemMessage로 표시
```

자동 재입력은 환경에 따라 순서대로 시도한다:

1. **tmux** — `paste-buffer`(bracketed paste) + Enter
2. **TIOCSTI** — `/dev/tty`에 키 입력 주입 (macOS 지원)
3. **클립보드 폴백** — 자동 입력이 불가능하면 번역문을 클립보드에 복사하고 안내 메시지 표시

## 설치

Claude Code 세션 안에서:

```
/plugin marketplace add callmejustdodo/claude-interpreter
/plugin install claude-interpreter@claude-interpreter
```

업데이트는 `/plugin marketplace update claude-interpreter`.

**요구사항**: `python3`, `claude` CLI. 자동 재입력은 tmux 안이거나 TIOCSTI를 지원하는 tty(macOS)가 필요하다. 최신 Linux 커널은 TIOCSTI가 기본 비활성이라 tmux 사용을 권장하며, 클립보드 폴백(`pbcopy`)은 macOS 전용이다.

### 로컬 개발

```bash
claude --plugin-dir /path/to/claude-interpreter
```

플러그인 파일 수정 후에는 세션 안에서 `/reload-plugins`.

## 설정 (환경변수)

| 변수 | 기본값 | 설명 |
| --- | --- | --- |
| `CLAUDE_INTERPRETER_MODE` | `replace` | `replace`: block + 영어 재입력(한국어가 컨텍스트에 안 남음). `context`: 한국어 프롬프트를 유지하고 영어 번역을 additionalContext로 주입(주입 해킹 없음, 대신 한국어가 컨텍스트에 남음) |
| `CLAUDE_INTERPRETER_MODEL` | `claude-haiku-4-5-20251001` | 번역에 사용할 모델 |

## 알아둘 것

- `/`로 시작하는 슬래시 명령과 영어 프롬프트는 건드리지 않는다.
- 번역은 `claude -p`(Haiku) 호출이라 프롬프트 제출/턴 종료 시 몇 초의 지연이 생긴다.
- 번역 실패 시 fail-open: 한국어 프롬프트가 그대로 전달된다 (Claude는 한국어도 이해하므로 메시지 유실보다 낫다).
- 답변이 이미 한국어(한글 비율 30% 초과)면 출력 번역은 생략된다.
- 훅 안에서 부르는 `claude -p`는 `CLAUDE_INTERPRETER_ACTIVE=1` 가드 + `disableAllHooks` 설정으로 재귀를 차단한다.
- 세션 상태는 `$TMPDIR/claude-interpreter/<session_id>.*` 파일로 관리된다.

## 구조

```
claude-interpreter/
├── .claude-plugin/plugin.json      # 플러그인 매니페스트
├── hooks/hooks.json                # UserPromptSubmit + Stop 훅 등록
└── scripts/
    ├── interpreter_common.py       # 번역(claude -p), 한글 감지, 세션 상태
    ├── translate_prompt.py         # 입력: 한→영 번역 + block + 재입력
    ├── inject_input.py             # 입력창 자동 타이핑 (tmux / TIOCSTI)
    └── translate_response.py       # 출력: 영→한 번역 표시
```
