import streamlit as st
import pandas as pd
import numpy as np

# ---------- 自动编码识别读取 ----------
def read_csv_auto(filepath):
    for enc in ['utf-8', 'gbk', 'gb2312']:
        try:
            return pd.read_csv(filepath, encoding=enc)
        except Exception:
            continue
    return None

# ---------- 数据清洗函数：处理百分比、货币符号等 ----------
def clean_numeric_column(series):
    """清理数值列，去除%和$符号"""
    if series.dtype == 'object':
        # 转换为字符串，去除%和$符号，以及空格
        cleaned = series.astype(str).str.replace('%', '').str.replace('$', '').str.replace(',', '').str.strip()
        # 转换为数值，无法转换的变为NaN
        return pd.to_numeric(cleaned, errors='coerce')
    return pd.to_numeric(series, errors='coerce')

df = read_csv_auto('datas/test.csv')
st.title("🎯 素材分发团队多维指标分析工具")
st.markdown("---")

if df is None:
    st.error("❌ 数据读取失败，请检查文件路径和编码！")
    st.stop()

# ---------- 字段映射（根据实际CSV字段名） ----------
col_map = {
    'date': '测试日期',
    'country': '国家',
    'install': 'Install(AF)',  # 使用AF安装数
    'ctr': 'CTR',
    'cvr': 'CVR',
    'cpi': 'CPI',
    'cpm': 'CPM',
    'spend': 'Spend',
    'roi': 'ROI1',
    'impression': 'Impression',
    'click': 'Click',
}

# 检查字段是否存在
for key, val in col_map.items():
    if val not in df.columns:
        st.warning(f"⚠️ 字段 '{val}' 不存在，请检查数据文件")

# ---------- 侧边栏：筛选条件 ----------
st.sidebar.header("📊 筛选条件")

# 日期筛选
if col_map['date'] in df.columns:
    date_options = sorted(df[col_map['date']].dropna().unique().tolist())
    sel_date = st.sidebar.multiselect(
        "📅 选择测试日期", 
        date_options, 
        default=date_options,
        help="可以选择一个或多个测试时间段"
    )
else:
    sel_date = None
    st.sidebar.warning("未找到日期字段")

# 国家筛选
if col_map['country'] in df.columns:
    country_options = sorted(df[col_map['country']].dropna().unique().tolist())
    sel_country = st.sidebar.multiselect(
        "🌍 选择国家", 
        country_options, 
        default=country_options,
        help="可以选择一个或多个国家"
    )
else:
    sel_country = None
    st.sidebar.warning("未找到国家字段")

# 安装数筛选
if col_map['install'] in df.columns:
    install_series = clean_numeric_column(df[col_map['install']])
    max_install = int(install_series.max()) if install_series.notna().any() else 1000
    min_install = st.sidebar.number_input(
        "📥 最小安装数 (Install AF)", 
        min_value=0, 
        max_value=max_install,
        value=0,
        help="只显示安装数大于等于此值的数据"
    )
else:
    min_install = None
    st.sidebar.warning("未找到安装数字段")

# ----------- 动态筛选数据 -----------
query = pd.Series([True] * len(df))

if sel_date is not None and col_map['date'] in df.columns:
    query &= df[col_map['date']].isin(sel_date)

if sel_country is not None and col_map['country'] in df.columns:
    query &= df[col_map['country']].isin(sel_country)

if min_install is not None and col_map['install'] in df.columns:
    install_series = clean_numeric_column(df[col_map['install']])
    query &= install_series >= min_install

df_sel = df[query].copy()

# ----------- 显示筛选结果统计 -----------
st.header("📈 数据概览")
col1, col2, col3 = st.columns(3)
col1.metric("📊 总数据量", f"{len(df)} 条")
col2.metric("✅ 筛选后数据量", f"{len(df_sel)} 条")
if len(df) > 0:
    col3.metric("📉 筛选比例", f"{len(df_sel)/len(df)*100:.1f}%")

st.markdown("---")

# ----------- 关键指标中位数计算 -----------
st.header("🎯 关键指标中位数")

# 定义要计算的指标
metrics_config = {
    'CTR (点击率)': {'col': 'CTR', 'format': 'percentage'},
    'CVR (转化率)': {'col': 'CVR', 'format': 'percentage'},
    'CPI (安装成本)': {'col': 'CPI', 'format': 'currency'},
    'CPM (千次展示成本)': {'col': 'CPM', 'format': 'currency'},
    'ROI (投资回报率)': {'col': 'ROI1', 'format': 'percentage'},
}

metrics_cols = st.columns(len(metrics_config))

for idx, (metric_name, config) in enumerate(metrics_config.items()):
    col_name = config['col']
    if col_name in df_sel.columns:
        # 清理数据
        cleaned_data = clean_numeric_column(df_sel[col_name])
        # 去除NaN值
        valid_data = cleaned_data.dropna()
        
        if len(valid_data) > 0:
            median_val = valid_data.median()
            if config['format'] == 'percentage':
                display_val = f"{median_val:.2f}%"
            elif config['format'] == 'currency':
                display_val = f"${median_val:.2f}"
            else:
                display_val = f"{median_val:.2f}"
            
            metrics_cols[idx].metric(metric_name, display_val)
        else:
            metrics_cols[idx].metric(metric_name, "无数据")
    else:
        metrics_cols[idx].metric(metric_name, "字段缺失")

st.markdown("---")

# ----------- 数据表格展示 -----------
st.header("📋 筛选后数据详情")

# 选择要显示的列
if len(df_sel) > 0:
    # 显示关键列
    display_cols = ['测试日期', '国家', 'Ad name', 'Spend', 'Install(AF)', 'CTR', 'CVR', 'CPI', 'CPM', 'ROI1']
    available_cols = [col for col in display_cols if col in df_sel.columns]
    
    st.dataframe(
        df_sel[available_cols].head(200), 
        use_container_width=True,
        height=400
    )
    
    # 下载按钮
    csv_data = df_sel.to_csv(index=False, encoding='utf-8-sig')  # 使用utf-8-sig确保Excel能正确打开中文
    st.download_button(
        '💾 下载筛选结果 (CSV)', 
        data=csv_data, 
        file_name=f'筛选结果_{len(df_sel)}条.csv', 
        mime='text/csv'
    )
else:
    st.warning("⚠️ 筛选后没有数据，请调整筛选条件")

st.markdown("---")
st.info("💡 **使用提示**：\n- 左侧边栏可以筛选日期、国家、安装数\n- 上方显示关键指标的中位数\n- 下方表格显示筛选后的详细数据\n- 可以下载筛选结果进行进一步分析")