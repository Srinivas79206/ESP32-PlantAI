void setup() {

  Serial.begin(9600);

  Serial.println("ESP32 Ready");
}

void loop() {

  if (Serial.available()) {

    String msg =
      Serial.readStringUntil('\n');

    msg.trim();

    Serial.print("Received: ");
    Serial.println(msg);

    if (msg == "DISEASED") {

      Serial.println(
        "Disease Detected!"
      );
    }

    else if (msg == "HEALTHY") {

      Serial.println(
        "Plant Healthy"
      );
    }
  }
}