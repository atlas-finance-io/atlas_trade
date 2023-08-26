from ib_insync import * 
import pandas as pd
import numpy as np
import datetime as dt
import os
import time

ib = IB()
ib.connect('127.0.0.1', 7497, clientId=1)
time.sleep(2)


# Strategy Parameters

frequency = "1 min" # Frequency of bars
window = 1
ib.