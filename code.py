import streamlit as st
import random
import paho.mqtt.client as mqtt
import paho.mqtt.publish as publish

# ------------------------------
# MQTT CONFIG
# ------------------------------

BROKER = "broker.hivemq.com"

TOPIC_HUMEDAD = "plantagotchi/humedad"
TOPIC_REGAR = "plantagotchi/regar"

# ------------------------------
# SESSION STATE
# ------------------------------

if "pantalla" not in st.session_state:
    st.session_state.pantalla = "maceta"

if "felicidad" not in st.session_state:
    st.session_state.felicidad = 70

if "humedad" not in st.session_state:
    st.session_state.humedad = 0

# ------------------------------
# MQTT CALLBACK
# ------------------------------

def on_message(client, userdata, msg):

    try:

        humedad = msg.payload.decode()

        st.session_state.humedad = int(humedad)

    except:
        pass

# ------------------------------
# MQTT CLIENT
# ------------------------------

client = mqtt.Client()

client.on_message = on_message

try:

    client.connect(BROKER, 1883)

    client.subscribe(TOPIC_HUMEDAD)

    client.loop_start()

except:
    st.warning("No se pudo conectar al broker MQTT")

# ------------------------------
# ESTILOS
# ------------------------------

st.markdown(
    """
    <style>

    .main {
        background-color: #dfffd8;
    }

    .stButton button {

        background-color: #ffb347;
        color: white;

        border-radius: 20px;

        border: none;

        padding: 10px 20px;

        font-size: 18px;
    }

    </style>
    """,
    unsafe_allow_html=True
)

# ------------------------------
# NAVBAR
# ------------------------------

col1, col2 = st.columns(2)

with col1:

    if st.button("🌱 Maceta"):

        st.session_state.pantalla = "maceta"

with col2:

    if st.button("🏠 Cuarto"):

        st.session_state.pantalla = "cuarto"

# ------------------------------
# PANTALLA MACETA
# ------------------------------

if st.session_state.pantalla == "maceta":

    st.title("🌱 Plantagotchi")

    st.image("assets/planta_feliz.png", width=300)

    st.subheader("Humedad de la planta")

    st.progress(st.session_state.humedad)

    st.write(
        f"💧 Humedad actual: {st.session_state.humedad}%"
    )

    # ------------------------------
    # BOTÓN REGAR
    # ------------------------------

    if st.button("💦 Regar Planta"):

        try:

            publish.single(
                TOPIC_REGAR,
                "ON",
                hostname=BROKER
            )

            st.success("Planta regada ✨")

            st.balloons()

        except:

            st.error("No se pudo enviar mensaje MQTT")

# ------------------------------
# PANTALLA CUARTO
# ------------------------------

if st.session_state.pantalla == "cuarto":

    st.title("🏠 Cuarto de tu Planta")

    st.image("assets/planta_feliz.png", width=250)

    st.write(
        f"❤️ Felicidad: {st.session_state.felicidad}"
    )

    # ------------------------------
    # DAR CARIÑO
    # ------------------------------

    if st.button("🤗 Dar cariño"):

        st.session_state.felicidad += 5

        st.success("Tu planta está feliz 🌱")

    # ------------------------------
    # MENSAJES
    # ------------------------------

    mensajes = [

        "Gracias por cuidarme 🌱",

        "Tengo sed 😢",

        "Estoy creciendo ✨",

        "Hoy me siento feliz ☀️"
    ]

    if st.button("💬 Hablar"):

        st.info(random.choice(mensajes))
