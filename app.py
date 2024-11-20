import streamlit as st 
import pandas as pd
import pyodbc

# Estilos personalizados
st.markdown(
    """
    <style>
    .main {
        background-color: #f9f9f9;
        font-family: 'Arial', sans-serif;
    }
    .sidebar .sidebar-content {
        background-color: #e6e6e6;
        font-family: 'Arial', sans-serif;
    }
    h1, h2, h3, h4, h5, h6 {
        color: #333333;
    }
    .stButton > button {
        background-color: #4CAF50;
        color: white;
        border: none;
        border-radius: 5px;
        padding: 10px 15px;
    }
    .stButton > button:hover {
        background-color: #45a049;
    }
    .dataframe-container {
        max-width: 90%;
        margin: auto;
    }
    .small-text {
        font-size: 14px;
        text-align: center;
        color: #555555;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# Encabezado de bienvenida
st.markdown(
    """
    <h1 style='text-align: center; color: #333333;'>
        Sistema de Gestión de Clientes
    </h1>
    """,
    unsafe_allow_html=True
)

# Diccionario de usuarios con nombres formateados
usuarios = {
    "12345": {"gestor": "Anahí Cabrales Araujo", "password": "12345"},
    "123": {"gestor": "Ana Laura Rivera Inzunza", "password": "123"},
    "983243": {"gestor": "Jessica Maribel Vargas Villagrana", "password": "34567"},
    "983242": {"gestor": "Cinthia Guadalupe Checa Robles", "password": "34562"},
    "983241": {"gestor": "Julissa Iveth Gamez Ramirez", "password": "34565"},
    "983247": {"gestor": "Marcos Eduardo Robles Vázquez", "password": "34568"},
    "983248": {"gestor": "Reyna Berenice Salazar Cabrera", "password": "34569"},
    "983244": {"gestor": "José Alfredo Alvarado Hernandez", "password": "34561"}
}

# Función de inicio de sesión
def login():
    st.title("Iniciar Sesión")
    codigo_acceso = st.text_input("Código de Acceso")
    password = st.text_input("Contraseña", type="password")
    
    if st.button("Iniciar Sesión"):
        if codigo_acceso in usuarios and usuarios[codigo_acceso]["password"] == password:
            gestor = usuarios[codigo_acceso]["gestor"]
            st.success(f"Bienvenido {gestor}")
            st.session_state["authenticated"] = True
            st.session_state["gestor"] = gestor
        else:
            st.error("Código de acceso o contraseña incorrectos")

# Botón para cerrar sesión
def cerrar_sesion():
    st.session_state["authenticated"] = False
    st.session_state["gestor"] = None
    st.session_state.clear()

# Verificar si el usuario está autenticado
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    login()
else:
    # Configurar la conexión a SQL Server
    server = '52.167.231.145,51433'
    database = 'CreditoYCobranza'  
    username = 'credito'  
    password = 'Cr3d$.23xme'  

    # Crear la conexión
    conn = pyodbc.connect(
        f'DRIVER={{SQL Server}};SERVER={server};DATABASE={database};UID={username};PWD={password}'
    )

    # Cargar datos desde SQL Server
    gestor_autenticado = st.session_state["gestor"].strip()
    query = f"SELECT * FROM Base_Nueva_CRM WHERE GESTOR = '{gestor_autenticado}'"
    data = pd.read_sql(query, conn)

    # Sidebar para navegación y botón de cerrar sesión
    st.sidebar.title(f"Gestor: {gestor_autenticado}")
    st.sidebar.markdown("---")
    page = st.sidebar.radio("Ir a", ["Información de Cliente", "Base Completa", "Estadísticas", "Comisiones"])
    st.sidebar.markdown("---")
    if st.sidebar.button("Cerrar Sesión"):
        cerrar_sesion()
        st.experimental_rerun()

    # Configurar páginas
    if page == "Información de Cliente":
        cortes = data["CORTE"].unique()
        selected_corte = st.selectbox("Seleccione un Corte", cortes)
        filtered_data = data[data['CORTE'] == selected_corte]

        # Buscador por ID_CLIENTE
        search_id = st.text_input("Buscar ID_CLIENTE", "")
        if search_id:
            filtered_data = filtered_data[filtered_data['ID_CLIENTE'].astype(str).str.contains(search_id)]

        # Navegación entre clientes
        index = st.session_state.get('index', 0)

        if len(filtered_data) > 0:
            cliente_placeholder = st.empty()  # Marcador para el contenido del cliente
            with cliente_placeholder.container():
                cliente = filtered_data.iloc[index]
                st.write(f"<p class='small-text'>Cliente {index + 1} de {len(filtered_data)} en el Corte {selected_corte}</p>", unsafe_allow_html=True)
                st.subheader("Información del Cliente")
                cols = st.columns(2)
                with cols[0]:
                    st.write(f"**Nombre:** {cliente['CLIENTE']}")
                    st.write(f"**ID cliente:** {cliente['ID_CLIENTE']}")
                    st.write(f"**Clasificación:** {cliente['VALOR_CLIENTE']}")
                    st.write(f"**Descuento disponible:** {cliente['BOLSA_DESCUENTO']}")
                    st.write(f"**Facturas históricas:** {cliente['FACTURAS_HISTORICAS']}")

                with cols[1]:
                    st.write(f"**Teléfono 1:** {cliente['TELEFONO_1']}")
                    st.write(f"**Teléfono 2:** {cliente['TELEFONO_2']}")
                    st.write(f"**Teléfono 3:** {cliente['TELEFONO_3']}")
                    st.write(f"**Comentarios:** {cliente['COMENTARIO']}")

                st.divider()

                # Mostrar saldos generales
                st.subheader("Saldos Generales del Cliente")
                st.write(f"**Moratorios:** {cliente['TOTAL_MORATORIOS']}")
                st.write(f"**Saldo Atrasado Mora:** {cliente['TOTAL_SALDO_ATRASADO_MORA']}")
                st.write(f"**Saldo Actual Mora:** {cliente['TOTAL_SALDO_ACTUAL']}")
                st.write(f"**Liquide con:** {cliente['TOTAL_LIQUIDE_CON']}")

                st.divider()

                # Mostrar facturas del cliente
                st.subheader("Facturas del Cliente")
                cliente_facturas = data[data['ID_CLIENTE'] == cliente['ID_CLIENTE']]
                for i, factura in cliente_facturas.iterrows():
                    st.write(f"**Folio:** {factura['FOLIO']}")
                    st.write(f"**Artículo:** {factura['ARTICULO']}")
                    st.write(f"**Saldo Atrasado:** {factura['CF_FOLIO_SALDO_ATRASADO_MORA']}")
                    st.write(f"**Saldo Actual:** {factura['CF_FOLIO_SALDO_ACTUAL']}")
                    st.divider()

                # Gestion modificada
                st.subheader("Gestiones del Cliente")
                gestion = st.selectbox("Gestión", options=["DP", "NDP", "PP", "SP"], index=0)
                comentario = st.text_area("Comentarios", value=cliente.get('COMENTARIO', ''))

                if st.button("Guardar Cambios"):
                    try:
                        cursor = conn.cursor()
                        query_update = """
                            UPDATE Base_Nueva_CRM
                            SET GESTION = ?, COMENTARIO = ?
                            WHERE ID_CLIENTE = ?
                        """
                        cursor.execute(query_update, (gestion, comentario, cliente['ID_CLIENTE']))
                        conn.commit()
                        cursor.close()
                        st.success("Gestión y comentario guardados exitosamente.")
                    except Exception as e:
                        st.error(f"Error al guardar los cambios: {e}")

            # Botones para navegar entre clientes
            col1, col2, col3 = st.columns([1, 1, 1])
            with col1:
                if st.button("Anterior") and index > 0:
                    st.session_state["index"] = index - 1
            with col3:
                if st.button("Siguiente") and index < len(filtered_data) - 1:
                    st.session_state["index"] = index + 1

        else:
            st.warning("No se encontraron clientes.")

    elif page == "Estadísticas":
        st.subheader("Estadísticas de Gestión")
        gestionadas = data[data["GESTION"].notna()]
        no_gestionadas = data[data["GESTION"].isna()]
        desglose = gestionadas["GESTION"].value_counts()

        st.metric("Cuentas Gestionadas", len(gestionadas))
        st.metric("Cuentas No Gestionadas", len(no_gestionadas))

        st.bar_chart(desglose)
