"""
PlantaPet — Tamagotchi para tu planta real
Integra sensor de humedad + servo de riego vía MQTT
"""

import os
import json
import time
from datetime import datetime

import streamlit as st
import paho.mqtt.client as mqtt
from streamlit_autorefresh import st_autorefresh

# ─── PAGE CONFIG ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="PlantaPet",
    page_icon="🌱",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ─── AUTO-REFRESH cada 3 s para mostrar datos MQTT en tiempo real ─────────────
st_autorefresh(interval=3000, key="plantapet_refresh")

# ─── HELPERS ──────────────────────────────────────────────────────────────────
def _secret(key: str, default: str = "") -> str:
    try:
        return st.secrets[key]
    except Exception:
        return os.environ.get(key, default)

def _log(shared: dict, msg: str) -> None:
    shared["log"].append(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")
    if len(shared["log"]) > 100:
        shared["log"] = shared["log"][-100:]

# ─── ESTADO COMPARTIDO (persiste entre reruns via cache_resource) ─────────────
@st.cache_resource
def get_shared() -> dict:
    return {
        "humedad":        55.0,
        "connected":      False,
        "riego_progreso": False,
        "ultimo_riego":   None,
        "log":            [],
    }

# ─── CLIENTE MQTT (singleton, hilo en background) ────────────────────────────
@st.cache_resource
def get_mqtt_client() -> mqtt.Client:
    shared = get_shared()
    broker   = _secret("MQTT_BROKER",   "broker.hivemq.com")
    port     = int(_secret("MQTT_PORT", "1883"))
    user     = _secret("MQTT_USER",     "")
    password = _secret("MQTT_PASS",     "")

    def on_connect(client, _u, _f, rc):
        if rc == 0:
            shared["connected"] = True
            client.subscribe("plantapet/humedad")
            client.subscribe("plantapet/confirmacion")
            _log(shared, "🔌 MQTT conectado")
        else:
            _log(shared, f"⚠️ MQTT error rc={rc}")

    def on_disconnect(_c, _u, rc):
        shared["connected"] = False
        _log(shared, f"🔌 MQTT desconectado (rc={rc})")

    def on_message(_c, _u, msg):
        topic   = msg.topic
        payload = msg.payload.decode().strip()

        if topic == "plantapet/humedad":
            try:
                val = float(payload)
            except ValueError:
                try:
                    val = float(json.loads(payload).get("humedad", shared["humedad"]))
                except Exception:
                    return
            shared["humedad"] = max(0.0, min(100.0, val))
            _log(shared, f"💧 Humedad recibida: {shared['humedad']:.1f}%")

        elif topic == "plantapet/confirmacion":
            shared["riego_progreso"] = False
            shared["ultimo_riego"]   = datetime.now().strftime("%H:%M:%S")
            _log(shared, f"✅ Riego confirmado a las {shared['ultimo_riego']}")

    client = mqtt.Client(client_id=f"plantapet_{int(time.time())}", clean_session=True)
    client.on_connect    = on_connect
    client.on_disconnect = on_disconnect
    client.on_message    = on_message

    if user:
        client.username_pw_set(user, password)

    try:
        client.connect(broker, port, 60)
        client.loop_start()
    except Exception as exc:
        _log(shared, f"⚠️ No se pudo conectar: {exc}")

    return client

# ─── INICIALIZAR SESSION STATE ────────────────────────────────────────────────
def _init() -> None:
    defaults: dict = {
        "hambre":    80,
        "felicidad": 70,
        "pantalla":  "maceta",
        "dec": {
            "sombrero": False,
            "gafas":    False,
            "bufanda":  False,
            "flores":   False,
            "arcoiris": False,
            "corona":   False,
        },
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

_init()

# ─── OBTENER CLIENTES ────────────────────────────────────────────────────────
shared = get_shared()
client = get_mqtt_client()

# ─── LÓGICA DE JUEGO ──────────────────────────────────────────────────────────
humedad   = shared["humedad"]
hambre    = st.session_state.hambre
felicidad = st.session_state.felicidad

# Humedad baja → mascota pierde hambre gradualmente
if humedad < 30:
    caida = (30 - humedad) / 30 * 1.5
    st.session_state.hambre = max(0, hambre - caida)
    hambre = st.session_state.hambre

# Después del riego exitoso → pequeño bonus
if (not shared["riego_progreso"]
        and shared["ultimo_riego"]
        and humedad > 55):
    st.session_state.hambre = min(100, hambre + 0.5)
    hambre = st.session_state.hambre


def _estado() -> str:
    if hambre < 15:                            return "agotado"
    if hambre < 35:                            return "muy_hambriento"
    if hambre < 55:                            return "hambriento"
    if humedad < 25:                           return "triste"
    if hambre > 75 and humedad > 50:           return "feliz"
    return "normal"


def _dar_comida() -> str:
    if st.session_state.hambre >= 95:
        return "lleno"
    st.session_state.hambre = min(100, st.session_state.hambre + 25)
    if st.session_state.hambre >= 75:
        shared["riego_progreso"] = True
        payload = json.dumps({"accion": "regar", "duracion": 5})
        try:
            client.publish("plantapet/regar", payload)
            _log(shared, "🚿 Comando de riego enviado")
        except Exception as exc:
            _log(shared, f"⚠️ Publish error: {exc}")
        return "riega"
    return "come"


estado = _estado()

# ─── CSS ──────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Press+Start+2P&display=swap');

.stApp {
    background: radial-gradient(ellipse at center, #0d2137 0%, #050d17 100%);
    min-height: 100vh;
}
.device {
    background: #0a1628;
    border: 3px solid #00e676;
    border-radius: 24px;
    padding: 18px 16px 14px;
    max-width: 340px;
    margin: 0 auto 12px;
    box-shadow: 0 0 32px #00e67644, inset 0 0 20px #000a14;
}
.device-screen {
    background: #061020;
    border: 2px solid #00b050;
    border-radius: 12px;
    min-height: 210px;
    display: flex;
    align-items: center;
    justify-content: center;
    margin-bottom: 12px;
    box-shadow: inset 0 0 18px #001508;
    padding: 10px;
}
.titulo {
    font-family: 'Press Start 2P', monospace;
    color: #00e676;
    text-align: center;
    font-size: 1em;
    text-shadow: 0 0 14px #00e676;
    margin-bottom: 6px;
    letter-spacing: 2px;
}
.pet-sprite {
    font-family: monospace;
    text-align: center;
    line-height: 1.8;
    user-select: none;
}
.barra {
    font-family: 'Courier New', monospace;
    font-size: 0.80em;
    color: #aaffcc;
    margin: 3px 0;
}
.alerta {
    background: #2a0800;
    border: 1px solid #ff4444;
    border-radius: 8px;
    padding: 8px 12px;
    font-family: monospace;
    color: #ff7070;
    text-align: center;
    font-size: 0.88em;
    margin: 8px auto;
    max-width: 340px;
    animation: blink 0.9s step-end infinite;
}
@keyframes blink { 50% { opacity: 0.25; } }

.mqtt-pill {
    font-size: 0.70em;
    font-family: monospace;
    text-align: right;
    padding: 2px 4px;
}
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding-top: 0.4rem; max-width: 400px; }
div[data-testid="stHorizontalBlock"] { gap: 6px; }
</style>
""", unsafe_allow_html=True)

# ─── SPRITES ──────────────────────────────────────────────────────────────────
_CARAS = {
    "feliz":          ("( ◕ ‿ ◕ )", "#00e676"),
    "normal":         ("( ・ω・ )",  "#8BC34A"),
    "hambriento":     ("( ；ω； )",  "#FFC107"),
    "muy_hambriento": ("( T▽T  )",   "#FF7043"),
    "agotado":        ("( x_x  )",   "#9E9E9E"),
    "triste":         ("( ；＿； )",  "#FF9800"),
    "regando":        ("( ≧∇≦ )",   "#29B6F6"),
}


def _sprite(estado_pet: str, decs: dict, maceta: bool = True) -> str:
    cara, color = _CARAS.get(estado_pet, _CARAS["normal"])
    top   = "👑" if decs.get("corona")   else ("🎩" if decs.get("sombrero") else "")
    left  = "🕶️ " if decs.get("gafas")   else ""
    right = "🧣"  if decs.get("bufanda")  else ""
    bot   = ("🌸 " if decs.get("flores")  else "") + ("🌈" if decs.get("arcoiris") else "")

    if maceta:
        return (
            f'<div class="pet-sprite">'
            f'<div style="font-size:1.5em;min-height:1.6em;">{top}</div>'
            f'<div style="font-size:1.1em;color:{color};white-space:nowrap;">{left}{cara}{right}</div>'
            f'<div style="font-size:1.1em;color:{color};">&nbsp;( 🌿 )&nbsp;</div>'
            f'<div style="font-size:2em;">🪴</div>'
            f'<div style="font-size:1.1em;min-height:1.4em;">{bot}</div>'
            f'</div>'
        )
    return (
        f'<div class="pet-sprite">'
        f'<div style="font-size:1.8em;min-height:1.8em;">{top}</div>'
        f'<div style="font-size:1.3em;color:{color};white-space:nowrap;">{left}{cara}{right}</div>'
        f'<div style="font-size:1.2em;color:{color};">♪&nbsp;( 🌿 )&nbsp;♪</div>'
        f'<div style="font-size:1.2em;min-height:1.4em;">{bot}</div>'
        f'</div>'
    )


def _barra_html(val: float, label: str, ico: str) -> str:
    color = "#00e676" if val > 60 else ("#FFC107" if val > 30 else "#F44336")
    n = int(val / 100 * 10)
    barra = "█" * n + "░" * (10 - n)
    return (
        f'<div class="barra">{ico} {label:8s} '
        f'<span style="color:{color};">[{barra}]</span>'
        f' <span style="color:#556;">{val:.0f}%</span></div>'
    )


# ─── TOP STATUS BAR ───────────────────────────────────────────────────────────
dot_col = "#00e676" if shared["connected"] else "#ff4444"
dot_txt = "● MQTT" if shared["connected"] else "○ sin MQTT"
st.markdown(
    f'<div class="mqtt-pill" style="color:{dot_col};">{dot_txt}</div>',
    unsafe_allow_html=True
)

# ─── TÍTULO ───────────────────────────────────────────────────────────────────
st.markdown('<div class="titulo">🌱 PlantaPet 🌱</div>', unsafe_allow_html=True)

# ─── NAVEGACIÓN (simula swipe izq / der) ──────────────────────────────────────
c1, c2 = st.columns(2)
with c1:
    if st.button(
        "🪴 Maceta", use_container_width=True,
        type="primary" if st.session_state.pantalla == "maceta" else "secondary",
    ):
        st.session_state.pantalla = "maceta"
        st.rerun()
with c2:
    if st.button(
        "🌿 Explorar", use_container_width=True,
        type="primary" if st.session_state.pantalla == "libre" else "secondary",
    ):
        st.session_state.pantalla = "libre"
        st.rerun()

st.markdown("<br>", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# PANTALLA 1 — MASCOTA EN MACETA
# ═══════════════════════════════════════════════════════════════════════════════
if st.session_state.pantalla == "maceta":

    est_sprite  = "regando" if shared["riego_progreso"] else estado
    sprite_html = _sprite(est_sprite, st.session_state.dec, maceta=True)

    st.markdown(
        f'<div class="device">'
        f'<div class="device-screen">{sprite_html}</div>'
        f'{_barra_html(hambre,    "Hambre",   "🍽️")}'
        f'{_barra_html(humedad,   "Humedad",  "💧")}'
        f'{_barra_html(felicidad, "Felicidad","😊")}'
        f'</div>',
        unsafe_allow_html=True,
    )

    if hambre < 50:
        st.markdown(
            '<div class="alerta">⚠️ ¡Tengo hambre! ¡Dame de comer! ⚠️</div>',
            unsafe_allow_html=True,
        )

    col_l, col_c, col_r = st.columns([1, 2, 1])
    with col_c:
        lbl = "🍎 ¡Dar de Comer!" if hambre < 50 else "🍎 Alimentar"
        if st.button(lbl, use_container_width=True, key="btn_comer"):
            result = _dar_comida()
            if result == "lleno":
                st.toast("Ya está lleno 😊", icon="✅")
            elif result == "riega":
                st.toast("💧 ¡Regando la planta!", icon="🚿")
                st.session_state.felicidad = min(100, felicidad + 10)
            else:
                st.toast("😋 ¡Qué rico!", icon="🍎")
            st.rerun()

    if shared["riego_progreso"]:
        st.markdown(
            '<div style="text-align:center;color:#29B6F6;font-family:monospace;'
            'margin-top:8px;font-size:0.9em;">💧 Regando la planta... 💧</div>',
            unsafe_allow_html=True,
        )

    if shared["ultimo_riego"]:
        st.markdown(
            f'<div style="text-align:center;color:#445;font-size:0.75em;'
            f'font-family:monospace;margin-top:4px;">'
            f'Último riego: {shared["ultimo_riego"]}</div>',
            unsafe_allow_html=True,
        )

# ═══════════════════════════════════════════════════════════════════════════════
# PANTALLA 2 — MASCOTA LIBRE / DECORAR
# ═══════════════════════════════════════════════════════════════════════════════
elif st.session_state.pantalla == "libre":

    est_libre   = "feliz" if felicidad > 60 else "normal"
    sprite_html = _sprite(est_libre, st.session_state.dec, maceta=False)

    st.markdown(
        f'<div class="device">'
        f'<div class="device-screen">{sprite_html}</div>'
        f'{_barra_html(felicidad, "Felicidad", "😊")}'
        f'</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div style="color:#00e676;font-family:monospace;text-align:center;'
        'font-size:0.85em;margin:8px 0;">✨ ¡Decora a tu mascota! ✨</div>',
        unsafe_allow_html=True,
    )

    DECS = [
        ("sombrero", "🎩 Sombrero"),
        ("gafas",    "🕶️ Gafas"),
        ("bufanda",  "🧣 Bufanda"),
        ("flores",   "🌸 Flores"),
        ("arcoiris", "🌈 Arcoíris"),
        ("corona",   "👑 Corona"),
    ]

    cols = st.columns(3)
    for i, (key, label) in enumerate(DECS):
        with cols[i % 3]:
            activo = st.session_state.dec.get(key, False)
            if st.button(
                f"{'✅' if activo else '◻'} {label}",
                use_container_width=True,
                key=f"dec_{key}",
            ):
                st.session_state.dec[key] = not activo
                if not activo:
                    st.session_state.felicidad = min(100, felicidad + 5)
                st.rerun()

# ─── LOG Y CONFIG MQTT ────────────────────────────────────────────────────────
with st.expander("📋 Registro & Configuración MQTT"):

    for msg in reversed(shared["log"][-15:]):
        st.text(msg)

    st.markdown("---")
    st.markdown("**Ajustes de conexión MQTT**")
    broker_in = st.text_input(
        "Broker", value=_secret("MQTT_BROKER", "broker.hivemq.com"), key="broker_in"
    )
    port_in = st.number_input("Puerto", value=1883, step=1, key="port_in")

    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("🔌 Reconectar", key="btn_recon"):
            try:
                client.disconnect()
                client.connect(broker_in, int(port_in), 60)
                _log(shared, f"Reconectando a {broker_in}:{int(port_in)}")
                st.toast("Reconectando...", icon="🔌")
            except Exception as exc:
                _log(shared, f"⚠️ {exc}")
                st.toast(str(exc), icon="⚠️")
    with col_b:
        if st.button("🧪 Simular seco", key="btn_sim"):
            shared["humedad"] = 18.0
            _log(shared, "🧪 Simulación: humedad = 18% (planta seca)")
            st.rerun()

