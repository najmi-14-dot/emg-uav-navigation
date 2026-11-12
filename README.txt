EMG-UAV CONTROL CENTER — Streamlit + Plotly + Power BI CSV
=======================================================

WHAT IS INCLUDED
- app.py: modern dashboard with live ESP32 serial readings, Random Forest
  predictions, 2D UAV simulation, stop/resume/reset and CSV data logging.
- requirements.txt: Python dependencies.
- START_DASHBOARD.bat: optional launcher (works when Python is on PATH).
- arduino/ESP32_Analog_Window_Stream.ino: analog acquisition sketch.

IMPORTANT: THE TRAINED MODEL IS NOT INCLUDED.
Copy your existing trusted file:
    emg_improved_model_experimental.pkl
into the same folder as app.py. The dashboard will NOT invent a model,
recordings or predictions. Without this model it shows a clear error.

SETUP — WINDOWS / ANACONDA PROMPT
1. Extract this ZIP into Documents or another folder.
2. Open ANACONDA PROMPT (not ordinary Windows CMD if Python is not on PATH).
3. Change directory to the extracted EMG_UAV_Control_Center folder:
   cd /d "C:\Users\User\Documents\EMG_UAV_Control_Center"
   (adjust path if you extracted it elsewhere)
4. Install dependencies:
   python -m pip install -r requirements.txt
5. Copy emg_improved_model_experimental.pkl into this folder.
6. Ensure ESP32 is transmitting 4 comma-separated numbers per line at
   115200 baud: Minimum_ADC,Maximum_ADC,Average_ADC,StdDev_ADC.
   Close Arduino Serial Monitor and all other COM-port users.
7. Run:
   python -m streamlit run app.py
8. In the browser, select the correct COM port and click Connect.
   Click RESUME SIMULATION to enable software-only UAV movement.
9. Stop the server with Ctrl+C in Anaconda Prompt.

POWER BI
- The dashboard writes emg_live_log.csv once valid readings arrive.
- Power BI Desktop: Home > Get Data > Text/CSV > select emg_live_log.csv.
- Charts: Timestamp vs Average_ADC; Predicted_Gesture counts;
  Timestamp vs Model_Score; Command counts; UAV_X vs UAV_Y.
- Refresh imported data to see updates. Importing CSV is NOT real-time
  Power BI streaming; Streamlit is the live control dashboard.
- The log has predictions, NOT verified gesture labels; do not report
  classification accuracy from this log without ground truth.

SAFETY
- This ZIP does NOT generate fake sensor readings.
- The Arduino sketch only reads GPIO34. It is NOT safe to attach your
  EMG electrodes based on this sketch alone.
- Previous sensor identification and bipolar power details are unresolved.
  Do NOT connect body electrodes until a qualified technician confirms
  sensor identity, isolation, safe power and ADC voltage compatibility.
- The STOP button controls ONLY the 2D simulation, not a physical UAV.
- Model score is not calibrated confidence.
- 200 Hz analog sampling may be unsuitable for raw sEMG; confirm the
  sensor output and match/retrain for acquisition conditions.

TROUBLESHOOTING
- "Python was not found": use Anaconda Prompt; check python --version.
- "No module named streamlit": run the pip install command above.
- "Missing trained model": copy your own .pkl into the app folder.
- SerialException: close Arduino Serial Monitor; verify selected COM port.
- No recordings: verify 4 comma-separated values at 115200 baud.
- UAV stays still: click RESUME; model needs 3 consecutive predictions
  with score >= threshold. This is expected for unrecognized signals.
