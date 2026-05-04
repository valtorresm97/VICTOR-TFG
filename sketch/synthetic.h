#pragma once
#include <Arduino.h>
#include <math.h>
#include <stdint.h>

#ifndef PI_F
#endif

// Rango útil ADS1299: 24-bit signed (2's complement)
static constexpr int32_t ADS_MIN = -8388608;  // -2^23
static constexpr int32_t ADS_MAX =  8388607;  //  2^23 - 1

static inline uint32_t xorshift32(uint32_t &s) {
  s ^= s << 13;
  s ^= s >> 17;
  s ^= s << 5;
  return s;
}

// [-1, 1]
static inline float randCentered(uint32_t &s) {
  uint32_t r = xorshift32(s);
  // 24-bit mantissa-ish
  float u = (float)(r & 0x00FFFFFF) / 16777215.0f; // [0,1]
  return 2.0f * u - 1.0f;
}

static inline int32_t clamp24(int32_t x) {
  if (x < ADS_MIN) return ADS_MIN;
  if (x > ADS_MAX) return ADS_MAX;
  return x;
}

// Genera un "EEG-like" por canal en microvoltios: mezcla alpha/beta, drift, hum 50Hz y ruido
static inline float synthEEG_uV(float t_s, uint8_t ch, uint32_t &rng) {
  // Fases por canal para que no sean idénticos
  float ph0 = 0.35f * ch;
  float ph1 = 0.71f * ch;
  float ph2 = 1.13f * ch;
  float ph3 = 1.57f * ch;

  // Modulaciones lentas de amplitud (simulan cambios de estado)
  float env_delta = 0.65f + 0.35f * sinf(2.0f * PI_F * 3.05f * t_s + 0.2f * ch);
  float env_theta = 0.70f + 0.30f * sinf(2.0f * PI_F * 2.08f * t_s + 0.5f + 0.3f * ch);
  float env_alpha = 0.75f + 0.25f * sinf(2.0f * PI_F * 1.12f * t_s + 1.0f + 0.4f * ch);
  float env_beta  = 0.60f + 0.40f * sinf(2.0f * PI_F * 1.18f * t_s + 1.7f + 0.2f * ch);
  float env_gamma = 0.50f + 0.50f * sinf(2.0f * PI_F * 3.10f * t_s + 2.1f + 0.1f * ch);

  // Componentes EEG principales
  float delta = env_delta * 22.0f * sinf(2.0f * PI_F * 2.0f  * t_s + ph0);  // 2 Hz
  float theta = env_theta * 16.0f * sinf(2.0f * PI_F * 6.0f  * t_s + ph1);  // 6 Hz
  float alpha = env_alpha * 28.0f * sinf(2.0f * PI_F * 10.0f * t_s + ph2);  // 10 Hz
  float beta  = env_beta  * 11.0f * sinf(2.0f * PI_F * 20.0f * t_s + ph3);  // 20 Hz
  float gamma = env_gamma *  4.0f * sinf(2.0f * PI_F * 38.0f * t_s + 0.9f * ch); // 38 Hz

  // Deriva lenta y respiración muy baja frecuencia
  float drift = 18.0f * sinf(2.0f * PI_F * 0.20f * t_s + 0.15f * ch);
  float slow2 = 10.0f * sinf(2.0f * PI_F * 0.07f * t_s + 0.8f);

  // Interferencia de red para probar notch
  float hum50 = 8.0f * sinf(2.0f * PI_F * 50.0f * t_s + 0.1f * ch);

  // Ruido blanco simple
  float noise = 5.0f * randCentered(rng);

  // Pequeño burst beta ocasional, suave y periódico
  float burst_env = 0.5f + 0.5f * sinf(2.0f * PI_F * 0.035f * t_s + 0.6f * ch);
  float beta_burst = burst_env * 6.0f * sinf(2.0f * PI_F * 24.0f * t_s + 0.4f * ch);

  return delta + theta + alpha + beta + gamma + beta_burst + drift + slow2 + hum50 + noise;
}

// Convierte uV -> raw counts usando LSB_V (V/count)
static inline int32_t uV_to_rawCounts(float uV, float LSB_V) {
  float v = uV * 1e-6f;
  float counts = v / LSB_V;

  // Redondeo manual (evita lroundf)
  if (counts >= 0.0f) counts += 0.5f;
  else                counts -= 0.5f;

  int32_t c = (int32_t)counts;
  return clamp24(c);
}

// Llena ch_raw[] como si viniera del ADS1299
static inline void generateSyntheticRaw(uint32_t sample_idx,
                                        float fs_hz,
                                        float LSB_V,
                                        int32_t *ch_raw,
                                        uint8_t nchan,
                                        uint32_t &rng) {
  float t = (float)sample_idx / fs_hz;
  for (uint8_t i = 0; i < nchan; ++i) {
    float uV = synthEEG_uV(t, i, rng);
    ch_raw[i] = uV_to_rawCounts(uV, LSB_V);
  }
}