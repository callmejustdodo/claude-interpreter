# claude-interpreter

Claude Code용 한국어 ↔ 영어 통역 플러그인.

> **English**: A Korean ↔ English interpreter layer for Claude Code. You type in Korean; the prompt is translated to English by Haiku and re-submitted so that **Korean never enters the model context**; Claude works and answers in English; the answer is translated back to Korean and shown at the end of the turn.

- **입력**: 한국어 프롬프트 → Haiku가 영어로 번역 → 영어 프롬프트만 Claude에게 전달 (한국어 원문은 컨텍스트에 남지 않음)
- **출력**: Claude의 영어 답변 → Haiku가 한국어로 번역 → 턴 종료 시 화면에 표시

한국어로 편하게 쓰면서도, 모델 컨텍스트는 영어로만 유지하고 싶을 때 사용한다.

## 데모

실제 세션 화면:

```
❯ 파이썬에서 리스트를 뒤집는 방법을 한 줄로 알려줘

⏺ UserPromptSubmit operation blocked by hook:
  🌐 한국어 프롬프트를 지우고 영어 번역으로 다시 제출합니다:
  Show me how to reverse a list in Python in one line.

❯ Show me how to reverse a list in Python in one line.      ← 자동 재입력

⏺ my_list[::-1] — that's the idiomatic one-liner:
  reversed_list = my_list[::-1]
  ...

  ⎿ Stop says: 🌐 한국어 번역
     `my_list[::-1]` — 이것이 관례적인 한 줄짜리 코드입니다:
     ...
```

## 설치

**방법 1 — 터미널에서 한 줄:**

```bash
claude plugin marketplace add callmejustdodo/claude-interpreter && claude plugin install claude-interpreter@claude-interpreter
```

**방법 2 — 이 프롬프트를 Claude Code에 그대로 붙여넣기:**

```
claude-interpreter 플러그인을 설치해줘.
`claude plugin marketplace add callmejustdodo/claude-interpreter` 와
`claude plugin install claude-interpreter@claude-interpreter` 를 실행하고,
끝나면 나한테 /reload-plugins 를 실행하라고 안내해줘.
```

**방법 3 — 슬래시 명령으로 직접:**

```
/plugin marketplace add callmejustdodo/claude-interpreter
/plugin install claude-interpreter@claude-interpreter
```

어느 방법이든 설치 후 `/reload-plugins`(또는 새 세션)부터 적용된다.
업데이트는 `/plugin marketplace update claude-interpreter`.

**요구사항**: `python3`, `claude` CLI. 자동 재입력은 cmux/tmux 안이거나 macOS(osascript)여야 한다. 그 외 Linux 환경은 최신 커널에서 TIOCSTI가 기본 비활성이라 tmux 사용을 권장한다.

### 제거

```
/plugin uninstall claude-interpreter@claude-interpreter
/plugin marketplace remove claude-interpreter
```

### 로컬 개발

```bash
claude --plugin-dir /path/to/claude-interpreter
```

플러그인 파일 수정 후에는 세션 안에서 `/reload-plugins`.

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

1. **cmux** — cmux CLI의 `send`/`send-key`로 호출자 workspace에 직접 입력
2. **tmux** — `paste-buffer`(bracketed paste) + Enter
3. **TIOCSTI** — `/dev/tty`에 키 입력 주입 (controlling tty가 있는 환경)
4. **osascript** — macOS System Events로 클립보드 자동 붙여넣기 + Enter (클립보드는 원래 내용으로 복원, 접근성 권한 필요)
5. **클립보드 폴백** — 위가 모두 불가능하면 번역문을 클립보드에 복사하고 안내 메시지 표시

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
├── .claude-plugin/
│   ├── plugin.json                 # 플러그인 매니페스트
│   └── marketplace.json            # 단일 리포 마켓플레이스 (source: "./")
├── hooks/hooks.json                # UserPromptSubmit + Stop 훅 등록
└── scripts/
    ├── interpreter_common.py       # 번역(claude -p), 한글 감지, 세션 상태
    ├── translate_prompt.py         # 입력: 한→영 번역 + block + 재입력
    ├── inject_input.py             # 입력창 자동 타이핑 (tmux / TIOCSTI)
    └── translate_response.py       # 출력: 영→한 번역 표시
```
