#!/bin/bash

# パラメータの範囲を定義
CMD="${1}"
START=25
STEP=3
END=38

# min_qp_iのループ
for min_qp_i in $(seq ${START} 1 ${END}); do
  # min_qp_pのループ
  for min_qp_p in $(seq ${START} ${STEP} ${END}); do
    # min_qp_bのループ
    for min_qp_b in $(seq ${START} ${STEP} ${END}); do
      # パターンを出力
      echo "${CMD} -min_qp_i ${min_qp_i} -min_qp_p ${min_qp_p} -min_qp_b ${min_qp_b}"
    done
  done
done
