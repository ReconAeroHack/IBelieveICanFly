import socket
import select
import time

# -----------------------------------------------------------
# WiFi TCP CONNECTION
# Drone acts as Access Point
# Connect your PC to drone's WiFi before running
# -----------------------------------------------------------
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect(("192.168.4.1", 8080))

# -----------------------------------------------------------
# CORE COMMUNICATION
# -----------------------------------------------------------
def empty_socket(sock):
    """Flush old data from buffer before sending new command"""
    input_ready, _, _ = select.select([sock], [], [], 0.0)
    while input_ready:
        data = sock.recv(1)
        if not data:
            break
        input_ready, _, _ = select.select([sock], [], [], 0.0)

def msg(tx):
    """Send command to drone and return response via WiFi TCP"""
    empty_socket(s)
    s.sendall((tx + "\n").encode("ASCII"))
    rx = ""
    while not rx.endswith("\n"):
        rx += s.recv(1).decode("ASCII")
    return rx[:-1]

# -----------------------------------------------------------
# DRONE CONTROL FUNCTIONS
# -----------------------------------------------------------
def emergency_stop():
    msg("mode0")

def e():
    emergency_stop()

def set_mode(m):
    # mode 0: off
    # mode 1: full manual motor control
    # mode 2: PID control for pitch and roll
    msg("mode" + str(m))

def get_mode():
    return msg("gMode")

def manual_thrusts(A, B, C, D):
    # always between 0 and 250
    # in mode 2 sets baseline value, PID results are added to it
    msg("manT\n" + str(A) + "," + str(B) + "," + str(C) + "," + str(D) + "\n")

def increment_thrusts(A, B, C, D):
    msg("incT\n" + str(A) + "," + str(B) + "," + str(C) + "," + str(D) + "\n")

# -----------------------------------------------------------
# MPU6050 SENSOR FUNCTIONS (data transferred via WiFi)
# -----------------------------------------------------------
def get_pitch():
    # tilt forward/back — unit close to degrees
    return float(msg("angX")) / 16

def get_roll():
    # tilt left/right — unit close to degrees
    return float(msg("angY")) / 16

def get_gyro_pitch():
    # pitch rotation rate in degrees/sec
    return float(msg("gyroX"))

def get_gyro_roll():
    # roll rotation rate in degrees/sec
    return float(msg("gyroY"))

def get_i_values():
    # returns [I_x, I_y] integrands from pitch and roll PID loops
    resp = msg("geti").split(",")
    return [float(resp[0]), float(resp[1])]

# -----------------------------------------------------------
# PID GAIN FUNCTIONS (drone's built-in PID)
# -----------------------------------------------------------
def set_p_gain(p):  # approx 0 - 0.5
    msg("gainP" + str(p))

def set_i_gain(i):  # below 0.00003
    msg("gainI" + str(i))

def set_d_gain(d):  # approx 0 - 10
    msg("gainD" + str(d))

def set_pitch(r):   # target pitch for mode 2
    msg("gx" + str(r))

def set_roll(r):    # target roll for mode 2
    msg("gy" + str(r))

def set_yaw(y):     # directly sets motor difference for yaw
    msg("yaw" + str(y))

def reset_integral():
    msg("irst")

# -----------------------------------------------------------
# LED FUNCTIONS
# -----------------------------------------------------------
def red_LED(val):   # 1 = on, 0 = off
    msg("lr" + str(val))

def blue_LED(val):
    msg("lb" + str(val))

def green_LED(val):
    msg("lg" + str(val))

# -----------------------------------------------------------
# FIRMWARE FUNCTIONS (requires firmware 1.2 or higher)
# -----------------------------------------------------------
def get_firmware_version():
    return msg("vers")

def lock_props():
    # use outside of cage — overrides all mode changes
    msg("lck")

def recalibrate():
    # recalibrates gyroscope
    # do NOT communicate with drone for 15 seconds after calling
    msg("rst")

# -----------------------------------------------------------
# HELPER
# -----------------------------------------------------------
def clamp(value, min_val=0, max_val=250):
    return max(min_val, min(max_val, int(value)))

# -----------------------------------------------------------
# MAIN
# -----------------------------------------------------------
if __name__ == "__main__":
    try:
        # Step 1 — confirm connection
        print("Connecting via WiFi TCP 192.168.4.1:8080...")
        print("Firmware version:", get_firmware_version())

        # Step 2 — recalibrate gyroscope (keep drone flat and still!)
        print("Calibrating gyroscope... do not move drone for 15 seconds")
        recalibrate()
        time.sleep(15)
        print("Calibration done!")

        # --------------------------------------------------
        # MODE 1 — manual motor test
        # --------------------------------------------------
        print("\nMode 1: Manual motor test...")
        set_mode(1)

        print("Spinning motors at low speed...")
        manual_thrusts(50, 50, 50, 50)
        time.sleep(3)

        set_mode(0)
        print("Mode 1 done!")
        time.sleep(1)

        # --------------------------------------------------
        # MODE 2 — drone built-in PID stabilized flight
        # --------------------------------------------------
        print("\nMode 2: PID stabilized flight...")
        set_mode(2)

        # Set drone's internal PID gains
        set_p_gain(0.3)     # proportional  (0 - 0.5)
        set_i_gain(0.00001) # integral      (below 0.00003)
        set_d_gain(5.0)     # derivative    (0 - 10)

        # Set targets — fly flat
        set_pitch(0)
        set_roll(0)
        set_yaw(0)
        reset_integral()

        # Spin up gradually
        print("Spinning up...")
        for thrust in range(0, 150, 5):
            manual_thrusts(thrust, thrust, thrust, thrust)
            time.sleep(0.1)

        # Hover loop
        BASE_THRUST = 150   # tune this:
                            # won't lift → increase (try 170)
                            # too fast   → decrease (try 130)

       # --------------------------------------------------
        # TEST 1 — increment pitch gradually (forward/back)
        # --------------------------------------------------
        print("\nTest 1: Incrementing pitch forward gradually...")
        for target_pitch in range(0, 10, 1):   # 0° to 10° forward
            set_pitch(target_pitch)
            manual_thrusts(BASE_THRUST, BASE_THRUST, BASE_THRUST, BASE_THRUST)

            pitch      = get_pitch()
            roll       = get_roll()
            i_vals     = get_i_values()

            print(
                f"Target Pitch: {target_pitch}°  |  "
                f"Actual Pitch: {pitch:.2f}°  "
                f"Roll: {roll:.2f}°  |  "
                f"I values: {i_vals}",
                end='\r'
            )
            time.sleep(0.5)     # wait 0.5s per step

        # Back to flat
        print("\nReturning pitch to 0...")
        for target_pitch in range(10, 0, -1):  # 10° back to 0°
            set_pitch(target_pitch)
            manual_thrusts(BASE_THRUST, BASE_THRUST, BASE_THRUST, BASE_THRUST)
            time.sleep(0.5)

        set_pitch(0)
        reset_integral()
        time.sleep(1)

        # --------------------------------------------------
        # TEST 2 — increment roll gradually (left/right)
        # --------------------------------------------------
        print("\nTest 2: Incrementing roll right gradually...")
        for target_roll in range(0, 10, 1):    # 0° to 10° right
            set_roll(target_roll)
            manual_thrusts(BASE_THRUST, BASE_THRUST, BASE_THRUST, BASE_THRUST)

            pitch      = get_pitch()
            roll       = get_roll()
            i_vals     = get_i_values()

            print(
                f"Target Roll: {target_roll}°  |  "
                f"Pitch: {pitch:.2f}°  "
                f"Actual Roll: {roll:.2f}°  |  "
                f"I values: {i_vals}",
                end='\r'
            )
            time.sleep(0.5)

        # Back to flat
        print("\nReturning roll to 0...")
        for target_roll in range(10, 0, -1):   # 10° back to 0°
            set_roll(target_roll)
            manual_thrusts(BASE_THRUST, BASE_THRUST, BASE_THRUST, BASE_THRUST)
            time.sleep(0.5)

        set_roll(0)
        reset_integral()
        time.sleep(1)

        # --------------------------------------------------
        # TEST 3 — increment both pitch and roll together
        # --------------------------------------------------
        print("\nTest 3: Incrementing pitch and roll together...")
        for target in range(0, 10, 1):
            set_pitch(target)
            set_roll(target)
            manual_thrusts(BASE_THRUST, BASE_THRUST, BASE_THRUST, BASE_THRUST)

            pitch      = get_pitch()
            roll       = get_roll()
            gyro_pitch = get_gyro_pitch()
            gyro_roll  = get_gyro_roll()
            i_vals     = get_i_values()

            print(
                f"Target: {target}°  |  "
                f"Pitch: {pitch:.2f}°  "
                f"Roll: {roll:.2f}°  |  "
                f"Gyro P: {gyro_pitch:.2f}°/s  "
                f"Gyro R: {gyro_roll:.2f}°/s  |  "
                f"I values: {i_vals}",
                end='\r'
            )
            time.sleep(0.5)

        # Return to flat
        print("\nReturning to flat...")
        set_pitch(0)
        set_roll(0)
        reset_integral()
        time.sleep(1)

        # --------------------------------------------------
        # LAND
        # --------------------------------------------------
        print("\nLanding...")
        for thrust in range(BASE_THRUST, 0, -5):
            manual_thrusts(thrust, thrust, thrust, thrust)
            time.sleep(0.1)

        set_mode(0)
        print("Landed!")

    except KeyboardInterrupt:
        print("\nEmergency stop!")
        emergency_stop()

    finally:
        s.close()
        print("Connection closed. Done!")