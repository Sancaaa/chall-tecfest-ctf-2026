#!/usr/bin/env bash
# uji ketahanan solver di banyak seed
cd "$(dirname "$0")" || exit 1
SAGE=~/miniforge3/envs/sage/bin/sage
pass=0; fail=0
for S in 1 2 3 4 5 6 7 8; do
  "$SAGE" gen.sage "$S" >/dev/null 2>&1
  out=$("$SAGE" solve.sage 2>/dev/null)
  if echo "$out" | grep -q "FLAG ="; then
    bs=$(echo "$out" | grep -o "block_size=[0-9]*")
    echo "seed $S: OK ($bs)"; pass=$((pass+1))
  else
    echo "seed $S: FAIL"; fail=$((fail+1))
  fi
done
echo "=== pass=$pass fail=$fail ==="
