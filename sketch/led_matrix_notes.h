#pragma once

#include <Arduino.h>

#if __has_include(<Arduino_LED_Matrix.h>)
#include <Arduino_LED_Matrix.h>
#define EEG_HAS_ARDUINO_LED_MATRIX 1
#else
#define EEG_HAS_ARDUINO_LED_MATRIX 0
#endif

#ifndef LED_MATRIX_NOTES_ENABLED
#define LED_MATRIX_NOTES_ENABLED EEG_HAS_ARDUINO_LED_MATRIX
#endif

static constexpr uint8_t LED_NOTE_ROWS = 8;
static constexpr uint8_t LED_NOTE_COLS = 13;
static constexpr uint8_t LED_NOTE_VELOCITY_COL = 12;
static constexpr uint32_t LED_NOTE_HOLD_MS = 180;

#if LED_MATRIX_NOTES_ENABLED && EEG_HAS_ARDUINO_LED_MATRIX
static ArduinoLEDMatrix ledMatrix;
static bool led_matrix_ready = false;
static bool led_note_visible = false;
static uint32_t led_note_clear_at_ms = 0;
#endif

static volatile bool led_note_pending = false;
static volatile uint8_t led_note_pending_pitch = 60;
static volatile uint8_t led_note_pending_velocity = 0;

static uint8_t ledNoteClamp7(int value) {
  if (value < 0) return 0;
  if (value > 127) return 127;
  return static_cast<uint8_t>(value);
}

static bool ledMatrixNotesAvailable() {
#if LED_MATRIX_NOTES_ENABLED && EEG_HAS_ARDUINO_LED_MATRIX
  return true;
#else
  return false;
#endif
}

static bool ledMatrixNotesInit() {
#if LED_MATRIX_NOTES_ENABLED && EEG_HAS_ARDUINO_LED_MATRIX
  ledMatrix.begin();
  ledMatrix.clear();
  led_matrix_ready = true;
  return true;
#else
  return false;
#endif
}

static bool led_note(int pitch_midi, int velocity) {
  const uint8_t pitch = ledNoteClamp7(pitch_midi);
  const uint8_t vel = ledNoteClamp7(velocity);

  noInterrupts();
  led_note_pending_pitch = pitch;
  led_note_pending_velocity = vel;
  led_note_pending = true;
  interrupts();

  return ledMatrixNotesAvailable();
}

#if LED_MATRIX_NOTES_ENABLED && EEG_HAS_ARDUINO_LED_MATRIX
static void packLedNoteFrame(const uint8_t pixels[LED_NOTE_ROWS][LED_NOTE_COLS], uint32_t frame[4]) {
  frame[0] = 0;
  frame[1] = 0;
  frame[2] = 0;
  frame[3] = 0;

  for (uint8_t y = 0; y < LED_NOTE_ROWS; ++y) {
    for (uint8_t x = 0; x < LED_NOTE_COLS; ++x) {
      if (!pixels[y][x]) continue;

      const uint8_t idx = y * LED_NOTE_COLS + x;
      const uint8_t word = idx / 32;
      const uint8_t bit = 31 - (idx % 32);
      frame[word] |= (1UL << bit);
    }
  }
}

static void renderLedNote(uint8_t pitch_midi, uint8_t velocity) {
  uint8_t pixels[LED_NOTE_ROWS][LED_NOTE_COLS] = {};

  const uint8_t pitch_class = pitch_midi % 12;
  const int low_midi = 48;   // C3
  const int high_midi = 84;  // C6
  int clamped_pitch = pitch_midi;
  if (clamped_pitch < low_midi) clamped_pitch = low_midi;
  if (clamped_pitch > high_midi) clamped_pitch = high_midi;

  const int pitch_span = high_midi - low_midi;
  const uint8_t row = static_cast<uint8_t>(
      (LED_NOTE_ROWS - 1) -
      (((clamped_pitch - low_midi) * (LED_NOTE_ROWS - 1) + pitch_span / 2) / pitch_span)
  );

  pixels[row][pitch_class] = 1;

  // Una nota mas fuerte ocupa mas pixeles, sin intentar codificar texto.
  if (velocity >= 80 && row > 0) {
    pixels[row - 1][pitch_class] = 1;
  }
  if (velocity >= 96 && pitch_class > 0) {
    pixels[row][pitch_class - 1] = 1;
  }
  if (velocity >= 112 && pitch_class < 11) {
    pixels[row][pitch_class + 1] = 1;
  }

  uint8_t vel_height = static_cast<uint8_t>(((uint16_t)velocity * LED_NOTE_ROWS + 126) / 127);
  if (vel_height < 1) vel_height = 1;
  for (uint8_t i = 0; i < vel_height && i < LED_NOTE_ROWS; ++i) {
    pixels[(LED_NOTE_ROWS - 1) - i][LED_NOTE_VELOCITY_COL] = 1;
  }

  uint32_t frame[4];
  packLedNoteFrame(pixels, frame);
  ledMatrix.loadFrame(frame);
}
#endif

static void serviceLedMatrixNotes() {
#if LED_MATRIX_NOTES_ENABLED && EEG_HAS_ARDUINO_LED_MATRIX
  if (!led_matrix_ready) return;

  bool has_pending = false;
  uint8_t pitch = 60;
  uint8_t velocity = 0;

  noInterrupts();
  if (led_note_pending) {
    has_pending = true;
    pitch = led_note_pending_pitch;
    velocity = led_note_pending_velocity;
    led_note_pending = false;
  }
  interrupts();

  if (has_pending) {
    renderLedNote(pitch, velocity);
    led_note_visible = true;
    led_note_clear_at_ms = millis() + LED_NOTE_HOLD_MS;
  }

  if (led_note_visible && (int32_t)(millis() - led_note_clear_at_ms) >= 0) {
    ledMatrix.clear();
    led_note_visible = false;
  }
#endif
}
