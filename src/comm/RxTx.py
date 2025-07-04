import time
import gpiod

print(f"gpiod file: {gpiod.__file__}")
print(f"gpiod version: {gpiod.__version__}")

RECEIVE_LINE = 27   # GPIO.BOARD 11 → GPIO27
TRANSMIT_LINE = 22  # GPIO.BOARD 7  → GPIO22

CHIP = "/dev/gpiochip0"

class RxTx:
    def __init__(self, codes={}):
        self._codes = codes
        self.chip = gpiod.Chip(CHIP)

        # --- Request input line ---
        in_config = gpiod.LineSettings()
        in_config.direction = gpiod.LineDirection.INPUT

        self.in_request = self.chip.request_lines(
            config=in_config,
            consumer="rxtx_rx",
            lines=[RECEIVE_LINE]
        )

        # --- Request output line ---
        out_config = gpiod.LineSettings()
        out_config.direction = gpiod.LineDirection.OUTPUT

        self.out_request = self.chip.request_lines(
            config=out_config,
            consumer="rxtx_tx",
            lines=[TRANSMIT_LINE]
        )

        # Set initial output low
        self.out_request.set_values([0])

    def _read(self):
        return self.in_request.get_values()[0]

    def _set_output(self, v):
        self.out_request.set_values([v])

    def _createBuffer(self, start_time, mode=1):
        if mode not in (0, 1):
            raise ValueError("Mode must be 0 or 1")
        buffer, t = [], 0
        while len(buffer) < 200:
            dt = time.time() - start_time
            bit = self._read()
            if bit == mode:
                t += dt
            else:
                if t:
                    buffer.append(t)
                t = 0
            start_time = time.time()
        return buffer

    def _processBuffer(self, buffer, mode=1):
        if mode not in (0, 1):
            raise ValueError("Mode must be 0 or 1")
        codes = []
        length = len(buffer)
        if mode == 1:
            for i in range(length - 25):
                segment = buffer[i:i+25]
                lmax, lmin = max(segment), min(segment)
                thresh = (lmax - lmin) / 3 + lmin
                out = ''.join('1' if x < thresh else '0' for x in segment)
                if out not in codes:
                    codes.append(out)
        else:
            for i in range(length - 25):
                segment = buffer[i:i+25]
                lmax, lmin = max(segment), min(segment)
                idx = segment.index(lmax) + i
                if idx == i:
                    new_seg = buffer[i+1:i+25]
                    lmax2 = max(new_seg)
                    thresh = (lmax2 - lmin) / 3 + lmin
                    out = ''.join('0' if x < thresh else '1' for x in new_seg)
                    if out not in codes:
                        codes.append(out)
        return codes

    def _sniffTiming(self, start_time):
        buffer = []
        temp_bit = self._read()
        buffer.append(0.0)
        while len(buffer) < 1000:
            dt = time.time() - start_time
            bit = self._read()
            if bit != temp_bit:
                buffer.append(dt)
                temp_bit = bit
                start_time = time.time()

        POWER = 1e5
        simp = [int(POWER * b) for b in buffer]
        interval_raw = max(simp)
        idx = simp.index(interval_raw)
        interval = interval_raw / POWER

        one_high = one_low = zero_high = zero_low = None
        while idx + 2 < len(simp):
            first, second = simp[idx+1], simp[idx+2]
            if first < second:
                one_high, one_low = first/POWER, second/POWER
            else:
                zero_high, zero_low = first/POWER, second/POWER
            if None not in (one_high, one_low, zero_high, zero_low):
                break
            idx += 2

        return one_high, one_low, zero_high, zero_low, interval

    def rxCode(self, runTime=None):
        start_time = time.time()
        while True:
            if runTime and (time.time() - start_time) > runTime:
                return None
            buffer = self._createBuffer(start_time, mode=1)
            codes = self._processBuffer(buffer, mode=1)
            for key, known in self._codes.items():
                if known in codes:
                    return key

    def txCode(self, code, one_high, one_low, zero_high, zero_low, interval):
        for _ in range(10):
            for bit in code:
                if bit == '1':
                    self._set_output(1)
                    time.sleep(one_high)
                    self._set_output(0)
                    time.sleep(one_low)
                else:
                    self._set_output(1)
                    time.sleep(zero_high)
                    self._set_output(0)
                    time.sleep(zero_low)
            self._set_output(0)
            time.sleep(interval)

    def sniffCode(self, seekTime=2):
        start_time = time.time()
        while time.time() - start_time < seekTime:
            low_buf = self._createBuffer(start_time, mode=0)
            low_codes = self._processBuffer(low_buf, mode=0)
            high_buf = self._createBuffer(start_time, mode=1)
            high_codes = self._processBuffer(high_buf, mode=1)
            timings = self._sniffTiming(time.time())
            for hi in high_codes:
                for lo in low_codes:
                    if lo == hi[:-1]:
                        return (hi, *timings)
        return None

    def cleanup(self):
        self._set_output(0)
        self.in_request.release()
        self.out_request.release()
        self.chip.close()
