"""
Dashboard interactivo para análisis de logs FlyTXT
Ejecutar con: streamlit run dashboard_flytxt.py
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import os

# Configuración de la página
st.set_page_config(
    page_title="Dashboard FlyTXT Logs",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Título principal
st.title("📊 Dashboard de Análisis - FlyTXT Logs")
st.markdown("---")

# Función para cargar datos
@st.cache_data
def load_data():
    """Cargar datos desde el archivo consolidado"""
    try:
        # Cargar el archivo CSV comprimido o normal
        if os.path.exists('consolidated_flytxt_logs.csv.gz'):
            st.sidebar.info("⏳ Cargando datos comprimidos...")
            df = pd.read_csv('consolidated_flytxt_logs.csv.gz', compression='gzip')
            st.sidebar.success(f"✓ Datos cargados: {len(df):,} registros")
        elif os.path.exists('consolidated_flytxt_logs.csv'):
            st.sidebar.info("⏳ Cargando datos... (puede tardar un momento con archivos grandes)")
            df = pd.read_csv('consolidated_flytxt_logs.csv')
            st.sidebar.success(f"✓ Datos cargados: {len(df):,} registros")
        elif os.path.exists('consolidated_flytxt_logs.xlsx'):
            df = pd.read_excel('consolidated_flytxt_logs.xlsx', sheet_name='Datos Consolidados')
            st.sidebar.success(f"✓ Datos cargados desde Excel: {len(df):,} registros")
        else:
            st.error("❌ No se encontró el archivo de datos consolidados")
            st.info("💡 Asegúrate de que el archivo consolidated_flytxt_logs.csv.gz esté en el mismo directorio")
            return None
        
        # Convertir fecha a datetime si es string
        if 'fecha' in df.columns:
            df['fecha'] = pd.to_datetime(df['fecha'])
        
        # Asegurar que mes está correctamente calculado desde la fecha
        if 'fecha' in df.columns:
            df['mes_calculado'] = df['fecha'].dt.month.astype(str).str.zfill(2)
            # Si hay discrepancia entre mes y fecha, corregir
            if 'mes' in df.columns:
                df['mes'] = df['mes_calculado']
        
        return df
    except Exception as e:
        st.error(f"❌ Error al cargar datos: {e}")
        return None

# Cargar datos
with st.spinner("Cargando datos..."):
    df = load_data()

if df is None:
    st.stop()

# Sidebar con filtros
st.sidebar.header("🔍 Filtros")

# Convertir columnas a string para evitar errores de tipo
if 'mes' in df.columns:
    df['mes'] = df['mes'].astype(str).str.zfill(2)  # Asegurar formato 09, 10, 11, 12
if 'pais' in df.columns:
    df['pais'] = df['pais'].astype(str)

# Filtro de país
paises_disponibles = ['Todos'] + sorted(df['pais'].unique().tolist())
pais_seleccionado = st.sidebar.selectbox("País", paises_disponibles)

# Filtro de mes
meses_map = {
    '09': 'Septiembre',
    '10': 'Octubre',
    '11': 'Noviembre',
    '12': 'Diciembre'
}
meses_disponibles = ['Todos'] + sorted(df['mes'].unique().tolist())
mes_seleccionado = st.sidebar.selectbox(
    "Mes", 
    meses_disponibles,
    format_func=lambda x: meses_map.get(x, x) if x != 'Todos' else x
)

# Aplicar filtros
df_filtrado = df.copy()

if pais_seleccionado != 'Todos':
    df_filtrado = df_filtrado[df_filtrado['pais'] == pais_seleccionado]

if mes_seleccionado != 'Todos':
    df_filtrado = df_filtrado[df_filtrado['mes'] == mes_seleccionado]

# Filtro de fecha (se aplica DESPUÉS del filtro de mes para mostrar el rango correcto)
if 'fecha' in df_filtrado.columns:
    fecha_min = df_filtrado['fecha'].min()
    fecha_max = df_filtrado['fecha'].max()
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 📅 Filtro Adicional por Fechas")
    if mes_seleccionado != 'Todos':
        st.sidebar.info(f"ℹ️ Mostrando fechas del mes seleccionado: {meses_map.get(mes_seleccionado, mes_seleccionado)}")
    
    fecha_rango = st.sidebar.date_input(
        "Rango de fechas",
        value=(fecha_min, fecha_max),
        min_value=fecha_min,
        max_value=fecha_max,
        help="Refina aún más el período dentro del mes seleccionado"
    )
    
    # Aplicar filtro de rango de fechas
    if len(fecha_rango) == 2:
        df_filtrado = df_filtrado[
            (df_filtrado['fecha'] >= pd.Timestamp(fecha_rango[0])) &
            (df_filtrado['fecha'] <= pd.Timestamp(fecha_rango[1]))
        ]

# Métricas principales
st.header("📈 Métricas Principales")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        "Total de Registros",
        f"{len(df_filtrado):,}",
        delta=f"{len(df_filtrado) - len(df):,}" if pais_seleccionado != 'Todos' or mes_seleccionado != 'Todos' else None
    )

with col2:
    paises_unicos = df_filtrado['pais'].nunique()
    st.metric("Países", paises_unicos)

with col3:
    if 'fecha' in df_filtrado.columns:
        dias_unicos = df_filtrado['fecha'].nunique()
        st.metric("Días con Datos", dias_unicos)

with col4:
    if 'status' in df_filtrado.columns and len(df_filtrado) > 0:
        tasa_exito = (df_filtrado['status'] == 'success').sum() / len(df_filtrado) * 100
        st.metric("Tasa de Éxito", f"{tasa_exito:.1f}%")
    else:
        st.metric("Tasa de Éxito", "N/A")

st.markdown("---")

# Gráficos principales
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📊 Tendencias", "🌎 Por País", "📅 Día Semana", "📆 Por Fecha", "⏰ Por Hora", "📈 Resumen"
])

with tab1:
    st.subheader("📈 Análisis de Tendencias Temporales")
    st.markdown("""
    **¿Qué muestra?** Evolución diaria del volumen de registros procesados y su tendencia general.
    """)
    
    if len(df_filtrado) == 0:
        st.warning("⚠️ No hay datos con los filtros seleccionados")
    elif 'fecha' in df_filtrado.columns:
        # Registros por día
        registros_dia = df_filtrado.groupby('fecha').size().reset_index(name='registros')
        
        # Calcular estadísticas
        promedio_registros = registros_dia['registros'].mean()
        max_registros = registros_dia['registros'].max()
        min_registros = registros_dia['registros'].min()
        fecha_max = registros_dia.loc[registros_dia['registros'].idxmax(), 'fecha']
        fecha_min = registros_dia.loc[registros_dia['registros'].idxmin(), 'fecha']
        
        # Mostrar estadísticas clave
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("📊 Promedio Diario", f"{promedio_registros:,.0f} registros")
        with col2:
            st.metric("📈 Día Máximo", f"{max_registros:,}", delta=f"{fecha_max}")
        with col3:
            st.metric("📉 Día Mínimo", f"{min_registros:,}", delta=f"{fecha_min}")
        
        st.markdown("---")
        
        # Gráfico principal con anotaciones
        fig_tendencia = go.Figure()
        
        fig_tendencia.add_trace(go.Scatter(
            x=registros_dia['fecha'],
            y=registros_dia['registros'],
            name='Registros Diarios',
            line=dict(color='#1f77b4', width=2),
            fill='tozeroy',
            fillcolor='rgba(31, 119, 180, 0.2)',
            hovertemplate='<b>Fecha:</b> %{x}<br><b>Registros:</b> %{y:,}<extra></extra>'
        ))
        
        # Línea de promedio
        fig_tendencia.add_trace(go.Scatter(
            x=registros_dia['fecha'],
            y=[promedio_registros] * len(registros_dia),
            name=f'Promedio ({promedio_registros:,.0f})',
            line=dict(color='red', width=2, dash='dash'),
            hovertemplate='<b>Promedio:</b> %{y:,}<extra></extra>'
        ))
        
        # Anotar punto máximo
        fig_tendencia.add_annotation(
            x=fecha_max,
            y=max_registros,
            text=f"Máximo: {max_registros:,}",
            showarrow=True,
            arrowhead=2,
            arrowcolor="green",
            bgcolor="lightgreen",
            bordercolor="green"
        )
        
        fig_tendencia.update_layout(
            title='📊 Evolución Diaria de Registros',
            xaxis_title='Fecha',
            yaxis_title='Número de Registros',
            height=450,
            hovermode='x unified',
            showlegend=True
        )
        st.plotly_chart(fig_tendencia, use_container_width=True)
        
        # Promedio móvil
        st.markdown("### 📉 Tendencia Suavizada (Promedio Móvil 7 días)")
        st.markdown("**¿Para qué sirve?** Elimina variaciones diarias y muestra la tendencia real del comportamiento.")
        
        registros_dia['promedio_movil_7d'] = registros_dia['registros'].rolling(window=7, min_periods=1).mean()
        
        fig_promedio = go.Figure()
        fig_promedio.add_trace(go.Scatter(
            x=registros_dia['fecha'],
            y=registros_dia['registros'],
            name='Datos Reales',
            line=dict(color='lightblue', width=1),
            opacity=0.4,
            hovertemplate='<b>Real:</b> %{y:,}<extra></extra>'
        ))
        fig_promedio.add_trace(go.Scatter(
            x=registros_dia['fecha'],
            y=registros_dia['promedio_movil_7d'],
            name='Tendencia (7 días)',
            line=dict(color='red', width=3),
            hovertemplate='<b>Tendencia:</b> %{y:,.0f}<extra></extra>'
        ))
        fig_promedio.update_layout(
            title='Comparación: Datos Reales vs Tendencia',
            xaxis_title='Fecha',
            yaxis_title='Registros',
            height=400,
            hovermode='x unified'
        )
        st.plotly_chart(fig_promedio, use_container_width=True)
        
        # Análisis automático inteligente con storytelling
        st.markdown("---")
        st.markdown("### 🔍 ¿Qué nos dicen los datos?")
        
        # NUEVO: Análisis de patrones por día de semana
        if 'dia_semana' in df_filtrado.columns:
            # Agregar día de semana a registros_dia
            registros_dia_completo = df_filtrado.groupby(['fecha', 'dia_semana']).size().reset_index(name='registros')
            dias_map_en = {
                'Monday': 'Lunes', 'Tuesday': 'Martes', 'Wednesday': 'Miércoles',
                'Thursday': 'Jueves', 'Friday': 'Viernes', 'Saturday': 'Sábado', 'Sunday': 'Domingo'
            }
            
            # Identificar días con caídas significativas
            promedio_temp = registros_dia['registros'].mean()
            umbral_caida = promedio_temp * 0.85  # 15% por debajo del promedio
            dias_con_caida = registros_dia[registros_dia['registros'] < umbral_caida]
            
            if len(dias_con_caida) > 0:
                # Unir con día de semana
                dias_con_caida_completo = dias_con_caida.merge(
                    registros_dia_completo[['fecha', 'dia_semana']], 
                    on='fecha', 
                    how='left'
                )
                
                # Contar qué día de semana aparece más en las caídas
                patron_caidas = dias_con_caida_completo['dia_semana'].value_counts()
                
                if len(patron_caidas) > 0:
                    # Análisis más inteligente: verificar si es realmente un patrón consistente
                    dia_mas_caidas = patron_caidas.index[0]
                    cantidad_caidas = patron_caidas.iloc[0]
                    dia_mas_caidas_es = dias_map_en.get(dia_mas_caidas, dia_mas_caidas)
                    
                    # Calcular cuántos días de ese tipo hay en total
                    total_dias_tipo = len(registros_dia_completo[registros_dia_completo['dia_semana'] == dia_mas_caidas])
                    consistencia = (cantidad_caidas / total_dias_tipo * 100) if total_dias_tipo > 0 else 0
                    
                    # Solo mostrar si es un patrón consistente (>50% de las veces)
                    if consistencia >= 50:
                        # Mostrar fechas específicas con caídas (formato completo YYYY-MM-DD)
                        fechas_caidas = dias_con_caida_completo[dias_con_caida_completo['dia_semana'] == dia_mas_caidas]['fecha'].tolist()
                        
                        # Formatear fechas mostrando mes completo
                        meses_nombre = {
                            '01': 'Enero', '02': 'Febrero', '03': 'Marzo', '04': 'Abril',
                            '05': 'Mayo', '06': 'Junio', '07': 'Julio', '08': 'Agosto',
                            '09': 'Septiembre', '10': 'Octubre', '11': 'Noviembre', '12': 'Diciembre'
                        }
                        
                        fechas_formateadas = []
                        for f in fechas_caidas[:10]:
                            if hasattr(f, 'strftime'):
                                mes_num = f.strftime('%m')
                                dia_num = f.strftime('%d')
                                mes_nombre = meses_nombre.get(mes_num, mes_num)
                                fechas_formateadas.append(f"{dia_num} {mes_nombre}")
                            else:
                                fecha_str = str(f).split()[0]  # Tomar solo la fecha
                                partes = fecha_str.split('-')
                                if len(partes) == 3:
                                    mes_nombre = meses_nombre.get(partes[1], partes[1])
                                    fechas_formateadas.append(f"{partes[2]} {mes_nombre}")
                        
                        fechas_str = ", ".join(fechas_formateadas)
                        
                        promedio_caidas = dias_con_caida_completo[dias_con_caida_completo['dia_semana'] == dia_mas_caidas]['registros'].mean()
                        impacto = ((promedio_temp - promedio_caidas) / promedio_temp * 100)
                        
                        # Análisis más inteligente de la causa
                        if dia_mas_caidas in ['Saturday', 'Sunday']:
                            causa = "Es fin de semana - Típicamente hay menos operaciones de negocio"
                            emoji_causa = "🏖️"
                        elif dia_mas_caidas == 'Monday':
                            causa = "Inicio de semana - Posible procesamiento de pendientes del fin de semana"
                            emoji_causa = "📅"
                        elif dia_mas_caidas == 'Friday':
                            causa = "Fin de semana laboral - Posible reducción anticipada de operaciones"
                            emoji_causa = "🎉"
                        else:
                            causa = "Patrón operativo recurrente - Revisar procesos programados"
                            emoji_causa = "🔍"
                        
                        st.warning(f"""
                        ### 🔍 PATRÓN DETECTADO: Caídas los {dia_mas_caidas_es}
                        
                        **🎯 Descubrimiento:** Los **{dia_mas_caidas_es}** tienen caídas recurrentes en el volumen de registros.
                        
                        📊 **Consistencia:** {consistencia:.0f}% - Ocurre en **{cantidad_caidas} de {total_dias_tipo}** {dia_mas_caidas_es}s analizados
                        
                        📅 **Fechas específicas afectadas:** {fechas_str}{'...' if len(fechas_caidas) > 10 else ''}
                        
                        📊 **Impacto Medido:** 
                        - Promedio general: **{promedio_temp:,.0f} registros/día**
                        - Promedio los {dia_mas_caidas_es}: **{promedio_caidas:,.0f} registros/día**
                        - **Reducción del {impacto:.1f}%** en días {dia_mas_caidas_es}
                        
                        {emoji_causa} **Análisis de Causa:**  
                        {causa}
                        
                        💡 **Recomendación:** Los {dia_mas_caidas_es} consistentemente procesan menos volumen. 
                    {'Posible día de bajo tráfico operativo o procesamiento reducido programado.' if impacto > 20 else 'Reducción moderada esperada.'}
                    """)
            
            # Detectar días con picos (por encima del promedio)
            umbral_pico = promedio_temp * 1.15  # 15% por encima del promedio
            dias_con_pico = registros_dia[registros_dia['registros'] > umbral_pico]
            
            if len(dias_con_pico) > 0:
                dias_con_pico_completo = dias_con_pico.merge(
                    registros_dia_completo[['fecha', 'dia_semana']], 
                    on='fecha', 
                    how='left'
                )
                
                patron_picos = dias_con_pico_completo['dia_semana'].value_counts()
                
                if len(patron_picos) > 0:
                    dia_mas_picos = patron_picos.index[0]
                    cantidad_picos = patron_picos.iloc[0]
                    dia_mas_picos_es = dias_map_en.get(dia_mas_picos, dia_mas_picos)
                    
                    # Calcular consistencia
                    total_dias_tipo_pico = len(registros_dia_completo[registros_dia_completo['dia_semana'] == dia_mas_picos])
                    consistencia_pico = (cantidad_picos / total_dias_tipo_pico * 100) if total_dias_tipo_pico > 0 else 0
                    
                    # Solo mostrar si es consistente (>50%)
                    if consistencia_pico >= 50:
                        fechas_picos = dias_con_pico_completo[dias_con_pico_completo['dia_semana'] == dia_mas_picos]['fecha'].tolist()
                        
                        # Formatear fechas con mes completo
                        meses_nombre = {
                            '01': 'Enero', '02': 'Febrero', '03': 'Marzo', '04': 'Abril',
                            '05': 'Mayo', '06': 'Junio', '07': 'Julio', '08': 'Agosto',
                            '09': 'Septiembre', '10': 'Octubre', '11': 'Noviembre', '12': 'Diciembre'
                        }
                        
                        fechas_picos_formateadas = []
                        for f in fechas_picos[:10]:
                            if hasattr(f, 'strftime'):
                                mes_num = f.strftime('%m')
                                dia_num = f.strftime('%d')
                                mes_nombre = meses_nombre.get(mes_num, mes_num)
                                fechas_picos_formateadas.append(f"{dia_num} {mes_nombre}")
                            else:
                                fecha_str = str(f).split()[0]
                                partes = fecha_str.split('-')
                                if len(partes) == 3:
                                    mes_nombre = meses_nombre.get(partes[1], partes[1])
                                    fechas_picos_formateadas.append(f"{partes[2]} {mes_nombre}")
                        
                        fechas_picos_str = ", ".join(fechas_picos_formateadas)
                        
                        promedio_picos = dias_con_pico_completo[dias_con_pico_completo['dia_semana'] == dia_mas_picos]['registros'].mean()
                        incremento = ((promedio_picos - promedio_temp) / promedio_temp * 100)
                        
                        # Análisis inteligente de causa para picos
                        if dia_mas_picos == 'Monday':
                            causa_pico = "Inicio de semana - Acumulación de trabajo del fin de semana"
                            emoji_pico = "🚀"
                            recomendacion = "Escalar recursos preventivamente los lunes para manejar la carga acumulada"
                        elif dia_mas_picos == 'Tuesday':
                            causa_pico = "Segundo día hábil - Peak operativo de la semana"
                            emoji_pico = "⚡"
                            recomendacion = "Mantener capacidad máxima disponible los martes"
                        elif dia_mas_picos in ['Wednesday', 'Thursday']:
                            causa_pico = "Mitad de semana - Procesamiento intensivo regular"
                            emoji_pico = "💪"
                            recomendacion = "Horario pico normal, mantener recursos estándar"
                        elif dia_mas_picos == 'Friday':
                            causa_pico = "Fin de semana - Cierre de procesos semanales"
                            emoji_pico = "🏁"
                            recomendacion = "Asegurar completar procesos antes del fin de semana"
                        else:
                            causa_pico = "Fin de semana - Posible procesamiento batch programado"
                            emoji_pico = "🔄"
                            recomendacion = "Verificar si son procesos programados o carga inesperada"
                        
                        st.success(f"""
                        ### 📈 PATRÓN DETECTADO: Picos los {dia_mas_picos_es}
                        
                        **🎯 Descubrimiento:** Los **{dia_mas_picos_es}** tienden a tener mayor volumen de procesamiento.
                        
                        📊 **Consistencia:** {consistencia_pico:.0f}% - Ocurre en **{cantidad_picos} de {total_dias_tipo_pico}** {dia_mas_picos_es}s analizados
                        
                        📅 **Fechas específicas con picos:** {fechas_picos_str}{'...' if len(fechas_picos) > 10 else ''}
                        
                        📊 **Impacto Medido:** 
                        - Promedio general: **{promedio_temp:,.0f} registros/día**
                        - Promedio los {dia_mas_picos_es}: **{promedio_picos:,.0f} registros/día**
                        - **Incremento del {incremento:.1f}%** en días {dia_mas_picos_es}
                        
                        {emoji_pico} **Análisis de Causa:**  
                        {causa_pico}
                        
                        💡 **Recomendación:** {recomendacion}
                        """)
        
        # Calcular métricas generales
        primer_valor = registros_dia['registros'].iloc[0]
        ultimo_valor = registros_dia['registros'].iloc[-1]
        cambio_absoluto = ultimo_valor - primer_valor
        cambio_porcentual = (cambio_absoluto / primer_valor * 100) if primer_valor > 0 else 0
        std_dev = registros_dia['registros'].std()
        coef_variacion = (std_dev / promedio_registros * 100) if promedio_registros > 0 else 0
        
        # Historia principal
        if cambio_porcentual > 10:
            icono = "📈"
            mensaje_principal = f"**El volumen está en CRECIMIENTO** ({cambio_porcentual:+.1f}%)"
            explicacion = f"Los datos muestran un aumento sostenido. Pasamos de **{primer_valor:,}** a **{ultimo_valor:,}** registros diarios, ganando **{cambio_absoluto:,}** registros en el período."
            color = "green"
            accion = "✅ **Acción:** Capacidad suficiente. Monitorear el crecimiento para planificar escalamiento futuro."
        elif cambio_porcentual < -10:
            icono = "📉"
            mensaje_principal = f"**El volumen está en DESCENSO** ({cambio_porcentual:.1f}%)"
            explicacion = f"Se observa una caída significativa. Pasamos de **{primer_valor:,}** a **{ultimo_valor:,}** registros diarios, perdiendo **{abs(cambio_absoluto):,}** registros."
            color = "red"
            accion = "⚠️ **Acción:** Investigar causas: ¿Hay problemas técnicos? ¿Es estacional? ¿Cambios en el negocio?"
        else:
            icono = "📊"
            mensaje_principal = f"**El volumen se mantiene ESTABLE** ({cambio_porcentual:+.1f}%)"
            explicacion = f"No hay cambios significativos. El volumen oscila alrededor de **{promedio_registros:,.0f}** registros diarios."
            color = "blue"
            accion = "✅ **Acción:** Operación normal. Sistema funcionando según lo esperado."
        
        st.markdown(f"### {icono} {mensaje_principal}")
        st.write(explicacion)
        st.info(accion)
        
        # Tarjetas visuales
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if coef_variacion < 15:
                st.success(f"""
                **✅ ESTABILIDAD: BUENA**
                
                Variación día a día: **{coef_variacion:.1f}%**
                
                📌 Los datos son predecibles
                """)
            else:
                st.warning(f"""
                **⚠️ ESTABILIDAD: VARIABLE**
                
                Variación día a día: **{coef_variacion:.1f}%**
                
                📌 Hay picos y valles importantes
                """)
        
        with col2:
            rango_pct = ((max_registros - min_registros) / promedio_registros * 100)
            if rango_pct < 30:
                st.success(f"""
                **✅ RANGO: CONTROLADO**
                
                Máx-Mín: **{max_registros - min_registros:,}** ({rango_pct:.0f}%)
                
                📌 Diferencias normales
                """)
            else:
                st.error(f"""
                **🔴 RANGO: AMPLIO**
                
                Máx-Mín: **{max_registros - min_registros:,}** ({rango_pct:.0f}%)
                
                📌 Días muy diferentes entre sí
                """)
        
        with col3:
            anomalias = registros_dia[
                (registros_dia['registros'] > promedio_registros + 2*std_dev) |
                (registros_dia['registros'] < promedio_registros - 2*std_dev)
            ]
            if len(anomalias) == 0:
                st.success(f"""
                **✅ ANOMALÍAS: NINGUNA**
                
                Días fuera de rango: **0**
                
                📌 Todo dentro de lo normal
                """)
            else:
                st.warning(f"""
                **⚠️ ANOMALÍAS: {len(anomalias)} día(s)**
                
                Valores extremos detectados
                
                📌 Revisar estos días
                """)
        
        # Hallazgos específicos
        st.markdown("---")
        st.markdown("### 💡 Hallazgos Específicos")
        
        hallazgos = []
        
        # Hallazgo 1: Día más activo
        hallazgos.append(f"🏆 **{fecha_max}** fue el día MÁS activo con **{max_registros:,} registros** (supera el promedio en {((max_registros - promedio_registros) / promedio_registros * 100):+.1f}%)")
        
        # Hallazgo 2: Día menos activo
        hallazgos.append(f"📉 **{fecha_min}** fue el día MENOS activo con **{min_registros:,} registros** (está {((promedio_registros - min_registros) / promedio_registros * 100):.1f}% por debajo del promedio)")
        
        # Hallazgo 3: Consistencia
        dias_arriba_promedio = len(registros_dia[registros_dia['registros'] > promedio_registros])
        pct_arriba = (dias_arriba_promedio / len(registros_dia) * 100)
        if pct_arriba > 60:
            hallazgos.append(f"📊 **{dias_arriba_promedio}** de **{len(registros_dia)}** días ({pct_arriba:.0f}%) están ARRIBA del promedio - Tendencia al alza reciente")
        elif pct_arriba < 40:
            hallazgos.append(f"📊 Solo **{dias_arriba_promedio}** de **{len(registros_dia)}** días ({pct_arriba:.0f}%) están arriba del promedio - Tendencia a la baja reciente")
        else:
            hallazgos.append(f"📊 **{dias_arriba_promedio}** de **{len(registros_dia)}** días ({pct_arriba:.0f}%) están arriba del promedio - Distribución balanceada")
        
        for hallazgo in hallazgos:
            st.write(f"- {hallazgo}")
        
        # Días anómalos expandibles
        if len(anomalias) > 0:
            with st.expander(f"🔍 Ver detalles de los {len(anomalias)} día(s) anómalos"):
                for _, row in anomalias.iterrows():
                    tipo = "⬆️ PICO" if row['registros'] > promedio_registros else "⬇️ CAÍDA"
                    desviacion = abs(row['registros'] - promedio_registros) / std_dev
                    diferencia = row['registros'] - promedio_registros
                    st.markdown(f"""
                    **{row['fecha']}** - {tipo}
                    - Registros: **{row['registros']:,}** (promedio: {promedio_registros:,.0f})
                    - Diferencia: **{diferencia:+,}** registros ({(diferencia/promedio_registros*100):+.1f}%)
                    - Desviación: **{desviacion:.1f}σ** {'🔴' if desviacion > 3 else '🟡'}
                    """)
                    st.markdown("---")
        
        # NUEVO: Análisis de Consistencia/Confiabilidad
        st.markdown("---")
        st.markdown("### 🔍 Análisis de Consistencia y Confiabilidad")
        
        # Detectar días con cero registros o muy pocos
        umbral_minimo = promedio_registros * 0.1  # 10% del promedio
        dias_problema = registros_dia[registros_dia['registros'] < umbral_minimo]
        
        if len(dias_problema) > 0:
            st.error(f"""
            🚨 **{len(dias_problema)} día(s) con registros anormalmente bajos detectados**  
            (menos del 10% del promedio: {umbral_minimo:,.0f} registros)
            
            **Posibles fallas del sistema o interrupciones:**
            """)
            for _, row in dias_problema.iterrows():
                st.write(f"- **{row['fecha']}**: {row['registros']:,} registros ({(row['registros']/promedio_registros*100):.1f}% del promedio) ⚠️")
        else:
            st.success("✅ No se detectaron días con volumen crítico bajo - Sistema operando consistentemente")
        
        # Calcular uptime/disponibilidad
        dias_con_datos = len(registros_dia)
        if 'fecha' in df_filtrado.columns:
            fecha_min = df_filtrado['fecha'].min()
            fecha_max = df_filtrado['fecha'].max()
            dias_esperados = (fecha_max - fecha_min).days + 1
            uptime = (dias_con_datos / dias_esperados * 100) if dias_esperados > 0 else 100
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("📅 Días con Datos", f"{dias_con_datos}")
            with col2:
                st.metric("📆 Días en Rango", f"{dias_esperados}")
            with col3:
                color = "normal" if uptime >= 95 else "inverse"
                st.metric("✅ Disponibilidad", f"{uptime:.1f}%", delta="Óptimo" if uptime >= 95 else "Revisar")
            
            if uptime < 100:
                dias_faltantes = dias_esperados - dias_con_datos
                st.warning(f"⚠️ Faltan datos de **{dias_faltantes} día(s)** en el rango seleccionado - Posibles gaps en la recolección")

with tab2:
    st.subheader("🌎 Análisis por País")
    st.markdown("""
    **¿Qué muestra?** Comparación del volumen de registros procesados entre diferentes países.
    """)
    
    if len(df_filtrado) == 0:
        st.warning("⚠️ No hay datos con los filtros seleccionados")
    else:
        # NUEVO: Análisis de Tendencias por País (crecimiento/decrecimiento)
        if 'fecha' in df_filtrado.columns and df_filtrado['fecha'].nunique() > 7:
            st.markdown("### 📈 Análisis de Tendencias por País")
            
            tendencias_pais = []
            for pais in df_filtrado['pais'].unique():
                datos_pais = df_filtrado[df_filtrado['pais'] == pais]
                registros_tiempo = datos_pais.groupby('fecha').size().sort_index()
                
                if len(registros_tiempo) > 3:
                    # Calcular tendencia (primeros 30% vs últimos 30%)
                    n = len(registros_tiempo)
                    inicio = registros_tiempo.iloc[:max(1, n//3)].mean()
                    fin = registros_tiempo.iloc[-max(1, n//3):].mean()
                    cambio = ((fin - inicio) / inicio * 100) if inicio > 0 else 0
                    
                    # Calcular volatilidad
                    volatilidad = registros_tiempo.std() / registros_tiempo.mean() * 100 if registros_tiempo.mean() > 0 else 0
                    
                    tendencias_pais.append({
                        'pais': pais.upper(),
                        'tendencia': cambio,
                        'volatilidad': volatilidad,
                        'promedio': registros_tiempo.mean(),
                        'total': len(datos_pais)
                    })
            
            if tendencias_pais:
                df_tendencias = pd.DataFrame(tendencias_pais).sort_values('tendencia', ascending=False)
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("#### 📈 Países en Crecimiento")
                    crecimiento = df_tendencias[df_tendencias['tendencia'] > 5].head(3)
                    if len(crecimiento) > 0:
                        for _, row in crecimiento.iterrows():
                            st.success(f"""
                            **{row['pais']}**: +{row['tendencia']:.1f}% 📈  
                            Promedio: {row['promedio']:,.0f} reg/día | Volatilidad: {row['volatilidad']:.1f}%
                            """)
                    else:
                        st.info("✅ No hay países con crecimiento significativo (>5%)")
                
                with col2:
                    st.markdown("#### 📉 Países en Descenso")
                    descenso = df_tendencias[df_tendencias['tendencia'] < -5].head(3)
                    if len(descenso) > 0:
                        for _, row in descenso.iterrows():
                            st.error(f"""
                            **{row['pais']}**: {row['tendencia']:.1f}% 📉  
                            Promedio: {row['promedio']:,.0f} reg/día | Volatilidad: {row['volatilidad']:.1f}%
                            """)
                    else:
                        st.info("✅ No hay países con descenso significativo (<-5%)")
                
                # Países estables
                estables = df_tendencias[(df_tendencias['tendencia'] >= -5) & (df_tendencias['tendencia'] <= 5)]
                if len(estables) > 0:
                    st.markdown("#### ➡️ Países Estables (-5% a +5%)")
                    estables_str = ", ".join([f"{row['pais']} ({row['tendencia']:+.1f}%)" for _, row in estables.iterrows()])
                    st.info(f"{estables_str}")
                
                # Detectar países con comportamiento anómalo (alta volatilidad)
                anomalos = df_tendencias[df_tendencias['volatilidad'] > 30]
                if len(anomalos) > 0:
                    st.warning(f"""
                    ⚠️ **Países con alta variabilidad detectados:**  
                    {', '.join(anomalos['pais'].tolist())} tienen volatilidad >{30}%  
                    → Comportamiento inconsistente, requiere investigación
                    """)
            
            st.markdown("---")
        
        # Distribución por país
        registros_pais = df_filtrado.groupby('pais').size().reset_index(name='registros')
        registros_pais['porcentaje'] = (registros_pais['registros'] / registros_pais['registros'].sum() * 100).round(2)
        registros_pais = registros_pais.sort_values('registros', ascending=False)
        
        # Tarjetas de resumen por país
        st.markdown("### 📊 Top Países por Volumen")
        cols = st.columns(min(len(registros_pais), 5))
        for i, (idx, row) in enumerate(registros_pais.head(5).iterrows()):
            with cols[i]:
                st.metric(
                    row['pais'].upper(),
                    f"{row['registros']:,}",
                    delta=f"{row['porcentaje']:.1f}%"
                )
        
        st.markdown("---")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Gráfico de barras con valores
            fig_pais = go.Figure()
            fig_pais.add_trace(go.Bar(
                x=registros_pais['pais'],
                y=registros_pais['registros'],
                text=registros_pais['registros'].apply(lambda x: f'{x:,}'),
                textposition='outside',
                marker_color=registros_pais['registros'],
                marker_colorscale='Blues',
                hovertemplate='<b>%{x}</b><br>Registros: %{y:,}<br>Porcentaje: ' + 
                              registros_pais['porcentaje'].astype(str) + '%<extra></extra>'
            ))
            fig_pais.update_layout(
                title='📊 Volumen de Registros por País',
                xaxis_title='País',
                yaxis_title='Número de Registros',
                height=450,
                showlegend=False
            )
            st.plotly_chart(fig_pais, use_container_width=True)
        
        with col2:
            # Gráfico de pastel mejorado
            fig_pie = go.Figure(data=[go.Pie(
                labels=registros_pais['pais'].str.upper(),
                values=registros_pais['registros'],
                hole=0.4,
                textinfo='label+percent',
                textposition='outside',
                hovertemplate='<b>%{label}</b><br>Registros: %{value:,}<br>Porcentaje: %{percent}<extra></extra>'
            )])
            fig_pie.update_layout(
                title='🍕 Distribución Porcentual por País',
                height=450,
                showlegend=True
            )
            st.plotly_chart(fig_pie, use_container_width=True)
        
        # Tabla comparativa
        st.markdown("### 📋 Tabla Comparativa")
        st.dataframe(
            registros_pais.rename(columns={
                'pais': 'País',
                'registros': 'Total Registros',
                'porcentaje': 'Porcentaje (%)'
            }).style.format({
                'Total Registros': '{:,}',
                'Porcentaje (%)': '{:.2f}%'
            }),
            use_container_width=True
        )
        
        # Evolución por país
        if 'fecha' in df_filtrado.columns:
            st.markdown("---")
            st.markdown("### 📈 Evolución Temporal por País")
            st.markdown("**¿Para qué sirve?** Ver cómo cambia el volumen de cada país a lo largo del tiempo.")
            
            registros_pais_tiempo = df_filtrado.groupby(['fecha', 'pais']).size().reset_index(name='registros')
            
            fig_pais_tiempo = px.line(
                registros_pais_tiempo,
                x='fecha',
                y='registros',
                color='pais',
                title='Comparación Temporal entre Países',
                labels={'fecha': 'Fecha', 'registros': 'Registros', 'pais': 'País'}
            )
            fig_pais_tiempo.update_traces(line_width=2)
            fig_pais_tiempo.update_layout(
                height=450,
                hovermode='x unified',
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            st.plotly_chart(fig_pais_tiempo, use_container_width=True)
            
            # Storytelling por país
            st.markdown("---")
            st.markdown("### 🔍 ¿Qué pasa por país?")
            
            pais_dominante = registros_pais.iloc[0]['pais']
            pais_menor = registros_pais.iloc[-1]['pais']
            top3_porcentaje = registros_pais.head(3)['porcentaje'].sum()
            
            # Historia principal
            if registros_pais.iloc[0]['porcentaje'] > 70:
                st.error(f"""
                ### 🚨 ALTO RIESGO: Un solo país domina
                
                **{pais_dominante.upper()}** maneja el **{registros_pais.iloc[0]['porcentaje']:.1f}%** del volumen total.
                
                ⚠️ **Riesgo:** Si este país tiene problemas, impacta gravemente la operación.
                
                💡 **Recomendación:** Diversificar o preparar contingencias para {pais_dominante.upper()}.
                """)
            elif registros_pais.iloc[0]['porcentaje'] > 50:
                st.warning(f"""
                ### ⚠️ CONCENTRACIÓN MODERADA
                
                **{pais_dominante.upper()}** es el líder con **{registros_pais.iloc[0]['porcentaje']:.1f}%** del total.
                
                📊 Hay dependencia significativa pero no crítica.
                
                💡 **Recomendación:** Monitorear el desempeño de {pais_dominante.upper()} de cerca.
                """)
            else:
                st.success(f"""
                ### ✅ DISTRIBUCIÓN BALANCEADA
                
                **{pais_dominante.upper()}** lidera con **{registros_pais.iloc[0]['porcentaje']:.1f}%**, pero sin dominancia excesiva.
                
                📊 El riesgo está bien distribuido entre países.
                
                💡 **Estado:** Configuración saludable y resiliente.
                """)
            
            # Comparativa visual
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown(f"""
                #### 🥇 Líder: {pais_dominante.upper()}
                - **{registros_pais.iloc[0]['registros']:,} registros**
                - **{registros_pais.iloc[0]['porcentaje']:.1f}%** del total
                - Promedio: **{registros_pais.iloc[0]['registros'] / len(df_filtrado['fecha'].unique()):,.0f}/día**
                """)
            
            with col2:
                st.markdown(f"""
                #### 📊 Menor: {pais_menor.upper()}
                - **{registros_pais.iloc[-1]['registros']:,} registros**
                - **{registros_pais.iloc[-1]['porcentaje']:.1f}%** del total
                - Promedio: **{registros_pais.iloc[-1]['registros'] / len(df_filtrado['fecha'].unique()):,.0f}/día**
                """)
            
            # Insights específicos
            st.markdown("### 💡 Insights Clave")
            
            ratio = registros_pais.iloc[0]['registros'] / registros_pais.iloc[-1]['registros']
            st.write(f"1️⃣ **Brecha:** {pais_dominante.upper()} procesa **{ratio:.1f}x más** que {pais_menor.upper()}")
            
            st.write(f"2️⃣ **Top 3:** Los 3 países principales concentran el **{top3_porcentaje:.1f}%** del volumen total")
            
            if top3_porcentaje > 80:
                st.write(f"   ⚠️ Solo 3 países manejan casi todo - Alta concentración")
            else:
                st.write(f"   ✅ Distribución saludable entre múltiples países")
            
            # Países medianos
            if len(registros_pais) > 3:
                paises_medios = registros_pais.iloc[1:3]
                promedio_medios = paises_medios['porcentaje'].mean()
                st.write(f"3️⃣ **Países secundarios:** {', '.join(paises_medios['pais'].str.upper())} tienen promedio de **{promedio_medios:.1f}%** c/u")
            
            # Crecimiento relativo
            if 'fecha' in df_filtrado.columns and len(registros_pais) > 1:
                with st.expander("📈 Ver análisis de crecimiento por país"):
                    for _, pais_row in registros_pais.iterrows():
                        datos_pais = df_filtrado[df_filtrado['pais'] == pais_row['pais']]
                        datos_por_dia = datos_pais.groupby('fecha').size()
                        if len(datos_por_dia) > 1:
                            crecimiento = ((datos_por_dia.iloc[-1] - datos_por_dia.iloc[0]) / datos_por_dia.iloc[0] * 100)
                            icono = "📈" if crecimiento > 0 else "📉" if crecimiento < 0 else "➡️"
                            st.write(f"{icono} **{pais_row['pais'].upper()}**: {crecimiento:+.1f}% en el período")

with tab3:
    st.subheader("📅 Análisis por Día de la Semana")
    st.markdown("""
    **¿Qué muestra?** Patrones de comportamiento según el día de la semana (Lunes, Martes, Miércoles, etc.).
    
    **¿Por qué es útil?** Identifica qué días de la semana tienen mayor/menor carga para planificación de recursos.
    
    ℹ️ **Nota importante:** Este análisis agrupa TODOS los lunes, TODOS los martes, etc. del período seleccionado.
    Por ejemplo, si seleccionas septiembre, suma todos los lunes de septiembre juntos.
    """)
    
    if len(df_filtrado) == 0:
        st.warning("⚠️ No hay datos con los filtros seleccionados")
    elif 'dia_semana' in df_filtrado.columns:
        # Orden de días
        dias_orden = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        dias_es = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
        
        registros_dia_semana = df_filtrado.groupby('dia_semana').size().reset_index(name='registros')
        
        # Crear mapeo de inglés a español
        dia_map = dict(zip(dias_orden, dias_es))
        registros_dia_semana['dia_es'] = registros_dia_semana['dia_semana'].map(dia_map)
        
        # Ordenar por día de la semana
        registros_dia_semana['orden'] = registros_dia_semana['dia_semana'].map(
            {dia: i for i, dia in enumerate(dias_orden)}
        )
        registros_dia_semana = registros_dia_semana.sort_values('orden')
        
        col1, col2 = st.columns(2)
        
        with col1:
            fig_dia = px.bar(
                registros_dia_semana,
                x='dia_es',
                y='registros',
                title='Registros por Día de la Semana',
                labels={'dia_es': 'Día', 'registros': 'Registros'},
                color='registros',
                color_continuous_scale='Viridis'
            )
            fig_dia.update_layout(height=400)
            st.plotly_chart(fig_dia, use_container_width=True)
        
        with col2:
            # Promedio por día de la semana
            if 'fecha' in df_filtrado.columns:
                promedio_dia = df_filtrado.groupby('dia_semana').size() / df_filtrado['fecha'].nunique()
                promedio_dia_df = promedio_dia.reset_index(name='promedio')
                promedio_dia_df['dia_es'] = promedio_dia_df['dia_semana'].map(dia_map)
                promedio_dia_df['orden'] = promedio_dia_df['dia_semana'].map(
                    {dia: i for i, dia in enumerate(dias_orden)}
                )
                promedio_dia_df = promedio_dia_df.sort_values('orden')
                
                fig_promedio_dia = px.line(
                    promedio_dia_df,
                    x='dia_es',
                    y='promedio',
                    title='Promedio de Registros por Día de la Semana',
                    labels={'dia_es': 'Día', 'promedio': 'Promedio de Registros'},
                    markers=True
                )
                fig_promedio_dia.update_layout(height=400)
                st.plotly_chart(fig_promedio_dia, use_container_width=True)
        
        # Mostrar qué fechas específicas corresponden a cada día
        st.markdown("---")
        st.markdown("### 📆 ¿Qué fechas incluye cada día?")
        st.markdown("**Desglose de fechas específicas por día de la semana:**")
        
        if 'fecha' in df_filtrado.columns:
            # Crear DataFrame con fecha y día de semana
            fechas_dias = df_filtrado[['fecha', 'dia_semana']].drop_duplicates().copy()
            fechas_dias['dia_es'] = fechas_dias['dia_semana'].map(dia_map)
            fechas_dias = fechas_dias.sort_values('fecha')
            
            # Agrupar fechas por día de semana
            for dia_en, dia_esp in zip(dias_orden, dias_es):
                fechas_del_dia = fechas_dias[fechas_dias['dia_semana'] == dia_en]['fecha'].tolist()
                if fechas_del_dia:
                    fechas_str = ", ".join([str(f) for f in sorted(fechas_del_dia)])
                    registros_del_dia = registros_dia_semana[registros_dia_semana['dia_semana'] == dia_en]['registros'].values
                    total = registros_del_dia[0] if len(registros_del_dia) > 0 else 0
                    st.write(f"**{dia_esp}** ({len(fechas_del_dia)} días): {fechas_str} → **{total:,} registros totales**")
        
        # Análisis automático de día de semana
        st.markdown("---")
        st.markdown("### 🤖 Análisis Automático")
        
        # Encontrar mejor y peor día
        dia_max_idx = registros_dia_semana['registros'].idxmax()
        dia_min_idx = registros_dia_semana['registros'].idxmin()
        dia_max_nombre = registros_dia_semana.loc[dia_max_idx, 'dia_es']
        dia_min_nombre = registros_dia_semana.loc[dia_min_idx, 'dia_es']
        registros_max = registros_dia_semana.loc[dia_max_idx, 'registros']
        registros_min = registros_dia_semana.loc[dia_min_idx, 'registros']
        
        diferencia_pct = ((registros_max - registros_min) / registros_min * 100)
        
        # Análisis de patrón semanal
        fin_semana = registros_dia_semana[registros_dia_semana['dia_semana'].isin(['Saturday', 'Sunday'])]['registros'].sum()
        entre_semana = registros_dia_semana[~registros_dia_semana['dia_semana'].isin(['Saturday', 'Sunday'])]['registros'].sum()
        
        if fin_semana > entre_semana * 0.4:  # Más del 40% del total
            patron = "📈 **Actividad alta en fin de semana** - Similar volumen que días laborales"
        elif fin_semana < entre_semana * 0.2:
            patron = "📉 **Baja actividad en fin de semana** - Principalmente procesamiento entre semana"
        else:
            patron = "📊 **Actividad moderada en fin de semana** - Volumen constante toda la semana"
        
        st.success(f"""
        **📅 Día con Mayor Carga:**  
        **{dia_max_nombre}** con **{registros_max:,} registros**
        
        **📉 Día con Menor Carga:**  
        **{dia_min_nombre}** con **{registros_min:,} registros**
        
        **📊 Diferencia:**  
        El día más activo procesa **{diferencia_pct:.1f}% más** que el menos activo
        
        **🎯 Patrón Semanal:**  
        {patron}
        """)
        
        if diferencia_pct > 30:
            st.warning(f"""
            ⚠️ **Alta variabilidad semanal detectada**  
            Considere ajustar recursos según el día de la semana para optimizar costos.
            """)
        else:
            st.info("✅ Distribución uniforme durante la semana - Carga balanceada.")

with tab4:
    st.subheader("📆 Análisis por Fecha Específica")
    st.markdown("""
    **¿Qué muestra?** Comportamiento día a día según fechas específicas del calendario (01, 02, 03, etc.).
    **¿Por qué es útil?** Identifica días concretos con comportamiento inusual o patrones mensuales.
    """)
    
    if len(df_filtrado) == 0:
        st.warning("⚠️ No hay datos con los filtros seleccionados")
    elif 'fecha' in df_filtrado.columns:
        # Agrupar por fecha específica
        registros_por_fecha = df_filtrado.groupby('fecha').size().reset_index(name='registros')
        registros_por_fecha = registros_por_fecha.sort_values('fecha')
        
        # Extraer día del mes
        registros_por_fecha['dia_mes'] = pd.to_datetime(registros_por_fecha['fecha']).dt.day
        
        # Estadísticas clave
        promedio_fecha = registros_por_fecha['registros'].mean()
        max_fecha = registros_por_fecha['registros'].max()
        min_fecha = registros_por_fecha['registros'].min()
        fecha_max_val = registros_por_fecha.loc[registros_por_fecha['registros'].idxmax(), 'fecha']
        fecha_min_val = registros_por_fecha.loc[registros_por_fecha['registros'].idxmin(), 'fecha']
        
        # Mostrar métricas principales
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("📅 Total Días", len(registros_por_fecha))
        with col2:
            st.metric("📊 Promedio/Día", f"{promedio_fecha:,.0f}")
        with col3:
            st.metric("📈 Día Máximo", f"{max_fecha:,}")
        with col4:
            st.metric("📉 Día Mínimo", f"{min_fecha:,}")
        
        st.markdown("---")
        
        # Gráfico de calendario (línea temporal con fechas)
        fig_fechas = go.Figure()
        
        fig_fechas.add_trace(go.Scatter(
            x=registros_por_fecha['fecha'],
            y=registros_por_fecha['registros'],
            mode='lines+markers',
            name='Registros por Fecha',
            line=dict(color='#2E86AB', width=2),
            marker=dict(size=6, color='#A23B72'),
            hovertemplate='<b>Fecha:</b> %{x}<br><b>Registros:</b> %{y:,}<extra></extra>'
        ))
        
        # Línea de promedio
        fig_fechas.add_trace(go.Scatter(
            x=registros_por_fecha['fecha'],
            y=[promedio_fecha] * len(registros_por_fecha),
            name=f'Promedio ({promedio_fecha:,.0f})',
            line=dict(color='orange', width=2, dash='dash'),
            hovertemplate='<b>Promedio:</b> %{y:,}<extra></extra>'
        ))
        
        # Resaltar máximo y mínimo
        fig_fechas.add_annotation(
            x=fecha_max_val,
            y=max_fecha,
            text=f"Máximo: {max_fecha:,}",
            showarrow=True,
            arrowhead=2,
            arrowcolor="green",
            bgcolor="lightgreen",
            bordercolor="green"
        )
        
        fig_fechas.add_annotation(
            x=fecha_min_val,
            y=min_fecha,
            text=f"Mínimo: {min_fecha:,}",
            showarrow=True,
            arrowhead=2,
            arrowcolor="red",
            bgcolor="lightcoral",
            bordercolor="red"
        )
        
        fig_fechas.update_layout(
            title='📊 Registros por Fecha del Calendario',
            xaxis_title='Fecha',
            yaxis_title='Número de Registros',
            height=500,
            hovermode='x unified',
            showlegend=True
        )
        st.plotly_chart(fig_fechas, use_container_width=True)
        
        # Análisis por día del mes (patrón mensual)
        st.markdown("### 📅 Patrón por Día del Mes (01-31)")
        st.markdown("**¿Qué muestra?** Si ciertos días del mes (ej: inicio, mitad, fin) tienen patrones consistentes.")
        
        dia_mes_stats = df_filtrado.copy()
        dia_mes_stats['dia_mes'] = pd.to_datetime(dia_mes_stats['fecha']).dt.day
        registros_dia_mes = dia_mes_stats.groupby('dia_mes').size().reset_index(name='registros')
        registros_dia_mes = registros_dia_mes.sort_values('dia_mes')
        
        fig_dia_mes = px.bar(
            registros_dia_mes,
            x='dia_mes',
            y='registros',
            title='Distribución por Día del Mes',
            labels={'dia_mes': 'Día del Mes', 'registros': 'Total Registros'},
            color='registros',
            color_continuous_scale='Blues'
        )
        fig_dia_mes.update_layout(height=400)
        fig_dia_mes.update_xaxes(dtick=1)  # Mostrar todos los días
        st.plotly_chart(fig_dia_mes, use_container_width=True)
        
        # Identificar períodos del mes
        if len(registros_dia_mes) > 0:
            inicio_mes = registros_dia_mes[registros_dia_mes['dia_mes'] <= 10]['registros'].sum()
            mitad_mes = registros_dia_mes[(registros_dia_mes['dia_mes'] > 10) & (registros_dia_mes['dia_mes'] <= 20)]['registros'].sum()
            fin_mes = registros_dia_mes[registros_dia_mes['dia_mes'] > 20]['registros'].sum()
            
            total_mes = inicio_mes + mitad_mes + fin_mes
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("🔵 Inicio Mes (01-10)", f"{inicio_mes:,}", 
                         delta=f"{(inicio_mes/total_mes*100):.1f}%")
            with col2:
                st.metric("🟢 Mitad Mes (11-20)", f"{mitad_mes:,}", 
                         delta=f"{(mitad_mes/total_mes*100):.1f}%")
            with col3:
                st.metric("🟡 Fin Mes (21-31)", f"{fin_mes:,}", 
                         delta=f"{(fin_mes/total_mes*100):.1f}%")
        
        # Análisis automático
        st.markdown("---")
        st.markdown("### 🤖 Análisis Automático por Fechas")
        
        # Calcular variabilidad
        coef_variacion = (registros_por_fecha['registros'].std() / promedio_fecha * 100)
        
        # Detectar anomalías (fechas con desviación > 2 sigma)
        desv_std = registros_por_fecha['registros'].std()
        anomalias = registros_por_fecha[
            (registros_por_fecha['registros'] > promedio_fecha + 2*desv_std) |
            (registros_por_fecha['registros'] < promedio_fecha - 2*desv_std)
        ]
        
        # Patrón mensual
        if inicio_mes > mitad_mes * 1.3 and inicio_mes > fin_mes * 1.3:
            patron_mes = "📈 **Alta carga al inicio del mes** - Posible procesamiento de cierre mensual previo"
        elif fin_mes > inicio_mes * 1.3 and fin_mes > mitad_mes * 1.3:
            patron_mes = "📊 **Acumulación al final del mes** - Cierre de período con mayor actividad"
        elif mitad_mes > inicio_mes * 1.2 and mitad_mes > fin_mes * 1.2:
            patron_mes = "📅 **Pico a mitad de mes** - Patrón quincenal posible"
        else:
            patron_mes = "➡️ **Distribución uniforme** - Sin patrones mensuales claros"
        
        st.success(f"""
        **📅 Fecha con Mayor Actividad:**  
        **{fecha_max_val}** con **{max_fecha:,} registros**
        
        **📉 Fecha con Menor Actividad:**  
        **{fecha_min_val}** con **{min_fecha:,} registros**
        
        **📊 Variabilidad:**  
        Coeficiente de variación: **{coef_variacion:.1f}%** 
        {' (Alta variabilidad - comportamiento inconsistente)' if coef_variacion > 30 else ' (Baja variabilidad - comportamiento estable)'}
        
        **🎯 Patrón Mensual:**  
        {patron_mes}
        """)
        
        # Mostrar anomalías si existen
        if len(anomalias) > 0:
            st.warning(f"""
            ⚠️ **{len(anomalias)} fechas con comportamiento anómalo detectadas:**
            
            Estas fechas tienen volúmenes significativamente diferentes al promedio (>2 desviaciones estándar).
            """)
            
            # Mostrar tabla de anomalías
            anomalias_display = anomalias[['fecha', 'registros']].copy()
            anomalias_display['desviacion_promedio'] = (
                (anomalias_display['registros'] - promedio_fecha) / promedio_fecha * 100
            ).round(1)
            anomalias_display.columns = ['Fecha', 'Registros', 'Desviación (%)']
            st.dataframe(anomalias_display, use_container_width=True)
            
            # Insight adicional
            if anomalias['registros'].min() < promedio_fecha * 0.5:
                st.error("🚨 Algunas fechas tienen menos del 50% del volumen esperado - Revisar posibles fallas")
            if anomalias['registros'].max() > promedio_fecha * 2:
                st.info("💡 Algunas fechas duplican el volumen normal - Posible reprocesamiento o carga especial")
        else:
            st.info("✅ No se detectaron anomalías significativas - Comportamiento estable por fecha")
        
        # NUEVO: Análisis Predictivo Simple
        if len(registros_por_fecha) >= 7:
            st.markdown("---")
            st.markdown("### 🔮 Análisis Predictivo Simple")
            
            # Calcular tendencia lineal simple (últimos 7 días)
            ultimos_dias = registros_por_fecha.tail(7)
            if len(ultimos_dias) >= 3:
                # Tendencia simple: comparar promedio primera mitad vs segunda mitad
                mitad = len(ultimos_dias) // 2
                promedio_inicio = ultimos_dias.head(mitad)['registros'].mean()
                promedio_fin = ultimos_dias.tail(len(ultimos_dias) - mitad)['registros'].mean()
                tendencia_pct = ((promedio_fin - promedio_inicio) / promedio_inicio * 100) if promedio_inicio > 0 else 0
                
                # Pronóstico simple para mañana (basado en promedio últimos 3 días + tendencia)
                promedio_ultimos_3 = ultimos_dias.tail(3)['registros'].mean()
                pronostico = promedio_ultimos_3 * (1 + tendencia_pct / 100)
                
                col1, col2 = st.columns(2)
                with col1:
                    if tendencia_pct > 0:
                        st.metric("📈 Tendencia (7 días)", f"+{tendencia_pct:.1f}%", delta="Creciente")
                    else:
                        st.metric("📉 Tendencia (7 días)", f"{tendencia_pct:.1f}%", delta="Decreciente")
                
                with col2:
                    st.metric("🔮 Pronóstico Próximo Día", f"{pronostico:,.0f} registros")
                
                # Alerta de anomalía esperada
                fecha_maxima = registros_por_fecha['fecha'].max()
                if 'dia_semana' in df_filtrado.columns:
                    # Obtener día de semana del último día
                    ultimo_dia_semana = df_filtrado[df_filtrado['fecha'] == fecha_maxima]['dia_semana'].iloc[0] if len(df_filtrado[df_filtrado['fecha'] == fecha_maxima]) > 0 else None
                    
                    if ultimo_dia_semana:
                        dias_orden_pred = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
                        idx_actual = dias_orden_pred.index(ultimo_dia_semana) if ultimo_dia_semana in dias_orden_pred else -1
                        proximo_dia_semana = dias_orden_pred[(idx_actual + 1) % 7] if idx_actual >= 0 else None
                        
                        if proximo_dia_semana:
                            dias_map_pred = {
                                'Monday': 'Lunes', 'Tuesday': 'Martes', 'Wednesday': 'Miércoles',
                                'Thursday': 'Jueves', 'Friday': 'Viernes', 'Saturday': 'Sábado', 'Sunday': 'Domingo'
                            }
                            proximo_dia_es = dias_map_pred.get(proximo_dia_semana, proximo_dia_semana)
                            
                            # Calcular promedio histórico de ese día de semana
                            historico_dia = df_filtrado[df_filtrado['dia_semana'] == proximo_dia_semana].groupby('fecha').size().mean()
                            
                            if abs(pronostico - historico_dia) > historico_dia * 0.2:
                                st.warning(f"""
                                ⚠️ **Alerta de Anomalía Esperada**  
                                El próximo día será **{proximo_dia_es}**, que históricamente tiene **{historico_dia:,.0f} registros/día**.  
                                El pronóstico de **{pronostico:,.0f}** difiere en {abs(pronostico - historico_dia) / historico_dia * 100:.0f}%.  
                                → Monitorear de cerca para detectar desviaciones.
                                """)
                            else:
                                st.success(f"""
                                ✅ **Pronóstico Consistente**  
                                El próximo día (**{proximo_dia_es}**) debería tener ~**{pronostico:,.0f} registros**.  
                                Esto es consistente con el promedio histórico de {proximo_dia_es}: **{historico_dia:,.0f} registros**.
                                """)
                
                # Detectar estacionalidad (primera semana vs última semana del mes)
                if 'dia_mes' in df_filtrado.columns or len(registros_dia_mes) > 0:
                    primera_semana = registros_dia_mes[registros_dia_mes['dia_mes'] <= 7]['registros'].mean()
                    ultima_semana = registros_dia_mes[registros_dia_mes['dia_mes'] >= 24]['registros'].mean()
                    
                    if abs(primera_semana - ultima_semana) > promedio_fecha * 0.15:
                        diferencia_pct = ((primera_semana - ultima_semana) / ultima_semana * 100)
                        periodo = "primera" if primera_semana > ultima_semana else "última"
                        st.info(f"""
                        📊 **Estacionalidad Mensual Detectada:**  
                        La **{periodo} semana del mes** tiene {abs(diferencia_pct):.0f}% {'más' if diferencia_pct > 0 else 'menos'} carga que la otra.  
                        → Considerar este patrón en la planificación mensual.
                        """)

with tab5:
    st.subheader("⏰ Análisis por Hora del Día")
    
    if len(df_filtrado) == 0:
        st.warning("⚠️ No hay datos con los filtros seleccionados")
    elif 'hora' in df_filtrado.columns:
        registros_hora = df_filtrado.groupby('hora').size().reset_index(name='registros')
        
        col1, col2 = st.columns(2)
        
        with col1:
            fig_hora = px.bar(
                registros_hora,
                x='hora',
                y='registros',
                title='Distribución de Registros por Hora',
                labels={'hora': 'Hora del Día', 'registros': 'Registros'},
                color='registros',
                color_continuous_scale='Plasma'
            )
            fig_hora.update_layout(height=400)
            st.plotly_chart(fig_hora, use_container_width=True)
        
        with col2:
            # Heatmap de día de semana vs hora
            if 'dia_semana' in df_filtrado.columns:
                heatmap_data = df_filtrado.groupby(['dia_semana', 'hora']).size().reset_index(name='registros')
                heatmap_pivot = heatmap_data.pivot(index='hora', columns='dia_semana', values='registros').fillna(0)
                
                # Reordenar columnas
                dias_orden = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
                heatmap_pivot = heatmap_pivot[[col for col in dias_orden if col in heatmap_pivot.columns]]
                
                fig_heatmap = px.imshow(
                    heatmap_pivot,
                    title='Heatmap: Hora vs Día de la Semana',
                    labels=dict(x="Día", y="Hora", color="Registros"),
                    color_continuous_scale='YlOrRd'
                )
                fig_heatmap.update_layout(height=400)
                st.plotly_chart(fig_heatmap, use_container_width=True)
        
        # Análisis automático por hora
        st.markdown("---")
        st.markdown("### 🤖 Análisis Automático")
        
        # Encontrar horas pico
        hora_max = registros_hora.loc[registros_hora['registros'].idxmax(), 'hora']
        hora_min = registros_hora.loc[registros_hora['registros'].idxmin(), 'hora']
        registros_hora_max = registros_hora['registros'].max()
        registros_hora_min = registros_hora['registros'].min()
        
        # Clasificar horarios
        registros_hora['periodo'] = registros_hora['hora'].apply(
            lambda x: 'Madrugada (0-6h)' if x < 6 
            else 'Mañana (6-12h)' if x < 12
            else 'Tarde (12-18h)' if x < 18
            else 'Noche (18-24h)'
        )
        
        periodo_max = registros_hora.groupby('periodo')['registros'].sum().idxmax()
        
        # Análisis de horario laboral vs no laboral
        horario_laboral = registros_hora[(registros_hora['hora'] >= 8) & (registros_hora['hora'] <= 18)]['registros'].sum()
        horario_no_laboral = registros_hora[(registros_hora['hora'] < 8) | (registros_hora['hora'] > 18)]['registros'].sum()
        pct_laboral = (horario_laboral / (horario_laboral + horario_no_laboral) * 100)
        
        if pct_laboral > 70:
            patron_horario = "🏢 **Principalmente en horario laboral** (8am-6pm)"
        elif pct_laboral > 50:
            patron_horario = "📊 **Balanceado** entre horario laboral y no laboral"
        else:
            patron_horario = "🌙 **Mayor actividad fuera de horario laboral**"
        
        st.success(f"""
        **⏰ Hora Pico:**  
        **{int(hora_max):02d}:00** con **{registros_hora_max:,} registros**
        
        **🔻 Hora Valle:**  
        **{int(hora_min):02d}:00** con **{registros_hora_min:,} registros**
        
        **🎯 Período Más Activo:**  
        **{periodo_max}** concentra el mayor volumen de procesamiento
        
        **💼 Distribución Laboral:**  
        {patron_horario} - **{pct_laboral:.1f}%** en horario 8am-6pm
        """)
        
        # Recomendaciones
        if hora_max >= 8 and hora_max <= 18:
            st.info("💡 **Recomendación:** Pico de actividad en horario laboral. Considere escalar recursos durante este período.")
        else:
            st.warning("⚠️ **Atención:** Pico de actividad fuera de horario laboral. Verifique si es procesamiento programado o tráfico inesperado.")
        
        # NUEVO: Análisis de Horas Críticas y Ventanas de Oportunidad
        st.markdown("---")
        st.markdown("### 🎯 Horas Críticas y Ventanas de Oportunidad")
        
        # Identificar ventanas de baja carga (para mantenimiento)
        promedio_hora = registros_hora['registros'].mean()
        ventanas_oportunidad = registros_hora[registros_hora['registros'] < promedio_hora * 0.5]
        
        if len(ventanas_oportunidad) > 0:
            horas_ventana = ventanas_oportunidad.sort_values('registros')['hora'].tolist()
            horas_str = ", ".join([f"{int(h):02d}:00" for h in horas_ventana])
            st.info(f"""
            💡 **Ventanas de Mantenimiento Recomendadas:**  
            Horas con <50% de la carga promedio: **{horas_str}**  
            → Ideal para tareas de mantenimiento, actualizaciones o respaldos
            """)
        
        # Detectar horas con picos recurrentes
        if 'fecha' in df_filtrado.columns:
            dias_con_pico_por_hora = {}
            umbral_pico_hora = promedio_hora * 1.3
            
            for hora_val in registros_hora[registros_hora['registros'] > umbral_pico_hora]['hora'].tolist():
                datos_hora = df_filtrado[df_filtrado['hora'] == hora_val]
                dias_con_pico = datos_hora.groupby('fecha').size()
                dias_con_pico_por_hora[hora_val] = len(dias_con_pico)
            
            if dias_con_pico_por_hora:
                hora_mas_consistente = max(dias_con_pico_por_hora, key=dias_con_pico_por_hora.get)
                dias_consistentes = dias_con_pico_por_hora[hora_mas_consistente]
                total_dias = df_filtrado['fecha'].nunique()
                consistencia = (dias_consistentes / total_dias * 100)
                
                st.success(f"""
                🔥 **Hora Pico Más Consistente:** **{int(hora_mas_consistente):02d}:00**  
                Tiene carga alta en **{dias_consistentes}** de **{total_dias}** días ({consistencia:.0f}%)  
                → Esta hora requiere máxima capacidad de forma predecible
                """)
        
        # Análisis de procesamiento nocturno vs diurno
        nocturno = registros_hora[(registros_hora['hora'] >= 22) | (registros_hora['hora'] < 6)]['registros'].sum()
        diurno = registros_hora[(registros_hora['hora'] >= 6) & (registros_hora['hora'] < 22)]['registros'].sum()
        total_hora = nocturno + diurno
        pct_nocturno = (nocturno / total_hora * 100) if total_hora > 0 else 0
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("🌙 Nocturno (22-6h)", f"{nocturno:,}", delta=f"{pct_nocturno:.1f}%")
        with col2:
            st.metric("☀️ Diurno (6-22h)", f"{diurno:,}", delta=f"{(100-pct_nocturno):.1f}%")
        with col3:
            tipo = "Nocturno" if pct_nocturno > 50 else "Diurno"
            st.metric("🎯 Perfil", tipo, delta="Dominante")
        
        if pct_nocturno > 40:
            st.warning(f"""
            ⚠️ **Alto procesamiento nocturno detectado** ({pct_nocturno:.1f}%)  
            → Verifique si corresponde a procesos batch programados o si indica problemas de latencia diurna
            """)
        
        # Calcular tasa de procesamiento (eficiencia)
        if 'fecha' in df_filtrado.columns:
            total_registros = len(df_filtrado)
            total_horas = df_filtrado['fecha'].nunique() * 24
            tasa_procesamiento = total_registros / total_horas if total_horas > 0 else 0
            
            st.markdown("### 📊 Eficiencia Operativa")
            col1, col2 = st.columns(2)
            with col1:
                st.metric("⚡ Tasa de Procesamiento", f"{tasa_procesamiento:,.0f} reg/hora")
            with col2:
                max_tasa = registros_hora['registros'].max() / len(df_filtrado['fecha'].unique()) if len(df_filtrado['fecha'].unique()) > 0 else 0
                st.metric("🔥 Tasa Máxima Horaria", f"{max_tasa:,.0f} reg/hora/día")

with tab6:
    st.subheader("📈 Dashboard Ejecutivo")
    st.markdown("""
    **Resumen consolidado** con las métricas y gráficos más importantes del análisis.
    """)
    
    if len(df_filtrado) == 0:
        st.warning("⚠️ No hay datos con los filtros seleccionados")
    else:
        # KPIs principales en grande
        st.markdown("### 🎯 Indicadores Clave (KPIs)")
        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        
        with kpi1:
            st.markdown(f"""
            <div style='text-align: center; padding: 20px; background-color: #1f77b4; border-radius: 10px;'>
                <h2 style='color: white; margin: 0;'>{len(df_filtrado):,}</h2>
                <p style='color: white; margin: 5px 0 0 0;'>Total Registros</p>
            </div>
            """, unsafe_allow_html=True)
        
        with kpi2:
            paises_count = df_filtrado['pais'].nunique()
            st.markdown(f"""
            <div style='text-align: center; padding: 20px; background-color: #ff7f0e; border-radius: 10px;'>
                <h2 style='color: white; margin: 0;'>{paises_count}</h2>
                <p style='color: white; margin: 5px 0 0 0;'>Países Activos</p>
            </div>
            """, unsafe_allow_html=True)
        
        with kpi3:
            if 'fecha' in df_filtrado.columns:
                dias_count = df_filtrado['fecha'].nunique()
                st.markdown(f"""
                <div style='text-align: center; padding: 20px; background-color: #2ca02c; border-radius: 10px;'>
                    <h2 style='color: white; margin: 0;'>{dias_count}</h2>
                    <p style='color: white; margin: 5px 0 0 0;'>Días Analizados</p>
                </div>
                """, unsafe_allow_html=True)
        
        with kpi4:
            promedio_dia = len(df_filtrado) / df_filtrado['fecha'].nunique() if 'fecha' in df_filtrado.columns else 0
            st.markdown(f"""
            <div style='text-align: center; padding: 20px; background-color: #d62728; border-radius: 10px;'>
                <h2 style='color: white; margin: 0;'>{promedio_dia:,.0f}</h2>
                <p style='color: white; margin: 5px 0 0 0;'>Promedio/Día</p>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Mini gráficos en dos columnas
        col1, col2 = st.columns(2)
        
        with col1:
            # Top 5 países
            st.markdown("#### 🏆 Top 5 Países")
            top_paises = df_filtrado['pais'].value_counts().head(5)
            fig_top = px.bar(
                x=top_paises.values,
                y=top_paises.index,
                orientation='h',
                text=top_paises.values,
                labels={'x': 'Registros', 'y': 'País'}
            )
            fig_top.update_traces(texttemplate='%{text:,}', textposition='outside')
            fig_top.update_layout(height=300, showlegend=False)
            st.plotly_chart(fig_top, use_container_width=True)
        
        with col2:
            # Distribución por día de semana
            if 'dia_semana' in df_filtrado.columns:
                st.markdown("#### 📅 Por Día de Semana")
                dias_map = {
                    'Monday': 'Lun', 'Tuesday': 'Mar', 'Wednesday': 'Mié',
                    'Thursday': 'Jue', 'Friday': 'Vie', 'Saturday': 'Sáb', 'Sunday': 'Dom'
                }
                dia_counts = df_filtrado['dia_semana'].value_counts()
                dia_counts.index = dia_counts.index.map(lambda x: dias_map.get(str(x), str(x)))
                
                fig_dias = px.bar(
                    x=dia_counts.index,
                    y=dia_counts.values,
                    labels={'x': 'Día', 'y': 'Registros'}
                )
                fig_dias.update_layout(height=300, showlegend=False)
                st.plotly_chart(fig_dias, use_container_width=True)
        
        st.markdown("---")
        
        # Tendencia simplificada
        if 'fecha' in df_filtrado.columns:
            st.markdown("#### 📊 Tendencia General")
            registros_dia = df_filtrado.groupby('fecha').size().reset_index(name='registros')
            
            fig_simple = px.area(
                registros_dia,
                x='fecha',
                y='registros',
                labels={'fecha': 'Fecha', 'registros': 'Registros'}
            )
            fig_simple.update_layout(height=300)
            st.plotly_chart(fig_simple, use_container_width=True)
        
        # NUEVO: Análisis de Tamaño de Archivos
        if 's3_size' in df_filtrado.columns and 'local_size' in df_filtrado.columns:
            st.markdown("---")
            st.markdown("### 📦 Análisis de Tamaño de Archivos")
            
            # Convertir a MB si es necesario
            df_sizes = df_filtrado[['s3_size', 'local_size']].copy()
            
            # Calcular estadísticas
            avg_s3_size = df_sizes['s3_size'].mean()
            avg_local_size = df_sizes['local_size'].mean()
            ratio_compresion = (1 - avg_local_size / avg_s3_size) * 100 if avg_s3_size > 0 else 0
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("📤 Promedio S3", f"{avg_s3_size:,.0f} bytes")
            with col2:
                st.metric("💾 Promedio Local", f"{avg_local_size:,.0f} bytes")
            with col3:
                st.metric("🗜️ Compresión", f"{ratio_compresion:.1f}%")
            
            # Detectar archivos anormalmente grandes o pequeños
            q1_s3 = df_sizes['s3_size'].quantile(0.25)
            q3_s3 = df_sizes['s3_size'].quantile(0.75)
            iqr_s3 = q3_s3 - q1_s3
            limite_superior = q3_s3 + 1.5 * iqr_s3
            limite_inferior = max(0, q1_s3 - 1.5 * iqr_s3)
            
            anomalos_grandes = df_filtrado[df_filtrado['s3_size'] > limite_superior]
            anomalos_pequeños = df_filtrado[df_filtrado['s3_size'] < limite_inferior]
            
            if len(anomalos_grandes) > 0 or len(anomalos_pequeños) > 0:
                st.warning(f"""
                ⚠️ **Archivos con tamaño anómalo detectados:**  
                - **{len(anomalos_grandes)}** archivos anormalmente grandes (>{limite_superior:,.0f} bytes)  
                - **{len(anomalos_pequeños)}** archivos anormalmente pequeños (<{limite_inferior:,.0f} bytes)  
                → Revisar posibles problemas de procesamiento o corrupción
                """)
            else:
                st.success("✅ Tamaños de archivo consistentes - No se detectaron anomalías")
            
            # Relación tamaño vs cantidad por país
            if 'pais' in df_filtrado.columns:
                sizes_pais = df_filtrado.groupby('pais').agg({
                    's3_size': 'mean',
                    'pais': 'count'
                }).rename(columns={'pais': 'cantidad'})
                sizes_pais['pais'] = sizes_pais.index
                
                fig_sizes = px.scatter(
                    sizes_pais,
                    x='cantidad',
                    y='s3_size',
                    text='pais',
                    title='Relación: Cantidad de Registros vs Tamaño Promedio por País',
                    labels={'cantidad': 'Cantidad de Registros', 's3_size': 'Tamaño Promedio (bytes)'}
                )
                fig_sizes.update_traces(textposition='top center', marker=dict(size=12))
                fig_sizes.update_layout(height=400)
                st.plotly_chart(fig_sizes, use_container_width=True)
        
        # NUEVO: Análisis de Correlaciones entre Países
        if 'pais' in df_filtrado.columns and 'fecha' in df_filtrado.columns and df_filtrado['pais'].nunique() > 1:
            st.markdown("---")
            st.markdown("### 🔗 Análisis de Correlaciones entre Países")
            
            # Crear matriz de registros por país y fecha
            matriz_pais_fecha = df_filtrado.groupby(['fecha', 'pais']).size().reset_index(name='registros')
            pivot_paises = matriz_pais_fecha.pivot(index='fecha', columns='pais', values='registros').fillna(0)
            
            if len(pivot_paises.columns) >= 2:
                # Calcular correlaciones
                correlaciones = pivot_paises.corr()
                
                # Encontrar pares con correlación negativa fuerte (compiten por recursos)
                pares_negativos = []
                for i in range(len(correlaciones.columns)):
                    for j in range(i+1, len(correlaciones.columns)):
                        corr_val = correlaciones.iloc[i, j]
                        if corr_val < -0.3:
                            pares_negativos.append({
                                'pais1': correlaciones.columns[i].upper(),
                                'pais2': correlaciones.columns[j].upper(),
                                'correlacion': corr_val
                            })
                
                if pares_negativos:
                    st.warning("⚠️ **Correlaciones negativas detectadas:**")
                    for par in pares_negativos:
                        st.write(f"- **{par['pais1']} vs {par['pais2']}**: Correlación {par['correlacion']:.2f}")
                        st.write(f"  → Cuando uno sube, el otro tiende a bajar. Posible competencia por recursos.")
                
                # Encontrar pares con correlación positiva fuerte (procesamiento en cadena)
                pares_positivos = []
                for i in range(len(correlaciones.columns)):
                    for j in range(i+1, len(correlaciones.columns)):
                        corr_val = correlaciones.iloc[i, j]
                        if corr_val > 0.7:
                            pares_positivos.append({
                                'pais1': correlaciones.columns[i].upper(),
                                'pais2': correlaciones.columns[j].upper(),
                                'correlacion': corr_val
                            })
                
                if pares_positivos:
                    st.success("✅ **Correlaciones positivas fuertes:**")
                    for par in pares_positivos:
                        st.write(f"- **{par['pais1']} vs {par['pais2']}**: Correlación {par['correlacion']:.2f}")
                        st.write(f"  → Ambos se mueven juntos. Posible procesamiento coordinado o dependencias compartidas.")
                
                if not pares_negativos and not pares_positivos:
                    st.info("ℹ️ No se detectaron correlaciones fuertes entre países - Operación independiente")

# Footer
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center'>
        <p>Dashboard FlyTXT Logs | Actualizado: {}</p>
    </div>
    """.format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
    unsafe_allow_html=True
)
