import pandas as pd
import logging

log = logging.getLogger(__name__)

def calculate_movement_analytics(data_frames):
    """
    Menghitung analitik pergerakan stok[cite: 154].
    """
    log.info("Menghitung analitik pergerakan...")
    
    df_movements = data_frames['stock_movements'].copy()
    
    # Pastikan 'movement_date' adalah datetime
    df_movements['movement_date'] = pd.to_datetime(df_movements['movement_date'])
    df_movements = df_movements.set_index('movement_date')

    # 1. Movement Trends (Daily, Weekly, Monthly) [cite: 158]
    # Kita hitung jumlah pergerakan (IN/OUT)
    df_out = df_movements[df_movements['movement_type'] == 'OUT']
    
    daily_trends = df_out.resample('D')['quantity'].count().reset_index(name='daily_movements')
    weekly_trends = df_out.resample('W')['quantity'].count().reset_index(name='weekly_movements')
    monthly_trends = df_out.resample('ME')['quantity'].count().reset_index(name='monthly_movements')
    
    # 2. Peak Periods Identification [cite: 157]
    # Kita cari hari dalam seminggu (Day of Week) yang paling sibuk
    daily_trends['day_of_week'] = daily_trends['movement_date'].dt.day_name()
    peak_dow = daily_trends.groupby('day_of_week')['daily_movements'].mean().sort_values(ascending=False).reset_index()
    
    # 3. Seasonal Patterns Detection [cite: 159]
    # Kita cari bulan yang paling sibuk
    monthly_trends['month_name'] = monthly_trends['movement_date'].dt.month_name()
    peak_month = monthly_trends.groupby('month_name')['monthly_movements'].mean().sort_values(ascending=False).reset_index()
    
    log.info(f"Analitik pergerakan selesai. Hari tersibuk: {peak_dow.iloc[0]['day_of_week']}. Bulan tersibuk: {peak_month.iloc[0]['month_name']}.")
    
    # Simpan hasil kalkulasi untuk Laporan
    data_frames['daily_trends'] = daily_trends
    data_frames['weekly_trends'] = weekly_trends
    data_frames['monthly_trends'] = monthly_trends
    data_frames['peak_day_of_week'] = peak_dow
    data_frames['peak_month'] = peak_month
    
    return data_frames