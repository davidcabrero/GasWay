import requests
import pandas as pd
import folium
from folium.plugins import MarkerCluster
import tkinter as tk
from tkinter import ttk
from io import BytesIO
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
from geopy.distance import geodesic

# Obtener datos de gasolineras
def obtener_datos():
    url = "https://sedeaplicaciones.minetur.gob.es/ServiciosRESTCarburantes/PreciosCarburantes/EstacionesTerrestres/"
    response = requests.get(url)
    data = response.json()["ListaEESSPrecio"]
    df = pd.DataFrame(data)

    for col in df.columns:
        df[col] = df[col].str.strip()
    for col in df.columns:
        if "Precio" in col:
            df[col] = df[col].str.replace(",", ".")
            df[col] = pd.to_numeric(df[col], errors="coerce")
    df["Latitud"] = df["Latitud"].str.replace(",", ".")
    df["Longitud (WGS84)"] = df["Longitud (WGS84)"].str.replace(",", ".")
    df["Latitud"] = pd.to_numeric(df["Latitud"], errors="coerce")
    df["Longitud (WGS84)"] = pd.to_numeric(df["Longitud (WGS84)"], errors="coerce")
    df = df.dropna(subset=["Latitud", "Longitud (WGS84)"])
    return df

df_gasolineras = obtener_datos()
combustibles_disponibles = [col for col in df_gasolineras.columns if "Precio" in col]

# Geolocalización del usuario
def obtener_ubicacion_usuario():
    try:
        response = requests.get("https://ipinfo.io/json")
        data = response.json()
        lat, lon = map(float, data["loc"].split(","))
        return lat, lon
    except:
        return (40.4165, -3.70256)  # Fallback: Madrid

# Filtrar gasolineras
def filtrar_gasolineras(ciudad, combustible):
    df_filtrado = df_gasolineras[df_gasolineras["Municipio"].str.lower() == ciudad.lower()]
    df_filtrado = df_filtrado[df_filtrado[combustible] > 0]
    return df_filtrado.nsmallest(10, combustible)

# Gasolinera más cercana
def gasolinera_mas_cercana(user_location, combustible):
    df_valido = df_gasolineras[df_gasolineras[combustible] > 0].copy()
    df_valido["Distancia"] = df_valido.apply(
        lambda row: geodesic(user_location, (row["Latitud"], row["Longitud (WGS84)"])).km, axis=1
    )
    return df_valido.loc[df_valido["Distancia"].idxmin()]

# Crear y mostrar el mapa
def crear_mapa(df_resultado):
    if df_resultado.empty:
        return folium.Map(location=[40.4165, -3.70256], zoom_start=6)

    centro = [df_resultado["Latitud"].mean(), df_resultado["Longitud (WGS84)"].mean()]
    mapa = folium.Map(location=centro, zoom_start=7)
    marker_cluster = MarkerCluster().add_to(mapa)

    for _, row in df_resultado.iterrows():
        popup = f"{row['Rótulo']}<br>{row['Dirección']}<br>{row['Municipio']}<br>{row[combo_combustible.get()]} €/L"
        folium.Marker(
            location=[row["Latitud"], row["Longitud (WGS84)"]],
            popup=popup
        ).add_to(marker_cluster)

    return mapa

def mostrar_mapa(df_resultado):
    mapa = crear_mapa(df_resultado)
    mapa.save("mapa_gasolineras.html")
    import webbrowser
    webbrowser.open("mapa_gasolineras.html")

# Mostrar gráfico comparativo
def mostrar_graficos(info, combustible):
    ciudad = info["Municipio"]
    precio = info[combustible]
    df_ciudad = df_gasolineras[df_gasolineras["Municipio"] == ciudad]
    media_ciudad = df_ciudad[combustible].mean()
    media_nacional = df_gasolineras[combustible].mean()

    fig, ax = plt.subplots(2, 1, figsize=(5, 6))
    ax[0].bar(["Gasolinera", "Media ciudad", "Media España"], [precio, media_ciudad, media_nacional], color=["blue", "orange", "green"])
    ax[0].set_title("Comparativa de precios")
    return fig

def mostrar_popup_grafico(info, combustible):
    popup = tk.Toplevel(root)
    popup.title("Gráficos de precios")
    fig = mostrar_graficos(info, combustible)
    canvas = FigureCanvasTkAgg(fig, master=popup)
    canvas.draw()
    canvas.get_tk_widget().pack()

# Buscar según filtros
def buscar():
    ciudad = entry_ciudad.get()
    combustible = combo_combustible.get()
    df_resultado = filtrar_gasolineras(ciudad, combustible)

    for widget in frame_resultados.winfo_children():
        widget.destroy()

    if df_resultado.empty:
        tk.Label(frame_resultados, text="No se encontraron resultados").pack()
        return

    for _, row in df_resultado.iterrows():
        frame = tk.Frame(frame_resultados, relief=tk.RAISED, bd=1, padx=4, pady=4)
        tk.Label(frame, text=f"{row['Rótulo']} - {row[combustible]} €/L").pack()
        tk.Label(frame, text=row["Dirección"]).pack()
        btn = tk.Button(frame, text="Ver gráficos", command=lambda r=row: mostrar_popup_grafico(r, combustible))
        btn.pack()
        frame.pack(fill="x", pady=2)

    mostrar_mapa(df_resultado)

# Buscar la gasolinera más cercana
def buscar_mas_cercana():
    user_location = obtener_ubicacion_usuario()
    combustible = combo_combustible.get()
    gasolinera = gasolinera_mas_cercana(user_location, combustible)
    mostrar_popup_grafico(gasolinera, combustible)
    mostrar_mapa(pd.DataFrame([gasolinera]))

# Interfaz gráfica
root = tk.Tk()
root.title("GasWay - Buscador de Gasolineras")

frame_top = tk.Frame(root)
frame_top.pack(pady=10)

tk.Label(frame_top, text="Ciudad:").grid(row=0, column=0)
entry_ciudad = tk.Entry(frame_top)
entry_ciudad.grid(row=0, column=1)

tk.Label(frame_top, text="Combustible:").grid(row=0, column=2)
combo_combustible = ttk.Combobox(frame_top, values=combustibles_disponibles)
combo_combustible.set("Precio Gasolina 95 E5")
combo_combustible.grid(row=0, column=3)

btn_buscar = tk.Button(frame_top, text="Buscar", command=buscar)
btn_buscar.grid(row=0, column=5, padx=5)

btn_cercana = tk.Button(frame_top, text="Gasolinera más cercana", command=buscar_mas_cercana)
btn_cercana.grid(row=0, column=6)

frame_resultados = tk.Frame(root)
frame_resultados.pack(fill="both", expand=True)

root.mainloop()
