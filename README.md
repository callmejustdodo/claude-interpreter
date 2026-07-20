<p align="center">
  <strong>tongyeok 통역</strong>
</p>
<p align="center">
  한국어로 쓰세요. Claude는 영어로 일합니다. 답은 한국어로 돌아옵니다.
</p>
<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/github/license/callmejustdodo/tongyeok?style=flat" alt="License"></a>
</p>

## 설치

### Claude Code

```bash
claude plugin marketplace add callmejustdodo/tongyeok
claude plugin install tongyeok@tongyeok
```

설치 후 `/reload-plugins`. 그다음부터 한국어로 쓰면 됩니다.

끄기: `/plugin` → tongyeok → Disable. 또는 `claude plugin disable tongyeok@tongyeok`.

### Codex

```bash
codex plugin marketplace add callmejustdodo/tongyeok --ref main
codex plugin add tongyeok@tongyeok
```

Codex는 훅을 **신뢰해야 실행**합니다. 설치 후 세션에서 `/hooks`를 열면 `UserPromptSubmit`과 `Stop`이 "need review"로 잡혀 있는데, `t`를 눌러 신뢰하면 활성화됩니다. `config.toml`에 `[features] hooks = true`도 필요합니다.

끄기: `codex plugin remove tongyeok`.

## 무엇을 하나

한국어 프롬프트를 영어로 번역해 대신 제출합니다. 한국어 원문은 모델 컨텍스트에 남지 않습니다. 답변은 한국어로 번역해 보여줍니다.

## 무엇이 달라지나

<table>
<tr>
<td width="50%">

## 그냥 한국어로 쓰면

> 컨텍스트에 한국어가 그대로 들어갑니다.
>
> ```
> ❯ 로그인 버튼이 안 눌려. src/auth.ts 봐줘
> ```
>
> 모델이 보는 것: 한국어 원문
>
> 답변도 한국어 — 편하지만 컨텍스트는 한국어로 채워집니다.

</td>
<td width="50%">

## tongyeok을 쓰면

> 한국어는 지워지고 영어만 들어갑니다.
>
> ```
> ❯ 로그인 버튼이 안 눌려. src/auth.ts 봐줘
>   🌐 blocked → 영어로 재제출
> ❯ The login button doesn't work.
>   Check src/auth.ts.
> ```
>
> 모델이 보는 것: 영어 번역본만
>
> 🌐 한국어 번역: 답변은 다시 한국어로.

</td>
</tr>
</table>

## 어떻게 동작하나

Claude Code 훅에는 프롬프트를 교체하는 API가 없습니다. 대신 **block된 프롬프트는 컨텍스트에서 지워진다**는 동작을 씁니다.

1. UserPromptSubmit 훅이 한글을 감지한다.
2. Haiku(`claude -p`)가 영어로 번역한다.
3. 한국어 프롬프트를 block한다 — 컨텍스트에서 사라진다.
4. 백그라운드 프로세스가 영어 번역문을 입력창에 타이핑하고 제출한다.
5. 재제출된 영어는 훅이 알아보고 통과시킨다.
6. Stop 훅이 영어 답변을 한국어로 번역해 보여준다.

자동 재입력은 환경에 따라 순서대로 시도합니다. cmux → tmux → TIOCSTI → osascript(macOS) → 클립보드 안내.

## 설정

| 변수 | 기본값 | 설명 |
| --- | --- | --- |
| `TONGYEOK_MODE` | `replace` | `replace`: block 후 영어 재입력. `context`: 한국어를 두고 영어 번역을 additionalContext로 첨부 (주입 없음, 대신 한국어가 컨텍스트에 남음) |
| `TONGYEOK_BACKEND` | `auto` | 번역에 쓸 CLI. `auto`는 `claude` 우선, 없으면 `codex` |
| `TONGYEOK_MODEL` | `claude-haiku-4-5-20251001` | 번역 모델 (claude 백엔드 전용) |

세션 하나만 통역 없이 쓰려면 `TONGYEOK_ACTIVE=1 claude`.

## 알아둘 것

1. 슬래시 명령과 영어 프롬프트는 건드리지 않습니다.
2. 번역마다 `claude -p` 호출이라 제출·턴 종료 시 몇 초 걸립니다.
3. 번역 실패 시 fail-open — 한국어가 그대로 전달됩니다. 메시지는 유실되지 않습니다.
4. 답변이 이미 한국어면(한글 30% 초과) 출력 번역은 건너뜁니다.
5. 훅 안의 `claude -p`는 가드 + `disableAllHooks`로 재귀를 막습니다.

**요구사항**: `python3`, 그리고 `claude` 또는 `codex` CLI 중 하나(번역에 씀). 자동 재입력은 cmux/tmux 안이거나 macOS. 그 외 Linux는 최신 커널에서 TIOCSTI가 막혀 있어 tmux를 권합니다.

## 고치기

```bash
git clone https://github.com/callmejustdodo/tongyeok
claude --plugin-dir ./tongyeok
```

`scripts/` 안의 훅을 고치고 `/reload-plugins`.

```
tongyeok/
├── .claude-plugin/        # Claude Code: plugin.json, marketplace.json
├── .codex-plugin/         # Codex: plugin.json
├── .agents/plugins/       # Codex: marketplace.json
├── hooks/hooks.json       # UserPromptSubmit + Stop (양쪽 공용)
└── scripts/
    ├── interpreter_common.py   # 번역, 한글 감지, 세션 상태
    ├── translate_prompt.py     # 한→영, block, 재입력
    ├── inject_input.py         # 입력창 타이핑 (cmux/tmux/TIOCSTI/osascript)
    └── translate_response.py   # 영→한 표시
```

## License

MIT.

한국어로 쓰면서 컨텍스트는 영어로 유지하고 싶었다면 ⭐
