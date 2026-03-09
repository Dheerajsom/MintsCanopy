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
        time.sleep(0.01)
        
        # Read 92 bytes to match the struct format used below
        data = self.spi.xfer2([0x00] * 92)

        raw = bytes(data)
        # Struct requires 92 bytes: 48+8+2+2+20+8+1+1+2 = 92
        parsed = struct.unpack('<24H4HHHfffff4HBBH', raw)
        
        return True, parsed

    def close(self):
        self.spi.close()
    
if __name__ == "__main__":
    opc = OPCN3(bus=0, device=0)
    print("=== MINTS OPC-N3 Reader ===")
    
    try:
        opc.set_fan_laser(True)
        time.sleep(2)
        opc.read_histogram() # Dummy read
        time.sleep(1)

        while True:
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
                    ("temperature",          str(d[30] * 1000)), 
                    ("humidity",             str(d[31] * 500)),
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

                print(f"PM2.5: {sensorDictionary['pm2_5']:.2f} | Temp: {d[30]:.1f}C")
                mSR.sensorFinisher(dateTime, "OPCN3", sensorDictionary)

            time.sleep(1)

    except KeyboardInterrupt:
        opc.set_fan_laser(False)
        opc.close()