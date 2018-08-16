# RPiCluster2


Yet another Raspberry Pi cluster, which can
**chain up to 1+32 Raspberry Pi's**!!!

![Diagram](https://github.com/Terminus-IMRC/RPiCluster2/raw/master/img/diagram.png)

The Pi on the Motherboard (master) is always turned on, while the other Pi's
(slaves) are turned on/off by the master via I2C.  The master can choose a slave
to communicate with over UART.
