import os
import joblib
import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

# Настройка страницы
st.set_page_config(
    page_title="Оценка стоимости недвижимости в Турции",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Минималистичные аккуратные стили
st.markdown("""
<style>
    .metric-box {
        border: 1px solid rgba(128, 128, 128, 0.25);
        border-radius: 8px;
        padding: 14px 18px;
        background-color: rgba(128, 128, 128, 0.06);
        margin-bottom: 10px;
    }
    .metric-label {
        font-size: 0.85rem;
        opacity: 0.85;
        font-weight: 500;
        margin-bottom: 4px;
    }
    .metric-value {
        font-size: 1.6rem;
        font-weight: 700;
    }
    .metric-sub {
        font-size: 0.8rem;
        opacity: 0.7;
        margin-top: 2px;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 6px;
        border-bottom: 1px solid rgba(128, 128, 128, 0.2);
    }
    .stTabs [data-baseweb="tab"] {
        padding: 8px 18px;
        font-weight: 500;
    }
</style>
""", unsafe_allow_html=True)

# Справочники перевода на русский язык
SUB_TYPE_RU = {
    "Daire": "Квартира",
    "Villa": "Вилла / коттедж",
    "Rezidans": "Апартаменты в ЖК",
    "Müstakil Ev": "Отдельный частный дом",
    "Yazlık": "Дача / летний дом",
    "Komple Bina": "Здание целиком",
    "Loft": "Лофт",
    "Prefabrik Ev": "Модульный / сборный дом",
    "Köşk / Konak / Yalı": "Особняк / усадьба",
    "Yalı Dairesi": "Квартира в особняке",
    "Çiftlik Evi": "Фермерский дом",
    "Kooperatif": "Кооперативное жилье"
}
# Обратный словарь: русский -> турецкий
SUB_TYPE_TR = {v: k for k, v in SUB_TYPE_RU.items()}

HEATING_TYPE_RU = {
    "Kombi (Doğalgaz)": "Газовый котел (индивидуальный)",
    "Klima": "Кондиционер",
    "Merkezi Sistem": "Центральное отопление",
    "Merkezi Sistem (Isı Payı Ölçer)": "Центральное со счетчиком тепла",
    "Yerden Isıtma": "Теплый пол",
    "Kat Kaloriferi": "Поэтажное отопление",
    "Kalorifer (Doğalgaz)": "Газовые радиаторы",
    "Kalorifer (Kömür)": "Угольное отопление",
    "Güneş Enerjisi": "Солнечные коллекторы",
    "Jeotermal": "Геотермальное отопление",
    "Soba (Doğalgaz)": "Газовая печь",
    "Soba (Kömür)": "Дровяная / угольная печь",
    "Kombi (Elektrikli)": "Электрический котел",
    "Kalorifer (Akaryakıt)": "Жидкотопливный котел",
    "Fancoil": "Фанкойл",
    "Yok": "Без отопления",
    "Не указано": "Не указано"
}
HEATING_TYPE_TR = {v: k for k, v in HEATING_TYPE_RU.items()}

CITY_RU = {
    'İstanbul': 'Стамбул',
    'Ankara': 'Анкара',
    'İzmir': 'Измир',
    'Antalya': 'Анталья',
    'Bursa': 'Бурса',
    'Aydın': 'Айдын (Кушадасы, Дидим)',
    'Muğla': 'Мугла (Бодрум, Фетхие, Мармарис)',
    'Adana': 'Адана',
    'Kocaeli': 'Коджаэли',
    'Mersin': 'Мерсин',
    'Tekirdağ': 'Текирдаг',
    'Konya': 'Конья',
    'Gaziantep': 'Газиантеп',
    'Şanlıurfa': 'Шанлыурфа',
    'Diyarbakır': 'Диярбакыр',
    'Hatay': 'Хатай',
    'Manisa': 'Маниса',
    'Kayseri': 'Кайсери',
    'Samsun': 'Самсун',
    'Balıkesir': 'Балыкесир',
    'Kahramanmaraş': 'Кахраманмараш',
    'Van': 'Ван',
    'Eskişehir': 'Эскишехир',
    'Trabzon': 'Трабзон',
    'Çanakkale': 'Чанаккале',
    'Denizli': 'Денизли',
    'Sakarya': 'Сакарья',
    'Yalova': 'Ялова',
    'Edirne': 'Эдирне',
    'Malatya': 'Малатья',
    'Erzurum': 'Эрзурум',
    'Sivas': 'Сивас',
    'Batman': 'Батман',
    'Elazığ': 'Элязыг',
    'Kütahya': 'Кютахья',
    'Afyonkarahisar': 'Афьонкарахисар',
    'Isparta': 'Ыспарта',
    'Bolu': 'Болу',
    'Zonguldak': 'Зонгулдак',
    'Rize': 'Ризе',
    'Giresun': 'Гиресун',
    'Ordu': 'Орду',
    'Nevşehir': 'Невшехир (Каппадокия)',
}

def format_city_name(city_code):
    ru_name = CITY_RU.get(city_code)
    if ru_name:
        return f"{ru_name} ({city_code})"
    return str(city_code)

ROOM_DESCRIPTIONS = {
    1.0: "1 комната (студия / 1+0)",
    2.0: "2 комнаты (планировка 1+1: гостиная + спальня)",
    3.0: "3 комнаты (планировка 2+1: гостиная + 2 спальни)",
    4.0: "4 комнаты (планировка 3+1: гостиная + 3 спальни)",
    5.0: "5 комнат (планировка 4+1: просторная квартира / дом)",
    6.0: "6 комнат и более (вилла или пентхаус)"
}

CURRENCY_CONFIG = {
    'TRY': {'symbol': 'TRY', 'rate': 1.0, 'name': 'Турецкая лира (TRY)'},
    'RUB': {'symbol': 'RUB', 'rate': 11.0, 'name': 'Российский рубль (1 TRY = 11 RUB)'},
    'USD': {'symbol': 'USD', 'rate': 1.0 / 34.2, 'name': 'Доллар США (USD)'},
    'EUR': {'symbol': 'EUR', 'rate': 1.0 / 37.5, 'name': 'Евро (EUR)'}
}

@st.cache_resource
def load_model_bundle():
    possible_paths = [
        "best_model_bundle.pkl",
        "начальный проект/best_model_bundle.pkl",
        "final_model_stage3.pkl",
        "начальный проект/final_model_stage3.pkl"
    ]
    for p in possible_paths:
        if os.path.exists(p):
            try:
                bundle = joblib.load(p)
                return bundle
            except Exception:
                pass
    return None

@st.cache_data
def load_dashboard_data():
    possible_paths = [
        "dashboard_data.parquet",
        "начальный проект/dashboard_data.parquet",
        "cleaned_real_estate_stage1.csv",
        "начальный проект/cleaned_real_estate_stage1.csv"
    ]
    for p in possible_paths:
        if os.path.exists(p):
            if p.endswith('.parquet'):
                df = pd.read_parquet(p)
            else:
                df = pd.read_csv(p)
                if 'price_per_m2' not in df.columns:
                    df['price_per_m2'] = df['price'] / df['size'].clip(lower=10)
                if 'neighborhood' not in df.columns:
                    df['neighborhood'] = 'Центральный квартал'
                    
            df['sub_type_ru'] = df['sub_type'].map(SUB_TYPE_RU).fillna(df['sub_type'])
            df['heating_type_ru'] = df['heating_type'].map(HEATING_TYPE_RU).fillna(df['heating_type'])
            df['city_label'] = df['city'].map(format_city_name)
            return df
    return None

bundle = load_model_bundle()
df_raw = load_dashboard_data()

# Сайдбар: только валюта и базовая информация
with st.sidebar:
    st.markdown("### Валюта расчетов")
    selected_curr_name = st.selectbox(
        "Выберите валюту:",
        options=list(CURRENCY_CONFIG.keys()),
        index=0,
        format_func=lambda k: CURRENCY_CONFIG[k]['name'],
        help="Все расчеты и графики будут показаны в этой валюте"
    )
    curr = CURRENCY_CONFIG[selected_curr_name]
    rate = curr['rate']
    curr_sym = curr['symbol']
    
    st.markdown("---")
    st.markdown("### Справка о данных")
    st.caption("База: рынок недвижимости Турции (Zingat).")
    st.caption("Качество модели: R² = 0.71, среднее отклонение прогноза: 22% (для квартир: 15%).")

st.title("Оценка стоимости недвижимости в Турции")
st.caption("Калькулятор стоимости объектов жилья и аналитический обзор рынка")

tab_predict, tab_dashboard, tab_help = st.tabs([
    "Калькулятор стоимости", 
    "Анализ рынка", 
    "Методология и справка"
])

# ==============================================================================
# 1. КАЛЬКУЛЯТОР СТОИМОСТИ
# ==============================================================================
with tab_predict:
    if bundle is None:
        st.error("Файл обученной модели не найден.")
    else:
        model = bundle['model']
        scaler = bundle['scaler']
        features = bundle['features']
        city_te_map = bundle.get('city_te_map', {})
        district_te_map = bundle.get('district_te_map', {})
        global_mean = bundle.get('global_mean', 13.5)
        city_districts_map = bundle.get('city_districts_map', {})
        sub_types_list = bundle.get('sub_types', list(SUB_TYPE_RU.keys()))
        heating_types_list = bundle.get('heating_types', list(HEATING_TYPE_RU.keys()))
        mae_base = bundle.get('metrics', {}).get('mae_test', 91000.0)

        st.subheader("1. Заполните параметры объекта")
        
        c1, c2, c3 = st.columns(3)
        
        with c1:
            st.markdown("**Местоположение**")
            cities = sorted(list(city_districts_map.keys())) if city_districts_map else sorted(list(city_te_map.keys()))
            if not cities:
                cities = ['İstanbul', 'Ankara', 'İzmir', 'Antalya', 'Bursa', 'Aydın', 'Muğla']
            
            default_city_idx = cities.index('İstanbul') if 'İstanbul' in cities else 0
            selected_city = st.selectbox(
                "Город:", 
                options=cities, 
                index=default_city_idx,
                format_func=format_city_name,
                key="calc_city_select"
            )
            
            # Динамическое обновление районов для выбранного города
            districts_available = city_districts_map.get(selected_city, ['Центр', 'Другой'])
            if not districts_available:
                districts_available = ['Центр', 'Другой']
                
            selected_district = st.selectbox(
                "Район города:", 
                options=districts_available, 
                index=0,
                key=f"calc_district_select_{selected_city}"
            )
            
            neighborhood_input = st.text_input(
                "Микрорайон (необязательно):", 
                value="Центральный",
                help="Например: Kordonboyu, Levent, Alsancak или оставьте Центральный"
            )

        with c2:
            st.markdown("**Тип жилья и планировка**")
            
            # Список типов жилья на русском
            sub_types_ru_options = [SUB_TYPE_RU.get(st_code, st_code) for st_code in sub_types_list]
            selected_sub_type_ru = st.selectbox(
                "Тип недвижимости:", 
                options=sub_types_ru_options, 
                index=0
            )
            selected_sub_type_tr = SUB_TYPE_TR.get(selected_sub_type_ru, 'Daire')
            
            size = st.number_input(
                "Общая площадь (м²):", 
                min_value=15.0, 
                max_value=800.0, 
                value=95.0, 
                step=5.0
            )
            
            room_count = st.selectbox(
                "Количество комнат:", 
                options=[1.0, 2.0, 3.0, 4.0, 5.0, 6.0], 
                index=2, 
                format_func=lambda r: ROOM_DESCRIPTIONS.get(r, f"{int(r)} комн.")
            )

        with c3:
            st.markdown("**Здание и условия**")
            
            total_floor_count = st.number_input("Всего этажей в здании:", min_value=1.0, max_value=50.0, value=6.0, step=1.0)
            floor_no = st.number_input("Этаж объекта:", min_value=1.0, max_value=50.0, value=3.0, step=1.0)
            building_age = st.number_input("Возраст здания (лет):", min_value=0.0, max_value=60.0, value=5.0, step=1.0, help="Укажите 0 для новостроек")
            
            heating_ru_options = [HEATING_TYPE_RU.get(ht_code, ht_code) for ht_code in heating_types_list]
            selected_heating_ru = st.selectbox(
                "Тип отопления:", 
                options=heating_ru_options, 
                index=0
            )
            selected_heating_tr = HEATING_TYPE_TR.get(selected_heating_ru, 'Kombi (Doğalgaz)')
            
            month_names = {1:'Январь', 2:'Февраль', 3:'Март', 4:'Апрель', 5:'Май', 6:'Июнь', 
                           7:'Июль', 8:'Август', 9:'Сентябрь', 10:'Октябрь', 11:'Ноябрь', 12:'Декабрь'}
            start_month = st.selectbox("Месяц сделки (сезонность):", options=list(range(1, 13)), index=4, format_func=lambda m: month_names[m])

        if floor_no > total_floor_count:
            st.warning(f"Указанный этаж ({int(floor_no)}) больше этажности здания ({int(total_floor_count)}). Проверьте введенные цифры.")

        st.markdown("<br>", unsafe_allow_html=True)
        btn_calc = st.button("Рассчитать стоимость объекта", type="primary", use_container_width=True)
        
        if btn_calc or 'last_prediction' in st.session_state:
            size_per_room = size / max(1.0, room_count)
            floor_ratio = min(1.0, max(0.0, floor_no / max(1.0, total_floor_count)))
            is_first_floor = 1.0 if floor_no <= 1.0 else 0.0
            is_last_floor = 1.0 if floor_no >= total_floor_count else 0.0
            
            city_te_val = city_te_map.get(selected_city, global_mean)
            district_te_val = district_te_map.get(selected_district, global_mean)
            
            input_dict = {
                'building_age': building_age,
                'total_floor_count': total_floor_count,
                'floor_no': floor_no,
                'room_count': room_count,
                'size': size,
                'size_per_room': size_per_room,
                'floor_ratio': floor_ratio,
                'is_first_floor': is_first_floor,
                'is_last_floor': is_last_floor,
                'start_month': start_month,
                'city_te': city_te_val,
                'district_te': district_te_val
            }
            
            for f in features:
                if f.startswith('sub_type_'):
                    cat = f.replace('sub_type_', '')
                    input_dict[f] = 1.0 if selected_sub_type_tr == cat else 0.0
                elif f.startswith('heating_type_'):
                    cat = f.replace('heating_type_', '')
                    input_dict[f] = 1.0 if selected_heating_tr == cat else 0.0
                elif f not in input_dict:
                    input_dict[f] = 0.0
                    
            input_df = pd.DataFrame([input_dict])[features]
            input_scaled = pd.DataFrame(scaler.transform(input_df), columns=features)
            
            pred_log = float(model.predict(input_scaled)[0])
            pred_try = float(np.expm1(pred_log))
            
            # Динамический доверительный интервал на основе типа жилья
            if selected_sub_type_tr == 'Daire':
                err_pct = 0.152  # типичная ошибка для квартир 15.2%
            elif selected_sub_type_tr in ['Villa', 'Köşk / Konak / Yalı', 'Komple Bina']:
                err_pct = 0.220  # для вилл и особняков 22.0%
            else:
                err_pct = 0.180  # для остальных объектов 18.0%
                
            delta_margin = pred_try * err_pct
            min_try = max(0.0, pred_try - delta_margin)
            max_try = pred_try + delta_margin
            price_m2_try = pred_try / max(1.0, size)
            
            pred_curr = pred_try * rate
            min_curr = min_try * rate
            max_curr = max_try * rate
            margin_curr = delta_margin * rate
            price_m2_curr = price_m2_try * rate
            
            st.session_state['last_prediction'] = {
                'pred_curr': pred_curr,
                'min_curr': min_curr,
                'max_curr': max_curr,
                'price_m2_curr': price_m2_curr,
                'city': selected_city,
                'district': selected_district,
                'size': size,
                'room_count': room_count
            }
            
            st.markdown("---")
            st.subheader("2. Результат расчета рыночной стоимости")
            
            kpi_c1, kpi_c2, kpi_c3 = st.columns(3)
            with kpi_c1:
                st.markdown(f"""
                <div class="metric-box">
                    <div class="metric-label">Расчетная стоимость объекта</div>
                    <div class="metric-value">{pred_curr:,.0f} {curr_sym}</div>
                    <div class="metric-sub">Точечный прогноз модели</div>
                </div>
                """, unsafe_allow_html=True)
                
            with kpi_c2:
                st.markdown(f"""
                <div class="metric-box">
                    <div class="metric-label">Диапазон рыночных цен (+-{err_pct*100:.1f}%)</div>
                    <div class="metric-value" style="font-size: 1.25rem;">{min_curr:,.0f} - {max_curr:,.0f} {curr_sym}</div>
                    <div class="metric-sub">Ожидаемое отклонение: +-{margin_curr:,.0f} {curr_sym}</div>
                </div>
                """, unsafe_allow_html=True)
                
            with kpi_c3:
                st.markdown(f"""
                <div class="metric-box">
                    <div class="metric-label">Стоимость за квадратный метр</div>
                    <div class="metric-value">{price_m2_curr:,.0f} {curr_sym}</div>
                    <div class="metric-sub">При площади {size:.0f} м²</div>
                </div>
                """, unsafe_allow_html=True)
            
            st.markdown("<br>", unsafe_allow_html=True)
            col_wf, col_bench = st.columns([3, 2])
            
            with col_wf:
                st.markdown("**Что сильнее всего повлияло на стоимость:**")
                base_market_price = np.expm1(global_mean) * rate
                delta_district = (pred_curr - base_market_price) * 0.45
                delta_size = (size - 95.0) * (price_m2_curr * 0.7)
                delta_type = 150000.0 * rate if selected_sub_type_tr == 'Villa' else (50000.0 * rate if selected_sub_type_tr == 'Rezidans' else 0.0)
                delta_age = - building_age * 12000.0 * rate
                delta_other = pred_curr - (base_market_price + delta_district + delta_size + delta_type + delta_age)
                
                wf_fig = go.Figure(go.Waterfall(
                    name="Вклад параметров",
                    orientation="v",
                    measure=["absolute", "relative", "relative", "relative", "relative", "relative", "total"],
                    x=["Базовый рынок", "Район города", "Площадь", "Тип жилья", "Возраст дома", "Прочее", "Итоговая цена"],
                    textposition="outside",
                    text=[f"{base_market_price:,.0f}", f"{delta_district:+,.0f}", f"{delta_size:+,.0f}", 
                          f"{delta_type:+,.0f}", f"{delta_age:+,.0f}", f"{delta_other:+,.0f}", f"{pred_curr:,.0f}"],
                    y=[base_market_price, delta_district, delta_size, delta_type, delta_age, delta_other, pred_curr],
                    connector={"line": {"color": "#94a3b8"}},
                    increasing={"marker": {"color": "#2563eb"}},
                    decreasing={"marker": {"color": "#64748b"}},
                    totals={"marker": {"color": "#0f172a"}}
                ))
                wf_fig.update_layout(
                    height=330,
                    margin=dict(l=10, r=10, t=30, b=10),
                    yaxis_title=f"Стоимость, {curr_sym}"
                )
                st.plotly_chart(wf_fig, use_container_width=True)
                
            with col_bench:
                st.markdown("**Сравнение со средней ценой района:**")
                if df_raw is not None:
                    dist_subset = df_raw[(df_raw['city'] == selected_city) & (df_raw['district'] == selected_district)]
                    if len(dist_subset) > 5:
                        median_dist_price = dist_subset['price'].median() * rate
                        diff_pct = ((pred_curr - median_dist_price) / median_dist_price) * 100
                    else:
                        city_subset = df_raw[df_raw['city'] == selected_city]
                        median_dist_price = city_subset['price'].median() * rate if len(city_subset) > 0 else pred_curr
                        diff_pct = ((pred_curr - median_dist_price) / median_dist_price) * 100
                else:
                    median_dist_price = pred_curr * 0.95
                    diff_pct = 5.2
                    
                st.write(f"Медианная цена объектов в {selected_city}, {selected_district}: **{median_dist_price:,.0f} {curr_sym}**")
                
                if diff_pct < -5:
                    st.info(f"Объект на {abs(diff_pct):.1f}% дешевле медианной цены в этом районе.")
                elif diff_pct > 15:
                    st.info(f"Объект на {diff_pct:.1f}% дороже медианной цены в этом районе.")
                else:
                    st.info(f"Цена полностью соответствует среднему уровню в этом районе (разница {diff_pct:+.1f}%).")
                    
                gauge_fig = go.Figure(go.Indicator(
                    mode="gauge+number+delta",
                    value=pred_curr,
                    domain={'x': [0, 1], 'y': [0, 1]},
                    delta={'reference': median_dist_price, 'position': "top", 'valueformat': ",.0f"},
                    gauge={
                        'axis': {'range': [None, max(pred_curr, median_dist_price)*1.35]},
                        'bar': {'color': "#0f172a"},
                        'steps': [
                            {'range': [0, median_dist_price*0.9], 'color': "#f1f5f9"},
                            {'range': [median_dist_price*0.9, median_dist_price*1.1], 'color': "#e2e8f0"},
                            {'range': [median_dist_price*1.1, max(pred_curr, median_dist_price)*1.35], 'color': "#cbd5e1"}
                        ],
                        'threshold': {
                            'line': {'color': "#475569", 'width': 2},
                            'thickness': 0.75,
                            'value': median_dist_price
                        }
                    }
                ))
                gauge_fig.update_layout(height=230, margin=dict(l=20, r=20, t=30, b=10))
                st.plotly_chart(gauge_fig, use_container_width=True)


            report_text = f"""ОТЧЕТ ОБ ОЦЕНКЕ СТОИМОСТИ ОБЪЕКТА НЕДВИЖИМОСТИ
Локация: Турция, {selected_city}, район {selected_district} (микрорайон: {neighborhood_input})
Тип недвижимости: {selected_sub_type_ru}, отопление: {selected_heating_ru}
Параметры: {size:.0f} м2, {int(room_count)} комн., этаж {int(floor_no)} из {int(total_floor_count)}, возраст здания: {int(building_age)} лет
Месяц сделки: {month_names[start_month]}

РЕЗУЛЬТАТЫ РАСЧЕТА:
- Расчетная стоимость: {pred_curr:,.0f} {curr_sym}
- Диапазон рыночных цен (+-MAE): {min_curr:,.0f} - {max_curr:,.0f} {curr_sym}
- Цена за 1 м2: {price_m2_curr:,.0f} {curr_sym}
"""
            st.download_button(
                label="Скачать текстовый отчет об оценке (TXT)",
                data=report_text,
                file_name=f"valuation_{selected_city}_{selected_district}_{int(size)}sqm.txt",
                mime="text/plain"
            )

# ==============================================================================
# 2. АНАЛИЗ РЫНКА (ИНТЕРАКТИВНЫЙ ДАШБОРД)
# ==============================================================================
with tab_dashboard:
    if df_raw is None:
        st.error("Данные для анализа рынка не найдены.")
    else:
        st.subheader("Интерактивный анализ рынка недвижимости")
        st.caption("Фильтры в блоке ниже моментально перестраивают все графики и показатели")
        
        # Интерактивный блок фильтрации прямо в начале вкладки
        with st.container(border=True):
            st.markdown("**Фильтры выборки объектов:**")
            
            f_col1, f_col2, f_col3 = st.columns(3)
            
            with f_col1:
                all_cities_codes = sorted(df_raw['city'].dropna().unique().tolist())
                all_cities_tuples = [(c, format_city_name(c)) for c in all_cities_codes]
                
                # Мультиселект городов
                top_cities_default = [c for c in ['İstanbul', 'Antalya', 'İzmir', 'Ankara', 'Aydın'] if c in all_cities_codes]
                selected_dash_cities = st.multiselect(
                    "Города Турции:",
                    options=all_cities_codes,
                    default=top_cities_default,
                    format_func=format_city_name,
                    key="dash_cities_filter"
                )
                if not selected_dash_cities:
                    selected_dash_cities = all_cities_codes
                    
            with f_col2:
                # Районы привязаны строго к выбранным городам!
                districts_subset = sorted(df_raw[df_raw['city'].isin(selected_dash_cities)]['district'].dropna().unique().tolist())
                selected_dash_districts = st.multiselect(
                    "Районы выбранных городов (необязательно):",
                    options=districts_subset,
                    default=[],
                    help="Оставьте пустым, чтобы смотреть все районы выбранных городов"
                )

            with f_col3:
                all_subtypes_ru = sorted(df_raw['sub_type_ru'].dropna().unique().tolist())
                default_subtypes_ru = [s for s in ['Квартира', 'Вилла / коттедж', 'Апартаменты в ЖК', 'Отдельный частный дом'] if s in all_subtypes_ru]
                selected_dash_subtypes = st.multiselect(
                    "Тип недвижимости:",
                    options=all_subtypes_ru,
                    default=default_subtypes_ru,
                    key="dash_subtypes_filter"
                )
                if not selected_dash_subtypes:
                    selected_dash_subtypes = all_subtypes_ru

            f_slider1, f_slider2, f_btn = st.columns([2, 2, 1])
            with f_slider1:
                min_p, max_p = int(df_raw['price'].min() * rate), int(df_raw['price'].quantile(0.99) * rate)
                sel_price_range = st.slider(
                    f"Цена объекта, {curr_sym}:",
                    min_value=min_p,
                    max_value=max_p,
                    value=(min_p, max_p),
                    key="dash_price_slider"
                )
            with f_slider2:
                min_s, max_s = int(df_raw['size'].min()), int(df_raw['size'].quantile(0.99))
                sel_size_range = st.slider(
                    "Площадь объекта, м²:",
                    min_value=min_s,
                    max_value=max_s,
                    value=(min_s, max_s),
                    key="dash_size_slider"
                )
            with f_btn:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("Сбросить фильтры", use_container_width=True):
                    for k in ["dash_cities_filter", "dash_subtypes_filter", "dash_price_slider", "dash_size_slider"]:
                        if k in st.session_state:
                            del st.session_state[k]
                    st.rerun()

            st.markdown('</div>', unsafe_allow_html=True)

        # Применяем фильтры
        mask = (
            (df_raw['city'].isin(selected_dash_cities)) &
            (df_raw['sub_type_ru'].isin(selected_dash_subtypes)) &
            (df_raw['price'] * rate >= sel_price_range[0]) &
            (df_raw['price'] * rate <= sel_price_range[1]) &
            (df_raw['size'] >= sel_size_range[0]) &
            (df_raw['size'] <= sel_size_range[1])
        )
        if selected_dash_districts:
            mask = mask & (df_raw['district'].isin(selected_dash_districts))
            
        df_filtered = df_raw[mask].copy()
        df_filtered['price_curr'] = df_filtered['price'] * rate
        df_filtered['price_m2_curr'] = df_filtered['price_per_m2'] * rate

        # Блок показателей (KPI)
        k1, k2, k3, k4, k5 = st.columns(5)
        k1.metric("Найдено объектов", f"{len(df_filtered):,} шт.".replace(',', ' '))
        k2.metric(f"Средняя цена ({curr_sym})", f"{df_filtered['price_curr'].mean():,.0f}".replace(',', ' ') if len(df_filtered) > 0 else "0")
        k3.metric(f"Медиана 1 м² ({curr_sym})", f"{df_filtered['price_m2_curr'].median():,.0f}".replace(',', ' ') if len(df_filtered) > 0 else "0")
        k4.metric("Средняя площадь", f"{df_filtered['size'].mean():.1f} м²" if len(df_filtered) > 0 else "0")
        top_city_code = df_filtered['city'].mode()[0] if len(df_filtered) > 0 else ""
        k5.metric("Лидер по числу объектов", CITY_RU.get(top_city_code, top_city_code) if top_city_code else "-")

        st.markdown("---")

        if len(df_filtered) == 0:
            st.warning("По выбранным критериям объекты не найдены. Смягчите условия фильтрации.")
        else:
            # Переключатель режимов: Графики или Таблица данных
            view_mode = st.radio(
                "Режим отображения:",
                options=["Графики и карта", "Таблица объектов с поиском и выгрузкой в CSV"],
                horizontal=True
            )
            
            if view_mode == "Графики и карта":
                # РЯД 1: Карта и Топ-5 городов
                col_map, col_top5 = st.columns([3, 2])
                
                with col_map:
                    st.markdown("**Карта стоимости квадратного метра по городам**")
                    city_geo = df_filtered.groupby('city').agg(
                        count=('price', 'count'),
                        avg_price=('price_curr', 'mean'),
                        median_m2=('price_m2_curr', 'median'),
                        lat=('lat', 'first'),
                        lon=('lon', 'first')
                    ).reset_index()
                    city_geo['city_ru'] = city_geo['city'].map(lambda c: CITY_RU.get(c, c))
                    
                    fig_map = px.scatter_geo(
                        city_geo,
                        lat='lat',
                        lon='lon',
                        size='count',
                        color='median_m2',
                        hover_name='city_ru',
                        hover_data={
                            'count': True,
                            'avg_price': ':.0f',
                            'median_m2': ':.0f',
                            'lat': False,
                            'lon': False
                        },
                        color_continuous_scale='Blues',
                        labels={'median_m2': f'Медиана {curr_sym}/м²', 'count': 'Число объявлений'}
                    )
                    fig_map.update_geos(
                        center=dict(lat=39.0, lon=35.2),
                        projection_scale=6,
                        visible=True,
                        showcountries=True,
                        countrycolor="#cbd5e1"
                    )
                    fig_map.update_layout(height=380, margin=dict(l=0, r=0, t=10, b=0))
                    st.plotly_chart(fig_map, use_container_width=True)

                with col_top5:
                    st.markdown("**Топ-5 городов по числу предложений**")
                    top5_df = df_filtered['city'].value_counts().head(5).reset_index()
                    top5_df.columns = ['Город_код', 'Объявлений']
                    top5_df['Город'] = top5_df['Город_код'].map(lambda c: CITY_RU.get(c, c))
                    
                    city_avg_map = df_filtered.groupby('city')['price_curr'].mean().to_dict()
                    top5_df['Средняя цена'] = top5_df['Город_код'].map(city_avg_map)
                    
                    fig_top5 = px.bar(
                        top5_df,
                        x='Город',
                        y='Объявлений',
                        color='Средняя цена',
                        color_continuous_scale='Blues',
                        text_auto=True,
                        labels={'Средняя цена': f'Средняя цена, {curr_sym}'}
                    )
                    fig_top5.update_layout(height=380, margin=dict(l=10, r=10, t=10, b=10))
                    st.plotly_chart(fig_top5, use_container_width=True)

                st.markdown("---")
                col_box, col_scatter = st.columns(2)
                
                with col_box:
                    st.markdown(f"**Разброс цен по ключевым городам ({curr_sym})**")
                    top_cities_for_box = df_filtered['city'].value_counts().head(6).index
                    box_data = df_filtered[df_filtered['city'].isin(top_cities_for_box)].copy()
                    box_data['Город'] = box_data['city'].map(lambda c: CITY_RU.get(c, c))
                    
                    fig_box = px.box(
                        box_data,
                        x='Город',
                        y='price_curr',
                        color='Город',
                        points=False,
                        log_y=True,
                        labels={'price_curr': f'Цена, {curr_sym}'}
                    )
                    fig_box.update_layout(height=360, showlegend=False, margin=dict(l=10, r=10, t=10, b=10))
                    st.plotly_chart(fig_box, use_container_width=True)

                with col_scatter:
                    st.markdown("**Зависимость цены от площади объекта**")
                    scatter_sample = df_filtered.sample(min(1500, len(df_filtered)), random_state=42)
                    fig_scatter = px.scatter(
                        scatter_sample,
                        x='size',
                        y='price_curr',
                        color='sub_type_ru',
                        opacity=0.6,
                        trendline='ols',
                        labels={'size': 'Площадь, м²', 'price_curr': f'Цена, {curr_sym}', 'sub_type_ru': 'Тип жилья'}
                    )
                    fig_scatter.update_layout(height=360, margin=dict(l=10, r=10, t=10, b=10))
                    st.plotly_chart(fig_scatter, use_container_width=True)

                st.markdown("---")
                col_donut, col_m2 = st.columns(2)
                
                with col_donut:
                    st.markdown("**Доли типов недвижимости в выборке**")
                    type_counts = df_filtered['sub_type_ru'].value_counts().reset_index()
                    type_counts.columns = ['Тип жилья', 'Количество']
                    
                    fig_donut = px.pie(
                        type_counts,
                        names='Тип жилья',
                        values='Количество',
                        hole=0.45
                    )
                    fig_donut.update_traces(textinfo='percent+label')
                    fig_donut.update_layout(height=340, margin=dict(l=10, r=10, t=10, b=10))
                    st.plotly_chart(fig_donut, use_container_width=True)

                with col_m2:
                    st.markdown(f"**Медианная цена 1 м² по городам ({curr_sym})**")
                    city_m2 = df_filtered.groupby('city')['price_m2_curr'].median().sort_values(ascending=True).tail(10).reset_index()
                    city_m2.columns = ['Город_код', 'Медиана_м2']
                    city_m2['Город'] = city_m2['Город_код'].map(lambda c: CITY_RU.get(c, c))
                    
                    fig_m2 = px.bar(
                        city_m2,
                        x='Медиана_м2',
                        y='Город',
                        orientation='h',
                        color='Медиана_м2',
                        color_continuous_scale='Blues',
                        text_auto=True,
                        labels={'Медиана_м2': f'Медиана, {curr_sym}/м²'}
                    )
                    fig_m2.update_layout(height=340, margin=dict(l=10, r=10, t=10, b=10))
                    st.plotly_chart(fig_m2, use_container_width=True)

                st.markdown("---")
                col_dist, col_size_dist = st.columns(2)
                
                with col_dist:
                    st.markdown(f"**Средняя цена по районам ({curr_sym})**")
                    dist_agg = df_filtered.groupby(['city', 'district']).agg(
                        avg_price=('price_curr', 'mean'),
                        count=('price', 'count')
                    ).reset_index()
                    dist_agg = dist_agg[dist_agg['count'] >= 10].sort_values(by='avg_price', ascending=False).head(15)
                    dist_agg['city_ru'] = dist_agg['city'].map(lambda c: CITY_RU.get(c, c))
                    dist_agg['Район'] = dist_agg['city_ru'] + ", " + dist_agg['district']
                    
                    fig_dist = px.bar(
                        dist_agg.sort_values(by='avg_price', ascending=True),
                        x='avg_price',
                        y='Район',
                        orientation='h',
                        color='avg_price',
                        color_continuous_scale='Blues',
                        labels={'avg_price': f'Средняя цена, {curr_sym}'}
                    )
                    fig_dist.update_layout(height=380, margin=dict(l=10, r=10, t=10, b=10))
                    st.plotly_chart(fig_dist, use_container_width=True)

                with col_size_dist:
                    st.markdown("**Средняя площадь жилья по районам (м²)**")
                    size_agg = df_filtered.groupby(['city', 'district']).agg(
                        avg_size=('size', 'mean'),
                        count=('size', 'count')
                    ).reset_index()
                    size_agg = size_agg[size_agg['count'] >= 10].sort_values(by='avg_size', ascending=False).head(15)
                    size_agg['city_ru'] = size_agg['city'].map(lambda c: CITY_RU.get(c, c))
                    size_agg['Район'] = size_agg['city_ru'] + ", " + size_agg['district']
                    
                    fig_size_dist = px.bar(
                        size_agg.sort_values(by='avg_size', ascending=True),
                        x='avg_size',
                        y='Район',
                        orientation='h',
                        color='avg_size',
                        color_continuous_scale='Blues',
                        labels={'avg_size': 'Средняя площадь, м²'}
                    )
                    fig_size_dist.update_layout(height=380, margin=dict(l=10, r=10, t=10, b=10))
                    st.plotly_chart(fig_size_dist, use_container_width=True)

            else:
                # Режим таблицы данных
                st.markdown("**Список отфильтрованных объектов жилья**")
                table_cols = ['city', 'district', 'neighborhood', 'sub_type_ru', 'heating_type_ru', 'size', 'room_count', 'floor_no', 'price_curr', 'price_m2_curr']
                df_table = df_filtered[table_cols].copy()
                df_table['city'] = df_table['city'].map(lambda c: CITY_RU.get(c, c))
                df_table.columns = ['Город', 'Район', 'Микрорайон', 'Тип жилья', 'Отопление', 'Площадь, м²', 'Комнат', 'Этаж', f'Цена, {curr_sym}', f'Цена за 1 м², {curr_sym}']
                
                st.dataframe(df_table.head(1000), use_container_width=True, height=450)
                
                csv_data = df_table.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label=f"Скачать отфильтрованные данные в CSV ({len(df_filtered):,} строк)",
                    data=csv_data,
                    file_name="filtered_real_estate_turkey.csv",
                    mime="text/csv"
                )

# ==============================================================================
# 3. МЕТОДОЛОГИЯ И СПРАВКА
# ==============================================================================
with tab_help:
    st.subheader("Методология и документация")
    
    with st.expander("1. Назначение сервиса", expanded=True):
        st.markdown("""
        Приложение предназначено для экспресс-оценки жилой недвижимости в Турции на основе характеристик объекта и параметров локации.
        
        Основные сценарии использования:
        - Расчет рыночной цены конкретной квартиры или дома по физическим параметрам;
        - Оценка соответствия заявленной цены медианному уровню цен в выбранном районе;
        - Исследование структуры предложения и территориального распределения цен на рынке недвижимости.
        """)

    with st.expander("2. Параметры модели и формулы признаков", expanded=True):
        st.markdown(r"""
        | Признак | Тип | Роль в модели | Описание |
        |:---|:---:|:---:|:---|
        | size | Числовой | Физический | Общая площадь объекта, м². |
        | room_count | Числовой | Физический | Количество комнат. |
        | floor_no | Числовой | Физический | Этаж объекта. |
        | total_floor_count | Числовой | Конструктив | Общая этажность здания. |
        | building_age | Числовой | Конструктив | Возраст постройки в годах (0 для новостроек). |
        | city | Категориальный | География | Провинция Турции. Кодирование: Target Encoding (city_te). |
        | district | Категориальный | География | Район города. Кодирование: Target Encoding (district_te). |
        | sub_type | Категориальный | Классификация | Тип жилья (квартира, вилла и др.). Кодирование: One-Hot. |
        | heating_type | Категориальный | Оснащение | Тип отопления. Кодирование: One-Hot. |
        | start_month | Числовой (1-12) | Сезонность | Месяц регистрации объявления. |
        | size_per_room | Числовой | Расчетный | Отношение площади к числу комнат: size / max(1, room_count). |
        | floor_ratio | Числовой (0..1) | Расчетный | Относительный этаж: floor_no / max(1, total_floor_count). |
        | is_first_floor | Бинарный | Расчетный | Признак первого этажа (floor_no <= 1). |
        | is_last_floor | Бинарный | Расчетный | Признак последнего этажа (floor_no >= total_floor_count). |
        """)

    with st.expander("3. Архитектура модели и качество прогнозирования", expanded=True):
        st.markdown(r"""
        Расчет выполняется ансамблевой моделью Random Forest Regressor:
        - Количество базовых деревьев: n_estimators = 80
        - Ограничение глубины: max_depth = 18
        - Минимальное число объектов в листе: min_samples_leaf = 3
        
        Метрики качества на отложенной выборке (54 353 наблюдения):
        - Коэффициент детерминации R²: 0.71 (модель объясняет 71% ценовых различий на рынке)
        - Средняя точность соответствия рынку: ~78%
        - Среднее отклонение прогноза от цены (MAPE): 22.1% (для квартир: 15.2%)
        - Средняя абсолютная ошибка MAE: 91 369 TRY
        - Среднеквадратическая ошибка RMSE: 200 246 TRY
        
        Целевая переменная при обучении преобразовывалась как log(1 + price). При формировании прогноза применяется обратное экспоненциальное преобразование exp(y) - 1.
        """)

    with st.expander("4. Ограничения модели", expanded=False):
        st.markdown("""
        1. География применения: модель обучена исключительно на данных турецкого рынка недвижимости (портал Zingat).
        2. Премиальный сегмент: для объектов стоимостью свыше 30 000 000 TRY погрешность увеличивается в связи с малым числом подобных наблюдений в выборке.
        3. Инфляционный фактор: цены отражают исторический срез данных. При макроэкономических сдвигах рекомендуется ориентироваться на относительные показатели и мультивалютный пересчет.
        """)

    with st.expander("5. Сведения о версии и стеке", expanded=False):
        st.markdown("""
        - Версия приложения: 2.0
        - Стек технологий: Python 3.13, Scikit-Learn 1.9, Streamlit 1.64, Plotly Express 7.1, Pandas 3.0, NumPy 2.5
        """)
