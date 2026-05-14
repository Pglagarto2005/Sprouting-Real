import streamlit as st
import requests
import random

# ------------------------------
# CONFIG
# ------------------------------

ESP32_URL = "http://192.168.1.50"

# ------------------------------
# SESSION STATE
# ------------------------------

if "pantalla" not in st.session_state:
    st.session_state.pantalla = "maceta"

if "felicidad" not in st.session_state:
    st.session_state.felicidad = 70

if "humedad" not in st.session_state:
    st.session_state.humedad = 40

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

    st.write(f"💧 Humedad actual: {st.session_state.humedad}%")

    # Leer humedad real
    try:
        response = requests.get(f"{ESP32_URL}/humedad")
        data = response.json()
        st.session_state.humedad = data["humedad"]
    except:
        st.warning("No se pudo conectar con el sensor")

    # Botón regar
    if st.button("💦 Regar Planta"):

        try:
            requests.get(f"{ESP32_URL}/regar")
            st.success("Planta regada ✨")
            st.balloons()
        except:
            st.error("No se pudo conectar al ESP32")

# ------------------------------
# PANTALLA CUARTO
# ------------------------------

if st.session_state.pantalla == "cuarto":

    st.title("🏠 Cuarto de tu Planta")

    st.image("assets/planta_feliz.png", width=250)

    st.write(f"❤️ Felicidad: {st.session_state.felicidad}")

    if st.button("🤗 Dar cariño"):
        st.session_state.felicidad += 5
        st.success("Tu planta está feliz 🌱")

    mensajes = [
        "Gracias por cuidarme 🌱",
        "Tengo sed 😢",
        "Estoy creciendo ✨",
        "Hoy me siento feliz ☀️"
    ]

    if st.button("💬 Hablar"):
        st.info(random.choice(mensajes))
