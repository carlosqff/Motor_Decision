import streamlit as st
import pandas as pd
import pyodbc
import gspread
from gspread_dataframe import get_as_dataframe
from google.oauth2.service_account import Credentials
from datetime import date, timedelta

# Configuración de la aplicación
st.title("Evaluación de Crédito")
st.write("Ingrese los datos solicitados para calcular el resultado de la evaluación de crédito.")

# Variables de entrada en la aplicación
ID_CLIENTE = st.number_input("ID CLIENTE", min_value=1, step=1)
score_buro = st.number_input("Score Buro", min_value=0, step=1)
score_nohit = st.number_input("Score No Hit", min_value=0, step=1)
mensualidad_moto = st.number_input("Mensualidad Moto", min_value=0, step=1)

@st.cache_data
def cargar_datos():
    # Configuración de conexión de Google Sheets
    SCOPES = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = Credentials.from_service_account_file(
        r"C:\Users\52667\Downloads\key.json",
        scopes=SCOPES
    )
    client = gspread.authorize(creds)

    # Carga de datos de Google Sheets
    spreadsheet_id = "1w2hMUpuWAJfc2rNv2IbH_WfiX8hVe8U7M47dOdzkrsg"
    worksheet_credito = client.open_by_key(spreadsheet_id).worksheet("CREDITO")
    spreadsheet = client.open_by_key(spreadsheet_id)
    worksheet_originacion = spreadsheet.worksheet("ORIGINACIÓN")

    credito = get_as_dataframe(worksheet_credito, evaluate_formulas=True)
    credito = credito[["Fecha de asignación", "FOLIO", "Cliente", "Resultado"]]
    credito = credito.rename(columns={"Cliente": "ID_CLIENTE"})

    originacion = get_as_dataframe(worksheet_originacion, evaluate_formulas=True)
    originacion = originacion[["Fecha de asignación", "FOLIO", "Cliente", "Estatus"]]
    originacion = originacion.rename(columns={"Estatus": "Resultado", "Cliente": "ID_CLIENTE"})

    credito = pd.concat([credito, originacion], ignore_index=True)

    # Conexión a la base de datos SQL
    server = '52.167.231.145,51433'
    database = 'CreditoYCobranza'
    username = 'credito'
    password = 'Cr3d$.23xme'

    conn = pyodbc.connect(
        f'DRIVER={{SQL Server}};SERVER={server};DATABASE={database};UID={username};PWD={password}'
    )

    query3 = """SELECT [SapIdCliente], CAST([FechaGenerado] AS DATE) AS FechaGenerado, [Fecha], [Mensualidad]
                FROM [CreditoyCobranza].[dbo].[Cartera_Financiera_Diaria]"""
    CF = pd.read_sql(query3, conn)
    Mensualidad = CF.groupby("SapIdCliente")[["Mensualidad"]].sum()

    query4 = """SELECT * FROM MODELO_GESTIONES"""
    posturas_gestiones = pd.read_sql(query4, conn)
    posturas_gestiones["ID_CLIENTE"] = pd.to_numeric(posturas_gestiones["ID_CLIENTE"], errors="coerce").astype("Int64")
    posturas_gestiones = posturas_gestiones.rename(columns={"Resultado": "Marca_Gestiones"})

    # Cargar datos de Excel
    vector_apvap = pd.read_excel(r"C:\Users\52667\Desktop\REPORTES ROBERTO\ULTIMOS_APVAP_VECTOR.xlsx", "Hoja1")
    vector_apvap = vector_apvap.rename(columns={"SapIdCliente": "ID_CLIENTE"})

    return credito, Mensualidad, posturas_gestiones, vector_apvap

# Cargar los datos iniciales en caché
credito, Mensualidad, posturas_gestiones, vector_apvap = cargar_datos()

# Nueva pestaña para mostrar la base `credito`
st.sidebar.title("Navegación")
page = st.sidebar.radio("Ir a", ["Evaluación de Crédito", "Base Crédito"])

if page == "Base Crédito":
    st.title("Base Crédito Consolidada")
    st.dataframe(credito)

elif page == "Evaluación de Crédito":
    if st.button("Calcular Resultado"):
        # Todo el resto de tu código original para "Calcular Resultado" aquí...
        credito["FOLIO"] = credito["FOLIO"].apply(lambda x: x.replace("#", "") if isinstance(x, str) else x)
        credito = credito[credito["Resultado"] == "EN PROCESO"]
        credito["ID_CLIENTE"] = credito["ID_CLIENTE"].astype("int64")

        def contador(row):
            if (
                pd.isnull(row["AP_VAP_FACTURA_1M"]) and 
                pd.isnull(row["AP_VAP_FACTURA_2M"]) and 
                pd.isnull(row["AP_VAP_FACTURA_3M"]) and 
                pd.isnull(row["AP_VAP_FACTURA_4M"]) and 
                pd.isnull(row["AP_VAP_FACTURA_5M"])
            ):
                return None 
            elif (
                row["AP_VAP_Actual"] == "AP3" or 
                row["AP_VAP_FACTURA_1M"] == "AP3" or 
                row["AP_VAP_FACTURA_2M"] == "AP3" or 
                row["AP_VAP_FACTURA_3M"] == "AP3" or 
                row["AP_VAP_FACTURA_4M"] == "AP3" or 
                row["AP_VAP_FACTURA_5M"] == "AP3"
            ):
                return 30
            elif (
                row["AP_VAP_Actual"] == "AP4" or 
                row["AP_VAP_FACTURA_1M"] == "AP4" or 
                row["AP_VAP_FACTURA_2M"] == "AP4" or 
                row["AP_VAP_FACTURA_3M"] == "AP4" or 
                row["AP_VAP_FACTURA_4M"] == "AP4" or 
                row["AP_VAP_FACTURA_5M"] == "AP4"
            ):
                return 30
            elif pd.isnull(row["AP_VAP_Actual"]):
                return 0
            else:
                return 0

        vector_apvap["AP3_U6M"] = vector_apvap.apply(contador, axis=1)

        vector_apvap = vector_apvap.sort_values(by="AP3_U6M", ascending=False)
        vector_apvap = vector_apvap.drop_duplicates(subset="ID_CLIENTE")
        vector_U6M = vector_apvap[["ID_CLIENTE", "AP3_U6M"]]

        base_credito = pd.merge(credito, vector_U6M, on="ID_CLIENTE", how="left")
        base_credito = pd.merge(base_credito, posturas_gestiones, on="ID_CLIENTE", how="left")

        dic_buro = {
            "ID_CLIENTE": [ID_CLIENTE],
            "Score_Buro": [score_buro],
            "Not_HIT": [score_nohit],
            "Mensualidad_Moto": [mensualidad_moto]
        }

        base_buro = pd.DataFrame(dic_buro)
        base_credito = pd.merge(base_credito, base_buro, on="ID_CLIENTE", how="left")
        mensualidad_df = Mensualidad.reset_index()
        rename = {"SapIdCliente": "ID_CLIENTE"}
        mensualidad_df = mensualidad_df.rename(columns=rename)
        mensualidad_df["ID_CLIENTE"] = pd.to_numeric(mensualidad_df["ID_CLIENTE"], errors="coerce").astype("Int64")
        base_credito = pd.merge(base_credito, mensualidad_df, on="ID_CLIENTE", how="left")

        def mens_total(row):
            return row["Mensualidad"] + row["Mensualidad_Moto"]

        base_credito["Mensualidad_Total"] = base_credito.apply(mens_total, axis=1)

        def variacion_mensualidad(row):
            if row["Mensualidad_Total"] > row["Mensualidad"] * 2:
                return 40
            else:
                return 0

        base_credito["Resultado_Mensualidad"] = base_credito.apply(variacion_mensualidad, axis=1)

        def resultado_buro(row):
            if pd.isna(row["Score_Buro"]):
                return "Sin historial"
            elif row["Score_Buro"] == 0:
                if row["Not_HIT"] >= 500 and row["Not_HIT"] < 600:
                    return 10
                elif row["Not_HIT"] > 600:
                    return 0
                else:
                    return 20
            elif row["Not_HIT"] == 0:
                if row["Score_Buro"] > 500 and row["Score_Buro"] < 580:
                    return 10
                elif row["Score_Buro"] >= 580:
                    return 0
                else:
                    return 20
            else:
                return 99999

        base_credito["Resultado_Buro"] = base_credito.apply(resultado_buro, axis=1)
        base_credito["Marca_Gestiones"] = base_credito["Marca_Gestiones"].apply(lambda x: "SIN GESTION" if pd.isnull(x) else x)

        def Resultado_Gestiones(row):
            if row["Marca_Gestiones"] == "EXCELENTE":
                return 0
            elif row["Marca_Gestiones"] == "BUENA" or row["Marca_Gestiones"] == "SIN GESTION":
                return 10
            elif row["Marca_Gestiones"] == "MALA" or row["Marca_Gestiones"] == "SIN CONTACTO":
                return 20
            else:
                return None

        base_credito["Resultado_Gestiones"] = base_credito.apply(Resultado_Gestiones, axis=1)

        def puntaje(row):
            ap3_u6m = pd.to_numeric(row["AP3_U6M"], errors="coerce") or 0
            resultado_mensualidad = pd.to_numeric(row["Resultado_Mensualidad"], errors="coerce") or 0
            resultado_buro = pd.to_numeric(row["Resultado_Buro"], errors="coerce") or 0
            resultado_gestiones = pd.to_numeric(row["Resultado_Gestiones"], errors="coerce") or 0

            return ap3_u6m + resultado_mensualidad + resultado_buro + resultado_gestiones

        base_credito["Puntaje"] = base_credito.apply(puntaje, axis=1)

        def resultado(row):
            if row["Puntaje"] > 50:
                return "Rechazado"
            elif row["Puntaje"] >= 0 and row["Puntaje"] <= 50:
                return "Aceptado"
            elif pd.isna(row["Puntaje"]):
                return "No aplica"
            else:
                return "No aplica"

        base_credito["Resultado"] = base_credito.apply(resultado, axis=1)

        Base_Final_Credito = base_credito[
            ["Fecha de asignación", "ID_CLIENTE", "AP3_U6M", "Marca_Gestiones", "Score_Buro", "Not_HIT",
             "Resultado_Mensualidad", "Resultado_Buro", "Resultado_Gestiones", "Puntaje", "Resultado"]
        ]

        base_1 = Base_Final_Credito[["Fecha de asignación", "ID_CLIENTE", "Puntaje", "Resultado"]]
        base_1 = pd.merge(base_1, base_buro, on="ID_CLIENTE", how="inner")
        base_2 = base_1[["Fecha de asignación", "ID_CLIENTE", "Puntaje", "Resultado"]]

        st.subheader("Resultado de la Evaluación de Crédito")

        fecha_asignacion = base_2.iloc[0]["Fecha de asignación"]
        id_cliente = base_2.iloc[0]["ID_CLIENTE"]
        puntaje = base_2.iloc[0]["Puntaje"]
        resultado = base_2.iloc[0]["Resultado"]

        col1, col2 = st.columns(2)

        with col1:
            st.markdown(f"**Fecha de Asignación:** {fecha_asignacion}")
            st.markdown(f"**ID Cliente:** {id_cliente}")
            st.markdown(f"**Puntaje Total:** {puntaje}")

        with col2:
            st.markdown(
                f"**Resultado:** {'🔴 Rechazado' if resultado == 'Rechazado' else ('🔴 No aplica para este análisis!' if resultado == 'No aplica' else '🟢 Aceptado')}")
        st.markdown("---")
