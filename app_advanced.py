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

# ---------- 计算素材得分函数 ----------
def calculate_score(df_filtered, col_map):
    """
    计算每条素材的得分
    得分规则：
    - CTR > 中位数 → +1分
    - CVR > 中位数 → +1分
    - 次留 > 中位数 → +1分
    - CPM < 中位数 → +1分
    最高4分（CPI已作为筛选条件，不再参与得分计算）
    """
    scores = pd.Series(0, index=df_filtered.index)
    
    # 需要计算的指标（已移除CPI，因为CPI作为筛选条件）
    metrics = {
        'ctr': {'col': 'CTR', 'direction': 'higher'},  # 越高越好
        'cvr': {'col': 'CVR', 'direction': 'higher'},
        'retention': {'col': '次留', 'direction': 'higher'},
        'cpm': {'col': 'CPM', 'direction': 'lower'},   # 越低越好
    }
    
    # 先计算中位数（包括CPI，虽然不参与得分计算，但要显示）
    medians = {}
    # 计算参与得分的指标中位数
    for key, config in metrics.items():
        col_name = config['col']
        if col_name in df_filtered.columns:
            cleaned = clean_numeric_column(df_filtered[col_name])
            valid_data = cleaned.dropna()
            if len(valid_data) > 0:
                medians[key] = valid_data.median()
            else:
                medians[key] = None
        else:
            medians[key] = None
    
    # 计算CPI中位数（虽然不参与得分，但要显示）
    if 'CPI' in df_filtered.columns:
        cpi_cleaned = clean_numeric_column(df_filtered['CPI'])
        cpi_valid = cpi_cleaned.dropna()
        if len(cpi_valid) > 0:
            medians['cpi'] = cpi_valid.median()
        else:
            medians['cpi'] = None
    else:
        medians['cpi'] = None
    
    # 计算每条素材的得分
    for key, config in metrics.items():
        col_name = config['col']
        if col_name in df_filtered.columns and medians[key] is not None:
            cleaned = clean_numeric_column(df_filtered[col_name])
            
            if config['direction'] == 'higher':
                # 越高越好：大于中位数得1分
                scores += (cleaned > medians[key]).astype(int)
            else:
                # 越低越好：小于中位数得1分
                scores += (cleaned < medians[key]).astype(int)
    
    return scores, medians

df = read_csv_auto('test.csv')
st.markdown("<h2 style='text-align: center;'>🎯 素材团队多维指标筛选分析工具</h2>", unsafe_allow_html=True)
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
    'retention': '次留',
    'spend': 'Spend',
    'roi': 'ROI1',
    'impression': 'Impression',
    'click': 'Click',
}

# 检查字段是否存在
missing_fields = []
for key, val in col_map.items():
    if val not in df.columns:
        missing_fields.append(val)

if missing_fields:
    st.warning(f"⚠️ 以下字段不存在：{', '.join(missing_fields)}，相关功能可能无法使用")

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

# 先筛选日期和国家（用于显示"总数据量"）
query_date_country = pd.Series([True] * len(df))

if sel_date is not None and col_map['date'] in df.columns:
    query_date_country &= df[col_map['date']].isin(sel_date)

if sel_country is not None and col_map['country'] in df.columns:
    query_date_country &= df[col_map['country']].isin(sel_country)

df_date_country_filtered = df[query_date_country].copy()

# ----------- 先计算中位数和得分（基于日期和国家的筛选，不受后续筛选影响） -----------
if len(df_date_country_filtered) > 0:
    scores, medians = calculate_score(df_date_country_filtered, col_map)
    df_date_country_filtered['得分'] = scores
else:
    scores = pd.Series()
    medians = {}
    st.sidebar.warning("⚠️ 日期和国家筛选后无数据")

# 安装数筛选
if col_map['install'] in df_date_country_filtered.columns:
    install_series = clean_numeric_column(df_date_country_filtered[col_map['install']])
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

# CPI筛选（放在安装数之后）
if col_map['cpi'] in df_date_country_filtered.columns:
    cpi_series = clean_numeric_column(df_date_country_filtered[col_map['cpi']])
    max_cpi = float(cpi_series.max()) if cpi_series.notna().any() else 10.0
    min_cpi = st.sidebar.number_input(
        "💰 最大CPI (安装成本)", 
        min_value=0.0, 
        max_value=max_cpi,
        value=max_cpi,
        step=0.01,
        format="%.2f",
        help="只显示CPI小于等于此值的数据（越低越好）"
    )
else:
    min_cpi = None
    st.sidebar.warning("未找到CPI字段")

# ----------- 应用安装数和CPI筛选（得分已计算，不受影响） -----------
# 使用df_date_country_filtered的索引创建query_base，确保索引匹配
query_base = pd.Series([True] * len(df_date_country_filtered), index=df_date_country_filtered.index)

if min_install is not None and col_map['install'] in df_date_country_filtered.columns:
    install_series = clean_numeric_column(df_date_country_filtered[col_map['install']])
    query_base &= install_series >= min_install

if min_cpi is not None and col_map['cpi'] in df_date_country_filtered.columns:
    cpi_series = clean_numeric_column(df_date_country_filtered[col_map['cpi']])
    query_base &= cpi_series <= min_cpi

df_base_filtered = df_date_country_filtered[query_base].copy()

# ----------- 得分筛选（得分已基于日期和国家计算，不受安装数和CPI影响） -----------
if len(df_base_filtered) > 0 and '得分' in df_base_filtered.columns:
    # 显示得分分布信息（基于当前筛选后的数据）
    st.sidebar.markdown("---")
    st.sidebar.subheader("📊 得分统计")
    score_dist = df_base_filtered['得分'].value_counts().sort_index(ascending=False)
    for score_val, count in score_dist.items():
        st.sidebar.text(f"得分 {score_val}: {count} 条素材")
    
    # 得分筛选
    max_score = int(df_base_filtered['得分'].max()) if len(df_base_filtered) > 0 else 4
    # 确保max_value至少比min_value大1，避免slider报错
    if max_score == 0:
        # 如果所有得分都是0，直接设置min_score为0，不显示slider
        min_score = 0
        st.sidebar.info("ℹ️ 所有素材得分均为0，无法进行得分筛选")
    else:
        min_score = st.sidebar.slider(
            "⭐ 最小得分",
            min_value=0,
            max_value=max_score,
            value=0,
            help="只显示得分大于等于此值的素材（最高4分）"
        )
    
    # 根据得分筛选
    df_final = df_base_filtered[df_base_filtered['得分'] >= min_score].copy()
elif len(df_date_country_filtered) == 0:
    df_final = pd.DataFrame()
    st.sidebar.warning("⚠️ 日期和国家筛选后无数据，无法计算得分")
else:
    df_final = pd.DataFrame()
    st.sidebar.warning("⚠️ 安装数和CPI筛选后无数据")

# ----------- 显示筛选结果统计 -----------
st.header("📈 数据概览")
col1, col2, col3, col4 = st.columns(4)
col1.metric("📊 总数据量", f"{len(df_date_country_filtered)} 条", help="筛选日期和国家后的数据量")
col2.metric("✅ 基础筛选后", f"{len(df_base_filtered)} 条", help="筛选日期、国家、安装数、CPI后的数据量")
col3.metric("⭐ 得分筛选后", f"{len(df_final)} 条", help="根据得分进一步筛选后的数据量")
if len(df_base_filtered) > 0:
    col4.metric("📉 得分筛选比例", f"{len(df_final)/len(df_base_filtered)*100:.1f}%")

st.markdown("---")

# ----------- 显示中位数（用于得分计算） -----------
if len(df_date_country_filtered) > 0 and medians:
    st.header("📊 中位数基准（用于得分计算）")
    st.info("💡 以下中位数基于【日期和国家筛选后】的数据计算，不受安装数和CPI筛选影响，用于判断每条素材是否达标")
    
    median_cols = st.columns(5)
    median_display = {
        'CTR': medians.get('ctr'),
        'CVR': medians.get('cvr'),
        '次留': medians.get('retention'),
        'CPI': medians.get('cpi'),
        'CPM': medians.get('cpm'),
    }
    
    for idx, (metric_name, median_val) in enumerate(median_display.items()):
        if median_val is not None:
            if metric_name in ['CTR', 'CVR', '次留']:
                display_val = f"{median_val:.2f}%"
            else:
                display_val = f"${median_val:.2f}"
            median_cols[idx].metric(f"{metric_name} 中位数", display_val)
        else:
            median_cols[idx].metric(f"{metric_name} 中位数", "无数据")

st.markdown("---")

# ----------- 数据表格展示（显示所有列） -----------
st.header("📋 筛选后数据详情（完整数据）")

if len(df_final) > 0:
    # 显示所有列，但将"得分"列放在前面方便查看
    all_cols = df_final.columns.tolist()
    if '得分' in all_cols:
        # 将得分列移到前面
        display_cols = ['得分'] + [col for col in all_cols if col != '得分']
    else:
        display_cols = all_cols
    
    st.dataframe(
        df_final[display_cols], 
        use_container_width=True,
        height=400
    )
    
    # 下载按钮
    csv_data = df_final.to_csv(index=False, encoding='utf-8-sig')
    st.download_button(
        '💾 下载筛选结果 (CSV)', 
        data=csv_data, 
        file_name=f'优秀素材筛选结果_{len(df_final)}条.csv', 
        mime='text/csv'
    )

    # ----------- 去重素材名称展示 -----------
    st.markdown("---")
    st.subheader("🧾 去重素材列表（Ad name）")

    if 'Ad name' in df_final.columns:
        # 统计每个素材出现的次数（在几次测试中表现优秀）
        ad_counts = df_final['Ad name'].value_counts().reset_index()
        ad_counts.columns = ['Ad name', '表现优秀次数']
        ad_counts = ad_counts.sort_values('表现优秀次数', ascending=False).reset_index(drop=True)

        st.caption(f"当前筛选条件下，共有 **{len(ad_counts)}** 支唯一素材。")

        # 以表格形式展示去重后的素材名称和出现次数
        st.dataframe(
            ad_counts,
            use_container_width=True,
            height=min(300, 40 + 24 * len(ad_counts))  # 根据数量自适应高度
        )
    else:
        st.info("未找到 `Ad name` 字段，无法展示去重素材列表。")
else:
    st.warning("⚠️ 筛选后没有数据，请调整筛选条件")

st.markdown("---")
st.info("💡 **使用说明**：\n"
        "1. **基础筛选**：先设置日期、国家、最小安装数、最大CPI\n"
        "2. **得分计算**：系统自动计算基础筛选后数据的中位数，然后为每条素材打分\n"
        "   - CTR/CVR/次留 > 中位数 → +1分\n"
        "   - CPM < 中位数 → +1分\n"
        "   - 最高4分（CPI已作为筛选条件，不参与得分）\n"
        "3. **得分筛选**：设置最小得分，只显示优秀素材\n"
        "4. **完整数据**：下方表格显示所有原始列，包括得分列")

