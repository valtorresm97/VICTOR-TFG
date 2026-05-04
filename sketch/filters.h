#pragma once
#include <Arduino.h>
#include <math.h>
#include <stdint.h>
#include <limits.h>

static inline int32_t round_to_i32(float x) {
  // redondeo clásico "half away from zero"
  if (x >= 0.0f) x += 0.5f;
  else          x -= 0.5f;

  // saturación por seguridad
  if (x > 2147483647.0f)  return INT32_MAX;
  if (x < -2147483648.0f) return INT32_MIN;
  return (int32_t)x;
}

static inline int32_t volts_to_uV_i32(float v) {
  return round_to_i32(v * 1e6f);
}


static constexpr float PI_F = 3.14159265358979323846f;

struct DCBlocker {
  float R = 0.0f;
  float x1 = 0.0f;
  float y1 = 0.0f;

  void init(float fc_hz, float fs_hz) {
    R = expf(-2.0f * PI_F * fc_hz / fs_hz);
    x1 = 0.0f;
    y1 = 0.0f;
  }

  float process(float x) {
    float y = x - x1 + R * y1;
    x1 = x;
    y1 = y;
    return y;
  }
};

struct Biquad {
  // Direct Form II Transposed
  float b0=1, b1=0, b2=0, a1=0, a2=0;
  float z1=0, z2=0;

  void reset() { z1 = 0.0f; z2 = 0.0f; }

  float process(float x) {
    float y = b0 * x + z1;
    z1 = b1 * x - a1 * y + z2;
    z2 = b2 * x - a2 * y;
    return y;
  }
};

inline Biquad makeNotch(float f0_hz, float fs_hz, float r) {
  float w0 = 2.0f * PI_F * (f0_hz / fs_hz);
  float c  = cosf(w0);

  Biquad q;
  q.b0 = 1.0f;
  q.b1 = -2.0f * c;
  q.b2 = 1.0f;
  q.a1 = -2.0f * r * c;
  q.a2 = r * r;
  q.reset();
  return q;
}

inline Biquad makeLowpassRBJ(float fc_hz, float fs_hz, float Q) {
  float w0 = 2.0f * PI_F * (fc_hz / fs_hz);
  float s  = sinf(w0);
  float c  = cosf(w0);
  float alpha = s / (2.0f * Q);

  float b0 = (1.0f - c) * 0.5f;
  float b1 = (1.0f - c);
  float b2 = (1.0f - c) * 0.5f;
  float a0 = 1.0f + alpha;
  float a1 = -2.0f * c;
  float a2 = 1.0f - alpha;

  Biquad q;
  q.b0 = b0 / a0;
  q.b1 = b1 / a0;
  q.b2 = b2 / a0;
  q.a1 = a1 / a0;
  q.a2 = a2 / a0;
  q.reset();
  return q;
}