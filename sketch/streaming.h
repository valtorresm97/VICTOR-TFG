// streaming.h
#pragma once
#include <Arduino.h>
#include <Arduino_RouterBridge.h>
#include <ADS1299Plus.h>
#include "bench.h"

constexpr uint8_t  BLOCK_SAMPLES     = 8;
constexpr uint16_t TX_BLOCK_RING_CAP = 32;

struct EegBlockUV {
  uint32_t block_idx;
  uint32_t first_sample_idx;
  uint8_t  sample_count;

  uint32_t status[BLOCK_SAMPLES];
  int32_t  ch_uV[BLOCK_SAMPLES][ADS1299Plus::NUM_CHANNELS];
};

struct TxBlockRing {
  EegBlockUV fill_block{};
  uint32_t   next_block_idx = 0;

  EegBlockUV ring[TX_BLOCK_RING_CAP]{};
  volatile uint16_t head  = 0;
  volatile uint16_t tail  = 0;
  volatile uint16_t count = 0;

  void resetFillBlock() {
    fill_block.block_idx        = next_block_idx++;
    fill_block.first_sample_idx = 0;
    fill_block.sample_count     = 0;
  }

  void resetRing() {
    head = 0;
    tail = 0;
    count = 0;
  }

  void resetStreamingState() {
    resetFillBlock();
    resetRing();
  }

  bool enqueueCompletedBlock(const EegBlockUV &blk, BenchStats &bench) {
    if (count >= TX_BLOCK_RING_CAP) {
      bench.tx_queue_drops_total++;
      bench.tx_queue_drops_window++;
      return false;
    }

    ring[head] = blk;
    head = (uint16_t)((head + 1) % TX_BLOCK_RING_CAP);
    count++;

    bench.blocks_enqueued_total++;
    bench.blocks_enqueued_window++;

    if (count > bench.tx_queue_max_global) {
      bench.tx_queue_max_global = count;
    }
    if (count > bench.tx_queue_max_window) {
      bench.tx_queue_max_window = count;
    }

    return true;
  }

  void appendSampleToFillBlock(uint32_t idx,
                               uint32_t status,
                               const int32_t ch_uV[ADS1299Plus::NUM_CHANNELS],
                               BenchStats &bench) {
    if (fill_block.sample_count == 0) {
      fill_block.first_sample_idx = idx;
    }

    const uint8_t pos = fill_block.sample_count;

    fill_block.status[pos] = status;
    for (int i = 0; i < ADS1299Plus::NUM_CHANNELS; ++i) {
      fill_block.ch_uV[pos][i] = ch_uV[i];
    }

    fill_block.sample_count++;

    if (fill_block.sample_count >= BLOCK_SAMPLES) {
      enqueueCompletedBlock(fill_block, bench);
      resetFillBlock();
    }
  }

  uint16_t publishPendingBlocks(BenchStats &bench, uint16_t max_blocks_to_send = 4) {
    uint16_t sent_blocks_now = 0;

    while (count > 0 && sent_blocks_now < max_blocks_to_send) {
      EegBlockUV &b = ring[tail];

      const uint32_t notify_start_us = micros();

      Bridge.notify(
        "eeg_block_uV",
        b.block_idx,
        b.first_sample_idx,
        b.sample_count,

        b.status[0], b.ch_uV[0][0], b.ch_uV[0][1], b.ch_uV[0][2], b.ch_uV[0][3],
        b.status[1], b.ch_uV[1][0], b.ch_uV[1][1], b.ch_uV[1][2], b.ch_uV[1][3],
        b.status[2], b.ch_uV[2][0], b.ch_uV[2][1], b.ch_uV[2][2], b.ch_uV[2][3],
        b.status[3], b.ch_uV[3][0], b.ch_uV[3][1], b.ch_uV[3][2], b.ch_uV[3][3],
        b.status[4], b.ch_uV[4][0], b.ch_uV[4][1], b.ch_uV[4][2], b.ch_uV[4][3],
        b.status[5], b.ch_uV[5][0], b.ch_uV[5][1], b.ch_uV[5][2], b.ch_uV[5][3],
        b.status[6], b.ch_uV[6][0], b.ch_uV[6][1], b.ch_uV[6][2], b.ch_uV[6][3],
        b.status[7], b.ch_uV[7][0], b.ch_uV[7][1], b.ch_uV[7][2], b.ch_uV[7][3]
      );

      const uint32_t notify_dt_us = micros() - notify_start_us;

      bench.notify_calls_total++;
      bench.notify_calls_window++;

      bench.blocks_sent_total++;
      bench.blocks_sent_window++;

      bench.samples_sent_total += b.sample_count;
      bench.samples_sent_window += b.sample_count;

      bench.notify_time_us_accum_total += notify_dt_us;
      bench.notify_time_us_accum_window += notify_dt_us;

      if (notify_dt_us > bench.notify_time_us_max_global) {
        bench.notify_time_us_max_global = notify_dt_us;
      }
      if (notify_dt_us > bench.notify_time_us_max_window) {
        bench.notify_time_us_max_window = notify_dt_us;
      }

      tail = (uint16_t)((tail + 1) % TX_BLOCK_RING_CAP);
      count--;
      sent_blocks_now++;
    }

    if (sent_blocks_now > bench.tx_publish_bursts_max_global) {
      bench.tx_publish_bursts_max_global = sent_blocks_now;
    }
    if (sent_blocks_now > bench.tx_publish_bursts_max_window) {
      bench.tx_publish_bursts_max_window = sent_blocks_now;
    }

    return sent_blocks_now;
  }
};