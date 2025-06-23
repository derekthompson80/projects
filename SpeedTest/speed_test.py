import speedtest

def check_internet_speed(log_file="speed_log.txt"):
    """
    Checks internet speed using speedtest-cli and logs the results to a text file.

    Args:
        log_file (str): The name of the log file to write results to. Defaults to "speed_log.txt".
    """

    try:
        st = speedtest.Speedtest()
        st.get_best_server()

        download_speed = st.download() / 1000000  # Convert to Mbps
        upload_speed = st.upload() / 1000000  # Convert to Mbps

        # Get current timestamp
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")

        # Log the results to a text file
        with open(log_file, "a") as f:  # Open in append mode
            f.write(f"{timestamp}: Download Speed = {download_speed:.2f} Mbps, Upload Speed = {upload_speed:.2f} Mbps\n")

        print(f"Speed test results logged to {log_file}")


    except Exception as e:
        print(f"An error occurred: {e}")

import time
if __name__ == "__main__":
    check_internet_speed()  # Call the function to run the speed test and log results