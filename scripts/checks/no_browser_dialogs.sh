#!/usr/bin/env bash
# Запрет системных диалогов браузера (скилл frontend).
# Ловит hx-confirm, window.alert/confirm/prompt и голые alert(/prompt(.
# Голый confirm( не ловим: так могут называться методы Alpine-компонентов.
set -euo pipefail
pattern='hx-confirm|window\.(alert|confirm|prompt)\s*\(|(^|[^.[:alnum:]_])(alert|prompt)\s*\('
files=("$@")
[ ${#files[@]} -eq 0 ] && exit 0
if grep -nHE "$pattern" "${files[@]}"; then
  echo "Системные диалоги браузера запрещены: используйте своё окно (confirm_dialog) или тост (window.toast)." >&2
  exit 1
fi
