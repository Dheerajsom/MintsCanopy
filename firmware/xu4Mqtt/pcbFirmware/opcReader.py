import spidev
import time
import struct
import datetime
from collections import OrderedDict
from mintsXU4 import mintsSensorReader as mSR
from mintsXU4 import mintsDefinitions  as mD

class OPCN3:
    def __init__(self, bus=0, device=0):
        self.spi = spidev.SpiDev()
        self.spi.open(bus, device)
        self.spi.max_speed_hz = 500000 
        self.spi.mode = 1
        
    def _wait_for_ready(self, timeout=5):
        """Polls the sensor until it responds with the 0xF3 ready byte"""
        start = time.time()
        while time.time() - start < timeout:
            if self.spi.xfer2([0x00])[0] == 0xF3:
                return True
            time.sleep(0.001)
        raise TimeoutError("OPC-N3 not ready")
    
    def set_fan_laser(self, on=True):
        self.spi.xfer2([0x03])
        time.sleep(0.01)
        if on:
            self.spi.xfer2([0x07]) # Fan and Laser ON
        else:
            self.spi.xfer2([0x00]) # Fan and Laser OFF
        return True

    def read_histogram(self):
        """Reads the histogram and unpacks all fields"""
        self.spi.xfer2([0x30])
        self._wait_for_ready()  # Poll for 0xF3
        
        data = self.spi.xfer2([0x00] * 86)
        raw = bytes(data)

        # Unpacking data according to the OPC-N3 specification
        
        # 48 + 4 + 8 + 12 + 4 + 2 + 1 + 2 = 81 bytes used from 86
        # indices: 0-23  24-27  28-31  32-34  35-38  39  40  41
        parsed = struct.unpack('<24H 4B HHHH fff 4B H B H', raw[:81])
        
        return True, parsed

    def close(self):
        self.spi.close()
    
if __name__ == "__main__":
    opc = OPCN3(bus=0, device=0)
    print("=== MINTS OPC-N3 Reader ===")
    
    try:
        opc.set_fan_laser(True)
        time.sleep(2)
        
        try:
            opc.read_histogram() # Dummy read
        except TimeoutError:
            print("Initial dummy read timed out. Skipping to main loop...")
            
        time.sleep(1)

        while True:
            try:
                result = opc.read_histogram()
                if result:
                    valid_bool, d = result
                    dateTime = datetime.datetime.now()

                    sensorDictionary = OrderedDict([
                        ("dateTime", str(dateTime)),
                        ("valid", "1" if valid_bool else "0"),
                    ])
                    
                    for i in range(24):
                        sensorDictionary[f"binCount{i}"] = d[i]
                    
                    sensorDictionary.update([
                        ("bin1TimeToCross",      d[24]),
                        ("bin3TimeToCross",      d[25]),
                        ("bin5TimeToCross",      d[26]),
                        ("bin7TimeToCross",      d[27]),
                        ("samplingPeriod",       d[28]),
                        ("sampleFlowRate",       d[29]),
                        ("temperature",          str((d[30] / 10.0) - 273.15)), 
                        ("humidity",             str(d[31] / 10.0)),
                        ("pm1",                  d[32]),
                        ("pm2_5",                d[33]),
                        ("pm10",                 d[34]),
                        ("rejectCountGlitch",    d[35]),
                        ("rejectCountLongTOF",   d[36]),
                        ("rejectCountRatio",     d[37]),
                        ("rejectCountOutOfRange",d[38]),
                        ("fanRevCount",          d[39]),
                        ("laserStatus",          d[40]),
                        ("checkSum",             d[41])
                    ])

                    print(f"PM2.5: {d[33]:.2f} | Temp: {(d[30]/10.0)-273.15:.1f}C")
                    mSR.sensorFinisher(dateTime, "OPCN3", sensorDictionary)
            
            except TimeoutError as e:
                print(f"SPI Read Error: {e}")

            time.sleep(1)

    except KeyboardInterrupt:
        opc.set_fan_laser(False)
        opc.close()