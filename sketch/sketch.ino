// sketch.ino
#include <Arduino.h>
#include <SPI.h>
#include <math.h>

#include <ADS1299Plus.h>
#include <ADS1299_SafeSPI.h>

#include "filters.h"
#include "bench.h"
#include "streaming.h"

// UNO Q: comunicación MCU<->MPU (Qualcomm) vía Bridge (MsgPack RPC) + Monitor
#include <Arduino_RouterBridge.h>

#ifndef LED_MATRIX_ENABLED
#define LED_MATRIX_ENABLED 0
#endif

#if LED_MATRIX_ENABLED
#include <Arduino_LED_Matrix.h>
Arduino_LED_Matrix ledMatrix;
#endif

// Prueba sintética
#define USE_SYNTHETIC 0
#include "synthetic.h"

// ---------------------------
// Pines (ajusta a tu wiring)
// ---------------------------
static constexpr uint8_t PIN_CS    = D10;
static constexpr uint8_t PIN_SCLK  = SCK;
static constexpr uint8_t PIN_MOSI  = MOSI;
static constexpr uint8_t PIN_MISO  = MISO;
static constexpr uint8_t PIN_DRDY  = 7;   // DRDY activo bajo
static constexpr uint8_t PIN_START = D9;
static constexpr uint8_t PIN_RESET = D8;
static constexpr uint8_t PIN_PWDN  = D5;

// ADS1299
ADS1299_SafeSPI safeSpi(PIN_CS);
ADS1299Plus::Pins adsPins = {
  PIN_CS, PIN_SCLK, PIN_MOSI, PIN_MISO, PIN_DRDY, PIN_START, PIN_RESET, PIN_PWDN
};
ADS1299Plus ads(safeSpi, adsPins);

static_assert(ADS1299Plus::NUM_CHANNELS == 4, "Este main.cpp asume ADS1299 de 4 canales.");

// ---------------------------
// Parámetros de muestreo y conversión
// ---------------------------
static constexpr float FS_HZ  = 250.0f;
static constexpr float LSB_V  = 2.235e-8f;   // tu LSB (según tu config/gain)

// ---------------------------
// Diagnóstico ADS1299 opcional
// ---------------------------
// 0 = captura real normal INxP-INxN
// 1 = entradas internas en corto (ruido/offset interno)
// 2 = señal de test interna ADS1299 (escala/ganancia/SPI)
// 3 = normal sin lead-off sense (baseline antes de BIAS/DRL)
// 4 = BIAS/DRL activo derivado solo de CH1P+CH1N, sin lead-off sense
// 5 = igual que 4, pero CH2-CH4 apagados para descartar entradas flotantes
//
// Mantener en 0 para capturas reales. Cambiar solo para compilar una prueba
// diagnóstica temporal y volver a 0 después.
#ifndef ADS_DIAGNOSTIC_MODE
#define ADS_DIAGNOSTIC_MODE 5
#endif

#define ADS_DIAG_NORMAL 0
#define ADS_DIAG_SHORTED_INPUTS 1
#define ADS_DIAG_TEST_SIGNAL_INTERNAL 2
#define ADS_DIAG_NO_BIAS_LOFF_OFF 3
#define ADS_DIAG_BIAS_CH1PN_LOFF_OFF 4
#define ADS_DIAG_BIAS_CH1_ONLY_LOFF_OFF 5

// ---------------------------
// Debug / rendimiento
// ---------------------------
static constexpr bool     DEBUG_MONITOR = true;
static constexpr uint32_t DEBUG_EVERY_N = 500;

// Streaming EEG y benchmark / instrumentación
//
// Compatibilidad: si algún perfil externo define BENCH_NOTIFY_ENABLED, se usa
// como alias legacy para controlar el streaming EEG por Bridge. El nombre nuevo
// deja claro que no controla los informes de benchmark.
#ifndef EEG_STREAMING_NOTIFY_ENABLED
#ifdef BENCH_NOTIFY_ENABLED
#define EEG_STREAMING_NOTIFY_ENABLED BENCH_NOTIFY_ENABLED
#else
#define EEG_STREAMING_NOTIFY_ENABLED 1
#endif
#endif

#ifndef BENCH_REPORT_ENABLED
#define BENCH_REPORT_ENABLED 1
#endif

static constexpr bool     STREAMING_NOTIFY_ENABLED = (EEG_STREAMING_NOTIFY_ENABLED != 0);
static constexpr bool     BENCH_REPORTS_ENABLED    = (BENCH_REPORT_ENABLED != 0);
static constexpr uint32_t BENCH_REPORT_EVERY_MS    = 5000;

// ---------------------------
// Handshake con Python (para no perder notifies)
// ---------------------------
static bool mpu_ready = false;
static uint32_t last_ready_check_ms = 0;

// ---------------------------
// MIDI OUT live
// ---------------------------
static constexpr uint32_t MIDI_BAUD = 31250;

// Handler Bridge disponible para Python:
//   Bridge.call("midi_bytes", n, b0, b1, b2)
//
// Rama midi-config-v2: probar MIDI OUT fisico por D1/TX usando Serial1.
// En UNO Q / Zephyr, D0/D1 se exponen como UART de hardware. Si interfiere
// con Bridge/Monitor, compilar con MIDI_UART_ENABLED=0 para volver a dry-run.
#ifndef MIDI_SERIAL
#define MIDI_SERIAL Serial1
#endif

#ifndef MIDI_UART_ENABLED
#define MIDI_UART_ENABLED 1
#endif

#ifndef MIDI_MCU_SELF_TEST_ENABLED
#define MIDI_MCU_SELF_TEST_ENABLED 1
#endif

#if (MIDI_UART_ENABLED != 0)
#ifndef MIDI_SERIAL
#error "Define MIDI_SERIAL as the hardware UART verified for D1/TX MIDI OUT."
#endif
#define MIDI_UART_CONFIGURED 1
#else
#define MIDI_UART_CONFIGURED 0
#endif

#if MIDI_UART_CONFIGURED
#if !defined(USART1) || !defined(USART_CR2_TXINV)
#error "N-audio MIDI OUT hardware requires inverted TX, but USART1/TXINV symbols are unavailable."
#endif
#endif

static uint8_t midi_debug_left = 16;
static uint32_t midi_calls_total = 0;
static uint32_t midi_bytes_total = 0;
static bool midi_tx_inversion_applied = false;

static void midiConfigureTxPolarity() {
#if MIDI_UART_CONFIGURED
#if defined(USART_CR1_UE)
  const bool was_enabled = (USART1->CR1 & USART_CR1_UE) != 0;
  if (was_enabled) {
    USART1->CR1 &= ~USART_CR1_UE;
  }
  USART1->CR2 |= USART_CR2_TXINV;
  if (was_enabled) {
    USART1->CR1 |= USART_CR1_UE;
  }
#else
  USART1->CR2 |= USART_CR2_TXINV;
#endif
  midi_tx_inversion_applied = true;
  Monitor.println("MIDI TX inversion REQUIRED and enabled on USART1 (TXINV)");
#else
  midi_tx_inversion_applied = false;
#endif
}

static void midiWriteRawByte(uint8_t value) {
#if MIDI_UART_CONFIGURED
  MIDI_SERIAL.write(value);
#else
  (void)value;
#endif
}

static void midiWriteRawBytes(const uint8_t* data, int n) {
  for (int i = 0; i < n; ++i) {
    midiWriteRawByte(data[i]);
  }
}

static void midiSend2(uint8_t status_base, uint8_t channel_zero_based, uint8_t data1) {
  const uint8_t msg[2] = {
    static_cast<uint8_t>(status_base | (channel_zero_based & 0x0F)),
    static_cast<uint8_t>(data1 & 0x7F),
  };
  midiWriteRawBytes(msg, 2);
}

static void midiSend3(uint8_t status_base, uint8_t channel_zero_based, uint8_t data1, uint8_t data2) {
  const uint8_t msg[3] = {
    static_cast<uint8_t>(status_base | (channel_zero_based & 0x0F)),
    static_cast<uint8_t>(data1 & 0x7F),
    static_cast<uint8_t>(data2 & 0x7F),
  };
  midiWriteRawBytes(msg, 3);
}

static void midiSendControlChange(uint8_t channel_zero_based, uint8_t cc, uint8_t value) {
  midiSend3(0xB0, channel_zero_based, cc, value);
}

static void midiSendProgramChange(uint8_t channel_zero_based, uint8_t program) {
  midiSend2(0xC0, channel_zero_based, program);
}

static void midiSendNoteOn(uint8_t channel_zero_based, uint8_t note, uint8_t velocity) {
  midiSend3(0x90, channel_zero_based, note, velocity);
}

static void midiSendNoteOff(uint8_t channel_zero_based, uint8_t note) {
  midiSend3(0x80, channel_zero_based, note, 0);
}

#if MIDI_MCU_SELF_TEST_ENABLED
static constexpr uint8_t MIDI_SELF_TEST_CHANNEL_ZERO = 9;  // canal MIDI 10
static constexpr uint8_t MIDI_SELF_TEST_PROGRAM = 9;       // programa visible 10
static constexpr uint8_t MIDI_SELF_TEST_VELOCITY = 100;
static constexpr uint32_t MIDI_SELF_TEST_NOTE_MS = 80;
static constexpr uint32_t MIDI_SELF_TEST_GAP_MS = 20;
static const uint8_t MIDI_SELF_TEST_NOTES[] = {60, 64, 67, 72};
static uint8_t midi_self_test_note_idx = 0;
static bool midi_self_test_note_on = false;
static uint32_t midi_self_test_next_ms = 0;
static uint32_t midi_self_test_cycles = 0;

static void midiStartSelfTest() {
  midiSendControlChange(MIDI_SELF_TEST_CHANNEL_ZERO, 7, 127);   // Volume
  midiSendControlChange(MIDI_SELF_TEST_CHANNEL_ZERO, 11, 127);  // Expression
  midiSendControlChange(MIDI_SELF_TEST_CHANNEL_ZERO, 64, 0);    // Sustain off
  midiSendProgramChange(MIDI_SELF_TEST_CHANNEL_ZERO, MIDI_SELF_TEST_PROGRAM);

  midi_self_test_note_idx = 0;
  midi_self_test_note_on = false;
  midi_self_test_next_ms = millis() + 20;
  midi_self_test_cycles = 0;

  Monitor.println("MIDI MCU self-test enabled: Serial1 channel=10 program=10");
}

static void midiPumpSelfTest() {
  const uint32_t now = millis();
  if (static_cast<int32_t>(now - midi_self_test_next_ms) < 0) {
    return;
  }

  const uint8_t note_count = static_cast<uint8_t>(sizeof(MIDI_SELF_TEST_NOTES) / sizeof(MIDI_SELF_TEST_NOTES[0]));
  const uint8_t note = MIDI_SELF_TEST_NOTES[midi_self_test_note_idx % note_count];

  if (!midi_self_test_note_on) {
    midiSendNoteOn(MIDI_SELF_TEST_CHANNEL_ZERO, note, MIDI_SELF_TEST_VELOCITY);
    midi_self_test_note_on = true;
    midi_self_test_next_ms = now + MIDI_SELF_TEST_NOTE_MS;
    return;
  }

  midiSendNoteOff(MIDI_SELF_TEST_CHANNEL_ZERO, note);
  midi_self_test_note_on = false;
  midi_self_test_note_idx = static_cast<uint8_t>((midi_self_test_note_idx + 1) % note_count);
  if (midi_self_test_note_idx == 0) {
    ++midi_self_test_cycles;
    if ((midi_self_test_cycles % 32UL) == 0) {
      Monitor.print("[MIDI SELFTEST] cycles=");
      Monitor.println(midi_self_test_cycles);
    }
  }
  midi_self_test_next_ms = now + MIDI_SELF_TEST_GAP_MS;
}
#endif

static bool midi_bytes(int n, int b0, int b1, int b2) {
  if (n < 1 || n > 3) {
    return false;
  }

  ++midi_calls_total;
  midi_bytes_total += static_cast<uint32_t>(n);

  const uint8_t data[3] = {
    static_cast<uint8_t>(b0 & 0xFF),
    static_cast<uint8_t>(b1 & 0xFF),
    static_cast<uint8_t>(b2 & 0xFF),
  };

#if MIDI_UART_CONFIGURED
  if (midi_debug_left > 0) {
    Monitor.print("[MIDI TX] n=");
    Monitor.print(n);
    Monitor.print(" bytes=");
    for (int i = 0; i < n; ++i) {
      Monitor.print(" 0x");
      Monitor.print(data[i], HEX);
    }
    Monitor.println();
    --midi_debug_left;
  }

  if ((midi_calls_total % 128UL) == 0) {
    Monitor.print("[MIDI TX TOTAL] calls=");
    Monitor.print(midi_calls_total);
    Monitor.print(" bytes=");
    Monitor.println(midi_bytes_total);
  }

  midiWriteRawBytes(data, n);
  return true;
#else
  (void)data;
  return false;
#endif
}

// Handler Bridge compatible con el LED Matrix Painter:
//   Bridge.call("led_matrix_row", row_idx, chunk0, chunk1, chunk2)
//
// Cada fila 13x1 se empaqueta en 3 chunks positivos de 16/16/7 bits:
// 13 pixeles * 3 bits de brillo = 39 bits. Asi el handler no recibe
// std::vector ni reserva memoria dinamica en el MCU.
static constexpr size_t LED_MATRIX_WIDTH = 13;
static constexpr size_t LED_MATRIX_HEIGHT = 8;
static constexpr size_t LED_MATRIX_BYTES = LED_MATRIX_WIDTH * LED_MATRIX_HEIGHT;
static uint8_t led_frame_buffer[LED_MATRIX_BYTES] = {0};
static uint8_t led_rows_received_mask = 0;

static bool led_matrix_row(int row_idx, int chunk0, int chunk1, int chunk2) {
  if (row_idx < 0 || row_idx >= static_cast<int>(LED_MATRIX_HEIGHT)) {
    return false;
  }
  if (chunk0 < 0 || chunk0 > 0xFFFF || chunk1 < 0 || chunk1 > 0xFFFF || chunk2 < 0 || chunk2 > 0x7F) {
    return false;
  }

  if (row_idx == 0) {
    led_rows_received_mask = 0;
  }

  const uint64_t packed =
      (static_cast<uint64_t>(chunk0) & 0xFFFFULL) |
      ((static_cast<uint64_t>(chunk1) & 0xFFFFULL) << 16) |
      ((static_cast<uint64_t>(chunk2) & 0x7FULL) << 32);

  const size_t row_offset = static_cast<size_t>(row_idx) * LED_MATRIX_WIDTH;
  for (size_t col = 0; col < LED_MATRIX_WIDTH; ++col) {
    led_frame_buffer[row_offset + col] =
        static_cast<uint8_t>((packed >> (col * 3U)) & 0x7U);
  }

  led_rows_received_mask |= static_cast<uint8_t>(1U << row_idx);

#if LED_MATRIX_ENABLED
  const uint8_t full_frame_mask = static_cast<uint8_t>((1U << LED_MATRIX_HEIGHT) - 1U);
  if (row_idx == static_cast<int>(LED_MATRIX_HEIGHT - 1) && led_rows_received_mask == full_frame_mask) {
    ledMatrix.draw(led_frame_buffer);
  }
  return true;
#else
  return false;
#endif
}

static bool checkMpuReady() {
  bool ready = false;
  RpcCall c = Bridge.call("linux_started");
  if (c.result(ready) && ready) return true;
  return false;
}

// ---------------------------
// Señal DRDY por interrupción (más robusto que polling)
// ---------------------------
static volatile uint32_t drdy_count = 0;

static void onDrdyFalling() {
  drdy_count++;
}

// ---------------------------
// Filtros por canal
// ---------------------------
static DCBlocker hp[ADS1299Plus::NUM_CHANNELS];
static Biquad    notch50[ADS1299Plus::NUM_CHANNELS];
static Biquad    lp40[ADS1299Plus::NUM_CHANNELS];

// ---------------------------
// Estado global de streaming / métricas
// ---------------------------
static uint32_t    sample_idx = 0;
static TxBlockRing txBlocks;
static BenchStats  bench;

// ---------------------------
// Helpers de benchmark
// ---------------------------
static void reportBenchStatsIfDue() {
  if (!BENCH_REPORTS_ENABLED) return;

  const uint32_t now_ms = millis();
  if (now_ms - bench.report_last_ms < BENCH_REPORT_EVERY_MS) return;

  uint32_t dt_ms = now_ms - bench.report_last_ms;
  if (dt_ms == 0) dt_ms = 1;
  bench.report_last_ms = now_ms;

  const float dt_s = dt_ms / 1000.0f;

    const uint32_t gen_rate_x100 =
      (bench.samples_generated_window * 100000UL) / dt_ms;

  const uint32_t sent_rate_x100 =
      (bench.samples_sent_window * 100000UL) / dt_ms;

  const uint32_t blocks_enq_rate_x100 =
      (bench.blocks_enqueued_window * 100000UL) / dt_ms;

  const uint32_t blocks_sent_rate_x100 =
      (bench.blocks_sent_window * 100000UL) / dt_ms;

  const float filter_avg_us =
      (bench.samples_generated_window > 0)
        ? (float)bench.filter_time_us_accum_window / (float)bench.samples_generated_window
        : 0.0f;

  const float notify_avg_us =
      (bench.notify_calls_window > 0)
        ? (float)bench.notify_time_us_accum_window / (float)bench.notify_calls_window
        : 0.0f;

  const float notify_eff_us_per_sample =
      (bench.samples_sent_window > 0)
        ? (float)bench.notify_time_us_accum_window / (float)bench.samples_sent_window
        : 0.0f;

  Monitor.println();
  Monitor.println("============================================================");
  Monitor.println("[BENCH] EEG_MIDI");
  Monitor.println("------------------------------------------------------------");

  Monitor.print("  rate   | gen/s=");
  Monitor.print(gen_rate_x100 / 100);
  Monitor.print(".");
  Monitor.print(gen_rate_x100 % 100);

  Monitor.print("  sent/s=");
  Monitor.print(sent_rate_x100 / 100);
  Monitor.print(".");
  Monitor.print(sent_rate_x100 % 100);

  Monitor.print("  blk_enq/s=");
  Monitor.print(blocks_enq_rate_x100 / 100);
  Monitor.print(".");
  Monitor.print(blocks_enq_rate_x100 % 100);

  Monitor.print("  blk_sent/s=");
  Monitor.print(blocks_sent_rate_x100 / 100);
  Monitor.print(".");
  Monitor.println(blocks_sent_rate_x100 % 100);

  Monitor.print("  time   | filt_avg_us=");           Monitor.print(filter_avg_us, 2);
  Monitor.print("  filt_max_us_win=");                Monitor.print(bench.filter_time_us_max_window);
  Monitor.print("  notify_avg_us=");                  Monitor.print(notify_avg_us, 2);
  Monitor.print("  notify_eff_us/sample=");           Monitor.print(notify_eff_us_per_sample, 2);
  Monitor.print("  notify_max_us_win=");              Monitor.println(bench.notify_time_us_max_window);

  Monitor.print("  queue  | q=");                     Monitor.print(txBlocks.count);
  Monitor.print("  qmax_win=");                       Monitor.print(bench.tx_queue_max_window);
  Monitor.print("  drops_win=");                      Monitor.print(bench.tx_queue_drops_window);
  Monitor.print("  pub_burst_win=");                  Monitor.println(bench.tx_publish_bursts_max_window);

  Monitor.print("  jitter | lag_win=");               Monitor.print(bench.lag_events_window);
  Monitor.print("  catchup_win=");                    Monitor.print(bench.synthetic_catchup_iters_max_window);
  Monitor.print("  sample_iter_max_us_win=");         Monitor.print(bench.sample_iter_time_us_max_window);
  Monitor.print("  loop_max_us_win=");                Monitor.println(bench.loop_time_us_max_window);

  Monitor.print("  DRDY   | pin=");                   Monitor.print(digitalRead(PIN_DRDY));
  Monitor.print("  drdy_count_now=");
  noInterrupts();
  uint32_t drdy_snapshot = drdy_count;
  interrupts();
  Monitor.println(drdy_snapshot);
  
  Monitor.println("------------------------------------------------------------");
  Monitor.print("  total  | gen=");                   Monitor.print(bench.samples_generated_total);
  Monitor.print("  sent=");                           Monitor.print(bench.samples_sent_total);
  Monitor.print("  blk_enq=");                        Monitor.print(bench.blocks_enqueued_total);
  Monitor.print("  blk_sent=");                       Monitor.print(bench.blocks_sent_total);
  Monitor.print("  notify_calls=");                   Monitor.println(bench.notify_calls_total);

  Monitor.print("  peak   | qmax_global=");           Monitor.print(bench.tx_queue_max_global);
  Monitor.print("  drops_total=");                    Monitor.print(bench.tx_queue_drops_total);
  Monitor.print("  pub_burst_global=");               Monitor.print(bench.tx_publish_bursts_max_global);
  Monitor.print("  notify_max_global_us=");           Monitor.print(bench.notify_time_us_max_global);
  Monitor.print("  loop_max_global_us=");             Monitor.println(bench.loop_time_us_max_global);

  Monitor.println("============================================================");

  // Reset de ventana
  bench.samples_generated_window = 0;
  bench.samples_sent_window      = 0;

  bench.blocks_enqueued_window = 0;
  bench.blocks_sent_window     = 0;

  bench.notify_calls_window = 0;

  bench.filter_time_us_accum_window = 0;
  bench.notify_time_us_accum_window = 0;

  bench.filter_time_us_max_window      = 0;
  bench.notify_time_us_max_window      = 0;
  bench.sample_iter_time_us_max_window = 0;
  bench.loop_time_us_max_window        = 0;

  bench.lag_events_window                  = 0;
  bench.synthetic_catchup_iters_max_window = 0;

  bench.tx_queue_max_window          = txBlocks.count;
  bench.tx_queue_drops_window        = 0;
  bench.tx_publish_bursts_max_window = 0;
}

// ---------------------------
// Filtros
// ---------------------------
static void initFilters() {
  const float HP_FC    = 0.5f;
  const float NOTCH_F0 = 50.0f;
  const float NOTCH_R  = 0.95f;
  const float LP_FC    = 40.0f;
  const float LP_Q     = 0.70710678f;

  for (int i = 0; i < ADS1299Plus::NUM_CHANNELS; ++i) {
    hp[i].init(HP_FC, FS_HZ);
    notch50[i] = makeNotch(NOTCH_F0, FS_HZ, NOTCH_R);
    lp40[i]    = makeLowpassRBJ(LP_FC, FS_HZ, LP_Q);
  }
}

static bool applyAdsDiagnosticMode() {
#if ADS_DIAGNOSTIC_MODE == ADS_DIAG_SHORTED_INPUTS
  Monitor.println("ADS1299 DIAG: shorted_inputs (CH1-CH4 MUX=SHORT, lead-off sense off)");

  // La prueba de entradas cortocircuitadas mide ruido/offset interno. Se
  // desactiva lead-off para no inyectar corriente de comprobación durante la
  // medida diagnóstica.
  if (!ads.enableLeadOffSenseP(0x00)) return false;
  if (!ads.enableLeadOffSenseN(0x00)) return false;
  if (!ads.writeReg(ADS_REG_CONFIG2, ADS_CFG2_TEST_OFF)) return false;

  for (uint8_t ch = 1; ch <= ADS1299Plus::NUM_CHANNELS; ++ch) {
    if (!ads.setChannelMux(ch, ADS_MUX_SHORT)) return false;
  }
  return true;

#elif ADS_DIAGNOSTIC_MODE == ADS_DIAG_TEST_SIGNAL_INTERNAL
  Monitor.println("ADS1299 DIAG: test_signal_internal (CONFIG2 INT_CAL, CH1-CH4 MUX=TESTSIG)");

  // Señal interna lenta (~fCLK/2^21) con amplitud 1x. Sirve para verificar
  // escala, ganancia, reconstrucción 24-bit y streaming sin electrodos.
  if (!ads.enableLeadOffSenseP(0x00)) return false;
  if (!ads.enableLeadOffSenseN(0x00)) return false;
  if (!ads.writeReg(ADS_REG_CONFIG2, ADS_CFG2_MAKE(true, false, ADS_CALF_CLK_2_21))) return false;

  for (uint8_t ch = 1; ch <= ADS1299Plus::NUM_CHANNELS; ++ch) {
    if (!ads.setChannelMux(ch, ADS_MUX_TESTSIG)) return false;
  }
  return true;

#elif ADS_DIAGNOSTIC_MODE == ADS_DIAG_NO_BIAS_LOFF_OFF
  Monitor.println("ADS1299 DIAG: no_bias_loff_off (normal inputs, BIAS off, lead-off sense off)");

  // Baseline analogico antes de probar RLD/BIAS: misma entrada diferencial
  // real, pero sin inyeccion lead-off y con BIAS derivation desactivada.
  if (!ads.writeReg(ADS_REG_CONFIG2, ADS_CFG2_TEST_OFF)) return false;
  if (!ads.writeReg(ADS_REG_CONFIG3, ADS_CFG3_INTREF_NO_BIAS)) return false;
  if (!ads.setBiasDeriveP(0x00)) return false;
  if (!ads.setBiasDeriveN(0x00)) return false;
  if (!ads.enableLeadOffSenseP(0x00)) return false;
  if (!ads.enableLeadOffSenseN(0x00)) return false;

  for (uint8_t ch = 1; ch <= ADS1299Plus::NUM_CHANNELS; ++ch) {
    if (!ads.setChannelMux(ch, ADS_MUX_NORMAL)) return false;
  }
  return true;

#elif ADS_DIAGNOSTIC_MODE == ADS_DIAG_BIAS_CH1PN_LOFF_OFF
  Monitor.println("ADS1299 DIAG: bias_ch1pn_loff_off (BIAS on, derive CH1P+CH1N, lead-off sense off)");

  // Primera prueba RLD/BIAS segura para tu montaje Fp1-Fp2:
  // - CH1P y CH1N derivan el common-mode.
  // - BIASOUT/RLD_DRV se conecta a electrodo RLD dedicado.
  // - CH2-CH4 no se incluyen para evitar canales flotantes en el lazo.
  // - Lead-off sense queda off para no inyectar corriente diagnostica.
  if (!ads.writeReg(ADS_REG_CONFIG2, ADS_CFG2_TEST_OFF)) return false;
  if (!ads.writeReg(ADS_REG_CONFIG3, ADS_CFG3_MAKE(true, false, true, true, false))) return false;
  if (!ads.setBiasDeriveP(ADS_MASK_CH1)) return false;
  if (!ads.setBiasDeriveN(ADS_MASK_CH1)) return false;
  if (!ads.enableLeadOffSenseP(0x00)) return false;
  if (!ads.enableLeadOffSenseN(0x00)) return false;

  for (uint8_t ch = 1; ch <= ADS1299Plus::NUM_CHANNELS; ++ch) {
    if (!ads.setChannelMux(ch, ADS_MUX_NORMAL)) return false;
  }
  return true;

#elif ADS_DIAGNOSTIC_MODE == ADS_DIAG_BIAS_CH1_ONLY_LOFF_OFF
  Monitor.println("ADS1299 DIAG: bias_ch1_only_loff_off (CH1 active, CH2-CH4 powered down, BIAS CH1P+CH1N)");

  // Igual que bias_ch1pn_loff_off, pero apaga CH2-CH4. Sirve para comprobar
  // si canales no usados/flotantes contaminan el front-end o las métricas.
  if (!ads.writeReg(ADS_REG_CONFIG2, ADS_CFG2_TEST_OFF)) return false;
  if (!ads.writeReg(ADS_REG_CONFIG3, ADS_CFG3_MAKE(true, false, true, true, false))) return false;
  if (!ads.setBiasDeriveP(ADS_MASK_CH1)) return false;
  if (!ads.setBiasDeriveN(ADS_MASK_CH1)) return false;
  if (!ads.enableLeadOffSenseP(0x00)) return false;
  if (!ads.enableLeadOffSenseN(0x00)) return false;

  if (!ads.setChannel(1, ADS_CH_DEFAULT_GAIN24())) return false;
  for (uint8_t ch = 2; ch <= ADS1299Plus::NUM_CHANNELS; ++ch) {
    if (!ads.setChannel(ch, ADS_CH_MAKE(false, ADS_GAIN_24, ADS_MUX_SHORT, false))) return false;
  }
  return true;

#elif ADS_DIAGNOSTIC_MODE == ADS_DIAG_NORMAL
  Monitor.println("ADS1299 DIAG: normal acquisition (INxP-INxN)");
  return true;

#else
#error "ADS_DIAGNOSTIC_MODE must be 0 normal, 1 shorted_inputs, 2 test_signal_internal, 3 no_bias_loff_off, 4 bias_ch1pn_loff_off, or 5 bias_ch1_only_loff_off"
#endif
}

void setup() {
  Bridge.begin();
  Monitor.begin();
  delay(5000);

  Monitor.println("BOOT: EEG_MIDI");

#if LED_MATRIX_ENABLED
  ledMatrix.begin();
  ledMatrix.setGrayscaleBits(3);
  ledMatrix.clear();
  Monitor.println("LED matrix enabled: Arduino_LED_Matrix 13x8 grayscale 0..7");
#else
  Monitor.println("LED matrix disabled: led_matrix_row handler registered for dry-run only");
#endif

#if MIDI_UART_ENABLED
#if defined(SERIAL_8N1)
  MIDI_SERIAL.begin(MIDI_BAUD, SERIAL_8N1);
#else
  MIDI_SERIAL.begin(MIDI_BAUD);
#endif
  midiConfigureTxPolarity();
  Monitor.println("MIDI UART enabled at 31250 baud on Serial1/D1");
#if MIDI_MCU_SELF_TEST_ENABLED
  midiStartSelfTest();
#endif
#else
  Monitor.println("MIDI UART disabled: midi_bytes handler registered for dry-run only");
#endif

  if (!Bridge.provide_safe("midi_bytes", midi_bytes)) {
    Monitor.println("ERROR: no se pudo registrar handler midi_bytes");
  } else {
    Monitor.println("Bridge handler registered: midi_bytes");
  }

  if (!Bridge.provide_safe("led_matrix_row", led_matrix_row)) {
    Monitor.println("ERROR: no se pudo registrar handler led_matrix_row");
  } else {
    Monitor.println("Bridge handler registered: led_matrix_row");
  }

  bench.report_last_ms = millis();
  bench.tx_queue_max_window = 0;
  bench.tx_queue_drops_window = 0;
  bench.tx_publish_bursts_max_window = 0;

  txBlocks.resetStreamingState();
  initFilters();

#if USE_SYNTHETIC
  Monitor.println("Modo: SYNTHETIC (sin ADS1299)");
#else
  Monitor.println("Modo: REAL (ADS1299)");

  pinMode(PIN_DRDY, INPUT_PULLUP);
  pinMode(PIN_START, OUTPUT);
  pinMode(PIN_RESET, OUTPUT);
  pinMode(PIN_PWDN, OUTPUT);
  digitalWrite(PIN_PWDN, HIGH);

  attachInterrupt(digitalPinToInterrupt(PIN_DRDY), onDrdyFalling, FALLING);

  safeSpi.begin();

  if (!ads.begin()) {
    Monitor.println("ERROR: ads.begin() fallo");
    while (1) delay(1000);
  }
  uint8_t ads_id = 0;
  if (ads.readDeviceID(ads_id)) {
    Monitor.print("ADS1299 ID=0x");
    Monitor.println(ads_id, HEX);
  } else {
    Monitor.println("ERROR: no se pudo leer ADS1299 ID tras begin()");
  }
    if (!ads.configureDefaults()) {
    Monitor.println("ERROR: configureDefaults() fallo");
    while (1) delay(1000);
  }

  if (!applyAdsDiagnosticMode()) {
    Monitor.println("ERROR: applyAdsDiagnosticMode() fallo");
    while (1) delay(1000);
  }

  // Limpiar posibles interrupciones DRDY antiguas o espurias antes de arrancar adquisición
  noInterrupts();
  drdy_count = 0;
  interrupts();
  
  ads.pinStartHigh();
  delay(10);

  ads.cmdRDATAC();
  Monitor.println("START + RDATAC activo. Esperando DRDY...");

#endif
}

void loop() {
  const uint32_t loop_start_us = micros();

#if MIDI_MCU_SELF_TEST_ENABLED
  midiPumpSelfTest();
#endif

  // Handshake con Python (1 Hz)
  if (!mpu_ready) {
    const uint32_t now = millis();
    if (now - last_ready_check_ms > 1000) {
      last_ready_check_ms = now;
      const bool ready_now = checkMpuReady();

      if (ready_now && !mpu_ready) {
        mpu_ready = true;
        txBlocks.resetStreamingState();
        Monitor.println("MPU listo (linux_started=true). Comenzando streaming EEG filtrado...");
      } else if (!ready_now) {
        Monitor.println("Esperando a Python... (linux_started aun no disponible)");
      }
    }
  }

#if USE_SYNTHETIC
  static uint32_t rng = 0x12345678u;
  static uint32_t next_us = 0;
  if (next_us == 0) next_us = micros();

  const uint32_t step_us = (uint32_t)(1000000.0f / FS_HZ);
  uint32_t catchup_count = 0;

  while ((int32_t)(micros() - next_us) >= 0) {
    catchup_count++;
    next_us += step_us;

    const uint32_t sample_iter_start_us = micros();

    uint32_t status = 0;
    int32_t ch_raw[ADS1299Plus::NUM_CHANNELS] = {0};

    generateSyntheticRaw(sample_idx, FS_HZ, LSB_V, ch_raw, ADS1299Plus::NUM_CHANNELS, rng);

    bench.samples_generated_total++;
    bench.samples_generated_window++;

    int32_t ch_uV[ADS1299Plus::NUM_CHANNELS];

    const uint32_t filter_start_us = micros();

    for (int i = 0; i < ADS1299Plus::NUM_CHANNELS; ++i) {
      float v = (float)ch_raw[i] * LSB_V;
      v = hp[i].process(v);
      v = notch50[i].process(v);
      v = lp40[i].process(v);
      ch_uV[i] = volts_to_uV_i32(v);
    }

    const uint32_t filter_dt_us = micros() - filter_start_us;
    bench.filter_time_us_accum_total += filter_dt_us;
    bench.filter_time_us_accum_window += filter_dt_us;

    if (filter_dt_us > bench.filter_time_us_max_global) {
      bench.filter_time_us_max_global = filter_dt_us;
    }
    if (filter_dt_us > bench.filter_time_us_max_window) {
      bench.filter_time_us_max_window = filter_dt_us;
    }

    if (mpu_ready && STREAMING_NOTIFY_ENABLED) {
      txBlocks.appendSampleToFillBlock((uint32_t)sample_idx, (uint32_t)status, ch_uV, bench);
    }

    const uint32_t sample_iter_dt_us = micros() - sample_iter_start_us;
    if (sample_iter_dt_us > bench.sample_iter_time_us_max_global) {
      bench.sample_iter_time_us_max_global = sample_iter_dt_us;
    }
    if (sample_iter_dt_us > bench.sample_iter_time_us_max_window) {
      bench.sample_iter_time_us_max_window = sample_iter_dt_us;
    }

    if (DEBUG_MONITOR && (sample_idx % DEBUG_EVERY_N == 0)) {
      Monitor.print("SYN idx=");
      Monitor.print(sample_idx);
      Monitor.print(" uV0=");
      Monitor.println(ch_uV[0]);
    }

    sample_idx++;
  }

  if (catchup_count > 1) {
    bench.synthetic_lag_events_total++;
    bench.lag_events_window++;
  }

  if (catchup_count > bench.synthetic_catchup_iters_max_global) {
    bench.synthetic_catchup_iters_max_global = catchup_count;
  }
  if (catchup_count > bench.synthetic_catchup_iters_max_window) {
    bench.synthetic_catchup_iters_max_window = catchup_count;
  }

#else
uint32_t pending = 0;
noInterrupts();
pending = drdy_count;
drdy_count = 0;
interrupts();

if (pending > 1) {
  bench.lag_events_window++;
  bench.synthetic_lag_events_total++;
}

if (pending > 0) {
  const uint32_t sample_iter_start_us = micros();

  uint32_t status = 0;
  int32_t ch_raw[ADS1299Plus::NUM_CHANNELS] = {0};

  if (!ads.readFrameRDATAC(status, ch_raw)) {
    static uint32_t last_bad_print_ms = 0;
    uint32_t now_ms = millis();

    if (DEBUG_MONITOR && (now_ms - last_bad_print_ms > 1000)) {
      last_bad_print_ms = now_ms;
      Monitor.print("Frame invalido / error sincronía. status=0x");
      Monitor.println(status, HEX);
    }
    return;
  }

  bench.samples_generated_total++;
  bench.samples_generated_window++;

  int32_t ch_uV[ADS1299Plus::NUM_CHANNELS];

  const uint32_t filter_start_us = micros();

  for (int i = 0; i < ADS1299Plus::NUM_CHANNELS; ++i) {
    float v = (float)ch_raw[i] * LSB_V;
    v = hp[i].process(v);
    v = notch50[i].process(v);
    v = lp40[i].process(v);
    ch_uV[i] = volts_to_uV_i32(v);
  }

  const uint32_t filter_dt_us = micros() - filter_start_us;
  bench.filter_time_us_accum_total += filter_dt_us;
  bench.filter_time_us_accum_window += filter_dt_us;

  if (filter_dt_us > bench.filter_time_us_max_global) {
    bench.filter_time_us_max_global = filter_dt_us;
  }
  if (filter_dt_us > bench.filter_time_us_max_window) {
    bench.filter_time_us_max_window = filter_dt_us;
  }

  if (mpu_ready && STREAMING_NOTIFY_ENABLED) {
    txBlocks.appendSampleToFillBlock((uint32_t)sample_idx, (uint32_t)status, ch_uV, bench);
  }

  const uint32_t sample_iter_dt_us = micros() - sample_iter_start_us;
  if (sample_iter_dt_us > bench.sample_iter_time_us_max_global) {
    bench.sample_iter_time_us_max_global = sample_iter_dt_us;
  }
  if (sample_iter_dt_us > bench.sample_iter_time_us_max_window) {
    bench.sample_iter_time_us_max_window = sample_iter_dt_us;
  }

  if (DEBUG_MONITOR && (sample_idx % DEBUG_EVERY_N == 0)) {
    Monitor.print("idx=");
    Monitor.print(sample_idx);
    Monitor.print(" status=0x");
    Monitor.print(status, HEX);
    Monitor.print(" uV[0..1]=");
    Monitor.print(ch_uV[0]);
    Monitor.print(", ");
    Monitor.println(ch_uV[1]);
  }

  sample_idx++;
}
#endif

  {
    const uint32_t loop_dt = micros() - loop_start_us;
    if (loop_dt > bench.loop_time_us_max_global) {
      bench.loop_time_us_max_global = loop_dt;
    }
    if (loop_dt > bench.loop_time_us_max_window) {
      bench.loop_time_us_max_window = loop_dt;
    }
  }

  if (mpu_ready && STREAMING_NOTIFY_ENABLED) {
    txBlocks.publishPendingBlocks(bench, 4);
  }

  reportBenchStatsIfDue();
}
