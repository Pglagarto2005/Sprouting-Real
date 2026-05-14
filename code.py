#include <WiFi.h>
#include <WebServer.h>
#include <Servo.h>

const char* ssid = "TU_WIFI";
const char* password = "TU_PASSWORD";

WebServer server(80);

Servo servoMotor;

int sensorPin = 34;
int humedad = 0;

void setup() {

  Serial.begin(115200);

  servoMotor.attach(13);

  WiFi.begin(ssid, password);

  while (WiFi.status() != WL_CONNECTED) {
    delay(1000);
    Serial.println("Conectando...");
  }

  Serial.println(WiFi.localIP());

  server.on("/humedad", HTTP_GET, []() {

    humedad = analogRead(sensorPin);

    int porcentaje = map(humedad, 4095, 0, 0, 100);

    String json = "{\"humedad\":" + String(porcentaje) + "}";

    server.send(200, "application/json", json);
  });

  server.on("/regar", HTTP_GET, []() {

    servoMotor.write(90);

    delay(2000);

    servoMotor.write(0);

    server.send(200, "text/plain", "Regando planta");
  });

  server.begin();
}

void loop() {
  server.handleClient();
}
