# CopilotKit Integration Notes

## SessionManager patchについて
`copilotkit/patches/ag_ui_strands_patch.py` は、`ag_ui_strands` 側で
`session_manager` が `StrandsAgent` に渡せない問題を暫定的に回避するパッチです。
対象は `ag-ui-protocol/ag-ui` の PR #798 です。

## いつ削除するか
PR #798 がマージされ、利用バージョンに取り込まれたらこのパッチは不要です。
そのタイミングで:
1. `ag_ui_endpoint.py` からパッチ適用呼び出しを削除
2. `copilotkit/patches/ag_ui_strands_patch.py` を削除

## PRステータス確認コマンド
```bash
gh pr view 798 --repo ag-ui-protocol/ag-ui
```
