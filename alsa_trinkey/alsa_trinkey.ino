#include <Adafruit_NeoPixel.h>
#include "Adafruit_FreeTouch.h"

// Create the neopixel strip with the built in definitions NUM_NEOPIXEL and PIN_NEOPIXEL
Adafruit_NeoPixel strip = Adafruit_NeoPixel(NUM_NEOPIXEL, PIN_NEOPIXEL, NEO_GRB + NEO_KHZ800);

// Create the two touch pads on pins 1 and 2:
Adafruit_FreeTouch qt_1 = Adafruit_FreeTouch(1, OVERSAMPLE_4, RESISTOR_50K, FREQ_MODE_NONE);
Adafruit_FreeTouch qt_2 = Adafruit_FreeTouch(2, OVERSAMPLE_4, RESISTOR_50K, FREQ_MODE_NONE);



int16_t neo_brightness = 20; // initialize with 20 brightness (out of 255)
uint32_t greenishwhite = strip.Color(0, 64, 0, 64);
uint32_t blueishwhite = strip.Color(0, 0, 64, 64);
uint32_t redishwhite = strip.Color(64, 0, 0, 64);

uint32_t black = strip.Color(0,0,0);
uint32_t yellow = strip.Color(255, 255,0);
uint32_t orange = strip.Color(255, 140, 0);
uint32_t cyan = strip.Color(0, 255, 255);
uint32_t lightcyan = strip.Color(102,205,170);
uint32_t darkcyan = strip.Color(0, 128, 128);
uint32_t lightmagenta=strip.Color(238, 130, 238);
uint32_t magenta = strip.Color(255, 0, 255);
uint32_t cream = strip.Color(250, 250, 210);
uint32_t white = strip.Color(255,255,255);
uint32_t red = strip.Color(255,0,0);
uint32_t darkred = strip.Color(139, 0, 0);
uint32_t green = strip.Color(0,255,0);
uint32_t blue = strip.Color(0,0,255);

//                        off  44.1   48      88.2      96          176         192      365   384   error
uint32_t sample_cols[]={black,yellow,orange,lightcyan,darkcyan, lightmagenta, magenta, cream, white, darkred};
//                      off  16     24    32    error
uint32_t bit_cols[] = {black,red, green, blue, darkred};

int x=0;


void setup() {
  Serial.begin(115200);
  Serial.setTimeout(1);
  qt_1.begin();
  qt_2.begin();
  strip.begin();
  strip.setBrightness(neo_brightness);
  strip.show(); // Initialize all pixels to 'off'
}
void loop() {
  //while (!Serial.available());
  if (Serial.available()>0){
  x = Serial.readString().toInt();
  strip.setPixelColor(0,bit_cols[(x % 8)]);
  strip.fill(sample_cols[x / 8],1,NUM_NEOPIXEL);
  strip.show();
  }


    // measure the captouches
    uint16_t touch1 = qt_1.measure();
    uint16_t touch2 = qt_2.measure();

    // If the first pad is touched, reduce brightness
    if (touch1 > 500) {
      strip.setPixelColor(0,bit_cols[(x % 8)]);
      strip.fill(sample_cols[x / 8],1,NUM_NEOPIXEL);
      strip.show();
      // subtract 1 from brightness but dont go below 0
      neo_brightness = max(0, neo_brightness-1);
      //Serial.print("New brightness: "); Serial.println(neo_brightness);
      strip.setBrightness(neo_brightness);
    }

    // If the second pad is touched, increase brightness
    if (touch2 > 500) {
      strip.setPixelColor(0,bit_cols[(x % 8)]);
      strip.fill(sample_cols[x / 8],1,NUM_NEOPIXEL);
      strip.show();
      // add 1 to brightness but dont go above 255
      neo_brightness = min(255, neo_brightness+1);
      //Serial.print("New brightness: "); Serial.println(neo_brightness);
      strip.setBrightness(neo_brightness);
    }

    delay(100);

}