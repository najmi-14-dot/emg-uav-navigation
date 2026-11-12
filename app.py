import csv
import time
from collections import deque
from datetime import datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import serial
import serial.tools.list_ports
import streamlit as st

BASE = Path(__file__).resolve().parent
MODEL_PATH = BASE / 'emg_improved_model_experimental.pkl'
LOG_PATH = BASE / 'emg_live_log.csv'
FEATURES = ['Minimum_ADC', 'Maximum_ADC', 'Average_ADC', 'StdDev_ADC']
COMMANDS = {'REST':'HOVER','FIST':'HOLD POSITION','UP':'MOVE FORWARD','DOWN':'MOVE BACKWARD','LEFT':'MOVE LEFT','RIGHT':'MOVE RIGHT','FLIP':'NO ACTION'}
STABLE_WINDOWS = 3
TIMEOUT = 3.0

st.set_page_config(page_title='EMG-UAV Control Center', page_icon='🚁', layout='wide')
st.markdown('''<style>.stApp{background:#081120;color:#e8f1ff}div[data-testid="stMetric"]{background:#14243a;border:1px solid #24445f;border-radius:16px;padding:14px}h1,h2,h3{color:#5ce7f4}</style>''', unsafe_allow_html=True)

@st.cache_resource
def load_model(path, modified):
    return joblib.load(path)

if 'data' not in st.session_state:
    st.session_state.data = {
        'serial':None, 'port':None, 'last':0., 'count':0, 'gesture':'WAITING', 'score':0.,
        'command':'HOVER', 'features':[0.,0.,0.,0.], 'stopped':True,
        'adc':deque(maxlen=60), 'gestures':deque(maxlen=12),
        'stable':deque(maxlen=STABLE_WINDOWS), 'x':0., 'y':0., 'path_x':[0.], 'path_y':[0.],
        'status':'NOT CONNECTED', 'errors':0
    }
s = st.session_state.data

st.title('🚁 EMG-UAV CONTROL CENTER')
st.caption('Live ESP32 analog input → trained gesture classifier → 2D UAV simulation | No artificial readings or physical drone commands')

with st.sidebar:
    st.header('Connection & controls')
    ports = [p.device for p in serial.tools.list_ports.comports()]
    selected = st.selectbox('ESP32 serial port', options=ports or ['COM3'], index=0)
    threshold = st.slider('Model score threshold', 0.50, 0.99, 0.80, 0.01)
    st.caption('Score is a model estimate, not calibrated confidence.')
    if st.button('Connect', use_container_width=True):
        try:
            if s['serial'] is not None and s['serial'].is_open:
                s['serial'].close()
            s['serial'] = serial.Serial(selected, 115200, timeout=0)
            s['port'] = selected
            s['serial'].reset_input_buffer()
            s['last'] = 0.
            s['stable'].clear()
            s['status'] = 'WAITING FOR DATA'
            st.success(f'Opened {selected}')
        except (OSError, serial.SerialException) as exc:
            s['serial'] = None
            s['status'] = f'CONNECTION ERROR: {exc}'
            st.error(s['status'])
    if st.button('Disconnect', use_container_width=True):
        if s['serial'] is not None:
            try: s['serial'].close()
            except (OSError, serial.SerialException): pass
        s['serial'] = None
        s['stable'].clear()
        s['command'] = 'HOVER'
        s['status'] = 'DISCONNECTED'
    if st.button('🛑 STOP SIMULATION', use_container_width=True):
        s['stopped'] = True
        s['stable'].clear()
        s['command'] = 'HOVER'
    if st.button('▶ RESUME SIMULATION', use_container_width=True):
        s['stopped'] = False
        s['stable'].clear()
    if st.button('↺ RESET POSITION', use_container_width=True):
        s['x'] = s['y'] = 0.
        s['path_x'], s['path_y'] = [0.], [0.]
        s['stable'].clear()
        s['command'] = 'HOVER'
    st.warning('SIMULATION ONLY. STOP is not a physical UAV emergency stop.')
    st.info('Do not attach body electrodes until a qualified technician verifies isolation, power and ESP32 ADC voltage compatibility.')

if not MODEL_PATH.exists():
    st.error('Missing trained model: emg_improved_model_experimental.pkl. Copy your own trusted model file into this folder. No demo predictions are fabricated.')
    st.stop()
try:
    model = load_model(str(MODEL_PATH), MODEL_PATH.stat().st_mtime)
except Exception as exc:
    st.error(f'Could not load trained model: {exc}')
    st.stop()


def log_row(values, gesture, score, command):
    row = {'Timestamp':datetime.now().isoformat(timespec='seconds'), **dict(zip(FEATURES, values)),
           'Predicted_Gesture':gesture, 'Model_Score':round(score, 5), 'Command':command,
           'UAV_X':s['x'], 'UAV_Y':s['y']}
    with LOG_PATH.open('a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=list(row))
        if f.tell() == 0: writer.writeheader()
        writer.writerow(row)


def read_new_windows():
    port = s['serial']
    if port is None or not port.is_open:
        s['status'] = 'NOT CONNECTED'
        s['command'] = 'HOVER'
        s['stable'].clear()
        return
    try:
        # Consume up to 8 complete lines per refresh, avoiding indefinite UI blocking.
        for _ in range(8):
            if port.in_waiting <= 0: break
            raw = port.readline().decode('utf-8', errors='ignore').strip()
            parts = raw.split(',')
            if len(parts) != 4:
                s['errors'] += 1
                continue
            try: values = [float(p) for p in parts]
            except ValueError:
                s['errors'] += 1
                continue
            lo, hi, avg, sd = values
            if not (all(np.isfinite(values)) and 0 <= lo <= avg <= hi <= 4095 and sd >= 0):
                s['errors'] += 1
                continue
            sample = pd.DataFrame([values], columns=FEATURES)
            gesture = str(model.predict(sample)[0])
            score = float(np.max(model.predict_proba(sample)[0]))
            s['features'], s['gesture'], s['score'] = values, gesture, score
            s['last'], s['count'] = time.monotonic(), s['count'] + 1
            s['adc'].append(avg)
            s['gestures'].append(gesture)
            if score >= threshold: s['stable'].append(gesture)
            else: s['stable'].clear()
            stable = len(s['stable']) == STABLE_WINDOWS and len(set(s['stable'])) == 1
            command = COMMANDS.get(gesture, 'HOVER') if stable and not s['stopped'] else 'HOVER'
            s['command'] = command
            if command == 'MOVE FORWARD': s['y'] += 1
            elif command == 'MOVE BACKWARD': s['y'] -= 1
            elif command == 'MOVE LEFT': s['x'] -= 1
            elif command == 'MOVE RIGHT': s['x'] += 1
            s['x'] = float(np.clip(s['x'], -10, 10))
            s['y'] = float(np.clip(s['y'], -10, 10))
            s['path_x'].append(s['x']); s['path_y'].append(s['y'])
            log_row(values, gesture, score, command)
        if s['last'] and time.monotonic() - s['last'] <= TIMEOUT:
            s['status'] = 'RECEIVING LIVE DATA'
        else:
            s['status'] = 'WAITING / TIMED OUT'
            s['command'] = 'HOVER'
            s['stable'].clear()
    except (OSError, serial.SerialException) as exc:
        s['status'] = f'SERIAL ERROR: {exc}'
        s['command'] = 'HOVER'
        s['stable'].clear()
        try: port.close()
        except Exception: pass
        s['serial'] = None


@st.fragment(run_every='1s')
def live():
    read_new_windows()
    c1,c2,c3,c4 = st.columns(4)
    c1.metric('GESTURE', s['gesture'])
    c2.metric('MODEL SCORE', f"{s['score']*100:.1f}%")
    c3.metric('SIMULATED COMMAND', s['command'])
    c4.metric('RECEIVED WINDOWS', s['count'])
    if s['stopped']: st.warning(f"SIMULATION STOPPED | ESP32: {s['status']}")
    elif s['status'] == 'RECEIVING LIVE DATA': st.success(s['status'])
    else: st.warning(s['status'])
    left,right = st.columns(2)
    with left:
        st.subheader('📈 Incoming ADC window averages')
        fig = go.Figure(go.Scatter(y=list(s['adc']), mode='lines+markers', line_color='#56e5ff'))
        fig.update_layout(template='plotly_dark', height=380, yaxis_range=[0,4095],
                          xaxis_title='Recent one-second windows', yaxis_title='ADC average',
                          paper_bgcolor='#14243a', plot_bgcolor='#14243a')
        st.plotly_chart(fig, use_container_width=True)
    with right:
        st.subheader('🛰️ UAV navigation — simulation only')
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=s['path_x'], y=s['path_y'], mode='lines', name='Path', line_color='#20e9ad'))
        fig.add_trace(go.Scatter(x=[s['x']], y=[s['y']], mode='markers', name='UAV', marker=dict(size=18, color='#56e5ff', symbol='diamond')))
        fig.update_layout(template='plotly_dark', height=380, xaxis=dict(range=[-10,10]),
                          yaxis=dict(range=[-10,10], scaleanchor='x'),
                          paper_bgcolor='#14243a', plot_bgcolor='#14243a')
        st.plotly_chart(fig, use_container_width=True)
    a,b,c,d = st.columns(4)
    for box,name,value in zip((a,b,c,d), FEATURES, s['features']):
        box.metric(name.replace('_',' '), f'{value:.2f}')
    st.caption('Recent predicted gestures: ' + (' → '.join(s['gestures']) or 'Waiting for data'))
    st.caption(f"UAV position: ({s['x']:.0f}, {s['y']:.0f}) | Rejected serial lines: {s['errors']}")

live()
st.divider()
st.subheader('📊 Power BI integration — session log')
st.write('The dashboard appends genuine received windows and predictions to `emg_live_log.csv`. Import this CSV into Power BI Desktop using Get Data → Text/CSV. Refresh the report to see newly imported rows; CSV import is not a live streaming feed.')
if LOG_PATH.exists():
    st.download_button('Download Power BI CSV', LOG_PATH.read_bytes(), 'emg_live_log.csv', 'text/csv')
st.caption('Predicted gestures are not ground-truth labels. This log alone cannot establish model accuracy.')
