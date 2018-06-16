# Pi-GPIO-Monitoring
Flask Controller example to monitor Raspberry Pi 2 GPIOs 

GPIOs to be monitored are stored in the DB, you can open the gpio.sql to check for the table structure

Features:
- Enables/disables individual GPIO monitoring
- Records description from individual GPIO
- Shows the number of times one GPIO input has changed from high to low
- Shows GPIO current status
- Enable/disable Ajax update of the GPIO counters and statuses
- Sets the Ajax refresh time for GPIO counters and statuses
- Clears GPIO counters
- Export Data to CSV file
