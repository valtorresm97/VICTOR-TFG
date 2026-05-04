// bench.h
#pragma once
#include <Arduino.h>

struct BenchStats {
  // Totales desde arranque
  uint32_t samples_generated_total = 0;
  uint32_t samples_sent_total      = 0;

  uint32_t blocks_enqueued_total = 0;
  uint32_t blocks_sent_total     = 0;

  uint32_t notify_calls_total = 0;

  uint64_t filter_time_us_accum_total = 0;
  uint64_t notify_time_us_accum_total = 0;

  uint32_t filter_time_us_max_global      = 0;
  uint32_t notify_time_us_max_global      = 0;
  uint32_t sample_iter_time_us_max_global = 0;
  uint32_t loop_time_us_max_global        = 0;

  uint32_t synthetic_lag_events_total         = 0;
  uint32_t synthetic_catchup_iters_max_global = 0;

  uint32_t tx_queue_max_global          = 0;
  uint32_t tx_queue_drops_total         = 0;
  uint32_t tx_publish_bursts_max_global = 0;

  // Ventana actual
  uint32_t report_last_ms = 0;

  uint32_t samples_generated_window = 0;
  uint32_t samples_sent_window      = 0;

  uint32_t blocks_enqueued_window = 0;
  uint32_t blocks_sent_window     = 0;

  uint32_t notify_calls_window = 0;

  uint64_t filter_time_us_accum_window = 0;
  uint64_t notify_time_us_accum_window = 0;

  uint32_t filter_time_us_max_window      = 0;
  uint32_t notify_time_us_max_window      = 0;
  uint32_t sample_iter_time_us_max_window = 0;
  uint32_t loop_time_us_max_window        = 0;

  uint32_t lag_events_window                  = 0;
  uint32_t synthetic_catchup_iters_max_window = 0;

  uint32_t tx_queue_max_window          = 0;
  uint32_t tx_queue_drops_window        = 0;
  uint32_t tx_publish_bursts_max_window = 0;
};