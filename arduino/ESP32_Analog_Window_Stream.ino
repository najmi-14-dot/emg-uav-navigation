/* ESP32 analog feature stream. NO synthetic readings.
   IMPORTANT: Never attach body electrodes until a qualified technician
   has verified medical/electrical isolation, board supply, and that the
   analog input stays within ESP32 safe voltage limits.
   A 0..4095 ADC reading does NOT verify safe input voltage.
   This sketch alone does not make a body-connected system safe.
   Input: GPIO34 from an independently verified, safe 0..3.3 V source.
   Output: min,max,mean,population_stddev at 115200 baud.
   Sampling: 200 Hz, 200 samples/window (1 second).
   Re-train/validate the classifier if acquisition settings differ.
*/
#include <math.h>
const int inputPin = 34;
const int sampleCount = 200;
const unsigned long intervalUs = 5000;
void setup() {
  Serial.begin(115200);
  analogReadResolution(12);
  analogSetPinAttenuation(inputPin, ADC_11db);
}
void loop() {
  int mn = 4095, mx = 0;
  double sum = 0, sq = 0;
  unsigned long nextSample = micros();
  for (int i=0; i<sampleCount; ++i) {
    while ((long)(micros() - nextSample) < 0) {}
    nextSample += intervalUs;
    int v = analogRead(inputPin);
    if (v < mn) mn = v;
    if (v > mx) mx = v;
    sum += v;
    sq += (double)v*v;
  }
  double mean = sum / sampleCount;
  double variance = sq/sampleCount - mean*mean;
  if (variance < 0) variance = 0;
  Serial.print(mn); Serial.print(',');
  Serial.print(mx); Serial.print(',');
  Serial.print(mean, 2); Serial.print(',');
  Serial.println(sqrt(variance), 2);
}
